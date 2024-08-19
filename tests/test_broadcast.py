import asyncio
from unittest.mock import patch

import pytest

import xraptor
from xraptor.antenna_implementations.memory import MemoryAntenna


def test_get():
    _b = xraptor.Broadcast.get("a1")
    _b1 = xraptor.Broadcast.get("a1")
    assert _b == _b1


def test_add_member():
    _b = xraptor.Broadcast.get("a1")
    with patch.object(xraptor.Broadcast, "_open") as mock_x:
        _b.add_member("member_a1")
    assert mock_x.called


def test_remove_member():
    _b = xraptor.Broadcast.get("a1")
    with patch.object(xraptor.Broadcast, "_open"):
        _b.add_member("member_a1")
        with patch.object(xraptor.Broadcast, "_delete") as mock_x:
            with patch.object(xraptor.Broadcast, "_close") as mock_y:
                _b.remove_member("member_a1")
    assert mock_x.called
    assert mock_y.called


@pytest.mark.asyncio
async def test_open():
    async def xxx():
        pass

    _b = xraptor.Broadcast.get("a1")
    with patch.object(xraptor.Broadcast, "_listening", return_value=xxx()) as mock_x:
        with patch.object(xraptor.Broadcast, "_check", return_value=xxx()) as mock_y:
            _b._open()
    assert mock_x.called
    assert mock_y.called


@pytest.mark.asyncio
async def test_close():
    async def xxx():
        pass

    _b = xraptor.Broadcast.get("a1")
    with patch.object(xraptor.Broadcast, "_listening", return_value=xxx()):
        with patch.object(xraptor.Broadcast, "_check", return_value=xxx()):
            _b._open()
            _b._close()


@pytest.mark.asyncio
async def test_check_alive():
    xraptor.XRaptor.set_antenna(MemoryAntenna)
    _b = xraptor.Broadcast.get("a1")
    _a = xraptor.XRaptor.get_antenna()
    await _a.post("member1", "message")
    _b.add_member("member1")
    with pytest.raises(Exception):
        with patch.object(xraptor.Broadcast, "remove_member") as mock_x:
            with patch.object(asyncio, "sleep", side_effect=Exception):
                await _b._check(antenna=_a, frequency=0)
    _b._close()
    assert mock_x.called is False


@pytest.mark.asyncio
async def test_check_not_alive():
    xraptor.XRaptor.set_antenna(MemoryAntenna)
    _b = xraptor.Broadcast.get("a2")
    _a = xraptor.XRaptor.get_antenna()
    _b.add_member("member2")
    with pytest.raises(Exception):
        with patch.object(xraptor.Broadcast, "remove_member") as mock_x:
            with patch.object(asyncio, "sleep", side_effect=Exception):
                await _b._check(antenna=_a, frequency=0)
    assert mock_x.called
    _b._close()
