"""Registro mensual / reportes y exportación."""
import calendar
from datetime import date

from flask import Blueprint, render_template, request, send_file

from ..models import (
    Operacion, Agente, LineaComision, TIPOS_OPERACION, REPRESENTACIONES_CON_COMISION,
)
from ..services.reportes import balance_por_moneda
from ..services.exportar import exportar_excel, exportar_pdf
from ..utils.formato import nombre_mes
from sqlalchemy import or_

bp = Blueprint("reportes", __name__, url_prefix="/reportes")


def _operaciones_filtradas(args):
    hoy = date.today()
    try:
        anio = int(args.get("anio", hoy.year))
        mes = int(args.get("mes", hoy.month))
    except (TypeError, ValueError):
        anio, mes = hoy.year, hoy.month

    rango = args.get("rango", "mes")

    query = Operacion.query
    if rango == "anual":
        query = query.filter(Operacion.fecha >= date(anio, 1, 1),
                             Operacion.fecha <= date(anio, 12, 31))
        periodo = f"Año {anio}"
    elif rango != "personalizado":
        if not (1 <= mes <= 12):
            mes = hoy.month
        primero = date(anio, mes, 1)
        ultimo = date(anio, mes, calendar.monthrange(anio, mes)[1])
        query = query.filter(Operacion.fecha >= primero, Operacion.fecha <= ultimo)
        periodo = f"{nombre_mes(mes).capitalize()} {anio}"
    else:
        desde = args.get("desde", "").strip()
        hasta = args.get("hasta", "").strip()
        partes = []
        if desde:
            try:
                d = date.fromisoformat(desde)
                query = query.filter(Operacion.fecha >= d)
                partes.append(f"desde {d.strftime('%d/%m/%Y')}")
            except ValueError:
                pass
        if hasta:
            try:
                h = date.fromisoformat(hasta)
                query = query.filter(Operacion.fecha <= h)
                partes.append(f"hasta {h.strftime('%d/%m/%Y')}")
            except ValueError:
                pass
        periodo = "Período " + " ".join(partes) if partes else "Todas las operaciones"

    # Filtros extra (tipo, agente, texto)
    tipo = args.get("tipo", "").strip()
    agente_id = args.get("agente_id", "").strip()
    texto = args.get("q", "").strip()
    if tipo in TIPOS_OPERACION:
        query = query.filter(Operacion.tipo == tipo)
        periodo += f" · {tipo.capitalize()}"
    if agente_id.isdigit():
        query = query.filter(
            Operacion.lineas.any(
                (LineaComision.agente_id == int(agente_id))
                & (LineaComision.representacion.in_(REPRESENTACIONES_CON_COMISION))
            )
        )
        ag = Agente.query.get(int(agente_id))
        if ag:
            periodo += f" · Agente: {ag.nombre_completo}"
    if texto:
        like = f"%{texto}%"
        query = query.filter(or_(Operacion.propiedad.ilike(like), Operacion.notas.ilike(like)))

    operaciones = query.order_by(Operacion.fecha, Operacion.id).all()
    return operaciones, periodo


@bp.route("/")
def mensual():
    operaciones, periodo = _operaciones_filtradas(request.args)
    balance = balance_por_moneda(operaciones)
    agentes = Agente.query.order_by(Agente.apellido, Agente.nombre).all()
    hoy = date.today()
    return render_template(
        "reportes/mensual.html",
        operaciones=operaciones, balance=balance, periodo=periodo,
        agentes=agentes, filtros=request.args, tipos=TIPOS_OPERACION,
        anios=range(hoy.year - 5, hoy.year + 2),
        anio_sel=int(request.args.get("anio", hoy.year)) if request.args.get("anio", str(hoy.year)).isdigit() else hoy.year,
        mes_sel=int(request.args.get("mes", hoy.month)) if request.args.get("mes", str(hoy.month)).isdigit() else hoy.month,
    )


@bp.route("/excel")
def excel():
    operaciones, periodo = _operaciones_filtradas(request.args)
    archivo = exportar_excel(operaciones, titulo="Infinity Inmobiliaria — Operaciones",
                             subtitulo=periodo)
    nombre = f"infinity_operaciones_{_slug(periodo)}.xlsx"
    return send_file(
        archivo, as_attachment=True, download_name=nombre,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/pdf")
def pdf():
    operaciones, periodo = _operaciones_filtradas(request.args)
    archivo = exportar_pdf(operaciones, titulo="Reporte de operaciones",
                           subtitulo=periodo)
    nombre = f"infinity_operaciones_{_slug(periodo)}.pdf"
    return send_file(archivo, as_attachment=True, download_name=nombre,
                     mimetype="application/pdf")


def _slug(texto):
    import re
    t = texto.lower()
    t = re.sub(r"[áàä]", "a", t); t = re.sub(r"[éèë]", "e", t)
    t = re.sub(r"[íìï]", "i", t); t = re.sub(r"[óòö]", "o", t)
    t = re.sub(r"[úùü]", "u", t)
    t = t.replace("ñ", "n")
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    return t[:50] or "reporte"
