import json
import threading
from uuid import uuid4

from websockets.sync.client import connect

import xraptor
from xraptor.domain.methods import MethodType


def _sub(request_id, chat_id):
    return xraptor.Request(
        request_id=request_id,
        payload=json.dumps({"chat_id": chat_id}),
        header={},
        route="/chat_messages",
        method=MethodType.SUB,
    ).json()


def _unsub(request_id, chat_id):
    return xraptor.Request(
        request_id=request_id,
        payload=json.dumps({"chat_id": chat_id}),
        header={},
        route="/chat_messages",
        method=MethodType.UNSUB,
    ).json()


def _send(request_id, message, chat_id, client_id):
    return xraptor.Request(
        request_id=request_id,
        payload=json.dumps(
            {"message": message, "chat_id": chat_id, "client_id": client_id}
        ),
        header={},
        route="/send_message_to_chat_room",
        method=MethodType.POST,
    ).json()


def chat():
    client_id = str(uuid4())
    chat_id = input("Chat id ->")
    with connect("ws://localhost:8765") as websocket:
        sub_id = str(uuid4())
        websocket.send(_sub(sub_id, chat_id))

        def chat_message_loop():
            while True:
                message = websocket.recv()
                _data = json.loads(message)
                print(_data)
                if _data["request_id"] == sub_id:
                    _p = json.loads(_data["payload"])
                    if _p["origin"] == client_id:
                        print(f'You: {_p["message"]}')
                    else:
                        print(f'{_p["origin"]}: {_p["message"]}')

        _t = threading.Thread(target=chat_message_loop)
        _t.start()

        print(f"Start chat: {str(chat_id)}")
        while True:
            try:
                text = input()
                if text == "unsub":
                    websocket.send(_unsub(sub_id, chat_id))
                websocket.send(_send(str(uuid4()), text, chat_id, client_id))
            except Exception:  # pylint: disable=W0718
                websocket.send(_unsub(sub_id, chat_id))


if __name__ == "__main__":
    chat()
