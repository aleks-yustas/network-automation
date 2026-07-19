from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from netops_automation.core.config import AppConfig
from netops_automation.core.models import Job, ScenarioResult


@dataclass
class ArchiveProcessor:
    config: AppConfig

    def process(self, job: Job, result: ScenarioResult) -> ScenarioResult:
        if result.data is None:
            return result

        data = result.data.encode() if isinstance(result.data, str) else result.data
        device_part = str(job.device_id or "no-device")
        filename = result.metadata.get("artifact_filename") or f"{job.id}.txt"
        artifact_type = result.metadata.get("artifact_type", "text")
        path = self.config.artifact_dir / device_part / job.job_type / str(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        checksum = hashlib.sha256(data).hexdigest()
        artifact = {
            "type": artifact_type,
            "path": str(path),
            "checksum_sha256": checksum,
            "size_bytes": len(data),
        }
        return ScenarioResult(
            status=result.status,
            message=result.message,
            data=result.data,
            metadata=result.metadata,
            artifacts=[*result.artifacts, artifact],
        )
