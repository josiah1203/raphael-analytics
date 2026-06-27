"""Analytics domain tests."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from raphael_analytics.app import app


def test_overview_returns_aggregated_fields() -> None:
    client = TestClient(app)
    with patch("raphael_analytics.routes._fetch_json", return_value={}):
        res = client.get("/v1/analytics/overview?workspace_id=test-ws")
    assert res.status_code == 200
    body = res.json()
    assert body["workspace_id"] == "test-ws"
    assert body["health"] == "ok"
    assert "modules" in body
    assert "events_total" in body
    assert "event_types_top" in body
    assert "automations" in body
    assert "reviews" in body


def test_list_metrics_not_empty_after_overview(
    monkeypatch, tmp_path,
) -> None:
    monkeypatch.setenv("RAPHAEL_ANALYTICS_DB", str(tmp_path / "analytics.db"))
    from raphael_analytics.store import MetricsCacheStore
    import raphael_analytics.routes as routes

    routes._store = MetricsCacheStore(db_path=tmp_path / "analytics.db")
    client = TestClient(app)
    with patch("raphael_analytics.routes._fetch_json", return_value={"events": [], "modules": []}):
        overview = client.get("/v1/analytics/overview?workspace_id=metrics-ws")
    assert overview.status_code == 200

    metrics = client.get("/v1/analytics?workspace_id=metrics-ws")
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["service"] == "raphael-analytics"
    assert body["workspace_id"] == "metrics-ws"
    assert len(body["metrics"]) >= 5
    keys = {m["key"] for m in body["metrics"]}
    assert "events_total" in keys
    assert "modules" in keys


def test_overview_caches_event_type_counts() -> None:
    client = TestClient(app)
    fake_events = [
        {"event_type": "module.commit"},
        {"event_type": "module.commit"},
        {"event_type": "review.open"},
    ]
    with patch(
        "raphael_analytics.routes._fetch_json",
        side_effect=[
            {"events": fake_events},
            {"modules": [{"id": "m1"}]},
            {"automations": []},
            {"reviews": [{"id": "r1"}]},
        ],
    ):
        res = client.get("/v1/analytics/overview")
    body = res.json()
    assert body["events_total"] == 3
    assert body["modules"] == 1
    assert body["reviews"] == 1
    top = dict(body["event_types_top"])
    assert top["module.commit"] == 2
    assert top["review.open"] == 1
