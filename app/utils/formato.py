"""Formato es-AR para números, moneda y fechas (sin depender de locale del SO)."""
from decimal import Decimal

# Espacio irrompible: mantiene el símbolo de moneda pegado al número (una sola línea).
NBSP = " "


def formato_numero(valor, decimales=2):
    """1234567.5 -> '1.234.567,50' (miles con '.', decimales con ',')."""
    if valor is None or valor == "":
        valor = 0
    try:
        d = Decimal(str(valor))
    except Exception:
        d = Decimal("0")

    negativo = d < 0
    d = abs(d)
    texto = f"{d:.{decimales}f}"
    entero, _, frac = texto.partition(".")

    grupos = []
    while len(entero) > 3:
        grupos.insert(0, entero[-3:])
        entero = entero[:-3]
    grupos.insert(0, entero)
    salida = ".".join(grupos)

    if decimales:
        salida = f"{salida},{frac}"
    return ("-" if negativo else "") + salida


def simbolo_moneda(moneda):
    return "US$" if moneda == "USD" else "$"


def formato_moneda(valor, moneda="ARS", decimales=0):
    """Dinero es-AR. Por defecto SIN centavos (en Argentina no se usan) y con el
    símbolo pegado al número por un espacio irrompible para que nunca corte línea.
    Ej.: formato_moneda(6680000, 'ARS') -> '$ 6.680.000'."""
    return f"{simbolo_moneda(moneda)}{NBSP}{formato_numero(valor, decimales)}"


def formato_fecha(fecha):
    """date/datetime -> 'dd/mm/aaaa'."""
    if fecha is None:
        return ""
    return fecha.strftime("%d/%m/%Y")


def formato_porcentaje(valor):
    """3 -> '3%' ; 4.5 -> '4,5%' ; 20 -> '20%' (sin decimales innecesarios)."""
    if valor is None:
        return ""
    d = Decimal(str(valor)).normalize()
    texto = f"{d}"
    if "E" in texto or "e" in texto:
        # normalize() puede devolver notación científica para enteros con
        # ceros de cola (ej. 20 -> 2E+1). Usamos la representación plana y
        # solo recortamos ceros si hay parte decimal, para no mutilar el
        # entero (evita el bug "20" -> "2").
        texto = f"{d:f}"
        if "." in texto:
            texto = texto.rstrip("0").rstrip(".")
    return texto.replace(".", ",") + "%"


MESES_ES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def nombre_mes(numero):
    return MESES_ES[numero] if 1 <= numero <= 12 else ""
