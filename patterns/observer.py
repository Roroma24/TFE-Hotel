"""
Patrón Observer
Cuando una reserva cambia de estado, se notifican
automáticamente todos los observadores registrados
(correo al cliente, actualización de habitación, log, etc.)
sin que el código de la ruta sepa quiénes están suscritos.
"""

from abc import ABC, abstractmethod
from typing import List
import logging

logger = logging.getLogger(__name__)


# =========================
# INTERFAZ BASE
# =========================
class ObservadorReserva(ABC):
    @abstractmethod
    def actualizar(self, evento: str, datos: dict): ...


# =========================
# OBSERVADORES CONCRETOS
# =========================
class ObservadorCorreo(ObservadorCorreo if False else ObservadorReserva):
    """
    Envía un correo de confirmación al cliente.
    Después se sustituirá el print por flask_mail o smtplib.
    """
    EVENTOS_CORREO = {"reserva_confirmada", "checkin_realizado", "checkout_realizado"}

    def actualizar(self, evento: str, datos: dict):
        if evento not in self.EVENTOS_CORREO:
            return
        email = datos.get("cliente", {}).get("email", "")
        folio = datos.get("folio", "")
        if not email:
            return
        # TODO: reemplazar con flask_mail.send_message(...)
        logger.info(f"[Correo] Evento '{evento}' → {email} | Folio: {folio}")
        print(f"  📧 Correo enviado a {email} — evento: {evento}, folio: {folio}")


class ObservadorHabitacion(ObservadorReserva):
    """
    Mantiene el estado de la habitación sincronizado con
    el estado de la reserva. Llama directamente a execute_query.
    """
    def __init__(self, execute_query_fn):
        self._exec = execute_query_fn

    def actualizar(self, evento: str, datos: dict):
        id_habitacion = datos.get("id_habitacion")
        if not id_habitacion:
            return

        mapa = {
            "reserva_confirmada":  "reservada",
            "checkin_realizado":   "ocupada",
            "checkout_realizado":  "libre",
            "reserva_cancelada":   "libre",
        }
        nuevo_estado = mapa.get(evento)
        if nuevo_estado:
            self._exec(
                "UPDATE HABITACIONES SET estado = %s WHERE id_habitacion = %s",
                (nuevo_estado, id_habitacion),
            )
            logger.info(f"[Habitación {id_habitacion}] → {nuevo_estado}")


class ObservadorLog(ObservadorReserva):
    """Registra cada cambio de estado en el log de la aplicación."""
    def actualizar(self, evento: str, datos: dict):
        logger.info(
            f"[ReservaEvent] evento={evento} | "
            f"folio={datos.get('folio')} | "
            f"cliente={datos.get('cliente', {}).get('nombre')}"
        )


# =========================
# SUJETO (publicador de eventos)
# =========================
class GestorEventosReserva:
    """
    Punto central donde las rutas publican eventos.
    Los observadores se registran una sola vez al arrancar la app.

    Uso en app.py (al inicio, después de init_db_pool):
        from patterns.observer import GestorEventosReserva, ObservadorCorreo, ObservadorHabitacion, ObservadorLog
        gestor_eventos = GestorEventosReserva()
        gestor_eventos.suscribir(ObservadorCorreo())
        gestor_eventos.suscribir(ObservadorHabitacion(execute_query))
        gestor_eventos.suscribir(ObservadorLog())

    Uso en la ruta /cobro, después de insertar la reserva:
        gestor_eventos.notificar("reserva_confirmada", {
            "folio": format_folio(id_reserva),
            "id_habitacion": id_habitacion,
            "cliente": {"nombre": cliente["nombre"], "email": cliente["email"]},
        })

    Uso en admin_check_in:
        gestor_eventos.notificar("checkin_realizado", {
            "folio": folio,
            "id_habitacion": reserva["id_habitacion"],
            "cliente": {"nombre": "...", "email": "..."},
        })
    """

    def __init__(self):
        self._observadores: List[ObservadorReserva] = []

    def suscribir(self, observador: ObservadorReserva):
        self._observadores.append(observador)

    def desuscribir(self, observador: ObservadorReserva):
        self._observadores.remove(observador)

    def notificar(self, evento: str, datos: dict):
        for obs in self._observadores:
            try:
                obs.actualizar(evento, datos)
            except Exception as e:
                logger.error(f"[Observer] Error en {obs.__class__.__name__}: {e}")


# =========================
# Instancia global — importar desde app.py
# =========================
gestor_eventos = GestorEventosReserva()