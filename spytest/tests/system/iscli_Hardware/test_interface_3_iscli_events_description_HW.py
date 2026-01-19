"""
INTERFACE EVENTS - DESCRIPTION CONFIGURATION CHANGES (HARDWARE - DYNAMIC TESTBED)
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs_hardware.yaml \
  tests/system/iscli_Hardware/test_interface_3_iscli_events_description_HW.py \
  --logs-path ./logs/test_interface_3_iscli_events_description_HW_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates interface description configuration changes by:
  1. Dynamically getting the first interface from testbed
  2. Verifying baseline (no description or default)
  3. Adding description "sonic" and verifying in running-config
  4. Removing description (no description) and verifying in running-config
  5. Adding description "test_interface" and verifying in running-config
  6. Restoring to no description

  This mirrors the exact CLI workflow:
    - show running-configuration interface Ethernet X (capture baseline)
    - configure terminal -> interface Ethernet X -> description sonic -> exit
    - show running-configuration interface Ethernet X (verify: description sonic)
    - configure terminal -> interface Ethernet X -> no description -> exit
    - show running-configuration interface Ethernet X (verify: no description)
    - configure terminal -> interface Ethernet X -> description test_interface -> exit
    - show running-configuration interface Ethernet X (verify: description test_interface)
    - configure terminal -> interface Ethernet X -> no description -> exit
    - show running-configuration interface Ethernet X (verify: no description)

  IMPORTANT: Uses 'show running-configuration interface Ethernet X' command
  to validate description changes in the configuration.

  This hardware-focused version dynamically retrieves the FIRST device from the testbed
  and the FIRST interface from that device's topology links, making it portable across
  different testbed configurations without hardcoding interface names.

Pre-requisites:
  - Topology: 1-node minimum | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - Dynamic (uses first DUT and first interface from testbed)
        # +--------------------+
        # |       DUT1         |
        # | (First device in   |
        # |  testbed)          |<-----First Interface from topology
        # |                    |
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
WAIT_AFTER_DESCRIPTION_CHANGE = 2


@pytest.mark.topology("any")
class TestInterfaceDescriptionChangesHW:
    """Test cases for validating interface description configuration changes via CLI (klish mode) on hardware."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters dynamically from testbed."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing Interface Description Change Test Suite (Hardware)")
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
        """Restore interface to no description."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Restoring interface to no description")
        st.log("=" * 80)

        try:
            cls._remove_interface_description_static(cls.data.test_interface)
            st.log(f"Restored {cls.data.test_interface} to no description")
        except Exception as e:
            st.log(f"Warning: Failed to restore description: {str(e)}")

        st.log("Test teardown complete")

    @classmethod
    def _remove_interface_description_static(cls, interface: str) -> None:
        """
        Static helper to remove interface description during teardown.

        Args:
            interface: Interface name (e.g., "Ethernet0")
        """
        try:
            commands = [
                "configure terminal",
                f"interface {interface}",
                "no description",
                "exit"   # Only exit from interface mode
            ]
            st.config(cls.data.dut1, commands, type=CLI_TYPE)
            time.sleep(1)
        except Exception as e:
            st.log(f"Warning: Failed to remove description: {str(e)}")

    def setup_method(self) -> None:
        """Per-test setup - ensure interface has no description."""
        st.log("-" * 80)
        st.log("TEST METHOD SETUP: Ensuring interface has no description")
        st.log("-" * 80)

        self._remove_interface_description(self.data.test_interface)
        time.sleep(WAIT_AFTER_DESCRIPTION_CHANGE)
        st.log(f"Interface {self.data.test_interface} configured with no description")

    def teardown_method(self) -> None:
        """Per-test teardown - restore interface to no description."""
        st.log("-" * 80)
        st.log("TEST METHOD TEARDOWN: Restoring interface")
        st.log("-" * 80)

        try:
            self._remove_interface_description(self.data.test_interface)
            st.log(f"Restored {self.data.test_interface} to no description")
        except Exception as e:
            st.log(f"Warning: Teardown issue: {str(e)}")

    def _configure_interface_description(self, interface: str, description: str) -> None:
        """
        Configure interface description using klish commands.

        IMPORTANT: Uses only ONE exit command to exit from interface mode
        back to config mode. Does NOT exit from config mode to avoid prompt
        timeout. The framework will handle cleanup automatically.

        Args:
            interface: Interface name (e.g., "Ethernet0", "Ethernet272")
            description: Description text (e.g., "sonic", "test_interface")
        """
        st.log(f"Configuring {interface} with description '{description}'")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"description {description}",
            "exit"   # Only exit from interface mode, stay in config mode
        ]
        result = st.config(self.data.dut1, commands, type=self.data.cli_type)
        return result

    def _remove_interface_description(self, interface: str) -> None:
        """
        Remove interface description using klish commands.

        Args:
            interface: Interface name (e.g., "Ethernet0", "Ethernet272")
        """
        st.log(f"Removing description from {interface}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no description",
            "exit"   # Only exit from interface mode, stay in config mode
        ]
        result = st.config(self.data.dut1, commands, type=self.data.cli_type)
        return result

    def _get_running_config_interface(self, interface: str) -> str:
        """
        Get running-configuration for a specific interface.

        Args:
            interface: Interface name (e.g., "Ethernet0", "Ethernet272")

        Returns:
            String containing the output of 'show running-configuration interface Ethernet X' command
        """
        st.log(f"Getting running-configuration for {interface}")

        # Parse interface number from name (e.g., "Ethernet0" -> "0", "Ethernet272" -> "272")
        interface_number = interface.replace("Ethernet", "").strip()

        # Command: show running-configuration interface Ethernet X
        cmd = f"show running-configuration interface Ethernet {interface_number}"

        # Execute command - st.show will handle entering sonic-cli automatically
        output = st.show(
            self.data.dut1,
            cmd,
            type=self.data.cli_type,
            skip_tmpl=True,
            skip_error_check=True
        )

        # Convert to string if needed
        if not isinstance(output, str):
            output = str(output)

        st.log(f"Running-config output:\n{output}")
        return output

    def _extract_description_from_running_config(self, output: str) -> Optional[str]:
        """
        Extract description value from running-configuration output.

        Expected output format:
        !
        interface Ethernet0
         description sonic
         mtu 9100
         speed 40000
         ip address 10.0.0.0/31

        Args:
            output: Raw CLI output string from show running-configuration

        Returns:
            Description value as string (e.g., "sonic", "test_interface"), or None if not found
        """
        if not output:
            st.log("No output to parse")
            return None

        # Search for "description <value>" pattern
        # Pattern: match "description" followed by whitespace and any text until end of line
        description_pattern = r'description\s+(.+?)(?:\n|$)'
        match = re.search(description_pattern, output, re.IGNORECASE)

        if match:
            description_value = match.group(1).strip()
            st.log(f"Found description value: {description_value}")
            return description_value
        else:
            st.log("Description not found in output")
            return None

    def _verify_description_in_running_config(
        self,
        interface: str,
        expected_description: Optional[str]
    ) -> bool:
        """
        Verify that interface has the expected description in running-configuration.

        Args:
            interface: Interface name (e.g., "Ethernet0", "Ethernet272")
            expected_description: Expected description value (e.g., "sonic", "test_interface")
                                 or None if no description should be present

        Returns:
            True if description matches expected value, False otherwise
        """
        st.log(f"Verifying {interface} description = '{expected_description}' in running-configuration")

        # Get running-config output
        output = self._get_running_config_interface(interface)

        # Extract description value
        actual_description = self._extract_description_from_running_config(output)

        # Compare values
        if expected_description is None:
            # Expecting no description
            if actual_description is None:
                st.log(f"PASS: {interface} has no description (as expected)")
                return True
            else:
                st.error(f"FAIL: {interface} has description '{actual_description}' (expected no description)")
                return False
        else:
            # Expecting a specific description
            if actual_description == expected_description:
                st.log(f"PASS: {interface} description is '{actual_description}' (matches expected '{expected_description}')")
                return True
            else:
                st.error(f"FAIL: {interface} description is '{actual_description}' (expected '{expected_description}')")
                return False

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_DESCRIPTION_001_HW"])
    def test_interface_description_change_cycle(self) -> None:
        """
        TC_INTF_EVENTS_DESCRIPTION_001_HW: Validate CLI for description configuration changes on hardware.

        Test Procedure:
        1. Dynamically get first interface from testbed topology
        2. Verify baseline (no description)
        3. Add description "sonic"
        4. Verify description = "sonic" in running-config
        5. Remove description (no description)
        6. Verify no description in running-config
        7. Add description "test_interface"
        8. Verify description = "test_interface" in running-config
        9. Remove description
        10. Verify no description in running-config
        11. Final validation

        Expected Result:
        - Description changes are reflected accurately in running-configuration
        - Description can be successfully added and removed multiple times
        - System remains stable after all description changes
        """
        st.log("=" * 80)
        st.log("TEST: Interface Description Change Cycle (Hardware - Dynamic)")
        st.log("=" * 80)

        # Initialize validation failure tracking
        validation_failures = []

        interface = self.data.test_interface

        # ===== STEP 1: Verify baseline (no description) =====
        st.log("-" * 80)
        st.log("STEP 1: Verify baseline (no description)")
        st.log("-" * 80)

        if not self._verify_description_in_running_config(interface, None):
            error_msg = f"Baseline check failed: {interface} has a description when it should not"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Baseline verified - {interface} has no description")

        # ===== STEP 2: Add description "sonic" =====
        st.log("-" * 80)
        st.log("STEP 2: Add description 'sonic'")
        st.log("-" * 80)

        self._configure_interface_description(interface, "sonic")
        st.log(f"Configured {interface} with description 'sonic'")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_DESCRIPTION_CHANGE)

        # ===== STEP 3: Verify description = "sonic" =====
        st.log("-" * 80)
        st.log("STEP 3: Verify description = 'sonic' in running-config")
        st.log("-" * 80)

        if not self._verify_description_in_running_config(interface, "sonic"):
            error_msg = f"Description verification failed: {interface} does not show description 'sonic' in running-config"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {interface} description is 'sonic'")

        # ===== STEP 4: Remove description =====
        st.log("-" * 80)
        st.log("STEP 4: Remove description (no description)")
        st.log("-" * 80)

        self._remove_interface_description(interface)
        st.log(f"Removed description from {interface}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_DESCRIPTION_CHANGE)

        # ===== STEP 5: Verify no description =====
        st.log("-" * 80)
        st.log("STEP 5: Verify no description in running-config")
        st.log("-" * 80)

        if not self._verify_description_in_running_config(interface, None):
            error_msg = f"Description removal failed: {interface} still has a description in running-config"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {interface} has no description")

        # ===== STEP 6: Add description "test_interface" =====
        st.log("-" * 80)
        st.log("STEP 6: Add description 'test_interface'")
        st.log("-" * 80)

        self._configure_interface_description(interface, "test_interface")
        st.log(f"Configured {interface} with description 'test_interface'")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_DESCRIPTION_CHANGE)

        # ===== STEP 7: Verify description = "test_interface" =====
        st.log("-" * 80)
        st.log("STEP 7: Verify description = 'test_interface' in running-config")
        st.log("-" * 80)

        if not self._verify_description_in_running_config(interface, "test_interface"):
            error_msg = f"Description verification failed: {interface} does not show description 'test_interface' in running-config"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {interface} description is 'test_interface'")

        # ===== STEP 8: Remove description =====
        st.log("-" * 80)
        st.log("STEP 8: Remove description")
        st.log("-" * 80)

        self._remove_interface_description(interface)
        st.log(f"Removed description from {interface}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_DESCRIPTION_CHANGE)

        # ===== STEP 9: Verify no description =====
        st.log("-" * 80)
        st.log("STEP 9: Verify no description in running-config")
        st.log("-" * 80)

        if not self._verify_description_in_running_config(interface, None):
            error_msg = f"Final description removal failed: {interface} still has a description in running-config"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {interface} has no description")

        # ===== STEP 10: Final validation =====
        st.log("-" * 80)
        st.log("STEP 10: Final validation")
        st.log("-" * 80)

        # Get final running-config
        final_output = self._get_running_config_interface(interface)
        final_description = self._extract_description_from_running_config(final_output)

        if final_description is not None:
            error_msg = f"Final validation failed: {interface} has description '{final_description}', expected no description"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: Final validation complete")

        # ===== TEST COMPLETE =====
        st.log("=" * 80)
        st.log("TEST COMPLETE: Description change cycle validated successfully")
        st.log(f"Description transitions: {interface}: None → 'sonic' → None → 'test_interface' → None ✓")
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
