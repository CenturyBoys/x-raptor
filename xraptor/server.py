import asyncio
from typing import Self, Callable, Type, Awaitable

import witch_doctor
from websockets import serve

from xraptor import antenna_implementations as antennas
from xraptor.core.interfaces import Antenna
from xraptor.domain.methods import MethodType
from xraptor.domain.response import Response
from xraptor.domain.route import Route
from xraptor.handler import Handler


class XRaptor:
    _routes: list[Route] = []
    _map: dict = {}
    _antenna_cls: Type[object] = None

    def __init__(self, ip: str, port: int):
        self._ip = ip
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

    @classmethod
    def _load_oic(cls):
        """
        load oic container with the registered antenna implementation
        :return:
        """
        if cls._antenna_cls is None:
            cls._antenna_cls = antennas.RedisAntenna

        assert issubclass(
            cls._antenna_cls, Antenna
        ), "antenna is not subtype of {}".format(Antenna)

        container = witch_doctor.WitchDoctor.container()
        container(
            Antenna,
            cls._antenna_cls,
            witch_doctor.InjectionType.FACTORY,
        )
        witch_doctor.WitchDoctor.load_container()

    def load_routes(self) -> Self:
        """
        load all registered routes on server
        :return:
        """
        [self._map.update(r.get_match_map()) for r in self._routes]
        self._load_oic()
        return self

    async def serve(self):
        """
        start serve
        :return:
        """
        async with serve(Handler.watch, self._ip, self._port) as server:
            self._server = server
            while True:
                await asyncio.sleep(10)

    @classmethod
    def register(cls, name: str) -> Route:
        """
        register a route by name and return a Route instance that allow you to register as one of possible route types
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
