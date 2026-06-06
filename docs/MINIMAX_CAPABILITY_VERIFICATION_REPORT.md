# MiniMax 能力验收报告

> 生成时间: 2026-06-06 07:17 UTC
> Level: medium（仅4项，不含 safe 重复项）

## 验收摘要

| 状态 | 数量 |
|---|
| failed | 2 |
| success | 2 |

## 详细结果

| 能力 ID | Level | 状态 | HTTP | 延迟(ms) | 模型 | 输出类型 | 资产已存 | 错误 |
|---|---|---|---|---|---|---|---|---|
| image-t2i | medium | success | 200 | 16514 | image-01 | image | False | - |
| lyrics-gen | safe | failed | 400 | 344 | None | None | False | HTTP 400: {'base_resp': {'status_code': 2013, 'status_msg':  |
| music-gen | safe | failed | 0 | 60203 | None | None | False | timeout |
| tts-sync | medium | success | 200 | 641 | speech-02-turbo | audio | False | - |

## 失败分析

### lyrics-gen
- 错误: HTTP 400: {'base_resp': {'status_code': 2013, 'status_msg': 'invalid params'}}
- 分类: invalid_params — 请求参数格式不符合上游要求（status_code 2013），需要查阅最新文档修正参数

### music-gen
- 错误: timeout
- 分类: timeout — 上游响应超时，可能需要异步处理或增加超时时间

---
*此报告由  自动生成*