# MiniMax 能力全量覆盖矩阵

> 生成时间：2026-06-06
> 数据来源：`backend/config/capabilities.yaml` + `backend/config/models.yaml`
> 验收脚本：`backend/scripts/verify_minimax_capabilities.py`

---

## Token Plan Only 验收原则

本项目**默认只验收 TokenPlanPlus 极速版能力**：

1. **默认 Key 是 `MINIMAX_TOKEN_PLAN_KEY`**，所有验收脚本均使用该 Key
2. **`MINIMAX_API_KEY` 不参与默认验收**，仅在显式 `--key-source api-key` 时用于对照诊断
3. 如果 `MINIMAX_TOKEN_PLAN_KEY` 未配置，native 多模态状态为 `token_plan_key_not_set`
4. 之前 API Key 返回 1004 的记录仅作为诊断参考，**不作为 Token Plan 能力结论**
5. 全量矩阵以 Token Plan Key 实测结果为唯一事实来源

## Token Plan Key 配置状态（2026-06-06）

| Key | 配置状态 | 说明 |
|---|---|---|
| `MINIMAX_TOKEN_PLAN_KEY` | ❌ 未配置（`token_plan_key_not_set`） | 需在 `backend/.env` 中配置后才能验收 native 多模态 |
| `MINIMAX_API_KEY` | ✅ 已配置（`sk-cp-...`） | 仅用于可选诊断，不参与默认验收 |

**当前状态**：`token_plan_key_not_set`，native 多模态（tts-sync / image-t2i / lyrics-gen / music-gen）验收已跳过。

---

## 重要说明：HTTP 200 ≠ MiniMax 业务成功

MiniMax native API（tts-sync / image-t2i / lyrics-gen / music-gen / voice-list 等）使用 **HTTP 200 + 业务状态码** 双层状态体系：

```
HTTP 200 (网络层成功)
  └── base_resp.status_code == 0       ← 业务层真正成功
  └── base_resp.status_code == 1004    ← 业务层失败：鉴权/Token 不匹配
  └── base_resp.status_code == 其他    ← 业务层失败：其他错误
```

**验收必须检查 `base_resp.status_code`，不能仅凭 HTTP 200 判定 success。**

---

## False Positive 修复记录

### 2026-06-06 修复

**问题**：上一轮 `verify_minimax_capabilities.py --level medium` 显示 `4/4 success`，但实际 native API 返回：
```
base_resp.status_code=1004
auth_or_token_mismatch
```

**根因**：
1. `CapabilityInvoker._image_t2i` / `_lyrics_gen` / `_music_gen` / `_voice_list` 未检查 `base_resp.status_code`，直接返回 `UnifiedResponse(ok=True)`
2. `verify` 脚本未防御 `response.ok=False` 的返回路径（只捕获了抛出的异常）

**修复内容**：
1. `CapabilityInvoker` 新增 `parse_minimax_base_resp()` 统一解析函数
2. `_image_t2i` / `_lyrics_gen` / `_music_gen` / `_voice_list` 全部检查 `base_resp.status_code`
3. `UnifiedError` 数据类新增 `UnifiedErrorException` 抛出封装（`BaseModel` 无法继承 `BaseException`）
4. `verify` 脚本防御 `response.ok=False` 路径，强制转换为 `failed`
5. `1004` 统一归类为 `error_type=auth_or_token_mismatch`

**验证结果**（2026-06-06 medium run）：
| 能力 | 状态 | error_type | 实际错误 |
|---|---|---|---|
| tts-sync | failed | auth_or_token_mismatch | login fail: Please carry the API secret key... |
| image-t2i | failed | auth_or_token_mismatch | login fail: Please carry the API secret key... |
| lyrics-gen | failed | auth_or_token_mismatch | login fail: Please carry the API secret key... |
| music-gen | failed | auth_or_token_mismatch | login fail: Please carry the API secret key... |

**结论**：native 多模态（tts-sync / image-t2i / music-gen）因缺少 `MINIMAX_TOKEN_PLAN_KEY` 返回 1004 鉴权失败，不能判定为模型不可用。当前状态为 **auth_or_token_mismatch**，需配置 TokenPlan Key 才能完成验收。

---

## native 能力 base_resp 状态码映射

| status_code | 含义 | error_type | 是否可重试 |
|---|---|---|---|
| 0 / "0" / null | 业务成功 | — | — |
| 1004 | 鉴权 / Token 不匹配 | `auth_or_token_mismatch` | 否 |
| 其他非零 | MiniMax 业务错误 | `minimax_api_error` | 否 |

---

## 能力 × 模型 覆盖矩阵

### 对话类（OpenAI / Anthropic / Responses 兼容）

| 能力 | 模型 | 协议 | 验证层级 |
|---|---|---|---|
| chat-openai | MiniMax-M3 / M2.7 / M2.5 / M2.1 等 | openai | model_level_verified |
| chat-anthropic | MiniMax-M3 / M2.7-highspeed / M2.5-highspeed / M2.1-highspeed | anthropic | model_level_verified |
| chat-responses-create | MiniMax-M3 | openai | capability_level_verified |
| chat-responses-tokens | MiniMax-M3 | openai | capability_level_verified |

### Native 多模态（需检查 base_resp.status_code）

| 能力 | 模型 | 验证层级 | 当前状态 | 说明 |
|---|---|---|---|---|
| tts-sync | speech-02-turbo 等 | capability_level_verified | **auth_or_token_mismatch** | 需 TokenPlan Key |
| image-t2i | image-01 / image-01-live | capability_level_verified | **auth_or_token_mismatch** | 需 TokenPlan Key |
| music-gen | music-2.6 | capability_level_verified | **auth_or_token_mismatch** | 需 TokenPlan Key |
| lyrics-gen | — (无需模型) | capability_level_verified | **auth_or_token_mismatch** | 需 TokenPlan Key |
| voice-list | — (无需模型) | capability_level_verified | **auth_or_token_mismatch** | 需 TokenPlan Key |

### 高成本（high_cost_pending，未执行）

| 能力 | 说明 |
|---|---|
| voice-clone-do | 高成本，待确认 |
| voice-design | 高成本，待确认 |
| video-t2v / i2v / s2v | 高成本，待确认 |
| music-cover-prep | 高成本，待确认 |
| tts-async | 高成本，待确认 |

---

## TokenPlan Key 配置状态

- `MINIMAX_API_KEY`: 已配置（SHA256 前8位和前后4位已脱敏）
- `MINIMAX_TOKEN_PLAN_KEY`: **未配置**

> TokenPlan Key 与普通 API Key 不可混用。native 多模态（tts-sync / image-t2i / music-gen 等）权益由 TokenPlan Key 提供，普通 API Key 仅能访问 chat 类能力。

---

## Native Key 对照矩阵（2026-06-06 probe）

> 脚本：`backend/scripts/probe_model_level_support.py --scope low-cost`
> probe 范围：tts-sync(speech-02-turbo) / image-t2i(image-01) / music-gen(music-2.6) / lyrics-gen

### API Key vs TokenPlan Key 对照结果

| 能力 | 模型 | API Key result | TokenPlan Key result | 诊断 |
|---|---|---|---|---|
| tts-sync | speech-02-turbo | `auth_or_token_mismatch` (1004) | `token_plan_key_not_set` | 需 TokenPlan Key |
| image-t2i | image-01 | `auth_or_token_mismatch` (1004) | `token_plan_key_not_set` | 需 TokenPlan Key |
| music-gen | music-2.6 | `auth_or_token_mismatch` (1004) | `token_plan_key_not_set` | 需 TokenPlan Key |
| lyrics-gen | — | `auth_or_token_mismatch` (1004) | `token_plan_key_not_set` | 需 TokenPlan Key |

### 对照结论

| 场景 | 结论 | 状态 |
|---|---|---|
| API Key 1004，TokenPlan Key 成功 | native 多模态需要 TokenPlan Key | `token_plan_required` |
| API Key 成功，TokenPlan Key 1004 | native 多模态当前走普通 API Key，权限需确认 | `api_key_required` |
| 两者都 1004 | 账号权限、Key、套餐权益或账户余额仍需排查 | `both_keys_failed` |
| TokenPlan Key 未配置 | 无法完成 TokenPlan native 多模态验收 | `token_plan_key_not_set` |

**当前状态**：TokenPlan Key 未配置，所有 native 多模态 probe 返回 `auth_or_token_mismatch`，需配置 `MINIMAX_TOKEN_PLAN_KEY` 后重新验收。

### 前端状态展示映射

| probe_status | 前端显示 |
|---|---|
| `auth_or_token_mismatch` | 鉴权待排查 |
| `token_plan_required` | 需 TokenPlan Key |
| `api_key_required` | 需按量 API Key |
| `both_keys_failed` | 两类 Key 均失败 |
| `token_plan_key_not_set` | 缺少 TokenPlan Key |
| `output_missing` | 响应解析待修正 |
| `parser_mismatch` | 响应解析待修正 |

---

## lyrics-gen 多路径解析

`lyrics-gen` 响应字段路径（按优先级）：

1. `raw.lyrics`
2. `raw.data.lyrics`
3. `raw.data.text`
4. `raw.output`

如果 `base_resp.status_code == 0` 但上述路径均无歌词字段，标记为 `output_missing`，不判定 success。
