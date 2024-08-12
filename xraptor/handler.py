import json

import websockets

import xraptor
from xraptor.connection import Connection
from xraptor.domain.methods import MethodType
from xraptor.domain.request import Request


class Handler:

    @staticmethod
    async def watch(websocket: websockets.WebSocketServerProtocol):
        connection = Connection.from_ws(websocket)
        try:
            async for message in connection.ws:
                request = Request.from_message(message)
                await Handler._handle_request(request, connection)
        except websockets.exceptions.ConnectionClosed as e:
            print(f"Connection closed cleanly: {e.code}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            connection.unregister_all()

    @staticmethod
    async def _handle_request(request: Request, connection: Connection):
        try:
            result = "Not registered"
            if fn := xraptor.XRaptor.route_matcher(request.method, request.route):
                if (
                    request.method == MethodType.GET.value
                    or request.method == MethodType.POST.value
                ):
                    result = await fn(request.payload)
                if request.method == MethodType.SUB.value:
                    connection.register_response_receiver(request)
                    result = await fn(request.payload, request.request_id)
                #     If fail must close it
                if request.method == MethodType.UNSUB.value:
                    result = await fn(request.payload, request.request_id)
                    connection.unregister_response_receiver(request)
            if result:
                _data = json.loads(result)
                _m = {
                    "payload": _data,
                    "request_id": request.request_id
                }
                await connection.ws.send(json.dumps(_m).encode())
        except Exception as e:
            print(e)
