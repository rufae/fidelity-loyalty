"""Entorno de Alembic: usa la misma configuración que la aplicación."""

from logging.config import fileConfig

import app.models  # noqa: F401  # registra los modelos en Base.metadata (Fase 2+)
from alembic import context
from app.core.config import get_settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    # disable_existing_loggers=False: no debe romper la captura de logs de las pruebas.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Si quien invoca la migración ya fijó la URL (p. ej. las pruebas), se respeta.
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Ejecuta la migración en modo `offline` (genera SQL sin conectar)."""
    url = config.get_main_option("sqlalchemy.url") or ""
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta la migración conectándose a la base de datos."""
    connectable = context.config.attributes.get("connection", None)

    if connectable is None:
        from sqlalchemy import engine_from_config, pool

        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
