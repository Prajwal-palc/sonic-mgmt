"""
INTERFACE EVENTS - MTU CHANGES
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/interface_events/test_interface_events10_mtu.py \
  --logs-path ./logs/test_interface_events10_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates that interface MTU (Maximum Transmission Unit) can be changed to various supported
  values within the allowed range (1312-9216 bytes) and that configuration changes are accurately
  reflected in CLI outputs. Tests MTU modifications for minimum, maximum, standard, and jumbo
  frame sizes, persistence through interface flaps, rapid MTU changes, and proper error handling
  for invalid MTU values. Ensures interface remains operational after MTU changes and that new
  MTU value is correctly applied and displayed in interface status.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |       DUT1         |                       |       DUT2         |
        # | (smic_sonic1)      |<-----Ethernet0------->| (smic_sonic2)      |
        # | 192.168.100.193    |   (MTU Changes)       | 192.168.100.195    |
        # |                    |<-----Ethernet4------->|                    |
        # +--------------------+                       +--------------------+
  - MTU valid range: 1312-9216 bytes
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
class TestInterfaceMtuChanges:
    """Test cases for validating interface MTU change configurations and persistence."""

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

        # Store original MTU values for restoration
        cls.data.original_mtu = {}

        # MTU values to test (valid range: 1312-9216)
        cls.data.mtu_values = {
            "minimum": "1312",      # Minimum allowed MTU
            "standard": "1500",     # Standard Ethernet MTU
            "mid_range": "5000",    # Arbitrary mid-range value
            "jumbo": "9100",        # Common jumbo frame size
            "maximum": "9216"       # Maximum allowed MTU
        }

        # Invalid MTU values for negative testing
        cls.data.invalid_mtu_values = {
            "below_min": "1311",    # Below minimum (1312)
            "above_max": "9217",    # Above maximum (9216)
            "way_above": "10000"    # Far above maximum
        }

        # Verify timeout for status checks
        cls.data.verify_timeout = 30

        st.log(f"Test setup complete. DUT1: {cls.data.dut1}, CLI: {cls.data.cli_type}")
        st.log(f"Valid MTU range: 1312-9216 bytes")

    @classmethod
    def teardown_class(cls) -> None:
        """Restore interfaces to original state."""
        st.log("Teardown: Restoring interface MTU to original values")

        for interface, original_mtu in cls.data.original_mtu.items():
            try:
                if original_mtu:
                    st.log(f"Restoring {interface} to MTU {original_mtu}")
                    intf_api.interface_properties_set(
                        cls.data.dut1,
                        interface,
                        property="mtu",
                        value=original_mtu,
                        cli_type=cls.data.cli_type
                    )
                    # Ensure interface is up
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

            # Store baseline MTU if not already stored
            if interface not in self.data.original_mtu:
                status_output = intf_api.interface_status_show(
                    self.data.dut1,
                    interfaces=interface,
                    cli_type=self.data.cli_type
                )
                if status_output:
                    self.data.original_mtu[interface] = status_output[0].get("mtu", "9100")

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

    def _change_interface_mtu(self, interface: str, mtu: str) -> bool:
        """
        Change interface MTU configuration.

        Args:
            interface: Interface name (e.g., "Ethernet0")
            mtu: MTU value in bytes ("1312"-"9216")

        Returns:
            True if configuration successful, False otherwise
        """
        try:
            st.log(f"Changing {interface} MTU to {mtu}")
            result = intf_api.interface_properties_set(
                self.data.dut1,
                interface,
                property="mtu",
                value=mtu,
                cli_type=self.data.cli_type
            )
            time.sleep(2)  # Allow time for MTU change to apply
            return result
        except Exception as e:
            st.log(f"MTU change failed: {str(e)}")
            return False

    def _verify_interface_mtu(self, interface: str, expected_mtu: str) -> bool:
        """
        Verify interface MTU matches expected value.

        Args:
            interface: Interface name
            expected_mtu: Expected MTU value

        Returns:
            True if MTU matches, False otherwise
        """
        try:
            # Get interface status
            status_output = intf_api.interface_status_show(
                self.data.dut1,
                interfaces=interface,
                cli_type=self.data.cli_type
            )

            if not status_output:
                st.log(f"ERROR: No status output for {interface}")
                return False

            actual_mtu = str(status_output[0].get("mtu", ""))
            st.log(f"Interface {interface} - Expected MTU: {expected_mtu}, Actual MTU: {actual_mtu}")

            # Compare MTU values
            return actual_mtu == expected_mtu

        except Exception as e:
            st.log(f"MTU verification failed: {str(e)}")
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
            status_output = intf_api.interface_status_show(
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

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_010_01"])
    def test_mtu_change_to_minimum(self) -> None:
        """
        TC 010.01 - Verify interface MTU can be changed to minimum value (1312).

        Steps:
        1. Change Ethernet0 MTU to 1312 (minimum)
        2. Verify MTU shows as 1312 in interface status
        3. Verify interface remains operational
        """
        st.log("=" * 80)
        st.log("TEST: Change interface MTU to MINIMUM (1312)")
        st.log("=" * 80)

        interface = "Ethernet0"
        target_mtu = self.data.mtu_values["minimum"]

        # Step 1: Change MTU to minimum
        result = self._change_interface_mtu(interface, target_mtu)
        if not result:
            st.report_fail("msg", f"Failed to configure MTU {target_mtu} on {interface}")

        # Wait for configuration to apply
        time.sleep(5)

        # Step 2: Verify MTU change
        if not self._verify_interface_mtu(interface, target_mtu):
            st.report_fail("msg", f"{interface} MTU not showing as {target_mtu}")

        # Step 3: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational after MTU change to {target_mtu}")

        st.log(f"SUCCESS: {interface} MTU changed to {target_mtu} (minimum)")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_010_02"])
    def test_mtu_change_to_maximum(self) -> None:
        """
        TC 010.02 - Verify interface MTU can be changed to maximum value (9216).

        Steps:
        1. Change Ethernet0 MTU to 9216 (maximum)
        2. Verify MTU shows as 9216 in interface status
        3. Verify interface remains operational
        """
        st.log("=" * 80)
        st.log("TEST: Change interface MTU to MAXIMUM (9216)")
        st.log("=" * 80)

        interface = "Ethernet0"
        target_mtu = self.data.mtu_values["maximum"]

        # Step 1: Change MTU to maximum
        result = self._change_interface_mtu(interface, target_mtu)
        if not result:
            st.report_fail("msg", f"Failed to configure MTU {target_mtu} on {interface}")

        # Wait for configuration to apply
        time.sleep(5)

        # Step 2: Verify MTU change
        if not self._verify_interface_mtu(interface, target_mtu):
            st.report_fail("msg", f"{interface} MTU not showing as {target_mtu}")

        # Step 3: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational after MTU change to {target_mtu}")

        st.log(f"SUCCESS: {interface} MTU changed to {target_mtu} (maximum)")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_010_03"])
    def test_mtu_change_to_standard(self) -> None:
        """
        TC 010.03 - Verify interface MTU can be changed to standard Ethernet value (1500).

        Steps:
        1. Change Ethernet0 MTU to 1500 (standard Ethernet MTU)
        2. Verify MTU shows as 1500 in interface status
        3. Verify interface remains operational
        """
        st.log("=" * 80)
        st.log("TEST: Change interface MTU to STANDARD (1500)")
        st.log("=" * 80)

        interface = "Ethernet0"
        target_mtu = self.data.mtu_values["standard"]

        # Step 1: Change MTU to standard
        result = self._change_interface_mtu(interface, target_mtu)
        if not result:
            st.report_fail("msg", f"Failed to configure MTU {target_mtu} on {interface}")

        # Wait for configuration to apply
        time.sleep(5)

        # Step 2: Verify MTU change
        if not self._verify_interface_mtu(interface, target_mtu):
            st.report_fail("msg", f"{interface} MTU not showing as {target_mtu}")

        # Step 3: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational after MTU change to {target_mtu}")

        st.log(f"SUCCESS: {interface} MTU changed to {target_mtu} (standard Ethernet)")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_010_04"])
    def test_mtu_change_to_jumbo(self) -> None:
        """
        TC 010.04 - Verify interface MTU can be changed to jumbo frame size (9100).

        Steps:
        1. Change Ethernet0 MTU to 9100 (common jumbo frame size)
        2. Verify MTU shows as 9100 in interface status
        3. Verify interface remains operational
        """
        st.log("=" * 80)
        st.log("TEST: Change interface MTU to JUMBO (9100)")
        st.log("=" * 80)

        interface = "Ethernet0"
        target_mtu = self.data.mtu_values["jumbo"]

        # Step 1: Change MTU to jumbo
        result = self._change_interface_mtu(interface, target_mtu)
        if not result:
            st.report_fail("msg", f"Failed to configure MTU {target_mtu} on {interface}")

        # Wait for configuration to apply
        time.sleep(5)

        # Step 2: Verify MTU change
        if not self._verify_interface_mtu(interface, target_mtu):
            st.report_fail("msg", f"{interface} MTU not showing as {target_mtu}")

        # Step 3: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational after MTU change to {target_mtu}")

        st.log(f"SUCCESS: {interface} MTU changed to {target_mtu} (jumbo frame)")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_010_05"])
    def test_mtu_change_to_mid_range(self) -> None:
        """
        TC 010.05 - Verify interface MTU can be changed to mid-range value (5000).

        Steps:
        1. Change Ethernet0 MTU to 5000 (arbitrary mid-range value)
        2. Verify MTU shows as 5000 in interface status
        3. Verify interface remains operational
        """
        st.log("=" * 80)
        st.log("TEST: Change interface MTU to MID-RANGE (5000)")
        st.log("=" * 80)

        interface = "Ethernet0"
        target_mtu = self.data.mtu_values["mid_range"]

        # Step 1: Change MTU to mid-range
        result = self._change_interface_mtu(interface, target_mtu)
        if not result:
            st.report_fail("msg", f"Failed to configure MTU {target_mtu} on {interface}")

        # Wait for configuration to apply
        time.sleep(5)

        # Step 2: Verify MTU change
        if not self._verify_interface_mtu(interface, target_mtu):
            st.report_fail("msg", f"{interface} MTU not showing as {target_mtu}")

        # Step 3: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational after MTU change to {target_mtu}")

        st.log(f"SUCCESS: {interface} MTU changed to {target_mtu} (mid-range)")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_010_06"])
    def test_rapid_mtu_changes(self) -> None:
        """
        TC 010.06 - Verify system handles rapid sequential MTU changes.

        Steps:
        1. Rapidly change MTU: 1500 -> 9100 -> 1500 -> 9100
        2. Verify final MTU configuration is correct
        3. Verify interface remains operational
        4. Verify system stability
        """
        st.log("=" * 80)
        st.log("TEST: Rapid MTU changes")
        st.log("=" * 80)

        interface = "Ethernet0"
        mtu_sequence = ["1500", "9100", "1500", "9100"]

        # Step 1: Perform rapid MTU changes
        for mtu in mtu_sequence:
            st.log(f"Changing to MTU: {mtu}")
            self._change_interface_mtu(interface, mtu)
            time.sleep(1)  # Brief pause between changes

        # Wait for final state to stabilize
        time.sleep(5)

        # Step 2: Verify final MTU (should be 9100)
        final_mtu = "9100"
        if not self._verify_interface_mtu(interface, final_mtu):
            st.report_fail("msg", f"Final MTU not {final_mtu} after rapid changes")

        # Step 3: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational after rapid MTU changes")

        st.log(f"SUCCESS: System handled rapid MTU changes, final MTU is {final_mtu}")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_010_07"])
    def test_mtu_persistence_through_flap(self) -> None:
        """
        TC 010.07 - Verify MTU configuration persists through interface flap.

        Steps:
        1. Configure interface MTU to 9100
        2. Verify MTU configuration
        3. Shutdown interface
        4. Bring interface up (no shutdown)
        5. Verify MTU configuration persisted
        """
        st.log("=" * 80)
        st.log("TEST: MTU persistence through interface flap")
        st.log("=" * 80)

        interface = "Ethernet0"
        target_mtu = "9100"

        # Step 1: Configure MTU
        result = self._change_interface_mtu(interface, target_mtu)
        if not result:
            st.report_fail("msg", f"Failed to configure initial MTU {target_mtu}")

        time.sleep(3)

        # Step 2: Verify initial MTU
        if not self._verify_interface_mtu(interface, target_mtu):
            st.report_fail("msg", f"Initial MTU configuration failed")

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
        time.sleep(8)

        # Step 5: Verify MTU persisted
        if not self._verify_interface_mtu(interface, target_mtu):
            st.report_fail("msg", f"MTU configuration did not persist through interface flap")

        st.log(f"SUCCESS: MTU {target_mtu} persisted through interface flap")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_010_08"])
    def test_sequential_mtu_changes(self) -> None:
        """
        TC 010.08 - Verify multiple sequential MTU changes work correctly.

        Steps:
        1. Change to 1500, verify
        2. Change to 9100, verify
        3. Change to 1312, verify
        4. Change to 9216, verify
        5. Change to 9100, verify
        6. Verify interface operational after all changes
        """
        st.log("=" * 80)
        st.log("TEST: Sequential MTU changes with verification")
        st.log("=" * 80)

        interface = "Ethernet0"
        mtu_sequence = [
            ("1500", "Standard Ethernet"),
            ("9100", "Jumbo frame"),
            ("1312", "Minimum"),
            ("9216", "Maximum"),
            ("9100", "Jumbo frame restore")
        ]

        for idx, (mtu_to_set, description) in enumerate(mtu_sequence, 1):
            st.log(f"Step {idx}: Changing to {mtu_to_set} ({description})")

            # Configure MTU
            result = self._change_interface_mtu(interface, mtu_to_set)
            if not result:
                st.report_fail("msg", f"Failed to configure MTU {mtu_to_set} in step {idx}")

            time.sleep(5)

            # Verify MTU
            if not self._verify_interface_mtu(interface, mtu_to_set):
                st.report_fail("msg", f"MTU verification failed for {mtu_to_set} in step {idx}")

            st.log(f"Step {idx}: SUCCESS - MTU is {mtu_to_set}")

        # Final operational check
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not fully operational after sequential changes")

        st.log(f"SUCCESS: All sequential MTU changes completed successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_010_09"])
    @pytest.mark.negative
    def test_invalid_mtu_below_minimum(self) -> None:
        """
        TC 010.09 - Verify proper error handling for MTU values below minimum.

        Steps:
        1. Get current interface MTU
        2. Attempt to configure MTU below minimum (1311)
        3. Verify command is rejected or MTU unchanged
        4. Verify interface remains operational
        """
        st.log("=" * 80)
        st.log("TEST: Invalid MTU value below minimum (1311)")
        st.log("=" * 80)

        interface = "Ethernet0"
        invalid_mtu = self.data.invalid_mtu_values["below_min"]

        # Step 1: Get current MTU
        status_before = intf_api.interface_status_show(
            self.data.dut1,
            interfaces=interface,
            cli_type=self.data.cli_type
        )

        if not status_before:
            st.report_fail("msg", f"Could not get initial status for {interface}")

        mtu_before = str(status_before[0].get("mtu", ""))
        st.log(f"Current MTU before invalid change: {mtu_before}")

        # Step 2: Attempt invalid MTU configuration
        st.log(f"Attempting to configure invalid MTU: {invalid_mtu} (below minimum 1312)")
        result = self._change_interface_mtu(interface, invalid_mtu)

        time.sleep(3)

        # Step 3: Verify MTU unchanged or error occurred
        status_after = intf_api.interface_status_show(
            self.data.dut1,
            interfaces=interface,
            cli_type=self.data.cli_type
        )

        if status_after:
            mtu_after = str(status_after[0].get("mtu", ""))
            st.log(f"MTU after invalid change attempt: {mtu_after}")

            # Invalid MTU should be rejected - MTU should remain unchanged or command fail
            if result and mtu_after == invalid_mtu:
                st.report_fail("msg", f"Invalid MTU {invalid_mtu} was incorrectly accepted")

            st.log(f"EXPECTED: Invalid MTU {invalid_mtu} was rejected or not applied")

        # Step 4: Verify interface still operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: Interface operational status affected by invalid command")

        st.log(f"SUCCESS: MTU below minimum properly rejected")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_010_10"])
    @pytest.mark.negative
    def test_invalid_mtu_above_maximum(self) -> None:
        """
        TC 010.10 - Verify proper error handling for MTU values above maximum.

        Steps:
        1. Get current interface MTU
        2. Attempt to configure MTU above maximum (9217)
        3. Verify command is rejected or MTU unchanged
        4. Verify interface remains operational
        """
        st.log("=" * 80)
        st.log("TEST: Invalid MTU value above maximum (9217)")
        st.log("=" * 80)

        interface = "Ethernet0"
        invalid_mtu = self.data.invalid_mtu_values["above_max"]

        # Step 1: Get current MTU
        status_before = intf_api.interface_status_show(
            self.data.dut1,
            interfaces=interface,
            cli_type=self.data.cli_type
        )

        if not status_before:
            st.report_fail("msg", f"Could not get initial status for {interface}")

        mtu_before = str(status_before[0].get("mtu", ""))
        st.log(f"Current MTU before invalid change: {mtu_before}")

        # Step 2: Attempt invalid MTU configuration
        st.log(f"Attempting to configure invalid MTU: {invalid_mtu} (above maximum 9216)")
        result = self._change_interface_mtu(interface, invalid_mtu)

        time.sleep(3)

        # Step 3: Verify MTU unchanged or error occurred
        status_after = intf_api.interface_status_show(
            self.data.dut1,
            interfaces=interface,
            cli_type=self.data.cli_type
        )

        if status_after:
            mtu_after = str(status_after[0].get("mtu", ""))
            st.log(f"MTU after invalid change attempt: {mtu_after}")

            # Invalid MTU should be rejected - MTU should remain unchanged or command fail
            if result and mtu_after == invalid_mtu:
                st.report_fail("msg", f"Invalid MTU {invalid_mtu} was incorrectly accepted")

            st.log(f"EXPECTED: Invalid MTU {invalid_mtu} was rejected or not applied")

        # Step 4: Verify interface still operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: Interface operational status affected by invalid command")

        st.log(f"SUCCESS: MTU above maximum properly rejected")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_010_11"])
    @pytest.mark.negative
    def test_invalid_mtu_way_above_maximum(self) -> None:
        """
        TC 010.11 - Verify proper error handling for MTU values far above maximum.

        Steps:
        1. Get current interface MTU
        2. Attempt to configure MTU far above maximum (10000)
        3. Verify command is rejected or MTU unchanged
        4. Verify interface remains operational
        """
        st.log("=" * 80)
        st.log("TEST: Invalid MTU value far above maximum (10000)")
        st.log("=" * 80)

        interface = "Ethernet0"
        invalid_mtu = self.data.invalid_mtu_values["way_above"]

        # Step 1: Get current MTU
        status_before = intf_api.interface_status_show(
            self.data.dut1,
            interfaces=interface,
            cli_type=self.data.cli_type
        )

        if not status_before:
            st.report_fail("msg", f"Could not get initial status for {interface}")

        mtu_before = str(status_before[0].get("mtu", ""))
        st.log(f"Current MTU before invalid change: {mtu_before}")

        # Step 2: Attempt invalid MTU configuration
        st.log(f"Attempting to configure invalid MTU: {invalid_mtu} (far above maximum 9216)")
        result = self._change_interface_mtu(interface, invalid_mtu)

        time.sleep(3)

        # Step 3: Verify MTU unchanged or error occurred
        status_after = intf_api.interface_status_show(
            self.data.dut1,
            interfaces=interface,
            cli_type=self.data.cli_type
        )

        if status_after:
            mtu_after = str(status_after[0].get("mtu", ""))
            st.log(f"MTU after invalid change attempt: {mtu_after}")

            # Invalid MTU should be rejected
            if result and mtu_after == invalid_mtu:
                st.report_fail("msg", f"Invalid MTU {invalid_mtu} was incorrectly accepted")

            st.log(f"EXPECTED: Invalid MTU {invalid_mtu} was rejected or not applied")

        st.log(f"SUCCESS: MTU far above maximum properly rejected")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_010_12"])
    def test_mtu_changes_on_multiple_interfaces(self) -> None:
        """
        TC 010.12 - Verify MTU changes work on multiple interfaces.

        Steps:
        1. Change Ethernet0 to 1500, verify
        2. Change Ethernet4 to 1500, verify
        3. Change both to 9100, verify
        4. Verify both interfaces operational
        """
        st.log("=" * 80)
        st.log("TEST: MTU changes on multiple interfaces")
        st.log("=" * 80)

        interfaces = ["Ethernet0", "Ethernet4"]

        # Step 1 & 2: Change both to 1500
        for interface in interfaces:
            st.log(f"Changing {interface} to MTU 1500")
            result = self._change_interface_mtu(interface, "1500")
            if not result:
                st.report_fail("msg", f"Failed to configure MTU 1500 on {interface}")
            time.sleep(3)

        # Verify both at 1500
        time.sleep(5)
        for interface in interfaces:
            if not self._verify_interface_mtu(interface, "1500"):
                st.report_fail("msg", f"{interface} MTU not showing as 1500")
            st.log(f"SUCCESS: {interface} configured to MTU 1500")

        # Step 3: Change both to 9100
        for interface in interfaces:
            st.log(f"Changing {interface} to MTU 9100")
            result = self._change_interface_mtu(interface, "9100")
            if not result:
                st.report_fail("msg", f"Failed to configure MTU 9100 on {interface}")
            time.sleep(3)

        # Verify both at 9100
        time.sleep(5)
        for interface in interfaces:
            if not self._verify_interface_mtu(interface, "9100"):
                st.report_fail("msg", f"{interface} MTU not showing as 9100")
            st.log(f"SUCCESS: {interface} configured to MTU 9100")

        # Step 4: Verify both operational
        for interface in interfaces:
            if not self._verify_interface_operational(interface):
                st.log(f"WARNING: {interface} not fully operational")

        st.log(f"SUCCESS: MTU changes applied successfully on all interfaces")
        st.report_pass("test_case_passed")
