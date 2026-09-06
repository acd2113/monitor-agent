import asyncio
import threading
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.infrastructure.llm_client import LLMClient
from src.pipeline.orchestrator import MonitorOrchestrator

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="MonitorAgent")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


def item_dict(item):
    data = asdict(item)
    if item.published_at:
        data["published_at"] = item.published_at.isoformat()
    return data


def plan_dict(plan):
    return asdict(plan)


def session_dict(session):
    return {
        "topic": session.topic,
        "items": [item_dict(item) for item in session.items],
        "timeline": [
            {"label": group.label, "items": [item_dict(item) for item in group.items]}
            for group in session.timeline
        ],
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_running_loop()

    async def send(event):
        try:
            await websocket.send_json(event)
        except Exception:
            pass

    def emit_status(kind, text):
        asyncio.run_coroutine_threadsafe(send({"type": "status", "text": text}), loop)

    def emit_plan(plan):
        asyncio.run_coroutine_threadsafe(send({"type": "plan", "data": plan_dict(plan)}), loop)

    def emit_channel(channel_id, kind, text):
        asyncio.run_coroutine_threadsafe(
            send({"type": "channel", "channel_id": channel_id, "kind": kind, "text": text}), loop
        )

    def emit_item(item):
        asyncio.run_coroutine_threadsafe(
            send({"type": "item_result", "data": item_dict(item)}), loop
        )

    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") != "start":
                continue
            topic = str(message.get("topic", "")).strip()
            if not topic:
                continue

            def run():
                try:
                    client = LLMClient()
                    session = MonitorOrchestrator(client).run(
                        topic,
                        on_event=emit_status,
                        on_plan=emit_plan,
                        on_channel_event=emit_channel,
                        on_item=emit_item,
                    )
                    asyncio.run_coroutine_threadsafe(
                        send({"type": "result", "data": session_dict(session)}), loop
                    )
                except Exception as exc:
                    asyncio.run_coroutine_threadsafe(
                        send({"type": "error", "text": str(exc)}), loop
                    )

            threading.Thread(target=run, daemon=True).start()
    except WebSocketDisconnect:
        pass
