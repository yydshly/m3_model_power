"""OpenAI 兼容协议客户端。

覆盖端点：
  /v1/models          — 模型列表
  /v1/models/{model} — 模型详情
  /v1/chat/completions
  /v1/responses
  /v1/responses/input_tokens
"""
from __future__ import annotations

from typing import Any

from .base import MiniMaxBaseClient


class MiniMaxOpenAIClient(MiniMaxBaseClient):
    """OpenAI 兼容协议客户端。

    base_url = https://api.minimaxi.com/v1
    """

    base_url = "https://api.minimaxi.com/v1"

    # ── 模型 ─────────────────────────────────────────────────────────────────

    def list_models(self) -> dict[str, Any]:
        """GET /v1/models — 返回 OpenAI 兼容格式 {data: [...]}。"""
        return self.request_json("GET", "/models")

    def retrieve_model(self, model_id: str) -> dict[str, Any]:
        """GET /v1/models/{model_id}。"""
        return self.request_json("GET", f"/models/{model_id}")

    # ── Chat ─────────────────────────────────────────────────────────────────

    def chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /v1/chat/completions。"""
        return self.request_json("POST", "/chat/completions", json=payload)

    # ── Responses ─────────────────────────────────────────────────────────────

    def responses_create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /v1/responses。"""
        return self.request_json("POST", "/responses", json=payload)

    def responses_input_tokens(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /v1/responses/input_tokens。"""
        return self.request_json("POST", "/responses/input_tokens", json=payload)
