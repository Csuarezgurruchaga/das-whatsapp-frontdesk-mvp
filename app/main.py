from fastapi import FastAPI

from app.api import auth, bot, conversations, realtime, webhooks

app = FastAPI()
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(bot.router, prefix="/bot", tags=["bot"])
app.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
app.include_router(realtime.router, prefix="/realtime", tags=["realtime"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
