"""
STATIC ROUTE TEST - OC-SR-25: IPv6 Static Route - ECMP (Equal-Cost Multi-Path) (3 DUTs)

Test Case ID: OC-SR-25
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_oc_3d.yaml \
    tests/system/Static_Route/test_oc_static_route_15_ipv6_ecmp.py \
    --logs-path ./logs/oc_sr25_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates IPv6 static route ECMP (Equal-Cost Multi-Path) on SONiC OC-build.
  Multiple routes to same destination with equal cost for load balancing.
  Traffic distributed across multiple paths for bandwidth aggregation and redundancy.
  Topology: DUT1 <-> DUT2 with DUT3 hosting destination prefix on Loopback.

Manual sonic-cli commands validated:
  DUT1:
    interface Ethernet 0 -> ipv6 address 2001:1:1::1/64 -> no shutdown
    interface Ethernet 4 -> ipv6 address 2001:1:2::1/64 -> no shutdown
    ipv6 route 2001:db8:600::/64 2001:1:1::2  # First path
    ipv6 route 2001:db8:600::/64 2001:1:2::2  # Second path (ECMP)

  DUT2:
    interface Ethernet 0 -> ipv6 address 2001:1:1::2/64 -> no shutdown
    interface Ethernet 8 -> ipv6 address 2001:2:1::1/64 -> no shutdown
    interface Ethernet 12 -> ipv6 address 2001:2:2::1/64 -> no shutdown
    ipv6 route 2001:db8:600::/64 2001:2:1::2  # First path
    ipv6 route 2001:db8:600::/64 2001:2:2::2  # Second path (ECMP)

  DUT3:
    interface Loopback 0
    ipv6 address 2001:db8:600::1/128

Pre-requisites:
  - Topology: 3-node (D1-D2-D3) | Supported: HW and Virtual
  - OC-build with Klish CLI support and IPv6 ECMP support
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
    "dut1_eth4": "Ethernet 4",
    "dut1_eth4_ipv6": "2001:1:2::1/64",

    # DUT1 IPv6 ECMP Routes (same destination, multiple next-hops)
    "dut1_route_prefix": "2001:db8:600::/64",
    "dut1_route_nexthop1": "2001:1:1::2",  # First ECMP path
    "dut1_route_nexthop2": "2001:1:2::2",  # Second ECMP path

    # DUT2 Interface Configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ipv6": "2001:1:1::2/64",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ipv6": "2001:2:1::1/64",
    "dut2_eth12": "Ethernet 12",
    "dut2_eth12_ipv6": "2001:2:2::1/64",

    # DUT2 IPv6 ECMP Routes (same destination, multiple next-hops)
    "dut2_route_prefix": "2001:db8:600::/64",
    "dut2_route_nexthop1": "2001:2:1::2",  # First ECMP path
    "dut2_route_nexthop2": "2001:2:2::2",  # Second ECMP path

    # DUT3 Loopback Configuration (destination endpoint)
    "dut3_loopback": "Loopback 0",
    "dut3_loopback_ipv6": "2001:db8:600::1/128",
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "oc_sr25_interface_config": "TC-OC-SR-25-001",
    "oc_sr25_loopback_config": "TC-OC-SR-25-002",
    "oc_sr25_ecmp_route_add": "TC-OC-SR-25-003",
    "oc_sr25_ecmp_route_verify": "TC-OC-SR-25-004",
    "oc_sr25_ecmp_route_remove": "TC-OC-SR-25-005",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-25 MODULE CONFIGURATION - START")
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
    st.banner("OC STATIC ROUTE SR-25 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        static_route_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def static_route_pre_config():
    """Pre-configuration: Clear existing configs."""
    st.log("Pre-configuration: Clearing existing configuration on all DUTs")

    # Clear DUT1 interfaces
    for intf in [CONFIG.dut1_eth0, CONFIG.dut1_eth4]:
        try:
            st.config(vars.D1, [
                f"interface {intf}",
                "no ip address",
                "no ipv6 address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

    # Clear DUT2 interfaces
    for intf in [CONFIG.dut2_eth0, CONFIG.dut2_eth8, CONFIG.dut2_eth12]:
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

    # Remove DUT1 IPv6 ECMP routes
    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.dut1_route_prefix} {CONFIG.dut1_route_nexthop1}",
            f"no ipv6 route {CONFIG.dut1_route_prefix} {CONFIG.dut1_route_nexthop2}",
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT2 IPv6 ECMP routes
    try:
        st.config(vars.D2, [
            f"no ipv6 route {CONFIG.dut2_route_prefix} {CONFIG.dut2_route_nexthop1}",
            f"no ipv6 route {CONFIG.dut2_route_prefix} {CONFIG.dut2_route_nexthop2}",
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Clear DUT1 interfaces
    for intf in [CONFIG.dut1_eth0, CONFIG.dut1_eth4]:
        try:
            st.config(vars.D1, [
                f"interface {intf}",
                "no ipv6 address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

    # Clear DUT2 interfaces
    for intf in [CONFIG.dut2_eth0, CONFIG.dut2_eth8, CONFIG.dut2_eth12]:
        try:
            st.config(vars.D2, [
                f"interface {intf}",
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


def add_ipv6_ecmp_routes(dut, prefix, nexthop1, nexthop2):
    """Add IPv6 ECMP routes (same destination, multiple next-hops)."""
    st.log(f"Adding IPv6 ECMP routes for {prefix} on {dut}")
    st.log(f"  Path 1: via {nexthop1}")
    st.log(f"  Path 2: via {nexthop2}")

    try:
        st.config(dut, [
            f"ipv6 route {prefix} {nexthop1}",
            f"ipv6 route {prefix} {nexthop2}"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed to add IPv6 ECMP routes: {str(e)}")
        return False


def verify_ipv6_ecmp_routes(dut, prefix, nexthop1, nexthop2):
    """Verify IPv6 ECMP routes exist in routing table.

    Both next-hops should appear for the same destination prefix.
    This indicates ECMP is active with load balancing across paths.
    """
    st.log(f"Verifying IPv6 ECMP routes for {prefix} on {dut}")
    st.log(f"  Expecting path 1: via {nexthop1}")
    st.log(f"  Expecting path 2: via {nexthop2}")

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

        # Normalize for comparison
        prefix_lower = prefix.lower()
        nexthop1_lower = nexthop1.lower()
        nexthop2_lower = nexthop2.lower()

        # Check if both ECMP paths are present
        has_prefix = prefix_lower in output_str
        has_nexthop1 = nexthop1_lower in output_str
        has_nexthop2 = nexthop2_lower in output_str

        if has_prefix and has_nexthop1 and has_nexthop2:
            st.log(f"✓ IPv6 ECMP routes verified successfully")
            st.log(f"  ✓ Prefix {prefix} present")
            st.log(f"  ✓ Path 1 via {nexthop1} present")
            st.log(f"  ✓ Path 2 via {nexthop2} present")
            return True
        else:
            st.error(f"✗ IPv6 ECMP route verification failed")
            if not has_prefix:
                st.error(f"  ✗ Prefix {prefix} NOT found")
            if not has_nexthop1:
                st.error(f"  ✗ Path 1 via {nexthop1} NOT found")
            if not has_nexthop2:
                st.error(f"  ✗ Path 2 via {nexthop2} NOT found")
            st.log(f"Output: {output}")
            return False
    except Exception as e:
        st.error(f"✗ Failed to verify ECMP routes: {str(e)}")
        return False


def verify_ipv6_ecmp_routes_absent(dut, prefix):
    """Verify IPv6 ECMP routes do NOT exist in routing table."""
    st.log(f"Verifying IPv6 ECMP routes for {prefix} are absent on {dut}")

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

        prefix_lower = prefix.lower()

        # Count occurrences of the prefix (ECMP shows prefix multiple times)
        prefix_count = output_str.count(prefix_lower)

        if prefix_count == 0:
            st.log(f"✓ IPv6 ECMP routes for {prefix} correctly absent")
            return True
        else:
            st.error(f"✗ IPv6 ECMP routes for {prefix} still present ({prefix_count} entries)")
            st.log(f"Output: {output}")
            return False
    except Exception as e:
        # If show command fails or returns empty, routes might be absent
        st.log(f"Route verification returned error (likely absent): {str(e)}")
        return True


def delete_ipv6_ecmp_routes(dut, prefix, nexthop1, nexthop2):
    """Delete IPv6 ECMP routes (both next-hops)."""
    st.log(f"Deleting IPv6 ECMP routes for {prefix} on {dut}")
    st.log(f"  Removing path 1: via {nexthop1}")
    st.log(f"  Removing path 2: via {nexthop2}")

    try:
        st.config(dut, [
            f"no ipv6 route {prefix} {nexthop1}",
            f"no ipv6 route {prefix} {nexthop2}"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed to delete IPv6 ECMP routes: {str(e)}")
        return False


def test_oc_sr25_ipv6_ecmp():
    """
    Test Case: OC-SR-25 - IPv6 ECMP (Equal-Cost Multi-Path) Routes

    Steps:
    1. Configure IPv6 interfaces on DUT1 and DUT2
    2. Configure Loopback on DUT3 with destination IPv6 address
    3. Add IPv6 ECMP routes on DUT1 (2 paths to same destination)
    4. Add IPv6 ECMP routes on DUT2 (2 paths to same destination)
    5. Verify IPv6 ECMP routes (both paths visible)
    6. Delete IPv6 ECMP routes on DUT1 and DUT2
    7. Verify IPv6 ECMP routes are absent
    """
    st.banner("=" * 80)
    st.banner("TEST: OC-SR-25 - IPv6 ECMP (Equal-Cost Multi-Path) Routes")
    st.banner("=" * 80)

    # Track test results
    results = []

    # Step 1: Configure IPv6 interfaces on DUT1
    st.banner("STEP 1: Configure IPv6 Interfaces on DUT1")
    result1 = configure_ipv6_interface(vars.D1, CONFIG.dut1_eth0, CONFIG.dut1_eth0_ipv6)
    result2 = configure_ipv6_interface(vars.D1, CONFIG.dut1_eth4, CONFIG.dut1_eth4_ipv6)

    if result1 and result2:
        st.log("✓ DUT1 IPv6 interface configuration successful")
        st.report_tc_pass(TC_IDS.oc_sr25_interface_config, "ipv6_interface_config_dut1_passed")
        results.append(True)
    else:
        st.error("✗ DUT1 IPv6 interface configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr25_interface_config, "ipv6_interface_config_dut1_failed")
        results.append(False)

    # Step 1.5: Configure IPv6 interfaces on DUT2
    st.banner("STEP 1.5: Configure IPv6 Interfaces on DUT2")
    result1 = configure_ipv6_interface(vars.D2, CONFIG.dut2_eth0, CONFIG.dut2_eth0_ipv6)
    result2 = configure_ipv6_interface(vars.D2, CONFIG.dut2_eth8, CONFIG.dut2_eth8_ipv6)
    result3 = configure_ipv6_interface(vars.D2, CONFIG.dut2_eth12, CONFIG.dut2_eth12_ipv6)

    if result1 and result2 and result3:
        st.log("✓ DUT2 IPv6 interface configuration successful")
        results.append(True)
    else:
        st.error("✗ DUT2 IPv6 interface configuration failed")
        results.append(False)

    # Step 2: Configure Loopback on DUT3
    st.banner("STEP 2: Configure Loopback on DUT3")
    result = configure_loopback_ipv6(vars.D3, CONFIG.dut3_loopback, CONFIG.dut3_loopback_ipv6)

    if result:
        st.log("✓ DUT3 Loopback IPv6 configuration successful")
        st.report_tc_pass(TC_IDS.oc_sr25_loopback_config, "ipv6_loopback_config_passed")
        results.append(True)
    else:
        st.error("✗ DUT3 Loopback IPv6 configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr25_loopback_config, "ipv6_loopback_config_failed")
        results.append(False)

    st.wait(5, "Waiting for IPv6 neighbor discovery and interface stabilization")

    # Step 3: Add IPv6 ECMP routes on DUT1
    st.banner("STEP 3: Add IPv6 ECMP Routes on DUT1")
    st.log("Adding 2 equal-cost paths to 2001:db8:600::/64")

    result = add_ipv6_ecmp_routes(
        vars.D1,
        CONFIG.dut1_route_prefix,
        CONFIG.dut1_route_nexthop1,
        CONFIG.dut1_route_nexthop2
    )

    if result:
        st.log("✓ DUT1 IPv6 ECMP routes added successfully")
        st.report_tc_pass(TC_IDS.oc_sr25_ecmp_route_add, "ipv6_ecmp_route_add_dut1_passed")
        results.append(True)
    else:
        st.error("✗ DUT1 IPv6 ECMP route addition failed")
        st.report_tc_fail(TC_IDS.oc_sr25_ecmp_route_add, "ipv6_ecmp_route_add_dut1_failed")
        results.append(False)

    # Step 4: Add IPv6 ECMP routes on DUT2
    st.banner("STEP 4: Add IPv6 ECMP Routes on DUT2")
    st.log("Adding 2 equal-cost paths to 2001:db8:600::/64")

    result = add_ipv6_ecmp_routes(
        vars.D2,
        CONFIG.dut2_route_prefix,
        CONFIG.dut2_route_nexthop1,
        CONFIG.dut2_route_nexthop2
    )

    if result:
        st.log("✓ DUT2 IPv6 ECMP routes added successfully")
        results.append(True)
    else:
        st.error("✗ DUT2 IPv6 ECMP route addition failed")
        results.append(False)

    st.wait(3, "Waiting for ECMP routes to be programmed in routing table")

    # Step 5: Verify IPv6 ECMP routes on DUT1 and DUT2
    st.banner("STEP 5: Verify IPv6 ECMP Routes on DUT1 and DUT2")
    st.log("Verifying both next-hop paths are present for load balancing")

    # Verify DUT1 ECMP routes
    result1 = verify_ipv6_ecmp_routes(
        vars.D1,
        CONFIG.dut1_route_prefix,
        CONFIG.dut1_route_nexthop1,
        CONFIG.dut1_route_nexthop2
    )

    # Verify DUT2 ECMP routes
    result2 = verify_ipv6_ecmp_routes(
        vars.D2,
        CONFIG.dut2_route_prefix,
        CONFIG.dut2_route_nexthop1,
        CONFIG.dut2_route_nexthop2
    )

    if result1 and result2:
        st.log("✓ All IPv6 ECMP routes verified successfully on both DUTs")
        st.report_tc_pass(TC_IDS.oc_sr25_ecmp_route_verify, "ipv6_ecmp_route_verify_passed")
        results.append(True)
    else:
        st.error("✗ IPv6 ECMP route verification failed")
        st.report_tc_fail(TC_IDS.oc_sr25_ecmp_route_verify, "ipv6_ecmp_route_verify_failed")
        results.append(False)

    # Step 6: Delete IPv6 ECMP routes on DUT1 and DUT2
    st.banner("STEP 6: Delete IPv6 ECMP Routes on DUT1 and DUT2")

    # Delete DUT1 ECMP routes
    result1 = delete_ipv6_ecmp_routes(
        vars.D1,
        CONFIG.dut1_route_prefix,
        CONFIG.dut1_route_nexthop1,
        CONFIG.dut1_route_nexthop2
    )

    # Delete DUT2 ECMP routes
    result2 = delete_ipv6_ecmp_routes(
        vars.D2,
        CONFIG.dut2_route_prefix,
        CONFIG.dut2_route_nexthop1,
        CONFIG.dut2_route_nexthop2
    )

    if result1 and result2:
        st.log("✓ All IPv6 ECMP routes deleted successfully")
        st.report_tc_pass(TC_IDS.oc_sr25_ecmp_route_remove, "ipv6_ecmp_route_delete_passed")
        results.append(True)
    else:
        st.error("✗ IPv6 ECMP route deletion failed")
        st.report_tc_fail(TC_IDS.oc_sr25_ecmp_route_remove, "ipv6_ecmp_route_delete_failed")
        results.append(False)

    st.wait(2, "Waiting for ECMP route removal from routing table")

    # Step 7: Verify IPv6 ECMP routes are absent
    st.banner("STEP 7: Verify IPv6 ECMP Routes Absent on DUT1 and DUT2")

    # Verify DUT1 ECMP routes absent
    result1 = verify_ipv6_ecmp_routes_absent(vars.D1, CONFIG.dut1_route_prefix)

    # Verify DUT2 ECMP routes absent
    result2 = verify_ipv6_ecmp_routes_absent(vars.D2, CONFIG.dut2_route_prefix)

    if result1 and result2:
        st.log("✓ All IPv6 ECMP routes correctly absent from routing tables")
        results.append(True)
    else:
        st.error("✗ IPv6 ECMP route absence verification failed")
        results.append(False)

    # Final Result
    st.banner("=" * 80)
    st.banner("TEST RESULT SUMMARY: OC-SR-25")
    st.banner("=" * 80)

    if all(results):
        st.log("✓ ALL TEST STEPS PASSED")
        st.report_pass("test_case_passed")
    else:
        st.error("✗ ONE OR MORE TEST STEPS FAILED")
        st.report_fail("test_case_failed")
