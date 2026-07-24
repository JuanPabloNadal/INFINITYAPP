"""Configuración de la aplicación Infinity Inmobiliaria.

Funciona en dos modos según las variables de entorno:

  - LOCAL (sin variables): SQLite dentro de /instance, cookies sin HTTPS.
    Es lo que usa el instalador portable de la PC de la oficina.

  - PRODUCCIÓN (Vercel + Neon): si existe DATABASE_URL usa esa base
    PostgreSQL, exige INFINITY_SECRET_KEY y sirve las cookies solo por HTTPS.
"""
import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

# Vercel define la variable VERCEL=1 automáticamente en sus servidores.
EN_PRODUCCION = bool(os.environ.get("VERCEL") or os.environ.get("INFINITY_PROD"))


def _uri_base_de_datos():
    """Devuelve la URI de conexión.

    Neon entrega URLs tipo 'postgresql://usuario:clave@host/db?sslmode=require'.
    SQLAlchemy 2 + psycopg 3 requieren el prefijo 'postgresql+psycopg://'.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        # Sin DATABASE_URL: modo local con SQLite.
        return "sqlite:///" + os.path.join(INSTANCE_DIR, "infinity.db")

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class Config:
    # Clave para firmar sesiones/flash. En producción DEBE venir por variable
    # de entorno (si no, las sesiones se invalidan entre reinicios/instancias).
    SECRET_KEY = os.environ.get("INFINITY_SECRET_KEY", "infinity-inmobiliaria-local-dev")

    SQLALCHEMY_DATABASE_URI = _uri_base_de_datos()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # En serverless conviene reciclar conexiones y comprobarlas antes de usar,
    # para no arrastrar conexiones muertas de Neon tras un "autosuspend".
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # Contraseña de acceso a la app (pantalla de login). Cambiable sin tocar
    # código: variable de entorno APP_PASSWORD.
    APP_PASSWORD = os.environ.get("APP_PASSWORD", "infinity26")

    # Seguridad de la cookie de sesión.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = EN_PRODUCCION  # solo HTTPS en la nube
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

    # Parámetros de negocio por defecto (también editables en pantalla de Configuración).
    COMISION_DEFAULT_COMPRAVENTA = 3.0   # %
    COMISION_DEFAULT_ALQUILER = 4.5      # %
    OPCIONES_RETENCION = [30, 20, 10]    # %
    MONEDA_DEFAULT_ALQUILER = "ARS"
