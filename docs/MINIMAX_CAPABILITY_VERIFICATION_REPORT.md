# MiniMax 能力验收报告

> 生成时间：2026-06-06T10:13:58.470627+00:00

## 验收摘要

| 状态 | 数量 |
|---|---|
| failed | 4 |

## 详细结果

| 能力 ID | 状态 | HTTP | 延迟(ms) | 模型 | 错误 |
|---|---|---|---|---|---|
| image-t2i | failed | None | 295 | None | `UnifiedResponse` is not fully defined; you should define `L |
| lyrics-gen | failed | None | 282 | None | `UnifiedResponse` is not fully defined; you should define `L |
| music-gen | failed | None | 280 | None | `UnifiedResponse` is not fully defined; you should define `L |
| tts-sync | failed | None | 312 | None | `UnifiedResponse` is not fully defined; you should define `L |

---
*此报告由 `backend/scripts/verify_minimax_capabilities.py` 自动生成*