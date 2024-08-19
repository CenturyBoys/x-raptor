import json
from uuid import uuid4

import pytest

import xraptor
from tests.stub import StubWS
from xraptor import Request
from xraptor.antenna_implementations.memory import MemoryAntenna
from xraptor.connection import Connection
from xraptor.domain.methods import MethodType


def test_from_ws():
    _c = Connection.from_ws(StubWS())
    assert _c.path == "/test"
    assert _c.connection_hash == 1
    assert _c.remote_ip == "192.168.0.1"


@pytest.mark.asyncio
async def test_register_response_receiver():
    xraptor.XRaptor.set_antenna(MemoryAntenna)
    _c = Connection.from_ws(StubWS())
    _r = Request(
        request_id=str(uuid4()),
        payload=json.dumps({"chat_id": str(uuid4())}),
        header={},
        route="/send_message_to_chat_room",
        method=MethodType.POST,
    )

    _c.register_response_receiver(_r)
    assert _r.request_id in _c.response_receiver
    _c.unregister_response_receiver(_r)
    assert _r.request_id not in _c.response_receiver


@pytest.mark.asyncio
async def test_unregister_all():
    xraptor.XRaptor.set_antenna(MemoryAntenna)
    _c = Connection.from_ws(StubWS())
    _r = Request(
        request_id=str(uuid4()),
        payload=json.dumps({"chat_id": str(uuid4())}),
        header={},
        route="/send_message_to_chat_room",
        method=MethodType.POST,
    )

    _c.register_response_receiver(_r)
    assert _r.request_id in _c.response_receiver
    _c._unregister_all()
    assert _r.request_id not in _c.response_receiver
