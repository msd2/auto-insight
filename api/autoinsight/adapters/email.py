"""EmailProvider adapter interface.

Per the architecture: ``send(message) -> provider_message_id``. The first real
implementation is Postmark (Phase 3, WP 3.2); until then the app uses
``LoggingEmailProvider``, which records and logs instead of sending. No
email-provider-specific code may exist outside this package.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: str
    subject: str
    text_body: str


class EmailProvider(Protocol):
    async def send(self, message: EmailMessage) -> str:
        """Send ``message``; return the provider's message id."""
        ...


class LoggingEmailProvider:
    """Stub provider for development and tests: logs, never sends.

    Sent messages are kept on ``outbox`` so tests can assert on them.
    """

    def __init__(self) -> None:
        self.outbox: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> str:
        self.outbox.append(message)
        logger.info(
            "email to=%s subject=%r (not sent: logging provider)", message.to, message.subject
        )
        return f"logged-{uuid.uuid4()}"


_default_provider = LoggingEmailProvider()


def get_email_provider() -> EmailProvider:
    """FastAPI dependency for the configured email provider (stub for now)."""
    return _default_provider
