# Brain 2.0 Adaptive Agent

Agente principal de Brain 2.0 con razonamiento adaptativo y 17+ core tools.

## Estructura

```
adaptive/
├── __init__.py          # Exports públicos
├── agent.py             # Builder principal + ChainDefinition
├── executor.py          # Loop de ejecución (LLM → Tools → Events)
├── validators.py        # Validación de tools, loops, JSON
│
├── prompts/             # System prompts por proveedor
│   ├── __init__.py      # get_system_prompt(), get_workflow()
│   ├── base.py          # Secciones comunes (tools, workflows)
│   ├── ollama.py        # Prompt para Ollama/local
│   ├── openai.py        # Prompt para OpenAI/GPT
│   ├── anthropic.py     # Prompt para Claude
│   └── google.py        # Prompt para Gemini
│
├── handlers/            # Handlers de tools especializados
│   ├── __init__.py      # Registry de handlers
│   ├── base.py          # ToolHandler base + DefaultHandler
│   ├── finish.py        # Handler para finish (terminal)
│   ├── delegate.py      # Handler para delegate (subagentes)
│   ├── slides.py        # Handler para generate_slides
│   └── reasoning.py     # Handler para think/reflect/plan
│
└── events/              # Emisores de eventos
    ├── __init__.py      # Exports
    ├── stream_emitter.py # StreamEvents para SSE
    └── brain_emitter.py  # Brain Events para Open WebUI
```

## Flujo de Ejecución

```
1. build_adaptive_agent()
   ├── Detectar complejidad (trivial/simple/moderate/complex)
   ├── Configurar razonamiento (temperatura, max_iterations)
   └── Crear AdaptiveExecutor

2. AdaptiveExecutor.execute()
   ├── while iteration < max && !complete:
   │   ├── call_llm_with_tools()
   │   ├── Si respuesta directa → final_answer
   │   └── Si tool_calls:
   │       └── Para cada tool:
   │           ├── get_handler(tool_name)
   │           ├── tool_registry.execute()
   │           └── handler.process_result()
   └── Si no hay finish → force_finish()

3. Eventos emitidos:
   ├── StreamEvents: start, iteration_start, tool_start, token, end
   └── BrainEvents: thinking, action, sources, artifact (para Open WebUI)
```

## Uso

```python
from src.engine.chains.adaptive import build_adaptive_agent

async for event in build_adaptive_agent(
    config=chain_config,
    llm_url="http://ollama:11434",
    model="llama3.2",
    input_data={"message": "Genera una imagen de un gato"},
    memory=[],
    execution_id="abc123",
    provider_type="ollama",
    emit_brain_events=True  # Para Open WebUI
):
    print(event)
```

## Handlers Disponibles

| Handler | Tools | Comportamiento |
|---------|-------|---------------|
| `FinishHandler` | finish | Terminal, extrae answer |
| `DelegateHandler` | delegate | Invoca subagentes, emite imágenes |
| `SlidesHandler` | generate_slides | Terminal, emite artifacts |
| `ReasoningHandler` | think, reflect, plan | Emite thinking events |
| `DefaultHandler` | * (resto) | Ejecución genérica |

## Proveedores Soportados

- `ollama`: Modelos locales
- `openai`: GPT-4, GPT-4o
- `anthropic`: Claude 3.x
- `google`: Gemini 1.5/2.0
