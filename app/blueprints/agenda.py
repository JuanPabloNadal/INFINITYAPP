"""Agenda: vista calendario mensual de operaciones."""
import calendar
from datetime import date

from flask import Blueprint, render_template, request

from ..models import Operacion

bp = Blueprint("agenda", __name__, url_prefix="/agenda")

calendar.setfirstweekday(calendar.MONDAY)
DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


@bp.route("/")
def mensual():
    hoy = date.today()
    try:
        anio = int(request.args.get("anio", hoy.year))
        mes = int(request.args.get("mes", hoy.month))
    except (TypeError, ValueError):
        anio, mes = hoy.year, hoy.month
    if not (1 <= mes <= 12):
        mes = hoy.month

    primero = date(anio, mes, 1)
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    ultimo = date(anio, mes, ultimo_dia)

    operaciones = (
        Operacion.query
        .filter(Operacion.fecha >= primero, Operacion.fecha <= ultimo)
        .order_by(Operacion.fecha, Operacion.id)
        .all()
    )

    por_dia = {}
    for op in operaciones:
        por_dia.setdefault(op.fecha.day, []).append(op)

    semanas = calendar.monthcalendar(anio, mes)  # listas de días (0 = fuera de mes)

    mes_ant = (mes - 1) or 12
    anio_ant = anio - 1 if mes == 1 else anio
    mes_sig = (mes % 12) + 1
    anio_sig = anio + 1 if mes == 12 else anio

    return render_template(
        "agenda/mensual.html",
        anio=anio, mes=mes, semanas=semanas, por_dia=por_dia,
        dias_semana=DIAS_SEMANA, hoy=hoy,
        nav={"mes_ant": mes_ant, "anio_ant": anio_ant,
             "mes_sig": mes_sig, "anio_sig": anio_sig},
        total_operaciones=len(operaciones),
    )
