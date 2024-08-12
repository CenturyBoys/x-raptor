import asyncio
import json
import threading
from uuid import uuid4

from websockets.sync.client import connect


def _sub(request_id, chat_id):
    message = {
        "request_id": request_id,
        "payload": {"chat_id": chat_id},
        "header": "",
        "route": "/chat_messages",
        "method": "SUB",
    }
    return json.dumps(message).encode()


def _unsub(request_id, chat_id):
    message = {
        "request_id": request_id,
        "payload": {"chat_id": chat_id},
        "header": "",
        "route": "/chat_messages",
        "method": "UNSUB",
    }
    return json.dumps(message).encode()


def _send(request_id, message, chat_id, client_id):
    message = {
        "request_id": request_id,
        "payload": {"message": message, "chat_id": chat_id, "client_id": client_id},
        "header": "",
        "route": "/send_message_to_chat_room",
        "method": "POST",
    }
    return json.dumps(message).encode()


def hello1():
    client_id = str(uuid4())
    chat_id = input("Chat id ->")
    with connect("ws://localhost:8765") as websocket:
        sub_id = str(uuid4())
        websocket.send(_sub(sub_id, chat_id))

        def xxx():
            while True:
                message = websocket.recv()
                _data = json.loads(message)
                if _data["request_id"] == sub_id:
                    if _data["payload"]["origin"] == client_id:
                        print(f'You: {_data["payload"]["message"]}')
                    else:
                        print(f'{_data["payload"]["origin"]}: {_data["payload"]["message"]}')

        _t = threading.Thread(target=xxx)
        _t.start()
        print(f"Start chat: {str(chat_id)}")
        while True:
            try:
                text = input()
                if text == "unsub":
                    websocket.send(_unsub(sub_id, chat_id))
                websocket.send(_send(str(uuid4()), text, chat_id, client_id))
            except Exception:
                websocket.send(_unsub(sub_id, chat_id))


if __name__ == "__main__":
    hello1()
