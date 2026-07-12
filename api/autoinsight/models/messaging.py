"""Invitations, email delivery events, and the suppression list."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from autoinsight.models.base import Base, CreatedAtMixin, OrgOwned, UUIDPrimaryKeyMixin
from autoinsight.models.enums import EmailEventType, InvitationStatus, SuppressionReason


class Invitation(OrgOwned):
    __tablename__ = "invitations"

    allocation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("allocations.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    # The only identifier that ever leaves our system toward the survey engine.
    token: Mapped[uuid.UUID] = mapped_column(unique=True, default=uuid.uuid4)
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus, name="invitation_status"),
        default=InvitationStatus.pending,
    )
    sent_at: Mapped[datetime | None]
    responded_at: Mapped[datetime | None]


class EmailEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Normalised provider webhook event. Tenant-owned via the invitation."""

    __tablename__ = "email_events"

    invitation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invitations.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[EmailEventType] = mapped_column(Enum(EmailEventType, name="email_event_type"))
    provider_message_id: Mapped[str | None]
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    occurred_at: Mapped[datetime]


class Suppression(OrgOwned):
    __tablename__ = "suppressions"
    # Eligibility checks look up by (org_id, email_hash); rows are kept even
    # after a customer row is deleted, so the hash — not an FK — is the key.
    __table_args__ = (Index("ix_suppressions_org_id_email_hash", "org_id", "email_hash"),)

    email_hash: Mapped[str]
    reason: Mapped[SuppressionReason] = mapped_column(
        Enum(SuppressionReason, name="suppression_reason")
    )
