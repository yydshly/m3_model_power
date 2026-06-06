# MiniMax 能力验收报告

> 生成时间：2026-06-06T17:59:48.558355+00:00

## 验收摘要

| 状态 | 数量 |
|---|---|
| success | 10 |

## 详细结果

| 能力 ID | 状态 | HTTP | 延迟(ms) | 模型 | 错误 |
|---|---|---|---|---|---|
| chat-anthropic | success | 200 | 1297 | MiniMax-M3 | - |
| chat-openai | success | 200 | 2108 | MiniMax-M3 | - |
| chat-responses-create | success | 200 | 2436 | MiniMax-M3 | - |
| chat-responses-tokens | success | 200 | 296 | MiniMax-M3 | - |
| file-list | success | 200 | 281 | None | - |
| models-anthropic-list | success | 200 | 296 | None | - |
| models-anthropic-retrieve | success | 200 | 250 | MiniMax-M3 | - |
| models-openai-list | success | 200 | 860 | None | - |
| models-openai-retrieve | success | 200 | 250 | MiniMax-M3 | - |
| voice-list | success | 200 | 390 | None | - |

---
*此报告由 `backend/scripts/verify_minimax_capabilities.py` 自动生成*