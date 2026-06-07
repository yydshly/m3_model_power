# Runner Bug Triage

## 1. 当前 Runner 目标

为 `/capability-runner` 页面提供"引导式能力链"体验：
用户完成一个能力后，可将结果无缝带入下一个相关能力，形成连续体验链。

## 2. 当前已支持能力

| 能力 | Result Type | 下一步 |
|------|-------------|--------|
| voice-list | voice_list | tts-sync |
| lyrics-gen | text | music-gen |
| image-t2i | image | image-i2i |
| tts-sync | audio | — |
| music-gen | audio | — |
| image-i2i | image | — |
| chat-openai | chat | — |

## 3. 当前已知问题

### P0 — 必须在本轮修复

- **CapabilityRunnerPage hooks 调用顺序风险**：`useEffect` 放在条件 return 之后，违反 React 规则
- **业务错误仍渲染结果区**：当 `base_resp.status_code != 0` 时，仍显示 ResultBanner、链路按钮和"执行完成"
- **buildPayload 不是真正递归**：只处理固定层级，深层嵌套（如 `audio_setting.sample_rate`）无法正确替换
- **handoff 缺少可见状态**：用户不知道哪些字段是从上一步带入的，也无法清除

### P1 — 尽快修复

- **voice-list/image/audio 结果提取未经验证**：依赖真实 API 返回结构，嵌套路径未充分测试
- **复制操作无反馈**：`navigator.clipboard.writeText` 无成功/失败提示
- **guarded 能力风险提示不够明显**：music-gen/image-i2i 的确认勾选提示可以更清晰

### P2 — 后续迭代

- **CapabilityRunner.tsx 文件过大**：1500+ 行，建议拆分为多个子组件/工具模块
- **缺少 Runner 工具函数单测**：extractors、buildPayload 等核心函数应有一测覆盖

## 4. P0 / P1 / P2 问题分级

| 级别 | 问题 | 状态 |
|------|------|------|
| P0 | hooks 顺序风险 | 本轮修复 |
| P0 | 业务错误仍渲染结果 | 本轮修复 |
| P0 | buildPayload 非递归 | 本轮修复 |
| P0 | handoff 无可见状态 | 本轮修复 |
| P1 | 结果提取未验证 | 暂不修（需真实 API） |
| P1 | 复制无反馈 | 本轮修复 |
| P1 | guarded 提示不够明显 | 本轮修复 |
| P2 | 文件过大 | 暂不修 |
| P2 | 缺少单测 | 暂不修 |

## 5. 本轮修复范围

- 新增 `docs/RUNNER_BUG_TRIAGE.md`（本文档）
- 修复 hooks 调用顺序（拆分子组件方案）
- 修复业务错误时隐藏结果区
- buildPayload 改为通用递归 `resolveTemplateValue`
- handoff 字段可见提示 + 清除按钮
- 复制操作增加反馈提示
- 加强 music-gen / image-i2i 风险提示

## 6. 暂不修范围

- 不新增 capability
- 不做 tts-async / file-upload / video / clone / delete
- 不重构整个前端目录
- 不添加单测（本轮）
- 不做真实 API 调用验证

## 7. PR 前验收标准

### 功能验收
- [ ] `/capability-runner` 页面无 React hooks 警告/错误
- [ ] `voice-list` 结果中 voice_id 正确提取并显示
- [ ] 点击"用此音色合成"进入 tts-sync，voice_id 正确带入
- [ ] URL 参数 `?voice_id=xxx` 带入 tts-sync 表单
- [ ] 页面显示"已从上一步带入 voice_id / lyrics / img_url"提示
- [ ] 清除按钮可清空带入字段
- [ ] music-gen 未勾选 confirm_quota 时按钮 disabled
- [ ] image-i2i 未勾选 confirm_asset_source 时按钮 disabled
- [ ] music-gen/image-i2i 勾选后提示变为"已确认，可执行"
- [ ] 业务错误时页面不显示 ResultBanner / 链路按钮 / "执行完成"
- [ ] 业务错误时展示完整 JSON
- [ ] 复制 voice_id / image URL 后显示"复制成功"提示
- [ ] `buildPayload` 能正确处理嵌套对象（`subject_reference[].image_file`）
- [ ] `buildPayload` 能正确转换类型（boolean、number）

### 技术验收
- [ ] `npm run build` 通过
- [ ] `python -m compileall backend/app` 通过
- [ ] 所有 `check_*.py` 脚本通过
- [ ] `git status --short` 无多余文件
