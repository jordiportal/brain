"""
Buscador RAG
"""

from typing import List, Optional, Dict, Any
import structlog

from .vectorstore import RAGVectorStore, SearchResult
from .config import get_rag_config

logger = structlog.get_logger()


class RAGSearcher:
    """Buscador semántico en documentos RAG"""
    
    def __init__(
        self,
        collection: str = "default",
        embedding_model: str = None,
        embedding_base_url: str = None
    ):
        self.collection = collection
        self.vectorstore = RAGVectorStore(
            collection=collection,
            embedding_model=embedding_model,
            embedding_base_url=embedding_base_url
        )
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = None
    ) -> List[Dict[str, Any]]:
        """
        Buscar documentos relevantes para una query
        
        Args:
            query: Texto de búsqueda
            top_k: Número máximo de resultados
            min_score: Score mínimo para incluir resultados
            
        Returns:
            Lista de documentos con content, metadata y score
        """
        config = get_rag_config()
        min_score = min_score or config.similarity_threshold
        
        results = await self.vectorstore.search(query, top_k=top_k)
        
        # Filtrar por score mínimo
        filtered = [
            {
                "content": r.content,
                "metadata": r.metadata,
                "score": r.score,
                "chunk_id": r.chunk_id
            }
            for r in results
            if r.score >= min_score
        ]
        
        logger.info(
            f"Búsqueda RAG completada",
            collection=self.collection,
            query=query[:50],
            results=len(filtered),
            top_score=filtered[0]["score"] if filtered else 0
        )
        
        return filtered
    
    async def search_with_context(
        self,
        query: str,
        top_k: int = 5,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Buscar y formatear contexto para LLM
        
        Returns:
            Dict con context (texto formateado) y sources (lista de fuentes)
        """
        results = await self.search(query, top_k=top_k)
        
        if not results:
            return {
                "context": "",
                "sources": [],
                "has_context": False
            }
        
        # Formatear contexto
        context_parts = []
        sources = []
        
        for i, result in enumerate(results):
            source = result["metadata"].get("source", "desconocido")
            context_parts.append(
                f"[Fragmento {i+1} - Fuente: {source}]\n{result['content']}"
            )
            
            if include_sources and source not in sources:
                sources.append(source)
        
        return {
            "context": "\n\n---\n\n".join(context_parts),
            "sources": sources,
            "has_context": True,
            "num_results": len(results)
        }
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de la colección"""
        return await self.vectorstore.get_stats()


# Función helper para búsqueda rápida
async def quick_search(
    query: str,
    collection: str = "default",
    top_k: int = 5,
    embedding_base_url: str = None
) -> List[Dict[str, Any]]:
    """
    Búsqueda rápida sin crear instancia
    
    Uso:
        results = await quick_search("¿cómo configurar nginx?")
    """
    searcher = RAGSearcher(
        collection=collection,
        embedding_base_url=embedding_base_url
    )
    return await searcher.search(query, top_k=top_k)
