# 工作台能力闭环审计

> 审计日期：2026-06-07
> 审计目标：对远端 main 最新代码做全工作台体验闭环审计，明确每个能力的状态、分类和下一步建议。

---

## 1. 当前工作台页面地图

| 页面 | 路由 | 职责 |
|------|------|------|
| 能力画像 | `/capability-profiles` | 按能力族展示已验收能力、风险标签、模型推荐 |
| 场景推荐 | `/capability-scenarios` | 按用户目标推荐能力链路，含 CTA 直接进入 Runner |
| 流程体验 | `/capability-workflows` | 分步骤展示能力链路，每个步骤可跳转 Runner 或高级测试 |
| 能力运行器 | `/capability-runner` | 引导式能力执行：表单 → RiskGate → 执行 → 结果展示 |
| 高级测试 | `/test-console` | raw API 调用控制台，支持所有 capability |
| 能力详情 | `/cap/:id` | 单个能力的文档、API 说明、参数定义 |

---

## 2. 能力闭环矩阵

分类标准：

- **A 类（已闭环可体验）**：Runner 支持 + 结果展示 + 下一步链路完整
- **B 类（已验收未产品化）**：已在 capabilities.yaml 标记 `in_scope` 但 Runner 不支持，仅 Test Console 可用
- **C 类（仅高级测试）**：`in_scope` 但 Runner 表单或结果展示未完成，或需要异步状态机
- **D 类（风险 / 不默认执行）**：`warning_only` / `out_of_scope` / `destructive`，只做风险提示和高级测试

### 2.1 对话（chat）

| capability_id | Runner? | TestConsole? | scope | result_type | 当前 UX 状态 | 分类 |
|--------------|---------|-------------|-------|-------------|-------------|------|
| `chat-openai` | ✅ | ✅ | in_scope | chat | ✅ 已闭环：ChatResultPreview 统一展示 + next_steps | **A** |
| `chat-anthropic` | ✅ | ✅ | in_scope | chat | ✅ 已闭环：ChatResultPreview 统一展示（识别 content[].text） | **A** |
| `chat-responses-create` | ✅ | ✅ | in_scope | chat | ✅ 已闭环：ChatResultPreview 统一展示（识别 output_text） | **A** |
| `chat-responses-tokens` | ❌ | ✅ | in_scope | json | ⚠️ 纯计数接口，TestConsole 可用，Runner 无表单 | **B** |

**A 类说明（2026-06-07 P1-3 完成）**：三套对话协议统一通过 `ChatResultPreview` 展示，自动识别：
- OpenAI Chat：`choices[0].message.content`
- Anthropic Messages：`content[0].text`
- Responses API：`output_text`

`chat-responses-tokens` 为纯 token 计数接口，价值有限，保留为 B 类。

### 2.2 语音（voice）

| capability_id | Runner? | TestConsole? | scope | result_type | 当前 UX 状态 | 分类 |
|--------------|---------|-------------|-------|-------------|-------------|------|
| `voice-list` | ✅ | ✅ | in_scope | json | ✅ 已闭环：Runner 表单 + 结果展示音色列表卡片 + next_steps → tts-sync | **A** |
| `tts-sync` | ✅ | ✅ | in_scope | audio | ✅ 已闭环：AudioBanner + AssetResultPreview + next_steps → voice-list | **A** |
| `tts-async` | ✅ | ✅ | in_scope | async_task | ✅ 已闭环：AsyncTaskResultPreview + start/query 模式 + next_steps → self | **A** |
| `tts-ws` | ❌ | ✅ | in_scope | audio (stream) | ⚠️ WebSocket 流式，TestConsole 有事件摘要；Runner 无表单（WS 连接状态展示复杂） | **C** |
| `voice-clone-upload-audio` | ❌ | ✅ | warning_only | json | ⚠️ 高级测试可用；音色克隆需素材授权，warning_only 不进 Runner | **D** |
| `voice-clone-upload-prompt` | ❌ | ✅ | warning_only | json | 同上 | **D** |
| `voice-clone-do` | ❌ | ✅ | warning_only | json | 同上 | **D** |
| `voice-design` | ❌ | ✅ | warning_only | json | 同上 | **D** |
| `voice-delete` | ❌ | ✅ | warning_only | json | ⚠️ destructive，warning_only，TestConsole 可用 | **D** |

**A 类说明**：`voice-list → tts-sync` 形成完整链路，Runner 已验收。`tts-async` 通过 start/query 双模式实现异步任务提交与结果查询，无需自动轮询。

### 2.3 视觉（vision）

| capability_id | Runner? | TestConsole? | scope | result_type | 当前 UX 状态 | 分类 |
|--------------|---------|-------------|-------|-------------|-------------|------|
| `image-t2i` | ✅ | ✅ | in_scope | image | ✅ 已闭环：ResultBanner 单图展示 + AssetResultPreview + next_steps → image-i2i | **A** |
| `image-i2i` | ✅ | ✅ | in_scope | image | ✅ 已闭环：ImageComparePreview 对比展示（参考图 vs 生成图）+ skipPrimaryKinds 去重 | **A** |
| `video-t2v` | ❌ | ✅ | out_of_scope | — | ❌ out_of_scope，TestConsole 可用但不推荐进入 | **D** |
| `video-i2v` | ❌ | ✅ | out_of_scope | — | 同上 | **D** |
| `video-s2v` | ❌ | ✅ | out_of_scope | — | 同上 | **D** |
| `video-query` | ❌ | ✅ | out_of_scope | — | 同上 | **D** |
| `video-download` | ❌ | ✅ | out_of_scope | — | 同上 | **D** |

**A 类说明**：`image-t2i → image-i2i` 形成完整链路，Runner 已验收。视频 4 个 capability 均为 `out_of_scope`，不在本项目验收范围。

### 2.4 音乐（music）

| capability_id | Runner? | TestConsole? | scope | result_type | 当前 UX 状态 | 分类 |
|--------------|---------|-------------|-------|-------------|-------------|------|
| `lyrics-gen` | ✅ | ✅ | in_scope | text | ✅ 已闭环：ResultBanner 文本展示 + next_steps → music-gen | **A** |
| `music-gen` | ✅ | ✅ | in_scope | audio | ✅ 已闭环：AudioBanner 任务卡片（task 状态）+ AssetResultPreview skipAudioTaskCard + next_steps | **A** |
| `music-cover-prep` | ❌ | ✅ | warning_only | json | ⚠️ 翻唱预处理需音频素材授权，warning_only，TestConsole 可用 | **D** |

**A 类说明**：`lyrics-gen → music-gen` 形成完整链路，Runner 已验收。`music-gen` 的 task 状态（异步轮询）通过 `AudioTaskStatus` 专用卡片展示，不显示假播放器。

### 2.5 资产（files）

| capability_id | Runner? | TestConsole? | scope | result_type | 当前 UX 状态 | 分类 |
|--------------|---------|-------------|-------|-------------|-------------|------|
| `file-upload` | ✅ | ✅ | in_scope | file_upload | ✅ 已闭环：FileResultPreview + multipart 上传 + confirm_asset_source + next_steps → file-retrieve/content | **A** |
| `file-list` | ✅ | ✅ | in_scope | file_list | ✅ 已闭环：FileResultPreview 表格 + next_steps → file-retrieve/content | **A** |
| `file-retrieve` | ✅ | ✅ | in_scope | file_detail | ✅ 已闭环：FileResultPreview 元信息 + next_step → file-content | **A** |
| `file-content` | ✅ | ✅ | in_scope | file_content | ✅ 已闭环：FileResultPreview 文本预览（最多 3000 字）+ JSON 格式化 | **A** |
| `file-delete` | ❌ | ✅ | warning_only | json | ⚠️ destructive，warning_only，TestConsole 可用 | **D** |

**A 类说明**：文件链路已完整闭环：
- `file-upload` → `file-retrieve` / `file-content`：通过 next_steps handoff 传递 `file_id`
- `file-list` → `file-retrieve` / `file-content`：表格内按钮直接触发 handoff
- 上传安全约束：1MB 限制 + confirm_asset_source 确认

### 2.6 模型（models）

| capability_id | Runner? | TestConsole? | scope | result_type | 当前 UX 状态 | 分类 |
|--------------|---------|-------------|-------|-------------|-------------|------|
| `models-openai-list` | ❌ | ✅ | in_scope | json | ⚠️ 纯查询，TestConsole 可用；结果只显示 JSON，无模型卡片 | **B** |
| `models-openai-retrieve` | ❌ | ✅ | in_scope | json | ⚠️ 同上 | **B** |
| `models-anthropic-list` | ❌ | ✅ | in_scope | json | ⚠️ 同上 | **B** |
| `models-anthropic-retrieve` | ❌ | ✅ | in_scope | json | ⚠️ 同上 | **B** |

**B 类说明**：模型类能力为纯查询接口，只返回 JSON，无可视化资产，适合 TestConsole 不适合 Runner引导式体验。建议未来为 `models-openai-list` 和 `models-anthropic-list` 补专用结果卡片（模型列表表格）以提升体验。

---

## 3. A/B/C/D 分类汇总

### A 类：已闭环可体验（14 个）

```
✅ lyrics-gen       music-gen       voice-list
✅ tts-sync         image-t2i      image-i2i
✅ chat-openai      chat-anthropic   chat-responses-create
✅ file-upload     file-list      file-retrieve
✅ file-content    tts-async
```

特征：Runner 支持 + 表单完整 + 结果可视化展示 + next_steps 链路完整

### B 类：已验收未产品化（5 个）

```
chat-responses-tokens
models-openai-list  models-openai-retrieve
models-anthropic-list  models-anthropic-retrieve
```

特征：`in_scope` + 仅 TestConsole 可用 + 结果只显示 JSON

### C 类：仅高级测试（1 个）

```
tts-ws
```

特征：`in_scope` + 需要特殊 UI（WebSocket 事件流）

### D 类：风险 / 不默认执行（12 个）

```
voice-clone-upload-audio   voice-clone-upload-prompt   voice-clone-do
voice-design                voice-delete
music-cover-prep
video-t2v    video-i2v    video-s2v    video-query    video-download
file-delete
```

特征：`warning_only` / `out_of_scope` / `destructive`，只做风险提示和高级测试

---

## 4. 已闭环能力清单

### 4.1 Runner 支持的 14 个能力

| capability_id | result_type | 关键状态 |
|--------------|-------------|---------|
| `chat-openai` | chat | ✅ ChatResultPreview 统一展示（choices[].message.content） |
| `chat-anthropic` | chat | ✅ ChatResultPreview 统一展示（content[].text） |
| `chat-responses-create` | chat | ✅ ChatResultPreview 统一展示（output_text） |
| `voice-list` | json | ✅ VoiceListHint 音色卡片 + next_steps → tts-sync |
| `tts-sync` | audio | ✅ AudioBanner 播放器 + next_steps → voice-list |
| `tts-async` | async_task | ✅ AsyncTaskResultPreview + start/query 模式 + next_steps → self |
| `lyrics-gen` | text | ✅ ResultBanner 文本 + next_steps → music-gen |
| `music-gen` | audio | ✅ AudioBanner 任务卡片（task）+ skipAudioTaskCard |
| `image-t2i` | image | ✅ ResultBanner 单图 + next_steps → image-i2i |
| `image-i2i` | image | ✅ ImageComparePreview 对比（参考图 vs 生成图）+ skipPrimaryKinds |
| `file-upload` | file_upload | ✅ FileResultPreview + multipart 上传 + confirm_asset_source + next_steps → file-retrieve/content |
| `file-list` | file_list | ✅ FileResultPreview 表格 + next_steps → file-retrieve/content |
| `file-retrieve` | file_detail | ✅ FileResultPreview 元信息 + next_step → file-content |
| `file-content` | file_content | ✅ FileResultPreview 文本预览（最多 3000 字） |

### 4.2 跨能力链路

```
voice-list   → tts-sync       (音色选择 → 语音合成)       ✅ 双向 next_steps
lyrics-gen   → music-gen      (歌词 → 音乐生成)            ✅ 双向 next_steps
image-t2i    → image-i2i      (文生图 → 图生图)            ✅ 双向 next_steps
tts-async    → tts-async     (提交任务 → 查询结果)         ✅ self handoff（query 模式）
file-upload  → file-retrieve  → file-content              ✅ 链式 next_steps
file-upload  → file-content                            ✅ 链式 next_steps
file-list    → file-retrieve  / file-content             ✅ 表格内按钮 next_steps
```

---

## 5. 未闭环能力清单

| capability_id | 阻塞原因 | 建议 |
|--------------|---------|------|
| `chat-anthropic` | ✅ 已完成（2026-06-07 P1-3）：ChatResultPreview + Runner 模板 | ✅ 已完成 |
| `chat-responses-create` | ✅ 已完成（2026-06-07 P1-3）：ChatResultPreview + Runner 模板 | ✅ 已完成 |
| `chat-responses-tokens` | 纯计数，结果价值有限 | P2：考虑移除或标记为"仅调试" |
| `tts-ws` | WebSocket 事件流 UI 复杂，Runner 无状态管理 | P2：保留 TestConsole |
| `tts-async` | ✅ 已完成（2026-06-07 P1-2）：start/query 双模式 + AsyncTaskResultPreview | ✅ 已完成（P1-2） |
| `models-*` 全 4 个 | 纯 JSON 无资产，需专用模型卡片 | P2：补 ModelListPreview 表格卡片 |
| `voice-clone-*` 全 4 个 | warning_only，需要认证 + 素材授权 | P2：保留 TestConsole + 风险提示 |
| `voice-delete` | destructive，warning_only | P2：保留 TestConsole + 风险提示 |
| `music-cover-prep` | warning_only，需要音频素材授权 | P2：保留 TestConsole + 风险提示 |
| `video-*` 全 5 个 | out_of_scope，高成本异步任务 | P2：不做 Runner，保留 TestConsole 说明 |

---

## 6. 不建议进入 Runner 的能力清单

以下能力不应进入 Runner 主链路，只保留高级测试入口：

| capability_id | 原因 |
|--------------|------|
| `video-t2v / i2v / s2v / query / download` | out_of_scope，高成本，长时异步 |
| `voice-clone-do` | warning_only，需要认证 + 单独付费 |
| `voice-clone-upload-audio / prompt` | warning_only，素材授权风险 |
| `voice-design` | warning_only，单独付费 |
| `voice-delete` | destructive，warning_only |
| `file-delete` | destructive，warning_only |
| `music-cover-prep` | warning_only，素材授权风险 |

---

## 7. 需要真实 API Key 补票的能力清单

以下能力使用 TokenPlan 额度或单独计费，执行前需要 Key 补票提示：

| capability_id | 费用说明 |
|--------------|---------|
| `chat-openai / anthropic / responses-create` | TokenPlanPlus 共享配额 |
| `tts-sync` | TokenPlan 语音/字符额度 |
| `music-gen` | TokenPlan 音乐额度，Runner 有 confirm_quota 确认框 |
| `image-t2i / i2i` | TokenPlanPlus 共享配额 |
| `voice-clone-*` | 单独计费（9.9 元/音色），warning_only |
| `music-cover-prep` | 单独计费，warning_only |
| `video-*` | 高消耗，out_of_scope |

---

## 8. P0 / P1 / P2 修复建议

### P0（必须修复：用户误导性入口）

| # | 问题 | 修复 |
|---|------|------|
| P0-1 | 场景 `image_reference_variation` 的 CTA "开始体验" 链接 `image-i2i`，但 `image-i2i` 需要参考图 `img_url`。用户点进去不知道填什么 | 在 `image-i2i` Runner 表单上增加"从哪里获取参考图"的 hint 提示，链接回 `image-t2i` |
| P0-2 | 场景 `emotion_mv_music` 的 CTA "开始体验" 链接 `lyrics-gen`，但流程是 `lyrics-gen → music-gen`，缺少中间步骤引导 | 在 `lyrics-gen` Runner 结果页 next_steps 增加 music-gen 引导说明 |
| P0-3 | `chat-anthropic` 出现在能力画像"已验收能力"列表，但无 Runner 入口，只显示"暂无直接体验" | 能力画像中 `chat-anthropic` 的链接改为 `/test-console?capability=chat-anthropic`，不要链接到 Runner |
| P0-4 | `file_knowledge_entry` 场景的 CTA 显示"暂无直接体验入口"，因为 `file-upload` 不在 Runner 支持列表 | 场景页面 `file_knowledge_entry` 的 CTA 改为"高级测试 file-upload"，不要显示 disabled 按钮 |
| P0-5 | CapabilityWorkflows 中 non-Runner step 显示 disabled "去体验"，像坏了 | 改为"已验收，Runner 未产品化"（B/C 类）或"风险能力，不默认执行"（D 类） |

### P1-0（标签语义统一）

已废弃文案：`暂无直接体验`（2026-06-07 废弃）

标签语义对照表：

| 分类 | 标签 | 说明 |
|------|------|------|
| A 类（Runner 支持） | `可直接体验` | Runner 可用，无特殊确认 |
| A 类（Runner 支持，需额度） | `需额度确认` | music-gen 等需要 TokenPlan 额度确认 |
| A 类（Runner 支持，需图片来源） | `需图片来源确认` | image-i2i 需要参考图来源确认 |
| B 类（已验收未产品化） | `高级测试可用` | in_scope，TestConsole 可用，Runner 未产品化 |
| C 类（Runner 未产品化） | `Runner 未产品化` | 需要特殊 UI（WS/async/multipart） |
| D 类（风险能力） | `风险能力` | warning_only / destructive / out_of_scope |
| 未分类 | `仅详情说明` | 未在任何集合中，仅有详情页 |

相关集合：

- `RUNNER_SUPPORTED_CAPABILITIES`：A 类（lyrics-gen, music-gen, voice-list, tts-sync, tts-async, image-t2i, image-i2i, chat-openai, chat-anthropic, chat-responses-create, file-upload, file-list, file-retrieve, file-content）
- `QUOTA_SENSITIVE_CAPABILITIES`：A 类需额度（music-gen）
- `ASSET_GUARDED_CAPABILITIES`：A 类需图片来源（image-i2i）
- `ADVANCED_TEST_CAPABILITIES`：B 类（chat-responses-tokens, models-openai-list, models-openai-retrieve, models-anthropic-list, models-anthropic-retrieve）
- `RUNNER_NOT_PRODUCTIZED_CAPABILITIES`：C 类（tts-ws）
- `HIGH_RISK_CAPABILITIES`：D 类，包含以下子类：
  - video（out_of_scope）：video-t2v, video-i2v, video-s2v, video-query, video-download
  - voice clone/design（warning_only）：voice-clone-upload-audio, voice-clone-upload-prompt, voice-clone-do, voice-design, voice-delete
  - destructive：file-delete
  - music（warning_only）：music-cover-prep

### P1（产品化：补齐关键链路）

| # | 能力 | 修复方案 |
|---|------|---------|
| P1-1 | `tts-async` | ✅ 已完成（2026-06-07 P1-2）：start/query 双模式 + AsyncTaskResultPreview |
| P1-2 | `chat-anthropic` | ✅ 已完成（2026-06-07 P1-3）：ChatResultPreview 识别 content[].text + Runner 表单 |
| P1-3 | `chat-responses-create` | ✅ 已完成（2026-06-07 P1-3）：ChatResultPreview 识别 output_text + Runner 表单 |
| P1-4 | `models-openai-list / anthropic-list` | 补 ModelListPreview（模型卡片表格，含 model_id / context_window / capabilities），形成 `list → retrieve` 链路 |

### P2（优化体验）

| # | 能力 | 修复方案 |
|---|------|---------|
| P2-1 | `models-*` 全部 4 个 | 补 ModelDetailPreview（模型详情卡片，显示 context_window、supported_capabilities、official pricing） |
| P2-2 | `tts-ws` | 保留 TestConsole，Runner 暂不进入；补流式事件摘要展示（WebSocket 事件列表） |
| P2-3 | `voice-clone-*` / `voice-delete` / `music-cover-prep` | 完善 `warning_only` 页面说明，补充官方定价和认证要求说明 |
| P2-4 | `chat-responses-tokens` | 考虑从"已验收能力"列表移除（或标记为"仅调试"），因为纯计数接口对用户价值有限 |
| P2-5 | `video-*` 全部 5 个 | 在能力详情页 `/cap/video-t2v` 等增加 out_of_scope 说明，解释为何不在 Runner 中 |

---

## 9. 入口状态总览

| 页面 | 潜在误导问题 | 当前状态 |
|------|------------|---------|
| 能力画像 | `chat-anthropic` 等 B 类链接到 Runner 但无 Runner 入口 | ✅ 已修复（P1-3）：chat-anthropic / chat-responses-create 升为 A 类 |
| 场景推荐 | `image_reference_variation` → `image-i2i` 缺少参考图说明 | ⚠️ 需修复 |
| 场景推荐 | `emotion_mv_music` → `lyrics-gen` 缺少 music-gen 衔接说明 | ⚠️ 需修复 |
| 场景推荐 | `file_knowledge_entry` 显示 disabled CTA | ⚠️ 需修复 |
| 流程体验 | `file_knowledge` workflow 的 `file-upload` step 显示 disabled "去体验" | ⚠️ 需修复 |
| 流程体验 | `voice_generation` 的 `tts-async` step 显示 disabled "去体验" | ⚠️ 需修复 |

---

## 10. 本审计文档的检查规则

以下检查由 `scripts/check_workbench_capability_closure.py` 自动化：

1. registry 中所有 `in_scope` capability 都出现在本文档矩阵
2. Runner 支持能力（`RUNNER_SUPPORTED_CAPABILITIES`）都有 `capability_runner_templates.json` 中的 template
3. template 中 `result_type` 必须被 `ResultBanner` 或 `AssetResultPreview` 支持（text / audio / image / json）
4. `warning_only` / `out_of_scope` capability 不得出现在 `RUNNER_SUPPORTED_CAPABILITIES`
5. 需要 `operation_policy.requires_confirmation` 的能力必须有 RiskGate 确认字段
6. A 类能力必须有 result display 说明（已在矩阵中标注）
7. B/C/D 类能力必须有不进 Runner 的原因说明（已在矩阵中标注）

### P1-0 检查项（标签语义统一）

8. `getCapabilityTestabilityLabel` 不返回 `暂无直接体验`（已废弃）
9. `ADVANCED_TEST_CAPABILITIES` 集合存在
10. `RUNNER_NOT_PRODUCTIZED_CAPABILITIES` 集合存在
11. `chat-anthropic` 标签为"可直接体验"（A 类，2026-06-07 P1-3 完成）
12. `chat-responses-create` 标签为"可直接体验"（A 类，2026-06-07 P1-3 完成）
13. `file-list` 标签为"可直接体验"（A 类，2026-06-07 完成）
14. `tts-async` 标签为"可直接体验"（A 类，2026-06-07 完成）
15. `file-upload` 标签为"可直接体验"（A 类，2026-06-07 完成）
16. `file-delete` 不显示"高级测试可用"（D 类：风险能力）
17. `voice-delete` 不显示"高级测试可用"（D 类：风险能力）
18. `music-gen` 仍显示"需额度确认"
19. `image-i2i` 仍显示"需图片来源确认"
20. `voice-clone-upload-audio` 为"风险能力"（D 类）
21. `voice-clone-upload-prompt` 为"风险能力"（D 类）
22. `voice-clone-do` 为"风险能力"（D 类）
23. `voice-design` 为"风险能力"（D 类）
24. `music-cover-prep` 为"风险能力"（D 类）
25. `video-t2v` 为"风险能力"（D 类）
26. `video-download` 为"风险能力"（D 类）
