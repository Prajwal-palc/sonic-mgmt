"""
VLAN CONFIGURATION - VLAN CREATION AND PORT MANAGEMENT (HARDWARE - DYNAMIC TESTBED)
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs_hardware.yaml \
  tests/system/iscli_Hardware/test_interface_1_iscli_vlan_HW.py \
  --logs-path ./logs/test_interface_1_iscli_vlan_HW_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates VLAN creation and port management by:
  1. Dynamically getting the first interface from testbed
  2. Verifying baseline (no VLANs configured)
  3. Removing IP addresses (IPv4 and IPv6) from the first interface
  4. Creating VLAN 3
  5. Adding the first interface to VLAN 3 as tagged member
  6. Verifying VLAN 3 with the interface in show Vlan output
  7. Removing the interface from VLAN 3
  8. Verifying VLAN 3 with no ports in show Vlan output
  9. Deleting VLAN 3
  10. Verifying no VLANs configured

  This mirrors the exact CLI workflow:
    - show Vlan (baseline: No VLANs configured)
    - configure terminal -> interface Ethernet X -> no ip address -> no ipv6 address -> exit
    - configure terminal -> vlan 3 -> exit
    - show Vlan (verify: Vlan3 exists with no ports)
    - configure terminal -> interface Ethernet X -> switchport trunk allowed vlan 3 -> exit
    - show Vlan (verify: Vlan3 with Ethernet X)
    - configure terminal -> interface Ethernet X -> no switchport trunk allowed vlan 3 -> exit
    - show Vlan (verify: Vlan3 with no ports)
    - configure terminal -> no vlan 3 -> exit
    - show Vlan (verify: No VLANs configured)

  IMPORTANT: Uses 'show Vlan' command to validate VLAN creation and port membership.
  Uses only ONE exit command in each configuration block to stay in config mode.

  This hardware-focused version dynamically retrieves the FIRST device from the testbed
  and the FIRST interface from that device's topology links, making it portable across
  different testbed configurations without hardcoding interface names.

Pre-requisites:
  - Topology: 1-node minimum | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - Dynamic (uses first DUT and first interface from testbed)
        # +--------------------+
        # |       DUT1         |
        # | (First device)     |<-----First Interface from topology
        # |                    |      (Member of VLAN 3)
        # +--------------------+
  - Access to sonic-cli (klish mode)
  - Required test variables: CLI type (klish)
  - Minimum 1 interface available in testbed topology
"""

from __future__ import annotations

import pytest
import time
import re
from typing import Dict, Any, List, Optional

from spytest import st
from spytest.dicts import SpyTestDict


# CLI type for all operations
CLI_TYPE = "klish"

# Wait times
WAIT_AFTER_VLAN_CHANGE = 2


@pytest.mark.topology("any")
class TestVlanConfigurationHW:
    """Test cases for validating VLAN creation and port management via CLI (klish mode) on hardware."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters dynamically from testbed."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing VLAN Configuration Test Suite (Hardware)")
        st.log("=" * 80)

        # Get DUT handles - use FIRST device from testbed
        cls.data.dut_names = st.get_dut_names()
        if not cls.data.dut_names:
            st.report_fail("msg", "No DUTs available in topology")

        # Use FIRST device from testbed
        cls.data.dut1 = cls.data.dut_names[0]
        st.log(f"Primary DUT (First device from testbed): {cls.data.dut1}")

        # CLI type - use klish as specified
        cls.data.cli_type = CLI_TYPE
        st.log(f"CLI Type: {cls.data.cli_type}")

        # Test VLAN ID
        cls.data.test_vlan = "3"
        st.log(f"Test VLAN: {cls.data.test_vlan}")

        # Get FIRST interface from testbed topology dynamically
        cls.data.test_interface = cls._get_first_interface_from_testbed()
        st.log(f"Test Interface (First from testbed): {cls.data.test_interface}")

        st.log("Test setup complete")

    @classmethod
    def _get_first_interface_from_testbed(cls) -> str:
        """
        Dynamically retrieve the FIRST interface from the testbed topology.

        This method queries the testbed topology to find the first available
        interface on the primary DUT, making the test portable across different
        testbed configurations.

        Returns:
            str: First interface name (e.g., "Ethernet0")

        Raises:
            Failure if no interfaces found in testbed
        """
        try:
            # Method 1: Try to get DUT links (interfaces connected to other DUTs)
            dut_links = st.get_dut_links(cls.data.dut1)
            st.log(f"DUT links retrieved: {dut_links}")

            if dut_links and len(dut_links) > 0:
                # dut_links returns a list of links, each link is a list [local_port, remote_dut, remote_port]
                # We need to extract just the local port (first element)
                first_link = dut_links[0]

                # Handle different possible formats
                if isinstance(first_link, (list, tuple)) and len(first_link) > 0:
                    first_interface = str(first_link[0])  # Get local interface (first element)
                else:
                    first_interface = str(first_link)

                st.log(f"Found first interface from DUT links: {first_interface}")
                return first_interface

        except Exception as e:
            st.log(f"Note: Could not get DUT links: {str(e)}")

        try:
            # Method 2: Try to get all free ports
            free_ports = st.get_free_ports(cls.data.dut1)
            st.log(f"Free ports retrieved: {free_ports}")

            if free_ports and len(free_ports) > 0:
                first_interface = str(free_ports[0])
                st.log(f"Found first interface from free ports: {first_interface}")
                return first_interface

        except Exception as e:
            st.log(f"Note: Could not get free ports: {str(e)}")

        try:
            # Method 3: Try to get TG links (traffic generator links)
            tg_links = st.get_tg_links(cls.data.dut1)
            st.log(f"TG links retrieved: {tg_links}")

            if tg_links and len(tg_links) > 0:
                # Get the first TG link's DUT-side interface
                first_link = tg_links[0]
                # TG links are typically tuples/lists: (dut, interface)
                if isinstance(first_link, (list, tuple)) and len(first_link) >= 2:
                    first_interface = str(first_link[1])
                else:
                    first_interface = str(first_link)
                st.log(f"Found first interface from TG links: {first_interface}")
                return first_interface

        except Exception as e:
            st.log(f"Note: Could not get TG links: {str(e)}")

        # Fallback: If all methods fail, use default Ethernet0
        st.log("Warning: Could not dynamically retrieve interface from testbed")
        st.log("Falling back to default: Ethernet0")
        return "Ethernet0"

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup test suite - ensure VLAN is deleted."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Cleanup VLAN Configuration Test Suite")
        st.log("=" * 80)

        try:
            # Try to delete test VLAN if it exists
            cls._delete_vlan_static(cls.data.dut1, cls.data.test_vlan)
            st.log(f"Cleaned up VLAN {cls.data.test_vlan}")
        except Exception as e:
            st.log(f"Note: VLAN cleanup: {str(e)}")

        st.log("Cleanup completed")

    @classmethod
    def _delete_vlan_static(cls, dut: str, vlan_id: str) -> None:
        """
        Static helper to delete VLAN during teardown.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "3")
        """
        try:
            commands = [
                "configure terminal",
                f"no vlan {vlan_id}"
            ]
            st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)
            time.sleep(1)
        except Exception as e:
            st.log(f"Warning: Failed to delete VLAN {vlan_id}: {str(e)}")

    def setup_method(self) -> None:
        """Setup before each test method."""
        st.log("-" * 80)
        st.log("SETUP METHOD: Starting new test case")
        st.log("-" * 80)

    def teardown_method(self) -> None:
        """Teardown after each test method - ensure VLAN is deleted."""
        st.log("-" * 80)
        st.log("TEARDOWN METHOD: Cleaning up test case")
        st.log("-" * 80)

        try:
            # Remove interface from VLAN if still member
            self._remove_port_from_vlan(self.data.dut1, self.data.test_interface, self.data.test_vlan)
        except Exception as e:
            st.log(f"Note: Port cleanup: {str(e)}")

        try:
            # Delete VLAN if it exists
            self._delete_vlan(self.data.dut1, self.data.test_vlan)
        except Exception as e:
            st.log(f"Note: VLAN cleanup: {str(e)}")

    def _get_show_vlan_output(self, dut: str) -> str:
        """
        Get 'show Vlan' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log("Getting 'show Vlan' output")

        # Command: show Vlan
        command = "show Vlan"

        # Execute command and get raw output
        output = st.show(dut, command, type=self.data.cli_type, skip_tmpl=True)

        # Convert to string if needed
        if not isinstance(output, str):
            output = str(output)

        st.log(f"show Vlan output:\n{output}")
        return output

    def _remove_ip_addresses_from_interface(self, dut: str, interface: str) -> None:
        """
        Remove IPv4 and IPv6 addresses from specified interface.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
        """
        st.log(f"Removing IP addresses from {interface}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no ip address",
            "no ipv6 address",
            "exit"  # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=self.data.cli_type, skip_error_check=True)
        st.log(f"IP addresses removed from {interface}")

    def _create_vlan(self, dut: str, vlan_id: str) -> None:
        """
        Create VLAN using klish commands.

        IMPORTANT: Does NOT use exit - stays in config mode after VLAN creation.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "3")
        """
        st.log(f"Creating VLAN {vlan_id}")
        commands = [
            "configure terminal",
            f"vlan {vlan_id}"
            # NO exit - stay in config mode
        ]
        st.config(dut, commands, type=self.data.cli_type)

    def _delete_vlan(self, dut: str, vlan_id: str) -> None:
        """
        Delete VLAN using klish commands.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "3")
        """
        st.log(f"Deleting VLAN {vlan_id}")
        commands = [
            "configure terminal",
            f"no vlan {vlan_id}"
            # NO exit - stay in config mode
        ]
        st.config(dut, commands, type=self.data.cli_type, skip_error_check=True)

    def _add_port_to_vlan(self, dut: str, interface: str, vlan_id: str) -> None:
        """
        Add interface to VLAN as tagged member using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            vlan_id: VLAN ID (e.g., "3")
        """
        st.log(f"Adding {interface} to VLAN {vlan_id} as tagged member")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"switchport trunk allowed vlan {vlan_id}",
            "exit"   # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=self.data.cli_type)

    def _remove_port_from_vlan(self, dut: str, interface: str, vlan_id: str) -> None:
        """
        Remove interface from VLAN using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            vlan_id: VLAN ID (e.g., "3")
        """
        st.log(f"Removing {interface} from VLAN {vlan_id}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"no switchport trunk allowed vlan {vlan_id}",
            "exit"   # Only exit from interface mode, stay in config mode
        ]
        st.config(dut, commands, type=self.data.cli_type, skip_error_check=True)

    def _verify_no_vlans_configured(self, vlan_output: str) -> bool:
        """
        Verify that no VLANs are configured.

        Args:
            vlan_output: Raw output from 'show Vlan' command

        Returns:
            True if no VLANs are configured, False otherwise
        """
        st.log("Verifying no VLANs are configured")

        # Check for "No VLANs configured" message
        if "No VLANs configured" in vlan_output or "no vlans configured" in vlan_output.lower():
            st.log("PASS: No VLANs are configured")
            return True
        else:
            st.error("FAIL: VLANs are still configured")
            return False

    def _verify_vlan_exists(self, vlan_output: str, vlan_id: str) -> bool:
        """
        Verify that VLAN exists in show Vlan output.

        Args:
            vlan_output: Raw output from 'show Vlan' command
            vlan_id: VLAN ID (e.g., "3")

        Returns:
            True if VLAN exists, False otherwise
        """
        st.log(f"Verifying VLAN {vlan_id} exists")

        # Search for "Vlan<id>" pattern
        vlan_pattern = rf'Vlan{vlan_id}\s+\S+'
        match = re.search(vlan_pattern, vlan_output, re.IGNORECASE)

        if match:
            st.log(f"PASS: VLAN {vlan_id} exists")
            return True
        else:
            st.error(f"FAIL: VLAN {vlan_id} does not exist")
            return False

    def _verify_vlan_status(self, vlan_output: str, vlan_id: str, expected_status: str) -> bool:
        """
        Verify that VLAN has the expected status (Up/Down).

        Expected output format:
        Q: A - Access (Untagged), T - Tagged
        NUM       Status      Q Ports             Autostate   Dynamic
        ------------------------------------------------------------------
        Vlan3     Down                            Enable      No

        Args:
            vlan_output: Raw output from 'show Vlan' command
            vlan_id: VLAN ID (e.g., "3")
            expected_status: Expected status ("Up" or "Down")

        Returns:
            True if VLAN has expected status, False otherwise
        """
        st.log(f"Verifying VLAN {vlan_id} status is {expected_status}")

        # Search for VLAN line with status
        # Pattern: Vlan<id> followed by status (Up/Down)
        vlan_pattern = rf'Vlan{vlan_id}\s+(Up|Down)'
        match = re.search(vlan_pattern, vlan_output, re.IGNORECASE)

        if match:
            actual_status = match.group(1)
            if actual_status.lower() == expected_status.lower():
                st.log(f"PASS: VLAN {vlan_id} status is {actual_status}")
                return True
            else:
                st.error(f"FAIL: VLAN {vlan_id} status is {actual_status}, expected {expected_status}")
                return False
        else:
            st.error(f"FAIL: Could not determine VLAN {vlan_id} status from output")
            return False

    def _verify_port_in_vlan(self, vlan_output: str, vlan_id: str, interface: str) -> bool:
        """
        Verify that interface is a member of VLAN.

        Expected output format:
        Q: A - Access (Untagged), T - Tagged
        NUM       Status      Q Ports             Autostate   Dynamic
        ------------------------------------------------------------------
        Vlan3     Up          T  Ethernet4        Enable      No
                              T  Ethernet0                    No

        Args:
            vlan_output: Raw output from 'show Vlan' command
            vlan_id: VLAN ID (e.g., "3")
            interface: Interface name (e.g., "Ethernet0")

        Returns:
            True if interface is member of VLAN, False otherwise
        """
        st.log(f"Verifying {interface} is member of VLAN {vlan_id}")

        # Search for VLAN entry and check if interface is listed
        # The output can have ports on same line or continuation lines
        vlan_section_pattern = rf'Vlan{vlan_id}\s+.*?(?=Vlan\d+|$)'
        vlan_match = re.search(vlan_section_pattern, vlan_output, re.IGNORECASE | re.DOTALL)

        if not vlan_match:
            st.error(f"FAIL: VLAN {vlan_id} not found in output")
            return False

        vlan_section = vlan_match.group(0)

        # Check if interface is in this VLAN section
        if interface in vlan_section:
            st.log(f"PASS: {interface} is member of VLAN {vlan_id}")
            return True
        else:
            st.error(f"FAIL: {interface} is not member of VLAN {vlan_id}")
            return False

    def _verify_port_not_in_vlan(self, vlan_output: str, vlan_id: str, interface: str) -> bool:
        """
        Verify that interface is NOT a member of VLAN.

        Args:
            vlan_output: Raw output from 'show Vlan' command
            vlan_id: VLAN ID (e.g., "3")
            interface: Interface name (e.g., "Ethernet0")

        Returns:
            True if interface is NOT member of VLAN, False otherwise
        """
        st.log(f"Verifying {interface} is NOT member of VLAN {vlan_id}")

        # Search for VLAN entry and check if interface is NOT listed
        vlan_section_pattern = rf'Vlan{vlan_id}\s+.*?(?=Vlan\d+|$)'
        vlan_match = re.search(vlan_section_pattern, vlan_output, re.IGNORECASE | re.DOTALL)

        if not vlan_match:
            st.error(f"FAIL: VLAN {vlan_id} not found in output")
            return False

        vlan_section = vlan_match.group(0)

        # Check if interface is NOT in this VLAN section
        if interface not in vlan_section:
            st.log(f"PASS: {interface} is NOT member of VLAN {vlan_id}")
            return True
        else:
            st.error(f"FAIL: {interface} is still member of VLAN {vlan_id}")
            return False

    @pytest.mark.inventory(feature="Regression", testcases=["TC_VLAN_001_HW"])
    def test_vlan_creation_and_port_management(self) -> None:
        """
        TC_VLAN_001_HW: Validate CLI for VLAN creation and port management on hardware.

        Test Procedure:
        1. Dynamically get first interface from testbed
        2. Verify baseline (no VLANs configured)
        3. Remove IP addresses (IPv4 and IPv6) from first interface
        4. Create VLAN 3
        5. Verify VLAN 3 exists
        6. Add first interface to VLAN 3
        7. Verify interface is member of VLAN 3
        8. Remove interface from VLAN 3
        9. Verify VLAN 3 exists but has no ports
        10. Delete VLAN 3
        11. Verify no VLANs configured

        Expected Result:
        - IP addresses can be removed from interface
        - VLAN can be created successfully
        - Port can be added to VLAN as tagged member
        - Port can be removed from VLAN
        - VLAN can be deleted successfully
        - All changes are reflected accurately in 'show Vlan' output
        """
        st.log("=" * 80)
        st.log("TEST: VLAN Creation and Port Management (Hardware - Dynamic)")
        st.log("=" * 80)

        # Initialize validation failure tracking
        validation_failures = []

        dut = self.data.dut1
        vlan_id = self.data.test_vlan
        interface = self.data.test_interface

        # ===== STEP 1: Verify baseline (no VLANs configured) =====
        st.log("-" * 80)
        st.log("STEP 1: Verify baseline (no VLANs configured)")
        st.log("-" * 80)

        output = self._get_show_vlan_output(dut)
        if not self._verify_no_vlans_configured(output):
            error_msg = "Baseline check failed: VLANs are configured when none should exist"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: Baseline verified - no VLANs configured")

        # ===== STEP 2: Remove IP addresses from first interface =====
        st.log("-" * 80)
        st.log(f"STEP 2: Remove IP addresses (IPv4 and IPv6) from {interface}")
        st.log("-" * 80)

        self._remove_ip_addresses_from_interface(dut, interface)
        st.log(f"PASS: IP addresses removed from {interface}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 3: Create VLAN 3 =====
        st.log("-" * 80)
        st.log(f"STEP 3: Create VLAN {vlan_id}")
        st.log("-" * 80)

        self._create_vlan(dut, vlan_id)
        st.log(f"Created VLAN {vlan_id}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 4: Verify VLAN 3 exists =====
        st.log("-" * 80)
        st.log(f"STEP 4: Verify VLAN {vlan_id} exists")
        st.log("-" * 80)

        output = self._get_show_vlan_output(dut)
        if not self._verify_vlan_exists(output, vlan_id):
            error_msg = f"VLAN creation failed: VLAN {vlan_id} does not exist in 'show Vlan' output"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: VLAN {vlan_id} exists")

        # ===== STEP 4.1: Verify VLAN status is Down (no active ports yet) =====
        st.log("-" * 80)
        st.log(f"STEP 4.1: Verify VLAN {vlan_id} status is Down (no active member ports)")
        st.log("-" * 80)

        if not self._verify_vlan_status(output, vlan_id, "Down"):
            error_msg = f"VLAN status validation failed: VLAN {vlan_id} should be Down when no active member ports are configured"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: VLAN {vlan_id} status is Down (expected behavior with no active member ports)")

        # ===== STEP 5: Add first interface to VLAN 3 =====
        st.log("-" * 80)
        st.log(f"STEP 5: Add {interface} to VLAN {vlan_id}")
        st.log("-" * 80)

        self._add_port_to_vlan(dut, interface, vlan_id)
        st.log(f"Added {interface} to VLAN {vlan_id}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 6: Verify interface is member of VLAN 3 =====
        st.log("-" * 80)
        st.log(f"STEP 6: Verify {interface} is member of VLAN {vlan_id}")
        st.log("-" * 80)

        output = self._get_show_vlan_output(dut)
        if not self._verify_port_in_vlan(output, vlan_id, interface):
            error_msg = f"Port addition failed: {interface} is not member of VLAN {vlan_id}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {interface} is member of VLAN {vlan_id}")

        # ===== STEP 7: Remove interface from VLAN 3 =====
        st.log("-" * 80)
        st.log(f"STEP 7: Remove {interface} from VLAN {vlan_id}")
        st.log("-" * 80)

        self._remove_port_from_vlan(dut, interface, vlan_id)
        st.log(f"Removed {interface} from VLAN {vlan_id}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 8: Verify VLAN 3 exists but has no ports =====
        st.log("-" * 80)
        st.log(f"STEP 8: Verify VLAN {vlan_id} exists but has no ports")
        st.log("-" * 80)

        output = self._get_show_vlan_output(dut)
        if not self._verify_vlan_exists(output, vlan_id):
            error_msg = f"VLAN verification failed: VLAN {vlan_id} should still exist"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: VLAN {vlan_id} exists")

        if not self._verify_port_not_in_vlan(output, vlan_id, interface):
            error_msg = f"Port removal failed: {interface} is still member of VLAN {vlan_id}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: VLAN {vlan_id} exists with no ports")

        # ===== STEP 9: Delete VLAN 3 =====
        st.log("-" * 80)
        st.log(f"STEP 9: Delete VLAN {vlan_id}")
        st.log("-" * 80)

        self._delete_vlan(dut, vlan_id)
        st.log(f"Deleted VLAN {vlan_id}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 10: Verify no VLANs configured =====
        st.log("-" * 80)
        st.log("STEP 10: Verify no VLANs configured")
        st.log("-" * 80)

        output = self._get_show_vlan_output(dut)
        if not self._verify_no_vlans_configured(output):
            error_msg = "VLAN deletion failed: VLANs are still configured"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: No VLANs configured")

        # ===== TEST COMPLETE =====
        st.log("=" * 80)
        st.log("TEST COMPLETE: VLAN creation and port management validated successfully")
        st.log(f"VLAN {vlan_id} lifecycle: Created → Added {interface} → Removed {interface} → Deleted ✓")
        st.log("=" * 80)

        # Check for any validation failures
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED:")
            for idx, failure in enumerate(validation_failures, 1):
                st.error(f"{idx}. {failure}")
            st.log("!" * 80)
            st.report_fail("msg", f"Test completed with {len(validation_failures)} validation failure(s). See errors above.")
        else:
            st.log("All validations passed successfully")
            st.report_pass("test_case_passed")
