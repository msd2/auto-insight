"""Auth end-to-end: login, session cookie, logout, roles, password reset,

and the authed session → OrgContext → repository isolation path.
"""

import re
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from autoinsight.adapters.email import LoggingEmailProvider
from autoinsight.config import get_settings
from autoinsight.models import AuthSession, Event, PasswordResetToken, User, UserRole
from autoinsight.repositories import EventRepository, OrgContext
from tests.conftest import PASSWORD, make_user

COOKIE = get_settings().session_cookie_name


async def login(
    client: httpx.AsyncClient,
    email: str,
    password: str = PASSWORD,
    org_slug: str | None = None,
) -> httpx.Response:
    payload: dict[str, str] = {"email": email, "password": password}
    if org_slug is not None:
        payload["org_slug"] = org_slug
    return await client.post("/auth/login", json=payload)


# --- login & session cookie ---------------------------------------------------


async def test_login_sets_cookie_and_me_roundtrips(
    client: httpx.AsyncClient, admin_a: User
) -> None:
    response = await login(client, admin_a.email)
    assert response.status_code == 200
    set_cookie = response.headers["set-cookie"]
    assert COOKIE in set_cookie and "HttpOnly" in set_cookie and "SameSite=lax" in set_cookie

    me = await client.get("/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["user"]["email"] == admin_a.email
    assert body["user"]["role"] == "admin"
    assert body["org"]["slug"] == "org-a"


async def test_login_failures_are_401_with_one_message(
    client: httpx.AsyncClient, admin_a: User
) -> None:
    wrong_password = await login(client, admin_a.email, password="not-the-password")
    unknown_email = await login(client, "nobody@example.org")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


async def test_login_with_email_in_multiple_orgs_requires_org_slug(
    client: httpx.AsyncClient, ctx_a: OrgContext, ctx_b: OrgContext
) -> None:
    staff_email = "staff@culturecounts.example"
    await make_user(ctx_a, staff_email)
    await make_user(ctx_b, staff_email)

    ambiguous = await login(client, staff_email)
    assert ambiguous.status_code == 400

    scoped = await login(client, staff_email, org_slug="org-b")
    assert scoped.status_code == 200
    assert scoped.json()["org"]["slug"] == "org-b"


async def test_me_requires_a_valid_session(client: httpx.AsyncClient, admin_a: User) -> None:
    assert (await client.get("/auth/me")).status_code == 401
    client.cookies.set(COOKIE, "garbage-token")
    assert (await client.get("/auth/me")).status_code == 401


async def test_logout_invalidates_the_session(client: httpx.AsyncClient, admin_a: User) -> None:
    await login(client, admin_a.email)
    assert (await client.get("/auth/me")).status_code == 200
    assert (await client.post("/auth/logout")).status_code == 204
    assert (await client.get("/auth/me")).status_code == 401


async def test_expired_session_is_rejected(
    client: httpx.AsyncClient, session: AsyncSession, admin_a: User
) -> None:
    await login(client, admin_a.email)
    await session.execute(
        update(AuthSession).values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
    )
    assert (await client.get("/auth/me")).status_code == 401


# --- roles ---------------------------------------------------------------------


async def test_admin_gate_blocks_members(
    client: httpx.AsyncClient, admin_a: User, member_a: User
) -> None:
    await login(client, member_a.email)
    assert (await client.get("/_test/admin-only")).status_code == 403

    await login(client, admin_a.email)
    response = await client.get("/_test/admin-only")
    assert response.status_code == 200
    assert response.json() == {"user": admin_a.email}


# --- authed repository path stays org-isolated ----------------------------------


async def test_repositories_stay_org_scoped_through_the_authed_path(
    client: httpx.AsyncClient, ctx_a: OrgContext, ctx_b: OrgContext, admin_a: User
) -> None:
    event_a = await EventRepository(ctx_a).add(Event(external_id="ev-a", name="A Show"))
    await EventRepository(ctx_b).add(Event(external_id="ev-b", name="B Show"))

    assert (await client.get("/_test/events")).status_code == 401

    await login(client, admin_a.email)
    response = await client.get("/_test/events")
    assert response.status_code == 200
    assert response.json() == [str(event_a.id)]


# --- password reset --------------------------------------------------------------


def extract_token(provider: LoggingEmailProvider) -> str:
    match = re.search(r"token=([A-Za-z0-9_\-]+)", provider.outbox[-1].text_body)
    assert match is not None
    return match.group(1)


async def test_password_reset_happy_path(
    client: httpx.AsyncClient, email_provider: LoggingEmailProvider, admin_a: User
) -> None:
    await login(client, admin_a.email)

    requested = await client.post("/auth/password-reset/request", json={"email": admin_a.email})
    assert requested.status_code == 202
    assert len(email_provider.outbox) == 1
    assert email_provider.outbox[0].to == admin_a.email
    token = extract_token(email_provider)

    confirmed = await client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "new_password": "a-brand-new-password"},
    )
    assert confirmed.status_code == 204

    # The pre-reset session was revoked.
    assert (await client.get("/auth/me")).status_code == 401
    # Old password no longer works; the new one does.
    assert (await login(client, admin_a.email)).status_code == 401
    assert (await login(client, admin_a.email, password="a-brand-new-password")).status_code == 200


async def test_reset_request_does_not_leak_account_existence(
    client: httpx.AsyncClient, email_provider: LoggingEmailProvider, admin_a: User
) -> None:
    known = await client.post("/auth/password-reset/request", json={"email": admin_a.email})
    unknown = await client.post("/auth/password-reset/request", json={"email": "no@example.org"})
    assert known.status_code == unknown.status_code == 202
    assert known.content == unknown.content
    assert len(email_provider.outbox) == 1  # only the real account got an email


async def test_reset_covers_every_org_for_a_multi_org_email(
    client: httpx.AsyncClient,
    email_provider: LoggingEmailProvider,
    ctx_a: OrgContext,
    ctx_b: OrgContext,
) -> None:
    staff_email = "staff@culturecounts.example"
    await make_user(ctx_a, staff_email)
    await make_user(ctx_b, staff_email)
    await client.post("/auth/password-reset/request", json={"email": staff_email})
    assert len(email_provider.outbox) == 2
    assert {"Org A", "Org B"} <= {
        org for msg in email_provider.outbox for org in ("Org A", "Org B") if org in msg.text_body
    }


async def test_reset_token_is_single_use(
    client: httpx.AsyncClient, email_provider: LoggingEmailProvider, admin_a: User
) -> None:
    await client.post("/auth/password-reset/request", json={"email": admin_a.email})
    token = extract_token(email_provider)
    body = {"token": token, "new_password": "another-new-password"}
    assert (await client.post("/auth/password-reset/confirm", json=body)).status_code == 204
    assert (await client.post("/auth/password-reset/confirm", json=body)).status_code == 400


async def test_expired_reset_token_is_rejected(
    client: httpx.AsyncClient,
    session: AsyncSession,
    email_provider: LoggingEmailProvider,
    admin_a: User,
) -> None:
    await client.post("/auth/password-reset/request", json={"email": admin_a.email})
    token = extract_token(email_provider)
    await session.execute(
        update(PasswordResetToken).values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
    )
    response = await client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "new_password": "another-new-password"},
    )
    assert response.status_code == 400
    # And the password is unchanged.
    assert (await login(client, admin_a.email)).status_code == 200


async def test_garbage_reset_token_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/auth/password-reset/confirm",
        json={"token": "garbage", "new_password": "whatever-password"},
    )
    assert response.status_code == 400


async def test_short_new_password_is_rejected(
    client: httpx.AsyncClient, email_provider: LoggingEmailProvider, admin_a: User
) -> None:
    await client.post("/auth/password-reset/request", json={"email": admin_a.email})
    token = extract_token(email_provider)
    response = await client.post(
        "/auth/password-reset/confirm", json={"token": token, "new_password": "short"}
    )
    assert response.status_code == 422


# --- keep UserRole honest --------------------------------------------------------


def test_user_roles_match_the_architecture() -> None:
    assert {role.value for role in UserRole} == {"member", "admin"}
