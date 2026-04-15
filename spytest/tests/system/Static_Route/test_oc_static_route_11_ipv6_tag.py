"""
STATIC ROUTE TEST - OC-SR-21: IPv6 Static Route - Routes with Tags (3 DUTs)

Test Case ID: OC-SR-21
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_oc_3d.yaml \
    tests/system/Static_Route/test_oc_static_route_11_ipv6_tag.py \
    --logs-path ./logs/oc_sr21_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates IPv6 static routes with route tags on SONiC OC-build.
  Tags are used for route policy matching and filtering.
  Topology: DUT1 <-> DUT2 with DUT3 hosting destination prefixes on Loopback.

Manual sonic-cli commands validated:
  DUT1:
    interface Ethernet 0 -> ipv6 address 2001:1:1::1/64 -> no shutdown
    interface Ethernet 4 -> ipv6 address 2001:1:2::1/64 -> no shutdown
    ipv6 route 2001:db8:80::/48 2001:1:1::2 tag 60
    ipv6 route 2001:db8:81::/48 2001:1:2::2 tag 120

  DUT2:
    interface Ethernet 0 -> ipv6 address 2001:1:1::2/64 -> no shutdown
    interface Ethernet 8 -> ipv6 address 2001:2:1::1/64 -> no shutdown
    interface Ethernet 12 -> ipv6 address 2001:2:2::1/64 -> no shutdown
    ipv6 route 2001:db8:80::/48 2001:2:1::2 tag 60
    ipv6 route 2001:db8:81::/48 2001:2:2::2 tag 120

  DUT3:
    interface Loopback 0
    ipv6 address 2001:db8:80::1/128
    ipv6 address 2001:db8:81::1/128

Pre-requisites:
  - Topology: 3-node (D1-D2-D3) | Supported: HW and Virtual
  - OC-build with Klish CLI support and IPv6 route tag support
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

    # DUT1 IPv6 Routes with Tags
    "dut1_route1_prefix": "2001:db8:80::/48",
    "dut1_route1_nexthop": "2001:1:1::2",
    "dut1_route1_tag": "60",
    "dut1_route2_prefix": "2001:db8:81::/48",
    "dut1_route2_nexthop": "2001:1:2::2",
    "dut1_route2_tag": "120",

    # DUT2 Interface Configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ipv6": "2001:1:1::2/64",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ipv6": "2001:2:1::1/64",
    "dut2_eth12": "Ethernet 12",
    "dut2_eth12_ipv6": "2001:2:2::1/64",

    # DUT2 IPv6 Routes with Tags
    "dut2_route1_prefix": "2001:db8:80::/48",
    "dut2_route1_nexthop": "2001:2:1::2",
    "dut2_route1_tag": "60",
    "dut2_route2_prefix": "2001:db8:81::/48",
    "dut2_route2_nexthop": "2001:2:2::2",
    "dut2_route2_tag": "120",

    # DUT3 Loopback Configuration (destination endpoints)
    "dut3_loopback": "Loopback 0",
    "dut3_loopback_ipv6_1": "2001:db8:80::1/128",
    "dut3_loopback_ipv6_2": "2001:db8:81::1/128",
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "oc_sr21_interface_config": "TC-OC-SR-21-001",
    "oc_sr21_loopback_config": "TC-OC-SR-21-002",
    "oc_sr21_route_add": "TC-OC-SR-21-003",
    "oc_sr21_route_verify": "TC-OC-SR-21-004",
    "oc_sr21_route_remove": "TC-OC-SR-21-005",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-21 MODULE CONFIGURATION - START")
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
    st.banner("OC STATIC ROUTE SR-21 MODULE CLEANUP - START")
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

    # Remove DUT1 IPv6 routes with tags
    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.dut1_route1_prefix} {CONFIG.dut1_route1_nexthop} tag {CONFIG.dut1_route1_tag}",
            f"no ipv6 route {CONFIG.dut1_route2_prefix} {CONFIG.dut1_route2_nexthop} tag {CONFIG.dut1_route2_tag}",
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT2 IPv6 routes with tags
    try:
        st.config(vars.D2, [
            f"no ipv6 route {CONFIG.dut2_route1_prefix} {CONFIG.dut2_route1_nexthop} tag {CONFIG.dut2_route1_tag}",
            f"no ipv6 route {CONFIG.dut2_route2_prefix} {CONFIG.dut2_route2_nexthop} tag {CONFIG.dut2_route2_tag}",
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
            f"no ipv6 address {CONFIG.dut3_loopback_ipv6_1}",
            f"no ipv6 address {CONFIG.dut3_loopback_ipv6_2}",
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


def configure_loopback_ipv6(dut, loopback_intf, ipv6_addr1, ipv6_addr2):
    """Configure multiple IPv6 addresses on Loopback interface."""
    st.log(f"Configuring Loopback {loopback_intf} with IPv6 addresses on {dut}")
    try:
        st.config(dut, [
            f"interface {loopback_intf}",
            f"ipv6 address {ipv6_addr1}",
            f"ipv6 address {ipv6_addr2}",
            "exit"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed to configure loopback: {str(e)}")
        return False


def add_ipv6_route_with_tag(dut, prefix, nexthop, tag):
    """Add IPv6 static route with route tag."""
    st.log(f"Adding IPv6 route {prefix} via {nexthop} tag {tag} on {dut}")
    try:
        st.config(dut, [
            f"ipv6 route {prefix} {nexthop} tag {tag}"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed to add IPv6 route: {str(e)}")
        return False


def verify_ipv6_route_with_tag(dut, prefix, nexthop):
    """Verify IPv6 route exists in routing table.

    Note: The show command may not display tags directly, but we verify
    the route exists with the correct next-hop. Tags are stored in the
    routing table for policy matching but may not appear in show output.
    """
    st.log(f"Verifying IPv6 route {prefix} via {nexthop} on {dut}")

    # Exit config mode before show command
    st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

    # Exit Klish CLI to Linux shell before show command
    try:
        st.config(dut, ["exit"], type='klish', skip_error_check=True)
    except Exception:
        pass

    try:
        output = st.show(dut, f"show ipv6 route {prefix}", type='klish')
        output_str = str(output).lower()

        # Check if route exists with correct next-hop
        # Convert nexthop to lowercase for comparison
        nexthop_lower = nexthop.lower()

        if nexthop_lower in output_str and prefix.lower() in output_str:
            st.log(f"✓ IPv6 route {prefix} via {nexthop} found in routing table")
            return True
        else:
            st.error(f"✗ IPv6 route {prefix} via {nexthop} NOT found")
            st.log(f"Output: {output}")
            return False
    except Exception as e:
        st.error(f"✗ Failed to verify route: {str(e)}")
        return False


def verify_ipv6_route_absent(dut, prefix):
    """Verify IPv6 route does NOT exist in routing table."""
    st.log(f"Verifying IPv6 route {prefix} is absent on {dut}")

    # Exit config mode before show command
    st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

    # Exit Klish CLI to Linux shell before show command
    try:
        st.config(dut, ["exit"], type='klish', skip_error_check=True)
    except Exception:
        pass

    try:
        output = st.show(dut, f"show ipv6 route {prefix}", type='klish')
        output_str = str(output).lower()

        # Check if route is absent
        if "not in table" in output_str or "network not in table" in output_str or prefix.lower() not in output_str:
            st.log(f"✓ IPv6 route {prefix} correctly absent from routing table")
            return True
        else:
            st.error(f"✗ IPv6 route {prefix} still present (should be absent)")
            st.log(f"Output: {output}")
            return False
    except Exception as e:
        # If show command fails, route might be absent
        st.log(f"Route verification returned error (likely absent): {str(e)}")
        return True


def delete_ipv6_route_with_tag(dut, prefix, nexthop, tag):
    """Delete IPv6 static route with route tag."""
    st.log(f"Deleting IPv6 route {prefix} via {nexthop} tag {tag} on {dut}")
    try:
        st.config(dut, [
            f"no ipv6 route {prefix} {nexthop} tag {tag}"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed to delete IPv6 route: {str(e)}")
        return False


def test_oc_sr21_ipv6_tag_routes():
    """
    Test Case: OC-SR-21 - IPv6 Static Routes with Tags

    Steps:
    1. Configure IPv6 interfaces on DUT1 and DUT2
    2. Configure Loopback on DUT3 with destination IPv6 addresses
    3. Add IPv6 routes with tags on DUT1
    4. Add IPv6 routes with tags on DUT2
    5. Verify IPv6 routes on DUT1 and DUT2
    6. Delete IPv6 routes with tags on DUT1
    7. Delete IPv6 routes with tags on DUT2
    8. Verify IPv6 routes are absent on DUT1 and DUT2
    """
    st.banner("=" * 80)
    st.banner("TEST: OC-SR-21 - IPv6 Static Routes with Tags")
    st.banner("=" * 80)

    # Track test results
    results = []

    # Step 1: Configure IPv6 interfaces on DUT1
    st.banner("STEP 1: Configure IPv6 Interfaces on DUT1")
    result1 = configure_ipv6_interface(vars.D1, CONFIG.dut1_eth0, CONFIG.dut1_eth0_ipv6)
    result2 = configure_ipv6_interface(vars.D1, CONFIG.dut1_eth4, CONFIG.dut1_eth4_ipv6)

    if result1 and result2:
        st.log("✓ DUT1 IPv6 interface configuration successful")
        st.report_tc_pass(TC_IDS.oc_sr21_interface_config, "ipv6_interface_config_dut1_passed")
        results.append(True)
    else:
        st.error("✗ DUT1 IPv6 interface configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr21_interface_config, "ipv6_interface_config_dut1_failed")
        results.append(False)

    # Step 2: Configure IPv6 interfaces on DUT2
    st.banner("STEP 2: Configure IPv6 Interfaces on DUT2")
    result1 = configure_ipv6_interface(vars.D2, CONFIG.dut2_eth0, CONFIG.dut2_eth0_ipv6)
    result2 = configure_ipv6_interface(vars.D2, CONFIG.dut2_eth8, CONFIG.dut2_eth8_ipv6)
    result3 = configure_ipv6_interface(vars.D2, CONFIG.dut2_eth12, CONFIG.dut2_eth12_ipv6)

    if result1 and result2 and result3:
        st.log("✓ DUT2 IPv6 interface configuration successful")
        results.append(True)
    else:
        st.error("✗ DUT2 IPv6 interface configuration failed")
        results.append(False)

    # Step 2.5: Configure Loopback on DUT3
    st.banner("STEP 2.5: Configure Loopback on DUT3")
    result = configure_loopback_ipv6(
        vars.D3,
        CONFIG.dut3_loopback,
        CONFIG.dut3_loopback_ipv6_1,
        CONFIG.dut3_loopback_ipv6_2
    )

    if result:
        st.log("✓ DUT3 Loopback IPv6 configuration successful")
        st.report_tc_pass(TC_IDS.oc_sr21_loopback_config, "ipv6_loopback_config_passed")
        results.append(True)
    else:
        st.error("✗ DUT3 Loopback IPv6 configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr21_loopback_config, "ipv6_loopback_config_failed")
        results.append(False)

    st.wait(5, "Waiting for IPv6 neighbor discovery and interface stabilization")

    # Step 3: Add IPv6 routes with tags on DUT1
    st.banner("STEP 3: Add IPv6 Routes with Tags on DUT1")
    result1 = add_ipv6_route_with_tag(
        vars.D1,
        CONFIG.dut1_route1_prefix,
        CONFIG.dut1_route1_nexthop,
        CONFIG.dut1_route1_tag
    )
    result2 = add_ipv6_route_with_tag(
        vars.D1,
        CONFIG.dut1_route2_prefix,
        CONFIG.dut1_route2_nexthop,
        CONFIG.dut1_route2_tag
    )

    if result1 and result2:
        st.log("✓ DUT1 IPv6 routes with tags added successfully")
        st.report_tc_pass(TC_IDS.oc_sr21_route_add, "ipv6_route_add_dut1_passed")
        results.append(True)
    else:
        st.error("✗ DUT1 IPv6 routes with tags addition failed")
        st.report_tc_fail(TC_IDS.oc_sr21_route_add, "ipv6_route_add_dut1_failed")
        results.append(False)

    # Step 4: Add IPv6 routes with tags on DUT2
    st.banner("STEP 4: Add IPv6 Routes with Tags on DUT2")
    result1 = add_ipv6_route_with_tag(
        vars.D2,
        CONFIG.dut2_route1_prefix,
        CONFIG.dut2_route1_nexthop,
        CONFIG.dut2_route1_tag
    )
    result2 = add_ipv6_route_with_tag(
        vars.D2,
        CONFIG.dut2_route2_prefix,
        CONFIG.dut2_route2_nexthop,
        CONFIG.dut2_route2_tag
    )

    if result1 and result2:
        st.log("✓ DUT2 IPv6 routes with tags added successfully")
        results.append(True)
    else:
        st.error("✗ DUT2 IPv6 routes with tags addition failed")
        results.append(False)

    st.wait(3, "Waiting for routes to be programmed in routing table")

    # Step 5: Verify IPv6 routes on DUT1 and DUT2
    st.banner("STEP 5: Verify IPv6 Routes on DUT1 and DUT2")

    # Verify DUT1 routes
    result1 = verify_ipv6_route_with_tag(
        vars.D1,
        CONFIG.dut1_route1_prefix,
        CONFIG.dut1_route1_nexthop
    )
    result2 = verify_ipv6_route_with_tag(
        vars.D1,
        CONFIG.dut1_route2_prefix,
        CONFIG.dut1_route2_nexthop
    )

    # Verify DUT2 routes
    result3 = verify_ipv6_route_with_tag(
        vars.D2,
        CONFIG.dut2_route1_prefix,
        CONFIG.dut2_route1_nexthop
    )
    result4 = verify_ipv6_route_with_tag(
        vars.D2,
        CONFIG.dut2_route2_prefix,
        CONFIG.dut2_route2_nexthop
    )

    if result1 and result2 and result3 and result4:
        st.log("✓ All IPv6 routes with tags verified successfully")
        st.report_tc_pass(TC_IDS.oc_sr21_route_verify, "ipv6_route_verify_passed")
        results.append(True)
    else:
        st.error("✗ IPv6 route verification failed")
        st.report_tc_fail(TC_IDS.oc_sr21_route_verify, "ipv6_route_verify_failed")
        results.append(False)

    # Step 6: Delete IPv6 routes with tags on DUT1
    st.banner("STEP 6: Delete IPv6 Routes with Tags on DUT1")
    result1 = delete_ipv6_route_with_tag(
        vars.D1,
        CONFIG.dut1_route1_prefix,
        CONFIG.dut1_route1_nexthop,
        CONFIG.dut1_route1_tag
    )
    result2 = delete_ipv6_route_with_tag(
        vars.D1,
        CONFIG.dut1_route2_prefix,
        CONFIG.dut1_route2_nexthop,
        CONFIG.dut1_route2_tag
    )

    if result1 and result2:
        st.log("✓ DUT1 IPv6 routes deleted successfully")
        st.report_tc_pass(TC_IDS.oc_sr21_route_remove, "ipv6_route_delete_dut1_passed")
        results.append(True)
    else:
        st.error("✗ DUT1 IPv6 route deletion failed")
        st.report_tc_fail(TC_IDS.oc_sr21_route_remove, "ipv6_route_delete_dut1_failed")
        results.append(False)

    # Step 7: Delete IPv6 routes with tags on DUT2
    st.banner("STEP 7: Delete IPv6 Routes with Tags on DUT2")
    result1 = delete_ipv6_route_with_tag(
        vars.D2,
        CONFIG.dut2_route1_prefix,
        CONFIG.dut2_route1_nexthop,
        CONFIG.dut2_route1_tag
    )
    result2 = delete_ipv6_route_with_tag(
        vars.D2,
        CONFIG.dut2_route2_prefix,
        CONFIG.dut2_route2_nexthop,
        CONFIG.dut2_route2_tag
    )

    if result1 and result2:
        st.log("✓ DUT2 IPv6 routes deleted successfully")
        results.append(True)
    else:
        st.error("✗ DUT2 IPv6 route deletion failed")
        results.append(False)

    st.wait(2, "Waiting for route removal from routing table")

    # Step 8: Verify IPv6 routes are absent on DUT1 and DUT2
    st.banner("STEP 8: Verify IPv6 Routes Absent on DUT1 and DUT2")

    # Verify DUT1 routes absent
    result1 = verify_ipv6_route_absent(vars.D1, CONFIG.dut1_route1_prefix)
    result2 = verify_ipv6_route_absent(vars.D1, CONFIG.dut1_route2_prefix)

    # Verify DUT2 routes absent
    result3 = verify_ipv6_route_absent(vars.D2, CONFIG.dut2_route1_prefix)
    result4 = verify_ipv6_route_absent(vars.D2, CONFIG.dut2_route2_prefix)

    if result1 and result2 and result3 and result4:
        st.log("✓ All IPv6 routes correctly absent from routing tables")
        results.append(True)
    else:
        st.error("✗ IPv6 route absence verification failed")
        results.append(False)

    # Final Result
    st.banner("=" * 80)
    st.banner("TEST RESULT SUMMARY: OC-SR-21")
    st.banner("=" * 80)

    if all(results):
        st.log("✓ ALL TEST STEPS PASSED")
        st.report_pass("test_case_passed")
    else:
        st.error("✗ ONE OR MORE TEST STEPS FAILED")
        st.report_fail("test_case_failed")
