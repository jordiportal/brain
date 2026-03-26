# Propuesta: Estandarización de Artifacts al Estilo A2A

**Fecha:** 2026-03-26  
**Estado:** Borrador / RFC  
**Autor:** Brain Platform Team

---

## 1. Diagnóstico: Estado Actual

El sistema de artifacts tiene **4 implementaciones paralelas** que no comparten modelo, almacenamiento ni superficie de API. Esto genera inconsistencias, código duplicado y una experiencia fragmentada.

### 1.1 Inventario de Sistemas de Artifacts

| # | Sistema | Modelo | Storage | API Surface | Usado por |
|---|---------|--------|---------|-------------|-----------|
| **A** | **REST File Artifacts** | `artifacts/models.py` → `ArtifactResponse` | SQLite per-user (`user_db`) + ficheros en disco | `/api/v1/artifacts/*` | GUI (sidebar, viewer, profile), Tools (generate_image, generate_video, etc.) |
| **B** | **Engine Task Artifacts** | `engine/models.py` → `Artifact` con `Part[]` | Postgres `tasks.artifacts` JSONB | Interno (task_manager) | Casi sin uso real — `add_artifact()` definido pero nunca invocado |
| **C** | **A2A Protocol Artifacts** | `a2a/models.py` → `A2AArtifact` con `A2APart[]` | Derivado de (B) vía adapter | `/a2a/tasks/*`, `SendMessage` | Clientes A2A externos |
| **D** | **Brain Events (streaming)** | Markers HTML inline `<!--BRAIN_EVENT:...-->` | Sin persistencia (stream efímero) | SSE token stream | Open WebUI, GUI chat |

### 1.2 Comparación de Modelos

```
┌─────────────────────────────────────────────────────────────────┐
│  REST File Artifact (A)        │  Engine Artifact (B)           │
│  ─────────────────────────     │  ──────────────────            │
│  artifact_id: str              │  id: str (UUID)                │
│  type: ArtifactType (enum)     │  name: str                     │
│  title: str                    │  description: str              │
│  description: str              │  parts: list[Part]             │
│  file_name: str                │  agent_id: str                 │
│  file_path: str  ← FÍSICO     │  metadata: dict                │
│  mime_type: str                │  created_at: datetime          │
│  file_size: int                │                                │
│  conversation_id: str          │  Part:                         │
│  agent_id: str                 │    type: text|file|data|       │
│  source: ArtifactSource        │          image|video           │
│  tool_id: str                  │    text: str                   │
│  metadata: dict                │    url: str                    │
│  version: int                  │    data: dict                  │
│  is_latest: bool               │    media_type: str             │
│  status: ArtifactStatus        │    filename: str               │
│  created_at, updated_at,       │                                │
│  accessed_at                   │                                │
├─────────────────────────────────────────────────────────────────┤
│  A2A Artifact (C)              │  Brain Event Artifact (D)      │
│  ────────────────              │  ─────────────────────         │
│  artifact_id: str (UUID)       │  type: "artifact"              │
│  name: str                     │  artifact_type: str            │
│  description: str              │  title: str                    │
│  parts: list[A2APart]          │  content_base64: str           │
│  metadata: dict                │  format: html|markdown|text    │
│  extensions: list[str]         │  url: str (alternativo)        │
│                                │  artifact_id: str              │
│  A2APart:                      │  mime_type: str                │
│    text, raw, url, data,       │  metadata: dict                │
│    metadata, filename,         │                                │
│    media_type                  │                                │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Problemas Detectados

1. **Modelos incompatibles**: El modelo REST (A) es plano (1 artifact = 1 fichero), mientras que A2A (C) y Engine (B) son composicionales (1 artifact = N parts). No hay forma directa de mapear entre ellos.

2. **Storage dual desconectado**: Los file artifacts van a SQLite per-user; los task artifacts van a Postgres JSONB. No hay sincronización, no hay vista unificada.

3. **Task artifacts vacíos**: El Engine define `Task.artifacts` y el adapter lo traduce a A2A, pero **ninguna tool escribe ahí**. Las tools escriben en el SQLite de file artifacts. Un cliente A2A que pida `GetTask` siempre ve `artifacts: []`.

4. **Streaming propietario**: Brain Events usan un formato HTML-marker custom (`<!--BRAIN_EVENT:...-->`) en lugar del `TaskArtifactUpdateEvent` estándar A2A. Esto obliga a dos parsers diferentes en el frontend.

5. **Tipos dispersos**: `ArtifactType` (REST) tiene 9 valores; `Part.type` (Engine) tiene 5 valores; `A2APart` usa `media_type` (MIME). No hay mapeo canónico.

6. **Frontend acoplado al modelo plano**: Angular `ArtifactService` asume campos como `file_path`, `file_size`, `version`, `is_latest` que no existen en el mundo A2A.

---

## 2. Referencia: Modelo A2A v1.0

Según la [especificación A2A v1.0](https://google.github.io/A2A/specification/), un Artifact es:

> *"An output (e.g., a document, image, structured data) generated by the agent as a result of a task, composed of Parts."*

```protobuf
message Artifact {
  string artifact_id = 1;
  optional string name = 2;
  optional string description = 3;
  repeated Part parts = 4;
  optional google.protobuf.Struct metadata = 5;
  repeated string extensions = 6;
}

message Part {
  oneof part {
    TextPart text_part = 1;
    FilePart file_part = 2;
    DataPart data_part = 3;
  }
  optional google.protobuf.Struct metadata = 4;
}

message FilePart {
  oneof content {
    bytes inline_data = 1;
    FileUri file_uri = 2;
  }
  optional FilePartMetadata metadata = 3;
}
```

**Principios clave:**
- Un Artifact tiene **N Parts** (multimodal: texto + fichero + datos estructurados en el mismo artifact)
- `FilePart` soporta tanto **inline (base64)** como **URI** (para ficheros remotos o locales)
- Los artifacts viven en el **Task** como outputs
- El streaming usa `TaskArtifactUpdateEvent` con soporte de `append` + `last_chunk`
- `metadata` es un `Struct` genérico (extensible sin romper el esquema)

---

## 3. Opciones Propuestas

### Opción A: Unificación Total — Modelo A2A como Fuente Única

**Descripción**: Reemplazar todos los modelos de artifact por uno solo basado en A2A. Los file artifacts actuales se convierten en artifacts A2A con `FilePart` (URI apuntando al fichero en disco). El almacenamiento se unifica en Postgres (tabla `tasks.artifacts` o nueva tabla `artifacts` con estructura A2A).

**Cambios requeridos:**

| Componente | Cambio |
|------------|--------|
| `engine/models.py` | `Artifact` ya es casi A2A → alinear campo `id` → `artifact_id`, eliminar `agent_id`/`created_at` (van a `metadata`) |
| `artifacts/models.py` | Reescribir `ArtifactCreate`/`ArtifactResponse` para usar Part-based model. Mantener campos convenience (`file_path`, `mime_type`) como getters derivados |
| `artifacts/repository.py` | Migrar de SQLite per-user a Postgres. Un artifact es una fila con JSONB `parts[]` |
| `artifacts/router.py` | Mantener mismos endpoints `/api/v1/artifacts/*` pero retornar modelo A2A-compatible |
| `a2a/adapter.py` | Simplificar — la conversión se vuelve trivial o innecesaria |
| `brain_events.py` | Emitir `TaskArtifactUpdateEvent` serializado como SSE, eliminar markers HTML |
| Tools (`generate_image`, etc.) | Crear `Artifact` con `FilePart(uri=...)` en vez de `ArtifactCreate(file_path=...)` |
| Frontend `ArtifactService` | Adaptar interfaz `Artifact` al modelo Part-based, mantener helpers de conveniencia |
| SQL migrations | Nueva tabla `artifacts` en Postgres con estructura A2A; migrar datos de SQLite |

**Ventajas:**
- Un solo modelo para todo el sistema
- Compatibilidad A2A nativa (zero-conversion para clientes externos)
- Artifacts multimodales (un artifact con texto + imagen + datos)
- Streaming estándar con `TaskArtifactUpdateEvent`
- Elimina la brecha entre `/api/v1/artifacts` y `/a2a/tasks` — mismos datos

**Riesgos:**
- Migración invasiva: toca backend, frontend, tools, SQL, y streaming
- La persistencia pasa de SQLite per-user (aislado) a Postgres (compartido) — cambio de modelo de aislamiento
- El frontend necesita refactor significativo para manejar `parts[]` en vez de `file_path`

---

### Opción B: Capa de Compatibilidad — Modelo Interno A2A + REST Facade

**Descripción**: El modelo **interno** se unifica a estilo A2A (engine + storage), pero la API REST `/api/v1/artifacts` mantiene su interfaz actual como "facade" que traduce entre el modelo A2A interno y la respuesta plana que el frontend espera.

**Cambios requeridos:**

| Componente | Cambio |
|------------|--------|
| Nuevo: `core/artifact.py` | Modelo canónico `Artifact` + `Part` (estilo A2A) usado internamente |
| `artifacts/repository.py` | Migrar a Postgres, almacenar modelo A2A internamente |
| `artifacts/router.py` | Adapter layer: `A2AArtifact` → `ArtifactResponse` (plano) para la REST API |
| `a2a/adapter.py` | Se simplifica — modelo interno ya es A2A |
| `brain_events.py` | Emitir `TaskArtifactUpdateEvent` + mantener Brain Events como wrapper fino |
| Tools | Crean `Artifact(parts=[FilePart(...)])` internamente |
| Frontend | Sin cambios inmediatos — recibe mismo JSON que antes |
| SQL migrations | Misma migración de storage que Opción A |

**Ventajas:**
- Modelo interno limpio y alineado con A2A
- Frontend no requiere cambios inmediatos (migración gradual)
- Brain Events pueden seguir funcionando como wrapper sobre `TaskArtifactUpdateEvent`
- Menor riesgo de romper la GUI existente

**Riesgos:**
- Mantiene dos "formas" de un artifact (interna A2A + facade REST plano)
- La facade acumula complejidad si el modelo A2A evoluciona
- No resuelve completamente la fragmentación (la GUI sigue viendo el modelo viejo)

---

### Opcion C: Convergencia Gradual — Bridge Pattern

**Descripción**: En lugar de migrar todo de golpe, crear un **bridge** que conecte los sistemas existentes. Los file artifacts (A) se registran automáticamente como task artifacts (B), y el streaming (D) emite `TaskArtifactUpdateEvent` además de Brain Events.

**Cambios requeridos:**

| Componente | Cambio |
|------------|--------|
| `artifacts/repository.py` | Después de crear en SQLite, también llamar a `TaskRepository.add_artifact()` con conversión |
| Nuevo: `artifacts/bridge.py` | Módulo que convierte `ArtifactResponse` → `engine.Artifact` y registra en el Task activo |
| `brain_events.py` | Añadir emisión dual: Brain Event marker + `TaskArtifactUpdateEvent` como SSE separado |
| `a2a/router.py` | Ya funciona — ahora `task.artifacts` estará poblado |
| Tools | Mínimo: pasar `task_id` a las tools para que el bridge sepa dónde registrar |
| Frontend | Sin cambios (sigue consumiendo REST `/artifacts`) |
| SQL | Sin migración — se mantiene SQLite + Postgres |

**Ventajas:**
- Cambio mínimo e incremental
- No rompe nada existente
- Los clientes A2A empiezan a ver artifacts en tasks
- Permite migrar gradualmente hacia Opción A o B en el futuro

**Riesgos:**
- Duplicación de datos (SQLite + Postgres)
- El bridge añade complejidad y puede fallar silenciosamente
- No unifica el modelo — sigue habiendo 4 representaciones
- Deuda técnica a largo plazo

---

## 4. Matriz Comparativa

| Criterio | Opción A (Total) | Opción B (Facade) | Opción C (Bridge) |
|----------|:-:|:-:|:-:|
| Alineación con A2A spec | Alta | Alta | Media |
| Impacto en frontend | Alto | Bajo | Nulo |
| Impacto en backend | Alto | Medio | Bajo |
| Impacto en tools | Medio | Medio | Bajo |
| Riesgo de regresión | Alto | Medio | Bajo |
| Deuda técnica resultante | Baja | Media | Alta |
| Soporte multimodal (artifact con N parts) | Completo | Completo (interno) | Parcial |
| Streaming A2A (`TaskArtifactUpdateEvent`) | Nativo | Nativo (interno) | Dual (bridge) |
| Clientes A2A ven artifacts | Sí | Sí | Sí |
| Complejidad de implementación | Alta | Media | Baja |

---

## 5. Recomendación

**Opción B (Facade)** ofrece el mejor equilibrio:

1. **Internamente todo es A2A** — un solo modelo canónico, un solo storage, streaming estándar.
2. **El frontend no se rompe** — la REST API traduce a la forma plana que Angular espera.
3. **Migración progresiva del frontend** — cuando se quiera, se crea una nueva API `/api/v2/artifacts` que exponga el modelo A2A directamente y se migra el frontend.
4. **Los clientes A2A ven artifacts reales** — `GetTask` deja de retornar `artifacts: []`.

El plan de ejecución sería:

```
Fase 1: Modelo canónico interno
  ├── Crear src/core/artifacts.py con Artifact + Part estilo A2A
  ├── Migrar engine/models.py Artifact → importar del canónico
  └── Simplificar a2a/adapter.py

Fase 2: Unificación de storage
  ├── Nueva tabla Postgres `artifacts` con estructura Part-based
  ├── Migrar ArtifactRepository a Postgres
  └── Migrar datos existentes de SQLite

Fase 3: Integración con Tasks
  ├── Las tools registran artifacts en Task.artifacts
  ├── TaskArtifactUpdateEvent en streaming
  └── Brain Events como wrapper fino opcional

Fase 4: REST Facade
  ├── Router /api/v1/artifacts convierte modelo canónico → respuesta plana
  ├── Tests de compatibilidad con frontend actual
  └── Deprecar campos legacy

Fase 5 (futura): Frontend A2A-native
  ├── Nueva API /api/v2/artifacts con modelo Part-based
  ├── Migrar Angular a modelo Part-based
  └── Eliminar facade v1
```

---

## 6. Detalle Técnico del Modelo Canónico Propuesto

```python
# src/core/artifacts.py — Modelo canónico (propuesta)

class PartType(str, Enum):
    TEXT = "text"
    FILE = "file"
    DATA = "data"

class Part(BaseModel):
    """A2A-aligned Part: smallest content unit."""
    type: PartType = PartType.TEXT
    
    # TextPart
    text: Optional[str] = None
    
    # FilePart  
    inline_data: Optional[str] = None  # base64
    uri: Optional[str] = None          # file:// or https://
    
    # DataPart
    data: Optional[dict[str, Any]] = None
    
    # Common
    media_type: Optional[str] = None   # MIME type
    filename: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Artifact(BaseModel):
    """A2A-aligned Artifact: tangible task output."""
    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = None
    description: Optional[str] = None
    parts: list[Part] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    extensions: list[str] = Field(default_factory=list)

    # Brain-specific (in metadata for A2A, explicit for internal use)
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def primary_file(self) -> Optional[Part]:
        """Convenience: first file part (for backward compat with REST API)."""
        return next((p for p in self.parts if p.type == PartType.FILE), None)

    @property
    def primary_text(self) -> Optional[str]:
        """Convenience: concatenated text parts."""
        return "\n".join(p.text for p in self.parts if p.text)
    
    def to_a2a(self) -> "A2AArtifact":
        """Direct conversion to A2A wire format."""
        ...
    
    @classmethod
    def from_file(cls, *, uri: str, filename: str, media_type: str,
                  name: str, description: str = None, **kwargs) -> "Artifact":
        """Factory for single-file artifacts (replaces ArtifactCreate)."""
        return cls(
            name=name,
            description=description,
            parts=[Part(type=PartType.FILE, uri=uri, filename=filename,
                        media_type=media_type)],
            **kwargs,
        )
```

### Mapeo REST Facade (backward compat)

```python
# Conversión Artifact canónico → ArtifactResponse REST (plano)
def artifact_to_rest_response(art: Artifact) -> dict:
    fp = art.primary_file
    return {
        "artifact_id": art.artifact_id,
        "type": _mime_to_artifact_type(fp.media_type if fp else None),
        "title": art.name,
        "description": art.description,
        "file_name": fp.filename if fp else None,
        "file_path": fp.uri if fp else None,  # file:// URI
        "mime_type": fp.media_type if fp else None,
        "metadata": art.metadata,
        "created_at": art.created_at.isoformat(),
        # ... demás campos derivados
    }
```

---

## 7. Siguiente Paso

Decidir qué opción seguir y en qué fase comenzar. Si se elige la Opción B recomendada, el primer paso concreto sería:

1. Crear `src/core/artifacts.py` con el modelo canónico
2. Hacer que `engine/models.py` importe y re-exporte `Artifact` y `Part` desde ahí
3. Actualizar `a2a/adapter.py` para usar el modelo canónico
4. Escribir tests unitarios de conversión canónico ↔ A2A ↔ REST
