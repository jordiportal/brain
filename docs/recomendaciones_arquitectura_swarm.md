# Recomendaciones de arquitectura (con vista a agente Swarm)

Documento corto: qué cambiar **ahora** en la arquitectura de Brain para que un futuro agente Swarm encaje sin rehacer todo.

---

## 1. Conclusión rápida

**No hace falta cambiar el diseño actual.** La arquitectura es compatible con añadir un "agente Swarm" como una cadena más. Los ajustes recomendados son **pequeños y sobre todo de claridad/documentación**, no de reescritura.

---

## 2. Cambios que sí vale la pena hacer

### 2.1 Redis: dejar claro el rol (cache hoy, colas mañana)

**Situación:** Redis está en el stack pero casi no se usa (health check, config).

**Recomendación:**

- **Ahora:** Documentar en `docs/architecture.md` que Redis se usa para:
  - Cache (cuando se implemente).
  - Pub/Sub para WebSockets si aplica.
  - **Futuro:** colas de jobs para tareas asíncronas y/o agente Swarm (BullMQ, RQ o Celery).
- **Código:** No hace falta usar Redis en más sitios por ahora; con que el health check y la URL en config sigan sirviendo basta.
- **Beneficio:** Cuando añadas Swarm, Redis ya está; solo añades un consumer de colas (workers).

---

### 2.2 Celery: quitar o documentar

**Situación:** Celery está en `requirements.txt` pero no se usa en el código.

**Recomendación:**

- **Opción A (recomendada):** Quitar Celery de `requirements.txt` para no arrastrar dependencia muerta. Si más adelante quieres workers en Python, puedes volver a añadir Celery o usar RQ/ARQ (más ligeros).
- **Opción B:** Dejar Celery y añadir en el README o en architecture: "Reservado para futuros workers (p. ej. agente Swarm)".

---

### 2.3 Cadenas: ya está listo para Swarm

**Situación:** Tienes `chain_registry` y `register_all_chains()`; las cadenas (adaptive, team) se registran con un builder.

**Recomendación:** No tocar. Un futuro "agente Swarm" sería:

- Una nueva cadena registrada (ej. `id="swarm"`, `type="swarm"` o `type="agent"`).
- Un builder que en lugar de hacer loop LLM→tools use un Planner + DAG y encole tareas en Redis (BullMQ/RQ/Celery).

La API y el GUI ya exponen "cadenas"; Swarm sería una más. Nada que refactorizar a nivel arquitectura.

---

### 2.4 Ejecuciones y trazabilidad

**Situación:** Existen `brain_executions` y `brain_execution_traces`; el Swarm OSS habla de "trazabilidad artifact ← tarea ← run".

**Recomendación:**

- **Ahora:** Dejar el modelo como está.
- **Documentar** que una "ejecución" en Brain equivale a un "run" en Swarm, y que los traces son los pasos (equivalentes a tareas del DAG). Si en el futuro Swarm genera "artifacts" (archivos, informes), se pueden guardar por `execution_id` en el workspace o en una tabla `brain_artifacts` cuando toque.
- No hace falta nueva tabla ni nuevos campos por ahora; solo tener claro el mapeo conceptual.

---

### 2.5 Stack (Python vs Node)

**Situación:** El diseño Swarm OSS usa Fastify (Node); Brain usa FastAPI (Python).

**Recomendación:** Mantener todo en Python. Un orquestador Swarm puede ser:

- Un módulo Python que construya DAGs y encole jobs en Redis.
- Workers en Python (Celery/RQ/ARQ) o, si quisieras, un worker Node que solo ejecute un tipo de tarea.

No compensa reescribir la API en Node solo por Swarm; el agente Swarm puede ser "una cadena más" en la misma API.

---

## 3. Cambios que no recomiendo ahora

- **Introducir BullMQ/DAG/Planner ya:** Overkill hasta que definas el agente Swarm.
- **Separar workers en otro proceso/servicio:** Solo cuando tengas tareas claramente asíncronas (informes largos, pipelines batch).
- **Nueva tabla de artifacts:** Posponer hasta que Swarm genere artefactos que quieras versionar/recuperar.
- **Cambiar de PostgreSQL:** No; Postgres ya es la "verdad del sistema" y encaja con Swarm.

---

## 4. Resumen de acciones concretas

| Acción | Prioridad | Esfuerzo |
|--------|-----------|----------|
| Documentar en `architecture.md` el rol de Redis (cache + futuro colas) | Alta | Bajo |
| Quitar Celery de `requirements.txt` o documentar "reservado para Swarm" | Media | Bajo |
| Añadir en `architecture.md` una subsección "Futuro: agente Swarm" (1 párrafo) | Alta | Bajo |
| Dejar explícito en comparativa que Swarm será "una cadena más" | Hecho | - |

---

## 5. Párrafo sugerido para `architecture.md`

Texto que puedes pegar en la sección de Redis o en "Escalabilidad / Futuro":

```markdown
### Futuro: agente Swarm

Se prevé añadir un agente de tipo "Swarm" (orquestación multi-agente con DAG y colas)
como una cadena más en el registry. Redis está previsto para soportar colas de jobs
(BullMQ, RQ o Celery); la API y el modelo de ejecuciones actuales permiten integrar
dicho agente sin cambios estructurales.
```

---

Con estos pequeños ajustes, la arquitectura queda clara y preparada para un agente Swarm futuro sin hacer cambios grandes ahora.
