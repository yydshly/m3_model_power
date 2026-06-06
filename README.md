# MiniMax 能力聚合工作台

把 MiniMax TokenPlanPlus 极速版会员里**所有 32 个公开 API**统一登记、统一访问。
能力 / 模型清单由 YAML 配置驱动，前端动态渲染，未实现的能力也会出现在目录里并给出文档链接。

## 设计原则

- **配置即架构**：能力图谱与模型清单全在 `backend/config/*.yaml`，前端只是渲染器
- **三态显式**：每个 capability 标记 `implemented` / `planned` / `unsupported`，用户永远知道"能不能用、为什么"
- **handler 解耦**：新增一个能力 = 改 YAML + 写一个 `@register_handler("xxx-id")` 函数；前端无需任何改动
- **凭证不出后端**：API Key 仅在 backend `.env`，前端走 `/api/invoke/<cap_id>` 代理

## 仓库结构

```
backend/
  config/
    capabilities.yaml      ← 32 个接口的事实来源
    models.yaml            ← M3 / M2.7 / abab / speech / image / video / music 模型清单
  app/
    registry/              ← YAML 加载 + handler 注册
    capabilities/          ← 各能力 handler 实现（按域分文件）
    routers/               ← health / registry / invoke
    minimax/client.py      ← 统一鉴权 + JSON/字节/SSE 三种发送方式
frontend/
  src/
    pages/                 ← Overview / Category / Capability / Models
    components/            ← StatusBadge / InvokePanel / JsonView
    store.tsx              ← /api/registry 缓存
```

## 当前进度

**已实现 31 / 32**（仅 `tts-ws` 因需 WS 代理仍为 planned）

| 分类 | 接口 |
|---|---|
| 对话 | anthropic / openai / responses-create / responses-tokens（含 SSE 流式） |
| 语音 | tts-sync / tts-async / voice-list / voice-delete / voice-design / voice-clone-do（音色克隆触发） |
| 语音上传 | voice-clone-upload-audio / voice-clone-upload-prompt（multipart） |
| 视觉 | image-t2i / image-i2i / video-t2v / video-i2v / video-s2v / video-query / video-download |
| 音乐 | music-gen / lyrics-gen / music-cover-prep（multipart） |
| 资产 | file-upload（multipart）/ file-list / file-retrieve / file-content / file-delete |
| 模型 | OpenAI list+retrieve / Anthropic list+retrieve |
| 待实现 | tts-ws（需 WebSocket 代理） |

## 三种调用通道

| 类型 | 路由 | 触发条件 |
|---|---|---|
| 同步 | `POST /api/invoke/{cap_id}` | 默认；JSON 入参 JSON 出参 |
| 流式 | `POST /api/stream/{cap_id}` | capability.streaming=true，SSE 透传 |
| 上传 | `POST /api/upload/{cap_id}` | capability.multipart=true，前端选文件 |

详情页 [Capability.tsx](frontend/src/pages/Capability.tsx) 会自动根据配置切换面板。

## 添加新能力的工作量（设计目标）

1. `capabilities.yaml` 加一条（id / category / status / example / streaming? / multipart? …）
2. 写一个 handler：
   ```python
   @register_handler("xxx-id")
   async def my_handler(p: dict):
       return await post_json("/v1/xxx", p, with_group=True)
   ```
3. `POST /api/registry/reload`（或重启 uvicorn）

前端代码恒定为零修改。

## 启动

```bash
# 后端
cd backend
cp .env.example .env   # 填入 MINIMAX_API_KEY / MINIMAX_GROUP_ID
pip install -e .
uvicorn app.main:app --reload --port 8000

# 前端（另一个终端）
cd frontend
npm install
npm run dev            # http://localhost:5173
```

落地计划详情：`C:\Users\yun68\.claude\plans\polished-seeking-mango.md`
