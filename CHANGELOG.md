# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Migrated packaging from Poetry to **uv** (PEP 621 `[project]` metadata, `hatchling`
  build backend, `uv.lock`).
- CI reworked to use `uv`: lint job (ruff + ruff-format + mypy) and a test matrix on
  Python 3.11/3.12/3.13 with coverage uploaded to Codecov via OIDC.
- Publishing now triggers on `v*` tags and uses PyPI **Trusted Publishing (OIDC)**
  instead of an API token.
- Expanded Ruff ruleset (`E,W,F,I,UP,B,SIM,C4,ASYNC,RUF`) and added a static
  type-checking gate (`mypy`).

### Fixed
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
- Graceful shutdown of the server loop (SIGTERM/SIGINT + task cancellation) — Phase 3.
- `Broadcast.remove_member`/`_close` cancel tasks fire-and-forget (kept sync to avoid
  breaking the public API); awaiting cancellation would require an async API.

### Notes
- Manual one-time setup still required on the hosting side: create the GitHub
  `pypi` environment, configure the PyPI Trusted Publisher, enable Codecov for the
  repo, and remove the old `PYPI_API_TOKEN` secret.
