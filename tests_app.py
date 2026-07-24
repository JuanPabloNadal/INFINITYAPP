"""Prueba de humo de la app completa (rutas, formularios, exportación).

    venv/Scripts/python.exe tests_app.py
"""
import os
import tempfile

from app import create_app
from app.config import Config
from app.extensions import db


tmp = tempfile.mkdtemp()
db_path = os.path.join(tmp, "test.db")


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + db_path
    TESTING = True
    WTF_CSRF_ENABLED = False


app = create_app(TestConfig)
c = app.test_client()
c.post("/login", data={"clave": "infinity26"})  # pasar la puerta de acceso
fallos = 0


def ok(nombre, cond):
    global fallos
    print(f"  [{'OK ' if cond else 'FALLA'}] {nombre}")
    if not cond:
        fallos += 1


print("Rutas principales (GET):")
ok("GET /", c.get("/").status_code == 200)
ok("GET /operaciones/", c.get("/operaciones/").status_code == 200)
ok("GET /operaciones/nueva", c.get("/operaciones/nueva").status_code == 200)
ok("GET /agentes/", c.get("/agentes/").status_code == 200)
ok("GET /agenda/", c.get("/agenda/").status_code == 200)
ok("GET /reportes/", c.get("/reportes/").status_code == 200)
ok("GET /configuracion/", c.get("/configuracion/").status_code == 200)

print("Alta de agentes:")
c.post("/agentes/nuevo", data={"nombre": "Juan", "apellido": "Pérez", "activo": "on"})
c.post("/agentes/nuevo", data={"nombre": "Ana", "apellido": "Gómez",
                               "tiene_titulo_corredor": "on", "activo": "on"})
with app.app_context():
    from app.models import Agente
    agentes = Agente.query.order_by(Agente.id).all()
    ok("2 agentes creados", len(agentes) == 2)
    perez_id, gomez_id = agentes[0].id, agentes[1].id

print("Alta de compraventa (doble punta Infinity):")
r = c.post("/operaciones/nueva", data={
    "tipo": "COMPRAVENTA",
    "fecha": "2026-06-10",
    "propiedad": "Casa Los Ceibos 13",
    "monto_venta": "100000",
    "punta0_representacion": "INFINITY",
    "punta0_agenteId": str(gomez_id),
    "punta0_comisionTipo": "PORCENTAJE",
    "punta0_comisionPorcentaje": "3",
    "punta0_baseCalculo": "",
    "punta0_retencionPorcentaje": "30",
    "punta1_representacion": "INFINITY",
    "punta1_agenteId": str(perez_id),
    "punta1_comisionTipo": "PORCENTAJE",
    "punta1_comisionPorcentaje": "3",
    "punta1_baseCalculo": "",
    "punta1_retencionPorcentaje": "30",
}, follow_redirects=True)
ok("compraventa guardada (200)", r.status_code == 200)

with app.app_context():
    from app.models import Operacion
    op = Operacion.query.first()
    ok("operación creada", op is not None)
    ok("2 líneas de comisión", len(op.lineas) == 2)
    ok("comisión bruta total = 6000", str(op.comision_bruta_total) == "6000.00")
    ok("inmobiliaria total = 1800", str(op.monto_inmobiliaria_total) == "1800.00")
    ok("agentes total = 4200", str(op.monto_agente_total) == "4200.00")

print("Validación: % distinto al default sin motivo debe fallar:")
r = c.post("/operaciones/nueva", data={
    "tipo": "COMPRAVENTA", "fecha": "2026-06-11", "propiedad": "Depto Centro",
    "monto_venta": "50000",
    "punta0_representacion": "INFINITY", "punta0_agenteId": str(perez_id),
    "punta0_comisionTipo": "PORCENTAJE", "punta0_comisionPorcentaje": "1",
    "punta0_retencionPorcentaje": "30",
    "punta1_representacion": "PARTICULAR",
})
ok("rechaza % editado sin motivo (re-render 200, no redirect)", r.status_code == 200 and b"motivo" in r.data.lower())
with app.app_context():
    from app.models import Operacion
    ok("no se guardó la segunda operación", Operacion.query.count() == 1)

print("Alquiler con monto fijo (un canon) y otra inmobiliaria:")
r = c.post("/operaciones/nueva", data={
    "tipo": "ALQUILER", "fecha": "2026-06-15", "propiedad": "Depto Belgrano 500",
    "moneda": "ARS", "duracion_meses": "24", "canon_mensual": "300000",
    "monto_total_contrato": "7200000",
    "punta0_representacion": "INFINITY", "punta0_agenteId": str(gomez_id),
    "punta0_comisionTipo": "PORCENTAJE", "punta0_comisionPorcentaje": "4.5",
    "punta0_retencionPorcentaje": "20",
    "punta1_representacion": "OTRA_INMOBILIARIA", "punta1_nombreInmobiliaria": "Remax",
}, follow_redirects=True)
ok("alquiler guardado", r.status_code == 200)
with app.app_context():
    from app.models import Operacion, TIPO_ALQUILER
    alq = Operacion.query.filter_by(tipo=TIPO_ALQUILER).first()
    ok("comisión bruta alquiler = 324000", str(alq.comision_bruta_total) == "324000.00")
    ok("inmobiliaria alquiler = 64800", str(alq.monto_inmobiliaria_total) == "64800.00")
    ok("agente alquiler = 259200", str(alq.monto_agente_total) == "259200.00")

print("Exportaciones:")
r = c.get("/reportes/excel?rango=mes&mes=6&anio=2026")
ok("Excel descarga (xlsx, >1KB)", r.status_code == 200 and len(r.data) > 1000
   and r.data[:2] == b"PK")
r = c.get("/reportes/pdf?rango=mes&mes=6&anio=2026")
ok("PDF descarga (%PDF, >1KB)", r.status_code == 200 and len(r.data) > 1000
   and r.data[:4] == b"%PDF")

print("Filtros del listado:")
ok("filtro por tipo ALQUILER", c.get("/operaciones/?tipo=ALQUILER").status_code == 200)
ok("filtro por agente", c.get(f"/operaciones/?agente_id={gomez_id}").status_code == 200)
ok("búsqueda por texto", c.get("/operaciones/?q=Ceibos").status_code == 200)

print()
if fallos == 0:
    print("PRUEBA DE HUMO COMPLETA: TODO OK")
else:
    print(f"HAY {fallos} FALLA(S)")
    raise SystemExit(1)
