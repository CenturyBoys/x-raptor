# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Use **orjson** for request/response (de)serialization on the hot path
  (~7.6x faster dumps, ~3.8x faster loads in a local micro-benchmark). The wire
  format stays text JSON (`json()` still returns `str`).
- Migrated packaging from Poetry to **uv** (PEP 621 `[project]` metadata, `hatchling`
  build backend, `uv.lock`).
- CI reworked to use `uv`: lint job (ruff + ruff-format + mypy) and a test matrix on
  Python 3.11/3.12/3.13 with coverage uploaded to Codecov via OIDC.
- Publishing now triggers on `v*` tags and uses PyPI **Trusted Publishing (OIDC)**
  instead of an API token.
- Expanded Ruff ruleset (`E,W,F,I,UP,B,SIM,C4,ASYNC,RUF`) and added a static
  type-checking gate (`mypy`).

### Added
- Graceful shutdown: `serve()` now runs until `stop()` is called or SIGTERM/SIGINT
  is received, then closes the server and its connections cleanly (replaces the
  busy `while True: sleep` loop).
- Configurable connection limits on `XRaptor(...)`: `max_size` (inbound payload cap,
  DoS guard), `max_queue` (per-connection backpressure), `ping_interval`/`ping_timeout`
  (keepalive), forwarded to the websockets server with safe defaults.
- End-to-end integration tests (real server + real websockets client): GET round-trip,
  SUB streaming, concurrent connections, unsubscribe isolation and graceful shutdown.
  CI enforces a coverage gate (`--cov-fail-under=85`).
- Optional `uvloop` extra plus `XRaptor.run()` convenience entrypoint that uses uvloop
  when installed and falls back to the stdlib asyncio loop otherwise.
- `NatsAntenna` (via the `nats` extra): NATS core pubsub backend sharing a single
  connection across DI instances. Note: `is_alive` always returns `True` (NATS core
  has no per-subject subscriber count), so `Broadcast` pruning relies on the
  connection layer for this backend.

### Fixed
- `Request.from_message` now raises a clear `ValueError` on malformed input
  (bad JSON, non-object, missing fields, unknown method) instead of leaking
  `KeyError`/`JSONDecodeError`; the server drops such messages at warning level.
- Middleware regex patterns are validated at registration (clear `ValueError`),
  and the middleware return-type check raises `TypeError` instead of an assert.
- Connection listener tasks no longer spin forever when the peer is gone (break on
  `ConnectionClosed`) and are wired to a done-callback so unexpected failures are
  logged instead of swallowed.
- Expected client disconnects (`ConnectionClosed`) are logged at debug level without
  a traceback instead of as errors.
- **MemoryAntenna**: removed the singleton so one subscriber's `stop_listening()`
  no longer kills every other subscriber; replaced the 50ms busy-poll with an
  event-driven queue; fixed `is_alive` to reflect active subscribers; and removed
  the unbounded orphan-queue leak (posts to channels with no subscriber are dropped).
- **RedisAntenna**: no longer swallows connection errors in `__init__`; shares a
  single lazily-created client (connection pool) across DI-created instances instead
  of opening a new connection per `post`/`is_alive`/`subscribe`; validates config
  with a clear error; cleans up the pubsub on exit.
- **Broadcast**: fan-out now snapshots members and uses `gather(return_exceptions=True)`
  so one failing member no longer aborts the whole room; `_open` guards against
  double-start orphaning tasks.
- Replaced `assert`-based validation in `Request`/`Response`/`set_antenna` with explicit
  `TypeError` raises (asserts are stripped under `python -O`).
- Deduplicated routes in `XRaptor.register`.
- Corrected `Antenna` interface type signatures (`subscribe` is an async-generator
  factory, `post`/`is_alive` return `None`/`bool`), fixing Liskov violations flagged
  by mypy in the memory and Redis implementations.
- `_subscribe` and `Broadcast.get` return annotations aligned with runtime behavior.
- Annotated shared class state with `typing.ClassVar`.

### Known limitations (deferred)
- `Broadcast.remove_member`/`_close` cancel tasks fire-and-forget (kept sync to avoid
  breaking the public API); awaiting cancellation would require an async API.
- No built-in rate limiting: implement it as a middleware (the middleware chain is the
  intended hook for auth and rate limiting).
- No built-in metrics/health endpoint yet (observability).

### Maturity
- Ship a `py.typed` marker (PEP 561) so consumers get the (already mypy-clean) types.
- Test matrix extended to Python 3.14; document a SPEC 0-style version-support policy
  and the criteria for a 1.0 API freeze.
- Add property-based tests (Hypothesis) for the request parser. This surfaced and
  fixed a robustness gap: `Request.from_message` now raises `ValueError` (not a
  leaked `TypeError`) when field types are wrong, so the server drops the message
  instead of dropping the connection.

### Security
- Publishing no longer references `PYPI_API_TOKEN` (uses OIDC Trusted Publishing).
  The token is an **organization-level** secret shared by other repos, so it is
  left in place — this repo simply stops using it.
- Bumped vulnerable dev/tooling dependencies flagged by Dependabot (all dev-only,
  not shipped to library users): `pytest` (>=9.0.3), `pytest-asyncio` (1.x),
  `filelock` (>=3.20.3), `virtualenv` (>=20.36.1). The pytest-asyncio bump also
  removes the deprecated event-loop-policy warnings.

### Notes
- Manual one-time setup still required on the hosting side: create the GitHub
  `pypi` environment, configure the PyPI Trusted Publisher, and enable Codecov
  for the repo.
