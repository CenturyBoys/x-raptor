"""
Extras import
"""

from xraptor.antenna_implementations.memory import MemoryAntenna
from xraptor.core.interfaces import Antenna as IAntenna

__all__ = ["IAntenna", "MemoryAntenna"]

# Redis edition extra
try:
    import redis.asyncio as redis  # noqa: F401

    from .redis import ConfigAntenna, RedisAntenna

    __all__ += ["ConfigAntenna", "RedisAntenna"]
except ImportError:  # pragma: no cover
    pass
