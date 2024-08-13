import json
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Response:
    request_id: str
    payload: str
    header: dict

    def __post_init__(self):
        assert isinstance(self.request_id, str), "request_id is not of type {}".format(str)
        assert isinstance(self.header, dict), "header is not of type {}".format(dict)
        assert isinstance(self.payload, str), "payload is not of type {}".format(str)

    @classmethod
    def from_message(cls, request_id: str, header: dict, payload: str):
        return cls(
            request_id=request_id,
            payload=payload,
            header=header,
        )

    def json(self):
        return json.dumps({
            "request_id": self.request_id,
            "payload": self.payload,
            "header": self.header,
        })
