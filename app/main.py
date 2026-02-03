from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, bot, conversations, realtime, webhooks

app = FastAPI()
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(bot.router, prefix="/bot", tags=["bot"])
app.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
app.include_router(realtime.router, prefix="/realtime", tags=["realtime"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index() -> HTMLResponse:
    index_path = static_dir / "index.html"
    return HTMLResponse(index_path.read_text(encoding="utf-8"))
