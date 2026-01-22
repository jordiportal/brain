# 🚀 Brain v1.0.0 - Instrucciones de Deployment (Directo)

## 📋 Resumen

Debido a limitaciones de tamaño en el registry (`413 Request Entity Too Large`), usaremos **deployment directo** en el servidor sin registry intermedio.

**Ventajas:**
- ✅ Sin límites de tamaño
- ✅ Más rápido (no hay upload/download)
- ✅ Ideal para entornos de test
- ✅ Build optimizado para arquitectura del servidor

---

## 🔧 PASO 2: Deployment al Servidor

### Opción A: Deployment Automático (Script)

```bash
# 1. Editar el script con tu usuario SSH
nano /Users/jordip/cursor/brain/scripts/deploy-direct.sh
# Cambiar: USER="tu_usuario"

# 2. Ejecutar deployment
cd /Users/jordip/cursor/brain
./scripts/deploy-direct.sh
```

**Tiempo estimado:** 15-20 minutos (build en servidor)

---

### Opción B: Deployment Manual (Paso a Paso)

#### 1. Conectar al Servidor

```bash
ssh tu_usuario@192.168.7.102
```

#### 2. Clonar Repositorio

```bash
# Crear directorio
sudo mkdir -p /opt/brain
sudo chown -R $(whoami):$(whoami) /opt/brain

# Clonar
git clone https://github.com/jordiportal/brain.git /opt/brain
cd /opt/brain
```

#### 3. Configurar Variables de Entorno

```bash
# Copiar template
cp .env.production .env

# Editar con tus valores
nano .env
```

**Variables CRÍTICAS a cambiar:**

```env
# Secrets (generar con: openssl rand -base64 32)
JWT_SECRET=TU_VALOR_AQUI
ADMIN_JWT_SECRET=TU_VALOR_AQUI
APP_KEYS=key1,key2,key3,key4
API_TOKEN_SALT=TU_VALOR_AQUI
TRANSFER_TOKEN_SALT=TU_VALOR_AQUI
POSTGRES_PASSWORD=TU_PASSWORD_SEGURO

# URLs (ajustar IP si es necesario)
API_PUBLIC_URL=http://192.168.7.102:8000
STRAPI_PUBLIC_URL=http://192.168.7.102:1337
CORS_ORIGINS=http://192.168.7.102:4200,http://192.168.7.102:1337
```

#### 4. Construir Imágenes

```bash
cd /opt/brain

# Build (esto tomará 15-20 min)
docker compose -f docker-compose.production.yml build

# Ver progreso en otra terminal
docker compose -f docker-compose.production.yml build --progress=plain
```

#### 5. Levantar Servicios

```bash
# Iniciar todos los servicios
docker compose -f docker-compose.production.yml up -d

# Ver logs
docker compose -f docker-compose.production.yml logs -f

# Ver estado
docker compose -f docker-compose.production.yml ps
```

---

## ✅ Verificación Post-Deployment

### 1. Verificar Contenedores

```bash
docker ps | grep brain

# Todos deben estar "Up" y "healthy"
```

Salida esperada:
```
brain-gui              Up (healthy)
brain-api              Up
brain-strapi           Up (healthy)
brain-postgres         Up (healthy)
brain-redis            Up (healthy)
brain-browser-service  Up
```

### 2. Verificar APIs

```bash
# Health check API
curl http://localhost:8000/health
# Esperado: {"status":"ok","version":"0.1.0"}

# Chains disponibles
curl http://localhost:8000/api/v1/chains | jq '.chains[] | .id'

# Strapi health
curl http://localhost:1337/_health
# Esperado: 204 No Content
```

### 3. Acceder a Interfaces

Desde tu navegador local:

| Servicio | URL | Credenciales |
|----------|-----|--------------|
| **GUI** | http://192.168.7.102:4200 | (sin auth) |
| **API Docs** | http://192.168.7.102:8000/docs | (sin auth) |
| **Strapi Admin** | http://192.168.7.102:1337/admin | Crear en primer acceso |

---

## 🎯 Configuración Inicial de Strapi

### 1. Crear Admin User

```bash
# Acceder a http://192.168.7.102:1337/admin
# Primera vez te pedirá crear usuario admin
```

**Credenciales sugeridas:**
- Email: admin@brain.com
- Password: Admin123!
- Username: admin

### 2. Obtener API Token

1. **Settings** → **API Tokens** → **Create new API Token**
2. **Name:** `brain-api`
3. **Token type:** Full access
4. **Token duration:** Unlimited
5. **Copy token**

### 3. Actualizar Token en .env

```bash
# En el servidor
cd /opt/brain
nano .env

# Actualizar línea:
STRAPI_API_TOKEN=tu_token_copiado_aqui

# Reiniciar API
docker compose -f docker-compose.production.yml restart api
```

### 4. Configurar LLM Providers

En Strapi Admin:

1. **Content Manager** → **LLM Providers** → **Create new entry**
2. Agregar tus proveedores:
   - **Ollama** (si tienes): `http://tu_ip:11434`
   - **OpenAI**: Con tu API key
   - **Gemini**: Con tu API key
   - etc.

---

## 🐛 Troubleshooting

### Problema: Build falla por espacio en disco

```bash
# Limpiar Docker
docker system prune -a -f --volumes

# Verificar espacio
df -h
```

### Problema: Servicio no inicia

```bash
# Ver logs específicos
docker logs brain-api --tail 100
docker logs brain-gui --tail 100
docker logs brain-strapi --tail 100

# Reiniciar servicio
docker compose -f docker-compose.production.yml restart api
```

### Problema: GUI no carga cadenas

```bash
# Verificar que API esté accesible desde el navegador
curl http://192.168.7.102:8000/api/v1/chains

# Verificar variables de entorno inyectadas
docker exec brain-gui cat /usr/share/nginx/html/browser/assets/env.js

# Debe mostrar las URLs correctas
```

### Problema: CORS errors en el navegador

```bash
# Verificar CORS_ORIGINS en .env
cat /opt/brain/.env | grep CORS

# Debe incluir la URL del GUI
# Reiniciar API después de cambiar
docker compose -f docker-compose.production.yml restart api
```

### Problema: Strapi no conecta a PostgreSQL

```bash
# Verificar que postgres esté healthy
docker ps | grep postgres

# Ver logs de postgres
docker logs brain-postgres --tail 50

# Ver logs de strapi
docker logs brain-strapi --tail 50

# Verificar conexión desde strapi
docker exec brain-strapi pg_isready -h postgres -U brain
```

---

## 📝 Comandos Útiles

### Ver Logs

```bash
# Todos los servicios
docker compose -f docker-compose.production.yml logs -f

# Servicio específico
docker compose -f docker-compose.production.yml logs -f api

# Últimas 100 líneas
docker logs brain-api --tail 100
```

### Reiniciar Servicios

```bash
# Todos
docker compose -f docker-compose.production.yml restart

# Uno específico
docker compose -f docker-compose.production.yml restart api
```

### Actualizar Código

```bash
cd /opt/brain
git pull origin main
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml up -d
```

### Backup

```bash
# PostgreSQL
docker exec brain-postgres pg_dump -U brain brain_db > backup-$(date +%Y%m%d).sql

# Strapi uploads
docker cp brain-strapi:/app/public/uploads ./uploads-backup-$(date +%Y%m%d)
```

### Restaurar Backup

```bash
# PostgreSQL
cat backup-20260122.sql | docker exec -i brain-postgres psql -U brain brain_db

# Strapi uploads
docker cp ./uploads-backup-20260122 brain-strapi:/app/public/uploads
```

---

## 🎉 Deployment Completado

Una vez verificado:

- ✅ Todos los servicios running y healthy
- ✅ GUI accesible y cargando cadenas
- ✅ API respondiendo correctamente
- ✅ Strapi configurado con API token
- ✅ LLM providers configurados

**¡Brain v1.0.0 está en producción en 192.168.7.102!** 🚀

---

## 📞 Soporte

Si encuentras problemas:

1. Revisa los logs con `docker logs`
2. Verifica el estado con `docker ps`
3. Consulta la documentación en `/docs`
4. Revisa las variables de entorno en `.env`

**Archivos de referencia:**
- `PASO_1_COMPLETADO.md` - Cambios del Paso 1
- `DEPLOYMENT_LOCALHOST_AUDIT.md` - Auditoría completa
- `.env.production` - Template de variables

---

**Última actualización:** 2026-01-22  
**Versión:** v1.0.0  
**Método:** Build directo sin registry
