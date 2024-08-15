from abc import ABC, abstractmethod
from typing import AsyncIterator, Awaitable


class Antenna(ABC):

    @abstractmethod
    def subscribe(self, antenna_id: str) -> AsyncIterator[str]:
        """
        async generator that will yield message from the key's channel
        :param antenna_id: pubsub channel
        :return: str message async generator
        """

    @abstractmethod
    def post(self, antenna_id: str, message: str) -> Awaitable:
        """
        async function that will publish a message to a key's channel
        :param antenna_id: pubsub channel
        :param message: message
        :return:
        """

    @abstractmethod
    def is_alive(self, antenna_id: str) -> Awaitable[bool]:
        """
        verify that antenna_id still alive
        :param antenna_id:
        :return:
        """
