# Comparativa: Arquitectura Swarm OSS vs Brain actual

Comparación entre el diseño propuesto en *Arquitectura de Orquestación Multi-Agente (Swarm OSS)* y la arquitectura actual de Brain.

---

## 1. Resumen ejecutivo

| Aspecto | Brain actual | Swarm OSS (propuesto) |
|--------|---------------|------------------------|
| **Quién orquesta** | El LLM (decide paso a paso qué tool usar) | El sistema (DAG + colas; el LLM ejecuta tareas acotadas) |
| **Stack API** | FastAPI (Python) | Fastify (Node.js) |
| **Colas** | Redis (cache, pub/sub; no colas de jobs) | BullMQ + Redis (colas por tipo de worker) |
| **Planificación** | Emergente (el agente “piensa” y actúa en loop) | Determinista (Planner → blueprint → DAG → workers) |
| **Modelo de agentes** | 1–2 cadenas (adaptive, team) con muchas tools | Roles estables, agentes efímeros, muchos en paralelo |
| **Paralelismo** | Secuencial (una ejecución = un agente que itera) | Paralelo por diseño (nodos del DAG en colas distintas) |

---

## 2. Diferencias principales

### 2.1 Dónde vive la “inteligencia” del flujo

**Brain actual**

- El **LLM orquesta**: en cada paso el modelo elige la siguiente tool, hace think/reflect/plan y puede delegar.
- LangGraph/LangChain definen el *tipo* de flujo (loop agente con tools), pero **qué se hace en cada paso lo decide el LLM**.
- Ventaja: muy flexible para preguntas abiertas y tareas no predefinidas.
- Riesgo: coste y latencia menos predecibles, más dependiente del criterio del modelo.

**Swarm OSS**

- La **arquitectura orquesta**: un Planner (con algo de LLM corto para intención) elige un *blueprint*, se expande a un **DAG fijo** y las tareas se encolan en BullMQ.
- El LLM se usa como **worker** (llm-short, llm-long) en nodos concretos, no como cerebro del flujo.
- Ventaja: control de costes, plazos y paralelismo; “el swarm vive en la arquitectura”.
- Riesgo: menos adecuado para preguntas muy abiertas o flujos no contemplados en blueprints.

---

### 2.2 Planificación: emergente vs determinista

**Brain actual**

- **Plan emergente**: el agente usa tools `think`, `plan`, `reflect`; el “plan” es el recorrido que hace el LLM en tiempo de ejecución.
- No hay catálogo fijo de tareas ni blueprints: las “tareas” son las invocaciones a tools que el agente decide.
- Adecuado para: asistente general, coding, exploración, preguntas variadas.

**Swarm OSS**

- **Plan determinista** en 3 capas:
  1. **Catálogo de tareas** finito (ej. `validate_gl`, `compute_pnl`, `write_section`).
  2. **Blueprints** (ej. `financial_report_monthly_v1`) que encadenan tareas en un orden dado.
  3. **Reglas/guardrails** que mapean intención → blueprint y parametrizan (periodo, comparaciones, etc.).
- El DAG se construye sin LLM (o con uso mínimo); luego se ejecuta en workers.
- Adecuado para: informes recurrentes, pipelines de datos, documentación con estructura conocida.

---

### 2.3 Rol / Agente / Instancia

**Brain actual**

- **Cadenas** (adaptive, team) con un conjunto grande de **tools** (filesystem, web, execution, reasoning, delegate).
- “Subagentes” (slides, analyst, etc.) existen como destinos de la tool `delegate`; no hay modelo explícito Rol/Agente/Instancia.
- Una ejecución = una cadena que itera (agente único o equipo con consenso) hasta `finish`.

**Swarm OSS**

- **Rol** = especialización estable (DataAnalyst, ReportWriter, CodeBuilder, Verifier).
- **Agente** = un rol aplicado a una tarea concreta (ej. ReportWriter para sección P&L).
- **Instancia** = una llamada al modelo (una tarea en una cola).
- “Un rol puede tener muchos agentes en paralelo; cada agente tiene un solo rol.”

---

### 2.4 Ejecución: secuencial vs colas y workers

**Brain actual**

- Una petición → una ejecución → **un proceso secuencial**: LLM → tool → LLM → tool … hasta finish.
- Redis se usa para cache y pub/sub, **no** como cola de jobs con workers separados.
- Workers “externos”: browser, code-runners (Python/JS), pero orquestados desde el mismo flujo del agente.

**Swarm OSS**

- Una petición → Planner → **DAG** → nodos del DAG se encolan en **BullMQ**.
- **Colas por tipo**: cpu-analytics, llm-short, llm-long, render, con concurrencia definida por cola.
- Postgres mantiene el estado; BullMQ ejecuta; “BullMQ ejecuta, Postgres decide”.

---

### 2.5 Evidencia y anti-alucinaciones

**Brain actual**

- No hay contrato explícito “claim + evidence” en el modelo de datos.
- La calidad depende del prompt (reasoning, reflect) y del modelo; no hay capa que fuerce evidencias por insight.

**Swarm OSS**

- **Contrato de evidencia**: cada insight con métricas explícitas (claim + evidence con metric, period, value).
- El “redactor” solo convierte a prosa; los datos vienen de tareas anteriores (cálculo, validación).

---

### 2.6 Stack técnico

| Componente | Brain actual | Swarm OSS |
|------------|--------------|-----------|
| API | FastAPI (Python) | Fastify (Node.js) |
| BD | PostgreSQL + pgvector | PostgreSQL |
| Colas | Redis (cache/pub-sub) | BullMQ + Redis |
| Orquestación lógica | LangChain / LangGraph | Planner + DAG (propio) |
| Workers | Implícitos en API + code-runners, browser | Explícitos: cpu, llm-short, llm-long, render |
| Artifacts | RAG (pgvector), workspace | Artifacts store (filesystem / MinIO-S3) |

---

## 3. Ventajas y desventajas

### 3.1 Brain actual

**Ventajas**

- **Flexibilidad**: sirve para preguntas abiertas, coding, búsqueda, análisis ad hoc sin definir blueprints.
- **Un solo stack Python** para API y lógica de agentes (FastAPI + LangChain/LangGraph).
- **Razonamiento visible**: think/reflect/plan permiten inspeccionar el proceso.
- **Menos piezas**: no hace falta definir DAGs ni catálogos de tareas para empezar.
- **RAG y tools ricas**: pgvector, filesystem, web, execution, delegate ya integrados.

**Desventajas**

- **Coste y latencia** menos predecibles (muchas llamadas al LLM por ejecución).
- **Paralelismo limitado**: una ejecución es fundamentalmente secuencial.
- **Control de presupuesto** más difícil (no hay “budgets por run” ni colas por tipo).
- **Riesgo de deriva**: el modelo puede dar más vueltas de las necesarias si no se acota bien.

---

### 3.2 Swarm OSS (propuesto)

**Ventajas**

- **Control**: DAGs, colas y workers permiten presupuestos, tiempos máximos y priorización.
- **Paralelismo**: nodos independientes del DAG se ejecutan en paralelo en distintas colas.
- **Predecibilidad**: flujos acotados (informes, pipelines) con pasos bien definidos.
- **Evidencia**: contrato claim/evidence reduce alucinaciones en salidas analíticas.
- **Escalabilidad**: workers por tipo (CPU, LLM corto/largo, render) escalables por cola.
- **Enterprise**: BullMQ + Postgres + Fastify encaja bien en entornos controlados.

**Desventajas**

- **Poco adecuado para “asistente general”**: si la tarea no está en un blueprint, el sistema no la modela.
- **Mantenimiento de blueprints**: hay que definir y mantener catálogos y plantillas.
- **Stack Node + workers**: más componentes (Fastify, BullMQ, varios workers) que un monolito Brain.
- **Menos “magia” en el LLM**: la creatividad del flujo está en el diseño del DAG, no en el modelo.

---

## 4. Posibles híbridos (Brain + ideas Swarm)

Sin sustituir Brain, se podrían incorporar ideas del documento Swarm:

1. **Colas por tipo de tarea**  
   Usar Redis/BullMQ (o similar) para tareas pesadas (ej. “generar informe”, “reindexar RAG”) y dejar el chat/agente en tiempo real como ahora.

2. **Blueprints opcionales**  
   Para flujos recurrentes (informe mensual, documentación de repo), un “modo pipeline” que construya un min-DAG (validar → calcular → redactar) y lo ejecute con workers, manteniendo el agente libre para el resto.

3. **Contrato de evidencia en salidas analíticas**  
   En cadenas o tools que devuelvan “insights”, exigir estructura `claim` + `evidence` (métricas, periodo) antes de pasarlos a redacción.

4. **Rol/Agente en Brain**  
   Formalizar subagentes (slides, analyst, etc.) como “roles” con un solo rol por agente y varias instancias en paralelo cuando se deleguen varias tareas.

5. **Planner ligero**  
   Una capa previa (una llamada LLM corta o reglas) que clasifique intención y, si aplica, inyecte un “plan sugerido” (steps) al agente actual en lugar de dejar todo al loop desde cero.

---

## 5. Conclusión

- **Brain** está orientado a **agente conversacional y flexible** (asistente, código, exploración), con orquestación dentro del LLM y herramientas ricas.
- **Swarm OSS** está orientado a **pipelines predefinidos y controlados** (informes, análisis, documentación), con orquestación en la arquitectura (DAG + colas) y el LLM como worker.

No son excluyentes: Brain puede seguir siendo el núcleo para interacción abierta y, en paralelo, añadir un “modo swarm” para flujos repetitivos con DAGs, colas y contrato de evidencia, compartiendo Postgres y Redis donde tenga sentido.
