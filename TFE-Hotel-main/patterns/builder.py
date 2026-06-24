"""
Patrón Builder 
Construye los reportes del panel de administrador paso a paso.
Cada método del builder agrega una sección al reporte.
"""
from abc import ABC, abstractmethod


# =========================
# PRODUCTO: el reporte terminado
# =========================
class ReporteAdmin:
    def __init__(self):
        self.resumen:            dict = {}
        self.por_habitacion:     list = []
        self.clientes_top:       list = []
        self.ocupacion_por_tipo: dict = {}
        self.ingresos_por_mes:   list = []

    def to_dict(self) -> dict:
        return {
            "resumen":            self.resumen,
            "por_habitacion":     self.por_habitacion,
            "clientes_top":       self.clientes_top,
            "ocupacion_por_tipo": self.ocupacion_por_tipo,
            "ingresos_por_mes":   self.ingresos_por_mes,
        }


# =========================
# BUILDER ABSTRACTO
# =========================
class BuilderReporte(ABC):
    @abstractmethod
    def reset(self): ...
    @abstractmethod
    def agregar_resumen(self, reservas: list): ...
    @abstractmethod
    def agregar_detalle_habitaciones(self, reservas: list): ...
    @abstractmethod
    def agregar_clientes_top(self, reservas: list, limite: int): ...
    @abstractmethod
    def agregar_ocupacion_por_tipo(self, reservas: list): ...
    @abstractmethod
    def obtener_reporte(self) -> ReporteAdmin: ...


# =========================
# BUILDER CONCRETO
# =========================
class BuilderReporteHotel(BuilderReporte):
    """
    Construye el reporte a partir de la lista de reservas que
    devuelve get_reservas_db() (ya disponible en app.py).
    """

    def reset(self):
        self._reporte = ReporteAdmin()

    def __init__(self):
        self.reset()

    def agregar_resumen(self, reservas: list):
        total_ingresos = sum(r["detalle"]["total"] for r in reservas)
        total_noches   = sum(r["detalle"]["noches"] for r in reservas)
        habitaciones   = {r["detalle"]["habitacion"]["numero"] for r in reservas}

        self._reporte.resumen = {
            "total_reservas":      len(reservas),
            "habitaciones_usadas": len(habitaciones),
            "ingresos_totales":    round(total_ingresos, 2),
            "total_noches":        total_noches,
            "ticket_promedio":     round(total_ingresos / len(reservas), 2) if reservas else 0,
        }
        return self

    def agregar_detalle_habitaciones(self, reservas: list):
        agrupado: dict = {}
        for r in reservas:
            hab = r["detalle"]["habitacion"]
            key = hab["numero"]
            if key not in agrupado:
                agrupado[key] = {
                    "numero":   hab["numero"],
                    "nombre":   hab["nombre"],
                    "tipo":     hab["tipo"],
                    "reservas": 0,
                    "noches":   0,
                    "ingresos": 0,
                }
            agrupado[key]["reservas"] += 1
            agrupado[key]["noches"]   += r["detalle"]["noches"]
            agrupado[key]["ingresos"] += r["detalle"]["total"]

        self._reporte.por_habitacion = sorted(
            agrupado.values(), key=lambda x: x["ingresos"], reverse=True
        )
        return self

    def agregar_clientes_top(self, reservas: list, limite: int = 5):
        clientes: dict = {}
        for r in reservas:
            email = (r["cliente"]["email"] or "").lower() or r["cliente"]["nombre"]
            if email not in clientes:
                clientes[email] = {
                    "nombre":   r["cliente"]["nombre"],
                    "email":    r["cliente"]["email"],
                    "reservas": 0,
                    "noches":   0,
                    "gastado":  0,
                }
            clientes[email]["reservas"] += 1
            clientes[email]["noches"]   += r["detalle"]["noches"]
            clientes[email]["gastado"]  += r["detalle"]["total"]

        self._reporte.clientes_top = sorted(
            clientes.values(), key=lambda c: c["gastado"], reverse=True
        )[:limite]
        return self

    def agregar_ocupacion_por_tipo(self, reservas: list):
        por_tipo: dict = {}
        for r in reservas:
            tipo = r["detalle"]["tipo_estancia"]
            if tipo not in por_tipo:
                por_tipo[tipo] = {"reservas": 0, "noches": 0, "ingresos": 0}
            por_tipo[tipo]["reservas"] += 1
            por_tipo[tipo]["noches"]   += r["detalle"]["noches"]
            por_tipo[tipo]["ingresos"] += r["detalle"]["total"]

        self._reporte.ocupacion_por_tipo = por_tipo
        return self

    def obtener_reporte(self) -> ReporteAdmin:
        reporte = self._reporte
        self.reset()
        return reporte


# =========================
# DIRECTOR — orquesta el orden de construcción
# =========================
class DirectorReporte:
    """
    Uso en admin_dashboard()

        from patterns.builder import DirectorReporte, BuilderReporteHotel
        reservas = get_reservas_db()
        builder  = BuilderReporteHotel()
        director = DirectorReporte(builder)

        reporte_completo = director.reporte_gerente(reservas)
        reporte_dict     = reporte_completo.to_dict()

        return render_template("admin_dashboard.html",
                               resumen=reporte_dict["resumen"],
                               reservas=reservas,
                               reporte=reporte_dict)
    """

    def __init__(self, builder: BuilderReporte):
        self._builder = builder

    def reporte_gerente(self, reservas: list) -> ReporteAdmin:
        """Reporte completo con todas las secciones."""
        return (
            self._builder
            .agregar_resumen(reservas)
            .agregar_detalle_habitaciones(reservas)
            .agregar_clientes_top(reservas, limite=5)
            .agregar_ocupacion_por_tipo(reservas)
            .obtener_reporte()
        )

    def reporte_rapido(self, reservas: list) -> ReporteAdmin:
        """Solo resumen y habitaciones, para carga rápida."""
        return (
            self._builder
            .agregar_resumen(reservas)
            .agregar_detalle_habitaciones(reservas)
            .obtener_reporte()
        )