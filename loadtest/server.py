"""Target server for the load/soak harness (run as a separate process).

Usage: python loadtest/server.py --host localhost --port 8765
"""

import argparse
import asyncio
import json

import xraptor
from xraptor.antenna_implementations.memory import MemoryAntenna


@xraptor.XRaptor.register("/echo").as_get
async def _echo(request: xraptor.Request) -> xraptor.Response:
    return xraptor.Response.create(
        request_id=request.request_id,
        header={},
        payload=request.payload,
        method=request.method,
    )


@xraptor.XRaptor.register("/room").as_sub
async def _room_sub(request: xraptor.Request) -> None:
    room = json.loads(request.payload)["room"]
    xraptor.Broadcast.get(room).add_member(request.request_id)
    return None


@xraptor.XRaptor.register("/room").as_unsub
async def _room_unsub(request: xraptor.Request) -> None:
    room = json.loads(request.payload)["room"]
    xraptor.Broadcast.get(room).remove_member(request.request_id)
    return None


@xraptor.XRaptor.register("/publish").as_post
async def _publish(request: xraptor.Request) -> None:
    room = json.loads(request.payload)["room"]
    # Fan out to the room's broadcast channel; Broadcast._listening delivers it
    # to every member subscribed on this room.
    await xraptor.XRaptor.get_antenna().post(room, request.payload)
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = xraptor.XRaptor(args.host, args.port)
    server.set_antenna(MemoryAntenna)
    asyncio.run(server.load_routes().serve())


if __name__ == "__main__":
    main()
