"""Carga inicial de las operaciones de ALQUILER 2026 (Infinity Inmobiliaria).

Ejecutar UNA sola vez:  venv\\Scripts\\python.exe seed_alquileres_2026.py
Seguro: si ya hay alquileres cargados, aborta para no duplicar (no toca las compraventas).

Criterios (confirmados con el usuario):
  - Todas ALQUILER, en ARS.
  - Comisión = UN CANON (monto fijo = 1 mes), retención 20%.
  - Doble punta (ambos lados Infinity) = 1 canon dividido 50/50 entre los dos agentes
    -> se cargan dos líneas de medio canon (cada agente cobra su mitad; la inmobiliaria
       retiene el 20% del canon total).
  - Punta única (el otro lado es externo/particular) = 1 canon completo para ese agente.
"""
import unicodedata
from decimal import Decimal
from datetime import date

from app import create_app
from app.extensions import db
from app.models import (
    Agente, Operacion, LineaComision,
    TIPO_ALQUILER, MONEDA_ARS,
    ROL_LOCADORA, ROL_LOCATARIA,
    REP_INFINITY, REP_OTRA_INMOBILIARIA,
    COMISION_MONTO_FIJO,
)
from app.services.calculo import aplicar_calculo


def norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


# Punta: ("INF", clave[, "co-agente"])  |  ("EXT", "Nombre contraparte")
# Tupla op: (fecha, propiedad, canon, meses, tipo_contrato, escribano, extra, locadora, locataria)
OPS = [
    ("28/01/26", "Mono — Ameghino 300 (Alcazar)", 450000, 24, "residencial", "Paula Maldonado", "", ("INF","carina"), ("INF","carina")),
    ("30/01/26", "Depto (1d) — Adolfo Güemes 200", 550000, 24, "residencial", "Paula Maldonado", "", ("INF","nicolas"), ("INF","german")),
    ("30/01/26", "Depto (2d + c) — Anzoátegui 100", 700000, 24, "residencial", "Paula Maldonado", "", ("INF","german"), ("INF","duo")),
    ("19/01/26", "Mono amoblado — Av del Golf 200", 400000, 12, "residencial", "Río Gallegos", "Contrato certificado y legalizado", ("INF","german"), ("INF","duo")),
    ("03/02/26", "Casa (6 amb.) — Martín Cornejo 300", 1500000, 24, "comercial", "Paula Maldonado", "", ("INF","carina"), ("INF","federico")),
    ("04/02/26", "Depto (1d + c) — Grand Bourg", 650000, 24, "comercial", "Santa Fe", "Contrato certificado y legalizado", ("INF","duo"), ("INF","duo")),
    ("04/02/26", "Depto (1d) — Deán Funes 800 (247)", 750000, 24, "residencial", "Simón Dubois", "", ("INF","duo"), ("INF","lujan")),
    ("05/02/26", "Depto (1d) — Deán Funes 800 (113)", 650000, 24, "residencial", "Simón Dubois", "", ("INF","duo"), ("INF","duo")),
    ("09/02/26", "Depto (1d) — Deán Funes 800 (246)", 650000, 24, "residencial", "Simón Dubois", "", ("INF","duo"), ("EXT","Pitu&Gon")),
    ("10/02/26", "Depto (2d) — Uriburu 100 (Monumento Güemes)", 700000, 24, "residencial", "Paula Maldonado", "", ("INF","valeria"), ("INF","valeria")),
    ("13/02/26", "Dúplex — Madero Vistas (San Lorenzo)", 2200000, 12, "residencial", "Paula Palermo", "", ("INF","duo"), ("INF","duo")),
    ("13/02/26", "Mono — Belgrano 1100 (Terrace)", 450000, 24, "residencial", "Paula Palermo", "", ("INF","carina"), ("INF","mercedes")),
    ("13/02/26", "Depto (2d) — Maipú 1000", 680000, 24, "residencial", "Vanesa Ortiz", "", ("INF","ariana"), ("INF","ariana")),
    ("13/02/26", "Depto (1d) semiamoblado 406 — Leguizamón 800 (Ibero)", 550000, 24, "residencial", "Paula Palermo", "", ("INF","carina"), ("INF","marialaura")),
    ("18/02/26", "Depto (1d + c) — Pje Latorre 1200 (Atalaya)", 660000, 24, "residencial", "Josefina Villa", "", ("INF","lujan","Graciela"), ("INF","duo")),
    ("18/02/26", "Depto (4d) E2 — Parque Belgrano", 700000, 24, "residencial", "Paula Maldonado", "Abonó 1º año por adelantado", ("INF","duo"), ("INF","federico")),
    ("23/02/26", "Mono — Pje Mollinedo 200", 640000, 24, "residencial", "Claudia Lavin", "", ("INF","victoria"), ("INF","german")),
    ("02/03/26", "Depto (2d) amoblado 312 — Leguizamón 800 (Ibero)", 795000, 24, "residencial", "Orán", "Contrato certificado y legalizado", ("INF","carina"), ("INF","victoria")),
    ("19/03/26", "Mono (4) — Martín Cornejo 100", 415000, 9, "residencial", "Paula Maldonado", "", ("INF","carola"), ("INF","carola")),
    ("20/03/26", "Depto amoblado (1d) — 20 de Febrero 1200", 650000, 24, "residencial", "Florencia Carattoni", "", ("INF","julieta"), ("INF","victoria")),
    ("31/03/26", "Depto amoblado (2d) — Aniceto Latorre 700", 750000, 12, "residencial", "Florencia Carattoni", "", ("INF","victoria"), ("INF","victoria")),
    ("01/04/26", "Depto (1d) — Pje Latorre 1200 (Atalaya)", 600000, 24, "residencial", "Josefina Villa", "", ("INF","lujan","Graciela"), ("INF","marialaura")),
    ("01/04/26", "Mono (5ºB) — Pje Latorre 1200 (Atalaya)", 430000, 24, "residencial", "Josefina Villa", "", ("INF","lujan","Graciela"), ("INF","duo")),
    ("01/04/26", "Depto (1d) — República de Siria 600", 500000, 24, "residencial", "Paula Palermo", "", ("INF","duo"), ("INF","duo")),
    ("07/04/26", "Mono (7) — Martín Cornejo 100", 330000, 12, "residencial", "Florencia Carattoni", "", ("INF","carola"), ("INF","graciela")),
    ("08/04/26", "Casa (2d) — El Huaico", 750000, 24, "residencial", "Mara Gómez", "", ("INF","julieta"), ("INF","carola")),
    ("17/04/26", "Depto (2d + c) — Vicente López 1400 (Natania 68)", 750000, 24, "residencial", "Paula Palermo", "", ("INF","duo"), ("INF","duo")),
    ("06/04/26", "Depto (1d) 4C — Vicente López 1300", 650000, 24, "residencial", "Viviana Ola", "", ("INF","valeria"), ("INF","victoria")),
    ("21/04/26", "Depto (1d + c) — Deán Funes 800", 850000, 24, "residencial", "Simón Dubois", "", ("INF","duo"), ("EXT","Keller Williams")),
    ("30/04/26", "Local comercial — Leguizamón 700", 850000, 24, "comercial", "Viviana Pascual", "", ("INF","victoria"), ("INF","victoria")),
    ("30/04/26", "Casa (2d + c) — José Félix Uriburu 0", 1000000, 36, "residencial", "Paula Maldonado", "", ("INF","duo"), ("INF","lujan")),
    ("07/04/26", "Mono — Av Belgrano 2000 (Bambú)", 550000, 24, "residencial", "Paula Palermo", "", ("INF","valeria"), ("INF","federico")),
    ("06/05/26", "Depto (2d) 410 — Leguizamón 800 (Íbero)", 760000, 24, "residencial", "Florencia Carattoni", "", ("INF","carina"), ("INF","carina")),
    ("08/05/26", "Casa (3d + c) — San Remo (Mar Jónico 1200)", 650000, 24, "residencial", "Paula Palermo", "", ("INF","duo"), ("INF","federico")),
    ("30/04/26", "Galpón c/ oficina — Pachi Gorriti 2000", 1200000, 24, "comercial", "Florencia Carattoni", "", ("INF","valeria"), ("INF","valeria")),
    ("13/05/26", "Casa (3d + c) — Ciudad del Milagro", 850000, 24, "residencial", "Mara Gómez", "", ("INF","lujan"), ("INF","lujan")),
    ("12/05/26", "Local comercial — Deán Funes 1000", 1600000, 36, "comercial", "Florencia Carattoni", "", ("INF","carina"), ("EXT","Débora Masie Inmobiliaria")),
    ("20/05/26", "Depto (1d) 142 — Deán Funes 800", 650000, 24, "residencial", "Simón Dubois", "", ("INF","duo"), ("INF","duo")),
    ("28/05/26", "Mono amoblado (+ c) — Ameghino 300 (Alcazar)", 600000, 12, "residencial", "Paula Maldonado", "", ("INF","valeria"), ("INF","duo")),
    ("29/05/26", "Casa (3d + c) — Tres Cerritos (Las Encinas)", 1200000, 24, "residencial", "Florencia Carattoni", "", ("INF","german"), ("INF","carina")),
    ("29/05/26", "Depto (2d + c) — Vicente López 1400 (Natania 68)", 750000, 24, "residencial", "Paula Palermo", "", ("INF","duo"), ("INF","graciela")),
    ("02/06/26", "Casa (escuela) — Indalecio Gómez 100", 1200000, 36, "comercial", "Paula Maldonado", "", ("INF","duo"), ("INF","duo")),
    ("03/06/26", "Depto (1d) 115 — Deán Funes 800", 650000, 24, "residencial", "Simón Dubois", "", ("INF","duo"), ("INF","duo")),
    ("08/06/26", "Depto (1d) — Tres Cerritos (Los Tilos)", 380000, 12, "residencial", "Paula Palermo", "", ("INF","federico"), ("INF","ariana")),
    ("08/06/26", "Casa (4d + c) — Vertientes", 650000, 24, "residencial", "Florencia Carattoni", "", ("INF","german"), ("INF","lujan")),
    ("16/06/26", "Casa (5d + 2c) — La Almudena", 2000000, 24, "residencial", "Mara Gómez", "", ("INF","graciela","Luján"), ("INF","lujan")),
    ("19/06/26", "Casa (2d) — Vía Aurelia (zona Sur)", 800000, 24, "residencial", "Florencia Carattoni", "", ("INF","ariana"), ("INF","ariana")),
    ("22/06/26", "Casa (4d + c) — San Luis", 1000000, 24, "residencial", "Christian Abdenur", "", ("INF","carina"), ("INF","duo")),
]

NUEVOS = {"federico": "Federico", "valeria": "Valeria", "marialaura": "María Laura", "julieta": "Julieta"}

DUR = {24: "2 años", 12: "1 año", 36: "3 años", 9: "9 meses"}
ROL_TXT = {ROL_LOCADORA: "locadora", ROL_LOCATARIA: "locataria"}


def resolver_agentes():
    mapa = {norm(a.nombre): a.id for a in Agente.query.all()}
    resolve = {
        "german": mapa.get("german"), "victoria": mapa.get("victoria"),
        "carina": mapa.get("carina"), "lujan": mapa.get("lujan"),
        "carola": mapa.get("carola"), "graciela": mapa.get("graciela"),
        "ariana": mapa.get("ariana"), "mercedes": mapa.get("mercedes"),
        "nicolas": mapa.get("nicolas"), "duo": mapa.get("inmobiliario"),
    }
    for clave, disp in NUEVOS.items():
        existente = mapa.get(norm(disp))
        if existente:
            resolve[clave] = existente
        else:
            ag = Agente(nombre=disp, apellido="", tiene_titulo_corredor=False, activo=True)
            db.session.add(ag)
            db.session.flush()
            resolve[clave] = ag.id
            print(f"  + Agente creado: {disp}")
    faltan = [k for k, v in resolve.items() if v is None]
    if faltan:
        raise SystemExit(f"No se pudo resolver agente(s): {faltan}")
    return resolve


def main():
    app = create_app()
    with app.app_context():
        if Operacion.query.filter_by(tipo=TIPO_ALQUILER).count() > 0:
            raise SystemExit("Ya hay alquileres cargados. Abortando para no duplicar.")

        ag = resolver_agentes()

        for fecha_txt, prop, canon, meses, tipo_c, esc, extra, p1, p2 in OPS:
            d, m, y = fecha_txt.split("/")
            total = Decimal(canon) * meses
            n_inf = sum(1 for p in (p1, p2) if p[0] == "INF")
            canon_dec = Decimal(canon)
            por_linea = canon_dec if n_inf <= 1 else (canon_dec / 2)

            # Notas
            notas = [f"Contrato {tipo_c} x {DUR.get(meses, f'{meses} meses')}."]
            if esc:
                notas.append(f"Escribano/a: {esc}.")
            if extra:
                notas.append(f"{extra}.")
            notas.append("Comisión: 1 canon"
                         + (" dividido 50/50 entre los dos agentes." if n_inf == 2 else "."))

            lineas = []
            for rol, p in [(ROL_LOCADORA, p1), (ROL_LOCATARIA, p2)]:
                if p[0] == "INF":
                    if len(p) > 2:
                        notas.append(f"Co-agente (punta {ROL_TXT[rol]}): {p[2]}.")
                    l = LineaComision(
                        rol=rol, representacion=REP_INFINITY, agente_id=ag[p[1]],
                        comision_tipo=COMISION_MONTO_FIJO, comision_monto_fijo=por_linea,
                        base_calculo=total, retencion_porcentaje=20,
                    )
                    aplicar_calculo(l)
                else:
                    l = LineaComision(rol=rol, representacion=REP_OTRA_INMOBILIARIA,
                                      nombre_inmobiliaria=p[1], comision_bruta=0,
                                      monto_inmobiliaria=0, monto_agente=0)
                lineas.append(l)

            op = Operacion(
                tipo=TIPO_ALQUILER, moneda=MONEDA_ARS,
                fecha=date(2000 + int(y), int(m), int(d)),
                propiedad=prop, notas=" ".join(notas),
                duracion_meses=meses, canon_mensual=canon_dec, monto_total_contrato=total,
            )
            op.lineas = lineas
            db.session.add(op)

        db.session.commit()

        alq = Operacion.query.filter_by(tipo=TIPO_ALQUILER).all()
        bruta = sum((o.comision_bruta_total for o in alq))
        inmo = sum((o.monto_inmobiliaria_total for o in alq))
        agente = sum((o.monto_agente_total for o in alq))
        print(f"\n  Alquileres cargados: {len(alq)}")
        print(f"  Comisión bruta total (ARS): $ {bruta:,.2f}")
        print(f"  Total inmobiliaria (ARS):   $ {inmo:,.2f}")
        print(f"  Total agentes (ARS):        $ {agente:,.2f}")
        print("  CARGA COMPLETA OK")


if __name__ == "__main__":
    main()
