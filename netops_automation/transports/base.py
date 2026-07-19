from __future__ import annotations

from typing import Protocol


class Transport(Protocol):
    def close(self) -> None:
        ...

