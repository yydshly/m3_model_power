# MiniMax Workbench Backend

## 启动

```bash
cd backend
cp .env.example .env   # 填入 MINIMAX_API_KEY / MINIMAX_GROUP_ID
pip install -e .       # 或 uv pip install -e .
uvicorn app.main:app --reload --port 8000
```

健康检查：`curl http://localhost:8000/api/health`

## 风险门禁 API

### 门禁预检（不调用 MiniMax）

```bash
# 能力风险检查
curl -X POST http://localhost:8000/api/capabilities/{cap_id}/risk-check \
  -H "Content-Type: application/json" \
  -d '{"payload": {}, "confirmations": {}}'
```

### 带确认的执行调用

```bash
# 正式调用（RiskGate 仍会核验）
curl -X POST http://localhost:8000/api/invoke/{cap_id} \
  -H "Content-Type: application/json" \
  -d '{"payload": {}, "confirmations": {"confirm_paid": true}}'
```

确认项包括：`confirm_paid`, `confirm_high_cost`, `confirm_destructive`, `confirm_asset_source`, `confirm_long_running`, `confirm_existing_task`, `confirm_quota`。
