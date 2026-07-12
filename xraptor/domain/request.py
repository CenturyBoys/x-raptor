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
        # Explicit raises (not asserts): asserts are stripped under `python -O`,
        # which would silently disable input validation in production.
        if not isinstance(self.request_id, str):
            raise TypeError(f"request_id is not of type {str}")
        if not isinstance(self.payload, str):
            raise TypeError(f"payload is not of type {str}")
        if not isinstance(self.header, dict):
            raise TypeError(f"header is not of type {dict}")
        if not isinstance(self.route, str):
            raise TypeError(f"route is not of type {str}")
        if not isinstance(self.method, MethodType):
            raise TypeError(f"method is not of type {MethodType}")

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
        :raises ValueError: if the message is not a well-formed request
        """
        try:
            message_data = json.loads(message)
        except (json.JSONDecodeError, TypeError) as error:
            raise ValueError(f"malformed request: {error}") from error

        if not isinstance(message_data, dict):
            raise ValueError("request must be a JSON object")

        for field in ("request_id", "payload", "header", "route", "method"):
            if field not in message_data:
                raise ValueError(f"missing request field: {field!r}")

        try:
            method = MethodType[str(message_data["method"]).upper()]
        except KeyError as error:
            raise ValueError(f"unknown method: {message_data['method']!r}") from error

        return cls(
            request_id=message_data["request_id"],
            payload=message_data["payload"],
            header=message_data["header"],
            route=message_data["route"],
            method=method,
        )
