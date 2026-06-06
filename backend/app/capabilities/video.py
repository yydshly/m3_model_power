"""视频生成：3 种入口 + 任务查询 + 下载。"""
from typing import Any

from ..minimax.client import get_json, post_json
from ..registry import register_handler


@register_handler("video-t2v")
async def video_t2v(payload: dict) -> Any:
    return await post_json("/v1/video_generation", payload, with_group=True, timeout=60)


@register_handler("video-i2v")
async def video_i2v(payload: dict) -> Any:
    return await post_json("/v1/video_generation", payload, with_group=True, timeout=60)


@register_handler("video-s2v")
async def video_s2v(payload: dict) -> Any:
    return await post_json("/v1/video_generation", payload, with_group=True, timeout=60)


@register_handler("video-query")
async def video_query(payload: dict) -> Any:
    task_id = payload.get("task_id")
    if not task_id:
        raise ValueError("缺少参数 task_id")
    return await get_json("/v1/query/video_generation", params={"task_id": task_id}, with_group=True)


@register_handler("video-download")
async def video_download(payload: dict) -> Any:
    """视频任务完成后，上游返回 file_id；这里查询文件元数据。
    实际下载走 file-content（/api/download/file-content?file_id=...）。
    """
    file_id = payload.get("file_id")
    if not file_id:
        raise ValueError("缺少参数 file_id")
    return await get_json("/v1/files/retrieve", params={"file_id": file_id}, with_group=True)
