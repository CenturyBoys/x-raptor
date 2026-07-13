from collections.abc import AsyncIterator
from typing import ClassVar, TypedDict

import redis.asyncio as redis

from xraptor.core.interfaces import Antenna


class ConfigAntenna(TypedDict):
    """Formato esperado da config do RedisAntenna (passado em set_config)."""

    url: str


class RedisAntenna(Antenna):
    _config: ClassVar[dict] = {}
    # Cliente compartilhado (com connection pool interno) entre todas as
    # instâncias criadas pela factory do DI. Só o pubsub é por-instância.
    _client: ClassVar["redis.Redis | None"] = None

    def __init__(self) -> None:
        self._running = True
        self._pubsub: redis.client.PubSub | None = None

    @classmethod
    def _get_client(cls) -> "redis.Redis":
        """Lazily create (and reuse) the shared Redis client."""
        if cls._client is None:
            url = cls._config.get("url")
            if not url:
                raise ValueError(
                    "RedisAntenna is not configured; call "
                    "RedisAntenna.set_config({'url': ...}) before use"
                )
            cls._client = redis.Redis.from_url(url=url)
        return cls._client

    async def subscribe(self, antenna_id: str) -> AsyncIterator[str]:
        self._pubsub = self._get_client().pubsub()
        await self._pubsub.subscribe(antenna_id)
        try:
            async for message in self._pubsub.listen():
                if not self._running:
                    break
                if message["type"] == "message":
                    data = message["data"]
                    yield data.decode() if isinstance(data, bytes) else data
        finally:
            await self._pubsub.unsubscribe(antenna_id)
            await self._pubsub.aclose()

    async def stop_listening(self) -> None:
        self._running = False
        if self._pubsub is not None:
            # Pushes an 'unsubscribe' message, unblocking the listen() loop so
            # it can observe _running and exit cleanly.
            await self._pubsub.unsubscribe()

    async def post(self, antenna_id: str, message: str) -> None:
        await self._get_client().publish(antenna_id, message)

    async def is_alive(self, antenna_id: str) -> bool:
        num_subscribers = await self._get_client().execute_command(
            "PUBSUB", "NUMSUB", antenna_id
        )
        return bool(num_subscribers[1])

    @classmethod
    def set_config(cls, config: dict) -> None:
        cls._config = config
        cls._client = None  # re-create the client with the new config on next use
