"""核心规格类型：ModelSpec / CapabilitySpec。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


BillingCategory = Literal[
    "normal_token_plan_test",
    "quota_sensitive",
    "paid_confirm_required",
    "high_cost_confirm_required",
    "asset_required_confirm_required",
]


class BillingPolicy(BaseModel):
    billing_category: BillingCategory = "normal_token_plan_test"
    requires_explicit_confirmation: bool = False
    may_charge_extra: bool = False
    consumes_token_plan_quota: bool = True
    requires_certification: bool = False
    requires_uploaded_asset: bool = False
    billing_note: str = ""
    official_pricing_note: str = ""


OperationRisk = Literal[
    "normal",
    "destructive",
    "asset_required",
    "existing_task_only",
    "long_running",
    "quota_guarded",
]


class OperationPolicy(BaseModel):
    operation_risk: OperationRisk = "normal"
    requires_operation_confirmation: bool = False
    requires_uploaded_asset: bool = False
    requires_existing_task: bool = False
    is_destructive: bool = False
    is_long_running: bool = False
    max_default_chars: int | None = None
    requires_confirmation_above_chars: int | None = None
    hard_block_above_chars_without_confirm: int | None = None
    operation_note: str | None = None


class ModelSpec(BaseModel):
    """MiniMax 模型规格定义。

    用于 /api/registry 返回模型清单，
    也可用于其他项目直接导入复用。
    """
    id: str = Field(..., description="上游 model 字段实际值（API 调用直接用它）")
    label: str = Field(..., description="UI 显示名")
    family: Literal["chat", "speech", "image", "video", "music"] = Field(..., description="模型族")
    tier: Literal["flagship", "highspeed", "standard", "hd", "turbo", "legacy", "deprecated"] = Field(
        default="standard")
    official_current: bool = Field(default=False, description="官方当前文档是否列出该模型")
    live_available: bool | None = Field(default=None, description="真实 API /v1/models 是否返回（null=未验收）")
    subscription_expected: bool | str | None = Field(
        default=None, description="用户订阅套餐是否覆盖该模型；字符串时表示 unknown")
    enabled: bool = Field(default=True, description="前端默认显示")
    context: int | None = Field(default=None, description="最大上下文长度（仅 chat 系列）")
    input_modalities: list[str] = Field(
        default_factory=list,
        description="输入模态：text | image | video | audio")
    output_modalities: list[str] = Field(
        default_factory=list,
        description="输出模态：text | image | video | audio | music")
    protocols: list[str] = Field(
        default_factory=list,
        description="支持协议：openai | anthropic | responses | native")
    capabilities: list[str] = Field(
        default_factory=list,
        description="显式声明这个模型支持哪些 capability id；空则按 family 自动匹配")
    supports_tools: bool = Field(default=False, description="是否支持工具调用")
    supports_thinking: bool = Field(default=False, description="是否支持 thinking block")
    thinking_can_disable: bool = Field(default=False, description="thinking 是否可关闭")
    cost_level: Literal["quota", "low", "medium", "high", "unknown"] = Field(default="unknown")
    discovery_method: Literal["models_api", "capability_probe", "manual_official"] | None = Field(
        default=None)
    discovery_status: Literal["available", "unavailable", "not_applicable", "unknown"] | None = Field(
        default=None)
    discovery_note: str = Field(default="")
    note: str = Field(default="", description="UI 提示文案")
    quota_eligible: bool = Field(default=False, description="是否走 TokenPlanPlus 共享配额")


class CapabilitySpec(BaseModel):
    """MiniMax 能力规格定义。

    用于 /api/registry 返回能力清单，
    也可用于其他项目直接导入复用。
    """
    id: str = Field(..., description="唯一标识，前后端路由也走它")
    name: str = Field(..., description="中文名（capabilities.yaml label）")
    category: str = Field(..., description="能力分类 id（chat/voice/vision/music/files/models）")
    endpoint: str = Field(..., description="上游 MiniMax 路径，如 /v1/chat/completions")
    method: Literal["GET", "POST", "WS"] = Field(default="POST")
    protocol: Literal["openai", "anthropic", "responses", "native"] = Field(
        default="native")
    model_family: str | None = Field(
        default=None,
        description="关联模型族：chat/speech/image/video/music；用于按 family 过滤模型")
    protocols: list[str] = Field(
        default_factory=list,
        description="协议列表，用于过滤模型下拉，如 [openai], [anthropic], [responses]")
    supported_models: list[str] = Field(
        default_factory=list,
        description="支持该能力的模型 id 列表；空表示按 family 自动推断")
    default_model: str | None = Field(default=None)
    is_streaming: bool = Field(default=False)
    is_async: bool = Field(default=False, description="是否长任务（提交→轮询→下载）")
    requires_upload: bool = Field(default=False, description="是否需要 multipart 上传")
    cost_level: Literal["none", "quota", "low", "medium", "high"] = Field(default="quota")
    doc_url: str = Field(default="")
    status: Literal["implemented", "planned", "unsupported"] = Field(default="planned")
    requires_model: bool = Field(
        default=True,
        description="该能力是否需要选择模型；false = 如 lyrics-gen / file-* / models-list，无需模型即可调用")
    billing_policy: BillingPolicy = Field(default_factory=BillingPolicy)
    operation_policy: OperationPolicy = Field(default_factory=OperationPolicy)
