from abc import ABC, abstractmethod
from typing import AsyncIterator, Awaitable


class Antenna(ABC):

    @abstractmethod
    def subscribe(self, key: str) -> AsyncIterator[str]:
        """
        async generator that will yield message from the key's channel
        :param key: pubsub channel
        :return: str message async generator
        """
        pass

    @abstractmethod
    def post(self, key: str, message: str) -> Awaitable:
        """
        async function that will publish a message to a key's channel
        :param key: pubsub channel
        :param message: message
        :return:
        """
        pass
