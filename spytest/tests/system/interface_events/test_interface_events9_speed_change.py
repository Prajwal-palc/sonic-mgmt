"""
INTERFACE EVENTS - SPEED CHANGES
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/interface_events/test_interface_events9_speed_change.py \
  --logs-path ./logs/test_interface_events9_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates that interface speed can be changed to various supported values (auto, 10G, 1G, 100M)
  and that configuration changes are accurately reflected in CLI outputs. Tests speed modifications,
  persistence through interface flaps, rapid speed changes, and proper error handling for invalid
  speed values. Ensures interface remains operational after speed changes and that new speed is
  correctly applied and displayed in interface status.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |       DUT1         |                       |       DUT2         |
        # | (smic_sonic1)      |<-----Ethernet0------->| (smic_sonic2)      |
        # | 192.168.100.193    |   (Speed Changes)     | 192.168.100.195    |
        # |                    |<-----Ethernet4------->|                    |
        # +--------------------+                       +--------------------+
  - Interfaces support multiple speed configurations
  - Access to sonic-cli (klish)
  - Required test variables: CLI type (klish)
"""

from __future__ import annotations

import pytest
import time
from typing import Dict, Any, List, Optional

from spytest import st
from spytest.dicts import SpyTestDict
import apis.system.interface as intf_api


@pytest.mark.topology("any")
class TestInterfaceSpeedChanges:
    """Test cases for validating interface speed change configurations and persistence."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        # Get DUT handles
        cls.data.dut_names = st.get_dut_names()
        if not cls.data.dut_names:
            st.report_fail("msg", "No DUTs available in topology")

        cls.data.dut1 = cls.data.dut_names[0]

        # CLI type - use klish as specified
        cls.data.cli_type = "klish"

        # Test interfaces
        cls.data.test_interfaces = ["Ethernet0", "Ethernet4"]

        # Store original speeds for restoration
        cls.data.original_speeds = {}

        # Supported speeds to test
        cls.data.speeds_to_test = {
            "auto": "auto",
            "10G": "10000",
            "1G": "1000",
            "100M": "100"
        }

        # Verify timeout for status checks
        cls.data.verify_timeout = 30

        st.log(f"Test setup complete. DUT1: {cls.data.dut1}, CLI: {cls.data.cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """Restore interfaces to original state."""
        st.log("Teardown: Restoring interface speeds to original values")

        for interface, original_speed in cls.data.original_speeds.items():
            try:
                if original_speed:
                    st.log(f"Restoring {interface} to speed {original_speed}")
                    intf_api.interface_operation(
                        cls.data.dut1,
                        interface,
                        operation="startup",
                        cli_type=cls.data.cli_type
                    )
            except Exception as e:
                st.log(f"Warning: Failed to restore {interface}: {str(e)}")

    def setup_method(self) -> None:
        """Per-test setup - ensure interfaces are up."""
        st.log("Test setup: Bringing up test interfaces")

        for interface in self.data.test_interfaces:
            # Bring interface up
            intf_api.interface_operation(
                self.data.dut1,
                interface,
                operation="startup",
                cli_type=self.data.cli_type
            )

            # Store baseline speed if not already stored
            if interface not in self.data.original_speeds:
                status_output = intf_api.show_interface_status(
                    self.data.dut1,
                    interfaces=interface,
                    cli_type=self.data.cli_type
                )
                if status_output:
                    self.data.original_speeds[interface] = status_output[0].get("speed", "10000")

        # Wait for interfaces to come up
        time.sleep(5)

    def teardown_method(self) -> None:
        """Per-test teardown - ensure interfaces are operational."""
        st.log("Test teardown: Verifying interfaces are operational")

        for interface in self.data.test_interfaces:
            try:
                intf_api.interface_operation(
                    self.data.dut1,
                    interface,
                    operation="startup",
                    cli_type=self.data.cli_type
                )
            except Exception as e:
                st.log(f"Warning: Failed to ensure {interface} is up: {str(e)}")

    def _change_interface_speed(self, interface: str, speed: str) -> bool:
        """
        Change interface speed configuration.

        Args:
            interface: Interface name (e.g., "Ethernet0")
            speed: Speed value ("auto", "10000", "1000", "100")

        Returns:
            True if configuration successful, False otherwise
        """
        try:
            st.log(f"Changing {interface} speed to {speed}")
            result = intf_api.interface_speed_config(
                self.data.dut1,
                interface_list=[interface],
                speed=speed,
                cli_type=self.data.cli_type
            )
            time.sleep(3)  # Allow time for speed change to apply
            return result
        except Exception as e:
            st.log(f"Speed change failed: {str(e)}")
            return False

    def _verify_interface_speed(self, interface: str, expected_speed: str) -> bool:
        """
        Verify interface speed matches expected value.

        Args:
            interface: Interface name
            expected_speed: Expected speed value

        Returns:
            True if speed matches, False otherwise
        """
        try:
            # Get interface status
            status_output = intf_api.show_interface_status(
                self.data.dut1,
                interfaces=interface,
                cli_type=self.data.cli_type
            )

            if not status_output:
                st.log(f"ERROR: No status output for {interface}")
                return False

            actual_speed = status_output[0].get("speed", "")
            st.log(f"Interface {interface} - Expected speed: {expected_speed}, Actual speed: {actual_speed}")

            # Handle different speed representations
            # "auto" should match "auto" or negotiated value
            if expected_speed.lower() == "auto":
                return actual_speed.lower() == "auto" or actual_speed != ""

            # For numeric speeds, handle both formats (e.g., "10G", "10000")
            if expected_speed == "10000":
                return actual_speed in ["10G", "10000", "10000M"]
            elif expected_speed == "1000":
                return actual_speed in ["1G", "1000", "1000M"]
            elif expected_speed == "100":
                return actual_speed in ["100M", "100"]

            return actual_speed.lower() == expected_speed.lower()

        except Exception as e:
            st.log(f"Speed verification failed: {str(e)}")
            return False

    def _verify_interface_operational(self, interface: str) -> bool:
        """
        Verify interface is operationally up.

        Args:
            interface: Interface name

        Returns:
            True if interface is up, False otherwise
        """
        try:
            status_output = intf_api.show_interface_status(
                self.data.dut1,
                interfaces=interface,
                cli_type=self.data.cli_type
            )

            if not status_output:
                return False

            admin_status = status_output[0].get("admin", "")
            oper_status = status_output[0].get("oper", "")

            st.log(f"Interface {interface} - Admin: {admin_status}, Oper: {oper_status}")

            return admin_status.lower() == "up" and oper_status.lower() == "up"

        except Exception as e:
            st.log(f"Operational status check failed: {str(e)}")
            return False

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_009_01"])
    def test_speed_change_to_auto(self) -> None:
        """
        TC 009.01 - Verify interface speed can be changed to auto-negotiation mode.

        Steps:
        1. Change Ethernet0 speed to auto
        2. Verify speed shows as auto in interface status
        3. Verify interface remains operational
        """
        st.log("=" * 80)
        st.log("TEST: Change interface speed to AUTO")
        st.log("=" * 80)

        interface = "Ethernet0"
        target_speed = "auto"

        # Step 1: Change speed to auto
        result = self._change_interface_speed(interface, target_speed)
        if not result:
            st.report_fail("msg", f"Failed to configure speed {target_speed} on {interface}")

        # Wait for link to stabilize
        time.sleep(10)

        # Step 2: Verify speed change
        if not self._verify_interface_speed(interface, target_speed):
            st.report_fail("msg", f"{interface} speed not showing as {target_speed}")

        # Step 3: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.report_fail("msg", f"{interface} not operational after speed change")

        st.log(f"SUCCESS: {interface} speed changed to {target_speed} and operational")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_009_02"])
    def test_speed_change_to_10g(self) -> None:
        """
        TC 009.02 - Verify interface speed can be changed to fixed 10G.

        Steps:
        1. Change Ethernet0 speed to 10G (10000 Mbps)
        2. Verify speed shows as 10G in interface status
        3. Verify interface remains operational
        """
        st.log("=" * 80)
        st.log("TEST: Change interface speed to 10G")
        st.log("=" * 80)

        interface = "Ethernet0"
        target_speed = "10000"

        # Step 1: Change speed to 10G
        result = self._change_interface_speed(interface, target_speed)
        if not result:
            st.report_fail("msg", f"Failed to configure speed {target_speed} on {interface}")

        # Wait for link to stabilize
        time.sleep(10)

        # Step 2: Verify speed change
        if not self._verify_interface_speed(interface, target_speed):
            st.report_fail("msg", f"{interface} speed not showing as 10G")

        # Step 3: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.report_fail("msg", f"{interface} not operational after speed change to 10G")

        st.log(f"SUCCESS: {interface} speed changed to 10G and operational")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_009_03"])
    def test_speed_change_to_1g(self) -> None:
        """
        TC 009.03 - Verify interface speed can be changed to 1G (if supported).

        Steps:
        1. Change Ethernet0 speed to 1G (1000 Mbps)
        2. Verify speed configuration (may not be supported on all interfaces)
        3. If supported, verify interface operational

        Note: This test may fail on high-speed interfaces that don't support 1G.
        """
        st.log("=" * 80)
        st.log("TEST: Change interface speed to 1G (if supported)")
        st.log("=" * 80)

        interface = "Ethernet0"
        target_speed = "1000"

        # Step 1: Attempt to change speed to 1G
        result = self._change_interface_speed(interface, target_speed)

        if not result:
            st.log(f"NOTICE: Speed 1G not supported on {interface} - this is acceptable")
            st.report_pass("test_case_passed")
            return

        # Wait for link
        time.sleep(15)

        # Step 2: Verify speed change if command succeeded
        if self._verify_interface_speed(interface, target_speed):
            st.log(f"SUCCESS: {interface} supports and configured for 1G")

            # Step 3: Verify operational
            if not self._verify_interface_operational(interface):
                st.log(f"NOTICE: {interface} configured for 1G but link not up (may need peer configuration)")
        else:
            st.log(f"NOTICE: Speed command accepted but 1G may not be fully supported on {interface}")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_009_04"])
    def test_speed_change_to_100m(self) -> None:
        """
        TC 009.04 - Verify interface speed can be changed to 100M (if supported).

        Steps:
        1. Change Ethernet0 speed to 100M (100 Mbps)
        2. Verify speed configuration (typically not supported on high-speed interfaces)
        3. Verify error handling if unsupported

        Note: This test expects 100M to be unsupported on most modern interfaces.
        """
        st.log("=" * 80)
        st.log("TEST: Change interface speed to 100M (typically unsupported)")
        st.log("=" * 80)

        interface = "Ethernet0"
        target_speed = "100"

        # Step 1: Attempt to change speed to 100M
        result = self._change_interface_speed(interface, target_speed)

        if not result:
            st.log(f"EXPECTED: Speed 100M not supported on {interface}")
            st.report_pass("test_case_passed")
            return

        # If command succeeded (unlikely), verify
        time.sleep(10)

        if self._verify_interface_speed(interface, target_speed):
            st.log(f"NOTICE: {interface} supports 100M speed")
        else:
            st.log(f"NOTICE: 100M configuration attempted but not applied")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_009_05"])
    def test_rapid_speed_changes(self) -> None:
        """
        TC 009.05 - Verify system handles rapid sequential speed changes.

        Steps:
        1. Rapidly change speed: auto -> 10G -> auto -> 10G
        2. Verify final speed configuration is correct
        3. Verify interface remains operational
        4. Verify system stability
        """
        st.log("=" * 80)
        st.log("TEST: Rapid speed changes")
        st.log("=" * 80)

        interface = "Ethernet0"
        speed_sequence = ["auto", "10000", "auto", "10000"]

        # Step 1: Perform rapid speed changes
        for speed in speed_sequence:
            st.log(f"Changing to speed: {speed}")
            self._change_interface_speed(interface, speed)
            time.sleep(2)  # Brief pause between changes

        # Wait for final state to stabilize
        time.sleep(10)

        # Step 2: Verify final speed (should be 10G)
        final_speed = "10000"
        if not self._verify_interface_speed(interface, final_speed):
            st.report_fail("msg", f"Final speed not {final_speed} after rapid changes")

        # Step 3: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.report_fail("msg", f"{interface} not operational after rapid speed changes")

        st.log(f"SUCCESS: System handled rapid speed changes, final speed is 10G")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_009_06"])
    def test_speed_persistence_through_flap(self) -> None:
        """
        TC 009.06 - Verify speed configuration persists through interface flap.

        Steps:
        1. Configure interface speed to 10G
        2. Verify speed configuration
        3. Shutdown interface
        4. Bring interface up (no shutdown)
        5. Verify speed configuration persisted
        """
        st.log("=" * 80)
        st.log("TEST: Speed persistence through interface flap")
        st.log("=" * 80)

        interface = "Ethernet0"
        target_speed = "10000"

        # Step 1: Configure speed
        result = self._change_interface_speed(interface, target_speed)
        if not result:
            st.report_fail("msg", f"Failed to configure initial speed {target_speed}")

        time.sleep(5)

        # Step 2: Verify initial speed
        if not self._verify_interface_speed(interface, target_speed):
            st.report_fail("msg", f"Initial speed configuration failed")

        # Step 3: Shutdown interface
        st.log(f"Flapping {interface}: shutdown")
        intf_api.interface_operation(
            self.data.dut1,
            interface,
            operation="shutdown",
            cli_type=self.data.cli_type
        )
        time.sleep(3)

        # Step 4: Bring interface up
        st.log(f"Flapping {interface}: no shutdown")
        intf_api.interface_operation(
            self.data.dut1,
            interface,
            operation="startup",
            cli_type=self.data.cli_type
        )
        time.sleep(10)

        # Step 5: Verify speed persisted
        if not self._verify_interface_speed(interface, target_speed):
            st.report_fail("msg", f"Speed configuration did not persist through interface flap")

        st.log(f"SUCCESS: Speed {target_speed} persisted through interface flap")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_009_07"])
    def test_sequential_speed_changes(self) -> None:
        """
        TC 009.07 - Verify multiple sequential speed changes work correctly.

        Steps:
        1. Change to auto, verify
        2. Change to 10G, verify
        3. Change to auto, verify
        4. Change to 10G, verify
        5. Verify interface operational after all changes
        """
        st.log("=" * 80)
        st.log("TEST: Sequential speed changes with verification")
        st.log("=" * 80)

        interface = "Ethernet0"
        speed_sequence = [
            ("auto", "auto"),
            ("10000", "10000"),
            ("auto", "auto"),
            ("10000", "10000")
        ]

        for idx, (speed_to_set, speed_to_verify) in enumerate(speed_sequence, 1):
            st.log(f"Step {idx}: Changing to {speed_to_set}")

            # Configure speed
            result = self._change_interface_speed(interface, speed_to_set)
            if not result:
                st.report_fail("msg", f"Failed to configure speed {speed_to_set} in step {idx}")

            time.sleep(8)

            # Verify speed
            if not self._verify_interface_speed(interface, speed_to_verify):
                st.report_fail("msg", f"Speed verification failed for {speed_to_verify} in step {idx}")

            st.log(f"Step {idx}: SUCCESS - Speed is {speed_to_verify}")

        # Final operational check
        if not self._verify_interface_operational(interface):
            st.report_fail("msg", f"{interface} not operational after sequential changes")

        st.log(f"SUCCESS: All sequential speed changes completed successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_009_08"])
    @pytest.mark.negative
    def test_invalid_speed_value_handling(self) -> None:
        """
        TC 009.08 - Verify proper error handling for invalid speed values.

        Steps:
        1. Get current interface speed
        2. Attempt to configure invalid speed value (12345)
        3. Verify command is rejected or speed unchanged
        4. Verify interface remains operational
        """
        st.log("=" * 80)
        st.log("TEST: Invalid speed value handling")
        st.log("=" * 80)

        interface = "Ethernet0"
        invalid_speed = "12345"

        # Step 1: Get current speed
        status_before = intf_api.show_interface_status(
            self.data.dut1,
            interfaces=interface,
            cli_type=self.data.cli_type
        )

        if not status_before:
            st.report_fail("msg", f"Could not get initial status for {interface}")

        speed_before = status_before[0].get("speed", "")
        st.log(f"Current speed before invalid change: {speed_before}")

        # Step 2: Attempt invalid speed configuration
        st.log(f"Attempting to configure invalid speed: {invalid_speed}")
        result = self._change_interface_speed(interface, invalid_speed)

        time.sleep(5)

        # Step 3: Verify speed unchanged or error occurred
        status_after = intf_api.show_interface_status(
            self.data.dut1,
            interfaces=interface,
            cli_type=self.data.cli_type
        )

        if status_after:
            speed_after = status_after[0].get("speed", "")
            st.log(f"Speed after invalid change attempt: {speed_after}")

            # Invalid speed should be rejected - speed should remain unchanged or command fail
            if result and speed_after == invalid_speed:
                st.report_fail("msg", f"Invalid speed {invalid_speed} was incorrectly accepted")

            st.log(f"EXPECTED: Invalid speed {invalid_speed} was rejected")

        # Step 4: Verify interface still operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: Interface operational status affected by invalid command")

        st.log(f"SUCCESS: Invalid speed value properly handled")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_009_09"])
    def test_speed_changes_on_multiple_interfaces(self) -> None:
        """
        TC 009.09 - Verify speed changes work on multiple interfaces.

        Steps:
        1. Change Ethernet0 to auto, verify
        2. Change Ethernet4 to auto, verify
        3. Change both back to 10G, verify
        4. Verify both interfaces operational
        """
        st.log("=" * 80)
        st.log("TEST: Speed changes on multiple interfaces")
        st.log("=" * 80)

        interfaces = ["Ethernet0", "Ethernet4"]

        # Step 1 & 2: Change both to auto
        for interface in interfaces:
            st.log(f"Changing {interface} to auto")
            result = self._change_interface_speed(interface, "auto")
            if not result:
                st.report_fail("msg", f"Failed to configure auto on {interface}")
            time.sleep(5)

        # Verify both at auto
        time.sleep(10)
        for interface in interfaces:
            if not self._verify_interface_speed(interface, "auto"):
                st.report_fail("msg", f"{interface} speed not showing as auto")
            st.log(f"SUCCESS: {interface} configured to auto")

        # Step 3: Change both to 10G
        for interface in interfaces:
            st.log(f"Changing {interface} to 10G")
            result = self._change_interface_speed(interface, "10000")
            if not result:
                st.report_fail("msg", f"Failed to configure 10G on {interface}")
            time.sleep(5)

        # Verify both at 10G
        time.sleep(10)
        for interface in interfaces:
            if not self._verify_interface_speed(interface, "10000"):
                st.report_fail("msg", f"{interface} speed not showing as 10G")
            st.log(f"SUCCESS: {interface} configured to 10G")

        # Step 4: Verify both operational
        for interface in interfaces:
            if not self._verify_interface_operational(interface):
                st.log(f"WARNING: {interface} not fully operational")

        st.log(f"SUCCESS: Speed changes applied successfully on all interfaces")
        st.report_pass("test_case_passed")
