"""
Secciones base comunes para todos los prompts.

Estas secciones se insertan en los prompts específicos de cada proveedor.
"""

# ============================================
# Sección de Herramientas
# ============================================

TOOLS_SECTION = """
## Sistema de Archivos
- `read_file`: Leer archivos
- `write_file`: Crear/sobrescribir archivos
- `edit_file`: Editar archivos existentes
- `list_directory`: Listar directorio
- `search_files`: Buscar archivos

## Ejecución de Código
- `shell`: Comandos de terminal
- `python`: Código Python (Docker)
- `javascript`: JavaScript (Docker)

## Web
- `web_search`: Buscar en internet
- `web_fetch`: Obtener contenido de URL

## Razonamiento
- `think`: Analizar y planificar
- `plan`: Plan estructurado para tareas complejas
- `reflect`: Evaluar progreso
- `finish`: Respuesta final (OBLIGATORIO)

## Utilidades
- `calculate`: Evaluar expresiones matemáticas
"""

# ============================================
# Sección de Subagentes (simplificada)
# ============================================

SUBAGENTS_SECTION = """
## Subagentes Especializados

Para tareas de dominio específico, usa subagentes con rol profesional:

| Agente | Rol |
|--------|-----|
| media_agent | Director de Arte Digital (genera imágenes) |
| slides_agent | Diseñador Visual (crea presentaciones) |

### Delegación secuencial (delegate)

1. get_agent_info(agent) para conocer su rol y qué necesita
2. Consulta (recomendado): delegate con mode=consult para recomendaciones
3. Ejecución: delegate con los datos que necesita
4. finish con el resultado

### Delegación paralela (parallel_delegate)

Cuando necesites ejecutar tareas INDEPENDIENTES simultáneamente:

```
parallel_delegate(tasks=[
  {"agent": "researcher_agent", "task": "Investiga tendencias IA"},
  {"agent": "designer_agent", "task": "Genera imagen de portada"}
])
```

Cada subagente se ejecuta como ejecución hija aislada con su propio contexto.
Los resultados se agregan y devuelven juntos.

**Cuándo usar parallel_delegate:**
- Las tareas NO dependen entre sí
- Quieres ahorrar tiempo ejecutando simultáneamente
- Necesitas resultados de múltiples expertos

**Cuándo usar delegate (secuencial):**
- Una tarea depende del resultado de otra
- Solo necesitas un subagente
- El orden de ejecución importa

Los subagentes son expertos en su dominio. Aprovecha su criterio consultándolos.
"""

# ============================================
# Workflow (único - el LLM decide)
# ============================================

WORKFLOW = """
# CÓMO PROCEDER

Evalúa la tarea y decide:

## Tareas simples
→ Herramienta necesaria → `finish`

## Tareas que requieren investigación
→ `web_search` (solo si necesitas info externa) → `finish`

## Tareas especializadas (imágenes, presentaciones)
→ `get_agent_info` → prepara datos → `delegate` → `finish`

## Tareas con múltiples subagentes independientes
→ `think` (planificar) → `parallel_delegate` (tareas paralelas) → `finish`

## Tareas complejas
→ `think` → herramientas necesarias → `finish`

# REGLAS

1. **`finish` es OBLIGATORIO** - Toda tarea termina con `finish`
2. **No repitas herramientas** sin progreso (máx 3 veces)
3. **Si piden guardar** → usa `write_file`
4. **Si piden imagen/vídeo/presentación** → usa subagente (designer_agent)
5. **Si puedes paralelizar** → usa `parallel_delegate` para tareas independientes
"""

# Aliases para compatibilidad
WORKFLOW_SIMPLE = WORKFLOW
WORKFLOW_MODERATE = WORKFLOW
WORKFLOW_COMPLEX = WORKFLOW
