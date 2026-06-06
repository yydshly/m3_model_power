# MiniMax 全量能力覆盖矩阵

> 生成时间：2026-06-06T16:30:00Z
> 本报告基于本地 registry 配置和已有 probe 结果生成。
> 本轮更新：verify_minimax_capabilities.py 新增 file-upload multipart 上传支持、file-retrieve/file-content 验收、--file-id 参数、latest.json 合并写入（避免跨 run 覆盖）；file-upload/retrieve/content/file-list 4项全部 HTTP 200 验收成功；report_scope_gap.py 聚合源新增 Verification Report markdown；当前完成率 60%（12/20）；剩余 8 项待验收。

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

**重要说明**：
- `/v1/models` 主要覆盖 chat 模型，speech/image/video/music 不出现于其中，不代表不可用
- `models_api_verified` ≠ `model_level_verified`
- `capability_level_verified` ≠ 所有模型逐项验证
- `high_cost_pending` 能力必须显式确认后才执行（video / voice-clone / voice-design / tts-async / music-cover-prep）
- **scope_policy 已引入**：in_scope（20项）计入完成率，warning_only（7项）只做提示，out_of_scope（5项视频能力）不计入缺口

## 0. 项目范围与验收边界

> 本项目定位：MiniMax Token Plan 能力盘点与实测工作台。
> 当前项目范围：只关注 Token Plan 已确认的能力，不涵盖视频生成等 Token Plan 之外的付费能力。

### 范围分层定义

| scope | 含义 | 计入完成率 | 计入缺口矩阵 | 执行策略 |
|---|---|---|---|---|
| `in_scope` | Token Plan 核心验收范围 | ✅ 是 | ✅ 是 | 正常验收（safe/medium/high） |
| `warning_only` | 付费/认证/素材型能力，只做风险提示 | ❌ 否 | ❌ 否 | 只展示确认项，不执行验收 |
| `out_of_scope` | 不纳入当前验收范围 | ❌ 否 | ❌ 否 | 完全排除，不计入待办 |

### 验收记录聚合说明

`latest.json`（capability_verification/latest.json）只记录最近一次 verify 运行的 10 项 safe 结果，不等于全量已验收能力。完成率统计基于多来源聚合：

| 来源 | 内容 |
|---|---|
| `latest.json` | 最新运行结果（merge 模式保留历史，file-upload/retrieve/content/file-list 本轮新增） |
| `docs/MINIMAX_CAPABILITY_VERIFICATION_REPORT.md` | 历次验收 markdown 记录（chat-*/models-*/file-list/voice-list 前期成功） |
| `model_level_probe_report.json` | chat/tts-sync/image-t2i/music-gen model-level probe |
| `tts_ws_probe_report.json` | tts-ws WebSocket 流式 probe |
| `MINIMAX_FULL_CAPABILITY_MATRIX.md` | tts-async (full_async_flow) 和 lyrics-gen (medium) 的权威状态记录 |

**重要**：`latest.json` 每次运行 safe/medium/high 都会整体覆盖，但上述多来源聚合可保证历史成功记录不丢失。

### in_scope 能力（20项）

**已通过实际 Probe（12项）**：
- chat-anthropic（model_level via /v1/models，4模型成功）
- chat-openai（model_level via /v1/models，8模型成功）
- tts-sync（capability_level，6模型成功）
- tts-ws（WS流式成功，924ms）
- tts-async（full_async_flow，create→query→poll→download 全链路成功）
- image-t2i（model_level via model_probe，2模型成功）
- music-gen（capability_level via model_probe，音乐生成成功）
- lyrics-gen（capability_level，无需模型，文本生成成功）
- file-upload（multipart/purpose=retrieval，HTTP 200，本轮新增）
- file-list（HTTP 200，328ms）
- file-retrieve（file_id 查询，HTTP 200，本轮新增）
- file-content（file_id 内容读取，HTTP 200，本轮新增）

**待验收（8项）**：
- image-i2i（需参考图，requires_uploaded_asset）
- chat-responses-create（Responses API，前期 safe 运行 HTTP 200，但 latest.json 被覆盖后需补录）
- chat-responses-tokens（Responses Token 估算，前期 safe 运行 HTTP 200）
- voice-list（音色列表，前期 safe 运行 HTTP 200）
- models-openai-list（前期 safe 运行 HTTP 200）
- models-openai-retrieve（前期 safe 运行 HTTP 200）
- models-anthropic-list（前期 safe 运行 HTTP 200）
- models-anthropic-retrieve（前期 safe 运行 HTTP 200）

> 注：chat-responses-create/tokens、models-*、voice-list 在前几轮 safe 验收中已 HTTP 200 成功，但 latest.json 被后续运行覆盖，Verification Report 只记录最近一次 run。若需恢复这些记录，需要重新执行单个 --capability probe。

### warning_only 能力（7项）

不做验收，只在前端展示风险提示：
- `voice-clone-upload-audio`、`voice-clone-upload-prompt`：付费 + 素材
- `voice-clone-do`：付费 + 认证 + 素材
- `voice-design`：付费
- `file-delete`：破坏性操作
- `voice-delete`：破坏性操作
- `music-cover-prep`：素材型

### out_of_scope 能力（5项）

视频生成类，当前项目不涉及：
- `video-t2v`、`video-i2v`、`video-s2v`
- `video-query`、`video-download`

> 注：视频生成属于 Credits/视频资源包单独计费能力，不在 Token Plan 范围内，本项目不纳入验收。

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
| `speech-2.8-hd` | hd | ✓ | — | ✓ | ✓ | — | text | native | success |
| `speech-2.8-turbo` | turbo | ✓ | — | ✓ | ✓ | — | text | native | success |
| `speech-2.6-hd` | hd | ✓ | — | ✓ | ✓ | — | text | native | success |
| `speech-2.6-turbo` | turbo | ✓ | — | ✓ | ✓ | — | text | native | success |
| `speech-02-hd` | hd | ✓ | — | ✓ | ✓ | — | text | native | success |
| `speech-02-turbo` | turbo | ✓ | — | ✓ | ✓ | — | text | native | success |
| `speech-01-hd` | legacy | ✗ | — | ✗ | ✗ | — | text | native | not_probed |
| `speech-01-turbo` | legacy | ✗ | — | ✗ | ✗ | — | text | native | not_probed |
| `speech-01-240228` | deprecated | ✗ | — | ✗ | ✗ | — | text | native | not_probed |

### 图像

| ID | tier | official_current | live | subscription_expected | enabled | context | input_modalities | protocols | capability_probe_status |
|---|---|---|---|---|---|---|---|---|---|
| `image-01` | flagship | ✓ | — | ✓ | ✓ | — | text | native | success |
| `image-01-live` | flagship | ✓ | — | ✓ | ✓ | — | text | native | success |

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
| `music-2.6` | flagship | ✓ | — | ✓ | ✓ | — | text | native | success |
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

| model_id | capability_id | protocol | probe_scope | probe_status | http_status | latency_ms | output_present | error_type | last_probed_at |
|---|---|---|---|---|---|---|---|---|---|
| `MiniMax-M3` | `chat-openai` | openai | model_level | success | 200 | 1897.4 | True | — | 2026-06-06T11:27:14Z |
| `MiniMax-M2.7` | `chat-openai` | openai | model_level | success | 200 | 1163.7 | True | — | 2026-06-06T11:27:15Z |
| `MiniMax-M2.7-highspeed` | `chat-openai` | openai | model_level | success | 200 | 1340.1 | True | — | 2026-06-06T11:27:16Z |
| `MiniMax-M2.5` | `chat-openai` | openai | model_level | success | 200 | 1435.8 | True | — | 2026-06-06T11:27:18Z |
| `MiniMax-M2.5-highspeed` | `chat-openai` | openai | model_level | success | 200 | 1014.7 | True | — | 2026-06-06T11:27:19Z |
| `MiniMax-M2.1` | `chat-openai` | openai | model_level | success | 200 | 1510.2 | True | — | 2026-06-06T11:27:20Z |
| `MiniMax-M2.1-highspeed` | `chat-openai` | openai | model_level | success | 200 | 1179.7 | True | — | 2026-06-06T11:27:21Z |
| `MiniMax-M2` | `chat-openai` | openai | model_level | success | 200 | 1844.0 | True | — | 2026-06-06T11:27:23Z |
| `MiniMax-M3` | `chat-anthropic` | anthropic | model_level | success | 200 | 3595.2 | True | — | 2026-06-06T11:27:27Z |
| `MiniMax-M2.7-highspeed` | `chat-anthropic` | anthropic | model_level | success | 200 | 2270.7 | True | — | 2026-06-06T11:27:29Z |
| `MiniMax-M2.5-highspeed` | `chat-anthropic` | anthropic | model_level | success | 200 | 2596.0 | True | — | 2026-06-06T11:27:32Z |
| `MiniMax-M2.1-highspeed` | `chat-anthropic` | anthropic | model_level | success | 200 | 3628.8 | True | — | 2026-06-06T11:27:35Z |
| `speech-2.8-hd` | `tts-sync` | native | model_level | success | 200 | 920.4 | True | — | 2026-06-06T11:27:36Z |
| `speech-2.8-turbo` | `tts-sync` | native | model_level | success | 200 | 914.1 | True | — | 2026-06-06T11:27:37Z |
| `speech-2.6-hd` | `tts-sync` | native | model_level | success | 200 | 849.1 | True | — | 2026-06-06T11:27:38Z |
| `speech-2.6-turbo` | `tts-sync` | native | model_level | success | 200 | 864.4 | True | — | 2026-06-06T11:27:39Z |
| `speech-02-hd` | `tts-sync` | native | model_level | success | 200 | 862.2 | True | — | 2026-06-06T11:27:40Z |
| `speech-02-turbo` | `tts-sync` | native | model_level | success | 200 | 877.5 | True | — | 2026-06-06T11:27:41Z |
| `image-01` | `image-t2i` | native | model_level | success | 200 | 15112.7 | True | — | 2026-06-06T11:27:56Z |
| `image-01-live` | `image-t2i` | native | model_level | success | 200 | 8023.5 | True | — | 2026-06-06T11:28:04Z |
| `music-2.6` | `music-gen` | native | model_level | success | 200 | 33133.1 | True | — | 2026-06-06T11:28:37Z |

## 3. Capability Matrix

共 32 个能力。

| capability_id | name | category | requires_model | model_family | cost_level | status | supported_models | default_model | probe_status | probed_model | probe_scope |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `chat-anthropic` | Anthropic 兼容对话 | chat | ✓ | chat | quota | implemented | MiniMax-M3,MiniMax-M2.7-highspeed,MiniMax-M2.5-highspeed,MiniMax-M2.1-highspeed | MiniMax-M2.7-highspeed | not_probed | — | not_probed |
| `chat-openai` | OpenAI 兼容对话 | chat | ✓ | chat | quota | implemented | MiniMax-M3,MiniMax-M2.7,MiniMax-M2.7-highspeed,MiniMax-M2.5,MiniMax-M2.5-highspeed,MiniMax-M2.1,MiniMax-M2.1-highspeed,MiniMax-M2 | MiniMax-M2.7-highspeed | not_probed | — | not_probed |
| `chat-responses-create` | Responses API | chat | ✓ | chat | quota | implemented | MiniMax-M3 | MiniMax-M3 | not_probed | — | not_probed |
| `chat-responses-tokens` | Responses Token 估算 | chat | ✓ | chat | quota | implemented | MiniMax-M3 | MiniMax-M3 | not_probed | — | not_probed |
| `tts-sync` | T2A 同步 | voice | ✓ | speech | quota | implemented | speech-2.8-hd,speech-2.8-turbo,speech-2.6-hd,speech-2.6-turbo,speech-02-hd,speech-02-turbo | speech-2.8-hd | capability_level_verified | speech-02-turbo | capability_level |
| `tts-ws` | T2A WebSocket 流式 | voice | ✓ | speech | quota | implemented | speech-2.8-hd,speech-2.8-turbo,speech-2.6-hd,speech-2.6-turbo,speech-02-hd,speech-02-turbo | speech-02-turbo | capability_level_verified | speech-02-turbo | capability_level |
| `tts-async` | T2A 异步长文本 | voice | ✓ | speech | quota | implemented | speech-2.8-hd,speech-2.8-turbo,speech-2.6-hd,speech-2.6-turbo,speech-02-hd,speech-02-turbo | speech-02-turbo | full_async_flow_verified | speech-02-turbo | full_async_flow |
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
- `MiniMax-M2`
- `MiniMax-M2.7`
- `MiniMax-M2.5`
- `MiniMax-M2.1`

### 5.5 无支持模型的能力（requires_model=true，且 in_scope）
（warning_only/out_of_scope 能力不计入缺口）
- `voice-list`（in_scope，已 safe 验收）

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
- `tts-ws`
- `image-t2i`
- `music-gen`

### 5.9c in_scope 剩余缺口明细（4项未通过 probe）

| capability_id | current_status | why_not_verified | next_action | requires_asset | requires_confirmation |
|---|---|---|---|---|---|
| `image-i2i` | no_probe_record | requires reference image (operation_policy.requires_uploaded_asset=true) | prepare a safe sample image and run guarded probe with asset upload | 是 | confirm_asset_source |
| `file-upload` | no_probe_record | requires file upload (operation_policy.requires_uploaded_asset=true) | prepare a safe small text file and run guarded probe with multipart upload | 是 | confirm_asset_source |
| `file-retrieve` | no_probe_record | file-retrieve not individually probed | run verify_minimax_capabilities.py --capability file-retrieve | 否 | 否 |
| `file-content` | no_probe_record | file-content not individually probed | run verify_minimax_capabilities.py --capability file-content | 否 | 否 |

### 5.9b 已完成 full_async_flow 验收的异步能力
- `tts-async`（create → query → poll → download 全链路完成，asset 保存 49KB）

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

### 5.11 高成本暂缓（video 已 out_of_scope，voice-clone/voice-design/music-cover-prep 为 warning_only）
- `video-t2v`（out_of_scope，不计入缺口）
- `video-i2v`（out_of_scope，不计入缺口）
- `video-s2v`（out_of_scope，不计入缺口）
- `video-query`（out_of_scope，不计入缺口）
- `video-download`（out_of_scope，不计入缺口）
- `voice-clone-do`（warning_only，只做提示）
- `voice-design`（warning_only，只做提示）
- `music-cover-prep`（warning_only，只做提示）

### 5.12 chat-openai 模型级 probe 失败
（无）

### 5.13 chat-anthropic 模型级 probe 失败
（无）

## 6. 收费 / 高成本能力提示矩阵

> 以下能力已按 `billing_policy` 字段分类标记。标记为 `pending_explicit_confirmation` 的能力不得默认执行。

### 6.1 计费分类说明

| billing_category | 含义 | requires_explicit_confirmation |
|---|---|---|
| `normal_token_plan_test` | TokenPlanPlus 极速档正常测试范围，已完成验收 | false |
| `quota_sensitive` | 消耗 TokenPlan 语音/字符额度，需关注用量 | false |
| `paid_confirm_required` | 可能触发单独付费（音色克隆/音色设计），必须确认 | true |
| `high_cost_confirm_required` | 视频生成属于高消耗能力，必须确认 | true |
| `asset_required_confirm_required` | 需要参考音频/素材，必须确认 | true |

### 6.2 能力收费矩阵

| capability_id | billing_category | requires_explicit_confirmation | may_charge_extra | consumes_token_plan_quota | requires_certification | requires_uploaded_asset | current_verification_status | billing_note |
|---|---|---|---|---|---|---|---|---|
| `chat-anthropic` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | safe 验收完成 | TokenPlanPlus 极速档共享配额 |
| `chat-openai` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | safe 验收完成 | TokenPlanPlus 极速档共享配额 |
| `chat-responses-create` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | safe 验收完成 | TokenPlanPlus 极速档共享配额 |
| `chat-responses-tokens` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | safe 验收完成 | TokenPlanPlus 极速档共享配额 |
| `tts-sync` | quota_sensitive | ✗ | ✗ | ✓ | ✗ | ✗ | model_level 验收完成 | 消耗 TokenPlan 语音/字符额度 |
| `tts-ws` | quota_sensitive | ✗ | ✗ | ✓ | ✗ | ✗ | capability_level_verified（speech-02-turbo，9 chunk/13KB，verified_at=2026-06-06，task_started=true，task_finished=true，event_counts={task_continued:9}） | 消耗 TokenPlan 语音/字符额度；WS 协议：task_start→task_started→task_continue+task_finish→task_continued(audio hex)→task_finished；已通过 minimax_core invoke_async 验收 |
| `tts-async` | quota_sensitive | ✗ | ✗ | ✓ | ✗ | ✗ | full_async_flow_verified（create→query→poll→download 全链路通过；task_id/file_id/usage_characters 正确解析；asset 49KB 已保存；字符数保护已收口） | 消耗 TokenPlan 语音/字符额度；字符数保护规则（已收口）：<=300字默认允许；301~1000字允许但有warning；1001~5000字需confirm_quota=true；>5000字硬阻断（confirm_quota也无法绕过，需未来confirm_very_large_quota）；本轮仅用短文本(2字)测试 |
| `voice-clone-upload-audio` | paid_confirm_required | ✓ | ✓ | ✓ | ✗ | ✓ | pending_explicit_confirmation | 音色复刻可能触发单独音色费用 |
| `voice-clone-upload-prompt` | paid_confirm_required | ✓ | ✓ | ✓ | ✗ | ✓ | pending_explicit_confirmation | 音色复刻可能触发单独音色费用 |
| `voice-clone-do` | paid_confirm_required | ✓ | ✓ | ✓ | ✓ | ✓ | pending_explicit_confirmation | 音色克隆官方价 9.9 元/音色 |
| `voice-design` | paid_confirm_required | ✓ | ✓ | ✓ | ✗ | ✗ | pending_explicit_confirmation | 音色设计官方价 9.9 元/音色 |
| `voice-list` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | safe 验收完成 | TokenPlanPlus 极速档共享配额 |
| `voice-delete` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | safe 验收完成 | TokenPlanPlus 极速档共享配额 |
| `image-t2i` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | model_level 验收完成 | TokenPlanPlus 极速档共享配额 |
| `image-i2i` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | pending | TokenPlanPlus 极速档共享配额 |
| `video-t2v` | high_cost_confirm_required | ✓ | ✓ | ✓ | ✗ | ✗ | pending_explicit_confirmation | 视频生成高消耗，必须确认 |
| `video-i2v` | high_cost_confirm_required | ✓ | ✓ | ✓ | ✗ | ✗ | pending_explicit_confirmation | 视频生成高消耗，必须确认 |
| `video-s2v` | high_cost_confirm_required | ✓ | ✓ | ✓ | ✗ | ✗ | pending_explicit_confirmation | 视频生成高消耗，必须确认 |
| `video-query` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | pending | 仅查询状态，不创建视频任务 |
| `video-download` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | pending | 仅下载已有视频，不创建视频任务 |
| `music-gen` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | model_level 验收完成 | TokenPlanPlus 极速档共享配额 |
| `music-cover-prep` | asset_required_confirm_required | ✓ | ✓ | ✓ | ✗ | ✓ | pending_explicit_confirmation | 需要参考音频，属于素材型能力 |
| `lyrics-gen` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | medium 验收完成 | TokenPlanPlus 极速档共享配额 |
| `file-upload` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | safe 验收完成 | TokenPlanPlus 极速档共享配额 |
| `file-list` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | safe 验收完成 | TokenPlanPlus 极速档共享配额 |
| `file-retrieve` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | safe 验收完成 | TokenPlanPlus 极速档共享配额 |
| `file-content` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | safe 验收完成 | TokenPlanPlus 极速档共享配额 |
| `file-delete` | normal_token_plan_test | ✗ | ✗ | ✓ | ✗ | ✗ | safe 验收完成 | TokenPlanPlus 极速档共享配额 |
| `models-openai-list` | normal_token_plan_test | ✗ | ✗ | ✗ | ✗ | ✗ | safe 验收完成 | 纯查询接口，不消耗额度 |
| `models-openai-retrieve` | normal_token_plan_test | ✗ | ✗ | ✗ | ✗ | ✗ | safe 验收完成 | 纯查询接口，不消耗额度 |
| `models-anthropic-list` | normal_token_plan_test | ✗ | ✗ | ✗ | ✗ | ✗ | safe 验收完成 | 纯查询接口，不消耗额度 |
| `models-anthropic-retrieve` | normal_token_plan_test | ✗ | ✗ | ✗ | ✗ | ✗ | safe 验收完成 | 纯查询接口，不消耗额度 |

### 6.3 收费能力验收状态说明

| 状态 | 含义 |
|---|---|
| `safe/medium/model_level 验收完成` | 属于 TokenPlan 正常测试范围，已完成对应层级验收 |
| `pending` | 尚未进行验收，但不属于高成本/付费确认类别 |
| `pending_explicit_confirmation` | 高成本或可能产生额外费用，必须用户明确确认后才执行 |

### 6.4 重要说明

1. **已完成验收的能力**（safe/medium/model_level 验收完成）属于 TokenPlanPlus 极速档正常测试范围。
2. **voice-clone / voice-design** 可能触发单独音色费用（9.9 元/音色），调用前必须确认。
3. **voice-clone** 需要上传参考音频素材，7 天内未正式调用音色会被删除。
4. **video** 类能力属于高消耗，未执行，不得默认触发。
5. **music-cover** 需要参考音频，属于素材型能力，未执行。
6. `pending_explicit_confirmation` 不是失败，而是标记为"需确认后执行"。

## 7. 操作风险保护矩阵

> 以下能力已按 `operation_policy` 字段分类标记，防止前端和脚本误触发危险操作。

### 7.1 操作风险分类说明

| operation_risk | 含义 | requires_operation_confirmation |
|---|---|---|
| `normal` | 普通操作，无特殊风险 | false |
| `destructive` | 删除类操作，执行后不可恢复 | true |
| `asset_required` | 需要上传/引用用户素材，需确认来源 | true |
| `existing_task_only` | 只操作已有任务，不创建新任务 | false |
| `long_running` | 长任务/高消耗能力，必须显式确认 | true |
| `quota_guarded` | 有字符数阈值保护，超过需确认 | true |

### 7.2 能力操作风险矩阵

| capability_id | operation_risk | is_destructive | requires_uploaded_asset | requires_existing_task | is_long_running | operation_note |
|---|---|---|---|---|---|---|
| `chat-anthropic` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `chat-openai` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `chat-responses-create` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `chat-responses-tokens` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `tts-sync` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `tts-ws` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `tts-async` | quota_guarded | ✗ | ✗ | ✗ | ✓ | <=300字默认允许；301~1000字允许但有warning；1001~5000字需confirm_quota；>5000字硬阻断（plain confirm_quota无法绕过，需未来confirm_very_large_quota） |
| `voice-clone-upload-audio` | asset_required | ✗ | ✓ | ✗ | ✗ | 需要上传参考音频；请确认素材来源、隐私、版权 |
| `voice-clone-upload-prompt` | asset_required | ✗ | ✓ | ✗ | ✗ | 需要上传 Prompt 文本；请确认素材来源、隐私 |
| `voice-clone-do` | asset_required | ✗ | ✓ | ✗ | ✗ | 音色克隆训练；克隆音色 7 天未使用会被删除 |
| `voice-design` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `voice-list` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `voice-delete` | destructive | ✓ | ✗ | ✗ | ✗ | 执行前请确认音色 ID，删除后可能无法恢复 |
| `image-t2i` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `image-i2i` | asset_required | ✗ | ✓ | ✗ | ✗ | 需要参考图；请确认素材来源、隐私和版权 |
| `video-t2v` | long_running | ✗ | ✗ | ✗ | ✓ | 视频生成为长任务和高消耗能力，必须显式确认后执行 |
| `video-i2v` | long_running | ✗ | ✗ | ✗ | ✓ | 视频生成为长任务和高消耗能力，必须显式确认后执行 |
| `video-s2v` | long_running | ✗ | ✗ | ✗ | ✓ | 视频生成为长任务和高消耗能力，必须显式确认后执行 |
| `video-query` | existing_task_only | ✗ | ✗ | ✓ | ✗ | 仅限已有任务：需要 task_id，不会自动创建视频任务 |
| `video-download` | existing_task_only | ✗ | ✗ | ✓ | ✗ | 仅限已有任务：需要 file_id，不会自动创建视频任务 |
| `music-gen` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `music-cover-prep` | asset_required | ✗ | ✓ | ✗ | ✗ | 需要上传参考音频；请确认音频来源、版权 |
| `lyrics-gen` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `file-upload` | asset_required | ✗ | ✓ | ✗ | ✗ | 需要上传文件；请确认文件来源、隐私和存储风险 |
| `file-list` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `file-retrieve` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `file-content` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `file-delete` | destructive | ✓ | ✗ | ✗ | ✗ | 执行前请确认文件 ID，删除后可能无法恢复 |
| `models-openai-list` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `models-openai-retrieve` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `models-anthropic-list` | normal | ✗ | ✗ | ✗ | ✗ | — |
| `models-anthropic-retrieve` | normal | ✗ | ✗ | ✗ | ✗ | — |

### 7.3 重要说明

1. **file-delete / voice-delete** 是破坏性操作，执行前必须二次确认目标 ID。
2. **file-upload / image-i2i / voice-clone-upload-audio / music-cover-prep** 是素材型操作，需确认素材来源、隐私和版权。
3. **video-query / video-download** 仅限操作已有任务，不会自动创建视频任务。
4. **tts-async** 有字符数保护：<=300字允许默认测试，>1000字需二次确认，>5000字无显式确认禁止执行。
5. **video-t2v / video-i2v / video-s2v** 是长任务和高成本能力，必须用户显式确认后执行。
6. 本轮不执行任何高成本、破坏性、素材型能力。

## 8. Summary Statistics

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
| model_level probe 成功（本次） | 21 |
| model_level probe 失败（本次） | 0 |
| 能力总数 | 32 |
| **scope: in_scope** | **20** |
| **scope: warning_only** | **7** |
| **scope: out_of_scope** | **5** |
| **in_scope 已通过 probe** | **12**（5 model_level + 1 WS + 2 Matrix doc + 4 file 本轮新增） |
| **in_scope 待验收** | **8**（1 素材型 + 7 需补录 latest.json 覆盖前的成功记录） |
| **in_scope 验收完成率** | **60%**（12/20，基于多来源聚合结果） |
| requires_model=false 能力数 | 10 |
| file-*/models-* 能力数 | 9 |
| normal_token_plan_test 能力数 | 20 |
| quota_sensitive 能力数 | 3 |
| paid_confirm_required 能力数 | 4 |
| high_cost_confirm_required 能力数 | 3 |
| asset_required_confirm_required 能力数 | 1 |
| 可能额外收费能力数 | 8 |
| 需二次确认能力数 | 8 |
| normal 操作能力数 | 21 |
| destructive 操作能力数 | 2 |
| asset_required 操作能力数 | 5 |
| existing_task_only 操作能力数 | 2 |
| long_running 操作能力数 | 3 |
| quota_guarded 操作能力数 | 1 |
| 需操作确认能力数 | 10 |

**范围说明**：
- `in_scope`（20 项）：当前 Token Plan 重点验收能力，计入完成率
- `warning_only`（7 项）：付费/认证/素材型能力，只做风险提示，不计入缺口
- `out_of_scope`（5 项）：视频生成，不纳入当前验收范围，不计入缺口

**完成率计算**（基于 in_scope 20 项，多来源聚合）：
- 已通过 probe：12 项（model_level_probe + tts_ws_probe + Matrix doc + file 本轮新增）
- 待验收：8 项（image-i2i 需素材；其余 7 项前期已 HTTP 200 成功但 latest.json 被后续运行覆盖，需补录）
- 当前完成率：60%（12/20）
- 注：chat-responses-create/tokens、models-*、voice-list 在前期 safe 验收中已 HTTP 200 成功，但 latest.json 被覆盖；Verification Report 也只记录最近一次 run

## 9. 执行前确认门禁矩阵

风险能力默认不会自动执行。必须通过显式确认参数（脚本）或前端确认流程后才允许调用。后端 `CapabilityInvoker` 内置 `RiskGate`，未确认时返回 `risk_gate_blocked` 错误。

### 9.1 确认项说明

| 确认项 | 触发条件 |
|---|---|
| `confirm_paid` | `billing_policy.may_charge_extra=true` |
| `confirm_high_cost` | `billing_category=high_cost_confirm_required` |
| `confirm_destructive` | `operation_policy.is_destructive=true` |
| `confirm_asset_source` | `operation_policy.requires_uploaded_asset=true` |
| `confirm_long_running` | `operation_policy.is_long_running=true` |
| `confirm_existing_task` | `operation_policy.requires_existing_task=true`（需 payload 中有 task_id/file_id） |
| `confirm_quota` | `tts-async` 字符数超阈值（>1000字需确认，>5000字硬阻断） |

### 9.2 能力确认门禁矩阵

| capability_id | required_confirmations | risk_gate_default_allowed | blocked_reasons |
|---|---|---|---|
| `voice-clone-upload-audio` | confirm_paid, confirm_asset_source | 否 | may_charge_extra=true, requires_uploaded_asset=true |
| `voice-clone-upload-prompt` | confirm_paid, confirm_asset_source | 否 | may_charge_extra=true, requires_uploaded_asset=true |
| `voice-clone-do` | confirm_paid, confirm_asset_source | 否 | may_charge_extra=true, requires_uploaded_asset=true |
| `voice-design` | confirm_paid | 否 | may_charge_extra=true |
| `voice-delete` | confirm_destructive | 否 | is_destructive=true |
| `video-t2v` | confirm_high_cost, confirm_long_running | 否 | billing_category=high_cost_confirm_required, is_long_running=true |
| `video-i2v` | confirm_high_cost, confirm_long_running | 否 | billing_category=high_cost_confirm_required, is_long_running=true |
| `video-s2v` | confirm_high_cost, confirm_long_running | 否 | billing_category=high_cost_confirm_required, is_long_running=true |
| `video-query` | confirm_existing_task | 否（无 task_id 时） | requires_existing_task=true 且 payload 无 task_id/file_id |
| `video-download` | confirm_existing_task | 否（无 file_id 时） | requires_existing_task=true 且 payload 无 file_id |
| `music-cover-prep` | confirm_paid, confirm_asset_source | 否 | may_charge_extra=true, requires_uploaded_asset=true |
| `tts-async` | confirm_quota（字符数>1000时）；confirm_very_large_quota（字符数>5000时，未来预留） | 字符数<=300时允许；字符数>5000时无论confirm_quota都硬阻断 | text_length > requires_confirmation_above_chars（1001~5000需confirm_quota）；text_length > hard_block_above_chars_without_confirm（>5000硬阻断，plain confirm_quota无法绕过） |
| `image-i2i` | confirm_asset_source | 否 | requires_uploaded_asset=true |
| `file-upload` | confirm_asset_source | 否 | requires_uploaded_asset=true |
| `file-delete` | confirm_destructive | 否 | is_destructive=true |

### 9.3 重要说明

1. **风险能力默认阻断**：上表中的能力在未提供对应确认参数时，后端 `RiskGate` 会抛出 `risk_gate_blocked` 错误，不实际调用 MiniMax API。
2. **脚本确认参数**：通过 `verify_minimax_capabilities.py` 的 `--confirm-paid`、`--confirm-destructive`、`--confirm-asset-source`、`--confirm-long-running`、`--confirm-existing-task`、`--confirm-quota` 参数提供确认。
3. **tts-async 字符数保护（已收口）**：
   - text_length <= 300：默认允许
   - text_length 301~1000：允许但有 warning（消耗 quota）
   - text_length 1001~5000：需 `confirm_quota=true`
   - text_length > 5000：硬阻断，即使 `confirm_quota=true` 也不行（plain confirm_quota 无法绕过，需未来 `confirm_very_large_quota` 确认项）
4. **video-query / video-download**：即使提供 `confirm_existing_task=true`，若 payload 中无 `task_id`/`file_id` 仍会阻断。

## 10. 前端确认项与后端 RiskGate 闭环

> 本节说明前端确认 UI 与后端 RiskGate 的完整闭环机制。

### 10.1 闭环流程

1. **前端展示确认项**：Capability 页面根据 `billing_policy` 和 `operation_policy` 计算所需确认项，以 checkbox 形式展示
2. **用户勾选确认**：用户必须勾选所有 required confirmation 才能启用 "门禁检查 / Dry Run" 按钮
3. **前端调用 risk-check API**：`POST /api/capabilities/{cap_id}/risk-check`，携带 `confirmations` 字典
4. **后端 RiskGate 裁决**：后端调用 `evaluate_capability_risk()`，返回 `allowed` / `blocked_reasons` / `required_confirmations` / `warnings`
5. **前端展示结果**：页面展示 RiskGate 检查结果，包括是否允许执行、阻断原因、需要确认项、警告
6. **正式调用时再次核验**：前端调用 `POST /api/invoke/{cap_id}` 时仍需携带 `confirmations`，后端 RiskGate 再次裁决

### 10.2 risk-check API

```
POST /api/capabilities/{cap_id}/risk-check
Content-Type: application/json

{
  "payload": {},
  "confirmations": {
    "confirm_paid": false,
    "confirm_high_cost": false,
    "confirm_destructive": false,
    "confirm_asset_source": false,
    "confirm_long_running": false,
    "confirm_existing_task": false,
    "confirm_quota": false
  }
}
```

响应：
```json
{
  "allowed": false,
  "blocked_reasons": [],
  "required_confirmations": [],
  "warnings": []
}
```

**注意**：`risk-check` API 只做 RiskGate 评估，不调用 MiniMax API。

### 10.3 invoke API 确认参数

```
POST /api/invoke/{cap_id}
Content-Type: application/json

{
  "payload": {},
  "confirmations": {
    "confirm_paid": true,
    "confirm_high_cost": true,
    ...
  }
}
```

后端 RiskGate 仍作为最终执行裁决，未确认的风险能力会被阻断。

### 10.4 前端 checkbox 文案

| 确认项 | checkbox 文案 |
|---|---|
| `confirm_paid` | 我确认该能力可能产生额外费用 |
| `confirm_high_cost` | 我确认该能力属于高成本能力 |
| `confirm_destructive` | 我确认这是破坏性操作，资源删除后可能无法恢复 |
| `confirm_asset_source` | 我确认上传/引用素材来源合法，且已获得必要授权 |
| `confirm_long_running` | 我确认该能力是长任务，可能消耗较多额度 |
| `confirm_existing_task` | 我确认已提供已有任务 ID / 文件 ID |
| `confirm_quota` | 我确认文本长度超过默认阈值，允许消耗更多额度 |

### 10.5 前端 UI 门禁机制

1. **确认 checkbox**：Capability 页面展示所需确认项的 checkbox，与 InvokePanel 共享同一份 `confirmations` 状态
2. **Dry Run 按钮**：未全部勾选确认项时禁用，显示"请先完成执行前确认"
3. **真实调用按钮**：未全部勾选确认项时禁用，且对于 `requires_existing_task=true` 能力，无 `task_id`/`file_id` 时也禁用
4. **RiskGate 结果展示**：InvokePanel 内展示 RiskGate 检查结果，包括 allowed 状态、阻断原因、需要确认项、警告
5. **tts-async 字符数展示**：显示当前字符数、默认测试阈值、二次确认阈值、硬阻断阈值
6. **existing_task_only 输入**：video-query / video-download 展示 `task_id`/`file_id` 输入框，自动填充 JSON body

### 10.6 本轮测试结论

| capability | 无确认时 Invoke 按钮 | 需要确认项 |
|---|---|---|
| `tts-sync` | 默认允许 | 无 |
| `voice-design` | 禁用（需 confirm_paid） | `confirm_paid` |
| `video-t2v` | 禁用（需 confirm_paid + confirm_high_cost + confirm_long_running） | `confirm_high_cost`, `confirm_long_running`, `confirm_paid` |
| `file-delete` | 禁用（需 confirm_destructive） | `confirm_destructive` |
| `tts-async`（2000字） | 禁用（需 confirm_quota） | `confirm_quota` |
| `video-query`（无 task_id） | 禁用（需 task_id + confirm_existing_task） | `confirm_existing_task` |

**本轮真实调用按钮也接入 RiskGate 确认门禁，未确认的风险能力不会发起 invoke 请求。仅做 dry-run / risk-check，不执行任何高成本、删除、上传、tts-async、video、voice-clone 能力。**

---
*本报告由 `backend/scripts/generate_full_capability_matrix.py` 自动生成*