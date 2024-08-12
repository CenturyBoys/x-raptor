import asyncio
from contextlib import asynccontextmanager
from typing import Self, Callable, Coroutine

from websockets import serve

from xraptor.domain.methods import MethodType
from xraptor.domain.route import Route
from xraptor.handler import Handler


class XRaptor:
    _routes: list[Route] = []
    _map: dict = {}

    def __init__(self, ip: str, port: int):
        self.__ip = ip
        self.__port = port
        self.__server = None

    def load_routes(self) -> Self:
        [self._map.update(r.get_match_map()) for r in self._routes]
        return self

    async def serve(self):
        async with serve(Handler.watch, self.__ip, self.__port) as server:
            self.__server = server
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
        key = f"{name}:{method}"
        return cls._map.get(key)
