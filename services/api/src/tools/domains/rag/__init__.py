"""
RAG Domain Tools - Herramientas de Recuperación Aumentada para el RAG Agent

Estas herramientas permiten:
1. Buscar información en documentos indexados (RAG)
2. Ingerir nuevos documentos al knowledge base
3. Ver estadísticas de colecciones
"""

from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger()


async def rag_search(
    query: str,
    collection: str = "default",
    top_k: int = 5,
    min_score: float = 0.5
) -> Dict[str, Any]:
    """
    Busca información relevante en documentos indexados usando RAG.
    
    Esta herramienta realiza búsqueda semántica en el knowledge base,
    recuperando los chunks de documentos más relevantes para la query.
    
    Args:
        query: Pregunta o consulta de búsqueda
        collection: Colección de documentos a buscar (default: "default")
        top_k: Número máximo de resultados (default: 5)
        min_score: Score mínimo de similitud (0.0-1.0, default: 0.5)
    
    Returns:
        Dict con:
        - success: bool
        - results: Lista de documentos relevantes con content, metadata, score
        - context: Texto formateado listo para usar en prompts
        - total_found: Número de resultados encontrados
        - collection: Colección consultada
    
    Examples:
        >>> await rag_search("¿Qué es la transformación digital?")
        >>> await rag_search("Política de privacidad", collection="legal", top_k=3)
        >>> await rag_search("API endpoints", collection="docs", min_score=0.7)
    """
    
    logger.info(
        "🔍 RAG Search initiated",
        query=query[:100],
        collection=collection,
        top_k=top_k,
        min_score=min_score
    )
    
    try:
        from src.rag.searcher import RAGSearcher
        
        searcher = RAGSearcher(collection=collection)
        
        # Realizar búsqueda
        results = await searcher.search(
            query=query,
            top_k=top_k,
            min_score=min_score
        )
        
        if not results:
            return {
                "success": True,
                "results": [],
                "context": "No se encontraron documentos relevantes para esta consulta.",
                "total_found": 0,
                "collection": collection,
                "message": "No hay resultados. Considera indexar documentos relevantes primero."
            }
        
        # Formatear contexto para el LLM
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result.get("metadata", {}).get("source", "Documento desconocido")
            context_parts.append(
                f"[Documento {i}: {source}]\n"
                f"{result['content']}\n"
                f"(Relevancia: {result['score']:.2f})"
            )
        
        formatted_context = "\n\n---\n\n".join(context_parts)
        
        logger.info(
            "✅ RAG Search completed",
            results_found=len(results),
            top_score=results[0]["score"] if results else 0
        )
        
        return {
            "success": True,
            "results": results,
            "context": formatted_context,
            "total_found": len(results),
            "collection": collection,
            "message": f"Se encontraron {len(results)} documentos relevantes"
        }
        
    except Exception as e:
        logger.error(f"❌ RAG Search failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "results": [],
            "context": "",
            "total_found": 0,
            "collection": collection
        }


async def rag_ingest_document(
    source: str,
    collection: str = "default",
    document_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    source_type: str = "auto"
) -> Dict[str, Any]:
    """
    Indexa un nuevo documento en el knowledge base RAG.
    
    Soporta múltiples fuentes:
    - Archivos locales: /ruta/al/documento.pdf
    - URLs: https://ejemplo.com/documento.html
    - Texto directo: contenido en texto plano
    
    Args:
        source: Ruta del archivo, URL, o texto a indexar
        collection: Colección donde indexar (default: "default")
        document_id: ID único para el documento (opcional)
        metadata: Metadatos adicionales (autor, fecha, tags, etc.)
        source_type: Tipo de fuente - "file", "url", "text", o "auto" (detecta automáticamente)
    
    Returns:
        Dict con:
        - success: bool
        - document_id: ID asignado al documento
        - chunks_indexed: Número de chunks indexados
        - collection: Colección utilizada
        - source: Fuente original
        - message: Mensaje descriptivo
    
    Examples:
        >>> await rag_ingest_document("/docs/manual.pdf", collection="manuales")
        >>> await rag_ingest_document("https://docs.ejemplo.com/api", source_type="url")
        >>> await rag_ingest_document("Contenido a indexar...", source_type="text", metadata={"author": "Yo"})
    """
    
    logger.info(
        "📥 RAG Ingest initiated",
        source=source[:100],
        collection=collection,
        source_type=source_type
    )
    
    try:
        from src.rag.ingestor import DocumentIngestor
        from pathlib import Path
        import uuid
        
        # Detectar tipo automáticamente si es necesario
        if source_type == "auto":
            if source.startswith("http://") or source.startswith("https://"):
                source_type = "url"
            elif Path(source).exists():
                source_type = "file"
            else:
                source_type = "text"
        
        # Generar document_id si no se proporciona
        if not document_id:
            document_id = str(uuid.uuid4())[:8]
        
        ingestor = DocumentIngestor(collection=collection)
        
        # Ingerir según el tipo de fuente
        if source_type == "file":
            result = await ingestor.ingest_file(
                file_path=source,
                document_id=document_id,
                metadata=metadata or {}
            )
        elif source_type == "url":
            result = await ingestor.ingest_url(
                url=source,
                document_id=document_id,
                metadata=metadata or {}
            )
        elif source_type == "text":
            result = await ingestor.ingest_text(
                text=source,
                document_id=document_id,
                metadata=metadata or {}
            )
        else:
            raise ValueError(f"Tipo de fuente no soportado: {source_type}")
        
        logger.info(
            "✅ RAG Ingest completed",
            document_id=result.get("document_id"),
            chunks=result.get("chunks_indexed", 0),
            collection=collection
        )
        
        return {
            "success": True,
            "document_id": result.get("document_id", document_id),
            "chunks_indexed": result.get("chunks_indexed", 0),
            "collection": collection,
            "source": source[:100],
            "source_type": source_type,
            "message": f"Documento indexado exitosamente. {result.get('chunks_indexed', 0)} chunks en la colección '{collection}'"
        }
        
    except Exception as e:
        logger.error(f"❌ RAG Ingest failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "source": source[:100],
            "collection": collection,
            "message": f"Error al indexar documento: {str(e)}"
        }


async def rag_get_collection_stats(
    collection: str = "default"
) -> Dict[str, Any]:
    """
    Obtiene estadísticas de una colección RAG.
    
    Muestra información sobre documentos indexados, chunks totales,
    y estado general de la colección.
    
    Args:
        collection: Nombre de la colección (default: "default")
    
    Returns:
        Dict con:
        - success: bool
        - collection: Nombre de la colección
        - total_chunks: Número total de chunks
        - total_documents: Número de documentos únicos
        - collections_available: Lista de colecciones disponibles
        - message: Mensaje descriptivo
    
    Examples:
        >>> await rag_get_collection_stats()
        >>> await rag_get_collection_stats("manuales")
        >>> await rag_get_collection_stats("documentacion_legal")
    """
    
    logger.info("📊 RAG Collection Stats requested", collection=collection)
    
    try:
        from src.rag.vectorstore import RAGVectorStore
        
        vectorstore = RAGVectorStore(collection=collection)
        
        # Obtener estadísticas
        stats = await vectorstore.get_collection_stats()
        
        # Obtener lista de colecciones
        collections = await vectorstore.list_collections()
        
        logger.info(
            "✅ RAG Stats retrieved",
            collection=collection,
            chunks=stats.get("total_chunks", 0),
            documents=stats.get("total_documents", 0)
        )
        
        return {
            "success": True,
            "collection": collection,
            "total_chunks": stats.get("total_chunks", 0),
            "total_documents": stats.get("total_documents", 0),
            "collections_available": collections,
            "message": f"Colección '{collection}': {stats.get('total_chunks', 0)} chunks de {stats.get('total_documents', 0)} documentos. Colecciones disponibles: {', '.join(collections)}"
        }
        
    except Exception as e:
        logger.error(f"❌ RAG Stats failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "collection": collection,
            "message": f"Error al obtener estadísticas: {str(e)}"
        }


# ============================================
# Tool Registry Definitions
# ============================================

RAG_TOOLS = {
    "rag_search": {
        "id": "rag_search",
        "name": "rag_search",
        "description": """Busca información relevante en documentos indexados usando RAG (Retrieval Augmented Generation).

Esta herramienta realiza búsqueda semántica en el knowledge base, recuperando los documentos más relevantes para responder preguntas.

Casos de uso:
- Responder preguntas sobre documentos indexados
- Encontrar información específica en manuales, documentación, etc.
- Verificar hechos basándose en documentos oficiales
- Recuperar contexto relevante para análisis

La búsqueda usa embeddings y similitud de coseno para encontrar los chunks más relevantes.

Args:
    query: Pregunta o consulta de búsqueda
    collection: Colección de documentos (default: "default")
    top_k: Número de resultados (default: 5)
    min_score: Score mínimo de relevancia 0.0-1.0 (default: 0.5)

Returns:
    Documentos relevantes con su contenido, metadatos (fuente, autor, etc.) y score de relevancia.
    También incluye 'context' formateado listo para usar en prompts.
""",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Pregunta o consulta de búsqueda"
                },
                "collection": {
                    "type": "string",
                    "description": "Colección de documentos a buscar",
                    "default": "default"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Número máximo de resultados",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20
                },
                "min_score": {
                    "type": "number",
                    "description": "Score mínimo de similitud (0.0-1.0)",
                    "default": 0.5,
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            },
            "required": ["query"]
        },
        "handler": rag_search
    },
    
    "rag_ingest_document": {
        "id": "rag_ingest_document",
        "name": "rag_ingest_document",
        "description": """Indexa un nuevo documento en el knowledge base RAG.

Permite añadir documentos para que estén disponibles en futuras búsquedas.
Soporta archivos locales (PDF, DOCX, TXT, MD, HTML), URLs, o texto directo.

El documento se divide en chunks, se generan embeddings y se almacenan en la base de datos vectorial.

Casos de uso:
- Indexar manuales de usuario para consultas posteriores
- Añadir documentación técnica al knowledge base
- Ingerir contratos o documentos legales
- Crear colecciones temáticas de documentos

Formatos soportados: PDF, DOCX, TXT, MD, HTML

Args:
    source: Ruta de archivo, URL, o texto a indexar
    collection: Colección donde indexar (default: "default")
    document_id: ID único opcional
    metadata: Metadatos adicionales (autor, fecha, tags)
    source_type: "file", "url", "text", o "auto" (detecta automáticamente)

Returns:
    Confirmación con document_id asignado y número de chunks indexados.
""",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Ruta del archivo, URL, o texto a indexar"
                },
                "collection": {
                    "type": "string",
                    "description": "Colección donde indexar",
                    "default": "default"
                },
                "document_id": {
                    "type": "string",
                    "description": "ID único para el documento (opcional)"
                },
                "metadata": {
                    "type": "object",
                    "description": "Metadatos adicionales (autor, fecha, tags, etc.)"
                },
                "source_type": {
                    "type": "string",
                    "enum": ["auto", "file", "url", "text"],
                    "description": "Tipo de fuente",
                    "default": "auto"
                }
            },
            "required": ["source"]
        },
        "handler": rag_ingest_document
    },
    
    "rag_get_collection_stats": {
        "id": "rag_get_collection_stats",
        "name": "rag_get_collection_stats",
        "description": """Obtiene estadísticas de una colección RAG.

Muestra información sobre documentos indexados, chunks totales, y estado general.
Útil para ver qué colecciones existen y cuánta información contienen.

Args:
    collection: Nombre de la colección (default: "default")

Returns:
    Estadísticas incluyendo total de chunks, documentos únicos, y lista de colecciones disponibles.
""",
        "parameters": {
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Nombre de la colección",
                    "default": "default"
                }
            },
            "required": []
        },
        "handler": rag_get_collection_stats
    }
}
