"""
STATIC ROUTE TEST - OC-SR-19: IPv6 Static Route - Blackhole Routes

Test Case ID: OC-SR-19
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_oc_2d.yaml \\
  tests/system/Static_Route/test_oc_static_route_09_ipv6_blackhole.py \\
  --logs-path ./logs/oc_sr_19_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Verify IPv6 static blackhole routes on SONiC OC-build using Klish CLI.
  Blackhole routes silently drop packets destined to specified prefixes,
  showing as "Unreachable (blackhole)" in routing table.

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - OC-build with Klish CLI support
  - IPv6 enabled on interfaces
  - Test variables: spytest/vars/static_route/oc_static_route_vars.yaml
"""

import pytest
from spytest import st, SpyTestDict

# Test case IDs
TC_IDS = SpyTestDict({
    "ipv6_interface_config": "TC-OC-SR-19-001",
    "ipv6_blackhole_add": "TC-OC-SR-19-002",
    "ipv6_blackhole_verify": "TC-OC-SR-19-003",
    "ipv6_blackhole_delete": "TC-OC-SR-19-004",
    "ipv6_blackhole_verify_delete": "TC-OC-SR-19-005",
})

# Module level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    # DUT1 Interface Configuration
    "dut1_eth0": "Ethernet 0",
    "dut1_eth0_ipv6": "2001:1:1::1/64",

    # DUT2 Interface Configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ipv6": "2001:1:1::2/64",

    # DUT1 IPv6 Routes (blackhole + normal)
    "dut1_route_dead": "2001:db8:dead::/48",
    "dut1_route_dead_nh": "2001:1:1::1",
    "dut1_route_beef": "2001:db8:beef::/48",  # Blackhole route
    "dut1_route_cafe": "2001:db8:cafe::/48",
    "dut1_route_cafe_nh": "2001:2:1::2",

    # DUT2 IPv6 Routes (blackhole + normal)
    "dut2_route_dead": "2001:db8:dead::/48",
    "dut2_route_dead_nh": "2001:1:1::1",
    "dut2_route_beef": "2001:db8:beef::/48",  # Blackhole route
    "dut2_route_cafe": "2001:db8:cafe::/48",
    "dut2_route_cafe_nh": "2001:2:1::2",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module level fixture for setup and teardown."""
    global vars, data

    st.banner("MODULE PROLOGUE: OC-SR-19 - IPv6 Blackhole Routes")

    try:
        # Get testbed variables
        vars = st.ensure_min_topology("D1D2:1")

        # Set CLI type
        data.cli_type = 'klish'
        st.log(f"Using CLI type: {data.cli_type}")
        st.log(f"Test devices: D1={vars.D1}, D2={vars.D2}")

        # Pre-configuration
        static_route_pre_config()

    except Exception as e:
        st.error(f"Module prologue failed: {str(e)}")
        st.report_fail("module_config_failed", e)

    yield

    # Module cleanup - always executes
    st.banner("MODULE EPILOGUE: Cleanup")
    try:
        static_route_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def static_route_pre_config():
    """Pre-configuration: Clear existing configs."""
    st.log("Pre-configuration: Clearing existing configuration on DUT1 and DUT2")

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

    # Clear DUT2 interface
    try:
        st.config(vars.D2, [
            f"interface {CONFIG.dut2_eth0}",
            "no ipv6 address",
            "shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT1 routes if they exist
    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.dut1_route_dead} {CONFIG.dut1_route_dead_nh}",
            f"no ipv6 route {CONFIG.dut1_route_beef} blackhole",
            f"no ipv6 route {CONFIG.dut1_route_cafe} {CONFIG.dut1_route_cafe_nh}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT2 routes if they exist
    try:
        st.config(vars.D2, [
            f"no ipv6 route {CONFIG.dut2_route_dead} {CONFIG.dut2_route_dead_nh}",
            f"no ipv6 route {CONFIG.dut2_route_beef} blackhole",
            f"no ipv6 route {CONFIG.dut2_route_cafe} {CONFIG.dut2_route_cafe_nh}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Explicitly exit Klish CLI mode back to normal user mode on all DUTs
    for dut in [vars.D1, vars.D2]:
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

    st.wait(3, "Waiting for pre-config clear")
    st.log("Pre-configuration completed")


def static_route_cleanup():
    """Cleanup: Remove static routes and IP configuration."""
    st.log("Cleanup: Removing IPv6 blackhole routes and IP configuration")

    # Remove DUT1 routes
    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.dut1_route_dead} {CONFIG.dut1_route_dead_nh}",
            f"no ipv6 route {CONFIG.dut1_route_beef} blackhole",
            f"no ipv6 route {CONFIG.dut1_route_cafe} {CONFIG.dut1_route_cafe_nh}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT1 route cleanup warning: {str(e)}")

    # Remove DUT2 routes
    try:
        st.config(vars.D2, [
            f"no ipv6 route {CONFIG.dut2_route_dead} {CONFIG.dut2_route_dead_nh}",
            f"no ipv6 route {CONFIG.dut2_route_beef} blackhole",
            f"no ipv6 route {CONFIG.dut2_route_cafe} {CONFIG.dut2_route_cafe_nh}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT2 route cleanup warning: {str(e)}")

    # Clear IPv6 addresses - DUT1
    try:
        st.config(vars.D1, [
            f"interface {CONFIG.dut1_eth0}",
            "no ipv6 address",
            "shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT1 interface cleanup warning: {str(e)}")

    # Clear IPv6 addresses - DUT2
    try:
        st.config(vars.D2, [
            f"interface {CONFIG.dut2_eth0}",
            "no ipv6 address",
            "shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT2 interface cleanup warning: {str(e)}")

    # Explicitly exit Klish CLI mode back to normal user mode on all DUTs
    for dut in [vars.D1, vars.D2]:
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


def configure_interface_ipv6(dut, interface, ipv6_with_prefix):
    """Configure IPv6 on interface."""
    st.log(f"Configuring IPv6 {ipv6_with_prefix} on {dut} {interface}")
    try:
        st.config(dut, [
            f"interface {interface}",
            f"ipv6 address {ipv6_with_prefix}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ IPv6 {ipv6_with_prefix} configured on {interface}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to configure IPv6: {str(e)}")
        return False


def add_ipv6_static_route(dut, prefix, nexthop):
    """Add IPv6 static route with next-hop."""
    st.log(f"Adding IPv6 static route: ipv6 route {prefix} {nexthop}")
    try:
        st.config(dut, [
            f"ipv6 route {prefix} {nexthop}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ IPv6 static route added: {prefix} via {nexthop}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to add IPv6 static route: {str(e)}")
        return False


def add_ipv6_blackhole_route(dut, prefix):
    """Add IPv6 blackhole route."""
    st.log(f"Adding IPv6 blackhole route: ipv6 route {prefix} blackhole")
    try:
        st.config(dut, [
            f"ipv6 route {prefix} blackhole"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ IPv6 blackhole route added: {prefix}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to add IPv6 blackhole route: {str(e)}")
        return False


def delete_ipv6_static_route(dut, prefix, nexthop):
    """Delete IPv6 static route with next-hop."""
    st.log(f"Deleting IPv6 static route: no ipv6 route {prefix} {nexthop}")
    try:
        st.config(dut, [
            f"no ipv6 route {prefix} {nexthop}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ IPv6 static route deleted: {prefix} via {nexthop}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to delete IPv6 static route: {str(e)}")
        return False


def delete_ipv6_blackhole_route(dut, prefix):
    """Delete IPv6 blackhole route."""
    st.log(f"Deleting IPv6 blackhole route: no ipv6 route {prefix} blackhole")
    try:
        st.config(dut, [
            f"no ipv6 route {prefix} blackhole"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ IPv6 blackhole route deleted: {prefix}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to delete IPv6 blackhole route: {str(e)}")
        return False


def verify_ipv6_blackhole_route(dut, prefix):
    """Verify IPv6 blackhole route shows 'Unreachable (blackhole)' in routing table."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        # Exit Klish CLI to Linux shell before show command
        try:
            st.config(dut, ["exit"], type='klish', skip_error_check=True)
        except Exception:
            pass

        output = st.show(dut, f"show ipv6 route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output).lower()
        st.log(f"IPv6 blackhole route lookup '{prefix}': {output_str[:400]}")

        # Check for blackhole markers
        if "blackhole" in output_str or "unreachable" in output_str:
            st.log(f"✓ IPv6 blackhole route verified: {prefix}")
            return True
        else:
            st.error(f"✗ IPv6 blackhole route not found or incorrect: {prefix}")
            return False
    except Exception as e:
        st.error(f"IPv6 blackhole route verify failed: {str(e)}")
        return False


def verify_ipv6_static_route(dut, prefix, nexthop):
    """Verify IPv6 static route exists in routing table."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        # Exit Klish CLI to Linux shell before show command
        try:
            st.config(dut, ["exit"], type='klish', skip_error_check=True)
        except Exception:
            pass

        output = st.show(dut, f"show ipv6 route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output).lower()
        st.log(f"IPv6 route lookup '{prefix}': {output_str[:300]}")

        # Normalize IPv6 address for comparison
        nexthop_normalized = nexthop.lower()

        # Check if route exists with correct nexthop
        if "s" in output_str and nexthop_normalized in output_str:
            st.log(f"✓ IPv6 static route verified: {prefix} via {nexthop}")
            return True
        else:
            st.error(f"✗ IPv6 static route not found or incorrect: {prefix}")
            return False
    except Exception as e:
        st.error(f"IPv6 static route verify failed: {str(e)}")
        return False


def verify_ipv6_route_not_present(dut, prefix):
    """Verify IPv6 route is not in routing table."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        # Exit Klish CLI to Linux shell before show command
        try:
            st.config(dut, ["exit"], type='klish', skip_error_check=True)
        except Exception:
            pass

        output = st.show(dut, f"show ipv6 route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output).lower()
        st.log(f"IPv6 route lookup after deletion '{prefix}': {output_str[:200]}")

        # Normalize prefix for comparison
        prefix_normalized = prefix.lower()

        # Route should not have 'S' marker or prefix should not be present
        if "s" not in output_str or prefix_normalized not in output_str:
            st.log(f"✓ IPv6 route absent as expected: {prefix}")
            return True
        else:
            st.error(f"✗ IPv6 route still present: {prefix}")
            return False
    except Exception as e:
        st.error(f"IPv6 route verify failed: {str(e)}")
        return False


@pytest.mark.static_route
@pytest.mark.community
@pytest.mark.ipv6
def test_oc_sr19_ipv6_blackhole_routes():
    """Test OC-SR-19: IPv6 Static Route - Blackhole Routes."""

    st.banner("TEST OC-SR-19: IPv6 BLACKHOLE ROUTES")

    result_flag = True

    try:
        # Step 1: Configure IPv6 addresses on interfaces
        st.banner("STEP 1: Configure IPv6 Addresses on DUT1 and DUT2")

        if not configure_interface_ipv6(vars.D1, CONFIG.dut1_eth0, CONFIG.dut1_eth0_ipv6):
            st.report_tc_fail(TC_IDS.ipv6_interface_config, "ipv6_interface_config_failed", "DUT1")
            result_flag = False

        if not configure_interface_ipv6(vars.D2, CONFIG.dut2_eth0, CONFIG.dut2_eth0_ipv6):
            st.report_tc_fail(TC_IDS.ipv6_interface_config, "ipv6_interface_config_failed", "DUT2")
            result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.ipv6_interface_config, "ipv6_interface_config_successful")

        st.wait(3, "Waiting for IPv6 interfaces to stabilize")

        # Step 2: Add IPv6 routes (blackhole + normal) on DUT1
        st.banner("STEP 2: Add IPv6 Routes (Blackhole + Normal) on DUT1")

        if not add_ipv6_static_route(vars.D1, CONFIG.dut1_route_dead, CONFIG.dut1_route_dead_nh):
            st.error("DUT1: Failed to add route to 2001:db8:dead::/48")
            result_flag = False

        if not add_ipv6_blackhole_route(vars.D1, CONFIG.dut1_route_beef):
            st.error("DUT1: Failed to add blackhole route to 2001:db8:beef::/48")
            result_flag = False

        if not add_ipv6_static_route(vars.D1, CONFIG.dut1_route_cafe, CONFIG.dut1_route_cafe_nh):
            st.error("DUT1: Failed to add route to 2001:db8:cafe::/48")
            result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.ipv6_blackhole_add, "ipv6_blackhole_route_add_successful")
        else:
            st.report_tc_fail(TC_IDS.ipv6_blackhole_add, "ipv6_blackhole_route_add_failed", "DUT1")

        st.wait(2, "Waiting for DUT1 routes to be programmed")

        # Step 3: Add IPv6 routes (blackhole + normal) on DUT2
        st.banner("STEP 3: Add IPv6 Routes (Blackhole + Normal) on DUT2")

        if not add_ipv6_static_route(vars.D2, CONFIG.dut2_route_dead, CONFIG.dut2_route_dead_nh):
            st.error("DUT2: Failed to add route to 2001:db8:dead::/48")
            result_flag = False

        if not add_ipv6_blackhole_route(vars.D2, CONFIG.dut2_route_beef):
            st.error("DUT2: Failed to add blackhole route to 2001:db8:beef::/48")
            result_flag = False

        if not add_ipv6_static_route(vars.D2, CONFIG.dut2_route_cafe, CONFIG.dut2_route_cafe_nh):
            st.error("DUT2: Failed to add route to 2001:db8:cafe::/48")
            result_flag = False

        st.wait(2, "Waiting for DUT2 routes to be programmed")

        # Step 4: Verify IPv6 blackhole routes on both DUTs
        st.banner("STEP 4: Verify IPv6 Blackhole Routes")

        if not verify_ipv6_blackhole_route(vars.D1, CONFIG.dut1_route_beef):
            st.error("DUT1: Blackhole route 2001:db8:beef::/48 not verified")
            result_flag = False

        if not verify_ipv6_blackhole_route(vars.D2, CONFIG.dut2_route_beef):
            st.error("DUT2: Blackhole route 2001:db8:beef::/48 not verified")
            result_flag = False

        # Verify normal routes as well
        if not verify_ipv6_static_route(vars.D1, CONFIG.dut1_route_dead, CONFIG.dut1_route_dead_nh):
            st.error("DUT1: Normal route 2001:db8:dead::/48 not verified")
            result_flag = False

        if not verify_ipv6_static_route(vars.D2, CONFIG.dut2_route_cafe, CONFIG.dut2_route_cafe_nh):
            st.error("DUT2: Normal route 2001:db8:cafe::/48 not verified")
            result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.ipv6_blackhole_verify, "ipv6_blackhole_route_verify_successful")
        else:
            st.report_tc_fail(TC_IDS.ipv6_blackhole_verify, "ipv6_blackhole_route_verify_failed")

        # Step 5: Delete IPv6 routes
        st.banner("STEP 5: Delete IPv6 Routes")

        # Delete DUT1 routes
        if not delete_ipv6_static_route(vars.D1, CONFIG.dut1_route_dead, CONFIG.dut1_route_dead_nh):
            st.error("DUT1: Failed to delete route 2001:db8:dead::/48")
            result_flag = False

        if not delete_ipv6_blackhole_route(vars.D1, CONFIG.dut1_route_beef):
            st.error("DUT1: Failed to delete blackhole route 2001:db8:beef::/48")
            result_flag = False

        if not delete_ipv6_static_route(vars.D1, CONFIG.dut1_route_cafe, CONFIG.dut1_route_cafe_nh):
            st.error("DUT1: Failed to delete route 2001:db8:cafe::/48")
            result_flag = False

        # Delete DUT2 routes
        if not delete_ipv6_static_route(vars.D2, CONFIG.dut2_route_dead, CONFIG.dut2_route_dead_nh):
            st.error("DUT2: Failed to delete route 2001:db8:dead::/48")
            result_flag = False

        if not delete_ipv6_blackhole_route(vars.D2, CONFIG.dut2_route_beef):
            st.error("DUT2: Failed to delete blackhole route 2001:db8:beef::/48")
            result_flag = False

        if not delete_ipv6_static_route(vars.D2, CONFIG.dut2_route_cafe, CONFIG.dut2_route_cafe_nh):
            st.error("DUT2: Failed to delete route 2001:db8:cafe::/48")
            result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.ipv6_blackhole_delete, "ipv6_blackhole_route_delete_successful")
        else:
            st.report_tc_fail(TC_IDS.ipv6_blackhole_delete, "ipv6_blackhole_route_delete_failed")

        st.wait(2, "Waiting for route deletion")

        # Step 6: Verify IPv6 routes are deleted
        st.banner("STEP 6: Verify IPv6 Routes Deleted")

        if not verify_ipv6_route_not_present(vars.D1, CONFIG.dut1_route_beef):
            st.error("DUT1: Blackhole route 2001:db8:beef::/48 still present")
            result_flag = False

        if not verify_ipv6_route_not_present(vars.D2, CONFIG.dut2_route_beef):
            st.error("DUT2: Blackhole route 2001:db8:beef::/48 still present")
            result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.ipv6_blackhole_verify_delete, "ipv6_blackhole_route_deletion_verify_successful")
        else:
            st.report_tc_fail(TC_IDS.ipv6_blackhole_verify_delete, "ipv6_blackhole_route_deletion_verify_failed")

    except Exception as e:
        st.error(f"Test exception occurred: {str(e)}")
        result_flag = False

    finally:
        # Ensure cleanup executes
        st.log("Ensuring cleanup executes...")

    # Final result
    if result_flag:
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")
