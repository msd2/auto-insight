"""Auth service: the only code that reads/writes auth tables.

Endpoint handlers depend on ``AuthService`` (see ``auth.deps``), never on a
raw session — the same structural rule the repository layer enforces for
tenant data. Mutating methods commit: auth state changes (login, logout,
password reset) are their own transaction.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from autoinsight.adapters.email import EmailMessage, EmailProvider
from autoinsight.auth.passwords import hash_password, verify_password
from autoinsight.config import get_settings
from autoinsight.models import AuthSession, Organisation, PasswordResetToken, User

RESET_EMAIL_SUBJECT = "Reset your Auto Insight password"
# Operational (not research) email; still a locked template in the repo.
RESET_EMAIL_BODY = """\
Hello {first_name},

Someone requested a password reset for your Auto Insight account with
{org_name}. If this was you, set a new password here (link valid for
{ttl_minutes} minutes, single use):

{web_base_url}/reset-password?token={token}

If you did not request this, you can safely ignore this email.
"""


class InvalidCredentialsError(Exception):
    """Unknown email, wrong password, or no password set — never say which."""


class AmbiguousOrganisationError(Exception):
    """The email exists in more than one organisation; org_slug is required."""


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _new_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, _hash_token(raw)


def _now() -> datetime:
    return datetime.now(UTC)


class AuthService:
    def __init__(self, db: AsyncSession, email_provider: EmailProvider) -> None:
        self._db = db
        self._email_provider = email_provider

    # -- credentials -----------------------------------------------------------

    async def authenticate(self, email: str, password: str, org_slug: str | None = None) -> User:
        """Verify credentials; raise instead of returning ``None`` so callers

        cannot forget to check. Emails are per-org rows: if the same email
        exists in several orgs, the caller must pass ``org_slug``.
        """
        stmt = (
            select(User)
            .join(Organisation, User.org_id == Organisation.id)
            .where(User.email == email)
            .options(joinedload(User.organisation))
        )
        if org_slug is not None:
            stmt = stmt.where(Organisation.slug == org_slug)
        users = (await self._db.execute(stmt)).scalars().all()
        if len(users) > 1:
            raise AmbiguousOrganisationError(email)
        if not users:
            # Burn comparable time so unknown emails aren't distinguishable.
            verify_password(hash_password("timing-equalizer"), password)
            raise InvalidCredentialsError
        user = users[0]
        if user.password_hash is None or not verify_password(user.password_hash, password):
            raise InvalidCredentialsError
        return user

    # -- sessions --------------------------------------------------------------

    async def login(
        self, email: str, password: str, org_slug: str | None = None
    ) -> tuple[User, str]:
        """Authenticate and open a session; returns the raw cookie token."""
        user = await self.authenticate(email, password, org_slug)
        raw, token_hash = _new_token()
        expires_at = _now() + timedelta(hours=get_settings().session_ttl_hours)
        self._db.add(AuthSession(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
        await self._db.commit()
        return user, raw

    async def get_session(self, raw_token: str) -> AuthSession | None:
        """The valid (unexpired, unrevoked) session for a cookie token,

        with its user and organisation loaded — or ``None``.
        """
        stmt = (
            select(AuthSession)
            .where(
                AuthSession.token_hash == _hash_token(raw_token),
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > _now(),
            )
            .options(joinedload(AuthSession.user).joinedload(User.organisation))
        )
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def logout(self, raw_token: str) -> None:
        """Revoke the session for this token. Idempotent."""
        auth_session = await self.get_session(raw_token)
        if auth_session is not None:
            auth_session.revoked_at = _now()
            await self._db.commit()

    async def _revoke_all_sessions(self, user_id: uuid.UUID) -> None:
        stmt = select(AuthSession).where(
            AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)
        )
        for auth_session in (await self._db.execute(stmt)).scalars():
            auth_session.revoked_at = _now()

    # -- password reset ---------------------------------------------------------

    async def request_password_reset(self, email: str) -> None:
        """Create reset token(s) and send email(s) for every org this email

        belongs to. Deliberately silent when the email is unknown so the
        endpoint's response never leaks account existence.
        """
        settings = get_settings()
        stmt = select(User).where(User.email == email).options(joinedload(User.organisation))
        users = (await self._db.execute(stmt)).scalars().all()
        for user in users:
            raw, token_hash = _new_token()
            self._db.add(
                PasswordResetToken(
                    user_id=user.id,
                    token_hash=token_hash,
                    expires_at=_now() + timedelta(minutes=settings.password_reset_ttl_minutes),
                )
            )
            await self._email_provider.send(
                EmailMessage(
                    to=user.email,
                    subject=RESET_EMAIL_SUBJECT,
                    text_body=RESET_EMAIL_BODY.format(
                        first_name=user.name,
                        org_name=user.organisation.name,
                        ttl_minutes=settings.password_reset_ttl_minutes,
                        web_base_url=settings.web_base_url,
                        token=raw,
                    ),
                )
            )
        if users:
            await self._db.commit()

    async def reset_password(self, raw_token: str, new_password: str) -> bool:
        """Set a new password for a valid, unused, unexpired token.

        Marks the token used and revokes all of the user's sessions.
        Returns ``False`` for invalid/expired/used tokens.
        """
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == _hash_token(raw_token),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > _now(),
        )
        token = (await self._db.execute(stmt)).scalar_one_or_none()
        if token is None:
            return False
        user = await self._db.get(User, token.user_id)
        if user is None:  # pragma: no cover — FK guarantees existence
            return False
        user.password_hash = hash_password(new_password)
        token.used_at = _now()
        await self._revoke_all_sessions(user.id)
        await self._db.commit()
        return True
