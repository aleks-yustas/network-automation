from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AppConfig:
    database_dsn: str
    worker_id: str
    poll_interval_sec: float = 2.0
    default_job_timeout_sec: int = 300
    backoff_base_sec: int = 60
    backoff_max_sec: int = 3600
    artifact_dir: Path = Path("/var/lib/netops/artifacts")


def load_yaml(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain YAML mapping")
    return data


def load_config(path: Path | None = None) -> AppConfig:
    data = load_yaml(path)
    database_dsn = os.getenv("NETOPS_DATABASE_DSN") or data.get("database_dsn")
    if not database_dsn:
        raise ValueError("NETOPS_DATABASE_DSN or database_dsn is required")

    return AppConfig(
        database_dsn=database_dsn,
        worker_id=os.getenv("NETOPS_WORKER_ID") or data.get("worker_id") or os.uname().nodename,
        poll_interval_sec=float(os.getenv("NETOPS_POLL_INTERVAL_SEC") or data.get("poll_interval_sec", 2.0)),
        default_job_timeout_sec=int(os.getenv("NETOPS_DEFAULT_JOB_TIMEOUT_SEC") or data.get("default_job_timeout_sec", 300)),
        backoff_base_sec=int(os.getenv("NETOPS_BACKOFF_BASE_SEC") or data.get("backoff_base_sec", 60)),
        backoff_max_sec=int(os.getenv("NETOPS_BACKOFF_MAX_SEC") or data.get("backoff_max_sec", 3600)),
        artifact_dir=Path(os.getenv("NETOPS_ARTIFACT_DIR") or data.get("artifact_dir", "/var/lib/netops/artifacts")),
    )

