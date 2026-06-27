"""Cached analytics metrics store — Postgres dual-path with SQLite test fallback."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MetricsCacheStore:
    def __init__(self, db_path: Path | None = None) -> None:
        from raphael_contracts import db as rdb

        self._postgres = rdb.is_postgres()
        if self._postgres:
            rdb.ensure_migrations()
            self.db_path = Path("postgres")
        else:
            path = db_path or Path(
                os.environ.get("RAPHAEL_ANALYTICS_DB", "/tmp/raphael-analytics.db")
            )
            self.db_path = path
            self._init_sqlite()

    def _connect_sqlite(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self) -> None:
        with self._connect_sqlite() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics_metrics_cache (
                    workspace_id TEXT NOT NULL,
                    metric_key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (workspace_id, metric_key)
                )
                """
            )
            conn.commit()

    def save_snapshot(self, workspace_id: str, overview: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        metrics = {
            "modules": overview.get("modules", 0),
            "events_total": overview.get("events_total", 0),
            "automations": overview.get("automations", 0),
            "reviews": overview.get("reviews", 0),
            "event_types_top": overview.get("event_types_top", []),
            "health": overview.get("health", "ok"),
        }
        for key, value in metrics.items():
            payload = json.dumps(value)
            if self._postgres:
                from raphael_contracts.db import pg_execute

                pg_execute(
                    """
                    INSERT INTO analytics_metrics_cache (workspace_id, metric_key, value_json, updated_at)
                    VALUES (%s, %s, %s::jsonb, %s)
                    ON CONFLICT (workspace_id, metric_key) DO UPDATE SET
                        value_json = EXCLUDED.value_json,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (workspace_id, key, payload, now),
                )
            else:
                with self._connect_sqlite() as conn:
                    conn.execute(
                        """
                        INSERT INTO analytics_metrics_cache (workspace_id, metric_key, value_json, updated_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(workspace_id, metric_key) DO UPDATE SET
                            value_json = excluded.value_json,
                            updated_at = excluded.updated_at
                        """,
                        (workspace_id, key, payload, now),
                    )
                    conn.commit()

    def list_metrics(self, workspace_id: str | None = None) -> list[dict[str, Any]]:
        ws = workspace_id or "default"
        if self._postgres:
            from raphael_contracts.db import pg_fetchall

            rows = pg_fetchall(
                """
                SELECT metric_key, value_json, updated_at
                FROM analytics_metrics_cache
                WHERE workspace_id = %s
                ORDER BY metric_key
                """,
                (ws,),
            )
        else:
            with self._connect_sqlite() as conn:
                rows = conn.execute(
                    """
                    SELECT metric_key, value_json, updated_at
                    FROM analytics_metrics_cache
                    WHERE workspace_id = ?
                    ORDER BY metric_key
                    """,
                    (ws,),
                ).fetchall()
        metrics: list[dict[str, Any]] = []
        for row in rows:
            value = row["value_json"]
            if isinstance(value, str):
                value = json.loads(value)
            metrics.append(
                {
                    "workspace_id": ws,
                    "key": row["metric_key"],
                    "value": value,
                    "updated_at": row["updated_at"],
                }
            )
        return metrics
