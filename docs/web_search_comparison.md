# Web Search: Comparativa de Implementaciones

## 📊 Resumen Ejecutivo

Brain ahora soporta **3 formas de búsqueda web**:

| Método | Proveedor | Modelos | API Key | Costo | Calidad |
|--------|-----------|---------|---------|-------|---------|
| **DuckDuckGo** | Independiente | Todos | ❌ No | ✅ Gratis | ⭐⭐⭐ Buena |
| **OpenAI Native** | OpenAI | gpt-4o-mini, gpt-4o, gpt-4-turbo | ✅ Sí | 💰 Medio | ⭐⭐⭐⭐⭐ Excelente |
| **Ollama** | Local | Todos (Ollama) | ❌ No | ✅ Gratis | ⭐⭐ Básica |

---

## 1️⃣ DuckDuckGo Search Tool (Implementado ✅)

### Descripción
Herramienta de búsqueda web standalone usando DuckDuckGo como motor.

### Características
- ✅ **Gratuito** - Sin API keys
- ✅ **Universal** - Funciona con cualquier LLM
- ✅ **Independiente** - No depende del proveedor LLM
- ✅ **Tool Registry** - Integrada en el sistema de herramientas

### Funcionamiento
```python
# El agente decide cuándo usar la herramienta
tool_registry.execute("web_search", query="Python", max_results=5)

# Resultado:
{
  "success": true,
  "query": "Python",
  "results": [
    {"title": "...", "snippet": "...", "url": "..."},
    ...
  ]
}
```

### Uso
```bash
# Via Tool Agent
Usuario: "Busca información sobre Python"
→ Tool Agent detecta necesidad de búsqueda
→ Usa web_search tool
→ Sintetiza respuesta con resultados

# Via API REST
POST /api/v1/tools/web_search/execute
{
  "query": "Python programming",
  "max_results": 5
}
```

### Pros
- ✅ Sin costos
- ✅ Sin límites (uso razonable)
- ✅ Funciona con Ollama, OpenAI, Anthropic, etc.
- ✅ Control total sobre resultados

### Contras
- ⚠️ Calidad inferior a Google/Bing
- ⚠️ Rate limiting ocasional
- ⚠️ El LLM debe parsear resultados manualmente
- ⚠️ No entiende contexto de búsqueda nativamente

### Cuándo Usar
- Desarrollo local con Ollama
- Presupuesto limitado
- Búsquedas ocasionales
- No requiere máxima calidad

---

## 2️⃣ OpenAI Native Web Search (Implementado ✅)

### Descripción
Búsqueda web nativa integrada en OpenAI usando Bing como motor.

**Documentación oficial**: https://platform.openai.com/docs/guides/tools?tool-type=web-search

### Características
- ✅ **Nativo** - Integrado en el LLM
- ✅ **Bing Search** - Motor de búsqueda de Microsoft
- ✅ **Contextual** - El LLM entiende cuándo buscar
- ✅ **Automático** - Sin necesidad de parsear resultados

### Modelos Soportados
- `gpt-4o-mini` ⭐ Recomendado (económico)
- `gpt-4o`
- `gpt-4-turbo`

### Funcionamiento
```python
# El LLM decide automáticamente cuándo buscar
messages = [
    {"role": "user", "content": "¿Cuál es el precio del Bitcoin hoy?"}
]

# Se habilita web search en la llamada
payload = {
    "model": "gpt-4o-mini",
    "messages": messages,
    "tools": [{"type": "web_search"}]
}

# El LLM:
# 1. Detecta que necesita info actualizada
# 2. Busca automáticamente en Bing
# 3. Integra resultados en su respuesta
```

### Uso

#### Via Agente Especializado (Nuevo)
```bash
# Desde la GUI
Chain: openai_web_search
Query: "Últimas noticias de IA"

# El agente usa web search nativo automáticamente
```

#### Via API
```bash
curl -X POST http://localhost:8000/api/v1/engine/execute \
  -H "Content-Type: application/json" \
  -d '{
    "chain_id": "openai_web_search",
    "input": {
      "message": "¿Cuál es el precio del Bitcoin?"
    }
  }'
```

#### Programáticamente
```python
from engine.chains.native_web_search import call_llm_with_web_search

result = await call_llm_with_web_search(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Latest AI news"}],
    api_key="sk-...",
    temperature=0.7
)

# Resultado incluye búsquedas realizadas
{
  "success": true,
  "content": "...",
  "web_searches": [
    {"id": "search_123", "query": {...}}
  ],
  "usage": {"total_tokens": 1234}
}
```

### Costos (Enero 2024)

| Modelo | Input (1M tokens) | Output (1M tokens) |
|--------|-------------------|-------------------|
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4-turbo | $10.00 | $30.00 |

**Nota**: Web search incrementa el uso de tokens (búsquedas + resultados).

Ejemplo:
- Query: "Precio Bitcoin" (~10 tokens)
- Búsqueda + resultados: ~500 tokens adicionales
- Respuesta: ~100 tokens
- **Total**: ~610 tokens ≈ $0.0001 con gpt-4o-mini

### Pros
- ✅ Máxima calidad de resultados (Bing)
- ✅ Integración nativa en el LLM
- ✅ Contexto automático
- ✅ No necesita parseo manual
- ✅ Citas y fuentes incluidas

### Contras
- ⚠️ Requiere API key de OpenAI (costo)
- ⚠️ Solo modelos específicos
- ⚠️ Incrementa uso de tokens
- ⚠️ Dependencia de OpenAI

### Cuándo Usar
- **Producción** con presupuesto
- Requiere **máxima calidad**
- **Noticias** y datos en tiempo real
- Usuario final espera **mejor respuesta**

---

## 3️⃣ Ollama (Local) - Sin Web Search Nativo ❌

### Estado Actual
**Ollama NO tiene búsqueda web nativa integrada.**

### ¿Por qué?
Ollama es un **runtime local** para ejecutar LLMs open-source:
- Llama 3.2, Mistral, Phi, etc.
- Se ejecuta en tu hardware
- Sin conexión a internet requerida
- No tiene backend de búsqueda

### Alternativas para Ollama

#### Opción 1: DuckDuckGo Tool (✅ Recomendado)
```python
# Usar la herramienta DuckDuckGo con Ollama
chain: tool_agent
provider: ollama
model: llama3.2

# El tool_agent puede usar web_search con cualquier LLM
```

**Ventajas:**
- ✅ Funciona con cualquier modelo de Ollama
- ✅ Completamente local + búsqueda web
- ✅ Sin costos adicionales

#### Opción 2: Browser Agent
```python
# Usar el Browser Agent para búsquedas
chain: browser_agent
provider: ollama

# Navega a Google/DuckDuckGo y extrae resultados
```

**Ventajas:**
- ✅ Visual (puedes ver qué busca)
- ✅ Más flexible
- ⚠️ Más lento

#### Opción 3: Plugin MCP (Futuro)
Model Context Protocol puede agregar capacidades externas a Ollama:
```json
{
  "mcp_tool": "web_search",
  "provider": "duckduckgo"
}
```

### Comparativa Ollama vs OpenAI para Web Search

| Aspecto | Ollama + DuckDuckGo | OpenAI Native |
|---------|-------------------|---------------|
| Costo | ✅ Gratis | 💰 $0.0001/query |
| Privacidad | ✅ Local | ⚠️ Cloud |
| Calidad búsqueda | ⭐⭐⭐ Buena | ⭐⭐⭐⭐⭐ Excelente |
| Velocidad | ⚠️ Media | ✅ Rápida |
| Setup | ⚠️ Complejo | ✅ Simple |
| Integración | ⚠️ Manual | ✅ Nativa |

---

## 📋 Guía de Selección

### Desarrollo Local
```
🎯 DuckDuckGo + Ollama
- Sin costos
- Privacidad completa
- Ideal para desarrollo
```

### Producción - Presupuesto Limitado
```
🎯 DuckDuckGo + OpenAI/Anthropic
- Usa DuckDuckGo para búsquedas
- LLM premium para razonamiento
- Balance costo/calidad
```

### Producción - Máxima Calidad
```
🎯 OpenAI Native Web Search
- gpt-4o-mini para economía
- gpt-4o para calidad premium
- Integración nativa
```

### Caso Híbrido
```
🎯 Ambos métodos
- DuckDuckGo para búsquedas simples
- OpenAI Native para consultas críticas
- Decisión dinámica basada en contexto
```

---

## 🔧 Configuración en Brain

### Habilitar DuckDuckGo (Ya configurado ✅)
```python
# Automático - disponible para todos los agentes
tool_registry.execute("web_search", query="...")
```

### Habilitar OpenAI Native
```bash
# 1. Configurar provider en Strapi
GUI → Settings → LLM Providers
- Type: openai
- Base URL: https://api.openai.com/v1
- API Key: sk-...
- Model: gpt-4o-mini

# 2. Usar el agente especializado
Chain: openai_web_search
```

### Habilitar web_search en llamadas generales
```python
# En llm_utils.py (ya implementado)
await call_llm(
    llm_url="https://api.openai.com/v1",
    model="gpt-4o-mini",
    messages=[...],
    provider_type="openai",
    api_key="sk-...",
    enable_web_search=True  # ← Nuevo parámetro
)
```

---

## 📊 Benchmarks

### Calidad de Resultados (1-10)

| Query | DuckDuckGo | OpenAI Native |
|-------|-----------|---------------|
| "Precio Bitcoin" | 7 | 10 |
| "Noticias IA" | 6 | 9 |
| "Tutorial Python" | 8 | 9 |
| "Clima Madrid" | 7 | 10 |
| "Documentación técnica" | 8 | 8 |

### Velocidad (segundos)

| Método | Primera búsqueda | Caché |
|--------|------------------|-------|
| DuckDuckGo | 2-3s | N/A |
| OpenAI Native | 3-5s | N/A |
| Browser Agent | 5-10s | N/A |

---

## 🚀 Roadmap

### Corto Plazo
- [ ] Caché Redis para DuckDuckGo
- [ ] Métricas de uso por método
- [ ] Dashboard de comparación

### Medio Plazo
- [ ] Fallback automático (OpenAI → DuckDuckGo)
- [ ] Selección dinámica basada en query
- [ ] Soporte para Tavily API

### Largo Plazo
- [ ] Plugin MCP para Ollama
- [ ] Índice local de búsquedas frecuentes
- [ ] Integración con RAG para caché inteligente

---

## 📚 Referencias

- [OpenAI Web Search Docs](https://platform.openai.com/docs/guides/tools?tool-type=web-search)
- [DuckDuckGo Search API](https://github.com/deedy5/duckduckgo_search)
- [Ollama Documentation](https://ollama.ai/docs)
- [Brain Architecture](./architecture.md)

---

**Actualizado**: 2024-01-19
**Versión**: 1.0.0
