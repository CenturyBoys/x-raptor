class StubWS:
    def __init__(self):
        self.remote_address = ["192.168.0.1"]
        self.path = "/test"

    def __hash__(self):
        return 1

    async def send(self, data):
        pass

    async def close(self, code):
        pass

    async def __aiter__(self):
        yield self.netx_msg()

    def netx_msg(self) -> str:
        pass
