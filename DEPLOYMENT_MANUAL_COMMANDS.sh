#!/bin/bash

# ===========================================
# Deployment de Brain al servidor 192.168.7.102
# Usuario: root
# ===========================================

SERVER="192.168.7.102"
USER="root"
PASSWORD="f3ssK0l4."

cat << 'EOF'
================================================
🚀 Brain v1.0.0 - Deployment al Servidor
================================================

Ejecuta los siguientes comandos paso a paso:

================================================
PASO 1: Conectar al servidor
================================================

ssh root@192.168.7.102
# Password: f3ssK0l4.

================================================
PASO 2: Preparar directorio y clonar repo
================================================

# Crear directorio
mkdir -p /opt/brain

# Clonar repositorio
cd /opt
git clone https://github.com/jordiportal/brain.git

# Entrar al directorio
cd /opt/brain

================================================
PASO 3: Configurar variables de entorno
================================================

# Copiar template
cp .env.production .env

# Editar con nano
nano .env

# IMPORTANTE: Cambiar estos valores:
# - POSTGRES_PASSWORD=TU_PASSWORD_SEGURO
# - JWT_SECRET=$(openssl rand -base64 32)
# - ADMIN_JWT_SECRET=$(openssl rand -base64 32)
# - API_TOKEN_SALT=$(openssl rand -base64 32)
# - TRANSFER_TOKEN_SALT=$(openssl rand -base64 32)

# Guardar: Ctrl+O, Enter, Ctrl+X

================================================
PASO 4: Construir imágenes (15-20 min)
================================================

cd /opt/brain
docker compose -f docker-compose.production.yml build

# Para ver progreso detallado (en otra terminal):
# docker compose -f docker-compose.production.yml build --progress=plain

================================================
PASO 5: Levantar servicios
================================================

docker compose -f docker-compose.production.yml up -d

================================================
PASO 6: Verificar estado
================================================

# Ver estado de contenedores
docker compose -f docker-compose.production.yml ps

# Ver logs
docker compose -f docker-compose.production.yml logs -f

# Para salir de los logs: Ctrl+C

================================================
PASO 7: Verificar APIs
================================================

# API Health
curl http://localhost:8000/health

# Chains
curl http://localhost:8000/api/v1/chains

# Strapi
curl http://localhost:1337/_health

================================================
✅ DEPLOYMENT COMPLETADO
================================================

Accede desde tu navegador:
- GUI:        http://192.168.7.102:4200
- API Docs:   http://192.168.7.102:8000/docs
- Strapi:     http://192.168.7.102:1337/admin

================================================
CONFIGURACIÓN POST-DEPLOYMENT
================================================

1. Acceder a Strapi Admin:
   http://192.168.7.102:1337/admin
   
2. Crear usuario admin (primera vez)

3. Obtener API Token:
   Settings → API Tokens → Create new API Token
   Name: brain-api
   Type: Full access
   
4. Actualizar token en .env:
   nano /opt/brain/.env
   # Cambiar: STRAPI_API_TOKEN=tu_token_aqui
   
5. Reiniciar API:
   docker compose -f docker-compose.production.yml restart api

================================================

EOF
