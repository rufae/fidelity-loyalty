"""Acceso a PostgreSQL: motor perezoso, sesión por petición y chequeo de salud.

El motor no se crea al importar el módulo: la aplicación puede arrancar sin BD
(liveness en `/health`) y decidir su estado real en `/ready`.
"""

import logging
from collections.abc import Iterator
from dataclasses import dataclass

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_engine: Engine | None = None


@dataclass(frozen=True)
class DatabaseStatus:
    """Resultado sanitizado de un chequeo de BD (nunca expone la URL ni credenciales)."""

    reachable: bool
    error_type: str | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_settings().database_url,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def reset_engine() -> None:
    """Descarta el motor cacheado (lo usan las pruebas al cambiar la URL)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def get_session() -> Iterator[Session]:
    """Sesión por petición: confirma si no hubo errores y siempre la cierra."""
    session = Session(get_engine())
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database() -> DatabaseStatus:
    """`SELECT 1` contra la BD. Devuelve estado; no lanza excepciones."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning("database_unreachable error_type=%s", type(exc).__name__)
        return DatabaseStatus(reachable=False, error_type=type(exc).__name__)
    return DatabaseStatus(reachable=True)
