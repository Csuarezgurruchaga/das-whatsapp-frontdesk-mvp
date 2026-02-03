from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db.session import SessionLocal, get_engine
from app.realtime import WebSocketAuthError, get_current_user_for_websocket, manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    db = SessionLocal(bind=get_engine())
    try:
        try:
            user = get_current_user_for_websocket(websocket, db)
        except WebSocketAuthError:
            await websocket.accept()
            await websocket.close(code=1008)
            return

        await manager.connect(websocket, user)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    finally:
        db.close()
