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
    ws_server: WebSocketServerProtocol
    connection_id: str
    response_receiver: dict = field(default_factory=dict)

    @classmethod
    def from_ws(cls, ws_server: WebSocketServerProtocol):
        return cls(
            path=ws_server.path,
            connection_hash=ws_server.__hash__(),  # pylint: disable=C2801
            remote_ip=ws_server.remote_address[0],
            ws_server=ws_server,
            connection_id=str(uuid4()),
        )

    def register_response_receiver(self, request: Request):
        self.response_receiver.update(
            {
                request.request_id: self.antenna(request=request),
            }
        )

    async def unregister_response_receiver(self, request: Request):
        if request.request_id in self.response_receiver:
            _antenna, _task = self.response_receiver[request.request_id]
            await _antenna.stop_listening()
            _task.cancel()
            del self.response_receiver[request.request_id]

    async def _unregister_all(self):
        _r = [*self.response_receiver]
        for request_id in _r:
            if request_id in self.response_receiver:
                _antenna, _task = self.response_receiver[request_id]
                await _antenna.stop_listening()
                _task.cancel()
                del self.response_receiver[request_id]

    @witch_doctor.WitchDoctor.injection
    def antenna(self, request: Request, antenna: Antenna) -> tuple[Antenna, asyncio.Task]:
        async def listener():
            async for data in antenna.subscribe(request.request_id):
                try:
                    if isinstance(data, bytes):
                        data = data.decode()
                    _response = Response.create(
                        request_id=request.request_id,
                        header={},
                        payload=data,
                        method=request.method,
                    )
                    await self.ws_server.send(_response.json())
                except Exception as error:  # pylint: disable=W0718
                    logging.error(error)
        return antenna, asyncio.create_task(listener())

    async def close(self, close_code: CloseCode = CloseCode.NORMAL_CLOSURE):
        await self._unregister_all()
        await self.ws_server.close(close_code)
