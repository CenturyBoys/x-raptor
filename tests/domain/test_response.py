import json
from uuid import uuid4

import pytest

from xraptor import Response


@pytest.fixture(
    params=[
        {"request_id": 1.0},
        {"payload": {}},
        {"header": ""},
    ]
)
def attr_with_wrong_type(request):
    return request.param


def test_check_type(attr_with_wrong_type):
    _r = {
        "request_id": str(uuid4()),
        "payload": json.dumps({"chat_id": str(uuid4())}),
        "header": {},
    }
    _r.update(attr_with_wrong_type)
    with pytest.raises(AssertionError):
        Response(**_r)


def test_create():
    _r = {
        "request_id": str(uuid4()),
        "payload": json.dumps({"chat_id": str(uuid4())}),
        "header": {},
    }
    _response = Response.create(**_r)
    assert isinstance(_response, Response)


def test_json():
    _r = {
        "request_id": "c99215f9-33f0-4544-88ae-50378dde70fa",
        "payload": json.dumps({"chat_id": "5869ee0a-dfb5-4df1-96dc-b5fc97111a54"}),
        "header": {},
    }
    _response = Response(**_r)

    assert _response.json() == (
        '{"request_id": "c99215f9-33f0-4544-88ae-50378dde70fa", "payload": "{\\"'
        'chat_id\\": \\"5869ee0a-dfb5-4df1-96dc-b5fc97111a54\\"}", "header": {}}'
    )
