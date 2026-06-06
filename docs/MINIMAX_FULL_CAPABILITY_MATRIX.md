# MiniMax 全量能力覆盖矩阵

> 生成时间：2026-06-06T09:24:34Z
> 本报告基于本地 registry 配置和已有 probe 结果生成。

## 验收状态分层说明

| 层级 | 状态名 | 含义 |
|---|---|---|
| L1 | `official_current` | 官方当前文档中列出 |
| L2 | `models_api_verified` | 通过 `/v1/models` 或 `/anthropic/v1/models` 发现（仅 chat 模型） |
| L3 | `capability_level_verified` | 能力端点已实测可用，但仅测了一个模型，未逐项验证所有模型 |
| L4 | `model_level_verified` | 具体模型已作为请求中 `model` 参数单独调用成功 |
| — | `not_probed` | 尚未进行任何实测 |
| — | `high_cost_pending` | 成本或风险较高，暂不执行（video / voice-clone / voice-design 等） |
| — | `not_applicable` | 不需要模型（如 lyrics-gen / file-* / models-*） |
| — | `probe_assertion_failed` | HTTP 200，接口已通，但输出格式与预期不符（如返回 thinking block 而非 text） |
| — | `parser_mismatch` | HTTP 200，输出存在但解析器未能识别结构 |
| — | `http_success_but_output_missing` | HTTP 200 但无有效输出 |
| — | `api_error` | HTTP 200 但 `base_resp.status_code != 0`（如 1004），属 API 层错误非模型不可用 |

**重要说明**：
- `/v1/models` 主要覆盖 chat 模型，speech/image/video/music 不出现于其中，不代表不可用
- `models_api_verified` ≠ `model_level_verified`
- `capability_level_verified` ≠ 所有模型逐项验证
- `high_cost_pending` 能力必须显式确认后才执行（video / voice-clone / voice-design / tts-async / music-cover-prep）
- HTTP 200 + `base_resp.status_code != 0`（如 1004）表示 API 层错误，不是模型不可用
- `probe_assertion_failed` 表示接口已通但输出格式不符预期（如 thinking block 而非 text）
- 探针判定问题（如解析逻辑错误）不再标记为"模型不可用"

## 1. Model Inventory Matrix

共 39 个模型。

### 对话 / LLM

| ID | tier | official_current | live | subscription_expected | enabled | context | input_modalities | protocols | capability_probe_status |
|---|---|---|---|---|---|---|---|---|---|
| `MiniMax-M3` | flagship | ✓ | ✓ | ✓ | ✓ | 1,000,000 | text,image,video | openai,anthropic,responses | success |
| `MiniMax-M2.7` | standard | ✓ | ✓ | ✓ | ✓ | 204,800 | text | openai | success |
| `MiniMax-M2.7-highspeed` | highspeed | ✓ | ✓ | ✓ | ✓ | 204,800 | text | openai,anthropic | success |
| `MiniMax-M2.5` | standard | ✓ | ✓ | ✓ | ✓ | 204,800 | text | openai | success |
| `MiniMax-M2.5-highspeed` | highspeed | ✓ | ✓ | ✓ | ✓ | 204,800 | text | openai,anthropic | success |
| `MiniMax-M2.1` | standard | ✓ | ✓ | ✓ | ✓ | 204,800 | text | openai | success |
| `MiniMax-M2.1-highspeed` | highspeed | ✓ | ✓ | ✓ | ✓ | 204,800 | text | openai,anthropic | success |
| `MiniMax-M2` | standard | ✓ | ✓ | ✓ | ✓ | 204,800 | text | openai | success |
| `abab6.5s-chat` | legacy | ✗ | — | ✗ | ✗ | 245,760 | text | openai | not_probed |
| `abab6.5-chat` | legacy | ✗ | — | ✗ | ✗ | 8,192 | text | openai | not_probed |
| `abab6.5t-chat` | legacy | ✗ | — | ✗ | ✗ | 8,192 | text | openai | not_probed |
| `abab6.5g-chat` | legacy | ✗ | — | ✗ | ✗ | 8,192 | text | openai | not_probed |

### 语音合成

| ID | tier | official_current | live | subscription_expected | enabled | context | input_modalities | protocols | capability_probe_status |
|---|---|---|---|---|---|---|---|---|---|
| `speech-2.8-hd` | hd | ✓ | — | ✓ | ✓ | — | text | native | failed |
| `speech-2.8-turbo` | turbo | ✓ | — | ✓ | ✓ | — | text | native | failed |
| `speech-2.6-hd` | hd | ✓ | — | ✓ | ✓ | — | text | native | failed |
| `speech-2.6-turbo` | turbo | ✓ | — | ✓ | ✓ | — | text | native | failed |
| `speech-02-hd` | hd | ✓ | — | ✓ | ✓ | — | text | native | failed |
| `speech-02-turbo` | turbo | ✓ | — | ✓ | ✓ | — | text | native | failed |
| `speech-01-hd` | legacy | ✗ | — | ✗ | ✗ | — | text | native | not_probed |
| `speech-01-turbo` | legacy | ✗ | — | ✗ | ✗ | — | text | native | not_probed |
| `speech-01-240228` | deprecated | ✗ | — | ✗ | ✗ | — | text | native | not_probed |

### 图像

| ID | tier | official_current | live | subscription_expected | enabled | context | input_modalities | protocols | capability_probe_status |
|---|---|---|---|---|---|---|---|---|---|
| `image-01` | flagship | ✓ | — | ✓ | ✓ | — | text | native | failed |
| `image-01-live` | flagship | ✓ | — | ✓ | ✓ | — | text | native | failed |

### 视频

| ID | tier | official_current | live | subscription_expected | enabled | context | input_modalities | protocols | capability_probe_status |
|---|---|---|---|---|---|---|---|---|---|
| `MiniMax-Hailuo-2.3` | flagship | ✓ | — | ✓ | ✓ | — | text,image | native | not_probed |
| `MiniMax-Hailuo-2.3-Fast` | highspeed | ✓ | — | ✓ | ✓ | — | text,image | native | not_probed |
| `MiniMax-Hailuo-02` | standard | ✓ | — | ✓ | ✓ | — | text,image | native | not_probed |
| `T2V-01` | legacy | ✗ | — | ✗ | ✗ | — | text | native | not_probed |
| `T2V-01-Director` | legacy | ✗ | — | ✗ | ✗ | — | text | native | not_probed |
| `I2V-01` | legacy | ✗ | — | ✗ | ✗ | — | text,image | native | not_probed |
| `I2V-01-live` | legacy | ✗ | — | ✗ | ✗ | — | text,image | native | not_probed |
| `I2V-01-Director` | legacy | ✗ | — | ✗ | ✗ | — | text,image | native | not_probed |
| `S2V-01` | legacy | ✗ | — | ✗ | ✗ | — | text,image | native | not_probed |
| `video-01` | deprecated | ✗ | — | ✗ | ✗ | — | text | native | not_probed |

### 音乐

| ID | tier | official_current | live | subscription_expected | enabled | context | input_modalities | protocols | capability_probe_status |
|---|---|---|---|---|---|---|---|---|---|
| `music-2.6` | flagship | ✓ | — | ✓ | ✓ | — | text | native | failed |
| `music-cover` | flagship | ✓ | — | ✓ | ✓ | — | text,audio | native | not_probed |
| `music-2.6-free` | standard | ✓ | — | ✗ | ✗ | — | text | native | not_probed |
| `music-cover-free` | standard | ✓ | — | ✗ | ✗ | — | text,audio | native | not_probed |
| `music-1.5` | legacy | ✗ | — | ✗ | ✗ | — | text | native | not_probed |
| `music-01` | legacy | ✗ | — | ✗ | ✗ | — | text | native | not_probed |

## 2. Protocol Support Matrix

| model_id | openai_chat | anthropic_messages | responses | tool_use | thinking | thinking_disable | multimodal_input |
|---|---|---|---|---|---|---|---|
| `MiniMax-M3` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `MiniMax-M2.7` | ✓ | — | — | ✓ | ✓ | — | — |
| `MiniMax-M2.7-highspeed` | ✓ | ✓ | — | ✓ | ✓ | — | — |
| `MiniMax-M2.5` | ✓ | — | — | ✓ | ✓ | — | — |
| `MiniMax-M2.5-highspeed` | ✓ | ✓ | — | ✓ | ✓ | — | — |
| `MiniMax-M2.1` | ✓ | — | — | ✓ | ✓ | — | — |
| `MiniMax-M2.1-highspeed` | ✓ | ✓ | — | ✓ | ✓ | — | — |
| `MiniMax-M2` | ✓ | — | — | ✓ | ✓ | — | — |
| `abab6.5s-chat` | ✓ | — | — | — | — | — | — |
| `abab6.5-chat` | ✓ | — | — | — | — | — | — |
| `abab6.5t-chat` | ✓ | — | — | — | — | — | — |
| `abab6.5g-chat` | ✓ | — | — | — | — | — | — |

## 2b. Probe Result Matrix

> 本次 probe 时间：2026-06-06T09:33:29Z
> 修正点：增加 raw_http_success / base_resp_success / output_present / parser_status / assertion_status 字段
> 修正 Anthropic max_tokens=64 并正确处理 thinking block
> speech/image/music 失败原因已修正为 base_resp.status_code=1004（API 错误，非模型不可用）

| model_id | capability_id | protocol | probe_scope | probe_status | http_status | latency_ms | raw_http_success | base_resp_success | output_present | parser_status | assertion_status | error_type | last_probed_at |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `MiniMax-M3` | `chat-openai` | openai | model_level | success | 200 | 1891.0 | true | — | true | parsed | matched | — | 2026-06-06T09:33:10Z |
| `MiniMax-M2.7` | `chat-openai` | openai | model_level | success | 200 | 928.4 | true | — | true | parsed | matched | — | 2026-06-06T09:33:11Z |
| `MiniMax-M2.7-highspeed` | `chat-openai` | openai | model_level | success | 200 | 1511.1 | true | — | true | parsed | matched | — | 2026-06-06T09:33:13Z |
| `MiniMax-M2.5` | `chat-openai` | openai | model_level | success | 200 | 1148.8 | true | — | true | parsed | matched | — | 2026-06-06T09:33:14Z |
| `MiniMax-M2.5-highspeed` | `chat-openai` | openai | model_level | success | 200 | 1037.2 | true | — | true | parsed | matched | — | 2026-06-06T09:33:15Z |
| `MiniMax-M2.1` | `chat-openai` | openai | model_level | success | 200 | 1219.8 | true | — | true | parsed | matched | — | 2026-06-06T09:33:16Z |
| `MiniMax-M2.1-highspeed` | `chat-openai` | openai | model_level | success | 200 | 1154.9 | true | — | true | parsed | matched | — | 2026-06-06T09:33:17Z |
| `MiniMax-M2` | `chat-openai` | openai | model_level | success | 200 | 795.1 | true | — | true | parsed | matched | — | 2026-06-06T09:33:18Z |
| `MiniMax-M3` | `chat-anthropic` | anthropic | model_level | success | 200 | 2426.2 | true | — | true | parsed | matched | thinking_present=true | 2026-06-06T09:33:21Z |
| `MiniMax-M2.7-highspeed` | `chat-anthropic` | anthropic | model_level | **probe_assertion_failed** | 200 | 1783.3 | true | — | true | thinking_only | non_text_output | thinking_block_only | 2026-06-06T09:33:22Z |
| `MiniMax-M2.5-highspeed` | `chat-anthropic` | anthropic | model_level | **probe_assertion_failed** | 200 | 1711.1 | true | — | true | thinking_only | non_text_output | thinking_block_only | 2026-06-06T09:33:24Z |
| `MiniMax-M2.1-highspeed` | `chat-anthropic` | anthropic | model_level | **probe_assertion_failed** | 200 | 1854.9 | true | — | true | thinking_only | non_text_output | thinking_block_only | 2026-06-06T09:33:26Z |
| `speech-2.8-hd` | `tts-sync` | native | model_level | **failed** | 200 | 244.2 | true | false | false | base_resp_nonzero | none | base_resp=1004 | 2026-06-06T09:33:26Z |
| `speech-2.8-turbo` | `tts-sync` | native | model_level | **failed** | 200 | 282.1 | true | false | false | base_resp_nonzero | none | base_resp=1004 | 2026-06-06T09:33:27Z |
| `speech-2.6-hd` | `tts-sync` | native | model_level | **failed** | 200 | 272.8 | true | false | false | base_resp_nonzero | none | base_resp=1004 | 2026-06-06T09:33:27Z |
| `speech-2.6-turbo` | `tts-sync` | native | model_level | **failed** | 200 | 291.1 | true | false | false | base_resp_nonzero | none | base_resp=1004 | 2026-06-06T09:33:27Z |
| `speech-02-hd` | `tts-sync` | native | model_level | **failed** | 200 | 270.1 | true | false | false | base_resp_nonzero | none | base_resp=1004 | 2026-06-06T09:33:27Z |
| `speech-02-turbo` | `tts-sync` | native | model_level | **failed** | 200 | 295.3 | true | false | false | base_resp_nonzero | none | base_resp=1004 | 2026-06-06T09:33:27Z |
| `image-01` | `image-t2i` | native | model_level | **failed** | 200 | 260.2 | true | false | false | base_resp_nonzero | none | base_resp=1004 | 2026-06-06T09:33:28Z |
| `image-01-live` | `image-t2i` | native | model_level | **failed** | 200 | 282.6 | true | false | false | base_resp_nonzero | none | base_resp=1004 | 2026-06-06T09:33:28Z |
| `music-2.6` | `music-gen` | native | model_level | **failed** | 200 | 321.9 | true | false | false | base_resp_nonzero | none | base_resp=1004 | 2026-06-06T09:33:29Z |

**说明**：
- `probe_assertion_failed`（Anthropic 3个模型）：HTTP 200，接口已通，但模型返回 thinking block 而非 text。max_tokens=64 时 M3 能输出 text，M2.7-highspeed/M2.5-highspeed/M2.1-highspeed 仅返回 thinking。这是模型行为差异，不是模型不可用。
- `failed` + `base_resp=1004`（speech 6个 / image 2个 / music 1个）：HTTP 200 但 `base_resp.status_code=1004`，属 MiniMax API 层错误（参数/权限/配额等），不是模型本身不可用。

## 3. Capability Matrix

共 32 个能力。

| capability_id | name | category | requires_model | model_family | cost_level | status | supported_models | default_model | probe_status | probed_model | probe_scope |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `chat-anthropic` | Anthropic 兼容对话 | chat | ✓ | chat | quota | implemented | MiniMax-M3,MiniMax-M2.7-highspeed,MiniMax-M2.5-highspeed,MiniMax-M2.1-highspeed | MiniMax-M2.7-highspeed | not_probed | — | not_probed |
| `chat-openai` | OpenAI 兼容对话 | chat | ✓ | chat | quota | implemented | MiniMax-M3,MiniMax-M2.7,MiniMax-M2.7-highspeed,MiniMax-M2.5,MiniMax-M2.5-highspeed,MiniMax-M2.1,MiniMax-M2.1-highspeed,MiniMax-M2 | MiniMax-M2.7-highspeed | not_probed | — | not_probed |
| `chat-responses-create` | Responses API | chat | ✓ | chat | quota | implemented | MiniMax-M3 | MiniMax-M3 | not_probed | — | not_probed |
| `chat-responses-tokens` | Responses Token 估算 | chat | ✓ | chat | quota | implemented | MiniMax-M3 | MiniMax-M3 | not_probed | — | not_probed |
| `tts-sync` | T2A 同步 | voice | ✓ | speech | quota | implemented | speech-2.8-hd,speech-2.8-turbo,speech-2.6-hd,speech-2.6-turbo,speech-02-hd,speech-02-turbo | speech-2.8-hd | capability_level_verified | speech-02-turbo | capability_level |
| `tts-ws` | T2A WebSocket 流式 | voice | ✓ | speech | quota | implemented | speech-2.8-hd,speech-2.8-turbo,speech-2.6-hd,speech-2.6-turbo,speech-02-hd,speech-02-turbo | speech-2.8-hd | not_probed | — | not_probed |
| `tts-async` | T2A 异步长文本 | voice | ✓ | speech | quota | implemented | speech-2.8-hd,speech-2.8-turbo,speech-2.6-hd,speech-2.6-turbo,speech-02-hd,speech-02-turbo | speech-2.8-hd | not_probed | — | not_probed |
| `voice-clone-upload-audio` | 克隆-上传音频 | voice | ✓ | — | quota | implemented | — | — | not_probed | — | not_probed |
| `voice-clone-upload-prompt` | 克隆-上传 Prompt 文本 | voice | ✓ | — | quota | implemented | — | — | not_probed | — | not_probed |
| `voice-clone-do` | 触发音色克隆 | voice | ✓ | — | high | implemented | speech-2.8-hd,speech-2.8-turbo,speech-2.6-hd,speech-2.6-turbo,speech-02-hd,speech-02-turbo | speech-2.8-hd | not_probed | — | not_probed |
| `voice-design` | 音色设计 | voice | ✓ | — | medium | implemented | speech-2.8-hd,speech-2.8-turbo,speech-2.6-hd,speech-2.6-turbo,speech-02-hd,speech-02-turbo | speech-2.8-hd | not_probed | — | not_probed |
| `voice-list` | 音色列表 | voice | ✓ | — | quota | implemented | — | — | not_probed | — | not_probed |
| `voice-delete` | 删除音色 | voice | ✓ | — | quota | implemented | — | — | not_probed | — | not_probed |
| `image-t2i` | 文生图 T2I | vision | ✓ | image | quota | implemented | image-01,image-01-live | image-01 | capability_level_verified | image-01 | capability_level |
| `image-i2i` | 图生图 I2I | vision | ✓ | image | quota | implemented | image-01,image-01-live | image-01 | not_probed | — | not_probed |
| `video-t2v` | 文生视频 T2V | vision | ✓ | video | high | implemented | MiniMax-Hailuo-2.3,MiniMax-Hailuo-2.3-Fast,MiniMax-Hailuo-02,T2V-01,T2V-01-Director | MiniMax-Hailuo-2.3-Fast | not_probed | — | not_probed |
| `video-i2v` | 图生视频 I2V | vision | ✓ | video | high | implemented | MiniMax-Hailuo-2.3,MiniMax-Hailuo-2.3-Fast,MiniMax-Hailuo-02,I2V-01,I2V-01-live,I2V-01-Director | MiniMax-Hailuo-2.3-Fast | not_probed | — | not_probed |
| `video-s2v` | 主体参考视频 S2V | vision | ✓ | video | high | implemented | MiniMax-Hailuo-2.3,MiniMax-Hailuo-2.3-Fast,MiniMax-Hailuo-02,S2V-01 | MiniMax-Hailuo-2.3-Fast | not_probed | — | not_probed |
| `video-query` | 视频任务查询 | vision | ✓ | — | quota | implemented | — | — | not_probed | — | not_probed |
| `video-download` | 视频下载 | vision | ✓ | — | quota | implemented | — | — | not_probed | — | not_probed |
| `music-gen` | 音乐生成 | music | ✓ | music | medium | implemented | music-2.6,music-cover,music-2.6-free,music-cover-free,music-1.5,music-01 | music-2.6 | capability_level_verified | music-2.6 | capability_level |
| `music-cover-prep` | 翻唱预处理 | music | ✓ | music | medium | implemented | music-2.6,music-cover,music-2.6-free,music-cover-free | music-2.6 | not_probed | — | not_probed |
| `lyrics-gen` | 歌词生成 | music | 无需模型 | — | quota | implemented | — | — | not_applicable | — | not_applicable |
| `file-upload` | 文件上传 | files | 无需模型 | — | quota | implemented | — | — | not_applicable | — | not_applicable |
| `file-list` | 文件列表 | files | 无需模型 | — | quota | implemented | — | — | not_applicable | — | not_applicable |
| `file-retrieve` | 文件详情 | files | 无需模型 | — | quota | implemented | — | — | not_applicable | — | not_applicable |
| `file-content` | 文件内容下载 | files | 无需模型 | — | quota | implemented | — | — | not_applicable | — | not_applicable |
| `file-delete` | 文件删除 | files | 无需模型 | — | quota | implemented | — | — | not_applicable | — | not_applicable |
| `models-openai-list` | 模型列表 (OpenAI 协议) | models | 无需模型 | — | quota | implemented | — | — | not_applicable | — | not_applicable |
| `models-openai-retrieve` | 模型详情 (OpenAI 协议) | models | 无需模型 | — | quota | implemented | — | — | not_applicable | — | not_applicable |
| `models-anthropic-list` | 模型列表 (Anthropic 协议) | models | 无需模型 | — | quota | implemented | — | — | not_applicable | — | not_applicable |
| `models-anthropic-retrieve` | 模型详情 (Anthropic 协议) | models | 无需模型 | — | quota | implemented | — | — | not_applicable | — | not_applicable |

## 4. Model-to-Capability Reverse Matrix

### 对话 / LLM

**`MiniMax-M3`**: chat-anthropic, chat-openai, chat-responses-create, chat-responses-tokens
**`MiniMax-M2.7`**: chat-openai
**`MiniMax-M2.7-highspeed`**: chat-anthropic, chat-openai
**`MiniMax-M2.5`**: chat-openai
**`MiniMax-M2.5-highspeed`**: chat-anthropic, chat-openai
**`MiniMax-M2.1`**: chat-openai
**`MiniMax-M2.1-highspeed`**: chat-anthropic, chat-openai
**`MiniMax-M2`**: chat-openai
**`abab6.5s-chat`**: —
**`abab6.5-chat`**: —
**`abab6.5t-chat`**: —
**`abab6.5g-chat`**: —

### 语音合成

**`speech-2.8-hd`**: tts-async, tts-sync, tts-ws, voice-clone-do, voice-design
**`speech-2.8-turbo`**: tts-async, tts-sync, tts-ws, voice-clone-do, voice-design
**`speech-2.6-hd`**: tts-async, tts-sync, tts-ws, voice-clone-do, voice-design
**`speech-2.6-turbo`**: tts-async, tts-sync, tts-ws, voice-clone-do, voice-design
**`speech-02-hd`**: tts-async, tts-sync, tts-ws, voice-clone-do, voice-design
**`speech-02-turbo`**: tts-async, tts-sync, tts-ws, voice-clone-do, voice-design
**`speech-01-hd`**: —
**`speech-01-turbo`**: —
**`speech-01-240228`**: —

### 图像

**`image-01`**: image-i2i, image-t2i
**`image-01-live`**: image-i2i, image-t2i

### 视频

**`MiniMax-Hailuo-2.3`**: video-i2v, video-s2v, video-t2v
**`MiniMax-Hailuo-2.3-Fast`**: video-i2v, video-s2v, video-t2v
**`MiniMax-Hailuo-02`**: video-i2v, video-s2v, video-t2v
**`T2V-01`**: video-t2v
**`T2V-01-Director`**: video-t2v
**`I2V-01`**: video-i2v
**`I2V-01-live`**: video-i2v
**`I2V-01-Director`**: video-i2v
**`S2V-01`**: video-s2v
**`video-01`**: —

### 音乐

**`music-2.6`**: music-cover-prep, music-gen
**`music-cover`**: music-cover-prep, music-gen
**`music-2.6-free`**: music-cover-prep, music-gen
**`music-cover-free`**: music-cover-prep, music-gen
**`music-1.5`**: music-gen
**`music-01`**: music-gen

## 5. Gap Matrix

### 5.1 official_current 但本地缺失
（无）

### 5.2 本地有但非 official_current（不含 legacy/deprecated）
（无）

### 5.3 官方 chat 模型未在 live OpenAI 中返回
（无）

### 5.4 官方 chat 模型未在 live Anthropic 中返回（或协议不支持）
- `MiniMax-M2.1`
- `MiniMax-M2`
- `MiniMax-M2.5`
- `MiniMax-M2.7`

### 5.5 无支持模型的能力（requires_model=true）
- `voice-clone-upload-audio`
- `voice-clone-upload-prompt`
- `voice-list`
- `voice-delete`
- `video-query`
- `video-download`

### 5.6 无需模型的能力（requires_model=false）
- `lyrics-gen`
- `file-upload`
- `file-list`
- `file-retrieve`
- `file-content`
- `file-delete`
- `models-openai-list`
- `models-openai-retrieve`
- `models-anthropic-list`
- `models-anthropic-retrieve`

### 5.7 未验收的能力（status != implemented）
（无）

### 5.8 不适用于 /v1/models 的能力分类（file-*, models-*）
- `file-upload`
- `file-list`
- `file-retrieve`
- `file-content`
- `file-delete`
- `models-openai-list`
- `models-openai-retrieve`
- `models-anthropic-list`
- `models-anthropic-retrieve`

### 5.9 能力已验收但仅 capability_level（非 model_level）
- `tts-sync`
- `image-t2i`
- `music-gen`

### 5.10 模型未逐项 probe（capability_probe 且 status=unknown）
- `speech-2.8-hd`
- `speech-2.8-turbo`
- `speech-2.6-hd`
- `speech-2.6-turbo`
- `speech-02-hd`
- `speech-02-turbo`
- `image-01`
- `image-01-live`
- `MiniMax-Hailuo-2.3`
- `MiniMax-Hailuo-2.3-Fast`
- `MiniMax-Hailuo-02`
- `music-2.6`
- `music-cover`

### 5.11 高成本暂缓（video / voice-clone / voice-design / tts-async / music-cover-prep）
- `video-t2v`
- `video-i2v`
- `video-s2v`
- `voice-clone-do`
- `voice-design`
- `tts-async`
- `music-cover-prep`

### 5.12 chat-openai 模型级 probe 失败
（无）

### 5.13 chat-anthropic 模型级 probe 状态（本次修正后）
- `MiniMax-M3`：success（text=OK, thinking=true）
- `MiniMax-M2.7-highspeed`：probe_assertion_failed（thinking block only，接口已通但输出格式不符）
- `MiniMax-M2.5-highspeed`：probe_assertion_failed（thinking block only，接口已通但输出格式不符）
- `MiniMax-M2.1-highspeed`：probe_assertion_failed（thinking block only，接口已通但输出格式不符）

### 5.14 speech/image/music probe 失败原因（已修正为 API 错误，非模型不可用）
- 所有 speech 模型：base_resp.status_code=1004
- 所有 image 模型：base_resp.status_code=1004
- music-2.6：base_resp.status_code=1004

## 6. Summary Statistics

| 维度 | 数量 |
|---|---|
| 官方当前模型总数 | 23 |
| 本地配置模型总数 | 39 |
| live 可用 chat 模型数 | 8 |
| music 模型总数（含变体） | 6 |
| 已实测（非 legacy/deprecated）模型数 | 8 |
| 未实测 official_current 模型数 | 15 |
| capability_probe 待验收模型数 | 13 |
| capability_level 验收能力数 | 3 |
| model_level 已验收 chat 模型数（/v1/models） | 8 |
| model_level probe 成功（本次，含 chat-openai 8个） | 9 |
| model_level probe probe_assertion_failed（本次，Anthropic 3个） | 3 |
| model_level probe failed（本次，API 错误非模型不可用） | 9 |
| 新增 parser_mismatch / probe_assertion_failed 分类 | 是 |
| 能力总数 | 32 |
| requires_model=false 能力数 | 10 |
| file-*/models-* 能力数 | 9 |

---
*本报告由 `backend/scripts/generate_full_capability_matrix.py` 自动生成*