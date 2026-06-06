"""capability id → handler 的注册中心。

用法：
    @register_handler("voice-list")
    async def voice_list(payload: dict) -> Any: ...

前端调用 POST /api/invoke/<cap_id>，body 为该 capability 的输入。
未注册 handler 的 capability 会被 invoke 路由报 501（与 YAML status=implemented 双重判定）。
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

Handler = Callable[[dict], Awaitable[Any]]

HANDLERS: dict[str, Handler] = {}


def register_handler(cap_id: str) -> Callable[[Handler], Handler]:
    def deco(fn: Handler) -> Handler:
        if cap_id in HANDLERS:
            raise RuntimeError(f"handler for {cap_id} already registered")
        HANDLERS[cap_id] = fn
        return fn

    return deco
