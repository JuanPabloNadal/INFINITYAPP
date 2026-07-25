"""Fija la retención propia (por defecto) de agentes puntuales.

Sirve para las dos bases, según las variables de entorno (ver app/config.py):

    # base local (SQLite de instance/)
    venv\\Scripts\\python.exe aplicar_retenciones_default.py

    # base de la nube (Neon) — desde Bash, sin BOM:
    DATABASE_URL='postgresql://...' python aplicar_retenciones_default.py

Es idempotente: se puede correr varias veces sin efecto adicional. Agrega la
columna `agentes.retencion_default` si todavía no existe (en la nube el
arranque de la app no corre las migraciones livianas, a propósito).
"""
import unicodedata

from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db
from app.models import Agente

# (apellido, nombre) -> retención que deja en la inmobiliaria.
RETENCIONES = {
    ("DUO", "Inmobiliario"): 10,
    ("GARCIA", "Victoria"): 10,
    ("NADAL", "German"): 0,
    ("PROSIK", "Carina"): 0,
}


def _clave(apellido, nombre):
    """Normaliza para comparar sin distinguir mayúsculas ni acentos
    ('García' y 'GARCIA' son el mismo agente)."""
    def limpiar(texto):
        sin_acentos = unicodedata.normalize("NFKD", (texto or "").strip())
        sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
        return sin_acentos.casefold()
    return limpiar(apellido), limpiar(nombre)


def _asegurar_columna():
    insp = inspect(db.engine)
    columnas = {c["name"] for c in insp.get_columns("agentes")}
    if "retencion_default" not in columnas:
        db.session.execute(text("ALTER TABLE agentes ADD COLUMN retencion_default INTEGER"))
        db.session.commit()
        print("Columna agentes.retencion_default creada.")


def main():
    app = create_app()
    with app.app_context():
        print(f"Base: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]}")
        _asegurar_columna()

        objetivos = {_clave(ap, no): pct for (ap, no), pct in RETENCIONES.items()}
        encontrados = set()

        for agente in Agente.query.all():
            clave = _clave(agente.apellido, agente.nombre)
            if clave not in objetivos:
                continue
            encontrados.add(clave)
            nuevo = objetivos[clave]
            anterior = agente.retencion_default
            agente.retencion_default = nuevo
            estado = "sin cambios" if anterior == nuevo else f"{anterior} -> {nuevo}"
            print(f"  {agente.nombre_completo}: retención propia {nuevo}%  ({estado})")

        faltantes = set(objetivos) - encontrados
        if faltantes:
            print("\nATENCIÓN — no se encontraron estos agentes en esta base:")
            for apellido, nombre in faltantes:
                print(f"  {apellido}, {nombre}")

        db.session.commit()
        print("\nListo.")


if __name__ == "__main__":
    main()
