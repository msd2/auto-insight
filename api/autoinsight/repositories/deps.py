"""FastAPI dependencies wiring sessions → OrgContext → repositories.

Endpoint handlers depend on repositories (``UserRepositoryDep`` etc.), never
on ``AsyncSession`` directly — the session only exists behind ``OrgContext``.

``get_current_org_id`` is the auth seam: WP 0.3 replaces its body (or
overrides the dependency) to resolve the organisation from the authenticated
session cookie. Until then any endpoint requiring tenant data returns 401.
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from autoinsight.db import get_session
from autoinsight.repositories.allocations import AllocationRepository
from autoinsight.repositories.context import OrgContext
from autoinsight.repositories.customers import CustomerRepository
from autoinsight.repositories.events import EventRepository
from autoinsight.repositories.invitations import InvitationRepository
from autoinsight.repositories.organisations import OrganisationRepository
from autoinsight.repositories.users import UserRepository

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_org_id() -> uuid.UUID:
    """Resolve the caller's organisation. Implemented by auth in WP 0.3."""
    raise HTTPException(status_code=401, detail="Not authenticated")


async def get_org_context(
    org_id: Annotated[uuid.UUID, Depends(get_current_org_id)],
    session: SessionDep,
) -> OrgContext:
    return OrgContext(org_id=org_id, session=session)


OrgContextDep = Annotated[OrgContext, Depends(get_org_context)]


def get_user_repository(context: OrgContextDep) -> UserRepository:
    return UserRepository(context)


def get_event_repository(context: OrgContextDep) -> EventRepository:
    return EventRepository(context)


def get_customer_repository(context: OrgContextDep) -> CustomerRepository:
    return CustomerRepository(context)


def get_allocation_repository(context: OrgContextDep) -> AllocationRepository:
    return AllocationRepository(context)


def get_invitation_repository(context: OrgContextDep) -> InvitationRepository:
    return InvitationRepository(context)


def get_organisation_repository(session: SessionDep) -> OrganisationRepository:
    """Unscoped — for admin/seeding endpoints only (role-gated in WP 0.3)."""
    return OrganisationRepository(session)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
EventRepositoryDep = Annotated[EventRepository, Depends(get_event_repository)]
CustomerRepositoryDep = Annotated[CustomerRepository, Depends(get_customer_repository)]
AllocationRepositoryDep = Annotated[AllocationRepository, Depends(get_allocation_repository)]
InvitationRepositoryDep = Annotated[InvitationRepository, Depends(get_invitation_repository)]
OrganisationRepositoryDep = Annotated[OrganisationRepository, Depends(get_organisation_repository)]
