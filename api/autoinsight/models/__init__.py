"""SQLAlchemy models for the Auto Insight schema.

Importing this package registers every table on ``Base.metadata`` (Alembic's
``target_metadata``). Table names, columns, and enums follow
docs/02-architecture.md §Data model.
"""

from autoinsight.models.base import Base, OrgOwned
from autoinsight.models.boxoffice import (
    Attendance,
    BoxOfficeConnection,
    Customer,
    CustomerTag,
    Event,
    EventInstance,
)
from autoinsight.models.enums import (
    AllocationStatus,
    BoxOfficeProviderType,
    ConnectionStatus,
    EmailEventType,
    InsightReportStatus,
    InvitationStatus,
    SuppressionReason,
    SurveyFocus,
    UserRole,
)
from autoinsight.models.insight import InsightReport, Response
from autoinsight.models.messaging import EmailEvent, Invitation, Suppression
from autoinsight.models.org import Organisation, User
from autoinsight.models.survey import Allocation, SurveyTemplate, TemplateVersion

__all__ = [
    "Allocation",
    "AllocationStatus",
    "Attendance",
    "Base",
    "BoxOfficeConnection",
    "BoxOfficeProviderType",
    "ConnectionStatus",
    "Customer",
    "CustomerTag",
    "EmailEvent",
    "EmailEventType",
    "Event",
    "EventInstance",
    "InsightReport",
    "InsightReportStatus",
    "Invitation",
    "InvitationStatus",
    "OrgOwned",
    "Organisation",
    "Response",
    "SurveyFocus",
    "SurveyTemplate",
    "Suppression",
    "SuppressionReason",
    "TemplateVersion",
    "User",
    "UserRole",
]
