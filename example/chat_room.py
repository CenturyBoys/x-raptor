import asyncio
from asyncio import Task
from dataclasses import dataclass, field

import meeseeks
from redis.asyncio import Redis


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
        """
        add member on this chat room and if is the first to coming in, will open the room.
        :param member: member is an antenna id coming from request
        :return:
        """
        _members = {*self.members, member}
        self.members = list(_members)
        if len(self.members) == 1:
            self._open()

    def remove_member(self, member: str):
        """
        remove member from this chat room and if is the last to coming out, will close the room.
        :param member: member is an antenna id coming from request
        :return:
        """
        _members = {*self.members} - {member}
        self.members = list(_members)
        if len(self.members) == 0:
            self._close()

    def _close(self):
        print(f"Achat room '{self.chat_id}' is closing")
        self.task.cancel()
        self.check_task.cancel()

    def _open(self):
        """
        Start to task to listening chat pubsub channel and to check if registered members still connected.
        :return:
        """
        self.task = asyncio.create_task(self._listening())
        self.check_task = asyncio.create_task(self._check())

    async def _check(self):
        """
        check each 7 seconds, using PUBSUB NUMSUB redis command, if each member on this room still connected,
        otherwise the member will be removed.
        :return:
        """
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
        """
        start listening each message from the chat room pubsub channel and broadcast it to each member in this room.
        :return:
        """
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.chat_id)
        async for message in pubsub.listen():
            if message["type"] == "message":
                await asyncio.gather(
                    *[self.redis.publish(i, message["data"]) for i in self.members]
                )
