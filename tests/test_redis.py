from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xraptor.antenna_implementations.redis import RedisAntenna

_FROM_URL = "xraptor.antenna_implementations.redis.redis.Redis.from_url"


@pytest.fixture(autouse=True)
def _reset_redis_antenna():
    RedisAntenna._config = {}
    RedisAntenna._client = None
    yield
    RedisAntenna._config = {}
    RedisAntenna._client = None


@pytest.mark.asyncio
async def test_post_without_config_raises():
    _a = RedisAntenna()
    with pytest.raises(ValueError):
        await _a.post("chan", "msg")


@pytest.mark.asyncio
async def test_is_alive_without_config_raises():
    _a = RedisAntenna()
    with pytest.raises(ValueError):
        await _a.is_alive("chan")


@pytest.mark.asyncio
async def test_shared_client_created_once():
    RedisAntenna.set_config({"url": "redis://localhost:6379/0"})
    fake_client = MagicMock()
    fake_client.publish = AsyncMock()
    with patch(_FROM_URL, return_value=fake_client) as mock_from_url:
        _a1 = RedisAntenna()
        _a2 = RedisAntenna()
        await _a1.post("chan", "msg")
        await _a2.post("chan", "msg2")
    # Client is created once and reused across factory-created instances.
    assert mock_from_url.call_count == 1
    assert fake_client.publish.await_count == 2


@pytest.mark.asyncio
async def test_is_alive_parses_numsub():
    RedisAntenna.set_config({"url": "redis://localhost:6379/0"})
    fake_client = MagicMock()
    fake_client.execute_command = AsyncMock(side_effect=[[b"chan", 2], [b"chan", 0]])
    with patch(_FROM_URL, return_value=fake_client):
        _a = RedisAntenna()
        assert await _a.is_alive("chan") is True
        assert await _a.is_alive("chan") is False


@pytest.mark.asyncio
async def test_set_config_resets_client():
    RedisAntenna.set_config({"url": "redis://a:6379/0"})
    fake_client = MagicMock()
    fake_client.publish = AsyncMock()
    with patch(_FROM_URL, return_value=fake_client) as mock_from_url:
        await RedisAntenna().post("chan", "msg")
        RedisAntenna.set_config({"url": "redis://b:6379/0"})
        await RedisAntenna().post("chan", "msg")
    # New config forces the shared client to be recreated.
    assert mock_from_url.call_count == 2
