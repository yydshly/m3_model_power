"""multipart 上统一端点。

设计：
- 前端 POST multipart/form-data 到 /api/upload/<cap_id>
- 后端按 capability 路由到上游：
    file-upload                 → /v1/files/upload         （purpose 来自 form 字段）
    voice-clone-upload-audio    → /v1/files/upload          purpose=voice_clone
    voice-clone-upload-prompt   → /v1/files/upload          purpose=prompt_audio
    music-cover-prep            → /v1/music_cover/preprocess（按官方 multipart 协议）
- 仍走 minimax.client 的鉴权，但不能用 JSON 客户端，故内联 httpx 调用

安全约束（P1-5）：
- file-upload 必须确认素材来源（confirm_asset_source form 字段）
- 文件大小上限 1MB，超限拒绝
- 不把文件二进制内容写入 history（只写摘要：filename/size/mime_type/purpose）
"""
from typing import Any

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ..config import settings
from ..minimax.client import MiniMaxError
from ..minimax_core.verification.history_store import append_history
from ..registry import get_registry

router = APIRouter(prefix="/upload", tags=["upload"])

MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB

# capability id → (上游路径, 默认 purpose)
UPLOAD_MAP = {
    "file-upload": ("/v1/files/upload", None),
    "voice-clone-upload-audio": ("/v1/files/upload", "voice_clone"),
    "voice-clone-upload-prompt": ("/v1/files/upload", "prompt_audio"),
    "music-cover-prep": ("/v1/music_cover/preprocess", None),
}


def _headers() -> dict[str, str]:
    key = settings.minimax_effective_api_key
    if not key:
        raise MiniMaxError(500, "MINIMAX_TOKEN_PLAN_KEY / MINIMAX_API_KEY 均未配置，请检查 backend/.env")
    # 注意：multipart 不能预设 Content-Type，让 httpx 自动加 boundary
    return {"Authorization": f"Bearer {key}"}


def _params(extra: dict | None = None) -> dict:
    p = dict(extra or {})
    if settings.minimax_group_id and "GroupId" not in p:
        p["GroupId"] = settings.minimax_group_id
    return p


def _build_history_payload(
    filename: str | None,
    size_bytes: int,
    content_type: str,
    purpose: str | None,
    confirm_asset_source: bool | None,
) -> dict[str, Any]:
    """Build a history-safe payload summary (no binary content)."""
    return {
        "filename": filename or "unknown",
        "size": size_bytes,
        "content_type": content_type,
        "purpose": purpose,
        "confirm_asset_source": confirm_asset_source is True,
    }


@router.post("/{cap_id}")
async def upload(
    cap_id: str,
    file: UploadFile = File(...),
    purpose: str | None = Form(default=None),
    confirm_asset_source: bool | None = Form(default=None),
) -> Any:
    reg = get_registry()
    cap = next((c for c in reg.capabilities if c.id == cap_id), None)
    if cap is None:
        raise HTTPException(404, f"unknown capability: {cap_id}")
    if not cap.multipart:
        raise HTTPException(400, f"capability {cap_id} 不是 multipart 上传类型")
    if cap_id not in UPLOAD_MAP:
        raise HTTPException(501, f"上传路由未配置：{cap_id}")

    content = await file.read()
    content_size = len(content)

    # P1-5 safety: file-upload requires explicit confirm_asset_source and size check
    if cap_id == "file-upload":
        if confirm_asset_source is not True:
            raise HTTPException(400, "file-upload requires confirm_asset_source=true in form data")
        if content_size == 0:
            raise HTTPException(400, "上传文件不能为空")
        if content_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(400, f"文件大小不得超过 {MAX_FILE_SIZE_BYTES // (1024*1024)} MB")
    else:
        if content_size == 0:
            raise HTTPException(400, "上传文件不能为空")

    path, default_purpose = UPLOAD_MAP[cap_id]
    real_purpose = purpose or default_purpose or (cap.example.get("purpose") if cap.example else None)

    files = {"file": (file.filename or "upload.bin", content, file.content_type or "application/octet-stream")}
    data: dict[str, Any] = {}
    if real_purpose:
        data["purpose"] = real_purpose

    async with httpx.AsyncClient(base_url=settings.minimax_base_url, timeout=120) as c:
        r = await c.post(path, headers=_headers(), params=_params(), data=data, files=files)

    # Build history-safe payload (no binary content)
    history_payload = _build_history_payload(
        filename=file.filename,
        size_bytes=content_size,
        content_type=file.content_type or "application/octet-stream",
        purpose=real_purpose,
        confirm_asset_source=confirm_asset_source,
    )

    if r.status_code >= 400:
        try:
            err = r.json()
            msg = err.get("base_resp", {}).get("status_msg") or err.get("message") or r.text
        except ValueError:
            msg = r.text
        # Write failed upload to history (summary only, no binary)
        history_id = append_history(
            action="upload",
            capability_id=cap_id,
            payload=history_payload,
            confirmations={"confirm_asset_source": confirm_asset_source is True},
            result={"ok": False, "error": "minimax_error", "status": r.status_code, "message": msg},
        )
        content: dict[str, Any] = {"error": "minimax_error", "status": r.status_code, "message": msg}
        if history_id:
            content["history_id"] = history_id
        return JSONResponse(
            status_code=502 if r.status_code >= 500 else r.status_code,
            content=content,
        )

    # Success: parse response, write history with result summary (no binary)
    try:
        response_data = r.json()
    except ValueError:
        response_data = {"raw": r.text}

    # Write successful upload to history — result_summary is built by summarize_result(),
    # which extracts file_id/filename/etc. from response_data automatically.
    history_id = append_history(
        action="upload",
        capability_id=cap_id,
        payload=history_payload,
        confirmations={"confirm_asset_source": confirm_asset_source is True},
        result={"ok": True, "data": response_data},
    )

    content: dict[str, Any] = {"ok": True, "data": response_data}
    if history_id:
        content["history_id"] = history_id
    return content
