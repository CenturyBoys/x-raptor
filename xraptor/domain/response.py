import json
from dataclasses import dataclass

from xraptor.domain.methods import MethodType


@dataclass(slots=True, frozen=True)
class Response:
    request_id: str
    payload: str
    header: dict
    method: MethodType

    def __post_init__(self):
        assert isinstance(self.request_id, str), f"request_id is not of type {str}"
        assert isinstance(self.header, dict), f"header is not of type {dict}"
        assert isinstance(self.payload, str), f"payload is not of type {str}"
        assert isinstance(
            self.method, MethodType
        ), f"method is not of type {MethodType}"

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

    def json(self):
        """
        return a string data representation
        :return:
        """
        return json.dumps(
            {
                "request_id": self.request_id,
                "payload": self.payload,
                "header": self.header,
                "method": self.method.name,
            }
        )
