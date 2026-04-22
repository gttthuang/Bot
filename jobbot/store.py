from __future__ import annotations

from pathlib import Path
import json
import sqlite3

from .models import JobStatus, SourceRunStats, StoredJobState


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  source_name TEXT NOT NULL,
  external_id TEXT NOT NULL,
  status TEXT NOT NULL,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  missing_count INTEGER NOT NULL DEFAULT 0,
  closed_at TEXT,
  content_hash TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  PRIMARY KEY (source_name, external_id)
);

CREATE TABLE IF NOT EXISTS crawl_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_name TEXT NOT NULL,
  run_at TEXT NOT NULL,
  discovered_count INTEGER NOT NULL DEFAULT 0,
  created_count INTEGER NOT NULL DEFAULT 0,
  updated_count INTEGER NOT NULL DEFAULT 0,
  closed_count INTEGER NOT NULL DEFAULT 0,
  notified_count INTEGER NOT NULL DEFAULT 0,
  error TEXT
);
"""


class SQLiteStore:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def load_states_for_source(self, source_name: str) -> dict[str, StoredJobState]:
        rows = self.connection.execute(
            """
            SELECT source_name, external_id, status, first_seen_at, last_seen_at,
                   missing_count, closed_at, content_hash, payload_json
            FROM jobs
            WHERE source_name = ?
            """,
            (source_name,),
        ).fetchall()

        return {
            row["external_id"]: StoredJobState(
                source_name=row["source_name"],
                external_id=row["external_id"],
                status=JobStatus(row["status"]),
                first_seen_at=row["first_seen_at"],
                last_seen_at=row["last_seen_at"],
                missing_count=int(row["missing_count"]),
                closed_at=row["closed_at"],
                content_hash=row["content_hash"],
                payload=json.loads(row["payload_json"]),
            )
            for row in rows
        }

    def save_state(self, state: StoredJobState) -> None:
        self.connection.execute(
            """
            INSERT INTO jobs (
              source_name,
              external_id,
              status,
              first_seen_at,
              last_seen_at,
              missing_count,
              closed_at,
              content_hash,
              payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_name, external_id) DO UPDATE SET
              status = excluded.status,
              first_seen_at = excluded.first_seen_at,
              last_seen_at = excluded.last_seen_at,
              missing_count = excluded.missing_count,
              closed_at = excluded.closed_at,
              content_hash = excluded.content_hash,
              payload_json = excluded.payload_json
            """,
            (
                state.source_name,
                state.external_id,
                state.status.value,
                state.first_seen_at,
                state.last_seen_at,
                state.missing_count,
                state.closed_at,
                state.content_hash,
                json.dumps(state.payload, ensure_ascii=False, sort_keys=True),
            ),
        )
        self.connection.commit()

    def record_run(self, run_at: str, stats: SourceRunStats) -> None:
        self.connection.execute(
            """
            INSERT INTO crawl_runs (
              source_name, run_at, discovered_count, created_count, updated_count,
              closed_count, notified_count, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stats.source_name,
                run_at,
                stats.discovered_count,
                stats.created_count,
                stats.updated_count,
                stats.closed_count,
                stats.notified_count,
                stats.error,
            ),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
