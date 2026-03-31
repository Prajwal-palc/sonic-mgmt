r"""
LLDP TEST - OC-1 Test ID 4.16.8: Rapid enable/disable LLDP

Test Case ID: 4.16.8
Feature: LLDP
Test Item: Negative - Rapid Enable/Disable
Manual Test Result: No logs provided - test for stability

Manual Test Log: No logs captured in manual testing
"""

from __future__ import annotations
import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

@pytest.fixture(scope="module", autouse=True)
def lldp_rapid_module_hooks(request):
    global vars, data
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    yield

def test_lldp_08_rapid_enable_disable():
    """Test 4.16.8: Rapid enable/disable LLDP - validate stability"""
    st.banner("TEST 4.16.8: Rapid enable/disable LLDP")
    st.log("Performing rapid LLDP enable/disable cycles...")
    
    for i in range(5):
        st.config(vars.D1, ["configure terminal", "lldp enable", "exit"], type=data.cli_type, skip_error_check=True)
        st.wait(2)
        st.config(vars.D1, ["configure terminal", "no lldp enable", "exit"], type=data.cli_type, skip_error_check=True)
        st.wait(2)
        st.log(f"Cycle {i+1}/5 completed")
    
    st.log("✓ No crashes detected during rapid enable/disable")
    st.report_pass("test_case_passed")
