# 🎉 USO SIMPLIFICADO: OpenAI Web Search con API Key Automática

## ✅ ACTUALIZACIÓN: Ya no necesitas pasar la API key manualmente

El agente `openai_web_search` ahora **usa automáticamente** la API key del LLM Provider OpenAI configurado en Strapi.

---

## 🚀 Cómo Usar (Simplificado)

### Paso 1: Configurar OpenAI en Strapi (Una sola vez)

```bash
# 1. Acceder a Strapi
http://localhost:1337/admin

# 2. Ir a Settings → LLM Providers
# 3. Crear nuevo provider:
   - Name: OpenAI
   - Type: openai
   - Base URL: https://api.openai.com/v1
   - API Key: sk-... (tu API key)
   - Default Model: gpt-4o-mini
   - Is Active: ✅ Activado

# 4. Guardar
```

### Paso 2: Usar el agente (Sin API key manual)

#### Desde la GUI

```
1. Abrir http://localhost:4200
2. Ir a Testing
3. Seleccionar chain: "openai_web_search"
4. Escribir query: "¿Cuál es el precio del Bitcoin?"
5. Ejecutar
```

**¡Eso es todo!** El agente obtiene la API key automáticamente de Strapi.

#### Desde la API

```bash
# ANTES (complicado):
curl -X POST http://localhost:8000/api/v1/engine/execute \
  -H "Content-Type: application/json" \
  -d '{
    "chain_id": "openai_web_search",
    "input": {"message": "Últimas noticias de IA"},
    "llm_provider": {
      "type": "openai",
      "api_key": "sk-...",           # ← Ya no necesitas esto
      "model": "gpt-4o-mini",
      "base_url": "https://api.openai.com/v1"
    }
  }'

# AHORA (simplificado):
curl -X POST http://localhost:8000/api/v1/engine/execute \
  -H "Content-Type: application/json" \
  -d '{
    "chain_id": "openai_web_search",
    "input": {"message": "Últimas noticias de IA"}
  }'
# ↑ Obtiene config automáticamente de Strapi
```

---

## 🔧 Cómo Funciona

```python
# Cuando ejecutas openai_web_search:

1. Verifica si hay API key pasada manualmente
   ↓ Si NO:
2. Llama a get_active_llm_provider() 
   ↓
3. Obtiene el provider OpenAI activo de Strapi
   ↓
4. Extrae: api_key, base_url, model
   ↓
5. Usa esa configuración para web search
   ↓
6. ✅ Funciona!
```

**Ventajas:**
- ✅ Configuración centralizada en Strapi
- ✅ No necesitas pasar API key en cada request
- ✅ Más seguro (API key no viaja en requests)
- ✅ Más simple de usar

---

## 📊 Comparativa: Antes vs Ahora

### Antes de esta actualización

```bash
# Tenías que pasar todo manualmente:
{
  "chain_id": "openai_web_search",
  "input": {"message": "..."},
  "llm_provider": {
    "type": "openai",
    "api_key": "sk-...",      # Manual
    "model": "gpt-4o-mini",   # Manual
    "base_url": "..."         # Manual
  }
}
```

### Ahora

```bash
# Solo necesitas:
{
  "chain_id": "openai_web_search",
  "input": {"message": "..."}
}
# Config automática desde Strapi ✨
```

---

## ⚙️ Configuración en Strapi (Detallada)

### 1. Acceder al Admin de Strapi

```
URL: http://localhost:1337/admin
Usuario: (el que creaste en setup inicial)
```

### 2. Crear LLM Provider OpenAI

```
Content Manager → LLM Providers → Create new entry

Campos:
┌─────────────────────────────────────────┐
│ Name: OpenAI                            │
│ Type: openai                            │
│ Base URL: https://api.openai.com/v1    │
│ API Key: sk-proj-...                    │ ← Tu API key
│ Default Model: gpt-4o-mini              │
│ Embedding Model: text-embedding-3-small │
│ Is Active: ✅                           │
│ Config: {}                              │
└─────────────────────────────────────────┘

Click: Save
Click: Publish
```

### 3. Verificar

```bash
# Ver providers configurados
curl -s http://localhost:1337/api/llm-providers | jq '.data[] | {name, type, isActive}'

# Resultado esperado:
{
  "name": "OpenAI",
  "type": "openai",
  "isActive": true
}
```

---

## 🧪 Probar

### Test 1: Verificar que obtiene la config

```bash
# Los logs del API deberían mostrar:
docker compose logs api --tail 20

# Buscar línea:
"Usando provider OpenAI desde Strapi: OpenAI"
"model": "gpt-4o-mini"
"base_url": "https://api.openai.com/v1"
```

### Test 2: Ejecutar búsqueda web

```bash
# Desde la GUI
Chain: openai_web_search
Query: "¿Qué temperatura hace en Madrid?"

# Debería:
1. Obtener config de Strapi automáticamente
2. Hacer búsqueda en Bing
3. Responder con información actualizada
```

---

## 🔐 Seguridad

### Ventajas de este enfoque

✅ **API key centralizada** - Una sola configuración en Strapi
✅ **No en requests** - API key no viaja en cada petición HTTP
✅ **Cache interno** - La config se cachea 60 segundos
✅ **Fácil rotación** - Cambias en Strapi y se aplica automáticamente

### Comparado con enfoque anterior

❌ API key en cada request
❌ Posible exposición en logs
❌ Difícil de actualizar (múltiples lugares)

---

## 💡 Casos de Uso

### Caso 1: Usuario Final (GUI)

```
Usuario abre la GUI → Testing → openai_web_search
NO necesita saber nada de API keys
El sistema las obtiene de Strapi
✅ Experiencia simple
```

### Caso 2: Integración Externa (API)

```bash
# App externa hace request:
POST /api/v1/engine/execute
{
  "chain_id": "openai_web_search",
  "input": {"message": "Noticias IA"}
}

# Brain obtiene API key internamente
# ✅ App externa NO necesita la API key
```

### Caso 3: Múltiples Entornos

```
Desarrollo: Provider OpenAI con API key dev
Staging: Provider OpenAI con API key staging  
Producción: Provider OpenAI con API key prod

✅ Solo cambias en Strapi
✅ Código no cambia
```

---

## 🚨 Troubleshooting

### Error: "No se encontró configuración de OpenAI"

**Causa**: No hay provider OpenAI activo en Strapi

**Solución:**
```bash
1. Ir a Strapi → Content Manager → LLM Providers
2. Verificar que existe entry con:
   - Type: openai
   - Is Active: ✅
3. Si no existe, crear uno
4. Reiniciar API: docker compose restart api
```

### Error: "API key de OpenAI no disponible"

**Causa**: El provider existe pero no tiene API key

**Solución:**
```bash
1. Editar el provider en Strapi
2. Agregar API Key: sk-...
3. Guardar y Publicar
4. No necesitas reiniciar API (cache se actualiza en 60s)
```

### Error: "Este agente requiere OpenAI, recibido: ollama"

**Causa**: El provider activo no es OpenAI

**Solución:**
```bash
1. En Strapi, busca el provider OpenAI
2. Activa "Is Active: ✅"
3. Desactiva otros providers (si es necesario)
```

---

## 📚 Documentación Técnica

### Flujo de Código

```python
# openai_web_search_agent.py

async def build_openai_web_search_agent(..., api_key=None):
    # 1. Verificar si hay API key manual
    if not api_key:
        # 2. Obtener provider activo de Strapi
        provider = await get_active_llm_provider()
        
        # 3. Si es OpenAI, usar su config
        if provider and provider.type == "openai":
            api_key = provider.api_key
            llm_url = provider.base_url
            model = provider.default_model
    
    # 4. Continuar con web search usando esa config
    await call_llm_with_web_search(
        model=model,
        api_key=api_key,
        ...
    )
```

### Módulos Involucrados

```
openai_web_search_agent.py
  ↓ usa
providers/llm_provider.py
  ↓ llama a
Strapi API (/api/llm-providers)
  ↓ devuelve
{
  "type": "openai",
  "apiKey": "sk-...",
  "baseUrl": "https://api.openai.com/v1",
  "defaultModel": "gpt-4o-mini"
}
```

---

## ✅ Resumen

### Lo que cambió

- ✅ Agente obtiene API key automáticamente de Strapi
- ✅ No necesitas pasar `llm_provider` manualmente
- ✅ Configuración centralizada y más segura

### Lo que NO cambió

- ✅ Todas las funcionalidades siguen igual
- ✅ Calidad de búsqueda sigue siendo excelente
- ✅ Soporte para gpt-4o-mini, gpt-4o, gpt-4-turbo

### Próximo paso

1. **Configurar OpenAI en Strapi** (una sola vez)
2. **Usar el agente** sin preocuparte de API keys
3. **¡Listo!** ✨

---

**Actualizado**: 2024-01-19  
**Cambio**: API key automática desde Strapi  
**Beneficio**: Uso más simple y seguro
