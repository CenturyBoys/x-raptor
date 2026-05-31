from xraptor.domain.route import Route


def test_register_and_match_map():
    _route = Route("/test")

    @_route.as_get
    async def handler_get():
        pass

    @_route.as_post
    async def handler_post():
        pass

    @_route.as_sub
    async def handler_sub():
        pass

    @_route.as_unsub
    async def handler_unsub():
        pass

    _m = _route.get_match_map()
    assert "/test:GET" in _m
    assert "/test:POST" in _m
    assert "/test:SUB" in _m
    assert "/test:UNSUB" in _m
