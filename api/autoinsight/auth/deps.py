"""FastAPI dependencies for authentication and role gates."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from autoinsight.adapters.email import EmailProvider, get_email_provider
from autoinsight.auth.service import AuthService
from autoinsight.config import get_settings
from autoinsight.db import get_session
from autoinsight.models import AuthSession, Organisation, User, UserRole


def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_session)],
    email_provider: Annotated[EmailProvider, Depends(get_email_provider)],
) -> AuthService:
    return AuthService(db, email_provider)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@dataclass(frozen=True, slots=True)
class AuthContext:
    """The authenticated caller: session row + user (+ its organisation)."""

    auth_session: AuthSession
    user: User

    @property
    def organisation(self) -> Organisation:
        return self.user.organisation


def _unauthenticated() -> HTTPException:
    return HTTPException(status_code=401, detail="Not authenticated")


async def get_auth_context(request: Request, service: AuthServiceDep) -> AuthContext:
    """Resolve the session cookie to an AuthContext, or 401."""
    raw_token = request.cookies.get(get_settings().session_cookie_name)
    if not raw_token:
        raise _unauthenticated()
    auth_session = await service.get_session(raw_token)
    if auth_session is None:
        raise _unauthenticated()
    return AuthContext(auth_session=auth_session, user=auth_session.user)


AuthContextDep = Annotated[AuthContext, Depends(get_auth_context)]


async def require_admin(auth: AuthContextDep) -> AuthContext:
    """Role gate: 403 unless the authenticated user is an org admin."""
    if auth.user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin role required")
    return auth


AdminContextDep = Annotated[AuthContext, Depends(require_admin)]
