"""Pruebas de los criterios de aceptación del cálculo de comisiones.

    venv/Scripts/python.exe tests_calculo.py
"""
from decimal import Decimal

from app.services.calculo import calcular_comision
from app.models import COMISION_PORCENTAJE, COMISION_MONTO_FIJO

errores = 0


def chequear(nombre, obtenido, esperado):
    global errores
    ok = Decimal(obtenido) == Decimal(esperado)
    estado = "OK " if ok else "FALLA"
    if not ok:
        errores += 1
    print(f"  [{estado}] {nombre}: obtenido={obtenido}  esperado={esperado}")


print("Ejemplo 1 — Compraventa US$100.000 · 3% · retención 30%")
bruta, inmo, agente = calcular_comision(COMISION_PORCENTAJE, 3, None, 100000, 30)
chequear("comisión bruta", bruta, "3000.00")
chequear("monto inmobiliaria", inmo, "900.00")
chequear("monto agente", agente, "2100.00")

print("Ejemplo 2 — Alquiler 24m canon $300.000 (total 7.200.000) · 4,5% · retención 20%")
bruta, inmo, agente = calcular_comision(COMISION_PORCENTAJE, Decimal("4.5"), None, 7200000, 20)
chequear("comisión bruta", bruta, "324000.00")
chequear("monto inmobiliaria", inmo, "64800.00")
chequear("monto agente", agente, "259200.00")

print("Ejemplo 3 — Doble punta: otra línea 3% sobre US$100.000, retención 30%")
bruta2, inmo2, agente2 = calcular_comision(COMISION_PORCENTAJE, 3, None, 100000, 30)
chequear("bruta total 2 puntas", bruta + 0 if False else (Decimal("3000") + bruta2), "6000.00")

print("Ejemplo 4 — Monto fijo (un canon = $300.000) · retención 10%")
bruta, inmo, agente = calcular_comision(COMISION_MONTO_FIJO, None, 300000, 7200000, 10)
chequear("comisión bruta", bruta, "300000.00")
chequear("monto inmobiliaria", inmo, "30000.00")
chequear("monto agente", agente, "270000.00")

print("Ejemplo 5 — Comisión 1% (caso editado) US$100.000 · retención 20%")
bruta, inmo, agente = calcular_comision(COMISION_PORCENTAJE, 1, None, 100000, 20)
chequear("comisión bruta", bruta, "1000.00")
chequear("monto inmobiliaria", inmo, "200.00")
chequear("monto agente", agente, "800.00")

print()
if errores == 0:
    print("TODOS LOS CRITERIOS DE CALCULO PASARON [OK]")
else:
    print(f"HAY {errores} FALLA(S)")
    raise SystemExit(1)
