"""Punto de entrada de Infinity Inmobiliaria.

Dos modos de arranque:

  - Normal (sin ventana de terminal): se lanza con `iniciar.vbs`, que usa
    pythonw.exe y define INFINITY_TRAY=1. La app corre en segundo plano con un
    ícono en la bandeja del sistema (menú "Abrir Infinity" / "Salir").

  - Desarrollo: `python run.py` (o `iniciar.bat`) → servidor de Flask con la
    consola visible. Respeta FLASK_DEBUG (1 = recarga automática).
"""
import os
import socket
import logging
import threading
import webbrowser
from threading import Timer

from app import create_app

URL = "http://127.0.0.1:5000"
HOST, PUERTO = "127.0.0.1", 5000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = create_app()


def _abrir_navegador():
    webbrowser.open_new(URL)


def _configurar_log():
    """pythonw no tiene consola: registramos errores en un archivo."""
    logging.basicConfig(
        filename=os.path.join(BASE_DIR, "infinity.log"),
        level=logging.INFO,
        format="%(asctime)s  %(levelname)s  %(message)s",
    )


def _puerto_ocupado():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, PUERTO)) == 0


def _servir():
    from waitress import serve
    serve(app, host=HOST, port=PUERTO, threads=8)


def _ejecutar_con_bandeja():
    """Modo normal: sin consola, con ícono en la bandeja del sistema."""
    _configurar_log()

    # Evitar doble arranque: si ya hay una instancia, solo abrir el navegador.
    if _puerto_ocupado():
        _abrir_navegador()
        return

    threading.Thread(target=_servir, daemon=True).start()
    Timer(1.2, _abrir_navegador).start()

    try:
        import pystray
        from PIL import Image

        imagen = Image.open(os.path.join(BASE_DIR, "app", "static", "img", "favicon.png"))

        def _abrir(icon, item):
            _abrir_navegador()

        def _salir(icon, item):
            icon.stop()
            os._exit(0)

        menu = pystray.Menu(
            pystray.MenuItem("Abrir Infinity", _abrir, default=True),
            pystray.MenuItem("Salir", _salir),
        )
        pystray.Icon("infinity", imagen, "Infinity Inmobiliaria", menu).run()
    except Exception:
        # Si la bandeja no está disponible, igual seguimos sirviendo la app.
        logging.exception("No se pudo iniciar el ícono de bandeja; la app sigue corriendo.")
        threading.Event().wait()


def _ejecutar_dev():
    """Modo desarrollo: servidor de Flask con consola visible."""
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        Timer(1.2, _abrir_navegador).start()
    app.run(host=HOST, port=PUERTO, debug=debug, use_reloader=debug)


if __name__ == "__main__":
    if os.environ.get("INFINITY_TRAY") == "1":
        _ejecutar_con_bandeja()
    else:
        _ejecutar_dev()
