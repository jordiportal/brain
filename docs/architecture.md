# Arquitectura de Brain

## Visión General

Brain es un sistema de gestión de cadenas de pensamiento (thought chains) que utiliza LangChain y LangGraph para orquestar flujos de trabajo con IA. La API accede directamente a PostgreSQL para máxima eficiencia.

## Diagrama de Arquitectura

```
                                    ┌─────────────────┐
                                    │   Usuario/GUI   │
                                    └────────┬────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                              Docker Network                                 │
│                                                                            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│  │  Angular GUI │    │  Python API  │    │   Browser    │                 │
│  │    :4200     │◄──►│    :8000     │◄──►│   Service    │                 │
│  │              │    │              │    │    :6080     │                 │
│  │  - Dashboard │    │  - FastAPI   │    │              │                 │
│  │  - Grafos    │    │  - LangGraph │    │  - Chrome    │                 │
│  │  - Traces    │    │  - RAG       │    │  - noVNC     │                 │
│  └──────────────┘    └──────┬───────┘    └──────────────┘                 │
│                             │                                              │
│                             ▼                                              │
│                      ┌─────────────────────────────────┐                  │
│                      │     PostgreSQL + pgvector       │                  │
│                      │            :5432                │                  │
│                      │                                 │                  │
│                      │  - brain_documents (RAG)        │                  │
│                      │  - brain_chains                 │                  │
│                      │  - llm_providers                │                  │
│                      │  - mcp_connections              │                  │
│                      │  - brain_executions             │                  │
│                      └─────────────────────────────────┘                  │
│                                                                            │
│  ┌──────────────┐    ┌──────────────┐                                     │
│  │    Redis     │    │  Persistent  │                                     │
│  │    :6379     │    │   Runner     │                                     │
│  │              │    │              │                                     │
│  │  - Cache     │    │  - Python    │                                     │
│  │  - Tasks     │    │  - Workspace │                                     │
│  └──────────────┘    └──────────────┘                                     │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
         │
         │ host.docker.internal
         ▼
┌──────────────────┐
│  Ollama Server   │  (Externo)
│     :11434       │
│                  │
│  - llama3.2      │
│  - nomic-embed   │
└──────────────────┘
```

## Componentes

### 1. API Python (FastAPI + LangGraph)

Servidor principal que gestiona:

- **Grafos (LangGraph)**: Definición y ejecución de workflows
- **Cadenas (LangChain)**: Chains reutilizables
- **RAG**: Retrieval Augmented Generation con pgvector
- **Ejecuciones**: Historial y trazabilidad
- **Acceso directo a PostgreSQL**: Sin intermediarios

#### Estructura del código

```
services/api/src/
├── main.py              # FastAPI app, routes
├── config.py            # Settings (pydantic-settings)
├── db/                  # Acceso directo a PostgreSQL
│   ├── connection.py    # Pool de conexiones
│   ├── models.py        # Modelos de datos
│   └── repositories/    # Repositorios por entidad
├── engine/              # Motor de agentes
│   ├── chains/          # Cadenas y agentes
│   └── reasoning/       # Lógica de razonamiento
├── tools/               # Herramientas del agente
│   └── core/            # Tools nativas
├── rag/                 # RAG components
│   ├── vectorstore.py   # pgvector integration
│   ├── embeddings.py    # Embedding models
│   └── searcher.py      # Búsqueda semántica
└── mcp/                 # Model Context Protocol
    └── client.py        # Cliente MCP
```

### 2. PostgreSQL + pgvector

Base de datos única para todo el sistema:

#### Tablas principales

| Tabla | Descripción |
|-------|-------------|
| `brain_documents` | Documentos RAG con embeddings vectoriales |
| `brain_chains` | Configuraciones de cadenas |
| `llm_providers` | Proveedores LLM configurados |
| `mcp_connections` | Conexiones MCP |
| `brain_executions` | Registro de ejecuciones |
| `brain_execution_traces` | Trace paso a paso de cada ejecución |

#### Vector Search

```sql
-- Búsqueda de similitud coseno
SELECT id, content, 1 - (embedding <=> query_embedding) as similarity
FROM brain_documents
WHERE collection = 'my_collection'
ORDER BY embedding <=> query_embedding
LIMIT 5;
```

### 3. Angular GUI

Interfaz de usuario con:

- **Dashboard**: Vista general del sistema
- **Editor de Grafos**: Visualización y edición de workflows
- **Monitor de Ejecuciones**: Seguimiento en tiempo real
- **Explorador RAG**: Gestión de documentos y búsquedas
- **Testing LLM**: Chat interactivo con streaming

### 4. Browser Service

Navegador Chrome accesible via noVNC:

- Automatización web con Playwright
- Visualización en tiempo real
- Capturas de pantalla

### 5. Redis

Funciones auxiliares:

- Cache de resultados
- Pub/Sub para WebSockets (cuando se use)
- **Futuro:** colas de jobs para tareas asíncronas y/o agente Swarm (RQ, ARQ o Celery)

### 6. Persistent Runner

Contenedor para ejecución de código:

- Python con librerías científicas
- Workspace compartido con el host
- Acceso a la red interna

## Flujo de Datos

### Ejecución de un Grafo

```
1. Usuario solicita ejecución via GUI/API
          │
          ▼
2. API valida y crea registro en brain_executions
          │
          ▼
3. LangGraph ejecuta el grafo nodo por nodo
          │
          ├── Por cada nodo:
          │   ├── Guardar input en brain_execution_traces
          │   ├── Si necesita RAG → pgvector search
          │   ├── Si necesita LLM → Ollama call
          │   └── Guardar output en brain_execution_traces
          │
          ▼
4. Actualizar brain_executions con resultado final
          │
          ▼
5. Notificar a GUI via WebSocket (opcional)
```

### RAG Pipeline

```
1. Documento nuevo llega via API
          │
          ▼
2. Generar embedding con Ollama (nomic-embed-text)
          │
          ▼
3. Guardar en brain_documents con vector
          │
          ▼
[Búsqueda posterior]
          │
          ▼
4. Query llega → Generar embedding
          │
          ▼
5. pgvector similarity search
          │
          ▼
6. Devolver documentos más relevantes
```

## Escalabilidad

### Horizontal

- API: Múltiples instancias detrás de load balancer
- Redis: Cluster mode
- PostgreSQL: Read replicas

### Vertical

- pgvector: Índices HNSW para millones de vectores
- Workers para tareas pesadas

## Futuro: agente Swarm

Se prevé añadir un agente de tipo Swarm (orquestación multi-agente con DAG y colas) como **una cadena más** en el registry. Redis está previsto para soportar colas de jobs (RQ, ARQ o Celery); la API y el modelo de ejecuciones actuales permiten integrar dicho agente sin cambios estructurales.

## Seguridad

- JWT para autenticación
- CORS configurado por servicio
- Variables sensibles en .env
- Network isolation en Docker
