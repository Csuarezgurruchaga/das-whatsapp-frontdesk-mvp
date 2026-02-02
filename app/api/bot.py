from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import require_roles
from app.bot.menu import BotConfigError, get_bot_menu_yaml_path, reload_bot_config
from app.db.models import User, UserRole

router = APIRouter()


class BotReloadResponse(BaseModel):
    ok: bool
    root: str
    node_count: int
    path: str


@router.post("/reload", response_model=BotReloadResponse)
def reload_bot_menu(
    _current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> BotReloadResponse:
    path = get_bot_menu_yaml_path()
    try:
        config = reload_bot_config(path)
    except BotConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": exc.errors},
        ) from exc

    return BotReloadResponse(
        ok=True,
        root=config.root,
        node_count=len(config.nodes),
        path=path,
    )
