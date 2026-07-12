"""Auth endpoints: login, logout, me, password reset.

No self-serve signup — orgs and users are seeded via the CLI
(``python -m autoinsight.cli seed-org``).
"""

import uuid

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from autoinsight.auth.deps import AuthContextDep, AuthServiceDep
from autoinsight.auth.service import AmbiguousOrganisationError, InvalidCredentialsError
from autoinsight.config import get_settings
from autoinsight.models import User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str
    # Required only when the email exists in more than one organisation
    # (internal staff accounts).
    org_slug: str | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: UserRole


class OrgOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str


class MeResponse(BaseModel):
    user: UserOut
    org: OrgOut


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


def _me_payload(user: User) -> MeResponse:
    org = user.organisation
    return MeResponse(
        user=UserOut(id=user.id, email=user.email, name=user.name, role=user.role),
        org=OrgOut(id=org.id, name=org.name, slug=org.slug),
    )


@router.post("/login")
async def login(body: LoginRequest, response: Response, service: AuthServiceDep) -> MeResponse:
    try:
        user, raw_token = await service.login(body.email, body.password, body.org_slug)
    except AmbiguousOrganisationError as exc:
        raise HTTPException(
            status_code=400,
            detail="This email belongs to multiple organisations; specify org_slug.",
        ) from exc
    except InvalidCredentialsError as exc:
        # One message for unknown email and wrong password alike.
        raise HTTPException(status_code=401, detail="Invalid email or password") from exc
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
    )
    return _me_payload(user)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, service: AuthServiceDep) -> None:
    """Revoke the current session (if any) and clear the cookie. Idempotent."""
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    if raw_token:
        await service.logout(raw_token)
    response.delete_cookie(key=settings.session_cookie_name, path="/")


@router.get("/me")
async def me(auth: AuthContextDep) -> MeResponse:
    return _me_payload(auth.user)


@router.post("/password-reset/request", status_code=202)
async def request_password_reset(body: PasswordResetRequest, service: AuthServiceDep) -> None:
    """Always 202 — the response must not reveal whether the email exists."""
    await service.request_password_reset(body.email)


@router.post("/password-reset/confirm", status_code=204)
async def confirm_password_reset(body: PasswordResetConfirm, service: AuthServiceDep) -> None:
    if not await service.reset_password(body.token, body.new_password):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
