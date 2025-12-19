from unittest.mock import MagicMock

import pytest

import xraptor
from xraptor.connection import Connection
from xraptor.domain.methods import MethodType


@pytest.fixture(autouse=True)
def clear_middlewares():
    """Clear middlewares before each test."""
    xraptor.XRaptor._middlewares = []
    yield
    xraptor.XRaptor._middlewares = []


def test_middleware_registration():
    @xraptor.XRaptor.middleware(priority=1)
    async def my_middleware(request, connection):
        return None

    assert len(xraptor.XRaptor._middlewares) == 1
    assert xraptor.XRaptor._middlewares[0].priority == 1
    assert xraptor.XRaptor._middlewares[0].pattern is None
    assert xraptor.XRaptor._middlewares[0].func == my_middleware


def test_middleware_priority_conflict():
    @xraptor.XRaptor.middleware(priority=1)
    async def first_middleware(request, connection):
        return None

    with pytest.raises(ValueError, match="Middleware priority 1 already registered"):

        @xraptor.XRaptor.middleware(priority=1)
        async def second_middleware(request, connection):
            return None


def test_middleware_execution_order():
    execution_order = []

    @xraptor.XRaptor.middleware(priority=10)
    async def third_middleware(request, connection):
        execution_order.append(3)
        return None

    @xraptor.XRaptor.middleware(priority=1)
    async def first_middleware(request, connection):
        execution_order.append(1)
        return None

    @xraptor.XRaptor.middleware(priority=5)
    async def second_middleware(request, connection):
        execution_order.append(2)
        return None

    # Verify sorted by priority
    priorities = [mw.priority for mw in xraptor.XRaptor._middlewares]
    assert priorities == [1, 5, 10]


@pytest.mark.asyncio
async def test_middleware_execution_order_runtime():
    execution_order = []

    @xraptor.XRaptor.middleware(priority=10)
    async def third_middleware(request, connection):
        execution_order.append(3)
        return None

    @xraptor.XRaptor.middleware(priority=1)
    async def first_middleware(request, connection):
        execution_order.append(1)
        return None

    @xraptor.XRaptor.middleware(priority=5)
    async def second_middleware(request, connection):
        execution_order.append(2)
        return None

    request = xraptor.Request(
        request_id="test-id",
        payload="{}",
        header={},
        route="/test",
        method=MethodType.GET,
    )
    connection = MagicMock(spec=Connection)

    result = await xraptor.XRaptor._run_middlewares(request, connection)

    assert result is None
    assert execution_order == [1, 2, 3]


@pytest.mark.asyncio
async def test_middleware_short_circuit():
    execution_order = []

    @xraptor.XRaptor.middleware(priority=1)
    async def first_middleware(request, connection):
        execution_order.append(1)
        return None

    @xraptor.XRaptor.middleware(priority=2)
    async def blocking_middleware(request, connection):
        execution_order.append(2)
        return xraptor.Response.create(
            request_id=request.request_id,
            header={},
            payload='{"blocked": true}',
            method=request.method,
        )

    @xraptor.XRaptor.middleware(priority=3)
    async def third_middleware(request, connection):
        execution_order.append(3)
        return None

    request = xraptor.Request(
        request_id="test-id",
        payload="{}",
        header={},
        route="/test",
        method=MethodType.GET,
    )
    connection = MagicMock(spec=Connection)

    result = await xraptor.XRaptor._run_middlewares(request, connection)

    assert result is not None
    assert result.payload == '{"blocked": true}'
    assert execution_order == [1, 2]  # Third middleware should not run


@pytest.mark.asyncio
async def test_middleware_pattern_matching():
    api_calls = []
    other_calls = []

    @xraptor.XRaptor.middleware(priority=1, pattern=r"^/api/.*")
    async def api_middleware(request, connection):
        api_calls.append(request.route)
        return None

    @xraptor.XRaptor.middleware(priority=2)
    async def global_middleware(request, connection):
        other_calls.append(request.route)
        return None

    connection = MagicMock(spec=Connection)

    # Test API route
    api_request = xraptor.Request(
        request_id="test-id",
        payload="{}",
        header={},
        route="/api/users",
        method=MethodType.GET,
    )
    await xraptor.XRaptor._run_middlewares(api_request, connection)

    # Test non-API route
    other_request = xraptor.Request(
        request_id="test-id2",
        payload="{}",
        header={},
        route="/home",
        method=MethodType.GET,
    )
    await xraptor.XRaptor._run_middlewares(other_request, connection)

    assert api_calls == ["/api/users"]
    assert other_calls == ["/api/users", "/home"]


@pytest.mark.asyncio
async def test_middleware_global_pattern():
    calls = []

    @xraptor.XRaptor.middleware(priority=1)
    async def global_middleware(request, connection):
        calls.append(request.route)
        return None

    connection = MagicMock(spec=Connection)

    routes = ["/api/users", "/home", "/test/nested/route"]
    for route in routes:
        request = xraptor.Request(
            request_id="test-id",
            payload="{}",
            header={},
            route=route,
            method=MethodType.GET,
        )
        await xraptor.XRaptor._run_middlewares(request, connection)

    assert calls == routes


@pytest.mark.asyncio
async def test_middleware_invalid_return_type():
    @xraptor.XRaptor.middleware(priority=1)
    async def bad_middleware(request, connection):
        return {"invalid": "type"}  # Should return Response or None

    request = xraptor.Request(
        request_id="test-id",
        payload="{}",
        header={},
        route="/test",
        method=MethodType.GET,
    )
    connection = MagicMock(spec=Connection)

    with pytest.raises(AssertionError, match="Middleware must return Response or None"):
        await xraptor.XRaptor._run_middlewares(request, connection)
