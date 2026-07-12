"""Org-scoped customer repository."""

from sqlalchemy.orm import selectinload

from autoinsight.models import Customer
from autoinsight.repositories.base import OrgScopedRepository


class CustomerRepository(OrgScopedRepository[Customer]):
    model = Customer

    async def get_by_external_id(self, external_id: str) -> Customer | None:
        result = await self._session.execute(
            self._scoped()
            .where(Customer.external_id == external_id)
            .options(selectinload(Customer.tags))
        )
        return result.scalar_one_or_none()
