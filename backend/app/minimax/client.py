"""统一的 MiniMax HTTP 客户端 —— 所有外部调用都从这里走。"""
from __future__ import annotations

from typing import Any, AsyncIterator

import httpx

from ..config import settings


class MiniMaxError(Exception):
    def __init__(self, status: int, message: str, payload: Any = None) -> None:
        super().__init__(f"[MiniMax {status}] {message}")
        self.status = status
        self.message = message
        self.payload = payload


def _auth_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    if not settings.minimax_api_key:
        raise MiniMaxError(500, "MINIMAX_API_KEY 未配置，请检查 backend/.env")
    headers = {
        "Authorization": f"Bearer {settings.minimax_api_key}",
        "Content-Type": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def _with_group_id(params: dict[str, Any] | None = None) -> dict[str, Any]:
    p = dict(params or {})
    if settings.minimax_group_id and "GroupId" not in p:
        p["GroupId"] = settings.minimax_group_id
    return p


def _client(timeout: float = 60.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=settings.minimax_base_url, timeout=timeout)


async def get_json(path: str, *, params: dict[str, Any] | None = None, with_group: bool = False) -> Any:
    async with _client() as c:
        r = await c.get(path, headers=_auth_headers(), params=_with_group_id(params) if with_group else params)
        return _parse(r)


async def post_json(
    path: str,
    body: dict[str, Any],
    *,
    params: dict[str, Any] | None = None,
    with_group: bool = False,
    timeout: float = 120.0,
) -> Any:
    async with _client(timeout=timeout) as c:
        r = await c.post(
            path,
            headers=_auth_headers(),
            params=_with_group_id(params) if with_group else params,
            json=body,
        )
        return _parse(r)


async def post_bytes(
    path: str,
    body: dict[str, Any],
    *,
    params: dict[str, Any] | None = None,
    with_group: bool = False,
    timeout: float = 120.0,
) -> tuple[bytes, str]:
    """用于直接返回音频/图像字节流的接口。"""
    async with _client(timeout=timeout) as c:
        r = await c.post(
            path,
            headers=_auth_headers(),
            params=_with_group_id(params) if with_group else params,
            json=body,
        )
        if r.status_code >= 400:
            _parse(r)
        return r.content, r.headers.get("content-type", "application/octet-stream")


async def stream_post(
    path: str,
    body: dict[str, Any],
    *,
    params: dict[str, Any] | None = None,
    with_group: bool = False,
    timeout: float = 600.0,
) -> AsyncIterator[bytes]:
    """SSE / chunked 流式转发。"""
    client = _client(timeout=timeout)
    try:
        async with client.stream(
            "POST",
            path,
            headers=_auth_headers(),
            params=_with_group_id(params) if with_group else params,
            json=body,
        ) as r:
            if r.status_code >= 400:
                content = await r.aread()
                raise MiniMaxError(r.status_code, content.decode("utf-8", errors="replace"))
            async for chunk in r.aiter_bytes():
                yield chunk
    finally:
        await client.aclose()


def _parse(r: httpx.Response) -> Any:
    if r.status_code >= 400:
        try:
            data = r.json()
            msg = data.get("base_resp", {}).get("status_msg") or data.get("message") or r.text
            raise MiniMaxError(r.status_code, msg, data)
        except ValueError:
            raise MiniMaxError(r.status_code, r.text or r.reason_phrase)
    try:
        return r.json()
    except ValueError:
        return r.text
