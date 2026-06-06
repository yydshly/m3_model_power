"""文件管理（JSON 接口部分；上传/multipart 在 routers/upload.py）。"""
import base64
from typing import Any

from ..minimax.client import get_json, post_bytes, post_json
from ..registry import register_handler


@register_handler("file-list")
async def file_list(payload: dict) -> Any:
    params = {"purpose": payload.get("purpose")} if payload.get("purpose") else None
    return await get_json("/v1/files/list", params=params, with_group=True)


@register_handler("file-retrieve")
async def file_retrieve(payload: dict) -> Any:
    file_id = payload.get("file_id")
    if not file_id:
        raise ValueError("缺少参数 file_id")
    return await get_json("/v1/files/retrieve", params={"file_id": file_id}, with_group=True)


@register_handler("file-delete")
async def file_delete(payload: dict) -> Any:
    file_id = payload.get("file_id")
    if not file_id:
        raise ValueError("缺少参数 file_id")
    return await post_json("/v1/files/delete", {"file_id": file_id}, with_group=True)


@register_handler("file-content")
async def file_content(payload: dict) -> Any:
    """返回二进制内容的 base64，便于前端在 JSON 通道里展示/下载。
    大文件建议直接走 GET /api/download/file-content?file_id=... 二进制流。
    """
    file_id = payload.get("file_id")
    if not file_id:
        raise ValueError("缺少参数 file_id")
    # 上游既可能是 application/octet-stream，也可能 JSON 含 download_url —— 先尝试 JSON
    data = await get_json("/v1/files/retrieve_content", params={"file_id": file_id}, with_group=True)
    return data


# post_bytes 预留供后续直接代理二进制场景
_ = post_bytes
