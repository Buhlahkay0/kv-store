import os

import requests
from flask import Flask, Response, jsonify, request
from uhashring import HashRing

BACKENDS = [url.strip() for url in os.environ.get("BACKENDS", "").split(",") if url.strip()]
ring = HashRing(nodes=BACKENDS)

app = Flask(__name__)


@app.route("/<key>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy(key):
    node = ring.get_node(key)
    if node is None:
        return jsonify({"error": "No nodes available"}), 503
    try:
        response = requests.request(
            request.method,
            f"{node}/{key}",
            data=request.get_data(),
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
    except requests.RequestException:
        return jsonify({"error": f"Node {node} unavailable"}), 502
    return Response(response.content, status=response.status_code, content_type="application/json")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, threaded=True)
