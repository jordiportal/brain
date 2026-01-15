# ===========================================
# Brain Strapi CMS
# ===========================================
FROM node:20-alpine

# Instalar dependencias del sistema
RUN apk add --no-cache \
    build-base \
    gcc \
    autoconf \
    automake \
    zlib-dev \
    libpng-dev \
    vips-dev \
    git

# Establecer directorio de trabajo
WORKDIR /app

# Variables de entorno para Strapi
ENV NODE_ENV=development
ENV HOST=0.0.0.0
ENV PORT=1337
ENV STRAPI_TELEMETRY_DISABLED=true

# Crear proyecto Strapi si no existe
# En primera ejecución, se generará el proyecto
COPY package*.json* ./

# Si existe package.json, instalar dependencias
RUN if [ -f package.json ]; then npm install; fi

# Script de inicio que crea Strapi si no existe
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Puerto de Strapi
EXPOSE 1337

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:1337/_health || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["npm", "run", "develop"]
