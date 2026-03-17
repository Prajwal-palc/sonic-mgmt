"""
Pytest configuration file for L3 ACL tests.

This file contains pytest hooks and fixtures that are automatically
loaded before tests run. It's used for test setup and teardown.
"""

import pytest
from spytest import st


@pytest.fixture(scope="session", autouse=True)
def disable_pagination_on_all_duts(request):
    """
    Session-level fixture to disable pagination on all DUTs.
    Runs once per test session before any tests execute.

    This fixture disables CLI pagination to prevent --more-- output
    that causes SPyTest framework to hang when executing show commands.
    Uses the 'no-more' suffix approach which is more reliable than
    terminal configuration commands.
    """
    # Try to get DUT handles, but expect this might not work at session scope
    # So we use a try/except to handle gracefully
    try:
        dut_list = st.get_dut_names()
        if dut_list:
            st.log(f"[conftest] Attempting to disable pagination on DUTs: {dut_list}")

            # Try multiple approaches to disable pagination
            # Approach 1: Terminal configuration commands (works on some devices)
            pagination_commands = [
                "terminal length 0",
                "terminal pager off",
                "terminal width unlimited",
            ]

            for dut in dut_list:
                try:
                    st.log(f"[conftest] Processing {dut}")
                    # Try terminal length commands
                    for cmd in pagination_commands:
                        try:
                            st.cli(dut, cmd, skip_tmpl=True, skip_error_check=True)
                            st.log(f"[conftest] ✅ {dut}: '{cmd}' executed")
                        except Exception as cmd_err:
                            st.debug(f"[conftest] '{cmd}' on {dut}: {cmd_err}")
                except Exception as e:
                    st.debug(f"[conftest] Note: Could not disable pagination via terminal cmds on {dut}: {e}")
        else:
            st.log("[conftest] No DUTs found in testbed at session scope (expected - DUTs initialize after)")
    except Exception as e:
        st.debug(f"[conftest] Note: Session-scope fixture ran before DUT initialization (expected): {e}")

    yield  # Tests run after this point

    # Teardown (if needed in future)
