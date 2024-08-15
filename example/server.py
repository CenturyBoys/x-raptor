import asyncio
import json


import xraptor


_xraptor = xraptor.XRaptor("localhost", 8765)


@_xraptor.register("/chat_messages").as_sub
async def register_on_chat_room(request: xraptor.Request) -> None:
    data = json.loads(request.payload)
    _chat_id = data["chat_id"]
    chat_room = xraptor.Broadcast.get(_chat_id)
    chat_room.add_member(request.request_id)


@_xraptor.register("/chat_messages").as_unsub
async def unregister_on_chat_room(request: xraptor.Request) -> xraptor.Response:
    data = json.loads(request.payload)
    _chat_id = data["chat_id"]
    chat_room = xraptor.Broadcast.get(_chat_id)
    chat_room.remove_member(request.request_id)
    return xraptor.Response(
        request_id=request.request_id, header={}, payload='{"message": "tchau!"}'
    )


@_xraptor.register("/send_message_to_chat_room").as_post
async def send_message(request: xraptor.Request) -> xraptor.Response:
    antenna = xraptor.antennas.RedisAntenna()
    data = json.loads(request.payload)
    _chat_id = data["chat_id"]
    _msg = {
        "origin": data["client_id"],
        "message": data["message"],
    }
    await antenna.post(_chat_id, json.dumps(_msg))
    return xraptor.Response(
        request_id=request.request_id, header={}, payload='{"message": "Message sent"}'
    )


if __name__ == "__main__":
    asyncio.run(_xraptor.load_routes().serve())
