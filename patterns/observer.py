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
import os
import smtplib
from email.message import EmailMessage

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
    Envía un correo de confirmación al cliente cuando la reserva se confirma o paga.
    """
    EVENTOS_CORREO = {"reserva_confirmada", "checkin_realizado", "checkout_realizado", "pago_realizado"}

    def actualizar(self, evento: str, datos: dict):
        if evento not in self.EVENTOS_CORREO:
            return

        email = datos.get("cliente", {}).get("email", "") or datos.get("email", "")
        folio = datos.get("folio", "")
        if not email:
            return

        detalle = datos.get("detalle", {}) or {}
        habitacion = detalle.get("habitacion", {}) or {}
        fecha_entrada = detalle.get("fecha_entrada", "")
        fecha_salida = detalle.get("fecha_salida", "")
        noches = detalle.get("noches", "")
        monto_pagado = datos.get("monto_pagado")

        asunto = f"Reserva confirmada - {folio}" if evento in {"reserva_confirmada", "pago_realizado"} else f"Actualización de reserva - {folio}"
        nombre_cliente = datos.get("cliente", {}).get("nombre", "") or "Estimado huésped"

        texto = (
            f"Hola {nombre_cliente},\n\n"
            f"Tu reserva ha sido procesada correctamente.\n"
            f"Folio: {folio}\n"
            f"Evento: {evento}\n"
            f"Habitación: {habitacion.get('nombre', 'No especificada')}\n"
        )
        if fecha_entrada:
            texto += f"Fecha de entrada: {fecha_entrada}\n"
        if fecha_salida:
            texto += f"Fecha de salida: {fecha_salida}\n"
        if noches:
            texto += f"Noches: {noches}\n"
        if monto_pagado is not None:
            texto += f"Monto pagado: {monto_pagado:.2f} MXN\n"
        texto += "Gracias por elegir Plaza Delfino."

        html = f"""
        <html>
          <body style="margin:0; padding:0; background-color:#f5f2ea; font-family:Arial, sans-serif; color:#2f2f2f;">
            <div style="max-width:640px; margin:24px auto; background:#ffffff; border-radius:14px; overflow:hidden; box-shadow:0 8px 24px rgba(0,0,0,0.08);">
              <div style="background:linear-gradient(135deg, #1849b8 0%, #1849b8 100%); padding:28px 32px; color:#ffffff;">
                <h2 style="margin:0 0 8px 0; font-size:24px;">Plaza Delfino</h2>
                <p style="margin:0; font-size:15px; opacity:0.95;">Confirmación de reserva y pago</p>
              </div>
              <div style="padding:28px 32px 20px 32px;">
                <p style="margin:0 0 16px 0; font-size:16px;">Hola <strong>{nombre_cliente}</strong>,</p>
                <p style="margin:0 0 16px 0; line-height:1.6;">Tu reserva ha sido procesada correctamente y ya quedó registrada en nuestro sistema.</p>
                <div style="background:#f8f6ef; border-left:4px solid #caa56a; padding:16px 18px; border-radius:10px; margin-bottom:18px;">
                  <p style="margin:0 0 6px 0; font-size:14px; color:#6b6b6b; text-transform:uppercase; letter-spacing:0.04em;">Detalles de la reserva</p>
                  <p style="margin:4px 0; font-size:15px;"><strong>Folio:</strong> {folio}</p>
                  <p style="margin:4px 0; font-size:15px;"><strong>Evento:</strong> {evento}</p>
                  <p style="margin:4px 0; font-size:15px;"><strong>Habitación:</strong> {habitacion.get('nombre', 'No especificada')}</p>
                </div>
                <div style="display:grid; gap:8px; margin-bottom:18px;">
                  {f'<p style="margin:0; font-size:15px;"><strong>Fecha de entrada:</strong> {fecha_entrada}</p>' if fecha_entrada else ''}
                  {f'<p style="margin:0; font-size:15px;"><strong>Fecha de salida:</strong> {fecha_salida}</p>' if fecha_salida else ''}
                  {f'<p style="margin:0; font-size:15px;"><strong>Noches:</strong> {noches}</p>' if noches else ''}
                  {f'<p style="margin:0; font-size:15px;"><strong>Monto pagado:</strong> {monto_pagado:.2f} MXN</p>' if monto_pagado is not None else ''}
                </div>
                <p style="margin:0 0 10px 0; line-height:1.6;">Gracias por elegir <strong>Plaza Delfino</strong>. Estamos listos para recibirte.</p>
              </div>
              <div style="background:#f5f2ea; padding:16px 32px 24px 32px; text-align:center; font-size:12px; color:#777777;">
                Este correo se envió automáticamente desde el sistema de reservas.
              </div>
            </div>
          </body>
        </html>
        """

        mensaje = EmailMessage()
        mensaje["Subject"] = asunto
        mensaje["From"] = os.getenv("MAIL_DEFAULT_SENDER", "no-reply@plazadelfino.local")
        mensaje["To"] = email
        mensaje.set_content(texto)
        mensaje.add_alternative(html, subtype="html")

        servidor = os.getenv("MAIL_SERVER")
        if not servidor:
            logger.info(f"[Correo] Configuración SMTP no encontrada. Simulando envío a {email} | Folio: {folio}")
            print(f"  📧 Correo enviado a {email} — evento: {evento}, folio: {folio}")
            return

        try:
            with smtplib.SMTP(servidor, int(os.getenv("MAIL_PORT", "587"))) as smtp:
                if os.getenv("MAIL_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}:
                    smtp.starttls()
                usuario = os.getenv("MAIL_USERNAME")
                password = os.getenv("MAIL_PASSWORD")
                if usuario and password:
                    smtp.login(usuario, password)
                smtp.send_message(mensaje)
            logger.info(f"[Correo] Evento '{evento}' → {email} | Folio: {folio}")
            print(f"  📧 Correo enviado a {email} — evento: {evento}, folio: {folio}")
        except Exception as exc:
            logger.error(f"[Correo] No se pudo enviar el correo a {email}: {exc}")
            print(f"  ⚠️ No se pudo enviar el correo a {email}: {exc}")


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