"""Integration adapters (docs/02-architecture.md §Integration adapters).

External systems are only ever touched through these interfaces:
``BoxOfficeProvider`` (Phase 1), ``SurveyEngine`` (Phase 2), and
``EmailProvider`` (interface here; real Postmark implementation lands in
Phase 3).
"""

from autoinsight.adapters.email import EmailMessage, EmailProvider, LoggingEmailProvider

__all__ = ["EmailMessage", "EmailProvider", "LoggingEmailProvider"]
