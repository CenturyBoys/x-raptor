from typing import Coroutine, Callable

import meeseeks

from xraptor.domain.methods import MethodType


@meeseeks.OnlyOne(by_args_hash=True)
class Route:
    def __init__(self, name: str):
        self.name = name
        self.__map: dict[MethodType, Callable[..., Coroutine]] = {}

    def as_get(self, fn):
        self.__map.update({MethodType.GET: fn})

    def as_post(self, fn):
        self.__map.update({MethodType.POST: fn})

    def as_sub(self, fn):
        self.__map.update({MethodType.SUB: fn})

    def as_unsub(self, fn):
        self.__map.update({MethodType.UNSUB: fn})

    def get_match_map(self):
        return {f"{self.name}:{m.value}": self.__map[m] for m in self.__map}
