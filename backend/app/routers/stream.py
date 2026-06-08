"""SSE 流式代理：仅对 streaming=true 的 capability 开放。

设计思路：
- 配置驱动，由 capabilities.yaml 的 streaming + mm_path 决定上游路径
- 不在前端暴露 Key，复用 minimax.client 的鉴权
- 当前覆盖 chat-anthropic / chat-openai / chat-responses-create

历史写入（P1-2）：
- 流结束后写入摘要到 history.jsonl（不写完整流内容）
- 摘要包含 chunk_count、text_preview 前 1000 字、duration_ms、ok/error
"""
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..minimax.client import stream_post
from ..minimax_core.verification.history_store import append_history
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

    t0 = time.perf_counter()

    async def gen():
        chunk_count = 0
        preview_parts: list[str] = []
        try:
            async for chunk in stream_post(path, body, timeout=600):
                chunk_count += 1
                if len("".join(preview_parts)) < 1000:
                    try:
                        decoded = chunk.decode("utf-8", errors="ignore") if isinstance(chunk, bytes) else str(chunk)
                        preview_parts.append(decoded)
                    except Exception:
                        pass
                yield chunk

            duration_ms = int((time.perf_counter() - t0) * 1000)
            append_history(
                action="stream",
                capability_id=cap_id,
                payload=body,
                confirmations={},
                result={
                    "ok": True,
                    "data": {
                        "stream": True,
                        "chunk_count": chunk_count,
                        "text_preview": "".join(preview_parts)[:1000],
                    },
                },
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            append_history(
                action="stream",
                capability_id=cap_id,
                payload=body,
                confirmations={},
                result={
                    "ok": False,
                    "error": "stream_error",
                    "message": str(e),
                    "chunk_count": chunk_count,
                },
                duration_ms=duration_ms,
            )
            raise

    return StreamingResponse(gen(), media_type="text/event-stream")
