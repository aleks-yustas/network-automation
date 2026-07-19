from __future__ import annotations

from typing import Protocol

from netops_automation.core.models import Job, ScenarioResult


class Scenario(Protocol):
    def run(self, job: Job, transport: object) -> ScenarioResult:
        ...

