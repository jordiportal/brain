"""
Brain API - Entry Point
Servidor FastAPI para gestión de cadenas de pensamiento con LangChain/LangGraph
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
import structlog

from src.config import get_settings
from src.db import get_db
from src.llm.router import router as llm_router
from src.engine.router import router as chains_router
from src.engine.chains import get_builder
from src.rag.router import router as rag_router
from src.tools.router import router as tools_router
from src.tools.tool_registry import tool_registry
from src.mcp.router import router as mcp_router
from src.mcp.client import mcp_client
from src.browser.service import browser_service
from src.browser.router import router as browser_router
from src.engine.chains.agents.router import router as subagents_router
from src.engine.chains.agents.definitions_router import router as agent_definitions_router
from src.openai_compat.router import router as openai_compat_router
from src.config_router import router as config_router
from src.auth_router import router as auth_router
from src.user_router import router as user_router
from src.profile_router import router as profile_router
from src.task_router import router as task_router
from src.engine.task_router import router as engine_task_router
from src.conversation_router import router as conversation_router
from src.memory_router import router as memory_router
from src.monitoring.router import router as monitoring_router
from src.code_executor.router import router as workspace_router
from src.artifacts.router import router as artifacts_router
from src.middleware.monitoring import MonitoringMiddleware
from src.a2a.router import router as a2a_router
from src.a2a.errors import A2AProblemDetail, a2a_problem_handler
from src.a2a.middleware import A2AVersionMiddleware
from src.a2a.agent_card import build_agent_card
from src.skills.router import router as skills_router
from src.skills.sync_service import skill_sync_service

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

    # Auto-migrate
    try:
        await db.execute("""
            ALTER TABLE agent_definitions
            ADD COLUMN IF NOT EXISTS excluded_core_tools TEXT[] DEFAULT '{}'
        """)
    except Exception:
        pass

    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chain_versions (
                id SERIAL PRIMARY KEY,
                brain_chain_id INTEGER NOT NULL,
                version_number INTEGER NOT NULL,
                snapshot JSONB NOT NULL,
                changed_by VARCHAR(255),
                change_reason TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS chain_versions_chain_id_idx ON chain_versions (brain_chain_id)")
        await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS chain_versions_chain_version_idx ON chain_versions (brain_chain_id, version_number)")
    except Exception:
        pass

    # Engine v2: tasks, task_events, agent_states, memory tables
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id VARCHAR(255) PRIMARY KEY, context_id VARCHAR(255) NOT NULL,
                parent_task_id VARCHAR(255) REFERENCES tasks(id) ON DELETE SET NULL,
                agent_id VARCHAR(255), chain_id VARCHAR(255),
                state VARCHAR(50) NOT NULL DEFAULT 'submitted', state_reason TEXT,
                input JSONB NOT NULL, output JSONB,
                history JSONB DEFAULT '[]', artifacts JSONB DEFAULT '[]',
                checkpoint_thread_id VARCHAR(255),
                tokens_used INTEGER DEFAULT 0, cost_usd FLOAT DEFAULT 0.0,
                duration_ms INTEGER DEFAULT 0, iterations INTEGER DEFAULT 0,
                metadata JSONB DEFAULT '{}', created_by VARCHAR(255),
                created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW(),
                completed_at TIMESTAMPTZ
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_context ON tasks(context_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC)")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS task_events (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(255) NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                state VARCHAR(50) NOT NULL, reason TEXT,
                message JSONB, metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_task_events_task ON task_events(task_id)")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_states (
                agent_id VARCHAR(255) NOT NULL, context_id VARCHAR(255) NOT NULL,
                state JSONB DEFAULT '{}', updated_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (agent_id, context_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS memory_long_term (
                id SERIAL PRIMARY KEY, agent_id VARCHAR(255),
                user_id VARCHAR(255) NOT NULL, type VARCHAR(50) NOT NULL,
                content TEXT NOT NULL, embedding vector(768),
                source_task_id VARCHAR(255), relevance_score FLOAT DEFAULT 1.0,
                created_at TIMESTAMPTZ DEFAULT NOW(), accessed_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_memory_lt_user ON memory_long_term(user_id)")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS memory_episodes (
                id SERIAL PRIMARY KEY, agent_id VARCHAR(255),
                user_id VARCHAR(255) NOT NULL, context_id VARCHAR(255),
                summary TEXT NOT NULL, key_points JSONB DEFAULT '[]',
                task_ids TEXT[] DEFAULT '{}', message_count INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_episodes_user ON memory_episodes(user_id)")
        logger.info("Engine v2 tables verified")
    except Exception as e:
        logger.warning(f"Engine v2 auto-migrate: {e}")

    # Conversations: Brain as source of truth for chat history
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id VARCHAR(255) PRIMARY KEY, user_id VARCHAR(255) NOT NULL,
                title TEXT, chain_id VARCHAR(255), model VARCHAR(255),
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_conv_user_updated ON conversations(user_id, updated_at DESC)")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id VARCHAR(255) PRIMARY KEY,
                conversation_id VARCHAR(255) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role VARCHAR(50) NOT NULL, content TEXT NOT NULL DEFAULT '',
                parts JSONB, model VARCHAR(255), tokens_used INTEGER DEFAULT 0,
                task_id VARCHAR(255), metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_cmsg_conv ON conversation_messages(conversation_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_cmsg_conv_created ON conversation_messages(conversation_id, created_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_cmsg_task ON conversation_messages(task_id)")
        logger.info("Conversation tables verified")
    except Exception as e:
        logger.warning(f"Conversations auto-migrate: {e}")

    # Cargar TODOS los asistentes desde BD
    try:
        from src.engine.registry import chain_registry
        from src.engine.models import ChainDefinition, ChainConfig, NodeDefinition, NodeType
        from src.db.repositories.chains import ChainRepository

        db_chains = await ChainRepository.get_all()
        loaded = 0
        for dbc in db_chains:
            if not dbc.slug:
                continue
            try:
                cfg = dbc.config or {}
                prompts = dbc.prompts or {}
                raw_prompt = prompts.get("system", "")
                system_prompt = raw_prompt if isinstance(raw_prompt, str) else str(raw_prompt)

                config_dict = {k: v for k, v in cfg.items() if k in ChainConfig.model_fields}
                config_dict["system_prompt"] = system_prompt

                definition = ChainDefinition(
                    id=dbc.slug,
                    name=dbc.name or dbc.slug,
                    description=dbc.description or "",
                    type=dbc.type or "agent",
                    version=dbc.version or "1.0.0",
                    nodes=[NodeDefinition(id="adaptive_agent", type=NodeType.LLM, name="Adaptive Agent", temperature=cfg.get("temperature", 0.5))],
                    config=ChainConfig(**config_dict)
                )

                builder = get_builder(dbc.handler_type or dbc.slug)
                chain_registry.register(chain_id=dbc.slug, definition=definition, builder=builder)
                loaded += 1
            except Exception as e:
                logger.warning(f"Error cargando asistente '{dbc.slug}': {e}")

        logger.info(f"Asistentes cargados desde BD: {loaded}")
    except Exception as e:
        logger.warning(f"No se pudieron cargar asistentes desde BD: {e}")

    # Registrar subagentes especializados (ANTES de core tools para que el enum de delegate sea dinámico)
    try:
        from src.engine.chains.agents import register_all_subagents
        await register_all_subagents()
        logger.info("Subagentes especializados registrados")
    except Exception as e:
        logger.warning(f"No se pudieron registrar subagentes: {e}")

    # Skills sync from Git repository (after subagents so DB agents exist)
    try:
        await skill_sync_service.start_background_sync()
    except Exception as e:
        logger.warning(f"Skills sync startup: {e}")

    # Cargar herramientas built-in (core tools) - después de subagentes para que delegate tenga el enum correcto
    tool_registry.register_builtin_tools()
    logger.info("Herramientas built-in registradas")
    
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

        # Registrar herramientas MCP en el tool_registry para que los agentes las usen
        mcp_tools_count = await tool_registry.load_mcp_tools()
        if mcp_tools_count:
            logger.info(f"Herramientas MCP registradas en tool_registry: {mcp_tools_count}")
    except Exception as e:
        logger.warning(f"No se pudieron cargar conexiones MCP: {e}")

    # Precargar precios de modelos LLM desde models.dev (background, no bloquea startup)
    try:
        from src.monitoring.pricing import pricing_service
        asyncio.create_task(pricing_service.ensure_loaded())
        logger.info("LLM pricing preload scheduled (models.dev)")
    except Exception as e:
        logger.warning(f"Could not schedule pricing preload: {e}")

    # Sandbox cleanup background task
    async def _sandbox_cleanup_loop():
        import asyncio as _aio
        from src.code_executor.sandbox_manager import sandbox_manager
        while True:
            await _aio.sleep(300)  # every 5 min
            try:
                stopped = await sandbox_manager.stop_idle(max_idle_minutes=30)
                if stopped:
                    logger.info(f"Sandbox cleanup: stopped {stopped} idle container(s)")
            except Exception as exc:
                logger.warning(f"Sandbox cleanup error: {exc}")

    _cleanup_task = asyncio.create_task(_sandbox_cleanup_loop())
    logger.info("Sandbox cleanup task started (every 5 min, idle > 30 min)")

    # Initialize LangGraph checkpointer for durable execution
    try:
        from src.engine.checkpoint import init_checkpointer
        await init_checkpointer()
    except Exception as e:
        logger.warning(f"Checkpointer init skipped: {e}")

    yield

    _cleanup_task.cancel()
    skill_sync_service.stop()
    
    # Shutdown
    logger.info("Cerrando Brain API")

    # Shutdown checkpointer
    try:
        from src.engine.checkpoint import shutdown_checkpointer
        await shutdown_checkpointer()
    except Exception:
        pass

    # Desconectar servidores MCP
    await mcp_client.disconnect_all()
    logger.info("Conexiones MCP cerradas")
    
    # Cerrar servicio de navegador
    await browser_service.shutdown()
    logger.info("Servicio de navegador cerrado")
    
    # Cerrar conexiones SQLite per-user
    from src.db.user_db import user_db
    await user_db.close_all()
    logger.info("Conexiones SQLite de usuario cerradas")

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

# A2A protocol version middleware (validates A2A-Version header)
app.add_middleware(A2AVersionMiddleware)

# A2A error handler (RFC 9457 Problem Details)
app.add_exception_handler(A2AProblemDetail, a2a_problem_handler)

# Incluir routers
app.include_router(llm_router, prefix="/api/v1")
app.include_router(chains_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(tools_router, prefix="/api/v1")
app.include_router(mcp_router, prefix="/api/v1")
app.include_router(browser_router, prefix="/api/v1")
app.include_router(subagents_router, prefix="/api/v1")
app.include_router(agent_definitions_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(task_router, prefix="/api/v1")
app.include_router(monitoring_router, prefix="/api/v1")
app.include_router(workspace_router, prefix="/api/v1")
app.include_router(artifacts_router, prefix="/api/v1")
app.include_router(engine_task_router, prefix="/api/v1")
app.include_router(conversation_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")

# Auth Router (sin prefix para compatibilidad con Strapi)
app.include_router(auth_router)

# OpenAI-Compatible API (sin prefix /api para compatibilidad)
app.include_router(openai_compat_router)

# A2A Protocol — HTTP+JSON/REST binding (Section 11)
app.include_router(a2a_router, prefix="/a2a")

# Skills Sync from Git repository
app.include_router(skills_router, prefix="/api/v1")


# ===========================================
# A2A Agent Card (well-known URI, RFC 8615)
# ===========================================

@app.get("/.well-known/agent-card.json", tags=["A2A Protocol"])
async def well_known_agent_card(request: Request):
    """Public Agent Card for A2A discovery."""
    import json as _json
    base_url = str(request.base_url).rstrip("/")
    card = await build_agent_card(base_url=base_url)
    data = _json.loads(card.model_dump_json(by_alias=True, exclude_none=True))
    return data


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
