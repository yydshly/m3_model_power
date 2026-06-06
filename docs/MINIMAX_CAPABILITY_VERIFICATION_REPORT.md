# MiniMax 能力验收报告

> 生成时间：2026-06-06T10:44:15.687157+00:00

## 验收摘要

| 状态 | 数量 |
|---|---|
| failed | 4 |

## 详细结果

| 能力 ID | 状态 | HTTP | 延迟(ms) | 模型 | 错误 |
|---|---|---|---|---|---|
| image-t2i | failed | 200 | 530 | None | login fail: Please carry the API secret key in the 'Authoriz |
| lyrics-gen | failed | 200 | 500 | None | login fail: Please carry the API secret key in the 'Authoriz |
| music-gen | failed | 200 | 469 | None | login fail: Please carry the API secret key in the 'Authoriz |
| tts-sync | failed | 200 | 562 | None | login fail: Please carry the API secret key in the 'Authoriz |

---
*此报告由 `backend/scripts/verify_minimax_capabilities.py` 自动生成*