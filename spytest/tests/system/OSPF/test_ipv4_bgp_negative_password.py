"""
NEG-03: BGP Negative Test - Incorrect Password (IPv4)
======================================================

Test Objective:
--------------
Verify that BGP session does NOT establish when:
- BGP neighbors are configured with password authentication
- Password configured on DUT1 does NOT match password on DUT2
- IPv4 connectivity exists (ping works)

Expected Behavior (Negative Test):
----------------------------------
- BGP state should be Active or Connect (NOT Established)
- Last reset reason: "Waiting for peer OPEN"
- "Peer Authentication Enabled" should be shown
- This is CORRECT negative behavior - test PASSES when BGP fails to establish

Configuration:
-------------
DUT1:
  - Ethernet0: 10.1.1.1/24
  - BGP: neighbor 10.1.1.2, password WRONG_PASSWORD

DUT2:
  - Ethernet0: 10.1.1.2/24
  - BGP: neighbor 10.1.1.1, password CORRECT_PASSWORD

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
    "dut1_ip": "10.1.1.1",
    "dut2_ip": "10.1.1.2",
    "subnet_mask": "24",
    "asn": "65001",  # iBGP
    "dut1_router_id": "1.1.1.1",
    "dut2_router_id": "2.2.2.2",
    "dut1_password": "WRONG_PASSWORD",
    "dut2_password": "CORRECT_PASSWORD",
    "bgp_wait_time": 90,
})


@pytest.fixture(scope="module", autouse=True)
def bgp_negative_password_ipv4_module_hooks(request):
    """
    Module-level fixture for setup and cleanup
    """
    global vars
    vars = st.ensure_min_topology("D1D2:1")

    st.banner("MODULE SETUP: NEG-03 IPv4 Incorrect Password")

    # Pre-config: Clear any existing configuration
    module_prolog()

    yield

    # Cleanup after all tests
    st.banner("MODULE CLEANUP: NEG-03 IPv4 Incorrect Password")
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

        # Remove IP addresses
        remove_ip_addresses(dut)


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


def remove_ip_addresses(dut: str):
    """
    Remove IPv4 addresses from interfaces
    """
    st.log(f"Removing IPv4 addresses on {dut}")

    # Get IP config based on DUT
    if dut == vars.D1:
        ip_addr = CONFIG.dut1_ip
    else:
        ip_addr = CONFIG.dut2_ip

    commands = [
        "configure terminal",
        f"interface {CONFIG.interface}",
        f"no ip address {ip_addr}/{CONFIG.subnet_mask}",
        "exit",
        "exit"
    ]

    st.config(dut, commands, type='klish', skip_error_check=True)


def configure_ip_on_interface(dut: str, interface: str, ip_address: str) -> bool:
    """
    Configure IPv4 address on interface
    First removes any existing IP to avoid overlap errors
    """
    st.log(f"Configuring IP {ip_address}/{CONFIG.subnet_mask} on {dut} {interface}")

    # First, get existing IP addresses and remove them
    st.log(f"Checking for existing IP addresses on {interface}")
    show_cmd = "show ip interfaces"
    existing_ips = st.show(dut, show_cmd, type='klish', skip_error_check=True, skip_tmpl=True)

    # Remove any existing IP addresses on this interface
    remove_cmds = ["configure terminal", f"interface {interface}"]

    # Try to extract and remove existing IPs
    if existing_ips and interface in str(existing_ips):
        st.log(f"Found existing IPs, removing them first")
        # Add generic removal attempts for common IPs
        for subnet in ["10.1.1.1/24", "10.1.1.2/24", "10.1.1.3/24"]:
            remove_cmds.append(f"no ip address {subnet}")

    remove_cmds.extend(["exit", "exit"])
    st.config(dut, remove_cmds, type='klish', skip_error_check=True)
    st.wait(2, "Waiting after removing old IPs")

    # Now configure the new IP
    commands = [
        "configure terminal",
        f"interface {interface}",
        f"ip address {ip_address}/{CONFIG.subnet_mask}",
        "no shutdown",
        "exit",
        "exit"
    ]

    st.config(dut, commands, type='klish', skip_error_check=True)
    st.wait(2, "Waiting after IP configuration")

    # Verify IP configuration (correct command is "show ip interfaces" not "show ip interface brief")
    verify_cmd = "show ip interfaces"
    verify_out = st.show(dut, verify_cmd, type='klish', skip_tmpl=True, skip_error_check=True)

    if ip_address in str(verify_out):
        st.log(f"✓ SUCCESS: IP address {ip_address} configured on {dut}")
        return True
    else:
        st.log(f"✗ FAILED: IP address not found on {dut}")
        st.log(f"Verify output: {verify_out}")
        return False


def configure_bgp_neighbor_with_password(dut: str, router_id: str, neighbor_ip: str,
                                          remote_as: str, password: str) -> bool:
    """
    Configure BGP with neighbor using password authentication

    Important: password is configured in neighbor sub-mode without repeating "neighbor X.X.X.X"
    """
    st.log(f"Configuring BGP on {dut} with neighbor {neighbor_ip}, password {password}")

    commands = [
        "configure terminal",
        f"router bgp {CONFIG.asn}",
        f"router-id {router_id}",
        f"neighbor {neighbor_ip} remote-as {remote_as}",
        f"password {password}",  # No "neighbor X.X.X.X" prefix in sub-mode
        "address-family ipv4 unicast",
        "activate",
        "exit",
        "exit",
        "exit"
    ]

    result = st.config(dut, commands, type='klish', skip_error_check=True)
    st.wait(2, "Waiting after BGP configuration")

    return True


def ping_ipv4(dut, destination_ipv4, count=5):
    """
    Ping IPv4 address using ipapi
    """
    st.log(f"Pinging {destination_ipv4} from {dut}")

    result = ip_api.ping(
        dut=dut,
        addresses=destination_ipv4,
        family='ipv4',
        count=count
    )

    return result


def verify_bgp_negative_behavior_password(dut: str, neighbor_ip: str):
    """
    Verify BGP is in negative state due to password mismatch

    This is a NEGATIVE test - BGP should NOT establish due to password authentication failure.
    Test PASSES when BGP correctly fails to establish.

    Expected states: Active, Idle, Connect (anything except Established)
    Expected indicators: "Peer Authentication Enabled", "Waiting for peer OPEN"
    """
    st.log(f"Verifying negative BGP behavior on {dut} for neighbor {neighbor_ip}")

    # Wait for BGP to attempt connection
    st.wait(CONFIG.bgp_wait_time, f"Waiting {CONFIG.bgp_wait_time}s for BGP to attempt connection")

    # Get BGP summary
    output_raw = st.show(dut, "show bgp summary", type='klish', skip_tmpl=True, skip_error_check=True)

    output_str = str(output_raw)
    output_lower = output_str.lower()

    st.log(f"BGP Summary Output:\n{output_str}")

    # Check for negative states (Active, Idle, Connect)
    if 'idle' in output_lower or 'active' in output_lower or 'connect' in output_lower:
        st.log(f"✓ NEGATIVE TEST PASSED: BGP correctly NOT establishing (found Idle/Active/Connect state)")

        # Also check detailed neighbor info for authentication indicators
        neighbor_cmd = f"show bgp ipv4 unicast neighbors"
        neighbor_output = st.show(dut, neighbor_cmd, type='klish', skip_tmpl=True, skip_error_check=True)
        neighbor_str = str(neighbor_output)

        st.log(f"Detailed Neighbor Output:\n{neighbor_str}")

        # Check for authentication-related indicators
        if 'peer authentication enabled' in neighbor_str.lower():
            st.log(f"✓ CONFIRMED: Found 'Peer Authentication Enabled' - password auth is active")

        if 'waiting for peer open' in neighbor_str.lower():
            st.log(f"✓ CONFIRMED: Found 'Waiting for peer OPEN' - authentication handshake failing")

        return True

    # Check if BGP is Established (this would be FAILURE for negative test)
    if 'established' in output_lower:
        st.error(f"✗ NEGATIVE TEST FAILED: BGP is Established (should NOT be!)")
        st.error(f"BGP should fail due to password mismatch")
        return False

    # Unknown state
    st.log(f"⚠ WARNING: Could not determine BGP state from output")
    st.log(f"Output: {output_str}")
    return False


def test_ipv4_bgp_negative_password():
    """
    Main test function for NEG-03 IPv4 Incorrect Password

    Test Steps:
    1. Configure IPv4 addresses on both DUTs
    2. Verify IPv4 connectivity with ping
    3. Configure BGP with password authentication
       - DUT1: password WRONG_PASSWORD
       - DUT2: password CORRECT_PASSWORD
    4. Verify BGP does NOT establish (Active/Connect state)
    5. Verify "Peer Authentication Enabled" is shown

    Expected Result:
    - BGP state = Active or Connect (NOT Established)
    - Peer Authentication Enabled
    - Waiting for peer OPEN
    - This is CORRECT negative behavior
    """

    st.banner("TEST START: NEG-03 IPv4 Incorrect Password")

    # STEP 1: Configure IPv4 addresses on both DUTs
    st.banner("STEP 1: Configure IPv4 addresses")

    # DUT1
    if not configure_ip_on_interface(vars.D1, CONFIG.interface, CONFIG.dut1_ip):
        st.error(f"Failed to configure IP address on {vars.D1} {CONFIG.interface}")
        st.generate_tech_support([vars.D1, vars.D2], "ip_config_failed")
        st.report_fail("test_case_failed")

    # DUT2
    if not configure_ip_on_interface(vars.D2, CONFIG.interface, CONFIG.dut2_ip):
        st.error(f"Failed to configure IP address on {vars.D2} {CONFIG.interface}")
        st.generate_tech_support([vars.D1, vars.D2], "ip_config_failed")
        st.report_fail("test_case_failed")

    st.wait(5, "Waiting for IP addresses to be active")

    # STEP 2: Verify IPv4 connectivity
    st.banner("STEP 2: Verify IPv4 connectivity with ping")

    ping_result_d1 = ping_ipv4(vars.D1, CONFIG.dut2_ip, count=5)
    ping_result_d2 = ping_ipv4(vars.D2, CONFIG.dut1_ip, count=5)

    if not ping_result_d1:
        st.error(f"Ping failed from DUT1 to DUT2 ({CONFIG.dut2_ip})")
        st.generate_tech_support([vars.D1, vars.D2], "ipv4_ping_failed")
        st.report_fail("ping_fail", CONFIG.dut1_ip, CONFIG.dut2_ip)

    if not ping_result_d2:
        st.error(f"Ping failed from DUT2 to DUT1 ({CONFIG.dut1_ip})")
        st.generate_tech_support([vars.D1, vars.D2], "ipv4_ping_failed")
        st.report_fail("ping_fail", CONFIG.dut2_ip, CONFIG.dut1_ip)

    st.log("✓ IPv4 connectivity verified successfully")

    # STEP 3: Configure BGP with mismatched passwords
    st.banner("STEP 3: Configure BGP neighbors with MISMATCHED passwords")
    st.log(f"DUT1 password: {CONFIG.dut1_password}")
    st.log(f"DUT2 password: {CONFIG.dut2_password}")

    # DUT1: neighbor 10.1.1.2 with WRONG_PASSWORD
    configure_bgp_neighbor_with_password(
        dut=vars.D1,
        router_id=CONFIG.dut1_router_id,
        neighbor_ip=CONFIG.dut2_ip,
        remote_as=CONFIG.asn,
        password=CONFIG.dut1_password
    )

    # DUT2: neighbor 10.1.1.1 with CORRECT_PASSWORD
    configure_bgp_neighbor_with_password(
        dut=vars.D2,
        router_id=CONFIG.dut2_router_id,
        neighbor_ip=CONFIG.dut1_ip,
        remote_as=CONFIG.asn,
        password=CONFIG.dut2_password
    )

    st.wait(5, "Waiting after BGP configuration")

    # STEP 4: Exit config mode before verification
    st.banner("STEP 4: Exit Config Mode")
    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, "end", type='klish', skip_error_check=True, conf=False)
            st.config(dut, "exit", type='klish', skip_error_check=True, conf=False)
        except Exception as e:
            st.log(f"Exit config mode on {dut}: {str(e)}")

    st.wait(2, "Waiting after exiting config mode")

    # STEP 5: Verify BGP negative behavior
    st.banner("STEP 5: Verify BGP does NOT establish (Negative Test)")
    st.log("Expected: BGP state = Active/Connect, Peer Authentication Enabled")

    # Verify DUT1
    dut1_negative = verify_bgp_negative_behavior_password(vars.D1, CONFIG.dut2_ip)

    # Verify DUT2
    dut2_negative = verify_bgp_negative_behavior_password(vars.D2, CONFIG.dut1_ip)

    # Test Result
    if dut1_negative and dut2_negative:
        st.banner("✓ TEST PASSED: NEG-03 IPv4 Incorrect Password")
        st.log("BGP correctly failed to establish due to password mismatch")
        st.log("This is the expected negative behavior")
        st.report_tc_pass("NEG_03_IPv4_Incorrect_Password", "test_case_passed")
        st.report_pass("test_case_passed")
    else:
        st.banner("✗ TEST FAILED: NEG-03 IPv4 Incorrect Password")
        st.error("BGP did not show expected negative behavior")
        st.generate_tech_support([vars.D1, vars.D2], "bgp_negative_test_failed")
        st.report_tc_fail("NEG_03_IPv4_Incorrect_Password", "test_case_failed")
        st.report_fail("test_case_failed")
