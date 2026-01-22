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
    git \
    wget

# Establecer directorio de trabajo
WORKDIR /app

# Variables de entorno para Strapi
# TEMPORAL: Usar development por bug en Strapi 5.x admin panel
# https://github.com/strapi/strapi/issues/24384
ENV NODE_ENV=development
ENV HOST=0.0.0.0
ENV PORT=1337
ENV STRAPI_TELEMETRY_DISABLED=true

# Crear proyecto Strapi si no existe
# En primera ejecución, se generará el proyecto
COPY package*.json* ./

# Si existe package.json, instalar dependencias
RUN if [ -f package.json ]; then npm install; fi

# Copiar código fuente (content-types, configs, etc.)
COPY src/ ./src/
COPY config/ ./config/
COPY tsconfig.json ./

# Crear directorio de uploads necesario para Strapi
RUN mkdir -p /app/public/uploads && chmod 777 /app/public/uploads

# NO construir en build time, dejar que Strapi lo haga en runtime
# Esto evita problemas con dependencias y symlinks

# Script de inicio que crea Strapi si no existe
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Puerto de Strapi
EXPOSE 1337

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:1337/admin || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
# TEMPORAL: Usar develop por bug en admin panel de Strapi 5.x
CMD ["npm", "run", "develop"]
