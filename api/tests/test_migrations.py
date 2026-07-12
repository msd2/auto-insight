"""The baseline migration applies clean to an empty database and matches

the SQLAlchemy models exactly (no schema drift).
"""

import asyncio

import asyncpg
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from autoinsight.models import Base
from tests.conftest import PG_AUTH, PG_HOST, alembic_config, recreate_database

EXPECTED_TABLES = {
    "organisations",
    "users",
    "box_office_connections",
    "events",
    "event_instances",
    "customers",
    "customer_tags",
    "attendances",
    "survey_templates",
    "template_versions",
    "allocations",
    "invitations",
    "email_events",
    "suppressions",
    "responses",
    "insight_reports",
    # auth (WP 0.3)
    "sessions",
    "password_reset_tokens",
}


def test_migration_applies_clean_to_empty_database() -> None:
    """upgrade head → all 16 tables; downgrade base → nothing left behind."""
    db_name = "autoinsight_test_migrations"
    url = f"postgresql+asyncpg://{PG_AUTH}@{PG_HOST}/{db_name}"
    dsn = f"postgresql://{PG_AUTH}@{PG_HOST}/{db_name}"
    recreate_database(db_name)
    config = alembic_config(url)

    command.upgrade(config, "head")

    async def fetch_state() -> tuple[set[str], set[str]]:
        conn = await asyncpg.connect(dsn)
        try:
            tables = {
                row["tablename"]
                for row in await conn.fetch(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public'"
                )
            }
            enums = {
                row["typname"]
                for row in await conn.fetch("SELECT typname FROM pg_type WHERE typtype = 'e'")
            }
            return tables, enums
        finally:
            await conn.close()

    tables, enums = asyncio.run(fetch_state())
    assert tables == EXPECTED_TABLES | {"alembic_version"}
    assert "invitation_status" in enums

    # Downgrade must also be clean: no tables or enum types left behind.
    command.downgrade(config, "base")
    tables, enums = asyncio.run(fetch_state())
    assert tables == {"alembic_version"}
    assert enums == set()


async def test_no_drift_between_models_and_migrated_schema(migrated_database: str) -> None:
    """Autogenerate against the migrated DB finds nothing to do."""

    def diff(sync_conn: Connection) -> list[object]:
        migration_ctx = MigrationContext.configure(
            sync_conn, opts={"compare_type": True, "compare_server_default": True}
        )
        return compare_metadata(migration_ctx, Base.metadata)

    engine = create_async_engine(migrated_database, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            diffs = await conn.run_sync(diff)
    finally:
        await engine.dispose()
    assert diffs == []
