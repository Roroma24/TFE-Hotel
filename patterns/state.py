"""
Patrón State
Modela los estados de HABITACIÓN y RESERVA como objetos.
Cada estado sabe qué transiciones son válidas desde él.
Se hace uso de: HabitacionContext y ReservaContext 
"""

from abc import ABC, abstractmethod


# =========================
# ESTADOS DE HABITACIÓN
# =========================
class EstadoHabitacion(ABC):
    @abstractmethod
    def nombre(self) -> str: ...

    def reservar(self, ctx): raise ValueError(f"No se puede reservar desde '{self.nombre()}'")
    def hacer_checkin(self, ctx): raise ValueError(f"No se puede hacer check-in desde '{self.nombre()}'")
    def hacer_checkout(self, ctx): raise ValueError(f"No se puede hacer check-out desde '{self.nombre()}'")
    def liberar(self, ctx): raise ValueError(f"No se puede liberar desde '{self.nombre()}'")


class HabitacionLibre(EstadoHabitacion):
    def nombre(self): return "libre"
    def reservar(self, ctx): ctx.set_estado(HabitacionReservada())


class HabitacionReservada(EstadoHabitacion):
    def nombre(self): return "reservada"
    def hacer_checkin(self, ctx): ctx.set_estado(HabitacionOcupada())
    def liberar(self, ctx): ctx.set_estado(HabitacionLibre())


class HabitacionOcupada(EstadoHabitacion):
    def nombre(self): return "ocupada"
    def hacer_checkout(self, ctx): ctx.set_estado(HabitacionLibre())


class HabitacionContext:
    """
    Envuelve una habitación de la BD y gestiona sus transiciones.

    Ejemplo de uso en app.py (check-in):
        ctx = HabitacionContext("reservada")
        ctx.hacer_checkin()          # valida la transición
        execute_query(
            "UPDATE HABITACIONES SET estado = %s WHERE id_habitacion = %s",
            (ctx.estado_actual(), id_habitacion)
        )
    """
    _estados = {
        "libre":     HabitacionLibre,
        "reservada": HabitacionReservada,
        "ocupada":   HabitacionOcupada,
    }

    def __init__(self, estado_bd: str):
        clase = self._estados.get(estado_bd.lower(), HabitacionLibre)
        self._estado: EstadoHabitacion = clase()

    def set_estado(self, nuevo: EstadoHabitacion):
        self._estado = nuevo

    def estado_actual(self) -> str:
        return self._estado.nombre()

    def reservar(self):       self._estado.reservar(self)
    def hacer_checkin(self):  self._estado.hacer_checkin(self)
    def hacer_checkout(self): self._estado.hacer_checkout(self)
    def liberar(self):        self._estado.liberar(self)


# =========================
# ESTADOS DE RESERVA
# =========================
class EstadoReserva(ABC):
    @abstractmethod
    def nombre(self) -> str: ...

    def confirmar(self, ctx): raise ValueError(f"No se puede confirmar desde '{self.nombre()}'")
    def hacer_checkin(self, ctx): raise ValueError(f"No se puede hacer check-in desde '{self.nombre()}'")
    def hacer_checkout(self, ctx): raise ValueError(f"No se puede hacer check-out desde '{self.nombre()}'")


class ReservaPendiente(EstadoReserva):
    def nombre(self): return "pendiente"
    def confirmar(self, ctx): ctx.set_estado(ReservaConfirmada())


class ReservaConfirmada(EstadoReserva):
    def nombre(self): return "confirmada"
    def hacer_checkin(self, ctx): ctx.set_estado(ReservaCheckedIn())


class ReservaCheckedIn(EstadoReserva):
    def nombre(self): return "checked_in"
    def hacer_checkout(self, ctx): ctx.set_estado(ReservaCheckedOut())


class ReservaCheckedOut(EstadoReserva):
    def nombre(self): return "checked_out"


class ReservaContext:
    """
    Ejemplo de uso en admin_check_in():
        ctx = ReservaContext(reserva["estado_reserva"])
        ctx.hacer_checkin()
        execute_query(
            "UPDATE RESERVAS SET estado_reserva = %s WHERE id_reserva = %s",
            (ctx.estado_actual(), id_reserva)
        )
    """
    _estados = {
        "pendiente":   ReservaPendiente,
        "confirmada":  ReservaConfirmada,
        "checked_in":  ReservaCheckedIn,
        "checkin":     ReservaCheckedIn,
        "checked_out": ReservaCheckedOut,
    }

    def __init__(self, estado_bd: str):
        clase = self._estados.get((estado_bd or "pendiente").lower(), ReservaPendiente)
        self._estado: EstadoReserva = clase()

    def set_estado(self, nuevo: EstadoReserva):
        self._estado = nuevo

    def estado_actual(self) -> str:
        return self._estado.nombre()

    def confirmar(self):      self._estado.confirmar(self)
    def hacer_checkin(self):  self._estado.hacer_checkin(self)
    def hacer_checkout(self): self._estado.hacer_checkout(self)