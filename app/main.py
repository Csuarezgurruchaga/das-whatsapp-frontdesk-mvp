from fastapi import FastAPI

from app.api import auth, bot, conversations

app = FastAPI()
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(bot.router, prefix="/bot", tags=["bot"])
app.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
