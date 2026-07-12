"""Load / soak test harness for x-raptor.

Spawns the target server (loadtest/server.py) as a separate process, drives load
from this process, and reports throughput / latency percentiles / errors, plus
memory (RSS) and connection trends over time for the soak scenario.

Examples:
    uv run python loadtest/run.py smoke                      # tiny, fast (CI)
    uv run python loadtest/run.py load-ramp --connections 500 --requests 20
    uv run python loadtest/run.py broadcast --room-size 100 --messages 50
    uv run python loadtest/run.py soak --duration 300 --concurrency 100
    uv run python loadtest/run.py all

Numbers are relative to the machine they run on — use them to compare runs,
catch regressions and detect leaks, not as absolute production capacity.
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request
from uuid import uuid4

import websockets

SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")


def msg(request_id: str, route: str, method: str, payload: str = "") -> str:
    return json.dumps(
        {
            "request_id": request_id,
            "payload": payload,
            "header": {},
            "route": route,
            "method": method,
        }
    )


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (p / 100)
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def read_metrics(host: str, port: int) -> dict[str, float]:
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/metrics", timeout=2) as resp:
            text = resp.read().decode()
    except OSError:
        return {}
    out: dict[str, float] = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        name, _, value = line.partition(" ")
        try:
            out[name] = float(value)
        except ValueError:
            pass
    return out


def read_rss_kb(pid: int) -> int | None:
    try:
        with open(f"/proc/{pid}/status") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except OSError:
        return None
    return None


def start_server(host: str, port: int) -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, SERVER, "--host", host, "--port", str(port)]
    )
    deadline = time.time() + 20
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("target server exited before becoming healthy")
        try:
            with urllib.request.urlopen(
                f"http://{host}:{port}/health", timeout=1
            ) as resp:
                if resp.status == 200:
                    return proc
        except OSError:
            time.sleep(0.1)
    proc.terminate()
    raise RuntimeError("target server did not become healthy in time")


async def scenario_load_ramp(
    url: str, levels: list[int], requests_per_conn: int
) -> bool:
    print("\n== Load ramp (echo GET round-trips) ==")
    header = f"{'conns':>6} {'reqs':>8} {'req/s':>9} {'p50ms':>8} {'p95ms':>8} {'p99ms':>8} {'err':>5}"
    print(header)
    ok = True
    for n in levels:

        async def one() -> tuple[list[float], bool]:
            lats: list[float] = []
            try:
                async with websockets.connect(url, open_timeout=10) as ws:
                    for _ in range(requests_per_conn):
                        start = time.perf_counter()
                        await ws.send(msg(uuid4().hex, "/echo", "GET", "x"))
                        await asyncio.wait_for(ws.recv(), timeout=10)
                        lats.append((time.perf_counter() - start) * 1000)
                return lats, False
            except Exception:
                return lats, True

        started = time.perf_counter()
        results = await asyncio.gather(*[one() for _ in range(n)])
        elapsed = time.perf_counter() - started
        latencies = [x for lats, _ in results for x in lats]
        errors = sum(1 for _, failed in results if failed)
        rps = len(latencies) / elapsed if elapsed else 0
        print(
            f"{n:>6} {len(latencies):>8} {rps:>9.0f} "
            f"{pct(latencies, 50):>8.1f} {pct(latencies, 95):>8.1f} "
            f"{pct(latencies, 99):>8.1f} {errors:>5}"
        )
        if n and errors / n > 0.05:
            ok = False
    return ok


async def scenario_broadcast(url: str, room_size: int, messages: int) -> bool:
    print("\n== Broadcast fan-out ==")
    room = uuid4().hex
    subs = []
    for _ in range(room_size):
        ws = await websockets.connect(url, open_timeout=10)
        await ws.send(msg(uuid4().hex, "/room", "SUB", json.dumps({"room": room})))
        subs.append(ws)
    await asyncio.sleep(0.5)  # let the room open and subscriptions register

    delivery: list[float] = []
    counters = {"received": 0}

    async def receiver(ws) -> None:
        try:
            while True:
                raw = await ws.recv()
                payload = json.loads(json.loads(raw)["payload"])
                delivery.append((time.perf_counter() - payload["t"]) * 1000)
                counters["received"] += 1
        except Exception:
            return

    tasks = [asyncio.ensure_future(receiver(ws)) for ws in subs]
    publisher = await websockets.connect(url, open_timeout=10)
    for n in range(messages):
        body = json.dumps({"room": room, "t": time.perf_counter(), "n": n})
        await publisher.send(msg(uuid4().hex, "/publish", "POST", body))
        await asyncio.sleep(0.01)
    await asyncio.sleep(1.5)  # flush deliveries

    for task in tasks:
        task.cancel()
    await publisher.close()
    for ws in subs:
        await ws.close()

    expected = room_size * messages
    got = counters["received"]
    ratio = (got / expected * 100) if expected else 0
    print(
        f"subscribers={room_size} messages={messages} expected={expected} delivered={got} ({ratio:.0f}%)"
    )
    if delivery:
        print(
            f"delivery latency  p50={pct(delivery, 50):.1f}ms  "
            f"p95={pct(delivery, 95):.1f}ms  p99={pct(delivery, 99):.1f}ms"
        )
    return got >= expected * 0.95


async def scenario_soak(
    url: str,
    host: str,
    port: int,
    pid: int,
    duration: float,
    concurrency: int,
    interval: float,
) -> bool:
    print("\n== Soak (steady load + connection churn) ==")
    stop_at = time.perf_counter() + duration

    async def churn() -> None:
        while time.perf_counter() < stop_at:
            try:
                async with websockets.connect(url, open_timeout=5) as ws:
                    for _ in range(5):
                        await ws.send(msg(uuid4().hex, "/echo", "GET", "x"))
                        await asyncio.wait_for(ws.recv(), timeout=5)
            except Exception:
                await asyncio.sleep(0.05)

    workers = [asyncio.ensure_future(churn()) for _ in range(concurrency)]
    rss_start = read_rss_kb(pid)
    print(f"{'t(s)':>5} {'active':>7} {'requests':>10} {'rss_kb':>9}")
    t0 = time.perf_counter()
    while time.perf_counter() < stop_at:
        metrics = await asyncio.to_thread(read_metrics, host, port)
        rss = read_rss_kb(pid)
        print(
            f"{time.perf_counter() - t0:>5.0f} "
            f"{metrics.get('xraptor_connections_active', 0):>7.0f} "
            f"{metrics.get('xraptor_requests_total', 0):>10.0f} "
            f"{rss if rss else 0:>9}"
        )
        await asyncio.sleep(interval)

    for worker in workers:
        worker.cancel()
    await asyncio.sleep(1)
    metrics = await asyncio.to_thread(read_metrics, host, port)
    rss_end = read_rss_kb(pid)
    active_final = metrics.get("xraptor_connections_active", 0)

    delta = (rss_end or 0) - (rss_start or 0)
    print(f"\nRSS start={rss_start}kB end={rss_end}kB (delta={delta:+}kB)")
    print(f"active_connections after churn stopped: {active_final:.0f} (expect ~0)")

    ok = True
    if rss_start and rss_end and rss_end > rss_start * 1.5 + 20_000:
        print("WARN: RSS grew > 50% — possible memory leak")
        ok = False
    if active_final > 2:
        print("WARN: connections not released after churn — possible leak")
        ok = False
    return ok


async def run(args: argparse.Namespace, pid: int) -> int:
    url = f"ws://{args.host}:{args.port}"
    if args.scenario in ("all", "smoke"):
        scenarios = ["load-ramp", "broadcast", "soak"]
    else:
        scenarios = [args.scenario]

    results = []
    for name in scenarios:
        if name == "load-ramp":
            levels = sorted(
                {
                    max(1, args.connections // 4),
                    max(1, args.connections // 2),
                    args.connections,
                }
            )
            results.append(await scenario_load_ramp(url, levels, args.requests))
        elif name == "broadcast":
            results.append(await scenario_broadcast(url, args.room_size, args.messages))
        elif name == "soak":
            results.append(
                await scenario_soak(
                    url,
                    args.host,
                    args.port,
                    pid,
                    args.duration,
                    args.concurrency,
                    args.interval,
                )
            )

    ok = all(results)
    print(f"\n{'PASS' if ok else 'FAIL'}: {sum(results)}/{len(results)} scenarios ok")
    return 0 if ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="x-raptor load/soak harness")
    parser.add_argument(
        "scenario", choices=["load-ramp", "broadcast", "soak", "smoke", "all"]
    )
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--connections", type=int, default=200)
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--room-size", type=int, default=50)
    parser.add_argument("--messages", type=int, default=20)
    parser.add_argument("--duration", type=float, default=30)
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--interval", type=float, default=5)
    args = parser.parse_args()

    if args.scenario == "smoke":
        # tiny, fast parameters for CI sanity
        args.connections, args.requests = 10, 3
        args.room_size, args.messages = 5, 3
        args.duration, args.concurrency, args.interval = 3, 5, 1

    proc = start_server(args.host, args.port)
    try:
        exit_code = asyncio.run(run(args, proc.pid))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
