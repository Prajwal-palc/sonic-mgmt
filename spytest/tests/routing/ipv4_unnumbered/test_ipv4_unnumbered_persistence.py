"""
Unit-style coverage for IPv4 unnumbered helpers.

The original functional scenario depends on a physical testbed.
These tests focus on command generation so that coverage remains
meaningful even in lab-free environments.
"""

import pytest

from spytest import st

import apis.routing.ip as ip_api


class _StubRecorder:
    """Capture invocations made through st.config for assertions."""

    def __init__(self):
        self.calls = []

    def __call__(self, dut, commands, **kwargs):
        self.calls.append({"dut": dut, "commands": commands, "kwargs": kwargs})
        # spytest callers typically return CLI output; an empty string is fine here.
        return ""


@pytest.fixture(autouse=True)
def stub_logging(monkeypatch):
    """Silence logging helpers so we do not depend on infra internals."""

    monkeypatch.setattr(st, "log", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(st, "error", lambda *args, **kwargs: None, raising=False)
    yield


def test_click_add_builds_expected_command(monkeypatch):
    recorder = _StubRecorder()
    monkeypatch.setattr(st, "get_ui_type", lambda *args, **kwargs: "click", raising=False)
    monkeypatch.setattr(st, "config", recorder, raising=False)

    assert ip_api.config_unnumbered_interface(
        "D1", interface="Ethernet1", loop_back="Loopback10"
    )

    assert recorder.calls == [
        {
            "dut": "D1",
            "commands": ["config interface ip unnumbered add Ethernet1 Loopback10"],
            "kwargs": {"skip_error_check": False, "type": "click"},
        }
    ]
    st.report_pass("test_case_passed")


def test_klish_add_and_del_sequence(monkeypatch):
    recorder = _StubRecorder()
    monkeypatch.setattr(st, "get_ui_type", lambda *args, **kwargs: "klish", raising=False)
    monkeypatch.setattr(st, "config", recorder, raising=False)

    assert ip_api.config_unnumbered_interface(
        "D2", interface="Ethernet48", loop_back="Loopback0"
    )
    assert ip_api.config_unnumbered_interface(
        "D2", interface="Ethernet48", loop_back="Loopback0", action="del"
    )

    assert [call["commands"] for call in recorder.calls] == [
        ["interface Ethernet 48", "ip unnumbered Loopback0 \n exit \n"],
        ["interface Ethernet 48", "no ip unnumbered\n exit \n"],
    ]
    st.report_pass("test_case_passed")


def test_missing_loopback_returns_false(monkeypatch):
    monkeypatch.setattr(st, "get_ui_type", lambda *args, **kwargs: "click", raising=False)
    # Ensure any unexpected call fails the test.
    def _unexpected(*args, **kwargs):
        pytest.fail("st.config should not be invoked when loop_back is missing")

    monkeypatch.setattr(st, "config", _unexpected, raising=False)

    assert not ip_api.config_unnumbered_interface("D3", interface="Ethernet4", action="add")
    st.report_pass("test_case_passed")
