"""Shared fixtures: a real Postgres test database with migrations applied.

The suite runs against the dev Postgres from docker-compose (port 5433) but
in a dedicated ``autoinsight_test`` database: created fresh per session,
migrated via Alembic (which itself proves the migration applies clean to an
empty database), and truncated between tests.
"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import httpx
import pytest
from alembic.config import Config
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from autoinsight.adapters.email import LoggingEmailProvider, get_email_provider
from autoinsight.auth.deps import AdminContextDep
from autoinsight.auth.passwords import hash_password
from autoinsight.db import get_session
from autoinsight.main import create_app
from autoinsight.models import Base, Organisation, User, UserRole
from autoinsight.repositories import OrganisationRepository, OrgContext, UserRepository
from autoinsight.repositories.deps import EventRepositoryDep

API_DIR = Path(__file__).resolve().parent.parent
PG_HOST = "localhost:5433"
PG_AUTH = "autoinsight:autoinsight"
ADMIN_DSN = f"postgresql://{PG_AUTH}@{PG_HOST}/postgres"
TEST_DB_NAME = "autoinsight_test"
TEST_DB_URL = f"postgresql+asyncpg://{PG_AUTH}@{PG_HOST}/{TEST_DB_NAME}"


def recreate_database(name: str) -> None:
    """Drop and recreate ``name`` so migrations always start from empty."""

    async def _run() -> None:
        conn = await asyncpg.connect(ADMIN_DSN)
        try:
            await conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
            await conn.execute(f'CREATE DATABASE "{name}"')
        finally:
            await conn.close()

    asyncio.run(_run())


def alembic_config(database_url: str) -> Config:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


@pytest.fixture(scope="session")
def migrated_database() -> str:
    """A fresh test database with the full migration chain applied."""
    recreate_database(TEST_DB_NAME)
    command.upgrade(alembic_config(TEST_DB_URL), "head")
    return TEST_DB_URL


@pytest.fixture
async def session(migrated_database: str) -> AsyncIterator[AsyncSession]:
    """A session on the migrated test DB; all tables truncated afterwards."""
    engine = create_async_engine(migrated_database, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as sess:
            yield sess
            await sess.rollback()
        async with engine.begin() as conn:
            tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
            await conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    finally:
        await engine.dispose()


async def _make_org(session: AsyncSession, name: str, slug: str) -> Organisation:
    return await OrganisationRepository(session).add(Organisation(name=name, slug=slug))


@pytest.fixture
async def org_a(session: AsyncSession) -> Organisation:
    return await _make_org(session, "Org A", "org-a")


@pytest.fixture
async def org_b(session: AsyncSession) -> Organisation:
    return await _make_org(session, "Org B", "org-b")


@pytest.fixture
def ctx_a(session: AsyncSession, org_a: Organisation) -> OrgContext:
    return OrgContext(org_id=org_a.id, session=session)


@pytest.fixture
def ctx_b(session: AsyncSession, org_b: Organisation) -> OrgContext:
    return OrgContext(org_id=org_b.id, session=session)


# --- auth fixtures ------------------------------------------------------------

# One shared test password, hashed once (argon2 is deliberately slow).
PASSWORD = "correct-horse-battery-staple"
PASSWORD_HASH = hash_password(PASSWORD)


async def make_user(
    ctx: OrgContext,
    email: str,
    role: UserRole = UserRole.member,
    name: str = "Test User",
) -> User:
    return await UserRepository(ctx).add(
        User(email=email, name=name, role=role, password_hash=PASSWORD_HASH)
    )


@pytest.fixture
async def admin_a(ctx_a: OrgContext) -> User:
    return await make_user(ctx_a, "admin@org-a.example", role=UserRole.admin, name="Admin A")


@pytest.fixture
async def member_a(ctx_a: OrgContext) -> User:
    return await make_user(ctx_a, "member@org-a.example", name="Member A")


@pytest.fixture
def email_provider() -> LoggingEmailProvider:
    """Recording provider; tests assert on ``.outbox``."""
    return LoggingEmailProvider()


# Test-only routes proving the auth dependencies end-to-end: the admin role
# gate, and the authed session-cookie → OrgContext → repository path.
_test_router = APIRouter(prefix="/_test")


@_test_router.get("/admin-only")
async def _admin_only(auth: AdminContextDep) -> dict[str, str]:
    return {"user": auth.user.email}


@_test_router.get("/events")
async def _list_events(events: EventRepositoryDep) -> list[str]:
    return [str(event.id) for event in await events.list()]


@pytest.fixture
async def client(
    session: AsyncSession, email_provider: LoggingEmailProvider
) -> AsyncIterator[httpx.AsyncClient]:
    """The real app over ASGI, sharing the test DB session, cookies enabled."""
    app = create_app()
    app.include_router(_test_router)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_email_provider] = lambda: email_provider
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
