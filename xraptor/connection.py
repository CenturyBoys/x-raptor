import asyncio
import logging
from asyncio import Task
from dataclasses import dataclass, field
from uuid import uuid4

import witch_doctor
from websockets import WebSocketServerProtocol
from websockets.frames import CloseCode

from xraptor.core.interfaces import Antenna
from xraptor.domain.request import Request
from xraptor.domain.response import Response


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
            {
                request.request_id: asyncio.create_task(self.antenna(request=request)),
            }
        )

    def unregister_response_receiver(self, request: Request):
        if request.request_id in self.response_receiver:
            _task: Task = self.response_receiver[request.request_id]
            _task.cancel()
            del self.response_receiver[request.request_id]

    def _unregister_all(self):
        _r = [*self.response_receiver]
        for request_id in _r:
            if _task := self.response_receiver.get(request_id):
                _task.cancel()
                del self.response_receiver[request_id]

    @witch_doctor.WitchDoctor.injection
    async def antenna(self, request: Request, antenna: Antenna):
        async for data in antenna.subscribe(request.request_id):
            try:
                if isinstance(data, bytes):
                    data = data.decode()
                _response = Response.create(
                    request_id=request.request_id, header={}, payload=data
                )
                await self.ws.send(_response.json())
            except Exception as e:
                logging.error(e)

    async def close(self, close_code: CloseCode = CloseCode.NORMAL_CLOSURE):
        self._unregister_all()
        await self.ws.close(close_code)
