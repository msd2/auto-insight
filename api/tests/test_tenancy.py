"""Cross-org access is impossible through the repository layer.

Org B's context must not be able to read (get-by-id, list) or mutate
(update, delete) org A's rows — including rows owned indirectly via a parent
(event instances) and rows referenced by FK (allocation targets, invitation
customers).
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from autoinsight.models import (
    Allocation,
    Customer,
    Event,
    EventInstance,
    Invitation,
    SurveyTemplate,
    TemplateVersion,
    User,
    UserRole,
)
from autoinsight.repositories import (
    AllocationRepository,
    CustomerRepository,
    EventRepository,
    InvitationRepository,
    OrgContext,
    UserRepository,
)

# --- seeding helpers ---------------------------------------------------------


async def make_event(ctx: OrgContext, external_id: str = "ev-1") -> Event:
    return await EventRepository(ctx).add(Event(external_id=external_id, name="A Show"))


async def make_instance(ctx: OrgContext, event: Event) -> EventInstance:
    return await EventRepository(ctx).add_instance(
        EventInstance(
            event_id=event.id,
            external_id=f"{event.external_id}-i1",
            starts_at=datetime(2026, 9, 1, 19, 30, tzinfo=UTC),
        )
    )


async def make_customer(ctx: OrgContext, external_id: str = "cust-1") -> Customer:
    return await CustomerRepository(ctx).add(
        Customer(external_id=external_id, email="a@example.org", first_name="Ada")
    )


async def make_user(ctx: OrgContext, email: str = "user@example.org") -> User:
    return await UserRepository(ctx).add(User(email=email, name="Test User", role=UserRole.member))


async def make_template_version(session: AsyncSession) -> TemplateVersion:
    """Catalogue rows are global (no org); seed them directly."""
    template = SurveyTemplate(slug=f"pack-{uuid.uuid4().hex[:8]}", name="Pack", focus="quality")
    session.add(template)
    await session.flush()
    version = TemplateVersion(
        template_id=template.id,
        version=1,
        question_manifest={},
        insight_spec={},
        sample_dataset={},
    )
    session.add(version)
    await session.flush()
    return version


async def make_allocation(ctx: OrgContext, event: Event) -> Allocation:
    version = await make_template_version(ctx.session)
    return await AllocationRepository(ctx).add(
        Allocation(template_version_id=version.id, event_id=event.id)
    )


async def make_invitation(
    ctx: OrgContext, allocation: Allocation, customer: Customer
) -> Invitation:
    return await InvitationRepository(ctx).add(
        Invitation(allocation_id=allocation.id, customer_id=customer.id)
    )


# --- get-by-id ---------------------------------------------------------------


async def test_get_by_id_is_org_scoped(ctx_a: OrgContext, ctx_b: OrgContext) -> None:
    event = await make_event(ctx_a)
    customer = await make_customer(ctx_a)
    user = await make_user(ctx_a)
    allocation = await make_allocation(ctx_a, event)
    invitation = await make_invitation(ctx_a, allocation, customer)

    assert await EventRepository(ctx_a).get(event.id) is event
    assert await EventRepository(ctx_b).get(event.id) is None
    assert await CustomerRepository(ctx_b).get(customer.id) is None
    assert await UserRepository(ctx_b).get(user.id) is None
    assert await AllocationRepository(ctx_b).get(allocation.id) is None
    assert await InvitationRepository(ctx_b).get(invitation.id) is None


async def test_lookup_helpers_are_org_scoped(ctx_a: OrgContext, ctx_b: OrgContext) -> None:
    event = await make_event(ctx_a)
    customer = await make_customer(ctx_a)
    user = await make_user(ctx_a)
    allocation = await make_allocation(ctx_a, event)
    invitation = await make_invitation(ctx_a, allocation, customer)

    assert await EventRepository(ctx_b).get_by_external_id(event.external_id) is None
    assert await CustomerRepository(ctx_b).get_by_external_id(customer.external_id) is None
    assert await UserRepository(ctx_b).get_by_email(user.email) is None
    assert await InvitationRepository(ctx_b).get_by_token(invitation.token) is None
    assert await InvitationRepository(ctx_a).get_by_token(invitation.token) is invitation


# --- list --------------------------------------------------------------------


async def test_list_is_org_scoped(ctx_a: OrgContext, ctx_b: OrgContext) -> None:
    event_a = await make_event(ctx_a, "ev-a")
    event_b = await make_event(ctx_b, "ev-b")

    assert [e.id for e in await EventRepository(ctx_a).list()] == [event_a.id]
    assert [e.id for e in await EventRepository(ctx_b).list()] == [event_b.id]

    allocation_a = await make_allocation(ctx_a, event_a)
    customer_a = await make_customer(ctx_a)
    await make_invitation(ctx_a, allocation_a, customer_a)

    assert await AllocationRepository(ctx_b).list() == []
    assert await AllocationRepository(ctx_b).list_for_event(event_a.id) == []
    assert await InvitationRepository(ctx_b).list_for_allocation(allocation_a.id) == []
    assert await CustomerRepository(ctx_b).list() == []
    assert len(await InvitationRepository(ctx_a).list_for_allocation(allocation_a.id)) == 1


# --- update ------------------------------------------------------------------


async def test_update_cross_org_is_a_refused_noop(ctx_a: OrgContext, ctx_b: OrgContext) -> None:
    event = await make_event(ctx_a)
    customer = await make_customer(ctx_a)

    assert await EventRepository(ctx_b).update(event.id, {"name": "Hijacked"}) is None
    assert await CustomerRepository(ctx_b).update(customer.id, {"first_name": "Mallory"}) is None
    await ctx_a.session.flush()

    fresh_event = await EventRepository(ctx_a).get(event.id)
    fresh_customer = await CustomerRepository(ctx_a).get(customer.id)
    assert fresh_event is not None and fresh_event.name == "A Show"
    assert fresh_customer is not None and fresh_customer.first_name == "Ada"


async def test_update_cannot_move_a_row_between_orgs(ctx_a: OrgContext, ctx_b: OrgContext) -> None:
    event = await make_event(ctx_a)
    with pytest.raises(ValueError, match="protected fields"):
        await EventRepository(ctx_a).update(event.id, {"org_id": ctx_b.org_id})
    with pytest.raises(ValueError, match="unknown fields"):
        await EventRepository(ctx_a).update(event.id, {"nonexistent": 1})


# --- delete ------------------------------------------------------------------


async def test_delete_cross_org_is_a_refused_noop(ctx_a: OrgContext, ctx_b: OrgContext) -> None:
    event = await make_event(ctx_a)
    customer = await make_customer(ctx_a)

    assert await EventRepository(ctx_b).delete(event.id) is False
    assert await CustomerRepository(ctx_b).delete(customer.id) is False
    assert await EventRepository(ctx_a).get(event.id) is not None
    assert await CustomerRepository(ctx_a).get(customer.id) is not None

    assert await EventRepository(ctx_a).delete(event.id) is True
    assert await EventRepository(ctx_a).get(event.id) is None


# --- create ------------------------------------------------------------------


async def test_add_stamps_the_context_org_even_if_preset(
    ctx_a: OrgContext, ctx_b: OrgContext
) -> None:
    """A caller cannot smuggle a row into another org by pre-setting org_id."""
    event = await EventRepository(ctx_a).add(
        Event(org_id=ctx_b.org_id, external_id="ev-smuggled", name="Smuggled")
    )
    assert event.org_id == ctx_a.org_id
    assert await EventRepository(ctx_b).get(event.id) is None


# --- event instances (owned via the parent event, no org_id column) ----------


async def test_event_instances_are_scoped_through_their_event(
    ctx_a: OrgContext, ctx_b: OrgContext
) -> None:
    event = await make_event(ctx_a)
    instance = await make_instance(ctx_a, event)

    repo_b = EventRepository(ctx_b)
    assert await repo_b.get_instance(instance.id) is None
    assert await repo_b.list_instances(event.id) == []
    assert await repo_b.update_instance(instance.id, {"venue_name": "Hijacked Hall"}) is None
    assert await repo_b.delete_instance(instance.id) is False

    repo_a = EventRepository(ctx_a)
    fresh = await repo_a.get_instance(instance.id)
    assert fresh is not None and fresh.venue_name is None
    assert [i.id for i in await repo_a.list_instances(event.id)] == [instance.id]

    with pytest.raises(LookupError):
        await repo_b.add_instance(
            EventInstance(
                event_id=event.id,
                external_id="stolen-i2",
                starts_at=datetime(2026, 9, 2, 19, 30, tzinfo=UTC),
            )
        )


# --- FK targets must belong to the context's org -----------------------------


async def test_allocation_cannot_target_another_orgs_event_or_instance(
    ctx_a: OrgContext, ctx_b: OrgContext
) -> None:
    event_a = await make_event(ctx_a)
    instance_a = await make_instance(ctx_a, event_a)
    version = await make_template_version(ctx_b.session)

    with pytest.raises(LookupError):
        await AllocationRepository(ctx_b).add(
            Allocation(template_version_id=version.id, event_id=event_a.id)
        )
    with pytest.raises(LookupError):
        await AllocationRepository(ctx_b).add(
            Allocation(template_version_id=version.id, instance_id=instance_a.id)
        )


async def test_invitation_cannot_reference_another_orgs_rows(
    ctx_a: OrgContext, ctx_b: OrgContext
) -> None:
    event_a = await make_event(ctx_a)
    allocation_a = await make_allocation(ctx_a, event_a)
    customer_a = await make_customer(ctx_a)
    event_b = await make_event(ctx_b, "ev-b")
    allocation_b = await make_allocation(ctx_b, event_b)

    with pytest.raises(LookupError):
        await make_invitation(ctx_b, allocation_a, customer_a)
    with pytest.raises(LookupError):
        await InvitationRepository(ctx_b).add(
            Invitation(allocation_id=allocation_b.id, customer_id=customer_a.id)
        )
