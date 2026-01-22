# Auditoría de Localhost Hardcodeados - Brain v1.0

**Fecha:** 2026-01-22  
**Propósito:** Identificar todos los `localhost` hardcodeados antes del deployment a producción

---

## 🔴 CRÍTICO - Requieren cambio inmediato

### **Backend API (Python)**

#### `services/api/src/tools/tool_registry.py`
```python
# Línea 498
image_url = f"http://localhost:1337{file_info.get('url')}"
```
**Solución:** Usar variable de entorno `STRAPI_PUBLIC_URL`

#### `services/api/src/mcp/client.py`
```python
# Línea 21
STRAPI_URL = os.getenv("STRAPI_URL", "http://localhost:1337")
MCP_PLAYWRIGHT_URL = os.getenv("MCP_PLAYWRIGHT_URL", "http://localhost:3001")
```
**Solución:** Ya usa env vars, solo cambiar defaults

#### `services/api/src/config.py`
```python
# Línea 18, 21, 34
database_url: str = "postgresql://brain:brain_secret@localhost:5432/brain_db"
redis_url: str = "redis://localhost:6379"
cors_origins: list[str] = ["http://localhost:4200", "http://localhost:1337"]
```
**Solución:** Defaults están bien para desarrollo, pero verificar que las env vars funcionen

---

### **Frontend (Angular)**

#### `services/gui/src/app/core/services/api.service.ts`
```typescript
// Línea 9
private readonly API_URL = 'http://localhost:8000/api/v1';
```
**Solución:** Usar `environment.ts` con variable `apiUrl`

#### `services/gui/src/app/core/services/auth.service.ts`
```typescript
// Línea 11
private readonly STRAPI_URL = 'http://localhost:1337';
```
**Solución:** Usar `environment.ts` con variable `strapiUrl`

#### `services/gui/src/app/core/services/strapi.service.ts`
```typescript
// Línea 19
private readonly STRAPI_URL = 'http://localhost:1337/api';
```
**Solución:** Usar `environment.ts`

#### `services/gui/src/app/features/chains/chains.component.ts`
```typescript
// Línea 998, 1158, 1165, 1325
apiBaseUrl = 'http://localhost:8000/api/v1';
const url = `http://localhost:8000/api/v1/chains/...`;
llm_provider_url: this.selectedProvider?.baseUrl || 'http://localhost:11434',
```
**Solución:** Usar `environment.ts`

#### `services/gui/src/app/features/testing/testing.component.ts`
```typescript
// Línea 645
private readonly API_URL = 'http://localhost:8000/api/v1';
```
**Solución:** Usar `environment.ts`

#### `services/gui/src/app/features/settings/settings.component.ts`
```typescript
// Línea 577, 607, 664
private readonly API_URL = 'http://localhost:8000/api/v1';
baseUrl: ['http://localhost:11434', Validators.required],
```
**Solución:** Usar `environment.ts`

#### `services/gui/src/app/features/rag/rag.component.ts`
```typescript
// Línea 510
private readonly API_URL = 'http://localhost:8000/api/v1/rag';
```
**Solución:** Usar `environment.ts`

#### `services/gui/src/app/features/tools/tools.component.ts`
```typescript
// Líneas 151, 560, 575, 609, 627, 643, 675
Múltiples URLs hardcodeadas
```
**Solución:** Usar `environment.ts`

#### `services/gui/src/app/features/chains/chain-editor/chain-editor.component.ts`
```typescript
// Líneas 628, 704
URLs hardcodeadas
```
**Solución:** Usar `environment.ts`

#### `services/gui/src/app/shared/components/browser-viewer/browser-viewer.component.ts`
```typescript
// Línea 246
@Input() apiUrl = 'http://localhost:8000/api/v1';
```
**Solución:** Usar `environment.ts`

---

## 🟡 MEDIO - Verificar pero probablemente OK

### **Healthchecks en Dockerfiles**
```dockerfile
# services/api/Dockerfile (línea 70)
CMD curl -f http://localhost:8000/health || exit 1

# services/browser-service/Dockerfile (línea 53)
CMD curl -sf http://localhost:9222/json/version || exit 1

# services/mcp-playwright/Dockerfile (línea 61)
CMD curl -f http://localhost:${MCP_PORT}/health || exit 1

# services/strapi/Dockerfile (línea 47)
CMD wget --no-verbose --tries=1 --spider http://localhost:1337/_health || exit 1

# services/gui/Dockerfile (línea 55)
CMD wget --no-verbose --tries=1 --spider http://localhost:80/health || exit 1
```
**Solución:** ✅ **OK** - Los healthchecks dentro del contenedor usan localhost correctamente

---

### **Browser Service (WebSocket)**
```python
# services/api/src/browser/service.py (líneas 79-88)
headers={"Host": "localhost"}
ws_url = ws_url.replace("ws://localhost/", f"ws://{BROWSER_VNC_HOST}:{cdp_proxy_port}/")
```
**Solución:** ✅ **OK** - Es parte de la lógica de proxy de Chrome CDP

---

### **Configuraciones internas**
```python
# services/strapi/config/database.ts (línea 5)
host: env('DATABASE_HOST', 'localhost'),
```
**Solución:** ✅ **OK** - Ya usa env var con fallback

```conf
# services/browser-service/supervisord.conf (línea 30)
command=/usr/bin/websockify --web=/usr/share/novnc/ 6080 localhost:5900
```
**Solución:** ✅ **OK** - Configuración interna de VNC

```nginx
# services/gui/nginx.conf (línea 40)
server_name localhost;
```
**Solución:** ✅ **OK** - Se puede dejar, nginx escucha en todas las interfaces

---

## 🟢 BAJO - Documentación y ejemplos

### **README.md y docs**
- `README.md` - Ejemplos de curl con localhost
- `docs/*.md` - Documentación con localhost
- `.vscode/launch.json` - Configuración de debug

**Solución:** ✅ **OK** - Son solo ejemplos y documentación

---

## 📋 RESUMEN DE ACCIONES NECESARIAS

### **1. Backend (Python)**
- [ ] `tool_registry.py`: Usar `STRAPI_PUBLIC_URL` env var
- [ ] Verificar que todas las env vars se lean correctamente en producción

### **2. Frontend (Angular)**
- [ ] Crear `environment.prod.ts` con URLs de producción
- [ ] Reemplazar todos los hardcoded URLs en servicios con `environment.apiUrl`
- [ ] Actualizar componentes para usar el servicio de configuración

### **3. Docker & Compose**
- [ ] Verificar que healthchecks funcionen (ya están bien)
- [ ] Añadir variables de entorno en docker-compose para producción

---

## 🎯 SIGUIENTE PASO

**Crear archivo `environment.prod.ts` y actualizar servicios Angular**
