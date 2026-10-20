import os
import smtplib
import threading
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from functools import wraps

import psycopg2
import psycopg2.errors
import psycopg2.extras
from dotenv import load_dotenv
from flask import (Flask, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cambia-esto")

DOMINIO = os.getenv("DOMINIO_INSTITUCIONAL", "@universidad.edu.co")
MAX_INTENTOS_CORREO = 3


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
    horario = f"{n['inicio']:%H:%M} a {n['fin']:%H:%M}"
    if n["tipo"] == "cancelacion":
        return ("Reserva cancelada",
                f"Hola {n['usuario']},\n\nTu reserva de {n['espacio']} el {fecha} "
                f"({horario}) fue cancelada.")
    modulos = f"Módulos: {n['modulos']}\n" if n["modulos"] else ""
    return ("Reserva confirmada",
            f"Hola {n['usuario']},\n\nTu reserva quedó confirmada:\n"
            f"Espacio: {n['espacio']}\n{modulos}Fecha: {fecha}\nHorario: {horario}\n\n¡Gracias!")


def enviar_smtp(destino, asunto, cuerpo):
    msg = EmailMessage()
    msg["Subject"], msg["To"] = asunto, destino
    msg["From"] = os.getenv("SMTP_FROM", "reservas@universidad.edu.co")
    msg.set_content(cuerpo)
    with smtplib.SMTP(os.getenv("SMTP_HOST", "localhost"),
                      int(os.getenv("SMTP_PORT", 587)), timeout=20) as s:
        if os.getenv("SMTP_USER"):          # con credenciales (Gmail, etc.)
            s.starttls()
            s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
        s.send_message(msg)                 # sin credenciales (Mailpit en la demo)


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
                enviar_smtp(n["destinatario"], asunto, cuerpo)
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
    if inicio < datetime.now() + timedelta(days=esp["anticipacion_dias"]):
        return f"Debes reservar con al menos {esp['anticipacion_dias']} días de anticipación."

    horarios = query("SELECT apertura, cierre FROM horarios_espacio WHERE espacio_id=%s AND dia_semana=%s",
                     (esp["id"], inicio.isoweekday()))
    if not horarios:
        return "El espacio no abre ese día."
    if not any(h["apertura"] <= inicio.time() and fin.time() <= h["cierre"] for h in horarios):
        h = horarios[0]
        return f"Horario de ese día: {h['apertura']:%H:%M} a {h['cierre']:%H:%M}."

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
    return redirect(url_for("reservar" if "usuario_id" in session else "login"))


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        correo = request.form["correo"].strip().lower()
        clave = request.form["password"]
        if not correo.endswith(DOMINIO):
            flash(f"Usa tu correo institucional ({DOMINIO}).", "error")
        elif len(clave) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
        elif query("SELECT 1 FROM usuarios WHERE correo=%s", (correo,), uno=True):
            flash("Ese correo ya está registrado.", "error")
        else:
            query("INSERT INTO usuarios (nombre, correo, password_hash) VALUES (%s,%s,%s)",
                  (nombre, correo, generate_password_hash(clave)))
            flash("Cuenta creada. Ya puedes iniciar sesión.", "ok")
            return redirect(url_for("login"))
    return render_template("registro.html", dominio=DOMINIO)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = query("SELECT * FROM usuarios WHERE correo=%s",
                  (request.form["correo"].strip().lower(),), uno=True)
        if u and check_password_hash(u["password_hash"], request.form["password"]):
            session["usuario_id"], session["nombre"], session["correo"] = u["id"], u["nombre"], u["correo"]
            return redirect(url_for("reservar"))
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
        mods = [m for m in todos if m["id"] in elegidos] or todos   # sin selección = espacio completo

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
    return render_template("mis_reservas.html", reservas=reservas, ahora=datetime.now())


@app.post("/cancelar/<int:rid>")
@login_required
def cancelar(rid):
    conn = conectar()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""UPDATE reservas SET estado='cancelada'
                            WHERE id=%s AND usuario_id=%s AND estado='confirmada' AND inicio > now()
                        RETURNING id""", (rid, session["usuario_id"]))
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
                         WHERE m.espacio_id=%s AND tsrange(rm.inicio, rm.fin) && tsrange(%s, %s)
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


if __name__ == "__main__":
    threading.Thread(target=bucle_reintentos, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG") == "1", use_reloader=False)
