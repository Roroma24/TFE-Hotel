from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
from functools import wraps
import uuid

app = Flask(__name__)
app.secret_key = "plaza_delfino_simulado_2026"

HABITACIONES_CROQUIS = [
    {"id": 101, "nombre": "Coral", "tipo": "Suite Vista Mar", "precio": 420, "estado": "disponible"},
    {"id": 102, "nombre": "Brisa", "tipo": "Suite Vista Mar", "precio": 430, "estado": "disponible"},
    {"id": 103, "nombre": "Perla", "tipo": "Junior Suite", "precio": 390, "estado": "ocupada"},
    {"id": 104, "nombre": "Aura", "tipo": "Deluxe Garden", "precio": 360, "estado": "disponible"},
    {"id": 105, "nombre": "Marea", "tipo": "Suite Vista Mar", "precio": 440, "estado": "premium"},
    {"id": 106, "nombre": "Duna", "tipo": "Deluxe Garden", "precio": 350, "estado": "disponible"},
    {"id": 107, "nombre": "Luna", "tipo": "Junior Suite", "precio": 385, "estado": "disponible"},
    {"id": 108, "nombre": "Nácar", "tipo": "Suite Vista Mar", "precio": 435, "estado": "ocupada"},
    {"id": 109, "nombre": "Palma", "tipo": "Deluxe Garden", "precio": 355, "estado": "disponible"},
    {"id": 110, "nombre": "Horizonte", "tipo": "Suite Vista Mar", "precio": 460, "estado": "premium"},
]

# Demo: usuario y contraseña fijos para administrador
ADMIN_USER = "admin"
ADMIN_PASS = "delfino2026"

# Demo: aquí se guardan las reservas confirmadas mientras el servidor esté encendido
RESERVAS_CONFIRMADAS = []


def admin_required(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get("admin_autenticado"):
            return redirect(url_for("admin_login"))
        return vista(*args, **kwargs)
    return envoltura


def calcular_noches(fecha_entrada, fecha_salida):
    try:
        entrada = datetime.strptime(fecha_entrada, "%Y-%m-%d")
        salida = datetime.strptime(fecha_salida, "%Y-%m-%d")
        noches = (salida - entrada).days
        return noches if noches > 0 else 1
    except:
        return 1


def calcular_total(precio_habitacion, personas, noches):
    personas = int(personas)
    total = precio_habitacion * noches

    if personas > 2:
        total += (personas - 2) * 45 * noches

    return total


def resumen_admin():
    ganancias_totales = 0
    total_noches = 0
    habitaciones_rentadas = set()
    dias_por_habitacion = {}

    for reserva in RESERVAS_CONFIRMADAS:
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
                "ingresos": 0
            }

        dias_por_habitacion[habitacion_id]["dias"] += detalle["noches"]
        dias_por_habitacion[habitacion_id]["ingresos"] += detalle["total"]

    return {
        "total_reservas": len(RESERVAS_CONFIRMADAS),
        "habitaciones_rentadas": len(habitaciones_rentadas),
        "ganancias_totales": ganancias_totales,
        "total_noches": total_noches,
        "dias_por_habitacion": sorted(dias_por_habitacion.values(), key=lambda x: x["id"])
    }

def obtener_clientes_admin():
    clientes = {}

    for reserva in RESERVAS_CONFIRMADAS:
        cliente = reserva["cliente"]
        detalle = reserva["detalle"]

        email = cliente["email"].strip().lower()

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
                "ultima_salida": ""
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

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/galeria')
def galeria():
    return render_template('galeria.html')


@app.route('/contacto')
def contacto():
    return render_template('contacto.html')


@app.route('/reservas')
def reservas():
    return render_template('reservas.html')


@app.route('/reservas/crear-cuenta', methods=['GET', 'POST'])
def crear_cuenta_reserva():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip()
        telefono = request.form.get('telefono', '').strip()

        session['cliente_reserva'] = {
            'nombre': nombre,
            'email': email,
            'telefono': telefono
        }

        return redirect(url_for('detalles_reserva'))

    return render_template('crear_cuenta_reserva.html')


@app.route('/reservas/detalles', methods=['GET', 'POST'])
def detalles_reserva():
    if 'cliente_reserva' not in session:
        return redirect(url_for('crear_cuenta_reserva'))

    error = None
    datos = session.get('detalle_reserva', {})

    if request.method == 'POST':
        fecha_entrada = request.form.get('fecha_entrada', '')
        fecha_salida = request.form.get('fecha_salida', '')
        personas = request.form.get('personas', '2')
        tipo_estancia = request.form.get('tipo_estancia', '')
        comentarios = request.form.get('comentarios', '').strip()
        habitacion_id = request.form.get('habitacion_id', '').strip()

        habitacion = next((h for h in HABITACIONES_CROQUIS if str(h['id']) == habitacion_id), None)

        if not fecha_entrada or not fecha_salida:
            error = 'Debes seleccionar la fecha de entrada y la fecha de salida.'
        elif not habitacion:
            error = 'Debes seleccionar una habitación del croquis.'
        elif habitacion['estado'] == 'ocupada':
            error = 'La habitación elegida no está disponible.'
        else:
            noches = calcular_noches(fecha_entrada, fecha_salida)
            total = calcular_total(habitacion['precio'], personas, noches)

            session['detalle_reserva'] = {
                'fecha_entrada': fecha_entrada,
                'fecha_salida': fecha_salida,
                'personas': personas,
                'tipo_estancia': tipo_estancia or habitacion['tipo'],
                'comentarios': comentarios,
                'noches': noches,
                'total': total,
                'habitacion': habitacion
            }

            return redirect(url_for('cobro'))

        datos = {
            'fecha_entrada': fecha_entrada,
            'fecha_salida': fecha_salida,
            'personas': personas,
            'tipo_estancia': tipo_estancia,
            'comentarios': comentarios,
            'habitacion': habitacion
        }

    return render_template(
        'detalles_reserva.html',
        cliente=session.get('cliente_reserva'),
        habitaciones=HABITACIONES_CROQUIS,
        datos=datos,
        error=error
    )


@app.route('/cobro', methods=['GET', 'POST'])
def cobro():
    if 'cliente_reserva' not in session or 'detalle_reserva' not in session:
        return redirect(url_for('reservas'))

    cliente = session['cliente_reserva']
    detalle = session['detalle_reserva']

    if request.method == 'POST':
        titular = request.form.get('titular', '').strip()
        tarjeta = request.form.get('tarjeta', '').strip()
        vencimiento = request.form.get('vencimiento', '').strip()
        cvv = request.form.get('cvv', '').strip()

        confirmacion = {
            'folio': str(uuid.uuid4())[:8].upper(),
            'cliente': cliente,
            'detalle': detalle,
            'pago': {
                'titular': titular,
                'tarjeta': tarjeta[-4:] if len(tarjeta) >= 4 else tarjeta,
                'vencimiento': vencimiento,
                'cvv': cvv
            }
        }

        session['confirmacion_reserva'] = confirmacion
        RESERVAS_CONFIRMADAS.append(confirmacion)

        return redirect(url_for('confirmacion_reserva'))

    return render_template('cobro.html', cliente=cliente, detalle=detalle)


@app.route('/reservas/confirmacion')
def confirmacion_reserva():
    if 'confirmacion_reserva' not in session:
        return redirect(url_for('reservas'))

    return render_template(
        'confirmacion_reserva.html',
        reserva=session['confirmacion_reserva']
    )


# -------------------------
# ADMINISTRADOR
# -------------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None

    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        password = request.form.get('password', '').strip()

        if usuario == ADMIN_USER and password == ADMIN_PASS:
            session['admin_autenticado'] = True
            session['admin_usuario'] = usuario
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Credenciales de administrador incorrectas.'

    return render_template('admin_login.html', error=error)

@app.route('/admin/clients')
@admin_required
def admin_clients():
    clientes = obtener_clientes_admin()

    total_clientes = len(clientes)
    clientes_activos = sum(1 for c in clientes if c["reservas"] >= 1)
    ingresos_clientes = sum(c["gastado"] for c in clientes)
    noches_clientes = sum(c["noches"] for c in clientes)

    return render_template(
        'admin_clients.html',
        clientes=clientes,
        total_clientes=total_clientes,
        clientes_activos=clientes_activos,
        ingresos_clientes=ingresos_clientes,
        noches_clientes=noches_clientes
    )

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_autenticado', None)
    session.pop('admin_usuario', None)
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    resumen = resumen_admin()
    return render_template(
        'admin_dashboard.html',
        resumen=resumen,
        reservas=RESERVAS_CONFIRMADAS
    )


if __name__ == '__main__':
    app.run(debug=True)