from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import AsyncIterator, Awaitable


class Antenna(ABC):

    @abstractmethod
    @asynccontextmanager
    def subscribe(self, key: str) -> AsyncIterator[str]:
        pass

    @abstractmethod
    def post(self, key: str, message: str) -> Awaitable:
        pass