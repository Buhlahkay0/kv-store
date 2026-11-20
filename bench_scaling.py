import multiprocessing as mp

import kv_bench

PROCESSES = 4
THREADS = 8
KEYS = 3000


def one_client(phase):
    kv_bench.NUM_THREADS = THREADS
    kv_bench.NUM_KEYS = KEYS
    stats, elapsed = kv_bench.run_phase(phase)
    return stats.latencies, elapsed


def run(phase):
    with mp.Pool(PROCESSES) as pool:
        results = pool.map(one_client, [phase] * PROCESSES)

    latencies = sorted(lat for lats, _ in results for lat in lats)
    elapsed = max(t for _, t in results)
    ok = len(latencies)
    ops = ok / elapsed
    avg_ms = 1e3 * sum(latencies) / ok
    p99_ms = 1e3 * latencies[int(0.99 * (ok - 1))]
    print(f"{phase.upper()}: ok={ok} throughput={ops:.0f} ops/s "
          f"avg={avg_ms:.2f} ms p99={p99_ms:.2f} ms")
    return {"ok": ok, "ops_per_s": ops, "avg_ms": avg_ms, "p99_ms": p99_ms}


if __name__ == "__main__":
    run("set")
    run("get")
