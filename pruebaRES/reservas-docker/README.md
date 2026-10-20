# Demo: sistema de reservas con Docker

Servicios (todo lo levanta Docker Compose):

| Servicio | URL | Acceso |
|---|---|---|
| Página web (Python/Flask) | http://localhost:5000 | demo@universidad.edu.co / demo1234 |
| pgAdmin | http://localhost:5050 | admin@demo.com / admin |
| Correos (Mailpit) | http://localhost:8025 | sin clave |
| PostgreSQL | localhost:5432 | postgres / postgres, base `reservas` |

## Ejecutar
```
docker compose up --build
```
La primera vez PostgreSQL ejecuta en orden los archivos de `db/`:
`00_extensiones.sql` -> `01_schema.sql` (export de dbdiagram.io) -> `02_reglas.sql` -> `03_datos.sql`.

En pgAdmin el servidor "Reservas (demo)" ya aparece; la clave es `postgres`.

## Probar la demo
1. Entra a la web, elige "Laboratorio de Electrónica", una fecha dentro de 4 días y verás el Módulo A ocupado de 10:00 a 12:00.
2. Reserva el Módulo B en ese mismo horario: funciona. Reserva el Módulo A: la base de datos lo rechaza.
3. Abre Mailpit y verás el correo de confirmación.
4. En pgAdmin revisa las tablas `reservas`, `reserva_modulos` y `notificaciones`.

## Comandos útiles
```
docker compose down        # apaga (conserva los datos)
docker compose down -v     # apaga y borra los datos; el SQL de db/ se ejecuta de nuevo
```
