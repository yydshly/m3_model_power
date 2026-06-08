# MiniMax Token Plan 产品化工作台阶段完成报告

> 归档日期：2026/06/08
> 分支：main（已合并 PR #10、#11、#12）

---

## 1. 当前结论

m3_model_power 已从「能力验收脚本 / API 探测工具」演进为：

- **MiniMax Token Plan 能力验收工具** — 32 个能力登记，20 个 in_scope 全部验收
- **MiniMax 能力调用与风险控制底座** — RiskGate + 7 类确认项 + 统一响应结构
- **可视化能力测试控制台** — Test Console / Capability Runner 双入口
- **产品化 MiniMax 工作台首页** — Overview + 分组导航 + 行动卡
- **历史记录与资产预览系统** — 调用历史、duration_ms、资产摘要、结果折叠
- **Demo Payload 与费用说明** — 自动填充模板 + UsageCostExplainer
- **支持场景推荐、流程体验、能力画像的体验系统**

---

## 2. 阶段完成范围

### 2.1 已完成能力验收

| 指标 | 状态 |
|---|---|
| Registry 总能力 | 32 |
| in_scope 能力 | 20 / 20 verified |
| in_scope 能力说明 | 20 / 20 described |
| warning_only 能力 | 7（保留风险提示，不默认执行） |
| out_of_scope 能力 | 5（视频生成，不纳入） |
| RiskGate | ✅ 已建立 |
| Verification Index | ✅ 已建立 |
| 能力矩阵 | ✅ 已建立 |

### 2.2 PR #10：调用历史与资产结果

**合并 commit：** `3934eed Merge pull request #10 from yydshly/feature/invocation-history-and-assets`

主要实现：

- **duration_ms 写入 invocation history**：后端 `invoke.py` / `risk_check.py` 使用 `time.perf_counter()` 计时，结果写入 `history_store.py` 的 `append_history`，记录结构含 `duration_ms` 字段
- **资产提取函数**：后端 `history_store.py` 含 `_collect_assets`（图片 / 音频 / 文件分类提取）、`_is_sensitive_key`（敏感字段检测）、`summarize_result`（结果摘要）、`summarize_payload`（payload 脱敏）
- **HistoryAssetPreview 组件**：前端展示图片 URL（强制预览）、音频 URL（audio controls）、文件类结果（文件信息卡片）
- **InvocationHistoryPanel 组件**：复用至 Test Console 和 Capability Runner，包含「调试信息」折叠区块
- **Capability Runner 接入 history**：CapabilityRunner.tsx 使用 `getCapabilityHistory` API + `InvocationHistoryPanel` 组件
- **Test Console 调试信息折叠**：主 UI 不直接暴露 `history.jsonl` / `blocked_reasons` / `required_confirmations`

相关文件：
- `backend/app/minimax_core/verification/history_store.py`
- `backend/app/routers/invoke.py`
- `backend/app/routers/risk_check.py`
- `frontend/src/components/HistoryAssetPreview.tsx`
- `frontend/src/components/InvocationHistoryPanel.tsx`
- `frontend/src/components/AssetResultPreview.tsx`
- `frontend/src/components/assetResultUtils.ts`

### 2.3 PR #11：高级测试产品化

**合并 commit：** `eb46f77 Merge pull request #11 from yydshly/feature/productize-test-console-and-usage`

主要实现：

- **getCapabilityHistory 后端过滤**：后端 `history.py` 提供 `/api/history/capability/{capability_id}` 端点，按 capability_id 过滤历史记录，不再依赖前端过滤
- **UsageCostExplainer 组件**：说明 Token / 额度 / 费用关系，解释账单消耗估算逻辑
- **demo payload 自动填充**：Test Console 加载能力时自动使用 `buildDemoPayload` 模板
- **buildDemoPayload 模板变量解析**：支持 `{{ random_int }}`、`{{ timestamp }}`、`{{ model_name }}` 等变量，使用 `resolveTemplateValue` 递归解析
- **music-gen 示例歌词**：demo payload 包含默认歌词（非空字符串），避免生成失败
- **chat-responses-tokens demo payload**：包含 `input` 字段（非空 `{}`）
- **music-01 → music-2.6 修正**：demo payload 不再使用已下线模型名
- **speech-02 → speech-02-turbo 修正**：demo payload 使用完整模型名
- **Test Console sticky 筛选**：能力筛选状态在会话内保持
- **Runner 轻量草稿保存**：记录上一次 payload 模板变量值，支持会话恢复（不做完整 Run Session 恢复）

相关文件：
- `backend/app/routers/history.py`
- `frontend/src/components/UsageCostExplainer.tsx`
- `frontend/src/domain/demoPayload.ts`
- `frontend/src/pages/TestConsole.tsx`

### 2.4 PR #12：Overview 与导航产品化

**合并 commit：** `98248fb Merge pull request #12 from yydshly/feature/overview-navigation-productization`

主要实现：

- **Overview 首页重构**：全新 Overview.tsx，移除个人套餐续费时间 / 年度会员等硬编码信息
- **左侧导航分组**：主工作台 / 能力应用 / 能力目录 / 开发者 四组
  - 主工作台：首页概览
  - 能力应用：场景推荐、流程体验、能力画像
  - 能力目录：全部能力、分类浏览
  - 开发者：高级测试（Test Console）
- **我想做什么入口卡片**：首页行动卡，引导用户选择能力场景
- **最近调用概览**：展示本次会话最近的调用记录（使用 `getTestConsoleHistory` API）
- **风险说明卡**：说明高成本 / 素材型 / 删除型能力需要显式确认
- **高级诊断折叠**：展示 capability Probe / enabled / official_current 等内部状态（折叠在详情区）
- **OverviewRecentHistory 使用 Link**：不直接使用 `href`，使用 React Router `Link` 组件

相关文件：
- `frontend/src/pages/Overview.tsx`
- `frontend/src/navigation/workbenchNav.ts`
- `frontend/src/components/overview/OverviewRecentHistory.tsx`
- `frontend/src/components/overview/OverviewDiagnostics.tsx`

---

## 3. 当前产品形态

### 3.1 页面清单

| 页面 | 路由 | 目标用户 | 主要任务 | 当前状态 | 面向开发者 |
|---|---|---|---|---|---|
| 工作台首页 | `/` | 所有用户 | 了解能力入口、查看最近调用、风险说明 | ✅ 产品化 | 否 |
| 能力体验 | `/capability-runner` | 能力探索者 | 选择能力、构建 payload、执行调用 | ✅ 产品化 | 部分 |
| 高级测试 | `/test-console` | 开发者 | 调试能力、查看历史、执行 Risk Check | ✅ 产品化 | 是 |
| 场景推荐 | `/capability-scenarios` | 业务人员 | 按场景查找可用能力 | ✅ 可用 | 否 |
| 流程体验 | `/capability-workflows` | 探索者 | 按工作流体验能力组合 | ✅ 可用 | 否 |
| 能力画像 | `/capability-profiles` | 分析人员 | 查看能力详情与计费说明 | ✅ 可用 | 否 |
| 模型目录 | `/models-all` | 开发者 | 查看所有可用模型与状态 | ✅ 可用 | 是 |
| 能力分类页 | `/category/:id` | 所有用户 | 浏览特定分类下的能力 | ✅ 可用 | 否 |
| 能力详情页 | `/cap/:id` | 所有用户 | 查看单个能力详情与说明 | ✅ 可用 | 否 |

---

## 4. 核心产品能力

| 能力 | 说明 |
|---|---|
| **能力 Registry** | YAML 驱动，32 个能力，动态渲染目录，含 status / scope / billing / risk 字段 |
| **模型 Registry** | 三态模型状态（official_current / live_available / subscription_expected） |
| **RiskGate** | 7 类确认项（quota / asset_source / existing_task / long_running / paid / high_cost / destructive） |
| **UnifiedResponse / AssetRef** | 统一响应结构，含 `result` / `result_summary` / `assets` 字段 |
| **Verification Index** | 验收状态索引，可按 capability_id 查询 |
| **Invocation History** | 含 capability_id / action / status / result_summary / duration_ms，写入 `history.jsonl` |
| **Asset Preview** | HistoryAssetPreview / AssetResultPreview，支持图片强制预览、音频 controls、文件信息卡片 |
| **Demo Payload** | `buildDemoPayload` 模板变量解析，自动填充测试 payload |
| **UsageCostExplainer** | 说明 Token / 额度 / 费用关系，不做精确账单计算 |
| **Runner Session Draft** | 轻量草稿保存（不做完整 Run Session 恢复） |
| **Overview 导航** | 分组导航（主工作台 / 能力应用 / 能力目录 / 开发者） |

---

## 5. 风险边界

### 5.1 默认不执行的能力

以下能力**不默认执行**，必须经过 RiskGate + 显式确认：

| 能力 | 原因 |
|---|---|
| `video-*` | 高成本视频生成 |
| `voice-clone-*` | 付费 + 素材型 |
| `voice-design` | 付费 + 素材型 |
| `music-cover-prep` | 素材型 |
| `file-delete` | 破坏性操作 |
| `voice-delete` | 破坏性操作 |

### 5.2 必须 RiskGate + 显式确认的能力类型

- **高成本能力**：video 生成类
- **素材型能力**：voice-clone / voice-design / music-cover / file-upload
- **破坏性操作**：file-delete / voice-delete
- **长任务**：video-* 等异步任务
- **额外收费**：paid 确认项

### 5.3 费用说明

Token Plan 消耗**以 MiniMax 控制台为准**，本项目只做说明与估算辅助，不做精确计费。

---

## 6. 当前未完成项

如实列出当前已知未完成项：

- **未做完整 Run Session 恢复**：只有轻量草稿保存，不支持完整链式调用恢复
- **未做全量资产库 / 资产管理页**：资产预览已实现，但未做资产库 Gallery 页面
- **未做真实成本账单同步**：UsageCostExplainer 只做估算说明，不做实时账单同步
- **未做完整多租户 / 用户账号 / 权限隔离**：当前为单机单用户访问控制
- **未做生产级部署安全策略**：当前未包含完整的安全 headers、CORS、rate limiting 等
- **未做所有 warning_only 能力的真实验收**：只做了风险提示，未逐一实测
- **未做完整 e2e browser test**：只有 guard scripts 和单元级检查，无 Playwright e2e
- **runtime 测试资产**：本地存在测试资产但不应提交（已加入 .gitignore）

---

## 7. 下一阶段建议

### P0 — 立即可做

1. **真实页面人工验收 checklist**：逐页面、逐能力实际调用验证，形成 checklist 文档
2. **低成本 image/audio/file 实测**：t2i、i2i、tts-async、speech-02 等低成本能力实测
3. **资产结果展示增强**：支持更多资产类型（视频缩略图、3D 预览等）
4. **调用历史详情页**：历史记录支持点击展开完整 payload / response

### P1 — 下一步

1. **Run Session 完整恢复**：支持完整链式调用状态保存与恢复
2. **资产库 / Asset Gallery**：支持历史资产浏览与管理
3. **能力体验表单继续产品化**：优化 payload 构建表单，支持字段校验
4. **Test Console e2e 自动化**：Playwright 测试覆盖核心流程

### P2 — 长期

1. **minimax_core 可复用包整理**：将 core 模块整理为可独立发布的 Python 包
2. **独立应用模板**：Voice Lab / Image Tool / Music Tool / File KB Tool
3. **部署与权限隔离**：多租户支持、生产安全策略

---

## 8. 相关文档

- [CAPABILITY_MATRIX.md](CAPABILITY_MATRIX.md) — 能力矩阵
- [VERIFICATION_INDEX.md](VERIFICATION_INDEX.md) — 验收状态索引
- [FRONTEND_UI_FLOW_AUDIT.md](FRONTEND_UI_FLOW_AUDIT.md) — UI 流程审计
- [OFFICIAL_DOCS_ALIGNMENT_AUDIT.md](OFFICIAL_DOCS_ALIGNMENT_AUDIT.md) — 官方文档对齐审计
- [PROJECT_COMPLETION_REPORT.md](PROJECT_COMPLETION_REPORT.md) — 项目完成报告（前期）
