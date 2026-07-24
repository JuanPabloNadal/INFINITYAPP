"""Punto de entrada para Vercel (@vercel/python).

Vercel toma la variable `app` (aplicación WSGI) de este archivo y la sirve.
Agregamos la raíz del proyecto al path para poder importar el paquete `app`.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from app import create_app  # noqa: E402

app = create_app()
