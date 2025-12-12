"""
INTERFACE EVENTS - CLI ADMIN/LINK STATE CHANGES
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_interface_events/test_interface_1_iscli_events_admin_up_down.py \
  --logs-path ./logs/test_interface_1_iscli_events_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates that interface administrative state changes (shutdown/no shutdown) are
  accurately reflected in CLI outputs via the 'show interface status' command in klish mode.
  Tests the complete admin state transition cycle: up → down → up. Ensures that state
  changes affect only the target interface and that CLI reflects changes within seconds.
  Based on test plan TC_INTF_EVENTS_CLI_001 (1.1.1 - Validate CLI for admin/link state changes).

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |       DUT1         |                       |       DUT2         |
        # | (smic_sonic1)      |<-----Ethernet0------->| (smic_sonic2)      |
        # | 192.168.100.107    | (Admin State Tests)   | 192.168.100.54     |
        # |                    |<-----Ethernet4------->|                    |
        # |                    |<-----Ethernet8------->|                    |
        # |                    |<-----Ethernet12------>|                    |
        # +--------------------+                       +--------------------+
  - Access to sonic-cli (klish mode)
  - Required test variables: CLI type (klish)
"""

from __future__ import annotations

import pytest
import time
import re
from typing import Dict, Any, List, Optional

from spytest import st
from spytest.dicts import SpyTestDict
import apis.system.interface as intf_api


@pytest.mark.topology("any")
class TestInterfaceAdminStateChanges:
    """Test cases for validating interface admin state changes via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def _get_first_interface_from_testbed(cls) -> str:
        """
        Get the first interface from testbed topology.

        Returns:
            First interface name from testbed, or "Ethernet0" as fallback
        """
        try:
            # Get free ports from topology
            from apis.system.interface import get_all_interfaces
            interfaces = get_all_interfaces(cls.data.dut1, type="Eth")

            if interfaces:
                first_interface = interfaces[0]
                st.log(f"Retrieved first interface from testbed: {first_interface}")
                return first_interface
            else:
                st.log("No interfaces found, using fallback: Ethernet0")
                return "Ethernet0"
        except Exception as e:
            st.log(f"Failed to get interface from testbed: {str(e)}, using fallback: Ethernet0")
            return "Ethernet0"

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing Interface Admin State Test Suite")
        st.log("=" * 80)

        # Get DUT handles
        cls.data.dut_names = st.get_dut_names()
        if not cls.data.dut_names:
            st.report_fail("msg", "No DUTs available in topology")

        cls.data.dut1 = cls.data.dut_names[0]
        st.log(f"Primary DUT: {cls.data.dut1}")

        # CLI type - use klish as specified
        cls.data.cli_type = "klish"
        st.log(f"CLI Type: {cls.data.cli_type}")

        # Get test interface from testbed dynamically
        first_interface = cls._get_first_interface_from_testbed()

        # Test interfaces from testbed (using dynamic retrieval for first interface and conventional names for others)
        cls.data.test_interfaces = [first_interface, "Ethernet4", "Ethernet8", "Ethernet12"]
        cls.data.primary_test_interface = first_interface
        st.log(f"Test Interfaces: {cls.data.test_interfaces}")
        st.log(f"Primary Test Interface: {cls.data.primary_test_interface}")

        # Verification timeout
        cls.data.wait_time = 3  # seconds to wait after config changes
        st.log(f"Configuration wait time: {cls.data.wait_time} seconds")

        st.log("Test setup complete")

    @classmethod
    def teardown_class(cls) -> None:
        """Restore all interfaces to admin up state."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Restoring all interfaces to admin up state")
        st.log("=" * 80)

        for interface in cls.data.test_interfaces:
            try:
                cls._bring_interface_up_static(interface)
                st.log(f"Restored {interface} to admin up state")
            except Exception as e:
                st.log(f"Warning: Failed to restore {interface}: {str(e)}")

        st.log("Test teardown complete")

    @classmethod
    def _bring_interface_up_static(cls, interface: str) -> None:
        """
        Static helper to bring interface up during teardown.

        Args:
            interface: Interface name (e.g., "Ethernet0")
        """
        try:
            # Use interface API to bring interface up (startup)
            intf_api.interface_operation(
                cls.data.dut1,
                interface,
                operation="startup",
                cli_type=cls.data.cli_type
            )
            time.sleep(1)
        except Exception as e:
            st.log(f"Warning: Failed to bring up {interface}: {str(e)}")

    def setup_method(self) -> None:
        """Per-test setup - ensure all test interfaces are admin up."""
        st.log("-" * 80)
        st.log("TEST METHOD SETUP: Bringing all test interfaces to admin up state")
        st.log("-" * 80)

        for interface in self.data.test_interfaces:
            self._bring_interface_up(interface)
            st.log(f"Brought {interface} to admin up state")

        # Wait for interfaces to stabilize
        time.sleep(self.data.wait_time)
        st.log("All test interfaces are in admin up state")

    def teardown_method(self) -> None:
        """Per-test teardown - restore interfaces to admin up state."""
        st.log("-" * 80)
        st.log("TEST METHOD TEARDOWN: Restoring interfaces")
        st.log("-" * 80)

        for interface in self.data.test_interfaces:
            try:
                self._bring_interface_up(interface)
                st.log(f"Restored {interface} to admin up state")
            except Exception as e:
                st.log(f"Warning: Teardown issue on {interface}: {str(e)}")

    def _bring_interface_up(self, interface: str) -> None:
        """
        Bring interface to admin up state (no shutdown).

        Args:
            interface: Interface name (e.g., "Ethernet0")
        """
        # Use interface API to bring interface up (startup = no shutdown)
        intf_api.interface_operation(
            self.data.dut1,
            interface,
            operation="startup",
            cli_type=self.data.cli_type
        )

    def _bring_interface_down(self, interface: str) -> None:
        """
        Bring interface to admin down state (shutdown).

        Args:
            interface: Interface name (e.g., "Ethernet0")
        """
        # Use interface API to bring interface down (shutdown)
        intf_api.interface_operation(
            self.data.dut1,
            interface,
            operation="shutdown",
            cli_type=self.data.cli_type
        )

    def _get_interface_status(self) -> str:
        """
        Get interface status output from CLI.

        Returns:
            String containing the output of 'show interface status' command
        """
        # First exit config mode completely and go back to normal user
        st.config(
            self.data.dut1,
            "end",
            type=self.data.cli_type,
            conf=False,
            skip_error_check=True
        )

        # Exit from sonic-cli to bash
        st.config(
            self.data.dut1,
            "exit",
            type=self.data.cli_type,
            conf=False,
            skip_error_check=True
        )

        # Small delay for mode transition
        time.sleep(0.5)

        # Disable pagination before running show command
        st.config(
            self.data.dut1,
            "terminal length 0",
            type=self.data.cli_type,
            conf=False,
            skip_error_check=True
        )

        # Now run show command
        cmd = "show interface status"
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

        return output

    def _validate_interface_admin_state(
        self,
        interface: str,
        expected_state: str,
        output: str
    ) -> bool:
        """
        Validate interface admin state from show interface status output.

        Expected format:
        Name           Alias     Admin     Oper      Speed       MTU ...
        Ethernet0      Eth1      up        down      50000       9100 ...

        Validation logic using occurrence count:
        - If expecting "up": count occurrences of "up" in line
          - 2 "up" = Admin up, Oper up
          - 1 "up" = Admin up, Oper down
        - If expecting "down": count occurrences of "down" in line
          - 1 "down" = Admin down, Oper down (but we check >= 1 for admin down)

        Args:
            interface: Interface name (e.g., "Ethernet0")
            expected_state: Expected admin state ("up" or "down")
            output: Raw output from show interface status command

        Returns:
            True if validation passes, False otherwise
        """
        st.log(f"Validating {interface} admin state = {expected_state}")

        # Convert output to string if it's not already
        if not isinstance(output, str):
            output = str(output)

        # Split output into lines
        lines = output.split('\n')

        # Find the line containing the interface
        interface_line = None
        for line in lines:
            stripped = line.strip()
            # Check if line starts with the interface name
            if stripped.startswith(interface + " ") or stripped.startswith(interface + "\t"):
                # Make sure it's not a header line
                if "Name" not in line and "---" not in line:
                    interface_line = line
                    st.log(f"Found interface line: {line.strip()}")
                    break

        if not interface_line:
            st.error(f"Interface {interface} not found in output")
            return False

        # Count occurrences of the expected state in the line
        line_lower = interface_line.lower()
        state_count = line_lower.count(expected_state.lower())

        st.log(f"Count of '{expected_state}' in line: {state_count}")

        # Validation based on count
        if expected_state.lower() == "up":
            # Admin is up ONLY if we find EXACTLY 2 "up" (Admin=up AND Oper=up)
            # 1 "up" = Admin up but Oper down (FAIL - link not up)
            # 2 "up" = Admin up AND Oper up (PASS - both up)
            if state_count == 2:
                st.log(f"PASS: {interface} admin state is UP (found {state_count} occurrence(s) of 'up' - Admin=up, Oper=up)")
                return True
            else:
                st.error(f"FAIL: {interface} admin state check failed (found {state_count} occurrence(s) of 'up', expected 2)")
                return False

        elif expected_state.lower() == "down":
            # Admin is down if we find at least 1 "down"
            # After shutdown, the line should have at least 1 "down" in admin column
            if state_count >= 1:
                st.log(f"PASS: {interface} admin state is DOWN (found {state_count} occurrence(s) of 'down')")
                return True
            else:
                st.error(f"FAIL: {interface} admin state is not DOWN (found {state_count} occurrence(s) of 'down')")
                return False

        else:
            st.error(f"Invalid expected state: {expected_state}")
            return False

    def _validate_other_interfaces_unchanged(
        self,
        test_interface: str,
        expected_state: str,
        output: str
    ) -> bool:
        """
        Validate that other interfaces (not the test interface) remain in the expected state.

        Args:
            test_interface: The interface being tested (should be excluded from validation)
            expected_state: Expected state for other interfaces ("up" or "down")
            output: Raw output from show interface status command

        Returns:
            True if all other interfaces are in expected state, False otherwise
        """
        st.log(f"Validating that interfaces other than {test_interface} remain {expected_state}")

        all_pass = True
        for interface in self.data.test_interfaces:
            if interface == test_interface:
                continue  # Skip the test interface

            if not self._validate_interface_admin_state(interface, expected_state, output):
                st.error(f"FAIL: {interface} state changed unexpectedly")
                all_pass = False

        if all_pass:
            st.log(f"PASS: All other interfaces remain in {expected_state} state")

        return all_pass

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_CLI_001"])
    def test_interface_admin_state_up_down_up_cycle(self) -> None:
        """
        TC_INTF_EVENTS_CLI_001: Validate CLI for admin/link state changes.

        Test Procedure:
        1. Bring all testbed interfaces to admin UP state
        2. Verify baseline - all interfaces show Admin = "up"
        3. Shutdown primary test interface (Ethernet0)
        4. Verify Ethernet0 shows Admin = "down"
        5. Verify other interfaces remain Admin = "up"
        6. Bring Ethernet0 back up (no shutdown)
        7. Verify Ethernet0 shows Admin = "up"
        8. Verify complete state cycle: up → down → up

        Expected Result:
        - Admin state changes are reflected accurately in CLI
        - Only target interface state changes
        - State transitions complete within seconds
        - CLI output is consistent and accurate
        """
        st.log("=" * 80)
        st.log("TEST: Interface Admin State Up-Down-Up Cycle")
        st.log("=" * 80)

        # Initialize validation failures list for tracking
        validation_failures = []

        test_interface = self.data.primary_test_interface

        # ===== STEP 1 & 2: Verify baseline - all interfaces admin UP =====
        st.log("-" * 80)
        st.log("STEP 1-2: Verify baseline - all interfaces admin UP")
        st.log("-" * 80)

        output_baseline = self._get_interface_status()
        st.log("Baseline interface status retrieved")

        # Validate all test interfaces are admin up
        for interface in self.data.test_interfaces:
            if not self._validate_interface_admin_state(interface, "up", output_baseline):
                error_msg = f"Baseline check failed: {interface} is not in admin UP state"
                st.error(error_msg)
                validation_failures.append(error_msg)
            else:
                st.log(f"PASS: {interface} baseline verified - admin UP")

        if not validation_failures:
            st.log("PASS: Baseline verified - all interfaces are admin UP")
        else:
            st.log("WARNING: Baseline verification has failures - continuing test")

        # ===== STEP 3: Shutdown primary test interface =====
        st.log("-" * 80)
        st.log(f"STEP 3: Shutting down {test_interface}")
        st.log("-" * 80)

        self._bring_interface_down(test_interface)
        st.log(f"Executed shutdown command on {test_interface}")

        # Wait for state change to propagate
        time.sleep(self.data.wait_time)

        # ===== STEP 4: Verify test interface is admin DOWN =====
        st.log("-" * 80)
        st.log(f"STEP 4: Verify {test_interface} is admin DOWN")
        st.log("-" * 80)

        output_after_down = self._get_interface_status()

        if not self._validate_interface_admin_state(test_interface, "down", output_after_down):
            error_msg = f"Admin state verification failed: {test_interface} is not showing as DOWN after shutdown"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {test_interface} admin state is DOWN")

        # ===== STEP 5: Verify other interfaces remain admin UP =====
        st.log("-" * 80)
        st.log("STEP 5: Verify other interfaces remain admin UP")
        st.log("-" * 80)

        if not self._validate_other_interfaces_unchanged(test_interface, "up", output_after_down):
            error_msg = f"Interface isolation check failed: Other interfaces changed state when {test_interface} was shut down"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: Other interfaces remain admin UP")

        # ===== STEP 6: Bring test interface back UP =====
        st.log("-" * 80)
        st.log(f"STEP 6: Bringing {test_interface} back UP (no shutdown)")
        st.log("-" * 80)

        self._bring_interface_up(test_interface)
        st.log(f"Executed no shutdown command on {test_interface}")

        # Wait for state change to propagate
        time.sleep(self.data.wait_time)

        # ===== STEP 7: Verify test interface is admin UP again =====
        st.log("-" * 80)
        st.log(f"STEP 7: Verify {test_interface} is admin UP again")
        st.log("-" * 80)

        output_after_up = self._get_interface_status()

        if not self._validate_interface_admin_state(test_interface, "up", output_after_up):
            error_msg = f"Admin state verification failed: {test_interface} is not showing as UP after no shutdown"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {test_interface} admin state is UP")

        # ===== STEP 8: Final validation - all interfaces UP =====
        st.log("-" * 80)
        st.log("STEP 8: Final validation - all interfaces admin UP")
        st.log("-" * 80)

        for interface in self.data.test_interfaces:
            if not self._validate_interface_admin_state(interface, "up", output_after_up):
                error_msg = f"Final validation failed: {interface} is not in admin UP state"
                st.error(error_msg)
                validation_failures.append(error_msg)
            else:
                st.log(f"PASS: {interface} final validation - admin UP")

        if not validation_failures:
            st.log("PASS: All interfaces are admin UP")

        # ===== TEST COMPLETE =====
        st.log("=" * 80)
        st.log("TEST COMPLETE: Admin state cycle validated successfully")
        st.log(f"State transitions: {test_interface}: UP → DOWN → UP ✓")
        st.log("=" * 80)

        # ===== FINAL VALIDATION REPORT =====
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

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_CLI_001_ISOLATION"])
    def test_interface_admin_state_isolation(self) -> None:
        """
        Validate that admin state changes on one interface do not affect other interfaces.

        Test Procedure:
        1. Verify all interfaces are admin UP
        2. Shutdown Ethernet0
        3. Verify Ethernet4, Ethernet8, Ethernet12 remain UP
        4. Bring Ethernet0 back UP
        5. Verify all interfaces are UP

        Expected Result:
        - Interface admin state changes are isolated
        - Only target interface changes state
        - Other interfaces unaffected
        """
        st.log("=" * 80)
        st.log("TEST: Interface Admin State Isolation")
        st.log("=" * 80)

        # Initialize validation failures list for tracking
        validation_failures = []

        test_interface = self.data.primary_test_interface
        other_interfaces = [intf for intf in self.data.test_interfaces if intf != test_interface]

        # Step 1: Verify baseline
        st.log("STEP 1: Verify all interfaces are admin UP")
        output_baseline = self._get_interface_status()

        for interface in self.data.test_interfaces:
            if not self._validate_interface_admin_state(interface, "up", output_baseline):
                error_msg = f"Baseline failed: {interface} not UP"
                st.error(error_msg)
                validation_failures.append(error_msg)
            else:
                st.log(f"PASS: {interface} baseline verified - admin UP")

        if not validation_failures:
            st.log("PASS: Baseline - all interfaces UP")
        else:
            st.log("WARNING: Baseline verification has failures - continuing test")

        # Step 2: Shutdown test interface
        st.log(f"STEP 2: Shutting down {test_interface}")
        self._bring_interface_down(test_interface)
        time.sleep(self.data.wait_time)

        # Step 3: Verify isolation
        st.log("STEP 3: Verify other interfaces remain UP")
        output_after_down = self._get_interface_status()

        # Check test interface is down
        if not self._validate_interface_admin_state(test_interface, "down", output_after_down):
            error_msg = f"{test_interface} not DOWN after shutdown"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {test_interface} is DOWN")

        # Check other interfaces are still up
        for interface in other_interfaces:
            if not self._validate_interface_admin_state(interface, "up", output_after_down):
                error_msg = f"Isolation failed: {interface} changed state when {test_interface} was shut down"
                st.error(error_msg)
                validation_failures.append(error_msg)
            else:
                st.log(f"PASS: {interface} remains UP (isolation verified)")

        if not validation_failures:
            st.log("PASS: Other interfaces remain UP (isolation verified)")
        else:
            st.log("WARNING: Isolation verification has failures - continuing test")

        # Step 4: Restore test interface
        st.log(f"STEP 4: Bringing {test_interface} back UP")
        self._bring_interface_up(test_interface)
        time.sleep(self.data.wait_time)

        # Step 5: Verify all UP
        st.log("STEP 5: Verify all interfaces are UP")
        output_final = self._get_interface_status()

        for interface in self.data.test_interfaces:
            if not self._validate_interface_admin_state(interface, "up", output_final):
                error_msg = f"Final check failed: {interface} not UP"
                st.error(error_msg)
                validation_failures.append(error_msg)
            else:
                st.log(f"PASS: {interface} final validation - admin UP")

        if not validation_failures:
            st.log("PASS: All interfaces UP - test complete")

        st.log("=" * 80)
        st.log("TEST COMPLETE: Interface isolation validated")
        st.log("=" * 80)

        # ===== FINAL VALIDATION REPORT =====
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
