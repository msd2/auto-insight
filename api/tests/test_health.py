from collections.abc import AsyncIterator
from typing import Any

import httpx

from autoinsight.db import get_session
from autoinsight.main import create_app


class _FakeSession:
    """Stands in for AsyncSession; the health check only calls execute()."""

    def __init__(self, fail: bool) -> None:
        self.fail = fail

    async def execute(self, *args: Any, **kwargs: Any) -> None:
        if self.fail:
            raise ConnectionError("database unavailable")


def _client_with_session(fail: bool) -> httpx.AsyncClient:
    app = create_app()

    async def override() -> AsyncIterator[_FakeSession]:
        yield _FakeSession(fail=fail)

    app.dependency_overrides[get_session] = override
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_health_reports_database_ok() -> None:
    async with _client_with_session(fail=False) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_health_is_200_when_database_unavailable() -> None:
    async with _client_with_session(fail=True) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "unavailable"}
