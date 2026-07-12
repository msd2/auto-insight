"""Box office connection and the synced box-office data (events, audiences)."""

import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from autoinsight.models.base import Base, CreatedAtMixin, OrgOwned, UUIDPrimaryKeyMixin
from autoinsight.models.enums import BoxOfficeProviderType, ConnectionStatus


class BoxOfficeConnection(OrgOwned):
    __tablename__ = "box_office_connections"

    provider: Mapped[BoxOfficeProviderType] = mapped_column(
        Enum(BoxOfficeProviderType, name="box_office_provider")
    )
    # Encrypted blob (KMS / libsodium sealed box); encryption happens in the
    # adapter layer — never store plaintext credentials here.
    credentials: Mapped[bytes]
    status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus, name="box_office_connection_status"),
        default=ConnectionStatus.pending,
    )
    last_synced_at: Mapped[datetime | None]


class Event(OrgOwned):
    __tablename__ = "events"
    # Sync upsert key (docs/02-architecture.md §Spektrix sync).
    __table_args__ = (UniqueConstraint("org_id", "external_id"),)

    external_id: Mapped[str]
    name: Mapped[str]
    description: Mapped[str | None]
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)

    instances: Mapped[list["EventInstance"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", passive_deletes=True
    )


class EventInstance(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A single performance. Tenant-owned via its event (no direct org_id)."""

    __tablename__ = "event_instances"
    __table_args__ = (UniqueConstraint("event_id", "external_id"),)

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str]
    starts_at: Mapped[datetime]
    venue_name: Mapped[str | None]
    capacity: Mapped[int | None]

    event: Mapped[Event] = relationship(back_populates="instances")


class Customer(OrgOwned):
    __tablename__ = "customers"
    # Sync upsert key (docs/02-architecture.md §Spektrix sync).
    __table_args__ = (UniqueConstraint("org_id", "external_id"),)

    external_id: Mapped[str]
    email: Mapped[str | None]
    first_name: Mapped[str | None]
    # From box office contact preferences; also mirrored into suppressions.
    opted_out_at: Mapped[datetime | None]

    tags: Mapped[list["CustomerTag"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan", passive_deletes=True
    )


class CustomerTag(Base):
    """Tag rows (donor, member, regular…). Tenant-owned via the customer."""

    __tablename__ = "customer_tags"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True
    )
    tag: Mapped[str] = mapped_column(primary_key=True)

    customer: Mapped[Customer] = relationship(back_populates="tags")


class Attendance(OrgOwned):
    __tablename__ = "attendances"
    # One row per customer per instance keeps the sync upsert idempotent.
    __table_args__ = (UniqueConstraint("instance_id", "customer_id"),)

    instance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_instances.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    tickets: Mapped[int]
    booked_at: Mapped[datetime | None]
