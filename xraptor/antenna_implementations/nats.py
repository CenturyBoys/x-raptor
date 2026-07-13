import asyncio
import contextlib
from collections.abc import AsyncIterator
from typing import ClassVar, TypedDict

import nats
from nats.aio.client import Client
from nats.aio.subscription import Subscription

from xraptor.core.interfaces import Antenna


class ConfigNatsAntenna(TypedDict):
    """Expected config shape for NatsAntenna (passed to set_config).

    ``servers`` is a NATS URL or a list of URLs, e.g. ``"nats://localhost:4222"``.
    """

    servers: str | list[str]


class NatsAntenna(Antenna):
    """NATS-backed antenna (core pub/sub over subjects).

    A single client connection is shared across every instance created by the DI
    factory (NATS multiplexes all subscriptions over one connection); only the
    per-subscription state is instance-local.

    Note: NATS core exposes no per-subject subscriber count, so ``is_alive`` always
    reports ``True``. Member liveness is handled at the connection level instead
    (websocket keepalive + disconnect cleanup); ``Broadcast`` auto-pruning via the
    antenna is therefore a no-op with this backend.
    """

    _config: ClassVar[dict] = {}
    _client: ClassVar[Client | None] = None
    _connect_lock: ClassVar[asyncio.Lock | None] = None

    def __init__(self) -> None:
        self._running = True
        self._sub: Subscription | None = None

    @classmethod
    async def _get_client(cls) -> Client:
        """Lazily open (and reuse) the shared NATS connection."""
        if cls._client is not None and cls._client.is_connected:
            return cls._client
        if cls._connect_lock is None:
            cls._connect_lock = asyncio.Lock()
        async with cls._connect_lock:
            if cls._client is None or not cls._client.is_connected:
                servers = cls._config.get("servers")
                if not servers:
                    raise ValueError(
                        "NatsAntenna is not configured; call "
                        "NatsAntenna.set_config({'servers': ...}) before use"
                    )
                cls._client = await nats.connect(servers)
            return cls._client

    async def subscribe(self, antenna_id: str) -> AsyncIterator[str]:
        client = await self._get_client()
        self._sub = await client.subscribe(antenna_id)
        try:
            async for msg in self._sub.messages:
                if not self._running:
                    break
                data = msg.data
                yield data.decode() if isinstance(data, bytes) else data
        finally:
            with contextlib.suppress(Exception):
                await self._sub.unsubscribe()

    async def stop_listening(self) -> None:
        self._running = False
        if self._sub is not None:
            # Ends the messages iterator so subscribe() can exit cleanly.
            with contextlib.suppress(Exception):
                await self._sub.unsubscribe()

    async def post(self, antenna_id: str, message: str) -> None:
        client = await self._get_client()
        await client.publish(antenna_id, message.encode())

    async def is_alive(self, antenna_id: str) -> bool:
        # NATS core has no per-subject subscriber count; see the class docstring.
        return True

    @classmethod
    def set_config(cls, config: dict) -> None:
        cls._config = config
        cls._client = None  # re-connect with the new config on next use
