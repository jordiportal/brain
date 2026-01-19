# Herramienta de Búsqueda Web (Web Search Tool)

## 📋 Descripción

Herramienta de búsqueda web integrada en Brain que utiliza **DuckDuckGo** para obtener información actualizada de Internet. Está disponible automáticamente para todos los agentes que usen el `tool_registry`.

## 🚀 Características

- ✅ **Búsquedas gratuitas** sin API keys
- ✅ **Sin límites de rate** (uso razonable)
- ✅ **Resultados relevantes** de DuckDuckGo
- ✅ **Integración nativa** con el sistema de herramientas
- ✅ **Logging estructurado** de todas las búsquedas
- ✅ **Manejo de errores** robusto

## 📦 Instalación

La dependencia ya está incluida en `requirements.txt`:

```txt
duckduckgo-search==6.3.5
```

Para instalar en desarrollo local:

```bash
cd services/api
pip install -r requirements.txt
```

Para aplicar en Docker:

```bash
docker compose build api
docker compose restart api
```

## 🔧 Uso

### Desde el Tool Agent

El agente `tool_agent` puede usar automáticamente la búsqueda web:

```python
# El LLM decide cuándo usar web_search basándose en la pregunta
input_data = {
    "message": "¿Cuál es el precio actual del Bitcoin?"
}

# El tool_agent llamará automáticamente a web_search si es necesario
```

### Uso Directo del Tool Registry

```python
from tools.tool_registry import tool_registry

# Registrar herramientas builtin
tool_registry.register_builtin_tools()

# Ejecutar búsqueda
result = await tool_registry.execute(
    "web_search",
    query="Python programming language",
    max_results=5
)

# Resultado
{
    "success": True,
    "query": "Python programming language",
    "count": 5,
    "results": [
        {
            "position": 1,
            "title": "Python.org - Official Website",
            "snippet": "Python is a programming language that lets you work quickly...",
            "url": "https://www.python.org/"
        },
        ...
    ]
}
```

### Desde el Orquestador

El `orchestrator_agent` puede delegar búsquedas web al `tool_agent`:

```python
# El usuario pregunta algo que requiere información actualizada
user_query = "¿Cuáles son las últimas noticias sobre IA?"

# El orchestrator:
# 1. Detecta que necesita búsqueda web
# 2. Delega al tool_agent
# 3. El tool_agent usa web_search
# 4. Devuelve resultados al orchestrator
# 5. El orchestrator sintetiza la respuesta final
```

## 📝 Parámetros

### Input

| Parámetro | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `query` | string | ✅ Sí | - | Consulta de búsqueda |
| `max_results` | integer | ❌ No | 5 | Número máximo de resultados (1-20) |

### Output (éxito)

```json
{
    "success": true,
    "query": "consulta realizada",
    "count": 5,
    "results": [
        {
            "position": 1,
            "title": "Título del resultado",
            "snippet": "Extracto del contenido...",
            "url": "https://ejemplo.com"
        }
    ]
}
```

### Output (error)

```json
{
    "success": false,
    "error": "Descripción del error",
    "query": "consulta que falló"
}
```

## 🎯 Ejemplos de Uso

### Búsqueda de Noticias

```python
result = await tool_registry.execute(
    "web_search",
    query="latest AI news 2024",
    max_results=5
)
```

### Búsqueda de Información Técnica

```python
result = await tool_registry.execute(
    "web_search",
    query="FastAPI async streaming tutorial",
    max_results=3
)
```

### Búsqueda de Precios/Datos Actuales

```python
result = await tool_registry.execute(
    "web_search",
    query="EUR USD exchange rate today",
    max_results=3
)
```

## 🧪 Testing

Ejecutar el script de prueba:

```bash
# Desde la raíz del proyecto
python test_web_search.py
```

Salida esperada:

```
============================================================
🧪 TEST: Búsqueda Web con DuckDuckGo
============================================================

📦 Registrando herramientas builtin...
✅ Herramienta encontrada: web_search
   Descripción: Busca información en la web usando DuckDuckGo...
   Tipo: builtin

🔍 Ejecutando búsqueda: 'Python programming language'
------------------------------------------------------------
✅ Búsqueda exitosa - 3 resultados

📄 Resultado 1:
   Título: Welcome to Python.org
   Snippet: The official home of the Python Programming Language...
   URL: https://www.python.org/
...
```

## 📡 API Endpoints

### GET `/api/v1/tools`

Lista todas las herramientas disponibles, incluyendo `web_search`:

```bash
curl http://localhost:8000/api/v1/tools
```

### GET `/api/v1/tools/web_search`

Obtiene detalles de la herramienta:

```bash
curl http://localhost:8000/api/v1/tools/web_search
```

### POST `/api/v1/tools/web_search/execute`

Ejecuta una búsqueda web:

```bash
curl -X POST http://localhost:8000/api/v1/tools/web_search/execute \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python tutorials",
    "max_results": 3
  }'
```

## 🔍 Integración con Agentes

### Tool Agent

El `tool_agent` reconoce automáticamente cuando usar `web_search`:

**Prompt del Tool Agent:**
```
HERRAMIENTAS DISPONIBLES:
- calculator: Realiza cálculos matemáticos...
- current_datetime: Obtiene la fecha y hora actual...
- web_search: Busca información en la web usando DuckDuckGo...

Si la pregunta requiere información actualizada de internet,
usa web_search con el query apropiado.
```

### Orchestrator Agent

El orquestador puede planificar pasos que incluyan búsquedas web:

```json
{
  "plan": [
    {
      "step": 1,
      "description": "Buscar últimas noticias sobre IA",
      "agent": "tool_agent"
    },
    {
      "step": 2,
      "description": "Resumir los hallazgos",
      "agent": "conversational"
    }
  ]
}
```

## ⚠️ Consideraciones

### Límites de Rate

DuckDuckGo no tiene límites oficiales, pero:

- Uso razonable: < 1 búsqueda por segundo
- Si se detecta abuso, puede haber rate limiting temporal
- Implementar caché para consultas repetidas (futuro)

### Calidad de Resultados

- ✅ Buenos para: información general, noticias, tutoriales
- ⚠️ Limitados para: búsquedas muy específicas o técnicas
- ❌ No ideal para: investigación académica profunda

### Privacidad

- ✅ DuckDuckGo no rastrea usuarios
- ✅ No se almacenan queries en sus servidores
- ✅ Mayor privacidad que Google

## 🚀 Mejoras Futuras

### Caché de Resultados (Planned)

```python
# TODO: Implementar caché en Redis
# - Cachear resultados por 1 hora
# - Reducir llamadas repetidas
# - Mejorar latencia
```

### Búsqueda de Imágenes (Planned)

```python
# TODO: Agregar soporte para búsqueda de imágenes
ddgs.images(query, max_results=10)
```

### Búsqueda de Noticias (Planned)

```python
# TODO: Endpoint específico para noticias
ddgs.news(query, max_results=10)
```

### Fallback a Otros Motores (Planned)

Si DuckDuckGo falla, usar:
1. Tavily API (para IA)
2. Browser Agent + Google
3. Caché local

## 📚 Referencias

- [DuckDuckGo Search Python](https://github.com/deedy5/duckduckgo_search)
- [DuckDuckGo API](https://duckduckgo.com/api)
- [Tool Registry Documentation](./tool_registry.md)

## 🐛 Troubleshooting

### Error: "duckduckgo-search no está instalado"

**Solución:**
```bash
cd services/api
pip install duckduckgo-search==6.3.5
```

### Error: "No results found"

Causas posibles:
1. Query demasiado específico
2. Rate limiting temporal
3. Problemas de red

**Solución:**
- Simplificar el query
- Esperar 1 minuto y reintentar
- Verificar conectividad

### Error: "Timeout"

DuckDuckGo puede ser lento ocasionalmente.

**Solución:**
- Aumentar timeout en httpx
- Implementar retry logic
- Usar caché para queries populares

## 📊 Logs

Todas las búsquedas se registran con structlog:

```json
{
  "event": "Buscando en web",
  "query": "Python tutorials",
  "max_results": 5,
  "timestamp": "2024-01-19T10:30:00"
}
```

```json
{
  "event": "Búsqueda completada",
  "query": "Python tutorials",
  "results_count": 5,
  "timestamp": "2024-01-19T10:30:02"
}
```

## ✅ Checklist de Implementación

- [x] Agregar dependencia `duckduckgo-search` a requirements.txt
- [x] Implementar `_builtin_web_search` en tool_registry.py
- [x] Registrar herramienta en `register_builtin_tools()`
- [x] Actualizar tool_agent.py con nota sobre registry
- [x] Crear script de prueba (test_web_search.py)
- [x] Documentación completa
- [ ] Tests unitarios con pytest
- [ ] Implementar caché en Redis
- [ ] Métricas de uso en monitoring
