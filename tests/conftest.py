import pytest

from xraptor.antenna_implementations.memory import MemoryAntenna
from xraptor.broadcaster import Broadcast


@pytest.fixture(autouse=True)
def _reset_shared_state():
    """Isolate tests: clear process-wide antenna/broadcast state between them."""
    MemoryAntenna._queues.clear()
    MemoryAntenna._subscribers.clear()
    Broadcast._broadcasts.clear()
    yield
    MemoryAntenna._queues.clear()
    MemoryAntenna._subscribers.clear()
    Broadcast._broadcasts.clear()
