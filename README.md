# Distributed key-value store

A key-value store served over HTTP, built with Python and Flask. A router spreads the keys across one to three storage nodes using consistent hashing, and every node runs in its own Docker container. Each node supports GET, PUT and DELETE, handles concurrent requests, logs every operation, and saves its data to disk.

## How it works

Clients send every request to the router on port 8080, and the router never stores data itself. For each key, the router asks a consistent hash ring (the uhashring library, with 160 virtual nodes per node) which node owns the key. It then forwards the request to that node and returns the node's answer unchanged. The same key always goes to the same node, and adding or removing a node changes the owner of only about 1/N of the keys.

The router answers 502 when the node that owns a key can't be reached, and 503 when no nodes are configured.

Files:
- `kv_store.py` is one storage node.
- `router.py` is the router.
- `Dockerfile` builds one image that contains both programs.
- `docker-compose.yml` starts three nodes and the router together.
- `kv_bench.py` is the provided benchmark, and it is not modified.
- `bench_scaling.py` runs the same benchmark with several client processes, to produce heavier load.

## Setup

Python 3 and Docker are required.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the cluster with Docker

```bash
docker compose up --build --wait
```

The command starts three nodes and the router. The router starts only after all three nodes pass their health check. The router is reachable at http://localhost:8080, and the nodes are only reachable from inside the compose network.

To use fewer nodes, set `BACKENDS` to the nodes the router should use. All three containers still start, but the router sends keys only to the nodes in the list.

```bash
BACKENDS=http://kv1:8080 docker compose up --build --wait                       # 1 node
BACKENDS=http://kv1:8080,http://kv2:8080 docker compose up --build --wait       # 2 nodes
```

To stop the cluster, run `docker compose down`. Each node keeps its data in a named volume, so the data survives this command. Add `-v` to delete the volumes as well. A node can lose up to 5 seconds of recent writes when it is stopped, because the final snapshot isn't guaranteed.

## Run without Docker

Start each node with its own port and data directory, and then start the router.

```bash
PORT=9001 DATA_DIR=data1 python kv_store.py &
PORT=9002 DATA_DIR=data2 python kv_store.py &
PORT=9003 DATA_DIR=data3 python kv_store.py &
BACKENDS=http://127.0.0.1:9001,http://127.0.0.1:9002,http://127.0.0.1:9003 python router.py
```

A node reads three environment variables. `PORT` defaults to 8080, `HOST` defaults to 127.0.0.1, and `DATA_DIR` defaults to the current directory. The Docker image sets `HOST=0.0.0.0` and `DATA_DIR=/data`.

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

## Persistence and logging

Each node saves its keys to `kv_snapshot.json` every 5 seconds and when it shuts down, and it reloads that file when it starts. Each node also writes every operation with a timestamp to `server.log`. Both files are in the node's `DATA_DIR`.

## Benchmark

The provided benchmark runs against the router at http://127.0.0.1:8080.

```bash
python kv_bench.py          # write phase, then read-and-verify phase
python kv_bench.py set      # write only
python kv_bench.py get      # verify only
```

The provided benchmark sends only 300 requests from 3 threads, which is too little load to show a difference between one and three nodes. `bench_scaling.py` imports `kv_bench`, changes its settings, and runs it in several processes at the same time.

```bash
python bench_scaling.py
```

The settings are at the top of the file. The defaults are 4 processes with 8 threads each and 3,000 keys per process, which makes 12,000 requests per phase.

To compare node counts, restart the cluster before every measured run (`docker compose down -v`, then start it with the `BACKENDS` value you want), because of the router limit described below.

## Results

Each row is the average of two runs on a freshly started cluster, with 32 requests in flight and no errors.

| Nodes | SET ops/s | GET ops/s | SET avg / p99 latency | GET avg / p99 latency |
|-------|-----------|-----------|-----------------------|-----------------------|
| 1 | 1,750 | 1,621 | 18.3 / 25.3 ms | 19.7 / 27.1 ms |
| 2 | 2,133 | 2,296 | 14.9 / 29.5 ms | 13.8 / 26.6 ms |
| 3 | 2,695 | 2,902 | 11.7 / 24.5 ms | 10.8 / 22.0 ms |

From one node to three nodes, SET throughput rose 1.54 times and GET throughput rose 1.79 times. The gain is below 3 times because the router and the benchmark client, which runs on the host machine and reaches Docker through port forwarding, have their own limits.

## Measure again and draw the charts

The measurements in the report are saved in `results/results.csv`, and `plot_results.py` turns that file into two charts, `results/throughput.png` and `results/latency.png`. Charts need matplotlib, which the Docker image doesn't use, so it has its own requirements file.

```bash
pip install -r requirements-bench.txt
python plot_results.py
```

To measure again, start Docker and run `run_benchmarks.py`. For each node count, the script deletes the old cluster and its volumes, starts a new cluster, runs `bench_scaling.py`, and writes the results to a CSV file. A full run (1, 2 and 3 nodes, 2 runs each) takes a few minutes, and the numbers will differ slightly from the report.

```bash
python run_benchmarks.py                       # writes results/results.csv, which replaces the report data
python run_benchmarks.py --out new_results.csv # keeps results/results.csv unchanged
python plot_results.py new_results.csv
```

## Limitations

- The router opens a new connection to a node for every request. Closed connections wait in the TIME_WAIT state, and a container has about 28,200 ports available for one destination, so a router that sends more than about 28,000 requests to a single node starts returning 502. With three nodes the limit applies to each node separately.
- When the list of nodes changes, the router uses the new ring right away, but the keys that now belong to a different node aren't moved. Those keys read as missing until they're written again.
- Each key is stored on one node only, so a node that goes down makes its keys unavailable.

## Assumptions

- Keys are single URL path segments and can't contain `/`. Percent-encode special characters such as `?` and `#`.
- Values are any JSON value.
