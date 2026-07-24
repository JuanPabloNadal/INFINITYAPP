"""Parseo y validación del formulario de operaciones.

Convierte los datos del formulario en una Operacion con sus LineaComision,
recalculando SIEMPRE las comisiones en el servidor (no se confía en el cliente).
"""
from datetime import date
from decimal import Decimal

from ..models import (
    Operacion, LineaComision, Configuracion, FiguraComision, TipoFiguraPersonalizada,
    TIPO_COMPRAVENTA, TIPO_ALQUILER, TIPOS_OPERACION, ROLES_POR_TIPO,
    REP_INFINITY, REP_DESARROLLO, REP_OTRA_INMOBILIARIA, REP_PARTICULAR,
    REPRESENTACIONES_CON_COMISION,
    COMISION_PORCENTAJE, COMISION_MONTO_FIJO, MONEDAS, MONEDA_USD,
    FIGURA_DATERO, FIGURA_CAPTADOR_DESARROLLO, FIGURA_AAA, FIGURA_PERSONALIZADA,
    AAA_SITUACIONES,
)
from .calculo import aplicar_calculo, a_decimal


def _num(form, campo):
    valor = (form.get(campo) or "").strip()
    if valor == "":
        return None
    return a_decimal(valor)


def parsear_operacion(form, operacion=None):
    """Devuelve (operacion, errores, advertencias).

    Si se pasa `operacion`, se actualiza (modo edición); si no, se crea una nueva.
    En caso de error de validación bloqueante, `errores` no estará vacío.
    """
    cfg = Configuracion.obtener()
    errores = []
    advertencias = []

    if operacion is None:
        operacion = Operacion()

    tipo = (form.get("tipo") or "").strip().upper()
    if tipo not in TIPOS_OPERACION:
        errores.append("Tipo de operación inválido.")
        return operacion, errores, advertencias
    operacion.tipo = tipo

    # Fecha
    fecha_txt = (form.get("fecha") or "").strip()
    try:
        operacion.fecha = date.fromisoformat(fecha_txt)
    except ValueError:
        errores.append("La fecha es obligatoria y debe ser válida.")

    operacion.propiedad = (form.get("propiedad") or "").strip()
    if not operacion.propiedad:
        errores.append("La propiedad / identificación es obligatoria.")

    operacion.notas = (form.get("notas") or "").strip() or None

    # Moneda y montos según tipo
    if tipo == TIPO_COMPRAVENTA:
        operacion.moneda = MONEDA_USD  # compraventa siempre USD
        operacion.monto_venta = _num(form, "monto_venta")
        operacion.duracion_meses = None
        operacion.canon_mensual = None
        operacion.monto_total_contrato = None
        if not operacion.monto_venta or operacion.monto_venta <= 0:
            errores.append("El monto de venta debe ser mayor a 0.")
        base_por_defecto = operacion.monto_venta or Decimal("0")
        comision_default = cfg.comision_default_compraventa
    else:  # ALQUILER
        moneda = (form.get("moneda") or cfg.moneda_default_alquiler).strip().upper()
        operacion.moneda = moneda if moneda in MONEDAS else cfg.moneda_default_alquiler
        operacion.monto_venta = None
        duracion = form.get("duracion_meses")
        operacion.duracion_meses = int(duracion) if (duracion or "").strip().isdigit() else None
        operacion.canon_mensual = _num(form, "canon_mensual")
        total = _num(form, "monto_total_contrato")
        if total is None and operacion.canon_mensual and operacion.duracion_meses:
            total = operacion.canon_mensual * operacion.duracion_meses
        operacion.monto_total_contrato = total
        if not operacion.monto_total_contrato or operacion.monto_total_contrato <= 0:
            errores.append("El monto total del contrato debe ser mayor a 0.")
        base_por_defecto = operacion.monto_total_contrato or Decimal("0")
        comision_default = cfg.comision_default_alquiler

    # --- Puntas / líneas de comisión ---
    nuevas_lineas = []
    roles = ROLES_POR_TIPO[tipo]
    for i, rol in enumerate(roles):
        rep = (form.get(f"punta{i}_representacion") or REP_PARTICULAR).strip()
        linea = LineaComision(rol=rol, representacion=rep)

        if rep in REPRESENTACIONES_CON_COMISION:
            agente_id = (form.get(f"punta{i}_agenteId") or "").strip()
            if not agente_id.isdigit():
                errores.append(f"{_rol_label(rol)}: seleccioná el agente de Infinity que cobra.")
            else:
                linea.agente_id = int(agente_id)

            if rep == REP_DESARROLLO:
                linea.nombre_desarrollo = (form.get(f"punta{i}_nombreDesarrollo") or "").strip() or None
                if not linea.nombre_desarrollo:
                    errores.append(f"{_rol_label(rol)}: indicá el nombre del desarrollo.")

            linea.comision_tipo = (form.get(f"punta{i}_comisionTipo") or COMISION_PORCENTAJE).strip()
            linea.comision_porcentaje = _num(form, f"punta{i}_comisionPorcentaje")
            linea.comision_monto_fijo = _num(form, f"punta{i}_comisionMontoFijo")

            base = _num(form, f"punta{i}_baseCalculo")
            linea.base_calculo = base if base is not None else base_por_defecto

            retencion = (form.get(f"punta{i}_retencionPorcentaje") or "30").strip()
            linea.retencion_porcentaje = int(retencion) if retencion.isdigit() else 30

            motivo = (form.get(f"punta{i}_comisionMotivoEdicion") or "").strip()
            linea.comision_motivo_edicion = motivo or None

            # Validaciones de comisión
            if linea.comision_tipo == COMISION_PORCENTAJE:
                if linea.comision_porcentaje is None or linea.comision_porcentaje <= 0:
                    errores.append(f"{_rol_label(rol)}: el porcentaje de comisión debe ser mayor a 0.")
                elif linea.comision_porcentaje != a_decimal(comision_default) and not motivo:
                    errores.append(
                        f"{_rol_label(rol)}: el porcentaje difiere del {_pct(comision_default)} "
                        f"por defecto; cargá el motivo."
                    )
            else:  # MONTO_FIJO
                if linea.comision_monto_fijo is None or linea.comision_monto_fijo <= 0:
                    errores.append(f"{_rol_label(rol)}: el monto fijo de comisión debe ser mayor a 0.")

            figuras, errores_figuras = _parsear_figuras(form, i, tipo, rep, linea.agente_id)
            errores.extend(errores_figuras)
            linea.figuras = figuras

            aplicar_calculo(linea)

        elif rep == REP_OTRA_INMOBILIARIA:
            linea.nombre_inmobiliaria = (form.get(f"punta{i}_nombreInmobiliaria") or "").strip() or None
            _en_cero(linea)
        else:  # PARTICULAR
            _en_cero(linea)

        nuevas_lineas.append(linea)

    # Venta de desarrollo: es una sola punta (el comprador no paga). Se descarta
    # la otra punta para que la operación quede con una única línea de comisión.
    if any(l.representacion == REP_DESARROLLO for l in nuevas_lineas):
        nuevas_lineas = [l for l in nuevas_lineas if l.genera_comision]

    # Advertencia si ninguna punta genera comisión
    if not any(l.genera_comision for l in nuevas_lineas):
        advertencias.append(
            "Ninguna punta genera comisión para Infinity: esta operación no genera ingresos."
        )

    if not errores:
        operacion.lineas = nuevas_lineas

    return operacion, errores, advertencias


def _parsear_figuras(form, i, tipo, rep, agente_principal_id):
    """Parsea las figuras adicionales de una punta: datero / captador de
    desarrollo / AAA (Acta 001/2026, solo COMPRAVENTA) y las figuras
    PERSONALIZADAS creadas desde Configuración (cualquier tipo). El captador
    de desarrollo solo tiene sentido si la punta es de tipo DESARROLLO.
    Ninguna figura puede ser el mismo agente que el agente principal.
    """
    figuras = []
    errores = []
    cfg = Configuracion.obtener()
    rol_actual = ROLES_POR_TIPO[tipo][i]

    def _agente_valido(campo_id, etiqueta):
        agente_id = (form.get(campo_id) or "").strip()
        if not agente_id.isdigit():
            errores.append(f"{_rol_label(rol_actual)}: seleccioná el agente {etiqueta}.")
            return None
        agente_id = int(agente_id)
        if agente_principal_id is not None and agente_id == agente_principal_id:
            errores.append(f"{_rol_label(rol_actual)}: el {etiqueta} debe ser un agente distinto al principal.")
            return None
        return agente_id

    if tipo == TIPO_COMPRAVENTA:
        # Datero — agente distinto al principal.
        if form.get(f"punta{i}_datero") == "on":
            agente_id = _agente_valido(f"punta{i}_dateroAgenteId", "datero")
            if agente_id is not None:
                retencion = (form.get(f"punta{i}_dateroRetencion") or "30").strip()
                figuras.append(FiguraComision(
                    tipo=FIGURA_DATERO, agente_id=agente_id,
                    porcentaje=cfg.datero_pct,
                    retencion_porcentaje=int(retencion) if retencion.isdigit() else 30,
                ))

        # Captador de desarrollo — solo si la punta es de tipo DESARROLLO.
        if rep == REP_DESARROLLO and form.get(f"punta{i}_captador") == "on":
            agente_id = _agente_valido(f"punta{i}_captadorAgenteId", "captador de desarrollo")
            if agente_id is not None:
                retencion = (form.get(f"punta{i}_captadorRetencion") or "30").strip()
                figuras.append(FiguraComision(
                    tipo=FIGURA_CAPTADOR_DESARROLLO, agente_id=agente_id,
                    porcentaje=cfg.captador_desarrollo_pct,
                    retencion_porcentaje=int(retencion) if retencion.isdigit() else 30,
                ))

        # Agente Asistente al Ausente (AAA).
        if form.get(f"punta{i}_aaa") == "on":
            agente_id = _agente_valido(f"punta{i}_aaaAgenteId", "asistente al ausente")
            situacion = (form.get(f"punta{i}_aaaSituacion") or "").strip().upper()
            if situacion not in AAA_SITUACIONES:
                errores.append(f"{_rol_label(rol_actual)}: elegí la situación del AAA.")
            elif agente_id is not None:
                retencion = (form.get(f"punta{i}_aaaRetencion") or "30").strip()
                figuras.append(FiguraComision(
                    tipo=FIGURA_AAA, agente_id=agente_id, situacion_aaa=situacion,
                    retencion_porcentaje=int(retencion) if retencion.isdigit() else 30,
                ))

    # Figuras personalizadas (Configuración) — disponibles en cualquier tipo
    # de operación, con % editable en cada operación (parte del sugerido).
    # Se incluyen también las inactivas: si una operación ya las usaba, deben
    # poder seguir guardándose al reeditar esa operación (la desactivación
    # solo impide *agregarlas* a operaciones nuevas, no afecta lo ya cargado).
    for tp in TipoFiguraPersonalizada.query.all():
        campo_base = f"punta{i}_personalizada{tp.id}"
        if form.get(campo_base) != "on":
            continue
        agente_id = _agente_valido(f"{campo_base}AgenteId", tp.nombre)
        pct = _num(form, f"{campo_base}Pct")
        if pct is None or pct <= 0:
            errores.append(f"{_rol_label(rol_actual)}: el % de '{tp.nombre}' debe ser mayor a 0.")
            continue
        if agente_id is not None:
            retencion = (form.get(f"{campo_base}Retencion") or "30").strip()
            figuras.append(FiguraComision(
                tipo=FIGURA_PERSONALIZADA, agente_id=agente_id,
                tipo_figura_personalizada_id=tp.id, porcentaje=pct,
                retencion_porcentaje=int(retencion) if retencion.isdigit() else 30,
            ))

    return figuras, errores


def _en_cero(linea):
    linea.agente_id = None
    linea.comision_tipo = None
    linea.comision_porcentaje = None
    linea.comision_monto_fijo = None
    linea.base_calculo = None
    linea.comision_bruta = Decimal("0")
    linea.monto_inmobiliaria = Decimal("0")
    linea.monto_agente = Decimal("0")


def _rol_label(rol):
    from ..models import ETIQUETA_ROL
    return ETIQUETA_ROL.get(rol, rol)


def _pct(valor):
    from ..utils.formato import formato_porcentaje
    return formato_porcentaje(valor)
