#!/bin/bash
set -e

echo "==================================="
echo "Brain Persistent Python Runner"
echo "==================================="
echo "Workspace: ${WORKSPACE}"
echo "Fecha: $(date)"
echo "==================================="

# Crear directorios si no existen
mkdir -p ${WORKSPACE}/{scripts,downloads,logs,data}

# Ejecutar comando pasado o supervisor
exec "$@"
