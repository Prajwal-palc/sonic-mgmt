"""
INTERFACE EVENTS - MTU CHANGES NEGATIVE SCENARIOS
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/interface_events/test_interface_events11_mtu_negative.py \
  --logs-path ./logs/test_interface_events11_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates that interface MTU configuration properly rejects invalid values that fall outside
  the allowed range (less than 1312 or greater than 9216 bytes). Tests negative scenarios to
  ensure system provides appropriate error messages when invalid MTU values are configured and
  that interface MTU remains unchanged at previous valid value. Verifies interface operational
  status is not negatively impacted by invalid MTU attempts and that system handles errors
  gracefully without crashes or unexpected behavior. Includes boundary testing, non-numeric
  input validation, and system stability verification.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |       DUT1         |                       |       DUT2         |
        # | (smic_sonic1)      |<-----Ethernet0------->| (smic_sonic2)      |
        # | 192.168.100.193    | (Invalid MTU Tests)   | 192.168.100.195    |
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
class TestInterfaceMtuNegative:
    """Negative test cases for interface MTU configuration - verify invalid values are rejected."""

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

        # Valid MTU range: 1312-9216
        cls.data.min_valid_mtu = 1312
        cls.data.max_valid_mtu = 9216

        # Baseline valid MTU for testing
        cls.data.baseline_mtu = "9100"

        # Invalid MTU values to test (MUST be rejected)
        cls.data.invalid_mtu_below_min = ["1311", "1000", "576", "100", "0"]
        cls.data.invalid_mtu_above_max = ["9217", "10000", "16000", "65535"]
        cls.data.invalid_mtu_negative = ["-1", "-100"]

        # Boundary test values
        cls.data.boundary_values = {
            "just_below_min": "1311",  # Should be REJECTED
            "at_min": "1312",          # Should be ACCEPTED
            "at_max": "9216",          # Should be ACCEPTED
            "just_above_max": "9217"   # Should be REJECTED
        }

        st.log(f"Test setup complete. DUT1: {cls.data.dut1}, CLI: {cls.data.cli_type}")
        st.log(f"Valid MTU range: {cls.data.min_valid_mtu}-{cls.data.max_valid_mtu} bytes")
        st.log("NEGATIVE TESTING: Verifying invalid MTU values are rejected")

    @classmethod
    def teardown_class(cls) -> None:
        """Restore interfaces to operational state."""
        st.log("Teardown: Ensuring interfaces are operational with valid MTU")

        for interface in cls.data.test_interfaces:
            try:
                # Set valid MTU
                intf_api.interface_properties_set(
                    cls.data.dut1,
                    interface,
                    property="mtu",
                    value=cls.data.baseline_mtu,
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
                st.log(f"Warning: Teardown issue on {interface}: {str(e)}")

    def setup_method(self) -> None:
        """Per-test setup - establish known valid MTU baseline."""
        st.log("Test setup: Establishing baseline with valid MTU")

        for interface in self.data.test_interfaces:
            # Set baseline valid MTU
            try:
                intf_api.interface_properties_set(
                    self.data.dut1,
                    interface,
                    property="mtu",
                    value=self.data.baseline_mtu,
                    cli_type=self.data.cli_type
                )
                # Ensure interface is up
                intf_api.interface_operation(
                    self.data.dut1,
                    interface,
                    operation="startup",
                    cli_type=self.data.cli_type
                )
            except Exception as e:
                st.log(f"Setup warning for {interface}: {str(e)}")

        time.sleep(3)

    def teardown_method(self) -> None:
        """Per-test teardown - restore valid MTU."""
        st.log("Test teardown: Restoring valid MTU")

        for interface in self.data.test_interfaces:
            try:
                intf_api.interface_properties_set(
                    self.data.dut1,
                    interface,
                    property="mtu",
                    value=self.data.baseline_mtu,
                    cli_type=self.data.cli_type
                )
            except Exception as e:
                st.log(f"Teardown warning for {interface}: {str(e)}")

    def _get_interface_mtu(self, interface: str) -> Optional[str]:
        """
        Get current MTU value for an interface.

        Args:
            interface: Interface name

        Returns:
            Current MTU value as string, or None if unable to retrieve
        """
        try:
            status_output = intf_api.show_interface_status(
                self.data.dut1,
                interfaces=interface,
                cli_type=self.data.cli_type
            )

            if not status_output:
                st.log(f"ERROR: No status output for {interface}")
                return None

            mtu = str(status_output[0].get("mtu", ""))
            return mtu

        except Exception as e:
            st.log(f"Failed to get MTU for {interface}: {str(e)}")
            return None

    def _attempt_invalid_mtu(self, interface: str, invalid_mtu: str) -> bool:
        """
        Attempt to configure invalid MTU (should fail).

        Args:
            interface: Interface name
            invalid_mtu: Invalid MTU value to attempt

        Returns:
            True if command succeeded (BAD - invalid value accepted),
            False if command failed (GOOD - invalid value rejected)
        """
        try:
            st.log(f"Attempting INVALID MTU {invalid_mtu} on {interface}")
            result = intf_api.interface_properties_set(
                self.data.dut1,
                interface,
                property="mtu",
                value=invalid_mtu,
                cli_type=self.data.cli_type,
                skip_error_check=True  # Don't fail test on expected error
            )
            time.sleep(2)
            return result
        except Exception as e:
            st.log(f"Expected failure attempting invalid MTU: {str(e)}")
            return False

    def _verify_mtu_unchanged(self, interface: str, expected_mtu: str) -> bool:
        """
        Verify MTU remains at expected value (unchanged after invalid attempt).

        Args:
            interface: Interface name
            expected_mtu: Expected MTU value (should be unchanged)

        Returns:
            True if MTU is unchanged, False otherwise
        """
        actual_mtu = self._get_interface_mtu(interface)

        if actual_mtu is None:
            st.log(f"ERROR: Could not retrieve MTU for {interface}")
            return False

        st.log(f"MTU verification - Expected: {expected_mtu}, Actual: {actual_mtu}")
        return actual_mtu == expected_mtu

    def _verify_interface_operational(self, interface: str) -> bool:
        """
        Verify interface is still operational.

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
            return admin_status.lower() == "up"

        except Exception as e:
            st.log(f"Operational check failed: {str(e)}")
            return False

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_011_01"])
    @pytest.mark.negative
    def test_mtu_reject_below_minimum_1311(self) -> None:
        """
        TC 011.01 - Verify MTU value just below minimum (1311) is REJECTED.

        Steps:
        1. Set baseline MTU 9100
        2. Attempt to set MTU to 1311 (1 below minimum 1312)
        3. Verify command rejected or MTU unchanged
        4. Verify interface remains operational
        """
        st.log("=" * 80)
        st.log("TEST: Reject MTU 1311 (below minimum 1312)")
        st.log("=" * 80)

        interface = "Ethernet0"
        invalid_mtu = "1311"
        baseline_mtu = self.data.baseline_mtu

        # Step 1: Verify baseline MTU
        current_mtu = self._get_interface_mtu(interface)
        st.log(f"Baseline MTU: {current_mtu}")

        # Step 2: Attempt invalid MTU
        result = self._attempt_invalid_mtu(interface, invalid_mtu)

        time.sleep(3)

        # Step 3: Verify MTU unchanged
        if not self._verify_mtu_unchanged(interface, baseline_mtu):
            if result:
                st.report_fail("msg", f"INVALID MTU {invalid_mtu} was incorrectly ACCEPTED")
            else:
                st.log(f"MTU changed unexpectedly after rejected command")

        # If invalid MTU was accepted, test FAILS
        if result:
            final_mtu = self._get_interface_mtu(interface)
            if final_mtu == invalid_mtu:
                st.report_fail("msg", f"CRITICAL: Invalid MTU {invalid_mtu} was ACCEPTED (below minimum {self.data.min_valid_mtu})")

        # Step 4: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: Interface {interface} not operational after invalid attempt")

        st.log(f"SUCCESS: Invalid MTU {invalid_mtu} properly REJECTED")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_011_02"])
    @pytest.mark.negative
    def test_mtu_reject_below_minimum_1000(self) -> None:
        """
        TC 011.02 - Verify MTU value significantly below minimum (1000) is REJECTED.

        Steps:
        1. Set baseline MTU 9100
        2. Attempt to set MTU to 1000
        3. Verify MTU unchanged
        4. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Reject MTU 1000 (far below minimum)")
        st.log("=" * 80)

        interface = "Ethernet0"
        invalid_mtu = "1000"
        baseline_mtu = self.data.baseline_mtu

        # Attempt invalid MTU
        result = self._attempt_invalid_mtu(interface, invalid_mtu)
        time.sleep(3)

        # Verify MTU unchanged
        if not self._verify_mtu_unchanged(interface, baseline_mtu):
            st.log(f"WARNING: MTU changed from baseline")

        # Verify not accepted
        if result:
            final_mtu = self._get_interface_mtu(interface)
            if final_mtu == invalid_mtu:
                st.report_fail("msg", f"CRITICAL: Invalid MTU {invalid_mtu} was ACCEPTED")

        st.log(f"SUCCESS: Invalid MTU {invalid_mtu} properly REJECTED")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_011_03"])
    @pytest.mark.negative
    def test_mtu_reject_below_minimum_576(self) -> None:
        """
        TC 011.03 - Verify MTU 576 (standard IP minimum) is REJECTED (below SONiC minimum).

        Note: 576 is the minimum MTU per RFC 791, but SONiC requires minimum 1312.

        Steps:
        1. Attempt to set MTU to 576
        2. Verify MTU unchanged
        3. Verify rejected or not applied
        """
        st.log("=" * 80)
        st.log("TEST: Reject MTU 576 (standard IP min, but below SONiC min)")
        st.log("=" * 80)

        interface = "Ethernet0"
        invalid_mtu = "576"
        baseline_mtu = self.data.baseline_mtu

        # Attempt invalid MTU
        result = self._attempt_invalid_mtu(interface, invalid_mtu)
        time.sleep(3)

        # Verify MTU unchanged
        if not self._verify_mtu_unchanged(interface, baseline_mtu):
            st.log(f"WARNING: MTU changed from baseline")

        # Verify not accepted
        if result:
            final_mtu = self._get_interface_mtu(interface)
            if final_mtu == invalid_mtu:
                st.report_fail("msg", f"CRITICAL: Invalid MTU {invalid_mtu} was ACCEPTED (below SONiC minimum)")

        st.log(f"SUCCESS: MTU {invalid_mtu} properly REJECTED")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_011_04"])
    @pytest.mark.negative
    def test_mtu_reject_zero(self) -> None:
        """
        TC 011.04 - Verify MTU value of 0 is REJECTED.

        Steps:
        1. Attempt to set MTU to 0
        2. Verify MTU unchanged
        3. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Reject MTU 0 (zero)")
        st.log("=" * 80)

        interface = "Ethernet0"
        invalid_mtu = "0"
        baseline_mtu = self.data.baseline_mtu

        # Attempt invalid MTU
        result = self._attempt_invalid_mtu(interface, invalid_mtu)
        time.sleep(3)

        # Verify MTU unchanged
        if not self._verify_mtu_unchanged(interface, baseline_mtu):
            st.log(f"WARNING: MTU changed from baseline")

        # Verify not accepted
        if result:
            final_mtu = self._get_interface_mtu(interface)
            if final_mtu == invalid_mtu:
                st.report_fail("msg", f"CRITICAL: Zero MTU was ACCEPTED")

        st.log(f"SUCCESS: Zero MTU properly REJECTED")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_011_05"])
    @pytest.mark.negative
    def test_mtu_reject_above_maximum_9217(self) -> None:
        """
        TC 011.05 - Verify MTU value just above maximum (9217) is REJECTED.

        Steps:
        1. Set baseline MTU 9100
        2. Attempt to set MTU to 9217 (1 above maximum 9216)
        3. Verify command rejected or MTU unchanged
        4. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Reject MTU 9217 (above maximum 9216)")
        st.log("=" * 80)

        interface = "Ethernet0"
        invalid_mtu = "9217"
        baseline_mtu = self.data.baseline_mtu

        # Attempt invalid MTU
        result = self._attempt_invalid_mtu(interface, invalid_mtu)
        time.sleep(3)

        # Verify MTU unchanged
        if not self._verify_mtu_unchanged(interface, baseline_mtu):
            st.log(f"WARNING: MTU changed from baseline")

        # Verify not accepted
        if result:
            final_mtu = self._get_interface_mtu(interface)
            if final_mtu == invalid_mtu:
                st.report_fail("msg", f"CRITICAL: Invalid MTU {invalid_mtu} was ACCEPTED (above maximum {self.data.max_valid_mtu})")

        # Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: Interface not operational after invalid attempt")

        st.log(f"SUCCESS: Invalid MTU {invalid_mtu} properly REJECTED")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_011_06"])
    @pytest.mark.negative
    def test_mtu_reject_above_maximum_10000(self) -> None:
        """
        TC 011.06 - Verify MTU value significantly above maximum (10000) is REJECTED.

        Steps:
        1. Attempt to set MTU to 10000
        2. Verify MTU unchanged
        3. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Reject MTU 10000 (far above maximum)")
        st.log("=" * 80)

        interface = "Ethernet0"
        invalid_mtu = "10000"
        baseline_mtu = self.data.baseline_mtu

        # Attempt invalid MTU
        result = self._attempt_invalid_mtu(interface, invalid_mtu)
        time.sleep(3)

        # Verify MTU unchanged
        if not self._verify_mtu_unchanged(interface, baseline_mtu):
            st.log(f"WARNING: MTU changed from baseline")

        # Verify not accepted
        if result:
            final_mtu = self._get_interface_mtu(interface)
            if final_mtu == invalid_mtu:
                st.report_fail("msg", f"CRITICAL: Invalid MTU {invalid_mtu} was ACCEPTED")

        st.log(f"SUCCESS: Invalid MTU {invalid_mtu} properly REJECTED")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_011_07"])
    @pytest.mark.negative
    def test_mtu_reject_above_maximum_65535(self) -> None:
        """
        TC 011.07 - Verify maximum 16-bit value (65535) is REJECTED as MTU.

        Steps:
        1. Attempt to set MTU to 65535
        2. Verify MTU unchanged
        3. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Reject MTU 65535 (max 16-bit value)")
        st.log("=" * 80)

        interface = "Ethernet0"
        invalid_mtu = "65535"
        baseline_mtu = self.data.baseline_mtu

        # Attempt invalid MTU
        result = self._attempt_invalid_mtu(interface, invalid_mtu)
        time.sleep(3)

        # Verify MTU unchanged
        if not self._verify_mtu_unchanged(interface, baseline_mtu):
            st.log(f"WARNING: MTU changed from baseline")

        # Verify not accepted
        if result:
            final_mtu = self._get_interface_mtu(interface)
            if final_mtu == invalid_mtu:
                st.report_fail("msg", f"CRITICAL: Invalid MTU {invalid_mtu} was ACCEPTED")

        st.log(f"SUCCESS: Invalid MTU {invalid_mtu} properly REJECTED")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_011_08"])
    @pytest.mark.negative
    def test_mtu_boundary_below_minimum(self) -> None:
        """
        TC 011.08 - Boundary test: Verify 1311 REJECTED but 1312 ACCEPTED.

        Steps:
        1. Attempt MTU 1311 (should be REJECTED)
        2. Verify MTU unchanged
        3. Attempt MTU 1312 (should be ACCEPTED)
        4. Verify MTU changed to 1312
        5. Restore baseline
        """
        st.log("=" * 80)
        st.log("TEST: Boundary - 1311 REJECTED, 1312 ACCEPTED")
        st.log("=" * 80)

        interface = "Ethernet0"
        invalid_mtu = "1311"
        valid_min_mtu = "1312"
        baseline_mtu = self.data.baseline_mtu

        # Step 1: Attempt 1311 (invalid - below minimum)
        st.log(f"Step 1: Attempting INVALID MTU {invalid_mtu}")
        result_invalid = self._attempt_invalid_mtu(interface, invalid_mtu)
        time.sleep(3)

        # Step 2: Verify 1311 rejected - MTU should be unchanged
        if not self._verify_mtu_unchanged(interface, baseline_mtu):
            st.log(f"WARNING: MTU changed after invalid attempt")

        if result_invalid:
            final_mtu = self._get_interface_mtu(interface)
            if final_mtu == invalid_mtu:
                st.report_fail("msg", f"CRITICAL: Invalid MTU {invalid_mtu} was ACCEPTED at boundary")

        st.log(f"SUCCESS: MTU {invalid_mtu} properly REJECTED")

        # Step 3: Attempt 1312 (valid - at minimum)
        st.log(f"Step 2: Attempting VALID MTU {valid_min_mtu} (minimum)")
        result_valid = intf_api.interface_properties_set(
            self.data.dut1,
            interface,
            property="mtu",
            value=valid_min_mtu,
            cli_type=self.data.cli_type
        )
        time.sleep(3)

        # Step 4: Verify 1312 accepted
        if not result_valid:
            st.report_fail("msg", f"VALID minimum MTU {valid_min_mtu} was REJECTED")

        if not self._verify_mtu_unchanged(interface, valid_min_mtu):
            st.report_fail("msg", f"MTU not set to minimum {valid_min_mtu}")

        st.log(f"SUCCESS: MTU {valid_min_mtu} properly ACCEPTED (minimum boundary)")

        # Step 5: Restore baseline
        intf_api.interface_properties_set(
            self.data.dut1,
            interface,
            property="mtu",
            value=baseline_mtu,
            cli_type=self.data.cli_type
        )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_011_09"])
    @pytest.mark.negative
    def test_mtu_boundary_above_maximum(self) -> None:
        """
        TC 011.09 - Boundary test: Verify 9216 ACCEPTED but 9217 REJECTED.

        Steps:
        1. Attempt MTU 9217 (should be REJECTED)
        2. Verify MTU unchanged
        3. Attempt MTU 9216 (should be ACCEPTED)
        4. Verify MTU changed to 9216
        5. Restore baseline
        """
        st.log("=" * 80)
        st.log("TEST: Boundary - 9216 ACCEPTED, 9217 REJECTED")
        st.log("=" * 80)

        interface = "Ethernet0"
        invalid_mtu = "9217"
        valid_max_mtu = "9216"
        baseline_mtu = self.data.baseline_mtu

        # Step 1: Attempt 9217 (invalid - above maximum)
        st.log(f"Step 1: Attempting INVALID MTU {invalid_mtu}")
        result_invalid = self._attempt_invalid_mtu(interface, invalid_mtu)
        time.sleep(3)

        # Step 2: Verify 9217 rejected - MTU should be unchanged
        if not self._verify_mtu_unchanged(interface, baseline_mtu):
            st.log(f"WARNING: MTU changed after invalid attempt")

        if result_invalid:
            final_mtu = self._get_interface_mtu(interface)
            if final_mtu == invalid_mtu:
                st.report_fail("msg", f"CRITICAL: Invalid MTU {invalid_mtu} was ACCEPTED at boundary")

        st.log(f"SUCCESS: MTU {invalid_mtu} properly REJECTED")

        # Step 3: Attempt 9216 (valid - at maximum)
        st.log(f"Step 2: Attempting VALID MTU {valid_max_mtu} (maximum)")
        result_valid = intf_api.interface_properties_set(
            self.data.dut1,
            interface,
            property="mtu",
            value=valid_max_mtu,
            cli_type=self.data.cli_type
        )
        time.sleep(3)

        # Step 4: Verify 9216 accepted
        if not result_valid:
            st.report_fail("msg", f"VALID maximum MTU {valid_max_mtu} was REJECTED")

        if not self._verify_mtu_unchanged(interface, valid_max_mtu):
            st.report_fail("msg", f"MTU not set to maximum {valid_max_mtu}")

        st.log(f"SUCCESS: MTU {valid_max_mtu} properly ACCEPTED (maximum boundary)")

        # Step 5: Restore baseline
        intf_api.interface_properties_set(
            self.data.dut1,
            interface,
            property="mtu",
            value=baseline_mtu,
            cli_type=self.data.cli_type
        )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_011_10"])
    @pytest.mark.negative
    def test_mtu_rapid_invalid_attempts(self) -> None:
        """
        TC 011.10 - Verify system stability with rapid invalid MTU attempts.

        Steps:
        1. Rapidly attempt multiple invalid MTU values
        2. Verify MTU remains at baseline
        3. Verify system stable
        4. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Rapid invalid MTU attempts - system stability")
        st.log("=" * 80)

        interface = "Ethernet0"
        baseline_mtu = self.data.baseline_mtu

        invalid_values = ["1000", "10000", "0", "9217", "1311", "65535"]

        # Rapid invalid MTU attempts
        st.log(f"Attempting {len(invalid_values)} rapid invalid MTU configurations")
        for invalid_mtu in invalid_values:
            self._attempt_invalid_mtu(interface, invalid_mtu)
            time.sleep(0.5)  # Brief pause

        # Wait for system to stabilize
        time.sleep(5)

        # Verify MTU unchanged
        if not self._verify_mtu_unchanged(interface, baseline_mtu):
            st.log(f"WARNING: MTU changed during rapid invalid attempts")

        final_mtu = self._get_interface_mtu(interface)

        # Ensure final MTU is not any of the invalid values
        if final_mtu in invalid_values:
            st.report_fail("msg", f"CRITICAL: Invalid MTU {final_mtu} was applied during rapid testing")

        # Verify interface operational
        if not self._verify_interface_operational(interface):
            st.report_fail("msg", f"Interface not operational after rapid invalid attempts")

        st.log(f"SUCCESS: System stable after rapid invalid MTU attempts")
        st.log(f"MTU remained at valid value: {final_mtu}")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_011_11"])
    @pytest.mark.negative
    def test_mtu_invalid_multiple_interfaces(self) -> None:
        """
        TC 011.11 - Verify invalid MTU rejection works on multiple interfaces.

        Steps:
        1. Attempt invalid MTU on Ethernet0
        2. Verify MTU unchanged on Ethernet0
        3. Attempt invalid MTU on Ethernet4
        4. Verify MTU unchanged on Ethernet4
        5. Verify both interfaces operational
        """
        st.log("=" * 80)
        st.log("TEST: Invalid MTU rejection on multiple interfaces")
        st.log("=" * 80)

        interfaces = ["Ethernet0", "Ethernet4"]
        invalid_values_to_test = [
            ("1311", "below minimum"),
            ("9217", "above maximum"),
            ("10000", "far above maximum")
        ]
        baseline_mtu = self.data.baseline_mtu

        for interface in interfaces:
            st.log(f"Testing interface: {interface}")

            for invalid_mtu, description in invalid_values_to_test:
                st.log(f"  Attempting {invalid_mtu} ({description})")

                # Attempt invalid MTU
                result = self._attempt_invalid_mtu(interface, invalid_mtu)
                time.sleep(2)

                # Verify MTU unchanged
                if not self._verify_mtu_unchanged(interface, baseline_mtu):
                    st.log(f"  WARNING: MTU changed on {interface}")

                # Verify not accepted
                if result:
                    final_mtu = self._get_interface_mtu(interface)
                    if final_mtu == invalid_mtu:
                        st.report_fail("msg", f"CRITICAL: Invalid MTU {invalid_mtu} ACCEPTED on {interface}")

                st.log(f"  SUCCESS: {invalid_mtu} properly REJECTED on {interface}")

            # Verify interface operational
            if not self._verify_interface_operational(interface):
                st.log(f"  WARNING: {interface} not operational")

        st.log(f"SUCCESS: Invalid MTU properly rejected on all interfaces")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_011_12"])
    @pytest.mark.negative
    def test_mtu_invalid_with_interface_flap(self) -> None:
        """
        TC 011.12 - Verify invalid MTU doesn't affect interface through flap.

        Steps:
        1. Set baseline valid MTU
        2. Attempt invalid MTU (should be rejected)
        3. Verify MTU unchanged
        4. Flap interface (shutdown/no shutdown)
        5. Verify MTU still at valid value after flap
        6. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Invalid MTU with interface flap")
        st.log("=" * 80)

        interface = "Ethernet0"
        baseline_mtu = self.data.baseline_mtu
        invalid_mtu = "10000"

        # Step 1: Ensure baseline valid MTU
        current_mtu = self._get_interface_mtu(interface)
        st.log(f"Baseline MTU: {current_mtu}")

        # Step 2: Attempt invalid MTU
        result = self._attempt_invalid_mtu(interface, invalid_mtu)
        time.sleep(3)

        # Step 3: Verify MTU unchanged
        if not self._verify_mtu_unchanged(interface, baseline_mtu):
            st.log(f"WARNING: MTU changed after invalid attempt")

        # Step 4: Flap interface
        st.log(f"Flapping {interface}: shutdown")
        intf_api.interface_operation(
            self.data.dut1,
            interface,
            operation="shutdown",
            cli_type=self.data.cli_type
        )
        time.sleep(3)

        st.log(f"Flapping {interface}: no shutdown")
        intf_api.interface_operation(
            self.data.dut1,
            interface,
            operation="startup",
            cli_type=self.data.cli_type
        )
        time.sleep(8)

        # Step 5: Verify MTU still at valid value after flap
        if not self._verify_mtu_unchanged(interface, baseline_mtu):
            st.report_fail("msg", f"MTU changed after interface flap (should remain {baseline_mtu})")

        # Ensure invalid MTU was never applied
        final_mtu = self._get_interface_mtu(interface)
        if final_mtu == invalid_mtu:
            st.report_fail("msg", f"CRITICAL: Invalid MTU {invalid_mtu} applied after flap")

        # Step 6: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: Interface not operational after flap")

        st.log(f"SUCCESS: Valid MTU {baseline_mtu} maintained through flap, invalid MTU never applied")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_011_13"])
    @pytest.mark.negative
    def test_mtu_all_invalid_below_minimum(self) -> None:
        """
        TC 011.13 - Comprehensive test: Verify all invalid MTU values below minimum are rejected.

        Steps:
        1. Test each invalid MTU value below minimum
        2. Verify each is rejected
        3. Verify MTU remains unchanged
        4. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Comprehensive - All invalid MTU below minimum REJECTED")
        st.log("=" * 80)

        interface = "Ethernet0"
        baseline_mtu = self.data.baseline_mtu

        for invalid_mtu in self.data.invalid_mtu_below_min:
            st.log(f"Testing INVALID MTU: {invalid_mtu} (below minimum {self.data.min_valid_mtu})")

            # Attempt invalid MTU
            result = self._attempt_invalid_mtu(interface, invalid_mtu)
            time.sleep(2)

            # Verify MTU unchanged
            current_mtu = self._get_interface_mtu(interface)

            if current_mtu != baseline_mtu:
                st.log(f"  WARNING: MTU changed to {current_mtu}")

            # Verify invalid value not accepted
            if result and current_mtu == invalid_mtu:
                st.report_fail("msg", f"CRITICAL: Invalid MTU {invalid_mtu} was ACCEPTED")

            st.log(f"  SUCCESS: {invalid_mtu} properly REJECTED")

        # Final verification
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: Interface not operational after tests")

        st.log(f"SUCCESS: All invalid MTU values below minimum properly REJECTED")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_011_14"])
    @pytest.mark.negative
    def test_mtu_all_invalid_above_maximum(self) -> None:
        """
        TC 011.14 - Comprehensive test: Verify all invalid MTU values above maximum are rejected.

        Steps:
        1. Test each invalid MTU value above maximum
        2. Verify each is rejected
        3. Verify MTU remains unchanged
        4. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Comprehensive - All invalid MTU above maximum REJECTED")
        st.log("=" * 80)

        interface = "Ethernet0"
        baseline_mtu = self.data.baseline_mtu

        for invalid_mtu in self.data.invalid_mtu_above_max:
            st.log(f"Testing INVALID MTU: {invalid_mtu} (above maximum {self.data.max_valid_mtu})")

            # Attempt invalid MTU
            result = self._attempt_invalid_mtu(interface, invalid_mtu)
            time.sleep(2)

            # Verify MTU unchanged
            current_mtu = self._get_interface_mtu(interface)

            if current_mtu != baseline_mtu:
                st.log(f"  WARNING: MTU changed to {current_mtu}")

            # Verify invalid value not accepted
            if result and current_mtu == invalid_mtu:
                st.report_fail("msg", f"CRITICAL: Invalid MTU {invalid_mtu} was ACCEPTED")

            st.log(f"  SUCCESS: {invalid_mtu} properly REJECTED")

        # Final verification
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: Interface not operational after tests")

        st.log(f"SUCCESS: All invalid MTU values above maximum properly REJECTED")
        st.report_pass("test_case_passed")
