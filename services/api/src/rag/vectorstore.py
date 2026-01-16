"""
Vector Store con pgvector
"""

from typing import List, Optional, Dict, Any
import asyncpg
import structlog
from dataclasses import dataclass

from .embeddings import OllamaEmbeddings
from .config import get_rag_config
from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class SearchResult:
    """Resultado de búsqueda"""
    content: str
    metadata: Dict[str, Any]
    score: float
    chunk_id: int


class RAGVectorStore:
    """Vector store usando pgvector directamente"""
    
    def __init__(
        self,
        collection: str = "default",
        embedding_model: str = None,
        embedding_base_url: str = None
    ):
        self.collection = collection
        config = get_rag_config()
        
        self.embeddings = OllamaEmbeddings(
            base_url=embedding_base_url or config.embedding_base_url,
            model=embedding_model or config.embedding_model
        )
        
        self._pool: Optional[asyncpg.Pool] = None
    
    async def _get_pool(self) -> asyncpg.Pool:
        """Obtener o crear pool de conexiones"""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                settings.database_url.replace("+psycopg2", ""),
                min_size=1,
                max_size=10
            )
        return self._pool
    
    async def ensure_table(self):
        """Asegurar que la tabla de vectores existe"""
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            # Crear extensión pgvector si no existe
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Crear tabla para chunks
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id SERIAL PRIMARY KEY,
                    collection VARCHAR(255) NOT NULL,
                    document_id VARCHAR(255),
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    embedding vector(4096),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Crear índice IVFFlat para búsqueda (soporta hasta 16000 dims)
            # Nota: HNSW solo soporta 2000 dims, IVFFlat soporta más
            try:
                # Primero verificar si hay datos para crear el índice
                count = await conn.fetchval("SELECT COUNT(*) FROM rag_chunks")
                if count > 0:
                    await conn.execute("""
                        CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx 
                        ON rag_chunks 
                        USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists = 100)
                    """)
            except Exception as e:
                # Ignorar error si el índice ya existe o no hay suficientes filas
                logger.warning(f"No se pudo crear índice ivfflat: {e}")
            
            # Índice para filtrar por colección
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS rag_chunks_collection_idx 
                ON rag_chunks (collection)
            """)
            
            logger.info("Tabla rag_chunks verificada/creada")
    
    async def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        document_id: str = None
    ) -> List[int]:
        """Añadir documentos al vector store"""
        await self.ensure_table()
        
        if metadatas is None:
            metadatas = [{}] * len(texts)
        
        # Generar embeddings
        logger.info(f"Generando embeddings para {len(texts)} chunks...")
        embeddings = await self.embeddings.aembed_documents(texts)
        
        pool = await self._get_pool()
        chunk_ids = []
        
        async with pool.acquire() as conn:
            for text, metadata, embedding in zip(texts, metadatas, embeddings):
                # Serializar metadata a JSON string
                import json
                metadata_json = json.dumps(metadata) if metadata else '{}'
                
                # Insertar chunk
                chunk_id = await conn.fetchval("""
                    INSERT INTO rag_chunks (collection, document_id, content, metadata, embedding)
                    VALUES ($1, $2, $3, $4::jsonb, $5)
                    RETURNING id
                """, self.collection, document_id, text, metadata_json, str(embedding))
                
                chunk_ids.append(chunk_id)
        
        logger.info(f"Añadidos {len(chunk_ids)} chunks a colección '{self.collection}'")
        return chunk_ids
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[SearchResult]:
        """Buscar documentos similares"""
        await self.ensure_table()
        
        # Generar embedding de la query
        query_embedding = await self.embeddings.aembed_query(query)
        
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            # Búsqueda por similitud coseno
            # 1 - distancia coseno = similitud coseno
            results = await conn.fetch("""
                SELECT 
                    id,
                    content,
                    metadata,
                    1 - (embedding <=> $1::vector) as score
                FROM rag_chunks
                WHERE collection = $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
            """, str(query_embedding), self.collection, top_k)
        
        return [
            SearchResult(
                content=row["content"],
                metadata=row["metadata"] or {},
                score=float(row["score"]),
                chunk_id=row["id"]
            )
            for row in results
        ]
    
    async def delete_by_document(self, document_id: str) -> int:
        """Eliminar chunks de un documento"""
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM rag_chunks
                WHERE collection = $1 AND document_id = $2
            """, self.collection, document_id)
            
            # Parsear "DELETE X" para obtener el count
            count = int(result.split()[-1]) if result else 0
            logger.info(f"Eliminados {count} chunks del documento {document_id}")
            return count
    
    async def delete_collection(self) -> int:
        """Eliminar toda una colección"""
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM rag_chunks WHERE collection = $1
            """, self.collection)
            
            count = int(result.split()[-1]) if result else 0
            logger.info(f"Eliminada colección '{self.collection}' ({count} chunks)")
            return count
    
    async def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de la colección"""
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_chunks,
                    COUNT(DISTINCT document_id) as total_documents,
                    MIN(created_at) as oldest_chunk,
                    MAX(created_at) as newest_chunk
                FROM rag_chunks
                WHERE collection = $1
            """, self.collection)
        
        return {
            "collection": self.collection,
            "total_chunks": stats["total_chunks"],
            "total_documents": stats["total_documents"],
            "oldest_chunk": stats["oldest_chunk"].isoformat() if stats["oldest_chunk"] else None,
            "newest_chunk": stats["newest_chunk"].isoformat() if stats["newest_chunk"] else None
        }
    
    async def close(self):
        """Cerrar conexiones"""
        if self._pool:
            await self._pool.close()
            self._pool = None
