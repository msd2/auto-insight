"""Organisations and their users."""

from typing import Any

from sqlalchemy import Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from autoinsight.models.base import Base, CreatedAtMixin, OrgOwned, UUIDPrimaryKeyMixin
from autoinsight.models.enums import UserRole


class Organisation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "organisations"

    name: Mapped[str]
    slug: Mapped[str] = mapped_column(unique=True)
    sender_domain: Mapped[str | None]
    settings: Mapped[dict[str, Any]] = mapped_column(default=dict)


class User(OrgOwned):
    __tablename__ = "users"
    # Email is unique per org, not globally: internal staff accounts exist in
    # several orgs (roadmap WP 0.3 "org switcher for internal staff accounts").
    __table_args__ = (UniqueConstraint("org_id", "email"),)

    email: Mapped[str]
    name: Mapped[str]
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"))
    # Auth fields (populated by WP 0.3; nullable so seeding can precede auth).
    password_hash: Mapped[str | None]
