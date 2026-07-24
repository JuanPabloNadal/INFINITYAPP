"""Puerta de acceso: una sola contraseña compartida para toda la app.

Pensado para uso interno de la inmobiliaria. La contraseña se define con la
variable de entorno APP_PASSWORD (por defecto 'infinity26'). No hay usuarios
individuales: quien tiene la clave, entra.
"""
import secrets

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, flash,
    current_app,
)

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    # Si ya está adentro, no tiene sentido mostrar el login.
    if session.get("autenticado"):
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        clave = request.form.get("clave", "")
        correcta = current_app.config["APP_PASSWORD"]
        # compare_digest evita filtrar información por el tiempo de comparación.
        if secrets.compare_digest(clave, correcta):
            session["autenticado"] = True
            session.permanent = True
            destino = request.args.get("next", "")
            # Solo redirigimos a rutas internas (evita open-redirect).
            if destino.startswith("/") and not destino.startswith("//"):
                return redirect(destino)
            return redirect(url_for("dashboard.index"))
        flash("Contraseña incorrecta.", "error")

    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("auth.login"))
