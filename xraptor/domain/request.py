import json
from dataclasses import dataclass
from uuid import uuid4

from xraptor.domain.methods import MethodType


@dataclass(slots=True, frozen=True)
class Request:
    request_id: str
    payload: str
    header: dict
    route: str
    method: MethodType

    def __post_init__(self):
        assert isinstance(self.request_id, str), "request_id is not of type {}".format(
            str
        )
        assert isinstance(self.payload, str), "header is not of type {}".format(str)
        assert isinstance(self.header, dict), "payload is not of type {}".format(dict)
        assert isinstance(self.route, str), "payload is not of type {}".format(str)
        assert isinstance(self.method, MethodType), "payload is not of type {}".format(
            MethodType
        )

    @classmethod
    def from_message(cls, message: str | bytes):
        """
        cast string message to a valid Request object instance
        :param message: json like string
        :return: Request instance
        """

        if isinstance(message, bytes):
            message: str = message.decode()

        message_data = json.loads(message)

        payload = message_data["payload"]

        if isinstance(payload, dict):
            payload = json.dumps(payload)

        return cls(
            request_id=message_data.get("request_id", str(uuid4())),
            payload=payload,
            header=message_data["header"],
            route=message_data["route"],
            method=MethodType[message_data["method"]],
        )
