import threading
import time
from flask import Flask, request, jsonify
import logging
import json
import os
import atexit

# The base URL of the Flask server
BASE_URL = 'http://127.0.0.1:8080'
SNAPSHOT_INTERVAL = 5
PORT = int(os.environ.get("PORT", "8080"))
HOST = os.environ.get("HOST", "127.0.0.1")
DATA_DIR = os.environ.get("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)
SNAPSHOT_FILE = os.path.join(DATA_DIR, "kv_snapshot.json")
LOG_FILE = os.path.join(DATA_DIR, "server.log")

app = Flask(__name__)

kv_store = {}
lock = threading.Lock()

logger = logging.getLogger("kv_store")
logger.setLevel(logging.INFO)
logger.propagate = False

file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))

logger.addHandler(file_handler)

@app.route('/<key>', methods=['GET'])
def get_value(key):
    with lock:
        exists = key in kv_store
        value = kv_store[key] if exists else None
        
    if exists:
        logger.info(f"GET {key} succeeded: Value retrieved")
        return jsonify({'value': value}), 200
    else:
        logger.warning(f"GET {key} failed: Key not found")
        return jsonify({'error': 'Key not found'}), 404

@app.route('/<key>', methods=['POST', 'PUT'])
def set_value(key):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or 'value' not in data:
        logger.warning(f"PUT {key} failed: Invalid request, missing value")
        return jsonify({'error': 'Invalid request, missing value'}), 400
    with lock:
        kv_store[key] = data['value']

    logger.info(f"PUT {key} succeeded: Value set to {data['value']}")
    return jsonify({'message': 'Value set successfully'}), 200

@app.route('/<key>', methods=['DELETE'])
def delete_value(key):
    with lock:
        exists = key in kv_store
        if exists:
            del kv_store[key]

    if exists:
        logger.info(f"DELETE {key} succeeded: Key deleted")
        return jsonify({'message': 'Key deleted successfully'}), 200
    else:
        logger.warning(f"DELETE {key} failed: Key not found")
        return jsonify({'error': 'Key not found'}), 404

def load_snapshot():
    if os.path.exists(SNAPSHOT_FILE):
        with open(SNAPSHOT_FILE, encoding="utf-8") as f:
            kv_store.update(json.load(f))

def save_snapshot():
    with lock:
        data = dict(kv_store)
    temp = SNAPSHOT_FILE + ".tmp"
    with open(temp, "w", encoding="utf-8") as file:
        json.dump(data, file)
    # Atomic write
    os.replace(temp, SNAPSHOT_FILE)

def snapshot_loop():
    while True:
        time.sleep(SNAPSHOT_INTERVAL)
        save_snapshot()

if __name__ == '__main__':
    load_snapshot()
    threading.Thread(target=snapshot_loop, daemon=True).start()
    atexit.register(save_snapshot)
    app.run(host=HOST, port=PORT, threaded=True)