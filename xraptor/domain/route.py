from typing import Callable, Awaitable

import meeseeks

from xraptor.domain.methods import MethodType
from xraptor.domain.request import Request
from xraptor.domain.response import Response


@meeseeks.OnlyOne(by_args_hash=True)
class Route:
    __slots__ = ["name", "_map"]

    def __init__(self, name: str):
        self.name = name
        self._map: dict[
            MethodType, Callable[[Request], Awaitable[Response | None]]
        ] = {}

    def as_get(self, func: Callable[[Request], Awaitable[Response | None]]):
        self._map.update({MethodType.GET: func})

    def as_post(self, func: Callable[[Request], Awaitable[Response | None]]):
        self._map.update({MethodType.POST: func})

    def as_sub(self, func: Callable[[Request], Awaitable[Response | None]]):
        self._map.update({MethodType.SUB: func})

    def as_unsub(self, func: Callable[[Request], Awaitable[Response | None]]):
        self._map.update({MethodType.UNSUB: func})

    def as_put(self, func: Callable[[Request], Awaitable[Response | None]]):
        self._map.update({MethodType.PUT: func})

    def get_match_map(self):
        return {f"{self.name}:{m.value}": v for m, v in self._map.items()}
