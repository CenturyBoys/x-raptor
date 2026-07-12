from xraptor.observability import Metrics


def test_health_shape():
    _m = Metrics()
    _m.connections_active = 3
    _h = _m.health()
    assert _h["status"] == "ok"
    assert _h["active_connections"] == 3
    assert _h["uptime_seconds"] >= 0


def test_prometheus_format():
    _m = Metrics()
    _m.requests_total = 5
    _m.connections_total = 2
    _text = _m.prometheus()
    assert "# TYPE xraptor_requests_total counter" in _text
    assert "xraptor_requests_total 5" in _text
    assert "xraptor_connections_total 2" in _text
    assert _text.endswith("\n")
