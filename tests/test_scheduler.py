from datetime import date, timedelta

from netops_automation.app.scheduler import _build_payloads, _expand_target_dates, _idempotency_key


def test_expand_target_dates_last_n_days():
    expected = [
        (date.today() - timedelta(days=offset)).strftime("%Y%m%d")
        for offset in range(1, 4)
    ]
    assert _expand_target_dates({"target_dates": "last_3_days"}) == expected


def test_build_payloads_expands_dates_and_preserves_device_metadata():
    schedule = {
        "payload": {
            "target_dates": "last_2_days",
            "processors": ["archive"],
        }
    }
    device = {
        "id": "device-1",
        "name": "rrs-1",
        "vendor": "NEC",
        "model": "Pasolink",
        "mgmt_ip": "172.18.0.107",
        "host": None,
        "site": "site-1",
        "region": "region-1",
        "metadata": {"device": "Pasolink NEO/c"},
    }

    payloads = _build_payloads(schedule, device, {})

    assert len(payloads) == 2
    assert [payload["target_date"] for payload in payloads] == _expand_target_dates({"target_dates": "last_2_days"})
    assert all(payload["host"] == "172.18.0.107" for payload in payloads)
    assert all(payload["device"] == "Pasolink NEO/c" for payload in payloads)
    assert all("target_dates" not in payload for payload in payloads)


def test_idempotency_key_uses_resolved_target_date():
    schedule = {"name": "pasolink-pmon-catchup", "idempotency_scope": "target_date"}
    device = {"id": "device-1"}
    payload = {"target_date": "20260719"}

    assert _idempotency_key(schedule, device, payload) == "pasolink-pmon-catchup:20260719:device-1"

