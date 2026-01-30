# Brain 2.0 Subagentes Especializados

Subagentes de dominio que el Adaptive Agent puede invocar via `delegate`.

## Estructura

```
agents/
├── __init__.py          # Exports + register_all_subagents()
├── base.py              # BaseSubAgent + SubAgentRegistry
├── router.py            # Routing de tareas (legacy)
│
├── media/               # Subagente de imágenes
│   ├── __init__.py      # Export MediaAgent
│   ├── agent.py         # Lógica principal
│   └── prompts.py       # System prompt
│
└── slides/              # Subagente de presentaciones
    ├── __init__.py      # Export SlidesAgent
    ├── agent.py         # Lógica principal
    ├── styles.py        # CSS de las slides
    ├── templates.py     # Dataclasses + generación HTML
    └── events.py        # Brain Events helpers
```

## Flujo de Delegación

```
1. Adaptive Agent llama delegate(agent="media_agent", task="...")
   
2. delegation.py:
   ├── Obtiene subagent de subagent_registry
   └── Llama subagent.execute(task, context, llm_config)

3. Subagente ejecuta:
   ├── MediaAgent: Genera imagen con DALL-E/SD/Flux
   └── SlidesAgent: Genera HTML con Brain Events

4. Retorna SubAgentResult:
   ├── success, response, agent_id
   ├── tools_used, images, sources
   └── data (específico del dominio)
```

## Subagentes Disponibles

### MediaAgent (`media_agent`)

Genera imágenes usando modelos de IA.

```python
# Invocación via delegate
delegate(
    agent="media_agent",
    task="Genera un logo minimalista para empresa tech"
)

# Resultado
{
    "success": True,
    "images": [{"url": "...", "provider": "openai", "model": "dall-e-3"}],
    "response": "He generado la imagen..."
}
```

**Proveedores:**
- OpenAI DALL-E 3
- Stable Diffusion
- Flux

### SlidesAgent (`slides_agent`)

Genera presentaciones HTML con streaming de Brain Events.

```python
# Invocación via delegate con outline JSON
delegate(
    agent="slides_agent",
    task='{"title": "IA", "slides": [{"title": "Intro", "type": "bullets", "bullets": ["..."]}]}'
)

# Resultado incluye Brain Events para Open WebUI
{
    "success": True,
    "data": {"html": "<style>...</style><div class='slide'>...", "slides_count": 5},
    "response": "<!--BRAIN_EVENT:{...}-->..."
}
```

**Tipos de slides:**
- `title`: Slide de título
- `bullets`: Lista de puntos
- `stats`: Estadísticas con valores grandes
- `comparison`: Grid de comparación
- `quote`: Cita destacada
- `content`: Contenido genérico

## Crear un Nuevo Subagente

1. Crear carpeta `agents/nuevo/`

2. Crear `agent.py`:
```python
from ..base import BaseSubAgent, SubAgentResult

class NuevoAgent(BaseSubAgent):
    id = "nuevo_agent"
    name = "Nuevo Agent"
    description = "Descripción para el prompt del Adaptive Agent"
    
    async def execute(self, task, context=None, **llm_config) -> SubAgentResult:
        # Tu lógica aquí
        return SubAgentResult(
            success=True,
            response="Resultado",
            agent_id=self.id,
            agent_name=self.name
        )
```

3. Registrar en `agents/__init__.py`:
```python
from .nuevo import NuevoAgent

def register_all_subagents():
    subagent_registry.register(NuevoAgent())
```

4. Añadir a `DELEGATE_TOOL` en `tools/core/delegation.py`

## SubAgentResult

```python
@dataclass
class SubAgentResult:
    success: bool           # Si la tarea se completó
    response: str           # Respuesta textual
    agent_id: str           # ID del subagente
    agent_name: str         # Nombre legible
    tools_used: List[str]   # Tools usadas
    images: List[dict]      # Imágenes generadas [{url, prompt, provider}]
    sources: List[str]      # Fuentes consultadas
    data: Dict[str, Any]    # Datos específicos del dominio
    error: Optional[str]    # Mensaje de error si falló
    execution_time_ms: int  # Tiempo de ejecución
```
