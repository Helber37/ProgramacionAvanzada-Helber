#!/usr/bin/env python3
# Emula 3 sensores publicando JSON al broker EMQX cada N segundos.
# Versión en Python de ../emulando_HA.sh (mismo topic y mismo payload).
#
# Topic: sensors/<device>/data  →  lo recoge Telegraf (suscrito a sensors/#)
#                                 →  escribe en VictoriaMetrics
#                                 →  Grafana lo consulta.
#
# Configuración por variables de entorno:
#   MQTT_HOST, MQTT_PORT            endpoint del broker
#   INTERVAL                        segundos entre rondas (default 3)
#   MQTT_USERNAME, MQTT_PASSWORD    opcionales: el EMQX del demo no tiene auth

import os
import random
import signal
import sys
import time

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1884"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
INTERVAL = float(os.getenv("INTERVAL", "3"))
DEVICES = ["sensor-1", "sensor-2", "sensor-3"]


def build_payload(dev):
    sound_level = 30 + random.random() * 70      # 30-100 dB
    air_quality = 350 + random.random() * 1400   # 350-1750 ppm CO2
    power = random.random() * 2000                # 0-2000 W
    return (
        f'{{"device":"{dev}",'
        f'"sound_level":{sound_level:.2f},'
        f'"air_quality":{air_quality:.2f},'
        f'"power":{power:.1f}}}'
    )


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"ERROR: EMQX rechazó la conexión: {reason_code}")
    else:
        print(f">> Conectado a {MQTT_HOST}:{MQTT_PORT}")


def on_connect_fail(client, userdata):
    print(f"WARN: no pude conectar a {MQTT_HOST}:{MQTT_PORT}, reintentando...")


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    print(f"WARN: desconectado del broker ({reason_code}), reintentando...")


def main():
    # docker stop envía SIGTERM: salir limpio igual que con Ctrl+C
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    # Auth solo si hay user/pass
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_connect_fail = on_connect_fail
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=10)

    print(f">> Publicando a {MQTT_HOST}:{MQTT_PORT}  (intervalo {INTERVAL:g}s)")
    print(">> Topic: sensors/<device>/data | Ctrl+C para parar")
    print()

    # connect_async + loop_start: el hilo de red reintenta la conexión solo
    client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    try:
        while True:
            if client.is_connected():
                for dev in DEVICES:
                    payload = build_payload(dev)
                    info = client.publish(f"sensors/{dev}/data", payload)
                    if info.rc != mqtt.MQTT_ERR_SUCCESS:
                        print(f"WARN: fallo publicando {dev}: {mqtt.error_string(info.rc)}")
                        continue
                    print(f"[{time.strftime('%H:%M:%S')}] {dev:<9} → {payload}")
            time.sleep(INTERVAL)
    except (KeyboardInterrupt, SystemExit):
        print()
        print("Detenido.")
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()