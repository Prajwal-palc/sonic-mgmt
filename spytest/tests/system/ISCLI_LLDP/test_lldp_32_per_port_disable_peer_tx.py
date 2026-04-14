r"""
LLDP TEST - OC-1 Test ID 4.16.32: Per Port Disable Peer Tx

Test Case ID: 4.16.32
Feature: LLDP
Manual Test Result: FAIL - Per-port disable not working
"""

from __future__ import annotations
import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

@pytest.fixture(scope="module", autouse=True)
def lldp_test_32_module_hooks(request):
    global vars, data
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    yield

def test_lldp_32_per_port_disable_peer_tx():
    """Test 4.16.32: Per Port Disable Peer Tx"""
    st.banner("TEST 4.16.32: Per Port Disable Peer Tx")
    st.log("Manual Test Result: FAIL - Per-port disable not working")

    # Determine test result based on manual testing
    manual_result = "FAIL - Per-port disable not working"

    if "PASS" in manual_result:
        st.log("✓ Test marked as PASS in manual testing")
        st.report_pass("test_case_passed")
    elif "Not Feasible" in manual_result or "Not Applicable" in manual_result:
        st.log(f"⊘ Test marked as {manual_result}")
        st.report_skip("msg", f"Test 4.16.32: {manual_result}")
    else:
        st.log(f"✗ Test marked as FAIL in manual testing: {manual_result}")
        st.report_fail("msg", f"Test 4.16.32: {manual_result}")
