from fastapi import FastAPI, Request
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()

    for alert in payload.get("alerts", []):
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        logger.info(
            "alert received | name=%s status=%s namespace=%s pod=%s severity=%s summary=%s",
            labels.get("alertname"),
            alert.get("status"),
            labels.get("namespace"),
            labels.get("pod"),
            labels.get("severity"),
            annotations.get("summary"),
        )

    return {"status": "received"}


@app.get("/health")
def health():
    return {"status": "ok"}
