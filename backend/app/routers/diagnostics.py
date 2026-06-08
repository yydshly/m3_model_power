"""Diagnostics trace API — trace events for history chain observability."""
from __future__ import annotations

from fastapi import APIRouter

from ..minimax_core.verification.diagnostics_store import (
    get_diagnostics_status,
    list_trace_events,
)

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("/status")
async def diagnostics_status() -> dict:
    """Return diagnostics trace file status."""
    return get_diagnostics_status()


@router.get("/trace/{trace_id}")
async def diagnostics_trace(trace_id: str) -> dict:
    """Return all trace events for the given trace_id."""
    return {"trace_id": trace_id, "events": list_trace_events(trace_id)}
