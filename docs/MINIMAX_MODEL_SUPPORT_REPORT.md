# MiniMax 模型支持报告

> 生成时间：2026-06-06T06:56:05.738074+00:00
> API Key：`sk-c***MnK8`
> Base URL：`https://api.minimaxi.com`

## 概览

| 维度 | 数量 |
|---|---|
| 官方当前模型（official_current） | 22 |
| 实际可用模型（live） | 8 |
| 本地配置模型（local） | 38 |
| 本地缺失（missing_in_local） | 0 |
| 本地历史/未知（deprecated/unknown） | 16 |

## 本地历史/未知模型（local 有但非 official_current 且不在 live 中）

- `I2V-01`
- `I2V-01-Director`
- `I2V-01-live`
- `S2V-01`
- `T2V-01`
- `T2V-01-Director`
- `abab6.5-chat`
- `abab6.5g-chat`
- `abab6.5s-chat`
- `abab6.5t-chat`
- `music-01`
- `music-1.5`
- `speech-01-240228`
- `speech-01-hd`
- `speech-01-turbo`
- `video-01`

## 本地当前模型未在 live 中返回

以下模型在 `models.yaml` 标记 `official_current: true`，但本次 live 查询未返回。可能是端点路由、权限或 API 版本差异：

- `MiniMax-Hailuo-02`
- `MiniMax-Hailuo-2.3`
- `MiniMax-Hailuo-2.3-Fast`
- `image-01`
- `image-01-live`
- `music-2.6`
- `music-2.6-free`
- `music-cover`
- `speech-02-hd`
- `speech-02-turbo`
- `speech-2.6-hd`
- `speech-2.6-turbo`
- `speech-2.8-hd`
- `speech-2.8-turbo`

## OpenAI 协议 live 模型

数量：8
- `MiniMax-M2`
- `MiniMax-M2.1`
- `MiniMax-M2.1-highspeed`
- `MiniMax-M2.5`
- `MiniMax-M2.5-highspeed`
- `MiniMax-M2.7`
- `MiniMax-M2.7-highspeed`
- `MiniMax-M3`

## Anthropic 协议 live 模型

数量：8
- `MiniMax-M2`
- `MiniMax-M2.1`
- `MiniMax-M2.1-highspeed`
- `MiniMax-M2.5`
- `MiniMax-M2.5-highspeed`
- `MiniMax-M2.7`
- `MiniMax-M2.7-highspeed`
- `MiniMax-M3`

## 官方当前模型（official_current: true）

- `MiniMax-Hailuo-02`
- `MiniMax-Hailuo-2.3`
- `MiniMax-Hailuo-2.3-Fast`
- `MiniMax-M2`
- `MiniMax-M2.1`
- `MiniMax-M2.1-highspeed`
- `MiniMax-M2.5`
- `MiniMax-M2.5-highspeed`
- `MiniMax-M2.7`
- `MiniMax-M2.7-highspeed`
- `MiniMax-M3`
- `image-01`
- `image-01-live`
- `music-2.6`
- `music-2.6-free`
- `music-cover`
- `speech-02-hd`
- `speech-02-turbo`
- `speech-2.6-hd`
- `speech-2.6-turbo`
- `speech-2.8-hd`
- `speech-2.8-turbo`

## 本地所有模型（包含历史）

- `I2V-01`
- `I2V-01-Director`
- `I2V-01-live`
- `MiniMax-Hailuo-02`
- `MiniMax-Hailuo-2.3`
- `MiniMax-Hailuo-2.3-Fast`
- `MiniMax-M2`
- `MiniMax-M2.1`
- `MiniMax-M2.1-highspeed`
- `MiniMax-M2.5`
- `MiniMax-M2.5-highspeed`
- `MiniMax-M2.7`
- `MiniMax-M2.7-highspeed`
- `MiniMax-M3`
- `S2V-01`
- `T2V-01`
- `T2V-01-Director`
- `abab6.5-chat`
- `abab6.5g-chat`
- `abab6.5s-chat`
- `abab6.5t-chat`
- `image-01`
- `image-01-live`
- `music-01`
- `music-1.5`
- `music-2.6`
- `music-2.6-free`
- `music-cover`
- `speech-01-240228`
- `speech-01-hd`
- `speech-01-turbo`
- `speech-02-hd`
- `speech-02-turbo`
- `speech-2.6-hd`
- `speech-2.6-turbo`
- `speech-2.8-hd`
- `speech-2.8-turbo`
- `video-01`

---
*此报告由 `backend/scripts/sync_minimax_models.py` 自动生成*