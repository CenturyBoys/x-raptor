# X-raptor

![banner](https://raw.githubusercontent.com/CenturyBoys/x-raptor/main/docs/banner.jpeg)

```
By: CenturyBoys
```

## ⚠️ Fast as a hell, CAUTION!!!

This package is being developed and is in the testing process. **🚨 NOT USE THIS PACKAGE IN PRODUCTION !!!**

Fast as websocket easy as http, this package is an abstraction of [websockets](https://pypi.org/project/websockets/) package
to allow user to register `get`, `post`, `sub`, `unsub` asynchronous callbacks. For this all message must be a requests or a response object.

```python
import xraptor

_xraptor = xraptor.XRaptor("localhost", 8765)

@_xraptor.register("/send_message_to_chat_room").as_post
async def send_message(
        request: xraptor.Request
) -> xraptor.Response:
    ...
    return xraptor.Response(
        request_id=request.request_id,
        header={},
        payload='{"message": "Message sent"}'
    )
```

To allow multiple asynchronous responses on routes X-raptor use the `request_id` as antenna. Those antennas are pubsub channels that `yield` string messages.

### Antenna

There is no default antenna configuration, you have two options implements your own antenna class using the [interface](./xraptor/core/interfaces.py) 
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

### Broadcast


### Extras

#### Redis

This extra add the redis [package](https://pypi.org/project/redis/) in version `^5.0.8`.

How to install extra packages?

```shell
poetry add xraptor -E redis_edition
OR
pip install 'xraptor[redis_edition]'
```

You need pass the `X_RAPTOR_REDIS_URL` parameter on configuration

### Full Example

A very simple chat implementation was created to test `sub`, `poss` and `unsub` routes.

The test work using the `redis_edition`.

- The [server.py](./example/server.py) implementation can be found here.
- The [client.py](./example/client.py) implementation can be found here.