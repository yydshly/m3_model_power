# MiniMax Token Plan 能力聚合工作台

MiniMax Token Plan 能力盘点、实测验收与可视化测试工作台。

把 MiniMax 订阅内所有公开 API 统一登记、统一访问。
能力 / 模型清单由 YAML 配置驱动，前端动态渲染，未实现的能力也会出现在目录里并给出文档链接。

## 项目定位

**m3_model_power** 是 MiniMax Token Plan 能力盘点、实测验收与可视化测试工作台。

它不是简单 API demo，而是用于：
- 确认当前 Token Plan 实际可用能力
- 记录验收状态与能力说明
- 说明能力用途与使用限制
- 控制高成本 / 素材型 / 删除型操作风险
- 为后续 MiniMax 应用开发提供基础能力模块

## 当前完成状态

| 指标 | 状态 |
|---|---|
| Registry 总能力 | 32 |
| in_scope 能力 | 20 / 20 verified |
| in_scope 能力说明 | 20 / 20 described |
| Test Console 页面 | ✅ 已完成 |
| Protected Invoke + RiskGate | ✅ 已完成 |
| 调用历史 + 脱敏 | ✅ 已完成 |
| Asset Result Preview | ✅ 已完成 |
| Overview 工作台首页 | ✅ 已完成（PR #12） |
| 分组导航 | ✅ 已完成（PR #12） |
| UsageCostExplainer | ✅ 已完成（PR #11） |
| Demo Payload 自动填充 | ✅ 已完成（PR #11） |
| InvocationHistoryPanel | ✅ 已完成（PR #10） |

## 核心模块

| 模块 | 职责 |
|---|---|
| `minimax_core/registry` | YAML 配置加载，capability / model 注册表 |
| `minimax_core/invoker` | 统一调用入口（同步 / 流式 / 异步） |
| `minimax_core/guards` | RiskGate 风险评估与阻断 |
| `minimax_core/verification` | 验收结果结构定义 |
| `minimax_core/descriptions` | 人类可读能力说明加载 |
| `routers/verification` | 验收 Summary API |
| `routers/risk_check` | Risk Check API |
| `routers/history` | 调用历史 API |
| `routers/descriptions` | 能力说明 API |
| `frontend TestConsole` | 可视化测试控制台页面 |

## Test Console

访问 `/test-console`（需启动前端 `npm run dev`）：

### 功能清单

- **验收进度查看**：Summary Banner 显示 Token Plan 整体验收进度，in_scope 说明覆盖率
- **Capability 表格**：按 category 分组展示所有 32 个能力，显示 scope / billing / risk / verified / desc 状态
- **能力说明**：点击任意 in_scope 能力，查看完整人类可读说明
- **Risk Check**：使用真实 payload 执行风险检查，验证 required_confirmations
- **Protected Invoke**：勾选所有必需确认项后执行真实调用，结果写入 history
- **调用历史**：查看本次会话所有 RC（Risk Check）和 INV（Invoke）记录
- **Asset Result Preview**：图片 URL 展示图片预览，音频 URL 展示 audio controls，文件类结果展示文件信息

### 当前工作台入口

| 页面 | 路由 | 目标用户 |
|---|---|---|
| 工作台首页 | `/` | 所有用户 |
| 能力体验 | `/capability-runner` | 能力探索者 |
| 高级测试 | `/test-console` | 开发者 |
| 场景推荐 | `/capability-scenarios` | 业务人员 |
| 流程体验 | `/capability-workflows` | 探索者 |
| 能力画像 | `/capability-profiles` | 分析人员 |
| 模型目录 | `/models-all` | 开发者 |

详细产品说明见 [docs/PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md](docs/PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md)。

## 不执行的能力

以下能力默认不执行（需显式确认）：

| 能力 | 原因 |
|---|---|
| video-* | 高成本视频生成 |
| voice-clone-* | 付费 + 素材型 |
| voice-design | 付费 + 素材型 |
| music-cover-prep | 素材型 |
| file-delete | 破坏性操作 |
| voice-delete | 破坏性操作 |

## Capability Description Layer

能力说明层补足 registry 不适合承载的人类理解信息：

- **registry** → 机器可读配置（YAML 驱动，API 返回）
- **description** → 人类可读说明（静态 JSON，后端 API 加载，前端按需展示）

### 每个 description 包含

```yaml
summary           # 一句话说明能力用途
use_cases         # 适用场景列表
not_recommended_for  # 不适用场景
input_notes       # 输入注意事项
output_notes      # 输出格式说明
risk_notes        # 风险提示
billing_notes     # 计费说明
common_errors     # 常见错误排查
product_usage     # 产品级使用建议
integration_tips  # 集成开发提示
```

### 说明校验

```bash
python scripts/check_capability_descriptions.py
```

## History

调用历史存储路径：`backend/runtime/test_console/history.jsonl`

### 特点

- **脱敏**：只保存 payload 摘要，不保存完整敏感 payload
- **字段**：payload_keys / payload_size_chars / payload_preview
- **敏感字段递归脱敏**：支持嵌套 dict/list 中的 key 脱敏
- **文件超过 2MB**：自动 compact，保留最后 1000 行
- **runtime 不提交**：`.gitignore` 已排除 `backend/runtime/`

## RiskGate

RiskGate 在实际调用 MiniMax API 前评估风险，不满足条件时阻断执行。

### 受保护确认项

| 确认项 | 触发条件 |
|---|---|
| `confirm_quota` | tts-async 字符数 > 1000 |
| `confirm_asset_source` | 需要上传素材（image-i2i / file-upload / voice-clone-*） |
| `confirm_existing_task` | 只操作已有任务（video-query / video-download） |
| `confirm_long_running` | 长任务（video-*） |
| `confirm_paid` | 可能额外收费 |
| `confirm_high_cost` | 高成本能力 |
| `confirm_destructive` | 删除型操作（file-delete / voice-delete） |

### 阻断响应

未满足条件时返回 `error_type: risk_gate_blocked`，不实际调用 MiniMax API。

## 运行与验证命令

```bash
# 后端
cd backend
cp .env.example .env   # 填入 MINIMAX_TOKEN_PLAN_KEY
pip install -e .
uvicorn app.main:app --reload --port 8777

# 前端（另一个终端）
cd frontend
npm install
npm run dev            # http://localhost:5173

# 验证命令
python -m compileall backend/app
python scripts/check_history_store.py
python scripts/check_capability_descriptions.py
cd frontend && npm run build && cd ..
```

## Git / 安全约束

- `.env` **不提交**（已在 `.gitignore`）
- `backend/runtime/` **不提交**
- 真实媒体资产 **不提交**
- `Token Plan Key` 只允许放后端环境变量
- 前端永远不接触 API Key
- 高成本 / 素材型 / 删除型能力必须经过 RiskGate 和显式确认

## 项目范围边界

| scope | 数量 | 说明 | 计入完成率 |
|---|---|---|---|
| `in_scope` | 20 | Token Plan 核心验收范围 | ✅ 是 |
| `warning_only` | 7 | 付费/认证/素材型能力，只做风险提示 | ❌ 否 |
| `out_of_scope` | 5 | 视频生成，完全不纳入 | ❌ 否 |

## 模型事实来源

三类状态独立维护，不能混淆：

| 状态 | 来源 | 说明 |
|---|---|---|
| `official_current` | [官方文档](https://platform.minimaxi.com/docs/api-reference/api-overview) | 官方当前是否列出该模型 |
| `live_available` | `scripts/sync_minimax_models.py` 真实 API 查询 | OpenAI / Anthropic 模型列表接口实际返回 |
| `subscription_expected` | 用户订阅权益说明 | 套餐是否覆盖该模型 |

## 后续路线

当前阶段目标已完成。详细路线图与未完成项见 [docs/PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md](docs/PRODUCTIZED_WORKBENCH_COMPLETION_REPORT.md)。

近期优先：

1. 真实页面人工验收 checklist
2. 低成本 image/audio/file 实测
3. 资产结果展示增强
4. 调用历史详情页
5. Run Session 完整恢复（P1）

---

## 仓库结构

```
backend/
  config/
    capabilities.yaml   ← 32 个接口的事实来源（status: implemented/planned/unsupported）
    models.yaml          ← 模型清单（official_current / live_available / subscription_expected 三态）
  app/
    registry/           ← YAML 加载 + handler 注册
    capabilities/       ← 各能力 handler 实现
    routers/            ← health / registry / invoke / stream / upload / ws / verification / risk_check / history / descriptions
    minimax/client.py   ← 统一鉴权 + JSON/字节/SSE 三种发送方式
  scripts/
    sync_minimax_models.py         ← 模型发现脚本（live API 查询）
    verify_minimax_capabilities.py ← 能力验收脚本（分级验证）
    check_history_store.py         ← History 脱敏与存储校验
    check_capability_descriptions.py ← Description 覆盖率校验
frontend/
  src/
    pages/              ← Overview / Category / Capability / Models / TestConsole
    components/         ← StatusBadge / InvokePanel / JsonView / ChatPanel / AssetPreview / ...
    store.tsx           ← /api/registry 缓存
```
