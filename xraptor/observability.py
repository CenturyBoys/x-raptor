import time


class Metrics:
    """In-process counters/gauges for the server.

    asyncio is single-threaded and these are only mutated from the event loop, so
    plain integer counters are safe (no locking needed).
    """

    __slots__ = (
        "_start",
        "connections_active",
        "connections_total",
        "request_errors_total",
        "requests_total",
    )

    def __init__(self) -> None:
        self.connections_total = 0
        self.connections_active = 0
        self.requests_total = 0
        self.request_errors_total = 0
        self._start = time.monotonic()

    def uptime_seconds(self) -> float:
        return time.monotonic() - self._start

    def health(self) -> dict:
        return {
            "status": "ok",
            "uptime_seconds": round(self.uptime_seconds(), 1),
            "active_connections": self.connections_active,
        }

    def prometheus(self) -> str:
        """Render metrics in the Prometheus text exposition format."""
        metrics = [
            (
                "xraptor_connections_total",
                "counter",
                "Total connections accepted",
                self.connections_total,
            ),
            (
                "xraptor_connections_active",
                "gauge",
                "Currently open connections",
                self.connections_active,
            ),
            (
                "xraptor_requests_total",
                "counter",
                "Total requests handled",
                self.requests_total,
            ),
            (
                "xraptor_request_errors_total",
                "counter",
                "Total request errors",
                self.request_errors_total,
            ),
            (
                "xraptor_uptime_seconds",
                "gauge",
                "Server uptime in seconds",
                round(self.uptime_seconds(), 1),
            ),
        ]
        lines = []
        for name, kind, help_text, value in metrics:
            lines.append(f"# HELP {name} {help_text}.")
            lines.append(f"# TYPE {name} {kind}")
            lines.append(f"{name} {value}")
        return "\n".join(lines) + "\n"
