import logging
from typing import AsyncIterator, TypedDict

import redis.asyncio as redis

from xraptor.core.interfaces import Antenna


class ConfigAntenna(TypedDict):
    url: str


class RedisAntenna(Antenna):
    _config: ConfigAntenna = {}

    def __init__(self):
        try:
            self._redis = redis.Redis.from_url(url=self._config["url"])
        except Exception as error:  # pylint: disable=W0718
            logging.error(error)

    async def subscribe(self, antenna_id: str) -> AsyncIterator[str]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(antenna_id)
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield message["data"]

    async def post(self, antenna_id: str, message: str):
        await self._redis.publish(antenna_id, message)

    async def is_alive(self, antenna_id: str) -> bool:
        num_subscribers = await self._redis.execute_command(
            "PUBSUB", "NUMSUB", antenna_id
        )
        return bool(num_subscribers[1])

    @classmethod
    def set_config(cls, config: ConfigAntenna):
        cls._config = config
