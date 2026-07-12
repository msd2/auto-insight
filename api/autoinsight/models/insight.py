"""Ingested survey responses and generated insight reports."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from autoinsight.models.base import OrgOwned
from autoinsight.models.enums import InsightReportStatus


class Response(OrgOwned):
    __tablename__ = "responses"

    # One response per invitation: the token is single-use by design.
    invitation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invitations.id", ondelete="CASCADE"), unique=True
    )
    engine_response_ref: Mapped[str | None]
    answers: Mapped[dict[str, Any]]
    submitted_at: Mapped[datetime]


class InsightReport(OrgOwned):
    __tablename__ = "insight_reports"

    allocation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("allocations.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[InsightReportStatus] = mapped_column(
        Enum(InsightReportStatus, name="insight_report_status"),
        default=InsightReportStatus.pending,
    )
    charts_data: Mapped[dict[str, Any] | None]
    narrative: Mapped[dict[str, Any] | None]
    generated_at: Mapped[datetime | None]
