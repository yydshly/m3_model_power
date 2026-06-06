"""redaction — 日志/响应脱敏工具。

所有对外暴露的错误信息、日志和响应必须经过脱敏。
禁止直接打印或返回完整 API Key、Token、订单号等敏感字段。
"""
from __future__ import annotations


def redact_key(key: str | None, visible_chars: int = 4) -> str:
    """对 API Key / Token 等凭证脱敏。

    显示前 visible_chars 位和后 visible_chars 位，中间用 *** 替换。
    如果 key 为空或过短，返回 ***

    用法：
        redact_key("sk-abcdef123456")  # -> "sk-***3456"
    """
    if not key or len(key) <= visible_chars * 2:
        return "***"
    return f"{key[:visible_chars]}***{key[-visible_chars:]}"


def redact_url(url: str | None) -> str:
    """对 URL 中的 key 参数脱敏。

    常见 key 参数名：api_key / key / token / access_token / Authorization
    """
    if not url:
        return ""
    import re
    # 替换常见 key 参数值
    masked = re.sub(
        r'(api_key|key|token|access_token|Authorization)[^&#"]*',
        lambda m: f'{m.group(0).split("=")[0]}=***',
        url,
    )
    return masked
