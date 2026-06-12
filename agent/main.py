import logging
from fastapi import FastAPI, BackgroundTasks, Request
from investigator import investigate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()

    for alert in payload.get("alerts", []):
        labels = alert.get("labels", {})
        logger.info(
            "alert received | name=%s status=%s namespace=%s pod=%s severity=%s",
            labels.get("alertname"),
            alert.get("status"),
            labels.get("namespace"),
            labels.get("pod"),
            labels.get("severity"),
        )
        if alert.get("status") == "firing":
            background_tasks.add_task(investigate, alert)

    return {"status": "received"}


@app.get("/health")
def health():
    return {"status": "ok"}
