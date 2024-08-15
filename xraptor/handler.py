import asyncio
import logging
from typing import Callable, Awaitable

import websockets
from websockets.frames import CloseCode

import xraptor
from xraptor.connection import Connection
from xraptor.domain.methods import MethodType
from xraptor.domain.request import Request
from xraptor.domain.response import Response


class Handler:

    @staticmethod
    async def watch(websocket: websockets.WebSocketServerProtocol):
        connection = Connection.from_ws(websocket)
        close_code: CloseCode = CloseCode.NORMAL_CLOSURE
        try:
            async for message in connection.ws:
                await Handler._handle_request(message, connection)
        except websockets.exceptions.ConnectionClosed as e:
            logging.error(e)
            close_code = CloseCode.GOING_AWAY
        except websockets.exceptions.InvalidHandshake as e:
            logging.error(e)
            close_code = CloseCode.TLS_HANDSHAKE
        except websockets.exceptions.WebSocketException as e:
            logging.error(e)
            close_code = CloseCode.PROTOCOL_ERROR
        except Exception as e:
            logging.error(e)
            close_code = CloseCode.ABNORMAL_CLOSURE
        finally:
            await connection.close(close_code=close_code)
            del connection

    @staticmethod
    async def _handle_request(message: str | bytes, connection: Connection):
        try:
            request = Request.from_message(message)
        except AssertionError:
            return

        try:
            result = None
            if fn := xraptor.XRaptor.route_matcher(request.method, request.route):
                if (
                    request.method == MethodType.GET
                    or request.method == MethodType.POST
                ):
                    result = await fn(request)
                if request.method == MethodType.SUB:
                    result = await Handler._subscribe(request, connection, fn)
                if request.method == MethodType.UNSUB:
                    result = await fn(request)
                    connection.unregister_response_receiver(request)

                if result is not None:
                    await connection.ws.send(result.json())
                return
            await connection.ws.send(
                Response.create(
                    request_id=request.request_id,
                    header={},
                    payload='{"message": "Not registered"}',
                ).json()
            )
        except Exception as e:
            logging.error(e)
            _response = Response.create(
                request_id=request.request_id, header={}, payload='{"message": "fail"}'
            )
            await connection.ws.send(_response.json())

    @staticmethod
    async def _subscribe(
        request: Request, connection: Connection, fn: Callable
    ) -> Awaitable[Response | None]:
        try:
            connection.register_response_receiver(request)
            result = await fn(request)
            return result
        except Exception as e:
            logging.error(e)
            connection.unregister_response_receiver(request)
