# X-raptor

![banner](https://raw.githubusercontent.com/CenturyBoys/x-raptor/main/docs/banner.jpeg)

```
By: CenturyBoys
```

## ⚠️ Fast as a hell, CAUTION!!!

This package is being developed and is in the testing process. **🚨 NOT USE THIS PACKAGE IN PRODUCTION !!!**

Fast as websocket easy as http, this package is an abstraction of [websockets](https://pypi.org/project/websockets/) package
to allow user to register `get`, `post`, `sub`, `unsub` asynchronous callbacks. For this all message must be a requests or a response object.

To allow multiple asynchronous responses on routes X-raptor use the `request_id` as antenna. Those antennas are pubsub channels that `yield` string messages.

### Registering a route

To register a route you can use the `xraptor.XRaptor.register` to get the route instance and use the `as_` (`as_get`, `as_post`, `as_sub`, `as_unsub`,) decorator. See below an example

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

_xraptor.set_antenna(xraptor.antennas.RedisAntenna)

asyncio.run(_xraptor.load_routes().serve())
```

### 📡 Antenna

There is a default antenna (that use memory queue) configuration but is not recommended to use, you have two options implements your own antenna class using the [interface](./xraptor/core/interfaces.py) 
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
```

### 📤 Broadcast

The library provides a broadcast room implementation that enables users to register and receive messages within a shared space. This functionality is similar to a chat room where multiple users can join and automatically receive all messages posted without requiring constant polling.

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
poetry add xraptor -E redis_version
OR
pip install 'xraptor[redis_version]'
```

You need pass the `X_RAPTOR_REDIS_URL` parameter on configuration

## 🧮 Full Example

A very simple chat implementation was created to test `sub`, `poss` and `unsub` routes.

The test work using the `redis_edition`.

- The [server.py](./example/server.py) implementation can be found here.
- The [client.py](./example/client.py) implementation can be found here.