import asyncio
import ssl as _ssl
from logging.config import fileConfig
from urllib.parse import urlencode

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings

# Import all models so Alembic can detect them
from app.core.database import Base  # noqa: F401
import app.domains.auth.models  # noqa: F401
import app.domains.cloud_accounts.models  # noqa: F401
import app.domains.decision_engine.models  # noqa: F401
import app.domains.workflow.models  # noqa: F401
import app.domains.experiments.models  # noqa: F401
import app.domains.risk_budgets.models  # noqa: F401
import app.domains.change_events.models  # noqa: F401
import app.domains.audit_chain.models  # noqa: F401
import app.domains.policy.models  # noqa: F401
import app.domains.economics.models  # noqa: F401
import app.domains.admin.models  # noqa: F401
import app.domains.notifications.models  # noqa: F401
import app.domains.intel.models  # noqa: F401
import app.domains.auth.token_blacklist  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    import sqlalchemy as sa
    from alembic.ddl.impl import DefaultImpl
    from sqlalchemy import Column, MetaData, PrimaryKeyConstraint, Table

    # alembic 1.14+ hardcodes version_num as String(32); revision IDs in this
    # project exceed that limit, so we override the hook to use String(128).
    def _wide_version_table_impl(self, *, version_table, version_table_schema, version_table_pk, **kw):
        vt = Table(
            version_table,
            MetaData(),
            Column("version_num", sa.String(128), nullable=False),
            schema=version_table_schema,
        )
        if version_table_pk:
            vt.append_constraint(PrimaryKeyConstraint("version_num", name=f"{version_table}_pkc"))
        return vt

    DefaultImpl.version_table_impl = _wide_version_table_impl

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    settings = get_settings()
    configuration = config.get_section(config.config_ini_section, {})

    # Parse URL and remove SSL query params that asyncpg doesn't accept
    raw_url = settings.database_url
    url = make_url(raw_url)
    query = dict(url.query)

    # Extract SSL-related query params to pass via connect_args instead
    ssl_from_query = query.pop("ssl", None)
    query.pop("sslmode", None)

    # Rebuild URL without SSL query params
    if query:
        url = url.set(query=urlencode(query, doseq=True))
    else:
        url = url.set(query=None)

    configuration["sqlalchemy.url"] = str(url)

    connect_args: dict = {}
    # Enable SSL if: explicit ?ssl=true in URL, or db_ssl_enabled, or production
    ssl_enabled = (
        ssl_from_query is not None
        or settings.db_ssl_enabled
        or settings.is_production
    )
    if ssl_enabled:
        ssl_ctx = _ssl.create_default_context()
        if settings.db_ssl_ca_file:
            ssl_ctx.load_verify_locations(cafile=settings.db_ssl_ca_file)
        if not settings.db_ssl_verify:
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = _ssl.CERT_NONE
        connect_args["ssl"] = ssl_ctx

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
