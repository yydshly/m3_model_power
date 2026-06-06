# MiniMax 全量能力覆盖矩阵

> 生成时间：2026-06-06T08:43:57Z
> 本报告基于本地 registry 配置和已有验收报告生成，不调用真实 API。

## 1. Model Inventory Matrix

共 38 个模型。

### 对话 / LLM

| ID | 显示名 | tier | official_current | live_available | context | input_modalities | output_modalities | protocols | supports_tools | supports_thinking | thinking_can_disable |
|---|---|---|---|---|---|---|---|---|---|---|
| `MiniMax-M3` | MiniMax M3 | flagship | ✓ | ✓ | 1,000,000 | text,image,video | text | openai,anthropic,responses | ✓ | ✓ | ✓ |
| `MiniMax-M2.7` | MiniMax M2.7 | standard | ✓ | ✓ | 204,800 | text | text | openai | ✓ | ✓ | — |
| `MiniMax-M2.7-highspeed` | MiniMax M2.7 Highspeed | highspeed | ✓ | ✓ | 204,800 | text | text | openai,anthropic | ✓ | ✓ | — |
| `MiniMax-M2.5` | MiniMax M2.5 | standard | ✓ | ✓ | 204,800 | text | text | openai | ✓ | ✓ | — |
| `MiniMax-M2.5-highspeed` | MiniMax M2.5 Highspeed | highspeed | ✓ | ✓ | 204,800 | text | text | openai,anthropic | ✓ | ✓ | — |
| `MiniMax-M2.1` | MiniMax M2.1 | standard | ✓ | ✓ | 204,800 | text | text | openai | ✓ | ✓ | — |
| `MiniMax-M2.1-highspeed` | MiniMax M2.1 Highspeed | highspeed | ✓ | ✓ | 204,800 | text | text | openai,anthropic | ✓ | ✓ | — |
| `MiniMax-M2` | MiniMax M2 | standard | ✓ | ✓ | 204,800 | text | text | openai | ✓ | ✓ | — |
| `abab6.5s-chat` | abab 6.5s | legacy | ✗ | — | 245,760 | text | text | openai | — | — | — |
| `abab6.5-chat` | abab 6.5 | legacy | ✗ | — | 8,192 | text | text | openai | — | — | — |
| `abab6.5t-chat` | abab 6.5t | legacy | ✗ | — | 8,192 | text | text | openai | — | — | — |
| `abab6.5g-chat` | abab 6.5g | legacy | ✗ | — | 8,192 | text | text | openai | — | — | — |

### 语音合成

| ID | 显示名 | tier | official_current | live_available | context | input_modalities | output_modalities | protocols | supports_tools | supports_thinking | thinking_can_disable |
|---|---|---|---|---|---|---|---|---|---|---|
| `speech-2.8-hd` | speech-2.8-hd | hd | ✓ | — | — | text | audio | native | — | — | — |
| `speech-2.8-turbo` | speech-2.8-turbo | turbo | ✓ | — | — | text | audio | native | — | — | — |
| `speech-2.6-hd` | speech-2.6-hd | hd | ✓ | — | — | text | audio | native | — | — | — |
| `speech-2.6-turbo` | speech-2.6-turbo | turbo | ✓ | — | — | text | audio | native | — | — | — |
| `speech-02-hd` | speech-02-hd | hd | ✓ | — | — | text | audio | native | — | — | — |
| `speech-02-turbo` | speech-02-turbo | turbo | ✓ | — | — | text | audio | native | — | — | — |
| `speech-01-hd` | speech-01-hd | legacy | ✗ | — | — | text | audio | native | — | — | — |
| `speech-01-turbo` | speech-01-turbo | legacy | ✗ | — | — | text | audio | native | — | — | — |
| `speech-01-240228` | speech-01-240228 | deprecated | ✗ | — | — | text | audio | native | — | — | — |

### 图像

| ID | 显示名 | tier | official_current | live_available | context | input_modalities | output_modalities | protocols | supports_tools | supports_thinking | thinking_can_disable |
|---|---|---|---|---|---|---|---|---|---|---|
| `image-01` | image-01 | flagship | ✓ | — | — | text | image | native | — | — | — |
| `image-01-live` | image-01-live | flagship | ✓ | — | — | text | image | native | — | — | — |

### 视频

| ID | 显示名 | tier | official_current | live_available | context | input_modalities | output_modalities | protocols | supports_tools | supports_thinking | thinking_can_disable |
|---|---|---|---|---|---|---|---|---|---|---|
| `MiniMax-Hailuo-2.3` | MiniMax Hailuo 2.3 | flagship | ✓ | — | — | text,image | video | native | — | — | — |
| `MiniMax-Hailuo-2.3-Fast` | MiniMax Hailuo 2.3 Fast | highspeed | ✓ | — | — | text,image | video | native | — | — | — |
| `MiniMax-Hailuo-02` | MiniMax Hailuo 02 | standard | ✓ | — | — | text,image | video | native | — | — | — |
| `T2V-01` | T2V-01 | legacy | ✗ | — | — | text | video | native | — | — | — |
| `T2V-01-Director` | T2V-01-Director | legacy | ✗ | — | — | text | video | native | — | — | — |
| `I2V-01` | I2V-01 | legacy | ✗ | — | — | text,image | video | native | — | — | — |
| `I2V-01-live` | I2V-01-live | legacy | ✗ | — | — | text,image | video | native | — | — | — |
| `I2V-01-Director` | I2V-01-Director | legacy | ✗ | — | — | text,image | video | native | — | — | — |
| `S2V-01` | S2V-01 | legacy | ✗ | — | — | text,image | video | native | — | — | — |
| `video-01` | video-01 | deprecated | ✗ | — | — | text | video | native | — | — | — |

### 音乐

| ID | 显示名 | tier | official_current | live_available | context | input_modalities | output_modalities | protocols | supports_tools | supports_thinking | thinking_can_disable |
|---|---|---|---|---|---|---|---|---|---|---|
| `music-2.6` | music-2.6 | flagship | ✓ | — | — | text | music | native | — | — | — |
| `music-cover` | music-cover | flagship | ✓ | — | — | text,audio | music | native | — | — | — |
| `music-2.6-free` | music-2.6-free | standard | ✓ | — | — | text | music | native | — | — | — |
| `music-1.5` | music 1.5 | legacy | ✗ | — | — | text | music | native | — | — | — |
| `music-01` | music 01 | legacy | ✗ | — | — | text | music | native | — | — | — |

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

## 3. Capability Matrix

共 32 个能力。

| capability_id | name | category | requires_model | model_family | cost_level | status | supported_models_count | default_model |
|---|---|---|---|---|---|---|---|---|
| `chat-anthropic` | Anthropic 兼容对话 | chat | ✓ | chat | quota | implemented | 4 | MiniMax-M2.7-highspeed |
| `chat-openai` | OpenAI 兼容对话 | chat | ✓ | chat | quota | implemented | 8 | MiniMax-M2.7-highspeed |
| `chat-responses-create` | Responses API | chat | ✓ | chat | quota | implemented | 1 | MiniMax-M3 |
| `chat-responses-tokens` | Responses Token 估算 | chat | ✓ | chat | quota | implemented | 1 | MiniMax-M3 |
| `tts-sync` | T2A 同步 | voice | ✓ | speech | quota | implemented | 6 | speech-2.8-hd |
| `tts-ws` | T2A WebSocket 流式 | voice | ✓ | speech | quota | implemented | 6 | speech-2.8-hd |
| `tts-async` | T2A 异步长文本 | voice | ✓ | speech | quota | implemented | 6 | speech-2.8-hd |
| `voice-clone-upload-audio` | 克隆-上传音频 | voice | ✓ | — | quota | implemented | 0 | — |
| `voice-clone-upload-prompt` | 克隆-上传 Prompt 文本 | voice | ✓ | — | quota | implemented | 0 | — |
| `voice-clone-do` | 触发音色克隆 | voice | ✓ | — | high | implemented | 6 | speech-2.8-hd |
| `voice-design` | 音色设计 | voice | ✓ | — | medium | implemented | 6 | speech-2.8-hd |
| `voice-list` | 音色列表 | voice | ✓ | — | quota | implemented | 0 | — |
| `voice-delete` | 删除音色 | voice | ✓ | — | quota | implemented | 0 | — |
| `image-t2i` | 文生图 T2I | vision | ✓ | image | quota | implemented | 2 | image-01 |
| `image-i2i` | 图生图 I2I | vision | ✓ | image | quota | implemented | 2 | image-01 |
| `video-t2v` | 文生视频 T2V | vision | ✓ | video | high | implemented | 5 | MiniMax-Hailuo-2.3-Fast |
| `video-i2v` | 图生视频 I2V | vision | ✓ | video | high | implemented | 6 | MiniMax-Hailuo-2.3-Fast |
| `video-s2v` | 主体参考视频 S2V | vision | ✓ | video | high | implemented | 4 | MiniMax-Hailuo-2.3-Fast |
| `video-query` | 视频任务查询 | vision | ✓ | — | quota | implemented | 0 | — |
| `video-download` | 视频下载 | vision | ✓ | — | quota | implemented | 0 | — |
| `music-gen` | 音乐生成 | music | ✓ | music | medium | implemented | 5 | music-2.6 |
| `music-cover-prep` | 翻唱预处理 | music | ✓ | music | medium | implemented | 3 | music-2.6 |
| `lyrics-gen` | 歌词生成 | music | 无需模型 | — | quota | implemented | 0 | — |
| `file-upload` | 文件上传 | files | 无需模型 | — | quota | implemented | 0 | — |
| `file-list` | 文件列表 | files | 无需模型 | — | quota | implemented | 0 | — |
| `file-retrieve` | 文件详情 | files | 无需模型 | — | quota | implemented | 0 | — |
| `file-content` | 文件内容下载 | files | 无需模型 | — | quota | implemented | 0 | — |
| `file-delete` | 文件删除 | files | 无需模型 | — | quota | implemented | 0 | — |
| `models-openai-list` | 模型列表 (OpenAI 协议) | models | 无需模型 | — | quota | implemented | 0 | — |
| `models-openai-retrieve` | 模型详情 (OpenAI 协议) | models | 无需模型 | — | quota | implemented | 0 | — |
| `models-anthropic-list` | 模型列表 (Anthropic 协议) | models | 无需模型 | — | quota | implemented | 0 | — |
| `models-anthropic-retrieve` | 模型详情 (Anthropic 协议) | models | 无需模型 | — | quota | implemented | 0 | — |

## 4. Model-to-Capability Reverse Matrix

每个模型支持的能力列表：

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
**`music-1.5`**: music-gen
**`music-01`**: music-gen

## 5. Gap Matrix

### 5.1 official_current 但本地缺失
（无）

### 5.2 本地有但非 official_current（不含 legacy/deprecated）
（无）

### 5.3 官方 chat 模型未在 live OpenAI 中返回
（无）

### 5.4 官方 chat 模型未在 live Anthropic 中返回（或协议不支持 Anthropic）
- `MiniMax-M2.7`
- `MiniMax-M2`
- `MiniMax-M2.1`
- `MiniMax-M2.5`

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

## 6. Summary Statistics

| 维度 | 数量 |
|---|---|
| 官方当前模型总数 | 22 |
| 本地配置模型总数 | 38 |
| live 可用 chat 模型数 | 8 |
| 已实测（非 legacy/deprecated）模型数 | 8 |
| 未实测 official_current 模型数 | 14 |
| capability_probe 待验收模型数 | 13 |
| 能力总数 | 32 |
| requires_model=false 能力数 | 10 |
| file-*/models-* 能力数 | 9 |

---
*本报告由 `backend/scripts/generate_full_capability_matrix.py` 自动生成*