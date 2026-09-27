#!/usr/bin/env bash
# Emula 3 sensores publicando JSON al broker EMQX cada N segundos.
# Topic: sensors/<device>/data  →  lo recoge Telegraf (suscrito a sensors/#)
#                                 →  escribe en VictoriaMetrics
#                                 →  Grafana lo consulta.
#
# Requiere: mosquitto-clients   (sudo apt install -y mosquitto-clients)
# Lee credenciales MQTT_USERNAME / MQTT_PASSWORD del .env del demo.

set -euo pipefail

# --- Carga .env ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
if [ -f "$ENV_FILE" ]; then
  set -a; . "$ENV_FILE"; set +a
else
  echo "WARN: no encontré $ENV_FILE — usaré conexión anónima."
  MQTT_USERNAME="${MQTT_USERNAME:-}"
  MQTT_PASSWORD="${MQTT_PASSWORD:-}"
fi

# --- Descubrir endpoint MQTT (NodePort de EMQX, puerto 1883) ---
MQTT_HOST="${MQTT_HOST:-127.0.0.1}"
if [ -z "${MQTT_PORT:-}" ]; then
  MQTT_PORT=$(kubectl -n iot get svc emqx \
    -o jsonpath='{.spec.ports[?(@.port==1883)].nodePort}' 2>/dev/null || true)
fi
if [ -z "${MQTT_PORT:-}" ]; then
  echo "ERROR: no pude descubrir el NodePort MQTT. Define MQTT_PORT a mano."
  echo "       (mira con:  kubectl -n iot get svc emqx)"
  exit 1
fi

INTERVAL="${INTERVAL:-3}"
DEVICES=("sensor-1" "sensor-2" "sensor-3")

# Construye flags de auth solo si hay user/pass
AUTH_FLAGS=()
if [ -n "$MQTT_USERNAME" ] && [ -n "$MQTT_PASSWORD" ]; then
  AUTH_FLAGS=(-u "$MQTT_USERNAME" -P "$MQTT_PASSWORD")
fi

echo ">> Publicando a ${MQTT_HOST}:${MQTT_PORT}  (intervalo ${INTERVAL}s)"
echo ">> Topic: sensors/<device>/data | Ctrl+C para parar"
echo

trap 'echo; echo Detenido.; exit 0' INT TERM

while true; do
  for dev in "${DEVICES[@]}"; do
    sound=$(awk -v s=$RANDOM 'BEGIN { srand(s); printf "%.2f", 30 + rand()*70 }')
    air=$(awk   -v s=$RANDOM 'BEGIN { srand(s); printf "%.2f", 350 + rand()*1400 }')
    power=$(awk -v s=$RANDOM 'BEGIN { srand(s); printf "%.1f", rand()*2000 }')
    payload="{\"device\":\"$dev\",\"sound_level\":$sound,\"air_quality\":$air,\"power\":$power}"

    mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" "${AUTH_FLAGS[@]}" \
      -t "sensors/$dev/data" -m "$payload"

    printf "[%s] %-15s → %s\n" "$(date +%T)" "$dev" "$payload"
  done
  sleep "$INTERVAL"
done