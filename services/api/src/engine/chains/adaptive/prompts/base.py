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
  
FLUJO PARA TAREAS DE SUBAGENTES:
1. Si necesitas información actual, primero usa web_search
2. Piensa en qué información darle al subagente
3. Llama `delegate(agent="media_agent|slides_agent", task="descripción detallada")`
4. Después de delegate, llama `finish` con el resultado

Ejemplo imágenes: delegate(agent="media_agent", task="Genera una imagen de un gato astronauta") → finish
Ejemplo presentaciones: delegate(agent="slides_agent", task="Crea presentación sobre IA: 5 slides, incluye historia, aplicaciones y futuro") → finish

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
