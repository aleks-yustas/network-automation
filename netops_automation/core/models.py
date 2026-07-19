from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class JobStatus(StrEnum):
    NEW = "NEW"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    RETRY = "RETRY"
    SKIPPED = "SKIPPED"
    TIMEOUT = "TIMEOUT"


@dataclass(frozen=True)
class Job:
    id: UUID
    job_type: str
    scenario: str
    transport: str
    status: JobStatus
    device_id: UUID | None
    payload: dict[str, Any]
    attempt: int
    max_attempts: int
    timeout_sec: int
    expires_at: datetime | None
    priority: int
    run_after: datetime
    locked_by: str | None = None
    locked_at: datetime | None = None


@dataclass(frozen=True)
class ScenarioResult:
    status: str = "ok"
    message: str = ""
    data: bytes | str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
