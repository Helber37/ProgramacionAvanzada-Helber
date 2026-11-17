import os
import secrets
import hmac
import logging
import threading
import time
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from functools import wraps

import psycopg2
import psycopg2.errors
import psycopg2.extras
from dotenv import load_dotenv
from flask import (Flask, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from correo import enviar_correo  # Envía notificaciones mediante Gmail SMTP.

logging.getLogger("werkzeug").setLevel(logging.ERROR)  # Oculta accesos HTTP normales.
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cambia-esto")

@app.template_filter("hora12")
def hora12(valor):
    """Presenta horas en formato de 12 horas sin alterar los datos almacenados."""
    if valor is None:
        return ""
    if isinstance(valor, str):
        valor = datetime.strptime(valor[:5], "%H:%M")
    return f"{valor.hour % 12 or 12}:{valor.minute:02d} {'a. m.' if valor.hour < 12 else 'p. m.'}"


DOMINIO = os.getenv("DOMINIO_INSTITUCIONAL", "@universidad.edu.co")
MAX_INTENTOS_CORREO = 3
TIPOS_USUARIO = ("estudiante", "docente", "empleado", "egresado")
ROLES = ("usuario", "administrador", "superadministrador")


def es_administrador():
    """Consulta permisos actuales en PostgreSQL; evita sesiones con rol obsoleto."""
    if "usuario_id" not in session:
        return False
    u = query("SELECT rol FROM usuarios WHERE id=%s", (session["usuario_id"],), uno=True)
    return bool(u and u["rol"] in ("administrador", "superadministrador"))


def es_superadministrador():
    if "usuario_id" not in session:
        return False
    u = query("SELECT rol FROM usuarios WHERE id=%s", (session["usuario_id"],), uno=True)
    return bool(u and u["rol"] == "superadministrador")


def token_csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


@app.context_processor
def contexto_permisos():
    return {"puede_administrar": es_administrador(), "es_superadmin": es_superadministrador(), "csrf_token": token_csrf}



# ======================= Base de datos =======================
def conectar():
    return psycopg2.connect(
        os.getenv("DATABASE_URL", "dbname=reservas user=postgres password=postgres host=localhost"),
        cursor_factory=psycopg2.extras.RealDictCursor)


def query(sql, params=(), uno=False):
    conn = conectar()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.description:
                return cur.fetchone() if uno else cur.fetchall()
    finally:
        conn.close()


# ======================= Correos (cola con reintentos) =======================
def armar_correo(n):
    fecha = f"{n['inicio']:%d/%m/%Y}"
    horario = f"{hora12(n['inicio'])} a {hora12(n['fin'])}"
    if n["tipo"] == "cancelacion":
        return ("Reserva cancelada",
                f"Hola {n['usuario']},\n\nTu reserva de {n['espacio']} el {fecha} "
                f"({horario}) fue cancelada.")
    modulos = f"Módulos: {n['modulos']}\n" if n["modulos"] else ""
    return ("Reserva confirmada",
            f"Hola {n['usuario']},\n\nTu reserva quedó confirmada:\n"
            f"Espacio: {n['espacio']}\n{modulos}Fecha: {fecha}\nHorario: {horario}\n\n¡Gracias!")




_candado = threading.Lock()


def procesar_notificaciones():
    """Envía las notificaciones pendientes o fallidas (máx. 3 intentos)."""
    with _candado:
        pendientes = query("""
            SELECT n.*, r.inicio, r.fin, e.nombre AS espacio, u.nombre AS usuario,
                   (SELECT string_agg(m.nombre, ', ' ORDER BY m.nombre)
                      FROM reserva_modulos rm JOIN modulos m ON m.id = rm.modulo_id
                     WHERE rm.reserva_id = r.id) AS modulos
              FROM notificaciones n
              JOIN reservas r ON r.id = n.reserva_id
              JOIN espacios e ON e.id = r.espacio_id
              JOIN usuarios u ON u.id = r.usuario_id
             WHERE n.estado IN ('pendiente', 'fallida') AND n.intentos < %s
             ORDER BY n.id""", (MAX_INTENTOS_CORREO,))
        for n in pendientes:
            try:
                asunto, cuerpo = armar_correo(n)
                enviar_correo(n["destinatario"], asunto, cuerpo)
                query("""UPDATE notificaciones SET estado='enviada', intentos=intentos+1,
                         enviada_en=now(), error=NULL WHERE id=%s""", (n["id"],))
            except Exception as e:
                print("No se pudo enviar el correo:", e)
                query("""UPDATE notificaciones SET estado='fallida', intentos=intentos+1,
                         error=%s WHERE id=%s""", (str(e)[:300], n["id"]))


def lanzar_envio():
    threading.Thread(target=procesar_notificaciones, daemon=True).start()


def bucle_reintentos():
    while True:
        time.sleep(60)
        try:
            procesar_notificaciones()
        except Exception as e:
            print("Error en reintentos:", e)


# ======================= Sesión =======================
def login_required(f):
    @wraps(f)
    def envoltura(*a, **k):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        return f(*a, **k)
    return envoltura


# ======================= Panel de administración =======================
@app.get("/admin")
@login_required
def admin():
    # Verificar permisos en el servidor antes de consultar datos institucionales.
    if not es_administrador():
        flash("No tienes permisos para acceder al panel administrativo.", "error")
        return redirect(url_for("reservar"))
    estadisticas = query("""
        SELECT (SELECT count(*) FROM espacios) AS espacios,
               (SELECT count(*) FROM usuarios) AS usuarios,
               (SELECT count(*) FROM reservas WHERE estado='confirmada') AS activas,
               (SELECT count(*) FROM reservas WHERE estado='cancelada') AS canceladas
    """, uno=True)
    recientes = query("""
        SELECT r.id, r.inicio, r.fin, r.estado, e.nombre AS espacio,
               u.nombre AS usuario, u.correo
        FROM reservas r
        JOIN espacios e ON e.id = r.espacio_id
        JOIN usuarios u ON u.id = r.usuario_id
        ORDER BY r.creada DESC LIMIT 300
    """)
    usuarios = query("""SELECT u.id, u.nombre, u.correo, u.tipo_usuario, u.rol,
                       (SELECT count(*) FROM reservas r WHERE r.usuario_id=u.id) AS reservas
                       FROM usuarios u ORDER BY u.id DESC""")
    espacios_admin = query("""SELECT e.*, ed.nombre AS edificio, t.nombre AS tipo,
                       (SELECT count(*) FROM modulos m WHERE m.espacio_id=e.id) AS num_modulos,
                       (SELECT count(*) FROM reservas r WHERE r.espacio_id=e.id) AS reservas
                       FROM espacios e JOIN edificios ed ON ed.id=e.edificio_id
                       JOIN tipos_espacio t ON t.id=e.tipo_id ORDER BY e.id DESC""")
    edificios = query("SELECT id, nombre FROM edificios ORDER BY nombre")
    tipos_espacio = query("SELECT id, nombre FROM tipos_espacio ORDER BY nombre")
    modulos_admin = query("SELECT id, espacio_id, nombre, capacidad FROM modulos ORDER BY id")
    return render_template("admin.html", estadisticas=estadisticas, recientes=recientes,
                           usuarios=usuarios, tipos=TIPOS_USUARIO, roles=ROLES,
                           espacios=espacios_admin, edificios=edificios,
                           tipos_espacio=tipos_espacio, modulos=modulos_admin,
                           ahora=datetime.now(ZoneInfo("America/Bogota")).replace(tzinfo=None))


# ======================= Gestión de usuarios y permisos =======================
@app.post("/admin/usuarios/<int:usuario_id>/permisos")
@login_required
def actualizar_permisos(usuario_id):
    """Solo superadministración puede cambiar tipos y privilegios."""
    if not es_superadministrador():
        return ("Acceso denegado", 403)
    if not hmac.compare_digest(request.form.get("csrf", ""), session.get("csrf", "")):
        return ("Solicitud no válida", 400)
    tipo = request.form.get("tipo_usuario", "")
    rol = request.form.get("rol", "")
    if tipo not in TIPOS_USUARIO or rol not in ROLES:
        flash("Tipo o rol no válido.", "error")
        return redirect(url_for("admin"))
    if usuario_id == session["usuario_id"] and rol != "superadministrador":
        flash("No puedes quitarte tu propio permiso de superadministrador.", "error")
        return redirect(url_for("admin"))
    # Bloquea el registro durante la actualización y evita quitar el último superadmin.
    conn = conectar()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT rol FROM usuarios WHERE id=%s FOR UPDATE", (usuario_id,))
            anterior = cur.fetchone()
            if not anterior:
                flash("Usuario no encontrado.", "error")
            else:
                if anterior["rol"] == "superadministrador" and rol != "superadministrador":
                    cur.execute("SELECT id FROM usuarios WHERE rol='superadministrador' FOR UPDATE")
                    if len(cur.fetchall()) <= 1:
                        flash("Debe existir al menos un superadministrador.", "error")
                        return redirect(url_for("admin"))
                cur.execute("UPDATE usuarios SET tipo_usuario=%s, rol=%s WHERE id=%s",
                            (tipo, rol, usuario_id))
                flash("Permisos actualizados correctamente.", "ok")
    finally:
        conn.close()
    return redirect(url_for("admin"))


# ======================= Operaciones administrativas protegidas =======================
def validar_admin_form(superadmin=False):
    """Valida permisos reales y token CSRF antes de modificar datos."""
    if not (es_superadministrador() if superadmin else es_administrador()):
        return ("Acceso denegado", 403)
    if not hmac.compare_digest(request.form.get("csrf", ""), session.get("csrf", "")):
        return ("Solicitud no válida", 400)
    return None


def regresar_admin(seccion):
    return redirect(url_for("admin") + "#" + seccion)


@app.post("/admin/reservas/<int:reserva_id>/cancelar")
@login_required
def admin_cancelar_reserva(reserva_id):
    error = validar_admin_form()
    if error:
        return error
    conn = conectar()
    cancelada = False
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""UPDATE reservas SET estado='cancelada'
                           WHERE id=%s AND estado='confirmada' AND inicio > %s
                           RETURNING id, usuario_id""",
                        (reserva_id, datetime.now(ZoneInfo("America/Bogota")).replace(tzinfo=None)))
            reserva = cur.fetchone()
            if reserva:
                cur.execute("DELETE FROM reserva_modulos WHERE reserva_id=%s", (reserva_id,))
                cur.execute("""INSERT INTO notificaciones(reserva_id,destinatario,tipo)
                               SELECT %s,correo,'cancelacion' FROM usuarios WHERE id=%s""",
                            (reserva_id, reserva["usuario_id"]))
                cancelada = True
    finally:
        conn.close()
    flash("Reserva cancelada y módulos liberados." if cancelada else
          "Solo se pueden cancelar reservas futuras confirmadas.", "ok" if cancelada else "error")
    if cancelada:
        lanzar_envio()
    return regresar_admin("reservas")


@app.post("/admin/historial/eliminar")
@login_required
def admin_eliminar_historial():
    """Elimina únicamente registros históricos tras validar permisos y confirmación."""
    error = validar_admin_form(superadmin=True)  # Solo superadministrador y CSRF válido.
    if error:
        return error
    if request.form.get("confirmacion") != "ELIMINAR":  # Confirmación explícita.
        flash("Debes confirmar la eliminación del historial.", "error")
        return regresar_admin("historial")
    modo = request.form.get("modo", "")  # seleccionadas, canceladas o finalizadas.
    ahora = datetime.now(ZoneInfo("America/Bogota")).replace(tzinfo=None)
    parametros = []  # Valores enviados como parámetros SQL, nunca interpolados.
    if modo == "seleccionadas":
        ids_texto = request.form.getlist("reserva_ids")  # Identificadores seleccionados.
        if not ids_texto or len(ids_texto) > 300:
            flash("Selecciona entre 1 y 300 reservas del historial.", "error")
            return regresar_admin("historial")
        try:
            ids = list({int(x) for x in ids_texto if int(x) > 0})
        except (TypeError, ValueError):
            return ("Identificadores inválidos", 400)
        if not ids:
            return ("Identificadores inválidos", 400)
        filtro = "r.id = ANY(%s)"
        parametros.append(ids)
    elif modo == "canceladas":
        filtro = "r.estado = 'cancelada'"
    elif modo == "finalizadas":
        filtro = "r.estado = 'confirmada' AND r.fin <= %s"
        parametros.append(ahora)
    else:
        return ("Operación no válida", 400)

    # Un registro histórico es cancelado o está finalizado; nunca se borran reservas activas.
    condicion_historica = "(r.estado = 'cancelada' OR (r.estado = 'confirmada' AND r.fin <= %s))"
    parametros.append(ahora)
    conn = conectar()
    try:
        with conn, conn.cursor() as cur:  # Transacción atómica; ON DELETE CASCADE limpia relaciones.
            cur.execute(f"""SELECT r.id FROM reservas r
                            WHERE {filtro} AND {condicion_historica}
                            FOR UPDATE""", tuple(parametros))
            ids_borrar = [fila["id"] for fila in cur.fetchall()]
            if modo == "seleccionadas" and len(ids_borrar) != len(ids):
                flash("Algunas reservas ya no están en el historial. No se eliminó ninguna.", "error")
                return regresar_admin("historial")
            if ids_borrar:
                cur.execute("DELETE FROM reservas WHERE id = ANY(%s)", (ids_borrar,))
            cantidad = len(ids_borrar)
    finally:
        conn.close()
    flash(f"Se eliminaron {cantidad} reservas del historial y sus registros asociados.", "ok")
    return regresar_admin("historial")


@app.post("/admin/usuarios/<int:usuario_id>/eliminar")
@login_required
def admin_eliminar_usuario(usuario_id):
    error = validar_admin_form(superadmin=True)
    if error:
        return error
    if usuario_id == session["usuario_id"]:
        flash("No puedes eliminar tu propia cuenta.", "error")
        return regresar_admin("usuarios")
    conn = conectar()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT rol FROM usuarios WHERE id=%s FOR UPDATE", (usuario_id,))
            usuario = cur.fetchone()
            if not usuario:
                flash("Usuario no encontrado.", "error")
            elif usuario["rol"] == "superadministrador":
                flash("No se permite eliminar cuentas de superadministrador.", "error")
            else:
                cur.execute("SELECT 1 FROM reservas WHERE usuario_id=%s LIMIT 1", (usuario_id,))
                if cur.fetchone():
                    flash("No se puede eliminar: el usuario tiene reservas en el historial.", "error")
                else:
                    cur.execute("DELETE FROM usuarios WHERE id=%s", (usuario_id,))
                    flash("Usuario eliminado correctamente.", "ok")
    finally:
        conn.close()
    return regresar_admin("usuarios")


@app.post("/admin/espacios/crear")
@login_required
def admin_crear_espacio():
    error = validar_admin_form()
    if error:
        return error
    nombre = request.form.get("nombre", "").strip()[:120]
    try:
        edificio_id = int(request.form.get("edificio_id", ""))
        tipo_id = int(request.form.get("tipo_id", ""))
        capacidad = int(request.form.get("capacidad", ""))
        piso = int(request.form.get("piso") or 1)
        apertura = datetime.strptime(request.form.get("apertura", ""), "%H:%M").time()
        cierre = datetime.strptime(request.form.get("cierre", ""), "%H:%M").time()
        modulos = [x.strip() for x in request.form.get("modulos", "").split(",") if x.strip()]
        if not nombre or capacidad < 1 or capacidad > 10000 or piso < -10 or piso > 200 or not apertura < cierre:
            raise ValueError()
        if not modulos or len(modulos) > 50 or len(set(modulos)) != len(modulos) or any(len(x) > 80 for x in modulos):
            raise ValueError()
    except ValueError:
        flash("Revisa el nombre, capacidad, horario y módulos del espacio.", "error")
        return regresar_admin("espacios")
    conn = conectar()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM edificios WHERE id=%s", (edificio_id,))
            if not cur.fetchone():
                raise ValueError("Edificio no válido")
            cur.execute("SELECT 1 FROM tipos_espacio WHERE id=%s", (tipo_id,))
            if not cur.fetchone():
                raise ValueError("Tipo de espacio no válido")
            cur.execute("""INSERT INTO espacios(edificio_id,tipo_id,nombre,piso,capacidad,accesible,activo)
                           VALUES (%s,%s,%s,%s,%s,%s,TRUE) RETURNING id""",
                        (edificio_id,tipo_id,nombre,piso,capacidad,request.form.get("accesible")=="on"))
            espacio_id = cur.fetchone()["id"]
            for modulo in modulos:
                cur.execute("INSERT INTO modulos(espacio_id,nombre,capacidad) VALUES (%s,%s,%s)",
                            (espacio_id,modulo,capacidad))
            for dia in range(1,7):
                cur.execute("""INSERT INTO horarios_espacio(espacio_id,dia_semana,apertura,cierre)
                               VALUES (%s,%s,%s,%s)""", (espacio_id,dia,apertura,cierre))
        flash("Espacio y módulos creados correctamente.", "ok")
    except (ValueError, psycopg2.Error) as exc:
        flash("No se pudo crear el espacio: " + str(exc)[:120], "error")
    finally:
        conn.close()
    return regresar_admin("espacios")


@app.post("/admin/espacios/<int:espacio_id>/estado")
@login_required
def admin_estado_espacio(espacio_id):
    error = validar_admin_form()
    if error:
        return error
    actualizado = query("UPDATE espacios SET activo=NOT activo WHERE id=%s RETURNING id", (espacio_id,), uno=True)
    flash("Disponibilidad del espacio actualizada." if actualizado else "Espacio no encontrado.",
          "ok" if actualizado else "error")
    return regresar_admin("espacios")


@app.post("/admin/espacios/<int:espacio_id>/editar")
@login_required
def admin_editar_espacio(espacio_id):
    error = validar_admin_form()
    if error:
        return error
    nombre = request.form.get("nombre", "").strip()[:120]
    try:
        capacidad = int(request.form.get("capacidad", ""))
        if not nombre or not 1 <= capacidad <= 10000:
            raise ValueError()
    except ValueError:
        flash("Nombre o capacidad inválidos.", "error")
        return regresar_admin("espacios")
    actualizado = query("UPDATE espacios SET nombre=%s, capacidad=%s WHERE id=%s RETURNING id",
                        (nombre, capacidad, espacio_id), uno=True)
    flash("Espacio actualizado." if actualizado else "Espacio no encontrado.",
          "ok" if actualizado else "error")
    return regresar_admin("espacios")


@app.post("/admin/espacios/<int:espacio_id>/modulos")
@login_required
def admin_agregar_modulo(espacio_id):
    error = validar_admin_form()
    if error:
        return error
    nombre = request.form.get("nombre", "").strip()[:80]
    try:
        capacidad = int(request.form.get("capacidad", ""))
        if not nombre or not 1 <= capacidad <= 10000:
            raise ValueError()
    except ValueError:
        flash("Nombre o capacidad del módulo inválidos.", "error")
        return regresar_admin("espacios")
    conn = conectar()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM espacios WHERE id=%s FOR UPDATE", (espacio_id,))
            if not cur.fetchone():
                flash("Espacio no encontrado.", "error")
            else:
                cur.execute("SELECT 1 FROM modulos WHERE espacio_id=%s AND lower(nombre)=lower(%s)",
                            (espacio_id,nombre))
                if cur.fetchone():
                    flash("Ya existe un módulo con ese nombre.", "error")
                else:
                    cur.execute("INSERT INTO modulos(espacio_id,nombre,capacidad) VALUES (%s,%s,%s)",
                                (espacio_id,nombre,capacidad))
                    flash("Módulo agregado.", "ok")
    finally:
        conn.close()
    return regresar_admin("espacios")


@app.post("/admin/espacios/<int:espacio_id>/eliminar")
@login_required
def admin_eliminar_espacio(espacio_id):
    error = validar_admin_form(superadmin=True)
    if error:
        return error
    conn = conectar()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM espacios WHERE id=%s FOR UPDATE", (espacio_id,))
            if not cur.fetchone():
                flash("Espacio no encontrado.", "error")
            else:
                cur.execute("SELECT 1 FROM reservas WHERE espacio_id=%s LIMIT 1", (espacio_id,))
                if cur.fetchone():
                    flash("El espacio tiene reservas asociadas. Deshabilítalo para conservar el historial.", "error")
                else:
                    cur.execute("DELETE FROM espacios WHERE id=%s", (espacio_id,))
                    flash("Espacio eliminado.", "ok")
    finally:
        conn.close()
    return regresar_admin("espacios")


# ======================= Vista independiente del panel de ocupación =======================
@app.get("/ocupacion")
@login_required
def ocupacion():
    """Presenta el panel institucional sin mezclarlo con las demás páginas."""
    return render_template("ocupacion.html")


# ======================= Ocupación institucional (WSGI / HTTP) =======================
@app.get("/api/ocupacion")
@login_required
def api_ocupacion():
    """Resumen de reservas confirmadas; una consulta por actualización del navegador."""
    ahora = datetime.now(ZoneInfo("America/Bogota")).replace(tzinfo=None)  # Hora de Colombia; reservas guardadas sin zona horaria.
    inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    fin_dia = inicio_dia + timedelta(days=1)
    # Fecha seleccionada para consultar estadísticas históricas o futuras.
    fecha_parametro = request.args.get("fecha", "").strip()
    try:
        fecha_consulta = date.fromisoformat(fecha_parametro) if fecha_parametro else inicio_dia.date()
    except ValueError:
        return jsonify({"error": "La fecha debe tener formato AAAA-MM-DD"}), 400
    inicio_consulta = datetime.combine(fecha_consulta, datetime.min.time())
    fin_consulta = inicio_consulta + timedelta(days=1)
    # Intervalo elegido en el panel: si no hay filtro, se consulta el instante actual.
    hora_inicio_param = request.args.get("hora_inicio", "").strip()
    hora_fin_param = request.args.get("hora_fin", "").strip()
    if bool(hora_inicio_param) != bool(hora_fin_param):
        return jsonify({"error": "Indica las dos horas del intervalo."}), 400
    if hora_inicio_param:
        try:
            inicio_intervalo = datetime.strptime(f"{fecha_consulta} {hora_inicio_param}", "%Y-%m-%d %H:%M")
            fin_intervalo = datetime.strptime(f"{fecha_consulta} {hora_fin_param}", "%Y-%m-%d %H:%M")
        except ValueError:
            return jsonify({"error": "Horario no válido."}), 400
        if fin_intervalo <= inicio_intervalo:
            return jsonify({"error": "La hora final debe ser posterior a la inicial."}), 400
    else:
        inicio_intervalo, fin_intervalo = ahora, ahora + timedelta(microseconds=1)
    # Disponibilidad real de módulos, contando cada módulo una sola vez.
    disponibilidad = query("""
        SELECT COUNT(*)::int AS total,
               COUNT(*) FILTER (WHERE NOT EXISTS (
                   SELECT 1 FROM reserva_modulos rm
                   JOIN reservas r ON r.id = rm.reserva_id
                   WHERE rm.modulo_id = m.id AND r.estado = 'confirmada'
                     AND rm.inicio < %s AND rm.fin > %s
               ))::int AS disponibles
        FROM modulos m JOIN espacios e ON e.id = m.espacio_id
        WHERE e.activo
    """, (fin_intervalo, inicio_intervalo), uno=True)
    reservas_activas = query("""
        SELECT COUNT(*)::int AS cantidad FROM reservas
        WHERE estado = 'confirmada' AND inicio <= %s AND fin > %s
    """, (ahora, ahora), uno=True)["cantidad"]
    reservas_proximas = query("""
        SELECT COUNT(*)::int AS cantidad FROM reservas
        WHERE estado = 'confirmada' AND inicio > %s
    """, (ahora,), uno=True)["cantidad"]
    filas = query("""
        SELECT e.id, e.nombre,
               COUNT(DISTINCT m.id)::int AS total_modulos,
               COUNT(DISTINCT m.id) FILTER (WHERE EXISTS (
                   SELECT 1 FROM reserva_modulos rm
                   JOIN reservas r ON r.id = rm.reserva_id
                   WHERE rm.modulo_id = m.id AND r.estado = 'confirmada'
                     AND rm.inicio <= %s AND rm.fin > %s
               ))::int AS ocupados_ahora,
               COUNT(DISTINCT r_hoy.id)::int AS reservas_hoy
        FROM espacios e
        LEFT JOIN modulos m ON m.espacio_id = e.id
        LEFT JOIN reservas r_hoy ON r_hoy.espacio_id = e.id
            AND r_hoy.estado = 'confirmada'
            AND r_hoy.inicio < %s AND r_hoy.fin > %s
        WHERE e.activo
        GROUP BY e.id, e.nombre
        ORDER BY e.nombre
    """, (ahora, ahora, fin_dia, inicio_dia))
    # Estado global de cada módulo: ocupado ahora, reservado después o libre.
    # No se filtra por usuario; se consultan todas las reservas confirmadas.
    modulos_filas = query("""
        SELECT m.id, m.espacio_id, m.nombre,
               EXISTS (
                   SELECT 1 FROM reserva_modulos rm
                   JOIN reservas r ON r.id = rm.reserva_id
                   WHERE rm.modulo_id = m.id AND r.estado = 'confirmada'
                     AND rm.inicio <= %s AND rm.fin > %s
               ) AS ocupado_ahora,
               (SELECT MIN(rm.inicio) FROM reserva_modulos rm
                JOIN reservas r ON r.id = rm.reserva_id
                WHERE rm.modulo_id = m.id AND r.estado = 'confirmada'
                  AND rm.inicio > %s AND rm.fin > %s) AS proxima_inicio,
               (SELECT rm.fin FROM reserva_modulos rm
                JOIN reservas r ON r.id = rm.reserva_id
                WHERE rm.modulo_id = m.id AND r.estado = 'confirmada'
                  AND rm.inicio > %s AND rm.fin > %s
                ORDER BY rm.inicio, rm.reserva_id LIMIT 1) AS proxima_fin
        FROM modulos m JOIN espacios e ON e.id = m.espacio_id
        WHERE e.activo ORDER BY m.espacio_id, m.id
    """, (ahora, ahora, ahora, ahora, ahora, ahora))
    modulos_por_espacio = {}
    for m in modulos_filas:
        estado = 'ocupado' if m['ocupado_ahora'] else ('proxima' if m['proxima_inicio'] else 'libre')
        modulos_por_espacio.setdefault(m['espacio_id'], []).append({
            'id': m['id'], 'nombre': m['nombre'], 'estado': estado,
            'proxima_inicio': m['proxima_inicio'].isoformat(timespec='minutes') if m['proxima_inicio'] else None,
            'proxima_fin': m['proxima_fin'].isoformat(timespec='minutes') if m['proxima_fin'] else None
        })
    total = sum(f["total_modulos"] for f in filas)
    ocupados = sum(f["ocupados_ahora"] for f in filas)
    # Módulos ocupados en cada hora: cuenta los intervalos que se cruzan con reservas confirmadas.
    horarios = query("""
        SELECT horas.hora::int AS hora, COUNT(DISTINCT rm.modulo_id)::int AS cantidad
        FROM generate_series(0, 23) AS horas(hora)
        JOIN reserva_modulos rm
          ON rm.inicio < (%s::timestamp + (horas.hora + 1) * interval '1 hour')
         AND rm.fin > (%s::timestamp + horas.hora * interval '1 hour')
        JOIN reservas r ON r.id = rm.reserva_id AND r.estado = 'confirmada'
        GROUP BY horas.hora ORDER BY horas.hora
    """, (inicio_dia, inicio_dia))
    # Siete días desde hoy: cada reserva se cuenta una vez por día que ocupa.
    proximos = query("""
        SELECT dias.dia::int AS dia, COUNT(DISTINCT r.id)::int AS cantidad
        FROM generate_series(0, 6) AS dias(dia)
        JOIN reservas r ON r.estado = 'confirmada'
          AND r.inicio < (%s::timestamp + (dias.dia + 1) * interval '1 day')
          AND r.fin > (%s::timestamp + dias.dia * interval '1 day')
        GROUP BY dias.dia ORDER BY dias.dia
    """, (inicio_dia, inicio_dia))
    # Horas-módulo de hoy por espacio: duración real de reservas confirmadas dentro del día.
    horas_espacios = query("""
        SELECT r.espacio_id, ROUND((SUM(EXTRACT(EPOCH FROM
            (LEAST(rm.fin, %s::timestamp) - GREATEST(rm.inicio, %s::timestamp)))) / 3600)::numeric, 2) AS horas
        FROM reserva_modulos rm JOIN reservas r ON r.id = rm.reserva_id
        WHERE r.estado = 'confirmada' AND rm.inicio < %s AND rm.fin > %s
        GROUP BY r.espacio_id
    """, (fin_dia, inicio_dia, fin_dia, inicio_dia))
    horas_por_espacio = {f['espacio_id']: float(f['horas']) for f in horas_espacios}
    # Próximas reservas confirmadas, incluso fuera de los siete días.
    siguientes = query("""
        SELECT r.id, e.nombre AS espacio, r.inicio, r.fin, r.estado
        FROM reservas r
        JOIN espacios e ON e.id = r.espacio_id
        WHERE r.estado = 'confirmada' AND r.fin > %s
        ORDER BY r.inicio, r.id
        LIMIT 20
    """, (ahora,))
    hoy_por_hora = {f["hora"]: f["cantidad"] for f in horarios}
    semana = {f["dia"]: f["cantidad"] for f in proximos}
    return jsonify({
        "actualizado": ahora.strftime("%H:%M:%S"),
        "disponibles_intervalo": disponibilidad["disponibles"],
        "total_intervalo": disponibilidad["total"],
        "reservas_activas": reservas_activas,
        "reservas_proximas": reservas_proximas,
        "fecha": ahora.strftime("%Y-%m-%d"),
        "fecha_consulta": fecha_consulta.isoformat(),
        "total_futuras": query("SELECT COUNT(*)::int AS cantidad FROM reservas WHERE estado='confirmada' AND fin > %s", (ahora,), uno=True)["cantidad"],
        # Cuenta módulos únicos con una reserva confirmada que comenzará después de ahora.
        # No filtra por usuario y no confunde reservas futuras con ocupación actual.
        # Módulos con reservas confirmadas durante cualquier hora del día de hoy.
        "modulos_reservados_hoy": query("""
            SELECT COUNT(DISTINCT rm.modulo_id)::int AS cantidad
            FROM reserva_modulos rm
            JOIN reservas r ON r.id = rm.reserva_id
            JOIN modulos m ON m.id = rm.modulo_id
            JOIN espacios e ON e.id = m.espacio_id
            WHERE r.estado = 'confirmada'
              AND rm.inicio < %s AND rm.fin > %s AND e.activo
        """, (fin_dia, inicio_dia), uno=True)["cantidad"],
        "modulos_futuros": query("""
            SELECT COUNT(DISTINCT rm.modulo_id)::int AS cantidad
            FROM reserva_modulos rm
            JOIN reservas r ON r.id = rm.reserva_id
            JOIN modulos m ON m.id = rm.modulo_id
            JOIN espacios e ON e.id = m.espacio_id
            WHERE r.estado = 'confirmada' AND rm.inicio > %s AND e.activo
        """, (ahora,), uno=True)["cantidad"],
        "siguientes": [{"id": f["id"], "espacio": f["espacio"], "inicio": f["inicio"].isoformat(timespec="minutes"), "fin": f["fin"].isoformat(timespec="minutes"), "estado": f["estado"]} for f in siguientes],
        "total_modulos": total,
        "ocupados": ocupados,
        "porcentaje": round(ocupados * 100 / total) if total else 0,
        "espacios_en_uso": sum(f["ocupados_ahora"] > 0 for f in filas),
        "total_espacios": len(filas),
        "reservas_hoy": sum(f["reservas_hoy"] for f in filas),
        "espacios": [{"id": f["id"], "nombre": f["nombre"],
                     "total": f["total_modulos"], "ocupados": f["ocupados_ahora"],
                     "reservas_hoy": f["reservas_hoy"],
                     "horas_modulo_hoy": horas_por_espacio.get(f["id"], 0),
                     "modulos": modulos_por_espacio.get(f["id"], [])} for f in filas],
        "horas": [{"hora": h, "cantidad": hoy_por_hora.get(h, 0)} for h in range(24)],
        "proximos": [{"dia": i, "fecha": (inicio_dia + timedelta(days=i)).strftime("%d/%m"),
                      "cantidad": semana.get(i, 0)} for i in range(7)]
    })


# ======================= Reglas de negocio =======================
def cargar_espacio(espacio_id):
    return query("""SELECT e.*, t.anticipacion_dias, t.max_horas, t.nombre AS tipo
                      FROM espacios e JOIN tipos_espacio t ON t.id = e.tipo_id
                     WHERE e.id = %s AND e.activo""", (espacio_id,), uno=True)


def validar(esp, mods, inicio, fin, asistentes):
    """Devuelve un mensaje de error o None si la reserva cumple todas las reglas."""
    if fin <= inicio:
        return "La hora de fin debe ser posterior a la de inicio."
    if inicio.date() != fin.date():
        return "La reserva debe terminar el mismo día."
    if fin - inicio > timedelta(hours=esp["max_horas"]):
        return f"Este tipo de espacio permite máximo {esp['max_horas']} horas por reserva."
    if inicio <= datetime.now(ZoneInfo("America/Bogota")).replace(tzinfo=None):
        return "La reserva debe comenzar en una fecha y hora futuras."

    horarios = query("SELECT apertura, cierre FROM horarios_espacio WHERE espacio_id=%s AND dia_semana=%s",
                     (esp["id"], inicio.isoweekday()))
    if not horarios:
        return "El espacio no abre ese día."
    if not any(h["apertura"] <= inicio.time() and fin.time() <= h["cierre"] for h in horarios):
        h = horarios[0]
        return f"Horario de ese día: {hora12(h['apertura'])} a {hora12(h['cierre'])}."

    cierre = query("""SELECT motivo FROM cierres_espacio
                       WHERE espacio_id=%s AND tsrange(inicio, fin) && tsrange(%s, %s)""",
                   (esp["id"], inicio, fin), uno=True)
    if cierre:
        return f"El espacio está cerrado en ese horario ({cierre['motivo'] or 'sin motivo indicado'})."

    if asistentes and asistentes > sum(m["capacidad"] for m in mods):
        return "El número de asistentes supera la capacidad de lo que elegiste."
    return None


def crear_reserva(usuario_id, espacio_id, mods, inicio, fin, motivo, asistentes, correo):
    """Todo en una sola transacción. Lanza ExclusionViolation si el módulo ya está ocupado."""
    conn = conectar()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO reservas (usuario_id, espacio_id, inicio, fin, motivo, num_asistentes)
                           VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (usuario_id, espacio_id, inicio, fin, motivo, asistentes or None))
            rid = cur.fetchone()["id"]
            for m in mods:
                cur.execute("""INSERT INTO reserva_modulos (reserva_id, modulo_id, inicio, fin)
                               VALUES (%s,%s,%s,%s)""", (rid, m["id"], inicio, fin))
            cur.execute("""INSERT INTO notificaciones (reserva_id, destinatario, tipo)
                           VALUES (%s,%s,'confirmacion')""", (rid, correo))
        return rid
    finally:
        conn.close()


# ======================= Rutas: cuenta =======================
@app.route("/")
def inicio():
    return redirect(url_for("admin" if es_administrador() else "reservar") if "usuario_id" in session else url_for("login"))


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        correo = request.form["correo"].strip().lower()
        clave = request.form["password"]
        tipo = request.form.get("tipo_usuario", "estudiante")
        if tipo not in TIPOS_USUARIO:
            flash("Selecciona un tipo de usuario válido.", "error")
        elif not correo.endswith(DOMINIO):
            flash(f"Usa tu correo institucional ({DOMINIO}).", "error")
        elif len(clave) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
        elif query("SELECT 1 FROM usuarios WHERE correo=%s", (correo,), uno=True):
            flash("Ese correo ya está registrado.", "error")
        else:
            query("INSERT INTO usuarios (nombre, correo, password_hash, tipo_usuario, rol) VALUES (%s,%s,%s,%s,'usuario')",
                  (nombre, correo, generate_password_hash(clave), tipo))
            flash("Cuenta creada. Ya puedes iniciar sesión.", "ok")
            return redirect(url_for("login"))
    return render_template("registro.html", dominio=DOMINIO, tipos=TIPOS_USUARIO)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = query("SELECT * FROM usuarios WHERE correo=%s",
                  (request.form["correo"].strip().lower(),), uno=True)
        if u and check_password_hash(u["password_hash"], request.form["password"]):
            session["usuario_id"], session["nombre"], session["correo"] = u["id"], u["nombre"], u["correo"]
            session["rol"] = u["rol"]  # Rol obtenido de PostgreSQL, nunca del formulario.
            session["tipo_usuario"] = u["tipo_usuario"]
            return redirect(url_for("admin" if u["rol"] in ("administrador", "superadministrador") else "reservar"))
        flash("Correo o contraseña incorrectos.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ======================= Rutas: reservas =======================
@app.route("/reservar", methods=["GET", "POST"])
@login_required
def reservar():
    if request.method == "POST":
        try:
            espacio_id = int(request.form["espacio_id"])
            fecha = request.form["fecha"]
            inicio = datetime.strptime(f"{fecha} {request.form['hora_inicio']}", "%Y-%m-%d %H:%M")
            fin = datetime.strptime(f"{fecha} {request.form['hora_fin']}", "%Y-%m-%d %H:%M")
            asistentes = int(request.form.get("asistentes") or 0)
            elegidos = [int(x) for x in request.form.getlist("modulos")]
        except (ValueError, KeyError):
            flash("Completa todos los campos.", "error")
            return redirect(url_for("reservar"))

        esp = cargar_espacio(espacio_id)
        if not esp:
            flash("El espacio no existe o no está disponible.", "error")
            return redirect(url_for("reservar"))

        todos = query("SELECT id, nombre, capacidad FROM modulos WHERE espacio_id=%s", (espacio_id,))
        # Si no se seleccionan módulos, reservar solo los libres para ese horario.
        if elegidos and any(x not in {m["id"] for m in todos} for x in elegidos):
            flash("La selección de módulos no corresponde al espacio.", "error")
            return redirect(url_for("reservar"))
        ocupados = query("""SELECT DISTINCT rm.modulo_id FROM reserva_modulos rm
                           JOIN reservas r ON r.id = rm.reserva_id
                           WHERE r.espacio_id=%s AND r.estado='confirmada'
                             AND rm.inicio < %s AND rm.fin > %s""", (espacio_id, fin, inicio))
        ids_ocupados = {m["modulo_id"] for m in ocupados}
        disponibles = [m for m in todos if m["id"] not in ids_ocupados]
        mods = [m for m in disponibles if m["id"] in elegidos] if elegidos else disponibles
        if not mods or (elegidos and len(mods) != len(set(elegidos))):
            flash("Los módulos elegidos están ocupados. Selecciona otros disponibles.", "error")
            return redirect(url_for("reservar"))

        error = validar(esp, mods, inicio, fin, asistentes)
        if error:
            flash(error, "error")
            return redirect(url_for("reservar"))
        try:
            crear_reserva(session["usuario_id"], espacio_id, mods, inicio, fin,
                          request.form.get("motivo", "").strip()[:200], asistentes, session["correo"])
        except psycopg2.errors.ExclusionViolation:
            flash("Alguien reservó ese espacio o módulo en ese horario hace un momento. Elige otro horario.", "error")
            return redirect(url_for("reservar"))
        lanzar_envio()
        flash("Reserva confirmada. Te enviamos un correo.", "ok")
        return redirect(url_for("mis_reservas"))

    categorias = query("SELECT * FROM categorias ORDER BY id")
    espacios = query("""SELECT e.id, e.nombre, e.accesible, t.nombre AS tipo, t.categoria_id
                          FROM espacios e JOIN tipos_espacio t ON t.id = e.tipo_id
                         WHERE e.activo ORDER BY t.categoria_id, e.nombre""")
    return render_template("reservar.html", categorias=categorias, espacios=espacios)


@app.route("/mis-reservas")
@login_required
def mis_reservas():
    reservas = query("""
        SELECT r.*, e.nombre AS espacio,
               string_agg(m.nombre, ', ' ORDER BY m.nombre) AS modulos
          FROM reservas r
          JOIN espacios e ON e.id = r.espacio_id
          LEFT JOIN reserva_modulos rm ON rm.reserva_id = r.id
          LEFT JOIN modulos m ON m.id = rm.modulo_id
         WHERE r.usuario_id = %s
         GROUP BY r.id, e.nombre
         ORDER BY r.inicio DESC""", (session["usuario_id"],))
    # Utiliza la hora local de Colombia para evaluar el estado de cada reserva.
    ahora_colombia = datetime.now(ZoneInfo("America/Bogota")).replace(tzinfo=None)
    # Separa las reservas vigentes del historial sin borrar registros de PostgreSQL.
    vigentes = [r for r in reservas if r["estado"] == "confirmada" and r["fin"] > ahora_colombia]
    historial = [r for r in reservas if r["estado"] == "cancelada" or r["fin"] <= ahora_colombia]
    return render_template("mis_reservas.html", reservas_vigentes=vigentes,
                           reservas_historial=historial, ahora=ahora_colombia)


@app.post("/cancelar/<int:rid>")
@login_required
def cancelar(rid):
    conn = conectar()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""UPDATE reservas SET estado='cancelada'
                            WHERE id=%s AND usuario_id=%s AND estado='confirmada' AND inicio > %s
                        RETURNING id""", (rid, session["usuario_id"], datetime.now(ZoneInfo("America/Bogota")).replace(tzinfo=None)))
            if cur.fetchone():
                cur.execute("DELETE FROM reserva_modulos WHERE reserva_id=%s", (rid,))  # libera los módulos
                cur.execute("""INSERT INTO notificaciones (reserva_id, destinatario, tipo)
                               VALUES (%s,%s,'cancelacion')""", (rid, session["correo"]))
                flash("Reserva cancelada.", "ok")
            else:
                flash("No se puede cancelar esa reserva.", "error")
    finally:
        conn.close()
    lanzar_envio()
    return redirect(url_for("mis_reservas"))



# ======================= API para la interfaz =======================
@app.get("/api/espacio/<int:espacio_id>")
@login_required
def api_espacio(espacio_id):
    esp = cargar_espacio(espacio_id)
    if not esp:
        return jsonify({"error": "no existe"}), 404
    modulos = query("SELECT id, nombre, capacidad FROM modulos WHERE espacio_id=%s ORDER BY nombre", (espacio_id,))
    recursos = query("""SELECT r.nombre, er.cantidad FROM espacio_recursos er
                          JOIN recursos r ON r.id = er.recurso_id
                         WHERE er.espacio_id=%s ORDER BY r.nombre""", (espacio_id,))
    return jsonify({
        "tipo": esp["tipo"], "capacidad": esp["capacidad"], "accesible": esp["accesible"],
        "notas_accesibilidad": esp["notas_accesibilidad"],
        "anticipacion_dias": esp["anticipacion_dias"], "max_horas": esp["max_horas"],
        "modulos": modulos, "recursos": recursos})


@app.get("/api/disponibilidad")
@login_required
def api_disponibilidad():
    try:
        espacio_id = int(request.args["espacio_id"])
        dia = datetime.strptime(request.args["fecha"], "%Y-%m-%d")
    except (KeyError, ValueError):
        return jsonify({"error": "parámetros inválidos"}), 400
    siguiente = dia + timedelta(days=1)

    horario = query("SELECT apertura, cierre FROM horarios_espacio WHERE espacio_id=%s AND dia_semana=%s",
                    (espacio_id, dia.isoweekday()))
    cierres = query("""SELECT inicio, fin, motivo FROM cierres_espacio
                        WHERE espacio_id=%s AND tsrange(inicio, fin) && tsrange(%s, %s)""",
                    (espacio_id, dia, siguiente))
    ocupados = query("""SELECT rm.modulo_id, rm.inicio, rm.fin
                          FROM reserva_modulos rm JOIN modulos m ON m.id = rm.modulo_id
                          JOIN reservas r ON r.id = rm.reserva_id
                         WHERE m.espacio_id=%s AND r.estado='confirmada'
                           AND tsrange(rm.inicio, rm.fin) && tsrange(%s, %s)
                         ORDER BY rm.inicio""", (espacio_id, dia, siguiente))

    def hora(ts):
        return "23:59" if ts >= siguiente else ts.strftime("%H:%M")

    por_modulo = {}
    for o in ocupados:
        por_modulo.setdefault(o["modulo_id"], []).append(
            {"inicio": o["inicio"].strftime("%H:%M"), "fin": o["fin"].strftime("%H:%M")})
    return jsonify({
        "horario": [{"apertura": h["apertura"].strftime("%H:%M"), "cierre": h["cierre"].strftime("%H:%M")} for h in horario],
        "cierres": [{"inicio": hora(max(c["inicio"], dia)), "fin": hora(min(c["fin"], siguiente)),
                     "motivo": c["motivo"]} for c in cierres],
        "ocupados": por_modulo})


def main():
    """Inicia Flask solo cuando app.py se ejecuta directamente."""
    # Este hilo no debe arrancar durante la importación WSGI por Gunicorn.
    threading.Thread(target=bucle_reintentos, daemon=True).start()
    # Gunicorn importa app:app; no ejecuta esta función principal.
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG") == "1", use_reloader=False)


if __name__ == "__main__":
    main()  # Protege el punto de entrada y evita iniciar el servidor al importar.
