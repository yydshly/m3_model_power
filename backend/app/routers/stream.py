"""SSE 流式代理：仅对 streaming=true 的 capability 开放。

设计思路：
- 配置驱动，由 capabilities.yaml 的 streaming + mm_path 决定上游路径
- 不在前端暴露 Key，复用 minimax.client 的鉴权
- 当前覆盖 chat-anthropic / chat-openai / chat-responses-create
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..minimax.client import stream_post
from ..registry import get_registry

router = APIRouter(prefix="/stream", tags=["stream"])

# 哪些 capability 走流式 + 是否要把 stream=true 注入 body
STREAM_MAP = {
    "chat-anthropic": ("/anthropic/v1/messages", True),
    "chat-openai": ("/v1/chat/completions", True),
    "chat-responses-create": ("/v1/responses", True),
}


@router.post("/{cap_id}")
async def stream(cap_id: str, payload: dict) -> StreamingResponse:
    reg = get_registry()
    cap = next((c for c in reg.capabilities if c.id == cap_id), None)
    if cap is None:
        raise HTTPException(404, f"unknown capability: {cap_id}")
    if not cap.streaming:
        raise HTTPException(400, f"capability {cap_id} 不是流式")
    if cap_id not in STREAM_MAP:
        raise HTTPException(501, f"流式代理未配置该能力：{cap_id}")
    path, inject_stream = STREAM_MAP[cap_id]
    body = {**payload}
    if inject_stream:
        body["stream"] = True

    async def gen():
        async for chunk in stream_post(path, body, timeout=600):
            yield chunk

    return StreamingResponse(gen(), media_type="text/event-stream")
