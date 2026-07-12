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
- Corrected `Antenna` interface type signatures (`subscribe` is an async-generator
  factory, `post`/`is_alive` return `None`/`bool`), fixing Liskov violations flagged
  by mypy in the memory and Redis implementations.
- `_subscribe` and `Broadcast.get` return annotations aligned with runtime behavior.
- Annotated shared class state with `typing.ClassVar`.

### Notes
- Manual one-time setup still required on the hosting side: create the GitHub
  `pypi` environment, configure the PyPI Trusted Publisher, enable Codecov for the
  repo, and remove the old `PYPI_API_TOKEN` secret.
