from __future__ import annotations

import argparse
import logging
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import yaml

from netops_automation.core.config import load_config
from netops_automation.core.db import connect
from netops_automation.core.queue import QueueManager

log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="NetOps Automation scheduler")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--schedule", required=True, type=Path)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = load_config(args.config)
    schedule = _load_schedule(args.schedule, args.name)

    with connect(config.database_dsn) as conn:
        queue = QueueManager(conn, config)
        devices = _select_devices(conn, schedule)
        created = skipped = 0
        for device in devices:
            credential = _load_credential(conn, schedule, device)
            payload = _build_payload(schedule, device, credential)
            job_id = queue.enqueue(
                job_type=schedule["job_type"],
                scenario=schedule["scenario"],
                transport=schedule["transport"],
                device_id=device["id"],
                payload=payload,
                priority=int(schedule.get("priority", 100)),
                max_attempts=int(schedule.get("max_attempts", 3)),
                timeout_sec=int(schedule.get("timeout_sec", config.default_job_timeout_sec)),
                expires_at=_expires_at(schedule, payload),
                idempotency_key=_idempotency_key(schedule, device),
            )
            if job_id is None:
                skipped += 1
            else:
                created += 1
        log.info("Schedule %s: created=%s skipped=%s", args.name, created, skipped)


def _load_schedule(path: Path, name: str) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    schedules = data.get("schedules", {})
    if name not in schedules:
        raise ValueError(f"schedule {name!r} not found in {path}")
    schedule = schedules[name]
    schedule["name"] = name
    return schedule


def _select_devices(conn, schedule: dict[str, Any]) -> list[dict[str, Any]]:
    selector = schedule.get("device_selector", {})
    where = ["enabled = true"]
    params = []
    for column in ("vendor", "model", "site", "region"):
        if selector.get(column):
            where.append(f"{column} = %s")
            params.append(selector[column])
    rows = conn.execute(
        f"SELECT * FROM netops_devices WHERE {' AND '.join(where)} ORDER BY name",
        params,
    ).fetchall()
    return list(rows)


def _load_credential(conn, schedule: dict[str, Any], device: dict[str, Any]) -> dict[str, Any]:
    purpose = schedule.get("credential_purpose")
    if not purpose:
        return {}
    row = conn.execute(
        """
        SELECT username, secret
        FROM netops_device_credentials
        WHERE device_id = %s AND purpose = %s
        """,
        (device["id"], purpose),
    ).fetchone()
    if row is None:
        log.warning("No credential for device=%s purpose=%s", device["name"], purpose)
        return {}
    secret = row["secret"] or {}
    return {"username": row["username"], **secret}


def _build_payload(schedule: dict[str, Any], device: dict[str, Any], credential: dict[str, Any]) -> dict[str, Any]:
    payload = dict(schedule.get("payload", {}))
    if payload.get("target_date") == "yesterday":
        payload["target_date"] = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
    payload["host"] = str(device["mgmt_ip"] or device["host"])
    payload.update({k: v for k, v in credential.items() if k not in payload})
    payload["target"] = {
        "name": device["name"],
        "vendor": device["vendor"],
        "model": device["model"],
        "site": device["site"],
        "region": device["region"],
    }
    payload.update(device.get("metadata") or {})
    return payload


def _idempotency_key(schedule: dict[str, Any], device: dict[str, Any]) -> str:
    scope = schedule.get("idempotency_scope", "daily")
    if scope == "daily":
        scope_value = date.today().isoformat()
    elif scope == "target_date":
        target_date = schedule.get("payload", {}).get("target_date")
        if target_date == "yesterday":
            scope_value = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
        elif target_date:
            scope_value = str(target_date)
        else:
            scope_value = date.today().isoformat()
    else:
        scope_value = str(scope)
    return f"{schedule['name']}:{scope_value}:{device['id']}"


def _expires_at(schedule: dict[str, Any], payload: dict[str, Any]) -> datetime | None:
    days = schedule.get("expires_after_days")
    if days is None:
        return None
    target_date = payload.get("target_date")
    if not target_date:
        return datetime.now(UTC) + timedelta(days=int(days))
    parsed = datetime.strptime(str(target_date), "%Y%m%d").date()
    expires_on = parsed + timedelta(days=int(days))
    return datetime.combine(expires_on, time.max, tzinfo=UTC)


if __name__ == "__main__":
    main()
