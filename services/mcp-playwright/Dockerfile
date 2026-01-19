# ===========================================
# MCP Playwright Server
# Servidor MCP para control de navegador Chrome/Chromium
# ===========================================
FROM node:20-slim

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive

# Variables de configuración
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV MCP_PORT=3001
ENV MCP_HEADLESS=true

WORKDIR /app

# Instalar dependencias del sistema para Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dependencias de Chromium
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    fonts-liberation \
    fonts-noto-color-emoji \
    # Utilidades
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Instalar @playwright/mcp globalmente
RUN npm install -g @anthropic-ai/mcp-server-playwright@latest || \
    npm install -g @playwright/mcp@latest || \
    npm install -g playwright-mcp-server@latest

# Instalar navegadores de Playwright
RUN npx playwright install chromium && \
    npx playwright install-deps chromium

# Copiar script de entrada
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Puerto del servidor MCP
EXPOSE 3001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${MCP_PORT}/health || exit 1

# Comando de inicio
ENTRYPOINT ["/app/entrypoint.sh"]
