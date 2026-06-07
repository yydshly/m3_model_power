# MiniMax Token Plan 能力整理阶段完成报告

**分支**: `add-test-console-page`
**日期**: 2026-06-07
**状态**: ✅ MVP 完成，待合并

---

## 1. 项目目标

通过 YAML 配置驱动、前端动态渲染的方式，完整展示 Token Plan 订阅内所有可用 API 能力，并支持：

- 能力说明（人类可读）
- 风险控制（RiskGate）
- 真实验收（分层验证）
- 调用历史（脱敏可追溯）
- 可视化测试（Test Console）

## 2. 当前完成状态

| 指标 | 数值 | 状态 |
|---|---|---|
| Registry 总能力 | 32 | ✅ |
| in_scope 能力 | 20 / 20 | ✅ verified |
| in_scope 能力说明 | 20 / 20 | ✅ described |
| Test Console 页面 | 100% | ✅ |
| Protected Invoke + RiskGate | 100% | ✅ |
| History + 脱敏 | 100% | ✅ |
| Asset Result Preview | 100% | ✅ |
| Pydantic v2 兼容性 | 100% | ✅ |

## 3. in_scope 能力验收结果

20 / 20 in_scope 能力全部完成验收：

**对话类**: chat-anthropic / chat-openai / chat-responses-create / chat-responses-tokens
**语音类**: tts-sync / tts-ws / tts-async / voice-list
**视觉-图像类**: image-t2i / image-i2i
**音乐类**: music-gen / lyrics-gen
**资产类**: file-upload / file-list / file-retrieve / file-content
**模型类**: models-openai-list / models-anthropic-list

## 4. in_scope 能力说明覆盖结果

20 / 20 in_scope 能力全部包含人类可读说明，校验通过：

```
Registry total capabilities : 32
Registry in_scope           : 20
Description coverage         : 20 / 32
In_scope description coverage: 20 / 20
```

## 5. Test Console 功能说明

### 页面结构

- **Summary Banner**: Token Plan 验收进度，in_scope 说明覆盖率
- **Capability 表格**: 32 个能力，scope / billing / risk / verified / desc 五维状态
- **能力说明面板**: 点击任意 in_scope 能力查看完整人类可读说明
- **调用历史面板**: RC / INV 记录，带 badge 标识

### 核心流程

1. 选择能力 → 查看说明
2. 构造 payload → Risk Check（验证确认项）
3. 勾选所有必需确认项 → Protected Invoke
4. 结果写入 history → Asset Result Preview 展示

### 不执行能力

以下能力必须经过显式确认，不做默认自动执行：

- video-t2v / video-i2v / video-s2v（高成本）
- voice-clone-*（付费 + 素材）
- voice-design（付费）
- music-cover-prep（素材型）
- file-delete / voice-delete（破坏性）

## 6. RiskGate 安全边界

### 确认项矩阵

| 确认项 | 触发能力 |
|---|---|
| confirm_quota | tts-async 字符数 > 1000 |
| confirm_asset_source | image-i2i / file-upload / voice-clone-* |
| confirm_existing_task | video-query / video-download |
| confirm_long_running | video-* |
| confirm_paid | voice-clone-* / voice-design |
| confirm_high_cost | video-* |
| confirm_destructive | file-delete / voice-delete |

### 阻断机制

- 后端 `CapabilityInvoker.invoke()` 在实际调用 MiniMax API 前通过 RiskGate 评估
- 未满足条件返回 `error_type: risk_gate_blocked`
- 前端在未勾选所有必需确认项时禁用 Invoke 按钮

## 7. History 与可追踪性

### 存储路径

```
backend/runtime/test_console/history.jsonl
```

### 脱敏规则

- 不保存完整 payload，只保存摘要
- 敏感 key（api_key / token / password / secret 等）递归脱敏
- 支持嵌套结构深度脱敏（最大深度 10 层）

### 脱敏字段

```python
敏感 key 模式（不区分大小写）:
- api_key / api-key / apikey
- token
- password / passwd
- secret
- authorization / auth
- credential
- private_key / private-key
```

### 文件管理

- 单文件最大 2MB
- 超过时 compact，保留最后 1000 行
- runtime 目录 `.gitignore` 排除，不提交

## 8. Asset Result Preview

### 支持类型

| 类型 | 展示方式 |
|---|---|
| JSON（普通） | JsonView fallback |
| 图片 URL（http/https） | `<img>` 预览，支持长 URL 不截断 |
| 音频 URL（http/https，.mp3/.wav 等） | `<audio controls>` |
| 音频 URL（长文本） | 完整 URL，不截断 |
| file_id / task_id | 文件/任务信息卡片 |

### 校验结果

```bash
python scripts/check_history_store.py
# All tests PASSED
```

## 9. 当前不纳入默认执行的能力

| 能力 | scope | 原因 |
|---|---|---|
| video-t2v / video-i2v / video-s2v | out_of_scope | Token Plan 之外 |
| video-query / video-download | warning_only | 已有任务操作 |
| voice-clone-upload-audio | warning_only | 付费 + 素材 |
| voice-clone-upload-prompt | warning_only | 付费 + 素材 |
| voice-clone-do | warning_only | 付费 + 素材 |
| voice-design | warning_only | 付费 |
| music-cover-prep | warning_only | 素材型 |
| file-delete | warning_only | 破坏性 |
| voice-delete | warning_only | 破坏性 |

## 10. 已知限制

1. **tts-async 字符数保护**：> 5000 字硬阻断，即使 confirm_quota 也无法绕过
2. **MiniMax API HTTP 200 ≠ 业务成功**：需检查 `base_resp.status_code`
3. **highspeed 模型协议**：MiniMax-M2.7-highspeed 等仅支持 openai / anthropic，不支持 responses
4. **speech 模型不可发现**：`/v1/models` 不返回 speech 模型，不代表不可用（通过 capability probe 验证）

## 11. 后续路线

当前阶段（Token Plan 能力全量盘点 + 验收）已完成。后续优先方向：

1. **Test Console 交互体验**：增强能力搜索、批量 Risk Check、history 搜索过滤
2. **Asset Result Preview**：支持视频 URL 预览、多图网格、文件下载
3. **History 详情**：支持展开完整 payload preview、导出 CSV/JSON
4. **minimax_core 沉淀**：整理为可 pip install 的 Python 包
5. **产品入口**：Voice Lab / 图片工具 / 音乐工具 / 文件知识库等产品级入口

## 12. 合并前验收命令

```bash
git status --short
python -m compileall backend/app
python scripts/check_history_store.py
python scripts/check_capability_descriptions.py
cd frontend && npm run build && cd ..
```

所有命令通过后方可合并。

---

## 提交记录

| 提交 | 说明 |
|---|---|
| `6f2df82` | fix: preserve audio asset urls |
| `e2e162b` | feat: preview asset results in test console |
| `b1ec819` | test: validate capability descriptions |
| `b2e1960` | feat: add capability descriptions |
| `4ade606` | fix: convert nested Pydantic models to dicts in _spec_to_capability |
| `docs` | docs: summarize test console and capability layer |
