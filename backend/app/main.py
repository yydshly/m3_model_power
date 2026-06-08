from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import capabilities  # noqa: F401 —— 触发 handler 注册
from .config import settings
from .minimax.client import MiniMaxError
from .minimax_core.verification.diagnostics_store import new_trace_id, append_trace_event
from .routers import descriptions, diagnostics, health, history, invoke, profiles, registry, risk_check, runner, scenarios, stream, upload, verification, workflows, ws

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
app.include_router(diagnostics.router, prefix="/api")
app.include_router(invoke.router, prefix="/api")
app.include_router(risk_check.router, prefix="/api")
app.include_router(stream.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(verification.router, prefix="/api")
app.include_router(ws.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(descriptions.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")
app.include_router(workflows.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")
app.include_router(runner.router, prefix="/api")


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    """Inject trace_id from header or generate new one; propagate in response."""
    trace_id = request.headers.get("X-MMW-Trace-ID") or new_trace_id()
    request.state.trace_id = trace_id

    append_trace_event(
        trace_id,
        "http_request_received",
        capability_id=None,
        action=None,
        data={"method": request.method, "path": request.url.path},
    )

    response = await call_next(request)
    response.headers["X-MMW-Trace-ID"] = trace_id

    append_trace_event(
        trace_id,
        "http_response_sent",
        status="ok" if response.status_code < 400 else "error",
        data={"status_code": response.status_code, "path": request.url.path},
    )

    return response


@app.get("/")
async def root() -> dict:
    return {"name": "MiniMax Workbench API", "docs": "/docs", "registry": "/api/registry"}
