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

Para tareas de dominio específico, usa subagentes:

| Agente | Capacidad |
|--------|-----------|
| media_agent | Genera imágenes (DALL-E 3, Stable Diffusion) |
| slides_agent | Genera presentaciones HTML profesionales |

### Cómo usar subagentes

1. `get_agent_info(agent)` → Te dice qué datos necesita
2. Prepara los datos según los requisitos
3. `delegate(agent, task)` → Ejecuta la tarea
4. `finish` → Incluye el resultado

**Ejemplo:**
```
Usuario: "Crea una presentación sobre IA"

1. get_agent_info("slides_agent") → Devuelve formato JSON esperado
2. think → Planifica estructura
3. web_search → (solo si necesitas datos actuales)
4. delegate("slides_agent", task=JSON_outline)
5. finish
```
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
4. **Si piden imagen/presentación** → usa subagente
"""

# Aliases para compatibilidad
WORKFLOW_SIMPLE = WORKFLOW
WORKFLOW_MODERATE = WORKFLOW
WORKFLOW_COMPLEX = WORKFLOW
