"""验收结果结构：VerificationResult。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class VerificationResult(BaseModel):
    """单次能力验收结果。

    用于 /api/verify 或内部验收流程的标准化输出。
    """
    capability_id: str = Field(..., description="能力 id")
    level: Literal["safe", "medium", "high"] = Field(default="safe", description="验收级别")
    status: Literal[
        "success", "success_with_warning", "failed", "skipped",
        "unauthorized", "quota_limited", "timeout"
    ] = Field(..., description="验收状态")
    model: str | None = Field(default=None, description="实际调用的模型")
    http_status: int | None = Field(default=None)
    latency_ms: int | None = Field(default=None)
    output_type: str | None = Field(default=None)
    # 资产
    audio_returned: bool | None = Field(
        default=None,
        description="data.audio / data.audio_url 是否存在于响应中")
    audio_payload_type: Literal["hex", "url", "text", "unknown"] | None = Field(
        default=None)
    asset_saved: bool | None = Field(
        default=None,
        description="音频/图片文件是否写入 runtime/assets/")
    asset_committed: bool | None = Field(
        default=None,
        description="runtime 资产是否已提交 Git（应为 False）")
    # 可选扩展字段（能力相关）
    audio_format: str | None = Field(default=None)
    audio_length: int | None = Field(default=None, description="音频时长 ms")
    audio_sample_rate: int | None = Field(default=None)
    asset_size: int | None = Field(default=None, description="字节大小")
    image_urls_count: int | None = Field(default=None)
    success_count: int | None = Field(default=None)
    failed_count: int | None = Field(default=None)
    music_duration: int | None = Field(default=None, description="音乐时长 ms")
    bitrate: int | None = Field(default=None)
    song_title: str | None = Field(default=None)
    lyrics_preview: str | None = Field(default=None)
    # 错误
    error_type: str | None = Field(default=None)
    error_message: str | None = Field(default=None)
    # 元数据
    started_at: str | None = Field(default=None)
    ended_at: str | None = Field(default=None)
