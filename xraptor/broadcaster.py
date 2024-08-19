import asyncio
from asyncio import Task
from typing import Self

import witch_doctor

from xraptor.core.interfaces import Antenna


class Broadcast:
    __broadcast_id: str
    __members: list[str]
    __task: Task | None
    __check_task: Task | None
    _broadcasts: dict[str, Self] = {}

    def __init__(self, broadcast_id: str):
        self.__broadcast_id = broadcast_id
        self.__members = []
        self.__task = None
        self.__check_task = None

    @classmethod
    def get(cls, broadcast_id: str) -> Self:
        """
        correct way to get a broadcast instance
        :param broadcast_id: string identifier
        :return: Broadcast object instance
        """
        if cls._broadcasts.get(broadcast_id) is None:
            cls._broadcasts.update({broadcast_id: Broadcast(broadcast_id)})
        return cls._broadcasts.get(broadcast_id)

    @classmethod
    def _delete(cls, broadcast_id: str):
        del cls._broadcasts[broadcast_id]

    def add_member(self, member: str):
        """
        add member on this chat room and if is the first to coming in, will open the room.
        :param member: member is an antenna id coming from request
        :return:
        """
        _members = {*self.__members, member}
        self.__members = list(_members)
        if len(self.__members) == 1:
            self._open()

    def remove_member(self, member: str):
        """
        remove member from this chat room and if is the last to coming out, will close the room.
        :param member: member is an antenna id coming from request
        :return:
        """
        _members = {*self.__members} - {member}
        self.__members = list(_members)
        if len(self.__members) == 0:
            self._close()
            self._delete(self.__broadcast_id)

    def _close(self):
        if self.__task:
            self.__task.cancel()
        if self.__check_task:
            self.__check_task.cancel()

    def _open(self):
        """
        Start to task to listening chat pubsub channel and to check if
        registered members still connected.
        :return:
        """
        self.__task = asyncio.create_task(self._listening())  # pylint: disable=E1120
        self.__check_task = asyncio.create_task(self._check())  # pylint: disable=E1120

    @witch_doctor.WitchDoctor.injection
    async def _check(self, antenna: Antenna, frequency: int = 7):
        """
        check each 7 seconds, using PUBSUB NUMSUB redis command, if each
        member on this room still connected, otherwise the member will be removed.
        :return:
        """
        while True:
            _to_check = [*self.__members]
            _status = await asyncio.gather(*[antenna.is_alive(i) for i in _to_check])
            _ = [
                None if is_alive else self.remove_member(_to_check[index])
                for index, is_alive in enumerate(_status)
            ]
            await asyncio.sleep(frequency)

    @witch_doctor.WitchDoctor.injection
    async def _listening(self, antenna: Antenna):
        """
        start listening each message from the chat room pubsub
        channel and broadcast it to each member in this room.
        :return:
        """
        async for data in antenna.subscribe(self.__broadcast_id):
            await asyncio.gather(*[antenna.post(i, data) for i in self.__members])
