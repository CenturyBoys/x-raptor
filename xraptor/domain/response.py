from dataclasses import dataclass

import orjson

from xraptor.domain.methods import MethodType


@dataclass(slots=True, frozen=True)
class Response:
    request_id: str
    payload: str
    header: dict
    method: MethodType

    def __post_init__(self):
        # Explicit raises (not asserts): asserts are stripped under `python -O`,
        # which would silently disable validation in production.
        if not isinstance(self.request_id, str):
            raise TypeError(f"request_id is not of type {str}")
        if not isinstance(self.header, dict):
            raise TypeError(f"header is not of type {dict}")
        if not isinstance(self.payload, str):
            raise TypeError(f"payload is not of type {str}")
        if not isinstance(self.method, MethodType):
            raise TypeError(f"method is not of type {MethodType}")

    @classmethod
    def create(cls, request_id: str, header: dict, payload: str, method: MethodType):
        """
        create a new valid Response object instance
        :param method: the request method type that generated this response
        :param request_id: the origin request id
        :param header: string key value map
        :param payload: string payload, normally json data
        :return: Response instance
        """
        return cls(request_id=request_id, payload=payload, header=header, method=method)

    def json(self) -> str:
        """
        return a string data representation
        :return:
        """
        return orjson.dumps(
            {
                "request_id": self.request_id,
                "payload": self.payload,
                "header": self.header,
                "method": self.method.name,
            }
        ).decode()
