"""Migración no destructiva de perfiles y permisos, ejecutada antes de Gunicorn."""
import os
import psycopg2



def main():
    """Ejecuta la migración solo cuando se invoca este script explícitamente."""
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(20261102)")  # Evita migraciones simultáneas.
            cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS tipo_usuario TEXT")
            cur.execute("UPDATE usuarios SET tipo_usuario = CASE WHEN rol IN ('estudiante','docente') THEN rol WHEN rol='administrativo' THEN 'empleado' ELSE 'estudiante' END WHERE tipo_usuario IS NULL")
            cur.execute("ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS usuarios_rol_check")  # Retira validación antigua antes de actualizar roles.
            cur.execute("UPDATE usuarios SET rol = CASE WHEN rol IN ('admin','administrativo') THEN 'administrador' WHEN rol IN ('estudiante','docente','egresado','empleado') THEN 'usuario' ELSE rol END WHERE rol NOT IN ('usuario','administrador','superadministrador')")
            cur.execute("ALTER TABLE usuarios ALTER COLUMN rol SET DEFAULT 'usuario'")
            cur.execute("ALTER TABLE usuarios ALTER COLUMN tipo_usuario SET DEFAULT 'estudiante'")
            cur.execute("ALTER TABLE usuarios ALTER COLUMN tipo_usuario SET NOT NULL")
            cur.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='usuarios_rol_valido') THEN ALTER TABLE usuarios ADD CONSTRAINT usuarios_rol_valido CHECK (rol IN ('usuario','administrador','superadministrador')); END IF; END $$")
            cur.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='usuarios_tipo_valido') THEN ALTER TABLE usuarios ADD CONSTRAINT usuarios_tipo_valido CHECK (tipo_usuario IN ('estudiante','docente','empleado','egresado')); END IF; END $$")
            cur.execute("""CREATE TABLE IF NOT EXISTS intentos_login (
                           clave CHAR(64) PRIMARY KEY,
                           fallos INTEGER NOT NULL DEFAULT 0,
                           primer_fallo TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
                           )""")  # Control compartido entre procesos, sin datos personales en claro.
            # Libera módulos de cancelaciones antiguas; no elimina reservas ni su historial.
            cur.execute("""DELETE FROM reserva_modulos rm USING reservas r
                           WHERE rm.reserva_id = r.id AND r.estado = 'cancelada'""")
    print("Migración de roles, perfiles y módulos cancelados completada.")


if __name__ == "__main__":
    main()  # Importar este módulo nunca modifica PostgreSQL.
