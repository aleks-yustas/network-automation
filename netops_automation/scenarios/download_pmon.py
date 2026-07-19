from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from netops_automation.core.errors import NonRetryableError, ScenarioError
from netops_automation.core.models import Job, ScenarioResult
from netops_automation.modules.pmon.profiles import PMON_PROFILES
from netops_automation.transports.tftp import TftpTransport


@dataclass(frozen=True)
class DownloadPmonScenario:
    """Download PMON raw file from RRS by TFTP."""

    def run(self, job: Job, transport: object) -> ScenarioResult:
        if not isinstance(transport, TftpTransport):
            raise NonRetryableError("download_pmon requires tftp transport")

        device = job.payload.get("device")
        target_date = str(job.payload.get("target_date", ""))
        if not device:
            raise NonRetryableError("payload.device is required")
        if not target_date or len(target_date) != 8 or not target_date.isdigit():
            raise NonRetryableError("payload.target_date must be YYYYMMDD")

        profile = PMON_PROFILES.get(str(device))
        if profile is None:
            raise NonRetryableError(f"unsupported PMON device profile: {device}")

        remote_path = profile.path_template.format(date=target_date)
        local_name = Path(remote_path).name
        local_path = Path(job.payload.get("work_dir", "/tmp/netops-pmon")) / str(job.id) / local_name

        transport.get(remote_path, local_path)
        data = local_path.read_bytes()
        validation = _validate_pmon(data, profile.header_size, profile.record_size)
        if validation["status"] == "error":
            raise ScenarioError(validation["message"])

        return ScenarioResult(
            status=validation["status"],
            message=f"PMON downloaded: {remote_path}",
            data=data,
            metadata={
                "artifact_type": "pmon_raw",
                "artifact_filename": local_name,
                "device": device,
                "target_date": target_date,
                "remote_path": remote_path,
                **validation,
            },
        )


def _validate_pmon(data: bytes, header_size: int, record_size: int) -> dict[str, object]:
    size = len(data)
    if size <= header_size:
        return {"status": "empty", "message": f"PMON file empty: {size} bytes", "records": 0, "size_bytes": size}
    payload_size = size - header_size
    if payload_size % record_size != 0:
        return {
            "status": "error",
            "message": f"PMON size not aligned: {size} bytes",
            "records": None,
            "size_bytes": size,
        }
    return {"status": "ok", "message": "PMON file valid", "records": payload_size // record_size, "size_bytes": size}

