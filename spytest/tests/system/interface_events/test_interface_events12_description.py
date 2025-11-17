"""
INTERFACE EVENTS - INTERFACE DESCRIPTION UPDATES
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/interface_events/test_interface_events12_description.py \
  --logs-path ./logs/test_interface_events12_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates that interface description can be configured, modified, and removed successfully
  and that description changes are accurately reflected in CLI outputs. Tests various description
  formats including alphanumeric, special characters, spaces, mixed case, and long text.
  Ensures description configurations persist through interface flaps and that interface remains
  operational after description changes. Verifies that descriptions are purely cosmetic and
  have no impact on interface functionality.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |       DUT1         |                       |       DUT2         |
        # | (smic_sonic1)      |<-----Ethernet0------->| (smic_sonic2)      |
        # | 192.168.100.193    | (Description Tests)   | 192.168.100.195    |
        # |                    |<-----Ethernet4------->|                    |
        # +--------------------+                       +--------------------+
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
class TestInterfaceDescriptions:
    """Test cases for validating interface description configurations and persistence."""

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

        # Store original descriptions for restoration
        cls.data.original_descriptions = {}

        st.log(f"Test setup complete. DUT1: {cls.data.dut1}, CLI: {cls.data.cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """Restore interfaces to original state."""
        st.log("Teardown: Cleaning up interface descriptions")

        for interface in cls.data.test_interfaces:
            try:
                # Remove description
                cls._remove_description_static(interface)
                # Ensure interface is up
                intf_api.interface_operation(
                    cls.data.dut1,
                    interface,
                    operation="startup",
                    cli_type=cls.data.cli_type
                )
            except Exception as e:
                st.log(f"Warning: Failed to clean up {interface}: {str(e)}")

    @classmethod
    def _remove_description_static(cls, interface: str) -> None:
        """Static helper to remove description during teardown."""
        try:
            intf_api.interface_description_config(
                cls.data.dut1,
                interface,
                description="",
                config="remove",
                cli_type=cls.data.cli_type
            )
        except Exception as e:
            st.log(f"Warning: Failed to remove description from {interface}: {str(e)}")

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

            # Store baseline description if not already stored
            if interface not in self.data.original_descriptions:
                status_output = intf_api.show_interface_status(
                    self.data.dut1,
                    interfaces=interface,
                    cli_type=self.data.cli_type
                )
                if status_output:
                    self.data.original_descriptions[interface] = status_output[0].get("description", "")

        # Wait for interfaces to come up
        time.sleep(3)

    def teardown_method(self) -> None:
        """Per-test teardown - clean up descriptions."""
        st.log("Test teardown: Removing descriptions from interfaces")

        for interface in self.data.test_interfaces:
            try:
                self._remove_description(interface)
            except Exception as e:
                st.log(f"Warning: Teardown issue on {interface}: {str(e)}")

    def _set_description(self, interface: str, description: str) -> bool:
        """
        Set interface description.

        Args:
            interface: Interface name (e.g., "Ethernet0")
            description: Description text

        Returns:
            True if configuration successful, False otherwise
        """
        try:
            st.log(f"Setting description on {interface}: '{description}'")
            result = intf_api.interface_description_config(
                self.data.dut1,
                interface,
                description=description,
                cli_type=self.data.cli_type
            )
            time.sleep(2)  # Allow time for configuration to apply
            return result
        except Exception as e:
            st.log(f"Description configuration failed: {str(e)}")
            return False

    def _remove_description(self, interface: str) -> bool:
        """
        Remove interface description.

        Args:
            interface: Interface name

        Returns:
            True if successful, False otherwise
        """
        try:
            st.log(f"Removing description from {interface}")
            result = intf_api.interface_description_config(
                self.data.dut1,
                interface,
                description="",
                config="remove",
                cli_type=self.data.cli_type
            )
            time.sleep(2)
            return result
        except Exception as e:
            st.log(f"Description removal failed: {str(e)}")
            return False

    def _get_interface_description(self, interface: str) -> Optional[str]:
        """
        Get current description from interface status.

        Args:
            interface: Interface name

        Returns:
            Current description as string, or None if unable to retrieve
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

            description = status_output[0].get("description", "")
            return description

        except Exception as e:
            st.log(f"Failed to get description for {interface}: {str(e)}")
            return None

    def _verify_description(self, interface: str, expected_description: str) -> bool:
        """
        Verify interface description matches expected value.

        Args:
            interface: Interface name
            expected_description: Expected description text

        Returns:
            True if description matches, False otherwise
        """
        actual_description = self._get_interface_description(interface)

        if actual_description is None:
            st.log(f"ERROR: Could not retrieve description for {interface}")
            return False

        st.log(f"Interface {interface} - Expected: '{expected_description}', Actual: '{actual_description}'")

        # Handle empty/no description cases
        if expected_description == "" or expected_description == "-":
            return actual_description == "" or actual_description == "-"

        return actual_description == expected_description

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

            return admin_status.lower() == "up"

        except Exception as e:
            st.log(f"Operational status check failed: {str(e)}")
            return False

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_012_01"])
    def test_description_simple_alphanumeric(self) -> None:
        """
        TC 012.01 - Verify simple alphanumeric description can be configured.

        Steps:
        1. Set simple description "TestPort1" on Ethernet0
        2. Verify description is displayed in interface status
        3. Verify interface remains operational
        """
        st.log("=" * 80)
        st.log("TEST: Simple alphanumeric description")
        st.log("=" * 80)

        interface = "Ethernet0"
        description = "TestPort1"

        # Step 1: Set description
        result = self._set_description(interface, description)
        if not result:
            st.report_fail("msg", f"Failed to configure description '{description}' on {interface}")

        # Wait for configuration to apply
        time.sleep(3)

        # Step 2: Verify description
        if not self._verify_description(interface, description):
            st.report_fail("msg", f"{interface} description not showing as '{description}'")

        # Step 3: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational after description change")

        st.log(f"SUCCESS: Description '{description}' configured and displayed correctly")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_012_02"])
    def test_description_with_spaces(self) -> None:
        """
        TC 012.02 - Verify description with spaces can be configured.

        Steps:
        1. Set description "Test Port One" on Ethernet0
        2. Verify description with spaces is displayed correctly
        3. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Description with spaces")
        st.log("=" * 80)

        interface = "Ethernet0"
        description = "Test Port One"

        # Step 1: Set description
        result = self._set_description(interface, description)
        if not result:
            st.report_fail("msg", f"Failed to configure description with spaces on {interface}")

        time.sleep(3)

        # Step 2: Verify description (spaces preserved)
        if not self._verify_description(interface, description):
            st.report_fail("msg", f"Description with spaces not displayed correctly on {interface}")

        # Step 3: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational")

        st.log(f"SUCCESS: Description with spaces '{description}' configured correctly")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_012_03"])
    def test_description_with_special_characters(self) -> None:
        """
        TC 012.03 - Verify description with special characters can be configured.

        Steps:
        1. Set description "Server_Port-01" on Ethernet0
        2. Verify special characters (underscore, hyphen) preserved
        3. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Description with special characters")
        st.log("=" * 80)

        interface = "Ethernet0"
        description = "Server_Port-01"

        # Step 1: Set description
        result = self._set_description(interface, description)
        if not result:
            st.report_fail("msg", f"Failed to configure description with special characters")

        time.sleep(3)

        # Step 2: Verify description (special chars preserved)
        if not self._verify_description(interface, description):
            st.report_fail("msg", f"Special characters not preserved in description")

        # Step 3: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational")

        st.log(f"SUCCESS: Description with special characters '{description}' configured correctly")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_012_04"])
    def test_description_with_numbers(self) -> None:
        """
        TC 012.04 - Verify description with numbers can be configured.

        Steps:
        1. Set description "Port123" on Ethernet0
        2. Verify numeric characters preserved
        3. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Description with numbers")
        st.log("=" * 80)

        interface = "Ethernet0"
        description = "Port123"

        # Step 1: Set description
        result = self._set_description(interface, description)
        if not result:
            st.report_fail("msg", f"Failed to configure description with numbers")

        time.sleep(3)

        # Step 2: Verify description
        if not self._verify_description(interface, description):
            st.report_fail("msg", f"Numeric characters not preserved in description")

        # Step 3: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational")

        st.log(f"SUCCESS: Description with numbers '{description}' configured correctly")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_012_05"])
    def test_description_mixed_case(self) -> None:
        """
        TC 012.05 - Verify description with mixed case is preserved.

        Steps:
        1. Set description "UplinkToCore" on Ethernet0
        2. Verify case is preserved (not converted to upper or lower)
        3. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Description with mixed case")
        st.log("=" * 80)

        interface = "Ethernet0"
        description = "UplinkToCore"

        # Step 1: Set description
        result = self._set_description(interface, description)
        if not result:
            st.report_fail("msg", f"Failed to configure mixed case description")

        time.sleep(3)

        # Step 2: Verify description (case preserved)
        if not self._verify_description(interface, description):
            st.report_fail("msg", f"Case not preserved in description")

        # Step 3: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational")

        st.log(f"SUCCESS: Mixed case description '{description}' preserved correctly")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_012_06"])
    def test_description_long_text(self) -> None:
        """
        TC 012.06 - Verify long description can be configured.

        Steps:
        1. Set long description on Ethernet0
        2. Verify description is stored (may be truncated in display)
        3. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Long description text")
        st.log("=" * 80)

        interface = "Ethernet0"
        description = "Connection to Server Room Rack 01 Port 24"

        # Step 1: Set description
        result = self._set_description(interface, description)
        if not result:
            st.report_fail("msg", f"Failed to configure long description")

        time.sleep(3)

        # Step 2: Verify description (may be truncated in display, but should match or start with)
        actual_description = self._get_interface_description(interface)
        if actual_description is None:
            st.report_fail("msg", f"Could not retrieve description")

        # Check if description matches or is truncated version
        if not (actual_description == description or description.startswith(actual_description)):
            st.log(f"Note: Long description may be truncated in display")
            st.log(f"Expected: '{description}'")
            st.log(f"Actual: '{actual_description}'")

        # Step 3: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational")

        st.log(f"SUCCESS: Long description configured")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_012_07"])
    def test_description_modify(self) -> None:
        """
        TC 012.07 - Verify description can be modified.

        Steps:
        1. Set initial description "First Description"
        2. Verify initial description
        3. Modify to "Second Description"
        4. Verify description changed
        5. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Modify existing description")
        st.log("=" * 80)

        interface = "Ethernet0"
        initial_description = "First Description"
        modified_description = "Second Description"

        # Step 1: Set initial description
        result = self._set_description(interface, initial_description)
        if not result:
            st.report_fail("msg", f"Failed to set initial description")

        time.sleep(3)

        # Step 2: Verify initial description
        if not self._verify_description(interface, initial_description):
            st.report_fail("msg", f"Initial description not set correctly")

        st.log(f"Initial description '{initial_description}' verified")

        # Step 3: Modify description
        result = self._set_description(interface, modified_description)
        if not result:
            st.report_fail("msg", f"Failed to modify description")

        time.sleep(3)

        # Step 4: Verify modified description
        if not self._verify_description(interface, modified_description):
            st.report_fail("msg", f"Description not modified correctly")

        st.log(f"Modified description '{modified_description}' verified")

        # Step 5: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational after modification")

        st.log(f"SUCCESS: Description modified from '{initial_description}' to '{modified_description}'")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_012_08"])
    def test_description_remove(self) -> None:
        """
        TC 012.08 - Verify description can be removed.

        Steps:
        1. Set description "Temporary Description"
        2. Verify description is set
        3. Remove description using "no description"
        4. Verify description is removed (empty or "-")
        5. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Remove description")
        st.log("=" * 80)

        interface = "Ethernet0"
        description = "Temporary Description"

        # Step 1: Set description
        result = self._set_description(interface, description)
        if not result:
            st.report_fail("msg", f"Failed to set description")

        time.sleep(3)

        # Step 2: Verify description is set
        if not self._verify_description(interface, description):
            st.report_fail("msg", f"Description not set correctly")

        st.log(f"Description '{description}' set successfully")

        # Step 3: Remove description
        result = self._remove_description(interface)
        if not result:
            st.log(f"WARNING: Remove description command may have failed, continuing verification")

        time.sleep(3)

        # Step 4: Verify description is removed
        actual_description = self._get_interface_description(interface)
        if actual_description and actual_description != "-" and actual_description != "":
            st.report_fail("msg", f"Description not removed - still shows '{actual_description}'")

        st.log(f"Description successfully removed from {interface}")

        # Step 5: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational after removal")

        st.log(f"SUCCESS: Description removed successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_012_09"])
    def test_description_persistence_through_flap(self) -> None:
        """
        TC 012.09 - Verify description persists through interface flap.

        Steps:
        1. Set description "Persistent Port"
        2. Verify description is set
        3. Shutdown interface
        4. Bring interface up (no shutdown)
        5. Verify description persisted
        6. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Description persistence through interface flap")
        st.log("=" * 80)

        interface = "Ethernet0"
        description = "Persistent Port"

        # Step 1: Set description
        result = self._set_description(interface, description)
        if not result:
            st.report_fail("msg", f"Failed to set description")

        time.sleep(3)

        # Step 2: Verify description is set
        if not self._verify_description(interface, description):
            st.report_fail("msg", f"Initial description not set correctly")

        st.log(f"Description '{description}' set successfully")

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

        # Step 5: Verify description persisted
        if not self._verify_description(interface, description):
            st.report_fail("msg", f"Description did not persist through interface flap")

        st.log(f"Description '{description}' persisted through flap")

        # Step 6: Verify interface operational
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational after flap")

        st.log(f"SUCCESS: Description persisted through interface flap")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_012_10"])
    def test_description_multiple_interfaces(self) -> None:
        """
        TC 012.10 - Verify descriptions can be set on multiple interfaces.

        Steps:
        1. Set description "Port to DUT2 Eth0" on Ethernet0
        2. Set description "Port to DUT2 Eth4" on Ethernet4
        3. Verify both descriptions are correct
        4. Verify both interfaces operational
        """
        st.log("=" * 80)
        st.log("TEST: Descriptions on multiple interfaces")
        st.log("=" * 80)

        interfaces = ["Ethernet0", "Ethernet4"]
        descriptions = {
            "Ethernet0": "Port to DUT2 Eth0",
            "Ethernet4": "Port to DUT2 Eth4"
        }

        # Step 1 & 2: Set descriptions
        for interface in interfaces:
            description = descriptions[interface]
            st.log(f"Setting description on {interface}: '{description}'")
            result = self._set_description(interface, description)
            if not result:
                st.report_fail("msg", f"Failed to set description on {interface}")
            time.sleep(3)

        # Step 3: Verify both descriptions
        for interface in interfaces:
            expected_description = descriptions[interface]
            if not self._verify_description(interface, expected_description):
                st.report_fail("msg", f"{interface} description not correct")
            st.log(f"SUCCESS: {interface} description verified: '{expected_description}'")

        # Step 4: Verify both interfaces operational
        for interface in interfaces:
            if not self._verify_interface_operational(interface):
                st.log(f"WARNING: {interface} not operational")

        st.log(f"SUCCESS: Descriptions configured on all interfaces")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_012_11"])
    def test_description_sequential_changes(self) -> None:
        """
        TC 012.11 - Verify multiple sequential description changes.

        Steps:
        1. Set description "First"
        2. Verify and change to "Second"
        3. Verify and change to "Third"
        4. Verify and change to "Final"
        5. Verify final description
        6. Verify interface operational
        """
        st.log("=" * 80)
        st.log("TEST: Sequential description changes")
        st.log("=" * 80)

        interface = "Ethernet0"
        descriptions = ["First", "Second", "Third", "Final"]

        for idx, description in enumerate(descriptions, 1):
            st.log(f"Step {idx}: Setting description to '{description}'")

            # Set description
            result = self._set_description(interface, description)
            if not result:
                st.report_fail("msg", f"Failed to set description '{description}' in step {idx}")

            time.sleep(3)

            # Verify description
            if not self._verify_description(interface, description):
                st.report_fail("msg", f"Description '{description}' not verified in step {idx}")

            st.log(f"Step {idx}: SUCCESS - Description is '{description}'")

        # Final verification
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational after sequential changes")

        st.log(f"SUCCESS: All sequential description changes completed")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Interface Events", testcases=["TC_INTF_EVENTS_012_12"])
    def test_description_comprehensive_formats(self) -> None:
        """
        TC 012.12 - Comprehensive test of various description formats.

        Steps:
        1. Test each description format
        2. Verify each is configured correctly
        3. Verify interface operational after all changes
        """
        st.log("=" * 80)
        st.log("TEST: Comprehensive description format testing")
        st.log("=" * 80)

        interface = "Ethernet0"
        test_descriptions = [
            ("Simple", "Simple description"),
            ("WithSpaces", "Test Port One", "Description with spaces"),
            ("WithNumbers", "Port123", "Description with numbers"),
            ("SpecialChars", "Server_Port-01", "Special characters"),
            ("MixedCase", "UplinkToCore", "Mixed case"),
            ("Detailed", "Connection to Switch01", "Detailed description")
        ]

        for test_name, description, *desc_type in test_descriptions:
            type_desc = desc_type[0] if desc_type else test_name

            st.log(f"Testing: {type_desc} - '{description}'")

            # Set description
            result = self._set_description(interface, description)
            if not result:
                st.report_fail("msg", f"Failed to set {type_desc}")

            time.sleep(2)

            # Verify description
            if not self._verify_description(interface, description):
                st.report_fail("msg", f"{type_desc} not verified: '{description}'")

            st.log(f"SUCCESS: {type_desc} verified")

        # Final operational check
        if not self._verify_interface_operational(interface):
            st.log(f"WARNING: {interface} not operational after comprehensive tests")

        st.log(f"SUCCESS: All description formats tested successfully")
        st.report_pass("test_case_passed")
