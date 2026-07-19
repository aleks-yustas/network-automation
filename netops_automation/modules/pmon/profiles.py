from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PmonProfile:
    path_template: str
    header_size: int = 16
    record_size: int = 30
    records_per_day: int = 96


PMON_PROFILES: dict[str, PmonProfile] = {
    "Pasolink NEO/c": PmonProfile(path_template="/pmon/daily-dmr-{date}.pm"),
    "Pasolink NEO": PmonProfile(path_template="/pmon/daily-{date}.pm"),
}

