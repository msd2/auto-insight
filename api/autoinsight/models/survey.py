"""Insight pack templates (global catalogue) and per-org allocations."""

import uuid
from typing import Any

from sqlalchemy import CheckConstraint, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from autoinsight.models.base import Base, CreatedAtMixin, OrgOwned, UUIDPrimaryKeyMixin
from autoinsight.models.enums import AllocationStatus, SurveyFocus


class SurveyTemplate(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Catalogue entry. Global content, not tenant-owned — no org_id."""

    __tablename__ = "survey_templates"

    slug: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    focus: Mapped[SurveyFocus] = mapped_column(Enum(SurveyFocus, name="survey_focus"))
    description: Mapped[str | None]

    versions: Mapped[list["TemplateVersion"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", passive_deletes=True
    )


class TemplateVersion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable published pack version (packs are data — see CLAUDE.md)."""

    __tablename__ = "template_versions"
    __table_args__ = (UniqueConstraint("template_id", "version"),)

    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("survey_templates.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int]
    question_manifest: Mapped[dict[str, Any]]
    insight_spec: Mapped[dict[str, Any]]
    sample_dataset: Mapped[dict[str, Any]]
    # Reference to the survey created in the engine (Culture Counts), set by
    # SurveyEngine.ensure_survey().
    engine_survey_ref: Mapped[str | None]

    template: Mapped[SurveyTemplate] = relationship(back_populates="versions")


class Allocation(OrgOwned):
    __tablename__ = "allocations"
    # Doc: "event_id (or instance_id)" — exactly one target must be set.
    __table_args__ = (
        CheckConstraint(
            "(event_id IS NULL) != (instance_id IS NULL)",
            name="exactly_one_target",
        ),
    )

    template_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("template_versions.id", ondelete="RESTRICT"), index=True
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    instance_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("event_instances.id", ondelete="CASCADE"), index=True
    )
    send_delay_hours: Mapped[int] = mapped_column(default=18)
    reminder_enabled: Mapped[bool] = mapped_column(default=True)
    status: Mapped[AllocationStatus] = mapped_column(
        Enum(AllocationStatus, name="allocation_status"),
        default=AllocationStatus.scheduled,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
