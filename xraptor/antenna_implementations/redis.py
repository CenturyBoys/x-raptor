from typing import AsyncIterator

import redis.asyncio as redis
from decouple import config

from xraptor.core.interfaces import Antenna


class RedisAntenna(Antenna):

    def __init__(self):
        try:
            self._redis = redis.Redis.from_url(url=config("X_RAPTOR_REDIS_URL"))
        except Exception as e:
            print(e)

    async def subscribe(self, key: str) -> AsyncIterator[str]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(key)
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield message["data"]

    async def post(self, key: str, message: str):
        await self._redis.publish(key, message)
