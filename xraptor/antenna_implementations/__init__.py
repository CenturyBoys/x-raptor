"""
Extras import
"""

from xraptor.antenna_implementations.memory import MemoryAntenna
from xraptor.core.interfaces import Antenna as IAntenna

__all__ = ["IAntenna", "MemoryAntenna"]

# Redis edition extra
try:
    import redis.asyncio as redis
    from .redis import RedisAntenna, ConfigAntenna

    __all__ += "RedisAntenna"
    __all__ += "ConfigAntenna"
except ImportError as error:  # pragma: no cover
    pass
