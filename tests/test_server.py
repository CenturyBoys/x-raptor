import asyncio
from unittest.mock import patch
from uuid import uuid4

import pytest
import witch_doctor

import xraptor
from xraptor.antenna_implementations.memory import MemoryAntenna
from xraptor.domain.methods import MethodType
from xraptor.domain.route import Route


def test_set_antenna_wrong_type():
    class Stub:
        pass

    with pytest.raises(TypeError):
        xraptor.XRaptor.set_antenna(Stub)


def test_set_antenna():
    with patch.object(
        witch_doctor.WitchDoctor,
        "load_container",
    ) as mock_x:
        xraptor.XRaptor.set_antenna(MemoryAntenna)
    assert mock_x.called


def test_get_antenna():
    xraptor.XRaptor.set_antenna(MemoryAntenna)
    _a = xraptor.XRaptor.get_antenna()
    assert isinstance(_a, MemoryAntenna)


def test_register():
    xraptor.XRaptor.set_antenna(MemoryAntenna)

    _r = xraptor.XRaptor.register("/test")
    assert isinstance(_r, Route)


def test_load_routes():
    xraptor.XRaptor.set_antenna(MemoryAntenna)

    @xraptor.XRaptor.register("/test").as_get
    async def y():
        pass

    _s = xraptor.XRaptor("localhost", 8756)
    with patch.object(
        witch_doctor.WitchDoctor,
        "load_container",
    ) as mock_x:
        _s.load_routes()

    assert mock_x.called
    assert "/test:GET" in _s._map


def test_route_matcher_not_registered():
    _fn = xraptor.XRaptor.route_matcher(MethodType.GET, f"/{uuid4()}")
    assert _fn is None


def test_route_matcher():
    xraptor.XRaptor.set_antenna(MemoryAntenna)

    @xraptor.XRaptor.register("/test").as_get
    async def y():
        pass

    _s = xraptor.XRaptor("localhost", 8756)
    _s.load_routes()
    _fn = _s.route_matcher(MethodType.GET, "/test")
    assert _fn


def test_register_no_duplicates():
    name = f"/{uuid4()}"
    _r1 = xraptor.XRaptor.register(name)
    _r2 = xraptor.XRaptor.register(name)
    assert _r1 is _r2
    assert xraptor.XRaptor._routes.count(_r1) == 1


def test_stop_without_serve_is_noop():
    _s = xraptor.XRaptor("localhost", 0)
    _s.stop()  # no serve() running yet -> must not raise


def test_serve_options_defaults_and_override():
    _s = xraptor.XRaptor("localhost", 0)
    assert _s._serve_options["max_size"] == 2**20
    _s2 = xraptor.XRaptor("localhost", 0, max_size=1024, max_queue=8)
    assert _s2._serve_options["max_size"] == 1024
    assert _s2._serve_options["max_queue"] == 8


@pytest.mark.asyncio
async def test_serve_graceful_stop():
    _s = xraptor.XRaptor("localhost", 0)  # port 0 -> OS picks a free port
    _task = asyncio.ensure_future(_s.serve())
    await asyncio.sleep(0.05)  # let the server bind
    _s.stop()
    # serve() must return promptly once stop() is signaled.
    await asyncio.wait_for(_task, timeout=2)
