from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xraptor.antenna_implementations.nats import NatsAntenna

_CONNECT = "xraptor.antenna_implementations.nats.nats.connect"


@pytest.fixture(autouse=True)
def _reset_nats_antenna():
    NatsAntenna._config = {}
    NatsAntenna._client = None
    NatsAntenna._connect_lock = None
    yield
    NatsAntenna._config = {}
    NatsAntenna._client = None
    NatsAntenna._connect_lock = None


def _fake_client() -> MagicMock:
    client = MagicMock()
    client.is_connected = True
    client.publish = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_post_without_config_raises():
    with pytest.raises(ValueError):
        await NatsAntenna().post("subj", "msg")


@pytest.mark.asyncio
async def test_shared_client_created_once():
    NatsAntenna.set_config({"servers": "nats://localhost:4222"})
    client = _fake_client()
    with patch(_CONNECT, new=AsyncMock(return_value=client)) as mock_connect:
        await NatsAntenna().post("subj", "m1")
        await NatsAntenna().post("subj", "m2")
    assert mock_connect.await_count == 1  # reused across instances
    assert client.publish.await_count == 2
    client.publish.assert_awaited_with("subj", b"m2")  # str encoded to bytes


@pytest.mark.asyncio
async def test_subscribe_yields_decoded_messages():
    NatsAntenna.set_config({"servers": "nats://localhost:4222"})

    class _Msg:
        def __init__(self, data):
            self.data = data

    async def _messages():
        yield _Msg(b"hello")
        yield _Msg(b"world")

    fake_sub = MagicMock()
    fake_sub.messages = _messages()
    fake_sub.unsubscribe = AsyncMock()
    client = _fake_client()
    client.subscribe = AsyncMock(return_value=fake_sub)

    with patch(_CONNECT, new=AsyncMock(return_value=client)):
        _a = NatsAntenna()
        agen = _a.subscribe("subj")
        got = []
        async for message in agen:
            got.append(message)
            if len(got) == 2:
                break
        await agen.aclose()  # runs the finally (as task cancellation does in prod)

    assert got == ["hello", "world"]
    fake_sub.unsubscribe.assert_awaited()


@pytest.mark.asyncio
async def test_is_alive_always_true():
    assert await NatsAntenna().is_alive("anything") is True


@pytest.mark.asyncio
async def test_set_config_resets_client():
    NatsAntenna.set_config({"servers": "nats://a:4222"})
    client = _fake_client()
    with patch(_CONNECT, new=AsyncMock(return_value=client)) as mock_connect:
        await NatsAntenna().post("s", "m")
        NatsAntenna.set_config({"servers": "nats://b:4222"})
        await NatsAntenna().post("s", "m")
    assert mock_connect.await_count == 2  # reconnect after config change
