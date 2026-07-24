"""Migra los datos del SQLite local (instance/infinity.db) a la base de la nube.

USO (una sola vez, desde la PC donde está la base con los datos):

    1. Conseguí la cadena de conexión de Neon (empieza con postgresql://...).
    2. En la terminal, dentro de "D:\\INFINITY APP":

       Windows PowerShell:
         $env:DATABASE_URL = "postgresql://USUARIO:CLAVE@HOST/neondb?sslmode=require"
         venv\\Scripts\\python.exe migrar_a_postgres.py

    El script:
      - Crea las tablas en Neon (si no existen).
      - BORRA lo que haya en Neon y copia TODO desde el SQLite local,
        conservando los IDs. Es seguro correrlo más de una vez (repite la carga).
      - Ajusta las secuencias de Postgres para que los próximos IDs sigan bien.

Los importes se leen con los tipos del modelo (Decimal), así no se pierde
precisión en las comisiones.
"""
import os
import sys

from sqlalchemy import create_engine, text

from app import create_app
from app.config import BASE_DIR
from app.extensions import db

SQLITE_PATH = os.path.join(BASE_DIR, "instance", "infinity.db")


def main():
    destino = os.environ.get("DATABASE_URL")
    if not destino:
        print("ERROR: definí la variable DATABASE_URL con la cadena de Neon antes de correr esto.")
        sys.exit(1)

    if not os.path.exists(SQLITE_PATH):
        print(f"ERROR: no encuentro la base local en {SQLITE_PATH}")
        sys.exit(1)

    # create_app usa DATABASE_URL -> crea/migra el esquema en el DESTINO (Neon).
    app = create_app()

    with app.app_context():
        destino_dialecto = db.engine.dialect.name
        print(f"Destino: {db.engine.url.render_as_string(hide_password=True)}  ({destino_dialecto})")
        print(f"Origen : {SQLITE_PATH}")

        tablas = list(db.metadata.sorted_tables)  # orden que respeta las FK

        # --- Leer TODO del SQLite usando los tipos del modelo (Decimal, date, bool) ---
        origen = create_engine("sqlite:///" + SQLITE_PATH)
        datos = {}
        with origen.connect() as conn:
            for tabla in tablas:
                filas = [dict(r._mapping) for r in conn.execute(tabla.select())]
                datos[tabla.name] = filas
        origen.dispose()

        print("\nFilas encontradas en el origen:")
        for tabla in tablas:
            print(f"  {tabla.name:28} {len(datos[tabla.name])}")

        # --- Vaciar el destino (en orden inverso por las FK) y volver a cargar ---
        for tabla in reversed(tablas):
            db.session.execute(tabla.delete())
        db.session.commit()

        for tabla in tablas:
            filas = datos[tabla.name]
            if filas:
                db.session.execute(tabla.insert(), filas)
        db.session.commit()

        # --- Ajustar las secuencias de Postgres para que sigan desde el MAX(id) ---
        if destino_dialecto == "postgresql":
            for tabla in tablas:
                if "id" not in tabla.c:
                    continue
                maxid = db.session.execute(text(f'SELECT MAX(id) FROM "{tabla.name}"')).scalar()
                if maxid is not None:
                    db.session.execute(
                        text("SELECT setval(pg_get_serial_sequence(:t, 'id'), :m, true)"),
                        {"t": tabla.name, "m": maxid},
                    )
            db.session.commit()

        # --- Verificación: contar filas en el destino ---
        print("\nFilas cargadas en el destino:")
        ok = True
        for tabla in tablas:
            n = db.session.execute(text(f'SELECT COUNT(*) FROM "{tabla.name}"')).scalar()
            esperado = len(datos[tabla.name])
            marca = "OK " if n == esperado else "DIFF"
            if n != esperado:
                ok = False
            print(f"  [{marca}] {tabla.name:28} {n} (esperado {esperado})")

        print("\nMIGRACION COMPLETA." if ok else "\nATENCION: hubo diferencias, revisá arriba.")


if __name__ == "__main__":
    main()
