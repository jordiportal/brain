#!/bin/bash

# Esperar a que Xvfb esté listo
sleep 2

echo "Starting Chromium with CDP on port 9222..."

# Limpiar perfil anterior para evitar múltiples ventanas
rm -rf /tmp/chrome-profile 2>/dev/null

# Iniciar Chromium con CDP habilitado - maximizado
exec /usr/bin/chromium \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --disable-software-rasterizer \
    --remote-debugging-port=9222 \
    --remote-debugging-address=0.0.0.0 \
    --remote-allow-origins=* \
    --start-maximized \
    --user-data-dir=/tmp/chrome-profile \
    --disable-background-networking \
    --disable-default-apps \
    --disable-extensions \
    --disable-sync \
    --disable-translate \
    --no-first-run \
    --safebrowsing-disable-auto-update \
    --disable-infobars \
    "about:blank"
