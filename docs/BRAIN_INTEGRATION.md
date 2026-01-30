# Brain Integration Guide

Documentación técnica para integrar Brain con Open WebUI.

## Resumen

Brain se conecta a Open WebUI como un modelo compatible con la API de OpenAI. La comunicación de eventos especiales (thinking, actions, artifacts) se realiza mediante **markers** embebidos en el stream de texto.

## API Endpoint

Brain debe exponer un endpoint compatible con OpenAI Chat Completions:

```
POST /v1/chat/completions
```

### Headers requeridos

```
Content-Type: application/json
Authorization: Bearer <API_KEY>
```

### Request Body

```json
{
  "model": "brain-slides",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "Crea una presentación sobre IA"}
  ],
  "stream": true
}
```

## Streaming Response (SSE)

Brain debe responder con Server-Sent Events en formato OpenAI:

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"brain-slides","choices":[{"index":0,"delta":{"content":"texto aquí"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"brain-slides","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

## Brain Events (Markers)

Los eventos especiales se envían como **comentarios HTML** dentro del content:

```
<!--BRAIN_EVENT:{"type":"thinking","content":"Analizando..."}-->
```

### Formato del marker

```
<!--BRAIN_EVENT:{JSON_PAYLOAD}-->
```

- El JSON debe estar en una sola línea (sin saltos de línea internos)
- Para contenido HTML con `-->`, usar `content_base64` (ver sección Artifacts)

---

## Tipos de Eventos

### 1. Thinking

Muestra el proceso de razonamiento del agente.

```json
{
  "type": "thinking",
  "content": "Analizando la petición del usuario...\n\n1. Tema: IA\n2. Formato: Presentación\n3. Slides estimadas: 5",
  "status": "progress"
}
```

**Campos:**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| type | string | Sí | `"thinking"` |
| content | string | Sí | Texto del razonamiento (soporta markdown) |
| status | string | No | `"start"`, `"progress"`, `"complete"`, `"error"` |

**Ejemplo de secuencia:**
```
<!--BRAIN_EVENT:{"type":"thinking","content":"Iniciando análisis...","status":"start"}-->
<!--BRAIN_EVENT:{"type":"thinking","content":"Paso 1: Investigar fuentes\nPaso 2: Estructurar contenido"}-->
<!--BRAIN_EVENT:{"type":"thinking","status":"complete"}-->
```

---

### 2. Action

Muestra acciones que está realizando el agente.

```json
{
  "type": "action",
  "action_type": "search",
  "title": "Buscando información",
  "status": "running"
}
```

**Campos:**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| type | string | Sí | `"action"` |
| action_type | string | Sí | Tipo de acción (ver tabla abajo) |
| title | string | Sí | Descripción de la acción |
| status | string | Sí | `"running"`, `"completed"`, `"error"` |
| description | string | No | Detalle adicional |
| results_count | number | No | Número de resultados (para búsquedas) |

**Tipos de action_type:**
| action_type | Icono | Uso |
|-------------|-------|-----|
| `search` | 🔍 | Búsqueda web |
| `read` | 📖 | Lectura de documento |
| `write` | ✍️ | Escritura/generación |
| `code_exec` | ⚡ | Ejecución de código |
| `slides` | 📊 | Generación de slides |
| `image` | 🖼️ | Generación de imagen |
| `data` | 📈 | Procesamiento de datos |
| `files` | 📁 | Operación de archivos |
| `web` | 🌐 | Operación web |

**Ejemplo de secuencia (acción con inicio y fin):**
```
<!--BRAIN_EVENT:{"type":"action","action_type":"search","title":"Buscando fuentes","status":"running"}-->
... (otros eventos o texto) ...
<!--BRAIN_EVENT:{"type":"action","action_type":"search","title":"Buscando fuentes","status":"completed","results_count":15}-->
```

---

### 3. Sources

Muestra las fuentes consultadas.

```json
{
  "type": "sources",
  "sources": [
    {
      "url": "https://example.com/article",
      "title": "Título del artículo",
      "snippet": "Extracto relevante del contenido...",
      "favicon": "🌐",
      "date": "2024-01-15"
    }
  ]
}
```

**Campos del source:**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| url | string | Sí | URL de la fuente |
| title | string | Sí | Título del documento |
| snippet | string | No | Extracto relevante |
| favicon | string | No | Emoji o URL del favicon |
| date | string | No | Fecha de publicación |

---

### 4. Artifact (SLIDES)

**IMPORTANTE:** Para artifacts con contenido HTML, el contenido debe codificarse en **base64** para evitar que `-->` dentro del HTML rompa el marker.

```json
{
  "type": "artifact",
  "artifact_type": "slides",
  "title": "Presentación: Inteligencia Artificial",
  "content_base64": "PGRpdiBjbGFzcz0ic2xpZGUiPi4uLjwvZGl2Pg==",
  "format": "html"
}
```

**Campos:**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| type | string | Sí | `"artifact"` |
| artifact_type | string | Sí | `"slides"` |
| title | string | No | Título del artifact |
| content_base64 | string | Sí* | Contenido en base64 |
| content | string | Sí* | Contenido directo (solo si no tiene `-->`) |
| format | string | No | `"html"` |

*Usar `content_base64` para HTML, `content` solo para texto plano sin `-->`

---

## Estructura HTML para Slides

Cada slide debe ser un `<div class="slide">`:

```html
<style>
/* Estilos opcionales */
.slide { padding: 24px; }
h1 { font-size: 1.8rem; }
/* ... */
</style>

<div class="slide">
  <span class="badge">INTRO</span>
  <h1>Título de la Slide</h1>
  <p>Contenido...</p>
</div>

<div class="slide">
  <h2>Segunda Slide</h2>
  <ul>
    <li>Punto 1</li>
    <li>Punto 2</li>
  </ul>
</div>
```

### Clases CSS soportadas

El viewer aplica estilos por defecto, pero puedes usar estas clases:

| Clase | Uso |
|-------|-----|
| `.slide` | **Requerido** - Contenedor de cada slide |
| `.badge` | Etiqueta/badge pequeño |
| `.highlight` | Texto destacado (color púrpura) |
| `.stats` | Contenedor flex para estadísticas |
| `.stat-value` | Número grande |
| `.stat-label` | Etiqueta pequeña |
| `.grid` | Grid de 2 columnas |
| `.card` | Tarjeta con fondo |
| `.card-title` | Título de tarjeta |
| `.card-desc` | Descripción de tarjeta |

---

## Ejemplo Completo: Generación de Slides

### Secuencia de eventos recomendada

```
1. THINKING     → "Analizando requisitos..."
2. ACTION       → search/running
3. ACTION       → search/completed
4. SOURCES      → Lista de fuentes consultadas
5. ACTION       → slides/running
6. TEXT         → "Generando presentación..."
7. ARTIFACT     → Slide 1 (content_base64)
8. ARTIFACT     → Slide 1+2 (content_base64 acumulativo)
9. ARTIFACT     → Slide 1+2+3 (content_base64 acumulativo)
10. ACTION      → slides/completed
11. TEXT        → "Presentación completada"
```

### Código de ejemplo (Node.js)

```javascript
// Función para enviar evento Brain
function sendBrainEvent(res, event) {
  let eventContent;
  
  if (event.type === 'artifact' && event.content) {
    // Codificar HTML en base64
    const eventCopy = { ...event };
    eventCopy.content_base64 = Buffer.from(event.content).toString('base64');
    delete eventCopy.content;
    eventContent = `\n<!--BRAIN_EVENT:${JSON.stringify(eventCopy)}-->\n`;
  } else {
    eventContent = `\n<!--BRAIN_EVENT:${JSON.stringify(event)}-->\n`;
  }
  
  const chunk = {
    id: `chatcmpl-${Date.now()}`,
    object: 'chat.completion.chunk',
    created: Math.floor(Date.now() / 1000),
    model: 'brain-slides',
    choices: [{
      index: 0,
      delta: { content: eventContent },
      finish_reason: null
    }]
  };
  
  res.write(`data: ${JSON.stringify(chunk)}\n\n`);
}

// Función para enviar texto normal
function sendText(res, text) {
  const chunk = {
    id: `chatcmpl-${Date.now()}`,
    object: 'chat.completion.chunk',
    created: Math.floor(Date.now() / 1000),
    model: 'brain-slides',
    choices: [{
      index: 0,
      delta: { content: text },
      finish_reason: null
    }]
  };
  
  res.write(`data: ${JSON.stringify(chunk)}\n\n`);
}

// Ejemplo de generación de slides
async function generateSlides(res, prompt) {
  // 1. Thinking
  sendBrainEvent(res, {
    type: 'thinking',
    content: `Creando presentación sobre: ${prompt}`
  });
  
  // 2. Action - búsqueda
  sendBrainEvent(res, {
    type: 'action',
    action_type: 'search',
    title: 'Investigando tema',
    status: 'running'
  });
  
  await sleep(1000);
  
  sendBrainEvent(res, {
    type: 'action',
    action_type: 'search',
    title: 'Investigando tema',
    status: 'completed',
    results_count: 12
  });
  
  // 3. Sources
  sendBrainEvent(res, {
    type: 'sources',
    sources: [
      { url: 'https://...', title: 'Fuente 1', snippet: '...' }
    ]
  });
  
  // 4. Action - generación
  sendBrainEvent(res, {
    type: 'action',
    action_type: 'slides',
    title: 'Generando slides',
    status: 'running'
  });
  
  sendText(res, '\n🎨 **Generando presentación...**\n\n');
  
  // 5. Generar slides progresivamente
  let slidesHTML = '<style>.slide{padding:24px}</style>';
  
  for (let i = 1; i <= 5; i++) {
    slidesHTML += `<div class="slide"><h1>Slide ${i}</h1></div>`;
    
    sendText(res, `📄 Slide ${i} generada...\n`);
    
    sendBrainEvent(res, {
      type: 'artifact',
      artifact_type: 'slides',
      title: `Presentación: ${prompt}`,
      content: slidesHTML,  // Se codificará a base64 automáticamente
      format: 'html'
    });
    
    await sleep(500);
  }
  
  // 6. Completar
  sendBrainEvent(res, {
    type: 'action',
    action_type: 'slides',
    title: 'Generando slides',
    status: 'completed'
  });
  
  sendText(res, '\n✅ **Presentación completada**\n');
}
```

---

## Configuración en Open WebUI

### 1. Añadir conexión Brain

1. Ir a **Admin Settings** → **Connections**
2. Añadir nueva conexión OpenAI:
   - **URL**: `http://localhost:8000/v1` (o URL de Brain)
   - **API Key**: Tu API key de Brain

### 2. Verificar modelos

Los modelos de Brain deben empezar con `brain-` para que Open WebUI active el parsing de eventos:

- `brain-slides`
- `brain-docs`
- `brain-chat`
- etc.

---

## Debugging

### Logs del parser

En la consola del navegador verás:

```
Brain artifact updated: {type: "slides", content: "...", title: "..."}
```

### Verificar eventos

Puedes ver los eventos raw en Network → filtrar por `chat/completions` → Response.

---

## Referencia Rápida

```
┌─────────────────────────────────────────────────────────┐
│ Marker format:                                          │
│ <!--BRAIN_EVENT:{"type":"...", ...}-->                  │
├─────────────────────────────────────────────────────────┤
│ Event types:                                            │
│ • thinking  - Razonamiento del agente                   │
│ • action    - Acción en progreso                        │
│ • sources   - Fuentes consultadas                       │
│ • artifact  - Contenido generado (slides, docs, etc.)   │
├─────────────────────────────────────────────────────────┤
│ Para HTML artifacts:                                    │
│ Usar content_base64 = Base64.encode(html)               │
├─────────────────────────────────────────────────────────┤
│ Slides HTML:                                            │
│ <div class="slide">...</div>                            │
│ <div class="slide">...</div>                            │
└─────────────────────────────────────────────────────────┘
```
