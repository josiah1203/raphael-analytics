"""API routes for raphael-analytics."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["raphael-analytics"])


@router.get("")
def list_root() -> dict[str, str]:
  return {"service": "raphael-analytics", "status": "stub"}
