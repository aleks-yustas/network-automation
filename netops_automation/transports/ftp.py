from __future__ import annotations

from dataclasses import dataclass
from ftplib import FTP, error_perm
from pathlib import Path

from netops_automation.core.errors import TransportError


@dataclass
class FtpTransport:
    host: str
    username: str
    password: str
    port: int = 21
    timeout_sec: int = 30

    def __post_init__(self) -> None:
        self._ftp: FTP | None = None

    def connect(self) -> None:
        try:
            ftp = FTP()
            ftp.connect(self.host, self.port, timeout=self.timeout_sec)
            ftp.login(self.username, self.password)
            self._ftp = ftp
        except OSError as exc:
            raise TransportError(f"ftp connect failed: {exc}") from exc
        except error_perm as exc:
            raise TransportError(f"ftp login failed: {exc}") from exc

    def get(self, remote_path: str, local_path: Path) -> None:
        if self._ftp is None:
            raise TransportError("ftp is not connected")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with local_path.open("wb") as f:
                self._ftp.retrbinary(f"RETR {remote_path}", f.write)
        except (OSError, error_perm) as exc:
            raise TransportError(f"ftp get failed: {exc}") from exc

    def close(self) -> None:
        if self._ftp is not None:
            try:
                self._ftp.quit()
            finally:
                self._ftp = None

