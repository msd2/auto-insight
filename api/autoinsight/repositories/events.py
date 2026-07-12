"""Org-scoped event repository, including event instances.

``event_instances`` has no ``org_id`` of its own — it is tenant-owned through
its parent event — so every instance query joins ``events`` and applies the
org filter there.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, select

from autoinsight.models import Event, EventInstance
from autoinsight.repositories.base import OrgScopedRepository


class EventRepository(OrgScopedRepository[Event]):
    model = Event

    async def get_by_external_id(self, external_id: str) -> Event | None:
        result = await self._session.execute(self._scoped().where(Event.external_id == external_id))
        return result.scalar_one_or_none()

    # -- instances (scoped through the parent event) --------------------------

    def _scoped_instances(self) -> Select[tuple[EventInstance]]:
        return (
            select(EventInstance)
            .join(Event, EventInstance.event_id == Event.id)
            .where(Event.org_id == self.context.org_id)
        )

    async def add_instance(self, instance: EventInstance) -> EventInstance:
        """Add an instance; its parent event must belong to this org."""
        await self._require_owned(Event, instance.event_id)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get_instance(self, instance_id: uuid.UUID) -> EventInstance | None:
        result = await self._session.execute(
            self._scoped_instances().where(EventInstance.id == instance_id)
        )
        return result.scalar_one_or_none()

    async def list_instances(self, event_id: uuid.UUID) -> Sequence[EventInstance]:
        result = await self._session.execute(
            self._scoped_instances()
            .where(EventInstance.event_id == event_id)
            .order_by(EventInstance.starts_at)
        )
        return result.scalars().all()

    async def update_instance(
        self, instance_id: uuid.UUID, values: dict[str, object]
    ) -> EventInstance | None:
        forbidden = {"id", "event_id"} & values.keys()
        if forbidden:
            raise ValueError(f"refusing to update protected fields: {sorted(forbidden)}")
        unknown = [key for key in values if not hasattr(EventInstance, key)]
        if unknown:
            raise ValueError(f"unknown fields for EventInstance: {sorted(unknown)}")
        instance = await self.get_instance(instance_id)
        if instance is None:
            return None
        for key, value in values.items():
            setattr(instance, key, value)
        await self._session.flush()
        return instance

    async def delete_instance(self, instance_id: uuid.UUID) -> bool:
        instance = await self.get_instance(instance_id)
        if instance is None:
            return False
        await self._session.delete(instance)
        await self._session.flush()
        return True
