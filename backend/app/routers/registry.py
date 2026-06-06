from fastapi import APIRouter, HTTPException

from ..registry import HANDLERS, get_registry, reload_registry

router = APIRouter(prefix="/registry", tags=["registry"])


@router.get("")
async def registry() -> dict:
    """前端启动时拉一次，渲染整个工作台。"""
    reg = get_registry()
    return {
        "categories": [c.model_dump() for c in reg.categories],
        "capabilities": [
            {**c.model_dump(), "has_handler": c.id in HANDLERS} for c in reg.capabilities
        ],
        "models": [m.model_dump() for m in reg.models],
    }


@router.get("/capabilities/{cap_id}/models")
async def models_for(cap_id: str) -> list[dict]:
    reg = get_registry()
    if not any(c.id == cap_id for c in reg.capabilities):
        raise HTTPException(404, f"unknown capability: {cap_id}")
    return [m.model_dump() for m in reg.models_for_capability(cap_id)]


@router.post("/reload")
async def reload_() -> dict:
    """运行时改 YAML 后调用，无需重启。"""
    reload_registry()
    reg = get_registry()
    return {"ok": True, "capabilities": len(reg.capabilities), "models": len(reg.models)}
