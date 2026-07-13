import json
from uuid import uuid4

import pytest

from xraptor import Request
from xraptor.domain.methods import MethodType


@pytest.fixture(
    params=[
        {"request_id": 1.0},
        {"payload": {}},
        {"header": ""},
        {"route": 1.0},
        {"method": True},
    ]
)
def attr_with_wrong_type(request):
    return request.param


def test_check_type(attr_with_wrong_type):
    _r = {
        "request_id": str(uuid4()),
        "payload": json.dumps({"chat_id": str(uuid4())}),
        "header": {},
        "route": "/send_message_to_chat_room",
        "method": MethodType.POST,
    }
    _r.update(attr_with_wrong_type)
    with pytest.raises(TypeError):
        Request(**_r)


def test_from_message():
    msg = (
        '{"request_id": "c99215f9-33f0-4544-88ae-50378dde70fa", "payload": '
        '"{\\"chat_id\\": \\"5869ee0a-dfb5-4df1-96dc-b5fc97111a54\\"}", "he'
        'ader": {}, "route": "/send_message_to_chat_room", "method": "POST"}'
    )
    _request = Request.from_message(msg)
    assert isinstance(_request, Request)


def test_from_message_invalid_json():
    with pytest.raises(ValueError, match="malformed request"):
        Request.from_message("{not json")


def test_from_message_not_an_object():
    with pytest.raises(ValueError, match="must be a JSON object"):
        Request.from_message("[1, 2, 3]")


def test_from_message_missing_field():
    with pytest.raises(ValueError, match="missing request field"):
        Request.from_message('{"request_id": "x", "payload": "", "header": {}}')


def test_from_message_unknown_method():
    _msg = json.dumps(
        {
            "request_id": "x",
            "payload": "",
            "header": {},
            "route": "/r",
            "method": "TELEPORT",
        }
    )
    with pytest.raises(ValueError, match="unknown method"):
        Request.from_message(_msg)


def test_json():
    _r = {
        "request_id": "c99215f9-33f0-4544-88ae-50378dde70fa",
        "payload": json.dumps({"chat_id": "5869ee0a-dfb5-4df1-96dc-b5fc97111a54"}),
        "header": {},
        "route": "/send_message_to_chat_room",
        "method": MethodType.POST,
    }
    _request = Request(**_r)

    assert json.loads(_request.json()) == {
        "request_id": _r["request_id"],
        "payload": _r["payload"],
        "header": {},
        "route": _r["route"],
        "method": "POST",
    }
