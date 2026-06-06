# MiniMax Workbench Backend

## 启动

```bash
cd backend
cp .env.example .env   # 填入 MINIMAX_API_KEY / MINIMAX_GROUP_ID
pip install -e .       # 或 uv pip install -e .
uvicorn app.main:app --reload --port 8000
```

健康检查：`curl http://localhost:8000/api/health`
