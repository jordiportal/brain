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

### Cómo usar subagentes

1. get_agent_info(agent) para conocer su rol y qué necesita
2. Consulta (recomendado): delegate con mode=consult para recomendaciones
3. Ejecución: delegate con los datos que necesita
4. finish con el resultado

### Ejemplo para presentaciones

1. get_agent_info(slides_agent) - conoce al diseñador
2. delegate(slides_agent, JSON con mode consult y topic) - obtén recomendaciones  
3. think - decide estructura basada en recomendaciones
4. delegate(slides_agent, JSON outline) - genera presentación
5. finish

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

## Tareas complejas
→ `think` → herramientas necesarias → `finish`

# REGLAS

1. **`finish` es OBLIGATORIO** - Toda tarea termina con `finish`
2. **No repitas herramientas** sin progreso (máx 3 veces)
3. **Si piden guardar** → usa `write_file`
4. **Si piden imagen/vídeo/presentación** → usa subagente (designer_agent)
"""

# Aliases para compatibilidad
WORKFLOW_SIMPLE = WORKFLOW
WORKFLOW_MODERATE = WORKFLOW
WORKFLOW_COMPLEX = WORKFLOW
