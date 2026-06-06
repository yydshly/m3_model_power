"""Files 客户端。

覆盖端点：
  /v1/files/list        — 文件列表
  /v1/files/retrieve    — 文件详情
  /v1/files/retrieve_content — 文件内容（返回原始 bytes）
  /v1/files/delete     — 文件删除
  /v1/files/upload     — 文件上传（multipart）

本轮先实现 list_files，upload/retrieve_content 等后续扩展。
"""
from __future__ import annotations

from typing import Any

import httpx

from .base import MiniMaxBaseClient


class MiniMaxFilesClient(MiniMaxBaseClient):
    """Files API 客户端。

    base_url = https://api.minimaxi.com/v1
    """

    base_url = "https://api.minimaxi.com/v1"

    def list_files(self) -> dict[str, Any]:
        """GET /v1/files/list — 列出账户下文件。"""
        return self.request_json("GET", "/files/list")

    def retrieve_file(self, file_id: str) -> dict[str, Any]:
        """GET /v1/files/retrieve?file_id=... — 查询文件元数据。"""
        return self.request_json("GET", "/files/retrieve", params={"file_id": file_id})

    def delete_file(self, file_id: str) -> dict[str, Any]:
        """POST /v1/files/delete — 删除文件。"""
        return self.request_json("POST", "/files/delete", json={"file_id": file_id})

    def retrieve_content(self, file_id: str) -> tuple[bytes, str]:
        """GET /v1/files/retrieve_content?file_id=... — 返回 (bytes, content_type)。"""
        url = f"{self.base_url.rstrip('/')}/files/retrieve_content"
        params = self._with_group({"file_id": file_id})
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(url, headers=self.auth_header(), params=params)
                if resp.status_code >= 400:
                    self._raise_error(resp)
                ctype = resp.headers.get("content-type", "application/octet-stream")
                return resp.content, ctype
        except httpx.TimeoutException:
            from ..contracts import UnifiedError
            raise UnifiedError(
                capability_id="file-content",
                error_type="timeout",
                message="File content download timeout",
                http_status=None,
                retryable=True,
            )
