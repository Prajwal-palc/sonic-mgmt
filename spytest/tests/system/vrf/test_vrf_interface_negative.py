"""
VRF INTERFACE BINDING NEGATIVE TESTS
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \\
  --testbed ./testbeds/ztp_standalone.yaml  \\
  tests/system/vrf/test_vrf_interface_negative.py \\
  --logs-path ./logs/vrf_interface_negative_$(date +%F_%H%M%S) \\
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Negative test suite validating VRF forwarding restrictions on interfaces with
  existing Layer 3 (IP) configurations. The suite verifies that VRF binding fails
  with appropriate error messages when attempted on:
  1. VLAN SVI interfaces with IP addresses configured
  2. Physical Ethernet interfaces with IP addresses configured

  These tests confirm proper system behavior by ensuring VRF forwarding cannot be
  applied to interfaces that already have L3 configuration, requiring IP removal
  before VRF binding. All configurations are cleaned up after each test to maintain
  system state.

Pre-requisites:
  - Topology: standalone (single DUT) | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 1 node (standalone)
        # +--------------------+
        # |        dut1        |
        # |   (smic_sonic1)    |
        # |  Ethernet28 (test) |
        # |  Management0       |
        # +--------------------+

  - Feature flags / min SONiC version: VRF and VLAN support enabled
  - Required test variables (YAML): vars/system/vrf/vars_vrf_interface_negative.yaml
    - defaults.cli_type (klish)
    - defaults.verify_timeout
    - defaults.cleanup
    - test_interface (Ethernet28)
    - vlan_id (100)
    - ip_pools (with fallbacks)
    - testcases.* definitions
"""

# Negative testcases for VRF interface binding restrictions with L3 configurations.

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

import pytest
import yaml

from spytest import SpyTestDict, st

VAR_FILE_ENV = "VRF_INTERFACE_NEGATIVE_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "system"
    / "vrf"
    / "vars_vrf_interface_negative.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"VRF interface negative variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("VRF interface negative YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestVrfInterfaceNegative:
    """Testcases covering VRF interface binding negative scenarios with L3 configurations."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        min_topology = defaults.get("min_topology") or ["D1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))

        # Get CLI type from defaults
        cli_type_raw = defaults.get("cli_type", "klish")
        cls.data.cli_type = cli_type_raw if isinstance(cli_type_raw, str) else "klish"

        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Resource tracking for cleanup
        cls.data.configured_vrfs = []
        cls.data.configured_vlans = []
        cls.data.configured_ips = []

        cls.data.dut_map = SpyTestDict()

        # Get DUT handle
        cls.data.dut = topology.D1 if hasattr(topology, 'D1') else None
        if not cls.data.dut:
            # Fallback to getting first DUT from dut_names
            dut_names = st.get_dut_names()
            if dut_names:
                cls.data.dut = dut_names[0]
            else:
                st.error("No DUT found in topology")

        cls.data.dut_names = st.get_dut_names()

        # Get test interface from config
        cls.data.test_interface = config.get("test_interface", "Ethernet28")
        cls.data.vlan_id = config.get("vlan_id", 100)
        cls.data.ip_pools = SpyTestDict(config.get("ip_pools", {}))

        # Disable pagination globally for this test suite to avoid "--more--" prompts
        st.log("Setting terminal length to 0 to disable pagination")
        st.show(cls.data.dut, "terminal length 0", type=cls.data.cli_type, skip_tmpl=True, skip_error_check=True)

        st.log(f"Setup complete. DUT: {cls.data.dut}, CLI Type: {cls.data.cli_type}")
        st.log(f"Test Interface: {cls.data.test_interface}, VLAN ID: {cls.data.vlan_id}")

    @classmethod
    def teardown_class(cls) -> None:
        """Ensure all test resources are removed after the suite completes."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping resource removal")
            return
        cls._cleanup_all_resources()

    def setup_method(self) -> None:
        """Reset per-test bookkeeping."""
        self._test_vrfs = []
        self._test_vlans = []
        self._test_ips = []
        # Ensure terminal length is set at start of each test
        self._ensure_terminal_length()

    def teardown_method(self) -> None:
        """Remove any resources that the testcase configured."""
        if not self.data.cleanup_enabled:
            self._test_vrfs = []
            self._test_vlans = []
            self._test_ips = []
            return

        st.log("Starting per-test cleanup")

        # Cleanup IPs first
        while self._test_ips:
            ip_config = self._test_ips.pop()
            self._remove_ip_from_interface(ip_config['interface'], ip_config['ip'], ip_config['subnet'])
            if ip_config in self.data.configured_ips:
                self.data.configured_ips.remove(ip_config)

        # Cleanup VLANs
        while self._test_vlans:
            vlan_config = self._test_vlans.pop()
            self._cleanup_vlan(vlan_config['vlan_id'], vlan_config.get('interface'))
            if vlan_config in self.data.configured_vlans:
                self.data.configured_vlans.remove(vlan_config)

        # Cleanup VRFs
        while self._test_vrfs:
            vrf_name = self._test_vrfs.pop()
            self._remove_vrf(vrf_name)
            if vrf_name in self.data.configured_vrfs:
                self.data.configured_vrfs.remove(vrf_name)

    @classmethod
    def _cleanup_all_resources(cls) -> None:
        """Remove all resources tracked across the suite."""
        st.log("Starting class-level cleanup of all resources")

        # Cleanup IPs
        while cls.data.configured_ips:
            ip_config = cls.data.configured_ips.pop()
            try:
                commands = [
                    f"interface {ip_config['interface']}",
                    f"no ip address {ip_config['ip']}/{ip_config['subnet']}",
                    "exit"
                ]
                st.config(cls.data.dut, commands, type=cls.data.cli_type, skip_error_check=True)
            except Exception as e:
                st.log(f"Error during IP cleanup: {e}")

        # Cleanup VLANs
        while cls.data.configured_vlans:
            vlan_config = cls.data.configured_vlans.pop()
            try:
                commands = []
                # Remove VLAN member if interface is specified
                if vlan_config.get('interface'):
                    commands.extend([
                        f"interface {vlan_config['interface']}",
                        "no switchport access Vlan",
                        "exit"
                    ])
                # Delete VLAN
                commands.append(f"no vlan {vlan_config['vlan_id']}")
                st.config(cls.data.dut, commands, type=cls.data.cli_type, skip_error_check=True)
            except Exception as e:
                st.log(f"Error during VLAN cleanup: {e}")

        # Cleanup VRFs
        while cls.data.configured_vrfs:
            vrf_name = cls.data.configured_vrfs.pop()
            try:
                command = f"no ip vrf {vrf_name}"
                st.config(cls.data.dut, command, type=cls.data.cli_type, skip_error_check=True)
            except Exception as e:
                st.log(f"Error during VRF cleanup: {e}")

    def _ensure_terminal_length(self) -> None:
        """
        Ensure terminal length is set to 0 to prevent --more-- pagination.
        Must be called before any show commands that might produce long output.
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log("Ensuring terminal length 0 is set to prevent pagination")
        try:
            # Execute from exec mode (not config mode)
            st.show(dut, "terminal length 0", type=cli_type, skip_tmpl=True, skip_error_check=True)
        except Exception as e:
            st.log(f"Note: Could not set terminal length (non-critical): {e}")

    def _find_available_ip(self, pool_name: str) -> Tuple[str, str]:
        """
        Find an available IP address from the pool that's not in use.
        Returns: (ip_address, subnet_mask)
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        pool = self.data.ip_pools.get(pool_name, {})
        primary_ip = pool.get("primary")
        subnet = pool.get("subnet", "24")
        fallback_ips = pool.get("fallback", [])

        # Ensure terminal length is set before show commands
        self._ensure_terminal_length()

        # Get all currently configured IPs using manual show command
        st.log(f"Checking for IP conflicts in pool '{pool_name}'")
        output = st.show(dut, "show ip interface", type=cli_type, skip_tmpl=True)

        # Extract just the IP addresses (without subnet) from output
        used_ips = []
        if output:
            # Parse the output to extract IP addresses
            for line in output.split('\n'):
                if '/' in line and 'Ethernet' in line or 'Vlan' in line:
                    parts = line.split()
                    for part in parts:
                        if '/' in part and '.' in part:
                            # Extract IP without subnet
                            ip_only = part.split('/')[0]
                            used_ips.append(ip_only)
                            break

        st.log(f"Currently used IPs: {used_ips}")

        # Check primary IP first
        if primary_ip not in used_ips:
            st.log(f"Primary IP {primary_ip}/{subnet} is available")
            return (primary_ip, subnet)

        # Try fallback IPs
        for fallback in fallback_ips:
            # Fallback may have subnet included
            if '/' in fallback:
                fallback_ip, fallback_subnet = fallback.split('/')
            else:
                fallback_ip = fallback
                fallback_subnet = subnet

            if fallback_ip not in used_ips:
                st.log(f"Using fallback IP {fallback_ip}/{fallback_subnet}")
                return (fallback_ip, fallback_subnet)

        # No available IP found
        st.report_fail("msg", f"No available IP found in pool '{pool_name}'. All IPs are in use.")

    def _create_vrf(self, vrf_name: str) -> None:
        """Create a VRF and track it for cleanup."""
        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log(f"Creating VRF '{vrf_name}'")
        command = f"ip vrf {vrf_name}"
        output = st.config(dut, command, type=cli_type, skip_error_check=False)

        if "Error" in str(output) or "error" in str(output):
            st.report_fail("msg", f"Failed to create VRF '{vrf_name}'")

        # Track for cleanup
        if vrf_name not in self._test_vrfs:
            self._test_vrfs.append(vrf_name)
        if vrf_name not in self.data.configured_vrfs:
            self.data.configured_vrfs.append(vrf_name)

        st.log(f"VRF '{vrf_name}' created successfully")

    def _remove_vrf(self, vrf_name: str) -> None:
        """Remove a VRF, ignoring errors."""
        dut = self.data.dut
        cli_type = self.data.cli_type

        # Skip system VRFs
        if vrf_name.lower() in ["default", "mgmt"]:
            st.log(f"Skipping removal of system VRF: {vrf_name}")
            return

        st.log(f"Removing VRF '{vrf_name}'")
        try:
            command = f"no ip vrf {vrf_name}"
            st.config(dut, command, type=cli_type, skip_error_check=True)
            st.log(f"VRF '{vrf_name}' removed")
        except Exception as e:
            st.log(f"Error removing VRF '{vrf_name}': {e}")

    def _configure_vlan_svi(self, vlan_id: int, ip_addr: str, subnet: str, interface: str) -> None:
        """
        Configure VLAN SVI with IP address and member interface.
        Steps:
        1. Create VLAN
        2. Configure IP on VLAN interface
        3. Add physical interface as VLAN member
        4. Bring up interfaces
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log(f"Configuring VLAN {vlan_id} SVI with IP {ip_addr}/{subnet}")

        # Step 1: Create VLAN using manual command
        st.log(f"Creating VLAN {vlan_id}")
        commands = [f"vlan {vlan_id}", "exit"]
        result = st.config(dut, commands, type=cli_type, skip_error_check=False)

        if "Error" in str(result) or "error" in str(result):
            st.report_fail("msg", f"Failed to create VLAN {vlan_id}")

        # Wait for VLAN creation to complete
        st.log("Waiting for VLAN creation to settle")
        st.wait(2)

        # Step 2: Configure IP on VLAN interface using manual commands
        vlan_intf = f"Vlan{vlan_id}"
        st.log(f"Configuring IP {ip_addr}/{subnet} on {vlan_intf}")

        commands = [
            f"interface {vlan_intf}",
            f"ip address {ip_addr}/{subnet}",
            "no shutdown",
            "exit"
        ]

        result = st.config(dut, commands, type=cli_type, skip_error_check=False)

        if "Error" in str(result) or "error" in str(result):
            st.report_fail("msg", f"Failed to configure IP on {vlan_intf}")

        st.wait(1)

        # Step 3: Add physical interface as VLAN member (access mode) using manual command
        st.log(f"Adding {interface} to VLAN {vlan_id} as access port")
        commands = [
            f"interface {interface}",
            f"switchport access Vlan {vlan_id}",
            "no shutdown",
            "exit"
        ]

        result = st.config(dut, commands, type=cli_type, skip_error_check=False)

        if "Error" in str(result) or "error" in str(result):
            st.report_fail("msg", f"Failed to add {interface} to VLAN {vlan_id}")

        # CRITICAL: Ensure we exit to exec mode for all CLI types
        # This is necessary so that subsequent show commands don't get "do" prefix
        if cli_type == "klish":
            st.log("Exiting to exec mode after VLAN configuration")
            # Use 'end' to forcefully exit to exec mode from any config level
            st.config(dut, "end", type=cli_type, skip_error_check=True, conf=False)
            st.wait(1)  # Wait for prompt to stabilize

        # Track for cleanup
        vlan_config = {'vlan_id': vlan_id, 'interface': interface}
        if vlan_config not in self._test_vlans:
            self._test_vlans.append(vlan_config)
        if vlan_config not in self.data.configured_vlans:
            self.data.configured_vlans.append(vlan_config)

        ip_config = {'interface': vlan_intf, 'ip': ip_addr, 'subnet': subnet}
        if ip_config not in self._test_ips:
            self._test_ips.append(ip_config)
        if ip_config not in self.data.configured_ips:
            self.data.configured_ips.append(ip_config)

        st.log(f"VLAN {vlan_id} SVI configured successfully")

    def _verify_vlan_configuration(self, vlan_id: int, interface: str, ip_addr: str) -> bool:
        """Verify VLAN configuration including member and IP."""
        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log(f"Verifying VLAN {vlan_id} configuration")

        # DON'T call _ensure_terminal_length() here - causes "do" prefix errors
        # Terminal length was already set at class setup

        # Verify VLAN exists with member - use st.show() for show commands
        cmd = f"show Vlan {vlan_id}"
        output_str = st.show(dut, cmd, type=cli_type, skip_tmpl=True, skip_error_check=True)

        st.log(f"Raw VLAN output: {output_str}")

        # Check if VLAN and interface appear in raw output
        vlan_exists = f"Vlan{vlan_id}" in output_str or str(vlan_id) in output_str
        interface_exists = interface in output_str

        if not vlan_exists:
            st.log(f"VLAN {vlan_id} verification failed: VLAN not found in output")
            return False

        if not interface_exists:
            st.log(f"VLAN {vlan_id} verification failed: Interface {interface} not found as member")
            return False

        # Verify IP on VLAN interface using manual show command
        vlan_intf = f"Vlan{vlan_id}"
        st.log(f"Verifying IP {ip_addr} on {vlan_intf}")

        ip_output = st.show(dut, "show ip interface", type=cli_type, skip_tmpl=True, skip_error_check=True)

        # Check if the IP address is found in the output
        ip_found = False
        if vlan_intf in ip_output and ip_addr in ip_output:
            ip_found = True

        if not ip_found:
            st.log(f"VLAN {vlan_id} verification failed: IP {ip_addr} not found on {vlan_intf}")
            return False

        st.log(f"VLAN {vlan_id} configuration verified successfully")
        return True

    def _cleanup_vlan(self, vlan_id: int, interface: str = None) -> None:
        """
        Cleanup VLAN configuration.
        Steps (in reverse order of creation):
        1. Remove interface from VLAN
        2. Remove IP from VLAN interface
        3. Delete VLAN
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log(f"Cleaning up VLAN {vlan_id}")

        # Remove interface from VLAN if specified
        if interface:
            st.log(f"Removing {interface} from VLAN {vlan_id}")
            try:
                commands = [
                    f"interface {interface}",
                    "no switchport access Vlan",
                    "exit"
                ]
                st.config(dut, commands, type=cli_type, skip_error_check=True)
            except Exception as e:
                st.log(f"Error removing VLAN member: {e}")

        # Remove IP from VLAN interface (will be done by _test_ips cleanup)
        vlan_intf = f"Vlan{vlan_id}"
        st.log(f"Note: IP on {vlan_intf} will be removed by IP cleanup")

        # Delete VLAN
        st.log(f"Deleting VLAN {vlan_id}")
        try:
            command = f"no vlan {vlan_id}"
            st.config(dut, command, type=cli_type, skip_error_check=True)
            st.log(f"VLAN {vlan_id} deleted")
        except Exception as e:
            st.log(f"Error deleting VLAN: {e}")

    def _configure_interface_ip(self, interface: str, ip_addr: str, subnet: str) -> None:
        """
        Configure IP address on physical interface.
        Steps:
        1. Ensure interface is not in switchport mode
        2. Configure IP address
        3. Bring up interface
         """
        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log(f"Configuring IP {ip_addr}/{subnet} on {interface}")

        # Step 1: Remove from any VLAN and configure IP using manual commands
        st.log(f"Ensuring {interface} is in L3 mode and configuring IP")

        commands = [
            f"interface {interface}",
            "no switchport access Vlan",  # Remove from switchport mode
            f"ip address {ip_addr}/{subnet}",
            "no shutdown",
            "exit"
        ]

        result = st.config(dut, commands, type=cli_type, skip_error_check=True)

        # Check for errors (ignore "not in switchport mode" errors)
        if result and "Error" in str(result) and "switchport" not in str(result):
            st.report_fail("msg", f"Failed to configure IP {ip_addr}/{subnet} on {interface}")

        # Track for cleanup
        ip_config = {'interface': interface, 'ip': ip_addr, 'subnet': subnet}
        if ip_config not in self._test_ips:
            self._test_ips.append(ip_config)
        if ip_config not in self.data.configured_ips:
            self.data.configured_ips.append(ip_config)

        st.log(f"IP {ip_addr}/{subnet} configured on {interface} successfully")

    def _verify_interface_ip(self, interface: str, ip_addr: str) -> bool:
        """Verify IP address is configured on interface."""
        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log(f"Verifying IP {ip_addr} on {interface}")

        # Use manual show command
        output = st.show(dut, "show ip interface", type=cli_type, skip_tmpl=True, skip_error_check=True)

        # Check if the interface and IP appear in the output
        if interface in output and ip_addr in output:
            st.log(f"IP {ip_addr} verified on {interface}")
            return True
        else:
            st.log(f"IP {ip_addr} NOT found on {interface}")
            return False

    def _remove_ip_from_interface(self, interface: str, ip_addr: str, subnet: str) -> None:
        """Remove IP address from interface."""
        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log(f"Removing IP {ip_addr}/{subnet} from {interface}")
        try:
            commands = [
                f"interface {interface}",
                f"no ip address {ip_addr}/{subnet}",
                "exit"
            ]
            st.config(dut, commands, type=cli_type, skip_error_check=True)
            st.log(f"IP removed from {interface}")
        except Exception as e:
            st.log(f"Error removing IP: {e}")

    def _attempt_vrf_binding(self, vrf_name: str, interface: str) -> Tuple[bool, str]:
        """
        Attempt to bind VRF to interface. This should FAIL if interface has IP.
        Returns: (success: bool, output: str)
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log(f"Attempting to bind VRF '{vrf_name}' to {interface} (expected to FAIL)")

        # Use vrf bind API with skip_error to capture the error message
        try:
            # Build command manually to capture output
            from utilities.utils import get_interface_number_from_name
            intfv = get_interface_number_from_name(interface)

            commands = []
            commands.append(f"interface {intfv['type']} {intfv['number']}")
            commands.append(f"ip vrf forwarding {vrf_name}")
            commands.append("exit")

            command_string = "\n".join(commands)

            # Execute with skip_error_check to capture error
            output = st.config(
                dut,
                command_string,
                type=cli_type,
                conf=True,
                skip_error_check=True
            )

            st.log(f"VRF binding attempt output: {output}")

            # Check if error occurred
            if "Error" in output or "error" in output:
                st.log(f"VRF binding failed as expected (Error detected)")
                return (False, output)
            else:
                st.log(f"WARNING: VRF binding succeeded (should have failed!)")
                return (True, output)

        except Exception as e:
            st.log(f"Exception during VRF binding attempt: {e}")
            return (False, str(e))

    def _verify_error_message(self, error_output: str, expected_substring: str) -> bool:
        """Verify that error output contains expected error message."""
        st.log(f"Checking if error contains: '{expected_substring}'")

        if expected_substring in error_output:
            st.log(f"✓ Expected error message found in output")
            return True
        else:
            st.log(f"✗ Expected error message NOT found in output")
            st.log(f"Output was: {error_output}")
            return False

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    @pytest.mark.inventory(feature="Regression", testcases=["VRF_Interface_TC2.1"])
    @pytest.mark.negative
    def test_vrf_binding_vlan_svi_with_ip(self) -> None:
        """
        TC 2.1 – Negative test: VRF binding on VLAN SVI with IP configuration.

        Verify that VRF forwarding cannot be applied to a VLAN interface (SVI)
        that has an IP address configured. The system should reject this with
        an error message.
        """
        st.banner("TC 2.1: VRF binding on VLAN SVI with IP should fail")

        testcase = self._get_testcase("2.1")
        vlan_id = testcase.get("vlan_id", self.data.vlan_id)
        vrf_name = testcase.get("vrf_name")
        interface = testcase.get("interface", self.data.test_interface)
        expected_error = testcase.get("expected_error")

        st.log(f"Test Case: {testcase.get('title')}")
        st.log(f"Description: {testcase.get('description')}")

        # Pre-test cleanup: Ensure interface has no IP configuration
        st.log(f"Pre-test cleanup: Ensuring {interface} has no IP or VLAN configuration")

        # Ensure terminal length is set before querying IPs
        self._ensure_terminal_length()

        # Query and remove any existing IPs on the test interface
        st.log(f"Checking if {interface} has any IP addresses configured")
        try:
            # Use manual show command to get IPs
            output = st.show(self.data.dut, "show ip interface", type=self.data.cli_type, skip_tmpl=True, skip_error_check=True)

            # Parse output to find IPs on this interface
            ips_found = []
            if output and interface in output:
                for line in output.split('\n'):
                    if interface in line and '/' in line:
                        parts = line.split()
                        for part in parts:
                            if '/' in part and '.' in part:
                                ips_found.append(part)
                                break

            if ips_found:
                st.log(f"Found {len(ips_found)} IP(s) on {interface}, removing them")
                for ip_with_mask in ips_found:
                    ip_only, mask = ip_with_mask.split('/')
                    st.log(f"Removing existing IP {ip_only}/{mask} from {interface}")
                    self._remove_ip_from_interface(interface, ip_only, mask)
            else:
                st.log(f"No IP addresses found on {interface}")
        except Exception as e:
            st.log(f"Note: Could not query IPs on {interface}: {e}")

        # Pre-test cleanup: Remove VLAN if exists
        st.log("Pre-test cleanup: Removing VLAN if exists")
        self._cleanup_vlan(vlan_id, interface)

        # Remove VRF if exists and recreate fresh
        st.log(f"Pre-test cleanup: Removing VRF '{vrf_name}' if exists")
        self._remove_vrf(vrf_name)

        # Create VRF
        st.log(f"Creating VRF '{vrf_name}'")
        self._create_vrf(vrf_name)

        # Wait for VRF to be applied
        st.log("Waiting 3 seconds for VRF creation to settle")
        st.wait(3)

        # Find available IP for VLAN SVI
        ip_addr, subnet = self._find_available_ip("vlan_svi")

        # Configure VLAN SVI with IP and member
        st.log(f"Configuring VLAN {vlan_id} SVI with IP {ip_addr}/{subnet}")
        self._configure_vlan_svi(vlan_id, ip_addr, subnet, interface)

        # Wait for configuration to settle
        st.log("Waiting 3 seconds for VLAN configuration to settle")
        st.wait(3)

        # Verify VLAN configuration
        st.log(f"Verifying VLAN {vlan_id} configuration")
        if not self._verify_vlan_configuration(vlan_id, interface, ip_addr):
            st.report_fail("msg", f"VLAN {vlan_id} configuration verification failed")

        # Attempt VRF binding (should FAIL)
        st.log(f"Attempting VRF binding on Vlan{vlan_id} (should fail with error)")
        success, output = self._attempt_vrf_binding(vrf_name, f"Vlan{vlan_id}")

        # Verify test result
        if success:
            st.report_fail("msg", f"VRF binding succeeded but should have FAILED! "
                          f"Interface Vlan{vlan_id} has IP {ip_addr} configured.")

        # Verify error message
        if not self._verify_error_message(output, expected_error):
            st.report_fail("msg", f"Expected error message '{expected_error}' not found in output")

        st.log("✓ Test PASSED: VRF binding correctly rejected due to L3 configuration")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["VRF_Interface_TC2.2"])
    @pytest.mark.negative
    def test_vrf_binding_physical_interface_with_ip(self) -> None:
        """
        TC 2.2 – Negative test: VRF binding on physical interface with IP configuration.

        Verify that VRF forwarding cannot be applied to a physical Ethernet interface
        that has an IP address configured. The system should reject this with an
        error message.
        """
        st.banner("TC 2.2: VRF binding on physical interface with IP should fail")

        testcase = self._get_testcase("2.2")
        vrf_name = testcase.get("vrf_name")
        interface = testcase.get("interface", self.data.test_interface)
        expected_error = testcase.get("expected_error")

        st.log(f"Test Case: {testcase.get('title')}")
        st.log(f"Description: {testcase.get('description')}")

        # Pre-test cleanup: Remove any existing IP from interface
        st.log(f"Pre-test cleanup: Ensuring {interface} has no IP configuration")

        # Ensure terminal length is set before querying IPs
        self._ensure_terminal_length()

        # Get current IPs and remove them using manual command
        try:
            output = st.show(self.data.dut, "show ip interface", type=self.data.cli_type, skip_tmpl=True, skip_error_check=True)

            # Parse output to find IPs on this interface
            ips_found = []
            if output and interface in output:
                for line in output.split('\n'):
                    if interface in line and '/' in line:
                        parts = line.split()
                        for part in parts:
                            if '/' in part and '.' in part:
                                ips_found.append(part)
                                break

            if ips_found:
                for ip_with_mask in ips_found:
                    ip_only, mask = ip_with_mask.split('/')
                    self._remove_ip_from_interface(interface, ip_only, mask)
        except Exception as e:
            st.log(f"Note: Could not query IPs on {interface}: {e}")

        # Remove VRF if exists and recreate fresh
        st.log(f"Pre-test cleanup: Removing VRF '{vrf_name}' if exists")
        self._remove_vrf(vrf_name)

        # Create VRF
        st.log(f"Creating VRF '{vrf_name}'")
        self._create_vrf(vrf_name)

        # Wait for VRF to be applied
        st.log("Waiting 3 seconds for VRF creation to settle")
        st.wait(3)

        # Find available IP for physical interface
        ip_addr, subnet = self._find_available_ip("physical_interface")

        # Configure IP on physical interface
        st.log(f"Configuring IP {ip_addr}/{subnet} on {interface}")
        self._configure_interface_ip(interface, ip_addr, subnet)

        # Wait for configuration to settle
        st.log("Waiting 3 seconds for IP configuration to settle")
        st.wait(3)

        # Verify IP configuration
        st.log(f"Verifying IP {ip_addr} on {interface}")
        if not self._verify_interface_ip(interface, ip_addr):
            st.report_fail("msg", f"IP {ip_addr} verification failed on {interface}")

        # Attempt VRF binding (should FAIL)
        st.log(f"Attempting VRF binding on {interface} (should fail with error)")
        success, output = self._attempt_vrf_binding(vrf_name, interface)

        # Verify test result
        if success:
            st.report_fail("msg", f"VRF binding succeeded but should have FAILED! "
                          f"Interface {interface} has IP {ip_addr} configured.")

        # Verify error message
        if not self._verify_error_message(output, expected_error):
            st.report_fail("msg", f"Expected error message '{expected_error}' not found in output")

        st.log("✓ Test PASSED: VRF binding correctly rejected due to L3 configuration")
        st.report_pass("test_case_passed")
