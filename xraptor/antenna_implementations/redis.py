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

    async def subscribe(self, antenna_id: str) -> AsyncIterator[str]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(antenna_id)
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield message["data"]

    async def post(self, antenna_id: str, message: str):
        await self._redis.publish(antenna_id, message)

    async def is_alive(self, antenna_id: str) -> bool:
        num_subscribers = await self._redis.execute_command("PUBSUB", "NUMSUB", antenna_id)
        return bool(num_subscribers[1])
