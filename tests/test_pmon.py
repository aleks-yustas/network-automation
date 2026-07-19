from netops_automation.scenarios.download_pmon import _validate_pmon


def test_validate_pmon_empty_header_only():
    assert _validate_pmon(b"0" * 16, 16, 30)["status"] == "empty"


def test_validate_pmon_full_day():
    result = _validate_pmon(b"0" * (16 + 30 * 96), 16, 30)
    assert result["status"] == "ok"
    assert result["records"] == 96


def test_validate_pmon_rejects_unaligned_size():
    assert _validate_pmon(b"0" * 17, 16, 30)["status"] == "error"

