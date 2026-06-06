# MiniMax 能力验收报告

> 生成时间：2026-06-06T06:57:54.360032+00:00

## 验收摘要

| 状态 | 数量 |
|---|---|
| success | 8 |
| success_with_warning | 2 |

## 详细结果

| 能力 ID | 状态 | HTTP | 延迟(ms) | 模型 | 错误 |
|---|---|---|---|---|---|
| chat-anthropic | success | 200 | 3719 | MiniMax-M3 | - |
| chat-openai | success | 200 | 1375 | MiniMax-M3 | - |
| chat-responses-create | success | 200 | 2672 | MiniMax-M3 | - |
| chat-responses-tokens | success | 200 | 265 | MiniMax-M3 | - |
| file-list | success | 200 | 265 | None | - |
| models-anthropic-list | success_with_warning | 200 | 265 | None | - |
| models-anthropic-retrieve | success_with_warning | 200 | 265 | None | - |
| models-openai-list | success | 200 | 530 | None | - |
| models-openai-retrieve | success | 200 | 265 | None | - |
| voice-list | success | 200 | 344 | None | - |

---
*此报告由 `backend/scripts/verify_minimax_capabilities.py` 自动生成*