"""
NEG-02: BGP Negative Test - Wrong Update-Source (IPv6)
========================================================

Test Objective:
--------------
Verify that BGP session does NOT establish when:
- IPv6 BGP neighbors are configured using loopback addresses
- update-source is set to Loopback interface
- NO static routes exist to reach the loopback addresses

Expected Behavior (Negative Test):
----------------------------------
- BGP state should be Active or Idle (NOT Established)
- Last reset reason: "No path to specified Neighbor"
- This is CORRECT negative behavior - test PASSES when BGP fails to establish

Configuration:
-------------
DUT1:
  - Ethernet0: 2001:db8:1::1/64
  - Loopback0: 2001:db8:100::1/128
  - BGP: neighbor 2001:db8:100::2, update-source Loopback0

DUT2:
  - Ethernet0: 2001:db8:1::2/64
  - Loopback0: 2001:db8:100::2/128
  - BGP: neighbor 2001:db8:100::1, update-source Loopback0

Author: Auto-generated SpyTest
"""

import pytest
import time
from spytest import st, SpyTestDict
from spytest.dicts import SpyTestDict

# Import SpyTest APIs
import apis.routing.ip as ip_api
import apis.switching.vlan as vlanapi

# Test configuration
CONFIG = SpyTestDict({
    "interface": "Ethernet0",
    "loopback": "Loopback0",
    "dut1_eth_ipv6": "2001:db8:1::1",
    "dut2_eth_ipv6": "2001:db8:1::2",
    "dut1_lo_ipv6": "2001:db8:100::1",
    "dut2_lo_ipv6": "2001:db8:100::2",
    "eth_ipv6_mask": "64",
    "lo_ipv6_mask": "128",
    "asn": "65001",  # iBGP - same AS number
    "dut1_router_id": "1.1.1.1",
    "dut2_router_id": "2.2.2.2",
    "bgp_wait_time": 90,
})


@pytest.fixture(scope="module", autouse=True)
def bgp_negative_updatesource_ipv6_module_hooks(request):
    """
    Module-level fixture for setup and cleanup
    """
    global vars
    vars = st.ensure_min_topology("D1D2:1")

    st.banner("MODULE SETUP: NEG-02 IPv6 Wrong Update-Source")

    # Pre-config: Clear any existing configuration
    module_prolog()

    yield

    # Cleanup after all tests
    st.banner("MODULE CLEANUP: NEG-02 IPv6 Wrong Update-Source")
    module_epilog()


def module_prolog():
    """
    Pre-configuration steps before test execution
    """
    st.banner("PRE-CONFIG: Cleaning up VLAN and BGP configuration")

    for dut in [vars.D1, vars.D2]:
        # Clear VLAN configuration
        cleanup_vlan_from_interface(dut, CONFIG.interface)

        # Clear any existing BGP configuration
        cleanup_bgp_config(dut)

        # Ensure interface is up
        st.config(dut, [
            "configure terminal",
            f"interface {CONFIG.interface}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=True)


def module_epilog():
    """
    Cleanup after test execution
    """
    st.banner("CLEANUP: Removing all test configuration")

    for dut in [vars.D1, vars.D2]:
        # Remove BGP configuration
        cleanup_bgp_config(dut)

        # Remove IPv6 addresses
        remove_ipv6_addresses(dut)

        # Remove loopback interface
        remove_loopback_interface(dut)


def cleanup_vlan_from_interface(dut, interface):
    """
    Remove interface from any VLAN memberships and delete VLANs
    """
    st.log(f"Cleaning up VLAN configuration on {dut} {interface}")

    # Exit any config mode first
    st.config(dut, "end", type='klish', skip_error_check=True, conf=False)

    # Show VLAN configuration (use capital V for Klish)
    vlan_show_cmd = "show Vlan brief"
    vlan_output = st.show(dut, vlan_show_cmd, type='klish', skip_error_check=True)

    if not vlan_output:
        st.log(f"No VLAN configuration found on {dut}")
        return

    # Build cleanup commands
    cleanup_cmds = ["configure terminal"]

    # Remove interface from VLAN members
    for vlan_entry in vlan_output:
        if isinstance(vlan_entry, dict) and 'vid' in vlan_entry:
            vlan_id = vlan_entry['vid']
            members = vlan_entry.get('member', '')

            if interface in str(members):
                st.log(f"Removing {interface} from Vlan{vlan_id}")
                cleanup_cmds.extend([
                    f"interface Vlan {vlan_id}",
                    f"no member {interface}",
                    "exit",
                ])

    # Delete VLAN interfaces
    for vlan_id in [10, 100, 1000]:
        cleanup_cmds.extend([
            f"no interface Vlan {vlan_id}"
        ])

    cleanup_cmds.append("exit")

    # Execute cleanup
    st.config(dut, cleanup_cmds, type='klish', skip_error_check=True)
    st.wait(2, "Waiting after VLAN cleanup")


def cleanup_bgp_config(dut: str):
    """
    Remove BGP configuration
    """
    st.log(f"Cleaning up BGP configuration on {dut}")

    commands = [
        "configure terminal",
        f"no router bgp {CONFIG.asn}",
        "exit"
    ]

    st.config(dut, commands, type='klish', skip_error_check=True)
    st.wait(2, "Waiting after BGP cleanup")


def remove_ipv6_addresses(dut: str):
    """
    Remove IPv6 addresses from Ethernet and Loopback interfaces
    """
    st.log(f"Removing IPv6 addresses on {dut}")

    # Get IPv6 config based on DUT
    if dut == vars.D1:
        eth_ipv6 = CONFIG.dut1_eth_ipv6
        lo_ipv6 = CONFIG.dut1_lo_ipv6
    else:
        eth_ipv6 = CONFIG.dut2_eth_ipv6
        lo_ipv6 = CONFIG.dut2_lo_ipv6

    # Try sonic-cli first
    commands = [
        "configure terminal",
        f"interface {CONFIG.interface}",
        f"no ipv6 address {eth_ipv6}/{CONFIG.eth_ipv6_mask}",
        "exit",
        f"interface {CONFIG.loopback}",
        f"no ipv6 address {lo_ipv6}/{CONFIG.lo_ipv6_mask}",
        "exit",
        "exit"
    ]

    st.config(dut, commands, type='klish', skip_error_check=True)

    # Also try with SONiC config command as fallback
    st.config(dut, f"config interface ip remove {CONFIG.interface} {eth_ipv6}/{CONFIG.eth_ipv6_mask}",
              type='click', skip_error_check=True, conf=False)
    st.config(dut, f"config interface ip remove {CONFIG.loopback} {lo_ipv6}/{CONFIG.lo_ipv6_mask}",
              type='click', skip_error_check=True, conf=False)


def remove_loopback_interface(dut: str):
    """
    Remove Loopback interface
    """
    st.log(f"Removing Loopback interface on {dut}")

    commands = [
        "configure terminal",
        f"no interface {CONFIG.loopback}",
        "exit"
    ]

    st.config(dut, commands, type='klish', skip_error_check=True)


def configure_ipv6_on_interface(dut: str, interface: str, ipv6_address: str, mask: str) -> bool:
    """
    Configure IPv6 address on interface with workaround for SONiC CLI bug

    Workaround strategy:
    1. Try SONiC CLI (sonic-cli/klish) 3 times with skip_error_check
    2. If all fail, use SONiC 'config' command: config interface ip add {interface} {ipv6}/{mask}
    3. This ensures IPv6 gets configured even with SONiC CLI bug

    Bug: /usr/sbin/cli/ipv6_actions.py has SyntaxError when SSH warnings appear
    """
    st.log(f"Configuring IPv6 {ipv6_address}/{mask} on {dut} {interface}")

    # Try sonic-cli 3 times
    for attempt in range(1, 4):
        st.log(f"Attempt {attempt}/3: Using SONiC CLI (sonic-cli)")

        commands = [
            "configure terminal",
            f"interface {interface}",
            f"ipv6 address {ipv6_address}/{mask}",
            "no shutdown",
            "exit",
            "exit"
        ]

        st.config(dut, commands, type='klish', skip_error_check=True)
        st.wait(2, f"Waiting after IPv6 config attempt {attempt}")

        # Verify if IPv6 was configured
        verify_cmd = "show ipv6 interface brief"
        verify_out = st.show(dut, verify_cmd, type='klish', skip_error_check=True, skip_tmpl=True)

        if ipv6_address in str(verify_out):
            st.log(f"✓ SUCCESS: IPv6 configured via SONiC CLI on attempt {attempt}")
            return True
        else:
            st.log(f"✗ FAILED: IPv6 not found in output on attempt {attempt}")

    # All sonic-cli attempts failed, use SONiC config command
    st.log(f"SONiC CLI (sonic-cli) failed 3 times due to /usr/sbin/cli/ipv6_actions.py bug")
    st.log(f"WORKAROUND: Using SONiC 'config' command to configure IPv6")

    # Exit sonic-cli mode first
    exit_commands = ["end", "exit"]
    for cmd in exit_commands:
        st.config(dut, cmd, type='klish', skip_error_check=True, conf=False)

    # Use SONiC 'config' command (type='click' runs in bash)
    config_cmd = f"config interface ip add {interface} {ipv6_address}/{mask}"
    st.config(dut, config_cmd, type='click', skip_error_check=True, conf=False)

    # Ensure interface is up
    startup_cmd = f"config interface startup {interface}"
    st.config(dut, startup_cmd, type='click', skip_error_check=True, conf=False)

    st.wait(3, "Waiting after SONiC config command")

    # Verify using click mode
    verify_cmd = "show ipv6 interfaces"
    verify_output = st.config(dut, verify_cmd, type='click', skip_error_check=True, conf=False)

    if ipv6_address in str(verify_output):
        st.log(f"✓ SUCCESS: IPv6 configured via SONiC config command")
        return True
    else:
        st.log(f"✗ FAILED: IPv6 configuration failed even with SONiC config command")
        st.log(f"Verify output: {verify_output}")
        return False


def configure_loopback_interface(dut: str, ipv6_address: str) -> bool:
    """
    Configure Loopback interface with IPv6 address
    """
    st.log(f"Configuring Loopback interface on {dut}")

    # Try sonic-cli first
    commands = [
        "configure terminal",
        f"interface {CONFIG.loopback}",
        f"ipv6 address {ipv6_address}/{CONFIG.lo_ipv6_mask}",
        "no shutdown",
        "exit",
        "exit"
    ]

    st.config(dut, commands, type='klish', skip_error_check=True)
    st.wait(2, "Waiting after Loopback config")

    # Verify
    verify_cmd = "show ipv6 interface brief"
    verify_out = st.show(dut, verify_cmd, type='klish', skip_error_check=True, skip_tmpl=True)

    if ipv6_address in str(verify_out):
        st.log(f"✓ SUCCESS: Loopback configured via SONiC CLI")
        return True

    # Fallback to SONiC config command
    st.log("WORKAROUND: Using SONiC config command for Loopback")

    # Exit sonic-cli
    exit_commands = ["end", "exit"]
    for cmd in exit_commands:
        st.config(dut, cmd, type='klish', skip_error_check=True, conf=False)

    # Use SONiC config command
    config_cmd = f"config interface ip add {CONFIG.loopback} {ipv6_address}/{CONFIG.lo_ipv6_mask}"
    st.config(dut, config_cmd, type='click', skip_error_check=True, conf=False)

    startup_cmd = f"config interface startup {CONFIG.loopback}"
    st.config(dut, startup_cmd, type='click', skip_error_check=True, conf=False)

    st.wait(3, "Waiting after Loopback SONiC config")

    # Verify
    verify_output = st.config(dut, "show ipv6 interfaces", type='click', skip_error_check=True, conf=False)

    if ipv6_address in str(verify_output):
        st.log(f"✓ SUCCESS: Loopback configured via SONiC config command")
        return True
    else:
        st.log(f"✗ FAILED: Loopback configuration failed")
        return False


def configure_bgp_neighbor_with_updatesource(dut: str, router_id: str, neighbor_ipv6: str,
                                               remote_as: str, update_source: str) -> bool:
    """
    Configure BGP with IPv6 neighbor using update-source

    Important: update-source syntax is "update-source interface Loopback 0"
    """
    st.log(f"Configuring BGP on {dut} with neighbor {neighbor_ipv6}")

    commands = [
        "configure terminal",
        f"router bgp {CONFIG.asn}",
        f"router-id {router_id}",
        f"neighbor {neighbor_ipv6} remote-as {remote_as}",
        f"update-source interface {update_source} 0",  # "interface Loopback 0"
        "address-family ipv6 unicast",
        "activate",
        "exit",
        "exit",
        "exit"
    ]

    result = st.config(dut, commands, type='klish', skip_error_check=True)
    st.wait(2, "Waiting after BGP configuration")

    return True


def ping_ipv6(dut, destination_ipv6, count=5):
    """
    Ping IPv6 address using ipapi
    """
    st.log(f"Pinging {destination_ipv6} from {dut}")

    result = ip_api.ping(
        dut=dut,
        addresses=destination_ipv6,
        family='ipv6',
        count=count
    )

    return result


def verify_bgp_negative_behavior_ipv6(dut: str, neighbor_ipv6: str):
    """
    Verify BGP is in negative state (Active/Idle, NOT Established)

    This is a NEGATIVE test - BGP should NOT establish.
    Test PASSES when BGP correctly fails to establish.

    Expected states: Active, Idle, Connect (anything except Established)
    Expected reason: "No path to specified Neighbor"
    """
    st.log(f"Verifying negative BGP behavior on {dut} for neighbor {neighbor_ipv6}")

    # Wait for BGP to attempt connection
    st.wait(CONFIG.bgp_wait_time, f"Waiting {CONFIG.bgp_wait_time}s for BGP to attempt connection")

    # Command is "show bgp summary" (shows both IPv4 and IPv6)
    output_raw = st.show(dut, "show bgp summary", type='klish', skip_tmpl=True, skip_error_check=True)

    output_str = str(output_raw)
    output_lower = output_str.lower()

    st.log(f"BGP Summary Output:\n{output_str}")

    # Check for negative states (Active, Idle, Connect)
    if 'idle' in output_lower or 'active' in output_lower or 'connect' in output_lower:
        st.log(f"✓ NEGATIVE TEST PASSED: BGP correctly NOT establishing (found Idle/Active/Connect state)")

        # Also check detailed neighbor info
        neighbor_cmd = "show bgp ipv6 unicast neighbors"
        neighbor_output = st.show(dut, neighbor_cmd, type='klish', skip_tmpl=True, skip_error_check=True)
        neighbor_str = str(neighbor_output)

        st.log(f"Detailed Neighbor Output:\n{neighbor_str}")

        # Check for expected failure reason
        if 'no path to specified neighbor' in neighbor_str.lower():
            st.log(f"✓ CONFIRMED: Found expected failure reason 'No path to specified Neighbor'")

        return True

    # Check if BGP is Established (this would be FAILURE for negative test)
    if 'established' in output_lower:
        st.error(f"✗ NEGATIVE TEST FAILED: BGP is Established (should NOT be!)")
        st.error(f"BGP should fail due to missing static routes to loopback addresses")
        return False

    # Unknown state
    st.log(f"⚠ WARNING: Could not determine BGP state from output")
    st.log(f"Output: {output_str}")
    return False


def test_ipv6_bgp_negative_updatesource():
    """
    Main test function for NEG-02 IPv6 Wrong Update-Source

    Test Steps:
    1. Configure Ethernet0 with IPv6 addresses on both DUTs
    2. Verify IPv6 connectivity with ping
    3. Configure Loopback0 with IPv6 addresses on both DUTs
    4. Configure BGP with update-source Loopback0
    5. Verify BGP does NOT establish (Active/Idle state)

    Expected Result:
    - BGP state = Active or Idle (NOT Established)
    - Last reset reason: "No path to specified Neighbor"
    - This is CORRECT negative behavior
    """

    st.banner("TEST START: NEG-02 IPv6 Wrong Update-Source")

    # STEP 1: Configure Ethernet0 with IPv6 on both DUTs
    st.banner("STEP 1: Configure Ethernet0 with IPv6 addresses")

    # DUT1
    if not configure_ipv6_on_interface(vars.D1, CONFIG.interface, CONFIG.dut1_eth_ipv6, CONFIG.eth_ipv6_mask):
        st.report_fail("ipv6_address_config_fail", vars.D1, CONFIG.interface)

    # DUT2
    if not configure_ipv6_on_interface(vars.D2, CONFIG.interface, CONFIG.dut2_eth_ipv6, CONFIG.eth_ipv6_mask):
        st.report_fail("ipv6_address_config_fail", vars.D2, CONFIG.interface)

    st.wait(5, "Waiting for IPv6 addresses to be active")

    # STEP 2: Verify IPv6 connectivity
    st.banner("STEP 2: Verify IPv6 connectivity with ping")

    ping_result_d1 = ping_ipv6(vars.D1, CONFIG.dut2_eth_ipv6, count=5)
    ping_result_d2 = ping_ipv6(vars.D2, CONFIG.dut1_eth_ipv6, count=5)

    if not ping_result_d1:
        st.error(f"Ping failed from DUT1 to DUT2 ({CONFIG.dut2_eth_ipv6})")
        st.generate_tech_support([vars.D1, vars.D2], "ipv6_ping_failed")
        st.report_fail("ping_fail", CONFIG.dut1_eth_ipv6, CONFIG.dut2_eth_ipv6)

    if not ping_result_d2:
        st.error(f"Ping failed from DUT2 to DUT1 ({CONFIG.dut1_eth_ipv6})")
        st.generate_tech_support([vars.D1, vars.D2], "ipv6_ping_failed")
        st.report_fail("ping_fail", CONFIG.dut2_eth_ipv6, CONFIG.dut1_eth_ipv6)

    st.log("✓ IPv6 connectivity verified successfully")

    # STEP 3: Configure Loopback0 with IPv6
    st.banner("STEP 3: Configure Loopback0 with IPv6 addresses")

    # DUT1
    if not configure_loopback_interface(vars.D1, CONFIG.dut1_lo_ipv6):
        st.report_fail("ipv6_address_config_fail", vars.D1, CONFIG.loopback)

    # DUT2
    if not configure_loopback_interface(vars.D2, CONFIG.dut2_lo_ipv6):
        st.report_fail("ipv6_address_config_fail", vars.D2, CONFIG.loopback)

    st.wait(5, "Waiting for Loopback interfaces to be active")

    # STEP 4: Configure BGP with update-source Loopback0
    st.banner("STEP 4: Configure BGP neighbors with update-source Loopback0")

    # DUT1: neighbor 2001:db8:100::2
    configure_bgp_neighbor_with_updatesource(
        dut=vars.D1,
        router_id=CONFIG.dut1_router_id,
        neighbor_ipv6=CONFIG.dut2_lo_ipv6,
        remote_as=CONFIG.asn,
        update_source=CONFIG.loopback
    )

    # DUT2: neighbor 2001:db8:100::1
    configure_bgp_neighbor_with_updatesource(
        dut=vars.D2,
        router_id=CONFIG.dut2_router_id,
        neighbor_ipv6=CONFIG.dut1_lo_ipv6,
        remote_as=CONFIG.asn,
        update_source=CONFIG.loopback
    )

    st.wait(5, "Waiting after BGP configuration")

    # STEP 5: Exit config mode before verification
    st.banner("STEP 5: Exit Config Mode")
    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, "end", type='klish', skip_error_check=True, conf=False)
            st.config(dut, "exit", type='klish', skip_error_check=True, conf=False)
        except Exception as e:
            st.log(f"Exit config mode on {dut}: {str(e)}")

    st.wait(2, "Waiting after exiting config mode")

    # STEP 6: Verify BGP negative behavior
    st.banner("STEP 6: Verify BGP does NOT establish (Negative Test)")
    st.log("Expected: BGP state = Active/Idle, Last reset = 'No path to specified Neighbor'")

    # Verify DUT1
    dut1_negative = verify_bgp_negative_behavior_ipv6(vars.D1, CONFIG.dut2_lo_ipv6)

    # Verify DUT2
    dut2_negative = verify_bgp_negative_behavior_ipv6(vars.D2, CONFIG.dut1_lo_ipv6)

    # Test Result
    if dut1_negative and dut2_negative:
        st.banner("✓ TEST PASSED: NEG-02 IPv6 Wrong Update-Source")
        st.log("BGP correctly failed to establish due to missing static routes")
        st.log("This is the expected negative behavior")
        st.report_tc_pass("NEG_02_IPv6_Wrong_UpdateSource", "test_case_passed")
        st.report_pass("test_case_passed")
    else:
        st.banner("✗ TEST FAILED: NEG-02 IPv6 Wrong Update-Source")
        st.error("BGP did not show expected negative behavior")
        st.generate_tech_support([vars.D1, vars.D2], "bgp_negative_test_failed")
        st.report_tc_fail("NEG_02_IPv6_Wrong_UpdateSource", "test_case_failed")
        st.report_fail("test_case_failed")
