# 官方文档对齐审计报告

## 参考文档

- https://platform.minimaxi.com/docs/llms.txt
- https://platform.minimaxi.com/docs/api-reference/text-chat-anthropic
- https://platform.minimaxi.com/docs/api-reference/text-chat-openai
- https://platform.minimaxi.com/docs/api-reference/responses-create
- https://platform.minimaxi.com/docs/api-reference/speech-t2a-http
- https://platform.minimaxi.com/docs/api-reference/voice-management-get
- https://platform.minimaxi.com/docs/api-reference/image-generation-t2i
- https://platform.minimaxi.com/docs/api-reference/image-generation-i2i
- https://platform.minimaxi.com/docs/api-reference/music-generation
- https://platform.minimaxi.com/docs/api-reference/lyrics-generation
- https://platform.minimaxi.com/docs/api-reference/file-management-upload

---

## 1. Chat 对话模块

### 官方文档地址
- https://platform.minimaxi.com/docs/api-reference/text-chat-anthropic
- https://platform.minimaxi.com/docs/api-reference/text-chat-openai
- https://platform.minimaxi.com/docs/api-reference/responses-create

### 官方模型枚举

| 模型 | 上下文 | 能力 | 官方定位 |
|------|--------|------|----------|
| MiniMax-M3 | 128K推荐 / 512K上限 | text+image+video, thinking, tools | **Frontier / Agentic / 多模态旗舰** |
| MiniMax-M2.7 | 64K推荐 / 200K上限 | text+tools, thinking 不可关闭 | 标准档 |
| MiniMax-M2.7-highspeed | 同 M2.7 | 同 M2.7，速度更快 | Token Plan 高频体验 |
| MiniMax-M2.5 / M2.5-highspeed | 64K推荐 / 200K上限 | text+tools, thinking 不可关闭 | 历史档 |
| MiniMax-M2.1 / M2.1-highspeed | 64K推荐 / 200K上限 | text+tools, thinking 不可关闭 | 历史档 |
| MiniMax-M2 | 64K推荐 / 200K上限 | text+tools, thinking 不可关闭 | 历史档 |

### 官方推荐模型
- **M3**：官方示例中使用 M3 作为 Responses API 的默认示例；唯一支持多模态（图片/视频理解）+ thinking + tools 的模型
- **M2.7-highspeed**：适合 Token Plan 高频体验，速度快
- Responses API 官方文档示例统一使用 MiniMax-M3

### 当前本地配置模型
- MiniMax-M3, M2.7, M2.7-highspeed, M2.5, M2.5-highspeed, M2.1, M2.1-highspeed, M2

### Token Plan 已验收模型
- M2.7-highspeed（M2 档位高速版，Token Plan 共享配额）
- M2.5 / M2.1 / M2（标准档，按量计费）

### UI 当前展示推荐
```
"推荐模型"：未分层展示
```

### 是否存在误导
**是**。未区分：
- 官方当前旗舰（M3）vs 体验优先（M2.7-highspeed）
- 高速度场景 vs 高能力场景
- 历史兼容模型 vs 当前推荐模型

### 需要修正的字段
- `model_notes`：增加 source、recommendation_level、best_for、not_best_for、notes
- 分层推荐：official_current / verified_stable / low_latency / compatible

### 修正建议
```json
{
  "model": "MiniMax-M3",
  "label": "旗舰多模态模型",
  "source": "official_docs",
  "recommendation_level": "official_primary",
  "token_plan_status": "available_direct",
  "best_for": ["多模态理解（图片/视频）", "复杂 Agent 工作流", "1M 超长上下文", "thinking 思考模式"],
  "not_best_for": ["Token Plan 高频快速体验（推荐 M2.7-highspeed）", "纯文本低成本场景"],
  "notes": "官方 Responses API 示例默认使用 M3；唯一支持多模态输入的模型"
}
```

---

## 2. Voice 语音模块

### 官方文档地址
- https://platform.minimaxi.com/docs/api-reference/speech-t2a-http
- https://platform.minimaxi.com/docs/api-reference/voice-management-get

### 官方模型枚举

| 模型 | 状态 | 特点 |
|------|------|------|
| speech-2.8-hd | **当前最新** | 高质量，新代，支持语气词标签 |
| speech-2.8-turbo | **当前最新** | 低延迟，新代，支持语气词标签 |
| speech-2.6-hd | 稳定版 | 高质量，支持 fluent/whisper 情绪 |
| speech-2.6-turbo | 稳定版 | 低延迟，支持 fluent/whisper 情绪 |
| speech-02-hd | 历史兼容 | 已稳定验收，高质量兼容 |
| speech-02-turbo | 历史兼容 | 已稳定验收，低延迟兼容 |
| speech-01-hd | 历史 | 更早版本 |
| speech-01-turbo | 历史 | 更早版本 |

**关键限制**：
- `fluent` / `whisper` 情绪选项**仅 2.6 系列支持**，2.8 不支持 whisper
- 语气词标签 `(laughs)`, `(chuckle)` 等**仅 2.8 系列支持**
- text 长度限制：< 10,000 字符
- > 3000 字符推荐流式输出
- output_format 支持 `url`（有效期24小时）或 `hex`

### 官方推荐模型
- speech-2.8-hd 和 speech-2.8-turbo 是当前最新代
- speech-2.6 系列仍是稳定主力（因支持 whisper/fluent 情绪）

### 当前本地配置模型
- speech-02-turbo, speech-02-hd, speech-2.6-turbo, speech-2.6-hd, speech-2.8-turbo, speech-2.8-hd

### Token Plan 已验收模型
- speech-02-hd / speech-02-turbo（已长期稳定验收）

### UI 当前展示推荐
```
"02 系列低延迟版 / 02 系列高质量版"
```
这会让用户误以为 02 系列是当前最佳。

### 是否存在误导
**是**。02 系列不是当前最新，但 UI 未标注"历史兼容"。

### 需要修正的字段
- `model_notes`：增加 source、recommendation_level、best_for、not_best_for
- 关键参数补全
- 分层标注：official_current / verified_stable / compatible

### 修正建议
```json
[
  {
    "model": "speech-2.8-hd",
    "label": "新一代高质量语音",
    "source": "official_docs",
    "recommendation_level": "official_current",
    "best_for": ["高质量旁白", "正式成片", "自然听感", "语气词效果（laughs等）"],
    "not_best_for": ["whisper/fluent 情绪（仅 2.6 支持）"],
    "notes": "官方同步 TTS 示例使用 speech-2.8-hd；语气词标签仅 2.8 系列支持"
  },
  {
    "model": "speech-2.8-turbo",
    "label": "新一代低延迟语音",
    "source": "official_docs",
    "recommendation_level": "official_current",
    "best_for": ["快速生成", "低延迟优先"],
    "not_best_for": ["whisper/fluent 情绪（仅 2.6 支持）"],
    "notes": "2.8 系列最低延迟版本"
  },
  {
    "model": "speech-02-hd",
    "label": "已验收稳定版（历史兼容）",
    "source": "token_plan_verified",
    "recommendation_level": "verified_stable",
    "best_for": ["Token Plan 长期稳定使用", "兼容性优先"],
    "not_best_for": ["需要最新语气词标签效果"],
    "notes": "已长期验收，稳定回归；非官方当前最新"
  }
]
```

### 关键参数补全
```json
{
  "key_parameters": [
    {"name": "model", "description": "语音模型，如 speech-2.8-hd / speech-2.8-turbo / speech-02-hd"},
    {"name": "text", "description": "待合成文本，必须 < 10,000 字符；> 3000 字推荐 stream=true"},
    {"name": "stream", "description": "是否流式返回，> 3000 字建议开启"},
    {"name": "voice_setting.voice_id", "description": "音色 ID，从 voice-list 查询获取"},
    {"name": "voice_setting.speed", "description": "语速，范围 [0.5, 2]，默认 1.0"},
    {"name": "voice_setting.vol", "description": "音量，(0, 10]，默认 1"},
    {"name": "voice_setting.pitch", "description": "音调，[-12, 12]，默认 0"},
    {"name": "voice_setting.emotion", "description": "情绪类型：happy/sad/angry/fearful/disgusted/surprised/calm/fluent/whisper；fluent/whisper 仅 2.6 支持"},
    {"name": "audio_setting.sample_rate", "description": "采样率，默认 32000；可选 8000/16000/22050/24000/32000/44100"},
    {"name": "audio_setting.bitrate", "description": "比特率，默认 128000；mp3 支持 32000/64000/128000/256000"},
    {"name": "audio_setting.format", "description": "音频格式，默认 mp3；支持 mp3/pcm/flac/wav/pcmu_raw/pcmu_wav/opus"},
    {"name": "output_format", "description": "输出格式：hex（默认）或 url；url 有效期 24 小时"},
    {"name": "aigc_watermark", "description": "是否添加 AIGC 水印，默认 false"},
    {"name": "subtitle_enable", "description": "是否启用字幕输出，默认 false"},
    {"name": "voice_modify", "description": "音色修饰：pitch/intensity/timbre/sound_effects（仅 2.8 支持 sound_effects）"}
  ]
}
```

---

## 3. Vision 图片模块

### 官方文档地址
- https://platform.minimaxi.com/docs/api-reference/image-generation-t2i
- https://platform.minimaxi.com/docs/api-reference/image-generation-i2i

### 官方模型枚举

| 模型 | 能力 | 官方定位 |
|------|------|----------|
| image-01 | 文生图 + 图生图（subject_reference） | 主力模型，支持 width/height，支持 21:9 |
| image-01-live | 文生图 + 图生图 + style 画风 | 画风设置，适合手绘/卡通/风格化；不支持 width/height |

**注意**：i2i（图生图）通过 `subject_reference` 参数实现，不是独立模型。

### 关键参数（官方文档）

**文生图 / 图生图共同**：
- `model`: image-01 或 image-01-live
- `prompt`: 文本描述，max 1500 字符
- `subject_reference`: 图生图必需，类型为 character，包含参考图 URL 或 base64
- `aspect_ratio`: 1:1/16:9/4:3/3:2/2:3/3:4/9:16/21:9（21:9 仅 image-01）
- `response_format`: url 或 base64，url 有效期 24 小时
- `seed`, `n`, `prompt_optimizer`, `aigc_watermark`

**仅 image-01**：
- `width` / `height`: [512, 2048]，需是 8 的倍数

**仅 image-01-live**：
- `style.style_type`: 漫画/元气/中世纪/水彩
- `style.style_weight`: (0, 1]，默认 0.8

### 官方推荐模型
- 官方示例使用 `image-01` 作为 t2i 默认示例
- `image-01-live` 用于需要风格控制的场景

### 当前本地配置模型
- image-01, image-01-live

### Token Plan 已验收模型
- image-01（图生图主力）

### UI 当前展示推荐
```
"主力文生图/图生图模型"
"Live 画风版，更多画风设置"
```
未区分两个模型的不同适用场景。

### 是否存在误导
**部分**。image-01-live 不支持 width/height（这对专业用户很重要），UI 未标注。

### 需要修正的字段
- `model_notes`：增加 source、recommendation_level、best_for、not_best_for
- 补全关键参数
- 强调 subject_reference 是图生图核心

### 修正建议
```json
[
  {
    "model": "image-01",
    "label": "文生图/图生图主力模型",
    "source": "official_docs",
    "recommendation_level": "official_primary",
    "best_for": ["通用文生图", "图生图（subject_reference）", "需要精确尺寸控制（width/height）", "21:9 超宽比例"],
    "not_best_for": ["手绘/卡通/风格化场景（使用 image-01-live）"],
    "notes": "官方 t2i 示例默认使用 image-01；图生图通过 subject_reference 参数实现"
  },
  {
    "model": "image-01-live",
    "label": "画风控制版",
    "source": "official_docs",
    "recommendation_level": "official_current",
    "best_for": ["手绘风格", "卡通风格", "水彩风格", "中世纪风格", "需要 style 画风控制的场景"],
    "not_best_for": ["需要精确像素尺寸（width/height）", "21:9 超宽比例"],
    "notes": "style 画风设置仅 image-01-live 支持；不支持 width/height 参数"
  }
]
```

### 关键参数补全
```json
{
  "key_parameters": [
    {"name": "model", "description": "图像模型：image-01（主力）或 image-01-live（画风控制）"},
    {"name": "prompt", "description": "文本描述，max 1500 字符，描述越详细效果越好"},
    {"name": "subject_reference", "description": "图生图必需；包含 character 类型的角色参考图；需确认素材来源（用户自有图片）"},
    {"name": "style.style_type", "description": "画风类型：漫画/元气/中世纪/水彩（仅 image-01-live）"},
    {"name": "style.style_weight", "description": "画风强度，(0, 1]，默认 0.8（仅 image-01-live）"},
    {"name": "aspect_ratio", "description": "图片比例：1:1/16:9/4:3/3:2/2:3/3:4/9:16/21:9（21:9 仅 image-01）"},
    {"name": "width", "description": "像素宽度，[512, 2048]，需是 8 的倍数（仅 image-01）"},
    {"name": "height", "description": "像素高度，[512, 2048]，需是 8 的倍数（仅 image-01）"},
    {"name": "response_format", "description": "url（默认，24小时有效）或 base64"},
    {"name": "seed", "description": "随机种子，同 seed + 参数产生相似结果"},
    {"name": "n", "description": "每次生成图片数量，1-9"},
    {"name": "prompt_optimizer", "description": "自动优化 prompt，默认 false"},
    {"name": "aigc_watermark", "description": "添加 AIGC 水印，默认 false"},
    {"name": "confirm_asset_source", "description": "素材来源确认（图生图必需）"}
  ]
}
```

---

## 4. Music 音乐模块

### 官方文档地址
- https://platform.minimaxi.com/docs/api-reference/music-generation
- https://platform.minimaxi.com/docs/api-reference/lyrics-generation

### 官方模型枚举

| 模型 | 类型 | 访问 | 官方推荐 |
|------|------|------|----------|
| music-2.6 | 文本生成音乐 | Token Plan & 付费用户；较高 RPM | ✅ **是** |
| music-cover | 参考音频翻唱 | Token Plan & 付费用户；较高 RPM | 否 |
| music-2.6-free | music-2.6 免费版 | 所有 API Key 用户；较低 RPM | 否（免费版） |
| music-cover-free | music-cover 免费版 | 所有 API Key 用户；较低 RPM | 否（免费版） |

**lyrics-generation 是独立端点**，无需选择模型，参数包括 mode/prompt/lyrics/title。

### 官方推荐模型
- **music-2.6**：官方文档明确标注为推荐模型
- music-2.6-free 仅是免费变体，不应作为 Token Plan 默认推荐

### 当前本地配置模型
- music-2.6, music-cover, music-2.6-free, music-cover-free

### Token Plan 已验收模型
- music-2.6（官方推荐，已验收）

### UI 当前展示推荐
```
"音乐生成主力模型"
"翻唱生成模型"
```
未区分 free 版和正式版。

### 是否存在误导
**是**。未标注 music-2.6-free 是免费变体（低 RPM），用户可能误选。

### 需要修正的字段
- `model_notes`：区分 official_recommended / free_tier
- 增加 recommendation_level / best_for / notes

### 修正建议
```json
[
  {
    "model": "music-2.6",
    "label": "官方推荐音乐生成模型",
    "source": "official_docs",
    "recommendation_level": "official_primary",
    "best_for": ["AI 歌曲草稿", "情绪 MV", "短视频 BGM", "音乐创作灵感"],
    "not_best_for": ["免费额度测试（使用 music-2.6-free）"],
    "notes": "官方文档明确推荐；Token Plan 和付费用户可用；RPM 较高"
  },
  {
    "model": "music-cover",
    "label": "翻唱生成（需要参考音频）",
    "source": "official_docs",
    "recommendation_level": "guarded",
    "best_for": ["基于参考音频生成翻唱版本"],
    "not_best_for": ["默认音乐生成（使用 music-2.6）", "未确认版权的参考音频"],
    "notes": "需要参考音频（audio_url / audio_base64 / cover_feature_id）；涉及版权风险，不默认执行"
  },
  {
    "model": "music-2.6-free",
    "label": "免费版（低 RPM）",
    "source": "official_docs",
    "recommendation_level": "free_tier",
    "best_for": ["免费额度测试", "体验预览"],
    "not_best_for": ["正式内容生成（RPM 较低）", "Token Plan 主力使用"],
    "notes": "所有用户可用，RPM 较低；不应作为 Token Plan 默认推荐"
  }
]
```

### 关键参数补全
```json
{
  "key_parameters": [
    {"name": "model", "description": "音乐模型：music-2.6（推荐）或 music-cover（翻唱）或 free 版"},
    {"name": "prompt", "description": "音乐风格描述（music-gen）"},
    {"name": "lyrics", "description": "歌词内容（music-gen，可从 lyrics-generation 获取）"},
    {"name": "title", "description": "歌曲标题（可选）"},
    {"name": "style", "description": "音乐风格（流行/摇滚/民谣等）"},
    {"name": "stream", "description": "是否流式返回"},
    {"name": "is_instrumental", "description": "是否生成纯音乐（仅 music-2.6 支持）"},
    {"name": "lyrics_optimizer", "description": "优化歌词（仅 music-2.6 支持）"},
    {"name": "audio_url", "description": "参考音频 URL（music-cover 必需）"},
    {"name": "audio_base64", "description": "参考音频 base64（music-cover 替代选项）"},
    {"name": "cover_feature_id", "description": "封面特征 ID（music-cover 两步流程选项）"},
    {"name": "output_format", "description": "输出格式"},
    {"name": "aigc_watermark", "description": "添加 AIGC 水印"}
  ]
}
```

---

## 5. Assets 文件模块

### 官方文档地址
- https://platform.minimaxi.com/docs/api-reference/file-management-upload
- https://platform.minimaxi.com/docs/api-reference/file-management-retrieve
- https://platform.minimaxi.com/docs/api-reference/file-management-retrieve-content
- https://platform.minimaxi.com/docs/api-reference/file-management-list

### 文件能力说明
文件管理不是"模型能力"，不需要推荐模型。

| 操作 | capability | 风险 | 说明 |
|------|-----------|------|------|
| file-upload | file-upload | guarded | 上传文件获取 file_id，需 confirm_asset_source |
| file-list | file-list | safe | 查询已上传文件列表 |
| file-retrieve | file-retrieve | safe | 查询文件元数据 |
| file-content | file-content | safe | 读取文件内容或摘要 |
| file-delete | file-delete | blocked | 删除文件，破坏性操作，不默认执行 |

### UI 当前展示推荐
```
"recommended_models": [] （空）
```
符合预期。

### 是否存在误导
**否**。

### 需要修正的字段
- `model_notes`：可标注为空（文件不是模型能力）
- 无需修改 recommended_models

---

## 6. Models 模型发现模块

### 官方文档地址
- https://platform.minimaxi.com/docs/api-reference/models/openai/list-models
- https://platform.minimaxi.com/docs/api-reference/models/anthropic/list-models

### 关键说明
`/v1/models` API 返回的是**兼容协议的模型列表**（主要是 chat 模型），**不包含**：
- speech / image / music / video 等 native 模型
- 这些 native 模型需要通过各自的能力端点验证

### UI 当前展示推荐
```
OpenAI 协议模型
Anthropic 协议模型
```
符合预期。

### 是否存在误导
**是**，需要在 UI 或文档中明确说明：此列表不包含语音/图片/音乐/视频等 native 模型。

### 需要修正的字段
- `model_notes`：增加说明此列表的局限性
- `risk_notes`：明确 native 模型不在此列表中

### 修正建议
```json
{
  "model_notes": [
    {
      "model": "OpenAI Models",
      "label": "OpenAI 兼容协议模型",
      "description": "/v1/models 主要返回 chat 模型；speech/image/music/video 等 native 模型不在此列表",
      "source": "official_docs",
      "recommendation_level": "official_current"
    },
    {
      "model": "Anthropic Models",
      "label": "Anthropic 兼容协议模型",
      "description": "/v1/models 主要返回 chat 模型；speech/image/music/video 等 native 模型不在此列表",
      "source": "official_docs",
      "recommendation_level": "official_current"
    }
  ],
  "risk_notes": [
    "/v1/models 主要返回 chat 模型，speech/image/music/video 等 native 模型不在此列表",
    "native 模型需要通过各自的能力端点验证可用性"
  ]
}
```

---

## 总结：需要修正的文件

| 文件 | 主要修正内容 |
|------|------------|
| capability_profiles.json | 全面升级 model_notes 结构，增加 source/recommendation_level/best_for/not_best_for/notes |
| capability_workflows.json | 关键参数补全 |
| capability_scenarios.json | recommended_models 标注来源和推荐理由 |
| check_capability_profiles.py | 增加新字段校验 |

## source 可选值
- `official_docs` - 官方文档标注
- `token_plan_verified` - Token Plan 已验收
- `local_config` - 本地配置
- `historical_compat` - 历史兼容
- `risk_warning` - 风险警示

## recommendation_level 可选值
- `official_primary` - 官方首选/推荐
- `official_current` - 官方当前最新
- `verified_stable` - 已验收稳定
- `low_latency` - 低延迟
- `high_quality` - 高质量
- `quota_friendly` - 额度友好
- `compatible` - 兼容性好
- `guarded` - 需要确认
- `free_tier` - 免费版
- `not_default` - 不默认执行
