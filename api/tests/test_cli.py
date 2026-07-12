"""The seed CLI creates working credentials and is safe to re-run."""

import asyncio

import httpx
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from autoinsight.adapters.email import LoggingEmailProvider
from autoinsight.auth.service import AuthService
from autoinsight.cli import main, seed_org
from autoinsight.models import Organisation, User, UserRole


async def test_seed_org_is_idempotent_and_credentials_work(
    client: httpx.AsyncClient, session: AsyncSession
) -> None:
    kwargs = {
        "org_name": "Seeded Theatre",
        "slug": "seeded-theatre",
        "email": "admin@seeded.example",
        "user_name": "Seed Admin",
    }
    await seed_org(session, password="first-password", **kwargs)
    # Re-run with a new password: must not duplicate, must rotate the password.
    await seed_org(session, password="second-password", **kwargs)

    orgs = (await session.execute(select(Organisation))).scalars().all()
    users = (await session.execute(select(User))).scalars().all()
    assert len(orgs) == 1 and len(users) == 1
    assert users[0].role == UserRole.admin

    stale = await client.post(
        "/auth/login", json={"email": kwargs["email"], "password": "first-password"}
    )
    assert stale.status_code == 401
    fresh = await client.post(
        "/auth/login", json={"email": kwargs["email"], "password": "second-password"}
    )
    assert fresh.status_code == 200
    assert fresh.json() == {
        "user": {
            "id": str(users[0].id),
            "email": kwargs["email"],
            "name": "Seed Admin",
            "role": "admin",
        },
        "org": {"id": str(orgs[0].id), "name": "Seeded Theatre", "slug": "seeded-theatre"},
    }


def test_cli_main_seeds_working_credentials(migrated_database: str) -> None:
    """End-to-end through argparse ``main()``, twice, against the real DB."""
    argv = [
        "seed-org",
        "--name",
        "CLI Theatre",
        "--slug",
        "cli-theatre",
        "--email",
        "admin@cli.example",
        "--user-name",
        "CLI Admin",
        "--password",
        "cli-seeded-password",
        "--database-url",
        migrated_database,
    ]
    assert main(argv) == 0
    assert main(argv) == 0  # idempotent re-run

    async def verify_and_clean() -> None:
        engine = create_async_engine(migrated_database, poolclass=NullPool)
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as db:
                service = AuthService(db, LoggingEmailProvider())
                user, _token = await service.login("admin@cli.example", "cli-seeded-password")
                assert user.role == UserRole.admin
                assert user.organisation.slug == "cli-theatre"
                # Clean up (this test bypasses the truncating session fixture).
                await db.execute(delete(Organisation).where(Organisation.slug == "cli-theatre"))
                await db.commit()
        finally:
            await engine.dispose()

    asyncio.run(verify_and_clean())


def test_cli_requires_a_password_from_arg_or_env(
    migrated_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AUTOINSIGHT_SEED_PASSWORD", raising=False)
    argv = [
        "seed-org",
        "--name",
        "X",
        "--slug",
        "x-org",
        "--email",
        "x@example.org",
        "--user-name",
        "X",
        "--database-url",
        migrated_database,
    ]
    assert main(argv) == 2
