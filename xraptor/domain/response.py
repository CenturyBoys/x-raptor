import json
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Response:
    request_id: str
    payload: str
    header: dict

    def __post_init__(self):
        assert isinstance(self.request_id, str), f"request_id is not of type {str}"
        assert isinstance(self.header, dict), f"header is not of type {dict}"
        assert isinstance(self.payload, str), f"payload is not of type {str}"

    @classmethod
    def create(cls, request_id: str, header: dict, payload: str):
        """
        create a new valid Response object instance
        :param request_id: the origin request id
        :param header: string key value map
        :param payload: string payload, normally json data
        :return: Response instance
        """
        return cls(
            request_id=request_id,
            payload=payload,
            header=header,
        )

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
            }
        )
