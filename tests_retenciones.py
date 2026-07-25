"""Pruebas de la retención propia por agente (incluido el caso 0%).

    venv/Scripts/python.exe tests_retenciones.py
"""
import os
import tempfile

from app import create_app
from app.config import Config
from app.extensions import db


tmp = tempfile.mkdtemp()
db_path = os.path.join(tmp, "test_retenciones.db")


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + db_path
    TESTING = True
    WTF_CSRF_ENABLED = False


app = create_app(TestConfig)
c = app.test_client()
c.post("/login", data={"clave": "infinity26"})
fallos = 0


def ok(nombre, cond):
    global fallos
    print(f"  [{'OK ' if cond else 'FALLA'}] {nombre}")
    if not cond:
        fallos += 1


print("Alta de agentes con retención propia:")
c.post("/agentes/nuevo", data={"nombre": "Inmobiliario", "apellido": "DUO",
                               "activo": "on", "retencion_default": "10"})
c.post("/agentes/nuevo", data={"nombre": "German", "apellido": "NADAL",
                               "tiene_titulo_corredor": "on", "activo": "on",
                               "retencion_default": "0"})
c.post("/agentes/nuevo", data={"nombre": "Sin", "apellido": "PACTO",
                               "activo": "on", "retencion_default": ""})

with app.app_context():
    from app.models import Agente
    duo = Agente.query.filter_by(apellido="DUO").first()
    nadal = Agente.query.filter_by(apellido="NADAL").first()
    sin_pacto = Agente.query.filter_by(apellido="PACTO").first()
    ok("DUO guarda retención propia 10%", duo.retencion_default == 10)
    ok("DUO sugiere 10%", duo.retencion_sugerida == 10)
    ok("NADAL guarda retención propia 0% (no se pierde el cero)", nadal.retencion_default == 0)
    ok("NADAL sugiere 0% (gana sobre el 20% del título)", nadal.retencion_sugerida == 0)
    ok("sin pacto queda en automática (None)", sin_pacto.retencion_default is None)
    ok("sin pacto sugiere 30%", sin_pacto.retencion_sugerida == 30)
    duo_id, nadal_id = duo.id, nadal.id

print("Formulario de operación: el 0% es elegible aunque no esté en Configuración:")
r = c.get("/operaciones/nueva")
html = r.data.decode("utf-8")
ok("el selector ofrece la opción 0%", '<option value="0"' in html)
ok("el agente NADAL viaja con data-retencion=\"0\"", 'data-retencion="0"' in html)
ok("el agente DUO viaja con data-retencion=\"10\"", 'data-retencion="10"' in html)

print("Compraventa con retención 0% y 10%:")
r = c.post("/operaciones/nueva", data={
    "tipo": "COMPRAVENTA", "fecha": "2026-06-10", "propiedad": "Casa Test 1",
    "monto_venta": "100000",
    "punta0_representacion": "INFINITY", "punta0_agenteId": str(nadal_id),
    "punta0_comisionTipo": "PORCENTAJE", "punta0_comisionPorcentaje": "3",
    "punta0_retencionPorcentaje": "0",
    "punta1_representacion": "INFINITY", "punta1_agenteId": str(duo_id),
    "punta1_comisionTipo": "PORCENTAJE", "punta1_comisionPorcentaje": "3",
    "punta1_retencionPorcentaje": "10",
}, follow_redirects=True)
ok("operación guardada", r.status_code == 200)

with app.app_context():
    from app.models import Operacion
    op = Operacion.query.first()
    linea_0 = [l for l in op.lineas if l.agente_id == nadal_id][0]
    linea_10 = [l for l in op.lineas if l.agente_id == duo_id][0]
    ok("línea 0%: retención persistida en 0", linea_0.retencion_porcentaje == 0)
    ok("línea 0%: la inmobiliaria no retiene nada", str(linea_0.monto_inmobiliaria) == "0.00")
    ok("línea 0%: el agente se lleva los 3000", str(linea_0.monto_agente) == "3000.00")
    ok("línea 10%: inmobiliaria 300", str(linea_10.monto_inmobiliaria) == "300.00")
    ok("línea 10%: agente 2700", str(linea_10.monto_agente) == "2700.00")
    ok("total inmobiliaria de la operación = 300", str(op.monto_inmobiliaria_total) == "300.00")
    ok("total agentes de la operación = 5700", str(op.monto_agente_total) == "5700.00")
    op_id = op.id

print("Reedición: la retención 0% no se pisa con 30%:")
r = c.get(f"/operaciones/{op_id}/editar")
html = r.data.decode("utf-8")
# El select de la punta que tiene 0% debe traer esa opción seleccionada.
bloque = html.split('name="punta0_retencionPorcentaje"')[1].split("</select>")[0]
ok("la punta al 0% reabre seleccionada en 0", '<option value="0" selected' in bloque)

print("Detalle de operación con figura AAA (etiqueta de la situación):")
r = c.post("/operaciones/nueva", data={
    "tipo": "COMPRAVENTA", "fecha": "2026-06-12", "propiedad": "Casa Test 2",
    "monto_venta": "100000",
    "punta0_representacion": "INFINITY", "punta0_agenteId": str(duo_id),
    "punta0_comisionTipo": "PORCENTAJE", "punta0_comisionPorcentaje": "3",
    "punta0_retencionPorcentaje": "10",
    "punta0_aaa": "on", "punta0_aaaAgenteId": str(nadal_id),
    "punta0_aaaSituacion": "B1", "punta0_aaaRetencion": "0",
    "punta1_representacion": "PARTICULAR",
}, follow_redirects=True)
ok("operación con AAA guardada", r.status_code == 200)
with app.app_context():
    from app.models import Operacion, FIGURA_AAA
    op2 = Operacion.query.filter_by(propiedad="Casa Test 2").first()
    figura = [f for l in op2.lineas for f in l.figuras if f.tipo == FIGURA_AAA][0]
    ok("la figura AAA expone la etiqueta de su situación",
       figura.etiqueta_situacion.startswith("AAA consigue la oferta"))
    op2_id = op2.id
r = c.get(f"/operaciones/{op2_id}")
ok("el detalle muestra el texto de la situación del AAA",
   "AAA consigue la oferta" in r.data.decode("utf-8"))

print()
if fallos == 0:
    print("RETENCIONES POR AGENTE: TODO OK")
else:
    print(f"HAY {fallos} FALLA(S)")
    raise SystemExit(1)
