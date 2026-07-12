"""Org-scoped user repository."""

from autoinsight.models import User
from autoinsight.repositories.base import OrgScopedRepository


class UserRepository(OrgScopedRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(self._scoped().where(User.email == email))
        return result.scalar_one_or_none()
