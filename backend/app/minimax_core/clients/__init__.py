"""
minimax_core.clients — MiniMax API 客户端集合。

对外暴露：
    MiniMaxBaseClient
    MiniMaxOpenAIClient
    MiniMaxAnthropicClient
    MiniMaxNativeClient
    MiniMaxFilesClient
"""
from __future__ import annotations

from .base import MiniMaxBaseClient
from .openai import MiniMaxOpenAIClient
from .anthropic import MiniMaxAnthropicClient
from .native import MiniMaxNativeClient
from .files import MiniMaxFilesClient

__all__ = [
    "MiniMaxBaseClient",
    "MiniMaxOpenAIClient",
    "MiniMaxAnthropicClient",
    "MiniMaxNativeClient",
    "MiniMaxFilesClient",
]
