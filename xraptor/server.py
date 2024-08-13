import asyncio
from typing import Self, Callable, Coroutine, Type

import witch_doctor
from websockets import serve

from xraptor import antenna_implementations as antennas
from xraptor.core.interfaces import Antenna
from xraptor.domain.methods import MethodType
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
    def _load_oic(cls):
        if cls._antenna_cls is None:
            cls._antenna_cls = antennas.RedisAntenna

        assert issubclass(cls._antenna_cls, Antenna), "antenna is not subtype of {}".format(Antenna)

        container = witch_doctor.WitchDoctor.container()
        container(
            Antenna,
            cls._antenna_cls,
            witch_doctor.InjectionType.SINGLETON,
        )
        witch_doctor.WitchDoctor.load_container()

    def load_routes(self) -> Self:
        [self._map.update(r.get_match_map()) for r in self._routes]
        self._load_oic()
        return self

    async def serve(self):
        async with serve(Handler.watch, self._ip, self._port) as server:
            self._server = server
            await asyncio.Future()

    @classmethod
    def register(cls, name: str) -> Route:
        _route = Route(name)
        cls._routes.append(_route)
        return _route

    @classmethod
    def route_matcher(
            cls, method: MethodType, name: str
    ) -> Callable[..., Coroutine] | None:
        key = f"{name}:{method.value}"
        return cls._map.get(key)
