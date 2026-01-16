"""
Router de la API para RAG
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
import tempfile
import os
import structlog

from .ingestor import DocumentIngestor
from .searcher import RAGSearcher
from .vectorstore import RAGVectorStore
from .config import get_rag_config_from_strapi
from src.config import get_settings
from src.providers import get_active_llm_provider

logger = structlog.get_logger()
settings = get_settings()
router = APIRouter(prefix="/rag", tags=["RAG"])


async def get_embedding_config() -> tuple[str, str]:
    """Obtener URL y modelo de embeddings desde Strapi o fallback"""
    try:
        provider = await get_active_llm_provider()
        if provider:
            base_url = provider.base_url
            model = provider.embedding_model or "qwen3-embedding:8b"
            logger.info(f"Usando config de Strapi: {base_url}, {model}")
            return base_url, model
    except Exception as e:
        logger.warning(f"No se pudo obtener config de Strapi: {e}")
    
    # Fallback - intentar leer de variable de entorno o usar default
    import os
    fallback_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    logger.info(f"Usando fallback: {fallback_url}")
    return fallback_url, "qwen3-embedding:8b"


# ============================================
# Request/Response Models
# ============================================

class IngestUrlRequest(BaseModel):
    url: str
    collection: str = "default"
    document_id: Optional[str] = None
    metadata: Optional[dict] = None


class IngestTextRequest(BaseModel):
    text: str
    document_id: str
    collection: str = "default"
    metadata: Optional[dict] = None
    # Parámetros opcionales para override de config
    embedding_url: Optional[str] = None
    embedding_model: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    collection: str = "default"
    top_k: int = 5
    min_score: Optional[float] = None
    # Parámetros opcionales para override de config
    embedding_url: Optional[str] = None
    embedding_model: Optional[str] = None


class SearchResult(BaseModel):
    content: str
    metadata: dict
    score: float


class SearchResponse(BaseModel):
    query: str
    collection: str
    results: List[dict]
    total: int


class CollectionStats(BaseModel):
    collection: str
    total_chunks: int
    total_documents: int


# ============================================
# Endpoints - Ingestión
# ============================================

@router.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    collection: str = Form("default"),
    document_id: Optional[str] = Form(None)
):
    """
    Ingestar un archivo subido directamente
    
    Formatos soportados: PDF, TXT, MD, DOCX, HTML
    """
    # Verificar extensión
    allowed_extensions = {".pdf", ".txt", ".md", ".docx", ".html"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {file_ext}. Permitidos: {allowed_extensions}"
        )
    
    # Guardar temporalmente
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        base_url, embed_model = await get_embedding_config()
        
        ingestor = DocumentIngestor(
            collection=collection,
            embedding_base_url=base_url,
            embedding_model=embed_model
        )
        
        result = await ingestor.ingest_file(
            file_path=tmp_path,
            document_id=document_id or file.filename.rsplit(".", 1)[0],
            metadata={"original_filename": file.filename}
        )
        
        return {
            "status": "success",
            "message": f"Documento indexado correctamente",
            **result
        }
    
    finally:
        # Limpiar archivo temporal
        os.unlink(tmp_path)


@router.post("/ingest/url")
async def ingest_url(request: IngestUrlRequest):
    """
    Ingestar documento desde URL
    
    Útil para indexar documentos desde Strapi u otras fuentes
    """
    try:
        base_url, embed_model = await get_embedding_config()
        
        ingestor = DocumentIngestor(
            collection=request.collection,
            embedding_base_url=base_url,
            embedding_model=embed_model
        )
        
        result = await ingestor.ingest_from_url(
            url=request.url,
            document_id=request.document_id,
            metadata=request.metadata
        )
        
        return {
            "status": "success",
            "message": "Documento indexado desde URL",
            **result
        }
    
    except Exception as e:
        logger.error(f"Error ingesting URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/text")
async def ingest_text(request: IngestTextRequest):
    """
    Ingestar texto directamente
    """
    try:
        base_url, embed_model = await get_embedding_config()
        
        # Override con parámetros del request si se proporcionan
        if request.embedding_url:
            base_url = request.embedding_url
        if request.embedding_model:
            embed_model = request.embedding_model
        
        ingestor = DocumentIngestor(
            collection=request.collection,
            embedding_base_url=base_url,
            embedding_model=embed_model
        )
        
        result = await ingestor.ingest_text(
            text=request.text,
            document_id=request.document_id,
            metadata=request.metadata
        )
        
        return {
            "status": "success",
            "message": "Texto indexado correctamente",
            **result
        }
    
    except Exception as e:
        logger.error(f"Error ingesting text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/strapi/{document_id}")
async def ingest_from_strapi(
    document_id: str,
    collection: str = Query("default")
):
    """
    Ingestar documento desde Strapi por su documentId
    
    Descarga el archivo de Strapi y lo indexa
    """
    try:
        import httpx
        
        # Obtener documento de Strapi
        strapi_url = "http://strapi:1337"  # URL interna en Docker
        
        async with httpx.AsyncClient() as client:
            # Obtener info del documento
            response = await client.get(
                f"{strapi_url}/api/rag-documents/{document_id}",
                params={"populate": "file"}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail="Documento no encontrado en Strapi")
            
            doc_data = response.json().get("data", {})
            file_info = doc_data.get("file")
            
            if not file_info:
                raise HTTPException(status_code=400, detail="El documento no tiene archivo adjunto")
            
            # Construir URL del archivo
            file_url = file_info.get("url", "")
            if file_url.startswith("/"):
                file_url = f"{strapi_url}{file_url}"
        
        # Ingestar desde URL
        base_url, embed_model = await get_embedding_config()
        
        ingestor = DocumentIngestor(
            collection=collection,
            embedding_base_url=base_url,
            embedding_model=embed_model
        )
        
        result = await ingestor.ingest_from_url(
            url=file_url,
            document_id=document_id,
            metadata={
                "strapi_document_id": document_id,
                "name": doc_data.get("name", "")
            }
        )
        
        # Actualizar estado en Strapi
        async with httpx.AsyncClient() as client:
            await client.put(
                f"{strapi_url}/api/rag-documents/{document_id}",
                json={
                    "data": {
                        "status": "indexed",
                        "chunksCount": result["chunks_created"],
                        "indexedAt": "now"
                    }
                }
            )
        
        return {
            "status": "success",
            "message": "Documento de Strapi indexado",
            **result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting from Strapi: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Endpoints - Búsqueda
# ============================================

@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    Buscar documentos por similitud semántica
    """
    try:
        base_url, embed_model = await get_embedding_config()
        
        # Override con parámetros del request si se proporcionan
        if request.embedding_url:
            base_url = request.embedding_url
        if request.embedding_model:
            embed_model = request.embedding_model
        
        searcher = RAGSearcher(
            collection=request.collection,
            embedding_base_url=base_url,
            embedding_model=embed_model
        )
        
        results = await searcher.search(
            query=request.query,
            top_k=request.top_k,
            min_score=request.min_score
        )
        
        return SearchResponse(
            query=request.query,
            collection=request.collection,
            results=results,
            total=len(results)
        )
    
    except Exception as e:
        logger.error(f"Error searching: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_documents_get(
    query: str,
    collection: str = "default",
    top_k: int = 5
):
    """
    Buscar documentos (GET para pruebas rápidas)
    """
    return await search_documents(SearchRequest(
        query=query,
        collection=collection,
        top_k=top_k
    ))


# ============================================
# Endpoints - Gestión de Colecciones
# ============================================

@router.get("/collections")
async def list_collections():
    """
    Listar colecciones disponibles con estadísticas
    """
    try:
        import asyncpg
        
        pool = await asyncpg.create_pool(
            settings.database_url.replace("+psycopg2", ""),
            min_size=1,
            max_size=5
        )
        
        async with pool.acquire() as conn:
            collections = await conn.fetch("""
                SELECT 
                    collection,
                    COUNT(*) as total_chunks,
                    COUNT(DISTINCT document_id) as total_documents
                FROM rag_chunks
                GROUP BY collection
                ORDER BY collection
            """)
        
        await pool.close()
        
        return {
            "collections": [
                {
                    "name": row["collection"],
                    "total_chunks": row["total_chunks"],
                    "total_documents": row["total_documents"]
                }
                for row in collections
            ]
        }
    
    except Exception as e:
        logger.error(f"Error listing collections: {e}")
        # Si la tabla no existe, retornar lista vacía
        return {"collections": []}


@router.get("/collections/{collection}/stats")
async def get_collection_stats(collection: str):
    """
    Obtener estadísticas de una colección
    """
    try:
        base_url, embed_model = await get_embedding_config()
        
        vectorstore = RAGVectorStore(
            collection=collection,
            embedding_base_url=base_url,
            embedding_model=embed_model
        )
        stats = await vectorstore.get_stats()
        return stats
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collections/{collection}")
async def delete_collection(collection: str):
    """
    Eliminar una colección completa
    """
    try:
        base_url, embed_model = await get_embedding_config()
        
        vectorstore = RAGVectorStore(
            collection=collection,
            embedding_base_url=base_url,
            embedding_model=embed_model
        )
        count = await vectorstore.delete_collection()
        
        return {
            "status": "success",
            "message": f"Colección '{collection}' eliminada",
            "chunks_deleted": count
        }
    
    except Exception as e:
        logger.error(f"Error deleting collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    collection: str = "default"
):
    """
    Eliminar un documento específico del índice
    """
    try:
        base_url, embed_model = await get_embedding_config()
        
        ingestor = DocumentIngestor(
            collection=collection,
            embedding_base_url=base_url,
            embedding_model=embed_model
        )
        count = await ingestor.delete_document(document_id)
        
        return {
            "status": "success",
            "message": f"Documento '{document_id}' eliminado",
            "chunks_deleted": count
        }
    
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
