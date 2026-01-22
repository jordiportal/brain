#!/bin/bash
set -e

# ===========================================
# Deployment Directo en Servidor - Brain v1.0.0
# Sin registry, build directo en producción
# ===========================================

SERVER="192.168.7.102"
USER="tu_usuario"  # Cambiar por tu usuario SSH
PROJECT_DIR="/opt/brain"

echo "=================================================="
echo "🚀 Brain - Deployment Directo al Servidor"
echo "=================================================="
echo ""
echo "Servidor:      $SERVER"
echo "Usuario:       $USER"
echo "Directorio:    $PROJECT_DIR"
echo ""

# Verificar conexión SSH
echo "🔐 Verificando conexión SSH..."
if ! ssh ${USER}@${SERVER} "echo 'Conexión OK'"; then
    echo "❌ Error: No se puede conectar al servidor"
    echo "   Verifica el usuario y la conexión SSH"
    exit 1
fi

echo "✅ Conexión SSH exitosa"
echo ""

# Clonar o actualizar repositorio
echo "📦 Clonando/actualizando repositorio..."
ssh ${USER}@${SERVER} << 'ENDSSH'
    # Crear directorio si no existe
    sudo mkdir -p /opt/brain
    sudo chown -R $(whoami):$(whoami) /opt/brain
    
    # Clonar o pull
    if [ -d "/opt/brain/.git" ]; then
        echo "Actualizando repositorio existente..."
        cd /opt/brain
        git pull origin main
    else
        echo "Clonando repositorio..."
        git clone https://github.com/jordiportal/brain.git /opt/brain
        cd /opt/brain
    fi
    
    echo "✅ Código actualizado"
ENDSSH

echo ""
echo "🔨 Construyendo imágenes en el servidor..."
ssh ${USER}@${SERVER} << 'ENDSSH'
    cd /opt/brain
    
    # Build con docker compose
    docker compose -f docker-compose.production.yml build --no-cache
    
    echo "✅ Imágenes construidas"
ENDSSH

echo ""
echo "🚀 Desplegando servicios..."
ssh ${USER}@${SERVER} << 'ENDSSH'
    cd /opt/brain
    
    # Copiar .env.production a .env si no existe
    if [ ! -f ".env" ]; then
        cp .env.production .env
        echo "⚠️  IMPORTANTE: Edita /opt/brain/.env con tus valores de producción"
    fi
    
    # Levantar servicios
    docker compose -f docker-compose.production.yml up -d
    
    echo "✅ Servicios desplegados"
ENDSSH

echo ""
echo "✅ Verificando servicios..."
sleep 10

ssh ${USER}@${SERVER} << 'ENDSSH'
    cd /opt/brain
    docker compose -f docker-compose.production.yml ps
ENDSSH

echo ""
echo "=================================================="
echo "✅ DEPLOYMENT COMPLETADO"
echo "=================================================="
echo ""
echo "📋 Servicios disponibles en:"
echo "  - GUI:         http://${SERVER}:4200"
echo "  - API:         http://${SERVER}:8000"
echo "  - API Docs:    http://${SERVER}:8000/docs"
echo "  - Strapi:      http://${SERVER}:1337/admin"
echo ""
echo "⚠️  SIGUIENTE PASO:"
echo "   1. SSH al servidor: ssh ${USER}@${SERVER}"
echo "   2. Editar: nano /opt/brain/.env"
echo "   3. Reiniciar: cd /opt/brain && docker compose -f docker-compose.production.yml restart"
echo ""
