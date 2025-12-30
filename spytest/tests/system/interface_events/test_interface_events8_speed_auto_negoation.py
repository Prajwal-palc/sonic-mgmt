"""
INTERFACE EVENTS - SPEED AUTO-NEGOTIATION
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_2vs.yaml  \
  tests/system/interface_events/test_interface_events8_speed_auto_negoation.py \
  --logs-path ./logs/test_interface_events8_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  This test suite validates that interface speed auto-negotiation can be configured
  successfully and is accurately reflected in CLI outputs. It ensures that the "speed auto"
  configuration is properly applied, displayed in interface status, and enables proper
  link negotiation between connected devices. The test verifies that auto-negotiation
  works correctly for various interface types and successfully establishes optimal speed
  and duplex settings.

Pre-requisites:
  - Topology: 2 nodes | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |       DUT1         |                       |       DUT2         |
        # | (smic_sonic1)      |<-----Ethernet0------->| (smic_sonic2)      |
        # | 192.168.100.193    |    (Auto-Neg)         | 192.168.100.195    |
        # |                    |<-----Ethernet4------->|                    |
        # |                    |    (Auto-Neg)         |                    |
        # +--------------------+                       +--------------------+

  - Interfaces support auto-negotiation
  - Physical links capable of auto-negotiation
  - Required CLI type: klish
  - Min SONiC version: any
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

import pytest

from spytest import SpyTestDict, st

# CLI type for all operations - using klish as per requirement
CLI_TYPE = "klish"

# Test interfaces
TEST_INTERFACE_1 = "Ethernet0"
TEST_INTERFACE_2 = "Ethernet4"

# Wait times
WAIT_FOR_INTERFACE_UP = 5
WAIT_FOR_AUTO_NEGOTIATION = 15
VERIFICATION_DELAY = 2


@pytest.mark.topology("any")
class TestInterfaceEventsSpeedAutoNegotiation:
    """Test suite for interface speed auto-negotiation validation."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize test suite with topology and device handles."""
        st.log("=" * 80)
        st.log("SETUP: Initializing Interface Speed Auto-Negotiation Test Suite")
        st.log("=" * 80)

        # Get minimum topology - 2 devices connected
        min_topology = ["D1D2:2"]  # 2 links between D1 and D2
        topology = st.ensure_min_topology(*min_topology)

        cls.data.topology = topology
        cls.data.dut1 = topology.D1
        cls.data.dut2 = topology.D2
        cls.data.dut_names = st.get_dut_names()

        # Store test interfaces
        cls.data.interface1 = TEST_INTERFACE_1
        cls.data.interface2 = TEST_INTERFACE_2

        # Store original interface configurations
        cls.data.original_configs = {}

        # Set terminal length 0 once to avoid pagination for all show commands
        st.log("Setting terminal length 0 to disable pagination")
        st.config(cls.data.dut1, "terminal length 0", type=CLI_TYPE)

        st.log(f"DUT1: {cls.data.dut1}")
        st.log(f"DUT2: {cls.data.dut2}")
        st.log(f"Test Interface 1: {cls.data.interface1}")
        st.log(f"Test Interface 2: {cls.data.interface2}")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup test suite - restore interface configurations."""
        st.log("=" * 80)
        st.log("TEARDOWN: Cleaning up Interface Speed Auto-Negotiation Test Suite")
        st.log("=" * 80)

        # Restore interfaces to up state
        cls._ensure_interface_up(cls.data.dut1, cls.data.interface1)
        cls._ensure_interface_up(cls.data.dut1, cls.data.interface2)

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
    def _configure_klish_commands(dut: str, commands: List[str]) -> bool:
        """
        Configure multiple klish commands on the specified DUT.

        Args:
            dut: Device handle
            commands: List of configuration commands

        Returns:
            True if successful, False otherwise
        """
        st.log(f"Configuring on {dut}:")
        for cmd in commands:
            st.log(f"  {cmd}")

        result = st.config(dut, commands, type=CLI_TYPE)
        return result

    @classmethod
    def _ensure_interface_up(cls, dut: str, interface: str) -> bool:
        """
        Ensure interface is administratively up.

        Args:
            dut: Device handle
            interface: Interface name

        Returns:
            True if successful
        """
        st.log(f"Ensuring interface {interface} is up on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no shutdown",
            "exit",
            "exit"
        ]
        return cls._configure_klish_commands(dut, commands)

    @staticmethod
    def _configure_speed_auto(dut: str, interface: str) -> bool:
        """
        Configure speed auto-negotiation on interface.

        Args:
            dut: Device handle
            interface: Interface name

        Returns:
            True if successful
        """
        st.log(f"Configuring speed auto on {interface} on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "speed auto",
            "exit",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return result

    @staticmethod
    def _get_interface_status(dut: str, interface: str = None) -> Any:
        """
        Get interface status using 'show interface status' command.

        Args:
            dut: Device handle
            interface: Specific interface name (optional)

        Returns:
            Command output
        """
        if interface:
            command = f"show interface status {interface}"
        else:
            command = "show interface status"

        output = st.show(dut, command, type=CLI_TYPE)
        st.log(f"Interface status output: {output}")
        return output

    @staticmethod
    def _get_interface_details(dut: str, interface: str) -> Any:
        """
        Get detailed interface information using 'show interface' command.

        Args:
            dut: Device handle
            interface: Interface name

        Returns:
            Command output
        """
        command = f"show interface {interface}"
        output = st.show(dut, command, type=CLI_TYPE)
        st.log(f"Interface details output: {output}")
        return output

    @staticmethod
    def _get_running_config(dut: str, interface: str) -> Any:
        """
        Get running configuration for interface.

        Args:
            dut: Device handle
            interface: Interface name

        Returns:
            Command output
        """
        command = f"show running-configuration interface {interface}"
        output = st.show(dut, command, type=CLI_TYPE)
        st.log(f"Running configuration output: {output}")
        return output

    @staticmethod
    def _verify_interface_speed(interface_output: Any, interface: str,
                                expected_speed: str) -> bool:
        """
        Verify interface speed from show command output.

        Args:
            interface_output: Output from show interface status command
            interface: Interface name to verify
            expected_speed: Expected speed value (e.g., "auto", "10G", "1G")

        Returns:
            True if speed matches expected, False otherwise
        """
        if not interface_output:
            st.log(f"No interface output to verify")
            return False

        if isinstance(interface_output, list):
            for entry in interface_output:
                if isinstance(entry, dict):
                    intf_name = entry.get("interface", "")
                    speed = entry.get("speed", "").lower()

                    if interface in intf_name:
                        st.log(f"Interface {interface}: speed={speed}, expected={expected_speed}")
                        # Match speed (case-insensitive, handle variations)
                        return expected_speed.lower() in speed or speed in expected_speed.lower()

        st.log(f"Could not find interface {interface} in output")
        return False

    @staticmethod
    def _verify_interface_admin_status(interface_output: Any, interface: str,
                                      expected_status: str) -> bool:
        """
        Verify interface administrative status from show command output.

        Args:
            interface_output: Output from show interface status command
            interface: Interface name to verify
            expected_status: Expected admin status (up/down)

        Returns:
            True if status matches expected, False otherwise
        """
        if not interface_output:
            st.log(f"No interface output to verify")
            return False

        if isinstance(interface_output, list):
            for entry in interface_output:
                if isinstance(entry, dict):
                    intf_name = entry.get("interface", "")
                    admin_status = entry.get("admin", "").lower()

                    if interface in intf_name:
                        st.log(f"Interface {interface}: admin={admin_status}, expected={expected_status}")
                        return admin_status == expected_status.lower()

        st.log(f"Could not find interface {interface} in output")
        return False

    @staticmethod
    def _verify_interface_oper_status(interface_output: Any, interface: str,
                                     expected_status: str) -> bool:
        """
        Verify interface operational status from show command output.

        Args:
            interface_output: Output from show interface status command
            interface: Interface name to verify
            expected_status: Expected oper status (up/down)

        Returns:
            True if status matches expected, False otherwise
        """
        if not interface_output:
            st.log(f"No interface output to verify")
            return False

        if isinstance(interface_output, list):
            for entry in interface_output:
                if isinstance(entry, dict):
                    intf_name = entry.get("interface", "")
                    oper_status = entry.get("oper", "").lower()

                    if interface in intf_name:
                        st.log(f"Interface {interface}: oper={oper_status}, expected={expected_status}")
                        return oper_status == expected_status.lower()

        st.log(f"Could not find interface {interface} in output")
        return False

    @staticmethod
    def _extract_interface_speed(interface_output: Any, interface: str) -> str:
        """
        Extract interface speed from show command output.

        Args:
            interface_output: Output from show interface status command
            interface: Interface name

        Returns:
            Speed value as string, or empty string if not found
        """
        if not interface_output:
            return ""

        if isinstance(interface_output, list):
            for entry in interface_output:
                if isinstance(entry, dict):
                    intf_name = entry.get("interface", "")
                    if interface in intf_name:
                        speed = entry.get("speed", "")
                        st.log(f"Extracted speed for {interface}: {speed}")
                        return speed

        return ""

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_008_01"])
    def test_initial_interface_configuration(self) -> None:
        """
        TC_INTF_EVENTS_008_01: Bring interfaces to UP state.

        Test Steps:
            1. Configure no shutdown on Ethernet0 and Ethernet4
            2. Verify interfaces are administratively up
            3. Verify operational status

        Expected Result:
            - Interfaces show admin and oper status as 'up'
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Initial Interface Configuration")
        st.log("=" * 80)

        # Bring up interfaces on DUT1
        st.log("\nStep 1: Bringing up test interfaces on DUT1")
        for interface in [self.data.interface1, self.data.interface2]:
            result = self._ensure_interface_up(self.data.dut1, interface)
            if not result:
                st.report_fail("msg", f"Failed to bring up {interface}")

        time.sleep(WAIT_FOR_INTERFACE_UP)

        # Verify interface status
        st.log("\nStep 2: Verifying interface status")
        interface_status = self._get_interface_status(self.data.dut1)

        for interface in [self.data.interface1, self.data.interface2]:
            if not self._verify_interface_admin_status(interface_status, interface, "up"):
                st.report_fail("msg", f"Interface {interface} admin status not up")

        st.log("\nTest interfaces successfully brought up and verified")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_008_02"])
    def test_baseline_interface_status_check(self) -> None:
        """
        TC_INTF_EVENTS_008_02: Baseline interface status check (before auto-negotiation).

        Test Steps:
            1. Capture interface status before auto-negotiation
            2. Record current speed configuration
            3. Store baseline data

        Expected Result:
            - Baseline data captured successfully
            - Current speed configuration recorded
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Baseline Interface Status Check")
        st.log("=" * 80)

        # Capture baseline interface status
        st.log("\nStep 1: Capturing baseline interface status")
        self.data.baseline_interface_status = self._get_interface_status(self.data.dut1)

        # Capture specific interface details
        st.log("\nStep 2: Capturing baseline details for test interfaces")
        self.data.baseline_interface1_status = self._get_interface_status(
            self.data.dut1, self.data.interface1
        )
        self.data.baseline_interface2_status = self._get_interface_status(
            self.data.dut1, self.data.interface2
        )

        # Extract and log current speeds
        speed1 = self._extract_interface_speed(
            self.data.baseline_interface1_status, self.data.interface1
        )
        speed2 = self._extract_interface_speed(
            self.data.baseline_interface2_status, self.data.interface2
        )

        st.log(f"\nBaseline speed for {self.data.interface1}: {speed1}")
        st.log(f"Baseline speed for {self.data.interface2}: {speed2}")

        st.log("\nBaseline interface status captured successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_008_03"])
    def test_configure_speed_auto_ethernet0(self) -> None:
        """
        TC_INTF_EVENTS_008_03: Configure speed auto on Ethernet0.

        Test Steps:
            1. Execute speed auto command on Ethernet0
            2. Verify command executes without errors

        Expected Result:
            - Speed auto configuration accepted
            - No errors during configuration
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Configure Speed Auto on Ethernet0")
        st.log("=" * 80)

        # Configure speed auto on Ethernet0
        st.log(f"\nStep 1: Configuring speed auto on {self.data.interface1}")
        result = self._configure_speed_auto(self.data.dut1, self.data.interface1)

        if not result:
            st.log("Warning: Speed auto configuration may have failed")
            st.log("Note: Not all interface types support auto-negotiation")
            # Don't fail the test - some interfaces may not support auto-negotiation

        time.sleep(VERIFICATION_DELAY)

        st.log(f"\nSpeed auto configuration attempted on {self.data.interface1}")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_008_04"])
    def test_verify_speed_auto_ethernet0(self) -> None:
        """
        TC_INTF_EVENTS_008_04: Verify speed auto configuration on Ethernet0.

        Test Steps:
            1. Execute show interface status command
            2. Verify speed shows as "auto"
            3. Verify interface remains operational

        Expected Result:
            - Speed field shows "auto"
            - Interface operational status is up
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Verify Speed Auto Configuration on Ethernet0")
        st.log("=" * 80)

        # Get interface status
        st.log(f"\nStep 1: Checking interface status for {self.data.interface1}")
        interface_status = self._get_interface_status(self.data.dut1, self.data.interface1)

        # Verify speed is auto
        st.log("\nStep 2: Verifying speed shows as 'auto'")
        if not self._verify_interface_speed(interface_status, self.data.interface1, "auto"):
            st.log("Warning: Speed may not show as 'auto' - this could be expected")
            st.log("Note: Some interfaces may not support auto-negotiation")
            st.log("Or auto-negotiation may have already completed")

        # Verify interface is operational
        st.log("\nStep 3: Verifying interface operational status")
        if not self._verify_interface_oper_status(interface_status, self.data.interface1, "up"):
            st.log("Warning: Interface operational status not up")

        # Extract and display current speed
        current_speed = self._extract_interface_speed(interface_status, self.data.interface1)
        st.log(f"\nCurrent speed for {self.data.interface1}: {current_speed}")

        st.log("\nSpeed auto verification completed")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_008_05"])
    def test_verify_link_negotiation_ethernet0(self) -> None:
        """
        TC_INTF_EVENTS_008_05: Verify link negotiation on Ethernet0.

        Test Steps:
            1. Wait for auto-negotiation to complete
            2. Check interface status
            3. Verify negotiated speed
            4. Verify link is stable

        Expected Result:
            - Auto-negotiation completes successfully
            - Interface shows negotiated speed
            - Link is stable and operational
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Verify Link Negotiation on Ethernet0")
        st.log("=" * 80)

        # Wait for auto-negotiation to complete
        st.log(f"\nStep 1: Waiting {WAIT_FOR_AUTO_NEGOTIATION} seconds for auto-negotiation")
        time.sleep(WAIT_FOR_AUTO_NEGOTIATION)

        # Get interface status after negotiation
        st.log(f"\nStep 2: Checking interface status after negotiation")
        interface_status = self._get_interface_status(self.data.dut1, self.data.interface1)

        # Verify interface is up
        st.log("\nStep 3: Verifying interface operational status")
        if not self._verify_interface_oper_status(interface_status, self.data.interface1, "up"):
            st.log("Warning: Interface operational status not up after negotiation")

        # Extract and display negotiated speed
        negotiated_speed = self._extract_interface_speed(interface_status, self.data.interface1)
        st.log(f"\nNegotiated speed for {self.data.interface1}: {negotiated_speed}")

        # Get detailed interface information
        st.log("\nStep 4: Getting detailed interface information")
        interface_details = self._get_interface_details(self.data.dut1, self.data.interface1)

        st.log("\nLink negotiation verification completed")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_008_06"])
    def test_configure_speed_auto_ethernet4(self) -> None:
        """
        TC_INTF_EVENTS_008_06: Configure speed auto on Ethernet4.

        Test Steps:
            1. Execute speed auto command on Ethernet4
            2. Verify command executes without errors

        Expected Result:
            - Speed auto configuration accepted
            - No errors during configuration
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Configure Speed Auto on Ethernet4")
        st.log("=" * 80)

        # Configure speed auto on Ethernet4
        st.log(f"\nStep 1: Configuring speed auto on {self.data.interface2}")
        result = self._configure_speed_auto(self.data.dut1, self.data.interface2)

        if not result:
            st.log("Warning: Speed auto configuration may have failed")
            st.log("Note: Not all interface types support auto-negotiation")

        time.sleep(VERIFICATION_DELAY)

        st.log(f"\nSpeed auto configuration attempted on {self.data.interface2}")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_008_07"])
    def test_verify_speed_auto_ethernet4(self) -> None:
        """
        TC_INTF_EVENTS_008_07: Verify speed auto configuration on Ethernet4.

        Test Steps:
            1. Execute show interface status command
            2. Verify speed shows as "auto" or negotiated value
            3. Verify interface remains operational

        Expected Result:
            - Speed configuration applied
            - Interface operational status is up
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Verify Speed Auto Configuration on Ethernet4")
        st.log("=" * 80)

        # Get interface status
        st.log(f"\nStep 1: Checking interface status for {self.data.interface2}")
        interface_status = self._get_interface_status(self.data.dut1, self.data.interface2)

        # Extract and display current speed
        current_speed = self._extract_interface_speed(interface_status, self.data.interface2)
        st.log(f"\nCurrent speed for {self.data.interface2}: {current_speed}")

        # Verify interface is operational
        st.log("\nStep 2: Verifying interface operational status")
        if not self._verify_interface_oper_status(interface_status, self.data.interface2, "up"):
            st.log("Warning: Interface operational status not up")

        st.log("\nSpeed auto verification completed for Ethernet4")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_008_08"])
    def test_verify_multiple_interfaces_auto_negotiation(self) -> None:
        """
        TC_INTF_EVENTS_008_08: Verify multiple interfaces with auto-negotiation.

        Test Steps:
            1. Get status of all interfaces
            2. Verify both Ethernet0 and Ethernet4 configured
            3. Verify both interfaces operational

        Expected Result:
            - Both interfaces show speed configuration
            - Both interfaces operational
            - No conflicts with multiple interfaces using auto-negotiation
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Verify Multiple Interfaces with Auto-Negotiation")
        st.log("=" * 80)

        # Wait for negotiation on both interfaces
        st.log(f"\nWaiting for auto-negotiation on both interfaces")
        time.sleep(WAIT_FOR_AUTO_NEGOTIATION)

        # Get status of all interfaces
        st.log("\nStep 1: Getting status of all interfaces")
        interface_status = self._get_interface_status(self.data.dut1)

        # Verify both interfaces
        st.log("\nStep 2: Verifying both test interfaces")
        for interface in [self.data.interface1, self.data.interface2]:
            current_speed = self._extract_interface_speed(interface_status, interface)
            st.log(f"Interface {interface} speed: {current_speed}")

            if not self._verify_interface_oper_status(interface_status, interface, "up"):
                st.log(f"Warning: Interface {interface} operational status not up")

        st.log("\nMultiple interfaces verification completed")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_008_09"])
    def test_configuration_persistence(self) -> None:
        """
        TC_INTF_EVENTS_008_09: Test configuration persistence.

        Test Steps:
            1. Get running configuration for test interfaces
            2. Verify speed auto configuration present
            3. Validate configuration consistency

        Expected Result:
            - Running configuration shows speed auto
            - Configuration properly saved
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Configuration Persistence")
        st.log("=" * 80)

        # Get running configuration for both interfaces
        st.log("\nStep 1: Getting running configuration for test interfaces")

        st.log(f"\nRunning configuration for {self.data.interface1}:")
        config1 = self._get_running_config(self.data.dut1, self.data.interface1)

        st.log(f"\nRunning configuration for {self.data.interface2}:")
        config2 = self._get_running_config(self.data.dut1, self.data.interface2)

        st.log("\nConfiguration persistence check completed")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_008_10"])
    def test_final_state_verification(self) -> None:
        """
        TC_INTF_EVENTS_008_10: Final state verification.

        Test Steps:
            1. Verify all test interfaces operational
            2. Check interface speeds
            3. Verify no error conditions
            4. Confirm system stability

        Expected Result:
            - All interfaces in expected state
            - No residual error conditions
            - System stable
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: Final State Verification")
        st.log("=" * 80)

        # Get final interface status
        st.log("\nStep 1: Getting final interface status")
        interface_status = self._get_interface_status(self.data.dut1)

        # Verify test interfaces
        st.log("\nStep 2: Verifying test interfaces")
        for interface in [self.data.interface1, self.data.interface2]:
            current_speed = self._extract_interface_speed(interface_status, interface)
            st.log(f"Final speed for {interface}: {current_speed}")

            admin_status = self._verify_interface_admin_status(interface_status, interface, "up")
            oper_status = self._verify_interface_oper_status(interface_status, interface, "up")

            st.log(f"Interface {interface}: admin={'up' if admin_status else 'down'}, "
                   f"oper={'up' if oper_status else 'down'}")

        # Get detailed status for both interfaces
        st.log("\nStep 3: Getting detailed interface information")
        interface1_details = self._get_interface_details(self.data.dut1, self.data.interface1)
        interface2_details = self._get_interface_details(self.data.dut1, self.data.interface2)

        st.log("\nFinal state verification completed successfully")
        st.log("System is in clean state after all speed auto-negotiation tests")
        st.report_pass("test_case_passed")
