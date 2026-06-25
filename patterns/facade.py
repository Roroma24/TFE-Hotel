"""
Patrón Facade 
ServicioReservas es una interfaz simplificada que orquesta
todos los subsistemas (BD, estados, tarifas, documentos, eventos)
para cada operación hotelera principal.
Las rutas de Flask solo llaman a ServicioReservas — no conocen
los detalles internos de ningún patrón.
"""

from datetime import date, datetime

from patterns.state    import HabitacionContext, ReservaContext
from patterns.strategy import ContextoReserva, ReservaOnline, ReservaRecepcion, TarifaEstandar
from patterns.factory  import FabricaHabitacion, FabricaDocumento
from patterns.observer import gestor_eventos


class ServicioReservas:
    """
    Punto único de entrada para la lógica de negocio.

    Inyectar las funciones de BD al instanciar (evita import circular):
        from patterns.facade import ServicioReservas
        from database.db import fetch_one, fetch_all, execute_query
        svc = ServicioReservas(fetch_one, fetch_all, execute_query)

    O crear una instancia global en database/db.py y exportarla.
    """

    def __init__(self, fetch_one_fn, fetch_all_fn, execute_query_fn):
        self._fetch_one   = fetch_one_fn
        self._fetch_all   = fetch_all_fn
        self._exec        = execute_query_fn

    # =========================
    # RESERVA ONLINE (ruta /cobro)
    # =========================
    def crear_reserva_online(
        self,
        id_cliente: int,
        id_habitacion: int,
        id_usuario: int,
        fecha_entrada: str,
        fecha_salida: str,
        personas: int,
        precio_base: float,
        noches: int,
    ) -> dict:
        """
        Orquesta: Strategy → INSERT reserva → Factory (factura + pago)
                  → State (habitación) → Observer (correo + log)
        Devuelve {"id_reserva": ..., "total": ..., "folio": ...}
        """
        ctx = ContextoReserva(ReservaOnline(), TarifaEstandar())
        total = ctx.calcular_total(precio_base, personas, noches)

        # =========================
        # Insertar reserva
        # =========================
        id_reserva = self._exec(
            """
            INSERT INTO RESERVAS
                (id_cliente, id_habitacion, id_usuario, fecha_reserva,
                 fecha_entrada, fecha_salida, cantidad_huespedes, estado_reserva, total_estimado)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (id_cliente, id_habitacion, id_usuario, date.today(),
             fecha_entrada, fecha_salida, personas, ctx.estado_reserva(), total),
        )

        # =========================
        # Factura + pago (Factory)
        # =========================
        FabricaDocumento.crear_factura_y_pago(self._exec, id_reserva, id_cliente, total)

        # =========================
        # Estado habitación (State)
        # =========================
        hab_ctx = HabitacionContext("libre")
        hab_ctx.reservar()
        self._exec(
            "UPDATE HABITACIONES SET estado = %s WHERE id_habitacion = %s",
            (hab_ctx.estado_actual(), id_habitacion),
        )

        folio = f"RSV-{id_reserva:05d}"

        # =========================
        # Notificar observadores
        # =========================
        gestor_eventos.notificar("reserva_confirmada", {
            "folio": folio,
            "id_habitacion": id_habitacion,
            "cliente": {"email": ""},   
        })

        return {"id_reserva": id_reserva, "total": total, "folio": folio}

    # =========================
    # RESERVA EN RECEPCIÓN (/admin/nueva-reservacion)
    # =========================
    def crear_reserva_recepcion(
        self,
        id_cliente: int,
        id_habitacion: int,
        id_usuario: int,
        fecha_entrada: str,
        fecha_salida: str,
        personas: int,
        precio_base: float,
        noches: int,
        checkin_directo: bool = False,
    ) -> dict:
        estrategia = ReservaRecepcion(checkin_directo=checkin_directo)
        ctx = ContextoReserva(estrategia, TarifaEstandar())
        total = ctx.calcular_total(precio_base, personas, noches)

        id_reserva = self._exec(
            """
            INSERT INTO RESERVAS
                (id_cliente, id_habitacion, id_usuario, fecha_reserva,
                 fecha_entrada, fecha_salida, cantidad_huespedes, estado_reserva, total_estimado)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (id_cliente, id_habitacion, id_usuario, date.today(),
             fecha_entrada, fecha_salida, personas, ctx.estado_reserva(), total),
        )

        # =========================
        # Estado habitación
        # =========================
        estado_hab = "ocupada" if checkin_directo else "reservada"
        hab_ctx = HabitacionContext("libre")
        if checkin_directo:
            hab_ctx.reservar()
            hab_ctx.hacer_checkin()
        else:
            hab_ctx.reservar()
        self._exec(
            "UPDATE HABITACIONES SET estado = %s WHERE id_habitacion = %s",
            (hab_ctx.estado_actual(), id_habitacion),
        )

        # =========================
        # Check-in directo
        # =========================
        if checkin_directo:
            self._exec(
                """
                INSERT INTO CHECKIN (id_reserva, id_usuario, fecha_hora_checkin, observaciones)
                VALUES (%s,%s,%s,%s)
                """,
                (id_reserva, id_usuario, datetime.now(), "Check-in directo desde recepción"),
            )

        folio = f"RSV-{id_reserva:05d}"
        evento = "checkin_realizado" if checkin_directo else "reserva_confirmada"
        gestor_eventos.notificar(evento, {"folio": folio, "id_habitacion": id_habitacion, "cliente": {}})

        return {"id_reserva": id_reserva, "total": total, "folio": folio}

    # =========================
    # CHECK-IN
    # =========================
    def hacer_checkin(self, id_reserva: int, folio: str, id_usuario: int):
        reserva = self._fetch_one(
            "SELECT id_habitacion, estado_reserva FROM RESERVAS WHERE id_reserva = %s",
            (id_reserva,),
        )
        if not reserva:
            return

        res_ctx = ReservaContext(reserva["estado_reserva"])
        res_ctx.hacer_checkin()
        self._exec(
            "UPDATE RESERVAS SET estado_reserva = %s WHERE id_reserva = %s",
            (res_ctx.estado_actual(), id_reserva),
        )

        hab_ctx = HabitacionContext("reservada")
        hab_ctx.hacer_checkin()
        self._exec(
            "UPDATE HABITACIONES SET estado = %s WHERE id_habitacion = %s",
            (hab_ctx.estado_actual(), reserva["id_habitacion"]),
        )

        self._exec(
            """
            INSERT INTO CHECKIN (id_reserva, id_usuario, fecha_hora_checkin, observaciones)
            VALUES (%s,%s,%s,%s)
            """,
            (id_reserva, id_usuario, datetime.now(), "Check-in desde panel administrativo"),
        )

        gestor_eventos.notificar("checkin_realizado", {
            "folio": folio, "id_habitacion": reserva["id_habitacion"], "cliente": {},
        })

    # =========================
    # CHECK-OUT
    # =========================
    def hacer_checkout(self, id_reserva: int, folio: str, id_usuario: int):
        reserva = self._fetch_one(
            "SELECT id_habitacion, estado_reserva FROM RESERVAS WHERE id_reserva = %s",
            (id_reserva,),
        )
        if not reserva:
            return

        res_ctx = ReservaContext(reserva["estado_reserva"])
        res_ctx.hacer_checkout()
        self._exec(
            "UPDATE RESERVAS SET estado_reserva = %s WHERE id_reserva = %s",
            (res_ctx.estado_actual(), id_reserva),
        )

        hab_ctx = HabitacionContext("ocupada")
        hab_ctx.hacer_checkout()
        self._exec(
            "UPDATE HABITACIONES SET estado = %s WHERE id_habitacion = %s",
            (hab_ctx.estado_actual(), reserva["id_habitacion"]),
        )

        # Registrar checkout sin sumar consumos a la factura (cliente ya pagó la reserva)
        # Los consumos se mantienen en la tabla SERVICIOS y se muestran/acomulan por separado.
        self._exec(
            """
            INSERT INTO CHECKOUT (id_reserva, id_usuario, fecha_hora_checkout, observaciones, cargos_adicionales)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (id_reserva, id_usuario, datetime.now(), "Check-out desde panel administrativo", 0),
        )

        gestor_eventos.notificar("checkout_realizado", {
            "folio": folio, "id_habitacion": reserva["id_habitacion"], "cliente": {},
        })