"""End-to-end tests: a real XRaptor server driven by a real websockets client."""

import asyncio
import json
import urllib.request

import pytest
import pytest_asyncio
import websockets

import xraptor
from xraptor.antenna_implementations.memory import MemoryAntenna
from xraptor.domain.methods import MethodType


@xraptor.XRaptor.register("/echo").as_get
async def _echo_handler(request: xraptor.Request) -> xraptor.Response:
    return xraptor.Response.create(
        request_id=request.request_id,
        header={},
        payload=request.payload,
        method=request.method,
    )


@xraptor.XRaptor.register("/stream").as_sub
async def _stream_handler(request: xraptor.Request) -> None:
    # SUB handler: the subscription is set up by the framework; messages are
    # later pushed through the antenna on this request_id.
    return None


@xraptor.XRaptor.register("/stream").as_unsub
async def _stream_unsub_handler(request: xraptor.Request) -> None:
    return None


def _msg(request_id: str, route: str, method: str, payload: str = "") -> str:
    return json.dumps(
        {
            "request_id": request_id,
            "payload": payload,
            "header": {},
            "route": route,
            "method": method,
        }
    )


@pytest_asyncio.fixture
async def server_port():
    xraptor.XRaptor.set_antenna(MemoryAntenna)
    server = xraptor.XRaptor("localhost", 0)  # port 0 -> ephemeral
    server.load_routes()
    task = asyncio.ensure_future(server.serve())
    for _ in range(200):  # wait until the socket is bound
        if server._server is not None:
            break
        await asyncio.sleep(0.01)
    assert server._server is not None
    port = server._server.sockets[0].getsockname()[1]
    yield server, port
    server.stop()
    await asyncio.wait_for(task, timeout=2)


@pytest.mark.asyncio
async def test_get_round_trip(server_port):
    _server, port = server_port
    async with websockets.connect(f"ws://localhost:{port}") as ws:
        await ws.send(_msg("r1", "/echo", "GET", payload="hello"))
        raw = await asyncio.wait_for(ws.recv(), timeout=2)
    data = json.loads(raw)
    assert data["request_id"] == "r1"
    assert data["payload"] == "hello"


@pytest.mark.asyncio
async def test_unknown_route_replies_not_registered(server_port):
    _server, port = server_port
    async with websockets.connect(f"ws://localhost:{port}") as ws:
        await ws.send(_msg("r2", "/nope", "GET"))
        raw = await asyncio.wait_for(ws.recv(), timeout=2)
    assert "Not registered" in json.loads(raw)["payload"]


@pytest.mark.asyncio
async def test_sub_streams_messages(server_port):
    _server, port = server_port
    async with websockets.connect(f"ws://localhost:{port}") as ws:
        await ws.send(_msg("sub1", "/stream", "SUB"))
        await asyncio.sleep(0.1)  # let the server register the subscription
        # Push a message on the subscription's antenna channel (request_id).
        await MemoryAntenna().post("sub1", "streamed-payload")
        raw = await asyncio.wait_for(ws.recv(), timeout=2)
    data = json.loads(raw)
    assert data["request_id"] == "sub1"
    assert data["payload"] == "streamed-payload"
    assert data["method"] == MethodType.SUB.name


@pytest.mark.asyncio
async def test_concurrent_connections(server_port):
    _server, port = server_port

    async def round_trip(i: int) -> str:
        async with websockets.connect(f"ws://localhost:{port}") as ws:
            await ws.send(_msg(f"c{i}", "/echo", "GET", payload=f"p{i}"))
            raw = await asyncio.wait_for(ws.recv(), timeout=2)
        return json.loads(raw)["payload"]

    results = await asyncio.gather(*[round_trip(i) for i in range(10)])
    assert sorted(results) == sorted(f"p{i}" for i in range(10))


def _http_get(port: int, path: str) -> tuple[int, str]:
    with urllib.request.urlopen(f"http://localhost:{port}{path}", timeout=2) as resp:
        return resp.status, resp.read().decode()


@pytest.mark.asyncio
async def test_health_endpoint(server_port):
    _server, port = server_port
    status, body = await asyncio.to_thread(_http_get, port, "/health")
    assert status == 200
    data = json.loads(body)
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert "active_connections" in data


@pytest.mark.asyncio
async def test_metrics_endpoint(server_port):
    _server, port = server_port
    # generate some traffic so counters are non-zero
    async with websockets.connect(f"ws://localhost:{port}") as ws:
        await ws.send(_msg("m1", "/echo", "GET", payload="x"))
        await asyncio.wait_for(ws.recv(), timeout=2)
    status, body = await asyncio.to_thread(_http_get, port, "/metrics")
    assert status == 200
    assert "# TYPE xraptor_requests_total counter" in body
    assert "xraptor_connections_total" in body
    assert "xraptor_uptime_seconds" in body


@pytest.mark.asyncio
async def test_unsub_isolation_end_to_end(server_port):
    _server, port = server_port
    async with (
        websockets.connect(f"ws://localhost:{port}") as ws_a,
        websockets.connect(f"ws://localhost:{port}") as ws_b,
    ):
        await ws_a.send(_msg("a", "/stream", "SUB"))
        await ws_b.send(_msg("b", "/stream", "SUB"))
        await asyncio.sleep(0.1)

        # Client A unsubscribes; client B must keep receiving (regression for the
        # old shared-_running singleton that killed every subscriber at once).
        await ws_a.send(_msg("a", "/stream", "UNSUB"))
        await asyncio.sleep(0.1)

        await MemoryAntenna().post("b", "still-alive")
        raw = await asyncio.wait_for(ws_b.recv(), timeout=2)
        assert json.loads(raw)["payload"] == "still-alive"
