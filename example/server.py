import asyncio
import json

import xraptor


@xraptor.XRaptor.register("/chat_messages").as_sub
async def register_on_chat_room(request: xraptor.Request) -> None:
    data = json.loads(request.payload)
    _chat_id = data["chat_id"]
    chat_room = xraptor.Broadcast.get(_chat_id)
    chat_room.add_member(request.request_id)


@xraptor.XRaptor.register("/chat_messages").as_unsub
async def unregister_on_chat_room(request: xraptor.Request) -> xraptor.Response:
    data = json.loads(request.payload)
    _chat_id = data["chat_id"]
    chat_room = xraptor.Broadcast.get(_chat_id)
    chat_room.remove_member(request.request_id)
    return xraptor.Response(
        request_id=request.request_id,
        header={},
        payload='{"message": "tchau!"}',
        method=xraptor.MethodType.UNSUB,
    )


@xraptor.XRaptor.register("/send_message_to_chat_room").as_post
async def send_message(request: xraptor.Request) -> xraptor.Response:
    antenna = xraptor.XRaptor.get_antenna()
    data = json.loads(request.payload)
    _chat_id = data["chat_id"]
    _msg = {
        "origin": data["client_id"],
        "message": data["message"],
    }
    await antenna.post(_chat_id, json.dumps(_msg))
    return xraptor.Response(
        request_id=request.request_id,
        header={},
        payload='{"message": "Message sent"}',
        method=xraptor.MethodType.POST,
    )


if __name__ == "__main__":
    _xraptor = xraptor.XRaptor("localhost", 8765)

    _xraptor.set_antenna(xraptor.antennas.MemoryAntenna)

    asyncio.run(_xraptor.load_routes().serve())
