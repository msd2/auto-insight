"""Enumerations from docs/02-architecture.md §Data model.

Members are lowercase so the stored value equals the member name; each maps to
a native Postgres enum type (type name given at the column definition).
"""

from enum import StrEnum


class UserRole(StrEnum):
    member = "member"
    admin = "admin"


class BoxOfficeProviderType(StrEnum):
    spektrix = "spektrix"


class ConnectionStatus(StrEnum):
    """Not enumerated in the architecture doc; values cover the sync flow

    (docs/02-architecture.md §Key flows: heartbeat + error state).
    """

    pending = "pending"
    active = "active"
    error = "error"
    disabled = "disabled"


class SurveyFocus(StrEnum):
    quality = "quality"
    impact = "impact"
    feedback = "feedback"
    profile = "profile"


class AllocationStatus(StrEnum):
    """Statuses from the roadmap's allocations dashboard (WP 2.4) plus

    ``cancelled`` (WP 2.3 allows cancel before first send).
    """

    scheduled = "scheduled"
    sending = "sending"
    collecting = "collecting"
    complete = "complete"
    cancelled = "cancelled"


class InvitationStatus(StrEnum):
    pending = "pending"
    sent = "sent"
    reminded = "reminded"
    responded = "responded"
    bounced = "bounced"
    suppressed = "suppressed"
    failed = "failed"


class EmailEventType(StrEnum):
    delivery = "delivery"
    bounce = "bounce"
    complaint = "complaint"
    open = "open"


class SuppressionReason(StrEnum):
    unsubscribe = "unsubscribe"
    bounce = "bounce"
    complaint = "complaint"
    box_office_opt_out = "box_office_opt_out"


class InsightReportStatus(StrEnum):
    """Not enumerated in the architecture doc; values cover the insight-job

    lifecycle (docs/02-architecture.md §Response ingestion & insight).
    """

    pending = "pending"
    generating = "generating"
    ready = "ready"
    failed = "failed"
