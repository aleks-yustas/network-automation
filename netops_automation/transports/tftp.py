from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from netops_automation.core.errors import TransportError


@dataclass
class TftpTransport:
    host: str
    timeout_sec: int = 30

    def get(self, remote_path: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = local_path.with_suffix(local_path.suffix + ".tmp")
        try:
            result = subprocess.run(
                ["tftp", "-g", "-r", remote_path, "-l", str(tmp), self.host],
                timeout=self.timeout_sec,
                capture_output=True,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            tmp.unlink(missing_ok=True)
            raise TransportError("tftp timeout") from exc
        except FileNotFoundError as exc:
            raise TransportError("tftp binary not found") from exc
        if result.returncode != 0:
            tmp.unlink(missing_ok=True)
            stderr = result.stderr.decode(errors="ignore").strip()
            raise TransportError(f"tftp failed: {stderr}")
        if not tmp.exists() or tmp.stat().st_size == 0:
            tmp.unlink(missing_ok=True)
            raise TransportError("tftp returned empty file")
        tmp.replace(local_path)

    def close(self) -> None:
        return None

