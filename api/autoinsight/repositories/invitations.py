"""Org-scoped invitation repository."""

import uuid
from collections.abc import Sequence

from autoinsight.models import Allocation, Customer, Invitation
from autoinsight.repositories.base import OrgScopedRepository


class InvitationRepository(OrgScopedRepository[Invitation]):
    model = Invitation

    async def add(self, instance: Invitation) -> Invitation:
        """Persist an invitation after checking its FKs are this org's."""
        await self._require_owned(Allocation, instance.allocation_id)
        await self._require_owned(Customer, instance.customer_id)
        return await super().add(instance)

    async def get_by_token(self, token: uuid.UUID) -> Invitation | None:
        result = await self._session.execute(self._scoped().where(Invitation.token == token))
        return result.scalar_one_or_none()

    async def list_for_allocation(self, allocation_id: uuid.UUID) -> Sequence[Invitation]:
        result = await self._session.execute(
            self._scoped()
            .where(Invitation.allocation_id == allocation_id)
            .order_by(Invitation.created_at)
        )
        return result.scalars().all()
