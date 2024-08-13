from typing import Coroutine, Callable

import meeseeks

from xraptor.domain.methods import MethodType


@meeseeks.OnlyOne(by_args_hash=True)
class Route:
    __slots__ = ["name", "_map"]

    def __init__(self, name: str):
        self.name = name
        self._map: dict[MethodType, Callable[..., Coroutine]] = {}

    def as_get(self, fn):
        self._map.update({MethodType.GET: fn})

    def as_post(self, fn):
        self._map.update({MethodType.POST: fn})

    def as_sub(self, fn):
        self._map.update({MethodType.SUB: fn})

    def as_unsub(self, fn):
        self._map.update({MethodType.UNSUB: fn})

    def get_match_map(self):
        return {f"{self.name}:{m.value}": self._map[m] for m in self._map}
