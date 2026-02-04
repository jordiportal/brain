# Team vía LLM: consenso con herramientas de cognición

Objetivo: que el **consenso lo haga el LLM** usando think / reflect / plan (y finish), no el código fijo de ConsensusEngine.

---

## Situación actual (ya implementado)

- **Team** = build_team_coordinator que usa AdaptiveExecutor con tools: think, reflect, plan, finish, get_agent_info, consult_team_member.
- ConsensusEngine y TeamCoordinator fueron **eliminados**; el consenso lo hace el LLM en un único bucle.

## Objetivo (logrado)

- El **mismo trabajo** (seleccionar equipo, recoger propuestas, alcanzar consenso, síntesis) lo hace un **LLM en un bucle con tools**.
- Tools mínimas: **cognición** (think, reflect, plan, finish) + **consulta a subagentes** (consult_team_member).
- Sin ConsensusEngine: el “consenso” es el razonamiento del LLM sobre las respuestas de los subagentes.

---

## Diseño propuesto

### Flujo

1. **Selección de equipo**: se puede dejar en código (rápido, estable) o convertirlo en una primera llamada LLM con tool `list_team_members` + think. Por simplicidad, opción A: mantener selección en código (como ahora). Opción B: el propio agente recibe la tarea y usa think + consult_team_member por quien quiera.
2. **Consenso vía LLM**:
   - Un único agente “coordinador” que tiene solo estas tools:
     - **think**, **reflect**, **plan**, **finish**
     - **consult_team_member**(agent_id, task) → devuelve la propuesta/respuesta de ese subagente para la tarea (sin ejecutar la tarea final; solo “opina”).
   - System prompt: “Eres un coordinador de equipo. Tu objetivo es alcanzar consenso. Usa think para planificar a quién preguntar y cómo sintetizar; consult_team_member para obtener la opinión de cada miembro; reflect para valorar coincidencias y conflictos; plan para decidir si pides aclaraciones o pasas a síntesis; finish cuando tengas la respuesta consensuada.”
   - El LLM itera: think → consult_team_member(A) → consult_team_member(B) → reflect → quizá consult again o plan → finish con la respuesta fusionada.
3. **Ejecución final** (opcional): si se quiere “un agente líder ejecuta”, se puede dejar como una tool más `execute_with_lead_agent(agent_id, brief)` que internamente llame al subagente con el brief, o que el finish ya incluya “quién hace qué” y una segunda fase lo ejecute. Por ahora podemos dejar que finish devuelva la respuesta consensuada y la ejecución sea opcional o posterior.

### Ventajas

- Consenso y síntesis **hechos por el LLM**, no por reglas fijas.
- Uso explícito de **think / reflect / plan** (y finish), alineado con Adaptive.
- Un solo bucle “agente con tools”; Team sería un **Adaptive con tools restringidas** (cognición + consult_team_member).
- Más flexible: el modelo puede pedir aclaraciones, más rondas, o sintetizar cuando considere que hay suficiente acuerdo.

### Implementación mínima

1. **Nueva tool** `consult_team_member`(agent_id: str, task: str) → llama al subagente en modo “consulta” (solo propuesta, sin ejecutar tarea pesada) y devuelve texto/estructura para el LLM.
2. **Team como cadena tipo Adaptive**:
   - Mismo esquema que Adaptive: builder que prepara prompt + tools y delega en **AdaptiveExecutor** (o un executor compartido).
   - Tools para esta cadena: think, reflect, plan, finish, consult_team_member (y list_team_members si se quiere que elija el equipo el LLM).
   - System prompt específico para “coordinador que busca consenso”.
3. **Eliminar** ConsensusEngine en el flujo Team: **hecho**; el archivo consensus.py y la clase TeamCoordinator se eliminaron.

### Comparativa rápida

| Aspecto | Antes (Team actual) | Después (Team vía LLM) |
|--------|----------------------|-------------------------|
| Consenso | Código (ConsensusEngine) | LLM con think/reflect/plan |
| Rondas | Fijas (max_rounds) | Las que decida el LLM |
| Merge | _merge_proposals (código) | LLM sintetiza en finish |
| Tools usadas | Ninguna de cognición | think, reflect, plan, finish + consult_team_member |

---

Si te encaja este diseño, el siguiente paso es implementar `consult_team_member` y el builder de Team que use AdaptiveExecutor con ese conjunto de tools y el prompt de coordinador.
