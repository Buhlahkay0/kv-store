# Single-Server Key-Value Store

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the server
```bash
python kv_store.py
```
The server listens on http://127.0.0.1:8080. Stop it with Ctrl+C, which saves a final snapshot.

## API
| Operation | Request | Success | Errors |
|-----------|---------|---------|--------|
| PUT | `POST /<key>` with body `{"value": ...}` | 200 | 400 if `value` is missing |
| GET | `GET /<key>` | 200 `{"value": ...}` | 404 if key not found |
| DEL | `DELETE /<key>` | 200 | 404 if key not found |

Examples:
```bash
curl -X POST -H "Content-Type: application/json" -d '{"value": "hello"}' localhost:8080/greeting
curl localhost:8080/greeting
curl -X DELETE localhost:8080/greeting
```

## Persistence and logging
- The store is saved to `kv_snapshot.json` every 5 seconds and on shutdown. It is reloaded when the server starts.
- Every operation is logged with a timestamp to `server.log`.

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
