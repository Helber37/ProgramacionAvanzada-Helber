#!/bin/bash
# Respalda el volumen de VictoriaMetrics (histórico de datos de sensores)
# en un .tar.gz local. Ajusta VOLUME_DATA con el nombre real que veas
# en 'docker volume ls'.

set -e

VOLUME_DATA="ioT_emqx_victoria_data"
FECHA=$(date +%Y-%m-%d_%H-%M)
SALIDA="./backups"

mkdir -p "$SALIDA"

echo "Respaldando volumen: $VOLUME_DATA ..."
docker run --rm \
  -v "${VOLUME_DATA}:/data:ro" \
  -v "$(pwd)/${SALIDA}:/backup" \
  alpine \
  tar czf "/backup/victoria_data_${FECHA}.tar.gz" -C /data .

echo ""
echo "✅ Backup completo en $SALIDA/"
ls -lh "$SALIDA"/*"${FECHA}"*
