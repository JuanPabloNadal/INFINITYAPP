"""Extensiones compartidas (evita imports circulares)."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
