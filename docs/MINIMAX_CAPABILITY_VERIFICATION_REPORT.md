# MiniMax 能力验收报告

> 生成时间：2026-06-06T14:37:02.326076+00:00

## 验收摘要

| 状态 | 数量 |
|---|---|
| success | 6 |

## 详细结果

| 能力 ID | 状态 | HTTP | 延迟(ms) | 模型 | 错误 |
|---|---|---|---|---|---|
| image-t2i | success | 200 | 15139 | image-01 | - |
| lyrics-gen | success | 200 | 3281 | None | - |
| music-gen | success | 200 | 38703 | music-2.6 | - |
| tts-async | success | 200 | 8171 | speech-02-turbo | - |
| tts-sync | success | 200 | 1203 | speech-02-turbo | - |
| tts-ws | success | 200 | 703 | speech-02-turbo | - |

---
*此报告由 `backend/scripts/verify_minimax_capabilities.py` 自动生成*