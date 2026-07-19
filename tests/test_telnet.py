from netops_automation.transports.telnet import _strip_telnet_negotiation


def test_strip_telnet_negotiation_removes_option_triplets():
    assert _strip_telnet_negotiation(bytes([255, 251, 1]) + b"login:") == b"login:"


def test_strip_telnet_negotiation_keeps_escaped_iac():
    assert _strip_telnet_negotiation(b"a" + bytes([255, 255]) + b"b") == b"a" + bytes([255]) + b"b"

