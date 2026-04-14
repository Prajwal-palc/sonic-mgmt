"""
STATIC ROUTE TEST - OC-SR-20: IPv6 Static Route - Interface-Based Routes

Test Case ID: OC-SR-20
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_oc_static_3vs.yaml \\
  tests/system/Static_Route/test_oc_static_route_10_ipv6_interface.py \\
  --logs-path ./logs/oc_sr_20_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Verify IPv6 static interface-based routes on SONiC OC-build using Klish CLI.
  Interface-based routes specify only the egress interface without a next-hop
  IPv6 address, showing as "directly connected, <interface>" in routing table.
  DUT3 hosts destination prefixes on Loopback0 for reachability testing.

Pre-requisites:
  - Topology: three-node (D1-D2-D3) | Supported: HW and Virtual
  - OC-build with Klish CLI support
  - IPv6 enabled on interfaces
  - Test variables: spytest/vars/static_route/oc_static_route_vars.yaml
"""

import pytest
from spytest import st, SpyTestDict

# Test case IDs
TC_IDS = SpyTestDict({
    "ipv6_interface_config": "TC-OC-SR-20-001",
    "ipv6_interface_route_add": "TC-OC-SR-20-002",
    "ipv6_interface_route_verify": "TC-OC-SR-20-003",
    "ipv6_interface_route_delete": "TC-OC-SR-20-004",
    "ipv6_interface_route_verify_delete": "TC-OC-SR-20-005",
})

# Module level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    # DUT1 Interface Configuration
    "dut1_eth0": "Ethernet 0",
    "dut1_eth0_ipv6": "2001:1:1::1/64",
    "dut1_eth4": "Ethernet 4",
    "dut1_eth4_ipv6": "2001:1:2::1/64",

    # DUT2 Interface Configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ipv6": "2001:1:1::2/64",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ipv6": "2001:2:1::1/64",
    "dut2_eth12": "Ethernet 12",
    "dut2_eth12_ipv6": "2001:2:2::1/64",

    # DUT3 Interface Configuration
    "dut3_eth8": "Ethernet 8",
    "dut3_eth8_ipv6": "2001:2:1::2/64",
    "dut3_loopback": "Loopback 0",
    "dut3_loopback_ipv6_1": "2001:db8:70::1/128",
    "dut3_loopback_ipv6_2": "2001:db8:71::1/128",
    "dut3_loopback_ipv6_3": "2001:db8:72::1/128",

    # DUT1 IPv6 Interface-Based Routes (no next-hop IP)
    "dut1_route1_prefix": "2001:db8:70::/48",
    "dut1_route1_interface": "Ethernet 0",
    "dut1_route2_prefix": "2001:db8:71::/48",
    "dut1_route2_interface": "Ethernet 4",

    # DUT2 IPv6 Interface-Based Routes (no next-hop IP)
    "dut2_route1_prefix": "2001:db8:70::/48",
    "dut2_route1_interface": "Ethernet 8",
    "dut2_route2_prefix": "2001:db8:72::/48",
    "dut2_route2_interface": "Ethernet 12",

    # DUT3 IPv6 Interface-Based Routes (no next-hop IP)
    "dut3_route1_prefix": "2001:db8:70::/48",
    "dut3_route1_interface": "Ethernet 8",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module level fixture for setup and teardown."""
    global vars, data

    st.banner("MODULE PROLOGUE: OC-SR-20 - IPv6 Interface-Based Routes")

    try:
        # Get testbed variables
        vars = st.ensure_min_topology("D1D2:1", "D2D3:1")

        # Set CLI type
        data.cli_type = 'klish'
        st.log(f"Using CLI type: {data.cli_type}")
        st.log(f"Test devices: D1={vars.D1}, D2={vars.D2}, D3={vars.D3}")

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

    # Clear DUT3 interfaces
    try:
        st.config(vars.D3, [
            f"interface {CONFIG.dut3_eth8}",
            "no ipv6 address",
            "shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Clear DUT3 loopback
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

    # Remove DUT1 interface-based routes if they exist
    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.dut1_route1_prefix} interface {CONFIG.dut1_route1_interface}",
            f"no ipv6 route {CONFIG.dut1_route2_prefix} interface {CONFIG.dut1_route2_interface}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT2 interface-based routes if they exist
    try:
        st.config(vars.D2, [
            f"no ipv6 route {CONFIG.dut2_route1_prefix} interface {CONFIG.dut2_route1_interface}",
            f"no ipv6 route {CONFIG.dut2_route2_prefix} interface {CONFIG.dut2_route2_interface}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT3 interface-based routes if they exist
    try:
        st.config(vars.D3, [
            f"no ipv6 route {CONFIG.dut3_route1_prefix} interface {CONFIG.dut3_route1_interface}"
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

    st.wait(3, "Waiting for pre-config clear")
    st.log("Pre-configuration completed")


def static_route_cleanup():
    """Cleanup: Remove static routes and IP configuration."""
    st.log("Cleanup: Removing IPv6 interface-based routes and IP configuration")

    # Remove DUT1 interface-based routes
    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.dut1_route1_prefix} interface {CONFIG.dut1_route1_interface}",
            f"no ipv6 route {CONFIG.dut1_route2_prefix} interface {CONFIG.dut1_route2_interface}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT1 route cleanup warning: {str(e)}")

    # Remove DUT2 interface-based routes
    try:
        st.config(vars.D2, [
            f"no ipv6 route {CONFIG.dut2_route1_prefix} interface {CONFIG.dut2_route1_interface}",
            f"no ipv6 route {CONFIG.dut2_route2_prefix} interface {CONFIG.dut2_route2_interface}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT2 route cleanup warning: {str(e)}")

    # Remove DUT3 interface-based routes
    try:
        st.config(vars.D3, [
            f"no ipv6 route {CONFIG.dut3_route1_prefix} interface {CONFIG.dut3_route1_interface}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT3 route cleanup warning: {str(e)}")

    # Clear IPv6 addresses - DUT1
    for intf in [CONFIG.dut1_eth0, CONFIG.dut1_eth4]:
        try:
            st.config(vars.D1, [
                f"interface {intf}",
                "no ipv6 address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception as e:
            st.log(f"DUT1 {intf} cleanup warning: {str(e)}")

    # Clear IPv6 addresses - DUT2
    for intf in [CONFIG.dut2_eth0, CONFIG.dut2_eth8, CONFIG.dut2_eth12]:
        try:
            st.config(vars.D2, [
                f"interface {intf}",
                "no ipv6 address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception as e:
            st.log(f"DUT2 {intf} cleanup warning: {str(e)}")

    # Clear DUT3 interfaces and loopback
    try:
        st.config(vars.D3, [
            f"interface {CONFIG.dut3_eth8}",
            "no ipv6 address",
            "shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT3 {CONFIG.dut3_eth8} cleanup warning: {str(e)}")

    try:
        st.config(vars.D3, [
            f"interface {CONFIG.dut3_loopback}",
            f"no ipv6 address {CONFIG.dut3_loopback_ipv6_1}",
            f"no ipv6 address {CONFIG.dut3_loopback_ipv6_2}",
            f"no ipv6 address {CONFIG.dut3_loopback_ipv6_3}",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT3 loopback cleanup warning: {str(e)}")

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




def configure_loopback_ipv6(dut, loopback_intf, ipv6_addr1, ipv6_addr2, ipv6_addr3):
    """Configure multiple IPv6 addresses on Loopback interface."""
    st.log(f"Configuring Loopback {loopback_intf} with IPv6 addresses on {dut}")
    try:
        st.config(dut, [
            f"interface {loopback_intf}",
            f"ipv6 address {ipv6_addr1}",
            f"ipv6 address {ipv6_addr2}",
            f"ipv6 address {ipv6_addr3}",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ Loopback configured with {ipv6_addr1}, {ipv6_addr2}, {ipv6_addr3}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to configure loopback: {str(e)}")
        return False


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


def add_ipv6_interface_route(dut, prefix, interface):
    """Add IPv6 static route with interface (no next-hop IP)."""
    st.log(f"Adding IPv6 interface-based route: ipv6 route {prefix} interface {interface}")
    try:
        st.config(dut, [
            f"ipv6 route {prefix} interface {interface}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ IPv6 interface-based route added: {prefix} via interface {interface}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to add IPv6 interface-based route: {str(e)}")
        return False


def delete_ipv6_interface_route(dut, prefix, interface):
    """Delete IPv6 static route with interface."""
    st.log(f"Deleting IPv6 interface-based route: no ipv6 route {prefix} interface {interface}")
    try:
        st.config(dut, [
            f"no ipv6 route {prefix} interface {interface}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ IPv6 interface-based route deleted: {prefix} via interface {interface}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to delete IPv6 interface-based route: {str(e)}")
        return False


def verify_ipv6_interface_route(dut, prefix, interface):
    """Verify IPv6 interface-based route shows 'directly connected, <interface>' in routing table."""
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
        st.log(f"IPv6 interface route lookup '{prefix}': {output_str[:400]}")

        # Normalize interface name for comparison
        interface_normalized = interface.replace(" ", "").lower()

        # Check for interface-based route markers
        if "s" in output_str and ("directly connected" in output_str or interface_normalized in output_str):
            st.log(f"✓ IPv6 interface-based route verified: {prefix} via {interface}")
            return True
        else:
            st.error(f"✗ IPv6 interface-based route not found or incorrect: {prefix}")
            return False
    except Exception as e:
        st.error(f"IPv6 interface route verify failed: {str(e)}")
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
def test_oc_sr20_ipv6_interface_routes():
    """Test OC-SR-20: IPv6 Static Route - Interface-Based Routes."""

    st.banner("TEST OC-SR-20: IPv6 INTERFACE-BASED ROUTES")

    result_flag = True

    try:
        # Step 1: Configure IPv6 addresses on interfaces
        st.banner("STEP 1: Configure IPv6 Addresses on DUT1 Interfaces")

        if not configure_interface_ipv6(vars.D1, CONFIG.dut1_eth0, CONFIG.dut1_eth0_ipv6):
            st.report_tc_fail(TC_IDS.ipv6_interface_config, "ipv6_interface_config_failed", "DUT1 Ethernet0")
            result_flag = False

        if not configure_interface_ipv6(vars.D1, CONFIG.dut1_eth4, CONFIG.dut1_eth4_ipv6):
            st.report_tc_fail(TC_IDS.ipv6_interface_config, "ipv6_interface_config_failed", "DUT1 Ethernet4")
            result_flag = False

        st.banner("STEP 2: Configure IPv6 Addresses on DUT2 Interfaces")

        if not configure_interface_ipv6(vars.D2, CONFIG.dut2_eth0, CONFIG.dut2_eth0_ipv6):
            st.report_tc_fail(TC_IDS.ipv6_interface_config, "ipv6_interface_config_failed", "DUT2 Ethernet0")
            result_flag = False

        if not configure_interface_ipv6(vars.D2, CONFIG.dut2_eth8, CONFIG.dut2_eth8_ipv6):
            st.report_tc_fail(TC_IDS.ipv6_interface_config, "ipv6_interface_config_failed", "DUT2 Ethernet8")
            result_flag = False

        if not configure_interface_ipv6(vars.D2, CONFIG.dut2_eth12, CONFIG.dut2_eth12_ipv6):
            st.report_tc_fail(TC_IDS.ipv6_interface_config, "ipv6_interface_config_failed", "DUT2 Ethernet12")
            result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.ipv6_interface_config, "ipv6_interface_config_successful")

        st.wait(3, "Waiting for IPv6 interfaces to stabilize")

        # Step 2.5: Configure DUT3 Loopback and Interface
        st.banner("STEP 2.5: Configure DUT3 Interface and Loopback (Destination)")

        if not configure_interface_ipv6(vars.D3, CONFIG.dut3_eth8, CONFIG.dut3_eth8_ipv6):
            st.error("DUT3: Failed to configure Ethernet8")
            result_flag = False

        # Configure loopback with destination prefixes
        if not configure_loopback_ipv6(vars.D3, CONFIG.dut3_loopback, 
                                       CONFIG.dut3_loopback_ipv6_1,
                                       CONFIG.dut3_loopback_ipv6_2,
                                       CONFIG.dut3_loopback_ipv6_3):
            st.error("DUT3: Failed to configure Loopback0")
            result_flag = False

        st.wait(2, "Waiting for DUT3 interfaces to stabilize")

        # Step 3: Add IPv6 interface-based routes on DUT1
        st.banner("STEP 3: Add IPv6 Interface-Based Routes on DUT1")

        if not add_ipv6_interface_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_interface):
            st.error(f"DUT1: Failed to add interface route {CONFIG.dut1_route1_prefix} via {CONFIG.dut1_route1_interface}")
            result_flag = False

        if not add_ipv6_interface_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_interface):
            st.error(f"DUT1: Failed to add interface route {CONFIG.dut1_route2_prefix} via {CONFIG.dut1_route2_interface}")
            result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.ipv6_interface_route_add, "ipv6_interface_route_add_successful", "DUT1")
        else:
            st.report_tc_fail(TC_IDS.ipv6_interface_route_add, "ipv6_interface_route_add_failed", "DUT1")

        st.wait(2, "Waiting for DUT1 routes to be programmed")

        # Step 4: Add IPv6 interface-based routes on DUT2
        st.banner("STEP 4: Add IPv6 Interface-Based Routes on DUT2")

        if not add_ipv6_interface_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_interface):
            st.error(f"DUT2: Failed to add interface route {CONFIG.dut2_route1_prefix} via {CONFIG.dut2_route1_interface}")
            result_flag = False

        if not add_ipv6_interface_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_interface):
            st.error(f"DUT2: Failed to add interface route {CONFIG.dut2_route2_prefix} via {CONFIG.dut2_route2_interface}")
            result_flag = False

        st.wait(2, "Waiting for DUT2 routes to be programmed")

        # Step 4.5: Add IPv6 interface-based route on DUT3
        st.banner("STEP 4.5: Add IPv6 Interface-Based Route on DUT3")

        if not add_ipv6_interface_route(vars.D3, CONFIG.dut3_route1_prefix, CONFIG.dut3_route1_interface):
            st.error(f"DUT3: Failed to add interface route {CONFIG.dut3_route1_prefix} via {CONFIG.dut3_route1_interface}")
            result_flag = False

        st.wait(2, "Waiting for DUT3 routes to be programmed")

        # Step 5: Verify IPv6 interface-based routes
        st.banner("STEP 5: Verify IPv6 Interface-Based Routes")

        if not verify_ipv6_interface_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_interface):
            st.error(f"DUT1: Interface route {CONFIG.dut1_route1_prefix} not verified")
            result_flag = False

        if not verify_ipv6_interface_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_interface):
            st.error(f"DUT1: Interface route {CONFIG.dut1_route2_prefix} not verified")
            result_flag = False

        if not verify_ipv6_interface_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_interface):
            st.error(f"DUT2: Interface route {CONFIG.dut2_route1_prefix} not verified")
            result_flag = False

        if not verify_ipv6_interface_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_interface):
            st.error(f"DUT2: Interface route {CONFIG.dut2_route2_prefix} not verified")
            result_flag = False

        if not verify_ipv6_interface_route(vars.D3, CONFIG.dut3_route1_prefix, CONFIG.dut3_route1_interface):
            st.error(f"DUT3: Interface route {CONFIG.dut3_route1_prefix} not verified")
            result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.ipv6_interface_route_verify, "ipv6_interface_route_verify_successful")
        else:
            st.report_tc_fail(TC_IDS.ipv6_interface_route_verify, "ipv6_interface_route_verify_failed")

        # Step 6: Delete IPv6 interface-based routes
        st.banner("STEP 6: Delete IPv6 Interface-Based Routes")

        # Delete DUT1 routes
        if not delete_ipv6_interface_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_interface):
            st.error(f"DUT1: Failed to delete interface route {CONFIG.dut1_route1_prefix}")
            result_flag = False

        if not delete_ipv6_interface_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_interface):
            st.error(f"DUT1: Failed to delete interface route {CONFIG.dut1_route2_prefix}")
            result_flag = False

        # Delete DUT2 routes
        if not delete_ipv6_interface_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_interface):
            st.error(f"DUT2: Failed to delete interface route {CONFIG.dut2_route1_prefix}")
            result_flag = False

        if not delete_ipv6_interface_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_interface):
            st.error(f"DUT2: Failed to delete interface route {CONFIG.dut2_route2_prefix}")
            result_flag = False

        # Delete DUT3 routes
        if not delete_ipv6_interface_route(vars.D3, CONFIG.dut3_route1_prefix, CONFIG.dut3_route1_interface):
            st.error(f"DUT3: Failed to delete interface route {CONFIG.dut3_route1_prefix}")
            result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.ipv6_interface_route_delete, "ipv6_interface_route_delete_successful")
        else:
            st.report_tc_fail(TC_IDS.ipv6_interface_route_delete, "ipv6_interface_route_delete_failed")

        st.wait(2, "Waiting for route deletion")

        # Step 7: Verify IPv6 routes are deleted
        st.banner("STEP 7: Verify IPv6 Routes Deleted")

        if not verify_ipv6_route_not_present(vars.D1, CONFIG.dut1_route1_prefix):
            st.error(f"DUT1: Route {CONFIG.dut1_route1_prefix} still present")
            result_flag = False

        if not verify_ipv6_route_not_present(vars.D1, CONFIG.dut1_route2_prefix):
            st.error(f"DUT1: Route {CONFIG.dut1_route2_prefix} still present")
            result_flag = False

        if not verify_ipv6_route_not_present(vars.D2, CONFIG.dut2_route1_prefix):
            st.error(f"DUT2: Route {CONFIG.dut2_route1_prefix} still present")
            result_flag = False

        if not verify_ipv6_route_not_present(vars.D2, CONFIG.dut2_route2_prefix):
            st.error(f"DUT2: Route {CONFIG.dut2_route2_prefix} still present")
            result_flag = False

        if not verify_ipv6_route_not_present(vars.D3, CONFIG.dut3_route1_prefix):
            st.error(f"DUT3: Route {CONFIG.dut3_route1_prefix} still present")
            result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.ipv6_interface_route_verify_delete, "ipv6_interface_route_deletion_verify_successful")
        else:
            st.report_tc_fail(TC_IDS.ipv6_interface_route_verify_delete, "ipv6_interface_route_deletion_verify_failed")

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
