# Sistema de Reservas Institucionales ITM — Documentación integral

> Documentación técnica y funcional. Este repositorio es un prototipo académico; no implica despliegue ni aprobación oficial del ITM.

## Descripción y problema
El proyecto digitaliza las reservas de espacios y módulos institucionales. Centraliza solicitudes, horarios, ocupación, usuarios, roles, cancelaciones, historial y correos de notificación. Evita que los módulos se asignen a reservas superpuestas mediante validaciones de aplicación y una restricción de exclusión en PostgreSQL.

## Arquitectura de una petición
1. El navegador presenta HTML, CSS y JavaScript y envía solicitudes HTTP.
2. Gunicorn recibe las solicitudes y, mediante la interfaz WSGI, ejecuta Flask.
3. Flask valida sesión, permisos, reglas de reserva y datos recibidos.
4. `psycopg2` consulta PostgreSQL con parámetros SQL; la base conserva la información.
5. Flask devuelve HTML o JSON; el módulo `correo.py` permite notificaciones SMTP/TLS.
6. Docker Compose inicia y conecta los servicios `web`, `db` y `pgadmin`.

**Conceptos:** Flask es el framework del servidor; PostgreSQL es el gestor de datos; WSGI es una interfaz entre Gunicorn y Flask, no una tabla; pgAdmin es una interfaz de administración; GPG firma commits de Git, no cifra la base de datos ni sustituye una licencia.

## Diseño y funcionamiento de la base de datos
- `usuarios`: correo, nombre, hash de contraseña, rol y tipo de usuario.
- `edificios`, `categorias`, `tipos_espacio`: clasificación y políticas de anticipación y duración.
- `espacios`, `horarios_espacio`, `cierres_espacio`: disponibilidad física y temporal.
- `modulos`, `recursos`, `espacio_recursos`: unidades reservables y equipamiento.
- `reservas`, `reserva_modulos`: solicitudes y módulos asociados.
- `notificaciones`: mensajes y estado de entrega.

La restricción `EXCLUDE USING gist` sobre `reserva_modulos` impide solapamientos de intervalos para un mismo módulo. El estado `finalizada` se determina por tiempo transcurrido en las vistas; la restricción SQL de `reservas.estado` contempla `confirmada` y `cancelada`.

## Ciberseguridad: controles y límites reales
**Incluido en el ZIP:** hashes de contraseñas mediante Werkzeug, consultas parametrizadas, autorización por rol consultando PostgreSQL, token CSRF en operaciones administrativas, `.gitignore` y puertos Docker enlazados a `127.0.0.1`.

**Pendiente antes de producción:** sustituir la clave secreta de respaldo (`cambia-esto`) por una clave obligatoria, proteger globalmente los formularios, limitar intentos de inicio de sesión, endurecer cookies y cabeceras, desplegar HTTPS, realizar pruebas automatizadas y mantener copias de seguridad verificadas. El cierre de sesión usa GET en esta versión.

**Advertencia:** el ZIP de origen incluye `.env`. Nunca lo publiques; si las credenciales fueron compartidas, cámbialas. No subas bases de datos, respaldos ni claves GPG privadas. Las firmas GPG de commits autentican la clave firmante, pero no acreditan por sí solas titularidad legal del software.

## Verificación y pruebas recomendadas
- Registro con correo del dominio configurado y rechazo de dominios no autorizados.
- Inicio/cierre de sesión y permisos de usuario, administrador y superadministrador.
- Reserva de módulo libre y rechazo de solapamiento de horario.
- Cancelación y actualización del panel de ocupación.
- Pestañas administrativas, creación de módulos y eliminación controlada de historial.
- SMTP con cuenta de prueba y revisión de logs sin revelar secretos.
- Restauración de un respaldo en una base separada.

**Estado de comprobación:** se inspeccionó el código y la estructura del ZIP; no se ejecutaron pruebas funcionales con Docker ni pruebas de penetración.

---

# Sistema de Reservas de Espacios ITM

Aplicación web para gestionar la reserva de espacios institucionales y sus módulos, consultar la ocupación y administrar usuarios, espacios y el historial de reservas.

## 1. Tecnologías

| Componente | Tecnología | Función |
|---|---|---|
| Aplicación web | Python 3.12 y Flask 3.0.3 | Rutas, sesiones, validaciones y lógica de negocio |
| Servidor web | Gunicorn 23.0.0 (WSGI) | Ejecución de Flask dentro del contenedor |
| Base de datos | PostgreSQL 16 | Persistencia de usuarios, espacios y reservas |
| Administración de BD | pgAdmin 4 | Consulta y administración de PostgreSQL |
| Interfaz | HTML, CSS y JavaScript | Formularios, pestañas y panel de ocupación |
| Notificaciones | SMTP con TLS | Correos de confirmación y cancelación |
| Despliegue | Docker y Docker Compose | Ejecución coordinada de servicios |

## 2. Funcionalidades

### Usuarios

- Registro e inicio de sesión mediante correo institucional configurado en `DOMINIO_INSTITUCIONAL`.
- Tipos de usuario: estudiante, docente, empleado y egresado.
- Consulta de disponibilidad de espacios y módulos.
- Creación de reservas, con validación de horarios y conflictos.
- Consulta de **Mis reservas** e **Historial**.
- Cancelación de reservas permitidas, con liberación de los módulos reservados.
- Horarios presentados al usuario en formato de **12 horas (a. m./p. m.)**, con referencia horaria de Colombia.

### Panel de ocupación

- Porcentaje de módulos ocupados en el momento de consulta.
- Indicadores de espacios en uso y reservas del día.
- Disponibilidad por espacio y por módulo.
- Gráficas de ocupación durante el día y reservas próximas.
- Actualización periódica desde el navegador mediante `/api/ocupacion`.

### Panel administrativo (`/admin`)

El panel está organizado en cuatro pestañas independientes:

1. **Reservas:** consulta y cancelación de reservas futuras.
2. **Usuarios:** consulta de cuentas, gestión de roles y eliminación cuando está permitida.
3. **Espacios:** creación, edición, activación, desactivación, eliminación de espacios sin reservas asociadas y creación de módulos.
4. **Historial:** consulta de reservas canceladas o finalizadas. El superadministrador puede eliminar registros seleccionados, todas las canceladas o todas las finalizadas, previa confirmación.

La eliminación del historial es **definitiva** y puede eliminar notificaciones relacionadas. Haz un respaldo antes de usarla.

## 3. Roles y permisos

| Acción | Usuario | Administrador | Superadministrador |
|---|:---:|:---:|:---:|
| Crear y consultar sus reservas | Sí | Sí | Sí |
| Consultar panel administrativo | No | Sí | Sí |
| Consultar y cancelar reservas desde administración | No | Sí | Sí |
| Crear, editar y habilitar/deshabilitar espacios | No | Sí | Sí |
| Agregar módulos | No | Sí | Sí |
| Cambiar roles | No | No | Sí |
| Eliminar usuarios y espacios elegibles | No | No | Sí |
| Eliminar registros históricos | No | No | Sí |

Las operaciones administrativas se validan en Flask y utilizan protección CSRF. Las eliminaciones de usuarios y espacios se restringen cuando existen reservas asociadas para preservar la integridad de los datos.

## 4. Estructura del proyecto

```text
reservas-docker/
├── .env.example               # Ejemplo de variables; no contiene secretos reales
├── .gitignore                 # Archivos que Git no debe publicar
├── docker-compose.yml         # Servicios PostgreSQL, pgAdmin y web
├── ADMINISTRACION.md          # Notas adicionales del panel administrativo
├── db/
│   ├── 00_extensiones.sql     # Extensiones PostgreSQL
│   ├── 01_schema.sql          # Tablas y relaciones
│   ├── 02_reglas.sql          # Restricciones y reglas de datos
│   └── 03_datos.sql           # Datos iniciales de demostración
├── pgadmin/
│   └── servers.json           # Configuración inicial de conexión
└── web/
    ├── app.py                 # Aplicación Flask y rutas
    ├── correo.py              # Envío de correo SMTP
    ├── migrate_roles.py       # Migraciones de roles al iniciar
    ├── gunicorn.conf.py       # Configuración del servidor WSGI
    ├── Dockerfile             # Imagen del servicio web
    ├── requirements.txt       # Dependencias Python
    ├── templates/             # Plantillas HTML y Jinja2
    └── static/                # CSS y JavaScript
```

## 5. Requisitos

- Docker Desktop con Docker Compose habilitado.
- Puertos locales **5000**, **5050** y **5432** disponibles.
- Un navegador web moderno.
- Opcional: cuenta de Gmail con contraseña de aplicación para las notificaciones SMTP.

## 6. Configuración del entorno

Abre una terminal en la carpeta `reservas-docker` y crea el archivo `.env` a partir de `.env.example`.

En PowerShell:

```powershell
Copy-Item .env.example .env
```

Completa las variables con tus valores reales:

```dotenv
# PostgreSQL: conserva la contraseña original si ya existe un volumen con datos.
POSTGRES_USER=postgres
POSTGRES_PASSWORD=CAMBIA_ESTA_CLAVE
POSTGRES_DB=reservas

# Acceso a pgAdmin.
PGADMIN_EMAIL=admin@demo.com
PGADMIN_PASSWORD=CAMBIA_ESTA_CLAVE

# Sesiones de Flask: utiliza una clave larga y aleatoria.
SECRET_KEY=CAMBIA_ESTA_CLAVE

# Dominio de correo autorizado para registrar usuarios.
DOMINIO_INSTITUCIONAL=@correo.itm.edu.co

# Gmail SMTP: contraseña de aplicación, no contraseña habitual de Gmail.
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_correo@gmail.com
SMTP_PASSWORD=TU_CLAVE_DE_APLICACION
SMTP_FROM=tu_correo@gmail.com
SMTP_FROM_NAME=Sistema de Reservas ITM
```

**Seguridad:** nunca publiques `.env` en GitHub. El nombre `SMTP_FROM_NAME` cambia el nombre mostrado del remitente, pero **no oculta** la dirección real de Gmail. Para enviar desde una dirección institucional es necesario contar con una cuenta o alias autorizado.

## 7. Instalación y ejecución

Desde `reservas-docker`:

```powershell
# Valida la configuración de Compose.
docker compose config --quiet

# Construye e inicia los servicios en segundo plano.
docker compose up -d --build

# Comprueba el estado de los contenedores.
docker compose ps

# Muestra los registros del servicio web.
docker compose logs -f web
```

Direcciones locales:

| Servicio | URL |
|---|---|
| Aplicación ITM | http://localhost:5000 |
| Inicio de sesión | http://localhost:5000/login |
| Panel administrativo | http://localhost:5000/admin |
| Panel de ocupación | http://localhost:5000/ocupacion |
| pgAdmin | http://localhost:5050 |

Los puertos están publicados en `127.0.0.1`: el acceso está limitado al equipo local salvo cambios explícitos en Docker Compose.

Para detener los contenedores sin borrar los volúmenes:

```powershell
docker compose down
```

**No ejecutes `docker compose down -v`** si deseas conservar la base de datos.

## 8. Base de datos

Las tablas principales incluyen:

- `usuarios`: identificación, correo, hash de contraseña, tipo de usuario y rol.
- `edificios`, `categorias`, `tipos_espacio` y `espacios`: clasificación y ubicación de espacios.
- `modulos`: unidades reservables dentro de cada espacio.
- `horarios_espacio` y `cierres_espacio`: disponibilidad y cierres.
- `reservas` y `reserva_modulos`: reservas y módulos asignados.
- `notificaciones`: estado, intentos y resultados del envío de correos.

Los scripts de `db/` se ejecutan al inicializar un **volumen PostgreSQL nuevo**. No vuelven a ejecutarse automáticamente sobre una base de datos existente. `migrate_roles.py` se ejecuta al iniciar el servicio web.

### Acceder a PostgreSQL

```powershell
docker compose exec db psql -U postgres -d reservas
```

Si cambiaste `POSTGRES_USER` o `POSTGRES_DB`, sustituye esos valores en el comando.

### Asignar el primer superadministrador

Primero registra la cuenta desde la interfaz y luego, desde pgAdmin o `psql`, ejecuta:

```sql
-- Sustituye el correo por el de la cuenta que ya registraste.
UPDATE usuarios
SET rol = 'superadministrador'
WHERE correo = 'cuenta@correo.itm.edu.co'
RETURNING id, correo, rol;
```

Cierra sesión y vuelve a ingresar para acceder al panel con los permisos actualizados. No conviertas en superadministrador a usuarios que no deban gestionar el sistema.

## 9. Envío de correos

El archivo `web/correo.py` gestiona la conexión SMTP. `web/app.py` registra las notificaciones relacionadas con las reservas y dispone de un mecanismo de reintentos de envío, con un máximo configurado de **tres intentos**.

Para diagnosticar errores:

```powershell
docker compose logs --tail=100 web
```

Verifica que el contenedor reciba `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` y `SMTP_FROM_NAME`. No imprimas ni compartas el contenido de `SMTP_PASSWORD`.

## 10. Respaldo de PostgreSQL

Para crear un respaldo SQL desde PowerShell:

```powershell
# Crea la carpeta local de respaldos si no existe.
New-Item -ItemType Directory -Force backups | Out-Null

# Exporta la base de datos en un archivo SQL.
docker compose exec -T db pg_dump -U postgres -d reservas -f /dev/stdout > backups/reservas.sql
```

Para bases de datos grandes o respaldos de producción, conviene utilizar el formato personalizado de `pg_dump` y probar periódicamente la restauración en un entorno separado. Protege los archivos de respaldo porque pueden contener información de usuarios.

## 11. Seguridad y buenas prácticas

- Las contraseñas de usuarios se almacenan como **hash**, no en texto plano.
- Las consultas SQL de la aplicación utilizan parámetros para datos variables.
- El servidor verifica la sesión y los roles antes de operaciones administrativas.
- Los formularios administrativos incorporan comprobaciones CSRF.
- `if __name__ == "__main__":` evita iniciar el servidor Flask al importar directamente `app.py`.
- `gunicorn` importa el objeto `app` como aplicación WSGI.
- Las reservas canceladas no deben contar como ocupación activa.
- Se recomienda habilitar **HTTPS**, cookies seguras, políticas de contraseñas más estrictas, limitación de intentos de acceso, respaldos y supervisión antes de desplegar en producción.

Estas medidas no sustituyen una auditoría de seguridad. La configuración actual está orientada principalmente a ejecución local o demostración.

## 12. Problemas frecuentes

**Docker advierte que `POSTGRES_PASSWORD` o `SECRET_KEY` no están definidas.** Verifica que `.env` exista junto a `docker-compose.yml`, no como `.env.txt`, y ejecuta `docker compose config --quiet`.

**`password authentication failed for user "postgres"`.** La contraseña del volumen PostgreSQL existente puede ser distinta de la indicada en `.env`. No borres el volumen: sincroniza las credenciales con cuidado.

**No se envían correos.** Comprueba la contraseña de aplicación de Gmail, las variables SMTP y los registros de `web`.

**No aparecen las pestañas nuevas.** Reconstruye el contenedor y actualiza el navegador con `Ctrl + F5` para evitar archivos JavaScript almacenados en caché.

**No puedo eliminar un usuario o espacio.** Revisa el rol de la cuenta y si el registro tiene reservas asociadas. Es una restricción deliberada para proteger la integridad de los datos.

**Una reserva aparece finalizada antes de tiempo.** Comprueba que el servidor y las comparaciones utilicen correctamente la hora de Colombia (`America/Bogota`).

## 13. Alcance y observaciones

Este README describe la versión del proyecto que incluye el panel administrativo por pestañas y las opciones de eliminación del historial. Las operaciones destructivas deben probarse primero con datos de demostración y un respaldo reciente. Las contraseñas de ejemplo **no son adecuadas para producción**.

---

**Proyecto académico:** Sistema de Reservas de Espacios ITM.
