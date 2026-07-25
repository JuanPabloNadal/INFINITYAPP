"""Modelo de datos de Infinity Inmobiliaria."""
from datetime import datetime, date
from decimal import Decimal

from .extensions import db

# --- Constantes de dominio -------------------------------------------------

TIPO_COMPRAVENTA = "COMPRAVENTA"
TIPO_ALQUILER = "ALQUILER"
TIPOS_OPERACION = [TIPO_COMPRAVENTA, TIPO_ALQUILER]

# Roles (puntas) según el tipo de operación.
ROL_VENDEDORA = "VENDEDORA"
ROL_COMPRADORA = "COMPRADORA"
ROL_LOCADORA = "LOCADORA"
ROL_LOCATARIA = "LOCATARIA"

ROLES_POR_TIPO = {
    TIPO_COMPRAVENTA: [ROL_VENDEDORA, ROL_COMPRADORA],
    TIPO_ALQUILER: [ROL_LOCADORA, ROL_LOCATARIA],
}

ETIQUETA_ROL = {
    ROL_VENDEDORA: "Punta vendedora",
    ROL_COMPRADORA: "Punta compradora",
    ROL_LOCADORA: "Punta locadora",
    ROL_LOCATARIA: "Punta locataria",
}

# Representación de cada punta.
REP_INFINITY = "INFINITY"
REP_DESARROLLO = "DESARROLLO"
REP_OTRA_INMOBILIARIA = "OTRA_INMOBILIARIA"
REP_PARTICULAR = "PARTICULAR"

ETIQUETA_REPRESENTACION = {
    REP_INFINITY: "Infinity (genera comisión)",
    REP_DESARROLLO: "Desarrollo (constructora/desarrolladora)",
    REP_OTRA_INMOBILIARIA: "Otra inmobiliaria",
    REP_PARTICULAR: "Particular / sin intermediación",
}

# Representaciones que generan comisión para Infinity (agente de Infinity cobra).
REPRESENTACIONES_CON_COMISION = (REP_INFINITY, REP_DESARROLLO)

# Forma de expresar la comisión.
COMISION_PORCENTAJE = "PORCENTAJE"
COMISION_MONTO_FIJO = "MONTO_FIJO"

MONEDA_ARS = "ARS"
MONEDA_USD = "USD"
MONEDAS = [MONEDA_ARS, MONEDA_USD]

# --- Figuras adicionales (Acta de Asamblea 001/2026) -----------------------
# Cobran un % de la comisión bruta de una línea, DESCONTADO ANTES de la
# retención; luego tanto el agente principal como cada figura dejan, CADA
# UNO, su propia retención en la inmobiliaria (no una retención única sobre
# el total). Datero/Captador de desarrollo/AAA solo aplican a compraventa
# (por voto del acta). Las figuras PERSONALIZADAS (creadas desde
# Configuración, para casos excepcionales) aplican a cualquier tipo.

FIGURA_DATERO = "DATERO"
FIGURA_CAPTADOR_DESARROLLO = "CAPTADOR_DESARROLLO"
FIGURA_AAA = "AAA"
FIGURA_PERSONALIZADA = "PERSONALIZADA"
TIPOS_FIGURA = [FIGURA_DATERO, FIGURA_CAPTADOR_DESARROLLO, FIGURA_AAA, FIGURA_PERSONALIZADA]

ETIQUETA_FIGURA = {
    FIGURA_DATERO: "Datero",
    FIGURA_CAPTADOR_DESARROLLO: "Captador de desarrollo",
    FIGURA_AAA: "Agente Asistente al Ausente (AAA)",
    FIGURA_PERSONALIZADA: "Figura personalizada",
}

# Situaciones del Agente Asistente al Ausente (AAA) — cada una define su
# propio % de la comisión de la punta. La situación A es especial: paga
# US$100 fijo, o 10% si la comisión total de la punta es menor a US$1.000
# (lo que sea menor de los dos) — ver app/services/calculo.py.
AAA_SITUACION_A = "A"
AAA_SITUACION_B1 = "B1"
AAA_SITUACION_B2 = "B2"
AAA_SITUACION_B3 = "B3"
AAA_SITUACION_C1 = "C1"
AAA_SITUACION_C2 = "C2"
AAA_SITUACIONES = [AAA_SITUACION_A, AAA_SITUACION_B1, AAA_SITUACION_B2,
                   AAA_SITUACION_B3, AAA_SITUACION_C1, AAA_SITUACION_C2]

ETIQUETA_AAA_SITUACION = {
    AAA_SITUACION_A: "Operación avanzada (oferta/reserva aceptada, fecha de firma tentativa)",
    AAA_SITUACION_B1: "AAA consigue la oferta; se concreta con el agente aún de viaje",
    AAA_SITUACION_B2: "AAA consigue la oferta de viaje; el agente regresa antes de concretarse",
    AAA_SITUACION_B3: "AAA consigue la oferta luego de que el agente ya regresó",
    AAA_SITUACION_C1: "AAA concreta con cliente cedido, sobre la MISMA propiedad ofrecida",
    AAA_SITUACION_C2: "AAA concreta con cliente cedido, sobre OTRA propiedad distinta",
}

# % fijo de cada situación (la situación A se calcula aparte, ver calculo.py).
AAA_PORCENTAJE_SITUACION = {
    AAA_SITUACION_B1: Decimal("50"),
    AAA_SITUACION_B2: Decimal("33"),
    AAA_SITUACION_B3: Decimal("25"),
    AAA_SITUACION_C1: Decimal("50"),
    AAA_SITUACION_C2: Decimal("66"),
}


class Agente(db.Model):
    __tablename__ = "agentes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    apellido = db.Column(db.String(80), nullable=False)
    tiene_titulo_corredor = db.Column(db.Boolean, default=False, nullable=False)
    matricula = db.Column(db.String(60))
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # Captador de desarrollo (Acta 001/2026): cobra un % en CADA operación
    # de los desarrollos que captó, aunque no trabaje esa venta puntual.
    es_captador_desarrollo = db.Column(db.Boolean, default=False, nullable=False)
    desarrollos_captados = db.Column(db.Text)  # nombres separados por coma

    lineas = db.relationship("LineaComision", back_populates="agente")

    @property
    def nombre_completo(self):
        return f"{self.apellido}, {self.nombre}".strip(", ")

    @property
    def retencion_sugerida(self):
        # Con título de corredor se sugiere 20%; por defecto 30%.
        return 20 if self.tiene_titulo_corredor else 30

    @property
    def lista_desarrollos_captados(self):
        if not self.desarrollos_captados:
            return []
        return [d.strip() for d in self.desarrollos_captados.split(",") if d.strip()]

    def capta(self, nombre_desarrollo):
        """True si este agente figura como captador del desarrollo dado (case-insensitive)."""
        if not nombre_desarrollo:
            return False
        objetivo = nombre_desarrollo.strip().lower()
        return any(d.lower() == objetivo for d in self.lista_desarrollos_captados)

    @staticmethod
    def buscar_captador(nombre_desarrollo):
        """Agente activo marcado como captador de ese desarrollo, si existe."""
        if not nombre_desarrollo:
            return None
        for ag in Agente.query.filter_by(es_captador_desarrollo=True, activo=True).all():
            if ag.capta(nombre_desarrollo):
                return ag
        return None


class Operacion(db.Model):
    __tablename__ = "operaciones"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    propiedad = db.Column(db.String(200), nullable=False)
    moneda = db.Column(db.String(3), nullable=False, default=MONEDA_USD)
    notas = db.Column(db.Text)

    # Compraventa
    monto_venta = db.Column(db.Numeric(18, 2))

    # Alquiler
    duracion_meses = db.Column(db.Integer)
    canon_mensual = db.Column(db.Numeric(18, 2))
    monto_total_contrato = db.Column(db.Numeric(18, 2))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lineas = db.relationship(
        "LineaComision",
        back_populates="operacion",
        cascade="all, delete-orphan",
        order_by="LineaComision.id",
        lazy="selectin",  # carga anticipada: evita N+1 al listar operaciones
    )

    # --- Totales derivados (solo cuentan las puntas que generan comisión) ---
    # Nota: la comisión de una línea puede repartirse entre el agente
    # principal y sus "figuras" (datero, captador de desarrollo, AAA — Acta
    # 001/2026); estos totales suman SIEMPRE ambas partes.
    @property
    def lineas_con_comision(self):
        return [l for l in self.lineas if l.genera_comision]

    # Alias retrocompatible (incluye también desarrollos).
    lineas_infinity = lineas_con_comision

    @property
    def comision_bruta_total(self):
        return sum((l.comision_bruta or Decimal("0")) for l in self.lineas_con_comision) or Decimal("0")

    @property
    def monto_inmobiliaria_total(self):
        total = Decimal("0")
        for l in self.lineas_con_comision:
            total += l.monto_inmobiliaria or Decimal("0")
            for f in l.figuras:
                total += f.monto_inmobiliaria or Decimal("0")
        return total

    @property
    def monto_agente_total(self):
        total = Decimal("0")
        for l in self.lineas_con_comision:
            total += l.monto_agente or Decimal("0")
            for f in l.figuras:
                total += f.monto_agente or Decimal("0")
        return total

    @property
    def agentes_intervinientes(self):
        nombres = []
        for l in self.lineas_con_comision:
            if l.agente and l.agente.nombre_completo not in nombres:
                nombres.append(l.agente.nombre_completo)
            for f in l.figuras:
                if f.agente and f.agente.nombre_completo not in nombres:
                    nombres.append(f.agente.nombre_completo)
        return nombres

    @property
    def genera_comision(self):
        return len(self.lineas_con_comision) > 0


class LineaComision(db.Model):
    __tablename__ = "lineas_comision"

    id = db.Column(db.Integer, primary_key=True)
    operacion_id = db.Column(db.Integer, db.ForeignKey("operaciones.id"), nullable=False)

    rol = db.Column(db.String(20), nullable=False)
    representacion = db.Column(db.String(20), nullable=False, default=REP_INFINITY)

    agente_id = db.Column(db.Integer, db.ForeignKey("agentes.id"))
    nombre_inmobiliaria = db.Column(db.String(120))
    nombre_desarrollo = db.Column(db.String(120))

    comision_tipo = db.Column(db.String(20), default=COMISION_PORCENTAJE)
    comision_porcentaje = db.Column(db.Numeric(7, 4))
    comision_monto_fijo = db.Column(db.Numeric(18, 2))
    comision_motivo_edicion = db.Column(db.Text)

    base_calculo = db.Column(db.Numeric(18, 2))
    retencion_porcentaje = db.Column(db.Integer, default=30)

    # Calculados (persistidos). NOTA: cuando la línea tiene figuras (datero,
    # captador de desarrollo, AAA), estos tres campos representan SOLO la
    # porción del agente principal (comision_bruta sigue siendo el bruto
    # TOTAL de la línea; monto_agente/monto_inmobiliaria son lo que queda
    # tras descontar a las figuras y aplicar la retención del principal).
    # El aporte de cada figura vive en `figuras` (cada una con su propio
    # bruto/inmobiliaria/agente).
    comision_bruta = db.Column(db.Numeric(18, 2), default=0)
    monto_inmobiliaria = db.Column(db.Numeric(18, 2), default=0)
    monto_agente = db.Column(db.Numeric(18, 2), default=0)

    operacion = db.relationship("Operacion", back_populates="lineas")
    agente = db.relationship("Agente", back_populates="lineas", lazy="selectin")
    figuras = db.relationship(
        "FiguraComision", back_populates="linea",
        cascade="all, delete-orphan", order_by="FiguraComision.id",
        lazy="selectin",  # carga anticipada: evita N+1 con las figuras
    )

    @property
    def etiqueta_rol(self):
        return ETIQUETA_ROL.get(self.rol, self.rol)

    @property
    def genera_comision(self):
        return self.representacion in REPRESENTACIONES_CON_COMISION

    @property
    def comision_bruta_figuras(self):
        """Suma de lo que se llevan las figuras (datero/captador/AAA) de esta línea."""
        return sum((f.comision_bruta or Decimal("0")) for f in self.figuras) or Decimal("0")

    @property
    def comision_bruta_principal(self):
        """Lo que queda de la comisión bruta para el agente principal, tras las figuras."""
        return (self.comision_bruta or Decimal("0")) - self.comision_bruta_figuras

    @property
    def monto_inmobiliaria_total(self):
        """Retención total de esta línea: la del agente principal + la de cada figura."""
        total = self.monto_inmobiliaria or Decimal("0")
        for f in self.figuras:
            total += f.monto_inmobiliaria or Decimal("0")
        return total

    @property
    def representante(self):
        if self.representacion == REP_INFINITY:
            return self.agente.nombre_completo if self.agente else "Infinity (sin agente)"
        if self.representacion == REP_DESARROLLO:
            desarrollo = self.nombre_desarrollo or "Desarrollo"
            agente = self.agente.nombre_completo if self.agente else "sin agente"
            return f"{desarrollo} · {agente}"
        if self.representacion == REP_OTRA_INMOBILIARIA:
            return self.nombre_inmobiliaria or "Otra inmobiliaria"
        return "Particular"


class FiguraComision(db.Model):
    """Figura adicional que cobra sobre una línea: datero, captador de
    desarrollo o Agente Asistente al Ausente (Acta de Asamblea 001/2026).

    Se descuenta un % de la comisión bruta de la línea ANTES de aplicar
    cualquier retención. Luego esa porción (igual que la del agente
    principal) deja SU PROPIA retención en la inmobiliaria — cada una según
    la retención que corresponda a ese agente en particular.
    """
    __tablename__ = "figuras_comision"

    id = db.Column(db.Integer, primary_key=True)
    linea_comision_id = db.Column(db.Integer, db.ForeignKey("lineas_comision.id"), nullable=False)

    tipo = db.Column(db.String(30), nullable=False)
    agente_id = db.Column(db.Integer, db.ForeignKey("agentes.id"), nullable=False)
    situacion_aaa = db.Column(db.String(5))  # solo para tipo == FIGURA_AAA
    tipo_figura_personalizada_id = db.Column(
        db.Integer, db.ForeignKey("tipos_figura_personalizada.id"))  # solo para tipo == FIGURA_PERSONALIZADA

    porcentaje = db.Column(db.Numeric(7, 4))            # % de la comisión bruta de la línea
    retencion_porcentaje = db.Column(db.Integer, default=30)  # retención propia de esta figura

    # Calculados (persistidos)
    comision_bruta = db.Column(db.Numeric(18, 2), default=0)
    monto_inmobiliaria = db.Column(db.Numeric(18, 2), default=0)
    monto_agente = db.Column(db.Numeric(18, 2), default=0)

    linea = db.relationship("LineaComision", back_populates="figuras")
    agente = db.relationship("Agente", lazy="selectin")
    tipo_figura_personalizada = db.relationship("TipoFiguraPersonalizada", lazy="selectin")

    @property
    def etiqueta_tipo(self):
        if self.tipo == FIGURA_PERSONALIZADA:
            if self.tipo_figura_personalizada:
                return self.tipo_figura_personalizada.nombre
            return ETIQUETA_FIGURA[FIGURA_PERSONALIZADA]
        return ETIQUETA_FIGURA.get(self.tipo, self.tipo)

    @property
    def etiqueta_situacion(self):
        return ETIQUETA_AAA_SITUACION.get(self.situacion_aaa, "")


class TipoFiguraPersonalizada(db.Model):
    """Catálogo de figuras adicionales creadas a mano desde Configuración,
    para casos excepcionales no previstos por el Acta 001/2026 (datero,
    captador de desarrollo, AAA). Se comportan como el datero: un % fijo
    (editable al usarlas) de la comisión bruta de la línea, con su propia
    retención. A diferencia de esas tres, están disponibles en cualquier
    tipo de operación (compraventa y alquiler)."""
    __tablename__ = "tipos_figura_personalizada"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    porcentaje_sugerido = db.Column(db.Numeric(7, 4), nullable=False, default=10.0)
    activo = db.Column(db.Boolean, default=True, nullable=False)


class Configuracion(db.Model):
    """Fila única con los parámetros editables del sistema."""
    __tablename__ = "configuracion"

    id = db.Column(db.Integer, primary_key=True)
    comision_default_compraventa = db.Column(db.Numeric(7, 4), default=3.0)
    comision_default_alquiler = db.Column(db.Numeric(7, 4), default=4.5)
    opciones_retencion = db.Column(db.String(50), default="30,20,10")
    moneda_default_alquiler = db.Column(db.String(3), default=MONEDA_ARS)
    datero_pct = db.Column(db.Numeric(7, 4), default=20.0)
    captador_desarrollo_pct = db.Column(db.Numeric(7, 4), default=33.0)

    @property
    def lista_retencion(self):
        return [int(x) for x in str(self.opciones_retencion).split(",") if x.strip()]

    @staticmethod
    def obtener():
        cfg = db.session.get(Configuracion, 1)
        if cfg is None:
            cfg = Configuracion(id=1)
            db.session.add(cfg)
            db.session.commit()
        return cfg
