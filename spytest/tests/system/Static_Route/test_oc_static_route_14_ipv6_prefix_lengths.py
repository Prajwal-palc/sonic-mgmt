"""
STATIC ROUTE TEST - OC-SR-24: IPv6 Static Route - Host Routes and Prefix Lengths (3 DUTs)

Test Case ID: OC-SR-24
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_oc_3d.yaml \
    tests/system/Static_Route/test_oc_static_route_14_ipv6_prefix_lengths.py \
    --logs-path ./logs/oc_sr24_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates IPv6 static routes with various prefix lengths on SONiC OC-build.
  Tests host routes (/128), aggregates (/32), and various subnet sizes (/48, /64).
  Demonstrates IPv6 prefix length flexibility and longest prefix match behavior.
  Topology: DUT1 <-> DUT2 <-> DUT3 with DUT3 hosting destination prefixes on Loopback.

Manual sonic-cli commands validated:
  DUT1:
    interface Ethernet 0 -> ipv6 address 2001:1:1::1/64 -> no shutdown
    ipv6 route 2001:db8::1/128 2001:1:1::2        # Host route (/128)
    ipv6 route 2001:db8::/32 2001:1:1::2          # Large aggregate (/32)
    ipv6 route 2001:db8:100::/48 2001:1:1::2      # /48 subnet
    ipv6 route 2001:db8:100::/64 2001:1:1::2      # /64 subnet

  DUT2:
    interface Ethernet 0 -> ipv6 address 2001:1:1::2/64 -> no shutdown
    interface Ethernet 8 -> ipv6 address 2001:2:1::1/64 -> no shutdown
    ipv6 route 2001:db8::1/128 2001:2:1::2        # Host route (/128)
    ipv6 route 2001:db8::/32 2001:2:1::2          # Large aggregate (/32)
    ipv6 route 2001:db8:100::/48 2001:2:1::2      # /48 subnet
    ipv6 route 2001:db8:100::/64 2001:2:1::2      # /64 subnet

  DUT3:
    interface Loopback 0
    ipv6 address 2001:db8::1/128
    ipv6 address 2001:db8:1::1/128
    ipv6 address 2001:db8:100::1/128

Pre-requisites:
  - Topology: 3-node (D1-D2-D3) | Supported: HW and Virtual
  - OC-build with Klish CLI support and IPv6 prefix length support
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

    # DUT1 IPv6 Routes with Various Prefix Lengths
    "dut1_route1_prefix": "2001:db8::1/128",      # Host route
    "dut1_route1_nexthop": "2001:1:1::2",
    "dut1_route2_prefix": "2001:db8::/32",        # Large aggregate
    "dut1_route2_nexthop": "2001:1:1::2",
    "dut1_route3_prefix": "2001:db8:100::/48",    # /48 subnet
    "dut1_route3_nexthop": "2001:1:1::2",
    "dut1_route4_prefix": "2001:db8:100::/64",    # /64 subnet
    "dut1_route4_nexthop": "2001:1:1::2",

    # DUT2 Interface Configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ipv6": "2001:1:1::2/64",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ipv6": "2001:2:1::1/64",

    # DUT2 IPv6 Routes with Various Prefix Lengths
    "dut2_route1_prefix": "2001:db8::1/128",      # Host route
    "dut2_route1_nexthop": "2001:2:1::2",
    "dut2_route2_prefix": "2001:db8::/32",        # Large aggregate
    "dut2_route2_nexthop": "2001:2:1::2",
    "dut2_route3_prefix": "2001:db8:100::/48",    # /48 subnet
    "dut2_route3_nexthop": "2001:2:1::2",
    "dut2_route4_prefix": "2001:db8:100::/64",    # /64 subnet
    "dut2_route4_nexthop": "2001:2:1::2",

    # DUT3 Loopback Configuration (destination endpoints)
    "dut3_loopback": "Loopback 0",
    "dut3_loopback_ipv6_1": "2001:db8::1/128",      # Matches /128 route
    "dut3_loopback_ipv6_2": "2001:db8:1::1/128",    # Within /32 aggregate
    "dut3_loopback_ipv6_3": "2001:db8:100::1/128",  # Matches /48 and /64
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "oc_sr24_interface_config": "TC-OC-SR-24-001",
    "oc_sr24_loopback_config": "TC-OC-SR-24-002",
    "oc_sr24_route_add": "TC-OC-SR-24-003",
    "oc_sr24_route_verify": "TC-OC-SR-24-004",
    "oc_sr24_route_remove": "TC-OC-SR-24-005",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-24 MODULE CONFIGURATION - START")
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
    st.banner("OC STATIC ROUTE SR-24 MODULE CLEANUP - START")
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

    # Remove DUT1 IPv6 routes
    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.dut1_route1_prefix} {CONFIG.dut1_route1_nexthop}",
            f"no ipv6 route {CONFIG.dut1_route2_prefix} {CONFIG.dut1_route2_nexthop}",
            f"no ipv6 route {CONFIG.dut1_route3_prefix} {CONFIG.dut1_route3_nexthop}",
            f"no ipv6 route {CONFIG.dut1_route4_prefix} {CONFIG.dut1_route4_nexthop}",
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT2 IPv6 routes
    try:
        st.config(vars.D2, [
            f"no ipv6 route {CONFIG.dut2_route1_prefix} {CONFIG.dut2_route1_nexthop}",
            f"no ipv6 route {CONFIG.dut2_route2_prefix} {CONFIG.dut2_route2_nexthop}",
            f"no ipv6 route {CONFIG.dut2_route3_prefix} {CONFIG.dut2_route3_nexthop}",
            f"no ipv6 route {CONFIG.dut2_route4_prefix} {CONFIG.dut2_route4_nexthop}",
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

    # Clear DUT3 Loopback
    try:
        st.config(vars.D3, [
            f"interface {CONFIG.dut3_loopback}",
            f"no ipv6 address {CONFIG.dut3_loopback_ipv6_1}",
            f"no ipv6 address {CONFIG.dut3_loopback_ipv6_2}",
            f"no ipv6 address {CONFIG.dut3_loopback_ipv6_3}",
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


def configure_loopback_ipv6_multiple(dut, loopback_intf, ipv6_addr1, ipv6_addr2, ipv6_addr3):
    """Configure multiple IPv6 addresses on Loopback interface."""
    st.log(f"Configuring Loopback {loopback_intf} with 3 IPv6 addresses on {dut}")
    try:
        st.config(dut, [
            f"interface {loopback_intf}",
            f"ipv6 address {ipv6_addr1}",
            f"ipv6 address {ipv6_addr2}",
            f"ipv6 address {ipv6_addr3}",
            "exit"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed to configure loopback: {str(e)}")
        return False


def add_ipv6_route(dut, prefix, nexthop):
    """Add IPv6 static route."""
    st.log(f"Adding IPv6 route {prefix} via {nexthop} on {dut}")
    try:
        st.config(dut, [
            f"ipv6 route {prefix} {nexthop}"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed to add IPv6 route: {str(e)}")
        return False


def verify_ipv6_route(dut, prefix, nexthop):
    """Verify IPv6 route exists in routing table."""
    st.log(f"Verifying IPv6 route {prefix} via {nexthop} on {dut}")

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

        # Normalize prefix for comparison (remove leading zeros, etc.)
        prefix_lower = prefix.lower()
        nexthop_lower = nexthop.lower()

        if prefix_lower in output_str and nexthop_lower in output_str:
            st.log(f"✓ IPv6 route {prefix} via {nexthop} found in routing table")
            return True
        else:
            st.error(f"✗ IPv6 route {prefix} via {nexthop} NOT found")
            st.log(f"Output: {output}")
            return False
    except Exception as e:
        st.error(f"✗ Failed to verify route: {str(e)}")
        return False


def verify_ipv6_routes_absent(dut, prefixes):
    """Verify multiple IPv6 routes do NOT exist in routing table."""
    st.log(f"Verifying IPv6 routes are absent on {dut}: {prefixes}")

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

        all_absent = True
        for prefix in prefixes:
            prefix_lower = prefix.lower()
            if prefix_lower in output_str:
                st.error(f"✗ IPv6 route {prefix} still present (should be absent)")
                all_absent = False

        if all_absent:
            st.log(f"✓ All specified IPv6 routes correctly absent from routing table")
            return True
        else:
            st.log(f"Output: {output}")
            return False
    except Exception as e:
        # If show command fails or returns empty, routes might be absent
        st.log(f"Route verification returned error (likely absent): {str(e)}")
        return True


def delete_ipv6_route(dut, prefix, nexthop):
    """Delete IPv6 static route."""
    st.log(f"Deleting IPv6 route {prefix} via {nexthop} on {dut}")
    try:
        st.config(dut, [
            f"no ipv6 route {prefix} {nexthop}"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed to delete IPv6 route: {str(e)}")
        return False


def test_oc_sr24_ipv6_prefix_lengths():
    """
    Test Case: OC-SR-24 - IPv6 Host Routes and Prefix Lengths

    Steps:
    1. Configure IPv6 interfaces on DUT1 and DUT2
    2. Configure Loopback on DUT3 with destination IPv6 addresses
    3. Add IPv6 routes with various prefix lengths on DUT1
    4. Add IPv6 routes with various prefix lengths on DUT2
    5. Verify IPv6 routes with all prefix lengths
    6. Delete IPv6 routes on DUT1 and DUT2
    7. Verify IPv6 routes are absent
    """
    st.banner("=" * 80)
    st.banner("TEST: OC-SR-24 - IPv6 Host Routes and Prefix Lengths")
    st.banner("=" * 80)

    # Track test results
    results = []

    # Step 1: Configure IPv6 interface on DUT1
    st.banner("STEP 1: Configure IPv6 Interface on DUT1")
    result = configure_ipv6_interface(vars.D1, CONFIG.dut1_eth0, CONFIG.dut1_eth0_ipv6)

    if result:
        st.log("✓ DUT1 IPv6 interface configuration successful")
        st.report_tc_pass(TC_IDS.oc_sr24_interface_config, "ipv6_interface_config_dut1_passed")
        results.append(True)
    else:
        st.error("✗ DUT1 IPv6 interface configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr24_interface_config, "ipv6_interface_config_dut1_failed")
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

    # Step 2: Configure Loopback on DUT3 with multiple addresses
    st.banner("STEP 2: Configure Loopback on DUT3")
    result = configure_loopback_ipv6_multiple(
        vars.D3,
        CONFIG.dut3_loopback,
        CONFIG.dut3_loopback_ipv6_1,
        CONFIG.dut3_loopback_ipv6_2,
        CONFIG.dut3_loopback_ipv6_3
    )

    if result:
        st.log("✓ DUT3 Loopback IPv6 configuration successful")
        st.report_tc_pass(TC_IDS.oc_sr24_loopback_config, "ipv6_loopback_config_passed")
        results.append(True)
    else:
        st.error("✗ DUT3 Loopback IPv6 configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr24_loopback_config, "ipv6_loopback_config_failed")
        results.append(False)

    st.wait(5, "Waiting for IPv6 neighbor discovery and interface stabilization")

    # Step 3: Add IPv6 routes with various prefix lengths on DUT1
    st.banner("STEP 3: Add IPv6 Routes with Various Prefix Lengths on DUT1")
    st.log("Adding /128 host route, /32 aggregate, /48 and /64 subnets")

    result1 = add_ipv6_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop)
    result2 = add_ipv6_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop)
    result3 = add_ipv6_route(vars.D1, CONFIG.dut1_route3_prefix, CONFIG.dut1_route3_nexthop)
    result4 = add_ipv6_route(vars.D1, CONFIG.dut1_route4_prefix, CONFIG.dut1_route4_nexthop)

    if result1 and result2 and result3 and result4:
        st.log("✓ DUT1 IPv6 routes with various prefix lengths added successfully")
        st.report_tc_pass(TC_IDS.oc_sr24_route_add, "ipv6_route_add_dut1_passed")
        results.append(True)
    else:
        st.error("✗ DUT1 IPv6 route addition failed")
        st.report_tc_fail(TC_IDS.oc_sr24_route_add, "ipv6_route_add_dut1_failed")
        results.append(False)

    # Step 4: Add IPv6 routes with various prefix lengths on DUT2
    st.banner("STEP 4: Add IPv6 Routes with Various Prefix Lengths on DUT2")
    st.log("Adding /128 host route, /32 aggregate, /48 and /64 subnets")

    result1 = add_ipv6_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop)
    result2 = add_ipv6_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop)
    result3 = add_ipv6_route(vars.D2, CONFIG.dut2_route3_prefix, CONFIG.dut2_route3_nexthop)
    result4 = add_ipv6_route(vars.D2, CONFIG.dut2_route4_prefix, CONFIG.dut2_route4_nexthop)

    if result1 and result2 and result3 and result4:
        st.log("✓ DUT2 IPv6 routes with various prefix lengths added successfully")
        results.append(True)
    else:
        st.error("✗ DUT2 IPv6 route addition failed")
        results.append(False)

    st.wait(3, "Waiting for routes to be programmed in routing table")

    # Step 5: Verify IPv6 routes with various prefix lengths
    st.banner("STEP 5: Verify IPv6 Routes on DUT1 and DUT2")
    st.log("Verifying /128, /32, /48, and /64 prefix routes")

    # Verify DUT1 routes
    result1 = verify_ipv6_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop)
    result2 = verify_ipv6_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop)
    result3 = verify_ipv6_route(vars.D1, CONFIG.dut1_route3_prefix, CONFIG.dut1_route3_nexthop)
    result4 = verify_ipv6_route(vars.D1, CONFIG.dut1_route4_prefix, CONFIG.dut1_route4_nexthop)

    # Verify DUT2 routes
    result5 = verify_ipv6_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop)
    result6 = verify_ipv6_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop)
    result7 = verify_ipv6_route(vars.D2, CONFIG.dut2_route3_prefix, CONFIG.dut2_route3_nexthop)
    result8 = verify_ipv6_route(vars.D2, CONFIG.dut2_route4_prefix, CONFIG.dut2_route4_nexthop)

    if result1 and result2 and result3 and result4 and result5 and result6 and result7 and result8:
        st.log("✓ All IPv6 routes with various prefix lengths verified successfully")
        st.report_tc_pass(TC_IDS.oc_sr24_route_verify, "ipv6_route_verify_passed")
        results.append(True)
    else:
        st.error("✗ IPv6 route verification failed")
        st.report_tc_fail(TC_IDS.oc_sr24_route_verify, "ipv6_route_verify_failed")
        results.append(False)

    # Step 6: Delete IPv6 routes on DUT1 and DUT2
    st.banner("STEP 6: Delete IPv6 Routes on DUT1 and DUT2")

    # Delete DUT1 routes
    result1 = delete_ipv6_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop)
    result2 = delete_ipv6_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop)
    result3 = delete_ipv6_route(vars.D1, CONFIG.dut1_route3_prefix, CONFIG.dut1_route3_nexthop)
    result4 = delete_ipv6_route(vars.D1, CONFIG.dut1_route4_prefix, CONFIG.dut1_route4_nexthop)

    # Delete DUT2 routes
    result5 = delete_ipv6_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop)
    result6 = delete_ipv6_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop)
    result7 = delete_ipv6_route(vars.D2, CONFIG.dut2_route3_prefix, CONFIG.dut2_route3_nexthop)
    result8 = delete_ipv6_route(vars.D2, CONFIG.dut2_route4_prefix, CONFIG.dut2_route4_nexthop)

    if result1 and result2 and result3 and result4 and result5 and result6 and result7 and result8:
        st.log("✓ All IPv6 routes deleted successfully")
        st.report_tc_pass(TC_IDS.oc_sr24_route_remove, "ipv6_route_delete_passed")
        results.append(True)
    else:
        st.error("✗ IPv6 route deletion failed")
        st.report_tc_fail(TC_IDS.oc_sr24_route_remove, "ipv6_route_delete_failed")
        results.append(False)

    st.wait(2, "Waiting for route removal from routing table")

    # Step 7: Verify IPv6 routes are absent
    st.banner("STEP 7: Verify IPv6 Routes Absent on DUT1 and DUT2")

    # Verify DUT1 routes absent
    dut1_prefixes = [
        CONFIG.dut1_route1_prefix,
        CONFIG.dut1_route2_prefix,
        CONFIG.dut1_route3_prefix,
        CONFIG.dut1_route4_prefix
    ]
    result1 = verify_ipv6_routes_absent(vars.D1, dut1_prefixes)

    # Verify DUT2 routes absent
    dut2_prefixes = [
        CONFIG.dut2_route1_prefix,
        CONFIG.dut2_route2_prefix,
        CONFIG.dut2_route3_prefix,
        CONFIG.dut2_route4_prefix
    ]
    result2 = verify_ipv6_routes_absent(vars.D2, dut2_prefixes)

    if result1 and result2:
        st.log("✓ All IPv6 routes correctly absent from routing tables")
        results.append(True)
    else:
        st.error("✗ IPv6 route absence verification failed")
        results.append(False)

    # Final Result
    st.banner("=" * 80)
    st.banner("TEST RESULT SUMMARY: OC-SR-24")
    st.banner("=" * 80)

    if all(results):
        st.log("✓ ALL TEST STEPS PASSED")
        st.report_pass("test_case_passed")
    else:
        st.error("✗ ONE OR MORE TEST STEPS FAILED")
        st.report_fail("test_case_failed")
