# Arquitectura de Brain

## Visión General

Brain es un sistema de gestión de cadenas de pensamiento (thought chains) que utiliza LangChain y LangGraph para orquestar flujos de trabajo con IA.

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
│  │  Angular GUI │    │  Python API  │    │  Strapi CMS  │                 │
│  │    :4200     │◄──►│    :8000     │◄──►│    :1337     │                 │
│  │              │    │              │    │              │                 │
│  │  - Dashboard │    │  - FastAPI   │    │  - Content   │                 │
│  │  - Grafos    │    │  - LangGraph │    │  - Config    │                 │
│  │  - Traces    │    │  - RAG       │    │  - Users     │                 │
│  └──────────────┘    └──────┬───────┘    └──────┬───────┘                 │
│                             │                    │                         │
│                             ▼                    ▼                         │
│                      ┌─────────────────────────────────┐                  │
│                      │     PostgreSQL + pgvector       │                  │
│                      │            :5432                │                  │
│                      │                                 │                  │
│                      │  - brain_documents (RAG)        │                  │
│                      │  - brain_graphs                 │                  │
│                      │  - brain_executions             │                  │
│                      │  - brain_execution_traces       │                  │
│                      │  - strapi_* (CMS tables)        │                  │
│                      └─────────────────────────────────┘                  │
│                                                                            │
│  ┌──────────────┐                                                         │
│  │    Redis     │◄── Cache / Task Queue                                   │
│  │    :6379     │                                                         │
│  └──────────────┘                                                         │
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

#### Estructura del código

```
services/api/src/
├── main.py              # FastAPI app, routes
├── config.py            # Settings (pydantic-settings)
├── chains/              # LangChain chains
│   ├── __init__.py
│   ├── base.py          # Base chain class
│   └── examples/        # Example chains
├── graphs/              # LangGraph workflows
│   ├── __init__.py
│   ├── base.py          # Base graph class
│   └── examples/        # Example graphs
├── rag/                 # RAG components
│   ├── __init__.py
│   ├── vectorstore.py   # pgvector integration
│   ├── embeddings.py    # Embedding models
│   └── retriever.py     # Custom retrievers
└── models/              # Pydantic models
    └── __init__.py
```

### 2. PostgreSQL + pgvector

Base de datos única para todo el sistema:

#### Tablas principales

| Tabla | Descripción |
|-------|-------------|
| `brain_documents` | Documentos RAG con embeddings vectoriales |
| `brain_graphs` | Definiciones de grafos LangGraph |
| `brain_executions` | Registro de ejecuciones |
| `brain_execution_traces` | Trace paso a paso de cada ejecución |
| `brain_chains` | Configuraciones de LangChain chains |

#### Vector Search

```sql
-- Búsqueda de similitud coseno
SELECT id, content, 1 - (embedding <=> query_embedding) as similarity
FROM brain_documents
WHERE collection = 'my_collection'
ORDER BY embedding <=> query_embedding
LIMIT 5;
```

### 3. Strapi CMS

Gestión de contenido y configuraciones:

- Usuarios y permisos
- Configuraciones de grafos/chains
- Plantillas de prompts
- Logs y auditoría

### 4. Angular GUI

Interfaz de usuario con:

- **Dashboard**: Vista general del sistema
- **Editor de Grafos**: Visualización y edición de workflows
- **Monitor de Ejecuciones**: Seguimiento en tiempo real
- **Explorador RAG**: Gestión de documentos y búsquedas

### 5. Redis

Funciones auxiliares:

- Cache de resultados
- Cola de tareas asíncronas (Celery)
- Pub/Sub para WebSockets

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
1. Documento nuevo llega (via API o Strapi)
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
- Celery workers para tareas pesadas

## Seguridad

- JWT para autenticación (Strapi)
- CORS configurado por servicio
- Variables sensibles en .env
- Network isolation en Docker
