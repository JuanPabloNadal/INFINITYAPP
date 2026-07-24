"""Agregaciones para reportes y dashboard.

Regla clave: NUNCA se suman monedas distintas. Todo balance se agrupa por moneda.
"""
from collections import defaultdict
from decimal import Decimal

from ..models import REP_INFINITY, MONEDA_USD


def _cero():
    return Decimal("0")


def _partes(linea):
    """Cada 'parte' que reparte la comisión de una línea: el agente principal
    y cada figura adicional (datero / captador de desarrollo / AAA — Acta
    001/2026). Todas comparten la misma forma (agente, monto_agente,
    monto_inmobiliaria), por eso se puede iterar de manera uniforme."""
    yield linea
    for f in linea.figuras:
        yield f


def balance_por_moneda(operaciones):
    """Devuelve un dict {moneda: {...}} con totales y reparto por agente.

    Cada moneda incluye:
      - comision_bruta, monto_inmobiliaria, monto_agente_total
      - cantidad_operaciones
      - por_agente: lista [(nombre, monto)] ordenada desc (incluye a las
        figuras — datero/captador/AAA — como agentes más en el reparto)
    """
    monedas = {}

    for op in operaciones:
        m = op.moneda
        bucket = monedas.setdefault(m, {
            "comision_bruta": _cero(),
            "monto_inmobiliaria": _cero(),
            "monto_agente_total": _cero(),
            "cantidad_operaciones": 0,
            "_agentes": {},
        })
        bucket["cantidad_operaciones"] += 1

        for linea in op.lineas:
            if not linea.genera_comision:
                continue
            bucket["comision_bruta"] += linea.comision_bruta or _cero()

            for parte in _partes(linea):
                inmo = parte.monto_inmobiliaria or _cero()
                monto_agente = parte.monto_agente or _cero()
                bucket["monto_inmobiliaria"] += inmo
                bucket["monto_agente_total"] += monto_agente

                nombre = parte.agente.nombre_completo if parte.agente else "Sin agente"
                bucket["_agentes"][nombre] = bucket["_agentes"].get(nombre, _cero()) + monto_agente

    # Ordenar agentes por monto desc y limpiar clave interna.
    for bucket in monedas.values():
        bucket["por_agente"] = sorted(
            bucket.pop("_agentes").items(), key=lambda kv: kv[1], reverse=True
        )

    return monedas


def ranking_agentes(operaciones, moneda):
    """Ranking [(nombre, monto_agente)] para una moneda específica."""
    balance = balance_por_moneda(operaciones)
    return balance.get(moneda, {}).get("por_agente", [])


def desempeno_en_pesos(operaciones, tipo_cambio):
    """Ranking de ingresos TOTALES en pesos (agentes + inmobiliaria).

    Convierte las comisiones en US$ a ARS con `tipo_cambio` (ARS por 1 US$) y
    las suma con las comisiones que ya están en ARS. Devuelve (filas, resumen):
      - filas: lista de dicts ordenada de mayor a menor ingreso en pesos, donde
        cada fila es un agente (incluye datero/captador/AAA) o la inmobiliaria.
      - resumen: totales globales en pesos.
    """
    tc = Decimal(str(tipo_cambio))

    agentes = defaultdict(lambda: {"ars": _cero(), "puntas": 0,
                                   "de_usd": _cero(), "de_ars": _cero()})
    inmo = {"ars": _cero(), "puntas": 0, "de_usd": _cero(), "de_ars": _cero()}
    bruta_total = _cero()

    for op in operaciones:
        factor = tc if op.moneda == MONEDA_USD else Decimal("1")
        es_usd = op.moneda == MONEDA_USD
        for linea in op.lineas:
            if not linea.genera_comision:
                continue
            bruta_total += (linea.comision_bruta or _cero()) * factor

            for parte in _partes(linea):
                ma = parte.monto_agente or _cero()
                mi = parte.monto_inmobiliaria or _cero()

                nombre = parte.agente.nombre_completo if parte.agente else "Sin agente"
                a = agentes[nombre]
                a["ars"] += ma * factor
                a["puntas"] += 1
                a["de_usd" if es_usd else "de_ars"] += ma * factor

                inmo["ars"] += mi * factor
                inmo["puntas"] += 1
                inmo["de_usd" if es_usd else "de_ars"] += mi * factor

    filas = [{
        "nombre": nombre, "tipo": "agente", "ars": d["ars"], "puntas": d["puntas"],
        "de_usd": d["de_usd"], "de_ars": d["de_ars"],
    } for nombre, d in agentes.items()]
    filas.append({
        "nombre": "Infinity Inmobiliaria", "tipo": "inmobiliaria", "ars": inmo["ars"],
        "puntas": inmo["puntas"], "de_usd": inmo["de_usd"], "de_ars": inmo["de_ars"],
    })

    filas.sort(key=lambda f: f["ars"], reverse=True)
    maximo = filas[0]["ars"] if filas else _cero()
    for f in filas:
        f["pct"] = float(f["ars"] / maximo * 100) if maximo else 0.0

    resumen = {
        "tipo_cambio": tc,
        "bruta": bruta_total,
        "inmobiliaria": inmo["ars"],
        "agentes": sum((f["ars"] for f in filas if f["tipo"] == "agente"), _cero()),
        "maximo": maximo,
    }
    return filas, resumen
