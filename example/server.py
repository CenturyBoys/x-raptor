import asyncio
import json
from asyncio import Task
from dataclasses import dataclass, field

import meeseeks
from redis.asyncio import Redis

from xraptor import XRaptor

_xraptor = XRaptor("localhost", 8765)


@meeseeks.OnlyOne(by_args_hash=True)
@dataclass(slots=True)
class ChatRoom:
    chat_id: str
    members: list[str] = field(default_factory=list)
    task: Task = None
    check_task: Task = None
    redis: Redis = None

    def __post_init__(self):
        self.redis = Redis(host="raspb.local", port=6379, db=0)

    def add_member(self, member: str):
        _members = {*self.members, member}
        self.members = list(_members)
        if len(self.members) == 1:
            self._open()

    def remove_member(self, member: str):
        _members = {*self.members} - {member}
        self.members = list(_members)
        if len(self.members) == 0:
            self._close()

    def _close(self):
        print("Sistema automatico de luz, apagando!")
        self.task.cancel()
        self.check_task.cancel()

    def _open(self):
        self.task = asyncio.create_task(self._listening())
        # self.check_task = asyncio.create_task(self._check())

    async def _check(self):
        while True:
            _to_check = [*self.members]
            for m in _to_check:
                num_subscribers = await self.redis.execute_command(
                    "PUBSUB", "NUMSUB", m
                )
                if int(num_subscribers[1]) != 1:
                    self.remove_member(m)
            await asyncio.sleep(7)

    async def _listening(self):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.chat_id)
        async for message in pubsub.listen():
            if message["type"] == "message":
                await asyncio.gather(
                    *[self.redis.publish(i, message["data"]) for i in self.members]
                )


@_xraptor.register("/chat_messages").as_sub
async def register_on_chat_room(payload: bytes, publish_id: str):
    data = json.loads(payload)
    _chat_id = data["chat_id"]
    chat_room = ChatRoom(_chat_id)
    chat_room.add_member(publish_id)


@_xraptor.register("/chat_messages").as_unsub
async def unregister_on_chat_room(payload: bytes, publish_id: str):
    data = json.loads(payload)
    _chat_id = data["chat_id"]
    chat_room = ChatRoom(_chat_id)
    chat_room.remove_member(publish_id)
    return '{"message": "tchau!"}'


@_xraptor.register("/send_message_to_chat_room").as_post
async def send_message_to_chat_room(
    payload: bytes,
):
    data = json.loads(payload)
    _chat_id = data["chat_id"]
    _redis = Redis(host="raspb.local", port=6379, db=0)
    _msg = {
        "origin": data["client_id"],
        "message": data["message"],
    }
    await _redis.publish(_chat_id, json.dumps(_msg))
    await _redis.aclose()
    return '{"message": "Message sent"}'


async def main():
    await _xraptor.load_routes().serve()


async def xxx():
    pubsub = Redis(host="raspb.local", port=6379, db=0).pubsub()
    await pubsub.subscribe("6465a666-0085-404e-9e53-9d05929aa448")
    async for message in pubsub.listen():
        print(message)


if __name__ == "__main__":
    # asyncio.run(xxx())
    asyncio.run(main())
