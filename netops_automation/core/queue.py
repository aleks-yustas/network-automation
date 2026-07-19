from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from psycopg import Connection
from psycopg.types.json import Jsonb

from netops_automation.core.config import AppConfig
from netops_automation.core.models import Job, JobStatus


class QueueManager:
    def __init__(self, conn: Connection, config: AppConfig):
        self.conn = conn
        self.config = config

    def enqueue(
        self,
        *,
        job_type: str,
        scenario: str,
        transport: str,
        payload: dict[str, Any],
        device_id: UUID | None = None,
        priority: int = 100,
        max_attempts: int = 3,
        timeout_sec: int | None = None,
        expires_at: datetime | None = None,
        idempotency_key: str | None = None,
        run_after: datetime | None = None,
    ) -> UUID | None:
        timeout = timeout_sec or self.config.default_job_timeout_sec
        run_at = run_after or datetime.now(UTC)
        with self.conn.transaction():
            row = self.conn.execute(
                """
                INSERT INTO netops_jobs (
                    job_type, device_id, scenario, transport, status, priority,
                    max_attempts, timeout_sec, expires_at, run_after, idempotency_key, payload
                )
                VALUES (%s, %s, %s, %s, 'NEW', %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING id
                """,
                (
                    job_type,
                    device_id,
                    scenario,
                    transport,
                    priority,
                    max_attempts,
                    timeout,
                    expires_at,
                    run_at,
                    idempotency_key,
                    Jsonb(payload),
                ),
            ).fetchone()
            if row is None:
                return None
            self.add_event(row["id"], "NEW", "job enqueued")
            return row["id"]

    def lease_next(self) -> Job | None:
        with self.conn.transaction():
            self._expire_waiting_jobs()
            row = self.conn.execute(
                """
                SELECT *
                FROM netops_jobs
                WHERE status IN ('NEW', 'RETRY')
                  AND run_after <= now()
                  AND (expires_at IS NULL OR expires_at > now())
                ORDER BY priority DESC, run_after ASC, created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            self.conn.execute(
                """
                UPDATE netops_jobs
                SET status = 'RUNNING',
                    attempt = attempt + 1,
                    locked_by = %s,
                    locked_at = now(),
                    started_at = COALESCE(started_at, now()),
                    updated_at = now()
                WHERE id = %s
                """,
                (self.config.worker_id, row["id"]),
            )
            self.add_event(row["id"], "RUNNING", f"leased by {self.config.worker_id}")
            row["status"] = "RUNNING"
            row["attempt"] += 1
            row["locked_by"] = self.config.worker_id
            return _job_from_row(row)

    def mark_done(self, job_id: UUID, result: dict[str, Any]) -> None:
        self._finish(job_id, JobStatus.DONE, result=result)

    def mark_skipped(self, job_id: UUID, message: str) -> None:
        self._finish(job_id, JobStatus.SKIPPED, result={"message": message})

    def mark_failed(self, job: Job, error_code: str, error_message: str, retryable: bool) -> None:
        retry_window_open = job.expires_at is None or job.expires_at > datetime.now(UTC)
        next_status = JobStatus.RETRY if retryable and retry_window_open and job.attempt < job.max_attempts else JobStatus.FAILED
        if retryable and not retry_window_open:
            next_status = JobStatus.SKIPPED
            error_message = f"{error_message}; retry window expired"
        delay = self._backoff_delay(job.attempt) if next_status == JobStatus.RETRY else None
        with self.conn.transaction():
            self.conn.execute(
                """
                UPDATE netops_jobs
                SET status = %s,
                    run_after = CASE WHEN %s::interval IS NULL THEN run_after ELSE now() + %s::interval END,
                    locked_by = NULL,
                    locked_at = NULL,
                    error_code = %s,
                    error_message = %s,
                    updated_at = now(),
                    finished_at = CASE WHEN %s IN ('FAILED', 'SKIPPED') THEN now() ELSE finished_at END
                WHERE id = %s
                """,
                (next_status.value, delay, delay, error_code, error_message, next_status.value, job.id),
            )
            self.add_event(job.id, next_status.value, error_message)

    def recover_stale_running(self) -> int:
        with self.conn.transaction():
            rows = self.conn.execute(
                """
                UPDATE netops_jobs
                SET status = CASE
                        WHEN attempt < max_attempts THEN 'RETRY'
                        ELSE 'TIMEOUT'
                    END,
                    run_after = CASE
                        WHEN attempt < max_attempts THEN now() + make_interval(secs => %s)
                        ELSE run_after
                    END,
                    locked_by = NULL,
                    locked_at = NULL,
                    error_code = 'worker_lost',
                    error_message = 'RUNNING job exceeded timeout or worker restarted',
                    updated_at = now(),
                    finished_at = CASE WHEN attempt >= max_attempts THEN now() ELSE finished_at END
                WHERE status = 'RUNNING'
                  AND locked_at + make_interval(secs => timeout_sec) < now()
                RETURNING id, status
                """,
                (self.config.backoff_base_sec,),
            ).fetchall()
            for row in rows:
                self.add_event(row["id"], row["status"], "stale RUNNING recovered")
            return len(rows)

    def add_event(self, job_id: UUID, status: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.conn.execute(
            """
            INSERT INTO netops_job_events (job_id, status, message, details)
            VALUES (%s, %s, %s, %s)
            """,
                (job_id, status, message, Jsonb(details or {})),
        )

    def _finish(self, job_id: UUID, status: JobStatus, result: dict[str, Any]) -> None:
        with self.conn.transaction():
            self.conn.execute(
                """
                UPDATE netops_jobs
                SET status = %s,
                    result = %s,
                    locked_by = NULL,
                    locked_at = NULL,
                    updated_at = now(),
                    finished_at = now()
                WHERE id = %s
                """,
                (status.value, Jsonb(result), job_id),
            )
            self.add_event(job_id, status.value, result.get("message", "job finished"))

    def _backoff_delay(self, attempt: int) -> str:
        seconds = min(self.config.backoff_base_sec * (2 ** max(attempt - 1, 0)), self.config.backoff_max_sec)
        return str(timedelta(seconds=seconds))

    def _expire_waiting_jobs(self) -> None:
        rows = self.conn.execute(
            """
            UPDATE netops_jobs
            SET status = 'SKIPPED',
                locked_by = NULL,
                locked_at = NULL,
                error_code = 'expired',
                error_message = 'job retry window expired',
                updated_at = now(),
                finished_at = now()
            WHERE status IN ('NEW', 'RETRY')
              AND expires_at IS NOT NULL
              AND expires_at <= now()
            RETURNING id
            """
        ).fetchall()
        for row in rows:
            self.add_event(row["id"], "SKIPPED", "job retry window expired")


def _job_from_row(row: dict[str, Any]) -> Job:
    return Job(
        id=row["id"],
        job_type=row["job_type"],
        scenario=row["scenario"],
        transport=row["transport"],
        status=JobStatus(row["status"]),
        device_id=row["device_id"],
        payload=row["payload"] or {},
        attempt=row["attempt"],
        max_attempts=row["max_attempts"],
        timeout_sec=row["timeout_sec"],
        expires_at=row["expires_at"],
        priority=row["priority"],
        run_after=row["run_after"],
        locked_by=row.get("locked_by"),
        locked_at=row.get("locked_at"),
    )
