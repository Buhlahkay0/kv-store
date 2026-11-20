# Distributed key-value store

A key-value store served over HTTP with Python and Flask. A router spreads the keys across one to three storage nodes using consistent hashing, and each node runs in its own Docker container.

## How it works

Clients send every request to the router on port 8080. For each key, the router asks a consistent hash ring (the uhashring library, with 160 virtual nodes per node) which node owns the key, forwards the request to that node, and returns the node's answer unchanged. The same key always reaches the same node, and adding or removing a node changes the owner of only about 1/N of the keys. The router answers 502 when the owning node can't be reached and 503 when no nodes are configured.

Each node keeps its keys in memory, saves them to `kv_snapshot.json` every 5 seconds and on shutdown, reloads that file when it starts, and logs every operation to `server.log`. Both files are in the node's `DATA_DIR`.

Files:
- `kv_store.py` is a storage node and `router.py` is the router.
- `Dockerfile` builds one image with both programs, and `docker-compose.yml` starts three nodes and the router.
- `kv_bench.py` is the provided benchmark and isn't modified. `bench_scaling.py` runs it from several processes, `run_benchmarks.py` measures 1, 2 and 3 nodes, and `plot_results.py` draws charts and table images from a results file.
- `requirements.txt` is for the cluster, and `requirements-bench.txt` is for the charts.

## Setup

Python 3 and Docker are required.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run with Docker

```bash
docker compose up --build --wait
```

The command starts three nodes and the router, and the router waits until all three nodes pass their health check. The router is at http://localhost:8080, and the nodes are reachable only inside the compose network.

To use fewer nodes, set `BACKENDS` to the nodes the router should use. All three containers still start, but the router sends keys only to the nodes in the list.

```bash
BACKENDS=http://kv1:8080 docker compose up --build --wait                 # 1 node
BACKENDS=http://kv1:8080,http://kv2:8080 docker compose up --build --wait # 2 nodes
```

To stop the cluster, run `docker compose down`, which keeps each node's named volume. Add `-v` to delete the volumes too. A node can lose up to 5 seconds of writes when it is stopped, because the final snapshot isn't guaranteed.

## Run without Docker

Start each node with its own port and data directory, and then start the router. Stop the router with Ctrl+C and the nodes with `pkill -f kv_store.py`.

```bash
PORT=9001 DATA_DIR=data1 python kv_store.py &
PORT=9002 DATA_DIR=data2 python kv_store.py &
PORT=9003 DATA_DIR=data3 python kv_store.py &
BACKENDS=http://127.0.0.1:9001,http://127.0.0.1:9002,http://127.0.0.1:9003 python router.py
```

A node reads `PORT` (default 8080), `HOST` (default 127.0.0.1) and `DATA_DIR` (default the current directory). The Docker image sets `HOST=0.0.0.0` and `DATA_DIR=/data`.

## API

| Operation | Request | Success | Errors |
|-----------|---------|---------|--------|
| PUT | `POST` or `PUT /<key>` with body `{"value": ...}` | 200 | 400 if `value` is missing |
| GET | `GET /<key>` | 200 `{"value": ...}` | 404 if the key isn't found |
| DEL | `DELETE /<key>` | 200 | 404 if the key isn't found |

```bash
curl -X POST -H "Content-Type: application/json" -d '{"value": "hello"}' localhost:8080/greeting
curl localhost:8080/greeting
curl -X DELETE localhost:8080/greeting
curl -i localhost:8080/greeting     # 404 after deletion
```

## Benchmarks

The provided benchmark runs against the router at http://127.0.0.1:8080.

```bash
python kv_bench.py          # write phase, then read-and-verify phase
python kv_bench.py set      # write only
python kv_bench.py get      # verify only
```

The provided benchmark sends only 300 requests from 3 threads, which is too little load to show a difference between one and three nodes. `bench_scaling.py` imports `kv_bench`, changes its settings, and runs it in 4 processes of 8 threads each with 3,000 keys per process, so each phase makes 12,000 requests.

```bash
python bench_scaling.py
```

To measure again, start Docker and run `run_benchmarks.py`. For each node count, it deletes the old cluster and its volumes, starts a new cluster, runs `bench_scaling.py`, and writes a CSV file. It needs a new cluster for every run because of the router limit described below. A full run takes a few minutes, and the numbers will differ slightly from the report. Charts need matplotlib, which the Docker image doesn't use.

```bash
pip install -r requirements-bench.txt
python run_benchmarks.py                        # writes results/results.csv, which replaces the report data
python run_benchmarks.py --out new_results.csv  # keeps results/results.csv unchanged
python plot_results.py new_results.csv          # writes 6 PNG files to a figures folder next to the CSV
```

## Results

Each row is the average of two runs on a freshly started cluster, with 32 requests in flight and no errors. The report data is in `results/results.csv`, and its charts and table images are in `results/figures/`.

| Nodes | SET ops/s | GET ops/s | SET avg / p99 latency | GET avg / p99 latency |
|-------|-----------|-----------|-----------------------|-----------------------|
| 1 | 1,750 | 1,621 | 18.3 / 25.3 ms | 19.7 / 27.1 ms |
| 2 | 2,133 | 2,296 | 14.9 / 29.5 ms | 13.8 / 26.6 ms |
| 3 | 2,695 | 2,902 | 11.7 / 24.5 ms | 10.8 / 22.0 ms |

From one node to three nodes, SET throughput rose 1.54 times and GET throughput rose 1.79 times. The gain is below 3 times because the router and the benchmark client, which reaches Docker through port forwarding, have their own limits.

## Limitations

- The router opens a new connection to a node for every request, and closed connections wait in the TIME_WAIT state. A container has about 28,200 ports for one destination, so a router that sends more than about 28,000 requests to one node starts returning 502.
- When the node list changes, the router uses the new ring right away, but keys that now belong to a different node aren't moved. Such keys read as missing until they're written again.
- Each key is stored on one node only, so a node that goes down makes its keys unavailable.

## Assumptions

- Keys are single URL path segments and can't contain `/`. Percent-encode special characters such as `?` and `#`.
- Values are any JSON value.
