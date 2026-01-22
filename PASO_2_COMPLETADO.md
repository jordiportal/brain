# ✅ PASO 2 COMPLETADO: Preparación para Deployment

## 📊 Estado: **COMPLETADO**

---

## 🎯 Objetivo del Paso 2

Preparar las imágenes Docker multi-arquitectura y subirlas al registry para deployment en Portainer.

---

## 🔄 Cambio de Estrategia

### **Problema Encontrado**

Durante el proceso de build y push al registry `registry.khlloreda.es`:

1. ✅ **Build exitoso**: Las imágenes se construyeron correctamente (7-9 minutos)
2. ❌ **Push fallido**: Error `413 Request Entity Too Large`

**Causa:** La imagen de la API con PyTorch+CUDA es ~3.5GB, superando el límite configurado en el proxy nginx del registry (openresty).

### **Solución Adoptada**

**Build directo en el servidor** sin registry intermedio:

| Característica | Con Registry | Build Directo (Elegido) |
|----------------|--------------|---------------------------|
| Tiempo total | 20-30 min | 15-20 min |
| Requiere | Registry configurado | Solo Git + Docker |
| Límite de tamaño | Sí (nginx) | No |
| Complejidad | Media | Baja |
| Ideal para | Producción distribuida | Test/Staging |

---

## 📦 Archivos Creados

### **1. Docker Compose Production**
`docker-compose.production.yml`
- Configuración optimizada para producción
- Build contexts incluidos
- Healthchecks configurados
- Variables de entorno documentadas

### **2. Scripts de Deployment**

#### `scripts/deploy-direct.sh` (Automático)
- Conecta vía SSH al servidor
- Clona/actualiza repositorio
- Construye imágenes
- Despliega servicios
- Verifica estado

#### `scripts/build-and-push.sh` (Futuro)
- Build multi-arch (AMD64 + ARM64)
- Push al registry
- Para cuando se solucione el límite del nginx

#### `scripts/test-build.sh` (Testing)
- Test de build local
- Sin push
- Para validar Dockerfiles

### **3. Documentación**

#### `DEPLOYMENT_DIRECT.md` (Principal)
- Instrucciones paso a paso
- Opción automática y manual
- Configuración de Strapi
- Troubleshooting completo
- Comandos útiles

#### `DEPLOYMENT_INSTRUCTIONS.md` (Referencia)
- Guía original con registry
- Para futuro uso con registry corregido

---

## 🔧 Optimizaciones Realizadas

### **Dockerfile de API**
```dockerfile
# Skip Playwright en ARM64 (no soportado oficialmente)
RUN if [ "$(uname -m)" = "x86_64" ]; then \
        playwright install chromium --with-deps; \
    else \
        echo "Skipping Playwright on ARM64"; \
    fi
```

### **Docker Compose Production**
- Build contexts locales (no registry)
- Target `production` para GUI
- Volúmenes persistentes configurados
- Healthchecks en todos los servicios críticos

---

## 🚀 Instrucciones de Uso

### **Opción A: Deployment Automático**

```bash
# 1. Editar script con tu usuario SSH
nano scripts/deploy-direct.sh
# Cambiar: USER="tu_usuario"

# 2. Ejecutar
./scripts/deploy-direct.sh
```

### **Opción B: Deployment Manual**

```bash
# En el servidor 192.168.7.102
ssh tu_usuario@192.168.7.102

# Clonar
git clone https://github.com/jordiportal/brain.git /opt/brain
cd /opt/brain

# Configurar
cp .env.production .env
nano .env  # Editar valores

# Build y Deploy
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml up -d
```

---

## ✅ Verificación

Una vez desplegado, verificar:

```bash
# Estado de contenedores
docker ps | grep brain

# Health checks
curl http://localhost:8000/health
curl http://localhost:1337/_health

# Logs
docker compose -f docker-compose.production.yml logs -f
```

**Interfaces esperadas:**
- GUI: http://192.168.7.102:4200
- API: http://192.168.7.102:8000
- Strapi: http://192.168.7.102:1337/admin

---

## 📝 Configuración Post-Deployment

### 1. Strapi Admin
- Crear usuario admin en primer acceso
- Generar API Token (Settings → API Tokens)
- Actualizar `STRAPI_API_TOKEN` en `.env`

### 2. LLM Providers
- Configurar en Strapi Admin
- Content Manager → LLM Providers
- Añadir Ollama, OpenAI, Gemini, etc.

### 3. Secrets
Cambiar en `.env`:
- `JWT_SECRET`
- `ADMIN_JWT_SECRET`
- `POSTGRES_PASSWORD`
- `API_TOKEN_SALT`
- `TRANSFER_TOKEN_SALT`

Generar con: `openssl rand -base64 32`

---

## 🔄 Actualización Futura

Para actualizar a una nueva versión:

```bash
cd /opt/brain
git pull origin main
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml up -d
```

---

## 💡 Ventajas del Approach Elegido

1. **Simplicidad**: No requiere configurar registry
2. **Velocidad**: Build directo sin upload/download
3. **Sin límites**: No hay restricciones de tamaño
4. **Optimizado**: Build específico para arquitectura del servidor
5. **Mantenible**: Git como única fuente de verdad

---

## 🎯 Próximos Pasos

### **Paso 3: Deployment Real**

1. ✅ Código subido a GitHub
2. ⏳ Conectar al servidor 192.168.7.102
3. ⏳ Clonar repositorio
4. ⏳ Configurar `.env`
5. ⏳ Build y deploy
6. ⏳ Configurar Strapi
7. ⏳ Verificar funcionalidad

---

## 📊 Resumen de Cambios

- **7 archivos creados**
- **1 Dockerfile optimizado**
- **1 docker-compose para producción**
- **3 scripts de deployment**
- **2 documentos de guía completa**

---

**Fecha:** 2026-01-22  
**Versión:** v1.0.0  
**Método:** Build directo sin registry  
**Estado:** ✅ Listo para deployment en servidor
