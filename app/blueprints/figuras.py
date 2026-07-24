"""Figuras adicionales de comisión: datero, captador de desarrollo y Agente
Asistente al Ausente (AAA) — Acta de Asamblea 001/2026.

Página de referencia (documenta las reglas) + listado dinámico de los
captadores de desarrollo actualmente registrados en la pestaña Agentes.
"""
from flask import Blueprint, render_template

from ..models import (
    Agente, Configuracion,
    AAA_SITUACIONES, ETIQUETA_AAA_SITUACION, AAA_PORCENTAJE_SITUACION,
)

bp = Blueprint("figuras", __name__, url_prefix="/figuras")


@bp.route("/")
def index():
    cfg = Configuracion.obtener()
    captadores = (
        Agente.query.filter_by(es_captador_desarrollo=True)
        .order_by(Agente.apellido, Agente.nombre).all()
    )
    return render_template(
        "figuras.html",
        cfg=cfg,
        captadores=captadores,
        aaa_situaciones=AAA_SITUACIONES,
        etiqueta_aaa_situacion=ETIQUETA_AAA_SITUACION,
        aaa_pct_situacion=AAA_PORCENTAJE_SITUACION,
    )
