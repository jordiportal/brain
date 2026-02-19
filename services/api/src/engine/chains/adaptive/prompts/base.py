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
# Sección de Subagentes (dinámica desde registry)
# ============================================

def get_subagents_section() -> str:
    from src.engine.chains.agents.base import subagent_registry
    agents = subagent_registry.list()
    if not agents:
        return ""
    lines = ["## SUBAGENTES DISPONIBLES\n\nPuedes delegar tareas a estos especialistas usando `delegate(agent, task, context)`:\n"]
    for a in agents:
        lines.append(f"- **{a.id}**: {a.description}")
        if a.expertise:
            lines.append(f"  Expertise: {a.expertise}")
    return "\n".join(lines)

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
5. **Si piden ventas, P&L, datos SAP, BIW o análisis de negocio** → delega a sap_analyst
6. **Si puedes paralelizar** → usa `parallel_delegate` para tareas independientes
"""

# Aliases para compatibilidad
WORKFLOW_SIMPLE = WORKFLOW
WORKFLOW_MODERATE = WORKFLOW
WORKFLOW_COMPLEX = WORKFLOW
