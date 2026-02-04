"""
SM_ISCLI_16 - IP Address Reconfiguration NOOP Test (IS-CLI/Klish)
Author: Athira
2026

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_1node.yaml \
  system/interface/test_sm_iscli_16_ip_noop.py \
  --logs-path ./logs/sm_iscli_16_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Automates bug fix verification for SM_ISCLI_16. The original bug reported that
  reconfiguring an IP address that already exists on an interface produces an error
  message instead of being a NOOP (no operation). After the fix, the second configuration
  should succeed silently without errors.

Pre-requisites:
  - Topology: Single DUT (D1) | Supported: HW and Virtual
  - Minimum SONiC version: 202505-smci-dev-iscli with SM_ISCLI_16 fix
  - Test interfaces: Auto-detected from testbed topology
  - For Loopback: Tests use Loopback0 (default system loopback)
  - For Ethernet: Uses first available Ethernet interface from testbed
  - For VLAN: Creates test VLAN 100 with member port
"""

from __future__ import annotations

import pytest

from spytest import SpyTestDict, st
import apis.routing.ip as ip_api
import apis.system.interface as intf_api
import apis.switching.vlan as vlan_api

# Test configuration
DEFAULT_CLI_TYPE = "klish"

# Test IP addresses
TEST_IPS = SpyTestDict({
    "loopback_ipv4": "10.10.10.1/32",
    "loopback_ipv6": "2001:db8:1::1/128",
    "ethernet_ipv4": "192.168.1.1/24",
    "ethernet_ipv6": "2001:db8:2::1/64",
    "vlan_ipv4": "172.16.1.1/24",
    "vlan_ipv6": "2001:db8:3::1/64",
})

# Test VLAN configuration
TEST_VLAN = "100"
TEST_VLAN_INTERFACE = "Vlan100"

vars = SpyTestDict()
data = SpyTestDict()


@pytest.fixture(scope="module", autouse=True)
def sm_iscli_16_module_hooks(request):
    """Module level setup and teardown"""
    global vars, data

    st.banner("SM_ISCLI_16 MODULE PROLOGUE: Starting")

    # Get device from testbed
    try:
        vars = st.get_testbed_vars()
        data.dut = vars.D1
    except Exception as e:
        pytest.skip(f"Unable to get testbed device: {e}")

    data.cli_type = DEFAULT_CLI_TYPE

    # Get test Ethernet interface from testbed topology
    data.test_ethernet = None
    try:
        if hasattr(vars, 'D1T1P1'):
            # If D1 is connected to traffic generator, use that interface
            data.test_ethernet = vars.D1T1P1
            st.log(f"Using D1T1P1 interface: {data.test_ethernet}")
        elif hasattr(vars, 'D1D2P1'):
            # If D1 is connected to D2, use that interface
            data.test_ethernet = vars.D1D2P1
            st.log(f"Using D1D2P1 interface: {data.test_ethernet}")
        else:
            # Get first available interface from DUT's connections
            dut_links = st.get_dut_links(data.dut)
            if dut_links:
                data.test_ethernet = dut_links[0]
                st.log(f"Using first available link: {data.test_ethernet}")
    except Exception as e:
        st.log(f"Could not auto-detect interface from topology: {e}")

    # Fallback: Use Ethernet0 as default if not found in topology
    if not data.test_ethernet:
        data.test_ethernet = "Ethernet0"
        st.log(f"Using default interface: {data.test_ethernet}")

    # Loopback interface
    data.loopback = "Loopback0"

    st.log(f"Testing on DUT: {data.dut}")
    st.log(f"CLI Type: {data.cli_type}")
    st.log(f"Test Loopback: {data.loopback}")
    st.log(f"Test Ethernet: {data.test_ethernet}")
    st.log(f"Test VLAN: {TEST_VLAN_INTERFACE}")

    yield

    # Cleanup
    st.banner("SM_ISCLI_16 MODULE EPILOGUE: Cleanup")
    cleanup_all_configs()


def cleanup_all_configs():
    """Remove all test configurations"""
    st.log("Cleaning up all test configurations")

    try:
        # Cleanup Loopback IPs
        st.log(f"Cleaning up Loopback {data.loopback}")
        ip_api.delete_ip_interface(
            data.dut,
            data.loopback,
            TEST_IPS.loopback_ipv4,
            family="ipv4",
            cli_type=data.cli_type
        )
        ip_api.delete_ip_interface(
            data.dut,
            data.loopback,
            TEST_IPS.loopback_ipv6,
            family="ipv6",
            cli_type=data.cli_type
        )
    except Exception as e:
        st.warn(f"Loopback cleanup failed: {e}")

    try:
        # Cleanup Ethernet IPs
        st.log(f"Cleaning up Ethernet {data.test_ethernet}")
        intf_api.clear_interface_config(data.dut, [data.test_ethernet])
    except Exception as e:
        st.warn(f"Ethernet cleanup failed: {e}")

    try:
        # Cleanup VLAN
        st.log(f"Cleaning up VLAN {TEST_VLAN}")
        vlan_api.delete_vlan(data.dut, TEST_VLAN, cli_type=data.cli_type)
    except Exception as e:
        st.warn(f"VLAN cleanup failed: {e}")


def configure_ip_and_verify_noop(interface, ip_address, family="ipv4"):
    """
    Configure IP address twice and verify second configuration is NOOP (no error).

    Args:
        interface: Interface name (e.g., Loopback0, Ethernet0, Vlan100)
        ip_address: IP address with subnet (e.g., 10.10.10.1/32)
        family: Address family (ipv4 or ipv6)

    Returns:
        bool: True if test passes (NOOP behavior works), False otherwise
    """
    st.log(f"Testing NOOP behavior for {interface} with {ip_address}")

    # Step 1: Configure IP address first time
    st.log(f"First configuration: {ip_address} on {interface}")
    result1 = ip_api.config_ip_addr_interface(
        data.dut,
        interface,
        ip_address.split('/')[0],
        subnet=ip_address.split('/')[1],
        family=family,
        cli_type=data.cli_type
    )

    if not result1:
        st.error(f"First IP configuration failed for {interface}")
        return False

    st.log(f"First configuration successful")
    st.wait(2, "Wait for configuration to settle")

    # Step 2: Verify IP is configured
    ip_output = ip_api.get_interface_ip_address(
        data.dut,
        interface,
        family=family,
        cli_type=data.cli_type
    )

    ip_found = False
    expected_ip = ip_address.split('/')[0]
    for entry in ip_output:
        if entry.get('interface') == interface and expected_ip in str(entry.get('ipaddr', '')):
            ip_found = True
            st.log(f"IP {ip_address} verified on {interface}")
            break

    if not ip_found:
        st.error(f"IP {ip_address} not found on {interface} after first configuration")
        return False

    # Step 3: Configure same IP address second time (should be NOOP)
    st.log(f"Second configuration (NOOP test): {ip_address} on {interface}")
    result2 = ip_api.config_ip_addr_interface(
        data.dut,
        interface,
        ip_address.split('/')[0],
        subnet=ip_address.split('/')[1],
        family=family,
        cli_type=data.cli_type
    )

    if not result2:
        st.error(f"Second IP configuration failed (should be NOOP): {interface}")
        st.error("Bug SM_ISCLI_16 NOT fixed: Reconfiguring same IP produces error")
        return False

    st.log(f"Second configuration successful (NOOP behavior verified)")

    # Step 4: Verify IP is still configured correctly
    ip_output2 = ip_api.get_interface_ip_address(
        data.dut,
        interface,
        family=family,
        cli_type=data.cli_type
    )

    ip_found2 = False
    for entry in ip_output2:
        if entry.get('interface') == interface and expected_ip in str(entry.get('ipaddr', '')):
            ip_found2 = True
            st.log(f"IP {ip_address} still correctly configured on {interface}")
            break

    if not ip_found2:
        st.error(f"IP {ip_address} missing after second configuration on {interface}")
        return False

    st.log(f"NOOP test PASSED for {interface} with {ip_address}")
    return True


@pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_16_TC1"])
@pytest.mark.sm_iscli_16
def test_sm_iscli_16_tc1_loopback_ipv4_noop():
    """
    SM_ISCLI_16_TC1: Verify IPv4 address reconfiguration NOOP on Loopback interface

    Scenario:
      1. Configure IPv4 address on Loopback0 (10.10.10.1/32)
      2. Verify IP is configured
      3. Configure same IPv4 address again (should be NOOP, no error)
      4. Verify IP is still configured correctly
    """
    st.log("=" * 80)
    st.banner("SM_ISCLI_16_TC1: Loopback IPv4 Address NOOP Test")
    st.log("=" * 80)

    result = configure_ip_and_verify_noop(
        data.loopback,
        TEST_IPS.loopback_ipv4,
        family="ipv4"
    )

    if not result:
        st.report_fail("msg", f"NOOP test failed for {data.loopback} IPv4")

    st.report_pass("test_case_passed")


@pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_16_TC2"])
@pytest.mark.sm_iscli_16
def test_sm_iscli_16_tc2_loopback_ipv6_noop():
    """
    SM_ISCLI_16_TC2: Verify IPv6 address reconfiguration NOOP on Loopback interface

    Scenario:
      1. Configure IPv6 address on Loopback0 (2001:db8:1::1/128)
      2. Verify IP is configured
      3. Configure same IPv6 address again (should be NOOP, no error)
      4. Verify IP is still configured correctly
    """
    st.log("=" * 80)
    st.banner("SM_ISCLI_16_TC2: Loopback IPv6 Address NOOP Test")
    st.log("=" * 80)

    result = configure_ip_and_verify_noop(
        data.loopback,
        TEST_IPS.loopback_ipv6,
        family="ipv6"
    )

    if not result:
        st.report_fail("msg", f"NOOP test failed for {data.loopback} IPv6")

    st.report_pass("test_case_passed")


@pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_16_TC3"])
@pytest.mark.sm_iscli_16
def test_sm_iscli_16_tc3_ethernet_ipv4_noop():
    """
    SM_ISCLI_16_TC3: Verify IPv4 address reconfiguration NOOP on Ethernet interface

    Scenario:
      1. Configure IPv4 address on Ethernet interface (192.168.1.1/24)
      2. Verify IP is configured
      3. Configure same IPv4 address again (should be NOOP, no error)
      4. Verify IP is still configured correctly
    """
    st.log("=" * 80)
    st.banner("SM_ISCLI_16_TC3: Ethernet IPv4 Address NOOP Test")
    st.log("=" * 80)

    result = configure_ip_and_verify_noop(
        data.test_ethernet,
        TEST_IPS.ethernet_ipv4,
        family="ipv4"
    )

    if not result:
        st.report_fail("msg", f"NOOP test failed for {data.test_ethernet} IPv4")

    st.report_pass("test_case_passed")


@pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_16_TC4"])
@pytest.mark.sm_iscli_16
def test_sm_iscli_16_tc4_ethernet_ipv6_noop():
    """
    SM_ISCLI_16_TC4: Verify IPv6 address reconfiguration NOOP on Ethernet interface

    Scenario:
      1. Configure IPv6 address on Ethernet interface (2001:db8:2::1/64)
      2. Verify IP is configured
      3. Configure same IPv6 address again (should be NOOP, no error)
      4. Verify IP is still configured correctly
    """
    st.log("=" * 80)
    st.banner("SM_ISCLI_16_TC4: Ethernet IPv6 Address NOOP Test")
    st.log("=" * 80)

    result = configure_ip_and_verify_noop(
        data.test_ethernet,
        TEST_IPS.ethernet_ipv6,
        family="ipv6"
    )

    if not result:
        st.report_fail("msg", f"NOOP test failed for {data.test_ethernet} IPv6")

    st.report_pass("test_case_passed")


@pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_16_TC5"])
@pytest.mark.sm_iscli_16
def test_sm_iscli_16_tc5_vlan_ipv4_noop():
    """
    SM_ISCLI_16_TC5: Verify VLAN IPv4 NOOP behavior

    Scenario:
      1. Create VLAN 100
      2. Configure IPv4 on Vlan100 interface (172.16.1.1/24)
      3. Verify IP is configured
      4. Reconfigure same IPv4 (should be NOOP - no error)
      5. Verify IP still configured correctly

    NOTE: Configures IP directly on Vlan interface, does NOT add members
    """
    st.log("=" * 80)
    st.banner("SM_ISCLI_16_TC5: VLAN IPv4 NOOP")
    st.log("=" * 80)

    # Create VLAN first
    st.log(f"Creating VLAN {TEST_VLAN}")
    if not vlan_api.create_vlan(data.dut, TEST_VLAN, cli_type=data.cli_type):
        st.report_fail("msg", f"Failed to create VLAN {TEST_VLAN}")

    st.wait(2, "Wait for VLAN creation to settle")

    # Configure IP on Vlan interface (no member addition needed)
    if not configure_ip_and_verify_noop(TEST_VLAN_INTERFACE, TEST_IPS.vlan_ipv4, family="ipv4"):
        st.report_fail("msg", "VLAN IPv4 NOOP test failed")

    st.report_pass("test_case_passed")


@pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_16_TC6"])
@pytest.mark.sm_iscli_16
def test_sm_iscli_16_tc6_vlan_ipv6_noop():
    """
    SM_ISCLI_16_TC6: Verify VLAN IPv6 NOOP behavior

    Scenario:
      1. Use existing VLAN 100
      2. Configure IPv6 on Vlan100 interface (2001:db8:3::1/64)
      3. Verify IP is configured
      4. Reconfigure same IPv6
      5. For IPv6: "overlap" message is EXPECTED and CORRECT
      6. Verify IP still configured correctly (NOOP achieved)

    NOTE: IPv6 shows overlap message on reconfiguration - this is normal
    """
    st.log("=" * 80)
    st.banner("SM_ISCLI_16_TC6: VLAN IPv6 NOOP (overlap message expected)")
    st.log("=" * 80)

    # VLAN should already exist from TC5, but create if needed
    vlan_api.create_vlan(data.dut, TEST_VLAN, cli_type=data.cli_type)
    st.wait(1, "Ensure VLAN exists")

    # Configure IP on Vlan interface
    if not configure_ip_and_verify_noop(TEST_VLAN_INTERFACE, TEST_IPS.vlan_ipv6, family="ipv6"):
        st.report_fail("msg", "VLAN IPv6 NOOP test failed")

    st.report_pass("test_case_passed")


@pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_16_TC7"])
@pytest.mark.sm_iscli_16
def test_sm_iscli_16_tc7_multiple_reconfigurations():
    """
    SM_ISCLI_16_TC7: Verify multiple consecutive reconfigurations are NOOP

    Scenario:
      1. Configure IPv4 on Loopback0
      2. Reconfigure same IP 5 times consecutively
      3. Verify each reconfiguration succeeds (NOOP)
      4. Verify IP remains correctly configured
    """
    st.log("=" * 80)
    st.banner("SM_ISCLI_16_TC7: Multiple Consecutive Reconfigurations NOOP Test")
    st.log("=" * 80)

    test_ip = "10.20.20.1/32"
    interface = data.loopback
    family = "ipv4"

    # First configuration
    st.log(f"Initial configuration: {test_ip} on {interface}")
    result = ip_api.config_ip_addr_interface(
        data.dut,
        interface,
        test_ip.split('/')[0],
        subnet=test_ip.split('/')[1],
        family=family,
        cli_type=data.cli_type
    )

    if not result:
        st.report_fail("msg", f"Initial IP configuration failed for {interface}")

    st.wait(2, "Wait for configuration to settle")

    # Multiple reconfigurations
    num_reconfigs = 5
    for i in range(1, num_reconfigs + 1):
        st.log(f"Reconfiguration attempt {i}/{num_reconfigs}")
        result = ip_api.config_ip_addr_interface(
            data.dut,
            interface,
            test_ip.split('/')[0],
            subnet=test_ip.split('/')[1],
            family=family,
            cli_type=data.cli_type
        )

        if not result:
            st.error(f"Reconfiguration {i} failed (should be NOOP)")
            st.report_fail("msg", f"Multiple NOOP test failed at iteration {i}")

        st.log(f"Reconfiguration {i} succeeded (NOOP)")

    # Final verification
    ip_output = ip_api.get_interface_ip_address(
        data.dut,
        interface,
        family=family,
        cli_type=data.cli_type
    )

    expected_ip = test_ip.split('/')[0]
    ip_found = False
    for entry in ip_output:
        if entry.get('interface') == interface and expected_ip in str(entry.get('ipaddr', '')):
            ip_found = True
            st.log(f"IP {test_ip} verified on {interface} after {num_reconfigs} reconfigurations")
            break

    if not ip_found:
        st.report_fail("msg", f"IP {test_ip} not found after multiple reconfigurations")

    st.report_pass("test_case_passed")


@pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_16_TC8"])
@pytest.mark.sm_iscli_16
def test_sm_iscli_16_tc8_mixed_ipv4_ipv6_noop():
    """
    SM_ISCLI_16_TC8: Verify NOOP works with both IPv4 and IPv6 on same interface

    Scenario:
      1. Configure IPv4 and IPv6 on Loopback0
      2. Reconfigure both IPs (should be NOOP)
      3. Verify both IPs remain correctly configured
    """
    st.log("=" * 80)
    st.banner("SM_ISCLI_16_TC8: Mixed IPv4/IPv6 NOOP Test")
    st.log("=" * 80)

    interface = data.loopback
    ipv4_addr = "10.30.30.1/32"
    ipv6_addr = "2001:db8:4::1/128"

    # Configure IPv4
    st.log(f"Configuring IPv4: {ipv4_addr} on {interface}")
    if not ip_api.config_ip_addr_interface(
        data.dut,
        interface,
        ipv4_addr.split('/')[0],
        subnet=ipv4_addr.split('/')[1],
        family="ipv4",
        cli_type=data.cli_type
    ):
        st.report_fail("msg", f"IPv4 configuration failed on {interface}")

    # Configure IPv6
    st.log(f"Configuring IPv6: {ipv6_addr} on {interface}")
    if not ip_api.config_ip_addr_interface(
        data.dut,
        interface,
        ipv6_addr.split('/')[0],
        subnet=ipv6_addr.split('/')[1],
        family="ipv6",
        cli_type=data.cli_type
    ):
        st.report_fail("msg", f"IPv6 configuration failed on {interface}")

    st.wait(2, "Wait for configuration to settle")

    # Reconfigure IPv4 (NOOP)
    st.log(f"Reconfiguring IPv4 (NOOP test): {ipv4_addr}")
    if not ip_api.config_ip_addr_interface(
        data.dut,
        interface,
        ipv4_addr.split('/')[0],
        subnet=ipv4_addr.split('/')[1],
        family="ipv4",
        cli_type=data.cli_type
    ):
        st.report_fail("msg", f"IPv4 reconfiguration failed (should be NOOP)")

    # Reconfigure IPv6 (NOOP)
    st.log(f"Reconfiguring IPv6 (NOOP test): {ipv6_addr}")
    if not ip_api.config_ip_addr_interface(
        data.dut,
        interface,
        ipv6_addr.split('/')[0],
        subnet=ipv6_addr.split('/')[1],
        family="ipv6",
        cli_type=data.cli_type
    ):
        st.report_fail("msg", f"IPv6 reconfiguration failed (should be NOOP)")

    # Verify both IPs
    ipv4_output = ip_api.get_interface_ip_address(data.dut, interface, family="ipv4", cli_type=data.cli_type)
    ipv6_output = ip_api.get_interface_ip_address(data.dut, interface, family="ipv6", cli_type=data.cli_type)

    ipv4_found = any(
        entry.get('interface') == interface and ipv4_addr.split('/')[0] in str(entry.get('ipaddr', ''))
        for entry in ipv4_output
    )

    ipv6_found = any(
        entry.get('interface') == interface and ipv6_addr.split('/')[0] in str(entry.get('ipaddr', ''))
        for entry in ipv6_output
    )

    if not ipv4_found:
        st.report_fail("msg", f"IPv4 {ipv4_addr} not found after NOOP test")

    if not ipv6_found:
        st.report_fail("msg", f"IPv6 {ipv6_addr} not found after NOOP test")

    st.log("Both IPv4 and IPv6 NOOP tests passed")
    st.report_pass("test_case_passed")
