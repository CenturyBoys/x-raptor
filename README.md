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

## ⚠️ Fast as a hell, CAUTION!!!

This package is being developed and is in the testing process. **🚨 NOT USE THIS PACKAGE IN PRODUCTION !!!**

Fast as websocket easy as http, this package is an abstraction of [websockets](https://pypi.org/project/websockets/)
package
to allow user to register `get`, `post`, `sub`, `unsub` asynchronous callbacks. For this all message must be a requests
or a response object.

To allow multiple asynchronous responses on routes X-raptor use the `request_id` as antenna. Those antennas are pubsub
channels that `yield` string messages.

### Registering a route

To register a route you can use the `xraptor.XRaptor.register` to get the route instance and use
the `as_` (`as_get`, `as_post`, `as_sub`, `as_unsub`,) decorator. See below an example

```python
import xraptor


@xraptor.XRaptor.register("/send_message_to_chat_room").as_post
async def send_message(
        request: xraptor.Request
) -> xraptor.Response:
    ...
```

### Start server

```python
import xraptor
import asyncio

_xraptor = xraptor.XRaptor("localhost", 8765)

xraptor.antennas.RedisAntenna.set_config({"url": "redis://:@localhost:6379/0"})

_xraptor.set_antenna(xraptor.antennas.RedisAntenna)

asyncio.run(_xraptor.load_routes().serve())
```

`serve()` runs until `stop()` is called or a `SIGTERM`/`SIGINT` is received, then
shuts down gracefully. Connection limits can be tuned on the constructor:

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

> **Auth & rate limiting** are not built in — implement them as
> [middleware](#-middleware) (the chain runs before every handler and can
> short-circuit a request).

### 🔗 Middleware

X-raptor supports middleware functions that run before route handlers. Middlewares can inspect/modify requests, short-circuit responses, or perform cross-cutting concerns like authentication and logging.

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
    return None  # Continue to next middleware/handler
```

**Priority**: Lower numbers run first. Each priority must be unique.

**Pattern matching**: Optionally restrict middleware to specific routes using regex:

```python
@xraptor.XRaptor.middleware(priority=2, pattern=r"^/api/.*")
async def api_only_middleware(request, connection):
    # Only runs for routes starting with /api/
    return None
```

**Short-circuiting**: Return a `Response` to stop the chain and skip the route handler. Return `None` to continue.

### 📡 Antenna

There is a default antenna (that use memory queue) configuration but is not recommended to use, you have two options
implements your own antenna class using the [interface](./xraptor/core/interfaces.py)
or use one of the extra packages.

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Awaitable


class Antenna(ABC):

    @abstractmethod
    def subscribe(self, key: str) -> AsyncIterator[str]:
        """
        async generator that will yield message from the key's channel 
        :param key: pubsub channel
        :return: str message async generator
        """
    
    @abstractmethod
    async def stop_listening(self):
        """
        stop listening messages
        :param antenna_id: pubsub channel
        :return:
        """

    @abstractmethod
    def post(self, key: str, message: str) -> Awaitable:
        """
        async function that will publish a message to a key's channel 
        :param key: pubsub channel
        :param message: message
        :return: 
        """

    @abstractmethod
    def is_alive(self, antenna_id: str) -> Awaitable[bool]:
        """
        verify that antenna_id still alive
        :param antenna_id:
        :return:
        """

    @classmethod
    @abstractmethod
    def set_config(cls, config: dict):
        """
        set config map for this antenna
        :param config:
        :return:
        """
```

### 📤 Broadcast

The library provides a broadcast room implementation that enables users to register and receive messages within a shared
space. This functionality is similar to a chat room where multiple users can join and automatically receive all messages
posted without requiring constant polling.

This broadcast implementation use the registered antenna to handle request and (un)subscriptions

```python
from typing import Self


class Broadcast:
    @classmethod
    def get(cls, broadcast_id: str) -> Self:
        """
        correct way to get a broadcast instance
        :param broadcast_id: string identifier
        :return: Broadcast object instance
        """

    def add_member(self, member: str):
        """
        add member on this chat room and if is the first to coming in, will open the room.
        :param member: member is an antenna id coming from request
        :return:
        """

    def remove_member(self, member: str):
        """
        remove member from this chat room and if is the last to coming out, will close the room.
        :param member: member is an antenna id coming from request
        :return:
        """
```

### Extras

#### Redis

This extra add the redis [package](https://pypi.org/project/redis/) in version `^5.0.8`.

How to install extra packages?

```shell
pip install 'xraptor[redis_version]'
# or with uv
uv add 'xraptor[redis_version]'
```

Redis antenna need string connection that you will configure on his antenna using the `set_config`.

```python
import xraptor

...

xraptor.antennas.RedisAntenna.set_config({"url": "redis://:@localhost:6379/0"})

...
```

#### uvloop

Optional faster event loop for the asyncio server. Install the extra and use
`XRaptor.run()` (it uses uvloop when available, otherwise falls back to asyncio):

```shell
pip install 'xraptor[uvloop]'
```

```python
import xraptor

_xraptor = xraptor.XRaptor("localhost", 8765)
_xraptor.set_antenna(xraptor.antennas.MemoryAntenna)
_xraptor.load_routes().run()   # uvloop if installed, else asyncio
```

## 🧮 Full Example

A very simple chat implementation was created to test `sub`, `poss` and `unsub` routes.

The test work using the `redis_edition`.

- The [server.py](./example/server.py) implementation can be found here.
- The [client.py](./example/client.py) implementation can be found here.