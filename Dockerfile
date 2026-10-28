FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY kv_store.py .

# Bind to all interfaces so the server is reachable from outside the container
RUN sed -i "s/host='127.0.0.1'/host='0.0.0.0'/" kv_store.py

EXPOSE 8080

CMD ["python", "kv_store.py"]