#!/bin/bash
set -e

# ===========================================
# Script para construir y push de imágenes multi-arch
# Brain v1.0.0 - Deployment Script
# ===========================================

REGISTRY="registry.khlloreda.es"
VERSION="v1.0.0"
# Solo AMD64 para entorno de test (el servidor Portainer es AMD64)
# ARM64 requiere demasiado espacio en disco para las deps de CUDA
PLATFORMS="linux/amd64"

echo "=================================================="
echo "🚀 Brain Deployment - Build & Push"
echo "=================================================="
echo ""
echo "Registry:   $REGISTRY"
echo "Version:    $VERSION"
echo "Platforms:  $PLATFORMS (test environment)"
echo ""

# Verificar buildx
if ! docker buildx version > /dev/null 2>&1; then
    echo "❌ Error: docker buildx no está disponible"
    exit 1
fi

# Crear/usar builder multi-platform si no existe
if ! docker buildx inspect brain-builder > /dev/null 2>&1; then
    echo "📦 Creando builder multi-platform..."
    docker buildx create --name brain-builder --use --bootstrap
else
    echo "✅ Usando builder existente: brain-builder"
    docker buildx use brain-builder
fi

echo ""
echo "=================================================="
echo "🔨 Construyendo imágenes..."
echo "=================================================="

# ===========================================
# 1. API (Python FastAPI)
# ===========================================
echo ""
echo "🐍 [1/4] Building API..."
docker buildx build \
    --platform $PLATFORMS \
    --tag $REGISTRY/brain-api:$VERSION \
    --tag $REGISTRY/brain-api:latest \
    --file ./services/api/Dockerfile \
    --push \
    ./services/api

echo "✅ API pushed successfully"

# ===========================================
# 2. GUI (Angular)
# ===========================================
echo ""
echo "🎨 [2/4] Building GUI..."
docker buildx build \
    --platform $PLATFORMS \
    --tag $REGISTRY/brain-gui:$VERSION \
    --tag $REGISTRY/brain-gui:latest \
    --file ./services/gui/Dockerfile \
    --push \
    ./services/gui

echo "✅ GUI pushed successfully"

# ===========================================
# 3. Strapi (CMS)
# ===========================================
echo ""
echo "📝 [3/4] Building Strapi..."
docker buildx build \
    --platform $PLATFORMS \
    --tag $REGISTRY/brain-strapi:$VERSION \
    --tag $REGISTRY/brain-strapi:latest \
    --file ./services/strapi/Dockerfile \
    --push \
    ./services/strapi

echo "✅ Strapi pushed successfully"

# ===========================================
# 4. Browser Service
# ===========================================
echo ""
echo "🌐 [4/4] Building Browser Service..."
docker buildx build \
    --platform linux/amd64 \
    --tag $REGISTRY/brain-browser-service:$VERSION \
    --tag $REGISTRY/brain-browser-service:latest \
    --file ./services/browser-service/Dockerfile \
    --push \
    ./services/browser-service

echo "✅ Browser Service pushed successfully"

echo ""
echo "=================================================="
echo "✅ TODAS LAS IMÁGENES CONSTRUIDAS Y SUBIDAS"
echo "=================================================="
echo ""
echo "📋 Imágenes disponibles en $REGISTRY:"
echo "  - brain-api:$VERSION"
echo "  - brain-gui:$VERSION"
echo "  - brain-strapi:$VERSION"
echo "  - brain-browser-service:$VERSION"
echo ""
echo "🎯 Próximo paso: Deployment a Portainer"
echo ""
