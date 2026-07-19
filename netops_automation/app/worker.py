from __future__ import annotations

import argparse
import logging
import signal
import time
from pathlib import Path

from netops_automation.core.config import AppConfig, load_config
from netops_automation.core.db import connect
from netops_automation.core.errors import NonRetryableError
from netops_automation.core.models import Job, ScenarioResult
from netops_automation.core.queue import QueueManager
from netops_automation.processors import PROCESSORS
from netops_automation.scenarios import SCENARIOS
from netops_automation.transports import TRANSPORTS

log = logging.getLogger(__name__)
STOP = False


def main() -> None:
    parser = argparse.ArgumentParser(description="NetOps Automation queue worker")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    config = load_config(args.config)
    with connect(config.database_dsn) as conn:
        queue = QueueManager(conn, config)
        recovered = queue.recover_stale_running()
        if recovered:
            log.info("Recovered stale RUNNING jobs: %s", recovered)

        while not STOP:
            job = queue.lease_next()
            if job is None:
                if args.once:
                    return
                time.sleep(config.poll_interval_sec)
                continue
            _run_job(queue, config, job)
            if args.once:
                return


def _run_job(queue: QueueManager, config: AppConfig, job: Job) -> None:
    try:
        scenario_cls = SCENARIOS[job.scenario]
        transport_cls = TRANSPORTS[job.transport]
    except KeyError as exc:
        queue.mark_failed(job, "unknown_handler", str(exc), retryable=False)
        return

    try:
        transport = _build_transport(transport_cls, job)
        result = scenario_cls().run(job, transport)
        result = _process_result(queue, config, job, result)
        queue.mark_done(job.id, _result_to_dict(result))
    except NonRetryableError as exc:
        queue.mark_failed(job, exc.__class__.__name__, str(exc), retryable=False)
    except Exception as exc:
        log.exception("Job failed: %s", job.id)
        queue.mark_failed(job, exc.__class__.__name__, str(exc), retryable=True)


def _build_transport(transport_cls: type, job: Job) -> object:
    transport_payload = job.payload.get("transport", {})
    host = transport_payload.get("host") or job.payload.get("host")
    if not host:
        raise NonRetryableError("payload.host or payload.transport.host is required")
    kwargs = {k: v for k, v in transport_payload.items() if k != "host"}
    kwargs.setdefault("timeout_sec", job.timeout_sec)
    return transport_cls(host=host, **kwargs)


def _process_result(queue: QueueManager, config: AppConfig, job: Job, result: ScenarioResult) -> ScenarioResult:
    processor_names = job.payload.get("processors", ["archive", "postgres_metadata"])
    for name in processor_names:
        processor_cls = PROCESSORS[name]
        if name == "archive":
            processor = processor_cls(config)
        elif name == "postgres_metadata":
            processor = processor_cls(queue.conn)
        else:
            processor = processor_cls()
        result = processor.process(job, result)
    return result


def _result_to_dict(result: ScenarioResult) -> dict:
    return {
        "status": result.status,
        "message": result.message,
        "metadata": result.metadata,
        "artifacts": result.artifacts,
    }


def _stop(signum: int, frame: object) -> None:
    global STOP
    STOP = True


if __name__ == "__main__":
    main()

