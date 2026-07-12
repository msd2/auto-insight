"""Declarative base and shared mixins for all Auto Insight models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, MetaData, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Deterministic constraint names so Alembic migrations are stable and reviewable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {
        # All timestamps are timezone-aware (timestamptz).
        datetime: DateTime(timezone=True),
        dict[str, Any]: JSONB,
    }


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class OrgOwned(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Abstract base for every tenant-owned table.

    Carries the non-null ``org_id`` FK required by the multi-tenancy model
    (docs/02-architecture.md §Multi-tenancy). The repository layer relies on
    this attribute to scope every query to an ``OrgContext``.
    """

    __abstract__ = True

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), index=True
    )
