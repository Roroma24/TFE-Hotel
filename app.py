from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, date
from functools import wraps
import os
import math
import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from patterns.observer import gestor_eventos, ObservadorCorreo, ObservadorHabitacion, ObservadorLog
from patterns.facade   import ServicioReservas
from patterns.builder  import DirectorReporte, BuilderReporteHotel

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "plaza_delfino_simulado_2026")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "hotel_delfino"),
}

ADMIN_USER_ENV = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS_ENV = os.getenv("ADMIN_PASS", "delfino2026")
RECEP_USER_ENV = os.getenv("RECEP_USER", "recepcion")
RECEP_PASS_ENV = os.getenv("RECEP_PASS", "recep2026")
WEB_SYSTEM_USER = os.getenv("WEB_SYSTEM_USER", "web_reservas")

ROOM_NAMES = {
    "101": "Coral",
    "102": "Brisa",
    "103": "Perla",
    "104": "Aura",
    "105": "Marea",
    "106": "Duna",
    "107": "Luna",
    "108": "Nácar",
    "109": "Palma",
    "110": "Horizonte",
}

ROOM_SEEDS = [
    {"numero": "101", "tipo": "Suite Vista Mar", "piso": "1", "estado": "libre", "observaciones": "Coral"},
    {"numero": "102", "tipo": "Suite Vista Mar", "piso": "1", "estado": "libre", "observaciones": "Brisa"},
    {"numero": "103", "tipo": "Junior Suite", "piso": "1", "estado": "libre", "observaciones": "Perla"},
    {"numero": "104", "tipo": "Deluxe Garden", "piso": "1", "estado": "libre", "observaciones": "Aura"},
    {"numero": "105", "tipo": "Suite Vista Mar", "piso": "1", "estado": "libre", "observaciones": "Marea"},
    {"numero": "106", "tipo": "Deluxe Garden", "piso": "2", "estado": "libre", "observaciones": "Duna"},
    {"numero": "107", "tipo": "Junior Suite", "piso": "2", "estado": "libre", "observaciones": "Luna"},
    {"numero": "108", "tipo": "Suite Vista Mar", "piso": "2", "estado": "libre", "observaciones": "Nácar"},
    {"numero": "109", "tipo": "Deluxe Garden", "piso": "2", "estado": "libre", "observaciones": "Palma"},
    {"numero": "110", "tipo": "Suite Vista Mar", "piso": "2", "estado": "libre", "observaciones": "Horizonte"},
]

TYPE_SEEDS = [
    {
        "nombre_tipo": "Suite Vista Mar",
        "descripcion": "Habitación premium con vista al mar",
        "capacidad": 2,
        "precio_base": 420.00,
    },
    {
        "nombre_tipo": "Junior Suite",
        "descripcion": "Habitación amplia para estancia confortable",
        "capacidad": 3,
        "precio_base": 390.00,
    },
    {
        "nombre_tipo": "Deluxe Garden",
        "descripcion": "Habitación elegante con vista al jardín",
        "capacidad": 2,
        "precio_base": 360.00,
    },
]


# =========================
# BASE DE DATOS
# =========================
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def fetch_all(query, params=None):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def fetch_one(query, params=None):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


def execute_query(query, params=None, many=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    if many:
        cursor.executemany(query, params)
    else:
        cursor.execute(query, params or ())
    conn.commit()
    last_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return last_id

gestor_eventos.suscribir(ObservadorCorreo())
gestor_eventos.suscribir(ObservadorHabitacion(execute_query))   
gestor_eventos.suscribir(ObservadorLog())

svc = ServicioReservas(fetch_one, fetch_all, execute_query)

# =========================
# HELPERS
# =========================
def split_name(full_name):
    partes = full_name.strip().split()
    if not partes:
        return "", ""
    nombre = partes[0]
    apellido = " ".join(partes[1:]) if len(partes) > 1 else ""
    return nombre, apellido


def calcular_noches(fecha_entrada, fecha_salida):
    try:
        entrada = datetime.strptime(fecha_entrada, "%Y-%m-%d")
        salida = datetime.strptime(fecha_salida, "%Y-%m-%d")
        noches = (salida - entrada).days
        return noches if noches > 0 else 1
    except Exception:
        return 1


def calcular_total(precio_habitacion, personas, noches):
    personas = int(personas)
    total = float(precio_habitacion) * noches
    if personas > 2:
        total += (personas - 2) * 45 * noches
    return round(total, 2)


def format_folio(id_reserva):
    return f"RSV-{int(id_reserva):05d}"


def folio_to_id(folio):
    try:
        return int(str(folio).replace("RSV-", "").strip())
    except Exception:
        return None


def password_matches(input_password, stored_password):
    if not stored_password:
        return False
    if stored_password.startswith("pbkdf2:") or stored_password.startswith("scrypt:"):
        return check_password_hash(stored_password, input_password)
    return stored_password == input_password


def admin_required(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get("admin_autenticado"):
            return redirect(url_for("admin_login"))
        return vista(*args, **kwargs)
    return envoltura


def role_required(*roles):
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if not session.get("admin_autenticado"):
                return redirect(url_for("admin_login"))

            if session.get("admin_rol") not in roles:
                if session.get("admin_rol") == "recepcionista":
                    return redirect(url_for("admin_recepcion"))
                return redirect(url_for("admin_dashboard"))

            return vista(*args, **kwargs)
        return envoltura
    return decorador


# =========================
# BOOTSTRAP
# =========================
def bootstrap_database():
    execute_query(
        """
        INSERT IGNORE INTO ROLES (id_rol, nombre_rol, descripcion)
        VALUES
            (1, 'cliente', 'Cliente del hotel'),
            (2, 'recepcionista', 'Operación hotelera'),
            (3, 'gerente', 'Administrador del sistema')
        """
    )

    for tipo in TYPE_SEEDS:
        existe = fetch_one(
            "SELECT id_tipo_habitacion FROM TIPOS_HABITACION WHERE nombre_tipo = %s",
            (tipo["nombre_tipo"],),
        )
        if not existe:
            execute_query(
                """
                INSERT INTO TIPOS_HABITACION (nombre_tipo, descripcion, capacidad, precio_base)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    tipo["nombre_tipo"],
                    tipo["descripcion"],
                    tipo["capacidad"],
                    tipo["precio_base"],
                ),
            )

    tipos = fetch_all("SELECT id_tipo_habitacion, nombre_tipo FROM TIPOS_HABITACION")
    tipos_map = {t["nombre_tipo"]: t["id_tipo_habitacion"] for t in tipos}

    for room in ROOM_SEEDS:
        existe = fetch_one(
            "SELECT id_habitacion FROM HABITACIONES WHERE numero = %s",
            (room["numero"],),
        )
        if not existe:
            execute_query(
                """
                INSERT INTO HABITACIONES (id_tipo_habitacion, numero, piso, estado, observaciones)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    tipos_map[room["tipo"]],
                    room["numero"],
                    room["piso"],
                    room["estado"],
                    room["observaciones"],
                ),
            )

    admin = fetch_one("SELECT id_usuario FROM USUARIOS WHERE usuario = %s", (ADMIN_USER_ENV,))
    if not admin:
        execute_query(
            """
            INSERT INTO USUARIOS (id_rol, nombre, apellido, usuario, password, correo, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                3,
                "Administrador",
                "Plaza Delfino",
                ADMIN_USER_ENV,
                generate_password_hash(ADMIN_PASS_ENV),
                f"{ADMIN_USER_ENV}@plazadelfino.com",
                "activo",
            ),
        )

    recepcionista = fetch_one("SELECT id_usuario FROM USUARIOS WHERE usuario = %s", (RECEP_USER_ENV,))
    if not recepcionista:
        execute_query(
            """
            INSERT INTO USUARIOS (id_rol, nombre, apellido, usuario, password, correo, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                2,
                "Recepcionista",
                "Plaza Delfino",
                RECEP_USER_ENV,
                generate_password_hash(RECEP_PASS_ENV),
                f"{RECEP_USER_ENV}@plazadelfino.com",
                "activo",
            ),
        )

    web_user = fetch_one("SELECT id_usuario FROM USUARIOS WHERE usuario = %s", (WEB_SYSTEM_USER,))
    if not web_user:
        execute_query(
            """
            INSERT INTO USUARIOS (id_rol, nombre, apellido, usuario, password, correo, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                2,
                "Sistema",
                "Reservas Web",
                WEB_SYSTEM_USER,
                generate_password_hash("web_reservas_2026"),
                "web_reservas@plazadelfino.com",
                "activo",
            ),
        )


def get_public_operator_user_id():
    row = fetch_one("SELECT id_usuario FROM USUARIOS WHERE usuario = %s", (WEB_SYSTEM_USER,))
    return row["id_usuario"] if row else None


# =========================
# HABITACIONES / RESERVAS
# =========================
def get_room_state_for_ui(db_state, room_number):
    state = (db_state or "libre").strip().lower()
    if state in ("ocupada", "reservada", "mantenimiento"):
        return "ocupada"
    if str(room_number) in ("105", "110"):
        return "premium"
    return "disponible"


def get_habitaciones_croquis_db():
    rows = fetch_all(
        """
        SELECT
            h.id_habitacion,
            h.numero,
            h.piso,
            h.estado,
            h.observaciones,
            t.nombre_tipo,
            t.precio_base
        FROM HABITACIONES h
        INNER JOIN TIPOS_HABITACION t
            ON t.id_tipo_habitacion = h.id_tipo_habitacion
        ORDER BY CAST(h.numero AS UNSIGNED)
        """
    )

    habitaciones = []
    for row in rows:
        numero = str(row["numero"])
        habitaciones.append(
            {
                "id": int(numero) if numero.isdigit() else numero,
                "id_db": row["id_habitacion"],
                "numero": numero,
                "nombre": row["observaciones"] or ROOM_NAMES.get(numero, f"Habitación {numero}"),
                "tipo": row["nombre_tipo"],
                "precio": float(row["precio_base"]),
                "estado": get_room_state_for_ui(row["estado"], numero),
            }
        )
    return habitaciones


def get_habitacion_por_numero(numero):
    row = fetch_one(
        """
        SELECT
            h.id_habitacion,
            h.numero,
            h.piso,
            h.estado,
            h.observaciones,
            t.nombre_tipo,
            t.precio_base
        FROM HABITACIONES h
        INNER JOIN TIPOS_HABITACION t
            ON t.id_tipo_habitacion = h.id_tipo_habitacion
        WHERE h.numero = %s
        """,
        (str(numero),),
    )

    if not row:
        return None

    numero_str = str(row["numero"])
    return {
        "id": int(numero_str) if numero_str.isdigit() else numero_str,
        "id_db": row["id_habitacion"],
        "numero": numero_str,
        "nombre": row["observaciones"] or ROOM_NAMES.get(numero_str, f"Habitación {numero_str}"),
        "tipo": row["nombre_tipo"],
        "precio": float(row["precio_base"]),
        "estado": get_room_state_for_ui(row["estado"], numero_str),
    }


def get_or_create_cliente(nombre_completo, email, telefono, documento_identidad=None, direccion=None, id_empresa=None):
    cliente = fetch_one("SELECT * FROM CLIENTES WHERE correo = %s", (email,))
    nombre, apellido = split_name(nombre_completo)

    # Convertir id_empresa a None si está vacío
    if id_empresa == "":
        id_empresa = None

    if cliente:
        execute_query(
            """
            UPDATE CLIENTES
            SET nombre = %s, apellido = %s, telefono = %s, documento_identidad = %s, direccion = %s, id_empresa = %s
            WHERE id_cliente = %s
            """,
            (nombre, apellido, telefono, documento_identidad, direccion, id_empresa, cliente["id_cliente"]),
        )
        return cliente["id_cliente"]

    return execute_query(
        """
        INSERT INTO CLIENTES (id_empresa, nombre, apellido, documento_identidad, telefono, correo, direccion, tipo_cliente)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (id_empresa, nombre, apellido, documento_identidad, telefono, email, direccion, "individual"),
    )


def get_reservas_db():
    rows = fetch_all(
        """
        SELECT
            r.id_reserva,
            r.fecha_reserva,
            r.fecha_entrada,
            r.fecha_salida,
            r.cantidad_huespedes,
            r.estado_reserva,
            r.total_estimado,
            c.nombre AS cliente_nombre,
            c.apellido AS cliente_apellido,
            c.correo AS cliente_correo,
            c.telefono AS cliente_telefono,
            h.numero AS habitacion_numero,
            h.observaciones AS habitacion_nombre,
            h.estado AS habitacion_estado,
            t.nombre_tipo,
            t.precio_base,
            EXISTS(SELECT 1 FROM CHECKIN ci WHERE ci.id_reserva = r.id_reserva) AS tiene_checkin,
            EXISTS(SELECT 1 FROM CHECKOUT co WHERE co.id_reserva = r.id_reserva) AS tiene_checkout
        FROM RESERVAS r
        INNER JOIN CLIENTES c
            ON c.id_cliente = r.id_cliente
        INNER JOIN HABITACIONES h
            ON h.id_habitacion = r.id_habitacion
        INNER JOIN TIPOS_HABITACION t
            ON t.id_tipo_habitacion = h.id_tipo_habitacion
        ORDER BY r.id_reserva DESC
        """
    )

    reservas = []
    for row in rows:
        noches = calcular_noches(str(row["fecha_entrada"]), str(row["fecha_salida"]))
        nombre_cliente = (row["cliente_nombre"] or "").strip()
        apellido_cliente = (row["cliente_apellido"] or "").strip()
        nombre_completo = f"{nombre_cliente} {apellido_cliente}".strip()

        estado_reserva = (row["estado_reserva"] or "").strip().lower()
        if estado_reserva in ("cancelada", "cancelled"):
            estado_operativo = "cancelada"
        elif row["tiene_checkout"]:
            estado_operativo = "checked_out"
        elif row["tiene_checkin"] or estado_reserva in ("checked_in", "checkin", "ocupada"):
            estado_operativo = "checked_in"
        else:
            estado_operativo = "reservada"

        numero = str(row["habitacion_numero"])
        reservas.append(
            {
                "id_reserva": row["id_reserva"],
                "folio": format_folio(row["id_reserva"]),
                "cliente": {
                    "nombre": nombre_completo,
                    "email": row["cliente_correo"] or "",
                    "telefono": row["cliente_telefono"] or "",
                },
                "detalle": {
                    "fecha_entrada": str(row["fecha_entrada"]),
                    "fecha_salida": str(row["fecha_salida"]),
                    "personas": int(row["cantidad_huespedes"]),
                    "tipo_estancia": row["nombre_tipo"],
                    "comentarios": "",
                    "noches": noches,
                    "total": float(row["total_estimado"] or 0),
                    "habitacion": {
                        "id": int(numero) if numero.isdigit() else numero,
                        "numero": numero,
                        "nombre": row["habitacion_nombre"] or ROOM_NAMES.get(numero, f"Habitación {numero}"),
                        "tipo": row["nombre_tipo"],
                        "precio": float(row["precio_base"]),
                    },
                },
                "estado_operativo": estado_operativo,
            }
        )
    return reservas


# =========================
# MÉTRICAS ADMIN
# =========================
def resumen_admin():
    reservas = get_reservas_db()
    ganancias_totales = 0
    total_noches = 0
    habitaciones_rentadas = set()
    dias_por_habitacion = {}

    for reserva in reservas:
        if reserva["estado_operativo"] == "cancelada":
            continue
        detalle = reserva["detalle"]
        habitacion = detalle["habitacion"]
        habitacion_id = habitacion["id"]

        ganancias_totales += detalle["total"]
        total_noches += detalle["noches"]
        habitaciones_rentadas.add(habitacion_id)

        if habitacion_id not in dias_por_habitacion:
            dias_por_habitacion[habitacion_id] = {
                "id": habitacion["id"],
                "nombre": habitacion["nombre"],
                "tipo": habitacion["tipo"],
                "dias": 0,
                "ingresos": 0,
            }

        dias_por_habitacion[habitacion_id]["dias"] += detalle["noches"]
        dias_por_habitacion[habitacion_id]["ingresos"] += detalle["total"]

    return {
        "total_reservas": len(reservas),
        "habitaciones_rentadas": len(habitaciones_rentadas),
        "ganancias_totales": round(ganancias_totales, 2),
        "total_noches": total_noches,
        "dias_por_habitacion": sorted(dias_por_habitacion.values(), key=lambda x: x["id"]),
    }


def obtener_clientes_admin():
    reservas = get_reservas_db()
    clientes = {}

    for reserva in reservas:
        if reserva["estado_operativo"] == "cancelada":
            continue
        cliente = reserva["cliente"]
        detalle = reserva["detalle"]
        email = (cliente["email"] or "").strip().lower() or f"sin-correo-{cliente['nombre']}"

        if email not in clientes:
            clientes[email] = {
                "nombre": cliente["nombre"],
                "email": cliente["email"],
                "telefono": cliente["telefono"],
                "reservas": 0,
                "noches": 0,
                "gastado": 0,
                "ultima_habitacion": "",
                "ultima_entrada": "",
                "ultima_salida": "",
            }

        clientes[email]["reservas"] += 1
        clientes[email]["noches"] += detalle["noches"]
        clientes[email]["gastado"] += detalle["total"]
        clientes[email]["ultima_habitacion"] = f'{detalle["habitacion"]["id"]} - {detalle["habitacion"]["nombre"]}'
        clientes[email]["ultima_entrada"] = detalle["fecha_entrada"]
        clientes[email]["ultima_salida"] = detalle["fecha_salida"]

    clientes_lista = list(clientes.values())
    clientes_lista.sort(key=lambda c: c["gastado"], reverse=True)
    return clientes_lista


def obtener_habitaciones_admin():
    habitaciones_db = get_habitaciones_croquis_db()
    reservas = get_reservas_db()

    activas_por_numero = {}
    for reserva in reservas:
        if reserva["estado_operativo"] in ("checked_out", "cancelada"):
            continue
        numero = str(reserva["detalle"]["habitacion"]["numero"])
        activas_por_numero[numero] = reserva

    habitaciones_admin = []
    for habitacion in habitaciones_db:
        numero = str(habitacion["numero"])
        reserva_activa = activas_por_numero.get(numero)

        if reserva_activa:
            estado_operativo = reserva_activa.get("estado_operativo", "reservada")
            estado_visual = "ocupada" if estado_operativo == "checked_in" else "reservada"
            habitaciones_admin.append(
                {
                    "id": habitacion["id"],
                    "numero": habitacion["numero"],
                    "nombre": habitacion["nombre"],
                    "tipo": habitacion["tipo"],
                    "precio": habitacion["precio"],
                    "estado_visual": estado_visual,
                    "folio": reserva_activa["folio"],
                    "cliente": reserva_activa["cliente"]["nombre"],
                    "email": reserva_activa["cliente"]["email"],
                    "telefono": reserva_activa["cliente"]["telefono"],
                    "entrada": reserva_activa["detalle"]["fecha_entrada"],
                    "salida": reserva_activa["detalle"]["fecha_salida"],
                    "noches": reserva_activa["detalle"]["noches"],
                    "total": reserva_activa["detalle"]["total"],
                }
            )
        else:
            habitaciones_admin.append(
                {
                    "id": habitacion["id"],
                    "numero": habitacion["numero"],
                    "nombre": habitacion["nombre"],
                    "tipo": habitacion["tipo"],
                    "precio": habitacion["precio"],
                    "estado_visual": "libre",
                    "folio": "",
                    "cliente": "",
                    "email": "",
                    "telefono": "",
                    "entrada": "",
                    "salida": "",
                    "noches": 0,
                    "total": 0,
                }
            )

    habitaciones_admin.sort(key=lambda x: int(str(x["numero"])))
    return habitaciones_admin


# =========================
# RUTAS PÚBLICAS
# =========================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/galeria")
def galeria():
    return render_template("galeria.html")


@app.route("/contacto")
def contacto():
    return render_template("contacto.html")


@app.route("/reservas")
def reservas():
    return render_template("reservas.html")


@app.route("/reservas/crear-cuenta", methods=["GET", "POST"])
def crear_cuenta_reserva():
    error = None

    empresas = fetch_all(
        """
        SELECT id_empresa, nombre_empresa
        FROM EMPRESAS
        """
    )

    if request.method == "POST":
        nombre_completo = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip()
        telefono = request.form.get("telefono", "").strip()
        password = request.form.get("password", "").strip()

        documento_identidad = request.form.get("documento_identidad", "").strip()
        direccion = request.form.get("direccion", "").strip()
        id_empresa = request.form.get("id_empresa") or None

        if not nombre_completo or not email or not telefono or not password:
            error = "Todos los campos obligatorios deben completarse."

        else:
            usuario_existente = fetch_one(
                """
                SELECT id_usuario
                FROM USUARIOS
                WHERE usuario = %s OR correo = %s
                """,
                (email, email),
            )

            if usuario_existente:
                error = "Ya existe una cuenta registrada con ese correo."

            else:
                nombre, apellido = split_name(nombre_completo)

                # =========================
                # INSERTAR EN USUARIOS
                # =========================
                execute_query(
                    """
                    INSERT INTO USUARIOS
                    (
                        id_rol,
                        nombre,
                        apellido,
                        usuario,
                        password,
                        correo,
                        estado
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        1,
                        nombre,
                        apellido,
                        email,
                        generate_password_hash(password),
                        email,
                        "activo",
                    ),
                )

                # =========================
                # INSERTAR EN CLIENTES
                # =========================
                execute_query(
                    """
                    INSERT INTO CLIENTES
                    (
                        id_empresa,
                        nombre,
                        apellido,
                        documento_identidad,
                        telefono,
                        correo,
                        direccion,
                        tipo_cliente
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        id_empresa,
                        nombre,
                        apellido,
                        documento_identidad,
                        telefono,
                        email,
                        direccion,
                        "individual",
                    ),
                )

                flow = request.args.get("flow") or request.form.get("flow")

                if flow == "reservas":
                    session["cliente_reserva"] = {
                        "nombre": nombre_completo,
                        "email": email,
                        "telefono": telefono,
                    }
                    return redirect(url_for("detalles_reserva"))

                return redirect(url_for("login"))

    return render_template(
        "crear_cuenta_reserva.html",
        error=error,
        empresas=empresas
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        correo = request.form.get('correo', '').strip()
        password = request.form.get('password', '').strip()

        user = fetch_one(
            """
            SELECT u.*, r.nombre_rol
            FROM USUARIOS u
            INNER JOIN ROLES r
                ON r.id_rol = u.id_rol
            WHERE u.correo = %s
            """,
            (correo,),
        )

        if not user:
            error = 'Correo no encontrado.'

        elif user["nombre_rol"] in ("gerente", "recepcionista"):
            error = 'Debe iniciar sesión desde el portal administrativo.'

        elif user["estado"] != "activo":
            error = 'La cuenta se encuentra inactiva.'

        elif not password_matches(password, user["password"]):
            error = 'Contraseña incorrecta.'

        else:
            session["cliente"] = {
                "id": user["id_usuario"],
                "usuario": user["usuario"],
                "nombre": f'{user["nombre"]} {user["apellido"]}',
                "correo": user["correo"],
                "rol": user["nombre_rol"]
            }

            return redirect(url_for('reservas'))

    return render_template('login.html', error=error)


@app.route("/reservas/detalles", methods=["GET", "POST"])
def detalles_reserva():
    if "cliente_reserva" not in session:
        if session.get("cliente"):
            cliente = session.get("cliente")
            session["cliente_reserva"] = {
                "nombre": cliente.get("nombre", ""),
                "email": cliente.get("correo") or cliente.get("email") or cliente.get("usuario", ""),
                "telefono": cliente.get("telefono", ""),
            }
        else:
            return redirect(url_for("crear_cuenta_reserva", flow='reservas'))

    error = None
    datos = session.get("detalle_reserva", {})
    habitaciones = get_habitaciones_croquis_db()

    if request.method == "POST":
        fecha_entrada = request.form.get("fecha_entrada", "")
        fecha_salida = request.form.get("fecha_salida", "")
        personas = request.form.get("personas", "2")
        tipo_estancia = request.form.get("tipo_estancia", "")
        comentarios = request.form.get("comentarios", "").strip()
        habitacion_id = request.form.get("habitacion_id", "").strip()

        habitacion = get_habitacion_por_numero(habitacion_id)

        if not fecha_entrada or not fecha_salida:
            error = "Debes seleccionar la fecha de entrada y la fecha de salida."
        else:
            try:
                fe = datetime.strptime(fecha_entrada, "%Y-%m-%d")
                fs = datetime.strptime(fecha_salida, "%Y-%m-%d")
                if fs <= fe:
                    error = "La fecha de salida debe ser posterior a la fecha de entrada."
            except Exception:
                error = "Fechas inválidas."

        if not error:
            if not habitacion:
                error = "Debes seleccionar una habitación del croquis."
            elif habitacion["estado"] == "ocupada":
                error = "La habitación elegida no está disponible."
            else:
                noches = calcular_noches(fecha_entrada, fecha_salida)
                total = calcular_total(habitacion["precio"], personas, noches)

                session["detalle_reserva"] = {
                    "fecha_entrada": fecha_entrada,
                    "fecha_salida": fecha_salida,
                    "personas": personas,
                    "tipo_estancia": tipo_estancia or habitacion["tipo"],
                    "comentarios": comentarios,
                    "noches": noches,
                    "total": total,
                    "habitacion": habitacion,
                }

                return redirect(url_for("cobro"))

        datos = {
            "fecha_entrada": fecha_entrada,
            "fecha_salida": fecha_salida,
            "personas": personas,
            "tipo_estancia": tipo_estancia,
            "comentarios": comentarios,
            "habitacion": habitacion,
        }

    return render_template(
        "detalles_reserva.html",
        cliente=session.get("cliente_reserva"),
        habitaciones=habitaciones,
        datos=datos,
        error=error,
    )

@app.route("/cobro", methods=["GET", "POST"])
def cobro():
    if "cliente_reserva" not in session or "detalle_reserva" not in session:
        return redirect(url_for("reservas"))

    cliente = session["cliente_reserva"]
    detalle = session["detalle_reserva"]
    desde_admin = session.get("reserva_desde_admin", False)
    
    # Recuperación de tarjetas guardadas
    tarjetas_cliente = []
    cliente_db = fetch_one("SELECT id_cliente FROM CLIENTES WHERE correo = %s", (cliente["email"],))

    if cliente_db:
        tarjetas_cliente = fetch_all(
            """
            SELECT id_tarjeta, titular, numero_enmascarado, vencimiento
            FROM TARJETAS_CLIENTE
            WHERE id_cliente = %s
            ORDER BY fecha_registro DESC
            """,
            (cliente_db["id_cliente"],)
        )

    if request.method == "POST":
        id_cliente = get_or_create_cliente(
            cliente["nombre"], cliente["email"], cliente["telefono"],
            documento_identidad=cliente.get("documento_identidad"),
            direccion=cliente.get("direccion"),
            id_empresa=cliente.get("id_empresa")
        )
        
        titular = request.form.get("titular", "").strip()
        numero_tarjeta = request.form.get("tarjeta", "").replace(" ", "")
        vencimiento = request.form.get("vencimiento", "").strip()
        ultimos_4 = numero_tarjeta[-4:] if numero_tarjeta else request.form.get("tarjeta_select", "")[-4:]

        # Lógica de guardado de tarjeta
        if request.form.get("guardar_tarjeta"):
            tarjeta_existente = fetch_one(
                "SELECT id_tarjeta FROM TARJETAS_CLIENTE WHERE id_cliente = %s AND ultimos_4 = %s AND vencimiento = %s",
                (id_cliente, ultimos_4, vencimiento)
            )
            if not tarjeta_existente:
                execute_query(
                    "INSERT INTO TARJETAS_CLIENTE (id_cliente, titular, numero_enmascarado, ultimos_4, vencimiento) VALUES (%s,%s,%s,%s,%s)",
                    (id_cliente, titular, f"**** **** **** {ultimos_4}", ultimos_4, vencimiento)
                )

        # Selección de servicio de reserva
        if desde_admin:
            checkin_directo = detalle.get("checkin_directo", False)
            resultado = svc.crear_reserva_recepcion(
                id_cliente=id_cliente, id_habitacion=detalle["habitacion"]["id_db"],
                id_usuario=session.get("admin_id"), fecha_entrada=detalle["fecha_entrada"],
                fecha_salida=detalle["fecha_salida"], personas=int(detalle["personas"]),
                precio_base=detalle["habitacion"]["precio"], noches=detalle["noches"],
                checkin_directo=checkin_directo
            )
        else:
            resultado = svc.crear_reserva_online(
                id_cliente=id_cliente, id_habitacion=detalle["habitacion"]["id_db"],
                id_usuario=get_public_operator_user_id(), fecha_entrada=detalle["fecha_entrada"],
                fecha_salida=detalle["fecha_salida"], personas=int(detalle["personas"]),
                precio_base=detalle["habitacion"]["precio"], noches=detalle["noches"],
                titular=titular, ultimos_4=ultimos_4
            )

        session["confirmacion_reserva"] = {
            "folio": resultado["folio"],
            "cliente": cliente,
            "detalle": detalle,
            "estado_operativo": "reservada",
            "pago": {"titular": titular, "tarjeta": ultimos_4, "vencimiento": vencimiento}
        }
        session["desde_admin_confirmacion"] = desde_admin
        return redirect(url_for("confirmacion_reserva"))

    return render_template("cobro.html", cliente=cliente, detalle=detalle, tarjetas=tarjetas_cliente)

@app.route("/reservas/confirmacion")
def confirmacion_reserva():
    if "confirmacion_reserva" not in session:
        return redirect(url_for("reservas"))

    desde_admin = session.get("desde_admin_confirmacion", False)

    if desde_admin:
        session.pop("cliente_reserva", None)
        session.pop("detalle_reserva", None)
        session.pop("confirmacion_reserva", None)
        session.pop("reserva_desde_admin", None)
        session.pop("desde_admin_confirmacion", None)
        return redirect(url_for("admin_bookings"))

    return render_template(
        "confirmacion_reserva.html",
        reserva=session["confirmacion_reserva"],
    )


# =========================
# LOGIN ADMIN / RECEPCIÓN
# =========================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "").strip()

        admin = fetch_one(
            """
            SELECT u.*, r.nombre_rol
            FROM USUARIOS u
            INNER JOIN ROLES r ON r.id_rol = u.id_rol
            WHERE u.usuario = %s
            """,
            (usuario,),
        )

        if (
            admin
            and admin["nombre_rol"] in ("gerente", "recepcionista")
            and password_matches(password, admin["password"])
        ):
            session["admin_autenticado"] = True
            session["admin_usuario"] = admin["usuario"]
            session["admin_id"] = admin["id_usuario"]
            session["admin_rol"] = admin["nombre_rol"]

            if admin["nombre_rol"] == "recepcionista":
                return redirect(url_for("admin_recepcion"))

            return redirect(url_for("admin_dashboard"))
        else:
            error = "Credenciales de administrador incorrectas."

    return render_template("admin_login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("cliente", None)
    session.pop("cliente_reserva", None)
    session.pop("detalle_reserva", None)
    session.pop("confirmacion_reserva", None)
    session.pop("admin_autenticado", None)
    session.pop("admin_usuario", None)
    session.pop("admin_id", None)
    session.pop("admin_rol", None)
    return redirect(url_for("index"))


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_autenticado", None)
    session.pop("admin_usuario", None)
    session.pop("admin_id", None)
    session.pop("admin_rol", None)
    return redirect(url_for("admin_login"))


# =========================
# RECEPCIÓN
# =========================
@app.route("/admin/recepcion")
@admin_required
@role_required("recepcionista", "gerente")
def admin_recepcion():
    habitaciones = obtener_habitaciones_admin()
    activas = [h for h in habitaciones if h["estado_visual"] != "libre"]

    return render_template(
        "admin_recepcion.html",
        habitaciones=habitaciones,
        activas=activas,
    )


# =========================
# GERENTE
# =========================
@app.route("/admin/dashboard")
@admin_required
@role_required("gerente")
def admin_dashboard():
    reservas = get_reservas_db()

    builder = BuilderReporteHotel()
    director = DirectorReporte(builder)
    reporte = director.reporte_gerente(reservas).to_dict()

    resumen_template = {
        "total_reservas":       reporte["resumen"]["total_reservas"],
        "habitaciones_rentadas": reporte["resumen"]["habitaciones_usadas"],
        "ganancias_totales":    reporte["resumen"]["ingresos_totales"],   
        "total_noches":         reporte["resumen"]["total_noches"],
        "dias_por_habitacion":  reporte["por_habitacion"],
        }
    
    return render_template(
        "admin_dashboard.html",
        resumen=resumen_template,
        reservas=reservas,
        reporte=reporte,
        )


@app.route("/admin/clients")
@admin_required
@role_required("gerente")
def admin_clients():
    clientes = obtener_clientes_admin()
    total_clientes = len(clientes)
    clientes_activos = sum(1 for c in clientes if c["reservas"] >= 1)
    ingresos_clientes = sum(c["gastado"] for c in clientes)
    noches_clientes = sum(c["noches"] for c in clientes)

    return render_template(
        "admin_clients.html",
        clientes=clientes,
        total_clientes=total_clientes,
        clientes_activos=clientes_activos,
        ingresos_clientes=ingresos_clientes,
        noches_clientes=noches_clientes,
    )


# =========================
# BOOKINGS / CHECK-IN / CHECK-OUT
# =========================
@app.route("/admin/bookings")
@admin_required
@role_required("gerente", "recepcionista")
def admin_bookings():
    habitaciones = obtener_habitaciones_admin()

    libres = sum(1 for h in habitaciones if h["estado_visual"] == "libre")
    reservadas = sum(1 for h in habitaciones if h["estado_visual"] == "reservada")
    ocupadas = sum(1 for h in habitaciones if h["estado_visual"] == "ocupada")
    activas = [h for h in habitaciones if h["estado_visual"] != "libre"]

    return render_template(
        "admin_bookings.html",
        habitaciones=habitaciones,
        libres=libres,
        reservadas=reservadas,
        ocupadas=ocupadas,
        activas=activas,
    )


@app.route("/admin/bookings/check-in/<folio>")
@admin_required
@role_required("gerente", "recepcionista")
def admin_check_in(folio):
    id_reserva = folio_to_id(folio)
    admin_id   = session.get("admin_id")

    if id_reserva and admin_id:
        ya_checkin  = fetch_one("SELECT id_checkin  FROM CHECKIN  WHERE id_reserva = %s", (id_reserva,))
        ya_checkout = fetch_one("SELECT id_checkout FROM CHECKOUT WHERE id_reserva = %s", (id_reserva,))

        if not ya_checkin and not ya_checkout:
            svc.hacer_checkin(id_reserva, folio, admin_id)

    return redirect(url_for("admin_bookings"))


@app.route("/admin/bookings/check-out/<folio>")
@admin_required
@role_required("gerente", "recepcionista")
def admin_check_out(folio):
    id_reserva = folio_to_id(folio)
    admin_id   = session.get("admin_id")

    if id_reserva and admin_id:
        ya_checkout = fetch_one("SELECT id_checkout FROM CHECKOUT WHERE id_reserva = %s", (id_reserva,))
        if not ya_checkout:
            svc.hacer_checkout(id_reserva, folio, admin_id)

    return redirect(url_for("admin_bookings"))


@app.route("/admin/bookings/cancelar/<folio>")
@admin_required
@role_required("gerente", "recepcionista")
def admin_cancelar_reserva(folio):
    id_reserva = folio_to_id(folio)

    if id_reserva:
        # Verificar que no tenga check-in ni check-out
        ya_checkin  = fetch_one("SELECT id_checkin  FROM CHECKIN  WHERE id_reserva = %s", (id_reserva,))
        ya_checkout = fetch_one("SELECT id_checkout FROM CHECKOUT WHERE id_reserva = %s", (id_reserva,))

        if not ya_checkin and not ya_checkout:
            # Cancelar la reserva
            execute_query(
                "UPDATE RESERVAS SET estado_reserva = 'cancelada' WHERE id_reserva = %s",
                (id_reserva,)
            )
            # Liberar la habitación
            execute_query(
                """
                UPDATE HABITACIONES h
                INNER JOIN RESERVAS r ON r.id_habitacion = h.id_habitacion
                SET h.estado = 'libre'
                WHERE r.id_reserva = %s
                """,
                (id_reserva,)
            )
            # Marcar la factura como cancelada (si existe)
            execute_query(
                "UPDATE FACTURAS SET estado_factura = 'cancelada' WHERE id_reserva = %s",
                (id_reserva,)
            )

    return redirect(url_for("admin_bookings"))


@app.route("/admin/nueva-reservacion", methods=["GET", "POST"])
@admin_required
@role_required("gerente", "recepcionista")
def admin_nueva_reservacion():
    habitaciones = get_habitaciones_croquis_db()
    empresas = fetch_all(
        """
        SELECT id_empresa, nombre_empresa
        FROM EMPRESAS
        """
    )
    error = None
    datos = {}

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip()
        telefono = request.form.get("telefono", "").strip()
        documento_identidad = request.form.get("documento_identidad", "").strip() or None
        direccion = request.form.get("direccion", "").strip() or None
        id_empresa = request.form.get("id_empresa", "").strip() or None
        fecha_entrada = request.form.get("fecha_entrada", "").strip()
        fecha_salida = request.form.get("fecha_salida", "").strip()
        personas = request.form.get("personas", "2").strip()
        tipo_estancia = request.form.get("tipo_estancia", "").strip()
        comentarios = request.form.get("comentarios", "").strip()
        habitacion_id = request.form.get("habitacion_id", "").strip()
        checkin_directo = request.form.get("checkin_directo") == "on"

        habitacion = get_habitacion_por_numero(habitacion_id)
        datos = {**request.form, "habitacion_id": habitacion_id, "checkin_directo": checkin_directo}

        if not nombre or not email or not telefono:
            error = "Debes completar los datos del cliente."
        elif not fecha_entrada or not fecha_salida:
            error = "Debes seleccionar entrada y salida."
        else:
            try:
                fe = datetime.strptime(fecha_entrada, "%Y-%m-%d")
                fs = datetime.strptime(fecha_salida, "%Y-%m-%d")
                if fs <= fe:
                    error = "La fecha de salida debe ser posterior a la fecha de entrada."
            except Exception:
                error = "Fechas inválidas."
        if not error:
            if not habitacion:
                error = "Debes seleccionar una habitación."
            elif habitacion["estado"] == "ocupada":
                error = "La habitación seleccionada no está disponible."
            else:
                noches = calcular_noches(fecha_entrada, fecha_salida)
                total = calcular_total(habitacion["precio"], personas, noches)

                # =========================
                # CREAR CLIENTE
                # =========================
                id_cliente = get_or_create_cliente(
                    nombre,
                    email,
                    telefono,
                    documento_identidad=documento_identidad,
                    direccion=direccion,
                    id_empresa=id_empresa,
                )
                
                id_usuario = session.get("admin_id")
                id_habitacion = habitacion["id_db"]

                # =========================
                # CREAR RESERVA
                # =========================
                resultado = svc.crear_reserva_recepcion(
                    id_cliente=id_cliente,
                    id_habitacion=id_habitacion,
                    id_usuario=id_usuario,
                    fecha_entrada=fecha_entrada,
                    fecha_salida=fecha_salida,
                    personas=int(personas),
                    precio_base=habitacion["precio"],
                    noches=noches,
                    checkin_directo=checkin_directo,
                )

                # =========================
                # DATOS DE PAGO
                # =========================
                titular = request.form.get("titular", "").strip()
                tarjeta = request.form.get("tarjeta", "").strip()
                metodo_pago = request.form.get("metodo_pago", "Tarjeta")

                # =========================
                # FACTURA
                # =========================
                subtotal = total
                impuestos = round(total * 0.16, 2)
                total_final = subtotal + impuestos
                execute_query(
                    """
                    INSERT INTO FACTURAS
                    (
                        id_reserva,
                        id_cliente,
                        fecha_factura,
                        subtotal,
                        impuestos,
                        total,
                        estado_factura
                    )
                    VALUES (%s, %s, CURDATE(), %s, %s, %s, %s)
                    """,
                    (
                        resultado["id_reserva"],
                        id_cliente,
                        subtotal,
                        impuestos,
                        total_final,
                        "pagada",
                    ),
                )

                # =========================
                # OBTENER ID FACTURA
                # =========================
                factura = fetch_one(
                    """
                    SELECT id_factura
                    FROM FACTURAS
                    WHERE id_reserva = %s
                    ORDER BY id_factura DESC
                    LIMIT 1
                    """,
                    (resultado["id_reserva"],),
                )

                # =========================
                # PAGO
                # =========================
                execute_query(
                    """
                    INSERT INTO PAGOS
                    (
                        id_factura,
                        fecha_pago,
                        monto,
                        referencia,
                        estado_pago
                    )
                    VALUES (%s, CURDATE(), %s, %s, %s)
                    """,
                    (
                        factura["id_factura"],
                        total_final,
                        tarjeta[-4:] if tarjeta else "PAGO ADMIN",
                        "aprobado",
                    ),
                )
                
                return redirect(url_for("admin_bookings"))


    return render_template(
        "admin_nueva_reservacion.html",
        habitaciones=habitaciones,
        empresas=empresas,
        datos=datos,
        error=error,
    )


if __name__ == "__main__":
    bootstrap_database()
    app.run(debug=True)