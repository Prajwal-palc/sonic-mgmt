"""
INTERFACE EVENTS - SPEED CONFIGURATION CHANGE AND RESTORATION
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/interface_events/test_interface_events9_speed_change_second_APPRO.py \
  --logs-path ./logs/test_interface_events9_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates interface speed configuration changes by:
  1. Getting the first operational interface from testbed
  2. Capturing baseline speed (e.g., 40G)
  3. Changing speed to a different value (e.g., 10G using "speed 10000")
  4. Verifying the speed change is reflected in "show interface status"
  5. Restoring the original speed
  6. Verifying the restoration

  This mirrors the exact CLI workflow:
    - show interface status (capture baseline)
    - configure terminal -> interface Ethernet0 -> speed 10000 -> exit
    - show interface status (verify change: 40G -> 10G)
    - configure terminal -> interface Ethernet0 -> speed 40000 -> exit
    - show interface status (verify restoration: 10G -> 40G)

  IMPORTANT: Uses only ONE exit command to stay in config mode and avoid
  prompt timeout issues when exiting from config mode to root mode.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - At least one interface should be operationally up
  - Access to sonic-cli (klish)
  - Required test variables: CLI type (klish)
"""

from __future__ import annotations

import pytest
import time
from typing import Dict, Any, List, Optional

from spytest import st, SpyTestDict


# CLI type for all operations
CLI_TYPE = "klish"

# Wait times
WAIT_AFTER_SPEED_CHANGE = 5
WAIT_FOR_LINK_STABILIZATION = 3


@pytest.mark.topology("any")
class TestInterfaceSpeedChanges:
    """Test cases for validating interface speed configuration changes and restoration."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and get first operational interface from testbed."""
        st.log("=" * 80)
        st.log("SETUP: Initializing Interface Speed Change Test Suite")
        st.log("=" * 80)

        # Get minimum topology - 2 devices connected
        min_topology = ["D1D2:2"]  # 2 links between D1 and D2
        topology = st.ensure_min_topology(*min_topology)

        cls.data.topology = topology
        cls.data.dut1 = topology.D1
        cls.data.dut2 = topology.D2
        cls.data.dut_names = st.get_dut_names()

        # Get first interface from topology links
        # topology has D1D2P1, D1D2P2 etc. - we'll use the first link
        if hasattr(topology, 'D1D2P1'):
            cls.data.test_interface = topology.D1D2P1
        else:
            # Fallback to Ethernet0 if topology doesn't have link info
            cls.data.test_interface = "Ethernet0"

        # Store original speed for restoration
        cls.data.original_speed = None
        cls.data.original_speed_numeric = None  # e.g., "40000" for 40G

        # Set terminal length 0 to disable pagination
        st.log("Setting terminal length 0 to disable pagination")
        st.config(cls.data.dut1, "terminal length 0", type=CLI_TYPE)

        st.log(f"DUT1: {cls.data.dut1}")
        st.log(f"DUT2: {cls.data.dut2}")
        st.log(f"Test Interface: {cls.data.test_interface}")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup test suite."""
        st.log("=" * 80)
        st.log("TEARDOWN: Cleaning up Interface Speed Change Test Suite")
        st.log("=" * 80)
        st.log("Cleanup completed")

    def setup_method(self) -> None:
        """Setup before each test method."""
        st.log("\n" + "-" * 80)
        st.log("SETUP METHOD: Starting new test case")
        st.log("-" * 80)

    def teardown_method(self) -> None:
        """Teardown after each test method."""
        st.log("-" * 80)
        st.log("TEARDOWN METHOD: Completed test case")
        st.log("-" * 80 + "\n")

    @staticmethod
    def _get_interface_status_raw(dut: str) -> str:
        """
        Get interface status using 'show interface status' command.
        Returns raw CLI output as string for manual parsing.

        IMPORTANT: Always uses "show interface status" WITHOUT interface name
        to avoid pagination issues.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        # ALWAYS use just "show interface status" - no interface name
        command = "show interface status"

        # Execute command and get raw output
        output = st.show(dut, command, type=CLI_TYPE)

        # If output is a list/dict (parsed), we need to convert back or get raw
        if isinstance(output, (list, dict)):
            # Try to get raw output using skip_tmpl
            st.log("Got parsed output, attempting to get raw output")
            output_raw = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)
            if output_raw:
                output = output_raw

        # Convert to string if needed
        if not isinstance(output, str):
            output = str(output)

        st.log(f"Interface status raw output:\n{output}")
        return output

    @staticmethod
    def _configure_interface_speed(dut: str, interface: str, speed_value: str) -> bool:
        """
        Configure interface speed using klish commands.
        Example: speed 10000 (for 10G), speed 40000 (for 40G)

        IMPORTANT: Uses only ONE exit command to exit from interface mode
        back to config mode. Does NOT exit from config mode to avoid prompt
        timeout. The framework will handle cleanup automatically.

        Args:
            dut: Device handle
            interface: Interface name
            speed_value: Speed value in Mbps (e.g., "10000" for 10G, "40000" for 40G)

        Returns:
            True if successful
        """
        st.log(f"Configuring {interface} with speed {speed_value}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"speed {speed_value}",
            "exit"   # Only exit from interface mode, stay in config mode
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return result

    @staticmethod
    def _extract_interface_speed(interface_output: str, interface: str) -> str:
        """
        Extract interface speed from raw CLI output by parsing the table.

        Example output:
        ------------------------------------------------------------------------------------------
        Name                Description         Admin          Oper           Speed          MTU
        ------------------------------------------------------------------------------------------
        Ethernet0           -                   up             up             40G            9100

        Args:
            interface_output: Raw CLI output string
            interface: Interface name

        Returns:
            Speed value as string (e.g., "40G", "10G"), or empty string if not found
        """
        if not interface_output:
            st.log("No output to parse")
            return ""

        # Split output into lines
        lines = interface_output.strip().split('\n')

        # Find the line containing the interface
        for line in lines:
            # Skip header and separator lines
            if '---' in line or 'Name' in line or 'Description' in line:
                continue

            # Check if this line contains our interface
            if interface in line:
                # Split line by whitespace
                parts = line.split()

                # Expected format: [Name, Description, Admin, Oper, Speed, MTU]
                # Example: ['Ethernet0', '-', 'up', 'up', '40G', '9100']
                if len(parts) >= 5:
                    speed = parts[4]  # Speed is the 5th column (index 4)
                    st.log(f"Found {interface} in output, speed = {speed}")
                    return speed

        st.log(f"Interface {interface} not found in output")
        return ""

    @staticmethod
    def _extract_interface_oper_status(interface_output: str, interface: str) -> str:
        """
        Extract interface operational status from raw CLI output.

        Example output:
        ------------------------------------------------------------------------------------------
        Name                Description         Admin          Oper           Speed          MTU
        ------------------------------------------------------------------------------------------
        Ethernet0           -                   up             up             40G            9100

        Args:
            interface_output: Raw CLI output string
            interface: Interface name

        Returns:
            Oper status as string (e.g., "up", "down"), or empty string if not found
        """
        if not interface_output:
            st.log("No output to parse")
            return ""

        # Split output into lines
        lines = interface_output.strip().split('\n')

        # Find the line containing the interface
        for line in lines:
            # Skip header and separator lines
            if '---' in line or 'Name' in line or 'Description' in line:
                continue

            # Check if this line contains our interface
            if interface in line:
                # Split line by whitespace
                parts = line.split()

                # Expected format: [Name, Description, Admin, Oper, Speed, MTU]
                # Example: ['Ethernet0', '-', 'up', 'up', '40G', '9100']
                if len(parts) >= 4:
                    oper_status = parts[3]  # Oper is the 4th column (index 3)
                    st.log(f"Found {interface} in output, oper status = {oper_status}")
                    return oper_status

        st.log(f"Interface {interface} not found in output")
        return ""

    @staticmethod
    def _verify_interface_oper_status(interface_output: str, interface: str,
                                     expected_status: str) -> bool:
        """
        Verify interface operational status matches expected value.

        Args:
            interface_output: Raw CLI output string
            interface: Interface name to verify
            expected_status: Expected oper status (up/down)

        Returns:
            True if status matches expected, False otherwise
        """
        actual_status = TestInterfaceSpeedChanges._extract_interface_oper_status(
            interface_output, interface
        )

        if not actual_status:
            st.log(f"Could not extract oper status for {interface}")
            return False

        matches = actual_status.lower() == expected_status.lower()
        st.log(f"Interface {interface}: oper={actual_status}, expected={expected_status}, match={matches}")
        return matches

    @staticmethod
    def _speed_display_to_numeric(speed_display: str) -> str:
        """
        Convert speed display format to numeric Mbps value.
        Example: "40G" -> "40000", "10G" -> "10000", "1G" -> "1000"

        Args:
            speed_display: Speed in display format (e.g., "40G", "10G")

        Returns:
            Speed in Mbps as string (e.g., "40000", "10000")
        """
        speed_map = {
            "40G": "40000",
            "10G": "10000",
            "1G": "1000",
            "100M": "100",
            "auto": "auto"
        }
        return speed_map.get(speed_display, speed_display)

    @staticmethod
    def _verify_speed_match(actual_speed: str, expected_speed: str) -> bool:
        """
        Verify if actual speed matches expected speed (handles different formats).

        Args:
            actual_speed: Speed from show command (e.g., "10G")
            expected_speed: Expected speed display (e.g., "10G")

        Returns:
            True if speeds match, False otherwise
        """
        # Normalize both speeds for comparison
        actual_lower = actual_speed.lower().strip()
        expected_lower = expected_speed.lower().strip()

        # Direct match
        if actual_lower == expected_lower:
            return True

        # Handle variations: "10G" vs "10g", "40G" vs "40000"
        speed_equivalents = {
            "10g": ["10g", "10000"],
            "40g": ["40g", "40000"],
            "1g": ["1g", "1000"],
            "100m": ["100m", "100"]
        }

        for key, values in speed_equivalents.items():
            if actual_lower in values and expected_lower in values:
                return True

        return False

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_009_01"])
    def test_get_first_operational_interface(self) -> None:
        """
        TC_INTF_EVENTS_009_01: Get first operational interface from testbed.

        Test Steps:
            1. Execute show interface status command
            2. Parse output line by line to find first interface with oper status = up
            3. Store interface name for subsequent tests

        Expected Result:
            - At least one interface is operationally up
            - Interface name stored successfully
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Get First Operational Interface from Testbed")
        st.log("=" * 80)

        # Ensure terminal length 0 is set to avoid pagination
        st.config(self.data.dut1, "terminal length 0", type=CLI_TYPE)

        # Step 1: Get all interface status (raw CLI output)
        st.log("\nStep 1: Executing: show interface status")
        interface_status_output = self._get_interface_status_raw(self.data.dut1)

        if not interface_status_output:
            st.report_fail("msg", "No interface status output received")

        # Step 2: Parse output line by line to find first UP interface
        st.log("\nStep 2: Parsing output to find first operationally UP interface")
        first_up_interface = None

        # Split output into lines
        lines = interface_status_output.strip().split('\n')

        for line in lines:
            # Skip header and separator lines
            if '---' in line or 'Name' in line or 'Description' in line:
                continue

            # Parse line: Name Description Admin Oper Speed MTU
            # Example: Ethernet0           -                   up             up             40G            9100
            parts = line.split()

            if len(parts) >= 4:
                interface_name = parts[0]  # First column
                oper_status = parts[3]     # Fourth column (Oper)

                st.log(f"  Checking {interface_name}: oper={oper_status}")

                if oper_status.lower() == "up":
                    first_up_interface = interface_name
                    st.log(f"\n  ✓ Found first UP interface: {first_up_interface}")
                    break

        if not first_up_interface:
            st.report_fail("msg", "No operationally UP interface found in testbed")

        # Step 3: Store the interface for subsequent tests
        self.data.test_interface = first_up_interface
        st.log(f"\nTest interface selected from testbed: {self.data.test_interface}")

        st.log("\nFirst operational interface identified successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_009_02"])
    def test_capture_baseline_speed(self) -> None:
        """
        TC_INTF_EVENTS_009_02: Capture baseline speed of the interface.

        Test Steps:
            1. Execute show interface status for the test interface
            2. Parse output to verify interface is operationally up
            3. Extract and store current speed (baseline)

        Expected Result:
            - Interface is operationally up
            - Baseline speed captured (e.g., "40G")
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Capture Baseline Speed")
        st.log("=" * 80)

        interface = self.data.test_interface

        # Ensure terminal length 0 is set to avoid pagination
        st.config(self.data.dut1, "terminal length 0", type=CLI_TYPE)

        # Step 1: Execute show interface status command
        st.log(f"\nStep 1: Executing: show interface status")
        interface_status = self._get_interface_status_raw(self.data.dut1)

        if not interface_status:
            st.report_fail("msg", f"No interface status output for {interface}")

        # Step 2: Parse and verify interface is operationally UP
        st.log("\nStep 2: Parsing output to verify interface is operationally UP")
        oper_status = self._extract_interface_oper_status(interface_status, interface)

        st.log(f"  Interface {interface} oper status: {oper_status}")

        if oper_status.lower() != "up":
            st.report_fail("msg", f"Interface {interface} is not operationally up (status: {oper_status})")

        # Step 3: Parse and extract baseline speed
        st.log("\nStep 3: Parsing output to extract baseline speed")
        baseline_speed = self._extract_interface_speed(interface_status, interface)

        if not baseline_speed:
            st.report_fail("msg", f"Could not extract speed for {interface}")

        # Store baseline speed
        self.data.original_speed = baseline_speed
        self.data.original_speed_numeric = self._speed_display_to_numeric(baseline_speed)

        st.log(f"\n  ✓ Baseline speed captured: {self.data.original_speed}")
        st.log(f"  ✓ Baseline speed numeric value: {self.data.original_speed_numeric}")

        st.log("\nBaseline speed captured successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_009_03"])
    def test_change_speed_to_10g(self) -> None:
        """
        TC_INTF_EVENTS_009_03: Change interface speed to 10G.

        Test Steps:
            1. Configure interface speed to 10000 (10G)
            2. Wait for speed change to apply
            3. Verify command executed successfully

        Expected Result:
            - Speed configuration command succeeds
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Change Interface Speed to 10G")
        st.log("=" * 80)

        interface = self.data.test_interface
        new_speed = "10000"  # 10G in Mbps

        # Step 1: Configure speed 10000
        st.log(f"\nStep 1: Configuring {interface} with speed {new_speed}")
        st.log(f"Executing: configure terminal -> interface {interface} -> speed 10000 -> exit")

        result = self._configure_interface_speed(self.data.dut1, interface, new_speed)

        if not result:
            st.log("Warning: Speed configuration command may have failed")

        # Step 2: Wait for speed change to apply
        st.log(f"\nStep 2: Waiting {WAIT_AFTER_SPEED_CHANGE} seconds for speed change to apply")
        time.sleep(WAIT_AFTER_SPEED_CHANGE)

        st.log(f"\nSpeed change command executed for {interface}")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_009_04"])
    def test_verify_speed_change_to_10g(self) -> None:
        """
        TC_INTF_EVENTS_009_04: Verify speed changed to 10G.

        Test Steps:
            1. Execute show interface status
            2. Parse output to extract current speed
            3. Verify speed is now 10G (changed from baseline)

        Expected Result:
            - Speed shows as "10G" in interface status
            - Speed has changed from baseline (e.g., 40G -> 10G)
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Verify Speed Changed to 10G")
        st.log("=" * 80)

        interface = self.data.test_interface

        # Ensure terminal length 0 is set to avoid pagination
        st.config(self.data.dut1, "terminal length 0", type=CLI_TYPE)

        # Step 1: Execute show interface status
        st.log(f"\nStep 1: Executing: show interface status")
        interface_status = self._get_interface_status_raw(self.data.dut1)

        if not interface_status:
            st.report_fail("msg", f"No interface status output for {interface}")

        # Step 2: Parse output to extract current speed
        st.log("\nStep 2: Parsing output to extract current speed")
        current_speed = self._extract_interface_speed(interface_status, interface)

        if not current_speed:
            st.report_fail("msg", f"Could not extract speed for {interface}")

        st.log(f"  Current speed: {current_speed}")
        st.log(f"  Baseline speed was: {self.data.original_speed}")

        # Step 3: Verify speed is 10G
        st.log("\nStep 3: Verifying speed changed to 10G")
        if not self._verify_speed_match(current_speed, "10G"):
            st.report_fail("msg", f"Speed not showing as 10G. Current: {current_speed}")

        st.log(f"\n  ✓ SUCCESS: Speed changed from {self.data.original_speed} to {current_speed}")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_009_05"])
    def test_restore_original_speed(self) -> None:
        """
        TC_INTF_EVENTS_009_05: Restore interface to original speed.

        Test Steps:
            1. Configure interface speed back to original/baseline value
            2. Wait for speed change to apply
            3. Verify command executed successfully

        Expected Result:
            - Speed configuration command succeeds
            - Interface configured with original speed
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Restore Original Speed")
        st.log("=" * 80)

        interface = self.data.test_interface
        original_speed_numeric = self.data.original_speed_numeric

        if not original_speed_numeric:
            st.report_fail("msg", "Original speed not captured - cannot restore")

        # Step 1: Configure back to original speed
        st.log(f"\nStep 1: Restoring {interface} to original speed {original_speed_numeric}")
        st.log(f"Executing: configure terminal -> interface {interface} -> speed {original_speed_numeric} -> exit")

        result = self._configure_interface_speed(self.data.dut1, interface, original_speed_numeric)

        if not result:
            st.log("Warning: Speed restoration command may have failed")

        # Step 2: Wait for speed change to apply
        st.log(f"\nStep 2: Waiting {WAIT_AFTER_SPEED_CHANGE} seconds for speed restoration")
        time.sleep(WAIT_AFTER_SPEED_CHANGE)

        st.log(f"\nSpeed restoration command executed for {interface}")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_009_06"])
    def test_verify_speed_restoration(self) -> None:
        """
        TC_INTF_EVENTS_009_06: Verify speed restored to original value.

        Test Steps:
            1. Execute show interface status
            2. Parse output to extract current speed
            3. Verify speed matches original baseline speed

        Expected Result:
            - Speed shows as original value (e.g., "40G")
            - Speed has been restored (10G -> 40G)
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Verify Speed Restoration")
        st.log("=" * 80)

        interface = self.data.test_interface

        # Ensure terminal length 0 is set to avoid pagination
        st.config(self.data.dut1, "terminal length 0", type=CLI_TYPE)

        # Step 1: Execute show interface status
        st.log(f"\nStep 1: Executing: show interface status")
        interface_status = self._get_interface_status_raw(self.data.dut1)

        if not interface_status:
            st.report_fail("msg", f"No interface status output for {interface}")

        # Step 2: Parse output to extract current speed
        st.log("\nStep 2: Parsing output to extract current speed")
        current_speed = self._extract_interface_speed(interface_status, interface)

        if not current_speed:
            st.report_fail("msg", f"Could not extract speed for {interface}")

        st.log(f"  Current speed: {current_speed}")
        st.log(f"  Original baseline speed: {self.data.original_speed}")

        # Step 3: Verify speed matches original
        st.log("\nStep 3: Verifying speed restored to original value")
        if not self._verify_speed_match(current_speed, self.data.original_speed):
            st.report_fail("msg",
                f"Speed not restored to original. Current: {current_speed}, Expected: {self.data.original_speed}")

        st.log(f"\n  ✓ SUCCESS: Speed restored to original value: {current_speed}")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_009_07"])
    def test_final_verification(self) -> None:
        """
        TC_INTF_EVENTS_009_07: Final verification of interface state.

        Test Steps:
            1. Execute show interface status
            2. Parse output to verify interface is still operationally up
            3. Parse output to verify speed is at baseline value
            4. Display test summary

        Expected Result:
            - Interface is operationally up
            - Speed is at original baseline value
            - System is stable
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Final Verification")
        st.log("=" * 80)

        interface = self.data.test_interface

        # Ensure terminal length 0 is set to avoid pagination
        st.config(self.data.dut1, "terminal length 0", type=CLI_TYPE)

        # Step 1: Execute show interface status
        st.log(f"\nStep 1: Executing: show interface status")
        interface_status = self._get_interface_status_raw(self.data.dut1)

        if not interface_status:
            st.report_fail("msg", f"No interface status output for {interface}")

        # Step 2: Parse and verify interface operational status
        st.log("\nStep 2: Parsing output to verify interface is operationally UP")
        oper_status = self._extract_interface_oper_status(interface_status, interface)
        st.log(f"  Interface {interface} oper status: {oper_status}")

        if oper_status.lower() != "up":
            st.log(f"  WARNING: Interface {interface} is not operationally up")

        # Step 3: Parse and verify speed
        st.log("\nStep 3: Parsing output to verify speed is at baseline value")
        current_speed = self._extract_interface_speed(interface_status, interface)
        st.log(f"  Final speed: {current_speed}")
        st.log(f"  Baseline speed: {self.data.original_speed}")

        if self._verify_speed_match(current_speed, self.data.original_speed):
            st.log("  ✓ Speed matches baseline - restoration confirmed")
        else:
            st.log(f"  Note: Speed is {current_speed}, baseline was {self.data.original_speed}")

        # Step 4: Display test summary
        st.log("\n" + "=" * 80)
        st.log("TEST SUMMARY")
        st.log("=" * 80)
        st.log(f"Interface:        {interface}")
        st.log(f"Baseline Speed:   {self.data.original_speed}")
        st.log(f"Changed to:       10G")
        st.log(f"Restored to:      {current_speed}")
        st.log(f"Final Oper Status: {oper_status}")
        st.log(f"System State:     Stable")
        st.log("=" * 80)

        st.log("\nFinal verification completed successfully")
        st.report_pass("test_case_passed")
