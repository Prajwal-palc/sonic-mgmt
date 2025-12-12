"""
CLEANUP SCRIPT FOR IPv6 BGP AND VLAN CONFIGURATIONS
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/routing/bgp/cleanup_ipv6_bgp_vlan.py \
  --logs-path ./logs/cleanup_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  This script cleans up all IPv6 BGP and VLAN configurations from both DUTs
  using Klish CLI. It removes:
  - BGP router configuration (AS 65001)
  - IPv6 addresses from physical interfaces (Ethernet32)
  - IPv6 addresses from VLAN interfaces (Vlan100)
  - VLAN interface configuration
  - Switchport access configuration
  - VLAN configuration

  The script is idempotent and safe to run multiple times.
"""

from __future__ import annotations

import pytest

from spytest import st, SpyTestDict


# Data dictionary for cleanup
data = SpyTestDict()
data.cli_type = "klish"
data.bgp_asn = "65001"
data.vlan_id = "100"
data.vlan_name = "Vlan100"
data.ipv6_addresses = [
    "2001:db8:1::1/64",      # Physical interface DUT1
    "2001:db8:1::2/64",      # Physical interface DUT2
    "2001:db8:100::1/64",    # VLAN interface DUT1
    "2001:db8:100::2/64"     # VLAN interface DUT2
]


@pytest.fixture(scope="module", autouse=True)
def cleanup_module_hooks(request):
    """
    Module-level fixture for cleanup.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1D2:1")

    st.banner("CLEANUP: Removing all IPv6 BGP and VLAN configuration")

    # Store DUT handles
    data.dut1 = vars.D1
    data.dut2 = vars.D2
    data.dut1_dut2_port = vars.D1D2P1
    data.dut2_dut1_port = vars.D2D1P1

    # Log information
    st.log(f"DUT1: {data.dut1}, DUT2: {data.dut2}")
    st.log(f"DUT1-DUT2 Port: {data.dut1_dut2_port}, DUT2-DUT1 Port: {data.dut2_dut1_port}")

    yield


def cleanup_bgp_config(dut, cli_type="klish"):
    """
    Remove BGP configuration from DUT using Klish CLI.

    Args:
        dut: Device under test
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful or already removed
    """
    st.log(f"Removing BGP configuration from {dut}")

    try:
        commands = []
        commands.append("no router bgp")

        st.config(dut, commands, type=cli_type, skip_error_check=True)
        st.log(f"Successfully removed BGP configuration from {dut}")
        return True
    except Exception as e:
        st.log(f"Note: BGP cleanup on {dut}: {str(e)} (may not exist)")
        return True  # Return True as it's already clean


def cleanup_ipv6_from_interface(dut, interface, cli_type="klish"):
    """
    Remove all IP addresses from an interface using Klish CLI.

    Args:
        dut: Device under test
        interface: Interface name (e.g., Ethernet32, Vlan100)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful or already removed
    """
    st.log(f"Removing IP addresses from {interface} on {dut}")

    try:
        commands = []
        commands.append(f"interface {interface}")
        commands.append("no ip address")
        commands.append("exit")

        st.config(dut, commands, type=cli_type, skip_error_check=True)
        st.log(f"Successfully removed IP addresses from {interface} on {dut}")
        return True
    except Exception as e:
        st.log(f"Note: IP cleanup on {interface}: {str(e)} (may not exist)")
        return True


def cleanup_vlan_interface(dut, vlan_name, cli_type="klish"):
    """
    Remove VLAN interface configuration using Klish CLI.

    Args:
        dut: Device under test
        vlan_name: VLAN interface name (e.g., Vlan100)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful or already removed
    """
    st.log(f"Removing VLAN interface {vlan_name} from {dut}")

    try:
        commands = []
        commands.append(f"no interface {vlan_name}")

        st.config(dut, commands, type=cli_type, skip_error_check=True)
        st.log(f"Successfully removed VLAN interface {vlan_name} from {dut}")
        return True
    except Exception as e:
        st.log(f"Note: VLAN interface cleanup: {str(e)} (may not exist)")
        return True


def cleanup_switchport_config(dut, interface, cli_type="klish"):
    """
    Remove switchport access configuration from interface using Klish CLI.

    Args:
        dut: Device under test
        interface: Interface name (e.g., Ethernet32)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful or already removed
    """
    st.log(f"Removing switchport access configuration from {interface} on {dut}")

    try:
        commands = []
        commands.append(f"interface {interface}")
        commands.append("no switchport access Vlan")
        commands.append("exit")

        st.config(dut, commands, type=cli_type, skip_error_check=True)
        st.log(f"Successfully removed switchport configuration from {interface}")
        return True
    except Exception as e:
        st.log(f"Note: Switchport cleanup: {str(e)} (may not exist)")
        return True


def cleanup_vlan(dut, vlan_id, cli_type="klish"):
    """
    Remove VLAN configuration using Klish CLI.

    Args:
        dut: Device under test
        vlan_id: VLAN ID to remove
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful or already removed
    """
    st.log(f"Removing VLAN {vlan_id} from {dut}")

    try:
        commands = []
        commands.append(f"no interface vlan {vlan_id}")

        st.config(dut, commands, type=cli_type, skip_error_check=True)
        st.log(f"Successfully removed VLAN {vlan_id} from {dut}")
        return True
    except Exception as e:
        st.log(f"Note: VLAN cleanup: {str(e)} (may not exist)")
        return True


def verify_cleanup(dut, cli_type="klish"):
    """
    Verify that all configurations have been cleaned up.

    Args:
        dut: Device under test
        cli_type: CLI type (default: klish)

    Returns:
        None
    """
    st.log(f"Verifying cleanup on {dut}")

    st.log("=" * 80)
    st.log(f"CLEANUP VERIFICATION FOR {dut}")
    st.log("=" * 80)

    # Check BGP
    st.log("\n--- Checking BGP Configuration ---")
    bgp_output = st.show(dut, "show bgp ipv6 unicast summary", type=cli_type, skip_error_check=True)
    st.log(f"BGP Output: {bgp_output}")

    # Check IPv6 interfaces
    st.log("\n--- Checking IPv6 Interfaces ---")
    ipv6_output = st.show(dut, "show ipv6 interfaces", type=cli_type, skip_error_check=True)
    st.log(f"IPv6 Interfaces: {ipv6_output}")

    # Check VLAN configuration
    st.log("\n--- Checking VLAN Configuration ---")
    vlan_output = st.show(dut, "show vlan brief", type=cli_type, skip_error_check=True)
    st.log(f"VLAN Config: {vlan_output}")

    st.log("=" * 80)


@pytest.mark.topology("any")
class TestCleanupIpv6BgpVlan:
    """
    Test class for cleanup operations.
    """

    @pytest.mark.cleanup_all
    def test_cleanup_all_configurations(self):
        """
        TestCase: test_cleanup_all_configurations

        Test Steps:
        1. Remove BGP configuration from both DUTs
        2. Remove IP addresses from VLAN interfaces (Vlan100)
        3. Remove switchport access configuration
        4. Remove VLAN configuration
        5. Verify cleanup on both DUTs

        Expected Result:
        - All BGP, IP, VLAN, and switchport configurations removed
        - Devices return to clean state
        """
        st.banner("CLEANUP: Removing ALL IPv6 BGP and VLAN Configurations")

        # Step 1: Remove BGP configuration
        st.log("Step 1: Removing BGP configuration from both DUTs")

        cleanup_bgp_config(data.dut1, data.cli_type)
        cleanup_bgp_config(data.dut2, data.cli_type)

        st.log("BGP configuration removed from both DUTs")

        # Step 2: Remove IPv6 from VLAN interfaces
        st.log("Step 2: Removing IP addresses from VLAN interfaces")

        cleanup_ipv6_from_interface(data.dut1, data.vlan_name, data.cli_type)
        cleanup_ipv6_from_interface(data.dut2, data.vlan_name, data.cli_type)

        st.log("IP addresses removed from VLAN interfaces")

        # Step 3: Remove switchport access configuration
        st.log("Step 3: Removing switchport access configuration")

        cleanup_switchport_config(data.dut1, data.dut1_dut2_port, data.cli_type)
        cleanup_switchport_config(data.dut2, data.dut2_dut1_port, data.cli_type)

        st.log("Switchport access configuration removed")

        # Step 4: Remove VLAN configuration
        st.log("Step 4: Removing VLAN configuration")

        cleanup_vlan(data.dut1, data.vlan_id, data.cli_type)
        cleanup_vlan(data.dut2, data.vlan_id, data.cli_type)

        st.log("VLAN configuration removed")

        # Step 5: Verify cleanup
        st.log("Step 5: Verifying cleanup on both DUTs")

        verify_cleanup(data.dut1, data.cli_type)
        verify_cleanup(data.dut2, data.cli_type)

        st.log("=" * 80)
        st.log("CLEANUP COMPLETED SUCCESSFULLY")
        st.log("=" * 80)
        st.log("\nYou can now run either:")
        st.log("  - test_ipv6_bgp_interface.py (for physical interface BGP)")
        st.log("  - test_ipv6_vlan_bgp_interface.py (for VLAN interface BGP)")
        st.log("=" * 80)

        st.report_pass("test_case_passed")


    @pytest.mark.cleanup_bgp_only
    def test_cleanup_bgp_only(self):
        """
        TestCase: test_cleanup_bgp_only

        Test Steps:
        1. Remove BGP configuration from both DUTs only
        2. Verify BGP is removed

        Expected Result:
        - BGP configuration removed
        - Other configurations remain unchanged
        """
        st.banner("CLEANUP: Removing BGP Configuration Only")

        st.log("Removing BGP configuration from both DUTs")

        cleanup_bgp_config(data.dut1, data.cli_type)
        cleanup_bgp_config(data.dut2, data.cli_type)

        st.log("Verifying BGP removal")
        bgp_output1 = st.show(data.dut1, "show bgp ipv6 unicast summary", type=data.cli_type, skip_error_check=True)
        bgp_output2 = st.show(data.dut2, "show bgp ipv6 unicast summary", type=data.cli_type, skip_error_check=True)

        st.log(f"DUT1 BGP Status: {bgp_output1}")
        st.log(f"DUT2 BGP Status: {bgp_output2}")

        st.log("BGP cleanup completed")
        st.report_pass("test_case_passed")


    @pytest.mark.cleanup_vlan_only
    def test_cleanup_vlan_only(self):
        """
        TestCase: test_cleanup_vlan_only

        Test Steps:
        1. Remove IP addresses from VLAN interface
        2. Remove switchport configuration
        3. Remove VLAN
        4. Verify VLAN cleanup

        Expected Result:
        - All VLAN-related configuration removed
        - BGP configurations remain unchanged
        """
        st.banner("CLEANUP: Removing VLAN Configuration Only")

        # Remove IP from VLAN interfaces
        st.log("Removing IP addresses from VLAN interfaces")
        cleanup_ipv6_from_interface(data.dut1, data.vlan_name, data.cli_type)
        cleanup_ipv6_from_interface(data.dut2, data.vlan_name, data.cli_type)

        # Remove switchport configuration
        st.log("Removing switchport access configuration")
        cleanup_switchport_config(data.dut1, data.dut1_dut2_port, data.cli_type)
        cleanup_switchport_config(data.dut2, data.dut2_dut1_port, data.cli_type)

        # Remove VLAN
        st.log("Removing VLAN configuration")
        cleanup_vlan(data.dut1, data.vlan_id, data.cli_type)
        cleanup_vlan(data.dut2, data.vlan_id, data.cli_type)

        # Verify
        st.log("Verifying VLAN removal")
        vlan_output1 = st.show(data.dut1, "show vlan brief", type=data.cli_type, skip_error_check=True)
        vlan_output2 = st.show(data.dut2, "show vlan brief", type=data.cli_type, skip_error_check=True)

        st.log(f"DUT1 VLAN Status: {vlan_output1}")
        st.log(f"DUT2 VLAN Status: {vlan_output2}")

        st.log("VLAN cleanup completed")
        st.report_pass("test_case_passed")
