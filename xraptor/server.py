import asyncio
import logging
import re
import signal
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import ClassVar, Self
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
    _routes: ClassVar[list[Route]] = []
    _map: ClassVar[dict] = {}
    _antenna_cls: ClassVar[type[Antenna] | None] = None
    _middlewares: ClassVar[list[MiddlewareConfig]] = []

    def __init__(self, ip_address: str, port: int):
        self._ip = ip_address
        self._port = port
        self._server = None
        self._stop_event: asyncio.Event | None = None

    @classmethod
    def set_antenna(cls, antenna: type[Antenna]):
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
        if cls._antenna_cls is None or not issubclass(cls._antenna_cls, Antenna):
            raise TypeError(f"antenna is not subtype of {Antenna}")
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
        # witch_doctor não tem stubs; a injeção retorna Any em tempo de type-check
        return cls._get_antenna()  # type: ignore[no-any-return]  # pylint: disable=E1120

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
        start serve until stop() is called (or SIGTERM/SIGINT is received),
        then shut down gracefully closing the server and its connections.
        :return:
        """
        self._stop_event = asyncio.Event()
        async with serve(self._watch, self._ip, self._port) as server:
            self._server = server
            self._install_signal_handlers()
            await self._stop_event.wait()

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self.stop)
            except (NotImplementedError, RuntimeError):
                # signal handlers may be unavailable (e.g. Windows, non-main thread)
                logging.debug("could not install signal handler for %s", sig)

    def stop(self) -> None:
        """Signal the serve() loop to shut down gracefully."""
        if self._stop_event is not None:
            self._stop_event.set()

    @classmethod
    def register(cls, name: str) -> Route:
        """
        register a route by name and return a Route instance that allow you to register
        as one of possible route types
        :param name: route name
        :return:
        """
        # Route is a singleton per name (meeseeks.OnlyOne), so re-registering the
        # same path returns the same object — avoid appending duplicates.
        _route = Route(name)
        if _route not in cls._routes:
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
        except websockets.exceptions.ConnectionClosed:
            # expected when a client disconnects — not an error, no traceback
            logging.debug("connection closed by peer")
            close_code = CloseCode.GOING_AWAY
        except websockets.exceptions.InvalidHandshake as error:
            logging.exception(error)
            close_code = CloseCode.TLS_HANDSHAKE
        except websockets.exceptions.WebSocketException as error:
            logging.exception(error)
            close_code = CloseCode.PROTOCOL_ERROR
        except Exception as error:  # pylint: disable=W0718
            logging.exception(error)
            close_code = CloseCode.ABNORMAL_CLOSURE
        finally:
            await connection.close(close_code=close_code)
            del connection

    @staticmethod
    async def _handle_request(message: str | bytes, connection: Connection):
        try:
            request = Request.from_message(message)
        except Exception as error:  # pylint: disable=W0718
            logging.exception(error)
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
            logging.exception(error)
            _response = Response.create(
                request_id=request.request_id,
                header={},
                payload='{"message": "fail"}',
                method=request.method,
            )
            await connection.ws_server.send(_response.json())

    @staticmethod
    async def _subscribe(
        request: Request,
        connection: Connection,
        func: Callable[[Request], Awaitable[Response | None]],
    ) -> Response | None:
        try:
            connection.register_response_receiver(request)
            return await func(request)
        except Exception as error:  # pylint: disable=W0718
            logging.exception(error)
            await connection.unregister_response_receiver(request)
            return None
