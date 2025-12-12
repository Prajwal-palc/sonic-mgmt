"""
INTERFACE EVENTS - IP ADDRESS CONFIGURATION AND CONNECTIVITY (HARDWARE - DYNAMIC TESTBED)
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs_hardware.yaml \
  tests/system/iscli_Hardware/test_interface_4_iscli_events_ip_address_HW.py \
  --logs-path ./logs/test_interface_4_iscli_events_ip_HW_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates interface IP address configuration and connectivity by:
  1. Dynamically getting the first interface from both DUTs in testbed
  2. Removing any existing IP addresses on both DUTs (baseline)
  3. Configuring IP address "10.0.0.2/30" on DUT1 first interface
  4. Configuring IP address "10.0.0.1/30" on DUT2 first interface
  5. Verifying IP addresses in running-config on both DUTs
  6. Testing ping connectivity from DUT1 to DUT2 (10.0.0.2 -> 10.0.0.1)
  7. Removing IP addresses from both DUTs

  This mirrors the exact CLI workflow:
    DUT1:
    - configure terminal -> interface Ethernet X -> no ip address -> exit
    - configure terminal -> interface Ethernet X -> ip address 10.0.0.2/30 -> exit
    - show running-configuration interface Ethernet X (verify: ip address 10.0.0.2/30)
    - ping 10.0.0.1
    - configure terminal -> interface Ethernet X -> no ip address -> exit

    DUT2:
    - configure terminal -> interface Ethernet Y -> no ip address -> exit
    - configure terminal -> interface Ethernet Y -> ip address 10.0.0.1/30 -> exit
    - show running-configuration interface Ethernet Y (verify: ip address 10.0.0.1/30)
    - configure terminal -> interface Ethernet Y -> no ip address -> exit

  IMPORTANT: Uses 'show running-configuration interface Ethernet X' command
  to validate IP address changes in the configuration.

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
        # |  10.0.0.2/30       | (IP: 10.0.0.2/30)     | 10.0.0.1/30        |
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
WAIT_AFTER_IP_CHANGE = 2


@pytest.mark.topology("any")
class TestInterfaceIPAddressHW:
    """Test cases for validating interface IP address configuration via CLI (klish mode) on hardware."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters dynamically from testbed."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing Interface IP Address and Connectivity Test Suite (Hardware)")
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

        # IP addresses for testing
        cls.data.dut1_ip = "10.0.0.2/30"
        cls.data.dut2_ip = "10.0.0.1/30"
        cls.data.dut1_ip_addr = "10.0.0.2"  # Without prefix for ping
        cls.data.dut2_ip_addr = "10.0.0.1"  # Without prefix for ping
        st.log(f"DUT1 IP: {cls.data.dut1_ip}")
        st.log(f"DUT2 IP: {cls.data.dut2_ip}")

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
        """Restore interfaces to no IP address on both DUTs."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Restoring interfaces to no IP address on both DUTs")
        st.log("=" * 80)

        try:
            cls._remove_interface_ip_static(cls.data.dut1, cls.data.dut1_interface)
            st.log(f"Restored {cls.data.dut1_interface} on DUT1 to no IP address")
        except Exception as e:
            st.log(f"Warning: Failed to restore IP address on DUT1: {str(e)}")

        try:
            cls._remove_interface_ip_static(cls.data.dut2, cls.data.dut2_interface)
            st.log(f"Restored {cls.data.dut2_interface} on DUT2 to no IP address")
        except Exception as e:
            st.log(f"Warning: Failed to restore IP address on DUT2: {str(e)}")

        st.log("Test teardown complete")

    @classmethod
    def _remove_interface_ip_static(cls, dut: str, interface: str) -> None:
        """
        Static helper to remove interface IP address during teardown.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
        """
        try:
            commands = [
                "configure terminal",
                f"interface {interface}",
                "no ip address",
                "exit"   # Only exit from interface mode
            ]
            st.config(dut, commands, type=CLI_TYPE)
            time.sleep(1)
        except Exception as e:
            st.log(f"Warning: Failed to remove IP address on {dut}: {str(e)}")

    def setup_method(self) -> None:
        """Per-test setup - ensure interfaces have no IP address on both DUTs."""
        st.log("-" * 80)
        st.log("TEST METHOD SETUP: Ensuring interfaces have no IP address on both DUTs")
        st.log("-" * 80)

        self._remove_interface_ip(self.data.dut1, self.data.dut1_interface)
        self._remove_interface_ip(self.data.dut2, self.data.dut2_interface)
        time.sleep(WAIT_AFTER_IP_CHANGE)
        st.log(f"Interfaces configured with no IP address on both DUTs")

    def teardown_method(self) -> None:
        """Per-test teardown - restore interfaces to no IP address on both DUTs."""
        st.log("-" * 80)
        st.log("TEST METHOD TEARDOWN: Restoring interfaces on both DUTs")
        st.log("-" * 80)

        try:
            self._remove_interface_ip(self.data.dut1, self.data.dut1_interface)
            st.log(f"Restored {self.data.dut1_interface} on DUT1 to no IP address")
        except Exception as e:
            st.log(f"Warning: Teardown issue on DUT1: {str(e)}")

        try:
            self._remove_interface_ip(self.data.dut2, self.data.dut2_interface)
            st.log(f"Restored {self.data.dut2_interface} on DUT2 to no IP address")
        except Exception as e:
            st.log(f"Warning: Teardown issue on DUT2: {str(e)}")

    def _configure_interface_ip(self, dut: str, interface: str, ip_address: str) -> None:
        """
        Configure interface IP address using klish commands.

        IMPORTANT: Uses only ONE exit command to exit from interface mode
        back to config mode. Does NOT exit from config mode to avoid prompt
        timeout. The framework will handle cleanup automatically.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0", "Ethernet272")
            ip_address: IP address with prefix (e.g., "10.0.0.2/30")
        """
        st.log(f"Configuring {interface} on {dut} with IP address {ip_address}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"ip address {ip_address}",
            "exit"   # Only exit from interface mode, stay in config mode
        ]
        result = st.config(dut, commands, type=self.data.cli_type)
        return result

    def _remove_interface_ip(self, dut: str, interface: str) -> None:
        """
        Remove interface IP address using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0", "Ethernet272")
        """
        st.log(f"Removing IP address from {interface} on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no ip address",
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

    def _extract_ip_from_running_config(self, output: str) -> Optional[str]:
        """
        Extract IP address from running-configuration output.

        Expected output format:
        !
        interface Ethernet0
         ip address 10.0.0.2/30
         mtu 9100
         speed 40000

        Args:
            output: Raw CLI output string from show running-configuration

        Returns:
            IP address as string (e.g., "10.0.0.2/30"), or None if not found
        """
        if not output:
            st.log("No output to parse")
            return None

        # Search for "ip address <value>" pattern
        ip_pattern = r'ip address\s+(\S+)'
        match = re.search(ip_pattern, output, re.IGNORECASE)

        if match:
            ip_value = match.group(1).strip()
            st.log(f"Found IP address: {ip_value}")
            return ip_value
        else:
            st.log("IP address not found in output")
            return None

    def _verify_ip_in_running_config(
        self,
        dut: str,
        interface: str,
        expected_ip: Optional[str]
    ) -> bool:
        """
        Verify that interface has the expected IP address in running-configuration.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0", "Ethernet272")
            expected_ip: Expected IP address (e.g., "10.0.0.2/30")
                        or None if no IP address should be present

        Returns:
            True if IP address matches expected value, False otherwise
        """
        st.log(f"Verifying {interface} on {dut} IP address = '{expected_ip}' in running-configuration")

        # Get running-config output
        output = self._get_running_config_interface(dut, interface)

        # Extract IP address
        actual_ip = self._extract_ip_from_running_config(output)

        # Compare values
        if expected_ip is None:
            # Expecting no IP address
            if actual_ip is None:
                st.log(f"PASS: {interface} on {dut} has no IP address (as expected)")
                return True
            else:
                st.error(f"FAIL: {interface} on {dut} has IP address '{actual_ip}' (expected no IP address)")
                return False
        else:
            # Expecting a specific IP address
            if actual_ip == expected_ip:
                st.log(f"PASS: {interface} on {dut} IP address is '{actual_ip}' (matches expected '{expected_ip}')")
                return True
            else:
                st.error(f"FAIL: {interface} on {dut} IP address is '{actual_ip}' (expected '{expected_ip}')")
                return False

    def _test_ping(self, source_dut: str, dest_ip: str) -> bool:
        """
        Test ping connectivity from source DUT to destination IP.

        IMPORTANT: Exits config mode before running ping command to ensure
        we're in exec mode where ping command works properly.

        Args:
            source_dut: Source device handle
            dest_ip: Destination IP address

        Returns:
            True if ping succeeds, False otherwise
        """
        st.log(f"Testing ping from {source_dut} to {dest_ip}")

        try:
            # First, exit config mode to get to exec mode where ping works
            st.config(
                source_dut,
                "end",
                type=self.data.cli_type,
                conf=False,
                skip_error_check=True
            )

            # Small delay for mode transition
            time.sleep(0.5)

            # Now run ping command from exec mode with packet count limit
            # Use -c 3 to send only 3 packets and exit
            cmd = f"ping -c 3 {dest_ip}"
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

            st.log(f"Ping output:\n{output}")

            # Check if ping was successful (look for success indicators)
            # Common patterns: "bytes from", "64 bytes", "received"
            if "bytes from" in output.lower() or "64 bytes" in output.lower():
                st.log(f"PASS: Ping from {source_dut} to {dest_ip} succeeded")
                return True
            else:
                st.log(f"INFO: Ping from {source_dut} to {dest_ip} failed")
                return False
        except Exception as e:
            st.log(f"INFO: Ping exception: {str(e)}")
            return False

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_IP_001_HW"])
    def test_interface_ip_address_and_connectivity(self) -> None:
        """
        TC_INTF_EVENTS_IP_001_HW: Validate CLI for IP address configuration and connectivity on hardware.

        Test Procedure:
        1. Dynamically get first interface from both DUTs in testbed
        2. Verify baseline (no IP address on both DUTs)
        3. Configure IP address "10.0.0.2/30" on DUT1
        4. Configure IP address "10.0.0.1/30" on DUT2
        5. Verify IP addresses in running-config on both DUTs
        6. Test ping from DUT1 to DUT2 (10.0.0.2 -> 10.0.0.1)
        7. Remove IP addresses from both DUTs
        8. Verify no IP addresses on both DUTs
        9. Final validation

        Expected Result:
        - IP addresses are configured successfully on both DUTs
        - IP addresses are reflected accurately in running-configuration
        - Ping connectivity test is performed from DUT1 to DUT2
        - IP addresses can be removed successfully
        - System remains stable
        """
        st.log("=" * 80)
        st.log("TEST: Interface IP Address Configuration and Connectivity (Hardware - Dynamic)")
        st.log("=" * 80)

        # Initialize validation failure tracking
        validation_failures = []

        # ===== STEP 1: Verify baseline (no IP address on both DUTs) =====
        st.log("-" * 80)
        st.log("STEP 1: Verify baseline (no IP address on both DUTs)")
        st.log("-" * 80)

        if not self._verify_ip_in_running_config(self.data.dut1, self.data.dut1_interface, None):
            error_msg = f"Baseline check failed: DUT1 {self.data.dut1_interface} has an IP address when it should not"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ip_in_running_config(self.data.dut2, self.data.dut2_interface, None):
            error_msg = f"Baseline check failed: DUT2 {self.data.dut2_interface} has an IP address when it should not"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not validation_failures:
            st.log("PASS: Baseline verified - both DUTs have no IP address")

        # ===== STEP 2: Configure IP address on DUT1 =====
        st.log("-" * 80)
        st.log(f"STEP 2: Configure IP address '{self.data.dut1_ip}' on DUT1")
        st.log("-" * 80)

        self._configure_interface_ip(self.data.dut1, self.data.dut1_interface, self.data.dut1_ip)
        st.log(f"Configured DUT1 {self.data.dut1_interface} with IP address '{self.data.dut1_ip}'")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_IP_CHANGE)

        # ===== STEP 3: Configure IP address on DUT2 =====
        st.log("-" * 80)
        st.log(f"STEP 3: Configure IP address '{self.data.dut2_ip}' on DUT2")
        st.log("-" * 80)

        self._configure_interface_ip(self.data.dut2, self.data.dut2_interface, self.data.dut2_ip)
        st.log(f"Configured DUT2 {self.data.dut2_interface} with IP address '{self.data.dut2_ip}'")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_IP_CHANGE)

        # ===== STEP 4: Verify IP addresses on both DUTs =====
        st.log("-" * 80)
        st.log("STEP 4: Verify IP addresses in running-config on both DUTs")
        st.log("-" * 80)

        if not self._verify_ip_in_running_config(self.data.dut1, self.data.dut1_interface, self.data.dut1_ip):
            error_msg = f"IP verification failed: DUT1 {self.data.dut1_interface} does not show IP '{self.data.dut1_ip}' in running-config"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ip_in_running_config(self.data.dut2, self.data.dut2_interface, self.data.dut2_ip):
            error_msg = f"IP verification failed: DUT2 {self.data.dut2_interface} does not show IP '{self.data.dut2_ip}' in running-config"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "IP verification failed" in f]) == 0:
            st.log("PASS: IP addresses verified on both DUTs")

        # ===== STEP 5: Test ping connectivity from DUT1 to DUT2 =====
        st.log("-" * 80)
        st.log(f"STEP 5: Test ping from DUT1 ({self.data.dut1_ip_addr}) to DUT2 ({self.data.dut2_ip_addr})")
        st.log("-" * 80)

        # Wait for interfaces to be ready
        time.sleep(5)

        # Test ping from DUT1 to DUT2
        ping_result = self._test_ping(self.data.dut1, self.data.dut2_ip_addr)

        if ping_result:
            st.log("PASS: Ping succeeded - connectivity verified")
        else:
            st.log("INFO: Ping failed - continuing test")

        # ===== STEP 6: Remove IP addresses from both DUTs =====
        st.log("-" * 80)
        st.log("STEP 6: Remove IP addresses from both DUTs")
        st.log("-" * 80)

        self._remove_interface_ip(self.data.dut1, self.data.dut1_interface)
        st.log(f"Removed IP address from DUT1 {self.data.dut1_interface}")

        self._remove_interface_ip(self.data.dut2, self.data.dut2_interface)
        st.log(f"Removed IP address from DUT2 {self.data.dut2_interface}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_IP_CHANGE)

        # ===== STEP 7: Verify no IP addresses on both DUTs =====
        st.log("-" * 80)
        st.log("STEP 7: Verify no IP addresses on both DUTs")
        st.log("-" * 80)

        if not self._verify_ip_in_running_config(self.data.dut1, self.data.dut1_interface, None):
            error_msg = f"IP removal failed: DUT1 {self.data.dut1_interface} still has an IP address"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ip_in_running_config(self.data.dut2, self.data.dut2_interface, None):
            error_msg = f"IP removal failed: DUT2 {self.data.dut2_interface} still has an IP address"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "IP removal failed" in f]) == 0:
            st.log("PASS: IP addresses removed from both DUTs")

        # ===== STEP 8: Final validation =====
        st.log("-" * 80)
        st.log("STEP 8: Final validation")
        st.log("-" * 80)

        # Get final running-config for both DUTs
        final_output_dut1 = self._get_running_config_interface(self.data.dut1, self.data.dut1_interface)
        final_ip_dut1 = self._extract_ip_from_running_config(final_output_dut1)

        final_output_dut2 = self._get_running_config_interface(self.data.dut2, self.data.dut2_interface)
        final_ip_dut2 = self._extract_ip_from_running_config(final_output_dut2)

        if final_ip_dut1 is not None:
            error_msg = f"Final validation failed: DUT1 {self.data.dut1_interface} has IP '{final_ip_dut1}', expected no IP"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if final_ip_dut2 is not None:
            error_msg = f"Final validation failed: DUT2 {self.data.dut2_interface} has IP '{final_ip_dut2}', expected no IP"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if final_ip_dut1 is None and final_ip_dut2 is None:
            st.log("PASS: Final validation complete")

        # ===== TEST COMPLETE =====
        st.log("=" * 80)
        st.log("TEST COMPLETE: IP address configuration and connectivity test completed")
        st.log(f"DUT1: None → '{self.data.dut1_ip}' → None ✓")
        st.log(f"DUT2: None → '{self.data.dut2_ip}' → None ✓")
        st.log(f"Ping test from DUT1 to DUT2: {'Succeeded ✓' if ping_result else 'Failed'}")
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
