"""Org-scoped repository base class.

Every query built here carries ``WHERE org_id = context.org_id``; every write
stamps the context's ``org_id``. Rows belonging to another organisation are
therefore invisible and immutable through a repository — reads return ``None``
or empty lists, mutations are no-ops reporting failure.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from autoinsight.models.base import OrgOwned
from autoinsight.repositories.context import OrgContext

#: Attributes that scoped ``update`` must never touch — changing them would
#: re-identify or re-home a row across tenants.
_PROTECTED_FIELDS = frozenset({"id", "org_id"})


class OrgScopedRepository[M: OrgOwned]:
    """Base repository for tenant-owned models (subclasses set ``model``)."""

    model: type[M]

    def __init__(self, context: OrgContext) -> None:
        self.context = context

    @property
    def _session(self) -> AsyncSession:
        return self.context.session

    def _scoped(self) -> Select[tuple[M]]:
        """A SELECT on ``model`` already filtered to this organisation.

        Every read path in subclasses must build on this (or join through a
        table that is itself scoped by it).
        """
        return select(self.model).where(self.model.org_id == self.context.org_id)

    async def add(self, instance: M) -> M:
        """Persist ``instance`` for this organisation.

        The context's ``org_id`` is stamped unconditionally, so a caller
        cannot smuggle a row into another tenant by pre-setting ``org_id``.
        """
        instance.org_id = self.context.org_id
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get(self, entity_id: uuid.UUID) -> M | None:
        result = await self._session.execute(self._scoped().where(self.model.id == entity_id))
        return result.scalar_one_or_none()

    async def list(self) -> Sequence[M]:
        result = await self._session.execute(self._scoped().order_by(self.model.created_at))
        return result.scalars().all()

    async def update(self, entity_id: uuid.UUID, values: dict[str, object]) -> M | None:
        """Update fields on this org's row; ``None`` if it isn't this org's."""
        forbidden = _PROTECTED_FIELDS & values.keys()
        if forbidden:
            raise ValueError(f"refusing to update protected fields: {sorted(forbidden)}")
        unknown = [key for key in values if not hasattr(self.model, key)]
        if unknown:
            raise ValueError(f"unknown fields for {self.model.__name__}: {sorted(unknown)}")
        instance = await self.get(entity_id)
        if instance is None:
            return None
        for key, value in values.items():
            setattr(instance, key, value)
        await self._session.flush()
        return instance

    async def delete(self, entity_id: uuid.UUID) -> bool:
        """Delete this org's row; ``False`` if it isn't this org's."""
        instance = await self.get(entity_id)
        if instance is None:
            return False
        await self._session.delete(instance)
        await self._session.flush()
        return True

    async def _require_owned[O: OrgOwned](self, model: type[O], entity_id: uuid.UUID) -> O:
        """Assert a referenced row belongs to this org (for FK targets)."""
        result = await self._session.execute(
            select(model).where(model.id == entity_id, model.org_id == self.context.org_id)
        )
        owned = result.scalar_one_or_none()
        if owned is None:
            raise LookupError(f"{model.__name__} {entity_id} does not exist in this organisation")
        return owned
