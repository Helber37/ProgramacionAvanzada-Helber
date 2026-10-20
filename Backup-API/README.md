# gdrive-backup (CLI)

Script en Python para **subir un archivo** a una carpeta específica de **Google Drive** usando OAuth (aplicación de escritorio/CLI) y configuración vía variables de entorno (`python-dotenv`). Útil para **simular un proceso de backup**.

## Características
- Autenticación OAuth 2.0 con `client_secret.json` (flujo Desktop).
- Gestión de credenciales persistentes en `token.json` (auto-refresh).
- Lectura de configuración desde `.env` (incluye `DRIVE_FOLDER_ID`).
- Subida **resumible** y salida por consola (incluye URL del archivo).
- Compatible con **Raspberry Pi** / entornos sin GUI (modo consola).

---

## Requisitos

- **Python** 3.8+  
- **Poetry** 1.6+ (recomendado) — https://python-poetry.org/
- Acceso a **Google Cloud Console** para habilitar la API y crear credenciales OAuth.

### Habilitar Google Drive API y credenciales
1. Crea o usa un proyecto en Google Cloud Console.
2. Habilita **Google Drive API**.
3. Configura la **pantalla de consentimiento OAuth**.
4. Crea credenciales: **ID de cliente de OAuth** → **Aplicación de escritorio**.
5. Descarga el JSON y guárdalo como `client_secret.json` (o la ruta que definas en `.env`).

> Si tu proyecto está en modo *Testing*, los *refresh tokens* pueden expirar a los **7 días**. Para usos prolongados, publica el proyecto (*In production*).

---

## Estructura sugerida

```
.
├── gdrive_backup.py
├── README.md
├── .env                    # configuración local (NO subir a git)
├── client_secret.json      # credenciales OAuth (NO subir a git)
├── token.json              # se genera tras autorizar (NO subir a git)
└── requirements.txt
```

### `.gitignore` recomendado
```
.env
client_secret.json
token.json
__pycache__/
*.pyc
```

---

## Instalación con Poetry

```bash
# 1) Crear/activar el entorno del proyecto (si aún no existe)
poetry init -n  # o usa tu pyproject.toml existente

# 2) Añadir dependencias
poetry add google-api-python-client google-auth-httplib2 google-auth-oauthlib python-dotenv

# 3) (Opcional) Exportar un requirements.txt bloqueado para pip/CI
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

> También puedes instalar con `pip` usando el `requirements.txt` incluido en este repo.

---

## Configuración

Crea un archivo `.env` en la raíz del proyecto (o copia de `.env.example`):

```dotenv
# ID de la carpeta de destino en Google Drive (obligatorio)
DRIVE_FOLDER_ID=1AbCDefGhIJkLmNoPqRstuVwxyz12345

# Rutas a credenciales y token (obligatorio CLIENT_SECRET_FILE)
CLIENT_SECRET_FILE=./client_secret.json
TOKEN_FILE=./token.json

# Scope por defecto (amplio). Puedes restringir a drive.file si lo prefieres.
GOOGLE_SCOPES=https://www.googleapis.com/auth/drive
# GOOGLE_SCOPES=https://www.googleapis.com/auth/drive.file

# Headless / Raspberry Pi: usa flujo por consola
USE_CONSOLE_AUTH=false   # en Raspberry Pi: true
OAUTH_PORT=0             # 0 = puerto aleatorio
```

> **Consejo de permisos (Unix):**
> ```bash
> chmod 600 client_secret.json token.json 2>/dev/null || true
> ```

---

## Uso

Ejecuta el script con Poetry:

```bash
poetry run python gdrive_backup.py
```

El programa te pedirá por terminal la **ruta completa** del archivo local a subir.  
Al finalizar, mostrará algo como:

```
✅ Subida exitosa
  • Nombre: backup_2025-11-03.zip
  • ID: 1x2y3z...
  • URL (ver en Drive): https://drive.google.com/file/d/1x2y3z.../view
  • URL (descarga directa): https://drive.google.com/uc?id=1x2y3z...
```

---

## Raspberry Pi / entornos sin navegador

En `.env`:
```
USE_CONSOLE_AUTH=true
OAUTH_PORT=0
```

Si el `token.json` ya existe y es válido, **no se te pedirá** reautorización.  
Si necesitas reautenticar, el flujo por consola te mostrará una URL y un **código** para pegar.

---

## Errores comunes y soluciones

- **`[ERROR] El archivo no existe...`**  
  Revisa la ruta ingresada y permisos del archivo local.

- **`invalid_grant` / problemas de autenticación**  
  Puede ser un token vencido o revocado. Elimina `token.json` y vuelve a ejecutar para reautorizar.

- **Carpeta inaccesible**  
  Verifica `DRIVE_FOLDER_ID` y tus permisos en esa carpeta (incluidas Unidades compartidas).

- **Hora del sistema incorrecta (TLS/refresh fallan)**  
  Asegúrate de tener NTP activo y la hora correcta (importante en la Raspberry Pi).

---

## Seguridad

- No subas `client_secret.json`, `token.json` ni `.env` a repos públicos.
- Restringe permisos de archivos sensibles (`chmod 600`).
- Considera usar el *scope* restringido `drive.file` si te basta con gestionar solo los archivos creados por la app.

---

## Licencia

Este proyecto se entrega “tal cual”. Ajusta y reutiliza el código bajo tu criterio en tu entorno.
