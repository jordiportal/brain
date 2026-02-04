# Comparativa: Brain 2.0 Adaptive Agent vs Brain Team

Comparación de los dos agentes actuales de Brain.

---

## 1. Resumen rápido

| Aspecto | Brain 2.0 Adaptive Agent | Brain Team |
|--------|----------------------------|------------|
| **ID** | `adaptive` | `team` |
| **Modelo** | Un agente que itera (LLM + tools) | Varios subagentes + coordinador + consenso |
| **Flujo** | Detección complejidad → loop LLM→tools hasta finish | Loop LLM coordinador con tools cognición + consult_team_member hasta finish |
| **Tools** | 17 core tools (filesystem, web, execution, reasoning, delegate) | think, reflect, plan, finish, get_agent_info, consult_team_member |
| **Subagentes** | Opcionales vía tool `delegate` | Consultados vía `consult_team_member` (el LLM elige a quién preguntar) |
| **Razonamiento** | think / reflect / plan / finish (adaptativo por complejidad) | think / reflect / plan / finish (consenso dirigido por LLM) |
| **Config** | temperature 0.5, max_memory 10, max_iterations por reasoning | temperature 0.7, max_iterations 10, timeout 300 s |
| **Uso típico** | Tarea abierta, una respuesta, rápido | Tarea compleja, varias perspectivas, respuesta elaborada |

---

## 2. Brain 2.0 Adaptive Agent

### Qué es

Un **solo agente** que en cada iteración: recibe mensajes, el LLM elige si llamar a una tool o dar la respuesta final. Loop hasta `finish` o límite de iteraciones.

### Flujo

1. **Análisis de complejidad** (sin LLM pesado): se clasifica la query (trivial → complex) y se elige modo de razonamiento.
2. **Preparación**: system prompt por proveedor, carga de core tools, construcción de mensajes (memoria + query).
3. **Loop (AdaptiveExecutor)**:
   - Llamada al LLM con tools.
   - Si el LLM pide una tool → se ejecuta (handler) → resultado se añade a mensajes → siguiente iteración.
   - Si el LLM llama a `finish` → se devuelve la respuesta y se termina.
4. **Límites**: máximo de iteraciones (ampliable con “continuar”), opción de preguntar antes de seguir.

### Componentes

- **agent.py**: definición de cadena, `build_adaptive_agent` (complejidad → executor).
- **executor.py**: loop LLM ↔ tools, detección de bucles, emisión de eventos.
- **handlers/**: un handler por tool (filesystem, web, reasoning, delegate, etc.).
- **reasoning/**: complejidad y modos de razonamiento.
- **tools**: registry de core tools (17).

### Cuándo usarlo

- Preguntas abiertas, coding, búsqueda, análisis ad hoc.
- Cuando quieres **una** respuesta coherente y relativamente rápida.
- Cuando la tarea no requiere varias “voces” ni debate explícito.

---

## 3. Brain Team

### Qué es

Un **coordinador LLM** que usa AdaptiveExecutor con herramientas de cognición (think, reflect, plan) y `consult_team_member` para pedir opiniones a los expertos; el consenso lo construye el propio LLM y responde con `finish`.

### Flujo

1. **Loop único (AdaptiveExecutor)**:
   - System prompt de coordinador + memoria + query.
   - Tools: think, reflect, plan, finish, get_agent_info, consult_team_member.
   - El LLM decide a quién consultar, cuándo reflexionar y cuándo dar la respuesta final con finish.
2. No hay fases fijas (selección → consenso → ejecución); todo lo orquesta el LLM en el mismo bucle.

### Componentes

- **coordinator.py**: `build_team_coordinator` (prepara mensajes + tools y delega en AdaptiveExecutor).
- **prompts.py**: `COORDINATOR_SYSTEM_PROMPT`.
- **agents/** (subagentes): slides, media, communication, analyst; se consultan vía `consult_team_member`.

### Cuándo usarlo

- Tareas que se benefician de **varias perspectivas** (ej. presentación + narrativa + datos).
- Cuando quieres una respuesta **elaborada** y no importa gastar más tiempo y tokens.
- Cuando la tarea encaja con los roles de los subagentes (presentaciones, imágenes, comunicación, análisis).

---

## 4. Diferencias técnicas

### Orquestación

- **Adaptive**: el LLM es el orquestador; en cada paso decide la siguiente tool (o finish). No hay “equipo” previo.
- **Team**: el LLM coordinador es el orquestador (mismo AdaptiveExecutor); usa think/reflect/plan y consult_team_member para alcanzar consenso y responde con finish.

### Uso del LLM

- **Adaptive**: muchas llamadas al mismo modelo en secuencia (una por iteración del loop).
- **Team**: mismo patrón (loop con tools); el coordinador consulta a subagentes vía consult_team_member y sintetiza con think/reflect/plan/finish.

### Tools

- **Adaptive**: usa core tools (read_file, web_search, delegate, etc.); puede delegar en un subagente vía `delegate` cuando convenga.
- **Team**: solo cognición + get_agent_info + consult_team_member; los subagentes se consultan (no se ejecuta la tarea completa salvo que el usuario pida algo ejecutable en la respuesta).

### Configuración

| Parámetro | Adaptive | Team |
|-----------|-----------|------|
| temperature | 0.5 | 0.7 |
| max_iterations | Por reasoning (ej. 5–20) | 10 |
| timeout | No explícito | 300 s |
| max_memory_messages | 10 | No usado en coordinator |
| ask_before_continue | Sí (opcional) | No |

---

## 5. Cuándo usar cada uno

- **Adaptive**: tarea única, respuesta directa, uso intensivo de tools (archivos, web, código), o cuando quieres que un solo agente “piense y actúe” con razonamiento visible.
- **Team**: tarea que pide **colaboración** (varias especialidades), resultado más elaborado y no importa más latencia ni más tokens (ej. “hazme una presentación con análisis y narrativa”).

---

## 6. Resumen en una frase

- **Adaptive**: un agente con muchas tools que itera hasta terminar.
- **Team**: un coordinador LLM que consulta a expertos (consult_team_member) y sintetiza con think/reflect/plan hasta finish.
