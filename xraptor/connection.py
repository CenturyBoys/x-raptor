import asyncio
import json
from asyncio import Task
from dataclasses import dataclass, field
from uuid import uuid4

import redis.asyncio as redis
from websockets import WebSocketServerProtocol

from xraptor.domain.request import Request


@dataclass(slots=True, frozen=True)
class Connection:
    path: str
    connection_hash: int
    remote_ip: str
    ws: WebSocketServerProtocol
    connection_id: str
    response_receiver: dict = field(default_factory=dict)

    @classmethod
    def from_ws(cls, ws: WebSocketServerProtocol):
        return cls(
            path=ws.path,
            connection_hash=ws.__hash__(),
            remote_ip=ws.remote_address[0],
            ws=ws,
            connection_id=str(uuid4()),
        )

    def register_response_receiver(self, request: Request):
        self.response_receiver.update(
            {request.request_id: asyncio.create_task(self.antenna(request.request_id))}
        )

    def unregister_response_receiver(self, request: Request):
        if request.request_id in self.response_receiver:
            _task: Task = self.response_receiver[request.request_id]
            _task.cancel()
            del self.response_receiver[request.request_id]

    def unregister_all(self):
        _r = [*self.response_receiver]
        for request_id in _r:
            if _task := self.response_receiver.get(request_id):
                _task.cancel()
                del self.response_receiver[request_id]

    async def antenna(self, request_id: str):
        redis_client = redis.Redis(host="raspb.local", port=6379, db=0)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(request_id)
        async for message in pubsub.listen():
            if message['type'] == "message":
                _data = json.loads(message["data"])
                _m = {
                    "payload": _data,
                    "request_id": request_id
                }
                await self.ws.send(json.dumps(_m).encode())
