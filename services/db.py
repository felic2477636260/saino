import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from config.settings import get_settings


logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: Path | None = None) -> None:
        settings = get_settings()
        self.db_path = Path(db_path or settings.database_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        schema_path = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
        with self.connect() as conn:
            conn.executescript(schema_path.read_text(encoding="utf-8"))
            self._apply_migrations(conn)
        logger.info("database initialized at %s", self.db_path)

    def _apply_migrations(self, conn: sqlite3.Connection) -> None:
        self._ensure_column(conn, "evidence_chunk", "chunk_index", "INTEGER DEFAULT 0")
        self._ensure_column(conn, "evidence_chunk", "section_title", "TEXT DEFAULT ''")
        self._ensure_column(conn, "evidence_chunk", "section_path", "TEXT DEFAULT ''")
        self._ensure_column(conn, "evidence_chunk", "metadata_json", "TEXT DEFAULT '{}'")
        self._ensure_column(conn, "evidence_chunk", "char_count", "INTEGER DEFAULT 0")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_section_path ON evidence_chunk(section_path)")

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        existing = {row["name"] for row in rows}
        if column_name in existing:
            return
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def execute(self, query: str, params: Iterable[Any] = ()) -> None:
        with self.connect() as conn:
            conn.execute(query, tuple(params))
            conn.commit()

    def executemany(self, query: str, rows: list[tuple[Any, ...]]) -> None:
        if not rows:
            return
        with self.connect() as conn:
            conn.executemany(query, rows)
            conn.commit()

    def fetchall(self, query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return rows

    def fetchone(self, query: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        with self.connect() as conn:
            row = conn.execute(query, tuple(params)).fetchone()
        return row

    def upsert_task(
        self,
        task_id: str,
        company_code: str,
        query: str,
        task_type: str,
        status: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        self.execute(
            """
            INSERT OR REPLACE INTO analysis_task(task_id, company_code, query, task_type, status, result_json)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (task_id, company_code, query, task_type, status, json.dumps(result or {}, ensure_ascii=False)),
        )

    def log_skill(self, task_id: str, skill_name: str, skill_type: str, status: str, message: str = "") -> None:
        self.execute(
            """
            INSERT INTO skill_execution_log(task_id, skill_name, skill_type, status, message)
            VALUES(?, ?, ?, ?, ?)
            """,
            (task_id, skill_name, skill_type, status, message),
        )

    def list_recent_tasks(self, limit: int = 6) -> list[dict[str, Any]]:
        rows = self.fetchall(
            """
            SELECT task_id, company_code, query, status, result_json, created_at
            FROM analysis_task
            WHERE task_type = 'analyze'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            {
                "task_id": row["task_id"],
                "company_code": row["company_code"],
                "query": row["query"],
                "status": row["status"],
                "created_at": row["created_at"],
                "report_title": self._decode_result_json(row["result_json"]).get("report_title", ""),
            }
            for row in rows
        ]

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        row = self.fetchone(
            """
            SELECT task_id, company_code, query, task_type, status, result_json, created_at
            FROM analysis_task
            WHERE task_id = ?
            """,
            (task_id,),
        )
        if not row:
            return None
        return {
            "task_id": row["task_id"],
            "company_code": row["company_code"],
            "query": row["query"],
            "task_type": row["task_type"],
            "status": row["status"],
            "created_at": row["created_at"],
            "result": self._decode_result_json(row["result_json"]),
        }

    def get_task_result(self, task_id: str) -> dict[str, Any] | None:
        row = self.fetchone("SELECT result_json FROM analysis_task WHERE task_id = ?", (task_id,))
        if not row or not row["result_json"]:
            return None
        result = self._decode_result_json(row["result_json"])
        return result or None

    def clear_analysis_history(self) -> int:
        task_rows = self.fetchall("SELECT task_id FROM analysis_task WHERE task_type = 'analyze'")
        task_ids = [row["task_id"] for row in task_rows]
        if not task_ids:
            return 0

        placeholders = ",".join("?" for _ in task_ids)
        with self.connect() as conn:
            conn.execute(f"DELETE FROM risk_result WHERE task_id IN ({placeholders})", task_ids)
            conn.execute(f"DELETE FROM skill_execution_log WHERE task_id IN ({placeholders})", task_ids)
            conn.execute("DELETE FROM analysis_task WHERE task_type = 'analyze'")
            conn.commit()
        return len(task_ids)

    def clear_system_cache(self) -> dict[str, int]:
        with self.connect() as conn:
            counts = {
                "analysis_tasks": self._count_rows(conn, "analysis_task"),
                "risk_results": self._count_rows(conn, "risk_result"),
                "skill_logs": self._count_rows(conn, "skill_execution_log"),
                "report_evaluations": self._count_rows(conn, "report_eval_result"),
                "parsed_documents": self._count_rows(conn, "report_meta"),
                "parsed_pages": self._count_rows(conn, "document_page"),
                "evidence_chunks": self._count_rows(conn, "evidence_chunk"),
                "company_records": self._count_rows(conn, "company"),
            }
            conn.execute("DELETE FROM report_eval_result")
            conn.execute("DELETE FROM skill_execution_log")
            conn.execute("DELETE FROM risk_result")
            conn.execute("DELETE FROM analysis_task")
            conn.execute("DELETE FROM evidence_chunk")
            conn.execute("DELETE FROM document_page")
            conn.execute("DELETE FROM report_meta")
            conn.execute("DELETE FROM company")
            conn.commit()
        return counts

    @staticmethod
    def _count_rows(conn: sqlite3.Connection, table_name: str) -> int:
        row = conn.execute(f"SELECT COUNT(*) AS total FROM {table_name}").fetchone()
        if not row:
            return 0
        return int(row["total"])

    def _decode_result_json(self, result_json: str | None) -> dict[str, Any]:
        if not result_json:
            return {}
        try:
            data = json.loads(result_json)
        except json.JSONDecodeError:
            logger.warning("failed to decode result_json payload")
            return {}
        return data if isinstance(data, dict) else {}
