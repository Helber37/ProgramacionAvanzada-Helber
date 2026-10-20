#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
gdrive_backup.py
----------------
Sube un archivo local a una carpeta específica de Google Drive (simulación de backup).

- Autenticación OAuth usando client_secret.json (ruta definida por variable de entorno).
- Guarda/recupera credenciales en token.json (ruta definida por variable de entorno).
- Lee configuración desde .env mediante python-dotenv.
- Solicita al usuario la ruta completa del archivo a subir.
- Informa el resultado (éxito/URL o error) por consola.

Dependencias:
  pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib python-dotenv
"""

import os
import sys
import mimetypes
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


def load_config():
    """Carga configuración desde .env y valida variables esenciales."""
    load_dotenv()

    client_secret_file = os.getenv("CLIENT_SECRET_FILE", "").strip()
    token_file = os.getenv("TOKEN_FILE", "token.json").strip()
    drive_folder_id = os.getenv("DRIVE_FOLDER_ID", "").strip()

    # Permite sobreescribir scopes desde .env (opcional). Por defecto usa 'drive' completo.
    scopes_env = os.getenv(
        "GOOGLE_SCOPES",
        "https://www.googleapis.com/auth/drive.file"
    )
    scopes: List[str] = [s.strip() for s in scopes_env.split(",") if s.strip()]

    use_console_auth = os.getenv("USE_CONSOLE_AUTH", "false").lower() == "true"
    oauth_port = int(os.getenv("OAUTH_PORT", "0"))  # 0 = puerto aleatorio

    # Validaciones mínimas
    if not drive_folder_id:
        raise ValueError(
            "Falta la variable de entorno DRIVE_FOLDER_ID en el archivo .env."
        )
    if not client_secret_file:
        raise ValueError(
            "Falta la variable de entorno CLIENT_SECRET_FILE en el archivo .env."
        )

    return {
        "client_secret_file": client_secret_file,
        "token_file": token_file,
        "drive_folder_id": drive_folder_id,
        "scopes": scopes,
        "use_console_auth": use_console_auth,
        "oauth_port": oauth_port,
    }


def get_credentials(client_secret_file: str, token_file: str, scopes: List[str]) -> Credentials:
    """Obtiene credenciales, refresca si están vencidas o inicia el flujo OAuth si no existen."""
    creds: Optional[Credentials] = None

    # Cargar token si existe
    if Path(token_file).exists():
        try:
            creds = Credentials.from_authorized_user_file(token_file, scopes)
        except Exception:
            creds = None

    # Si no hay credenciales válidas, iniciar flujo OAuth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                # Si falla el refresh, forzamos flujo nuevo
                creds = None

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes)
            use_console_auth = os.getenv("USE_CONSOLE_AUTH", "false").lower() == "true"
            oauth_port = int(os.getenv("OAUTH_PORT", "0"))

            if use_console_auth:
                # Autenticación por consola (útil en servidores sin navegador/Bastion)
                creds = flow.run_console(prompt="consent")
            else:
                # Abre el navegador local para consentimiento
                creds = flow.run_local_server(port=oauth_port, prompt="consent")

        # Guardar/actualizar token
        try:
            Path(token_file).parent.mkdir(parents=True, exist_ok=True)
            with open(token_file, "w", encoding="utf-8") as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"[ADVERTENCIA] No se pudo guardar el token en '{token_file}': {e}")

    return creds


def build_drive_service(creds: Credentials):
    """Construye el cliente de la API de Drive."""
    return build("drive", "v3", credentials=creds)


def upload_file(service, local_path: Path, folder_id: str):
    """Sube el archivo a la carpeta indicada. Retorna el dict con metadatos."""
    file_name = local_path.name
    mime_type, _ = mimetypes.guess_type(str(local_path))

    file_metadata = {
        "name": file_name,
        "parents": [folder_id],
    }

    media = MediaFileUpload(
        filename=str(local_path),
        mimetype=mime_type,
        resumable=True
    )

    request = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, webViewLink, webContentLink, parents",
        supportsAllDrives=True  # permite usar carpetas en 'Unidades compartidas'
    )

    # Progreso de subida (resumable)
    response = None
    try:
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"Subiendo... {pct}%\r", end="", flush=True)
    finally:
        print()  # salto de línea

    return response


def main():
    try:
        cfg = load_config()
        client_secret_file = cfg["client_secret_file"]
        token_file = cfg["token_file"]
        folder_id = cfg["drive_folder_id"]
        scopes = cfg["scopes"]

        # 1) Pedir la ruta del archivo al usuario
        user_input = input("Introduce la ruta COMPLETA del archivo a subir: ").strip()
        # Quitar comillas si el usuario las pegó desde el explorador
        if (user_input.startswith("'") and user_input.endswith("'")) or (user_input.startswith('"') and user_input.endswith('"')):
            user_input = user_input[1:-1]

        local_path = Path(user_input).expanduser().resolve()

        if not local_path.exists() or not local_path.is_file():
            print(f"[ERROR] El archivo no existe o no es un archivo regular: {local_path}")
            sys.exit(1)

        # 2) Autenticación
        if not Path(client_secret_file).exists():
            print(f"[ERROR] No se encontró el archivo de credenciales CLIENT_SECRET_FILE: {client_secret_file}")
            sys.exit(1)

        print("Autenticando con Google Drive...")
        creds = get_credentials(client_secret_file, token_file, scopes)
        service = build_drive_service(creds)

        # 3) Subida
        print(f"Subiendo '{local_path.name}' a la carpeta de Drive ID={folder_id} ...")
        uploaded = upload_file(service, local_path, folder_id)

        # 4) Confirmación
        if uploaded and uploaded.get("id"):
            file_id = uploaded["id"]
            web_view = uploaded.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"
            web_download = uploaded.get("webContentLink")  # puede ser None si no aplica

            print("\n✅ Subida exitosa")
            print(f"  • Nombre: {uploaded.get('name')}")
            print(f"  • ID: {file_id}")
            print(f"  • URL (ver en Drive): {web_view}")
            if web_download:
                print(f"  • URL (descarga directa): {web_download}")
        else:
            print("\n[ERROR] La API no devolvió metadatos del archivo subido.")
            sys.exit(1)

    except HttpError as e:
        print(f"\n[ERROR] Error de la API de Google Drive: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n[ERROR] Configuración inválida: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
