# ===========================================
# Browser Service - Chrome + noVNC + CDP
# Navegador visual accesible desde la web
# ===========================================
FROM node:20-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV CHROME_FLAGS="--no-sandbox --disable-dev-shm-usage --disable-gpu --window-size=1280,720"

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    # X11 Virtual Framebuffer
    xvfb \
    # VNC Server
    x11vnc \
    # Window Manager ligero
    fluxbox \
    # noVNC y websockify
    novnc \
    websockify \
    # Chromium y dependencias
    chromium \
    # Utilidades
    supervisor \
    procps \
    curl \
    # Para proxy de CDP
    socat \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio para logs
RUN mkdir -p /var/log/supervisor

# Configuración de supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Script de inicio de Chrome con CDP
COPY start-chrome.sh /app/start-chrome.sh
RUN chmod +x /app/start-chrome.sh

# Puertos:
# 6080 - noVNC (web interface)
# 5900 - VNC directo
# 9222 - Chrome DevTools Protocol (interno)
# 9223 - CDP Proxy (accesible externamente via socat)
EXPOSE 6080 5900 9222 9223

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:9222/json/version || exit 1

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
