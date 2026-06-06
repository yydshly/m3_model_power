# MiniMax 能力聚合工作台

MiniMax TokenPlanPlus 极速版年度会员能力盘点与实测工作台。

把 MiniMax 订阅内所有公开 API 统一登记、统一访问。
能力 / 模型清单由 YAML 配置驱动，前端动态渲染，未实现的能力也会出现在目录里并给出文档链接。

**当前目标**：先完整、正确展示并验证用户订阅可用的大模型和 API 能力，不做 SaaS 扩展。

## 项目定位

| 维度 | 说明 |
|---|---|
| 定位 | MiniMax TokenPlanPlus 极速版能力盘点与实测工作台 |
| 目标 | 完整、正确展示并验证订阅可用的大模型和 API 能力 |
| 订阅 | TokenPlanPlus 极速版 · 续费 2027-05-29 · Plus-极速版档位 |

## 项目范围边界

本项目范围由 `scope_policy` 字段定义，32 项能力分为三类：

| scope | 数量 | 说明 | 计入完成率 |
|---|---|---|---|
| `in_scope` | 20 | Token Plan 核心验收范围 | ✅ 是 |
| `warning_only` | 7 | 付费/认证/素材型能力，只做风险提示 | ❌ 否 |
| `out_of_scope` | 5 | 视频生成，完全不纳入 | ❌ 否 |

**完成率**：70%（14/20 in_scope 能力已完成验收）

**warning_only**（不做验收，只做提示）：voice-clone-* 系列（付费+素材）、voice-design（付费）、file-delete/voice-delete（破坏性）、music-cover-prep（素材）

**out_of_scope**（视频生成，Token Plan 之外）：video-t2v / video-i2v / video-s2v / video-query / video-download

## 模型事实来源

三类状态独立维护，不能混淆：

| 状态 | 来源 | 说明 |
|---|---|---|
| `official_current` | [官方文档](https://platform.minimaxi.com/docs/api-reference/api-overview) | 官方当前是否列出该模型 |
| `live_available` | `scripts/sync_minimax_models.py` 真实 API 查询 | OpenAI / Anthropic 模型列表接口实际返回 |
| `subscription_expected` | 用户订阅权益说明 | 套餐是否覆盖该模型 |

## 快速启动

```bash
# 后端
cd backend
cp .env.example .env   # 填入 MINIMAX_TOKEN_PLAN_KEY
pip install -e .
uvicorn app.main:app --reload --port 8000

# 前端（另一个终端）
cd frontend
npm install
npm run dev            # http://localhost:5173
```

## 仓库结构

```
backend/
  config/
    capabilities.yaml   ← 32 个接口的事实来源（status: implemented/planned/unsupported）
    models.yaml          ← 模型清单（official_current / live_available / subscription_expected 三态）
  app/
    registry/           ← YAML 加载 + handler 注册
    capabilities/       ← 各能力 handler 实现
    routers/            ← health / registry / invoke / stream / upload / ws
    minimax/client.py   ← 统一鉴权 + JSON/字节/SSE 三种发送方式
  scripts/
    sync_minimax_models.py         ← 模型发现脚本（live API 查询）
    verify_minimax_capabilities.py ← 能力验收脚本（分级验证）
frontend/
  src/
    pages/              ← Overview / Category / Capability / Models
    components/         ← StatusBadge / InvokePanel / JsonView / ChatPanel / ...
    store.tsx           ← /api/registry 缓存
```

## 当前进度

**已实现 32 / 32**（tts-ws 已实现 WebSocket 代理，`speech-01-hd/speech-01-turbo` 等旧模型已移入 legacy）

| 分类 | 接口 |
|---|---|
| 对话 | chat-anthropic / chat-openai / chat-responses-create / chat-responses-tokens（含 SSE 流式） |
| 语音 | tts-sync / tts-ws（WS 反向代理，已验收） / tts-async（异步，已验收） / voice-list / voice-delete / voice-design / voice-clone-do |
| 语音上传 | voice-clone-upload-audio / voice-clone-upload-prompt（multipart） |
| 视觉-图像 | image-t2i / image-i2i（image-01 / image-01-live） |
| 视觉-视频 | video-t2v / video-i2v / video-s2v / video-query / video-download（Hailuo 2.3 系列） |
| 音乐 | music-gen / lyrics-gen / music-cover-prep（music-2.6） |
| 资产 | file-upload（multipart）/ file-list / file-retrieve / file-content / file-delete |
| 模型 | models-openai-list / models-openai-retrieve / models-anthropic-list / models-anthropic-retrieve |

### tts-ws WebSocket 协议要点

> 已接入 `minimax_core` + FastAPI via `invoke_async()`：见 `MiniMaxNativeClient.tts_websocket()` + `CapabilityInvoker.invoke_async()` + `voice.py tts_ws handler`

1. 连接 `wss://api.minimaxi.com/ws/v1/t2a_v2`，发送 `task_start`（含 `model`/`voice_setting`/`audio_setting`，**不含 text**）
2. 收到 `task_started` 确认后，发送 `task_continue`（含 text）和 `task_finish`
3. 服务端通过 `task_continued` JSON 事件的 `data.audio` 字段返回 hex 音频（**非二进制帧**）
4. 全部接收完后收到 `task_finished`

**调用约定**：FastAPI async route 应使用 `await invoker.invoke_async("tts-ws", payload)`；CLI 脚本使用 `asyncio.run(invoke_async(...))` 在入口处封装。

### tts-async quota guard

> 已接入 `minimax_core` + `CapabilityInvoker.invoke_async()` + RiskGate quota guard

字符数保护规则（已收口）：
- `<=300` 字：默认允许，无需确认
- `301~1000` 字：允许，但有 warning 提示消耗 quota
- `1001~5000` 字：需 `confirm_quota=true`，否则被 RiskGate `risk_gate_blocked` 拦截
- `>5000` 字：**硬阻断**，plain `confirm_quota=true` 也无法绕过（需未来 `confirm_very_large_quota`）

CLI 示例：
```bash
# 短文本验证（自动通过 RiskGate）
python scripts/verify_minimax_capabilities.py --level medium --capability tts-async --confirm-cost

# 长文本验证（需显式 --confirm-cost）
python scripts/verify_minimax_capabilities.py --level medium --capability tts-async --confirm-cost --confirm-quota
```

## 官方当前模型（official_current: true）

| Family | 模型 | 上下文 | 模态 | 协议 | 说明 |
|---|---|---|---|---|---|
| chat | MiniMax-M3 | 1M | text+image+video | openai/anthropic/responses | 旗舰多模态，支持 thinking |
| chat | MiniMax-M2.7 | 204800 | text | openai/anthropic | 标准档 |
| chat | MiniMax-M2.7-highspeed | 204800 | text | openai/anthropic | 极速档，走配额 |
| chat | MiniMax-M2.5 | 204800 | text | openai | 标准档 |
| chat | MiniMax-M2.5-highspeed | 204800 | text | openai/anthropic | 极速档，走配额 |
| chat | MiniMax-M2.1 | 204800 | text | openai | 标准档 |
| chat | MiniMax-M2.1-highspeed | 204800 | text | openai/anthropic | 极速档，走配额 |
| chat | MiniMax-M2 | 204800 | text | openai | 标准档 |
| speech | speech-2.8-hd | — | audio | native | 最新 HD |
| speech | speech-2.8-turbo | — | audio | native | 最新 Turbo |
| speech | speech-2.6-hd | — | audio | native | HD |
| speech | speech-2.6-turbo | — | audio | native | Turbo |
| speech | speech-02-hd | — | audio | native | HD（推荐） |
| speech | speech-02-turbo | — | audio | native | Turbo |
| image | image-01 | — | image | native | 文生图/图生图主力 |
| image | image-01-live | — | image | native | 支持多种画风 |
| video | MiniMax-Hailuo-2.3 | — | video | native | 最新视频，含 T2V/I2V/S2V |
| video | MiniMax-Hailuo-2.3-Fast | — | video | native | 快速档 |
| video | MiniMax-Hailuo-02 | — | video | native | 高分辨率/更长时长 |
| music | music-2.6 | — | music | native | 最新音乐生成 |
| music | music-cover | — | music | native | 翻唱生成 |

### 全量统计原则

本项目优先保证 **MiniMax TokenPlanPlus 能力全量、准确、可追溯**。架构复用服务于全量统计，不替代全量统计。

1. **所有官方当前模型必须逐项展示**：每个模型单独一行，不允许用总数代替明细。
2. **highspeed 模型必须作为独立模型展示**：`MiniMax-M2.7-highspeed`、`MiniMax-M2.5-highspeed`、`MiniMax-M2.1-highspeed` 必须各自独立出现。
3. **`/v1/models` 不返回 non-chat 模型不代表它们不可用**：speech / image / video / music 模型通过 capability probe 验证，不能因 API 列表缺失就忽略。
4. **非 LLM 模型通过 capability probe 验证**：speech / image / video / music 模型以 `discovery_method: capability_probe` 标注，由能力端点实测确认。
5. **所有 32 个能力必须逐项出现**：包含 requires_model=false 的能力（如 lyrics-gen / file-* / models-*），正确显示"无需模型"。
6. **Gap 矩阵必须完整**：official_current 但本地缺失、本地有但非官方当前、live 有但本地缺失、能力无支持模型等缺口必须逐项列出。
7. **全量覆盖矩阵文档**：`docs/MINIMAX_FULL_CAPABILITY_MATRIX.md` 是全量统计的核心交付物，基于 registry 和已有报告生成，不调用真实 API。

### music-2.6-free 特殊说明

`music-2.6-free` 虽然 `official_current: true`，但 `subscription_expected: false`（免费档变体，不在主权益范围内），本地标记 `enabled: false`，不影响 TokenPlanPlus 主权益展示，但必须统计。

### highspeed 模型协议说明

| 模型 | openai | anthropic | responses |
|---|---|---|---|
| MiniMax-M2.7-highspeed | ✓ | ✓ | — |
| MiniMax-M2.5-highspeed | ✓ | ✓ | — |
| MiniMax-M2.1-highspeed | ✓ | ✓ | — |

highspeed 档位走 TokenPlanPlus 共享配额（`cost_level: quota`）。

### 验收状态分层说明

本项目对模型的验证分为以下层级：

| 层级 | 状态名 | 含义 |
|---|---|---|
| L1 | `official_current` | 官方当前文档中列出 |
| L2 | `models_api_verified` | 通过 `/v1/models` 或 `/anthropic/v1/models` 发现（仅 chat 模型） |
| L3 | `capability_level_verified` | 能力端点已实测可用，但仅测了一个模型，未逐项验证所有模型 |
| L4 | `model_level_verified` | 具体模型已作为请求中 `model` 参数单独调用成功 |
| — | `not_probed` | 尚未进行任何实测 |
| — | `high_cost_pending` | 成本或风险较高，暂不执行（video / voice-clone / voice-design 等） |
| — | `not_applicable` | 不需要模型（如 lyrics-gen / file-* / models-*） |

**重要说明**：

- `/v1/models` 主要覆盖 chat 模型，speech/image/video/music 不出现于其中，不代表不可用
- `models_api_verified` ≠ `model_level_verified`
- `capability_level_verified` ≠ 所有模型逐项验证
- `high_cost_pending` 能力必须显式确认后才执行（video / voice-clone / voice-design / music-cover-prep）
- 本轮已对 8 个 chat 模型完成 `chat-openai` 模型级逐项 probe，全部成功
- `chat-anthropic` 在 `max_tokens=4` 时返回 thinking block 而非 text，探针参数需调整
- TTS/Image/Music 非 "失败"，而是探针参数（短文本/无参考图）下未产生可检测输出

### music-2.6-free 特殊说明
abab6.5s-chat / abab6.5-chat / abab6.5t-chat / abab6.5g-chat / speech-01-hd / speech-01-turbo / speech-01-240228 / T2V-01 / T2V-01-Director / I2V-01 / I2V-01-live / I2V-01-Director / S2V-01 / video-01 / music-1.5 / music-01

## 三种调用通道

| 类型 | 路由 | 触发条件 |
|---|---|---|
| 同步 | `POST /api/invoke/{cap_id}` | 默认；JSON 入参 JSON 出参 |
| 流式 | `POST /api/stream/{cap_id}` | capability.streaming=true，SSE 透传 |
| 上传 | `POST /api/upload/{cap_id}` | capability.multipart=true，前端选文件 |

详情页 `Capability.tsx` 会自动根据配置切换面板。

## ⚠️ 重要：HTTP 200 ≠ MiniMax 业务成功

MiniMax native API（tts-sync / image-t2i / lyrics-gen / music-gen / voice-list 等）返回 HTTP 200，但**业务层状态码**在 `base_resp.status_code` 字段：

| base_resp.status_code | 含义 | 验收判定 |
|---|---|---|
| 0 / null | 业务成功 | success |
| 1004 | 鉴权 / Token 不匹配 | failed · auth_or_token_mismatch |
| 其他非零 | 业务错误 | failed · minimax_api_error |

**验收脚本和 CapabilityInvoker 必须检查 `base_resp.status_code`，不能仅凭 HTTP 200 判定 success。**

## Token Plan Only 模式

本项目**默认只验证 TokenPlanPlus 极速版能力**：

```bash
# 在 backend/.env 中配置 TokenPlan Key
MINIMAX_TOKEN_PLAN_KEY=你的TokenPlan订阅Key

# 运行验收（默认使用 token-plan）
python scripts/verify_minimax_capabilities.py --level medium --confirm-cost
python scripts/probe_model_level_support.py --scope low-cost
```

- `MINIMAX_TOKEN_PLAN_KEY` 是**唯一参与验收的凭证**
- `MINIMAX_API_KEY` 仅在显式传递 `--key-source api-key` 时用于对照诊断，**不参与默认验收**
- 如果 `MINIMAX_TOKEN_PLAN_KEY` 未配置，native 多模态验收将跳过并提示

## 能力验收方式

### Level 1 — 安全验收（默认执行）

```bash
python scripts/verify_minimax_capabilities.py --level safe
```

覆盖：models-openai-list / models-anthropic-list / chat-openai / chat-anthropic / chat-responses-create / file-list / voice-list 等。

### Level 2 — 中等成本（需确认）

```bash
python scripts/verify_minimax_capabilities.py --level medium --confirm-cost
```

覆盖：tts-sync / image-t2i / lyrics-gen / music-gen。

### Level 3 — 高成本（需双重确认）

```bash
python scripts/verify_minimax_capabilities.py --level high --confirm-cost --confirm-high-cost
```

覆盖：voice-clone-do / voice-design / video-t2v / video-i2v / video-s2v / music-cover-prep。

## 模型发现脚本

```bash
python scripts/sync_minimax_models.py
```

输出：
- `backend/runtime/model_discovery/model_discovery_report.json`
- `backend/runtime/model_discovery/openai_models.json`
- `backend/runtime/model_discovery/anthropic_models.json`
- `docs/MINIMAX_MODEL_SUPPORT_REPORT.md`

## 添加新能力的工作量

1. `capabilities.yaml` 加一条（id / category / status / example / streaming? / multipart? …）
2. 写一个 handler：
   ```python
   @register_handler("xxx-id")
   async def my_handler(p: dict):
       return await post_json("/v1/xxx", p, with_group=True)
   ```
3. `POST /api/registry/reload`（或重启 uvicorn）

前端代码恒定为零修改。

## 费用说明

| 标记 | 含义 |
|---|---|
| `cost_level: quota` | 走 TokenPlanPlus 极速档共享配额（极速档专属） |
| `cost_level: low` | 单独计费，单价低 |
| `cost_level: medium` | 单独计费，中等单价 |
| `cost_level: high` | 单独计费，单价高（视频/音色克隆等） |

> **注意**：高成本能力（video-t2v / voice-clone-do 等）默认不自动触发，验收脚本 Level 3 需二次确认。

## 收费与高成本能力提示

### 已完成验收的范围

本项目已完成 **TokenPlanPlus 极速档 low / medium** 能力验收，包括：

- `chat-openai` / `chat-anthropic` / `chat-responses-create` / `chat-responses-tokens`（safe 验收）
- `tts-sync`（model_level 验收，6 个 speech 模型全部成功）
- `image-t2i`（model_level 验收，2 个 image 模型全部成功）
- `lyrics-gen`（medium 验收）
- `music-gen`（model_level 验收，music-2.6 成功）

以上能力属于 `billing_category: normal_token_plan_test`，默认执行。

### 不得默认执行的能力

以下能力 `requires_explicit_confirmation: true`，**不得默认自动执行**：

| 能力 | 类别 | 原因 |
|---|---|---|
| `voice-clone-upload-audio` / `voice-clone-upload-prompt` / `voice-clone-do` | `paid_confirm_required` | 音色克隆可能触发单独费用（9.9 元/音色）；需要上传参考音频；7 天内未调用音色会被删除 |
| `voice-design` | `paid_confirm_required` | 音色设计可能触发单独费用（9.9 元/音色）；首次使用该音色合成时收费 |
| `video-t2v` / `video-i2v` / `video-s2v` | `high_cost_confirm_required` | 视频生成属于高消耗能力，可能大量消耗 TokenPlan/Credits/视频资源包额度 |
| `music-cover-prep` | `asset_required_confirm_required` | 需要参考音频，属于素材型能力；调用前需确认音频来源、版权、费用 |

### 重要原则

1. **HTTP 200 ≠ MiniMax 业务成功**：native API 响应必须检查 `base_resp.status_code`。
2. **Token Plan Only**：`MINIMAX_TOKEN_PLAN_KEY` 是唯一参与默认验收的凭证。
3. **不把这些未执行项算作失败**：pending_explicit_confirmation 是状态，不是错误。

详情见 [docs/MINIMAX_FULL_CAPABILITY_MATRIX.md](docs/MINIMAX_FULL_CAPABILITY_MATRIX.md#6-收费--高成本能力提示矩阵)。

## 操作风险保护层

本项目不仅区分计费风险，也区分操作风险：

| 操作风险类别 | 能力 | 说明 |
|---|---|---|
| 破坏性操作 | `file-delete` / `voice-delete` | 删除后不可恢复，执行前必须二次确认 |
| 素材型操作 | `file-upload` / `image-i2i` / `voice-clone-upload-audio` / `voice-clone-upload-prompt` / `music-cover-prep` | 需确认素材来源、隐私、版权 |
| 仅已有任务 | `video-query` / `video-download` | 只操作已有任务，不会自动创建视频任务 |
| 长任务/高成本 | `video-t2v` / `video-i2v` / `video-s2v` | 必须用户显式确认后才执行 |
| 额度保护 | `tts-async` | <=300字允许默认测试；>1000字需二次确认；>5000字无确认禁止执行 |

**重要原则**：

1. 未经确认，不执行高成本、破坏性、素材型能力。
2. 操作风险保护与计费风险独立：同一个能力可能同时标记为高成本和长任务。
3. 详情见 [docs/MINIMAX_FULL_CAPABILITY_MATRIX.md](docs/MINIMAX_FULL_CAPABILITY_MATRIX.md#7-操作风险保护矩阵)。

## 风险能力执行前确认机制

本项目内置 **RiskGate（执行前确认门禁）**，所有风险能力必须显式确认后才允许执行。

### 核心规则

只要满足以下任意条件，就必须阻断自动执行，除非用户显式确认：

- `billing_policy.requires_explicit_confirmation == true`
- `operation_policy.requires_operation_confirmation == true`
- `billing_policy.may_charge_extra == true`
- `operation_policy.is_destructive == true`
- `operation_policy.requires_uploaded_asset == true`
- `operation_policy.is_long_running == true`
- `operation_policy.requires_existing_task == true`

### 确认项

| 确认项 | 触发条件 |
|---|---|
| `--confirm-paid` | `may_charge_extra=true` |
| `--confirm-high-cost` | `billing_category=high_cost_confirm_required` |
| `--confirm-destructive` | `is_destructive=true` |
| `--confirm-asset-source` | `requires_uploaded_asset=true` |
| `--confirm-long-running` | `is_long_running=true` |
| `--confirm-existing-task` | `requires_existing_task=true`（需 payload 中有 task_id/file_id） |
| `--confirm-quota` | `tts-async` 字符数超阈值 |

### 后端 RiskGate

`backend/app/minimax_core/guards/risk_gate.py` 提供 `evaluate_capability_risk()` 函数，`CapabilityInvoker.invoke()` 在实际调用 MiniMax API 前先通过 RiskGate 评估：

```python
from app.minimax_core.guards.risk_gate import evaluate_capability_risk

decision = evaluate_capability_risk(capability, confirmations={"confirm_paid": True}, payload={"text": "hello"})
if not decision.allowed:
    print(decision.blocked_reasons)  # ["voice-design: may_charge_extra=true ..."]
```

未确认时后端返回 `error_type: risk_gate_blocked`，不实际调用 MiniMax API。

### 脚本确认参数

```bash
# 验收脚本支持以下确认参数
python scripts/verify_minimax_capabilities.py --level medium --confirm-cost \
  --confirm-paid --confirm-destructive --confirm-asset-source \
  --confirm-long-running --confirm-existing-task --confirm-quota
```

### 前端确认展示

能力详情页（`Capability.tsx`）对需要确认的能力展示"执行前需要确认"区块，列出所有需要的确认项。后端 RiskGate 会阻断未确认的执行请求。

### 详情

- 确认门禁矩阵：[docs/MINIMAX_FULL_CAPABILITY_MATRIX.md](docs/MINIMAX_FULL_CAPABILITY_MATRIX.md#9-执行前确认门禁矩阵)

## 安全注意

- API Key 仅存在 `backend/.env`，前端永远不接触 Key
- 所有调用通过后端 `/api/invoke/*` 代理
- 日志中只显示 Key 前后脱敏字符（如 `sk-***abcd`），不打印完整 Key
- `.env` 不提交到 Git（已在 `.gitignore` 中）

## 项目长期定位

本项目承担双重使命：

### 1. MiniMax TokenPlanPlus 能力盘点与实测工作台

通过 YAML 配置驱动、前端动态渲染的方式，完整展示用户订阅内所有可用 API 能力，并支持分层验收（safe / medium / high）。

### 2. MiniMax 应用开发可复用能力底座

`backend/app/minimax_core/` 是可供其他项目直接复用的核心模块：

```python
# 复用模型规格
from app.minimax_core.contracts import ModelSpec, CapabilitySpec

# 复用脱敏工具
from app.minimax_core.guards import redact_key, redact_url

# 复用验收结果结构
from app.minimax_core.contracts import VerificationResult
```

**minimax_core 模块边界**：

| 子模块 | 职责 |
|---|---|
| `contracts/specs.py` | ModelSpec、CapabilitySpec — 模型和能力规格定义 |
| `contracts/response.py` | AssetRef、UnifiedResponse、UnifiedError、UnifiedErrorException — 统一响应结构（`UnifiedErrorException` 支持 `raise` 语法） |
| `contracts/verification.py` | VerificationResult — 验收结果结构 |
| `guards/redaction.py` | redact_key / redact_url — 日志和响应脱敏 |

minimax_core 不依赖工作台路由、前端页面或 services 层，可被其他 Python 项目直接 pip install 或复制使用。

**架构原则**：

- minimax_core 负责：模型注册、能力注册、协议选择、认证 header 构造、统一错误处理、统一资产处理、高成本保护、日志脱敏、验收结果结构
- API 层（routers）只做：HTTP 入参解析、调用 core、返回 JSON、转换 HTTPException
- scripts 负责：实际调用上游 API、解析响应、写入 runtime 报告
