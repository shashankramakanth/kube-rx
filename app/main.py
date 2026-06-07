import os
import time
import threading
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["endpoint"],
)


@app.get("/health")
def health():
    REQUEST_COUNT.labels(method="GET", endpoint="/health", status_code=200).inc()
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/stress")
def stress():
    REQUEST_COUNT.labels(method="GET", endpoint="/stress", status_code=200).inc()

    def burn():
        end = time.time() + 30
        while time.time() < end:
            pass

    threading.Thread(target=burn, daemon=True).start()
    return {"status": "stressing", "duration_seconds": 30}


@app.get("/crash")
def crash():
    REQUEST_COUNT.labels(method="GET", endpoint="/crash", status_code=200).inc()
    os._exit(1)
