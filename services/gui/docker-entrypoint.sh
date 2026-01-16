#!/bin/sh
set -e

# Si no existe el proyecto Angular, crearlo
if [ ! -f "package.json" ]; then
    echo "Creando nuevo proyecto Angular..."
    ng new brain-gui \
        --directory=. \
        --routing=true \
        --style=scss \
        --skip-git \
        --skip-install=false \
        --ssr=false
fi

# Instalar dependencias si no existen o si se actualizó package.json
if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules" ]; then
    echo "Instalando dependencias..."
    npm install --legacy-peer-deps
fi

# Ejecutar el comando pasado
exec "$@"
