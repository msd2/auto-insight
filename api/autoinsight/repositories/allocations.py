"""Org-scoped allocation repository."""

import uuid
from collections.abc import Sequence

from autoinsight.models import Allocation, Event, EventInstance
from autoinsight.repositories.base import OrgScopedRepository


class AllocationRepository(OrgScopedRepository[Allocation]):
    model = Allocation

    async def add(self, instance: Allocation) -> Allocation:
        """Persist an allocation after checking its target is this org's.

        The FK alone would happily point at another organisation's event, so
        ownership of the target (event or instance) is verified here.
        """
        if instance.event_id is not None:
            await self._require_owned(Event, instance.event_id)
        if instance.instance_id is not None:
            owned_instance = await self._session.get(EventInstance, instance.instance_id)
            if owned_instance is None:
                raise LookupError(f"EventInstance {instance.instance_id} does not exist")
            await self._require_owned(Event, owned_instance.event_id)
        return await super().add(instance)

    async def list_for_event(self, event_id: uuid.UUID) -> Sequence[Allocation]:
        result = await self._session.execute(
            self._scoped().where(Allocation.event_id == event_id).order_by(Allocation.created_at)
        )
        return result.scalars().all()
