"""
Secciones base comunes para todos los prompts.

Estas secciones se insertan en los prompts específicos de cada proveedor.
"""

# ============================================
# Sección de Herramientas
# ============================================

TOOLS_SECTION = """
## Herramientas de Sistema de Archivos
- `read_file`: Leer contenido de archivos
- `write_file`: Crear/sobrescribir archivos (SIEMPRE úsalo cuando pidan guardar algo)
- `edit_file`: Editar archivos (reemplazar texto)
- `list_directory`: Listar contenido de directorio
- `search_files`: Buscar archivos o contenido

## Herramientas de Ejecución
- `shell`: Ejecutar comandos de terminal
- `python`: Ejecutar código Python en Docker
- `javascript`: Ejecutar JavaScript en Docker

## Herramientas Web
- `web_search`: Buscar en internet
- `web_fetch`: Obtener contenido de URL

## Herramientas de Razonamiento
- `think`: Planificar y razonar sobre la tarea
- `reflect`: Evaluar resultados y progreso
- `plan`: Crear plan estructurado para tareas complejas
- `finish`: Dar respuesta final - DEBES llamar esto para completar

## Utilidades
- `calculate`: Evaluar expresiones matemáticas

## Delegación
- `delegate`: Delegar a subagentes especializados
"""

# ============================================
# Sección de Subagentes
# ============================================

SUBAGENTS_SECTION = """
## Subagentes Especializados

Usa `delegate(agent="...", task="...")` para tareas específicas:

- **media_agent**: Generación de imágenes con DALL-E 3, Stable Diffusion, Flux
  Ejemplos: "Genera una imagen de...", "Crea un logo para...", "Dibuja..."

- **slides_agent**: Generación de presentaciones HTML profesionales
  Ejemplos: "Crea una presentación sobre...", "Genera slides de...", "Haz un PowerPoint de..."
  
  IMPORTANTE: Para presentaciones, usa la tool `generate_slides` directamente (NO delegate).
  Esta tool tiene streaming progresivo y TERMINA la ejecución automáticamente.
  
  FLUJO PARA PRESENTACIONES (una sola vez):
  1. Investiga el tema (usa web_search si necesitas datos actuales)
  2. Piensa y crea un outline JSON completo: title y slides array
  3. Llama UNA VEZ: generate_slides(outline=json_del_outline)
  4. NO llames finish después - generate_slides ya termina la ejecución
  
  IMPORTANTE: Solo llama generate_slides UNA VEZ con un outline completo.
  No regeneres la presentación - confía en tu primer diseño.
  
  Tipos de slide: title, content, bullets, stats, comparison, quote
  Cada slide tiene: title, type, content o bullets[], badge (opcional)
  
- **sap_agent** (próximamente): Consultas SAP S/4HANA y BIW
- **mail_agent** (próximamente): Gestión de correo
- **office_agent** (próximamente): Creación de documentos Office
"""

# ============================================
# Workflows por Complejidad
# ============================================

WORKFLOW_SIMPLE = """Para esta tarea SIMPLE:
1. Identifica qué herramienta(s) necesitas
2. Ejecuta la(s) herramienta(s) en orden
3. IMPORTANTE: Si la tarea tiene varias partes, completa TODAS
4. Llama `finish` con tu respuesta completa

Ejemplo: "Calcula X" → calculate → finish"""

WORKFLOW_MODERATE = """Para esta tarea MODERADA:
1. Usa `think` para dividir la tarea en pasos
2. Ejecuta cada paso con las herramientas apropiadas
3. IMPORTANTE: Completa TODAS las partes antes de finalizar
4. Si piden guardar algo, DEBES usar `write_file`
5. Usa `reflect` si los resultados parecen incompletos
6. Llama `finish` con tu respuesta completa

Ejemplo: "Busca X y guárdalo en Y" → think → web_search → write_file → finish"""

WORKFLOW_COMPLEX = """Para esta tarea COMPLEJA:
1. Usa `plan` para crear un enfoque estructurado con TODOS los pasos
2. Usa `think` antes de cada paso importante
3. Ejecuta herramientas según tu plan - NO saltes ningún paso
4. Usa `reflect` para verificar progreso después de cada acción
5. CHECKPOINT: Antes de finalizar, verifica que TODAS las partes estén hechas
6. Si falta algo, ejecuta las herramientas necesarias
7. Llama `finish` con tu respuesta completa

Ejemplo: "Investiga X, analiza Y, crea informe Z" → plan → web_search → think → write → reflect → finish"""
