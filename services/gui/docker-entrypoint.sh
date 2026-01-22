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

# Inyectar variables de entorno en runtime
if [ -f "/usr/share/nginx/html/browser/assets/env.js" ]; then
    echo "Inyectando variables de entorno en runtime..."
    
    API_PUBLIC_URL=${API_PUBLIC_URL:-http://localhost:8000}
    STRAPI_PUBLIC_URL=${STRAPI_PUBLIC_URL:-http://localhost:1337}
    
    cat > /usr/share/nginx/html/browser/assets/env.js << EOF
(function(window) {
  window['env'] = window['env'] || {};
  window['env']['apiUrl'] = '${API_PUBLIC_URL}/api/v1';
  window['env']['strapiUrl'] = '${STRAPI_PUBLIC_URL}';
  window['env']['strapiApiUrl'] = '${STRAPI_PUBLIC_URL}/api';
  window['env']['ollamaDefaultUrl'] = '${OLLAMA_URL:-http://localhost:11434}';
})(this);
EOF
    
    echo "Variables de entorno inyectadas:"
    echo "  API_PUBLIC_URL=${API_PUBLIC_URL}"
    echo "  STRAPI_PUBLIC_URL=${STRAPI_PUBLIC_URL}"
fi

# Ejecutar el comando pasado
exec "$@"
