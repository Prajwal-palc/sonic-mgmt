"""
INTERFACE EVENTS - MTU CONFIGURATION CHANGES (HARDWARE - DYNAMIC TESTBED)
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs_hardware.yaml \
  tests/system/iscli_Hardware/test_interface_2_iscli_events_mtu_change_HW.py \
  --logs-path ./logs/test_interface_2_iscli_events_mtu_HW_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates interface MTU (Maximum Transmission Unit) configuration changes by:
  1. Dynamically getting the first interface from testbed
  2. Verifying baseline MTU (default: 9100)
  3. Changing MTU to 1600 and verifying in running-config
  4. Changing MTU to 2000 and verifying in running-config
  5. Restoring MTU to 9100 and verifying in running-config

  This mirrors the exact CLI workflow:
    - show running-configuration interface Ethernet X (capture baseline)
    - configure terminal -> interface Ethernet X -> mtu 1600 -> end
    - show running-configuration interface Ethernet X (verify: mtu 1600)
    - configure terminal -> interface Ethernet X -> mtu 2000 -> end
    - show running-configuration interface Ethernet X (verify: mtu 2000)
    - configure terminal -> interface Ethernet X -> mtu 9100 -> end
    - show running-configuration interface Ethernet X (verify: mtu 9100)

  IMPORTANT: Uses 'show running-configuration interface Ethernet X' command
  to validate MTU changes in the configuration.

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
WAIT_AFTER_MTU_CHANGE = 2


@pytest.mark.topology("any")
class TestInterfaceMTUChangesHW:
    """Test cases for validating interface MTU configuration changes via CLI (klish mode) on hardware."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters dynamically from testbed."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing Interface MTU Change Test Suite (Hardware)")
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

        # Default MTU value
        cls.data.default_mtu = "9100"
        st.log(f"Default MTU: {cls.data.default_mtu}")

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
        """Restore interface to default MTU."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Restoring interface to default MTU")
        st.log("=" * 80)

        try:
            cls._configure_interface_mtu_static(cls.data.test_interface, cls.data.default_mtu)
            st.log(f"Restored {cls.data.test_interface} to default MTU {cls.data.default_mtu}")
        except Exception as e:
            st.log(f"Warning: Failed to restore MTU: {str(e)}")

        st.log("Test teardown complete")

    @classmethod
    def _configure_interface_mtu_static(cls, interface: str, mtu_value: str) -> None:
        """
        Static helper to configure interface MTU during teardown.

        Args:
            interface: Interface name (e.g., "Ethernet0")
            mtu_value: MTU value (e.g., "9100", "1600")
        """
        try:
            commands = [
                "configure terminal",
                f"interface {interface}",
                f"mtu {mtu_value}",
                "exit"   # Only exit from interface mode
            ]
            st.config(cls.data.dut1, commands, type=CLI_TYPE)
            time.sleep(1)
        except Exception as e:
            st.log(f"Warning: Failed to configure MTU: {str(e)}")

    def setup_method(self) -> None:
        """Per-test setup - ensure interface has default MTU."""
        st.log("-" * 80)
        st.log("TEST METHOD SETUP: Ensuring interface has default MTU")
        st.log("-" * 80)

        self._configure_interface_mtu(self.data.test_interface, self.data.default_mtu)
        time.sleep(WAIT_AFTER_MTU_CHANGE)
        st.log(f"Interface {self.data.test_interface} configured with default MTU {self.data.default_mtu}")

    def teardown_method(self) -> None:
        """Per-test teardown - restore interface to default MTU."""
        st.log("-" * 80)
        st.log("TEST METHOD TEARDOWN: Restoring interface")
        st.log("-" * 80)

        try:
            self._configure_interface_mtu(self.data.test_interface, self.data.default_mtu)
            st.log(f"Restored {self.data.test_interface} to default MTU {self.data.default_mtu}")
        except Exception as e:
            st.log(f"Warning: Teardown issue: {str(e)}")

    def _configure_interface_mtu(self, interface: str, mtu_value: str) -> None:
        """
        Configure interface MTU using klish commands.

        IMPORTANT: Uses only ONE exit command to exit from interface mode
        back to config mode. Does NOT exit from config mode to avoid prompt
        timeout. The framework will handle cleanup automatically.

        Args:
            interface: Interface name (e.g., "Ethernet0")
            mtu_value: MTU value (e.g., "9100", "1600", "2000")
        """
        st.log(f"Configuring {interface} with MTU {mtu_value}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"mtu {mtu_value}",
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

    def _extract_mtu_from_running_config(self, output: str) -> Optional[str]:
        """
        Extract MTU value from running-configuration output.

        Expected output format:
        !
        interface Ethernet0
         mtu 1600
         speed 40000
         ip address 10.0.0.0/31

        Args:
            output: Raw CLI output string from show running-configuration

        Returns:
            MTU value as string (e.g., "1600", "9100"), or None if not found
        """
        if not output:
            st.log("No output to parse")
            return None

        # Search for "mtu <value>" pattern
        # Pattern: match "mtu" followed by whitespace and digits
        mtu_pattern = r'mtu\s+(\d+)'
        match = re.search(mtu_pattern, output, re.IGNORECASE)

        if match:
            mtu_value = match.group(1)
            st.log(f"Found MTU value: {mtu_value}")
            return mtu_value
        else:
            st.log("MTU value not found in output")
            return None

    def _verify_mtu_in_running_config(
        self,
        interface: str,
        expected_mtu: str
    ) -> bool:
        """
        Verify that interface has the expected MTU in running-configuration.

        Args:
            interface: Interface name (e.g., "Ethernet0", "Ethernet272")
            expected_mtu: Expected MTU value (e.g., "1600", "9100")

        Returns:
            True if MTU matches expected value, False otherwise
        """
        st.log(f"Verifying {interface} MTU = {expected_mtu} in running-configuration")

        # Get running-config output
        output = self._get_running_config_interface(interface)

        # Extract MTU value
        actual_mtu = self._extract_mtu_from_running_config(output)

        if not actual_mtu:
            st.error(f"Could not extract MTU value from running-config for {interface}")
            return False

        # Compare values
        if actual_mtu == expected_mtu:
            st.log(f"PASS: {interface} MTU is {actual_mtu} (matches expected {expected_mtu})")
            return True
        else:
            st.error(f"FAIL: {interface} MTU is {actual_mtu} (expected {expected_mtu})")
            return False

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_MTU_001_HW"])
    def test_interface_mtu_change_cycle(self) -> None:
        """
        TC_INTF_EVENTS_MTU_001_HW: Validate CLI for MTU configuration changes on hardware.

        Test Procedure:
        1. Dynamically get first interface from testbed topology
        2. Verify baseline MTU (9100)
        3. Change MTU to 1600
        4. Verify MTU = 1600 in running-config
        5. Change MTU to 2000
        6. Verify MTU = 2000 in running-config
        7. Restore MTU to 9100
        8. Verify MTU = 9100 in running-config
        9. Final validation

        Expected Result:
        - MTU changes are reflected accurately in running-configuration
        - MTU can be successfully changed: 9100 → 1600 → 2000 → 9100
        - System remains stable after all MTU changes
        """
        st.log("=" * 80)
        st.log("TEST: Interface MTU Change Cycle (Hardware - Dynamic)")
        st.log("=" * 80)

        # Initialize validation failure tracking
        validation_failures = []

        interface = self.data.test_interface

        # ===== STEP 1: Verify baseline MTU (9100) =====
        st.log("-" * 80)
        st.log("STEP 1: Verify baseline MTU (9100)")
        st.log("-" * 80)

        if not self._verify_mtu_in_running_config(interface, self.data.default_mtu):
            error_msg = f"Baseline check failed: {interface} MTU is not {self.data.default_mtu}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Baseline MTU verified - {interface} has MTU {self.data.default_mtu}")

        # ===== STEP 2: Change MTU to 1600 =====
        st.log("-" * 80)
        st.log("STEP 2: Change MTU to 1600")
        st.log("-" * 80)

        self._configure_interface_mtu(interface, "1600")
        st.log(f"Configured {interface} with MTU 1600")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_MTU_CHANGE)

        # ===== STEP 3: Verify MTU = 1600 =====
        st.log("-" * 80)
        st.log("STEP 3: Verify MTU = 1600 in running-config")
        st.log("-" * 80)

        if not self._verify_mtu_in_running_config(interface, "1600"):
            error_msg = f"MTU verification failed: {interface} does not show MTU 1600 in running-config"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {interface} MTU changed to 1600")

        # ===== STEP 4: Change MTU to 2000 =====
        st.log("-" * 80)
        st.log("STEP 4: Change MTU to 2000")
        st.log("-" * 80)

        self._configure_interface_mtu(interface, "2000")
        st.log(f"Configured {interface} with MTU 2000")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_MTU_CHANGE)

        # ===== STEP 5: Verify MTU = 2000 =====
        st.log("-" * 80)
        st.log("STEP 5: Verify MTU = 2000 in running-config")
        st.log("-" * 80)

        if not self._verify_mtu_in_running_config(interface, "2000"):
            error_msg = f"MTU verification failed: {interface} does not show MTU 2000 in running-config"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {interface} MTU changed to 2000")

        # ===== STEP 6: Restore MTU to 9100 =====
        st.log("-" * 80)
        st.log("STEP 6: Restore MTU to 9100")
        st.log("-" * 80)

        self._configure_interface_mtu(interface, self.data.default_mtu)
        st.log(f"Configured {interface} with MTU {self.data.default_mtu}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_MTU_CHANGE)

        # ===== STEP 7: Verify MTU = 9100 =====
        st.log("-" * 80)
        st.log("STEP 7: Verify MTU = 9100 in running-config")
        st.log("-" * 80)

        if not self._verify_mtu_in_running_config(interface, self.data.default_mtu):
            error_msg = f"MTU restoration failed: {interface} does not show MTU {self.data.default_mtu} in running-config"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {interface} MTU restored to {self.data.default_mtu}")

        # ===== STEP 8: Final validation =====
        st.log("-" * 80)
        st.log("STEP 8: Final validation")
        st.log("-" * 80)

        # Get final running-config
        final_output = self._get_running_config_interface(interface)
        final_mtu = self._extract_mtu_from_running_config(final_output)

        if final_mtu != self.data.default_mtu:
            error_msg = f"Final validation failed: {interface} MTU is {final_mtu}, expected {self.data.default_mtu}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: Final validation complete")

        # ===== TEST COMPLETE =====
        st.log("=" * 80)
        st.log("TEST COMPLETE: MTU change cycle validated successfully")
        st.log(f"MTU transitions: {interface}: 9100 → 1600 → 2000 → 9100 ✓")
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
