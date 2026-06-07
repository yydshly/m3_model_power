# Frontend Flow Closure Audit

## 1. 页面关系图

```
/capability-profiles        — 能力画像，按 family 展示全貌
       ↓ recommended_workflows
/capability-workflows       — 流程体验，按步骤执行
       ↓ from_workflow param
/capability-runner          — 能力体验，handoff 支持
       ↓
/test-console               — 高级测试，开发者调试
```

### 页面职责

| 页面 | 职责 | 关键 URL 参数 |
|------|------|--------------|
| `/capability-profiles` | 展示能力族全貌、推荐流程入口 | `?family=voice\|music\|vision\|chat` |
| `/capability-workflows` | 展示步骤化流程，「去体验」带 `from_workflow` | `?workflow=voice_generation` |
| `/capability-scenarios` | 从目标出发推荐链路，「开始体验」带 `from_scenario` | `?scenario=xxx` |
| `/capability-runner` | 引导式体验，handoff 参数带入，显示 `from_workflow`/`from_scenario` 上下文 | `?capability=voice-list&from_workflow=xxx` |
| `/test-console` | 开发者调试 Risk Check / Invoke | `?capability=xxx` |

---

## 2. 主链路当前状态

### 2.1 voice-list → tts-sync ✅ 可闭环

| 步骤 | 组件 | 状态 | 说明 |
|------|------|------|------|
| voice-list 执行 | `CapabilityCard` | ✅ | `result_type: voice_list` |
| 音色列表解析 | `extractVoiceIds` | ✅ | 支持 `system_voice` / `voices` / `voice_list` / `items` |
| voice_name 显示 | `VoiceListHint` | ✅ | 优先 `voice_name` > `name` |
| per-voice 带入 | `VoiceListHint.onUseVoiceId` | ✅ | `onChain('tts-sync', { voice_id: vid })` |
| 下一步建议按钮 | `InvokeResultView` next_steps | ✅ | 始终显示「建议下一步：tts-sync」 |
| tts-sync 带入 voice_id | sessionStorage handoff | ✅ | `loadHandoff` → `saveHandoff` |
| 额度确认 | `getExecutionDisabled` | ✅ | tts-sync 无需确认 |
| 前端 extractor | `extractVoiceIds` | ✅ | 最多 30 项，每项含 `voice_id` + `name` |

**本轮修复**: `extractVoiceIds` 已支持 `system_voice` 和 `voice_name`；`InvokeResultView` 始终显示 tts-sync 下一步建议。

---

### 2.2 lyrics-gen → music-gen ✅ 可闭环

| 步骤 | 组件 | 状态 | 说明 |
|------|------|------|------|
| lyrics-gen 执行 | `CapabilityCard` | ✅ | `result_type: text` |
| 歌词提取 | `extractTextResult` | ✅ | 搜索 `lyrics` / `text` / `content` 等字段 |
| 下一步按钮 | `InvokeResultView` next_steps | ✅ | `template.next_steps` 含 `music-gen` |
| music-gen 带入 lyrics | `onChain('music-gen', { lyrics })` | ✅ | handoff via sessionStorage |
| confirm_quota 确认 | `getExecutionDisabled` | ✅ | 需勾选确认框方可执行 |
| 模板 handoff 声明 | `capability_runner_templates.json` | ✅ | `lyrics-gen.next_steps[0].handoff.lyrics` |

**当前问题**: MiniMax `/lyrics_generation` 真实响应字段名未确认，本轮未修改。

---

### 2.3 image-t2i → image-i2i ✅ 可闭环

| 步骤 | 组件 | 状态 | 说明 |
|------|------|------|------|
| image-t2i 执行 | `CapabilityCard` | ✅ | `result_type: image` |
| 图片 URL 提取 | `extractImageUrl` | ✅ | 支持 `image_url` / `img_url` / `file_url` 等 |
| 下一步按钮 | `InvokeResultView` next_steps | ✅ | `template.next_steps` 含 `image-i2i` |
| image-i2i 带入 img_url | `onChain('image-i2i', { img_url })` | ✅ | handoff via sessionStorage |
| confirm_asset_source 确认 | `getExecutionDisabled` | ✅ | 需勾选确认框方可执行 |
| 模板 handoff 声明 | `capability_runner_templates.json` | ✅ | `image-t2i.next_steps[0].handoff.img_url` |

---

### 2.4 chat-openai 单点体验 ✅ 可用

| 步骤 | 组件 | 状态 | 说明 |
|------|------|------|------|
| chat-openai 执行 | `CapabilityCard` | ✅ | `result_type: chat` |
| 回复展示 | `ResultBanner` | ✅ | 显示「💬 模型回复」banner |
| 资产预览 | `AssetResultPreview` | ✅ | JSON 树状展开 |
| next_steps | 模板定义 | ✅ | `next_steps: []`（无下一步，自然结束） |

---

## 3. 本轮修复项

| 修复项 | 文件 | 状态 |
|--------|------|------|
| `extractVoiceIds` 支持 `system_voice` | `CapabilityRunner.tsx` | ✅ 已修复 |
| `extractVoiceIds` 支持 `voice_name` | `CapabilityRunner.tsx` | ✅ 已修复 |
| `VoiceListHint` 显示 name 优先于 voice_id | `CapabilityRunner.tsx` | ✅ 已修复 |
| `VoiceListHint` 解析失败时显示 amber 提示 | `CapabilityRunner.tsx` | ✅ 已修复 |
| voice-list `next_steps` 添加 `handoff.voice_id` | `capability_runner_templates.json` | ✅ 已修复 |
| `InvokeResultView` 始终显示「建议下一步：tts-sync」 | `CapabilityRunner.tsx` | ✅ 已修复 |
| `from_workflow` 上下文在 Runner 顶部显示 | `CapabilityRunner.tsx` | ✅ 已修复 |
| `from_scenario` 上下文在 Runner 顶部显示 | `CapabilityRunner.tsx` | ✅ 已修复 |

---

## 4. 仍未产品化的边界

### 4.1 lyrics-gen 字段名未确认
MiniMax `/lyrics_generation` 真实响应字段名未确认，`extractTextResult` 可能无法正确提取歌词，导致 music-gen 带入失败。

**影响**: 用户需手动复制歌词粘贴到 music-gen。

**建议**: 接入真实 API Key 后确认响应字段。

### 4.2 voice-list 无真实 API 验证
`extractVoiceIds` 在前端解析 MiniMax 响应，若响应结构与预期不符（如字段名变化），用户看到的是 amber 提示而非直接失败。

**建议**: 定期巡检 `extractVoiceIds` 与真实 API 响应的一致性。

### 4.3 workflow state 未持久化
`from_workflow` 仅通过 URL 参数传递，刷新页面后丢失。Runner 内无「返回流程」按钮。

**建议**: 可在 sessionStorage 中暂存 `current_workflow` 状态。

### 4.4 场景页与 profile 页入口重复
`recommended_scenarios` 和 `recommended_workflows` 在 profile 页展示，但场景页 `CapabilityScenarios` 也有独立入口，存在信息重复。

---

## 5. 快速验证清单

启动后端和前端后，依次验证：

```
[ ] /capability-profiles?family=voice
    → 点击 voice-list「直接体验」
    → 执行 voice-list 查询
    → 页面显示 system_voice 音色卡片（name + voice_id）
    → 点击「用此音色合成」
    → 跳转 tts-sync，voice_id 已自动填入
    → 输入文本，执行 TTS

[ ] /capability-profiles?family=music
    → 点击 lyrics-gen「直接体验」
    → 执行 lyrics-gen
    → 点击「用这段歌词生成音乐」
    → 跳转 music-gen，lyrics 已带入（如识别成功）

[ ] /capability-profiles?family=vision
    → 点击 image-t2i「直接体验」
    → 执行 image-t2i
    → 点击「用此图片做图生图」
    → 跳转 image-i2i，img_url 已带入

[ ] /capability-profiles?family=chat
    → 点击 chat-openai「直接体验」
    → 执行 chat-openai
    → 页面显示模型回复 banner
```
