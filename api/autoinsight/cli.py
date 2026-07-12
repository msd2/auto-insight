"""Management CLI. No self-serve signup exists: orgs and users are seeded here.

Usage:

    uv run python -m autoinsight.cli seed-org \\
        --name "Demo Theatre" --slug demo-theatre \\
        --email admin@example.org --user-name "Demo Admin" \\
        --password 'a-strong-password'

The password may instead come from AUTOINSIGHT_SEED_PASSWORD. Re-running is
safe: an existing org (by slug) is reused, an existing user (by email within
the org) gets its name/role/password updated.
"""

import argparse
import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from autoinsight.auth.passwords import hash_password
from autoinsight.config import get_settings
from autoinsight.models import Organisation, User, UserRole
from autoinsight.repositories import OrganisationRepository, OrgContext, UserRepository


async def seed_org(
    db: AsyncSession,
    *,
    org_name: str,
    slug: str,
    email: str,
    user_name: str,
    password: str,
    role: UserRole = UserRole.admin,
) -> tuple[Organisation, User]:
    """Idempotently ensure an org and a user with working credentials."""
    orgs = OrganisationRepository(db)
    org = await orgs.get_by_slug(slug)
    if org is None:
        org = await orgs.add(Organisation(name=org_name, slug=slug))
    users = UserRepository(OrgContext(org_id=org.id, session=db))
    user = await users.get_by_email(email)
    password_hash = hash_password(password)
    if user is None:
        user = await users.add(
            User(email=email, name=user_name, role=role, password_hash=password_hash)
        )
    else:
        await users.update(
            user.id, {"name": user_name, "role": role, "password_hash": password_hash}
        )
    await db.commit()
    return org, user


async def _run_seed_org(args: argparse.Namespace) -> int:
    database_url = args.database_url or get_settings().database_url
    password = args.password or os.environ.get("AUTOINSIGHT_SEED_PASSWORD")
    if not password:
        print("error: provide --password or AUTOINSIGHT_SEED_PASSWORD", file=sys.stderr)
        return 2
    engine = create_async_engine(database_url)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as db:
            org, user = await seed_org(
                db,
                org_name=args.name,
                slug=args.slug,
                email=args.email,
                user_name=args.user_name,
                password=password,
                role=UserRole(args.role),
            )
        print(f"org {org.slug} ({org.id}): user {user.email} role={user.role.value} ready")
        return 0
    finally:
        await engine.dispose()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m autoinsight.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed = subparsers.add_parser("seed-org", help="Create/refresh an org and one of its users")
    seed.add_argument("--name", required=True, help="Organisation display name")
    seed.add_argument("--slug", required=True, help="Organisation slug (unique)")
    seed.add_argument("--email", required=True, help="User email (unique within the org)")
    seed.add_argument("--user-name", required=True, help="User display name")
    seed.add_argument(
        "--password",
        default=None,
        help="User password (or set AUTOINSIGHT_SEED_PASSWORD)",
    )
    seed.add_argument(
        "--role",
        choices=[role.value for role in UserRole],
        default=UserRole.admin.value,
        help="Role for the user (default: admin)",
    )
    seed.add_argument(
        "--database-url",
        default=None,
        help="Override DATABASE_URL (defaults to application settings)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "seed-org":
        return asyncio.run(_run_seed_org(args))
    raise AssertionError("unreachable: subcommand is required")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
