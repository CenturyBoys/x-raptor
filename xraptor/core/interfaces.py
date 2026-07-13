from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class Antenna(ABC):
    @abstractmethod
    def subscribe(self, antenna_id: str) -> AsyncIterator[str]:
        """
        async generator that will yield message from the key's channel
        :param antenna_id: pubsub channel
        :return: str message async generator
        """

    @abstractmethod
    async def stop_listening(self) -> None:
        """
        stop listening messages
        :param antenna_id: pubsub channel
        :return:
        """

    @abstractmethod
    async def post(self, antenna_id: str, message: str) -> None:
        """
        async function that will publish a message to a key's channel
        :param antenna_id: pubsub channel
        :param message: message
        :return:
        """

    @abstractmethod
    async def is_alive(self, antenna_id: str) -> bool:
        """
        verify that antenna_id still alive
        :param antenna_id:
        :return:
        """

    @classmethod
    @abstractmethod
    def set_config(cls, config: dict) -> None:
        """
        set config map for this antenna
        :param config:
        :return:
        """
