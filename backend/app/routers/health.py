from fastapi import APIRouter

from ..config import settings
from ..minimax.client import MiniMaxError, get_json

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """探活：是否能拿到 MiniMax 模型列表。前端用它显示连通状态。"""
    info = {
        "backend": "ok",
        "base_url": settings.minimax_base_url,
        "group_id_tail": settings.minimax_group_id[-4:] if settings.minimax_group_id else "",
        "api_key_configured": bool(settings.minimax_api_key),
    }
    if not settings.minimax_api_key:
        return {**info, "minimax": "no_key"}
    try:
        data = await get_json("/v1/models")  # OpenAI 风格 list
        count = len(data.get("data", [])) if isinstance(data, dict) else 0
        return {**info, "minimax": "ok", "model_count": count}
    except MiniMaxError as e:
        return {**info, "minimax": "error", "error": e.message, "status": e.status}
