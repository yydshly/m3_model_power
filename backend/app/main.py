from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import capabilities  # noqa: F401 —— 触发 handler 注册
from .config import settings
from .minimax.client import MiniMaxError
from .routers import health, invoke, registry, risk_check, stream, upload, verification, ws

app = FastAPI(title="MiniMax Workbench", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(MiniMaxError)
async def _minimax_err(_: Request, exc: MiniMaxError) -> JSONResponse:
    return JSONResponse(
        status_code=502 if exc.status >= 500 else exc.status,
        content={"error": "minimax_error", "status": exc.status, "message": exc.message},
    )


@app.exception_handler(ValueError)
async def _value_err(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": "bad_request", "message": str(exc)})


app.include_router(health.router, prefix="/api")
app.include_router(registry.router, prefix="/api")
app.include_router(invoke.router, prefix="/api")
app.include_router(risk_check.router, prefix="/api")
app.include_router(stream.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(verification.router, prefix="/api")
app.include_router(ws.router, prefix="/api")


@app.get("/")
async def root() -> dict:
    return {"name": "MiniMax Workbench API", "docs": "/docs", "registry": "/api/registry"}
