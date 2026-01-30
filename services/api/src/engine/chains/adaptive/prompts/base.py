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
# Workflow (único - el LLM decide)
# ============================================

WORKFLOW = """# CÓMO DECIDIR QUÉ HACER

Evalúa la tarea y decide el enfoque apropiado:

## Tareas simples (respuesta directa o 1-2 herramientas):
- Identifica qué herramienta necesitas
- Ejecútala
- Llama `finish` con tu respuesta

## Tareas que requieren investigación:
- Usa `web_search` si necesitas información actualizada o datos que no conoces
- NO busques si ya tienes el conocimiento suficiente

## Tareas que requieren planificación (presentaciones, proyectos complejos):
1. `think` - Analiza la tarea: qué se pide, cómo abordarlo
2. `web_search` - Solo si necesitas información externa
3. `plan` - Si hay múltiples pasos, crea un plan estructurado
4. Ejecuta las herramientas necesarias
5. `finish` - Confirma el resultado

## REGLAS IMPORTANTES:
- **SIEMPRE termina con `finish`** - Es obligatorio para completar cualquier tarea
- **Si piden guardar algo, usa `write_file`**
- **Si la tarea tiene varias partes, completa TODAS antes de finish**
- **No repitas la misma herramienta sin progreso** (máx 3 veces consecutivas)

## Ejemplos:
- "Calcula X" → calculate → finish
- "Busca sobre X" → web_search → finish
- "Lee archivo Y" → read_file → finish
- "Crea presentación sobre X" → think → [web_search] → plan → delegate(slides_agent) → finish
- "Genera imagen de X" → delegate(media_agent) → finish"""

# Aliases para compatibilidad (todos apuntan al mismo workflow)
WORKFLOW_SIMPLE = WORKFLOW
WORKFLOW_MODERATE = WORKFLOW
WORKFLOW_COMPLEX = WORKFLOW
