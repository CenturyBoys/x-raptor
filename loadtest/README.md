# Load / soak harness

A self-contained Python harness that spawns a real `XRaptor` server
([server.py](./server.py)) as a separate process, drives load against it, and
reports throughput, latency percentiles, errors, and — for the soak scenario —
memory (RSS) and connection trends over time.

> Numbers are **relative to the machine** they run on. Use them to compare runs,
> catch regressions and detect leaks — not as absolute production capacity.
> Pure-Python `websockets` caps around ~10k connections per core.

## Usage

```shell
uv run python loadtest/run.py smoke                       # tiny & fast (CI sanity)
uv run python loadtest/run.py load-ramp --connections 500 --requests 20
uv run python loadtest/run.py broadcast --room-size 100 --messages 50
uv run python loadtest/run.py soak --duration 300 --concurrency 100 --interval 10
uv run python loadtest/run.py all
```

## Scenarios

- **load-ramp** — opens increasing numbers of concurrent connections doing echo
  round-trips; reports throughput (req/s) and p50/p95/p99 latency per level.
- **broadcast** — N subscribers in a room, a publisher posts M messages; reports
  delivery ratio and delivery latency percentiles.
- **soak** — steady load with connection churn for a duration; samples
  `active_connections` (from `/metrics`) and process RSS over time. A healthy run
  shows RSS plateauing and `active_connections` returning to ~0 after churn stops
  (a leak shows growing RSS or connections that are never released).

Exit code is non-zero if any scenario fails its thresholds (error rate,
delivery ratio, or leak heuristics). `soak` reads server RSS from `/proc` (Linux).
