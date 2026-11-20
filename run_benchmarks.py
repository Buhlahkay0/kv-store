"""Run the scaling measurements and write them to a CSV file.

Docker must be running. For each node count and each run, the script deletes the old
cluster and its volumes, starts a new cluster, and runs the SET and GET phases of
bench_scaling.py. A new cluster is needed for every run because the router can send
only about 28,000 requests to one node before it runs out of ports (see the README).

Usage:
  python run_benchmarks.py                       # 1, 2 and 3 nodes, 2 runs each
  python run_benchmarks.py --runs 1 --nodes 3    # a quick check
  python run_benchmarks.py --out my_results.csv  # keep results/results.csv unchanged

Then draw the charts with: python plot_results.py results/results.csv
"""
import argparse
import csv
import os
import subprocess
import time

import requests

import bench_scaling

NODES = ["http://kv1:8080", "http://kv2:8080", "http://kv3:8080"]
ROUTER_URL = "http://127.0.0.1:8080"


def compose(*args, backends=None):
    env = dict(os.environ)
    if backends:
        env["BACKENDS"] = backends
    subprocess.run(["docker", "compose", *args], check=True, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_for_router():
    # Any HTTP answer, even a 404, shows that the router is accepting requests.
    for _ in range(30):
        try:
            requests.get(f"{ROUTER_URL}/ready", timeout=1)
            return
        except requests.RequestException:
            time.sleep(1)
    raise SystemExit("The router did not start within 30 seconds.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--runs", type=int, default=2, help="runs per node count")
    parser.add_argument("--nodes", type=int, nargs="+", default=[1, 2, 3], choices=[1, 2, 3])
    parser.add_argument("--out", default="results/results.csv")
    args = parser.parse_args()

    expected = bench_scaling.PROCESSES * bench_scaling.KEYS
    rows = []
    try:
        for nodes in args.nodes:
            for run in range(1, args.runs + 1):
                print(f"\n== {nodes} node(s), run {run}")
                compose("down", "-v")
                compose("up", "-d", "--wait", "--force-recreate", backends=",".join(NODES[:nodes]))
                wait_for_router()
                for phase in ("set", "get"):
                    result = bench_scaling.run(phase)
                    if result["ok"] != expected:
                        raise SystemExit(f"Only {result['ok']} of {expected} {phase} requests "
                                         "succeeded, so these numbers are not valid.")
                    rows.append({"nodes": nodes, "run": run, "phase": phase,
                                 "ops_per_s": round(result["ops_per_s"]),
                                 "avg_ms": round(result["avg_ms"], 2),
                                 "p99_ms": round(result["p99_ms"], 2)})
    finally:
        compose("down", "-v")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["nodes", "run", "phase", "ops_per_s", "avg_ms", "p99_ms"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
