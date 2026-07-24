"""Núcleo de cálculo de comisiones (autoridad del sistema).

Toda comisión se calcula en el servidor con Decimal para resultados exactos.

    comisionBruta     = base * (porcentaje / 100)     # si es PORCENTAJE
                        ó  montoFijo                    # si es MONTO_FIJO
    montoInmobiliaria = comisionBruta * (retencion / 100)
    montoAgente       = comisionBruta - montoInmobiliaria

Figuras adicionales (Acta de Asamblea 001/2026 — datero, captador de
desarrollo, Agente Asistente al Ausente): cada una toma un % de la
comisión bruta TOTAL de la línea, DESCONTADO ANTES de la retención. Lo que
resta queda para el agente principal. Tanto el agente principal como CADA
figura dejan, cada uno, su propia retención en la inmobiliaria — no hay una
retención única sobre el total. Ver `aplicar_calculo`.
"""
from decimal import Decimal, ROUND_HALF_UP

from ..models import (
    COMISION_MONTO_FIJO, FIGURA_AAA, AAA_SITUACION_A, AAA_PORCENTAJE_SITUACION,
)

DOS_DECIMALES = Decimal("0.01")

# Situación A del AAA: US$100 fijo, o 10% de la comisión de la punta si esa
# comisión es menor a US$1.000 (lo que sea menor de los dos). Equivale a
# min(US$100, comisión × 10%) — sin discontinuidad en el umbral de US$1.000.
AAA_SITUACION_A_TOPE = Decimal("100")
AAA_SITUACION_A_PCT = Decimal("10")


def a_decimal(valor, defecto="0"):
    """Convierte de forma segura a Decimal (acepta None, str con coma o punto)."""
    if valor is None or valor == "":
        valor = defecto
    if isinstance(valor, str):
        valor = valor.strip().replace(".", "").replace(",", ".") if _parece_es_ar(valor) else valor.strip()
    try:
        return Decimal(str(valor))
    except Exception:
        return Decimal(defecto)


def _parece_es_ar(texto):
    """Detecta si el string viene formateado es-AR (1.234.567,89)."""
    return "," in texto and texto.count(",") == 1


def redondear(valor):
    return Decimal(valor).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)


def calcular_solo_bruta(comision_tipo, comision_porcentaje, comision_monto_fijo, base_calculo):
    """Comisión bruta de una línea, sin aplicar ninguna retención."""
    if comision_tipo == COMISION_MONTO_FIJO:
        bruta = a_decimal(comision_monto_fijo)
    else:
        base = a_decimal(base_calculo)
        porcentaje = a_decimal(comision_porcentaje)
        bruta = base * (porcentaje / Decimal("100"))
    return redondear(bruta)


def calcular_comision(comision_tipo, comision_porcentaje, comision_monto_fijo,
                      base_calculo, retencion_porcentaje):
    """Devuelve (comision_bruta, monto_inmobiliaria, monto_agente) como Decimal.

    Es la única fuente de verdad del cálculo de una línea; el resto del
    sistema la usa. (No contempla figuras — ver `aplicar_calculo`.)
    """
    bruta = calcular_solo_bruta(comision_tipo, comision_porcentaje, comision_monto_fijo, base_calculo)
    retencion = a_decimal(retencion_porcentaje)
    inmobiliaria = redondear(bruta * (retencion / Decimal("100")))
    agente = redondear(bruta - inmobiliaria)
    return bruta, inmobiliaria, agente


def _dividir_por_retencion(monto_bruto, retencion_porcentaje):
    """Reparte un monto bruto entre inmobiliaria y agente según su retención."""
    retencion = a_decimal(retencion_porcentaje)
    inmobiliaria = redondear(monto_bruto * (retencion / Decimal("100")))
    agente = redondear(monto_bruto - inmobiliaria)
    return inmobiliaria, agente


def calcular_monto_figura(tipo, comision_bruta_linea, porcentaje=None, situacion_aaa=None):
    """% efectivo y monto bruto que le corresponde a una figura (datero,
    captador de desarrollo o AAA) sobre la comisión bruta TOTAL de la línea.

    Para AAA, el % sale de la situación elegida (con el caso especial de la
    situación A: tope US$100 o 10%, lo que sea menor). Para datero/captador
    de desarrollo, el % se recibe ya resuelto (viene de Configuración).
    """
    comision_bruta_linea = a_decimal(comision_bruta_linea)

    if tipo == FIGURA_AAA and situacion_aaa == AAA_SITUACION_A:
        monto = redondear(min(
            AAA_SITUACION_A_TOPE,
            comision_bruta_linea * (AAA_SITUACION_A_PCT / Decimal("100")),
        ))
        pct_efectivo = redondear((monto / comision_bruta_linea) * 100) if comision_bruta_linea else Decimal("0")
        return pct_efectivo, monto

    if tipo == FIGURA_AAA:
        pct = AAA_PORCENTAJE_SITUACION.get(situacion_aaa, Decimal("0"))
    else:
        pct = a_decimal(porcentaje)

    monto = redondear(comision_bruta_linea * (pct / Decimal("100")))
    return pct, monto


def aplicar_calculo_figura(figura, comision_bruta_linea):
    """Recalcula y asigna los campos derivados de una FiguraComision."""
    pct, bruta = calcular_monto_figura(
        figura.tipo, comision_bruta_linea,
        porcentaje=figura.porcentaje, situacion_aaa=figura.situacion_aaa,
    )
    inmo, agente = _dividir_por_retencion(bruta, figura.retencion_porcentaje)
    figura.porcentaje = pct
    figura.comision_bruta = bruta
    figura.monto_inmobiliaria = inmo
    figura.monto_agente = agente
    return figura


def aplicar_calculo(linea):
    """Recalcula los campos derivados de una LineaComision, incluidas sus figuras.

    Orden (Acta 001/2026):
      1) comisión bruta TOTAL de la línea (base × % o monto fijo).
      2) cada figura (datero/captador de desarrollo/AAA) toma su % de esa
         bruta total, y dejar su propia retención en la inmobiliaria.
      3) lo que resta (bruta total − figuras) va al agente principal, que
         deja SU propia retención en la inmobiliaria.
    """
    bruta_total = calcular_solo_bruta(
        linea.comision_tipo, linea.comision_porcentaje,
        linea.comision_monto_fijo, linea.base_calculo,
    )
    linea.comision_bruta = bruta_total

    for figura in linea.figuras:
        aplicar_calculo_figura(figura, bruta_total)

    bruta_principal = bruta_total - linea.comision_bruta_figuras
    inmo, agente = _dividir_por_retencion(bruta_principal, linea.retencion_porcentaje)
    linea.monto_inmobiliaria = inmo
    linea.monto_agente = agente
    return linea
