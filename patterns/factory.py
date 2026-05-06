"""
Patrón Factory Method 
En lugar de construir dicts de habitación o insertar facturas
con SQL disperso en las rutas, estas fábricas centralizan
la creación de cada tipo de objeto.
"""

from abc import ABC, abstractmethod
from datetime import date


# =========================
# FÁBRICA DE HABITACIONES (objetos Python)
# =========================
class HabitacionBase(ABC):
    """Interfaz común para todos los tipos de habitación."""

    def __init__(self, datos: dict):
        self.id_db        = datos.get("id_habitacion")
        self.numero       = str(datos.get("numero", ""))
        self.nombre       = datos.get("observaciones") or datos.get("nombre", "")
        self.tipo         = datos.get("nombre_tipo") or datos.get("tipo", "")
        self.precio       = float(datos.get("precio_base") or datos.get("precio", 0))
        self.estado       = (datos.get("estado") or "libre").lower()

    @abstractmethod
    def descripcion(self) -> str: ...

    def to_dict(self) -> dict:
        return {
            "id_db":  self.id_db,
            "numero": self.numero,
            "nombre": self.nombre,
            "tipo":   self.tipo,
            "precio": self.precio,
            "estado": self.estado,
        }


class SuiteVistaMar(HabitacionBase):
    def descripcion(self): return f"Suite vista al mar — hab. {self.numero} '{self.nombre}'"


class JuniorSuite(HabitacionBase):
    def descripcion(self): return f"Junior Suite — hab. {self.numero} '{self.nombre}'"


class DeluxeGarden(HabitacionBase):
    def descripcion(self): return f"Deluxe Garden — hab. {self.numero} '{self.nombre}'"


class HabitacionGenerica(HabitacionBase):
    def descripcion(self): return f"Habitación {self.numero} — {self.tipo}"


class FabricaHabitacion:
    """
    Crea el objeto de habitación correcto según el tipo_nombre de la BD.

    Uso — reemplaza el dict inline en get_habitacion_por_numero():
        fila = fetch_one("SELECT ... FROM HABITACIONES ...")
        hab  = FabricaHabitacion.crear(fila)
        return hab.to_dict()
    """

    _tipos: dict = {
        "suite vista mar": SuiteVistaMar,
        "junior suite":    JuniorSuite,
        "deluxe garden":   DeluxeGarden,
    }

    @classmethod
    def crear(cls, datos: dict) -> HabitacionBase:
        tipo_key = (datos.get("nombre_tipo") or datos.get("tipo") or "").lower()
        clase = cls._tipos.get(tipo_key, HabitacionGenerica)
        return clase(datos)


# =========================
# FÁBRICA DE DOCUMENTOS (Factura / Pago)
# =========================
class DocumentoContable(ABC):
    @abstractmethod
    def insertar(self, execute_query_fn) -> int:
        """Persiste el documento y devuelve el id generado."""
        ...


class Factura(DocumentoContable):
    """
    Encapsula la lógica de creación de una factura, incluyendo
    el cálculo de subtotal e impuestos (IVA 16 %).

    Uso en /cobro, después de insertar la reserva:
        factura = Factura(id_reserva, id_cliente, total)
        id_factura = factura.insertar(execute_query)
    """

    IVA = 0.16

    def __init__(self, id_reserva: int, id_cliente: int, total: float):
        self.id_reserva  = id_reserva
        self.id_cliente  = id_cliente
        self.total       = round(float(total), 2)
        self.subtotal    = round(self.total / (1 + self.IVA), 2)
        self.impuestos   = round(self.total - self.subtotal, 2)
        self.fecha       = date.today()

    def insertar(self, execute_query_fn) -> int:
        return execute_query_fn(
            """
            INSERT INTO FACTURAS
                (id_reserva, id_cliente, fecha_factura, subtotal, impuestos, total, estado_factura)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                self.id_reserva, self.id_cliente, self.fecha,
                self.subtotal, self.impuestos, self.total, "pagada",
            ),
        )


class Pago(DocumentoContable):
    """
    Registra un pago vinculado a una factura.

    Uso en /cobro, después de crear la factura:
        pago = Pago(id_factura, id_reserva, total)
        pago.insertar(execute_query)
    """

    def __init__(self, id_factura: int, id_reserva: int, monto: float):
        self.id_factura  = id_factura
        self.referencia  = f"REF-{id_reserva}"
        self.monto       = round(float(monto), 2)
        self.fecha       = date.today()

    def insertar(self, execute_query_fn) -> int:
        return execute_query_fn(
            """
            INSERT INTO PAGOS
                (id_factura, fecha_pago, monto, referencia, estado_pago)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (self.id_factura, self.fecha, self.monto, self.referencia, "aprobado"),
        )


class FabricaDocumento:
    """
    Crea y persiste factura + pago en una sola llamada.

    Uso en /cobro — reemplaza las dos inserciones SQL directas:
        id_factura = FabricaDocumento.crear_factura_y_pago(
            execute_query, id_reserva, id_cliente, total
        )
    """

    @staticmethod
    def crear_factura_y_pago(execute_query_fn, id_reserva: int, id_cliente: int, total: float) -> int:
        factura = Factura(id_reserva, id_cliente, total)
        id_factura = factura.insertar(execute_query_fn)

        pago = Pago(id_factura, id_reserva, total)
        pago.insertar(execute_query_fn)

        return id_factura