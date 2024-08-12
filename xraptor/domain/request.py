import json
from dataclasses import dataclass
from uuid import uuid4

from xraptor.domain.methods import MethodType


@dataclass
class Request:
    request_id: str
    payload: bytes
    header: dict
    route: str
    method: MethodType

    @classmethod
    def from_message(cls, message: str | bytes):
        if isinstance(message, bytes):
            message: str = message.decode()
        message_data = json.loads(message)
        pyload = message_data["payload"]
        if isinstance(pyload, dict):
            pyload: bytes = json.dumps(pyload).encode()
        if isinstance(pyload, str):
            pyload: bytes = pyload.encode()
        return cls(
            request_id=message_data.get("request_id", str(uuid4())),
            payload=pyload,
            header=message_data["header"],
            route=message_data["route"],
            method=message_data["method"],
        )
