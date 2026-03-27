# Propuesta Arquitectónica: Brain Core + Brain Hub + Paperclip Fork

## 1. Visión General

La propuesta consiste en una **reestructuración de Brain en dos capas** combinada con un **fork de Paperclip** que actúe como capa de orquestación empresarial, creando un ecosistema de tres componentes:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    BRAIN HUB (Fork de Paperclip)                │    │
│  │         Orquestación Empresarial · Dashboard · Gobernanza       │    │
│  │                                                                  │    │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │    │
│  │  │ Org      │ │ Presup.  │ │ Govern. │ │ Skills  │ │ Plugin │ │    │
│  │  │ Charts   │ │ & Costes │ │ Board   │ │ Library │ │ System │ │    │
│  │  └──────────┘ └──────────┘ └─────────┘ └─────────┘ └────────┘ │    │
│  │                                                                  │    │
│  │  Adaptadores:                                                    │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐ │    │
│  │  │ Claude   │ │ Codex    │ │ Cursor   │ │  🆕 Brain Adapter  │ │    │
│  │  │ Code     │ │          │ │          │ │  (brain-gateway)   │ │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └─────────┬──────────┘ │    │
│  └──────────────────────────────────────────────────────┼───────────┘    │
│                                                          │               │
│                              REST API / A2A / OpenAI-compat              │
│                                                          │               │
│  ┌──────────────────────────────────────────────────────┼───────────┐   │
│  │                       BRAIN CORE                      │           │   │
│  │              Motor de Ejecución de Agentes IA         ▼           │   │
│  │                                                                   │   │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐│   │
│  │  │ LangGraph│ │ RAG      │ │ MCP     │ │ Tools   │ │ Code     ││   │
│  │  │ Engine   │ │ pgvector │ │ Client  │ │ Registry│ │ Sandbox  ││   │
│  │  └──────────┘ └──────────┘ └─────────┘ └─────────┘ └──────────┘│   │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐│   │
│  │  │ Browser  │ │ Memory   │ │ Check-  │ │ LLM     │ │ A2A      ││   │
│  │  │ Auto.    │ │ Manager  │ │ points  │ │ Provid. │ │ Protocol ││   │
│  │  └──────────┘ └──────────┘ └─────────┘ └─────────┘ └──────────┘│   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    SERVICIOS COMPARTIDOS                          │   │
│  │         PostgreSQL + pgvector  ·  Redis  ·  Browser Service      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Los Tres Componentes

### 2.1 Brain Core — Motor de Ejecución

**Propósito**: Ejecutar agentes IA con capacidades profundas. Es el "trabajador inteligente".

**Responsabilidades**:
- Ejecución de cadenas LangGraph con checkpointing
- Gestión de proveedores LLM (Ollama, OpenAI, Gemini, Anthropic, Azure, Groq)
- RAG con pgvector (ingesta, búsqueda, colecciones)
- Integración MCP (Model Context Protocol)
- Registro y ejecución de herramientas (built-in + OpenAPI + MCP)
- Ejecución de código en sandboxes Docker
- Automatización de navegador (Chrome + VNC + CDP)
- Memoria (largo plazo + episódica)
- API compatible OpenAI (`/v1/chat/completions`, `/v1/models`)
- Protocolo A2A (agent-to-agent)
- Streaming SSE

**API expuesta** (Brain Core como servicio independiente):

```
POST   /v1/chat/completions          # OpenAI-compatible
GET    /v1/models                     # Listar modelos disponibles
POST   /api/v1/chains/{id}/invoke     # Ejecutar cadena
POST   /api/v1/chains/{id}/stream     # Ejecutar con streaming
POST   /api/v1/rag/search             # Búsqueda vectorial
POST   /api/v1/rag/ingest             # Ingesta de documentos
POST   /api/v1/tools/execute          # Ejecutar herramienta
POST   /api/v1/mcp/tools/call         # Llamar herramienta MCP
POST   /api/v1/browser/*              # Automatización de navegador
POST   /api/v1/engine/tasks           # Crear/gestionar tareas
GET    /api/v1/memory/*               # Contexto y memoria
POST   /a2a/message:send              # A2A protocol
POST   /a2a/message:stream            # A2A streaming
GET    /health                        # Liveness
GET    /health/ready                  # Readiness
GET    /.well-known/agent-card.json   # A2A discovery
```

**Módulos del código actual que van a Brain Core**:

| Módulo actual | Path | Notas |
|---------------|------|-------|
| `engine/` | `src/engine/` | Completo: executor, agent_runner, task_manager, checkpoint, memory, chains, handoff |
| `llm/` | `src/llm/` | Router de LLM |
| `rag/` | `src/rag/` | RAG completo |
| `tools/` | `src/tools/` | Registry + herramientas |
| `mcp/` | `src/mcp/` | Cliente MCP completo |
| `browser/` | `src/browser/` | Automatización de navegador |
| `code_executor/` | `src/code_executor/` | Sandboxes + workspace (solo ejecución) |
| `providers/` | `src/providers/` | Gestión de proveedores LLM |
| `openai_compat/` | `src/openai_compat/` | API compatible OpenAI |
| `a2a/` | `src/a2a/` | Protocolo A2A |
| `auth/` | `src/auth/` | Autenticación (compartido) |

**Tablas de base de datos Core**:

```sql
-- Motor de ejecución
tasks, task_events, agent_states

-- LangGraph
checkpoint_*, checkpoint_writes_*

-- Cadenas y agentes
brain_chains, brain_chain_links, chain_versions
agent_definitions, agent_versions, subagent_configs

-- LLM
brain_llm_providers, brain_model_configs

-- RAG
rag_documents, rag_chunks

-- Herramientas
openapi_connections, mcp_connections, tool_configs
components_tool_settings_executions

-- Memoria
memory_long_term, memory_episodes

-- Código
code_executions, code_executions_brain_chain_lnk
```

---

### 2.2 Brain Hub — Fork de Paperclip Extendido

**Propósito**: Orquestación empresarial, dashboard, gobernanza, monitorización. Es el "director de la empresa".

**Base**: Fork de [paperclipai/paperclip](https://github.com/paperclipai/paperclip) con extensiones propias.

**Qué hereda de Paperclip (sin modificar)**:
- Organigramas y jerarquías de agentes
- Sistema de presupuestos por agente
- Gobernanza board-operator
- Heartbeats y scheduling
- Sistema de tickets/issues
- Multi-empresa con aislamiento
- Framework de plugins + SDK
- CLI (`npx paperclipai`)
- React UI base
- Import/export de empresas
- Rutinas y tareas recurrentes

**Extensiones propias de Brain Hub (sobre el fork)**:

| Extensión | Descripción | Origen |
|-----------|-------------|--------|
| **Brain Adapter** | Adaptador `brain-gateway` en `packages/adapters/` | Nuevo |
| **Dashboard de monitorización** | Métricas, trazas, alertas (migrar desde Brain actual) | Brain `monitoring/` |
| **Gestión de configuración LLM** | UI para proveedores, modelos, API keys | Brain `config_router` |
| **Visor de RAG** | UI para colecciones, documentos, búsqueda | Brain `features/rag/` |
| **Panel de herramientas** | Config de OpenAPI, MCP, herramientas built-in | Brain `features/tools/` |
| **Visor de artefactos** | Sidebar + viewer de artefactos generados | Brain `artifacts/` |
| **Gestión de usuarios** | Auth, roles, perfiles, briefings | Brain `users/`, `profile/` |
| **Brain Settings** | Configuración global de Brain | Brain `brain_settings` |
| **Visor de navegador** | Embed del VNC viewer | Brain `features/sandboxes/` |

**Tablas de base de datos Hub** (adicionales al schema de Paperclip):

```sql
-- Monitorización (migradas de Brain)
api_metrics, execution_traces, monitoring_alerts
hourly_metrics (vista), chain_stats (vista)

-- Usuarios y perfiles (extendidas)
brain_users, brain_role_permissions
user_profiles, user_tasks, user_task_results

-- Configuración
brain_settings, brain_api_keys

-- Artefactos
artifacts, artifact_tags

-- Conversaciones (metadatos de UI)
conversations, conversation_messages

-- Sandboxes (gestión)
user_sandboxes
```

---

### 2.3 Brain Adapter — El Puente

El componente más crítico de la integración. Un paquete que implementa `ServerAdapterModule` de Paperclip para conectar Brain Hub con Brain Core.

**Path en el fork**: `packages/adapters/brain-gateway/`

**Estructura del paquete**:

```
packages/adapters/brain-gateway/
├── package.json
├── src/
│   ├── index.ts              # Metadata: type, label, models, docs
│   ├── server/
│   │   ├── index.ts          # Re-exports: execute, testEnvironment, etc.
│   │   ├── execute.ts        # Implementación de execute()
│   │   ├── environment.ts    # testEnvironment()
│   │   ├── session.ts        # sessionCodec (mapear sessions a Brain tasks)
│   │   ├── skills.ts         # listSkills / syncSkills vía Brain API
│   │   └── models.ts         # listModels vía Brain /v1/models
│   ├── ui/
│   │   └── index.ts          # Parsing de output para UI
│   └── cli/
│       └── index.ts          # Helpers CLI
├── tsconfig.json
└── vitest.config.ts
```

**Implementación del contrato `ServerAdapterModule`**:

```typescript
// packages/adapters/brain-gateway/src/index.ts
import type { ServerAdapterModule } from '@paperclipai/adapter-utils';

export const type = 'brain_gateway';
export const label = 'Brain (Gateway)';
export const agentConfigurationDoc = `
## Brain Gateway Adapter

Connects to a Brain Core instance to execute AI chains with
LangGraph, RAG, MCP, code sandboxes, and browser automation.

### Configuration
- \`brainUrl\`: URL of the Brain Core API (e.g. http://brain-core:8000)
- \`apiKey\`: Brain API key for authentication
- \`defaultChainId\`: Default chain to execute
- \`enableRag\`: Enable RAG context injection
- \`enableBrowser\`: Enable browser automation capabilities
- \`enableCodeExecution\`: Enable code sandbox
`;

export const models = [
  { id: 'brain-adaptive', name: 'Brain Adaptive Agent' },
  { id: 'brain-team', name: 'Brain Team Coordinator' },
];
```

```typescript
// packages/adapters/brain-gateway/src/server/execute.ts
import type {
  AdapterExecutionContext,
  AdapterExecutionResult,
} from '@paperclipai/adapter-utils';

interface BrainAdapterConfig {
  brainUrl: string;
  apiKey: string;
  defaultChainId?: string;
  enableRag?: boolean;
  enableBrowser?: boolean;
  enableCodeExecution?: boolean;
}

export async function execute(
  ctx: AdapterExecutionContext
): Promise<AdapterExecutionResult> {
  const config = ctx.config as BrainAdapterConfig;
  const { brainUrl, apiKey } = config;

  // 1. Construir el prompt a partir del contexto de Paperclip
  const prompt = buildPromptFromContext(ctx);

  // 2. Invocar Brain Core vía su API
  //    Opción A: OpenAI-compat (simple)
  //    Opción B: Chain invoke (completo)
  //    Opción C: A2A protocol (estandarizado)
  const response = await invokeBrainCore({
    url: `${brainUrl}/api/v1/chains/${config.defaultChainId}/invoke`,
    apiKey,
    body: {
      message: prompt,
      context: {
        issueId: ctx.context?.issueId,
        agentRole: ctx.agent?.role,
        companyGoals: ctx.context?.goals,
        ragEnabled: config.enableRag,
        browserEnabled: config.enableBrowser,
        codeExecutionEnabled: config.enableCodeExecution,
      },
    },
    onLog: ctx.onLog,
  });

  // 3. Mapear respuesta a AdapterExecutionResult
  return {
    exitCode: response.success ? 0 : 1,
    usage: {
      inputTokens: response.usage?.prompt_tokens ?? 0,
      outputTokens: response.usage?.completion_tokens ?? 0,
      totalCost: response.usage?.cost ?? 0,
    },
    sessionParams: response.taskId
      ? JSON.stringify({ taskId: response.taskId })
      : undefined,
    error: response.error,
  };
}

function buildPromptFromContext(ctx: AdapterExecutionContext): string {
  const parts: string[] = [];

  if (ctx.context?.goals) {
    parts.push(`## Company Goals\n${ctx.context.goals}`);
  }
  if (ctx.context?.issueDescription) {
    parts.push(`## Current Task\n${ctx.context.issueDescription}`);
  }
  if (ctx.context?.conversationHistory) {
    parts.push(`## Conversation\n${ctx.context.conversationHistory}`);
  }

  return parts.join('\n\n');
}

async function invokeBrainCore(opts: {
  url: string;
  apiKey: string;
  body: Record<string, unknown>;
  onLog?: (log: string) => void;
}) {
  const response = await fetch(opts.url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${opts.apiKey}`,
    },
    body: JSON.stringify(opts.body),
  });

  if (!response.ok) {
    const error = await response.text();
    return { success: false, error };
  }

  return { success: true, ...(await response.json()) };
}
```

```typescript
// packages/adapters/brain-gateway/src/server/environment.ts
import type { AdapterEnvironmentTestContext } from '@paperclipai/adapter-utils';

export async function testEnvironment(ctx: AdapterEnvironmentTestContext) {
  const config = ctx.config as { brainUrl: string; apiKey: string };
  const checks = [];

  // Verificar conectividad con Brain Core
  try {
    const res = await fetch(`${config.brainUrl}/health/ready`);
    const data = await res.json();
    checks.push({
      name: 'Brain Core connectivity',
      status: data.status === 'ready' ? 'pass' : 'warn',
      message: data.status === 'ready'
        ? 'Brain Core is running and ready'
        : `Brain Core status: ${data.status}`,
    });
  } catch (e) {
    checks.push({
      name: 'Brain Core connectivity',
      status: 'fail',
      message: `Cannot reach Brain Core at ${config.brainUrl}: ${e}`,
    });
  }

  // Verificar modelos disponibles
  try {
    const res = await fetch(`${config.brainUrl}/v1/models`, {
      headers: { Authorization: `Bearer ${config.apiKey}` },
    });
    const data = await res.json();
    checks.push({
      name: 'LLM Models',
      status: data.data?.length > 0 ? 'pass' : 'warn',
      message: `${data.data?.length ?? 0} models available`,
    });
  } catch {
    checks.push({
      name: 'LLM Models',
      status: 'warn',
      message: 'Could not verify available models',
    });
  }

  return { checks };
}
```

---

## 3. Protocolos de Comunicación

### 3.1 Brain Hub → Brain Core

Tres protocolos disponibles, en orden de preferencia:

```
┌───────────────────┐                    ┌──────────────────┐
│                   │   OpenAI-compat    │                  │
│                   │ ◄─ /v1/chat/... ─► │                  │
│                   │                    │                  │
│    Brain Hub      │   Chain Invoke     │   Brain Core     │
│   (Paperclip      │ ◄─ /api/v1/... ─► │   (FastAPI)      │
│    Fork)          │                    │                  │
│                   │   A2A Protocol     │                  │
│                   │ ◄─ /a2a/... ──── ► │                  │
│                   │                    │                  │
└───────────────────┘                    └──────────────────┘
```

| Protocolo | Cuándo usar | Ventajas | Limitaciones |
|-----------|-------------|----------|--------------|
| **OpenAI-compat** | Ejecución simple de chat | Estándar, fácil de integrar, streaming SSE | Sin acceso a herramientas, RAG implícito |
| **Chain Invoke** | Ejecución completa de cadenas | Control total: RAG, herramientas, memoria, subagentes | API propietaria de Brain |
| **A2A Protocol** | Comunicación estandarizada agent-to-agent | Protocolo abierto, soporte de tareas largas, push notifications | Más complejo de implementar |

**Recomendación**: Usar **Chain Invoke** como protocolo primario para el adapter (máximo control), **A2A** para comunicación inter-agente, y **OpenAI-compat** como fallback para integraciones simples.

### 3.2 Brain Core → Brain Hub (Callbacks)

Brain Core reporta eventos a Brain Hub para alimentar el dashboard:

```
Brain Core ──── Execution Events ───────► Brain Hub
             (webhook / polling / SSE)
             
Eventos:
  - task.started    { taskId, chainId, agentId, timestamp }
  - task.completed  { taskId, result, usage, duration }
  - task.failed     { taskId, error, retryable }
  - task.progress   { taskId, step, message }
  - metrics.update  { tokens, cost, latency }
```

**Implementación**: Brain Core puede exponer un endpoint SSE `/api/v1/events/stream` que Brain Hub consuma, o alternativamente publicar en Redis pub/sub si ambos comparten la instancia Redis.

---

## 4. Plan de Migración por Fases

### Fase 0 — Preparación (Base)

**Objetivo**: Establecer la infraestructura mínima sin romper funcionalidad existente.

**Tareas**:

1. **Fork de Paperclip** → Crear `brain-hub` como fork de `paperclipai/paperclip`
2. **Crear adapter skeleton** → `packages/adapters/brain-gateway/` con implementación mínima
3. **Registrar adapter** → Añadir a `server/src/adapters/registry.ts`
4. **CI/CD básico** → GitHub Actions para build y test del adapter
5. **Docker Compose** → Fichero de desarrollo que levante Brain Hub + Brain Core juntos

**Resultado**: Brain Hub arranca, puede "contratar" un agente Brain, y enviarle tareas básicas al Brain Core actual sin modificar.

```yaml
# docker-compose.dev.yml (nueva orquestación)
services:
  brain-core:
    build: ./brain-core
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://brain:brain@postgres:5432/brain_core
    depends_on:
      - postgres
      - redis

  brain-hub:
    build: ./brain-hub
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://brain:brain@postgres:5432/brain_hub
      BRAIN_CORE_URL: http://brain-core:8000
    depends_on:
      - postgres
      - brain-core

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: brain
      POSTGRES_PASSWORD: brain
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  browser-service:
    build: ./brain-core/services/browser-service
    ports:
      - "6080:6080"

volumes:
  pgdata:
```

### Fase 1 — Separación de Brain Core

**Objetivo**: Extraer Brain Core como servicio autónomo y limpio.

**Tareas**:

1. **Crear `main_core.py`** — Nuevo entry point solo con routers Core:
   ```python
   # services/api/src/main_core.py
   from fastapi import FastAPI
   
   app = FastAPI(title="Brain Core", version="2.0.0")
   
   # Solo routers Core
   app.include_router(llm_router, prefix="/api/v1/llm")
   app.include_router(chain_router, prefix="/api/v1/chains")
   app.include_router(rag_router, prefix="/api/v1/rag")
   app.include_router(tools_router, prefix="/api/v1/tools")
   app.include_router(mcp_router, prefix="/api/v1/mcp")
   app.include_router(browser_router, prefix="/api/v1/browser")
   app.include_router(engine_task_router, prefix="/api/v1/engine/tasks")
   app.include_router(memory_router, prefix="/api/v1/memory")
   app.include_router(workspace_router, prefix="/api/v1/workspace")
   app.include_router(openai_compat_router)
   app.include_router(a2a_router, prefix="/a2a")
   ```

2. **Desacoplar `context_injector`** — Que reciba briefing como parámetro del adapter en vez de leer tablas Hub directamente.

3. **Extraer `MonitoringMiddleware`** a un sistema de eventos:
   ```python
   # En vez de escribir directamente a api_metrics:
   class CoreEventEmitter:
       async def emit(self, event_type: str, data: dict):
           # Opción 1: Redis pub/sub
           await redis.publish("brain:events", json.dumps({...}))
           # Opción 2: Webhook callback a Brain Hub
           await httpx.post(f"{hub_url}/api/webhooks/core-events", json={...})
   ```

4. **Separar esquema DB** — Brain Core usa solo sus tablas, con migraciones Alembic propias.

5. **Nuevo `Dockerfile.core`** — Imagen optimizada sin dependencias Hub.

6. **Tests** — Asegurar que Brain Core arranca y responde sin Brain Hub.

### Fase 2 — Brain Hub (Fork de Paperclip)

**Objetivo**: Fork funcional de Paperclip con el Brain Adapter y extensiones de UI.

**Tareas**:

1. **Completar Brain Adapter** — Implementación completa de `execute`, `testEnvironment`, `sessionCodec`, `listModels`

2. **Plugin Brain Dashboard** — Plugin de Paperclip para las funcionalidades de monitorización:
   ```typescript
   // packages/plugins/brain-dashboard/src/worker.ts
   import { definePlugin } from '@paperclipai/plugin-sdk';
   
   export default definePlugin({
     async setup(ctx) {
       // Consumir eventos de Brain Core
       ctx.events.on('heartbeat.run.completed', async (event) => {
         // Almacenar métricas de ejecución
         await ctx.data.insert('brain_metrics', {
           runId: event.runId,
           tokens: event.usage.totalTokens,
           cost: event.usage.totalCost,
           duration: event.duration,
         });
       });
   
       // Job recurrente: sincronizar métricas
       ctx.jobs.register('sync-brain-metrics', async () => {
         const metrics = await fetchBrainCoreMetrics();
         await ctx.data.upsert('brain_dashboard', metrics);
       });
     },
   });
   ```

3. **UI Slots personalizados** — Aprovechar el sistema de slots de Paperclip:
   - Slot en dashboard: Widget de métricas Brain
   - Slot en agent detail: Estado de herramientas (RAG, MCP, Browser)
   - Slot en sidebar: Acceso rápido a RAG search
   - Nuevo launcher: "Brain Chat" para interacción directa

4. **Migrar features de Angular a React** (progresivo):
   - Monitorización → React component en Brain Hub
   - RAG viewer → React component
   - Tool config → React component
   - Settings → Integrar en config de Paperclip

5. **Personalización del fork**:
   - Branding: "Brain Hub" en vez de "Paperclip"
   - Tema visual personalizado
   - Idioma: soporte español nativo
   - Documentación adaptada

### Fase 3 — Integración Profunda

**Objetivo**: Sinergias avanzadas entre Brain Core y Brain Hub.

**Tareas**:

1. **RAG como servicio compartido** — Brain Hub puede pedir a Brain Core que busque en RAG para enriquecer contexto de cualquier agente:
   ```
   Paperclip Heartbeat → Brain Adapter → enrich context via RAG → send to agent
   ```

2. **MCP compartido** — Brain Core expone sus conexiones MCP como herramientas disponibles para todos los agentes vía el adapter.

3. **Browser automation como skill** — Registrar las capacidades de navegador de Brain Core como skills en la biblioteca de Paperclip.

4. **Code execution compartido** — Los sandboxes de Brain Core disponibles para cualquier agente orquestado por Brain Hub.

5. **Memoria unificada** — La memoria a largo plazo de Brain Core alimentada por la historia de ejecuciones de todos los agentes de Brain Hub.

6. **Gobernanza para cadenas** — Workflow de aprobación de Paperclip aplicado a ejecuciones de cadenas costosas o sensibles.

---

## 5. Estructura de Repositorios

### Opción A: Monorepo Único (Recomendada para el inicio)

```
brain/
├── brain-core/                    # Motor de ejecución (Python)
│   ├── services/api/              # FastAPI (simplificado)
│   ├── services/browser-service/
│   ├── services/code-runners/
│   ├── database/
│   ├── Dockerfile
│   └── requirements.txt
│
├── brain-hub/                     # Fork de Paperclip (TypeScript)
│   ├── server/                    # API Paperclip + extensiones
│   ├── ui/                        # React UI + extensiones
│   ├── cli/
│   ├── packages/
│   │   ├── adapters/
│   │   │   ├── brain-gateway/     # 🆕 Nuestro adapter
│   │   │   ├── claude-local/
│   │   │   └── ...
│   │   ├── plugins/
│   │   │   ├── brain-dashboard/   # 🆕 Plugin de monitorización
│   │   │   └── ...
│   │   ├── db/
│   │   └── shared/
│   ├── Dockerfile
│   └── package.json
│
├── docker-compose.yml             # Orquestación completa
├── docker-compose.dev.yml         # Desarrollo local
├── docker-compose.production.yml  # Producción
└── README.md
```

### Opción B: Repositorios Separados (Mejor a largo plazo)

```
Organización GitHub: brain-ai/

brain-ai/brain-core        → Motor de ejecución (Python)
brain-ai/brain-hub          → Fork de Paperclip (TypeScript)
brain-ai/brain-adapter      → Paquete npm del adapter
brain-ai/brain-dashboard    → Plugin de Paperclip
brain-ai/brain-deploy       → Docker Compose + Helm charts
```

**Recomendación**: Empezar con Opción A (más fácil de desarrollar y depurar), migrar a Opción B cuando la base de código sea estable y los contratos entre componentes estén bien definidos.

---

## 6. Mapeo Detallado de Código Actual → Nueva Estructura

### Lo que se mueve a Brain Core

| Actual | Destino | Cambios necesarios |
|--------|---------|-------------------|
| `services/api/src/engine/` | `brain-core/src/engine/` | Eliminar `context_injector` directo → API param |
| `services/api/src/llm/` | `brain-core/src/llm/` | Sin cambios |
| `services/api/src/rag/` | `brain-core/src/rag/` | Deduplicar rutas en main.py |
| `services/api/src/tools/` | `brain-core/src/tools/` | Sin cambios |
| `services/api/src/mcp/` | `brain-core/src/mcp/` | Sin cambios |
| `services/api/src/browser/` | `brain-core/src/browser/` | Sin cambios |
| `services/api/src/code_executor/` | `brain-core/src/code_executor/` | Separar workspace admin |
| `services/api/src/providers/` | `brain-core/src/providers/` | Sin cambios |
| `services/api/src/openai_compat/` | `brain-core/src/openai_compat/` | Sin cambios |
| `services/api/src/a2a/` | `brain-core/src/a2a/` | Sin cambios |
| `services/api/src/auth/` | `brain-core/src/auth/` | Simplificar: solo API keys/JWT service |
| `services/api/src/db/repositories/` | `brain-core/src/db/` | Solo repos Core |
| `services/browser-service/` | `brain-core/services/browser-service/` | Sin cambios |
| `services/code-runners/` | `brain-core/services/code-runners/` | Sin cambios |

### Lo que se migra/adapta para Brain Hub

| Actual | Destino | Forma |
|--------|---------|-------|
| `services/api/src/monitoring/` | `brain-hub/packages/plugins/brain-dashboard/` | Plugin Paperclip |
| `services/api/src/config_router` | `brain-hub/server/src/routes/brain-config/` | Extensión del server |
| `services/api/src/user_router` | Paperclip nativo (`agents`, `companies`) | Reemplazado |
| `services/api/src/profile_router` | Paperclip nativo | Adaptado |
| `services/api/src/task_router` | Paperclip nativo (`issues`, `routines`) | Reemplazado |
| `services/api/src/artifacts/` | `brain-hub/packages/plugins/brain-dashboard/` | Dentro del plugin |
| `services/api/src/conversation_router` | Paperclip `issues` conversations | Adaptado |
| `services/api/src/skills/` | Paperclip nativo (`skills`) | Reemplazado |
| `services/gui/` (Angular) | `brain-hub/ui/` (React) | Reescribir progresivamente |

### Lo que desaparece (reemplazado por Paperclip)

| Actual | Reemplazo en Paperclip |
|--------|----------------------|
| `src/auth/` (login/register) | Paperclip auth system |
| Tabla `brain_users` | Paperclip `users` |
| `user_tasks` (cron-style) | Paperclip `routines` |
| `user_sandboxes` (admin) | Paperclip execution workspaces |
| GUI: login, dashboard, users, profile | React UI de Paperclip |
| `persistence.py` (Strapi legacy) | Eliminado |

---

## 7. Puntos de Acoplamiento y Soluciones

### 7.1 `context_injector.py` — El acoplamiento más fuerte

**Problema**: Lee `user_profiles` y `user_task_results` (tablas Hub) para inyectar briefing en prompts de agentes.

**Solución**: El Brain Adapter envía el briefing como parte del contexto en la llamada a Brain Core:

```python
# Brain Core recibe contexto externo como parámetro
@router.post("/api/v1/chains/{chain_id}/invoke")
async def invoke_chain(chain_id: str, request: InvokeRequest):
    # request.external_context contiene briefing del Hub
    context = request.external_context or {}
    # El engine usa este contexto sin acceder a tablas Hub
```

### 7.2 `MonitoringMiddleware` — Escritura cruzada

**Problema**: Core escribe directamente a `api_metrics` y `execution_traces` (tablas Hub).

**Solución**: Patrón outbox + eventos:

```python
# Brain Core emite eventos en lugar de escribir a tablas Hub
class CoreMetricsEmitter:
    async def record_request(self, method, path, status, duration):
        await self.event_bus.publish("metrics.request", {
            "method": method, "path": path,
            "status": status, "duration_ms": duration,
        })

    async def record_execution(self, trace_data):
        await self.event_bus.publish("metrics.execution", trace_data)

# Brain Hub consume estos eventos vía:
# 1. Redis pub/sub (si comparten Redis)
# 2. SSE endpoint de Core
# 3. Webhook callback
# 4. Polling periódico
```

### 7.3 Tablas compartidas (`brain_chains`, `brain_llm_providers`)

**Problema**: Hub configura cadenas y proveedores, Core los ejecuta.

**Solución**: Ownership claro + sincronización:

```
Hub (owner) ──── sync API ────► Core (consumer)

Hub escribe:                    Core lee:
  brain_chains                    chain_registry (in-memory)
  brain_llm_providers             provider cache
  agent_definitions               agent builders

Sincronización vía:
  POST brain-core/api/v1/admin/sync/chains
  POST brain-core/api/v1/admin/sync/providers
  POST brain-core/api/v1/admin/sync/agents
```

### 7.4 Conversaciones — Doble escritor

**Problema**: Core escribe mensajes durante ejecución, Hub muestra/edita en UI.

**Solución**: Core es el owner de los datos, Hub lee vía API:

```
Core: escribe conversations + messages durante ejecución
Hub:  lee vía GET brain-core/api/v1/conversations
      muestra en UI (React, no Angular)
      metadata propia (read/unread, archive) en DB Hub
```

---

## 8. Estrategia de Sincronización con Upstream Paperclip

Como Brain Hub es un fork, necesitamos una estrategia para mantenernos al día:

### Áreas que NO modificamos del fork

Mantener intacto para facilitar merges:
- `packages/adapters/claude-local/`, `codex-local/`, etc. (adapters existentes)
- `packages/db/` (schema base de Paperclip)
- `server/src/services/heartbeat.ts` (core del scheduling)
- `server/src/services/` (servicios base)
- `ui/src/` (componentes base de React)
- `cli/` (CLI base)

### Áreas que SÍ modificamos

Nuestras extensiones viven en paths claramente separados:
- `packages/adapters/brain-gateway/` (nuevo)
- `packages/plugins/brain-dashboard/` (nuevo)
- `server/src/adapters/registry.ts` (una línea: importar brain-gateway)
- `server/src/routes/brain-config/` (rutas adicionales)
- `ui/src/extensions/brain/` (componentes React propios)

### Workflow de merge

```
paperclipai/paperclip (upstream)
       │
       │  git fetch upstream
       │  git merge upstream/master --no-commit
       │  # Resolver conflictos (mínimos si seguimos la estrategia)
       │  git commit
       ▼
brain-ai/brain-hub (nuestro fork)
       │
       │  Solo tocamos paths /brain-*/
       │  Adapter registrado con 1 línea en registry
       │
       ▼
  Merge limpio en >95% de los casos
```

---

## 9. Beneficios de la Arquitectura Propuesta

### Para el usuario final

| Beneficio | Detalle |
|-----------|---------|
| **Lo mejor de dos mundos** | Capacidades profundas de Brain + orquestación de Paperclip |
| **Multi-agente real** | Brain como agente especializado junto a Claude, Codex, Cursor |
| **Gobernanza** | Presupuestos, aprobaciones, organigramas para controlar costes y riesgos |
| **RAG para todos** | Cualquier agente puede beneficiarse del RAG de Brain Core |
| **UI moderna** | React + Vite de Paperclip con extensiones Brain |
| **CLI** | `npx paperclipai` para gestión rápida |

### Para el desarrollo

| Beneficio | Detalle |
|-----------|---------|
| **Separación de concerns** | Core (Python, ejecución) vs Hub (TypeScript, orquestación) |
| **Escalabilidad** | Core escala horizontal independiente del Hub |
| **Testing independiente** | Cada componente testeable por separado |
| **Comunidad** | Beneficio de las contribuciones upstream de Paperclip (35K+ estrellas) |
| **Releases independientes** | Core y Hub con ciclos de vida propios |

### Técnicos

| Beneficio | Detalle |
|-----------|---------|
| **Zero vendor lock-in** | Protocolos estándar (OpenAI, A2A, MCP) |
| **Despliegue flexible** | Todo-en-uno o distribuido |
| **Migración gradual** | Brain actual sigue funcionando durante la transición |
| **Plug & play** | Cambiar Brain Core por otro motor sin tocar Brain Hub |

---

## 10. Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **Paperclip cambia rápido** (releases semanales) | Conflictos de merge frecuentes | Minimizar cambios en código upstream; extensiones en paths separados |
| **Doble stack (Python + TypeScript)** | Mayor complejidad operacional | Docker Compose simplifica despliegue; equipos pueden especializarse |
| **Latencia añadida** (Hub → Core vía HTTP) | Experiencia de usuario degradada | Red Docker interna (<1ms); streaming SSE para respuestas largas |
| **Dos bases de datos** | Inconsistencia de datos | Ownership claro por tabla; sincronización explícita via API |
| **Angular → React** | Esfuerzo de reescritura de UI | Migración progresiva; priorizar features Hub; mantener Angular para acceso directo a Core |
| **Paperclip podría pivotar** | Fork diverge demasiado | Mantener adapter como paquete independiente publicable en npm; reducir dependencia del fork |

---

## 11. Siguiente Paso Inmediato

Para validar la propuesta con mínimo esfuerzo:

**Proof of Concept (PoC)**: Crear un Brain Adapter funcional para Paperclip vanilla (sin fork) que conecte a la instancia actual de Brain.

```bash
# 1. Clonar Paperclip
git clone https://github.com/paperclipai/paperclip brain-hub-poc
cd brain-hub-poc

# 2. Crear adapter
mkdir -p packages/adapters/brain-gateway/src/server
# ... implementar execute mínimo ...

# 3. Registrar en registry.ts
# ... una línea de import ...

# 4. Levantar ambos
docker compose up brain-core
pnpm dev  # Brain Hub/Paperclip
```

**Criterio de éxito del PoC**: Desde la UI de Paperclip, "contratar" un agente Brain, asignarle un issue, y ver que Brain Core ejecuta la cadena y devuelve el resultado.

---

*Documento generado el 27 de marzo de 2026*
*Propuesta basada en el análisis detallado de Brain y Paperclip*
