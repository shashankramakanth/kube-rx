import os
import time
import threading
from fastapi import FastAPI, Request
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


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    endpoint = request.url.path
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        status_code=response.status_code,
    ).inc()
    REQUEST_DURATION.labels(endpoint=endpoint).observe(duration)

    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/stress")
def stress():
    def burn():
        end = time.time() + 30
        while time.time() < end:
            pass

    threading.Thread(target=burn, daemon=True).start()
    return {"status": "stressing", "duration_seconds": 30}


@app.get("/crash")
def crash():
    os._exit(1)
