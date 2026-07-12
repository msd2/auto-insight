"""Auth storage: server-side login sessions and password-reset tokens.

Both tables hang off ``users`` (which carries ``org_id``), like customer_tags
hang off customers: a user row is already org-scoped, so a session pins both
the user and the organisation it is acting in. Only opaque token *hashes* are
stored — the raw values live in the cookie / reset email alone.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from autoinsight.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from autoinsight.models.org import User


class AuthSession(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]

    user: Mapped[User] = relationship()


class PasswordResetToken(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]

    user: Mapped[User] = relationship()
