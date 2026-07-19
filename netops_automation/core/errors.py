from __future__ import annotations


class NetOpsError(Exception):
    """Base NetOps Automation error."""


class RetryableError(NetOpsError):
    """Operation can be retried later."""


class NonRetryableError(NetOpsError):
    """Operation should fail without retry."""


class TransportError(RetryableError):
    """Transport-level failure."""


class ScenarioError(NetOpsError):
    """Scenario-level failure."""


class ScenarioTimeout(TransportError):
    """Scenario exceeded execution timeout."""
