# Frontend UI Flow Audit

## 1. 页面清单与定位

| 路径 | 页面 | 定位 |
|------|------|------|
| `/` | 总览 | 首页，展示统计摘要和快速入口 |
| `/category/:id` | 分类能力页 | 按 category 过滤能力列表 |
| `/cap/:id` | 单能力详情页 | 显示能力说明、模型、计费、风险 |
| `/models-all` | 所有模型页 | 全量模型清单，含验证状态 |
| `/capability-profiles` | 能力画像页 | 按 family(voice/chat/vision/music) 展示能力族全貌 |
| `/capability-scenarios` | 场景推荐页 | 从用户目标出发推荐能力链路 |
| `/capability-workflows` | 流程体验页 | 按步骤执行能力调用的完整链路 |
| `/capability-runner` | 能力体验 Runner | 引导式能力链，handoff 支持 |
| `/test-console` | 高级测试台 | 开发者调试 Risk Check / Invoke |

---

## 2. UI 链路矩阵

### `/` (总览)
| 控件 | 当前行为 | 目标行为 | 跳转 URL | query 参数 | 状态 |
|------|---------|---------|---------|-----------|------|
| 快速入口-能力体验 | ✅ 已存在 | 保持 | /capability-runner | — | OK |
| 快速入口-模型清单 | ✅ 已存在 | 保持 | /models-all | — | OK |
| 快速入口-场景推荐 | ✅ 已存在 | 保持 | /capability-scenarios | — | OK |
| 快速入口-流程体验 | ✅ 已存在 | 保持 | /capability-workflows | — | OK |
| 快速入口-能力画像 | ✅ 已存在 | 保持 | /capability-profiles | — | OK |

### `/models-all`
| 控件 | 当前行为 | 目标行为 | 跳转 URL | query 参数 | 状态 |
|------|---------|---------|---------|-----------|------|
| 官方当前-模型行 | 无动作 | 显示"能力说明/开始体验/高级测试" | 按 family | — | **Broken** |
| 历史兼容-模型行 | 无动作 | 同上 | 按 family | — | **Broken** |
| 筛选器 | ✅ 工作正常 | 保持 | — | — | OK |

### `/capability-profiles`
| 控件 | 当前行为 | 目标行为 | 跳转 URL | query 参数 | 状态 |
|------|---------|---------|---------|-----------|------|
| 推荐流程 | ✅ 跳转 workflows | 保持 | /capability-workflows?workflow=xxx | ✅ | OK |
| 推荐场景 | ❌ 无此链接 | 应跳转场景 | /capability-scenarios?scenario=xxx | **Missing** | **Broken** |
| 已验收能力 | ❌ 无此链接 | 应跳转 Runner 或说明 | /capability-runner?capability=xxx | ✅ | **Broken** |
| 风险提示能力 | ❌ 无此链接 | 应跳转说明或测试台 | /cap/xxx 或 /test-console | **Missing** | **Broken** |
| 模型建议 | ❌ 无此链接 | 应跳转模型页筛选该模型 | /models-all?search=xxx | **Missing** | **Broken** |
| family query 参数 | ❌ 不支持 | 应支持 ?family=voice 选中某族 | — | **Missing** | **Broken** |

### `/capability-scenarios`
| 控件 | 当前行为 | 目标行为 | 跳转 URL | query 参数 | 状态 |
|------|---------|---------|---------|-----------|------|
| 开始体验 | 随机选一个 capability 跳转 | 应选 primary 可体验能力 | /capability-runner?capability=xxx | ✅ | **Broken** |
| 查看流程 | ✅ 跳转 workflow | 保持 | /capability-workflows?workflow=xxx | ✅ | OK |
| 涉及能力标签 | ✅ 跳转 Runner | 保持 | /capability-runner?capability=xxx | ✅ | OK |
| 模拟链路展示 | ❌ 不存在 | 应显示能力链可体验性 | — | — | **Missing** |

### `/capability-workflows`
| 控件 | 当前行为 | 目标行为 | 跳转 URL | query 参数 | 状态 |
|------|---------|---------|---------|-----------|------|
| 流程卡片-查看详情 | ✅ 跳转 workflow detail | 保持 | /capability-workflows?workflow=xxx | ✅ | OK |
| 步骤-去体验 | ✅ 跳转 Runner | 保持 | /capability-runner?capability=xxx | ✅ | OK |
| 步骤-高级测试 | ✅ 跳转 test-console | 保持 | /test-console?capability=xxx | ✅ | OK |
| 步骤-能力说明 | ❌ 不存在 | 应跳转 /cap/xxx | /cap/xxx | **Missing** | **Broken** |
| 步骤-Runner 跳转 | 仅 capability 类型 | 应按 risk_level 判断 | — | — | **Needs UX** |
| 步骤-risk level 标签 | ✅ 显示 | 保持 | — | — | OK |

### `/capability-runner`
| 控件 | 当前行为 | 目标行为 | 跳转 URL | query 参数 | 状态 |
|------|---------|---------|---------|-----------|------|
| 能力选择卡片 | ✅ 工作正常 | 保持 | — | ✅ | OK |
| voice-list → tts-sync | ✅ handoff voice_id | 保持 | — | ✅ | OK |
| lyrics-gen → music-gen | ✅ handoff lyrics | 保持 | — | ✅ | OK |
| image-t2i → image-i2i | ✅ handoff img_url | 保持 | — | ✅ | OK |
| 业务错误渲染 | ✅ 隐藏结果区 | 保持 | — | — | OK |
| hooks 调用顺序 | ✅ 已修复 | 保持 | — | — | OK |
| handoff 可见提示 | ✅ 显示带入字段 | 保持 | — | — | OK |
| 复制反馈 | ✅ 有成功/失败提示 | 保持 | — | — | OK |

### `/test-console`
| 控件 | 当前行为 | 目标行为 | 跳转 URL | query 参数 | 状态 |
|------|---------|---------|---------|-----------|------|
| 高级测试台提示 | ✅ 已存在 | 保持 | — | — | OK |
| 返回能力体验链接 | ✅ 已存在 | 保持 | /capability-runner | ✅ | OK |
| 能力说明链接 | ✅ 显示在面板中 | 保持 | — | — | OK |
| 去用户体验 | ✅ 已存在 | 保持 | /capability-runner?capability=xxx | ✅ | OK |

---

## 3. 已知问题汇总

### P0 — 必须修复
1. **Models.tsx 无动作入口**：每行模型没有"能力说明/开始体验/高级测试"链接
2. **场景推荐开始体验失效**：music-gen / image-i2i 等 guarded 能力不在 RUNNER_SUPPORTED 列表中
3. **能力画像无推荐场景跳转**：recommended_scenarios 无链接
4. **能力画像无推荐流程跳转**（仅推荐流程有，场景缺失）
5. **流程体验无能力说明链接**：每个步骤没有"能力说明"按钮
6. **能力画像不支持 family query**：不支持按 family 过滤

### P1 — 应修复
1. **Models.tsx 无 family query**：无法从能力画像直接链接到某 family 的模型
2. **场景推荐缺少模拟链路展示**：用户不知道哪步可体验哪步需确认

---

## 4. 本轮修复范围

- [x] 新增 `docs/FRONTEND_UI_FLOW_AUDIT.md`
- [x] 新增 `frontend/src/navigation/capabilityLinks.ts` 统一链接规则
- [x] 修复 Models.tsx：增加 Actions 列（能力说明/开始体验/高级测试）
- [x] 修复 CapabilityScenarios.tsx：修复"开始体验"选取 primary，添加模拟链路
- [x] 修复 CapabilityWorkflows.tsx：增加"能力说明"按钮
- [x] 修复 CapabilityProfiles.tsx：支持 family query，补全推荐场景/流程/可体验能力链接
- [x] TestConsole.tsx：已包含高级测试提示，无需修改
- [x] 新增 `scripts/check_frontend_ui_links.py`

---

## 5. 暂不修范围

- 不新增新 capability
- 不做 file-upload / tts-async / video / clone / delete
- 不做总览页改造
- 不做 category 页改造
- 不做单能力详情页（/cap/:id）改造
