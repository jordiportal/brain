# ===========================================
# Brain GUI - Angular
# ===========================================

# -----------------------------
# Stage: Development
# -----------------------------
FROM node:20-alpine AS development

WORKDIR /app

# Instalar Angular CLI globalmente
RUN npm install -g @angular/cli@17

# Copiar package.json si existe
COPY package*.json* ./

# Instalar dependencias si existen (legacy-peer-deps para ngx-graph)
RUN if [ -f package.json ]; then npm install --legacy-peer-deps; fi

# Script de inicio para desarrollo
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Puerto de desarrollo Angular
EXPOSE 4200

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["ng", "serve", "--host", "0.0.0.0", "--port", "4200", "--poll", "2000"]

# -----------------------------
# Stage: Build
# -----------------------------
FROM development AS build

COPY . .
RUN npm run build --configuration=production

# -----------------------------
# Stage: Production
# -----------------------------
FROM nginx:alpine AS production

# Copiar configuración de nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Copiar build de Angular
COPY --from=build /app/dist/brain-gui/browser /usr/share/nginx/html

# Copiar script de entrypoint para inyección de env vars
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Puerto de producción
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/nginx-health || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
