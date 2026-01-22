#!/bin/bash
set -e

# ===========================================
# Test local de build multi-arch (sin push)
# ===========================================

PLATFORMS="linux/amd64,linux/arm64"

echo "=================================================="
echo "🧪 Test Build Multi-Arch (sin push)"
echo "=================================================="
echo ""
echo "Platforms:  $PLATFORMS"
echo ""

# Crear/usar builder multi-platform
if ! docker buildx inspect brain-builder > /dev/null 2>&1; then
    echo "📦 Creando builder multi-platform..."
    docker buildx create --name brain-builder --use --bootstrap
else
    echo "✅ Usando builder existente: brain-builder"
    docker buildx use brain-builder
fi

echo ""
echo "🔨 Testing API build..."
docker buildx build \
    --platform $PLATFORMS \
    --file ./services/api/Dockerfile \
    ./services/api \
    --progress=plain

echo ""
echo "✅ API build test successful!"
echo ""
echo "Para el build completo con push, ejecuta: ./scripts/build-and-push.sh"
