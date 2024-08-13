"""
Import of  default state and extras
"""

__all__ = []

# Redis edition extra
try:
    import redis.asyncio as redis
    from .redis import RedisAntenna

    __all__ += "RedisAntenna"
except ImportError as error:  # pragma: no cover
    pass
