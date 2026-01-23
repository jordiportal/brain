#!/bin/bash

# Script para migrar brain-chains del Strapi local al remoto
# Uso: ./migrate-brain-chains.sh <STRAPI_LOCAL_URL> <STRAPI_REMOTE_URL> <API_TOKEN>

STRAPI_LOCAL=${1:-http://localhost:1337}
STRAPI_REMOTE=${2:-http://192.168.7.103:1337}
API_TOKEN=${3}

echo "🔍 Obteniendo brain-chains desde $STRAPI_LOCAL..."

# Exportar datos del Strapi local
LOCAL_DATA=$(curl -s "${STRAPI_LOCAL}/api/brain-chains?populate=*" \
  -H "Authorization: Bearer ${API_TOKEN}")

# Guardar en archivo temporal
echo "$LOCAL_DATA" > /tmp/brain-chains-export.json

# Contar registros
COUNT=$(echo "$LOCAL_DATA" | jq '.data | length')
echo "✅ Se encontraron $COUNT registros"

if [ "$COUNT" -eq 0 ]; then
  echo "❌ No hay registros para migrar"
  exit 1
fi

# Mostrar los registros
echo ""
echo "📋 Registros a migrar:"
echo "$LOCAL_DATA" | jq -r '.data[] | "\(.id) - \(.attributes.name)"'

echo ""
echo "🚀 ¿Quieres importarlos al servidor remoto ($STRAPI_REMOTE)? (y/n)"
read -r CONFIRM

if [ "$CONFIRM" != "y" ]; then
  echo "❌ Importación cancelada"
  exit 0
fi

echo ""
echo "🔄 Importando a $STRAPI_REMOTE..."

# Importar cada registro
echo "$LOCAL_DATA" | jq -c '.data[]' | while read -r item; do
  NAME=$(echo "$item" | jq -r '.attributes.name')
  ATTRS=$(echo "$item" | jq '.attributes')
  
  echo "   → Importando: $NAME"
  
  # Crear el registro en el servidor remoto
  RESPONSE=$(curl -s -X POST "${STRAPI_REMOTE}/api/brain-chains" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"data\": $ATTRS}")
  
  # Verificar resultado
  if echo "$RESPONSE" | jq -e '.data.id' > /dev/null 2>&1; then
    ID=$(echo "$RESPONSE" | jq -r '.data.id')
    echo "   ✅ Creado con ID: $ID"
  else
    echo "   ❌ Error: $(echo "$RESPONSE" | jq -r '.error.message // "Unknown error"')"
  fi
done

echo ""
echo "✅ Migración completada"
