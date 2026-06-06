"""Anthropic 兼容协议客户端。

覆盖端点：
  /anthropic/v1/models
  /anthropic/v1/models/{model}
  /anthropic/v1/messages
"""
from __future__ import annotations

from typing import Any

from .base import MiniMaxBaseClient


class MiniMaxAnthropicClient(MiniMaxBaseClient):
    """Anthropic 兼容协议客户端。

    base_url = https://api.minimaxi.com/anthropic/v1
    """

    base_url = "https://api.minimaxi.com/anthropic/v1"

    # ── 模型 ─────────────────────────────────────────────────────────────────

    def list_models(self) -> dict[str, Any]:
        """GET /anthropic/v1/models。

        MiniMax Anthropic 端点实际返回 OpenAI 兼容格式 {data: [...]}，
        因此响应结构与 OpenAI 客户端一致。
        """
        return self.request_json(
            "GET",
            "/models",
            headers={"anthropic-version": "2023-06-01"},
        )

    def retrieve_model(self, model_id: str) -> dict[str, Any]:
        """GET /anthropic/v1/models/{model_id}。"""
        return self.request_json(
            "GET",
            f"/models/{model_id}",
            headers={"anthropic-version": "2023-06-01"},
        )

    # ── Messages ─────────────────────────────────────────────────────────────

    def messages(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /anthropic/v1/messages。"""
        return self.request_json(
            "POST",
            "/messages",
            headers=self.anthropic_header(),
            json=payload,
        )
