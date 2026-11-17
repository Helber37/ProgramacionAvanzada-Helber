# Seguridad y puesta en marcha

1. Copiar `.env.example` a `.env` y definir contraseñas reales y `SECRET_KEY` aleatoria (mínimo 32 caracteres).
2. Ejecutar `docker compose up -d --build`.
3. Verificar el inicio de sesión y que después de cinco fallos aparezca HTTP 429.
4. Verificar que los formularios POST sin CSRF devuelven HTTP 400.
5. Para producción habilitar HTTPS y `COOKIE_SECURE=true` detrás de un proxy TLS.

La migración `migrate_roles.py` crea la tabla `intentos_login` sin borrar los datos anteriores.
El archivo `.env` original se ha excluido para no divulgar secretos.

## Alcance

Las protecciones añadidas no constituyen una auditoría ni garantizan seguridad absoluta. La política CSP mantiene `unsafe-inline` por compatibilidad; se recomienda migrar scripts y estilos a archivos externos. Las contraseñas previamente compartidas deben rotarse.
