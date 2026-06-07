# Capability Profile, Workflow & Scenario Design

**分支**: `docs/capability-profile-workflow-design`
**目标**: MiniMax Token Plan 能力画像 + 场景推荐 + 流程体验工作台
**阶段**: 产品化增强需求定义（不写代码）

---

## 1. 产品目标

让用户清楚理解：

1. 我的 Token Plan 实际能做什么
2. 哪些能力已经实测通过
3. 哪些能力可以直接体验
4. 哪些能力需要确认或不默认执行
5. 每类能力支持哪些模型
6. 模型之间有什么差异
7. 每类能力有哪些关键参数
8. 哪些能力可以组成流程
9. 用户想做某个场景时应该用哪些能力
10. 后续产品如何复用这些能力

---

## 2. Token Plan 状态 vs API 接入状态

> **核心原则**：
> - API 存在 ≠ 当前 Token Plan 可直接使用
> - Token Plan 可用 ≠ 可以无确认执行
> - 已接入 ≠ 已真实验收
> - 模型列表 API 返回 ≠ MiniMax 全量模型能力

### 2.1 Token Plan 状态

回答：当前用户套餐能不能用？是否已实测通过？是否消耗套餐额度？

| 状态 | 含义 | 是否计入完成率 |
|---|---|---|
| `available_direct` | 可直接体验，无需确认 | ✅ |
| `available_guarded` | 可用但需确认（高成本/素材型/长任务） | ✅（需确认后执行） |
| `supported_not_default` | 已支持但不默认执行（voice-clone / video / delete 等） | ❌ |
| `api_only` | 仅 API 说明，不在 Token Plan 范围 | ❌ |
| `unavailable_or_unknown` | 不可用 / 未知 / 未配置 | ❌ |

### 2.2 API 接入状态

回答：项目是否登记了这个 API？是否实现了调用？是否有 payload 示例？

| 状态 | 含义 |
|---|---|
| `implemented_verified` | 已接入且已验收（实测通过） |
| `implemented_unverified` | 已接入但未验收 |
| `registered_only` | 仅登记在 registry，未实现 handler |
| `documented_only` | 仅在 capabilities.yaml 有说明，无 handler |
| `not_supported` | 当前不支持 |

---

## 3. 三层新概念

### 3.1 Capability Profile（能力画像）

**中文**: 能力画像

**作用**: 解释一个能力族整体能做什么、支持哪些模型、模型差异、关键参数、输出类型、风险和产品用途。

**能力画像不是单个 API 说明**。例如 voice 画像不是 tts-sync 的 API 文档，而是整个语音能力族的全局说明。

### 3.2 Capability Workflow（能力流程）

**中文**: 能力流程

**作用**: 把多个相关能力按用户可理解的步骤串联起来，形成完整使用链路。

**示例**:

```
voice-list → 选择音色 → tts-sync → 播放音频
lyrics-gen → 编辑歌词 → music-gen → 播放音乐
file-upload → file-retrieve → file-content
image-t2i → image-i2i
```

### 3.3 Capability Scenario（使用场景推荐）

**中文**: 使用场景推荐

**作用**: 从用户目标出发，推荐能力族、流程、模型和测试入口。

**示例**:

```
短视频旁白 → 语音生成流程
情绪 MV 音乐 → 歌词生成 + 音乐生成流程
图片封面生成 → 文生图流程
文件内容读取 → 文件上传 + 内容读取流程
```

### 3.4 三者关系

```
scenario：用户想做什么
   ↓
workflow：应该按什么步骤做
   ↓
capability：每一步调用哪个能力
   ↓
model / parameter：用哪个模型和参数
   ↓
result：得到什么输出
```

**示例**:

```
短视频旁白
   ↓
语音生成流程
   ↓
voice-list → tts-sync
   ↓
speech-02-turbo + voice_id + text
   ↓
audio controls 播放音频
```

---

## 4. 能力族定义

固定 6 个能力族：`chat` `voice` `vision` `music` `assets` `models`

---

### 4.1 chat 对话能力

**1. 能力族概述**
对话能力提供 OpenAI compatible / Anthropic compatible / MiniMax Responses API 三套协议，支持 chat 系列模型。

**2. Token Plan 状态**
- `available_direct`

**3. API 接入状态**
- `implemented_verified`

**4. 已验收子能力**
- `chat-openai`：OpenAI 兼容协议
- `chat-anthropic`：Anthropic 兼容协议
- `chat-responses-create`：MiniMax Responses API
- `chat-responses-tokens`：Token 计数 / 估算

**5. 可直接体验子能力**
全部 4 个均可直接体验

**6. 需确认子能力**
无

**7. 不默认执行子能力**
无

**8. 支持模型**
| 模型 | 协议 | 上下文 | 模态 | 特点 |
|---|---|---|---|---|
| MiniMax-M3 | OpenAI / Anthropic / Responses | 1M | text+image+video | 旗舰多模态，支持 thinking |
| MiniMax-M2.7 | OpenAI / Anthropic | 204800 | text | 标准档 |
| MiniMax-M2.7 Highspeed | OpenAI / Anthropic | 204800 | text | Token Plan 高频体验，quota 档 |
| MiniMax-M2.5 | OpenAI | 204800 | text | 标准档 |
| MiniMax-M2.5 Highspeed | OpenAI / Anthropic | 204800 | text | Token Plan 高频体验，quota 档 |
| MiniMax-M2.1 | OpenAI | 204800 | text | 标准档 |
| MiniMax-M2.1 Highspeed | OpenAI / Anthropic | 204800 | text | Token Plan 高频体验，quota 档 |
| MiniMax-M2 | OpenAI | 204800 | text | 标准档 |

**9. 模型差异**
- **M3**：旗舰，长上下文（1M），多模态输入（text+image+video），支持 tools / thinking
- **M2.7 / M2.5 / M2.1 Highspeed**：走 TokenPlanPlus 共享配额（`cost_level: quota`），适合高频场景
- **OpenAI / Anthropic / Responses**：三套协议，SDK 接入方式不同，返回格式略有差异

**10. 关键参数**
| 参数 | 说明 |
|---|---|
| model | MiniMax-M3 / M2.7 / ... |
| messages | 对话历史 |
| max_tokens | 最大输出 token |
| temperature | 采样温度 |
| stream | 是否流式返回 |
| tools | 工具调用（仅部分模型） |
| thinking | 是否启用思考（仅 M3） |

**11. 输出结果类型**
- text：对话文本
- thinking_block：（M3 + thinking=true 时）
- tool_calls：（启用 tools 时）
- usage：token 消耗统计

**12. 推荐使用场景**
- 问答系统
- 编码辅助（tools 调用）
- Agent 流程（tool_use / thinking）
- 长上下文处理（文档分析 / 知识库）
- 多协议 SDK 接入（OpenAI SDK / Anthropic SDK / 自有 SDK）

**13. 风险与额度说明**
- Highspeed 模型走 Token Plan 共享配额，不额外计费
- 标准档模型按实际 token 计费
- `chat-responses-tokens` 仅做估算，不产生真实调用

**14. 产品化用途**
- 构建 AI 助手
- 接入 Claude Code / Cursor 等 IDE
- 企业知识库问答
- 多模态内容分析

**15. 推荐流程**
```
models list → 选择协议 → 选择模型 → 输入消息 → chat → 展示回答 → token 估算
```

---

### 4.2 voice 语音能力

**1. 能力族概述**
语音能力提供音色查询、同步 TTS、流式 TTS、异步长文本 TTS。音色克隆和设计能力不默认执行。

**2. Token Plan 状态**
- `available_direct`（voice-list / tts-sync / tts-ws / tts-async）
- `supported_not_default`（voice-clone-* / voice-design / voice-delete）

**3. API 接入状态**
- `implemented_verified`（tts-sync / tts-async / voice-list）
- `implemented_unverified`（tts-ws WebSocket）

**4. 已验收子能力**
- `voice-list` ✅
- `tts-sync` ✅
- `tts-async` ✅
- `tts-ws` ✅

**5. 可直接体验子能力**
- `voice-list`（查询音色，无需确认）
- `tts-sync`（短文本 <= 300 字，无需确认）

**6. 需确认子能力**
- `tts-async`（长文本 > 1000 字需 `confirm_quota`）

**7. 不默认执行子能力**
- `voice-clone-upload-audio`（付费 + 素材）
- `voice-clone-upload-prompt`（付费 + 素材）
- `voice-clone-do`（付费 + 素材）
- `voice-design`（付费）
- `voice-delete`（破坏性）

**8. 支持模型**
| 模型 | 类型 | 特点 |
|---|---|---|
| speech-02-turbo | 低延迟 | 适合快速生成 |
| speech-02-hd | 高质量 | 音质优先 |
| speech-2.6-turbo | 新一代 | 性价比平衡 |
| speech-2.6-hd | 新一代 | 更高质量 |
| speech-2.8-turbo | 最新 | 最低延迟 |
| speech-2.8-hd | 最新 | 最高质量 |

**9. 模型差异**
- **turbo vs hd**：turbo 延迟低，hd 音质好
- **2.6 vs 2.8**：2.8 是最新代，质量和速度最优
- **02 系列**：稳定版推荐，02-hd 是主力推荐

**10. 关键参数**
| 参数 | 说明 | 注意 |
|---|---|---|
| text | 待合成文本 | tts-async > 1000 字需确认 |
| voice_id | 音色 ID | 从 voice-list 查询 |
| model | speech 模型 | speech-02-hd / speech-02-turbo / ... |
| speed | 语速 | 默认 1.0 |
| emotion | 情绪 | 部分音色支持 |
| format | 输出格式 | mp3 / wav / ... |
| sample_rate | 采样率 | 16000 / 24000 / ... |
| bitrate | 比特率 | 影响音质和大小 |

**11. 输出结果类型**
- audio：二进制音频（mp3 / wav）
- task_id：（tts-async）用于轮询
- base_resp：状态码（需检查 status_code 判断业务成功）

**12. 推荐使用场景**
- 短视频旁白
- 语音助手
- 情绪对话
- 有声书片段
- 游戏 / 小镇角色播报

**13. 风险与额度说明**
- tts-sync：默认允许，tts-async 字符数超 1000 需 `confirm_quota`
- 音色克隆和设计可能触发额外付费（9.9 元/音色）
- 流式 tts-ws 通过 WebSocket 透传

**14. 产品化用途**
- 语音助手 / NPC 播报
- 有声内容生成
- 多语言配音
- 情感语音定制

**15. 推荐流程**

**v1（说明型）**:
```
voice-list → 选择 voice_id → 选择 speech 模型 → 输入测试文本 → tts-sync 说明
```

**v2（真实串联）**:
```
voice-list → 真实查询音色列表 → 选择 voice_id → 选择 speech 模型
→ 输入测试文本 → tts-sync → audio controls 播放 → 保存 history
```

---

### 4.3 vision 视觉能力

**1. 能力族概述**
视觉能力提供文生图（image-t2i）和图生图（image-i2i）两种能力，支持 image-01 和 image-01-live 模型。

**2. Token Plan 状态**
- `available_direct`（image-t2i / image-i2i）
- `available_guarded`（image-i2i 图生图需 `confirm_asset_source`）

**3. API 接入状态**
- `implemented_verified`

**4. 已验收子能力**
- `image-t2i` ✅
- `image-i2i` ✅

**5. 可直接体验子能力**
- `image-t2i`（无需参考图）

**6. 需确认子能力**
- `image-i2i`（需要参考图输入，需 `confirm_asset_source`）

**7. 不默认执行子能力**
无

**8. 支持模型**
| 模型 | 特点 |
|---|---|
| image-01 | 文生图 / 图生图主力，支持多种画风 |
| image-01-live | 更多画风设置，支持 live 模式 |

**9. 模型差异**
- **image-01**：通用主力，画风多样
- **image-01-live**：强调实时感 / 动态感画风

**10. 关键参数**
| 参数 | 说明 | 注意 |
|---|---|---|
| prompt | 文本描述 | 核心输入，描述越详细效果越好 |
| model | image 模型 | image-01 / image-01-live |
| img_url | 参考图 URL | 仅 image-i2i 需要 |
| style | 画风 | image-01-live 特有 |
| aspect_ratio / size | 尺寸 | 影响构图和比例 |
| reference_strength | 参考强度 | 仅 image-i2i，影响与参考图的相似度 |
| confirm_asset_source | 素材来源确认 | image-i2i 必需 |

**11. 输出结果类型**
- image_url：生成的图片 URL（可能有时效性）
- base_resp：状态码

**12. 推荐使用场景**
- 封面图生成
- 海报图
- 情绪 MV 分镜图
- 产品配图
- 图生图风格迁移
- 漫画 / 插画创作

**13. 风险与额度说明**
- image-i2i 需要参考图，需确认素材来源（用户自有图片）
- 生成图片 URL 可能有过期时间，需要及时使用

**14. 产品化用途**
- 内容配图自动化
- UGC 图片生成
- 设计灵感生成
- 品牌视觉素材

**15. 推荐流程**

**v1（说明型）**:
```
输入 prompt → 选择 image 模型 → image-t2i 说明 → 图片预览说明
```

**v2（真实串联）**:
```
输入 prompt → 选择 image 模型 → image-t2i → 真实生成 → 图片预览
→ 上传参考图或使用生成图 → image-i2i → 风格变化结果
```

---

### 4.4 music 音乐能力

**1. 能力族概述**
音乐能力提供歌词生成（lyrics-gen）和音乐生成（music-gen）。翻唱（music-cover）涉及素材和版权，不默认执行。

**2. Token Plan 状态**
- `available_direct`（lyrics-gen / music-gen）
- `supported_not_default`（music-cover-prep）

**3. API 接入状态**
- `implemented_verified`

**4. 已验收子能力**
- `lyrics-gen` ✅
- `music-gen` ✅

**5. 可直接体验子能力**
- `lyrics-gen`
- `music-gen`

**6. 需确认子能力**
无

**7. 不默认执行子能力**
- `music-cover-prep`（素材型 + 版权风险）

**8. 支持模型**
| 模型 | 特点 |
|---|---|
| music-2.6 | 音乐生成主力 |
| music-cover | 翻唱生成，需要参考音频 |
| music-2.6-free / music-cover-free | free tier，不在 Token Plan 默认覆盖 |

**9. 模型差异**
- **歌词生成**：文本能力，输入 theme/prompt，输出 lyrics
- **音乐生成**：音频 / 音乐资产能力，输入 lyrics + style，输出 music
- **翻唱**：需要参考音频，涉及版权、素材和成本风险

**10. 关键参数**
| 参数 | 能力 | 说明 |
|---|---|---|
| theme / prompt | lyrics-gen | 歌词主题 |
| lyrics | music-gen | 歌词内容（可从 lyrics-gen 获取） |
| style | music-gen | 音乐风格 |
| title | music-gen | 歌曲标题 |
| model | music-gen | 音乐模型 |
| reference_audio | music-cover | 参考音频（不默认执行） |

**11. 输出结果类型**
- lyrics：（lyrics-gen）歌词文本
- music_url：（music-gen）生成的音乐文件 URL
- task_id：（music-gen 可能异步）
- base_resp：状态码

**12. 推荐使用场景**
- 情绪 MV
- AI 歌曲草稿
- 短视频 BGM
- 音乐创作灵感
- 歌词可视化

**13. 风险与额度说明**
- music-gen 属于中等成本，medium 级别验收已通过
- music-cover 涉及参考音频版权，需显式确认

**14. 产品化用途**
- 音乐创作工具
- UGC 音乐平台
- 短视频配乐
- 品牌音乐定制

**15. 推荐流程**

**v1（说明型）**:
```
输入主题 → lyrics-gen 说明 → 编辑歌词说明 → 选择风格说明 → music-gen 说明
```

**v2（真实串联）**:
```
输入主题 → lyrics-gen → 获取歌词 → 编辑歌词 → 选择风格 / model
→ music-gen → 轮询任务状态 → 获取 music_url → audio controls 播放
```

---

### 4.5 assets 文件 / 资产能力

**1. 能力族概述**
资产能力提供文件上传、列表、详情、内容读取。删除操作是破坏性的，不默认执行。

**2. Token Plan 状态**
- `available_direct`（file-upload / file-list / file-retrieve / file-content）
- `supported_not_default`（file-delete）

**3. API 接入状态**
- `implemented_verified`

**4. 已验收子能力**
- `file-upload` ✅
- `file-list` ✅
- `file-retrieve` ✅
- `file-content` ✅

**5. 可直接体验子能力**
- `file-list`（只读）
- `file-retrieve`（只读）
- `file-content`（只读）

**6. 需确认子能力**
- `file-upload`（需确认素材来源）
- `file-delete`（破坏性操作）

**7. 不默认执行子能力**
- `file-delete`

**8. 支持模型**
无需选择模型（`requires_model: false`）

**9. 模型差异**
N/A — 资产能力不绑定模型

**10. 关键参数**
| 参数 | 能力 | 说明 |
|---|---|---|
| file | file-upload | 上传文件（multipart） |
| file_id | file-retrieve / file-content | 文件唯一标识 |
| purpose | file-upload | 文件用途 |
| confirm_asset_source | file-upload | 素材来源确认 |

**11. 输出结果类型**
- file_id：（file-upload）文件唯一标识
- file_list：（file-list）文件列表
- file_info：（file-retrieve）文件元数据（filename / mime_type / size / ...）
- content：（file-content）文件内容（文本或摘要）

**12. 推荐使用场景**
- 文件能力测试
- 知识库入口
- 文档读取
- 资料分析工作流
- 图片 / 音频资产上传

**13. 风险与额度说明**
- file-upload 需要确认素材来源（用户自有文件）
- file-delete 是破坏性操作，需要 `confirm_destructive`
- 上传文件可能消耗存储额度

**14. 产品化用途**
- 知识库文件管理
- 图片素材上传（配合 image-i2i 参考图）
- 音频素材上传（配合 music-cover 参考音频）
- 文档分析入口

**15. 推荐流程**

**v1（说明型）**:
```
选择安全小文本文件 → file-upload 说明 → file-retrieve 说明 → file-content 说明
```

**v2（真实串联）**:
```
选择安全小文本文件 → file-upload → 获取 file_id → file-retrieve
→ 查看文件元数据 → file-content → 展示内容摘要 → 保存 history
```

---

### 4.6 models 模型发现能力

**1. 能力族概述**
模型发现能力提供 OpenAI 和 Anthropic 两套模型列表接口，用于构建模型选择器和做差异对比。

**2. Token Plan 状态**
- `available_direct`

**3. API 接入状态**
- `implemented_verified`

**4. 已验收子能力**
- `models-openai-list` ✅
- `models-openai-retrieve` ✅
- `models-anthropic-list` ✅
- `models-anthropic-retrieve` ✅

**5. 可直接体验子能力**
全部 4 个均可直接体验

**6. 需确认子能力**
无

**7. 不默认执行子能力**
无

**8. 支持模型**
无需选择模型（`requires_model: false`）

**9. 关键说明**
- `/v1/models` 主要返回 chat 模型
- speech / image / video / music 等 native 模型不一定出现在 models API 中
- 需要通过对应 capability endpoint 验证 native 模型可用性
- 本地 `models.yaml` 记录了完整的 official_current 模型清单

**10. 关键参数**
| 参数 | 说明 |
|---|---|
| 无 | GET 请求，无需参数 |

**11. 输出结果类型**
- models：模型列表（id / object / ...）
- model：单个模型详情

**12. 推荐使用场景**
- 构建模型选择器
- 对比 OpenAI / Anthropic 协议模型覆盖差异
- 校验当前 Key 可见模型
- 与本地 `models.yaml` 做差异对比（发现未被 API 返回但本地已知模型）

**13. 风险与额度说明**
- 仅做列表查询，不产生真实调用费用
- token 估算（chat-responses-tokens）可帮助预估消耗

**14. 产品化用途**
- 统一模型选择 UI
- 模型对比工具
- Token Plan 权益核对

**15. 推荐流程**
```
models-openai-list → 展示 OpenAI 模型列表
→ models-anthropic-list → 展示 Anthropic 模型列表
→ 对比两套协议差异 → 关联本地 models.yaml official_current
```

---

## 5. Capability Workflow 定义

### 5.1 语音生成流程

**workflow_id**: `voice_generation`

**步骤**:
```
1. voice-list        → 查询可用音色列表
2. 选择 voice_id     → 从音色列表中选择
3. 选择 speech 模型  → speech-02-hd / speech-02-turbo / 2.6 / 2.8
4. 输入测试文本      → 填写待合成文本
5. tts-sync          → 同步生成音频
6. 播放音频          → audio controls 展示
7. 切换音色 / 模型  → 再次测试对比
```

**v2 扩展**:
```
tts-ws   → WebSocket 流式合成
tts-async → 异步长文本合成（> 1000 字需确认）
```

### 5.2 音乐创作流程

**workflow_id**: `music_creation`

**步骤**:
```
1. 输入主题         → 描述想要的歌曲风格
2. lyrics-gen       → 生成歌词草稿
3. 编辑歌词         → 用户自定义修改
4. 选择风格 / 模型  → music-gen 参数
5. music-gen        → 生成音乐
6. 轮询任务状态     → 异步任务等待
7. 播放音乐结果     → audio controls 展示
```

### 5.3 图片创作流程

**workflow_id**: `image_creation`

**步骤**:
```
1. 输入 prompt      → 描述想要的图片
2. 选择 image 模型  → image-01 / image-01-live
3. image-t2i        → 文生图
4. 图片预览         → 展示生成结果
5. 选择参考图       → 使用生成图或上传自有图
6. image-i2i        → 图生图（风格变化）
7. 展示变化结果     → 对比原图和生成图
```

### 5.4 文件读取流程

**workflow_id**: `file_knowledge`

**步骤**:
```
1. 选择安全小文本文件 → 上传 txt / md 等文本文件
2. file-upload        → 上传获取 file_id
3. file-retrieve       → 查询文件元数据
4. file-content        → 读取文件内容
5. 展示内容摘要        → 文本预览或摘要
```

### 5.5 对话模型流程

**workflow_id**: `chat_model_comparison`

**步骤**:
```
1. models list        → 查询 OpenAI / Anthropic 模型
2. 选择协议           → OpenAI / Anthropic / Responses
3. 选择模型           → MiniMax-M3 / M2.7 / Highspeed / ...
4. 输入消息           → 填写对话内容
5. chat               → 发起对话请求
6. 展示回答           → 流式或完整文本展示
7. chat-responses-tokens → 估算 token 消耗
```

---

## 6. Capability Scenario 定义

每个 scenario 包含：label / summary / recommended_for / capability_family / workflow_id / capabilities / recommended_models / risk_level / expected_output / default_inputs / cta

---

### 6.1 short_video_voiceover（短视频旁白）

| 字段 | 内容 |
|---|---|
| label | 短视频旁白 |
| summary | 输入文本，选择音色和模型，生成可播放的语音旁白 |
| recommended_for | 短视频创作者、内容创作者、需要配音的自媒体 |
| capability_family | voice |
| workflow_id | voice_generation |
| capabilities | voice-list, tts-sync |
| recommended_models | speech-02-turbo（快）, speech-02-hd（质量） |
| risk_level | low |
| expected_output | MP3 / WAV 音频，可直接用于短视频 |
| default_inputs | text="这是一段测试旁白", speed=1.0 |
| cta | 立即体验语音旁白 |

### 6.2 emotion_dialog_voice（情绪对话语音）

| 字段 | 内容 |
|---|---|
| label | 情绪对话语音 |
| summary | 选择支持情绪的音色，生成带有情绪色彩的语音 |
| recommended_for | 游戏 NPC、语音助手、有声书、情绪类内容创作 |
| capability_family | voice |
| workflow_id | voice_generation |
| capabilities | voice-list, tts-sync |
| recommended_models | speech-02-hd（情绪细节更丰富） |
| risk_level | low |
| expected_output | 带情绪的语音音频 |
| default_inputs | text="你好呀！今天心情真好！", emotion=可选 |
| cta | 体验情绪对话 |

### 6.3 emotion_mv_music（情绪 MV 音乐）

| 字段 | 内容 |
|---|---|
| label | 情绪 MV 音乐 |
| summary | 输入主题生成歌词，选择风格生成音乐，生成 AI 歌曲草稿 |
| recommended_for | 音乐爱好者、MCN、UGC 音乐平台、AI 音乐创作 |
| capability_family | music |
| workflow_id | music_creation |
| capabilities | lyrics-gen, music-gen |
| recommended_models | music-2.6 |
| risk_level | medium |
| expected_output | 歌词文本 + 音乐文件 URL |
| default_inputs | theme="温暖的春日记忆", style="流行" |
| cta | 创作 AI 音乐 |

### 6.4 image_cover_generation（封面 / 海报图生成）

| 字段 | 内容 |
|---|---|
| label | 封面 / 海报图生成 |
| summary | 输入描述词，生成封面图或海报，支持多种画风 |
| recommended_for | 内容创作者、设计师、市场营销、自媒体运营 |
| capability_family | vision |
| workflow_id | image_creation |
| capabilities | image-t2i |
| recommended_models | image-01（主力）, image-01-live（多样画风） |
| risk_level | low |
| expected_output | 图片 URL，可下载或直接使用 |
| default_inputs | prompt="科技感封面图，蓝色调", aspect_ratio="16:9" |
| cta | 生成封面图 |

### 6.5 image_reference_variation（图生图参考变化）

| 字段 | 内容 |
|---|---|
| label | 图生图参考变化 |
| summary | 上传参考图或使用文生图结果，通过 image-i2i 生成风格变化 |
| recommended_for | 设计灵感、风格迁移、漫画创作、图像编辑 |
| capability_family | vision |
| workflow_id | image_creation |
| capabilities | image-t2i, image-i2i |
| recommended_models | image-01-live（画风更丰富） |
| risk_level | medium（需要确认素材来源） |
| expected_output | 风格变化后的图片 URL |
| default_inputs | img_url=参考图, prompt="变成水彩画风格", reference_strength=0.7 |
| cta | 体验图生图 |

### 6.6 file_knowledge_entry（文件知识入口）

| 字段 | 内容 |
|---|---|
| label | 文件知识入口 |
| summary | 上传文本文件，读取内容，作为知识库分析的入口 |
| recommended_for | 知识管理、文档分析、内容处理、数据处理工作流 |
| capability_family | assets |
| workflow_id | file_knowledge |
| capabilities | file-upload, file-retrieve, file-content |
| recommended_models | 无（不需要模型） |
| risk_level | low（文件操作，但仅读取） |
| expected_output | 文件内容摘要或文本 |
| default_inputs | purpose="batch_processing" |
| cta | 上传文件体验 |

### 6.7 chat_model_comparison（对话模型对比）

| 字段 | 内容 |
|---|---|
| label | 对话模型对比 |
| summary | 查询 OpenAI / Anthropic 两套协议模型，对比选择，输入消息体验对话 |
| recommended_for | 开发者、AI 爱好者、SDK 接入验证、模型选型 |
| capability_family | chat |
| workflow_id | chat_model_comparison |
| capabilities | models-openai-list, models-anthropic-list, chat-openai, chat-anthropic, chat-responses-tokens |
| recommended_models | MiniMax-M2.7-highspeed（quota）, MiniMax-M3（旗舰） |
| risk_level | low（quota 档不额外计费） |
| expected_output | 对话文本 + token 消耗估算 |
| default_inputs | messages=[{"role":"user","content":"你好"}] |
| cta | 开始对话 |

### 6.8 agent_api_integration（Agent / SDK 接入）

| 字段 | 内容 |
|---|---|
| label | Agent / SDK 接入 |
| summary | 通过 OpenAI / Anthropic 兼容协议，接入 Claude Code / Cursor 等 IDE |
| recommended_for | 开发者、Agent 构建、SDK 集成、AI 工作流 |
| capability_family | chat |
| workflow_id | chat_model_comparison |
| capabilities | chat-openai, chat-anthropic, chat-responses-create |
| recommended_models | MiniMax-M3（tools + thinking）, M2.7-highspeed（quota） |
| risk_level | low |
| expected_output | 兼容 SDK 的 API 响应 |
| default_inputs | stream=false, model=MiniMax-M3 |
| cta | 查看接入文档 |

---

## 7. 数据文件规划

新增三个数据文件，与现有模块的关系：

```
registry       机器可读能力定义（capabilities.yaml）
description    单个 capability 人类可读说明（capability_descriptions.json）
profile        能力族画像（capability_profiles.json）
workflow       多能力串联流程（capability_workflows.json）
scenario       用户场景推荐（capability_scenarios.json）
verification   真实验收证据（runtime/verification_reports/）
risk_gate      执行安全边界（minimax_core/guards/risk_gate.py）
```

### 7.1 backend/app/minimax_core/profiles/capability_profiles.json

```json
{
  "profiles": {
    "chat": {
      "family": "chat",
      "token_plan_status": "available_direct",
      "api_status": "implemented_verified",
      "sub_capabilities": ["chat-openai", "chat-anthropic", "chat-responses-create", "chat-responses-tokens"],
      "models": [...],
      "key_parameters": ["model", "messages", "max_tokens", "temperature"],
      "output_types": ["text", "thinking_block", "tool_calls", "usage"],
      "product_usage": [...],
      "recommended_workflow": "chat_model_comparison"
    },
    "voice": { ... },
    "vision": { ... },
    "music": { ... },
    "assets": { ... },
    "models": { ... }
  }
}
```

### 7.2 backend/app/minimax_core/workflows/capability_workflows.json

```json
{
  "workflows": {
    "voice_generation": {
      "id": "voice_generation",
      "label": "语音生成流程",
      "steps": [
        {"capability": "voice-list", "action": "query"},
        {"capability": "tts-sync", "action": "invoke"}
      ]
    },
    "music_creation": { ... },
    "image_creation": { ... },
    "file_knowledge": { ... },
    "chat_model_comparison": { ... }
  }
}
```

### 7.3 backend/app/minimax_core/scenarios/capability_scenarios.json

```json
{
  "scenarios": {
    "short_video_voiceover": {
      "id": "short_video_voiceover",
      "label": "短视频旁白",
      "capability_family": "voice",
      "workflow_id": "voice_generation",
      "recommended_models": ["speech-02-turbo", "speech-02-hd"],
      "risk_level": "low",
      "cta": "立即体验"
    }
  }
}
```

---

## 8. UI 信息架构

```
🏠 我的 Token Plan     → 首页：Token Plan 体感总结
🧭 能力画像            → 按能力族展示：模型差异、参数、风险、用途
🎯 场景推荐            → 从用户目标出发，推荐能力和流程
🔁 流程体验            → 步骤化执行：voice / music / image / file / chat
🧪 高级测试控制台      → 开发者入口：手动填 payload、Risk Check、Invoke
📚 API 图谱            → capability_id、endpoint、protocol、model、policy
📜 调用历史            → 测试记录和结果
```

### 页面职责

| 页面 | 职责 |
|---|---|
| 我的 Token Plan | 用自然语言总结当前套餐能做什么，已实测哪些，体验入口 |
| 能力画像 | 展示能力族、模型差异、关键参数、风险和产品用途 |
| 场景推荐 | 用户选择目标 → 推荐能力族和流程 → 跳转流程体验 |
| 流程体验 | 步骤化引导，按 workflow 执行，支持真实调用 |
| 高级测试控制台 | 开发者手动填 payload、Risk Check、Protected Invoke |
| API 图谱 | registry 机器数据展示，protocol / model / policy 详情 |
| 调用历史 | history.jsonl 可视化，支持搜索和导出 |

---

## 9. 开发分期

### v1：说明型产品化

**目标**: 不做真实调用串联，先把信息和架构搭起来

- [ ] 新增 `capability_profiles.json` 数据文件
- [ ] 新增 `capability_workflows.json` 数据文件
- [ ] 新增 `capability_scenarios.json` 数据文件
- [ ] 新增 profile / workflow / scenario loader
- [ ] 新增 `GET /api/profiles`, `GET /api/profiles/{family}`
- [ ] 新增 `GET /api/workflows`, `GET /api/workflows/{id}`
- [ ] 新增 `GET /api/scenarios`, `GET /api/scenarios/{id}`
- [ ] 新增「能力画像」页面（React）
- [ ] 新增「场景推荐」页面（React）
- [ ] 新增「流程体验」页面（React，步骤先跳 Test Console）
- [ ] 更新首页文案，从统计改为用户可理解的能力总结
- [ ] 将单能力详情页「适用模型」改为「当前能力适用模型」

**不做**: 真实调用串联、结果自动传递

### v2：语音流程真实串联

**目标**: voice 流程真实调用串联

- [ ] voice-list 真实查询音色列表
- [ ] voice_id 下拉选择（从 voice-list 结果）
- [ ] speech 模型下拉选择
- [ ] tts-sync 真实调用
- [ ] audio controls 播放
- [ ] 保存 history
- [ ] tts-async 长文本异步流程（可选）

### v3：多流程真实串联

**目标**: lyrics-gen → music-gen 串联

- [ ] lyrics-gen → music-gen 真实串联
- [ ] image-t2i → image-i2i 真实串联
- [ ] file-upload → file-content 真实串联
- [ ] chat models → chat → token count 真实串联

---

## 10. 当前 UI 已知问题与修正方向

### 10.1 当前问题

1. **首页统计过于工程化**：用户看到的是能力数量统计，但不清楚"我能做什么"
2. **"适用模型"文案容易误解**：用户以为这是全量模型列表，实际只是当前 capability 的关联模型
3. **Token Plan 状态和 API 状态混合**：用户不清楚哪些是"我能用的"，哪些是"API 存在但我套餐用不了"的
4. **能力以单点 API 展示**：缺少流程视角，用户不知道哪些能力可以串联
5. **能力说明缺少场景推荐**：只有 API 参数说明，没有"这个能力适合做什么"的信息
6. **用户不能从目标出发**：不能输入"我想做短视频旁白"然后找到推荐能力链路

### 10.2 修正方向

1. **首页改为 Token Plan 体感总结**：用自然语言描述当前套餐能做什么，已实测通过的能力列表
2. **单能力详情页将"适用模型"改为"当前能力适用模型"**：明确这是当前能力下可用的模型，不是全量模型清单
3. **增加能力画像页面**：按能力族组织，展示模型差异、关键参数、风险和产品用途
4. **增加场景推荐页面**：用户选择场景 → 推荐能力族和 workflow → 跳转流程体验
5. **增加流程体验页面**：步骤化引导，先做说明型（跳 Test Console），后期做真实串联
6. **保留高级测试控制台作为开发者入口**：Test Console 继续作为手动测试入口

---

## 11. 与现有模块的整合关系

```
现有模块：
  - registry（capabilities.yaml）→ 机器可读定义
  - description（capability_descriptions.json）→ 单能力人类可读说明
  - verification → 实测验收证据
  - risk_gate → 执行安全边界
  - history → 调用记录

新增模块：
  - profile → 能力族画像（关联 registry + description）
  - workflow → 多能力串联（引用 registry capability）
  - scenario → 用户场景推荐（引用 workflow + profile）
```

---

## 12. 不做的事

- 不写功能代码
- 不新增 API handler 实现
- 不新增 React 页面
- 不修改现有 UI
- 不执行 MiniMax 能力调用
- 不提交 .env
- 不提交 runtime / assets
- 不创建 PR（本次仅提交文档分支）
