from logging.config import fileConfig

from sqlalchemy import JSON, engine_from_config, pool
from sqlalchemy.dialects.postgresql import JSONB

from alembic import context

from app.core.config import settings
from app.db.base import Base
import app.models

# Alembic Config object
config = context.config

# Read database URL from .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = Base.metadata


def compare_type(context, inspected_column, metadata_column, inspected_type, metadata_type):
    """Normalize identical JSON SQL spellings, retaining JSON/JSONB differences."""
    if isinstance(inspected_type, JSON) and isinstance(metadata_type, JSON):
        return (inspected_type.compile(dialect=context.dialect).casefold()
                != metadata_type.compile(dialect=context.dialect).casefold())
    return None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=compare_type,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=compare_type,
            )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
