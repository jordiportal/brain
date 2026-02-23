#!/bin/bash
set -e

echo "==================================="
echo "Brain Persistent Python Runner"
echo "==================================="
echo "Workspace: ${WORKSPACE}"
echo "User: ${USER_ID:-shared}"
echo "Fecha: $(date)"
echo "==================================="

# Crear directorios si no existen
mkdir -p ${WORKSPACE}/{scripts,downloads,logs,data,media}

# Ejecutar comando pasado o supervisor
exec "$@"
