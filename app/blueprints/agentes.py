"""ABM de agentes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort

from ..extensions import db
from ..models import Agente

bp = Blueprint("agentes", __name__, url_prefix="/agentes")


@bp.route("/")
def listado():
    agentes = Agente.query.order_by(Agente.activo.desc(), Agente.apellido, Agente.nombre).all()
    return render_template("agentes/listado.html", agentes=agentes)


@bp.route("/nuevo", methods=["GET", "POST"])
def nuevo():
    if request.method == "POST":
        agente = _desde_form(Agente(), request.form)
        if not agente.nombre or not agente.apellido:
            flash("Nombre y apellido son obligatorios.", "error")
            return render_template("agentes/form.html", modo="nuevo", agente=agente)
        db.session.add(agente)
        db.session.commit()
        flash("Agente creado.", "success")
        return redirect(url_for("agentes.listado"))
    return render_template("agentes/form.html", modo="nuevo", agente=None)


@bp.route("/<int:agente_id>/editar", methods=["GET", "POST"])
def editar(agente_id):
    agente = db.session.get(Agente, agente_id) or abort(404)
    if request.method == "POST":
        _desde_form(agente, request.form)
        if not agente.nombre or not agente.apellido:
            flash("Nombre y apellido son obligatorios.", "error")
            return render_template("agentes/form.html", modo="editar", agente=agente)
        db.session.commit()
        flash("Agente actualizado.", "success")
        return redirect(url_for("agentes.listado"))
    return render_template("agentes/form.html", modo="editar", agente=agente)


@bp.route("/<int:agente_id>/eliminar", methods=["POST"])
def eliminar(agente_id):
    agente = db.session.get(Agente, agente_id) or abort(404)
    if agente.lineas:
        # Tiene operaciones asociadas: se desactiva en lugar de borrar.
        agente.activo = False
        db.session.commit()
        flash("El agente tiene operaciones asociadas; se marcó como inactivo.", "warning")
    else:
        db.session.delete(agente)
        db.session.commit()
        flash("Agente eliminado.", "success")
    return redirect(url_for("agentes.listado"))


def _desde_form(agente, form):
    agente.nombre = (form.get("nombre") or "").strip()
    agente.apellido = (form.get("apellido") or "").strip()
    agente.matricula = (form.get("matricula") or "").strip() or None
    agente.tiene_titulo_corredor = form.get("tiene_titulo_corredor") == "on"
    agente.activo = form.get("activo", "on") == "on"
    agente.es_captador_desarrollo = form.get("es_captador_desarrollo") == "on"
    agente.desarrollos_captados = (form.get("desarrollos_captados") or "").strip() or None
    return agente
