import json
from dataclasses import dataclass

from xraptor.domain.methods import MethodType


@dataclass(slots=True, frozen=True)
class Request:
    request_id: str
    payload: str
    header: dict
    route: str
    method: MethodType

    def __post_init__(self):
        assert isinstance(self.request_id, str), f"request_id is not of type {str}"
        assert isinstance(self.payload, str), f"payload is not of type {str}"
        assert isinstance(self.header, dict), f"header is not of type {dict}"
        assert isinstance(self.route, str), f"route is not of type {str}"
        assert isinstance(
            self.method, MethodType
        ), f"method is not of type {MethodType}"

    def json(self) -> str:
        """
        return a string data representation
        :return:
        """
        return json.dumps(
            {
                "request_id": self.request_id,
                "payload": self.payload,
                "header": self.header,
                "route": self.route,
                "method": self.method.value,
            }
        )

    @classmethod
    def from_message(cls, message: str | bytes):
        """
        cast string message to a valid Request object instance
        :param message: json like string
        :return: Request instance
        """

        message_data = json.loads(message)

        return cls(
            request_id=message_data["request_id"],
            payload=message_data["payload"],
            header=message_data["header"],
            route=message_data["route"],
            method=MethodType[message_data["method"]],
        )
