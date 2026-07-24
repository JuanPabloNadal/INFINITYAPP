"""Panel inicial: resumen del mes en curso + evolución del año.

Rediseño (handoff Claude Design, 2026-07): tira de KPIs, hero de retención con
sparkline, barras HTML/CSS por mes, donut compraventa/alquiler, ranking de
agentes y tabla de últimas operaciones. Sin cambios de modelo ni de cálculo:
todo lo que se muestra se deriva de `balance_por_moneda` y las operaciones ya
existentes.
"""
import calendar
from datetime import date
from decimal import Decimal

from flask import Blueprint, render_template, request

from ..models import Operacion, Agente, TIPO_COMPRAVENTA, MONEDA_USD, MONEDA_ARS
from ..services.reportes import balance_por_moneda
from ..utils.formato import nombre_mes
from ..utils.graficos import MESES_ABREV

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    hoy = date.today()

    # Mes/año consultados (navegación ‹ › en el encabezado). Si vienen mal
    # formados o fuera de rango, se cae siempre al mes en curso.
    try:
        anio_sel = int(request.args.get("anio", hoy.year))
        mes_sel = int(request.args.get("mes", hoy.month))
        if not (1 <= mes_sel <= 12):
            raise ValueError
        date(anio_sel, mes_sel, 1)  # valida el año (ValueError si es absurdo)
    except (TypeError, ValueError):
        anio_sel, mes_sel = hoy.year, hoy.month

    es_mes_actual = (anio_sel, mes_sel) == (hoy.year, hoy.month)
    anio_ant_nav, mes_ant_nav = _mes_anterior(anio_sel, mes_sel)
    anio_sig_nav, mes_sig_nav = _mes_siguiente(anio_sel, mes_sel)
    nav = {"mes_ant": mes_ant_nav, "anio_ant": anio_ant_nav,
           "mes_sig": mes_sig_nav, "anio_sig": anio_sig_nav}

    primero = date(anio_sel, mes_sel, 1)
    ultimo = date(anio_sel, mes_sel, calendar.monthrange(anio_sel, mes_sel)[1])

    operaciones_mes = (
        Operacion.query
        .filter(Operacion.fecha >= primero, Operacion.fecha <= ultimo)
        .order_by(Operacion.fecha.desc(), Operacion.id.desc())
        .all()
    )
    balance = balance_por_moneda(operaciones_mes)
    usd = balance.get(MONEDA_USD)
    ars = balance.get(MONEDA_ARS)

    # Mes anterior al consultado (para las variaciones "▲ % vs. mes pasado").
    anio_ant, mes_ant = anio_ant_nav, mes_ant_nav
    primero_ant = date(anio_ant, mes_ant, 1)
    ultimo_ant = date(anio_ant, mes_ant, calendar.monthrange(anio_ant, mes_ant)[1])
    operaciones_mes_anterior = (
        Operacion.query
        .filter(Operacion.fecha >= primero_ant, Operacion.fecha <= ultimo_ant)
        .all()
    )
    balance_anterior = balance_por_moneda(operaciones_mes_anterior)

    var_operaciones = _variacion_pct(len(operaciones_mes), len(operaciones_mes_anterior))
    if var_operaciones is not None:
        var_operaciones = round(var_operaciones)

    # Badge "▲ N% MoM" del hero: retención de la moneda con más actividad este
    # mes (si no hay dato previo comparable en ninguna moneda, se omite).
    mom_badge = None
    for moneda in (MONEDA_USD, MONEDA_ARS):
        actual = balance.get(moneda, {}).get("monto_inmobiliaria")
        previo = balance_anterior.get(moneda, {}).get("monto_inmobiliaria")
        if actual is not None and previo:
            pct = _variacion_pct(actual, previo)
            if pct is not None:
                mom_badge = {"pct": round(pct), "moneda": moneda}
                break

    # % de retención efectivo (USD) para la nota de la KPI destacada.
    retencion_pct_usd = None
    if usd and usd["comision_bruta"]:
        retencion_pct_usd = round(float(usd["monto_inmobiliaria"]) / float(usd["comision_bruta"]) * 100)

    # Compraventa vs. alquiler este mes (donut).
    cv_total_mes = sum(1 for op in operaciones_mes if op.tipo == TIPO_COMPRAVENTA)
    alq_total_mes = len(operaciones_mes) - cv_total_mes
    total_mes = cv_total_mes + alq_total_mes
    cv_pct = round(cv_total_mes / total_mes * 100) if total_mes else 0
    alq_pct = round(alq_total_mes / total_mes * 100) if total_mes else 0
    cv_deg = round(cv_total_mes / total_mes * 360, 1) if total_mes else 0

    # Ranking de agentes del mes (reparto en US$, top 5).
    por_agente_usd = (usd or {}).get("por_agente", [])[:5]
    max_monto = por_agente_usd[0][1] if por_agente_usd else Decimal("0")
    ranking_mes = [
        {"nombre": nombre, "monto": monto,
         "pct": float(monto / max_monto * 100) if max_monto else 0.0}
        for nombre, monto in por_agente_usd
    ]

    ultimas = Operacion.query.order_by(Operacion.id.desc()).limit(5).all()
    total_operaciones = Operacion.query.count()
    total_agentes = Agente.query.filter_by(activo=True).count()

    # La evolución anual siempre llega como mínimo hasta "hoy" cuando se está
    # viendo el año en curso (aunque se navegue a un mes anterior de ese año);
    # si se navega a otro año, se ancla al mes consultado.
    mes_referencia = mes_sel
    if anio_sel == hoy.year:
        mes_referencia = max(mes_referencia, hoy.month)
    evolucion = _evolucion_anual(anio_sel, mes_referencia)

    return render_template(
        "dashboard.html",
        periodo=f"{nombre_mes(mes_sel).capitalize()} {anio_sel}",
        anio=anio_sel,
        mes_actual=mes_sel,
        mes_anterior=mes_ant,
        es_mes_actual=es_mes_actual,
        nav=nav,
        balance=balance,
        usd=usd,
        ars=ars,
        operaciones_mes=operaciones_mes,
        var_operaciones=var_operaciones,
        mom_badge=mom_badge,
        retencion_pct_usd=retencion_pct_usd,
        cv_total_mes=cv_total_mes,
        alq_total_mes=alq_total_mes,
        cv_pct=cv_pct,
        alq_pct=alq_pct,
        cv_deg=cv_deg,
        ranking_mes=ranking_mes,
        ultimas=ultimas,
        total_operaciones=total_operaciones,
        total_agentes=total_agentes,
        **evolucion,
    )


def _mes_anterior(anio, mes):
    return (anio - 1, 12) if mes == 1 else (anio, mes - 1)


def _mes_siguiente(anio, mes):
    return (anio + 1, 1) if mes == 12 else (anio, mes + 1)


def _variacion_pct(actual, previo):
    """% de variación entre dos valores; None si no hay base de comparación."""
    previo = float(previo or 0)
    if not previo:
        return None
    return (float(actual) - previo) / previo * 100


def _spark_path(vals, w=300, h=78, pad=6):
    """Sparkline SVG (área + polyline) normalizada min-max, sin dependencias."""
    if not vals:
        return {"area": "", "line": ""}
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    n = len(vals)
    pts = []
    for i, v in enumerate(vals):
        x = pad + (i * (w - pad * 2) / (n - 1) if n > 1 else 0)
        y = h - pad - ((v - lo) / rng) * (h - pad * 2)
        pts.append((x, y))
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = ("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            + f" L{w - pad:.1f},{h} L{pad:.1f},{h} Z")
    return {"area": area, "line": line}


def _evolucion_anual(anio, mes_actual):
    """Series del año (barras por mes + sparkline de retención US$)."""
    ops = (
        Operacion.query
        .filter(Operacion.fecha >= date(anio, 1, 1), Operacion.fecha <= date(anio, 12, 31))
        .all()
    )

    ultimo_mes = mes_actual
    for op in ops:
        ultimo_mes = max(ultimo_mes, op.fecha.month)

    labels = [MESES_ABREV[m] for m in range(1, ultimo_mes + 1)]
    cv = [0] * ultimo_mes
    alq = [0] * ultimo_mes
    inmo_usd = [0.0] * ultimo_mes

    for op in ops:
        idx = op.fecha.month - 1
        if idx >= ultimo_mes:
            continue
        if op.tipo == TIPO_COMPRAVENTA:
            cv[idx] += 1
        else:
            alq[idx] += 1
        if op.moneda == MONEDA_USD:
            for linea in op.lineas:
                if linea.genera_comision:
                    inmo_usd[idx] += float(linea.monto_inmobiliaria or 0)

    max_total = max((cv[i] + alq[i] for i in range(ultimo_mes)), default=0) or 1
    escala = 132 / max_total
    bars = [
        {"mes": labels[i], "h_cv": round(cv[i] * escala, 1), "h_alq": round(alq[i] * escala, 1)}
        for i in range(ultimo_mes)
    ]

    return {
        "hay_graficos": bool(ops),
        "bars": bars,
        "spark_usd": _spark_path(inmo_usd),
        "spark_labels": labels,
        "total_cv_anio": sum(cv),
        "total_alq_anio": sum(alq),
    }
