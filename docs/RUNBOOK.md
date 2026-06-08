# m3_model_power Runbook

## 最短启动

```bash
python start.py
```

这会启动后端（8777）和前端（5175），并等待两端就绪后输出入口地址。

如果检测到后端已经健康运行（`/api/health` 返回 200），脚本会**复用**已有后端进程，不会重复启动。
如果检测到前端已经可访问，脚本会**复用**已有前端进程。

---

## 默认启动行为

`python start.py`（即 `python start.py dev`）的完整流程：

1. 检查 8777 端口：
   - 若空闲：启动后端 uvicorn 进程，等待 `/api/health` 返回 200
   - 若被占用且健康：复用已有后端，打印 `[INFO] Backend already running`
   - 若被占用但不健康：打印错误并退出，提示先释放端口
2. 检查 5175 端口：
   - 若空闲：启动前端 Vite 进程
   - 若被占用且可访问：复用已有前端，打印 `[INFO] Frontend already running`
   - 若被占用但不可访问：打印错误并退出，提示先释放端口
3. 打印所有页面入口地址
4. `Ctrl+C` 只会停止**本次启动器创建的子进程**，不会停止复用（已有）的旧进程

---

## 常见提示解释

| 提示 | 含义 |
|------|------|
| `[INFO] Backend already running on 127.0.0.1:8777 — reusing it.` | 脚本检测到 8777 已有健康后端，复用而非重启 |
| `[WARN] Port 8777 occupied (unknown process)` | 端口被占用但不是本项目后端，脚本无法判断其身份 |
| `[FAIL] Port 8777 is occupied by unknown process` | 脚本检测到端口被占用且不可访问，阻止启动 |
| `[WARN] frontend/node_modules not found` | 需先运行 `python start.py install` |
| `[INFO] Frontend already running on http://localhost:5175` | 脚本检测到前端已可访问，复用而非重启 |
| `Press Ctrl+C to stop processes started by this launcher.` | Ctrl+C 只停止本次启动的子进程；复用进程需手动停止 |

---

## 首次安装

```bash
python start.py install
```

依次执行：
- `pip install --upgrade pip`
- `pip install -e backend`
- `npm ci`（安装 frontend/node_modules）

---

## 环境检查

```bash
python start.py doctor
```

检查项：Python 版本、Node 版本、npm 版本、app.main 能否导入、8777/5175 端口是否占用、node_modules 是否存在。

---

## 快速检查（不启动服务）

```bash
python start.py check
```

运行：
- `check_runtime_smoke.py`
- `check_project_overview_page.py`
- `check_github_actions_ci_yaml.py`
- `check_history_result_summary.py`
- `python -m compileall backend scripts`
- `npm run build`（frontend 类型检查 + 构建）

---

## 后端单独启动

```bash
python start.py backend
```

启动 FastAPI 后端到 `http://127.0.0.1:8777`。

---

## 前端单独启动

```bash
python start.py frontend
```

启动 Vite 前端到 `http://localhost:5175`。

---

## 构建（不启动）

```bash
python start.py build
```

执行 `compileall` + `npm run build`。

---

## 清理运行时文件

```bash
python start.py clean
```

清理内容：
- `backend/runtime/test_console/history.jsonl`
- `backend/runtime/diagnostics/trace.jsonl`
- `frontend/node_modules/.vite`

**不删除**：`backend/runtime/assets`、`frontend/node_modules`（除 `.vite` 外）、`.env`。

---

## 查看端口占用

```bash
python start.py stop
```

显示 8777 和 5175 端口的占用进程 PID，**不会自动 kill**。

```bash
python start.py stop --kill
```

传入 `--kill` 参数才会尝试停止进程（Windows: `taskkill`）。

---

## 常用页面入口

| 路径 | 说明 |
|------|------|
| `/` | 总览：验收进度、最近调用、风险说明 |
| `/project-overview` | 项目说明：项目定位、能力范围、架构、技术要点 |
| `/test-console` | 高级测试：Raw JSON、RiskGate、开发者模式 |
| `/capability-runner` | 能力体验：低门槛能力调用入口 |
| `/models-all` | 所有模型：项目已建模的模型列表 |
| `/capability-scenarios` | 场景推荐：按场景组织能力 |
| `/capability-profiles` | 能力画像：能力适用模型、风险、输出说明 |

---

## 端口占用处理

后端默认 `8777`，前端默认 `5175`。

脚本行为原则：**不自动 kill**。只有显式传入 `--kill` 才会尝试停止进程。

### Windows 手动排查

```powershell
# 查看端口占用
netstat -ano | findstr :8777
netstat -ano | findstr :5175

# 查看进程名
tasklist /FI "PID eq <PID>"

# 手动 kill（替换 <PID> 为实际进程号）
taskkill //PID <PID> //F
```

### Linux / Git Bash 手动排查

```bash
# 查看端口占用
ss -tlnp | grep 8777
ss -tlnp | grep 5175

# kill
kill <PID>
```

---

## /api/history/probe 404 排查

`/api/history/probe` 是历史记录探针接口：

1. 确认后端已启动：`curl http://127.0.0.1:8777/api/health`
2. 确认 `backend/runtime/test_console/history.jsonl` 目录存在
3. 查看后端日志是否有 `history_append` 相关错误

---

## 禁止提交文件

以下文件/目录**不得**提交到 git：

| 路径 | 原因 |
|------|------|
| `.env` | 包含 API Key 等敏感信息 |
| `backend/runtime/test_console/history.jsonl` | 本地调用历史，含真实调用数据 |
| `backend/runtime/diagnostics/trace.jsonl` | 链路追踪日志 |
| `backend/runtime/assets/` 下的真实媒体文件 | 测试生成的音频/图片等 |
| `frontend/node_modules/` | 依赖包，由 `npm ci` 安装 |
| `frontend/dist/` | 构建产物，由 `npm run build` 生成 |

这些已全部列入 `.gitignore`，如发现被跟踪请立即清除。

---

## 命令一览

| 命令 | 说明 |
|------|------|
| `python start.py` | 默认 dev 模式（后端 + 前端） |
| `python start.py doctor` | 环境检查 |
| `python start.py install` | 安装依赖 |
| `python start.py backend` | 仅后端 |
| `python start.py frontend` | 仅前端 |
| `python start.py check` | 快速检查脚本 |
| `python start.py build` | 构建验证 |
| `python start.py clean` | 清理运行时文件 |
| `python start.py stop` | 查看端口占用 |
| `python start.py stop --kill` | 查看并尝试停止占用端口的进程 |
