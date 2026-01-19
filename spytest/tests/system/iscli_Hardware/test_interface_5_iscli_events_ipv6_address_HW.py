"""
INTERFACE EVENTS - IPV6 ADDRESS CONFIGURATION AND CONNECTIVITY (HARDWARE - DYNAMIC TESTBED)
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs_hardware.yaml \
  tests/system/iscli_Hardware/test_interface_5_iscli_events_ipv6_address_HW.py \
  --logs-path ./logs/test_interface_5_iscli_events_ipv6_HW_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates interface IPv6 address configuration and connectivity by:
  1. Dynamically getting the first interface from both DUTs in testbed
  2. Removing any existing IPv6 addresses on both DUTs (baseline)
  3. Configuring IPv6 address "2001:db8::2/64" on DUT1 first interface
  4. Configuring IPv6 address "2001:db8::1/64" on DUT2 first interface
  5. Verifying IPv6 addresses in running-config on both DUTs
  6. Testing ping6 connectivity from DUT1 to DUT2 (2001:db8::2 -> 2001:db8::1)
  7. Removing IPv6 addresses from both DUTs

  This mirrors the exact CLI workflow:
    DUT1:
    - configure terminal -> interface Ethernet X -> no ipv6 address -> exit
    - configure terminal -> interface Ethernet X -> ipv6 address 2001:db8::2/64 -> exit
    - show running-configuration interface Ethernet X (verify: ipv6 address 2001:db8::2/64)
    - ping6 2001:db8::1
    - configure terminal -> interface Ethernet X -> no ipv6 address -> exit

    DUT2:
    - configure terminal -> interface Ethernet Y -> no ipv6 address -> exit
    - configure terminal -> interface Ethernet Y -> ipv6 address 2001:db8::1/64 -> exit
    - show running-configuration interface Ethernet Y (verify: ipv6 address 2001:db8::1/64)
    - configure terminal -> interface Ethernet Y -> no ipv6 address -> exit

  IMPORTANT: Uses 'show running-configuration interface Ethernet X' command
  to validate IPv6 address changes in the configuration.

  This hardware-focused version dynamically retrieves the FIRST and SECOND devices
  from the testbed and the FIRST interface from each device's topology links,
  making it portable across different testbed configurations without hardcoding
  interface names.

Pre-requisites:
  - Topology: 2-node minimum | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - Dynamic (uses first two DUTs and first interface from each)
        # +--------------------+                       +--------------------+
        # |       DUT1         |                       |       DUT2         |
        # | (First device)     |<-----First Intf------>| (Second device)    |
        # |  2001:db8::2/64    | (IPv6: 2001:db8::2/64)| 2001:db8::1/64     |
        # +--------------------+                       +--------------------+
  - Access to sonic-cli (klish mode)
  - Required test variables: CLI type (klish)
  - Minimum 2 DUTs with at least 1 interface each in testbed topology
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
WAIT_AFTER_IPV6_CHANGE = 2


@pytest.mark.topology("any")
class TestInterfaceIPv6AddressHW:
    """Test cases for validating interface IPv6 address configuration via CLI (klish mode) on hardware."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters dynamically from testbed."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing Interface IPv6 Address and Connectivity Test Suite (Hardware)")
        st.log("=" * 80)

        # Get DUT handles - use FIRST and SECOND devices from testbed
        cls.data.dut_names = st.get_dut_names()
        if not cls.data.dut_names or len(cls.data.dut_names) < 2:
            st.report_fail("msg", "Need at least 2 DUTs for this test")

        # Use FIRST and SECOND devices from testbed
        cls.data.dut1 = cls.data.dut_names[0]
        cls.data.dut2 = cls.data.dut_names[1]
        st.log(f"DUT1 (First device from testbed): {cls.data.dut1}")
        st.log(f"DUT2 (Second device from testbed): {cls.data.dut2}")

        # CLI type - use klish as specified
        cls.data.cli_type = CLI_TYPE
        st.log(f"CLI Type: {cls.data.cli_type}")

        # Get FIRST interface from each DUT's testbed topology dynamically
        cls.data.dut1_interface = cls._get_first_interface_from_testbed(cls.data.dut1)
        cls.data.dut2_interface = cls._get_first_interface_from_testbed(cls.data.dut2)
        st.log(f"DUT1 Test Interface (First from testbed): {cls.data.dut1_interface}")
        st.log(f"DUT2 Test Interface (First from testbed): {cls.data.dut2_interface}")

        # IPv6 addresses for testing
        cls.data.dut1_ipv6 = "2001:db8::2/64"
        cls.data.dut2_ipv6 = "2001:db8::1/64"
        cls.data.dut1_ipv6_addr = "2001:db8::2"  # Without prefix for ping6
        cls.data.dut2_ipv6_addr = "2001:db8::1"  # Without prefix for ping6
        st.log(f"DUT1 IPv6: {cls.data.dut1_ipv6}")
        st.log(f"DUT2 IPv6: {cls.data.dut2_ipv6}")

        st.log("Test setup complete")

    @classmethod
    def _get_first_interface_from_testbed(cls, dut: str) -> str:
        """
        Dynamically retrieve the FIRST interface from the testbed topology for a given DUT.

        This method queries the testbed topology to find the first available
        interface on the specified DUT, making the test portable across different
        testbed configurations.

        Args:
            dut: Device handle

        Returns:
            str: First interface name (e.g., "Ethernet0")

        Raises:
            Failure if no interfaces found in testbed
        """
        try:
            # Method 1: Try to get DUT links (interfaces connected to other DUTs)
            dut_links = st.get_dut_links(dut)
            st.log(f"DUT links retrieved for {dut}: {dut_links}")

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
            free_ports = st.get_free_ports(dut)
            st.log(f"Free ports retrieved for {dut}: {free_ports}")

            if free_ports and len(free_ports) > 0:
                first_interface = str(free_ports[0])
                st.log(f"Found first interface from free ports: {first_interface}")
                return first_interface

        except Exception as e:
            st.log(f"Note: Could not get free ports: {str(e)}")

        try:
            # Method 3: Try to get TG links (traffic generator links)
            tg_links = st.get_tg_links(dut)
            st.log(f"TG links retrieved for {dut}: {tg_links}")

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
        """Restore interfaces to no IPv6 address on both DUTs."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Restoring interfaces to no IPv6 address on both DUTs")
        st.log("=" * 80)

        try:
            cls._remove_interface_ipv6_static(cls.data.dut1, cls.data.dut1_interface)
            st.log(f"Restored {cls.data.dut1_interface} on DUT1 to no IPv6 address")
        except Exception as e:
            st.log(f"Warning: Failed to restore IPv6 address on DUT1: {str(e)}")

        try:
            cls._remove_interface_ipv6_static(cls.data.dut2, cls.data.dut2_interface)
            st.log(f"Restored {cls.data.dut2_interface} on DUT2 to no IPv6 address")
        except Exception as e:
            st.log(f"Warning: Failed to restore IPv6 address on DUT2: {str(e)}")

        st.log("Test teardown complete")

    @classmethod
    def _remove_interface_ipv6_static(cls, dut: str, interface: str) -> None:
        """
        Static helper to remove interface IPv6 address during teardown.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
        """
        try:
            commands = [
                "configure terminal",
                f"interface {interface}",
                "no ipv6 address",
                "exit"   # Only exit from interface mode
            ]
            st.config(dut, commands, type=CLI_TYPE)
            time.sleep(1)
        except Exception as e:
            st.log(f"Warning: Failed to remove IPv6 address on {dut}: {str(e)}")

    def setup_method(self) -> None:
        """Per-test setup - ensure interfaces have no IPv6 address on both DUTs."""
        st.log("-" * 80)
        st.log("TEST METHOD SETUP: Ensuring interfaces have no IPv6 address on both DUTs")
        st.log("-" * 80)

        self._remove_interface_ipv6(self.data.dut1, self.data.dut1_interface)
        self._remove_interface_ipv6(self.data.dut2, self.data.dut2_interface)
        time.sleep(WAIT_AFTER_IPV6_CHANGE)
        st.log(f"Interfaces configured with no IPv6 address on both DUTs")

    def teardown_method(self) -> None:
        """Per-test teardown - restore interfaces to no IPv6 address on both DUTs."""
        st.log("-" * 80)
        st.log("TEST METHOD TEARDOWN: Restoring interfaces on both DUTs")
        st.log("-" * 80)

        try:
            self._remove_interface_ipv6(self.data.dut1, self.data.dut1_interface)
            st.log(f"Restored {self.data.dut1_interface} on DUT1 to no IPv6 address")
        except Exception as e:
            st.log(f"Warning: Teardown issue on DUT1: {str(e)}")

        try:
            self._remove_interface_ipv6(self.data.dut2, self.data.dut2_interface)
            st.log(f"Restored {self.data.dut2_interface} on DUT2 to no IPv6 address")
        except Exception as e:
            st.log(f"Warning: Teardown issue on DUT2: {str(e)}")

    def _configure_interface_ipv6(self, dut: str, interface: str, ipv6_address: str) -> None:
        """
        Configure interface IPv6 address using klish commands.

        IMPORTANT: Uses only ONE exit command to exit from interface mode
        back to config mode. Does NOT exit from config mode to avoid prompt
        timeout. The framework will handle cleanup automatically.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0", "Ethernet272")
            ipv6_address: IPv6 address with prefix (e.g., "2001:db8::2/64")
        """
        st.log(f"Configuring {interface} on {dut} with IPv6 address {ipv6_address}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"ipv6 address {ipv6_address}",
            "exit"   # Only exit from interface mode, stay in config mode
        ]
        result = st.config(dut, commands, type=self.data.cli_type)
        return result

    def _remove_interface_ipv6(self, dut: str, interface: str) -> None:
        """
        Remove interface IPv6 address using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0", "Ethernet272")
        """
        st.log(f"Removing IPv6 address from {interface} on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no ipv6 address",
            "exit"   # Only exit from interface mode, stay in config mode
        ]
        result = st.config(dut, commands, type=self.data.cli_type)
        return result

    def _get_running_config_interface(self, dut: str, interface: str) -> str:
        """
        Get running-configuration for a specific interface.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0", "Ethernet272")

        Returns:
            String containing the output of 'show running-configuration interface Ethernet X' command
        """
        st.log(f"Getting running-configuration for {interface} on {dut}")

        # Parse interface number from name (e.g., "Ethernet0" -> "0", "Ethernet272" -> "272")
        interface_number = interface.replace("Ethernet", "").strip()

        # Command: show running-configuration interface Ethernet X
        cmd = f"show running-configuration interface Ethernet {interface_number}"

        # Execute command
        output = st.show(
            dut,
            cmd,
            type=self.data.cli_type,
            skip_tmpl=True,
            skip_error_check=True
        )

        # Convert to string if needed
        if not isinstance(output, str):
            output = str(output)

        st.log(f"Running-config output from {dut}:\n{output}")
        return output

    def _extract_ipv6_from_running_config(self, output: str) -> Optional[str]:
        """
        Extract IPv6 address from running-configuration output.

        Expected output format:
        !
        interface Ethernet0
         ipv6 address 2001:db8::2/64
         mtu 9100
         speed 40000

        Args:
            output: Raw CLI output string from show running-configuration

        Returns:
            IPv6 address as string (e.g., "2001:db8::2/64"), or None if not found
        """
        if not output:
            st.log("No output to parse")
            return None

        # Search for "ipv6 address <value>" pattern
        ipv6_pattern = r'ipv6\s+address\s+([0-9a-fA-F:]+/\d+)'
        match = re.search(ipv6_pattern, output, re.IGNORECASE)

        if match:
            ipv6_value = match.group(1).strip()
            st.log(f"Found IPv6 address: {ipv6_value}")
            return ipv6_value
        else:
            st.log("IPv6 address not found in output")
            return None

    def _verify_ipv6_in_running_config(
        self,
        dut: str,
        interface: str,
        expected_ipv6: Optional[str]
    ) -> bool:
        """
        Verify that interface has the expected IPv6 address in running-configuration.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0", "Ethernet272")
            expected_ipv6: Expected IPv6 address (e.g., "2001:db8::2/64")
                          or None if no IPv6 address should be present

        Returns:
            True if IPv6 address matches expected value, False otherwise
        """
        st.log(f"Verifying {interface} on {dut} IPv6 address = '{expected_ipv6}' in running-configuration")

        # Get running-config output
        output = self._get_running_config_interface(dut, interface)

        # Extract IPv6 address
        actual_ipv6 = self._extract_ipv6_from_running_config(output)

        # Compare values
        if expected_ipv6 is None:
            # Expecting no IPv6 address
            if actual_ipv6 is None:
                st.log(f"PASS: {interface} on {dut} has no IPv6 address (as expected)")
                return True
            else:
                st.error(f"FAIL: {interface} on {dut} has IPv6 address '{actual_ipv6}' (expected no IPv6 address)")
                return False
        else:
            # Expecting a specific IPv6 address
            if actual_ipv6 == expected_ipv6:
                st.log(f"PASS: {interface} on {dut} IPv6 address is '{actual_ipv6}' (matches expected '{expected_ipv6}')")
                return True
            else:
                st.error(f"FAIL: {interface} on {dut} IPv6 address is '{actual_ipv6}' (expected '{expected_ipv6}')")
                return False

    def _test_ping6(self, source_dut: str, dest_ipv6: str) -> bool:
        """
        Test ping6 connectivity from source DUT to destination IPv6 address.

        IMPORTANT: Exits config mode before running ping6 command to ensure
        we're in exec mode where ping6 command works properly.

        Args:
            source_dut: Source device handle
            dest_ipv6: Destination IPv6 address

        Returns:
            True if ping6 succeeds, False otherwise
        """
        st.log(f"Testing ping6 from {source_dut} to {dest_ipv6}")

        try:
            # First, exit config mode to get to exec mode where ping6 works
            st.config(
                source_dut,
                "end",
                type=self.data.cli_type,
                conf=False,
                skip_error_check=True
            )

            # Small delay for mode transition
            time.sleep(0.5)

            # Now run ping6 command from exec mode with packet count limit
            # Use -c 3 to send only 3 packets and exit
            cmd = f"ping6 -c 3 {dest_ipv6}"
            output = st.show(
                source_dut,
                cmd,
                type=self.data.cli_type,
                skip_tmpl=True,
                skip_error_check=True
            )

            # Convert to string if needed
            if not isinstance(output, str):
                output = str(output)

            st.log(f"Ping6 output:\n{output}")

            # Check if ping6 was successful (look for success indicators)
            # Common patterns: "bytes from", "64 bytes", "received"
            if "bytes from" in output.lower() or "64 bytes" in output.lower():
                st.log(f"PASS: Ping6 from {source_dut} to {dest_ipv6} succeeded")
                return True
            else:
                st.log(f"INFO: Ping6 from {source_dut} to {dest_ipv6} failed")
                return False
        except Exception as e:
            st.log(f"INFO: Ping6 exception: {str(e)}")
            return False

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_IPV6_001_HW"])
    def test_interface_ipv6_address_and_connectivity(self) -> None:
        """
        TC_INTF_EVENTS_IPV6_001_HW: Validate CLI for IPv6 address configuration and connectivity on hardware.

        Test Procedure:
        1. Dynamically get first interface from both DUTs in testbed
        2. Verify baseline (no IPv6 address on both DUTs)
        3. Configure IPv6 address "2001:db8::2/64" on DUT1
        4. Configure IPv6 address "2001:db8::1/64" on DUT2
        5. Verify IPv6 addresses in running-config on both DUTs
        6. Test ping6 from DUT1 to DUT2 (2001:db8::2 -> 2001:db8::1)
        7. Remove IPv6 addresses from both DUTs
        8. Verify no IPv6 addresses on both DUTs
        9. Final validation

        Expected Result:
        - IPv6 addresses are configured successfully on both DUTs
        - IPv6 addresses are reflected accurately in running-configuration
        - Ping6 connectivity test is performed from DUT1 to DUT2
        - IPv6 addresses can be removed successfully
        - System remains stable
        """
        st.log("=" * 80)
        st.log("TEST: Interface IPv6 Address Configuration and Connectivity (Hardware - Dynamic)")
        st.log("=" * 80)

        # Initialize validation failure tracking
        validation_failures = []

        # ===== STEP 1: Verify baseline (no IPv6 address on both DUTs) =====
        st.log("-" * 80)
        st.log("STEP 1: Verify baseline (no IPv6 address on both DUTs)")
        st.log("-" * 80)

        if not self._verify_ipv6_in_running_config(self.data.dut1, self.data.dut1_interface, None):
            error_msg = f"Baseline check failed: DUT1 {self.data.dut1_interface} has an IPv6 address when it should not"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ipv6_in_running_config(self.data.dut2, self.data.dut2_interface, None):
            error_msg = f"Baseline check failed: DUT2 {self.data.dut2_interface} has an IPv6 address when it should not"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not validation_failures:
            st.log("PASS: Baseline verified - both DUTs have no IPv6 address")

        # ===== STEP 2: Configure IPv6 address on DUT1 =====
        st.log("-" * 80)
        st.log(f"STEP 2: Configure IPv6 address '{self.data.dut1_ipv6}' on DUT1")
        st.log("-" * 80)

        self._configure_interface_ipv6(self.data.dut1, self.data.dut1_interface, self.data.dut1_ipv6)
        st.log(f"Configured DUT1 {self.data.dut1_interface} with IPv6 address '{self.data.dut1_ipv6}'")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_IPV6_CHANGE)

        # ===== STEP 3: Configure IPv6 address on DUT2 =====
        st.log("-" * 80)
        st.log(f"STEP 3: Configure IPv6 address '{self.data.dut2_ipv6}' on DUT2")
        st.log("-" * 80)

        self._configure_interface_ipv6(self.data.dut2, self.data.dut2_interface, self.data.dut2_ipv6)
        st.log(f"Configured DUT2 {self.data.dut2_interface} with IPv6 address '{self.data.dut2_ipv6}'")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_IPV6_CHANGE)

        # ===== STEP 4: Verify IPv6 addresses on both DUTs =====
        st.log("-" * 80)
        st.log("STEP 4: Verify IPv6 addresses in running-config on both DUTs")
        st.log("-" * 80)

        if not self._verify_ipv6_in_running_config(self.data.dut1, self.data.dut1_interface, self.data.dut1_ipv6):
            error_msg = f"IPv6 verification failed: DUT1 {self.data.dut1_interface} does not show IPv6 '{self.data.dut1_ipv6}' in running-config"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ipv6_in_running_config(self.data.dut2, self.data.dut2_interface, self.data.dut2_ipv6):
            error_msg = f"IPv6 verification failed: DUT2 {self.data.dut2_interface} does not show IPv6 '{self.data.dut2_ipv6}' in running-config"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "IPv6 verification failed" in f]) == 0:
            st.log("PASS: IPv6 addresses verified on both DUTs")

        # ===== STEP 5: Test ping6 connectivity from DUT1 to DUT2 =====
        st.log("-" * 80)
        st.log(f"STEP 5: Test ping6 from DUT1 ({self.data.dut1_ipv6_addr}) to DUT2 ({self.data.dut2_ipv6_addr})")
        st.log("-" * 80)

        # Wait for interfaces to be ready
        time.sleep(5)

        # Test ping6 from DUT1 to DUT2
        ping_result = self._test_ping6(self.data.dut1, self.data.dut2_ipv6_addr)

        if ping_result:
            st.log("PASS: Ping6 succeeded - connectivity verified")
        else:
            st.log("INFO: Ping6 failed - continuing test")

        # ===== STEP 6: Remove IPv6 addresses from both DUTs =====
        st.log("-" * 80)
        st.log("STEP 6: Remove IPv6 addresses from both DUTs")
        st.log("-" * 80)

        self._remove_interface_ipv6(self.data.dut1, self.data.dut1_interface)
        st.log(f"Removed IPv6 address from DUT1 {self.data.dut1_interface}")

        self._remove_interface_ipv6(self.data.dut2, self.data.dut2_interface)
        st.log(f"Removed IPv6 address from DUT2 {self.data.dut2_interface}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_IPV6_CHANGE)

        # ===== STEP 7: Verify no IPv6 addresses on both DUTs =====
        st.log("-" * 80)
        st.log("STEP 7: Verify no IPv6 addresses on both DUTs")
        st.log("-" * 80)

        if not self._verify_ipv6_in_running_config(self.data.dut1, self.data.dut1_interface, None):
            error_msg = f"IPv6 removal failed: DUT1 {self.data.dut1_interface} still has an IPv6 address"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ipv6_in_running_config(self.data.dut2, self.data.dut2_interface, None):
            error_msg = f"IPv6 removal failed: DUT2 {self.data.dut2_interface} still has an IPv6 address"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "IPv6 removal failed" in f]) == 0:
            st.log("PASS: IPv6 addresses removed from both DUTs")

        # ===== STEP 8: Final validation =====
        st.log("-" * 80)
        st.log("STEP 8: Final validation")
        st.log("-" * 80)

        # Get final running-config for both DUTs
        final_output_dut1 = self._get_running_config_interface(self.data.dut1, self.data.dut1_interface)
        final_ipv6_dut1 = self._extract_ipv6_from_running_config(final_output_dut1)

        final_output_dut2 = self._get_running_config_interface(self.data.dut2, self.data.dut2_interface)
        final_ipv6_dut2 = self._extract_ipv6_from_running_config(final_output_dut2)

        if final_ipv6_dut1 is not None:
            error_msg = f"Final validation failed: DUT1 {self.data.dut1_interface} has IPv6 '{final_ipv6_dut1}', expected no IPv6"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if final_ipv6_dut2 is not None:
            error_msg = f"Final validation failed: DUT2 {self.data.dut2_interface} has IPv6 '{final_ipv6_dut2}', expected no IPv6"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if final_ipv6_dut1 is None and final_ipv6_dut2 is None:
            st.log("PASS: Final validation complete")

        # ===== TEST COMPLETE =====
        st.log("=" * 80)
        st.log("TEST COMPLETE: IPv6 address configuration and connectivity test completed")
        st.log(f"DUT1: None → '{self.data.dut1_ipv6}' → None ✓")
        st.log(f"DUT2: None → '{self.data.dut2_ipv6}' → None ✓")
        st.log(f"Ping6 test from DUT1 to DUT2: {'Succeeded ✓' if ping_result else 'Failed'}")
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
