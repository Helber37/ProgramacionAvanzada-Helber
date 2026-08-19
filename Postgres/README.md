# PostgreSQL & pgadmin4

Este es un proyecto que utiliza Docker Compose para configurar y ejecutar servicios de PostgreSQL y pgAdmin4.

## Descripción

Este proyecto configura un entorno de base de datos PostgreSQL y una herramienta de administración pgAdmin4 utilizando Docker Compose. Los servicios se configuran para funcionar juntos, permitiéndote administrar tu base de datos PostgreSQL a través de la interfaz gráfica de pgAdmin4.

## Requisitos

- Docker
- Docker Compose

## Configuración

1. Clona este repositorio:

   ```bash
   git clone https://github.com/Navarrojuan212/PostgreSQL.git
   cd PostgreSQL
   ```

2. Crea un archivo `.env` en el directorio raíz del proyecto con el siguiente contenido:
   ```bash
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_postgres_password
   POSTGRES_DB=pgdatabase
   PGADMIN_DEFAULT_EMAIL=admin@example.com
   PGADMIN_DEFAULT_PASSWORD=your_pgadmin_password	
   ```
>[!IMPORTANT]
> Reemplaza `your_postgres_password` y `your_pgadmin_password` con las contraseñas deseadas.

3. Levanta los servicios utilizando Docker Compose:
   ```bash
   docker-compose up -d
   ```
## Uso

1. Accede a pgAdmin4 en tu navegador web:
   ```bash 
   http://localhost:8080
   ``` 

2. Inicia sesión con el correo y la contraseña que configuraste en el archivo `.env` (`PGADMIN_DEFAULT_EMAIL` y `PGADMIN_DEFAULT_PASSWORD`).

3. Agrega un nuevo servidor en pgAdmin4 para conectar a PostgreSQL:

   - **Nombre:** PostgreSQL Server
   - **Host name/address:** postgres_container
   - **Port:** 5432
   - **Maintenance database:** postgres
   - **Username:** postgres
   - **Password:** la contraseña que configuraste en `POSTGRES_PASSWORD`

## Estructura del Proyecto
- `docker-compose.yml`: Archivo de configuración de Docker Compose para definir y ejecutar los servicios.
- `.env`: Archivo de configuración de entorno (no incluido en el repositorio por razones de seguridad, debes crearlo manualmente).

