"""API routes for raphael-analytics — platform metrics overview."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter

from raphael_analytics.store import MetricsCacheStore

router = APIRouter(tags=["raphael-analytics"])
_store = MetricsCacheStore()


def _fetch_json(url: str) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=8.0) as client:
            res = client.get(url)
            if res.status_code == 200:
                return res.json()
    except httpx.HTTPError:
        pass
    return {}


def _aggregate_overview(workspace_id: str) -> dict[str, Any]:
    audit = os.environ.get("RAPHAEL_AUDIT_URL", "http://127.0.0.1:8093").rstrip("/")
    ws = os.environ.get("RAPHAEL_WORKSPACES_URL", "http://127.0.0.1:8083").rstrip("/")
    auto = os.environ.get("RAPHAEL_AUTOMATION_URL", "http://127.0.0.1:8095").rstrip("/")
    reviews = os.environ.get("RAPHAEL_REVIEWS_URL", "http://127.0.0.1:8087").rstrip("/")

    timeline = _fetch_json(f"{audit}/v1/audit/timeline?limit=500")
    modules = _fetch_json(f"{ws}/v1/workspaces/{workspace_id}/modules")
    automations = _fetch_json(f"{auto}/v1/automations")
    review_list = _fetch_json(f"{reviews}/v1/reviews")

    events = timeline.get("events", [])
    event_types: dict[str, int] = {}
    for ev in events:
        t = ev.get("event_type") or "unknown"
        event_types[t] = event_types.get(t, 0) + 1

    return {
        "workspace_id": workspace_id,
        "modules": len(modules.get("modules", [])),
        "events_total": len(events),
        "event_types_top": sorted(event_types.items(), key=lambda x: -x[1])[:8],
        "automations": len(automations.get("automations", [])),
        "reviews": len(review_list.get("reviews", [])),
        "health": "ok",
    }


@router.get("")
def list_metrics(workspace_id: str = "default") -> dict[str, Any]:
    metrics = _store.list_metrics(workspace_id)
    if not metrics:
        overview = _aggregate_overview(workspace_id)
        _store.save_snapshot(workspace_id, overview)
        metrics = _store.list_metrics(workspace_id)
    return {"service": "raphael-analytics", "workspace_id": workspace_id, "metrics": metrics}


@router.get("/overview")
def overview(workspace_id: str = "default") -> dict[str, Any]:
    body = _aggregate_overview(workspace_id)
    _store.save_snapshot(workspace_id, body)
    return body
