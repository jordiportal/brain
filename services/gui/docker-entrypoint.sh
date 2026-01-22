#!/bin/sh
set -e

# ===============================================
# Entrypoint para Brain GUI
# ===============================================
# En desarrollo: Crea el proyecto y instala deps
# En producción: Solo inyecta env vars en runtime
# ===============================================

# Detectar si estamos en producción (nginx) o desarrollo (node)
if [ -d "/usr/share/nginx/html" ]; then
    # MODO PRODUCCIÓN: Solo inyectar env vars
    echo "🚀 Brain GUI - Modo Producción"
    echo "Inyectando variables de entorno..."
    
    API_PUBLIC_URL=${API_PUBLIC_URL:-http://localhost:8000}
    STRAPI_PUBLIC_URL=${STRAPI_PUBLIC_URL:-http://localhost:1337}
    OLLAMA_URL=${OLLAMA_URL:-http://localhost:11434}
    
    # Crear env.js con las variables de entorno
    mkdir -p /usr/share/nginx/html/browser/assets
    cat > /usr/share/nginx/html/browser/assets/env.js << EOF
(function(window) {
  window['env'] = window['env'] || {};
  window['env']['apiUrl'] = '${API_PUBLIC_URL}/api/v1';
  window['env']['strapiUrl'] = '${STRAPI_PUBLIC_URL}';
  window['env']['strapiApiUrl'] = '${STRAPI_PUBLIC_URL}/api';
  window['env']['ollamaDefaultUrl'] = '${OLLAMA_URL}';
})(this);
EOF
    
    echo "✅ Variables inyectadas:"
    echo "   API: ${API_PUBLIC_URL}"
    echo "   Strapi: ${STRAPI_PUBLIC_URL}"
    echo "   Ollama: ${OLLAMA_URL}"
    
else
    # MODO DESARROLLO: Gestionar proyecto Angular
    echo "🔧 Brain GUI - Modo Desarrollo"
    
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
fi

# Ejecutar el comando pasado
exec "$@"
