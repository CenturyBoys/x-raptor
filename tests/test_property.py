"""Property-based tests (Hypothesis) for the request protocol parser."""

from hypothesis import given
from hypothesis import strategies as st

from xraptor.domain.methods import MethodType
from xraptor.domain.request import Request

# Text without lone surrogates (those are not valid JSON / UTF-8).
_safe_text = st.text(st.characters(exclude_categories=["Cs"]))
_headers = st.dictionaries(_safe_text, _safe_text, max_size=5)


@given(
    request_id=_safe_text,
    payload=_safe_text,
    header=_headers,
    route=_safe_text,
    method=st.sampled_from(list(MethodType)),
)
def test_request_json_roundtrip(request_id, payload, header, route, method):
    """Any valid Request survives json() -> from_message() unchanged."""
    req = Request(
        request_id=request_id,
        payload=payload,
        header=header,
        route=route,
        method=method,
    )
    assert Request.from_message(req.json()) == req


@given(st.text())
def test_from_message_only_raises_valueerror_on_garbage(raw):
    """The parser must never leak anything other than ValueError on bad input."""
    try:
        Request.from_message(raw)
    except ValueError:
        pass  # expected for malformed input


_json_int = st.integers(min_value=-(2**63) + 1, max_value=2**63 - 1)


@given(
    st.dictionaries(
        st.sampled_from(["request_id", "payload", "header", "route", "method"]),
        st.one_of(_json_int, st.booleans(), st.none(), st.lists(_json_int)),
        max_size=5,
    )
)
def test_from_message_wrong_types_raise_valueerror(obj):
    """Well-formed JSON objects with wrong field types raise ValueError, not TypeError."""
    import orjson

    try:
        Request.from_message(orjson.dumps(obj))
    except ValueError:
        pass  # expected: uniform ValueError, never TypeError/KeyError
