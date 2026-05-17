"""
Credential-free demo services for docker-compose.demo.yml.

These mocks are intentionally small. They prove the launch/demo stack can boot
without real Twilio or OpenAI credentials, but they are not production adapters.
"""

import os
from datetime import datetime, timezone

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse


SERVICE_NAME = os.getenv("DEMO_SERVICE", "api")

app = FastAPI(title=f"Outvox demo {SERVICE_NAME}", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/")
async def root():
    return {
        "service": f"outvox-demo-{SERVICE_NAME}",
        "status": "ok",
        "timestamp": now_iso(),
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "timestamp": now_iso(),
    }


@app.get("/api/demo/status")
async def demo_status():
    return {
        "status": "ready",
        "database": os.getenv("DATABASE_URL", "not configured"),
        "openai_mock": os.getenv("OPENAI_BASE_URL", "http://mock-openai:8081"),
        "twilio_mock": os.getenv("TWILIO_BASE_URL", "http://mock-twilio:8082"),
        "credentials_required": False,
    }


@app.post("/2010-04-01/Accounts/{account_sid}/Messages.json")
async def create_message(account_sid: str, request: Request):
    form = await request.form()
    return JSONResponse(
        {
            "sid": "SM_DEMO_MESSAGE",
            "account_sid": account_sid,
            "status": "queued",
            "to": form.get("To"),
            "from": form.get("From"),
            "body": form.get("Body"),
            "date_created": now_iso(),
        }
    )


@app.post("/2010-04-01/Accounts/{account_sid}/Calls.json")
async def create_call(account_sid: str, request: Request):
    form = await request.form()
    return JSONResponse(
        {
            "sid": "CA_DEMO_CALL",
            "account_sid": account_sid,
            "status": "queued",
            "to": form.get("To"),
            "from": form.get("From"),
            "url": form.get("Url"),
            "date_created": now_iso(),
        }
    )


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "gpt-realtime-demo",
                "object": "model",
                "owned_by": "outvox-demo",
            }
        ],
    }


@app.websocket("/v1/realtime")
async def realtime(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json(
        {
            "type": "session.created",
            "session": {
                "id": "sess_demo",
                "model": "gpt-realtime-demo",
            },
        }
    )
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_json(
                {
                    "type": "response.text.delta",
                    "delta": f"demo echo: {message[:80]}",
                }
            )
    except Exception:
        await websocket.close()


@app.api_route("/twilio-voice", methods=["GET", "POST"])
async def twilio_voice():
    return PlainTextResponse(
        """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice">This is the Outvox credential-free demo.</Say>
</Response>""",
        media_type="application/xml",
    )
