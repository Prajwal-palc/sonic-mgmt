"""
OSPF NETWORK COMMAND REMOVAL VALIDATION
Author: Shiva
2026

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/ztp_standalone.yaml \\
  tests/routing/ospf/test_ospf_network_removal.py \\
  --logs-path ./logs/ospf_network_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Comprehensive validation of OSPF network statement removal behavior to ensure
  proper selective deletion without unintended side effects. This test suite
  addresses critical bugs where removing a single network statement incorrectly
  deletes ALL network statements or corrupts other OSPF configuration.

  Test Coverage:
  1. Selective Removal - Verify only specified network is removed
  2. Non-Existent Removal - Invalid commands don't mutate configuration
  3. Area-Specific Removal - Same prefix in different areas handled correctly
  4. Attribute Preservation - Other OSPF settings remain intact

  Validation Strategy:
  - Evidence-based testing with before/after configuration comparison
  - Detailed parsing of running configuration
  - Verification of network statement uniqueness (prefix, area) tuple
  - Preservation checks for passive-interface settings

Pre-requisites:
  - Topology: Single DUT (D1) | Supported: HW and Virtual
  - Topology Diagram:
        +--------------------+
        |    smic_sonic1     |
        | (192.168.100.134)  |
        |   OSPF Router      |
        +--------------------+

  - CLI Access: klish (SONiC IS-CLI)
  - Required test variables (YAML): vars/routing/ospf/vars_ospf_network_removal.yaml
  - CRITICAL: Terminal length 0 set to prevent pagination during show commands

Test Scenarios:
  TC1: Multiple Network Removal - Selective Deletion
       - Configure 3 networks, remove 1, verify 2 remain

  TC2: Remove Non-Existent Network Statement
       - Attempt invalid removal, verify no configuration change

  TC3: Same Prefix Different Areas
       - Verify (prefix, area) tuple uniqueness is respected

  TC4: Concurrent Attributes Preservation
       - Verify passive-interface survives network removal

Known Issues Tested:
  - Bug: Removing one network deletes all networks
  - Bug: Same prefix removal deletes all areas
  - Bug: Network removal corrupts other OSPF settings
"""

# Testcases for OSPF network command removal validation

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.ospf as ospf_api

# Module-level constants
VAR_FILE_ENV = "OSPF_NETWORK_REMOVAL_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "routing"
    / "ospf"
    / "vars_ospf_network_removal.yaml"
)

# Test case IDs for inventory tracking
TC_IDS = SpyTestDict({
    "selective_removal": "OSPF-NETWORK-REMOVAL-TC1",
    "nonexistent_removal": "OSPF-NETWORK-REMOVAL-TC2",
    "same_prefix_different_area": "OSPF-NETWORK-REMOVAL-TC3",
    "attributes_preservation": "OSPF-NETWORK-REMOVAL-TC4",
})


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"OSPF network removal variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("OSPF network removal YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestOspfNetworkRemoval:
    """
    Test suite for OSPF network command removal validation.

    Validates that OSPF network statement removal operates correctly:
    - Selective deletion (only specified network removed)
    - No bulk deletion bugs
    - Area-specific removal accuracy
    - Preservation of other OSPF configuration
    """

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup test suite: Load config and disable pagination."""
        st.banner("OSPF NETWORK REMOVAL TEST SUITE - Starting")

        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        min_topology = defaults.get("min_topology") or ["D1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.dut = topology.D1
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.config_wait_time = int(defaults.get("config_wait_time", 2))

        st.log(f"Test DUT: {cls.data.dut}")
        st.log(f"CLI Type: {cls.data.cli_type}")
        st.log(f"Config Wait Time: {cls.data.config_wait_time} seconds")

        # CRITICAL: Disable pagination before any show running-configuration commands
        cls._set_terminal_length(cls.data.dut, 0)
        st.log("✓ Terminal pagination disabled for all show commands")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup after test suite completion."""
        st.banner("TEARDOWN CLASS: OSPF Network Removal Tests")

        # Ensure all OSPF configuration is removed
        cls._cleanup_all_ospf(cls.data.dut)
        st.log("✓ OSPF configuration cleaned up")

    def setup_method(self) -> None:
        """Setup before each test: Ensure clean OSPF state."""
        st.banner(f"SETUP METHOD: Cleaning OSPF configuration")

        # Remove any existing OSPF configuration
        self._cleanup_all_ospf(self.data.dut)

        # Verify clean state
        time.sleep(1)
        config = self._get_ospf_running_config(self.data.dut)

        if "router ospf" in config:
            st.warn("OSPF configuration still present after cleanup, forcing removal")
            self._cleanup_all_ospf(self.data.dut)

        st.log("✓ Clean OSPF state confirmed")

    def teardown_method(self) -> None:
        """Cleanup after each test."""
        st.banner("TEARDOWN METHOD: Cleaning up OSPF configuration")
        self._cleanup_all_ospf(self.data.dut)

    @classmethod
    def _set_terminal_length(cls, dut: str, length: int = 0) -> None:
        """
        Set terminal length to control pagination in show commands.

        CRITICAL FOR RUNNING-CONFIG COMMANDS:
        Without this, 'show running-configuration' will pause at --More--
        prompts, causing tests to hang indefinitely.

        Args:
            dut: Device under test
            length: Terminal length (0 = no pagination, disable --More--)
        """
        try:
            cmd = f"terminal length {length}"
            st.config(
                dut,
                cmd,
                type="klish",
                conf=False,
                skip_error_check=True
            )
            st.log(f"✓ Set terminal length to {length} on {dut} (pagination disabled)")
        except Exception as e:
            st.error(f"✗ Failed to set terminal length: {e}")
            st.warn("WARNING: Tests may hang on --More-- prompts!")

    def _get_ospf_running_config(self, dut: str) -> str:
        """
        Get OSPF running configuration with proper safeguards.

        Returns:
            OSPF configuration as string
        """
        # Ensure terminal length is set (idempotent)
        self._set_terminal_length(dut, 0)

        # Execute show command
        cmd = "show running-configuration | find ospf"
        output = st.show(
            dut,
            cmd,
            type=self.data.cli_type,
            skip_tmpl=True,
            skip_error_check=True
        )

        # Normalize output
        output_str = str(output) if output else ""

        # Check for pagination artifacts
        if "--More--" in output_str:
            st.error("CRITICAL: Pagination detected! Terminal length not working")
            st.report_fail("msg", "Pagination artifacts found in output - terminal length issue")

        st.log(f"OSPF Running Config ({len(output_str)} chars):\n{output_str}")

        return output_str

    @staticmethod
    def _normalize_area(area_str: str) -> int:
        """
        Normalize OSPF area from dotted-decimal or integer format to integer.

        OSPF areas can be represented in two formats:
        - Integer format: 0, 1, 10, etc.
        - Dotted-decimal format: 0.0.0.0, 0.0.0.1, 0.0.0.10, etc.

        The show command outputs dotted-decimal format (e.g., area 0.0.0.0),
        while configuration accepts integer format (e.g., area 0).

        Conversion formula for a.b.c.d:
            area_number = (a * 16777216) + (b * 65536) + (c * 256) + d

        Args:
            area_str: Area in either format ("0", "1", "0.0.0.0", "0.0.0.1")

        Returns:
            Integer area number

        Examples:
            "0" → 0
            "1" → 1
            "0.0.0.0" → 0
            "0.0.0.1" → 1
            "0.0.0.10" → 10
            "0.0.1.0" → 256
        """
        area_str = str(area_str).strip()

        # Check if dotted-decimal format (contains dots)
        if '.' in area_str:
            # Parse dotted-decimal: a.b.c.d
            parts = area_str.split('.')
            if len(parts) == 4:
                try:
                    a, b, c, d = [int(p) for p in parts]
                    area_int = (a * 16777216) + (b * 65536) + (c * 256) + d
                    st.debug(f"Area conversion: {area_str} (dotted) → {area_int} (integer)")
                    return area_int
                except (ValueError, TypeError):
                    st.error(f"Invalid dotted-decimal area format: {area_str}")
                    return 0
            else:
                st.error(f"Invalid dotted-decimal area format (expected 4 octets): {area_str}")
                return 0
        else:
            # Integer format
            try:
                area_int = int(area_str)
                st.debug(f"Area conversion: {area_str} (integer) → {area_int}")
                return area_int
            except (ValueError, TypeError):
                st.error(f"Invalid area format: {area_str}")
                return 0

    def _parse_ospf_networks(self, output: str) -> List[Dict[str, Any]]:
        """
        Parse OSPF network statements from running config.

        Handles both area formats:
        - Configuration format: "network 10.0.0.0/24 area 0"
        - Show output format: "network 10.0.0.0/24 area 0.0.0.0"

        Args:
            output: Running configuration output

        Returns:
            List of {prefix, area} dictionaries with normalized area numbers
        """
        networks = []

        # Clean output - remove prompts
        output = output.replace("sonic#", "").replace("sonic(config)#", "")
        output = output.replace("sonic(config-router)#", "")

        # Parse line by line
        for line in output.split('\n'):
            line = line.strip()

            # Skip empty, comments, section headers
            if not line or line.startswith('!') or line == "router ospf":
                continue

            # Match: " network 10.0.0.0/24 area 0" OR " network 10.0.0.0/24 area 0.0.0.0"
            # Updated regex to handle both integer and dotted-decimal area formats
            network_pattern = r'network\s+(\S+)\s+area\s+([\d\.]+)'
            match = re.search(network_pattern, line, re.IGNORECASE)

            if match:
                prefix = match.group(1)
                area_str = match.group(2)

                # Normalize area to integer format
                area_int = self._normalize_area(area_str)

                network_entry = {
                    'prefix': prefix,
                    'area': area_int
                }
                networks.append(network_entry)
                st.log(f"  Parsed network: {prefix} area {area_int} (from '{area_str}')")

        return networks

    def _verify_network_present(self, config: str, prefix: str, area: int) -> bool:
        """
        Verify that a specific network statement is present in config.

        Args:
            config: OSPF running configuration
            prefix: Network prefix (e.g., "10.0.0.0/24")
            area: OSPF area number

        Returns:
            True if network found, False otherwise
        """
        networks = self._parse_ospf_networks(config)

        for network in networks:
            if network['prefix'] == prefix and network['area'] == area:
                st.log(f"✓ Network {prefix} area {area} - PRESENT")
                return True

        st.log(f"✗ Network {prefix} area {area} - ABSENT")
        return False

    def _verify_network_absent(self, config: str, prefix: str, area: int) -> bool:
        """
        Verify that a specific network statement is NOT present in config.

        Args:
            config: OSPF running configuration
            prefix: Network prefix
            area: OSPF area number

        Returns:
            True if network NOT found, False if it exists
        """
        return not self._verify_network_present(config, prefix, area)

    def _configure_ospf_networks(self, networks: List[Dict[str, Any]]) -> bool:
        """
        Configure OSPF with specified network statements.

        Args:
            networks: List of {prefix, area} dictionaries

        Returns:
            True if successful, False otherwise
        """
        commands = ["configure terminal", "router ospf"]

        for network in networks:
            prefix = network['prefix']
            area = network['area']
            commands.append(f"network {prefix} area {area}")

        commands.append("end")

        st.log(f"Configuring OSPF with {len(networks)} networks")
        success, details = ospf_api.apply_cli_sequence(
            self.data.dut,
            commands,
            cli_type=self.data.cli_type
        )

        if not success:
            st.error(f"Failed to configure OSPF: {details}")
            return False

        # Wait for configuration to propagate
        time.sleep(self.data.config_wait_time)

        st.log(f"✓ OSPF configured with {len(networks)} networks")
        return True

    def _configure_ospf_with_attributes(
        self,
        networks: List[Dict[str, Any]],
        router_id: Optional[str] = None,
        passive_interface_name: Optional[str] = None
    ) -> bool:
        """
        Configure OSPF with networks and additional attributes.

        Args:
            networks: List of {prefix, area} dictionaries
            router_id: OSPF router ID (optional)
            passive_interface_name: Interface name for passive-interface (e.g., "Ethernet0")

        Returns:
            True if successful, False otherwise
        """
        commands = ["configure terminal", "router ospf"]

        # Add router-id if specified
        if router_id:
            commands.append(f"router-id {router_id}")
            st.log(f"  Setting router-id: {router_id}")

        # Add passive-interface for specific interface if specified
        if passive_interface_name:
            commands.append(f"passive-interface {passive_interface_name}")
            st.log(f"  Setting passive-interface: {passive_interface_name}")

        # Add network statements
        for network in networks:
            prefix = network['prefix']
            area = network['area']
            commands.append(f"network {prefix} area {area}")

        commands.append("end")

        st.log(f"Configuring OSPF with attributes and {len(networks)} networks")
        success, details = ospf_api.apply_cli_sequence(
            self.data.dut,
            commands,
            cli_type=self.data.cli_type
        )

        if not success:
            st.error(f"Failed to configure OSPF: {details}")
            return False

        # Wait for configuration to propagate
        time.sleep(self.data.config_wait_time)

        st.log(f"✓ OSPF configured with attributes and {len(networks)} networks")
        return True

    def _remove_ospf_network(self, prefix: str, area: int) -> bool:
        """
        Remove a specific OSPF network statement.

        Args:
            prefix: Network prefix
            area: OSPF area number

        Returns:
            True if command executed, False on error
        """
        commands = [
            "configure terminal",
            "router ospf",
            f"no network {prefix} area {area}",
            "end"
        ]

        st.log(f"Removing OSPF network: {prefix} area {area}")
        success, details = ospf_api.apply_cli_sequence(
            self.data.dut,
            commands,
            cli_type=self.data.cli_type,
            skip_error_check=True  # Allow for non-existent network removal
        )

        # Wait for configuration to propagate
        time.sleep(self.data.config_wait_time)

        if not success:
            st.log(f"Network removal command had issues: {details}")

        return success

    @classmethod
    def _cleanup_all_ospf(cls, dut: str) -> None:
        """
        Remove all OSPF configuration.

        Args:
            dut: Device under test
        """
        commands = [
            "configure terminal",
            "no router ospf",
            "end"
        ]

        st.log("Removing all OSPF configuration")
        ospf_api.apply_cli_sequence(
            dut,
            commands,
            cli_type="klish",
            skip_error_check=True
        )

        time.sleep(2)

    # ==========================================================================
    # Test Case 1: Multiple Network Removal - Selective Deletion
    # ==========================================================================
    @pytest.mark.inventory(feature="OSPF", testcases=[TC_IDS.selective_removal])
    def test_ospf_network_selective_removal(self) -> None:
        """
        TC 1 - Multiple Network Removal - Selective Deletion.

        Objective:
            Verify that removing one network statement from multiple networks
            only removes the specified network, leaving others intact.

        Bug Tested:
            Removing one network deletes ALL network statements

        Test Flow:
            1. Configure OSPF with 3 networks
            2. Capture BEFORE configuration
            3. Remove middle network (20.0.0.0/24 area 0)
            4. Capture AFTER configuration
            5. Verify only specified network removed
            6. Verify other 2 networks still present
        """
        st.banner("TEST CASE 1: Multiple Network Removal - Selective Deletion")

        testcase = self.data.testcases.get("selective_removal", {})

        # Get test data
        networks = testcase.get("networks", [
            {'prefix': '10.0.0.0/24', 'area': 0},
            {'prefix': '20.0.0.0/24', 'area': 0},
            {'prefix': '30.0.0.0/24', 'area': 1},
        ])

        remove_network = testcase.get("remove", {'prefix': '20.0.0.0/24', 'area': 0})
        expected_present = testcase.get("expected_present", [
            {'prefix': '10.0.0.0/24', 'area': 0},
            {'prefix': '30.0.0.0/24', 'area': 1},
        ])
        expected_absent = testcase.get("expected_absent", [
            {'prefix': '20.0.0.0/24', 'area': 0},
        ])

        # STEP 1: Configure OSPF with multiple networks
        st.log("=" * 80)
        st.log("STEP 1: Configure OSPF with 3 networks")
        st.log("=" * 80)

        if not self._configure_ospf_networks(networks):
            st.report_fail("msg", "Failed to configure OSPF with networks")

        # STEP 2: Capture BEFORE configuration
        st.log("=" * 80)
        st.log("STEP 2: Capture BEFORE configuration")
        st.log("=" * 80)

        config_before = self._get_ospf_running_config(self.data.dut)
        networks_before = self._parse_ospf_networks(config_before)

        st.log(f"BEFORE: {len(networks_before)} networks configured")
        for network in networks_before:
            st.log(f"  - {network['prefix']} area {network['area']}")

        if len(networks_before) != 3:
            st.report_fail("msg", f"Expected 3 networks before removal, found {len(networks_before)}")

        # STEP 3: Remove one network
        st.log("=" * 80)
        st.log(f"STEP 3: Remove network {remove_network['prefix']} area {remove_network['area']}")
        st.log("=" * 80)

        self._remove_ospf_network(remove_network['prefix'], remove_network['area'])

        # STEP 4: Capture AFTER configuration
        st.log("=" * 80)
        st.log("STEP 4: Capture AFTER configuration")
        st.log("=" * 80)

        config_after = self._get_ospf_running_config(self.data.dut)
        networks_after = self._parse_ospf_networks(config_after)

        st.log(f"AFTER: {len(networks_after)} networks configured")
        for network in networks_after:
            st.log(f"  - {network['prefix']} area {network['area']}")

        # STEP 5: Validate expected networks present
        st.log("=" * 80)
        st.log("STEP 5: Validate expected networks PRESENT")
        st.log("=" * 80)

        for network in expected_present:
            if not self._verify_network_present(config_after, network['prefix'], network['area']):
                st.report_fail(
                    "msg",
                    f"Expected network {network['prefix']} area {network['area']} is MISSING"
                )

        # STEP 6: Validate removed network absent
        st.log("=" * 80)
        st.log("STEP 6: Validate removed network ABSENT")
        st.log("=" * 80)

        for network in expected_absent:
            if not self._verify_network_absent(config_after, network['prefix'], network['area']):
                st.report_fail(
                    "msg",
                    f"Network {network['prefix']} area {network['area']} should be REMOVED but is still PRESENT"
                )

        # Final validation
        if len(networks_after) != 2:
            st.report_fail(
                "msg",
                f"BUG DETECTED: Expected 2 networks after removal, found {len(networks_after)}"
            )

        st.banner("✓ TEST PASSED - Selective Network Removal")
        st.log(f"✓ Started with {len(networks_before)} networks")
        st.log(f"✓ Removed 1 network ({remove_network['prefix']} area {remove_network['area']})")
        st.log(f"✓ {len(networks_after)} networks remain (as expected)")
        st.report_pass("test_case_passed")

    # ==========================================================================
    # Test Case 2: Remove Non-Existent Network Statement
    # ==========================================================================
    @pytest.mark.inventory(feature="OSPF", testcases=[TC_IDS.nonexistent_removal])
    @pytest.mark.negative
    def test_ospf_network_remove_nonexistent(self) -> None:
        """
        TC 2 - Remove Non-Existent Network Statement.

        Objective:
            Verify that attempting to remove a non-existent network statement
            does NOT mutate the existing configuration.

        Bug Tested:
            Invalid removal commands corrupt or delete valid configuration

        Test Flow:
            1. Configure OSPF with 1 network
            2. Capture BEFORE configuration
            3. Attempt to remove non-existent network
            4. Capture AFTER configuration
            5. Verify original network still present
            6. Verify no configuration changes occurred
        """
        st.banner("TEST CASE 2: Remove Non-Existent Network Statement")

        testcase = self.data.testcases.get("nonexistent_removal", {})

        # Get test data
        networks = testcase.get("networks", [
            {'prefix': '10.0.0.0/24', 'area': 0},
        ])

        remove_network = testcase.get("remove", {'prefix': '20.0.0.0/24', 'area': 0})
        expected_present = testcase.get("expected_present", [
            {'prefix': '10.0.0.0/24', 'area': 0},
        ])

        # STEP 1: Configure OSPF
        st.log("=" * 80)
        st.log("STEP 1: Configure OSPF with 1 network")
        st.log("=" * 80)

        if not self._configure_ospf_networks(networks):
            st.report_fail("msg", "Failed to configure OSPF")

        # STEP 2: Capture BEFORE configuration
        st.log("=" * 80)
        st.log("STEP 2: Capture BEFORE configuration")
        st.log("=" * 80)

        config_before = self._get_ospf_running_config(self.data.dut)
        networks_before = self._parse_ospf_networks(config_before)

        st.log(f"BEFORE: {len(networks_before)} network(s) configured")

        # STEP 3: Attempt to remove non-existent network
        st.log("=" * 80)
        st.log(f"STEP 3: Attempt to remove NON-EXISTENT network {remove_network['prefix']} area {remove_network['area']}")
        st.log("=" * 80)

        self._remove_ospf_network(remove_network['prefix'], remove_network['area'])

        # STEP 4: Capture AFTER configuration
        st.log("=" * 80)
        st.log("STEP 4: Capture AFTER configuration")
        st.log("=" * 80)

        config_after = self._get_ospf_running_config(self.data.dut)
        networks_after = self._parse_ospf_networks(config_after)

        st.log(f"AFTER: {len(networks_after)} network(s) configured")

        # STEP 5: Validate no change occurred
        st.log("=" * 80)
        st.log("STEP 5: Validate NO CHANGE occurred")
        st.log("=" * 80)

        # Verify original network still present
        for network in expected_present:
            if not self._verify_network_present(config_after, network['prefix'], network['area']):
                st.report_fail(
                    "msg",
                    f"BUG: Original network {network['prefix']} area {network['area']} was DELETED by invalid removal"
                )

        # Verify count unchanged
        if len(networks_after) != len(networks_before):
            st.report_fail(
                "msg",
                f"BUG: Configuration changed by invalid removal (before: {len(networks_before)}, after: {len(networks_after)})"
            )

        st.banner("✓ TEST PASSED - Invalid Removal Had No Effect")
        st.log(f"✓ Configuration unchanged")
        st.log(f"✓ Original network preserved")
        st.report_pass("test_case_passed")

    # ==========================================================================
    # Test Case 3: Same Prefix Different Areas
    # ==========================================================================
    @pytest.mark.inventory(feature="OSPF", testcases=[TC_IDS.same_prefix_different_area])
    def test_ospf_network_same_prefix_different_area(self) -> None:
        """
        TC 3 - Same Prefix Different Areas.

        Objective:
            Verify that the (prefix, area) tuple is treated as a unique key,
            and removing one area doesn't affect the same prefix in another area.

        Bug Tested:
            Removing prefix from one area deletes all areas for that prefix

        Test Flow:
            1. Configure same prefix in 2 different areas
            2. Capture BEFORE configuration
            3. Remove prefix from area 0
            4. Capture AFTER configuration
            5. Verify area 0 entry removed
            6. Verify area 1 entry still present
        """
        st.banner("TEST CASE 3: Same Prefix Different Areas")

        testcase = self.data.testcases.get("same_prefix_different_area", {})

        # Get test data
        networks = testcase.get("networks", [
            {'prefix': '10.0.0.0/24', 'area': 0},
            {'prefix': '10.0.0.0/24', 'area': 1},
        ])

        remove_network = testcase.get("remove", {'prefix': '10.0.0.0/24', 'area': 0})
        expected_present = testcase.get("expected_present", [
            {'prefix': '10.0.0.0/24', 'area': 1},
        ])
        expected_absent = testcase.get("expected_absent", [
            {'prefix': '10.0.0.0/24', 'area': 0},
        ])

        # STEP 1: Configure same prefix in different areas
        st.log("=" * 80)
        st.log("STEP 1: Configure same prefix (10.0.0.0/24) in 2 different areas")
        st.log("=" * 80)

        if not self._configure_ospf_networks(networks):
            st.report_fail("msg", "Failed to configure OSPF")

        # STEP 2: Capture BEFORE configuration
        st.log("=" * 80)
        st.log("STEP 2: Capture BEFORE configuration")
        st.log("=" * 80)

        config_before = self._get_ospf_running_config(self.data.dut)
        networks_before = self._parse_ospf_networks(config_before)

        st.log(f"BEFORE: {len(networks_before)} network entries")
        for network in networks_before:
            st.log(f"  - {network['prefix']} area {network['area']}")

        if len(networks_before) != 2:
            st.report_fail("msg", f"Expected 2 network entries, found {len(networks_before)}")

        # STEP 3: Remove prefix from area 0
        st.log("=" * 80)
        st.log(f"STEP 3: Remove {remove_network['prefix']} from area {remove_network['area']} ONLY")
        st.log("=" * 80)

        self._remove_ospf_network(remove_network['prefix'], remove_network['area'])

        # STEP 4: Capture AFTER configuration
        st.log("=" * 80)
        st.log("STEP 4: Capture AFTER configuration")
        st.log("=" * 80)

        config_after = self._get_ospf_running_config(self.data.dut)
        networks_after = self._parse_ospf_networks(config_after)

        st.log(f"AFTER: {len(networks_after)} network entries")
        for network in networks_after:
            st.log(f"  - {network['prefix']} area {network['area']}")

        # STEP 5: Validate area 1 entry still present
        st.log("=" * 80)
        st.log("STEP 5: Validate area 1 entry STILL PRESENT")
        st.log("=" * 80)

        for network in expected_present:
            if not self._verify_network_present(config_after, network['prefix'], network['area']):
                st.report_fail(
                    "msg",
                    f"BUG: {network['prefix']} area {network['area']} was INCORRECTLY DELETED"
                )

        # STEP 6: Validate area 0 entry removed
        st.log("=" * 80)
        st.log("STEP 6: Validate area 0 entry REMOVED")
        st.log("=" * 80)

        for network in expected_absent:
            if not self._verify_network_absent(config_after, network['prefix'], network['area']):
                st.report_fail(
                    "msg",
                    f"Network {network['prefix']} area {network['area']} should be REMOVED"
                )

        # Final validation
        if len(networks_after) != 1:
            st.report_fail(
                "msg",
                f"BUG: Expected 1 network after removal, found {len(networks_after)}"
            )

        st.banner("✓ TEST PASSED - Area-Specific Removal")
        st.log(f"✓ Same prefix configured in 2 areas")
        st.log(f"✓ Removed from area 0 only")
        st.log(f"✓ Area 1 entry preserved correctly")
        st.report_pass("test_case_passed")

    # ==========================================================================
    # Test Case 4: Concurrent Attributes Preservation
    # ==========================================================================
    @pytest.mark.inventory(feature="OSPF", testcases=[TC_IDS.attributes_preservation])
    def test_ospf_network_attributes_preservation(self) -> None:
        """
        TC 4 - Concurrent Attributes Preservation.

        Objective:
            Verify that removing a network statement does NOT corrupt or delete
            other OSPF configuration attributes like passive-interface.

        Bug Tested:
            Bulk deletion bugs that wipe unrelated OSPF fields

        Test Flow:
            1. Configure OSPF with passive-interface and 2 networks
            2. Capture BEFORE configuration
            3. Remove one network
            4. Capture AFTER configuration
            5. Verify passive-interface preserved
            6. Verify only specified network removed
        """
        st.banner("TEST CASE 4: Concurrent Attributes Preservation")

        testcase = self.data.testcases.get("attributes_preservation", {})

        # Get test data - use configurable interface name
        passive_interface_name = testcase.get("passive_interface_name", "Ethernet0")
        networks = testcase.get("networks", [
            {'prefix': '10.0.0.0/24', 'area': 0},
            {'prefix': '20.0.0.0/24', 'area': 0},
        ])

        remove_network = testcase.get("remove", {'prefix': '10.0.0.0/24', 'area': 0})
        expected_present = testcase.get("expected_present", [
            {'prefix': '20.0.0.0/24', 'area': 0},
        ])

        # STEP 1: Configure OSPF with attributes and networks
        st.log("=" * 80)
        st.log(f"STEP 1: Configure OSPF with passive-interface {passive_interface_name} and 2 networks")
        st.log("=" * 80)

        if not self._configure_ospf_with_attributes(
            networks,
            router_id=None,
            passive_interface_name=passive_interface_name
        ):
            st.report_fail("msg", "Failed to configure OSPF with attributes")

        # STEP 2: Capture BEFORE configuration
        st.log("=" * 80)
        st.log("STEP 2: Capture BEFORE configuration")
        st.log("=" * 80)

        config_before = self._get_ospf_running_config(self.data.dut)
        networks_before = self._parse_ospf_networks(config_before)

        st.log(f"BEFORE Configuration:")
        st.log(f"  Networks: {len(networks_before)}")
        st.log(f"  Passive-Interface: {passive_interface_name}")

        # Verify passive-interface present before
        if f"passive-interface {passive_interface_name}" not in config_before:
            st.report_fail("msg", f"Passive-interface {passive_interface_name} not found in initial configuration")

        # STEP 3: Remove one network
        st.log("=" * 80)
        st.log(f"STEP 3: Remove network {remove_network['prefix']} area {remove_network['area']}")
        st.log("=" * 80)

        self._remove_ospf_network(remove_network['prefix'], remove_network['area'])

        # STEP 4: Capture AFTER configuration
        st.log("=" * 80)
        st.log("STEP 4: Capture AFTER configuration")
        st.log("=" * 80)

        config_after = self._get_ospf_running_config(self.data.dut)
        networks_after = self._parse_ospf_networks(config_after)

        st.log(f"AFTER Configuration:")
        st.log(f"  Networks: {len(networks_after)}")

        # STEP 5: Verify passive-interface preserved
        st.log("=" * 80)
        st.log(f"STEP 5: Verify passive-interface {passive_interface_name} PRESERVED")
        st.log("=" * 80)

        if f"passive-interface {passive_interface_name}" not in config_after:
            st.report_fail(
                "msg",
                f"BUG: Passive-interface {passive_interface_name} was DELETED during network removal"
            )

        st.log(f"✓ Passive-interface {passive_interface_name} preserved")

        # STEP 6: Verify correct network removed
        st.log("=" * 80)
        st.log("STEP 6: Verify correct network REMOVED, other network PRESERVED")
        st.log("=" * 80)

        # Verify remaining network present
        for network in expected_present:
            if not self._verify_network_present(config_after, network['prefix'], network['area']):
                st.report_fail(
                    "msg",
                    f"Expected network {network['prefix']} area {network['area']} is MISSING"
                )

        # Verify removed network absent
        if not self._verify_network_absent(config_after, remove_network['prefix'], remove_network['area']):
            st.report_fail(
                "msg",
                f"Network {remove_network['prefix']} area {remove_network['area']} should be REMOVED"
            )

        # Final count check
        if len(networks_after) != 1:
            st.report_fail(
                "msg",
                f"BUG: Expected 1 network after removal, found {len(networks_after)}"
            )

        st.banner("✓ TEST PASSED - Attributes Preserved")
        st.log(f"✓ Passive-interface {passive_interface_name} preserved")
        st.log(f"✓ Only specified network removed")
        st.log(f"✓ Other network preserved")
        st.report_pass("test_case_passed")
