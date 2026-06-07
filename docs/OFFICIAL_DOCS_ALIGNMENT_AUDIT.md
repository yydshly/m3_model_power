# MiniMax 官方文档对齐审计报告

> 审计日期：2026-06-08
> 审计范围：MiniMax 官网 `/docs/llms.txt` 全量 API 索引 vs 本项目 `models.yaml` / `capabilities.yaml` / Runner templates
> 审计原则：本轮只做审计记录，不执行真实 API，不修改业务代码

---

## 一、官网文档索引覆盖

### 官方文档入口
- https://platform.minimaxi.com/docs/llms.txt

### 官网模块分组

| 官方分组 | 官方文档路径 | 本项目状态 |
|----------|-------------|-----------|
| **文本 — Anthropic 兼容** | `text-chat-anthropic.md` | ✅ implemented (chat-anthropic) |
| **文本 — Anthropic 主动缓存** | `anthropic-api-compatible-cache.md` | ❌ missing_capability |
| **文本 — Anthropic SDK** | `text-anthropic-api.md` | ✅ via chat-anthropic |
| **文本 — OpenAI Chat** | `text-chat-openai.md` | ✅ implemented (chat-openai) |
| **文本 — OpenAI SDK** | `text-openai-api.md` | ✅ via chat-openai |
| **文本 — Responses Create** | `responses-create.md` | ✅ implemented (chat-responses-create) |
| **文本 — Responses Input Tokens** | `responses-input-tokens.md` | ✅ implemented (chat-responses-tokens) |
| **文本 — Prompt 缓存** | `text-prompt-caching.md` | ❌ missing_capability |
| **文本 — AI SDK** | `text-ai-sdk.md` | 🟡 docs_only |
| **语音 — TTS HTTP** | `speech-t2a-http.md` | ✅ implemented (tts-sync) |
| **语音 — TTS WebSocket** | `speech-t2a-websocket.md` | ✅ implemented (tts-ws) |
| **语音 — TTS Async** | `speech-t2a-async-create.md` | ✅ implemented (tts-async) |
| **语音 — 音色列表** | `voice-management-get.md` | ✅ implemented (voice-list) |
| **语音 — 音色克隆** | `voice-cloning-clone.md` | ✅ implemented (voice-clone-do) |
| **语音 — 音色设计** | `voice-design-design.md` | ✅ implemented (voice-design) |
| **语音 — 音色删除** | `voice-management-delete.md` | ✅ implemented (voice-delete) |
| **语音 — 上传克隆音频** | `voice-cloning-uploadcloneaudio.md` | ✅ implemented (voice-clone-upload-audio) |
| **语音 — 上传 Prompt** | `voice-cloning-uploadprompt.md` | ✅ implemented (voice-clone-upload-prompt) |
| **图像 — 文生图** | `image-generation-t2i.md` | ✅ implemented (image-t2i) |
| **图像 — 图生图** | `image-generation-i2i.md` | ✅ implemented (image-i2i) |
| **音乐 — 歌词生成** | `lyrics-generation.md` | ✅ implemented (lyrics-gen) |
| **音乐 — 音乐生成** | `music-generation.md` | ✅ implemented (music-gen) |
| **音乐 — 翻唱预处理** | `music-cover-preprocess.md` | ✅ implemented (music-cover-prep) |
| **文件 — 上传** | `file-management-upload.md` | ✅ implemented (file-upload) |
| **文件 — 列表** | `file-management-list.md` | ✅ implemented (file-list) |
| **文件 — 检索** | `file-management-retrieve.md` | ✅ implemented (file-retrieve) |
| **文件 — 内容下载** | `file-management-retrieve-content.md` | ✅ implemented (file-content) |
| **文件 — 删除** | `file-management-delete.md` | ✅ implemented (file-delete) |
| **视频 — 文生视频** | `video-generation-t2v.md` | ✅ implemented (video-t2v) |
| **视频 — 图生视频** | `video-generation-i2v.md` | ✅ implemented (video-i2v) |
| **视频 — 首尾帧视频** | `video-generation-fl2v.md` | ❌ missing_capability |
| **视频 — 主体参考视频** | `video-generation-s2v.md` | ✅ implemented (video-s2v) |
| **视频 — 视频查询** | `video-generation-query.md` | ✅ implemented (video-query) |
| **视频 — 视频下载** | `video-generation-download.md` | ✅ implemented (video-download) |
| **视频 — Agent 创建** | `video-agent-create.md` | ❌ missing_capability |
| **视频 — Agent 查询** | `video-agent-query.md` | ❌ missing_capability |
| **模型 — OpenAI list** | `models/openai/list-models.md` | ✅ implemented (models-openai-list) |
| **模型 — OpenAI retrieve** | `models/openai/retrieve-model.md` | ✅ implemented (models-openai-retrieve) |
| **模型 — Anthropic list** | `models/anthropic/list-models.md` | ✅ implemented (models-anthropic-list) |
| **模型 — Anthropic retrieve** | `models/anthropic/retrieve-model.md` | ✅ implemented (models-anthropic-retrieve) |
| **Token Plan — Claude Code** | `pricing-token-plan.md` | 🟡 token_plan_unknown |
| **Token Plan — Codex** | `pricing-token-plan.md` | 🟡 token_plan_unknown |
| **Token Plan — Cursor** | `pricing-token-plan.md` | 🟡 token_plan_unknown |
| **Token Plan — TRAE** | `pricing-token-plan.md` | 🟡 token_plan_unknown |
| **Token Plan — OpenClaw** | `pricing-token-plan.md` | 🟡 token_plan_unknown |
| **Token Plan — Hermes Agent** | `pricing-token-plan.md` | 🟡 token_plan_unknown |
| **Token Plan — MiniMax CLI** | `pricing-token-plan.md` | 🟡 token_plan_unknown |
| **Token Plan — Token Plan MCP** | `pricing-token-plan.md` | 🟡 token_plan_unknown |

---

## 二、能力差异矩阵

### 列说明

| 列名 | 说明 |
|------|------|
| Official Doc | 官网文档名称 |
| Official Endpoint | 实际 HTTP 端点或 WebSocket 路径 |
| OpenAPI Spec | 官网 OpenAPI 规范文件名 |
| Current capability_id | 本项目 `capabilities.yaml` 中的 id |
| Registry status | implemented / missing / warning_only / out_of_scope |
| Scope policy | 来自 capabilities.yaml scope_policy.current_scope |
| Billing policy | 来自 capabilities.yaml billing_policy.billing_category |
| Operation risk | 来自 capabilities.yaml operation_policy.operation_risk |
| Runner support | runner 模板是否完整（full / smoke / missing） |
| Advanced Test support | Advanced Test 场景是否覆盖 |
| Frontend detail support | 前端详情页是否完整说明所有参数 |
| Verified status | 已验收 / 未验收 / 需要探针 |
| Gap type | 见下方枚举 |
| Priority | P0 / P1 / P2 / P3 |
| Action | 下一步建议 |

### Gap type 枚举

| 值 | 含义 |
|----|------|
| missing_capability | 官网有，但本项目 capabilities.yaml 完全没有 |
| missing_model | 模型在官网列出但 models.yaml 缺失 |
| missing_parameter | 参数在官网支持但 Runner 表单/Advanced Test 未暴露 |
| wrong_protocol | 本项目协议标注与官网不符 |
| wrong_scope | scope_policy 与官网能力定位不符 |
| wrong_risk_policy | operation_risk 或 billing_policy 与实际风险不符 |
| runner_incomplete | Runner 表单只是 smoke，暴露参数不完整 |
| docs_only | 官网文档存在但本项目未实现 |
| out_of_scope_by_design | 本项目明确标注不执行（高成本/高风险），符合设计 |
| high_risk_by_design | 高成本/高风险，但需明确标注 |
| token_plan_unknown | Token Plan 支持情况需确认 |
| needs_real_probe | 需要真实 API 探针验证 |

### Priority 枚举

| 值 | 含义 |
|----|------|
| P0 | 当前 UI/Registry 明显误导用户 |
| P1 | 官网支持但本项目标注/参数不完整 |
| P2 | 高成本/高风险/非默认执行能力，仅需标注 |
| P3 | Token Plan 无法确认，保留观察 |

---

### 2.1 文本 — Anthropic 协议

| Official Doc | Official Endpoint | OpenAPI Spec | Current capability_id | Registry status | Scope policy | Billing policy | Operation risk | Runner support | Advanced Test support | Frontend detail support | Verified status | Gap type | Priority | Action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Anthropic Messages API | POST /anthropic/v1/messages | openapi-chat-anthropic | chat-anthropic | implemented | in_scope | normal_token_plan_test | normal | smoke (仅 3 模型 + prompt + max_tokens) | 部分暴露 | 不完整 | 已验收 | runner_incomplete | P1 | Runner 表单补全所有 Anthropic 支持参数（system / temperature / top_p / thinking / tools / tool_choice / metadata） |
| Anthropic 主动缓存 | (same endpoint, cache control headers) | — | — | missing | — | — | — | — | — | — | — | missing_capability | P1 | 新增 anthropic-active-cache capability，参考 text-prompt-caching |
| Models List (Anthropic) | GET /anthropic/v1/models | — | models-anthropic-list | implemented | in_scope | normal_token_plan_test | normal | full | 已覆盖 | 完整 | 已验收 | — | — | — |
| Models Retrieve (Anthropic) | GET /anthropic/v1/models/{model} | — | models-anthropic-retrieve | implemented | in_scope | normal_token_plan_test | normal | full | 已覆盖 | 完整 | 已验收 | — | — | — |

### 2.2 文本 — OpenAI Chat 协议

| Official Doc | Official Endpoint | OpenAPI Spec | Current capability_id | Registry status | Scope policy | Billing policy | Operation risk | Runner support | Advanced Test support | Frontend detail support | Verified status | Gap type | Priority | Action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Chat Completions API | POST /v1/chat/completions | openapi-chat-openai | chat-openai | implemented | in_scope | normal_token_plan_test | normal | smoke (仅 3 模型 + prompt + temperature) | 部分暴露 | 不完整 | 已验收 | runner_incomplete | P1 | Runner 表单补全 thinking / reasoning_split / max_completion_tokens / top_p / tools / stream_options |
| Models List (OpenAI) | GET /v1/models | — | models-openai-list | implemented | in_scope | normal_token_plan_test | normal | full | 已覆盖 | 完整 | 已验收 | — | — | — |
| Models Retrieve (OpenAI) | GET /v1/models/{model} | — | models-openai-retrieve | implemented | in_scope | normal_token_plan_test | normal | full | 已覆盖 | 完整 | 已验收 | — | — | — |

### 2.3 文本 — Responses 协议

| Official Doc | Official Endpoint | OpenAPI Spec | Current capability_id | Registry status | Scope policy | Billing policy | Operation risk | Runner support | Advanced Test support | Frontend detail support | Verified status | Gap type | Priority | Action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Responses Create | POST /v1/responses | openapi-responses | chat-responses-create | implemented | in_scope | normal_token_plan_test | normal | smoke (仅 3 模型 + prompt + max_output_tokens) | 部分暴露 | 不完整 | 已验收 | runner_incomplete | P1 | Runner 表单补全 output_text / output[].content[] / reasoning_text / tools 等参数 |
| Responses Input Tokens | POST /v1/responses/input_tokens | — | chat-responses-tokens | implemented | in_scope | normal_token_plan_test | normal | smoke | 部分暴露 | 不完整 | 已验收 | runner_incomplete | P2 | 仅估算接口，scope 合理；可补充说明 |
| Prompt 缓存 | (cache control params on existing endpoints) | — | — | missing | — | — | — | — | — | — | — | missing_capability | P1 | 新增 prompt-caching capability，记录缓存策略 |
| AI SDK | — | — | — | docs_only | — | — | — | — | — | — | — | docs_only | P3 | 无需本项目实现，仅标注 docs_only |
| Anthropic Active Cache | — | — | — | missing | — | — | — | — | — | — | — | missing_capability | P1 | 新增 anthropic-active-cache capability |

### 2.4 语音

| Official Doc | Official Endpoint | Current capability_id | Registry status | Scope policy | Billing policy | Operation risk | Runner support | Advanced Test support | Frontend detail support | Verified status | Gap type | Priority | Action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TTS HTTP Sync | POST /v1/t2a_v2 | tts-sync | implemented | in_scope | quota_sensitive | normal | full | 已覆盖 | 完整 | 已验收 | — | — | — |
| TTS WebSocket | WS /ws/v1/t2a_v2 | tts-ws | implemented | in_scope | quota_sensitive | normal | full | 已覆盖 | 完整 | 已验收 | — | — | — |
| TTS Async Create | POST /v1/t2a_async_v2 | tts-async | implemented | in_scope | quota_sensitive | quota_guarded | full | 已覆盖 | 完整 | 已验收 | — | — | — |
| Voice List | POST /v1/get_voice | voice-list | implemented | in_scope | normal_token_plan_test | normal | full | 已覆盖 | 完整 | 已验收 | — | — | — |
| Voice Clone Do | POST /v1/voice_clone | voice-clone-do | implemented | warning_only | paid_confirm_required | asset_required | warning_only | 部分暴露 | 部分 | 已标注 | 已验收 | out_of_scope_by_design | P2 | 标注准确，无需修改 |
| Voice Design | POST /v1/voice_design | voice-design | implemented | warning_only | paid_confirm_required | normal | warning_only | 部分暴露 | 部分 | 已验收 | out_of_scope_by_design | P2 | 标注准确，无需修改 |
| Voice Delete | POST /v1/delete_voice | voice-delete | implemented | warning_only | normal_token_plan_test | destructive | warning_only | 已覆盖 | 完整 | 已验收 | out_of_scope_by_design | P2 | 标注准确，无需修改 |
| Voice Clone Upload Audio | POST /v1/files/upload | voice-clone-upload-audio | implemented | warning_only | paid_confirm_required | asset_required | warning_only | full | 已覆盖 | 完整 | 已验收 | out_of_scope_by_design | P2 | 标注准确，无需修改 |
| Voice Clone Upload Prompt | POST /v1/files/upload | voice-clone-upload-prompt | implemented | warning_only | paid_confirm_required | asset_required | warning_only | full | 已覆盖 | 完整 | 已验收 | out_of_scope_by_design | P2 | 标注准确，无需修改 |

**Runner 参数缺失（tts-sync）**：
- `emotion` 参数：fluent/whisper 仅 2.6 系列支持，2.8 不支持 — UI 未区分说明
- `voice_modify`（sound_effects 仅 2.8 支持）— UI 未说明
- `aigc_watermark` / `subtitle_enable` — UI 未暴露
- **Priority**: P2（语音参数，不影响核心功能，但会影响高级用户使用）

### 2.5 图像

| Official Doc | Official Endpoint | Current capability_id | Registry status | Scope policy | Billing policy | Operation risk | Runner support | Advanced Test support | Frontend detail support | Verified status | Gap type | Priority | Action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Image T2I | POST /v1/image_generation | image-t2i | implemented | in_scope | normal_token_plan_test | normal | full | 已覆盖 | 完整 | 已验收 | — | — | — |
| Image I2I | POST /v1/image_generation | image-i2i | implemented | in_scope | normal_token_plan_test | asset_required | full | 已覆盖 | 部分 | 已验收 | runner_incomplete | P1 | `reference_mode` UI-only（无 API 路径），需确认是否 intentional |
| image-01 vs image-01-live | — | — | implemented | — | — | — | — | — | — | — | wrong_scope | P1 | image-01-live 不支持 width/height，UI 未标注此限制；image-01-live 的 style 画风控制仅 live 版支持 |

**image-i2i reference_mode 说明**：
- 官网 `subject_reference` 是必需参数
- 本项目 Runner 暴露 `reference_mode: subject|style|variation` 是 UI 选择
- `subject` 模式对应 `subject_reference[type=character]`
- 当前 `subject_reference.image_file` 只接受 URL，未支持 base64
- **Gap type**: runner_incomplete（P1 需确认是否为 intentional UI-only）

### 2.6 音乐

| Official Doc | Official Endpoint | Current capability_id | Registry status | Scope policy | Billing policy | Operation risk | Runner support | Advanced Test support | Frontend detail support | Verified status | Gap type | Priority | Action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Lyrics Generation | POST /v1/lyrics_generation | lyrics-gen | implemented | in_scope | normal_token_plan_test | normal | full | 已覆盖 | 完整 | 已验收 | — | — | — |
| Music Generation | POST /v1/music_generation | music-gen | implemented | in_scope | quota_sensitive | normal | full | 已覆盖 | 部分 | 已验收 | — | — | — |
| Music Cover Preprocess | POST /v1/music_cover/preprocess | music-cover-prep | implemented | warning_only | asset_required_confirm_required | asset_required | warning_only | 部分暴露 | 部分 | 未验收 | out_of_scope_by_design | P2 | 标注准确，无需修改 |
| music-2.6-free | — | — | implemented (models.yaml) | — | — | — | — | — | — | — | missing_model | P2 | models.yaml 有定义但 Runner 不展示；符合设计（free tier 不推荐） |
| music-cover-free | — | — | implemented (models.yaml) | — | — | — | — | — | — | — | missing_model | P2 | 同上 |

### 2.7 文件

| Official Doc | Official Endpoint | Current capability_id | Registry status | Scope policy | Billing policy | Operation risk | Runner support | Advanced Test support | Frontend detail support | Verified status | Gap type | Priority | Action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| File Upload | POST /v1/files/upload | file-upload | implemented | in_scope | normal_token_plan_test | asset_required | full | 已覆盖 | 完整 | 已验收 | — | — | — |
| File List | GET /v1/files/list | file-list | implemented | in_scope | normal_token_plan_test | normal | full | 已覆盖 | 完整 | 已验收 | — | — | — |
| File Retrieve | GET /v1/files/retrieve | file-retrieve | implemented | in_scope | normal_token_plan_test | normal | full | 已覆盖 | 完整 | 已验收 | — | — | — |
| File Content | GET /v1/files/retrieve_content | file-content | implemented | in_scope | normal_token_plan_test | normal | full | 已覆盖 | 完整 | 已验收 | — | — | — |
| File Delete | POST /v1/files/delete | file-delete | implemented | warning_only | normal_token_plan_test | destructive | warning_only | 已覆盖 | 完整 | 已验收 | out_of_scope_by_design | P2 | 标注准确，无需修改 |

### 2.8 视频

| Official Doc | Official Endpoint | Current capability_id | Registry status | Scope policy | Billing policy | Operation risk | Runner support | Advanced Test support | Frontend detail support | Verified status | Gap type | Priority | Action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Video T2V | POST /v1/video_generation | video-t2v | implemented | out_of_scope | high_cost_confirm_required | long_running | warning_only | 部分暴露 | 部分 | 未验收 | out_of_scope_by_design | P2 | 标注准确，无需修改 |
| Video I2V | POST /v1/video_generation | video-i2v | implemented | out_of_scope | high_cost_confirm_required | long_running | warning_only | 部分暴露 | 部分 | 未验收 | out_of_scope_by_design | P2 | 标注准确，无需修改 |
| Video FL2V（首尾帧） | POST /v1/video_generation | — | missing | — | — | — | — | — | — | — | — | missing_capability | P1 | 官网列出但 capabilities.yaml 缺失；需新增 video-fl2v capability，scope=out_of_scope |
| Video S2V | POST /v1/video_generation | video-s2v | implemented | out_of_scope | high_cost_confirm_required | long_running | warning_only | 部分暴露 | 部分 | 未验收 | out_of_scope_by_design | P2 | 标注准确，无需修改 |
| Video Query | GET /v1/query/video_generation | video-query | implemented | out_of_scope | normal_token_plan_test | existing_task_only | warning_only | 已覆盖 | 完整 | 未验收 | out_of_scope_by_design | P2 | 标注准确，无需修改 |
| Video Download | GET /v1/files/retrieve | video-download | implemented | out_of_scope | normal_token_plan_test | existing_task_only | warning_only | 已覆盖 | 完整 | 未验收 | out_of_scope_by_design | P2 | 标注准确，无需修改 |
| Video Agent Create | POST /v1/video_agent | — | missing | — | — | — | — | — | — | — | — | missing_capability | P2 | 官网列出但 capabilities.yaml 缺失；高成本高风险，建议 scope=out_of_scope |
| Video Agent Query | GET /v1/video_agent | — | missing | — | — | — | — | — | — | — | — | missing_capability | P2 | 同上 |

---

## 三、模型协议矩阵

### 3.1 Chat 模型（M 系列）

| model | official_current | live_available | subscription_expected | openai | anthropic | responses | context | input_modalities | output_modalities | supports_tools | supports_thinking | thinking_can_disable | source_doc | current_yaml_status | gap |
|-------|-----------------|----------------|----------------------|--------|-----------|-----------|---------|-----------------|-------------------|---------------|-----------------|---------------------|------------|-------------------|-----|
| MiniMax-M3 | true | true | true | ✅ | ✅ | ✅ | 1M | text,image,video | text | ✅ | ✅ | ✅ | text-chat-anthropic / text-chat-openai / responses-create | protocols=[openai,anthropic,responses] ✅ | — |
| MiniMax-M2.7 | true | true | true | ✅ | ❌ | ❌ | 200K | text | text | ✅ | ✅ | ❌ | text-chat-anthropic / text-chat-openai | protocols=[openai] ❌ wrong_protocol | P0: M2.7 supports Anthropic according to /v1/models |
| MiniMax-M2.7-highspeed | true | true | true | ✅ | ✅ | ❌ | 200K | text | text | ✅ | ✅ | ❌ | text-chat-anthropic / text-chat-openai | protocols=[openai,anthropic] ✅ | — |
| MiniMax-M2.5 | true | true | true | ✅ | ❌ | ❌ | 200K | text | text | ✅ | ✅ | ❌ | text-chat-anthropic / text-chat-openai | protocols=[openai] ❌ wrong_protocol | P0: M2.5 supports Anthropic according to /v1/models |
| MiniMax-M2.5-highspeed | true | true | true | ✅ | ✅ | ❌ | 200K | text | text | ✅ | ✅ | ❌ | text-chat-anthropic / text-chat-openai | protocols=[openai,anthropic] ✅ | — |
| MiniMax-M2.1 | true | true | true | ✅ | ❌ | ❌ | 200K | text | text | ✅ | ✅ | ❌ | text-chat-anthropic / text-chat-openai | protocols=[openai] ❌ wrong_protocol | P0: M2.1 supports Anthropic according to /v1/models |
| MiniMax-M2.1-highspeed | true | true | true | ✅ | ✅ | ❌ | 200K | text | text | ✅ | ✅ | ❌ | text-chat-anthropic / text-chat-openai | protocols=[openai,anthropic] ✅ | — |
| MiniMax-M2 | true | true | true | ✅ | ❌ | ❌ | 200K | text | text | ✅ | ✅ | ❌ | text-chat-anthropic / text-chat-openai | protocols=[openai] ❌ wrong_protocol | P0: M2 supports Anthropic according to /v1/models |

**关键发现**：M2.7 / M2.5 / M2.1 / M2 的 `protocols` 在 models.yaml 中标注为仅 `[openai]`，但根据 `/v1/models` 接口返回，这些模型同样支持 Anthropic 协议。这是 **P0 级别误导**（protocols 决定 UI 下拉显示，影响用户选择）。

### 3.2 Speech 模型

| model | official_current | live_available | subscription_expected | protocols | source_doc | current_yaml_status | gap |
|-------|-----------------|----------------|----------------------|-----------|------------|-------------------|-----|
| speech-2.8-hd | true | null | true | native | speech-t2a-http | ✅ | needs_real_probe |
| speech-2.8-turbo | true | null | true | native | speech-t2a-http | ✅ | needs_real_probe |
| speech-2.6-hd | true | null | true | native | speech-t2a-http | ✅ | needs_real_probe |
| speech-2.6-turbo | true | null | true | native | speech-t2a-http | ✅ | needs_real_probe |
| speech-02-hd | true | null | true | native | speech-t2a-http | ✅ (enabled=true) | — |
| speech-02-turbo | true | null | true | native | speech-t2a-http | ✅ (enabled=true) | — |
| speech-01-hd | false | null | false | native | — | ❌ official_current=false | — |
| speech-01-turbo | false | null | false | native | — | ❌ official_current=false | — |

**注意**：speech 族 `live_available` 全部为 null，因为 `/v1/models` 不返回 speech 模型。需通过 tts-sync endpoint 探针验证。

### 3.3 Image 模型

| model | official_current | live_available | subscription_expected | protocols | source_doc | current_yaml_status | gap |
|-------|-----------------|----------------|----------------------|-----------|------------|-------------------|-----|
| image-01 | true | null | true | native | image-generation-t2i / i2i | ✅ | needs_real_probe |
| image-01-live | true | null | true | native | image-generation-t2i / i2i | ✅ | needs_real_probe |

### 3.4 Video 模型

| model | official_current | live_available | subscription_expected | protocols | source_doc | current_yaml_status | gap |
|-------|-----------------|----------------|----------------------|-----------|------------|-------------------|-----|
| MiniMax-Hailuo-2.3 | true | null | true | native | video-generation-t2v | ✅ | needs_real_probe |
| MiniMax-Hailuo-2.3-Fast | true | null | true | native | video-generation-t2v | ✅ | needs_real_probe |
| MiniMax-Hailuo-02 | true | null | true | native | video-generation-t2v | ✅ | needs_real_probe |
| T2V-01 | false | null | false | native | — | ❌ official_current=false | — |
| T2V-01-Director | false | null | false | native | — | ❌ official_current=false | — |
| I2V-01 | false | null | false | native | — | ❌ official_current=false | — |
| I2V-01-live | false | null | false | native | — | ❌ official_current=false | — |
| I2V-01-Director | false | null | false | native | — | ❌ official_current=false | — |
| S2V-01 | false | null | false | native | — | ❌ official_current=false | — |
| video-01 | false | null | false | native | — | ❌ official_current=false | — |

### 3.5 Music 模型

| model | official_current | live_available | subscription_expected | protocols | source_doc | current_yaml_status | gap |
|-------|-----------------|----------------|----------------------|-----------|------------|-------------------|-----|
| music-2.6 | true | null | true | native | music-generation | ✅ | needs_real_probe |
| music-cover | true | null | true | native | music-cover-preprocess | ✅ | needs_real_probe |
| music-2.6-free | true | null | false | native | music-generation | ✅ (enabled=false) | — |
| music-cover-free | true | null | false | native | music-cover-preprocess | ✅ (enabled=false) | — |

---

## 四、Runner 下拉模型缺失（Protocol 维度）

### 4.1 chat-anthropic Runner 模型下拉

**当前暴露**：MiniMax-M3, MiniMax-M2.7-highspeed, MiniMax-M2.7（共 3 个）

**官网实际支持 Anthropic 的模型**：
- MiniMax-M3 ✅
- MiniMax-M2.7 ✅ (但 Runner 未列)
- MiniMax-M2.7-highspeed ✅
- MiniMax-M2.5 ✅ (但 Runner 未列)
- MiniMax-M2.5-highspeed ✅ (但 Runner 未列)
- MiniMax-M2.1 ✅ (但 Runner 未列)
- MiniMax-M2.1-highspeed ✅ (但 Runner 未列)
- MiniMax-M2 ✅ (但 Runner 未列)

**结论**：Runner 下拉只有 3 个模型，但官网 Anthropic 协议支持全部 8 个 M 系列模型。

**Gap type**: runner_incomplete
**Priority**: P0（模型下拉缺失导致用户无法选择已支持的模型）

### 4.2 chat-openai Runner 模型下拉

**当前暴露**：MiniMax-M3, MiniMax-M2.7-highspeed, MiniMax-M2.7（共 3 个）

**官网实际支持 OpenAI 的模型**：全部 8 个 M 系列均支持

**结论**：Runner 下拉只有 3 个模型，缺失 M2.5 / M2.5-highspeed / M2.1 / M2.1-highspeed / M2。

**Gap type**: runner_incomplete
**Priority**: P0（同上）

### 4.3 chat-responses-create Runner 模型下拉

**当前暴露**：MiniMax-M3, MiniMax-M2.7-highspeed, MiniMax-M2.7（共 3 个）

**官网 Responses Create 实际支持**：M3 为主力，官方文档示例均用 M3

**结论**：Runner 下拉只有 3 个模型，官网主要推荐 M3，其余为次选。当前可接受，但建议说明推荐逻辑。

**Gap type**: runner_incomplete
**Priority**: P1（建议说明推荐逻辑，非强制修复）

---

## 五、参数完整性审计

### 5.1 Anthropic Messages API 参数

| 官方支持参数 | 本项目 Runner 暴露 | 本项目 Advanced Test 暴露 | Gap type | Priority |
|------------|-----------------|----------------------|---------|---------|
| model | ✅ (3 of 8) | ✅ | runner_incomplete | P0 |
| system | ❌ | ❌ | missing_parameter | P1 |
| messages | ✅ | ✅ | — | — |
| temperature | ❌ | ❌ | missing_parameter | P1 |
| top_p | ❌ | ❌ | missing_parameter | P1 |
| max_tokens | ✅ | ✅ | — | — |
| thinking | ❌ | ❌ | missing_parameter | P1 |
| thoughts | ❌ | ❌ | missing_parameter | P2 |
| tools | ❌ | ❌ | missing_parameter | P1 |
| tool_choice | ❌ | ❌ | missing_parameter | P1 |
| metadata | ❌ | ❌ | missing_parameter | P2 |
| stream | ❌ (默认 false) | ❌ | missing_parameter | P2 |
| stop_sequences | ❌ | ❌ | missing_parameter | P2 |
| timeout | ❌ | ❌ | missing_parameter | P3 |

### 5.2 OpenAI Chat Completions API 参数

| 官方支持参数 | 本项目 Runner 暴露 | 本项目 Advanced Test 暴露 | Gap type | Priority |
|------------|-----------------|----------------------|---------|---------|
| model | ✅ (3 of 8) | ✅ | runner_incomplete | P0 |
| messages | ✅ | ✅ | — | — |
| temperature | ✅ | ✅ | — | — |
| top_p | ❌ | ❌ | missing_parameter | P1 |
| max_tokens / max_completion_tokens | ✅ (max_tokens) | ✅ | — | — |
| thinking | ❌ | ❌ | missing_parameter | P1 |
| reasoning_split | ❌ | ❌ | missing_parameter | P1 |
| tools | ❌ | ❌ | missing_parameter | P1 |
| tool_choice | ❌ | ❌ | missing_parameter | P1 |
| stream_options | ❌ | ❌ | missing_parameter | P2 |
| presence_penalty | ❌ | ❌ | missing_parameter | P2 |
| frequency_penalty | ❌ | ❌ | missing_parameter | P2 |
| logit_bias | ❌ | ❌ | missing_parameter | P3 |
| user | ❌ | ❌ | missing_parameter | P3 |

### 5.3 Responses Create API 参数

| 官方支持参数 | 本项目 Runner 暴露 | 本项目 Advanced Test 暴露 | Gap type | Priority |
|------------|-----------------|----------------------|---------|---------|
| model | ✅ (3 of 8) | ✅ | runner_incomplete | P1 |
| input | ✅ | ✅ | — | — |
| input_modality | ❌ | ❌ | missing_parameter | P1 |
| output_modality | ❌ | ❌ | missing_parameter | P1 |
| max_output_tokens | ✅ | ✅ | — | — |
| stream | ❌ (默认 false) | ❌ | missing_parameter | P2 |
| temperature | ❌ | ❌ | missing_parameter | P1 |
| top_p | ❌ | ❌ | missing_parameter | P1 |
| tools | ❌ | ❌ | missing_parameter | P1 |
| reasoning | ❌ | ❌ | missing_parameter | P1 |
| thinking | ❌ | ❌ | missing_parameter | P1 |
| prompt_caching | ❌ | ❌ | missing_parameter | P1 |

---

## 六、汇总

### 6.1 missing_capability 列表

| capability_id | 官网文档 | Priority |
|-------------|---------|---------|
| video-fl2v | video-generation-fl2v.md | P1 |
| video-agent-create | video-agent-create.md | P2 |
| video-agent-query | video-agent-query.md | P2 |
| anthropic-active-cache | anthropic-api-compatible-cache.md | P1 |
| prompt-caching | text-prompt-caching.md | P1 |

### 6.2 missing_model 列表

（无 - 所有官网模型均已在 models.yaml 中）

### 6.3 wrong_protocol 列表

| model | models.yaml protocols | 实际（根据 /v1/models） | Priority |
|------|----------------------|----------------------|---------|
| MiniMax-M2.7 | [openai] | [openai, anthropic] | P0 |
| MiniMax-M2.5 | [openai] | [openai, anthropic] | P0 |
| MiniMax-M2.1 | [openai] | [openai, anthropic] | P0 |
| MiniMax-M2 | [openai] | [openai, anthropic] | P0 |

### 6.4 runner_incomplete 列表

| capability_id | 缺失内容 | Priority |
|-------------|---------|---------|
| chat-anthropic | 仅 3 模型，缺 system/temperature/top_p/thinking/tools/tool_choice/metadata | P0 |
| chat-openai | 仅 3 模型，缺 thinking/reasoning_split/top_p/tools/tool_choice | P0 |
| chat-responses-create | 仅 3 模型，缺 input_modality/output_modality/reasoning/thinking | P1 |
| tts-sync | 缺 emotion/voice_modify/aigc_watermark/subtitle_enable | P2 |

### 6.5 high_risk_by_design 列表

（无 - 所有高风险能力均已标注 warning_only / out_of_scope）

### 6.6 out_of_scope_by_design 列表

| capability_id | 说明 |
|-------------|------|
| voice-clone-do | 高成本，需认证和资产 |
| voice-design | 需付费确认 |
| voice-delete | 破坏性操作 |
| voice-clone-upload-audio | 需上传资产 |
| voice-clone-upload-prompt | 需上传资产 |
| video-t2v | 高消耗，长任务 |
| video-i2v | 高消耗，长任务 |
| video-s2v | 高消耗，长任务 |
| video-query | 仅查询已有任务 |
| video-download | 仅下载已有视频 |
| music-cover-prep | 需资产和版权确认 |
| file-delete | 破坏性操作 |

### 6.7 token_plan_unknown 列表

| 能力 | 说明 |
|------|------|
| Claude Code | Token Plan 集成，需单独审计 |
| Codex | Token Plan 集成，需单独审计 |
| Cursor | Token Plan 集成，需单独审计 |
| TRAE | Token Plan 集成，需单独审计 |
| OpenClaw | Token Plan 集成，需单独审计 |
| Hermes Agent | Token Plan 集成，需单独审计 |
| MiniMax CLI | Token Plan 集成，需单独审计 |
| Token Plan MCP | Token Plan 集成，需单独审计 |

---

## 七、对齐结论

### 7.1 Anthropic 对齐结论

**官网支持 8 个 M 系列模型，本项目 Runner 只暴露 3 个，且 protocols 标注错误（4 个模型标注为仅 openai，实际支持 anthropic）。**

- **P0 问题**：M2.7 / M2.5 / M2.1 / M2 的 `protocols` 在 models.yaml 中错误标注为仅 `[openai]`，实际 `/v1/models` 返回显示支持 Anthropic
- **P1 问题**：Runner 表单缺失 system / temperature / top_p / thinking / tools / tool_choice / metadata 等核心参数
- **P1 问题**：缺少 anthropic-active-cache capability

### 7.2 OpenAI Chat 对齐结论

**Runner 表单缺失多个关键参数（thinking, reasoning_split, top_p, tools, tool_choice, stream_options）。**

- **P0 问题**：模型下拉只有 3 个，缺失 5 个已支持 OpenAI 的模型
- **P1 问题**：缺少 thinking / reasoning_split / top_p / tools / tool_choice 参数

### 7.3 Responses 对齐结论

**Runner 表单基本 smoke，缺失 input_modality / output_modality / reasoning / thinking / prompt_caching 等参数。**

- **P1 问题**：参数暴露不完整，建议补充说明官方推荐 M3 的原因

### 7.4 图像对齐结论

**基本对齐，image-i2i 的 reference_mode UI 设计与官网 API 语义需确认一致性。**

- **P1 问题**：image-01-live 不支持 width/height，UI 未标注此限制

### 7.5 语音对齐结论

**基本对齐，tts-sync 缺 emotion / voice_modify 等高级参数说明。**

- **P2 问题**：2.8 不支持 whisper/fluent，2.6 不支持 sound_effects，UI 未区分

### 7.6 音乐对齐结论

**基本对齐，music-cover-prep 标注 warning_only 准确。**

### 7.7 文件对齐结论

**完全对齐，无问题。**

### 7.8 视频对齐结论

**video-fl2v（首尾帧视频）和 video-agent-create/query 完全缺失（missing_capability）。**

- **P1 问题**：video-fl2v 缺失
- **P2 问题**：video-agent-create/query 缺失（高成本高风险，建议 scope=out_of_scope）

### 7.9 模型矩阵结论

**M2.7 / M2.5 / M2.1 / M2 的 protocols 标注错误（P0）。** 其他模型协议标注基本正确。

---

## 八、修复建议

### P0（立即修复）

| 编号 | 问题 | 修复文件 | 建议操作 |
|------|------|---------|---------|
| P0-1 | M2.7/M2.5/M2.1/M2 protocols=[openai] 错误 | models.yaml | 改为 protocols=[openai, anthropic] |
| P0-2 | chat-anthropic Runner 模型下拉只有 3 个 | capability_runner_templates.json | 补全 8 个 M 系列模型 |
| P0-3 | chat-openai Runner 模型下拉只有 3 个 | capability_runner_templates.json | 补全 8 个 M 系列模型 |

### P1（下一迭代修复）

| 编号 | 问题 | 修复文件 | 建议操作 |
|------|------|---------|---------|
| P1-1 | chat-anthropic 缺 system/temperature/top_p/thinking/tools/tool_choice/metadata | capability_runner_templates.json | 补全 Advanced Test 表单 |
| P1-2 | chat-openai 缺 thinking/reasoning_split/top_p/tools/tool_choice | capability_runner_templates.json | 补全 Advanced Test 表单 |
| P1-3 | chat-responses-create 缺 input_modality/output_modality/reasoning/thinking | capability_runner_templates.json | 补全 Advanced Test 表单 |
| P1-4 | 缺 anthropic-active-cache capability | capabilities.yaml | 新增 capability |
| P1-5 | 缺 prompt-caching capability | capabilities.yaml | 新增 capability |
| P1-6 | 缺 video-fl2v capability | capabilities.yaml + models.yaml | 新增 capability，scope=out_of_scope |
| P1-7 | image-01-live 不支持 width/height 未标注 | capability_runner_templates.json 或 UI | 在 model note 中补充说明 |

### P2（标注优化）

| 编号 | 问题 | 修复文件 | 建议操作 |
|------|------|---------|---------|
| P2-1 | tts-sync 缺 emotion/voice_modify 参数区分说明 | capability_runner_templates.json | 在 model options 中补充说明 2.6 vs 2.8 差异 |
| P2-2 | 缺 video-agent-create/query capability | capabilities.yaml | 新增，scope=out_of_scope |
| P2-3 | 需补充 Token Plan 各工具集成说明 | 文档 | Token Plan 工具链单独审计 |

### P3（观察）

| 编号 | 问题 | 建议操作 |
|------|------|---------|
| P3-1 | speech 族 live_available=null | 需真实 API 探针验证 |
| P3-2 | image 族 live_available=null | 需真实 API 探针验证 |
| P3-3 | video 族 live_available=null | 需真实 API 探针验证 |
| P3-4 | Token Plan 工具链状态 | 需官方文档确认 |

---

## 九、审计元数据

| 字段 | 值 |
|------|-----|
| 审计日期 | 2026-06-08 |
| 审计分支 | feature/official-docs-alignment-audit |
| base commit | 7abf66b |
| 官网文档索引 | https://platform.minimaxi.com/docs/llms.txt |
| 官网 API categories | 文本(Anthropic/OpenAI/Responses) / 语音 / 图像 / 音乐 / 文件 / 视频 / 模型 / Token Plan |
| 官网 official capabilities 总数 | ~40+ |
| 本项目 registered capabilities | ~30 |
| missing_capability | 5 |
| wrong_protocol | 4 (model-level) |
| runner_incomplete | 4 |
| out_of_scope_by_design | 12 |
| high_risk_by_design | 0 |
| token_plan_unknown | 8 (工具链) |
| needs_real_probe | 6+ (非 chat 模型 live 状态) |
| P0 issues | 3 |
| P1 issues | 7 |
| P2 issues | 3 |
| P3 issues | 4+ |
