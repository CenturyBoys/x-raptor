import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Self, Callable, Type, Awaitable
from uuid import uuid4

import websockets
import witch_doctor
from websockets import serve
from websockets.frames import CloseCode

from xraptor.connection import Connection
from xraptor.core.interfaces import Antenna
from xraptor.domain.methods import MethodType
from xraptor.domain.response import Response
from xraptor.domain.route import Route
from .domain.request import Request


@dataclass
class MiddlewareConfig:
    priority: int
    pattern: re.Pattern | None
    func: Callable[["Request", "Connection"], Awaitable["Response | None"]]


class XRaptor:
    _routes: list[Route] = []
    _map: dict = {}
    _antenna_cls: Type[object] = None
    _middlewares: list[MiddlewareConfig] = []

    def __init__(self, ip_address: str, port: int):
        self._ip = ip_address
        self._port = port
        self._server = None

    @classmethod
    def set_antenna(cls, antenna: Type[Antenna]):
        """
        set new antenna implementation
        :param antenna: class that implements all Antenna methods
        :return:
        """
        cls._antenna_cls = antenna
        cls._load_oic()

    @classmethod
    def _load_oic(cls):
        """
        load oic container with the registered antenna implementation
        :return:
        """
        assert issubclass(
            cls._antenna_cls, Antenna
        ), f"antenna is not subtype of {Antenna}"
        _container_name = str(uuid4())
        container = witch_doctor.WitchDoctor.container(_container_name)
        container(
            Antenna,
            cls._antenna_cls,
            witch_doctor.InjectionType.FACTORY,
        )
        witch_doctor.WitchDoctor.load_container(_container_name)

    @classmethod
    def get_antenna(cls) -> Antenna:
        """
        return the current antenna implementation
        :return: Antenna object instance
        """
        return cls._get_antenna()  # pylint: disable=E1120

    @classmethod
    @witch_doctor.WitchDoctor.injection
    def _get_antenna(cls, antenna: Antenna) -> Antenna:
        return antenna

    def load_routes(self) -> Self:
        """
        load all registered routes on server
        :return:
        """
        _ = [self._map.update(r.get_match_map()) for r in self._routes]
        self._load_oic()
        return self

    async def serve(self):
        """
        start serve
        :return:
        """
        async with serve(self._watch, self._ip, self._port) as server:
            self._server = server
            while True:
                await asyncio.sleep(10)

    @classmethod
    def register(cls, name: str) -> Route:
        """
        register a route by name and return a Route instance that allow you to register
        as one of possible route types
        :param name: route name
        :return:
        """
        _route = Route(name)
        cls._routes.append(_route)
        return _route

    @classmethod
    def route_matcher(
        cls, method: MethodType, name: str
    ) -> Callable[..., Awaitable[Response | None]] | None:
        """
        will return the registered async callback for the giving method and route name if registered
        :param method: on of the allowed MethodType
        :param name: route name
        :return:
        """
        key = f"{name}:{method.value}"
        return cls._map.get(key)

    @classmethod
    def middleware(cls, priority: int, pattern: str | None = None):
        """
        Decorator to register a middleware function.
        :param priority: execution order (lower runs first), must be unique
        :param pattern: optional regex pattern to match routes (None = all routes)
        :return: decorator
        """

        def decorator(
            func: Callable[[Request, Connection], Awaitable[Response | None]],
        ):
            for mw in cls._middlewares:
                if mw.priority == priority:
                    raise ValueError(
                        f"Middleware priority {priority} already registered"
                    )

            compiled_pattern = re.compile(pattern) if pattern else None
            cls._middlewares.append(
                MiddlewareConfig(
                    priority=priority,
                    pattern=compiled_pattern,
                    func=func,
                )
            )
            cls._middlewares.sort(key=lambda m: m.priority)
            return func

        return decorator

    @classmethod
    async def _run_middlewares(
        cls, request: Request, connection: Connection
    ) -> Response | None:
        """
        Execute all matching middlewares sequentially by priority.
        :return: Response if short-circuited, None to continue to handler
        """
        for mw in cls._middlewares:
            if mw.pattern is not None and not mw.pattern.match(request.route):
                continue
            result = await mw.func(request, connection)
            if result is not None:
                assert isinstance(
                    result, Response
                ), f"Middleware must return Response or None, got {type(result)}"
                return result
        return None

    @staticmethod
    async def _watch(websocket: websockets.WebSocketServerProtocol):
        connection = Connection.from_ws(websocket)
        close_code: CloseCode = CloseCode.NORMAL_CLOSURE
        try:
            async for message in connection.ws_server:
                await XRaptor._handle_request(message, connection)
        except websockets.exceptions.ConnectionClosed as error:
            logging.error(error)
            close_code = CloseCode.GOING_AWAY
        except websockets.exceptions.InvalidHandshake as error:
            logging.error(error)
            close_code = CloseCode.TLS_HANDSHAKE
        except websockets.exceptions.WebSocketException as error:
            logging.error(error)
            close_code = CloseCode.PROTOCOL_ERROR
        except Exception as error:  # pylint: disable=W0718
            logging.error(error)
            close_code = CloseCode.ABNORMAL_CLOSURE
        finally:
            await connection.close(close_code=close_code)
            del connection

    @staticmethod
    async def _handle_request(message: str | bytes, connection: Connection):
        try:
            request = Request.from_message(message)
        except Exception as error:  # pylint: disable=W0718
            logging.error(error)
            return

        try:
            middleware_result = await XRaptor._run_middlewares(request, connection)
            if middleware_result is not None:
                await connection.ws_server.send(middleware_result.json())
                return

            result = None
            if func := XRaptor.route_matcher(request.method, request.route):
                if request.method in (MethodType.GET, MethodType.POST, MethodType.PUT):
                    result = await func(request)
                if request.method == MethodType.SUB:
                    result = await XRaptor._subscribe(request, connection, func)
                if request.method == MethodType.UNSUB:
                    result = await func(request)
                    await connection.unregister_response_receiver(request)
                if result is not None:
                    await connection.ws_server.send(result.json())
                return
            await connection.ws_server.send(
                Response.create(
                    request_id=request.request_id,
                    header={},
                    payload='{"message": "Not registered"}',
                    method=request.method,
                ).json()
            )
        except Exception as error:  # pylint: disable=W0718
            logging.error(error)
            _response = Response.create(
                request_id=request.request_id,
                header={},
                payload='{"message": "fail"}',
                method=request.method,
            )
            await connection.ws_server.send(_response.json())

    @staticmethod
    async def _subscribe(
        request: Request, connection: Connection, func: Callable
    ) -> Awaitable[Response | None]:
        try:
            connection.register_response_receiver(request)
            return await func(request)
        except Exception as error:  # pylint: disable=W0718
            logging.error(error)
            await connection.unregister_response_receiver(request)
