# X-raptor

[![CI](https://github.com/CenturyBoys/x-raptor/actions/workflows/ci.yml/badge.svg)](https://github.com/CenturyBoys/x-raptor/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/CenturyBoys/x-raptor/branch/main/graph/badge.svg)](https://codecov.io/gh/CenturyBoys/x-raptor)
[![PyPI](https://img.shields.io/pypi/v/xraptor)](https://pypi.org/project/xraptor/)
[![Python](https://img.shields.io/pypi/pyversions/xraptor)](https://pypi.org/project/xraptor/)
[![License](https://img.shields.io/github/license/CenturyBoys/x-raptor)](https://github.com/CenturyBoys/x-raptor/blob/main/LICENSE)

![banner](https://raw.githubusercontent.com/CenturyBoys/x-raptor/main/docs/banner.jpeg)

```
By: CenturyBoys
```

Fast as a WebSocket, easy as HTTP. X-raptor is an abstraction over the
[websockets](https://pypi.org/project/websockets/) package that lets you register
`get`, `post`, `put`, `sub` and `unsub` asynchronous handlers with HTTP-like route
registration. Every message on the wire is a **request** or a **response** object.

To allow multiple asynchronous responses per route, X-raptor uses each
`request_id` as an **antenna** — a pubsub channel that `yield`s string messages
back to the client.

> ⚠️ **Pre-1.0:** the public API may still change between minor versions. Pin a
> version if you depend on it.

## 📦 Installation

```shell
pip install xraptor
# or with uv
uv add xraptor
```

Optional [extras](#-extras): `redis_version` (Redis antenna) and `uvloop` (faster
event loop).

## 🚀 Quick start

Register a route with the `as_<method>` decorators, then load the routes and serve:

```python
import asyncio

import xraptor


@xraptor.XRaptor.register("/send_message_to_chat_room").as_post
async def send_message(request: xraptor.Request) -> xraptor.Response:
    return xraptor.Response.create(
        request_id=request.request_id,
        header={},
        payload='{"ok": true}',
        method=request.method,
    )


_xraptor = xraptor.XRaptor("localhost", 8765)
_xraptor.set_antenna(xraptor.antennas.MemoryAntenna)

asyncio.run(_xraptor.load_routes().serve())
```

Routes are registered at import time with the decorators
(`as_get`, `as_post`, `as_put`, `as_sub`, `as_unsub`), then loaded into the server
with `load_routes()`.

## 📨 Message format

Every inbound message is a **request** and every outbound message is a **response**,
both JSON objects. `payload` is always a string (usually JSON-encoded).

**Request**

```json
{
  "request_id": "01H...",
  "payload": "{\"text\": \"hello\"}",
  "header": {"token": "..."},
  "route": "/send_message_to_chat_room",
  "method": "POST"
}
```

**Response**

```json
{
  "request_id": "01H...",
  "payload": "{\"ok\": true}",
  "header": {},
  "method": "POST"
}
```

`method` is case-insensitive on the way in. Unmatched routes get a
`{"message": "Not registered"}` response; malformed messages are dropped.

## 🖥️ Start server

```python
import asyncio

import xraptor

_xraptor = xraptor.XRaptor("localhost", 8765)

xraptor.antennas.RedisAntenna.set_config({"url": "redis://:@localhost:6379/0"})
_xraptor.set_antenna(xraptor.antennas.RedisAntenna)

asyncio.run(_xraptor.load_routes().serve())
```

`serve()` runs until `stop()` is called or a `SIGTERM`/`SIGINT` is received, then
shuts down gracefully (closing the server and its connections). Connection limits
can be tuned on the constructor:

```python
_xraptor = xraptor.XRaptor(
    "localhost",
    8765,
    max_size=2**20,      # max inbound payload in bytes (DoS guard)
    max_queue=32,        # per-connection backpressure
    ping_interval=20,    # keepalive; detects half-open connections
    ping_timeout=20,
)
```

## 🔗 Middleware

Middleware functions run before route handlers. They can inspect/modify requests,
short-circuit responses, or handle cross-cutting concerns like **authentication**
and **rate limiting** (there is no built-in auth or rate limiting — this is the hook).

```python
import xraptor


@xraptor.XRaptor.middleware(priority=1)
async def auth_middleware(request: xraptor.Request, connection) -> xraptor.Response | None:
    if not request.header.get("token"):
        return xraptor.Response.create(
            request_id=request.request_id,
            header={},
            payload='{"error": "unauthorized"}',
            method=request.method,
        )
    return None  # continue to the next middleware/handler
```

- **Priority**: lower numbers run first; each priority must be unique.
- **Pattern matching**: restrict a middleware to routes with an optional regex.
- **Short-circuiting**: return a `Response` to stop the chain and skip the handler;
  return `None` to continue.

```python
@xraptor.XRaptor.middleware(priority=2, pattern=r"^/api/.*")
async def api_only_middleware(request, connection):
    # only runs for routes starting with /api/
    return None
```

## 📡 Antenna

An antenna is the pubsub backend. There is a default in-memory antenna (not
recommended for production); you can implement your own against the
[interface](./xraptor/core/interfaces.py) or use one of the extras.

```python
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class Antenna(ABC):
    @abstractmethod
    def subscribe(self, antenna_id: str) -> AsyncIterator[str]:
        """async generator that yields messages from the channel"""

    @abstractmethod
    async def stop_listening(self) -> None:
        """stop listening for messages on this subscription"""

    @abstractmethod
    async def post(self, antenna_id: str, message: str) -> None:
        """publish a message to a channel"""

    @abstractmethod
    async def is_alive(self, antenna_id: str) -> bool:
        """whether the channel still has an active subscriber"""

    @classmethod
    @abstractmethod
    def set_config(cls, config: dict) -> None:
        """set the config map for this antenna"""
```

Built-in implementations:

- `xraptor.antennas.MemoryAntenna` — in-memory, single process (default).
- `xraptor.antennas.RedisAntenna` — Redis pubsub (via the `redis_version` extra).
- `xraptor.antennas.NatsAntenna` — NATS core pubsub (via the `nats` extra).

> `is_alive` (used by `Broadcast` to prune dead members) needs a per-channel
> subscriber count, which only Redis exposes natively. On NATS it always returns
> `True`, so member cleanup relies on the connection layer (websocket keepalive +
> disconnect) instead.

## 📤 Broadcast

A broadcast room lets multiple members join a shared space and automatically
receive every message posted to it — like a chat room, without polling. It is
built on the registered antenna and auto-cleans disconnected members.

```python
class Broadcast:
    @classmethod
    def get(cls, broadcast_id: str) -> "Broadcast":
        """get (or create) a broadcast instance by id"""

    def add_member(self, member: str):
        """add a member (antenna id); opens the room on the first member"""

    def remove_member(self, member: str):
        """remove a member; closes the room when the last one leaves"""
```

## 📊 Observability

The server exposes two HTTP endpoints on the same port (intercepted before the
WebSocket handshake), enabled by default:

- **`GET /health`** — JSON liveness for load balancers:
  `{"status": "ok", "uptime_seconds": ..., "active_connections": ...}`.
- **`GET /metrics`** — Prometheus text format: `xraptor_connections_total`,
  `xraptor_connections_active`, `xraptor_requests_total`,
  `xraptor_request_errors_total`, `xraptor_uptime_seconds`.

Paths are configurable (or set to `None` to disable); counters are also readable
in-process via `XRaptor.get_metrics()`.

```python
_xraptor = xraptor.XRaptor(
    "localhost", 8765,
    health_path="/health",   # None to disable
    metrics_path="/metrics",  # None to disable
)
```

## ⚡ Performance

- Request/response (de)serialization uses [orjson](https://github.com/ijl/orjson).
- Install the `uvloop` extra and start the server with `XRaptor.run()` to use
  [uvloop](https://github.com/MagicStack/uvloop) when available (falling back to
  asyncio otherwise):

```python
_xraptor.load_routes().run()   # uvloop if installed, else asyncio.run
```

## 🧩 Extras

### Redis

Adds the [redis](https://pypi.org/project/redis/) package for the Redis antenna.

```shell
pip install 'xraptor[redis_version]'
# or
uv add 'xraptor[redis_version]'
```

Configure the connection string on the antenna via `set_config`:

```python
import xraptor

xraptor.antennas.RedisAntenna.set_config({"url": "redis://:@localhost:6379/0"})
```

### NATS

Adds [nats-py](https://pypi.org/project/nats-py/) for the NATS antenna.

```shell
pip install 'xraptor[nats]'
# or
uv add 'xraptor[nats]'
```

```python
import xraptor

xraptor.antennas.NatsAntenna.set_config({"servers": "nats://localhost:4222"})
```

### uvloop

Optional faster event loop (excluded on Windows).

```shell
pip install 'xraptor[uvloop]'
```

## 🧮 Full example

A minimal chat implementation exercising the `sub`, `post` and `unsub` routes
(uses the `redis_version` extra):

- Server: [example/server.py](./example/server.py)
- Client: [example/client.py](./example/client.py)

## 🗓️ Versioning & support

- **SemVer.** While on `0.x`, the public API may change between minor versions —
  pin a version if you depend on it. See the [CHANGELOG](./CHANGELOG.md).
- **Python support** follows a [SPEC 0](https://scientific-python.org/specs/spec-0000/)-style
  policy: a Python version is supported until roughly 3 years after its release.
  Currently tested on **3.11, 3.12, 3.13 and 3.14**.
- **Type-checked and typed:** the package ships a `py.typed` marker (PEP 561), so
  downstream type checkers see its annotations.
- **Path to 1.0** — the API will be frozen once these are in place: a stable
  `Antenna` interface, built-in observability (metrics/health), and validation
  under real-world load.

## 🛠️ Development

The project uses [uv](https://docs.astral.sh/uv/) and `ruff` + `mypy` + `pytest`.

```shell
uv sync --all-extras --dev   # install
uv run pytest                # tests (with coverage)
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy xraptor/         # type check
```

Load/soak testing lives in [`loadtest/`](./loadtest/) (run manually):

```shell
uv run python loadtest/run.py smoke      # quick sanity
uv run python loadtest/run.py all        # full load-ramp + broadcast + soak
```
