"""Fábrica de la aplicación Flask — Infinity Inmobiliaria."""
import os

from flask import Flask

from .config import Config, INSTANCE_DIR
from .extensions import db
from .utils import formato
from .utils import graficos


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_class)

    # La carpeta instance/ solo hace falta para SQLite (modo local de escritorio).
    # En la nube usamos Postgres y el filesystem es de solo lectura, así que no
    # intentamos crearla (daría OSError: Read-only file system).
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        os.makedirs(INSTANCE_DIR, exist_ok=True)

    db.init_app(app)

    # Filtros Jinja para formato es-AR.
    app.jinja_env.filters["moneda"] = formato.formato_moneda
    app.jinja_env.filters["numero"] = formato.formato_numero
    app.jinja_env.filters["fecha"] = formato.formato_fecha
    app.jinja_env.filters["porcentaje"] = formato.formato_porcentaje
    app.jinja_env.filters["compacto"] = graficos.fmt_compacto
    app.jinja_env.globals["nombre_mes"] = formato.nombre_mes

    @app.context_processor
    def _inyectar_globales():
        from datetime import date
        return {"hoy_iso": date.today().isoformat()}

    # Blueprints
    from .blueprints.dashboard import bp as dashboard_bp
    from .blueprints.operaciones import bp as operaciones_bp
    from .blueprints.agentes import bp as agentes_bp
    from .blueprints.agenda import bp as agenda_bp
    from .blueprints.reportes import bp as reportes_bp
    from .blueprints.desempeno import bp as desempeno_bp
    from .blueprints.figuras import bp as figuras_bp
    from .blueprints.configuracion import bp as configuracion_bp
    from .blueprints.auth import bp as auth_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(operaciones_bp)
    app.register_blueprint(agentes_bp)
    app.register_blueprint(agenda_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(desempeno_bp)
    app.register_blueprint(figuras_bp)
    app.register_blueprint(configuracion_bp)
    app.register_blueprint(auth_bp)

    _configurar_puerta_de_acceso(app)

    # Crear tablas, migrar columnas nuevas y semilla de configuración.
    # Solo en modo local (SQLite): en la nube (Postgres) el esquema ya lo dejó
    # armado el script de migración, así que evitamos esas consultas en cada
    # arranque en frío del servidor (más rápido y sin escrituras innecesarias).
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        with app.app_context():
            from . import models  # noqa: F401
            db.create_all()
            _migrar_esquema()
            models.Configuracion.obtener()

    return app


def _configurar_puerta_de_acceso(app):
    """Exige la contraseña (pantalla de login) para todo, salvo el propio
    login y los archivos estáticos."""
    from flask import request, redirect, url_for, session

    abiertos = {"auth.login", "auth.logout", "static"}

    @app.before_request
    def _requerir_login():
        if request.endpoint in abiertos:
            return
        if not session.get("autenticado"):
            return redirect(url_for("auth.login", next=request.full_path
                                    if request.query_string else request.path))


def _migrar_esquema():
    """Migraciones livianas para bases ya existentes (agrega columnas faltantes)."""
    from sqlalchemy import inspect, text

    insp = inspect(db.engine)
    columnas_por_tabla = {
        "lineas_comision": [
            ("nombre_desarrollo", "VARCHAR(120)"),
        ],
        "agentes": [
            ("es_captador_desarrollo", "BOOLEAN DEFAULT FALSE"),
            ("desarrollos_captados", "TEXT"),
            ("retencion_default", "INTEGER"),
        ],
        "configuracion": [
            ("datero_pct", "NUMERIC(7, 4) DEFAULT 20.0"),
            ("captador_desarrollo_pct", "NUMERIC(7, 4) DEFAULT 33.0"),
        ],
        "figuras_comision": [
            ("tipo_figura_personalizada_id", "INTEGER"),
        ],
    }
    for tabla, columnas in columnas_por_tabla.items():
        existentes = {c["name"] for c in insp.get_columns(tabla)}
        for nombre, tipo in columnas:
            if nombre not in existentes:
                db.session.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}"))
                db.session.commit()
