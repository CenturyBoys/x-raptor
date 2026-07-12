import asyncio

import pytest

from xraptor.antenna_implementations.memory import MemoryAntenna


@pytest.mark.asyncio
async def test_stop_one_subscriber_does_not_affect_another():
    # Regression: MemoryAntenna used to be a singleton with a shared _running
    # flag, so one subscriber calling stop_listening() killed *all* of them.
    _a1 = MemoryAntenna()
    _a2 = MemoryAntenna()
    _g1 = _a1.subscribe("c1")
    _g2 = _a2.subscribe("c2")
    _n1 = asyncio.ensure_future(_g1.__anext__())
    _n2 = asyncio.ensure_future(_g2.__anext__())
    await asyncio.sleep(0)  # let both register and park on get()

    await _a1.post("c1", "m1")
    await _a2.post("c2", "m2")
    assert await _n1 == "m1"
    assert await _n2 == "m2"

    await _a1.stop_listening()
    with pytest.raises(StopAsyncIteration):
        await _g1.__anext__()
    assert await _a1.is_alive("c1") is False

    # Subscriber 2 must still be alive and receiving.
    assert await _a2.is_alive("c2") is True
    _n2b = asyncio.ensure_future(_g2.__anext__())
    await asyncio.sleep(0)
    await _a2.post("c2", "m3")
    assert await _n2b == "m3"

    await _a2.stop_listening()
    with pytest.raises(StopAsyncIteration):
        await _g2.__anext__()


@pytest.mark.asyncio
async def test_queue_cleaned_after_unsubscribe():
    _a = MemoryAntenna()
    _g = _a.subscribe("chan")
    _n = asyncio.ensure_future(_g.__anext__())  # parks on get()
    await asyncio.sleep(0)
    assert await _a.is_alive("chan") is True
    assert "chan" in MemoryAntenna._queues

    await _a.stop_listening()  # sentinel unblocks the parked get()
    with pytest.raises(StopAsyncIteration):
        await _n
    assert await _a.is_alive("chan") is False
    assert "chan" not in MemoryAntenna._queues  # no orphan queue left behind


@pytest.mark.asyncio
async def test_post_without_subscriber_is_dropped():
    _a = MemoryAntenna()
    await _a.post("nobody", "msg")
    assert "nobody" not in MemoryAntenna._queues
    assert await _a.is_alive("nobody") is False
