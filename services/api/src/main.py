"""
Brain API - Entry Point
Servidor FastAPI para gestión de cadenas de pensamiento con LangChain/LangGraph
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
import structlog

from src.config import get_settings
from src.db import get_db
from src.llm.router import router as llm_router
from src.engine.router import router as chains_router
from src.engine.chains import register_all_chains
from src.rag.router import router as rag_router
from src.tools.router import router as tools_router
from src.tools.tool_registry import tool_registry
from src.mcp.router import router as mcp_router
from src.mcp.client import mcp_client
from src.browser.service import browser_service
from src.browser.router import router as browser_router
from src.engine.chains.agents.router import router as subagents_router
from src.openai_compat.router import router as openai_compat_router
from src.config_router import router as config_router
from src.auth_router import router as auth_router
from src.monitoring.router import router as monitoring_router
from src.middleware.monitoring import MonitoringMiddleware

# Configurar logging estructurado
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    # Startup
    logger.info("Iniciando Brain API", version=settings.app_version)
    
    # Inicializar conexión a base de datos
    db = get_db()
    await db.connect()
    logger.info("Conexión a PostgreSQL establecida")
    
    # Registrar cadenas predefinidas
    register_all_chains()
    logger.info("Cadenas predefinidas registradas")

    # Cargar herramientas built-in (core tools)
    tool_registry.register_builtin_tools()
    logger.info("Herramientas built-in registradas")
    
    # Registrar subagentes especializados
    try:
        from src.engine.chains.agents import register_all_subagents
        register_all_subagents()
        logger.info("Subagentes especializados registrados")
    except Exception as e:
        logger.warning(f"No se pudieron registrar subagentes: {e}")
    
    # Cargar herramientas OpenAPI desde BD
    try:
        openapi_count = await tool_registry.load_openapi_tools()
        logger.info(f"Herramientas OpenAPI cargadas: {openapi_count}")
    except Exception as e:
        logger.warning(f"No se pudieron cargar herramientas OpenAPI: {e}")
    
    # Cargar conexiones MCP desde BD
    try:
        mcp_count = await mcp_client.load_connections_from_db()
        logger.info(f"Conexiones MCP cargadas: {mcp_count}")
        
        # Asegurar que existe conexión de Playwright (auto-configura si no existe)
        await mcp_client.ensure_playwright_connection()
    except Exception as e:
        logger.warning(f"No se pudieron cargar conexiones MCP: {e}")
    
    yield
    
    # Shutdown
    logger.info("Cerrando Brain API")
    
    # Desconectar servidores MCP
    await mcp_client.disconnect_all()
    logger.info("Conexiones MCP cerradas")
    
    # Cerrar servicio de navegador
    await browser_service.shutdown()
    logger.info("Servicio de navegador cerrado")
    
    # Cerrar conexión a base de datos
    await db.disconnect()
    logger.info("Conexión a PostgreSQL cerrada")


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API para gestión de cadenas de pensamiento con LangChain/LangGraph",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configurar CORS - permitir todas las peticiones en desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight por 1 hora
)

# Middleware de monitorización (captura métricas de todas las requests)
app.add_middleware(MonitoringMiddleware)

# Incluir routers
app.include_router(llm_router, prefix="/api/v1")
app.include_router(chains_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(tools_router, prefix="/api/v1")
app.include_router(mcp_router, prefix="/api/v1")
app.include_router(browser_router, prefix="/api/v1")
app.include_router(subagents_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")
app.include_router(monitoring_router, prefix="/api/v1")

# Auth Router (sin prefix para compatibilidad con Strapi)
app.include_router(auth_router)

# OpenAI-Compatible API (sin prefix /api para compatibilidad)
app.include_router(openai_compat_router)


# ===========================================
# Health Check Endpoints
# ===========================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Verificar estado de la API"""
    return {
        "status": "healthy",
        "version": settings.app_version,
    }


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Verificar que la API está lista para recibir tráfico"""
    from src.engine.registry import chain_registry
    
    mcp_connections = mcp_client.list_connections()
    mcp_connected = sum(1 for c in mcp_connections if c.get("is_connected"))
    
    tools_count = len(tool_registry.tools)
    openapi_tools_count = len([t for t in tool_registry.tools.values() if t.type.value == "openapi"])
    
    return {
        "status": "ready",
        "chains_registered": len(chain_registry.list_chain_ids()),
        "tools_total": tools_count,
        "tools_openapi": openapi_tools_count,
        "mcp_connections": len(mcp_connections),
        "mcp_connected": mcp_connected,
        "database": "connected",  # TODO: verificar real
        "redis": "connected",     # TODO: verificar real
    }


# ===========================================
# API Endpoints - RAG
# ===========================================

@app.get("/api/v1/rag/collections", tags=["RAG"])
async def list_rag_collections():
    """Listar colecciones de documentos RAG"""
    return {
        "collections": [
            {
                "name": settings.vector_collection_name,
                "document_count": 0,
                "embedding_model": settings.default_embedding_model
            }
        ]
    }


@app.post("/api/v1/rag/search", tags=["RAG"])
async def rag_search(query: str, collection: str = None, top_k: int = 5):
    """Búsqueda semántica en documentos RAG"""
    # TODO: Implementar búsqueda vectorial con pgvector
    return {
        "query": query,
        "results": [],
        "total": 0
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
