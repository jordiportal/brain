# Brain 2.0 - Roadmap de Evolución

> **Visión**: Combinar lo mejor de tres mundos - la arquitectura Docker de Brain, la organización de skills/tools de Clawdbot, y la adaptabilidad/razonamiento de Claude/Cursor.

---

## Filosofía de Diseño

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BRAIN 2.0 CORE                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   1. PENSAR SIEMPRE → Razonamiento visible antes de actuar              │
│   2. ADAPTAR        → Más o menos profundo según complejidad            │
│   3. ACTUAR         → Tools nativas universales                         │
│   4. EXTENDER       → Skills para dominios específicos (después)        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Principios

1. **Razonamiento Visible**: Siempre pensar antes de actuar, mostrando el proceso para entender el flujo
2. **Adaptabilidad**: Pensar más o menos según la complejidad de la tarea
3. **Core Minimalista**: 15 herramientas nativas universales (sin skills) para validar la inteligencia base
4. **Extensibilidad**: Skills como subagentes para dominios específicos (SAP, RAG, etc.)
5. **Medible**: Benchmark para evaluar la combinación agente/modelo

---

## Arquitectura Core

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BRAIN 2.0 CORE                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    REASONING LAYER                               │    │
│  │  think() → plan() → [actions] → reflect() → finish()            │    │
│  │            ↑_____________________↓                               │    │
│  │                  (loop adaptativo)                               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                           │
│  ┌───────────────────────────┼───────────────────────────────────────┐  │
│  │                     CORE TOOLS (15)                               │  │
│  │                                                                    │  │
│  │  Filesystem │ Execution │   Web    │ Reasoning │  Utils          │  │
│  │  ─────────  │ ───────── │ ──────── │ ───────── │ ──────          │  │
│  │  read       │ shell     │ search   │ think     │ calculate       │  │
│  │  write      │ python    │ fetch    │ reflect   │                 │  │
│  │  edit       │ javascript│          │ plan      │                 │  │
│  │  list       │           │          │ finish    │                 │  │
│  │  search     │           │          │           │                 │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                              │                                           │
│  ┌───────────────────────────┼───────────────────────────────────────┐  │
│  │                    SKILLS (Fase 2)                                │  │
│  │                                                                    │  │
│  │  [ SAP ]  [ RAG ]  [ Browser ]  [ Visualización ]  [ ... ]       │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Fase 1: Core Tools (15 herramientas nativas)

### 1.1 Filesystem (5 tools)

| Tool | Descripción | Parámetros |
|------|-------------|------------|
| `read` | Leer archivo completo o parcial | `path`, `offset?`, `limit?` |
| `write` | Crear/sobrescribir archivo | `path`, `content` |
| `edit` | Editar parte de un archivo | `path`, `old_text`, `new_text` |
| `list` | Listar directorio | `path`, `recursive?`, `pattern?` |
| `search` | Buscar archivos o contenido | `mode`, `pattern`, `path?` |

### 1.2 Execution (3 tools)

| Tool | Descripción | Parámetros |
|------|-------------|------------|
| `shell` | Ejecutar comando shell | `command`, `workdir?`, `timeout?` |
| `python` | Ejecutar código Python (Docker) | `code`, `timeout?` |
| `javascript` | Ejecutar código JS/Node (Docker) | `code`, `timeout?` |

### 1.3 Web (2 tools)

| Tool | Descripción | Parámetros |
|------|-------------|------------|
| `web_search` | Buscar en internet | `query`, `max_results?` |
| `web_fetch` | Obtener contenido de URL | `url`, `headers?` |

### 1.4 Reasoning - Meta-tools (4 tools)

| Tool | Descripción | Parámetros | Cuándo |
|------|-------------|------------|--------|
| `think` | Planificar/razonar | `thoughts` | Antes de actuar |
| `reflect` | Evaluar resultados | `observation`, `success?` | Después de resultados |
| `plan` | Crear plan estructurado | `goal`, `steps[]` | Tareas complejas |
| `finish` | Respuesta final | `answer`, `confidence?` | Al terminar |

### 1.5 Utilities (1 tool)

| Tool | Descripción | Parámetros |
|------|-------------|------------|
| `calculate` | Evaluar expresión matemática | `expression` |

### Implementación

```
services/api/src/
├── tools/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── filesystem.py      # read, write, edit, list, search
│   │   ├── execution.py       # shell, python, javascript
│   │   ├── web.py             # web_search, web_fetch
│   │   ├── reasoning.py       # think, reflect, plan, finish
│   │   └── utils.py           # calculate
│   ├── registry.py            # Tool registry actualizado
│   └── schemas.py             # JSON schemas para todas las tools
```

---

## Fase 2: Razonamiento Adaptativo

### 2.1 Detector de Complejidad

El sistema analiza la petición del usuario y determina:

| Nivel | Características | Modo de Razonamiento |
|-------|-----------------|----------------------|
| **TRIVIAL** | Respuesta directa, sin tools | `NONE` |
| **SIMPLE** | 1-2 tools, secuencial | `NONE` |
| **MODERATE** | 3-5 tools, posible ramificación | `INTERNAL` |
| **COMPLEX** | 6+ tools, múltiples fuentes | `EXTENDED` |

### 2.2 Modos de Razonamiento

#### NONE
- Sin razonamiento explícito
- Respuesta directa
- Para tareas triviales/simples

#### INTERNAL
- Razonamiento interno del modelo
- Thinking budget: 5000 tokens
- Para tareas moderadas

#### EXTENDED
- Razonamiento extendido con budget alto
- Thinking budget: 10000+ tokens
- Para tareas complejas

#### EXPLICIT (debugging)
- Meta-tools obligatorias (think/reflect)
- Trazabilidad completa
- Para auditoría/debugging

### 2.3 Flujo Adaptativo

```
                    ┌─────────────────────────┐
                    │    Query del Usuario     │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  🧠 THINK (obligatorio)  │
                    │  "¿Qué me piden?"        │
                    │  "¿Qué necesito?"        │
                    │  "¿Cómo lo hago?"        │
                    └───────────┬─────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
        ┌─────▼─────┐    ┌─────▼─────┐    ┌─────▼─────┐
        │  SIMPLE   │    │ MODERADO  │    │ COMPLEJO  │
        │           │    │           │    │           │
        │ think →   │    │ think →   │    │ plan() →  │
        │ tool →    │    │ tool →    │    │ think →   │
        │ finish    │    │ reflect → │    │ tool →    │
        │           │    │ tool →    │    │ reflect → │
        │           │    │ finish    │    │ ... →     │
        │           │    │           │    │ finish    │
        └───────────┘    └───────────┘    └───────────┘
```

### Implementación

```
services/api/src/
├── engine/
│   ├── reasoning/
│   │   ├── __init__.py
│   │   ├── complexity.py      # Detector de complejidad
│   │   ├── modes.py           # Modos de razonamiento
│   │   └── adaptive.py        # Lógica adaptativa
│   └── chains/
│       └── adaptive_agent.py  # Agente con razonamiento adaptativo
```

---

## Fase 3: Benchmark

### 3.1 Categorías de Test

| Categoría | Tests | Descripción |
|-----------|-------|-------------|
| **Reasoning** | 4 | Capacidad de pensar antes de actuar |
| **Filesystem** | 5 | Operaciones con archivos |
| **Execution** | 4 | Ejecutar comandos y código |
| **Web** | 3 | Obtener información de internet |
| **Integration** | 4 | Tareas que combinan múltiples tools |

### 3.2 Tests de Razonamiento

```python
[
    "simple_question",      # ¿Responde directamente sin tools?
    "multi_step_planning",  # ¿Planifica tareas complejas?
    "error_recovery",       # ¿Se recupera de errores?
    "ambiguity_handling",   # ¿Pide clarificación cuando es ambiguo?
]
```

### 3.3 Tests de Filesystem

```python
[
    "read_file",           # Leer archivo existente
    "write_file",          # Crear archivo nuevo
    "edit_file",           # Editar archivo existente
    "find_file",           # Encontrar archivo por patrón
    "search_content",      # Buscar texto en archivos
]
```

### 3.4 Tests de Ejecución

```python
[
    "simple_shell",        # Comando simple (ls, pwd)
    "python_calculation",  # Cálculo con Python
    "data_processing",     # Procesar datos con código
    "error_handling",      # Manejar errores de ejecución
]
```

### 3.5 Tests de Integración

```python
[
    "read_and_summarize",  # Leer archivo y resumir
    "search_and_edit",     # Buscar patrón y editar
    "fetch_and_process",   # Obtener datos web y procesar
    "complex_workflow",    # Tarea de 5+ pasos
]
```

### 3.6 Formato de Reporte

```
╔══════════════════════════════════════════════════════════════════╗
║                    BRAIN 2.0 BENCHMARK REPORT                     ║
╠══════════════════════════════════════════════════════════════════╣
║  Model:    ollama/gpt-oss:120b                                   ║
║  Provider: ollama                                                 ║
║  Date:     2026-01-26                                            ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  TOTAL SCORE: 78.5 / 100                                         ║
║                                                                   ║
╠══════════════════════════════════════════════════════════════════╣
║  CATEGORY SCORES:                                                 ║
║  ├── Razonamiento:      ████████████████████░░░░ 85%             ║
║  ├── Sistema Archivos:  ██████████████████░░░░░░ 75%             ║
║  ├── Ejecución:         ████████████████░░░░░░░░ 70%             ║
║  ├── Web:               ████████████████████░░░░ 80%             ║
║  └── Integración:       ████████████████████░░░░ 82%             ║
╚══════════════════════════════════════════════════════════════════╝
```

### Implementación

```
services/api/src/
├── benchmark/
│   ├── __init__.py
│   ├── runner.py          # Ejecutor de benchmarks
│   ├── evaluator.py       # Evaluador de resultados
│   ├── reporter.py        # Generador de reportes
│   └── tests/
│       ├── __init__.py
│       ├── reasoning.py   # Tests de razonamiento
│       ├── filesystem.py  # Tests de filesystem
│       ├── execution.py   # Tests de ejecución
│       ├── web.py         # Tests de web
│       └── integration.py # Tests de integración
```

---

## Fase 4: Skills (Subagentes)

Una vez validado el core con el benchmark, se añaden skills para dominios específicos.

### Estructura de un Skill

```
skills/
├── sap/
│   ├── SKILL.md           # Instrucciones para el agente
│   ├── config.yaml        # Configuración (endpoints, auth)
│   └── tools/
│       ├── get_orders.py
│       └── get_inventory.py
│
├── rag/
│   ├── SKILL.md
│   └── tools/
│       ├── search_docs.py
│       └── embed_document.py
│
├── browser/
│   ├── SKILL.md
│   └── tools/
│       ├── navigate.py
│       └── screenshot.py
│
└── data-viz/
    ├── SKILL.md
    └── tools/
        └── generate_chart.py
```

### Formato SKILL.md

```markdown
---
name: sap
description: "Consulta datos de SAP Business One"
metadata:
  type: "specialized"
  requires:
    env: ["SAP_BASE_URL", "SAP_API_KEY"]
  tools:
    - get_orders
    - get_inventory
---

# SAP Skill

Usa este skill para consultar datos del ERP SAP Business One.

## Capacidades
- Pedidos: Listar, filtrar por fecha/cliente
- Inventario: Stock actual, movimientos

## Limitaciones
- Máximo 1000 registros por consulta
```

---

## Plan de Implementación

### Sprint 1: Core Tools

**Objetivo**: Implementar las 15 herramientas nativas

- [ ] Filesystem tools (read, write, edit, list, search)
- [ ] Execution tools (shell, python, javascript)
- [ ] Web tools (web_search, web_fetch)
- [ ] Reasoning tools (think, reflect, plan, finish)
- [ ] Utility tools (calculate)
- [ ] Actualizar tool_registry.py
- [ ] Tests unitarios para cada tool

### Sprint 2: Razonamiento Adaptativo

**Objetivo**: Implementar el detector de complejidad y modos de razonamiento

- [ ] Detector de complejidad (complexity.py)
- [ ] Modos de razonamiento (modes.py)
- [ ] Agente adaptativo (adaptive_agent.py)
- [ ] Integración con el sistema de prompts
- [ ] Tests de razonamiento

### Sprint 3: Benchmark

**Objetivo**: Crear el sistema de benchmark para evaluar agente/modelo

- [ ] Runner de benchmarks
- [ ] Tests de todas las categorías
- [ ] Evaluador de resultados
- [ ] Generador de reportes
- [ ] CLI para ejecutar benchmarks
- [ ] Documentación de resultados

### Sprint 4: GUI Integration

**Objetivo**: Mostrar el razonamiento en la interfaz

- [ ] Componente de visualización de razonamiento
- [ ] Timeline de think/reflect/plan
- [ ] Panel de métricas en tiempo real
- [ ] Indicador de complejidad detectada

### Sprint 5: Skills (Futuro)

**Objetivo**: Sistema de skills como subagentes

- [ ] Loader de skills
- [ ] Formato SKILL.md
- [ ] Migrar agentes existentes a skills
- [ ] Tool policy por skill

---

## Comparativa: Antes vs Después

| Aspecto | Brain 1.0 | Brain 2.0 |
|---------|-----------|-----------|
| Razonamiento | Meta-tools (think/observe) | Adaptativo + visible |
| Tools | En código, monolítico | 15 core + skills modulares |
| Benchmark | No existe | Suite completa |
| Visibilidad | Logs | Timeline visual |
| Extensibilidad | Modificar código | Añadir SKILL.md |
| Complejidad | Fija | Detectada automáticamente |

---

## Métricas de Éxito

### Core Agent (sin skills)

- [ ] Benchmark score > 75% en todas las categorías
- [ ] Razonamiento visible en 100% de las respuestas
- [ ] Tiempo de respuesta < 10s para tareas simples
- [ ] Recovery de errores > 80%

### Con Skills

- [ ] Skill SAP: Consultas correctas > 95%
- [ ] Skill RAG: Relevancia > 80%
- [ ] Integración multi-skill funcional

---

## Referencias

- **Clawdbot**: Sistema de skills y tool policy
- **Claude/Cursor**: Razonamiento adaptativo y thinking blocks
- **Brain 1.0**: Arquitectura Docker y agentes especializados

---

*Documento creado: 2026-01-26*
*Última actualización: 2026-01-26*
