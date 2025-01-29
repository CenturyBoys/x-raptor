import asyncio
from asyncio import Queue
from typing import AsyncIterator

import meeseeks

from xraptor.core.interfaces import Antenna


@meeseeks.OnlyOne()
class MemoryAntenna(Antenna):
    _queues = {}
    _config = {}

    def __init__(self):
        self._running = True

    async def subscribe(self, antenna_id: str) -> AsyncIterator:
        if antenna_id not in self._queues:
            self._queues.update({antenna_id: Queue()})
        _q: Queue = self._queues[antenna_id]
        while True:
            if not self._running:
                break
            if _q.empty() is False:
                yield await _q.get()
            await asyncio.sleep(0.05)

    async def post(self, antenna_id: str, message: str):
        if antenna_id not in self._queues:
            self._queues.update({antenna_id: Queue()})
        _q: Queue = self._queues[antenna_id]
        await _q.put(message)

    async def stop_listening(self):
        self._running = False

    async def is_alive(self, antenna_id: str) -> bool:
        return antenna_id in self._queues

    @classmethod
    def set_config(cls, config: dict):
        pass
