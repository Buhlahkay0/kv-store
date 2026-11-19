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
    print(f"{phase.upper()}: ok={ok} throughput={ok / elapsed:.0f} ops/s "
          f"avg={1e3 * sum(latencies) / ok:.2f} ms "
          f"p99={1e3 * latencies[int(0.99 * (ok - 1))]:.2f} ms")


if __name__ == "__main__":
    run("set")
    run("get")
