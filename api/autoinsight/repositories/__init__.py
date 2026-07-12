"""OrgContext-scoped repository layer.

All tenant data access goes through these repositories; each requires an
``OrgContext`` and scopes every query to it. ``OrganisationRepository`` is
the one deliberate exception (unscoped, admin/bootstrap only).
"""

from autoinsight.repositories.allocations import AllocationRepository
from autoinsight.repositories.base import OrgScopedRepository
from autoinsight.repositories.context import OrgContext
from autoinsight.repositories.customers import CustomerRepository
from autoinsight.repositories.events import EventRepository
from autoinsight.repositories.invitations import InvitationRepository
from autoinsight.repositories.organisations import OrganisationRepository
from autoinsight.repositories.users import UserRepository

__all__ = [
    "AllocationRepository",
    "CustomerRepository",
    "EventRepository",
    "InvitationRepository",
    "OrgContext",
    "OrgScopedRepository",
    "OrganisationRepository",
    "UserRepository",
]
