# 🚀 Instrucciones de Deployment a Portainer

## 📋 Pre-requisitos

- [x] Paso 1 completado (localhost eliminados)
- [ ] Paso 2: Imágenes construidas y subidas a registry
- [ ] Acceso a Portainer (192.168.7.102)

---

## 🔨 PASO 2: Construir y Subir Imágenes

### Opción A: Build y Push Automático

```bash
cd /Users/jordip/cursor/brain
./scripts/build-and-push.sh
```

Este script hará:
1. ✅ Crear builder multi-platform si no existe
2. ✅ Construir 4 imágenes para `linux/amd64` y `linux/arm64`
3. ✅ Push al registry `registry.khlloreda.es`

**Tiempo estimado:** ~20-30 minutos

### Opción B: Test Local Primero (Recomendado)

```bash
# 1. Test sin push (solo build)
./scripts/test-build.sh

# 2. Si funciona, hacer el push completo
./scripts/build-and-push.sh
```

---

## 📦 Imágenes que se Construirán

| Servicio | Imagen | Plataformas | Tamaño aprox |
|----------|--------|-------------|--------------|
| API | `registry.khlloreda.es/brain-api:v1.0.0` | amd64, arm64 | ~1.2GB |
| GUI | `registry.khlloreda.es/brain-gui:v1.0.0` | amd64, arm64 | ~200MB |
| Strapi | `registry.khlloreda.es/brain-strapi:v1.0.0` | amd64, arm64 | ~400MB |
| Browser | `registry.khlloreda.es/brain-browser-service:v1.0.0` | amd64 | ~800MB |

**Total:** ~2.6GB (por plataforma)

---

## 🎯 PASO 3: Deployment a Portainer

### 1. Acceder a Portainer

```bash
open http://192.168.7.102:9000
```

### 2. Crear Nuevo Stack

1. **Navegar a:** Stacks → Add stack
2. **Name:** `brain-stack`
3. **Build method:** Web editor
4. **Copiar contenido de:** `docker-compose.production.yml`

### 3. Configurar Variables de Entorno

En la sección **Environment variables**, agregar:

```env
# Base de Datos
POSTGRES_USER=brain
POSTGRES_PASSWORD=CAMBIAR_EN_PRODUCCION
POSTGRES_DB=brain_db

# Strapi Secrets (generar con: openssl rand -base64 32)
JWT_SECRET=CAMBIAR_EN_PRODUCCION
ADMIN_JWT_SECRET=CAMBIAR_EN_PRODUCCION
APP_KEYS=key1,key2,key3,key4
API_TOKEN_SALT=CAMBIAR_EN_PRODUCCION
TRANSFER_TOKEN_SALT=CAMBIAR_EN_PRODUCCION
STRAPI_API_TOKEN=OBTENER_DE_STRAPI_ADMIN

# URLs Públicas
API_PUBLIC_URL=http://192.168.7.102:8000
STRAPI_PUBLIC_URL=http://192.168.7.102:1337
CORS_ORIGINS=http://192.168.7.102:4200,http://192.168.7.102:1337
```

### 4. Deploy Stack

- Click **Deploy the stack**
- Esperar que todos los servicios estén `running` (verde)
- Verificar healthchecks

---

## ✅ Verificación Post-Deployment

### 1. Verificar Servicios

```bash
# Desde Portainer UI o SSH al servidor
docker ps -a | grep brain

# Todos deben estar "Up" (healthy)
```

### 2. Verificar APIs

```bash
# Health check API
curl http://192.168.7.102:8000/health

# Chains disponibles
curl http://192.168.7.102:8000/api/v1/chains | jq '.chains[] | .id'

# Strapi health
curl http://192.168.7.102:1337/_health
```

### 3. Acceder a Interfaces

| Servicio | URL | Credenciales |
|----------|-----|--------------|
| **GUI** | http://192.168.7.102:4200 | (sin auth) |
| **API Docs** | http://192.168.7.102:8000/docs | (sin auth) |
| **Strapi Admin** | http://192.168.7.102:1337/admin | admin@brain.com / Admin123! |

---

## 🔧 Configuración Inicial de Strapi

### 1. Crear Admin User (si es primera vez)

```bash
# Acceder a http://192.168.7.102:1337/admin
# Crear usuario admin
```

### 2. Obtener API Token

1. **Settings** → **API Tokens** → **Create new API Token**
2. **Name:** `brain-api`
3. **Token type:** Full access
4. **Copy token** y actualizar env var `STRAPI_API_TOKEN`

### 3. Configurar LLM Providers

1. **Content Manager** → **LLM Providers** → **Create new entry**
2. Agregar proveedores (Ollama, OpenAI, Gemini, etc.)

---

## 🐛 Troubleshooting

### Problema: Imagen no se descarga del registry

```bash
# Verificar que el registry es accesible
curl http://registry.khlloreda.es/v2/_catalog

# Si falla, verificar DNS/firewall
```

### Problema: Servicio no inicia

```bash
# Ver logs en Portainer UI o:
docker logs brain-api --tail 50
docker logs brain-gui --tail 50
```

### Problema: GUI no carga

```bash
# Verificar que env.js se inyectó correctamente
docker exec brain-gui cat /usr/share/nginx/html/browser/assets/env.js

# Debe contener las URLs públicas correctas
```

### Problema: CORS errors

- Verificar que `CORS_ORIGINS` incluye la URL del GUI
- Verificar que las URLs públicas son accesibles desde el navegador del usuario

---

## 📝 Mantenimiento

### Actualizar a Nueva Versión

```bash
# 1. Construir nueva versión
VERSION=v1.1.0 ./scripts/build-and-push.sh

# 2. En Portainer, editar stack
# 3. Cambiar tag de v1.0.0 a v1.1.0
# 4. Update the stack
```

### Backup de Datos

```bash
# PostgreSQL
docker exec brain-postgres pg_dump -U brain brain_db > backup.sql

# Strapi uploads
docker cp brain-strapi:/app/public/uploads ./strapi-uploads-backup
```

### Ver Logs

```bash
# En Portainer UI: Stack → brain-stack → Logs
# O desde CLI:
docker logs -f brain-api
docker logs -f brain-gui
```

---

## 🎉 Deployment Completado

Una vez verificado:

- ✅ Todos los servicios `running` y `healthy`
- ✅ GUI accesible en http://192.168.7.102:4200
- ✅ API responde en http://192.168.7.102:8000/health
- ✅ Strapi configurado y API token generado
- ✅ Chains cargando correctamente en el GUI

**¡Brain v1.0.0 está en producción!** 🚀
