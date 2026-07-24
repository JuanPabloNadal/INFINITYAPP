"""Desempeño: ranking de ingresos en pesos (agentes + inmobiliaria).

Convierte las comisiones en US$ a ARS con un tipo de cambio editable y suma
todo en una sola moneda para poder rankear de mayores a menores ingresos.
"""
from datetime import date
from decimal import Decimal

from flask import Blueprint, render_template, request, send_file

from ..extensions import db
from ..models import Operacion
from ..services.reportes import desempeno_en_pesos
from ..services.exportar import exportar_desempeno_pdf

bp = Blueprint("desempeno", __name__, url_prefix="/desempeno")

TC_DEFAULT = Decimal("1450")


def _tipo_cambio(args):
    raw = (args.get("tc") or "").strip().replace("$", "").replace(" ", "")
    if "," in raw:                       # formato es-AR: 1.450,50
        raw = raw.replace(".", "").replace(",", ".")
    try:
        v = Decimal(raw)
        return v if v > 0 else TC_DEFAULT
    except Exception:
        return TC_DEFAULT


def _calcular(args):
    """Filtra operaciones según los parámetros y devuelve todo lo necesario."""
    tc = _tipo_cambio(args)
    anios = sorted({a[0].year for a in db.session.query(Operacion.fecha).all()}, reverse=True)
    periodo_sel = (args.get("anio") or "todo").strip()

    query = Operacion.query
    etiqueta_periodo = "Todo el historial"
    if periodo_sel != "todo" and periodo_sel.isdigit():
        y = int(periodo_sel)
        query = query.filter(Operacion.fecha >= date(y, 1, 1),
                             Operacion.fecha <= date(y, 12, 31))
        etiqueta_periodo = f"Año {y}"

    operaciones = query.all()
    filas, resumen = desempeno_en_pesos(operaciones, tc)
    return {
        "tc": tc, "anios": anios, "periodo_sel": periodo_sel,
        "etiqueta_periodo": etiqueta_periodo, "operaciones": operaciones,
        "filas": filas, "resumen": resumen,
    }


@bp.route("/")
def index():
    d = _calcular(request.args)
    return render_template(
        "desempeno.html",
        filas=d["filas"], resumen=d["resumen"], tc=d["tc"],
        anios=d["anios"], periodo_sel=d["periodo_sel"],
        etiqueta_periodo=d["etiqueta_periodo"], total_ops=len(d["operaciones"]),
    )


@bp.route("/pdf")
def pdf():
    d = _calcular(request.args)
    archivo = exportar_desempeno_pdf(
        d["filas"], d["resumen"], d["etiqueta_periodo"], len(d["operaciones"]))
    etiqueta = d["etiqueta_periodo"].lower().replace(" ", "_").replace("ñ", "n")
    nombre = f"infinity_desempeno_{etiqueta}.pdf"
    return send_file(archivo, as_attachment=True, download_name=nombre,
                     mimetype="application/pdf")
