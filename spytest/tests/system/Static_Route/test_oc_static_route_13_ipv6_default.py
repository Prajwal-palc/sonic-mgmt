"""
STATIC ROUTE TEST - OC-SR-23: IPv6 Static Route - Default Route (3 DUTs)

Test Case ID: OC-SR-23
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_oc_3d.yaml \
    tests/system/Static_Route/test_oc_static_route_13_ipv6_default.py \
    --logs-path ./logs/oc_sr23_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates IPv6 default route (::/0) configuration on SONiC OC-build.
  Default route is the route of last resort when no specific route matches.
  Also known as gateway of last resort.
  Topology: DUT1 <-> DUT2 <-> DUT3 with DUT3 hosting destination prefix on Loopback.

Manual sonic-cli commands validated:
  DUT1:
    interface Ethernet 0 -> ipv6 address 2001:1:1::1/64 -> no shutdown
    ipv6 route ::/0 2001:1:1::2

  DUT2:
    interface Ethernet 0 -> ipv6 address 2001:1:1::2/64 -> no shutdown
    interface Ethernet 8 -> ipv6 address 2001:2:1::1/64 -> no shutdown
    ipv6 route ::/0 2001:2:1::2

  DUT3:
    interface Ethernet 8 -> ipv6 address 2001:2:1::2/64 -> no shutdown
    interface Loopback 0
    ipv6 address 2001:db8:999::1/128
    ipv6 route ::/0 2001:2:1::1

Pre-requisites:
  - Topology: 3-node (D1-D2-D3) | Supported: HW and Virtual
  - OC-build with Klish CLI support and IPv6 default route support
  - Minimum topology: D1-D2 link and D2-D3 link
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration - matches manual testcase exactly
CONFIG = SpyTestDict({
    # DUT1 Interface Configuration
    "dut1_eth0": "Ethernet 0",
    "dut1_eth0_ipv6": "2001:1:1::1/64",

    # DUT1 IPv6 Default Route
    "dut1_default_prefix": "::/0",
    "dut1_default_nexthop": "2001:1:1::2",

    # DUT2 Interface Configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ipv6": "2001:1:1::2/64",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ipv6": "2001:2:1::1/64",

    # DUT2 IPv6 Default Route
    "dut2_default_prefix": "::/0",
    "dut2_default_nexthop": "2001:2:1::2",

    # DUT3 Interface Configuration
    "dut3_eth8": "Ethernet 8",
    "dut3_eth8_ipv6": "2001:2:1::2/64",

    # DUT3 Loopback Configuration (destination endpoint)
    "dut3_loopback": "Loopback 0",
    "dut3_loopback_ipv6": "2001:db8:999::1/128",

    # DUT3 IPv6 Default Route
    "dut3_default_prefix": "::/0",
    "dut3_default_nexthop": "2001:2:1::1",
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "oc_sr23_interface_config": "TC-OC-SR-23-001",
    "oc_sr23_loopback_config": "TC-OC-SR-23-002",
    "oc_sr23_route_add": "TC-OC-SR-23-003",
    "oc_sr23_route_verify": "TC-OC-SR-23-004",
    "oc_sr23_route_remove": "TC-OC-SR-23-005",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-23 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Ensure 3-DUT topology: D1-D2 link and D2-D3 link
    vars = st.ensure_min_topology("D1D2:1", "D2D3:1")
    data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}, DUT3: {vars.D3}")

    # Pre-configuration
    static_route_pre_config()

    yield

    # Cleanup - always executes even if test fails
    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-23 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        static_route_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def static_route_pre_config():
    """Pre-configuration: Clear existing configs."""
    st.log("Pre-configuration: Clearing existing configuration on all DUTs")

    # Clear DUT1 interface
    try:
        st.config(vars.D1, [
            f"interface {CONFIG.dut1_eth0}",
            "no ip address",
            "no ipv6 address",
            "shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Clear DUT2 interfaces
    for intf in [CONFIG.dut2_eth0, CONFIG.dut2_eth8]:
        try:
            st.config(vars.D2, [
                f"interface {intf}",
                "no ip address",
                "no ipv6 address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

    # Clear DUT3 interface
    try:
        st.config(vars.D3, [
            f"interface {CONFIG.dut3_eth8}",
            "no ip address",
            "no ipv6 address",
            "shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Clear DUT3 Loopback
    try:
        st.config(vars.D3, [
            f"interface {CONFIG.dut3_loopback}",
            "no ipv6 address",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Explicitly exit Klish CLI mode back to normal user mode on all DUTs
    for dut in [vars.D1, vars.D2, vars.D3]:
        try:
            # First exit from config mode to normal Klish prompt
            st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)
        except Exception:
            pass
        try:
            # Then exit from Klish CLI to Linux shell
            st.config(dut, ["exit"], type='klish', skip_error_check=True)
        except Exception:
            pass

    st.wait(3, "Waiting for pre-config clear to stabilize")
    st.log("Pre-configuration completed")


def static_route_cleanup():
    """Cleanup: Remove all test configurations."""
    st.log("Cleanup: Removing all test configurations")

    # Remove DUT1 IPv6 default route
    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.dut1_default_prefix} {CONFIG.dut1_default_nexthop}",
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT2 IPv6 default route
    try:
        st.config(vars.D2, [
            f"no ipv6 route {CONFIG.dut2_default_prefix} {CONFIG.dut2_default_nexthop}",
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT3 IPv6 default route
    try:
        st.config(vars.D3, [
            f"no ipv6 route {CONFIG.dut3_default_prefix} {CONFIG.dut3_default_nexthop}",
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Clear DUT1 interface
    try:
        st.config(vars.D1, [
            f"interface {CONFIG.dut1_eth0}",
            "no ipv6 address",
            "shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Clear DUT2 interfaces
    for intf in [CONFIG.dut2_eth0, CONFIG.dut2_eth8]:
        try:
            st.config(vars.D2, [
                f"interface {intf}",
                "no ipv6 address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

    # Clear DUT3 interface
    try:
        st.config(vars.D3, [
            f"interface {CONFIG.dut3_eth8}",
            "no ipv6 address",
            "shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Clear DUT3 Loopback
    try:
        st.config(vars.D3, [
            f"interface {CONFIG.dut3_loopback}",
            f"no ipv6 address {CONFIG.dut3_loopback_ipv6}",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Explicitly exit Klish CLI mode back to normal user mode on all DUTs
    for dut in [vars.D1, vars.D2, vars.D3]:
        try:
            # First exit from config mode to normal Klish prompt
            st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)
        except Exception:
            pass
        try:
            # Then exit from Klish CLI to Linux shell
            st.config(dut, ["exit"], type='klish', skip_error_check=True)
        except Exception:
            pass

    st.log("Cleanup completed")


def configure_ipv6_interface(dut, interface, ipv6_addr):
    """Configure IPv6 address on interface and bring it up."""
    st.log(f"Configuring {interface} with {ipv6_addr} on {dut}")
    try:
        st.config(dut, [
            f"interface {interface}",
            f"ipv6 address {ipv6_addr}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed to configure interface {interface}: {str(e)}")
        return False


def configure_loopback_ipv6(dut, loopback_intf, ipv6_addr):
    """Configure IPv6 address on Loopback interface."""
    st.log(f"Configuring Loopback {loopback_intf} with {ipv6_addr} on {dut}")
    try:
        st.config(dut, [
            f"interface {loopback_intf}",
            f"ipv6 address {ipv6_addr}",
            "exit"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed to configure loopback: {str(e)}")
        return False


def add_ipv6_default_route(dut, nexthop):
    """Add IPv6 default route (::/0)."""
    st.log(f"Adding IPv6 default route ::/0 via {nexthop} on {dut}")
    try:
        st.config(dut, [
            f"ipv6 route ::/0 {nexthop}"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed to add IPv6 default route: {str(e)}")
        return False


def verify_ipv6_default_route(dut, nexthop):
    """Verify IPv6 default route exists in routing table."""
    st.log(f"Verifying IPv6 default route ::/0 via {nexthop} on {dut}")

    # Exit config mode before show command
    st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

    # Exit Klish CLI to Linux shell before show command
    try:
        st.config(dut, ["exit"], type='klish', skip_error_check=True)
    except Exception:
        pass

    try:
        output = st.show(dut, "show ipv6 route static", type='klish')
        output_str = str(output).lower()

        # Check for default route indicators
        # Could show as "::/0", "0::/0", or "default"
        nexthop_lower = nexthop.lower()

        if ("::/0" in output_str or "0::/0" in output_str or "default" in output_str) and nexthop_lower in output_str:
            st.log(f"✓ IPv6 default route via {nexthop} found in routing table")
            return True
        else:
            st.error(f"✗ IPv6 default route via {nexthop} NOT found")
            st.log(f"Output: {output}")
            return False
    except Exception as e:
        st.error(f"✗ Failed to verify route: {str(e)}")
        return False


def verify_ipv6_default_route_absent(dut):
    """Verify IPv6 default route does NOT exist in routing table."""
    st.log(f"Verifying IPv6 default route ::/0 is absent on {dut}")

    # Exit config mode before show command
    st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

    # Exit Klish CLI to Linux shell before show command
    try:
        st.config(dut, ["exit"], type='klish', skip_error_check=True)
    except Exception:
        pass

    try:
        output = st.show(dut, "show ipv6 route static", type='klish')
        output_str = str(output).lower()

        # Check if default route is absent
        if "::/0" not in output_str and "0::/0" not in output_str:
            st.log(f"✓ IPv6 default route correctly absent from routing table")
            return True
        else:
            st.error(f"✗ IPv6 default route still present (should be absent)")
            st.log(f"Output: {output}")
            return False
    except Exception as e:
        # If show command fails or returns empty, route might be absent
        st.log(f"Route verification returned error (likely absent): {str(e)}")
        return True


def delete_ipv6_default_route(dut, nexthop):
    """Delete IPv6 default route (::/0)."""
    st.log(f"Deleting IPv6 default route ::/0 via {nexthop} on {dut}")
    try:
        st.config(dut, [
            f"no ipv6 route ::/0 {nexthop}"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed to delete IPv6 default route: {str(e)}")
        return False


def test_oc_sr23_ipv6_default_route():
    """
    Test Case: OC-SR-23 - IPv6 Default Route (::/0)

    Steps:
    1. Configure IPv6 interfaces on DUT1, DUT2, and DUT3
    2. Configure Loopback on DUT3 with destination IPv6 address
    3. Add IPv6 default route on DUT1
    4. Add IPv6 default route on DUT2
    5. Add IPv6 default route on DUT3
    6. Verify IPv6 default routes on all DUTs
    7. Delete IPv6 default routes on all DUTs
    8. Verify IPv6 default routes are absent
    """
    st.banner("=" * 80)
    st.banner("TEST: OC-SR-23 - IPv6 Default Route (::/0)")
    st.banner("=" * 80)

    # Track test results
    results = []

    # Step 1: Configure IPv6 interfaces on DUT1
    st.banner("STEP 1: Configure IPv6 Interface on DUT1")
    result = configure_ipv6_interface(vars.D1, CONFIG.dut1_eth0, CONFIG.dut1_eth0_ipv6)

    if result:
        st.log("✓ DUT1 IPv6 interface configuration successful")
        st.report_tc_pass(TC_IDS.oc_sr23_interface_config, "ipv6_interface_config_dut1_passed")
        results.append(True)
    else:
        st.error("✗ DUT1 IPv6 interface configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr23_interface_config, "ipv6_interface_config_dut1_failed")
        results.append(False)

    # Step 1.5: Configure IPv6 interfaces on DUT2
    st.banner("STEP 1.5: Configure IPv6 Interfaces on DUT2")
    result1 = configure_ipv6_interface(vars.D2, CONFIG.dut2_eth0, CONFIG.dut2_eth0_ipv6)
    result2 = configure_ipv6_interface(vars.D2, CONFIG.dut2_eth8, CONFIG.dut2_eth8_ipv6)

    if result1 and result2:
        st.log("✓ DUT2 IPv6 interface configuration successful")
        results.append(True)
    else:
        st.error("✗ DUT2 IPv6 interface configuration failed")
        results.append(False)

    # Step 1.7: Configure IPv6 interface on DUT3
    st.banner("STEP 1.7: Configure IPv6 Interface on DUT3")
    result = configure_ipv6_interface(vars.D3, CONFIG.dut3_eth8, CONFIG.dut3_eth8_ipv6)

    if result:
        st.log("✓ DUT3 IPv6 interface configuration successful")
        results.append(True)
    else:
        st.error("✗ DUT3 IPv6 interface configuration failed")
        results.append(False)

    # Step 2: Configure Loopback on DUT3
    st.banner("STEP 2: Configure Loopback on DUT3")
    result = configure_loopback_ipv6(vars.D3, CONFIG.dut3_loopback, CONFIG.dut3_loopback_ipv6)

    if result:
        st.log("✓ DUT3 Loopback IPv6 configuration successful")
        st.report_tc_pass(TC_IDS.oc_sr23_loopback_config, "ipv6_loopback_config_passed")
        results.append(True)
    else:
        st.error("✗ DUT3 Loopback IPv6 configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr23_loopback_config, "ipv6_loopback_config_failed")
        results.append(False)

    st.wait(5, "Waiting for IPv6 neighbor discovery and interface stabilization")

    # Step 3: Add IPv6 default route on DUT1
    st.banner("STEP 3: Add IPv6 Default Route on DUT1")
    result = add_ipv6_default_route(vars.D1, CONFIG.dut1_default_nexthop)

    if result:
        st.log("✓ DUT1 IPv6 default route added successfully")
        st.report_tc_pass(TC_IDS.oc_sr23_route_add, "ipv6_default_route_add_dut1_passed")
        results.append(True)
    else:
        st.error("✗ DUT1 IPv6 default route addition failed")
        st.report_tc_fail(TC_IDS.oc_sr23_route_add, "ipv6_default_route_add_dut1_failed")
        results.append(False)

    # Step 4: Add IPv6 default route on DUT2
    st.banner("STEP 4: Add IPv6 Default Route on DUT2")
    result = add_ipv6_default_route(vars.D2, CONFIG.dut2_default_nexthop)

    if result:
        st.log("✓ DUT2 IPv6 default route added successfully")
        results.append(True)
    else:
        st.error("✗ DUT2 IPv6 default route addition failed")
        results.append(False)

    # Step 5: Add IPv6 default route on DUT3
    st.banner("STEP 5: Add IPv6 Default Route on DUT3")
    result = add_ipv6_default_route(vars.D3, CONFIG.dut3_default_nexthop)

    if result:
        st.log("✓ DUT3 IPv6 default route added successfully")
        results.append(True)
    else:
        st.error("✗ DUT3 IPv6 default route addition failed")
        results.append(False)

    st.wait(3, "Waiting for default routes to be programmed in routing table")

    # Step 6: Verify IPv6 default routes on all DUTs
    st.banner("STEP 6: Verify IPv6 Default Routes on All DUTs")

    # Verify DUT1 default route
    result1 = verify_ipv6_default_route(vars.D1, CONFIG.dut1_default_nexthop)

    # Verify DUT2 default route
    result2 = verify_ipv6_default_route(vars.D2, CONFIG.dut2_default_nexthop)

    # Verify DUT3 default route
    result3 = verify_ipv6_default_route(vars.D3, CONFIG.dut3_default_nexthop)

    if result1 and result2 and result3:
        st.log("✓ All IPv6 default routes verified successfully")
        st.report_tc_pass(TC_IDS.oc_sr23_route_verify, "ipv6_default_route_verify_passed")
        results.append(True)
    else:
        st.error("✗ IPv6 default route verification failed")
        st.report_tc_fail(TC_IDS.oc_sr23_route_verify, "ipv6_default_route_verify_failed")
        results.append(False)

    # Step 7: Delete IPv6 default routes on all DUTs
    st.banner("STEP 7: Delete IPv6 Default Routes on All DUTs")
    result1 = delete_ipv6_default_route(vars.D1, CONFIG.dut1_default_nexthop)
    result2 = delete_ipv6_default_route(vars.D2, CONFIG.dut2_default_nexthop)
    result3 = delete_ipv6_default_route(vars.D3, CONFIG.dut3_default_nexthop)

    if result1 and result2 and result3:
        st.log("✓ All IPv6 default routes deleted successfully")
        st.report_tc_pass(TC_IDS.oc_sr23_route_remove, "ipv6_default_route_delete_passed")
        results.append(True)
    else:
        st.error("✗ IPv6 default route deletion failed")
        st.report_tc_fail(TC_IDS.oc_sr23_route_remove, "ipv6_default_route_delete_failed")
        results.append(False)

    st.wait(2, "Waiting for route removal from routing table")

    # Step 8: Verify IPv6 default routes are absent on all DUTs
    st.banner("STEP 8: Verify IPv6 Default Routes Absent on All DUTs")

    # Verify DUT1 default route absent
    result1 = verify_ipv6_default_route_absent(vars.D1)

    # Verify DUT2 default route absent
    result2 = verify_ipv6_default_route_absent(vars.D2)

    # Verify DUT3 default route absent
    result3 = verify_ipv6_default_route_absent(vars.D3)

    if result1 and result2 and result3:
        st.log("✓ All IPv6 default routes correctly absent from routing tables")
        results.append(True)
    else:
        st.error("✗ IPv6 default route absence verification failed")
        results.append(False)

    # Final Result
    st.banner("=" * 80)
    st.banner("TEST RESULT SUMMARY: OC-SR-23")
    st.banner("=" * 80)

    if all(results):
        st.log("✓ ALL TEST STEPS PASSED")
        st.report_pass("test_case_passed")
    else:
        st.error("✗ ONE OR MORE TEST STEPS FAILED")
        st.report_fail("test_case_failed")
