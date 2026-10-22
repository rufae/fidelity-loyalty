"""Base declarativa común a todos los modelos ORM."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Los modelos de la Fase 2+ heredan de aquí (migraciones vía Alembic)."""
