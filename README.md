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
cp .env.example .env   # 填入 MINIMAX_API_KEY
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
| 语音 | tts-sync / tts-ws（WS 反向代理） / tts-async / voice-list / voice-delete / voice-design / voice-clone-do |
| 语音上传 | voice-clone-upload-audio / voice-clone-upload-prompt（multipart） |
| 视觉-图像 | image-t2i / image-i2i（image-01 / image-01-live） |
| 视觉-视频 | video-t2v / video-i2v / video-s2v / video-query / video-download（Hailuo 2.3 系列） |
| 音乐 | music-gen / lyrics-gen / music-cover-prep（music-2.6） |
| 资产 | file-upload（multipart）/ file-list / file-retrieve / file-content / file-delete |
| 模型 | models-openai-list / models-openai-retrieve / models-anthropic-list / models-anthropic-retrieve |

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
- `high_cost_pending` 能力必须显式确认后才执行（video / voice-clone / voice-design / tts-async / music-cover-prep）
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
| `contracts/response.py` | AssetRef、UnifiedResponse、UnifiedError — 统一响应结构 |
| `contracts/verification.py` | VerificationResult — 验收结果结构 |
| `guards/redaction.py` | redact_key / redact_url — 日志和响应脱敏 |

minimax_core 不依赖工作台路由、前端页面或 services 层，可被其他 Python 项目直接 pip install 或复制使用。

**架构原则**：

- minimax_core 负责：模型注册、能力注册、协议选择、认证 header 构造、统一错误处理、统一资产处理、高成本保护、日志脱敏、验收结果结构
- API 层（routers）只做：HTTP 入参解析、调用 core、返回 JSON、转换 HTTPException
- scripts 负责：实际调用上游 API、解析响应、写入 runtime 报告
