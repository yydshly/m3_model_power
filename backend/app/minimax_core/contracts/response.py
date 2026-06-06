"""响应与错误结构：AssetRef / UnifiedResponse / UnifiedError。"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AssetRef(BaseModel):
    """统一资产引用。

    用于 UnifiedResponse 和 VerificationResult 中描述产出资产。
    不直接存储二进制，只记录引用和元数据。
    """
    type: Literal["audio", "image", "video", "music", "text", "file"] = Field(..., description="资产类型")
    format: str | None = Field(default=None, description="格式：mp3 / wav / png / jpg / mp4 等")
    path: str | None = Field(default=None, description="本地路径（runtime 资产）")
    url: str | None = Field(default=None, description="远程 URL（如 image_urls[0]）")
    size_bytes: int | None = Field(default=None, description="字节大小")
    duration_ms: int | None = Field(default=None, description="音视频时长（毫秒）")
    committed: bool = Field(default=False, description="是否已提交 Git（应为 False）")


class UnifiedResponse(BaseModel):
    """统一响应结构。

    minimax_core 发出的所有成功响应都使用这个结构。
    前端或调用方可以根据 output_type 字段决定如何解析。
    """
    ok: bool = Field(default=True)
    capability_id: str = Field(..., description="能力 id")
    model: str | None = Field(default=None, description="实际调用的模型 id")
    output_type: Literal["text", "audio", "image", "video", "music", "file", "json"] = Field(
        ..., description="产出类型")
    text: str | None = Field(default=None, description="文本产出（对话/歌词等）")
    assets: list[AssetRef] = Field(default_factory=list, description="资产引用列表")
    task: dict[str, Any] | None = Field(
        default=None, description="异步任务信息（如 task_id）")
    usage: dict[str, Any] | None = Field(default=None, description="用量信息")
    raw: dict[str, Any] | None = Field(
        default=None, description="原始上游响应（脱敏后）")


class UnifiedError(BaseModel):
    """统一错误结构。

    minimax_core 发出的所有失败响应都使用这个结构。
    敏感字段（API Key、订单号等）已被脱敏。
    """
    ok: bool = Field(default=False, constant=True)
    capability_id: str = Field(..., description="失败的能力 id")
    error_type: Literal[
        "timeout", "invalid_params", "unauthorized", "quota_limited",
        "rate_limited", "upstream_error", "network_error", "unknown"
    ] = Field(default="unknown")
    error_code: str | None = Field(default=None, description="上游错误码")
    message: str = Field(..., description="人类可读错误信息（已脱敏）")
    http_status: int | None = Field(default=None)
    retryable: bool = Field(default=False, description="是否可重试")
    redacted: bool = Field(default=True, constant=True, description="敏感信息已脱敏")
