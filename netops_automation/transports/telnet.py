from __future__ import annotations

import socket
import time
from dataclasses import dataclass

from netops_automation.core.errors import TransportError

IAC = 255
DONT = 254
DO = 253
WONT = 252
WILL = 251


@dataclass
class TelnetTransport:
    host: str
    port: int = 23
    timeout_sec: int = 30

    def __post_init__(self) -> None:
        self._sock: socket.socket | None = None

    def connect(self) -> None:
        try:
            self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout_sec)
            self._sock.settimeout(0.5)
        except OSError as exc:
            raise TransportError(f"telnet connect failed: {exc}") from exc

    def send_line(self, line: str) -> None:
        self._send((line + "\r\n").encode())

    def wait_for(self, patterns: list[str], timeout_sec: int | None = None) -> str:
        deadline = time.monotonic() + (timeout_sec or self.timeout_sec)
        buffer = bytearray()
        encoded_patterns = [p.encode(errors="ignore") for p in patterns]
        while time.monotonic() < deadline:
            chunk = self._recv_some()
            if chunk:
                buffer.extend(chunk)
                text = bytes(buffer).decode(errors="ignore")
                if any(pattern in bytes(buffer) for pattern in encoded_patterns):
                    return text
            else:
                time.sleep(0.1)
        raise TransportError(f"telnet wait timeout: {patterns}")

    def command(self, command: str, expect: list[str], timeout_sec: int | None = None) -> str:
        self.send_line(command)
        return self.wait_for(expect, timeout_sec=timeout_sec)

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def _send(self, data: bytes) -> None:
        if self._sock is None:
            raise TransportError("telnet socket is not connected")
        try:
            self._sock.sendall(data)
        except OSError as exc:
            raise TransportError(f"telnet send failed: {exc}") from exc

    def _recv_some(self) -> bytes:
        if self._sock is None:
            raise TransportError("telnet socket is not connected")
        try:
            data = self._sock.recv(4096)
        except socket.timeout:
            return b""
        except OSError as exc:
            raise TransportError(f"telnet receive failed: {exc}") from exc
        if not data:
            raise TransportError("telnet connection closed")
        clean, reply = _handle_telnet_negotiation(data)
        if reply:
            self._send(reply)
        return clean


def _strip_telnet_negotiation(data: bytes) -> bytes:
    clean, _reply = _handle_telnet_negotiation(data)
    return clean


def _handle_telnet_negotiation(data: bytes) -> tuple[bytes, bytes]:
    out = bytearray()
    reply = bytearray()
    i = 0
    while i < len(data):
        byte = data[i]
        if byte == IAC and i + 2 < len(data):
            command = data[i + 1]
            option = data[i + 2]
            if command == DO:
                reply.extend([IAC, WONT, option])
                i += 3
                continue
            if command == WILL:
                reply.extend([IAC, DONT, option])
                i += 3
                continue
            if command in (DONT, WONT):
                i += 3
                continue
        if byte == IAC and i + 2 < len(data) and data[i + 1] in (DO, DONT, WILL, WONT):
            i += 3
            continue
        if byte == IAC and i + 1 < len(data) and data[i + 1] == IAC:
            out.append(IAC)
            i += 2
            continue
        out.append(byte)
        i += 1
    return bytes(out), bytes(reply)
