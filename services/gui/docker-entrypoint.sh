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
    
    # Instalar dependencias adicionales para visualización de grafos
    npm install @swimlane/ngx-graph d3 @types/d3
    npm install @angular/cdk @angular/material
fi

# Ejecutar el comando pasado
exec "$@"
