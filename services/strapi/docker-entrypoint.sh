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

# En producción, construir si no existe dist
if [ "$NODE_ENV" = "production" ] && [ ! -d "/app/dist" ]; then
    echo "🔨 Construyendo admin panel para producción..."
    npm run build || {
        echo "⚠️  Error en build, intentando limpiar cache..."
        rm -rf /app/dist /app/.strapi/client /app/build /app/.cache
        npm run build
    }
fi

# Ejecutar el comando pasado
exec "$@"
