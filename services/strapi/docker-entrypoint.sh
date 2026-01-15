#!/bin/sh
set -e

# Si no existe el proyecto Strapi, crearlo
if [ ! -f "package.json" ]; then
    echo "Creando nuevo proyecto Strapi..."
    # Responder 'n' automáticamente a preguntas interactivas
    yes n | npx create-strapi-app@latest . \
        --no-run \
        --skip-cloud \
        --dbclient=postgres \
        --dbhost="${DATABASE_HOST}" \
        --dbport="${DATABASE_PORT}" \
        --dbname="${DATABASE_NAME}" \
        --dbusername="${DATABASE_USERNAME}" \
        --dbpassword="${DATABASE_PASSWORD}" \
        --dbssl=false \
        --typescript || true
    
    # Instalar dependencias adicionales útiles
    npm install @strapi/plugin-documentation || true
fi

# Ejecutar el comando pasado
exec "$@"
