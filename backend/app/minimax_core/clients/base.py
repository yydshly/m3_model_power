"""Base client — 所有 MiniMax 客户端的公共父类。

职责：
  - 统一 base_url / token 读取
  - 统一 header 构造
  - 统一 timeout / requests 调用
  - 统一错误包装（UnifiedError）
  - 统一敏感信息脱敏
"""
from __future__ import annotations

import os
import httpx
from typing import Any

from ..contracts import UnifiedError
from ..guards import redact_key


class MiniMaxBaseClient:
    """所有 MiniMax 客户端的基类。

    子类只需设置 base_url 和实现具体端点方法，
    公共逻辑（auth / request / error normalisation）统一在基类。
    """

    base_url: str = "https://api.minimaxi.com"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 60.0,
        group_id: str | None = None,
    ) -> None:
        self._api_key = api_key          # None = 从环境变量读取
        self._timeout = timeout
        self._group_id = group_id        # None = 从环境变量读取

    # ── Key 读取 ───────────────────────────────────────────────────────────────

    def get_api_key(self) -> str:
        """优先 MINIMAX_TOKEN_PLAN_KEY，其次 MINIMAX_API_KEY。"""
        if self._api_key:
            return self._api_key
        key = os.environ.get("MINIMAX_TOKEN_PLAN_KEY") or os.environ.get("MINIMAX_API_KEY", "")
        if not key:
            raise UnifiedError(
                capability_id="",
                error_type="unauthorized",
                message="MINIMAX_TOKEN_PLAN_KEY / MINIMAX_API_KEY 均未配置，请检查 backend/.env",
                http_status=500,
                retryable=False,
            )
        return key

    def get_group_id(self) -> str | None:
        """优先构造函数传入值，其次环境变量。"""
        if self._group_id is not None:
            return self._group_id
        return os.environ.get("MINIMAX_GROUP_ID") or None

    # ── Auth header ─────────────────────────────────────────────────────────────

    def auth_header(self) -> dict[str, str]:
        """返回 Authorization: Bearer <token> 字典。"""
        return {"Authorization": f"Bearer {self.get_api_key()}"}

    def anthropic_header(self) -> dict[str, str]:
        """返回 Anthropic 兼容 header。"""
        return {
            "x-api-key": self.get_api_key(),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    # ── 公共请求 ────────────────────────────────────────────────────────────────

    def _with_group(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """将 group_id 注入 query params（若缺失且已配置）。"""
        p = dict(params or {})
        gid = self.get_group_id()
        if gid and "GroupId" not in p:
            p["GroupId"] = gid
        return p

    def request_json(
        self,
        method: str,
        path: str,
        *,
        headers: dict | None = None,
        json: dict | None = None,
        params: dict | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """统一 GET/POST JSON 请求，返回解析后的响应字典。

        错误统一包装为 UnifiedError，不会抛出原始 httpx 异常。
        """
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        timeout = timeout if timeout is not None else self._timeout

        extra: dict[str, str] = dict(headers) if headers else {}
        # 合并 auth header（Bearer token）
        extra.update(self.auth_header())
        if json is not None:
            extra["Content-Type"] = "application/json"

        try:
            with httpx.Client(timeout=timeout) as client:
                if method.upper() == "GET":
                    resp = client.get(url, headers=extra, params=self._with_group(params))
                elif method.upper() == "POST":
                    resp = client.post(
                        url,
                        headers=extra,
                        params=self._with_group(params),
                        json=json,
                    )
                else:
                    raise UnifiedError(
                        capability_id="",
                        error_type="invalid_params",
                        message=f"Unsupported HTTP method: {method}",
                        http_status=400,
                        retryable=False,
                    )

                if resp.status_code >= 400:
                    self._raise_error(resp)

                return resp.json()

        except UnifiedError:
            raise
        except httpx.TimeoutException:
            raise UnifiedError(
                capability_id="",
                error_type="timeout",
                message=f"Request timeout after {timeout}s",
                http_status=None,
                retryable=True,
            )
        except httpx.ConnectError as exc:
            raise UnifiedError(
                capability_id="",
                error_type="network_error",
                message=f"Connection error: {exc}",
                http_status=None,
                retryable=True,
            )
        except Exception as exc:
            raise UnifiedError(
                capability_id="",
                error_type="upstream_error",
                message=f"Unexpected error: {exc}",
                http_status=None,
                retryable=False,
            )

    def _raise_error(self, resp: httpx.Response) -> None:
        """根据响应状态码构造 UnifiedError 并抛出。"""
        try:
            data = resp.json()
            msg = (
                data.get("base_resp", {}).get("status_msg")
                or data.get("message")
                or resp.text
            )
            error_type = "upstream_error"
            if resp.status_code == 401 or resp.status_code == 403:
                error_type = "unauthorized"
            elif resp.status_code == 429:
                error_type = "rate_limited"
        except Exception:
            msg = resp.text or resp.reason_phrase
            error_type = "upstream_error"

        raise UnifiedError(
            capability_id="",
            error_type=error_type,
            error_code=str(resp.status_code),
            message=f"[HTTP {resp.status_code}] {msg}",
            http_status=resp.status_code,
            retryable=resp.status_code >= 500 or resp.status_code == 429,
        )
