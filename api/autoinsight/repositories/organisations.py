"""Organisation repository — deliberately unscoped (admin/bootstrap only).

Organisations are the tenancy roots, so this is the one repository that takes
a bare session instead of an ``OrgContext``. It must only be used by admin
and seeding code paths, never handed to tenant-facing endpoints.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoinsight.models import Organisation


class OrganisationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, organisation: Organisation) -> Organisation:
        self._session.add(organisation)
        await self._session.flush()
        return organisation

    async def get(self, organisation_id: uuid.UUID) -> Organisation | None:
        return await self._session.get(Organisation, organisation_id)

    async def get_by_slug(self, slug: str) -> Organisation | None:
        result = await self._session.execute(select(Organisation).where(Organisation.slug == slug))
        return result.scalar_one_or_none()

    async def list(self) -> Sequence[Organisation]:
        result = await self._session.execute(select(Organisation).order_by(Organisation.name))
        return result.scalars().all()
