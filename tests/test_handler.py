from unittest.mock import patch
from uuid import uuid4

import pytest
import websockets

import xraptor
from tests.stub import StubWS
from xraptor import Request
from xraptor.connection import Connection
from xraptor.domain.methods import MethodType
from xraptor.server import XRaptor


@pytest.fixture(
    params=[
        websockets.exceptions.ConnectionClosed,
        websockets.exceptions.InvalidHandshake,
        websockets.exceptions.WebSocketException,
        Exception,
    ]
)
def possible_mapped_errors(request):
    return request.param


@pytest.mark.asyncio
async def test_watch(possible_mapped_errors):
    with patch.object(Connection, "close") as mock_x:
        with patch.object(StubWS, "netx_msg", side_effect=possible_mapped_errors):
            await XRaptor._watch(StubWS())
    assert mock_x.called


@pytest.mark.asyncio
async def test_handle_request_parse_fail():
    _c = Connection.from_ws(StubWS())
    with patch.object(StubWS, "send") as mock_x:
        _r = await XRaptor._handle_request("{", _c)
    assert mock_x.called is False


@pytest.mark.asyncio
async def test_handle_request_error():
    _c = Connection.from_ws(StubWS())
    _request = Request(
        request_id=str(uuid4()),
        payload="",
        header={},
        route="/not_allowed",
        method=MethodType.POST,
    )
    with patch.object(StubWS, "send") as mock_x:
        with patch.object(XRaptor, "route_matcher", side_effect=Exception):
            _response = await XRaptor._handle_request(_request.json(), _c)
    assert mock_x.called


def xxx(*args, **kwargs):
    pass


@pytest.mark.asyncio
async def test_handle_request_get():
    _c = Connection.from_ws(StubWS())
    _request = Request(
        request_id=str(uuid4()),
        payload="",
        header={},
        route="/not_allowed",
        method=MethodType.GET,
    )

    with patch.object(StubWS, "send") as mock_x:
        with patch.object(XRaptor, "route_matcher", return_value=xxx):
            _response = await XRaptor._handle_request(_request.json(), _c)
    assert mock_x.called


@pytest.mark.asyncio
async def test_handle_request_post():
    _c = Connection.from_ws(StubWS())
    _request = Request(
        request_id=str(uuid4()),
        payload="",
        header={},
        route="/not_allowed",
        method=MethodType.POST,
    )

    with patch.object(StubWS, "send") as mock_x:
        with patch.object(XRaptor, "route_matcher", return_value=xxx):
            _response = await XRaptor._handle_request(_request.json(), _c)
    assert mock_x.called


@pytest.mark.asyncio
async def test_handle_request_sub():
    _c = Connection.from_ws(StubWS())
    _request = Request(
        request_id=str(uuid4()),
        payload="",
        header={},
        route="/not_allowed",
        method=MethodType.SUB,
    )
    with patch.object(StubWS, "send") as mock_x:
        with patch.object(XRaptor, "_subscribe") as mock_y:
            with patch.object(XRaptor, "route_matcher", return_value=xxx):
                _response = await XRaptor._handle_request(_request.json(), _c)
    assert mock_x.called
    assert mock_y.called


@pytest.mark.asyncio
async def test_handle_request_unsub():
    _c = Connection.from_ws(StubWS())
    _request = Request(
        request_id=str(uuid4()),
        payload="",
        header={},
        route="/not_allowed",
        method=MethodType.UNSUB,
    )
    with patch.object(StubWS, "send") as mock_x:
        with patch.object(XRaptor, "route_matcher", return_value=xxx):
            _response = await XRaptor._handle_request(_request.json(), _c)
    assert mock_x.called
