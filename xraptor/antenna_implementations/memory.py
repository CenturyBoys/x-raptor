from asyncio import Queue
from collections.abc import AsyncIterator
from typing import ClassVar

from xraptor.core.interfaces import Antenna

# Sentinel used to unblock a subscribe() that is parked on queue.get() when
# stop_listening() is called on that subscription.
_STOP = object()


class MemoryAntenna(Antenna):
    # Shared across every instance created by the DI factory. NOT a singleton:
    # each subscription gets its own instance (and its own _running/_channel),
    # so stopping one subscriber no longer stops the others.
    _queues: ClassVar[dict[str, Queue]] = {}
    _subscribers: ClassVar[dict[str, int]] = {}
    _config: ClassVar[dict] = {}

    def __init__(self) -> None:
        self._running = True
        self._channel: str | None = None

    async def subscribe(self, antenna_id: str) -> AsyncIterator[str]:
        queue = self._queues.setdefault(antenna_id, Queue())
        self._channel = antenna_id
        self._running = True
        self._subscribers[antenna_id] = self._subscribers.get(antenna_id, 0) + 1
        try:
            while self._running:
                message = await queue.get()  # event-driven, no polling latency
                if message is _STOP:
                    break
                yield message
        finally:
            self._release(antenna_id)

    async def post(self, antenna_id: str, message: str) -> None:
        # Pub/sub semantics: deliver only when there is an active subscriber;
        # otherwise drop (avoids leaving orphan queues around forever).
        queue = self._queues.get(antenna_id)
        if queue is not None:
            await queue.put(message)

    async def stop_listening(self) -> None:
        self._running = False
        if self._channel is not None:
            queue = self._queues.get(self._channel)
            if queue is not None:
                queue.put_nowait(_STOP)

    async def is_alive(self, antenna_id: str) -> bool:
        return self._subscribers.get(antenna_id, 0) > 0

    def _release(self, antenna_id: str) -> None:
        remaining = self._subscribers.get(antenna_id, 0) - 1
        if remaining > 0:
            self._subscribers[antenna_id] = remaining
        else:
            self._subscribers.pop(antenna_id, None)
            self._queues.pop(antenna_id, None)

    @classmethod
    def set_config(cls, config: dict) -> None:
        pass
