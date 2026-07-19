from __future__ import annotations

from typing import Protocol

from netops_automation.core.models import Job, ScenarioResult


class Processor(Protocol):
    def process(self, job: Job, result: ScenarioResult) -> ScenarioResult:
        ...

