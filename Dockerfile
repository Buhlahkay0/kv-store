FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kv_store.py router.py ./

# Listen on all interfaces so other containers can reach the node.
ENV HOST=0.0.0.0 \
    PORT=8080 \
    DATA_DIR=/data

EXPOSE 8080

# Runs a storage node. The router overrides this command in docker-compose.yml.
CMD ["python", "kv_store.py"]
