"""Pantalla de configuración de parámetros por defecto."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort

from ..extensions import db
from ..models import Configuracion, MONEDAS, FiguraComision, TipoFiguraPersonalizada
from ..services.calculo import a_decimal

bp = Blueprint("configuracion", __name__, url_prefix="/configuracion")


def _tipos_figura_personalizada():
    return TipoFiguraPersonalizada.query.order_by(TipoFiguraPersonalizada.nombre).all()


@bp.route("/", methods=["GET", "POST"])
def editar():
    cfg = Configuracion.obtener()
    if request.method == "POST":
        cv = a_decimal(request.form.get("comision_default_compraventa"), "3")
        alq = a_decimal(request.form.get("comision_default_alquiler"), "4.5")
        datero = a_decimal(request.form.get("datero_pct"), "20")
        captador = a_decimal(request.form.get("captador_desarrollo_pct"), "33")
        if cv <= 0 or alq <= 0 or datero <= 0 or captador <= 0:
            flash("Las comisiones y porcentajes por defecto deben ser mayores a 0.", "error")
            return render_template(
                "configuracion/editar.html", cfg=cfg, monedas=MONEDAS,
                tipos_figura=_tipos_figura_personalizada(),
            )

        cfg.comision_default_compraventa = cv
        cfg.comision_default_alquiler = alq
        cfg.datero_pct = datero
        cfg.captador_desarrollo_pct = captador

        retenciones = request.form.get("opciones_retencion", "30,20,10")
        limpias = [p.strip() for p in retenciones.split(",") if p.strip().isdigit()]
        cfg.opciones_retencion = ",".join(limpias) if limpias else "30,20,10"

        moneda = (request.form.get("moneda_default_alquiler") or "ARS").strip().upper()
        cfg.moneda_default_alquiler = moneda if moneda in MONEDAS else "ARS"

        db.session.commit()
        flash("Configuración guardada.", "success")
        return redirect(url_for("configuracion.editar"))

    return render_template(
        "configuracion/editar.html", cfg=cfg, monedas=MONEDAS,
        tipos_figura=_tipos_figura_personalizada(),
    )


@bp.route("/figuras/nueva", methods=["POST"])
def nueva_figura():
    nombre = (request.form.get("nombre") or "").strip()
    pct = a_decimal(request.form.get("porcentaje_sugerido"), "10")
    if not nombre:
        flash("El nombre de la figura es obligatorio.", "error")
    elif pct <= 0:
        flash("El % sugerido debe ser mayor a 0.", "error")
    else:
        db.session.add(TipoFiguraPersonalizada(nombre=nombre, porcentaje_sugerido=pct))
        db.session.commit()
        flash(f"Figura '{nombre}' creada.", "success")
    return redirect(url_for("configuracion.editar"))


@bp.route("/figuras/<int:figura_id>/alternar", methods=["POST"])
def alternar_figura(figura_id):
    tf = db.session.get(TipoFiguraPersonalizada, figura_id) or abort(404)
    tf.activo = not tf.activo
    db.session.commit()
    flash(f"Figura '{tf.nombre}' {'activada' if tf.activo else 'desactivada'}.", "success")
    return redirect(url_for("configuracion.editar"))


@bp.route("/figuras/<int:figura_id>/eliminar", methods=["POST"])
def eliminar_figura(figura_id):
    tf = db.session.get(TipoFiguraPersonalizada, figura_id) or abort(404)
    en_uso = FiguraComision.query.filter_by(tipo_figura_personalizada_id=figura_id).count()
    if en_uso:
        tf.activo = False
        db.session.commit()
        flash(f"'{tf.nombre}' está en uso en {en_uso} operación(es); se desactivó en vez de eliminarla.", "warning")
    else:
        db.session.delete(tf)
        db.session.commit()
        flash(f"Figura '{tf.nombre}' eliminada.", "success")
    return redirect(url_for("configuracion.editar"))
