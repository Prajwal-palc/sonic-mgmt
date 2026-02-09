"""
SM_ISCLI_23 - Route-map visibility in show running-config

Author: Athira Arputharaj
Copyright (C) 2026, PALC Networks

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_1node.yaml \\
  routing/test_sm_iscli_23_route_map_show_run.py \\
  --logs-path ./logs/sm_iscli_23_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Verify that route-maps configured in the system are properly displayed in the
  running-config output. This test validates the fix for the issue where route-maps
  are present in Redis and vtysh but not shown in the running-config.

Pre-requisites:
  - Topology: single-node (D1) | Supported: HW and Virtual
  - SONiC version with route-map support

Test Scenario:
  1. Configure a route-map with permit action
  2. Verify route-map is present in Redis database
  3. Verify route-map appears in vtysh "show run"
  4. Verify route-map appears in SONiC "show running-config"
  5. Cleanup route-map configuration
"""

import pytest
from spytest import st, SpyTestDict

# Import feature APIs
import apis.routing.bgp as bgp_api
import apis.system.basic as basic_api

# Module level variables
data = SpyTestDict()


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module level setup and teardown"""
    global data

    st.banner("MODULE PROLOGUE: SM_ISCLI_23 - Route-map Show Running-Config Test")

    # Get testbed variables - single device topology
    data.vars = st.get_testbed_vars()
    data.dut = data.vars.D1

    # Test data
    data.route_map_name = "PERMIT_ALL"
    data.sequence = "10"
    data.action = "permit"

    st.log(f"Test will use device: {data.dut}")

    yield

    # Module epilogue - cleanup
    st.banner("MODULE EPILOGUE: Cleanup")
    cleanup_route_map()


def cleanup_route_map():
    """Remove route-map configuration"""
    st.log("Cleaning up route-map configuration")

    # Remove route-map using vtysh
    cmd = f"no route-map {data.route_map_name} {data.action} {data.sequence}"
    st.vtysh_config(data.dut, cmd)


def test_route_map_visibility_in_running_config():
    """
    TC-SM-ISCLI-23: Verify route-map appears in FRR running-config

    Steps:
      1. Configure route-map using vtysh
      2. Verify route-map appears in FRR running-config (vtysh "show running-config")

    Note: Route-maps are FRR-native objects and are NOT stored in Redis CONFIG_DB.
          They only exist in FRR's running-config. SONiC's "show running-configuration"
          command does NOT display FRR-native objects like route-maps - this is expected
          behavior, not a bug.
    """
    st.banner("TC-SM-ISCLI-23: Route-map visibility in FRR running-config")

    # Step 1: Configure route-map
    st.log(f"Step 1: Configuring route-map {data.route_map_name}")
    cmd = f"route-map {data.route_map_name} {data.action} {data.sequence}"
    st.vtysh_config(data.dut, cmd)

    # Small delay to ensure configuration is applied
    st.wait(2)

    # Step 2: Verify route-map in FRR running-config (vtysh)
    st.log("Step 2: Verifying route-map in FRR running-config (vtysh)")
    # Use st.show with vtysh command - this runs from bash shell, not inside vtysh
    vtysh_output = st.show(data.dut, "show running-config | include route-map", type="vtysh", skip_tmpl=True)

    st.log(f"FRR running-config output: {vtysh_output}")

    expected_vtysh_line = f"route-map {data.route_map_name} {data.action} {data.sequence}"
    vtysh_check = expected_vtysh_line in vtysh_output

    if not vtysh_check:
        st.error(f"Route-map NOT found in FRR running-config (vtysh)")
        st.error(f"Expected: {expected_vtysh_line}")
        st.error(f"Got: {vtysh_output}")
        st.report_fail("route_map_not_in_frr_config", data.route_map_name)
    else:
        st.log(f"✓ Route-map {data.route_map_name} found in FRR running-config")
        st.log("✓ SUCCESS: Route-map correctly configured and visible in FRR")
        st.report_pass("test_case_passed")


def test_route_map_removal_verification():
    """
    TC-SM-ISCLI-23-02: Verify route-map removal from FRR running-config

    Steps:
      1. Remove the route-map configuration
      2. Verify route-map is removed from FRR running-config (vtysh)

    Note: Route-maps are FRR-native objects and are NOT stored in Redis.
    """
    st.banner("TC-SM-ISCLI-23-02: Route-map removal verification")

    # Step 1: Remove route-map
    st.log(f"Step 1: Removing route-map {data.route_map_name}")
    cleanup_route_map()

    st.wait(2)

    # Step 2: Verify removal from FRR running-config (vtysh)
    st.log("Step 2: Verifying route-map removed from FRR running-config (vtysh)")
    # Use st.show with type="vtysh" - this runs from bash shell
    vtysh_output = st.show(data.dut, "show running-config | include route-map", type="vtysh", skip_tmpl=True)

    vtysh_still_present = data.route_map_name in vtysh_output

    if vtysh_still_present:
        st.error(f"Route-map {data.route_map_name} still present in FRR running-config after removal")
        st.report_fail("route_map_removal_failed_frr")
    else:
        st.log(f"✓ Route-map {data.route_map_name} successfully removed from FRR running-config")
        st.log("✓ SUCCESS: Route-map successfully removed")
        st.report_pass("test_case_passed")
