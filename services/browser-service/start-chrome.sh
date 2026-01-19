#!/bin/bash

# Esperar a que Xvfb esté listo
sleep 2

echo "Starting Chromium with CDP on port 9222..."

# Iniciar Chromium con CDP habilitado
exec /usr/bin/chromium \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --disable-software-rasterizer \
    --remote-debugging-port=9222 \
    --remote-debugging-address=0.0.0.0 \
    --remote-allow-origins=* \
    --window-size=1280,720 \
    --window-position=0,0 \
    --user-data-dir=/tmp/chrome-profile \
    --disable-background-networking \
    --disable-default-apps \
    --disable-extensions \
    --disable-sync \
    --disable-translate \
    --no-first-run \
    --safebrowsing-disable-auto-update \
    "about:blank"
