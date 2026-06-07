# Result Experience Audit

## 1. 组件职责边界

| 组件 | 职责 | 渲染位置 |
|------|------|---------|
| `ResultBanner` | 主结果体验：音频播放器（含错误处理）、图片预览（含i2i对比）、voice_list、text、chat banner | `InvokeResultView` 顶部 |
| `AssetResultPreview` | 补充资产提取 + 完整 JSON：音频/图片/file 资产卡片；任务状态卡片；JSON 折叠区 | `InvokeResultView` 底部 |
| `HistoryAssetPreview` | 历史记录资产回看（预留，当前未实现） | — |

**原则**：`ResultBanner` 负责主视觉，`AssetResultPreview` 负责补充资产和完整 JSON，不重复渲染同一内容。

---

## 2. image-t2i 当前展示

- `ResultBanner` (`resultType === 'image'`) 渲染单图：图片 + 复制 URL + 打开链接
- `AssetResultPreview` 底部折叠展示完整 JSON
- 无对比体验

---

## 3. image-i2i 参考图 vs 生成图对比（已修复）

**新增组件**：`ImageComparePreview`（`CapabilityRunner.tsx` 内部）

**渲染条件**：`resultType === 'image'` 且 `template.capability_id === 'image-i2i'` 且 `values.img_url` 有值

**布局**：两列对比（桌面端）/ 上下排列（窄屏）

| 左侧 | 右侧 |
|------|------|
| 参考图（`values.img_url`） | 生成图（`extractImageUrl(data)`） |
| 复制参考图 URL | 复制生成图 URL |
| 打开参考图 | 打开生成图 |

**边界提示**：
- 未识别到参考图 URL：amber 提示「未识别到参考图 URL，请检查 img_url 或完整 JSON」
- 未识别到生成图 URL：显示「未识别到生成图 URL，请查看完整 JSON」

---

## 4. tts-sync 音频播放

**提取字段**：`audio_url`、`voice_url`、`speech_url`、`url`、`audio_file`、`music_url`

**格式支持**：
- HTTP/HTTPS URL → `kind: 'url'`
- `data:audio/` → `kind: 'data_url'`
- 有效 base64（>50 字符，仅 A-Za-z0-9+/=）→ `kind: 'base64'`
- 有效 hex（MP3/WAV 魔数开头）→ `kind: 'hex'`，转为 Blob URL

**错误处理**：
- `onLoadedMetadata`: duration 为 0 或 NaN → 显示错误提示
- `onError`: 显示「浏览器未能解析该音频」
- 错误提示文案：「浏览器未能解析该音频。可能是编码格式不支持，或接口返回的不是最终音频文件。」

**Blob 生命周期**：`hex` / `base64` 在 `useEffect` 中创建 `URL.createObjectURL`，组件 unmount 时 `URL.revokeObjectURL`

---

## 5. music-gen 音频播放 / 状态型结果（已修复）

### 情况 A：返回可播放音频

**识别字段**：同 tts-sync，额外支持 `music_url`

**体验**：同 tts-sync 音频播放器

### 情况 B：只返回 status / extra_info（任务状态）

**识别逻辑**：当没有 URL/base64/hex 字段，但有 `status` + `extra_info` 时，返回 `kind: 'task'`

**显示内容**（橙色任务状态卡片）：
```
🎵 音乐生成任务状态
[status_msg 或 "任务已完成，请查询结果"]
时长：169.1 秒
采样率：44100 Hz
声道：立体声
文件大小：5.16 MB
当前响应未包含可直接播放的音频数据。状态 N 表示任务已提交，请通过结果查询接口获取音频。
```

**格式化规则**：
- `music_duration`（毫秒）→ 秒，保留 1 位小数
- `music_size`（字节）→ MB，保留 2 位小数（>1MB 时）

### 情况 C：播放失败（已修复）

**识别**：所有音频类型（url/data_url/base64/hex）在 `onLoadedMetadata` 或 `onError` 时 duration 为 0/NaN

**显示**：
```
浏览器未能解析该音频。可能是编码格式不支持，或接口返回的不是最终音频文件。
```

**不再显示**：`0:00 / 0:00` 假播放器

---

## 6. lyrics-gen 文本展示与 handoff

**ResultBanner**：`resultType === 'text'` 显示绿色「📝 文本结果」banner

**AssetResultPreview**：通过 `extractTextResult` 搜索 `lyrics` / `text` / `content` / `output` / `answer` / `message` 字段提取文本（最多 300 字符），展示为 JSON 树

**handoff**：`InvokeResultView` 检测 `resultType === 'text' && template.next_steps` 有 `music-gen` 时，提取歌词并显示「用这段歌词生成音乐」按钮

**当前问题**：MiniMax `/lyrics_generation` 真实响应字段名未确认，`extractTextResult` 可能无法提取歌词

---

## 7. chat-openai 回复展示

**ResultBanner**：`resultType === 'chat'` 显示蓝色「💬 模型回复」banner

**AssetResultPreview**：将对话内容展示为 JSON 树或文本（由后端返回格式决定）

**next_steps**：`chat-openai` 模板 `next_steps: []`，无下一步，自然结束

---

## 8. 本轮修复总结

| 问题 | 修复 |
|------|------|
| image-i2i 无参考图对比 | 新增 `ImageComparePreview` 组件，桌面端左右对比，窄屏上下排列 |
| music-gen 假播放器（0:00/0:00） | `extractAudioSource` 统一至 `assetResultUtils`；`status` + `extra_info` 识别为 `kind: 'task'`，不显示播放器 |
| base64 误判（长字符串字段被当音频） | base64 必须匹配 `/^[A-Za-z0-9+/=]{50,}$/` 才认为是音频 |
| hex 格式支持 | 验证 hex 格式 + MP3/WAV 魔数，才转为 Blob URL |
| audio `onError` 无提示 | 添加 `onLoadedMetadata` / `onError` 错误提示 |
| ResultBanner 无模板上下文 | `InvokeResultView` 传递 `template` + `values` 到 `ResultBanner` |
