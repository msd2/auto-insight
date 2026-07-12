"""Tenancy context — the capability object every scoped repository requires."""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class OrgContext:
    """A database session bound to one organisation.

    All tenant data access requires an ``OrgContext``; repositories apply its
    ``org_id`` to every query, so "forgot the org filter" is structurally hard
    (docs/02-architecture.md §Multi-tenancy). Endpoint handlers receive
    repositories via dependencies (see ``autoinsight.repositories.deps``) and
    never touch the session directly.
    """

    org_id: uuid.UUID
    session: AsyncSession
