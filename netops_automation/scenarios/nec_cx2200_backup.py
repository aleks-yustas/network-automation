from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from netops_automation.core.errors import NonRetryableError, ScenarioError
from netops_automation.core.models import Job, ScenarioResult
from netops_automation.transports.telnet import TelnetTransport


@dataclass(frozen=True)
class NecCx2200BackupConfigScenario:
    """Ask NEC CX2200 to save config to FTP server configured on device."""

    def run(self, job: Job, transport: object) -> ScenarioResult:
        if not isinstance(transport, TelnetTransport):
            raise NonRetryableError("nec_cx2200_backup_config requires telnet transport")

        payload = job.payload
        username = _required(payload, "username")
        password = _required(payload, "password")
        command = payload.get("command") or "save ftp configuration"
        login_prompts = payload.get("login_prompts", ["login:", "Username:"])
        password_prompts = payload.get("password_prompts", ["Password:"])
        shell_prompts = payload.get("shell_prompts", [">", "#"])
        success_markers = payload.get("success_markers", ["success", "completed", "OK"])
        failure_markers = payload.get("failure_markers", ["fail", "error", "denied"])

        transport.connect()
        transcript = []
        try:
            transcript.append(transport.wait_for(login_prompts, timeout_sec=payload.get("login_timeout_sec", 20)))
            transport.send_line(username)
            transcript.append(transport.wait_for(password_prompts, timeout_sec=20))
            transport.send_line(password)
            transcript.append(transport.wait_for(shell_prompts, timeout_sec=30))
            output = transport.command(command, expect=shell_prompts, timeout_sec=payload.get("command_timeout_sec", 120))
            transcript.append(output)
        finally:
            transport.close()

        normalized = "\n".join(transcript)
        lower_output = normalized.lower()
        if any(marker.lower() in lower_output for marker in failure_markers):
            raise ScenarioError("NEC backup command returned failure marker")
        if success_markers and not any(marker.lower() in lower_output for marker in success_markers):
            raise ScenarioError("NEC backup command success marker not found")

        return ScenarioResult(
            status="ok",
            message="NEC CX2200 backup command accepted",
            data=normalized,
            metadata={"command": command},
        )


def _required(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise NonRetryableError(f"payload.{key} is required")
    return value

