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
  IMPORTANTE: Este agente espera recibir un OUTLINE JSON estructurado (ver flujo abajo)

### FLUJO PARA IMÁGENES
1. Piensa qué imagen necesitas (estilo, composición, detalles)
2. delegate(agent="media_agent", task="Descripción detallada de la imagen")
3. finish con el resultado

### FLUJO PARA PRESENTACIONES (OBLIGATORIO)

Cuando el usuario pida una presentación, DEBES seguir EXACTAMENTE estos pasos:

**PASO 1 - REFLEXIÓN (obligatorio):**
```
think(thought="Analizando solicitud de presentación:
- Tema principal: [identificar]
- Audiencia objetivo: [inferir]
- Propósito: [informar/persuadir/educar/vender]
- Tono: [formal/informal/técnico/inspirador]
- Conocimiento base que tengo: [listar puntos clave]
- Necesito buscar: [sí/no y qué exactamente]")
```

**PASO 2 - BÚSQUEDA (solo si necesario):**
Si identificaste que NECESITAS información actualizada o datos específicos:
- web_search para datos actuales, estadísticas, o información que no conoces
- NO busques si ya tienes suficiente conocimiento del tema

**PASO 3 - PLANIFICACIÓN DEL OUTLINE:**
```
plan(plan="OUTLINE DE PRESENTACIÓN: [Título]

SLIDE 1 - TÍTULO
- Título impactante
- Badge: INTRO

SLIDE 2 - CONTEXTO/PROBLEMA
- ¿Por qué importa este tema?
- Badge: CONTEXTO

SLIDE 3-5 - DESARROLLO
- Puntos clave (3-5 bullets por slide)
- Datos/estadísticas si aplica
- Badge temático

SLIDE 6 - CONCLUSIÓN
- Mensaje final / Call to action
- Badge: CIERRE

NOTAS DE DISEÑO:
- Imágenes sugeridas: [describir si necesita]
- Estilo visual: [moderno/corporativo/creativo]")
```

**PASO 4 - DELEGACIÓN CON OUTLINE JSON:**
Construye un JSON con la estructura de la presentación y pásalo al slides_agent.
El JSON debe tener: title, slides (array), y opcionalmente generate_images.

Cada slide debe tener: title, type, badge, y bullets (si aplica).

Ejemplo de llamada:
delegate(agent="slides_agent", task="JSON con el outline de la presentación")

**PASO 5 - FINALIZAR:**
finish con confirmación del resultado

TIPOS DE SLIDE DISPONIBLES:
- title: Slide de título (primera slide)
- bullets: Lista de puntos (máximo 5 bullets, cortos)
- content: Texto descriptivo
- stats: Estadísticas con value y label
- quote: Cita con autor
- comparison: Comparación lado a lado

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
1. Usa `think` para analizar la tarea y dividirla en pasos
2. Ejecuta cada paso con las herramientas apropiadas
3. IMPORTANTE: Completa TODAS las partes antes de finalizar
4. Si piden guardar algo, DEBES usar `write_file`
5. Usa `reflect` si los resultados parecen incompletos
6. Llama `finish` con tu respuesta completa

PARA PRESENTACIONES (slides, diapositivas, PowerPoint):
1. `think` - Analiza el tema: audiencia, propósito, tono, estructura
2. `web_search` - SOLO si necesitas datos actuales o específicos que no conoces
3. `plan` - Crea el outline de slides con título, badges y contenido por slide
4. `delegate` - Envía al slides_agent el outline JSON estructurado
5. `finish` - Confirma el resultado

Ejemplo: "Crea presentación sobre X" → think(análisis) → [web_search si necesario] → plan(outline) → delegate(slides_agent) → finish"""

WORKFLOW_COMPLEX = """Para esta tarea COMPLEJA:
1. Usa `plan` para crear un enfoque estructurado con TODOS los pasos
2. Usa `think` antes de cada paso importante
3. Ejecuta herramientas según tu plan - NO saltes ningún paso
4. Usa `reflect` para verificar progreso después de cada acción
5. CHECKPOINT: Antes de finalizar, verifica que TODAS las partes estén hechas
6. Si falta algo, ejecuta las herramientas necesarias
7. Llama `finish` con tu respuesta completa

Ejemplo: "Investiga X, analiza Y, crea informe Z" → plan → web_search → think → write → reflect → finish"""
