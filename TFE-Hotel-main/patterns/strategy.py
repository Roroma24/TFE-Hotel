"""
Patrón Strategy
Encapsula las distintas formas de crear una reserva
(online por el cliente vs. en recepción) y los distintos
algoritmos de cálculo de tarifa.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime


# =========================
# ESTRATEGIAS DE RESERVA
# =========================
class EstrategiaReserva(ABC):
    """Define cómo se crea y valida una reserva."""

    @abstractmethod
    def estado_inicial(self) -> str:
        """Estado con el que se inserta la reserva en la BD."""
        ...

    @abstractmethod
    def requiere_pago_inmediato(self) -> bool: ...

    @abstractmethod
    def origen(self) -> str:
        """Texto para el campo observaciones / auditoría."""
        ...


class ReservaOnline(EstrategiaReserva):
    """
    Reserva hecha por el cliente desde la web.
    Estado inicial: 'confirmada' (pago ya procesado).
    """
    def estado_inicial(self): return "confirmada"
    def requiere_pago_inmediato(self): return True
    def origen(self): return "Reserva online por cliente"


class ReservaRecepcion(EstrategiaReserva):
    """
    Reserva registrada por recepcionista.
    Estado inicial: 'confirmada'. Puede activar check-in directo.
    """
    def __init__(self, checkin_directo: bool = False):
        self._checkin_directo = checkin_directo

    def estado_inicial(self):
        return "checked_in" if self._checkin_directo else "confirmada"

    def requiere_pago_inmediato(self): return False
    def origen(self): return "Reserva desde recepción"

    @property
    def checkin_directo(self): return self._checkin_directo


# =========================
# ESTRATEGIAS DE TARIFA
# =========================
class EstrategiaTarifa(ABC):
    @abstractmethod
    def calcular(self, precio_base: float, personas: int, noches: int) -> float: ...


class TarifaEstandar(EstrategiaTarifa):
    """
    Tarifa base + $45 por persona extra (más de 2) por noche.
    Replica exactamente calcular_total() actual.
    """
    CARGO_PERSONA_EXTRA = 45.0

    def calcular(self, precio_base: float, personas: int, noches: int) -> float:
        total = precio_base * noches
        if personas > 2:
            total += (personas - 2) * self.CARGO_PERSONA_EXTRA * noches
        return round(total, 2)


class TarifaTemporadaAlta(EstrategiaTarifa):
    """Aplica un factor de 1.25 sobre la tarifa estándar."""
    def __init__(self):
        self._base = TarifaEstandar()

    def calcular(self, precio_base: float, personas: int, noches: int) -> float:
        return round(self._base.calcular(precio_base, personas, noches) * 1.25, 2)


class TarifaDescuento(EstrategiaTarifa):
    """Descuento porcentual configurable (ej: 10 %)."""
    def __init__(self, descuento_pct: float = 10.0):
        self._descuento = descuento_pct / 100
        self._base = TarifaEstandar()

    def calcular(self, precio_base: float, personas: int, noches: int) -> float:
        total = self._base.calcular(precio_base, personas, noches)
        return round(total * (1 - self._descuento), 2)


# =========================
# CONTEXTO — punto de entrada único
# =========================
class ContextoReserva:
    """
    Centraliza la lógica de creación de reservas.

    Uso en /cobro (app.py):
        estrategia = ReservaOnline()
        tarifa = TarifaEstandar()
        ctx = ContextoReserva(estrategia, tarifa)
        total = ctx.calcular_total(habitacion["precio"], personas, noches)
        estado = ctx.estado_reserva()   # "confirmada"

    Uso en /admin/nueva-reservacion:
        es_directo = (checkin_directo == "on")
        estrategia = ReservaRecepcion(checkin_directo=es_directo)
        ctx = ContextoReserva(estrategia, TarifaEstandar())
        total  = ctx.calcular_total(...)
        estado = ctx.estado_reserva()
    """

    def __init__(self, estrategia: EstrategiaReserva, tarifa: EstrategiaTarifa = None):
        self._estrategia = estrategia
        self._tarifa = tarifa or TarifaEstandar()

    def calcular_total(self, precio_base: float, personas: int, noches: int) -> float:
        return self._tarifa.calcular(precio_base, int(personas), int(noches))

    def estado_reserva(self) -> str:
        return self._estrategia.estado_inicial()

    def requiere_pago(self) -> bool:
        return self._estrategia.requiere_pago_inmediato()

    def origen(self) -> str:
        return self._estrategia.origen()