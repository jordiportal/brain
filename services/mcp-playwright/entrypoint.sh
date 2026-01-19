#!/bin/bash
set -e

echo "==================================="
echo "MCP Playwright Server Starting..."
echo "Port: ${MCP_PORT:-3001}"
echo "Headless: ${MCP_HEADLESS:-true}"
echo "==================================="

# Determinar el comando correcto basado en qué paquete está instalado
if command -v mcp-server-playwright &> /dev/null; then
    echo "Using @anthropic-ai/mcp-server-playwright"
    CMD="mcp-server-playwright"
elif npx @playwright/mcp --help &> /dev/null 2>&1; then
    echo "Using @playwright/mcp"
    CMD="npx @playwright/mcp"
elif npx playwright-mcp-server --help &> /dev/null 2>&1; then
    echo "Using playwright-mcp-server"
    CMD="npx playwright-mcp-server"
else
    echo "ERROR: No MCP Playwright server found!"
    exit 1
fi

# Construir argumentos - usar 0.0.0.0 para que sea accesible desde otros contenedores
# --allowed-hosts '*' permite conexiones desde cualquier host (necesario para Docker)
# --shared-browser-context comparte el contexto entre clientes HTTP
ARGS="--port ${MCP_PORT:-3001} --host 0.0.0.0 --headless --no-sandbox --shared-browser-context"

echo "Command: ${CMD} ${ARGS} --allowed-hosts '*'"
exec ${CMD} ${ARGS} --allowed-hosts '*'
