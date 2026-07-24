"""Carga inicial de las operaciones de compraventa 2026 (Infinity Inmobiliaria).

Ejecutar UNA sola vez:  venv\\Scripts\\python.exe seed_2026.py
Es seguro: si ya hay operaciones cargadas, aborta para no duplicar.

Criterios (confirmados con el usuario):
  - Todas COMPRAVENTA, en US$.
  - Cada punta de Infinity: comisión 3% del monto de venta, retención 20%.
  - Doble punta (ambos lados Infinity) = dos comisiones del 3%.
  - Otra inmobiliaria / particular: no generan comisión.
"""
import unicodedata
from datetime import date

from app import create_app
from app.extensions import db
from app.models import (
    Agente, Operacion, LineaComision,
    TIPO_COMPRAVENTA, MONEDA_USD,
    ROL_VENDEDORA, ROL_COMPRADORA,
    REP_INFINITY, REP_OTRA_INMOBILIARIA, REP_PARTICULAR,
    COMISION_PORCENTAJE,
)
from app.services.calculo import aplicar_calculo


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return s.strip()


# Punta: ('INF', clave_agente) | ('OTH', 'Nombre Inmobiliaria') | ('PAR', None)
OPERACIONES = [
    ("18/06/26", "2 monoambientes (6E y 7E) — Alvarado 1300 (Ed. Marea)", "Escribana: Fátima González",
     140000, ("INF", "carina"), ("INF", "german")),
    ("26/05/26", "Casa (3d + 2c) — El Huaico", "Escribana: Laura Unamuno",
     97000, ("OTH", "Dávalos Propiedades"), ("INF", "carola")),
    ("20/05/26", "2 monoambientes (+1c) — Alvarado 1300 (Ed. Marea)", "Escribana: Fátima González",
     130000, ("INF", "carina"), ("INF", "german")),
    ("18/05/26", "Terreno (L 14 M 51) — Vía Aurelia", "Escribano: Francisco Durand",
     23000, ("INF", "graciela"), ("INF", "duo")),
    ("15/05/26", "Casa (3d + c) — Santa Ana", "Escribano: Federico Alurralde. Punta Infinity: Carina (Ariana).",
     57000, ("INF", "carina"), ("OTH", "AVS Inmobiliaria")),
    ("22/04/26", "Depto — Ampliación Intersindical", "Escribana: Gabriela Causarano",
     50000, ("PAR", None), ("INF", "ariana")),
    ("29/04/26", "Monoambiente — Tamayo y Balcarce", "Escribana: Patricia Abudi",
     41000, ("INF", "german"), ("INF", "german")),
    ("21/04/26", "Monoambiente (29,5 m²) — IES INFINITY", "Escribana: Agustina Paz Costa. Punta vendedora: IES (Carina).",
     67327, ("INF", "carina"), ("INF", "victoria")),
    ("27/03/26", "Depto (3d) — Parque Belgrano (3ª etapa)", "Escribana: Lorena Crescini",
     65000, ("INF", "carola"), ("INF", "graciela")),
    ("12/02/26", "Casa (3d) — Tres Cerritos (Los Mistoles)", "Escribana: Gabriela Causarano",
     105000, ("INF", "german"), ("INF", "german")),
    ("10/03/26", "Terreno — Los Arreboles (Cerrillos)", "Escribano: Fernando Echazú",
     10000, ("INF", "german"), ("INF", "graciela")),
    ("06/03/26", "Casa (3d) + Depto (1d) — España al 1600", "Escribana: Josefina Villa",
     92800, ("INF", "ariana"), ("INF", "german")),
    ("25/02/26", "Depto (4d + c) — Gral Güemes al 2000", "Escribana: María José Costilla. Co-agente: Nicolás.",
     75000, ("INF", "german"), ("OTH", "RH Inmobiliaria")),
    ("06/02/26", "Casa (2d) — Grand Bourg (Godoy Cruz al 3000)", "Escribana: Claudia Romani",
     142500, ("OTH", "Gaia Inmobiliaria"), ("INF", "carina")),
    ("06/02/26", "Casa (3d) — Tres Cerritos (Los Pinos)", "Escribana: Claudia Romani",
     135000, ("INF", "carina"), ("OTH", "Molins Inmobiliaria")),
    ("03/02/26", "Terreno — Campo La Calderilla (La Caldera)", None,
     22000, ("INF", "mercedes"), ("INF", "graciela")),
    ("14/01/26", "Casa (3d) — San Luis", "Escribana: Mara Gómez",
     160000, ("INF", "carina"), ("INF", "lujan")),
    ("08/01/26", "Casa (1d) — Vertientes", None,
     73000, ("INF", "lujan"), ("INF", "nicolas")),
]

# Agentes nuevos a crear (clave -> (nombre, apellido))
NUEVOS = {
    "carola":   ("Carola", ""),
    "graciela": ("Graciela", ""),
    "ariana":   ("Ariana", ""),
    "mercedes": ("Mercedes", ""),
    "nicolas":  ("Nicolás", ""),
}


def resolver_agentes():
    """Devuelve dict clave_normalizada -> agente_id, creando los que falten."""
    mapa = {}
    for a in Agente.query.all():
        mapa[norm(a.nombre)] = a.id          # german, victoria, carina, inmobiliario, lujan
    resolve = {
        "german":   mapa.get("german"),
        "victoria": mapa.get("victoria"),
        "carina":   mapa.get("carina"),
        "duo":      mapa.get("inmobiliario"),  # "Inmobiliario DUO"
        "lujan":    mapa.get("lujan"),
    }
    for clave, (nombre, apellido) in NUEVOS.items():
        existente = mapa.get(norm(nombre))
        if existente:
            resolve[clave] = existente
        else:
            ag = Agente(nombre=nombre, apellido=apellido, tiene_titulo_corredor=False, activo=True)
            db.session.add(ag)
            db.session.flush()
            resolve[clave] = ag.id
            print(f"  + Agente creado: {nombre}")
    faltan = [k for k, v in resolve.items() if v is None]
    if faltan:
        raise SystemExit(f"No se pudo resolver agente(s): {faltan}")
    return resolve


def crear_linea(rol, punta, monto, agentes):
    tipo, valor = punta
    if tipo == "INF":
        l = LineaComision(
            rol=rol, representacion=REP_INFINITY, agente_id=agentes[valor],
            comision_tipo=COMISION_PORCENTAJE, comision_porcentaje=3,
            base_calculo=monto, retencion_porcentaje=20,
        )
        aplicar_calculo(l)
        return l
    if tipo == "OTH":
        return LineaComision(rol=rol, representacion=REP_OTRA_INMOBILIARIA,
                             nombre_inmobiliaria=valor, comision_bruta=0,
                             monto_inmobiliaria=0, monto_agente=0)
    return LineaComision(rol=rol, representacion=REP_PARTICULAR,
                         comision_bruta=0, monto_inmobiliaria=0, monto_agente=0)


def main():
    app = create_app()
    with app.app_context():
        if Operacion.query.count() > 0:
            raise SystemExit("Ya hay operaciones cargadas. Abortando para no duplicar.")

        agentes = resolver_agentes()

        for fecha_txt, propiedad, notas, monto, vend, comp in OPERACIONES:
            d, m, y = fecha_txt.split("/")
            op = Operacion(
                tipo=TIPO_COMPRAVENTA, moneda=MONEDA_USD,
                fecha=date(2000 + int(y), int(m), int(d)),
                propiedad=propiedad, notas=notas, monto_venta=monto,
            )
            op.lineas = [
                crear_linea(ROL_VENDEDORA, vend, monto, agentes),
                crear_linea(ROL_COMPRADORA, comp, monto, agentes),
            ]
            db.session.add(op)

        db.session.commit()

        # Verificación
        ops = Operacion.query.all()
        bruta = sum((o.comision_bruta_total for o in ops))
        inmo = sum((o.monto_inmobiliaria_total for o in ops))
        agente = sum((o.monto_agente_total for o in ops))
        print(f"\n  Operaciones cargadas: {len(ops)}")
        print(f"  Comisión bruta total: US$ {bruta:,.2f}")
        print(f"  Total inmobiliaria:   US$ {inmo:,.2f}")
        print(f"  Total agentes:        US$ {agente:,.2f}")
        print("  CARGA COMPLETA OK")


if __name__ == "__main__":
    main()
