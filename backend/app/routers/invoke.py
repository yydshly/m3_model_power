"""统一调用入口。所有已实现 capability 都通过 POST /api/invoke/<id> 触发，
前端只关心 capability id 和 payload，不关心上游具体路径。

这样：
- 前端代码量恒定，新能力只需 register_handler
- 鉴权、错误归一化、未实现拦截只写一次
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..minimax.client import MiniMaxError
from ..registry import HANDLERS, get_registry

router = APIRouter(prefix="/invoke", tags=["invoke"])


@router.post("/{cap_id}")
async def invoke(cap_id: str, payload: dict | None = None) -> JSONResponse:
    reg = get_registry()
    cap = next((c for c in reg.capabilities if c.id == cap_id), None)
    if cap is None:
        raise HTTPException(404, f"unknown capability: {cap_id}")
    if cap.status == "unsupported":
        raise HTTPException(403, f"capability {cap_id} 在当前订阅档位下不可用")
    if cap.multipart:
        raise HTTPException(
            400,
            f"capability {cap_id} 是 multipart 上传，请走 POST /api/upload/{cap_id}",
        )
    handler = HANDLERS.get(cap_id)
    if handler is None:
        raise HTTPException(501, f"capability {cap_id} 尚未实现 handler")
    try:
        result = await handler(payload or {})
    except MiniMaxError as e:
        return JSONResponse(
            status_code=502 if e.status >= 500 else e.status,
            content={"error": "minimax_error", "status": e.status, "message": e.message},
        )
    return JSONResponse(content={"ok": True, "data": result})
