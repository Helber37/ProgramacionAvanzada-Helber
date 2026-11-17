"""Envío de correos SMTP independiente de Flask y PostgreSQL."""
import os  # Lee la configuración del entorno del contenedor.
import smtplib  # Abre la conexión con Gmail SMTP.
import ssl  # Verifica certificados y cifra la comunicación.
from email.message import EmailMessage  # Construye el mensaje MIME.
from email.utils import formataddr  # Añade un nombre visible al remitente.


def enviar_correo(destinatario, asunto, mensaje):
    """Envía un correo mediante SMTP autenticado con STARTTLS."""
    host = os.environ["SMTP_HOST"]  # Servidor SMTP configurado.
    puerto = int(os.getenv("SMTP_PORT", "587"))  # Puerto STARTTLS.
    usuario = os.environ["SMTP_USER"]  # Cuenta que autentica el envío.
    clave = os.environ["SMTP_PASSWORD"]  # Contraseña de aplicación de Google.
    remitente = os.getenv("SMTP_FROM") or usuario  # Dirección visible del remitente.
    if not usuario or not clave:  # Impide intentar envíos sin credenciales.
        raise ValueError("Faltan SMTP_USER o SMTP_PASSWORD en la configuración")

    correo = EmailMessage()  # Crea el correo electrónico.
    nombre = os.getenv("SMTP_FROM_NAME", "Sistema de Reservas ITM")  # Nombre institucional.
    correo["From"] = formataddr((nombre, remitente))  # Nombre y dirección autorizada.
    correo["To"] = destinatario  # Configura el destinatario.
    correo["Subject"] = asunto  # Configura el asunto.
    correo.set_content(mensaje)  # Agrega el texto del mensaje.

    with smtplib.SMTP(host, puerto, timeout=20) as servidor:  # Abre la conexión.
        servidor.ehlo()  # Identifica el cliente ante Gmail.
        servidor.starttls(context=ssl.create_default_context())  # Activa TLS verificado.
        servidor.ehlo()  # Reinicia la negociación SMTP tras TLS.
        servidor.login(usuario, clave)  # Autentica la cuenta Gmail.
        servidor.send_message(correo)  # Envía el mensaje.
