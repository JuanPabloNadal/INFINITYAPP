"""Operaciones: listado con filtros, alta, edición, detalle y borrado."""
from datetime import date

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort,
)
from sqlalchemy import or_

from ..extensions import db
from ..models import (
    Operacion, LineaComision, Agente, Configuracion, TipoFiguraPersonalizada,
    TIPOS_OPERACION, ROLES_POR_TIPO, TIPO_COMPRAVENTA, TIPO_ALQUILER,
    REPRESENTACIONES_CON_COMISION,
    FIGURA_DATERO, FIGURA_CAPTADOR_DESARROLLO, FIGURA_AAA, FIGURA_PERSONALIZADA,
    AAA_SITUACIONES, ETIQUETA_AAA_SITUACION,
)
from ..services.formulario import parsear_operacion

bp = Blueprint("operaciones", __name__, url_prefix="/operaciones")


def _filtrar(query, args):
    """Aplica filtros comunes (tipo, agente, propiedad, rango de fechas)."""
    tipo = args.get("tipo", "").strip()
    agente_id = args.get("agente_id", "").strip()
    texto = args.get("q", "").strip()
    desde = args.get("desde", "").strip()
    hasta = args.get("hasta", "").strip()

    if tipo in TIPOS_OPERACION:
        query = query.filter(Operacion.tipo == tipo)
    if agente_id.isdigit():
        query = query.filter(
            Operacion.lineas.any(
                (LineaComision.agente_id == int(agente_id))
                & (LineaComision.representacion.in_(REPRESENTACIONES_CON_COMISION))
            )
        )
    if texto:
        like = f"%{texto}%"
        query = query.filter(or_(Operacion.propiedad.ilike(like),
                                 Operacion.notas.ilike(like)))
    if desde:
        try:
            query = query.filter(Operacion.fecha >= date.fromisoformat(desde))
        except ValueError:
            pass
    if hasta:
        try:
            query = query.filter(Operacion.fecha <= date.fromisoformat(hasta))
        except ValueError:
            pass
    return query


@bp.route("/")
def listado():
    query = _filtrar(Operacion.query, request.args)
    operaciones = query.order_by(Operacion.fecha.desc(), Operacion.id.desc()).all()
    agentes = Agente.query.order_by(Agente.apellido, Agente.nombre).all()
    return render_template(
        "operaciones/listado.html",
        operaciones=operaciones,
        agentes=agentes,
        filtros=request.args,
        tipos=TIPOS_OPERACION,
    )


def _valores_distintos(columna):
    return sorted({r[0] for r in db.session.query(columna)
                   .filter(columna.isnot(None)).distinct().all() if r[0]})


def _datos_formulario():
    cfg = Configuracion.obtener()
    agentes = Agente.query.filter_by(activo=True).order_by(Agente.apellido, Agente.nombre).all()
    inmobiliarias = _valores_distintos(LineaComision.nombre_inmobiliaria)
    desarrollos = _valores_distintos(LineaComision.nombre_desarrollo)

    # Mapa "nombre de desarrollo" -> captador registrado (para autocompletar
    # en el formulario el agente captador de desarrollo, Acta 001/2026).
    captadores = {}
    for ag in Agente.query.filter_by(es_captador_desarrollo=True, activo=True).all():
        for d in ag.lista_desarrollos_captados:
            captadores[d.lower()] = {"agenteId": ag.id, "nombre": ag.nombre_completo}

    tipos_figura_personalizada = (
        TipoFiguraPersonalizada.query.filter_by(activo=True)
        .order_by(TipoFiguraPersonalizada.nombre).all()
    )

    return cfg, agentes, inmobiliarias, desarrollos, captadores, tipos_figura_personalizada


def _con_personalizadas_en_uso(tipos_figura_personalizada, operacion):
    """Al editar, agrega al listado (para que el checkbox se siga mostrando)
    cualquier figura personalizada YA usada en la operación aunque haya sido
    desactivada después en Configuración."""
    vistos = {t.id for t in tipos_figura_personalizada}
    extra = []
    for linea in operacion.lineas:
        for figura in linea.figuras:
            if (figura.tipo == FIGURA_PERSONALIZADA and figura.tipo_figura_personalizada
                    and figura.tipo_figura_personalizada_id not in vistos):
                extra.append(figura.tipo_figura_personalizada)
                vistos.add(figura.tipo_figura_personalizada_id)
    return tipos_figura_personalizada + extra


@bp.route("/nueva", methods=["GET", "POST"])
def nueva():
    cfg, agentes, inmobiliarias, desarrollos, captadores, tipos_figura_personalizada = _datos_formulario()

    if request.method == "POST":
        operacion, errores, advertencias = parsear_operacion(request.form)
        for adv in advertencias:
            flash(adv, "warning")
        if errores:
            for e in errores:
                flash(e, "error")
            return render_template(
                "operaciones/form.html", modo="nueva", operacion=operacion,
                cfg=cfg, agentes=agentes, inmobiliarias=inmobiliarias, desarrollos=desarrollos,
                captadores=captadores, tipos_figura_personalizada=tipos_figura_personalizada,
                aaa_situaciones=AAA_SITUACIONES,
                etiqueta_aaa_situacion=ETIQUETA_AAA_SITUACION,
                roles_por_tipo=ROLES_POR_TIPO, form=request.form,
            )
        db.session.add(operacion)
        db.session.commit()
        flash("Operación registrada correctamente.", "success")
        return redirect(url_for("operaciones.ver", operacion_id=operacion.id))

    return render_template(
        "operaciones/form.html", modo="nueva", operacion=None,
        cfg=cfg, agentes=agentes, inmobiliarias=inmobiliarias, desarrollos=desarrollos,
        captadores=captadores, tipos_figura_personalizada=tipos_figura_personalizada,
        aaa_situaciones=AAA_SITUACIONES,
        etiqueta_aaa_situacion=ETIQUETA_AAA_SITUACION,
        roles_por_tipo=ROLES_POR_TIPO, form={},
    )


@bp.route("/<int:operacion_id>")
def ver(operacion_id):
    operacion = db.session.get(Operacion, operacion_id) or abort(404)
    return render_template("operaciones/ver.html", operacion=operacion)


@bp.route("/<int:operacion_id>/editar", methods=["GET", "POST"])
def editar(operacion_id):
    operacion = db.session.get(Operacion, operacion_id) or abort(404)
    cfg, agentes, inmobiliarias, desarrollos, captadores, tipos_figura_personalizada = _datos_formulario()
    tipos_figura_personalizada = _con_personalizadas_en_uso(tipos_figura_personalizada, operacion)

    if request.method == "POST":
        op, errores, advertencias = parsear_operacion(request.form, operacion=operacion)
        for adv in advertencias:
            flash(adv, "warning")
        if errores:
            for e in errores:
                flash(e, "error")
            return render_template(
                "operaciones/form.html", modo="editar", operacion=operacion,
                cfg=cfg, agentes=agentes, inmobiliarias=inmobiliarias, desarrollos=desarrollos,
                captadores=captadores, tipos_figura_personalizada=tipos_figura_personalizada,
                aaa_situaciones=AAA_SITUACIONES,
                etiqueta_aaa_situacion=ETIQUETA_AAA_SITUACION,
                roles_por_tipo=ROLES_POR_TIPO, form=request.form,
            )
        db.session.commit()
        flash("Operación actualizada.", "success")
        return redirect(url_for("operaciones.ver", operacion_id=operacion.id))

    return render_template(
        "operaciones/form.html", modo="editar", operacion=operacion,
        cfg=cfg, agentes=agentes, inmobiliarias=inmobiliarias, desarrollos=desarrollos,
        captadores=captadores, tipos_figura_personalizada=tipos_figura_personalizada,
        aaa_situaciones=AAA_SITUACIONES,
        etiqueta_aaa_situacion=ETIQUETA_AAA_SITUACION,
        roles_por_tipo=ROLES_POR_TIPO, form=_form_desde_operacion(operacion),
    )


@bp.route("/<int:operacion_id>/eliminar", methods=["POST"])
def eliminar(operacion_id):
    operacion = db.session.get(Operacion, operacion_id) or abort(404)
    db.session.delete(operacion)
    db.session.commit()
    flash("Operación eliminada.", "success")
    return redirect(url_for("operaciones.listado"))


def _form_desde_operacion(op):
    """Reconstruye un dict tipo-form para precargar el formulario en edición."""
    f = {
        "tipo": op.tipo,
        "fecha": op.fecha.isoformat() if op.fecha else "",
        "propiedad": op.propiedad or "",
        "moneda": op.moneda or "",
        "notas": op.notas or "",
        "monto_venta": _s(op.monto_venta),
        "duracion_meses": op.duracion_meses or "",
        "canon_mensual": _s(op.canon_mensual),
        "monto_total_contrato": _s(op.monto_total_contrato),
    }
    roles = ROLES_POR_TIPO[op.tipo]
    # Mapear líneas existentes a su posición por rol.
    por_rol = {l.rol: l for l in op.lineas}
    for i, rol in enumerate(roles):
        l = por_rol.get(rol)
        if not l:
            continue
        f[f"punta{i}_representacion"] = l.representacion
        f[f"punta{i}_agenteId"] = l.agente_id or ""
        f[f"punta{i}_nombreInmobiliaria"] = l.nombre_inmobiliaria or ""
        f[f"punta{i}_nombreDesarrollo"] = l.nombre_desarrollo or ""
        f[f"punta{i}_comisionTipo"] = l.comision_tipo or "PORCENTAJE"
        f[f"punta{i}_comisionPorcentaje"] = _s(l.comision_porcentaje)
        f[f"punta{i}_comisionMontoFijo"] = _s(l.comision_monto_fijo)
        f[f"punta{i}_baseCalculo"] = _s(l.base_calculo)
        f[f"punta{i}_retencionPorcentaje"] = l.retencion_porcentaje or 30
        f[f"punta{i}_comisionMotivoEdicion"] = l.comision_motivo_edicion or ""

        for figura in l.figuras:
            if figura.tipo == FIGURA_DATERO:
                f[f"punta{i}_datero"] = "on"
                f[f"punta{i}_dateroAgenteId"] = figura.agente_id
                f[f"punta{i}_dateroRetencion"] = figura.retencion_porcentaje
            elif figura.tipo == FIGURA_CAPTADOR_DESARROLLO:
                f[f"punta{i}_captador"] = "on"
                f[f"punta{i}_captadorAgenteId"] = figura.agente_id
                f[f"punta{i}_captadorRetencion"] = figura.retencion_porcentaje
            elif figura.tipo == FIGURA_AAA:
                f[f"punta{i}_aaa"] = "on"
                f[f"punta{i}_aaaAgenteId"] = figura.agente_id
                f[f"punta{i}_aaaSituacion"] = figura.situacion_aaa
                f[f"punta{i}_aaaRetencion"] = figura.retencion_porcentaje
            elif figura.tipo == FIGURA_PERSONALIZADA:
                base = f"punta{i}_personalizada{figura.tipo_figura_personalizada_id}"
                f[base] = "on"
                f[f"{base}AgenteId"] = figura.agente_id
                f[f"{base}Pct"] = _s(figura.porcentaje)
                f[f"{base}Retencion"] = figura.retencion_porcentaje
    return f


def _s(valor):
    if valor is None:
        return ""
    # Para inputs type=number usamos punto decimal y sin separador de miles.
    texto = f"{valor}"
    return texto
