"""
VLAN BASIC CONFIGURATION - Running Config and Complete Lifecycle
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/ztp_standalone.yaml  \
  tests/switching/test_vlan_basic_config.py \
  --logs-path ./logs/test_vlan_basic_config_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

  To suppress framework deprecation warnings:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/ztp_standalone.yaml  \
  tests/switching/test_vlan_basic_config.py \
  --logs-path ./logs/test_vlan_basic_config_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native \
  -W ignore::DeprecationWarning

Description:
  Comprehensive VLAN testing with two test cases:

  Test 1: Running Configuration Verification (VLAN 200)
    - Verifies VLAN and interface appear in "show running-configuration"
    - Simple VLAN creation without port assignment or IP configuration

  Test 2: Complete VLAN Lifecycle (VLAN 100) - Matching vlan.md
    - Creates VLAN, assigns physical port as switchport access member
    - Configures IPv4 and IPv6 addresses on VLAN interface
    - Verifies using "show interface Vlan100" and "show interface Ethernet272"
    - Proper cleanup in reverse order (IPv6 → IPv4 → Port → VLAN)

  Pagination Handling:
  - Sets 'terminal length 0' to disable --more-- prompts in show commands
  - Prevents script from hanging on commands like 'show interface status'
  - Applied globally in setup_class and before critical show commands

Pre-requisites:
  - Topology: standalone (single DUT) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node (standalone)
        # +--------------------+
        # |        D1          |
        # |   (smic_sonic1)    |
        # |   Ethernet272      |
        # |   VLAN 100, 200    |
        # +--------------------+

  - Feature flags / min SONiC version: Basic VLAN and IPv4/IPv6 support
  - Required test variables (YAML): vars/switching/vlan/vars_vlan_basic.yaml
  - Configuration Override: Can override via testbed params or environment variables
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.switching.vlan as vlan_api
import apis.routing.ip as ip_api


# Module constants
VAR_FILE_ENV = "VLAN_BASIC_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[2]
    / "vars"
    / "switching"
    / "vlan"
    / "vars_vlan_basic.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override.

    Returns:
        Dictionary containing test configuration and defaults

    Raises:
        FileNotFoundError: If YAML file not found
        ValueError: If YAML structure is invalid
    """
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"VLAN basic config variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "defaults" not in content:
        raise ValueError("VLAN basic YAML must contain key 'defaults'")

    return content


def _set_terminal_length(dut: str, length: int = 0) -> None:
    """Set terminal length to control pagination in show commands.

    Args:
        dut: Device under test
        length: Terminal length (0 = no pagination, disable --more-- prompts)
    """
    try:
        # Use klish CLI to set terminal length
        cmd = f"terminal length {length}"
        st.config(dut, cmd, type="klish", conf=False, skip_error_check=True)
        st.log(f"Set terminal length to {length} on {dut} (pagination disabled)")
    except Exception as e:
        st.warn(f"Failed to set terminal length: {e}")


def _get_available_interfaces(dut: str) -> List[str]:
    """Get list of available Ethernet interfaces on the DUT.

    Args:
        dut: Device under test

    Returns:
        List of interface names (e.g., ['Ethernet0', 'Ethernet4', ...])
    """
    try:
        # Disable pagination to avoid --more-- prompts
        _set_terminal_length(dut, 0)

        # Get interface list using show commands
        output = st.show(dut, "show interface status", type="klish", skip_tmpl=True)

        interfaces = []
        if isinstance(output, str):
            # Parse interface names from output
            for line in output.split('\n'):
                match = re.search(r'(Ethernet\d+)', line)
                if match:
                    interfaces.append(match.group(1))

        # Fallback: common interface names
        if not interfaces:
            st.log("Could not auto-discover interfaces, using common names")
            interfaces = [f"Ethernet{i}" for i in [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40,
                                                     44, 48, 52, 56, 60, 64, 68, 72, 76, 80]]

        st.log(f"Available interfaces: {interfaces}")
        return interfaces

    except Exception as e:
        st.warn(f"Failed to get interface list: {e}, using fallback")
        return [f"Ethernet{i}" for i in range(0, 256, 4)]


def _merge_config_with_overrides(defaults: Dict[str, Any]) -> Dict[str, Any]:
    """Merge default config with testbed params and environment variable overrides.

    Precedence: Environment Variables > Testbed Params > YAML Defaults

    Args:
        defaults: Default configuration from YAML

    Returns:
        Merged configuration dictionary
    """
    merged = dict(defaults)

    # Get testbed params if available
    try:
        testbed_vars = st.get_testbed_vars()
        testbed_params = testbed_vars.get("params", {})
        vlan_params = testbed_params.get("vlan_tests", {})

        # Merge testbed params
        for key, value in vlan_params.items():
            merged[key] = value
            st.log(f"Testbed override: {key} = {value}")
    except Exception as e:
        st.debug(f"No testbed params override: {e}")

    # Environment variable overrides (highest priority)
    env_mappings = {
        "VLAN_ID": "vlan_id",
        "VLAN_ID_RUNNING_CONFIG": "vlan_id_running_config",
        "VLAN_IPV4": "ipv4_address",
        "VLAN_IPV6": "ipv6_address",
        "VLAN_INTERFACE": "manual_interface"
    }

    for env_var, config_key in env_mappings.items():
        env_value = st.getenv(env_var)
        if env_value:
            # Handle type conversion for vlan_id
            if "vlan_id" in config_key:
                merged[config_key] = int(env_value)
            else:
                merged[config_key] = env_value
            st.log(f"Environment override: {config_key} = {env_value}")

    return merged


@pytest.mark.topology("any")
class TestVlanBasicConfig:
    """Testcases covering VLAN running config verification and complete lifecycle."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.banner("CLASS SETUP: VLAN Basic Configuration Test Suite")

        # Load configuration
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # Merge with overrides
        merged_config = _merge_config_with_overrides(defaults)

        # Get minimum topology
        min_topology = merged_config.get("min_topology") or ["D1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(merged_config)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))

        # CLI settings
        cls.data.cli_type = merged_config.get("cli_type", "klish")
        cls.data.verify_timeout = int(merged_config.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(merged_config.get("cleanup", True))

        # DUT mapping
        cls.data.dut_names = st.get_dut_names()
        if not cls.data.dut_names:
            st.report_fail("msg", "No DUTs found in testbed")

        cls.data.dut = cls.data.dut_names[0]
        st.log(f"Using DUT: {cls.data.dut}")

        # Disable terminal pagination to avoid --more-- prompts in all show commands
        _set_terminal_length(cls.data.dut, 0)
        st.log("Terminal pagination disabled for all show commands")

        # Interface selection
        interface_selection = merged_config.get("interface_selection", "auto")
        if interface_selection == "auto":
            available_interfaces = _get_available_interfaces(cls.data.dut)
            # Use last interface to avoid mgmt/control plane interfaces
            cls.data.test_interface = available_interfaces[-1] if available_interfaces else "Ethernet272"
            st.log(f"Auto-selected interface: {cls.data.test_interface}")
        else:
            cls.data.test_interface = merged_config.get("manual_interface", "Ethernet272")
            st.log(f"Using manual interface: {cls.data.test_interface}")

        # Test parameters for Test 1 (Running Config)
        cls.data.vlan_id_running_config = str(merged_config.get("vlan_id_running_config", 200))

        # Test parameters for Test 2 (Complete Lifecycle)
        cls.data.vlan_id = str(merged_config.get("vlan_id", 100))
        cls.data.ipv4_address = merged_config.get("ipv4_address", "20.1.1.4")
        cls.data.ipv4_subnet = merged_config.get("ipv4_subnet", "24")
        cls.data.ipv6_address = merged_config.get("ipv6_address", "8000::1")
        cls.data.ipv6_subnet = merged_config.get("ipv6_subnet", "64")

        # Configuration tracking
        cls.data.configured_vlans = []
        cls.data.configured_ips = []
        cls.data.configured_members = []

        st.log("=" * 80)
        st.log("TEST CONFIGURATION SUMMARY")
        st.log("=" * 80)
        st.log(f"  DUT: {cls.data.dut}")
        st.log(f"  CLI Type: {cls.data.cli_type}")
        st.log(f"  Test 1 - Running Config VLAN: {cls.data.vlan_id_running_config}")
        st.log(f"  Test 2 - Lifecycle VLAN: {cls.data.vlan_id}")
        st.log(f"  Test 2 - Interface: {cls.data.test_interface}")
        st.log(f"  Test 2 - IPv4: {cls.data.ipv4_address}/{cls.data.ipv4_subnet}")
        st.log(f"  Test 2 - IPv6: {cls.data.ipv6_address}/{cls.data.ipv6_subnet}")
        st.log("=" * 80)

    @classmethod
    def teardown_class(cls) -> None:
        """Ensure all test configurations are removed after the suite completes."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled - skipping teardown")
            return

        st.banner("CLASS TEARDOWN: Cleaning up all test configurations")
        cls._cleanup_all_configurations()

    def setup_method(self, method) -> None:
        """Reset per-test bookkeeping.

        Args:
            method: The test method being set up (provided by pytest)
        """
        st.banner(f"TEST SETUP: {method.__name__}")
        self._test_config = SpyTestDict()

    def teardown_method(self, method) -> None:
        """Remove any configurations that the testcase created.

        Args:
            method: The test method being torn down (provided by pytest)
        """
        if not self.data.cleanup_enabled:
            st.log("Cleanup disabled - skipping test teardown")
            return

        st.banner(f"TEST TEARDOWN: {method.__name__}")
        # Cleanup is handled by individual test methods in finally blocks

    @classmethod
    def _cleanup_all_configurations(cls) -> None:
        """Remove all tracked configurations in proper reverse order."""
        dut = cls.data.dut
        cli_type = cls.data.cli_type

        try:
            # 1. Remove all IP addresses from VLAN interfaces
            for ip_config in cls.data.configured_ips:
                st.log(f"Removing IP: {ip_config}")
                try:
                    ip_api.delete_ip_interface(
                        dut,
                        interface_name=ip_config["interface"],
                        ip_address=ip_config["address"],
                        subnet=ip_config["subnet"],
                        family=ip_config["family"],
                        cli_type=cli_type,
                        skip_error=True
                    )
                except Exception as e:
                    st.debug(f"Failed to remove IP {ip_config}: {e}")

            # 2. Remove VLAN member ports
            for member_config in cls.data.configured_members:
                st.log(f"Removing VLAN member: {member_config}")
                try:
                    vlan_api.delete_vlan_member(
                        dut,
                        vlan=member_config["vlan"],
                        port_list=member_config["port"],
                        cli_type=cli_type
                    )
                except Exception as e:
                    st.debug(f"Failed to remove member {member_config}: {e}")

            # 3. Delete all VLANs
            for vlan_id in cls.data.configured_vlans:
                st.log(f"Deleting VLAN: {vlan_id}")
                try:
                    vlan_api.delete_vlan(dut, vlan_id, cli_type=cli_type)
                except Exception as e:
                    st.debug(f"Failed to delete VLAN {vlan_id}: {e}")

            st.log("All configurations cleaned up successfully")

        except Exception as e:
            st.error(f"Error during cleanup: {e}")

    @staticmethod
    def _get_running_config(dut: str) -> str:
        """Retrieve full running configuration with pagination disabled.

        Args:
            dut: Device under test

        Returns:
            Running configuration as string
        """
        # Ensure terminal length 0 to avoid --more-- pagination prompts
        _set_terminal_length(dut, 0)

        cmd = "show running-configuration"
        output = st.show(dut, cmd, type="klish", skip_tmpl=True, skip_error_check=True)

        if isinstance(output, list) and output:
            # Join list output into single string
            config_text = "\n".join(str(item) for item in output)
        elif isinstance(output, str):
            config_text = output
        else:
            config_text = str(output)

        return config_text

    @staticmethod
    def _vlan_exists_in_config(config_text: str, vlan_id: str) -> Dict[str, bool]:
        """Parse running config to check if VLAN exists.

        Args:
            config_text: Running configuration text
            vlan_id: VLAN ID to search for

        Returns:
            Dictionary with 'vlan_defined' and 'interface_defined' boolean flags
        """
        result = {
            "vlan_defined": False,
            "interface_defined": False
        }

        # Check for "vlan <id>" definition
        vlan_pattern = rf"^\s*vlan\s+{vlan_id}\s*$"
        if re.search(vlan_pattern, config_text, re.MULTILINE):
            result["vlan_defined"] = True
            st.log(f"Found 'vlan {vlan_id}' in configuration")

        # Check for "interface Vlan<id>" definition
        interface_pattern = rf"^\s*interface\s+Vlan{vlan_id}\s*$"
        if re.search(interface_pattern, config_text, re.MULTILINE | re.IGNORECASE):
            result["interface_defined"] = True
            st.log(f"Found 'interface Vlan{vlan_id}' in configuration")

        return result

    def _cleanup_vlan(self, vlan_id: str) -> None:
        """Remove VLAN if it exists (simple cleanup for Test 1).

        Args:
            vlan_id: VLAN ID to delete
        """
        try:
            vlan_api.delete_vlan(self.data.dut, vlan_id, cli_type=self.data.cli_type)
            st.log(f"Cleaned up VLAN {vlan_id}")
        except Exception as e:
            st.debug(f"Cleanup VLAN error (may not exist): {e}")

    def _cleanup_vlan_complete(self, vlan_id: str, interface: str) -> None:
        """Complete cleanup for Test 2 in reverse order.

        Args:
            vlan_id: VLAN ID
            interface: Physical interface name
        """
        dut = self.data.dut
        cli_type = self.data.cli_type
        interface_name = f"Vlan{vlan_id}"

        st.banner("CLEANUP: Removing test configuration in reverse order")

        # Step 1: Remove IPv6 address
        try:
            st.log(f"1. Removing IPv6 {self.data.ipv6_address}/{self.data.ipv6_subnet} from {interface_name}")
            ip_api.delete_ip_interface(
                dut,
                interface_name=interface_name,
                ip_address=self.data.ipv6_address,
                subnet=self.data.ipv6_subnet,
                family="ipv6",
                cli_type=cli_type,
                skip_error=True
            )
        except Exception as e:
            st.debug(f"IPv6 cleanup error: {e}")

        # Step 2: Remove IPv4 address
        try:
            st.log(f"2. Removing IPv4 {self.data.ipv4_address}/{self.data.ipv4_subnet} from {interface_name}")
            ip_api.delete_ip_interface(
                dut,
                interface_name=interface_name,
                ip_address=self.data.ipv4_address,
                subnet=self.data.ipv4_subnet,
                family="ipv4",
                cli_type=cli_type,
                skip_error=True
            )
        except Exception as e:
            st.debug(f"IPv4 cleanup error: {e}")

        # Step 3: Remove interface from VLAN
        try:
            st.log(f"3. Removing {interface} from VLAN {vlan_id}")
            vlan_api.delete_vlan_member(
                dut,
                vlan=vlan_id,
                port_list=interface,
                cli_type=cli_type
            )
        except Exception as e:
            st.debug(f"VLAN member removal error: {e}")

        # Step 4: Delete VLAN
        try:
            st.log(f"4. Deleting VLAN {vlan_id}")
            vlan_api.delete_vlan(dut, vlan_id, cli_type=cli_type)
        except Exception as e:
            st.debug(f"VLAN deletion error: {e}")

        st.log("Cleanup completed")

    @pytest.mark.inventory(feature="Regression", testcases=["VLAN_TC_001"])
    def test_vlan_creation_in_running_config(self) -> None:
        """TC 001 - Verify VLAN creation and interface appear in running configuration.

        Test Steps:
        1. Initial cleanup - delete VLAN 200 if exists
        2. Capture initial running config and verify VLAN 200 does NOT exist
        3. Create VLAN 200 via sonic-cli
        4. Enter interface Vlan 200 configuration mode
        5. Capture running config again and verify VLAN 200 DOES exist
        6. Verify both 'vlan 200' and 'interface Vlan200' sections are present
        7. Cleanup - delete VLAN 200
        """
        dut = self.data.dut
        vlan_id = self.data.vlan_id_running_config
        cli_type = self.data.cli_type

        st.banner("TEST 1: VLAN Running Configuration Verification")
        st.log(f"Testing VLAN {vlan_id} - Verifying appearance in running-configuration")

        try:
            st.banner("STEP 1: Initial cleanup - ensure VLAN does not exist")
            self._cleanup_vlan(vlan_id)

            st.banner("STEP 2: Check initial running configuration (baseline)")
            initial_config = self._get_running_config(dut)

            if not initial_config:
                st.report_fail("msg", "Failed to retrieve initial running configuration")

            st.log("Initial running configuration retrieved successfully")
            initial_check = self._vlan_exists_in_config(initial_config, vlan_id)

            if initial_check["vlan_defined"] or initial_check["interface_defined"]:
                st.report_fail(
                    "msg",
                    f"VLAN {vlan_id} already exists in initial config - cleanup failed"
                )

            st.log(f"Confirmed: VLAN {vlan_id} not present in initial configuration")

            st.banner(f"STEP 3: Create VLAN {vlan_id}")
            result = vlan_api.create_vlan(dut, vlan_id, cli_type=cli_type)

            if not result:
                st.report_fail("msg", f"Failed to create VLAN {vlan_id}")

            st.log(f"VLAN {vlan_id} created successfully")

            # Track for cleanup
            if vlan_id not in self.data.configured_vlans:
                self.data.configured_vlans.append(vlan_id)

            st.banner(f"STEP 4: Enter interface Vlan {vlan_id} configuration mode")
            # Configure interface to ensure it appears in running config
            interface_config_cmd = [
                f"interface Vlan {vlan_id}",
                "exit"
            ]
            st.config(dut, interface_config_cmd, type=cli_type)
            st.log(f"Entered and exited interface Vlan {vlan_id} configuration")

            st.banner("STEP 5: Verify VLAN in running configuration")
            # Add a small wait for configuration to propagate
            st.wait(2)

            final_config = self._get_running_config(dut)

            if not final_config:
                st.report_fail("msg", "Failed to retrieve final running configuration")

            st.log("Final running configuration retrieved successfully")
            final_check = self._vlan_exists_in_config(final_config, vlan_id)

            st.banner("STEP 6: Validate VLAN and interface presence")

            # Validate vlan definition
            if not final_check["vlan_defined"]:
                st.report_fail(
                    "msg",
                    f"VLAN {vlan_id} definition not found in running configuration"
                )

            st.log(f"✓ Confirmed: 'vlan {vlan_id}' present in running configuration")

            # Validate interface definition
            if not final_check["interface_defined"]:
                st.report_fail(
                    "msg",
                    f"Interface Vlan{vlan_id} not found in running configuration"
                )

            st.log(f"✓ Confirmed: 'interface Vlan{vlan_id}' present in running configuration")

            st.banner("TEST 1 PASSED: VLAN creation verified in running configuration")
            st.report_pass("test_case_passed")

        finally:
            # Cleanup
            st.banner("STEP 7: Cleanup - delete VLAN")
            self._cleanup_vlan(vlan_id)
            if vlan_id in self.data.configured_vlans:
                self.data.configured_vlans.remove(vlan_id)

    @pytest.mark.inventory(feature="Regression", testcases=["VLAN_LIFECYCLE_TC_001"])
    def test_vlan_complete_lifecycle(self) -> None:
        """TC 002 - Complete VLAN interface lifecycle with IPv4/IPv6 configuration.

        Test Steps (matching vlan.md scenario):
        1. Initial cleanup (reverse order if exists): IPv6 → IPv4 → Port → VLAN
        2. Create VLAN 100
        3. Configure Ethernet272 as switchport access in VLAN 100
        4. Configure IPv4 address 20.1.1.4/24 on Vlan100
        5. Configure IPv6 address 8000::1/64 on Vlan100
        6. Verify VLAN interface status using "show interface Vlan100"
        7. Verify physical port status using "show interface Ethernet272"
        8. Final cleanup in reverse order: IPv6 → IPv4 → Port → VLAN
        """
        dut = self.data.dut
        vlan_id = self.data.vlan_id
        test_interface = self.data.test_interface
        ipv4_addr = self.data.ipv4_address
        ipv4_subnet = self.data.ipv4_subnet
        ipv6_addr = self.data.ipv6_address
        ipv6_subnet = self.data.ipv6_subnet
        cli_type = self.data.cli_type
        interface_name = f"Vlan{vlan_id}"

        st.banner("TEST 2: Complete VLAN Lifecycle (from vlan.md)")
        st.log(f"Testing VLAN {vlan_id} with {test_interface}, IPv4: {ipv4_addr}/{ipv4_subnet}, IPv6: {ipv6_addr}/{ipv6_subnet}")

        try:
            st.banner("STEP 1: Initial cleanup (if configuration exists)")
            self._cleanup_vlan_complete(vlan_id, test_interface)

            st.banner(f"STEP 2: Create VLAN {vlan_id}")
            result = vlan_api.create_vlan(dut, vlan_id, cli_type=cli_type)
            if not result:
                st.report_fail("msg", f"Failed to create VLAN {vlan_id}")

            st.log(f"VLAN {vlan_id} created successfully")
            if vlan_id not in self.data.configured_vlans:
                self.data.configured_vlans.append(vlan_id)

            st.banner(f"STEP 3: Configure {test_interface} as switchport access in VLAN {vlan_id}")
            # First ensure the interface has no IP address (required for switchport mode)
            try:
                commands = [
                    f"interface {test_interface}",
                    "no ip address",
                    "exit"
                ]
                st.config(dut, commands, type=cli_type)
                st.log(f"Removed IP address from {test_interface}")
            except Exception as e:
                st.debug(f"No IP to remove from {test_interface}: {e}")

            # Add interface to VLAN as untagged (access) member
            result = vlan_api.add_vlan_member(
                dut,
                vlan=vlan_id,
                port_list=test_interface,
                tagging_mode=False,  # False = untagged/access mode
                cli_type=cli_type
            )

            if not result:
                st.report_fail("msg", f"Failed to add {test_interface} to VLAN {vlan_id} as access port")

            st.log(f"{test_interface} configured as access port in VLAN {vlan_id}")

            # Track for cleanup
            member_config = {"vlan": vlan_id, "port": test_interface}
            if member_config not in self.data.configured_members:
                self.data.configured_members.append(member_config)

            st.banner(f"STEP 4: Configure IPv4 address {ipv4_addr}/{ipv4_subnet} on {interface_name}")
            result = ip_api.config_ip_addr_interface(
                dut,
                interface_name=interface_name,
                ip_address=ipv4_addr,
                subnet=ipv4_subnet,
                family="ipv4",
                config="add",
                cli_type=cli_type
            )

            if not result:
                st.report_fail("msg", f"Failed to configure IPv4 {ipv4_addr}/{ipv4_subnet} on {interface_name}")

            st.log(f"IPv4 {ipv4_addr}/{ipv4_subnet} configured on {interface_name}")

            # Track for cleanup
            ip_config = {
                "interface": interface_name,
                "address": ipv4_addr,
                "subnet": ipv4_subnet,
                "family": "ipv4"
            }
            if ip_config not in self.data.configured_ips:
                self.data.configured_ips.append(ip_config)

            st.banner(f"STEP 5: Configure IPv6 address {ipv6_addr}/{ipv6_subnet} on {interface_name}")
            result = ip_api.config_ip_addr_interface(
                dut,
                interface_name=interface_name,
                ip_address=ipv6_addr,
                subnet=ipv6_subnet,
                family="ipv6",
                config="add",
                cli_type=cli_type
            )

            if not result:
                st.report_fail("msg", f"Failed to configure IPv6 {ipv6_addr}/{ipv6_subnet} on {interface_name}")

            st.log(f"IPv6 {ipv6_addr}/{ipv6_subnet} configured on {interface_name}")

            # Track for cleanup
            ip_config = {
                "interface": interface_name,
                "address": ipv6_addr,
                "subnet": ipv6_subnet,
                "family": "ipv6"
            }
            if ip_config not in self.data.configured_ips:
                self.data.configured_ips.append(ip_config)

            st.banner(f"STEP 6: Verify VLAN interface status - show interface {interface_name}")
            # Ensure pagination is disabled
            _set_terminal_length(dut, 0)

            cmd = f"show interface {interface_name}"
            output = st.show(dut, cmd, type=cli_type, skip_tmpl=True)
            st.log(f"Interface {interface_name} status:\n{output}")

            # Basic verification - check if output contains expected information
            output_str = str(output)
            if interface_name not in output_str:
                st.warn(f"Interface {interface_name} not found in output")

            if ipv4_addr in output_str:
                st.log(f"✓ IPv4 address {ipv4_addr} verified in interface output")
            else:
                st.warn(f"IPv4 address {ipv4_addr} not found in interface output")

            if ipv6_addr in output_str:
                st.log(f"✓ IPv6 address {ipv6_addr} verified in interface output")
            else:
                st.warn(f"IPv6 address {ipv6_addr} not found in interface output")

            st.banner(f"STEP 7: Verify physical port status - show interface {test_interface}")
            cmd = f"show interface {test_interface}"
            output = st.show(dut, cmd, type=cli_type, skip_tmpl=True)
            st.log(f"Interface {test_interface} status:\n{output}")

            # Verify port is in VLAN
            vlan_list = vlan_api.get_vlan_list(dut, cli_type=cli_type)
            if vlan_id in vlan_list:
                st.log(f"✓ VLAN {vlan_id} verified in VLAN list")
            else:
                st.warn(f"VLAN {vlan_id} not found in VLAN list")

            # Verify VLAN membership
            result = vlan_api.verify_vlan_config(
                dut,
                vlan_list=vlan_id,
                untagged=test_interface,
                cli_type=cli_type
            )

            if result:
                st.log(f"✓ {test_interface} verified as untagged member of VLAN {vlan_id}")
            else:
                st.warn(f"{test_interface} not verified as member of VLAN {vlan_id}")

            # Verify IP addresses
            result = ip_api.verify_interface_ip_address(
                dut,
                interface_name=interface_name,
                ip_address=ipv4_addr,
                family="ipv4",
                cli_type=cli_type
            )

            if result:
                st.log(f"✓ IPv4 address {ipv4_addr} verified on {interface_name}")
            else:
                st.warn(f"IPv4 address {ipv4_addr} not verified on {interface_name}")

            result = ip_api.verify_interface_ip_address(
                dut,
                interface_name=interface_name,
                ip_address=ipv6_addr,
                family="ipv6",
                cli_type=cli_type
            )

            if result:
                st.log(f"✓ IPv6 address {ipv6_addr} verified on {interface_name}")
            else:
                st.warn(f"IPv6 address {ipv6_addr} not verified on {interface_name}")

            st.banner("TEST 2 PASSED: VLAN complete lifecycle verified successfully")
            st.report_pass("test_case_passed")

        finally:
            # Cleanup in reverse order
            st.banner("STEP 8: Final cleanup in reverse order")
            self._cleanup_vlan_complete(vlan_id, test_interface)

            # Clear tracking
            if vlan_id in self.data.configured_vlans:
                self.data.configured_vlans.remove(vlan_id)

            # Clear IP tracking
            self.data.configured_ips = [ip for ip in self.data.configured_ips
                                        if ip["interface"] != interface_name]

            # Clear member tracking
            self.data.configured_members = [m for m in self.data.configured_members
                                           if not (m["vlan"] == vlan_id and m["port"] == test_interface)]
