#!/usr/bin/env python3
"""
Suscriptor MQTT que evalúa umbrales sobre los datos de sensores
publicados en sensors/<device>/data y envía un correo de alerta
cuando algún valor los supera.

Encaja con el stack ioT_emqx que ya tienes:
    sensors/<device>/data  (JSON: device, sound_level, air_quality, power)

Configuración: todo se lee de variables de entorno (.env), nunca
hardcodeado en el script.
"""

import json
import os
import smtplib
import ssl
import time
from email.mime.text import MIMEText

from dotenv import load_dotenv
import paho.mqtt.client as mqtt

load_dotenv()  # carga las variables definidas en .env

# --- Bróker MQTT -------------------------------------------------------
MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1884"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "sensors/#")

# --- Umbrales -----------------------------------------------------------
SOUND_MAX = float(os.getenv("SOUND_MAX", "70"))       # decibeles (dB)
AIR_QUALITY_MAX = float(os.getenv("AIR_QUALITY_MAX", "1000"))  # ppm de CO2
POWER_MAX = float(os.getenv("POWER_MAX", "1500"))     # vatios (W)

# --- Correo (SMTP / Gmail) -------------------------------------------------
# Para Gmail: SMTP_USER es tu cuenta de Gmail y SMTP_PASSWORD debe ser una
# "contraseña de aplicación" (https://myaccount.google.com/apppasswords),
# no la contraseña normal de la cuenta.
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# Lista de destinatarios: un correo por línea en este archivo .txt.
# Líneas vacías o que empiecen con # se ignoran.
ALERT_RECIPIENTS_FILE = os.getenv("ALERT_RECIPIENTS_FILE", "destinatarios.txt")

# Evita mandar un correo por cada mensaje: espera este tiempo entre
# alertas del mismo dispositivo+métrica.
ALERT_COOLDOWN = float(os.getenv("ALERT_COOLDOWN", "300"))

_last_alert: dict[str, float] = {}


def cargar_destinatarios(path: str) -> list[str]:
    if not os.path.exists(path):
        print(f"WARN: no existe el archivo de destinatarios '{path}'")
        return []
    with open(path, encoding="utf-8") as f:
        return [
            linea.strip()
            for linea in f
            if linea.strip() and not linea.strip().startswith("#")
        ]


def enviar_alerta(asunto: str, cuerpo: str) -> None:
    destinatarios = cargar_destinatarios(ALERT_RECIPIENTS_FILE)
    if not (SMTP_USER and SMTP_PASSWORD and destinatarios):
        print("WARN: faltan credenciales SMTP o destinatarios, no se envía correo")
        return

    msg = MIMEText(cuerpo)
    msg["Subject"] = asunto
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(destinatarios)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, destinatarios, msg.as_string())
        print(f">> Alerta enviada por correo a {len(destinatarios)} destinatario(s): {asunto}")
    except Exception as e:
        print(f"ERROR enviando correo: {e}")


def _disparar_alerta(device, topic, campo, nombre, valor, detalle):
    clave = f"{device}:{campo}"
    ahora = time.time()
    if ahora - _last_alert.get(clave, 0) < ALERT_COOLDOWN:
        return  # todavía en cooldown, no repetir alerta

    _last_alert[clave] = ahora
    fecha = time.strftime("%Y-%m-%d %H:%M:%S %z")
    asunto = f"Alerta: {nombre} {valor} en {device}"
    cuerpo = (
        f"El sensor {device} reportó {nombre} de {valor}, {detalle}.\n\n"
        f"Fecha:  {fecha}\n"
        f"Topic:  {topic}\n"
        f"Broker: {MQTT_HOST}:{MQTT_PORT}\n"
        f"— 170304004-2: Grupo 3, Programación Avanzada\n"
    )
    print(f"!! {asunto}")
    enviar_alerta(asunto, cuerpo)


def evaluar_umbrales(device: str, topic: str, data: dict) -> None:
    # modo "max": alerta si valor > umbral. modo "min": alerta si valor < umbral.
    checks = [
        ("sound_level", SOUND_MAX, "nivel de sonido", "max"),
        ("air_quality", AIR_QUALITY_MAX, "calidad del aire (CO2)", "max"),
        ("power", POWER_MAX, "consumo eléctrico", "max"),
    ]

    for campo, umbral, nombre, modo in checks:
        valor = data.get(campo)
        if valor is None:
            continue
        fuera_de_rango = valor > umbral if modo == "max" else valor < umbral
        if not fuera_de_rango:
            continue

        relacion = "por encima" if modo == "max" else "por debajo"
        _disparar_alerta(
            device, topic, campo, nombre, valor,
            f"{relacion} del umbral de {umbral}"
        )


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"ERROR: EMQX rechazó la conexión: {reason_code}")
        return
    print(f">> Conectado a {MQTT_HOST}:{MQTT_PORT}, suscrito a {MQTT_TOPIC}")
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        print(f"WARN: payload no es JSON válido en {msg.topic}")
        return

    device = data.get("device", msg.topic)
    print(f"[{time.strftime('%H:%M:%S')}] {device} -> {data}")
    evaluar_umbrales(device, msg.topic, data)


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=10)

    client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDetenido.")
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()