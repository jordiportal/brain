# Análisis y Propuesta de Estandarización de Agentes

## 📊 Análisis de Agentes Actuales

### Inventario de Agentes (8 totales)

| Agente | Archivo | Líneas | Prompts | Pasos | Patrón |
|--------|---------|--------|---------|-------|--------|
| **Conversational** | `conversational.py` | ~150 | 1 hardcoded | 1 (LLM) | Simple |
| **SAP Agent** | `sap_agent.py` | ~320 | 4 f-strings | 3 (Plan→Tool→Synth) | ReAct Simplificado |
| **Tool Agent** | `tool_agent.py` | ~380 | 2 hardcoded | 3 (Plan→Tool→Synth) | ReAct Simplificado |
| **Code Execution** | `code_execution_agent.py` | ~560 | 4 mixtos | 5 (Plan→Gen→Exec→Handle→Synth) | ReAct Completo |
| **Orchestrator** | `orchestrator_agent.py` | ~710 | 4 hardcoded | N (Think→Act→Observe loop) | ReAct Multi-Agente |
| **RAG** | `rag_chain.py` | ~340 | 1 hardcoded | 2 (Retrieval→Synth) | Retrieval |
| **Browser** | `browser_agent.py` | ~490 | 1 hardcoded | 3 (Plan→Action→Observe) | ReAct con Estado |
| **OpenAI Web Search** | `openai_web_search_agent.py` | ~270 | 1 hardcoded | 1 (Native API) | Pass-through |

---

## 🔍 Problemas Identificados

### 1. **Prompts NO Editables**
```python
# ❌ Problema: Hardcoded en el código Python
SYSTEM_PROMPT = """Eres un asistente..."""

# ✅ Solución: Prompts en NodeDefinition
NodeDefinition(
    id="planner",
    system_prompt="Eres un asistente...",  # Editable desde Strapi
    prompt_template="..."  # Con variables {{query}}, {{tools}}, etc.
)
```

**Agentes afectados**: TODOS (8/8)

### 2. **Estructura Inconsistente**

#### Conversational (Simple)
```python
async def build_conversational_chain_stream(...):
    # 1 paso: LLM directo
    messages = [system, memory, user]
    yield tokens...
```

#### SAP Agent (3 pasos)
```python
async def build_sap_agent(...):
    # Paso 1: Planificación (qué tool usar)
    # Paso 2: Ejecución (llamar tool)
    # Paso 3: Síntesis (formatear resultado)
```

#### Orchestrator (N pasos con loop)
```python
async def build_orchestrator_agent(...):
    for step in plan:
        # Think → Act → Observe (ReAct loop)
        yield sub_agent()
    # Síntesis final
```

**Problema**: No hay un patrón unificado de pasos/fases.

### 3. **Funciones Helper NO Reutilizables**

Cada agente reimplementa:
- `extract_json()` → 3 implementaciones diferentes
- `execute_tool()` → 2 implementaciones
- Manejo de memoria → Cada uno a su manera

### 4. **Prompts con Variables Hardcoded**

```python
# ❌ SAP Agent - f-string directo
synth_prompt = f"""Datos: {json.dumps(data)[:4000]}
Pregunta: {query}"""

# ❌ Code Execution - template en código
def get_code_generator_prompt(language, task, libraries):
    return f"""Lenguaje: {language}
    Tarea: {task}..."""
```

**Problema**: No se pueden editar desde GUI sin modificar código.

---

## 🎯 Propuesta de Estándar

### **Principios de Diseño**

1. ✅ **Separation of Concerns**: Prompts ≠ Lógica ≠ Configuración
2. ✅ **Editability**: Todos los prompts editables desde Strapi/GUI
3. ✅ **Consistency**: Patrón de fases común (aunque flexible)
4. ✅ **Reusability**: Funciones helper compartidas

---

## 📐 Estructura Estándar de un Agente

### **1. Metadata y Definición** (ChainDefinition)

```python
from ..models import ChainDefinition, NodeDefinition, ChainConfig

AGENT_DEFINITION = ChainDefinition(
    id="my_agent",
    name="My Agent",
    description="Brief description",
    type="tools",  # conversational | tools | rag | custom
    version="1.0.0",
    
    # ✅ NODOS con PROMPTS EDITABLES
    nodes=[
        NodeDefinition(
            id="input",
            type=NodeType.INPUT,
            name="User Input"
        ),
        NodeDefinition(
            id="planner",
            type=NodeType.LLM,
            name="Planner",
            system_prompt="You are a planner...",  # Editable
            prompt_template="""  # Editable con variables
Task: {{query}}
Tools: {{tools}}
Memory: {{memory}}
"""
        ),
        NodeDefinition(
            id="executor",
            type=NodeType.TOOL,
            name="Tool Executor"
        ),
        NodeDefinition(
            id="synthesizer",
            type=NodeType.LLM,
            name="Synthesizer",
            system_prompt="Synthesize results...",  # Editable
            prompt_template="""
Query: {{query}}
Results: {{results}}
"""
        ),
        NodeDefinition(
            id="output",
            type=NodeType.OUTPUT,
            name="Final Answer"
        )
    ],
    
    config=ChainConfig(
        use_memory=True,
        max_memory_messages=10,
        temperature=0.3
    )
)
```

---

### **2. Builder Function** (Lógica del Agente)

```python
from .agent_helpers import (  # ✅ Funciones compartidas
    extract_json,
    build_llm_messages,
    stream_llm_response
)

async def build_my_agent(
    config: ChainConfig,
    llm_url: str,
    model: str,
    input_data: dict,
    memory: list,
    execution_id: str = "",
    stream: bool = True,
    provider_type: str = "ollama",
    api_key: Optional[str] = None,
    **kwargs
) -> AsyncGenerator[StreamEvent, None]:
    """
    Builder siguiendo patrón estándar.
    
    FASES ESTÁNDAR:
    1. Planning (opcional): Decidir estrategia
    2. Execution: Ejecutar acción/herramienta
    3. Observation (opcional): Analizar resultado
    4. Synthesis: Generar respuesta final
    """
    
    query = input_data.get("message", "")
    
    # ========== FASE 1: PLANNING ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="planner",
        node_name="Planning",
        data={"query": query}
    )
    
    # ✅ Prompt desde NodeDefinition (editable)
    planner_node = AGENT_DEFINITION.get_node("planner")
    prompt_vars = {
        "query": query,
        "tools": get_tools_description(),
        "memory": format_memory(memory)
    }
    
    planner_messages = build_llm_messages(
        system_prompt=planner_node.system_prompt,
        template=planner_node.prompt_template,
        variables=prompt_vars,
        memory=memory
    )
    
    plan = await call_llm(llm_url, model, planner_messages, ...)
    
    yield StreamEvent(
        event_type="node_end",
        node_id="planner",
        data={"plan": plan}
    )
    
    # ========== FASE 2: EXECUTION ==========
    yield StreamEvent(...)
    result = await execute_action(plan, ...)
    yield StreamEvent(...)
    
    # ========== FASE 3: SYNTHESIS ==========
    yield StreamEvent(
        event_type="node_start",
        node_id="synthesizer",
        ...
    )
    
    synth_node = AGENT_DEFINITION.get_node("synthesizer")
    synth_messages = build_llm_messages(
        system_prompt=synth_node.system_prompt,
        template=synth_node.prompt_template,
        variables={
            "query": query,
            "results": result
        },
        memory=memory
    )
    
    full_response = ""
    async for token in call_llm_stream(...):
        full_response += token
        yield StreamEvent(
            event_type="token",
            content=token
        )
    
    yield StreamEvent(
        event_type="node_end",
        node_id="synthesizer",
        data={"response": full_response}
    )
    
    # Para modo no-streaming
    if not stream:
        yield {"_result": {"response": full_response}}
```

---

### **3. Helper Functions Compartidas** (Nuevo archivo)

```python
# services/api/src/engine/chains/agent_helpers.py

"""
Funciones helper compartidas por todos los agentes.
Evita duplicación de código.
"""

import json
import re
from typing import Optional, Dict, Any, List

def extract_json(text: str) -> Optional[Dict]:
    """Extraer JSON de texto (implementación única)"""
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
        r'\{[\s\S]*\}'
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
    return None


def build_llm_messages(
    system_prompt: str,
    template: Optional[str],
    variables: Dict[str, Any],
    memory: List[Dict] = None,
    max_memory: int = 10
) -> List[Dict]:
    """
    Construir mensajes para LLM con:
    - System prompt
    - Template con variables {{var}}
    - Memoria
    """
    messages = []
    
    # System prompt
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # Memoria (últimos N mensajes)
    if memory:
        messages.extend(memory[-max_memory:])
    
    # Template con variables
    if template:
        content = template
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"  # {{key}}
            content = content.replace(placeholder, str(value))
        messages.append({"role": "user", "content": content})
    
    return messages


def format_json_preview(data: Any, max_chars: int = 4000) -> tuple[str, bool]:
    """
    Formatear JSON con límite de caracteres.
    
    Returns:
        (json_string, was_truncated)
    """
    json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    truncated = len(json_str) > max_chars
    preview = json_str[:max_chars]
    return preview, truncated


def format_memory(memory: List[Dict], max_messages: int = 10) -> str:
    """Formatear memoria para incluir en prompts"""
    if not memory:
        return "No hay conversación previa."
    
    formatted = []
    for msg in memory[-max_messages:]:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        formatted.append(f"{role.upper()}: {content}")
    
    return "\n".join(formatted)
```

---

## 🏗️ Estructura de Archivos Propuesta

```
services/api/src/engine/chains/
├── __init__.py                 # Registry de todos los agentes
├── agent_helpers.py            # ✅ NUEVO: Funciones compartidas
├── llm_utils.py                # Utilidades LLM (ya existe)
│
├── conversational.py           # ✅ Refactorizar con estándar
├── sap_agent.py                # ✅ Refactorizar con estándar
├── tool_agent.py               # ✅ Refactorizar con estándar
├── code_execution_agent.py     # ✅ Refactorizar con estándar
├── orchestrator_agent.py       # ✅ Refactorizar con estándar
├── rag_chain.py                # ✅ Refactorizar con estándar
├── browser_agent.py            # ✅ Refactorizar con estándar
└── openai_web_search_agent.py  # ✅ Refactorizar con estándar
```

---

## 📋 Checklist de Refactorización por Agente

### ✅ **Para CADA agente**, aplicar:

- [ ] **1. Extraer prompts hardcoded a NodeDefinition**
  ```python
  # Antes (hardcoded)
  PROMPT = """System prompt..."""
  
  # Después (editable)
  NodeDefinition(
      id="step_name",
      system_prompt="System prompt...",
      prompt_template="Template con {{variables}}"
  )
  ```

- [ ] **2. Usar `agent_helpers` en lugar de funciones locales**
  ```python
  # Antes
  def extract_json(text): ...  # Local
  
  # Después
  from .agent_helpers import extract_json
  ```

- [ ] **3. Seguir patrón de fases estándar**
  ```python
  # 1. Planning (si aplica)
  yield StreamEvent("node_start", "planner")
  plan = await call_llm(...)
  yield StreamEvent("node_end", "planner")
  
  # 2. Execution
  yield StreamEvent("node_start", "executor")
  result = await execute(...)
  yield StreamEvent("node_end", "executor")
  
  # 3. Synthesis
  yield StreamEvent("node_start", "synthesizer")
  response = await synthesize(...)
  yield StreamEvent("node_end", "synthesizer")
  ```

- [ ] **4. Documentación clara**
  ```python
  """
  AGENT_NAME - Brief description
  
  PHASES:
  1. Phase name: Description
  2. Phase name: Description
  
  NODES:
  - node_id (type): Description
  
  MEMORY: Yes/No
  TOOLS: List of tools or "None"
  """
  ```

---

## 🎨 Ejemplo de Migración: Conversational Agent

### ANTES (actual)

```python
# conversational.py (líneas 40-41, 70, 76)
system_prompt="Eres un asistente útil..."  # Hardcoded en NodeDef
system_prompt = config.system_prompt or CONVERSATIONAL_CHAIN.nodes[1].system_prompt
messages.append({"role": "system", "content": system_prompt})
```

### DESPUÉS (estándar)

```python
# conversational.py (refactorizado)
from .agent_helpers import build_llm_messages

CONVERSATIONAL_DEFINITION = ChainDefinition(
    nodes=[
        NodeDefinition(
            id="llm",
            type=NodeType.LLM,
            system_prompt="Eres un asistente útil y amigable.",  # ✅ Editable
            prompt_template="{{user_message}}"  # ✅ Con variable
        )
    ]
)

async def build_conversational_chain_stream(...):
    llm_node = CONVERSATIONAL_DEFINITION.get_node("llm")
    
    messages = build_llm_messages(
        system_prompt=llm_node.system_prompt,
        template=llm_node.prompt_template,
        variables={"user_message": user_input},
        memory=memory
    )
    
    # Resto igual...
```

---

## 🔄 Persistencia de Prompts en Strapi

### Schema de `brain-chain` (actualizar)

```json
{
  "kind": "collectionType",
  "collectionName": "brain_chains",
  "info": {
    "singularName": "brain-chain",
    "pluralName": "brain-chains"
  },
  "attributes": {
    "chainId": {"type": "string", "required": true, "unique": true},
    "name": {"type": "string", "required": true},
    "description": {"type": "text"},
    
    // ✅ NUEVO: Nodes con prompts editables
    "nodes": {
      "type": "json",
      "default": [
        {
          "id": "input",
          "type": "input",
          "name": "Input"
        },
        {
          "id": "llm",
          "type": "llm",
          "name": "LLM",
          "systemPrompt": "Editable desde GUI",
          "promptTemplate": "Template con {{variables}}"
        }
      ]
    },
    
    "config": {
      "type": "json",
      "default": {
        "useMemory": true,
        "temperature": 0.7
      }
    }
  }
}
```

---

## 🎯 Prioridades de Implementación

### **Fase 1: Infraestructura** (2-3 horas)
1. ✅ Crear `agent_helpers.py` con funciones compartidas
2. ✅ Actualizar `NodeDefinition` para soportar `prompt_template`
3. ✅ Crear método `ChainDefinition.get_node(id)` helper

### **Fase 2: Refactorizar Agentes Simples** (3-4 horas)
1. ✅ Conversational (más simple)
2. ✅ Tool Agent
3. ✅ RAG Chain
4. ✅ OpenAI Web Search

### **Fase 3: Refactorizar Agentes Complejos** (4-5 horas)
1. ✅ SAP Agent
2. ✅ Code Execution Agent
3. ✅ Browser Agent
4. ✅ Orchestrator Agent

### **Fase 4: GUI Editor** (5-6 horas)
1. ✅ Actualizar `chain-editor.component.ts`
2. ✅ Editor de prompts con syntax highlighting
3. ✅ Preview de variables disponibles
4. ✅ Validación de templates

---

## 📊 Comparativa: Antes vs Después

| Característica | ANTES | DESPUÉS |
|----------------|-------|---------|
| **Prompts editables** | 0/8 agentes | 8/8 agentes ✅ |
| **Funciones duplicadas** | 3x `extract_json`, 2x `execute_tool` | 1x compartida ✅ |
| **Estructura consistente** | Cada agente diferente | Patrón estándar ✅ |
| **GUI editable** | Solo config | Config + Prompts + Nodos ✅ |
| **Documentación** | Inconsistente | Estándar claro ✅ |
| **Testing** | Difícil (prompts hardcoded) | Fácil (inyectar mocks) ✅ |

---

## 🚀 Beneficios del Estándar

1. ✅ **Editabilidad**: Usuarios pueden modificar prompts sin tocar código
2. ✅ **Mantenibilidad**: Menos duplicación, más reutilización
3. ✅ **Consistencia**: Todos los agentes siguen mismo patrón
4. ✅ **Debugging**: Más fácil entender flujo de cualquier agente
5. ✅ **Testing**: Fácil probar variantes de prompts
6. ✅ **Versionado**: Prompts en Strapi = historial de cambios

---

## 🤔 Decisiones Arquitectónicas

### ¿JSON vs Python?

**Conclusión**: **Híbrido (actual es correcto)**

- ✅ **Definición (JSON/Strapi)**: Metadata, prompts, config
- ✅ **Lógica (Python)**: Flujo, decisiones, herramientas

**Razón**: Agentes complejos (Orchestrator, Code Execution) tienen lógica que NO se puede expresar en JSON sin crear un DSL complejo.

### ¿Dónde van los prompts?

**Conclusión**: **NodeDefinition + Strapi**

```python
# Código (default)
NodeDefinition(system_prompt="Default prompt")

# Strapi (override)
{
  "nodes": [
    {"id": "llm", "systemPrompt": "Custom prompt"}
  ]
}

# Runtime (prioridad)
runtime_prompt = strapi_prompt or node.system_prompt
```

---

## ✅ Recomendación Final

**Implementar el estándar propuesto en 3 fases**:

1. **Fase 1**: Infraestructura (`agent_helpers.py`, actualizar modelos)
2. **Fase 2**: Refactorizar 4 agentes simples
3. **Fase 3**: Refactorizar 4 agentes complejos + GUI

**Tiempo estimado**: 10-15 horas total

**Valor**: 
- 🎯 Prompts editables desde GUI
- 🔧 Código más mantenible
- 📊 Base sólida para futuros agentes
