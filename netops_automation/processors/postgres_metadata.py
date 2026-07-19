from __future__ import annotations

from dataclasses import dataclass

from psycopg import Connection
from psycopg.types.json import Jsonb

from netops_automation.core.models import Job, ScenarioResult


@dataclass
class PostgresMetadataProcessor:
    conn: Connection

    def process(self, job: Job, result: ScenarioResult) -> ScenarioResult:
        for artifact in result.artifacts:
            self.conn.execute(
                """
                INSERT INTO netops_artifacts (
                    job_id, device_id, artifact_type, path, checksum_sha256, size_bytes, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    job.id,
                    job.device_id,
                    artifact.get("type", "unknown"),
                    artifact.get("path"),
                    artifact.get("checksum_sha256"),
                    artifact.get("size_bytes"),
                    Jsonb(artifact),
                ),
            )
        return result
