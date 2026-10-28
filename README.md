# Single-Server Key-Value Store

A key-value store served over HTTP, built with Python and Flask. It supports GET, PUT and DEL, handles concurrent requests, logs every operation, and persists data to disk.

## Setup
Requires Python 3.
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the server
```bash
python kv_store.py
```
The server listens on port 8080 (http://localhost:8080). Stop it with Ctrl+C, which saves a final snapshot. Use Ctrl+C rather than `kill`, otherwise up to 5 seconds of writes can be lost.

## Run with Docker
```bash
docker build -t kv-store .
docker run --rm -p 8080:8080 kv-store
```
The snapshot and log live inside the container, so they are lost when the container is removed. Stop the container with `docker stop` (it may take up to 10 seconds); a final snapshot is not guaranteed, so up to 5 seconds of recent writes can be lost.

## API
| Operation | Request | Success | Errors |
|-----------|---------|---------|--------|
| PUT | `POST` or `PUT /<key>` with body `{"value": ...}` | 200 | 400 if `value` is missing |
| GET | `GET /<key>` | 200 `{"value": ...}` | 404 if key not found |
| DEL | `DELETE /<key>` | 200 | 404 if key not found |

Examples:
```bash
curl -X POST -H "Content-Type: application/json" -d '{"value": "hello"}' localhost:8080/greeting
curl localhost:8080/greeting
curl -X DELETE localhost:8080/greeting
curl -i localhost:8080/greeting     # 404 after deletion
```

## Persistence and logging
- The store is saved to `kv_snapshot.json` every 5 seconds and on shutdown. It is reloaded when the server starts.
- Every operation is logged with a timestamp to `server.log`.
- Both files are created in the directory the server is run from.

## Benchmark
With the server running, in another terminal:
```bash
python kv_bench.py          # write phase, then read-and-verify phase
python kv_bench.py set      # write only
python kv_bench.py get      # verify only, after restarting the server
```
To test durability: run `set`, stop the server with Ctrl+C, restart it, then run `get`.

## Assumptions
- Keys are single URL path segments and cannot contain `/`. Please percent-encode special characters such as `?` and `#`.
- Values are any JSON value.
