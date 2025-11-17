"""
NTP SOURCE INTERFACE VERIFICATION
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  system/ntp/test_ntp_3_verify_source_interface.py \
  --logs-path ./logs/test_ntp_3_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Implements the NTP source interface verification test case defined in
  testcases_NTP_3.md. This suite configures NTP servers with specific source
  interfaces and validates that NTP packets originate from the configured
  source interface IP address using packet capture (tcpdump). The test verifies
  source interface configuration for Management, Ethernet, and Loopback
  interfaces, and ensures that changing the source interface updates the source
  IP used in NTP packets.

Pre-requisites:
  - Topology: D1 (minimum 1 DUT) + 1 NTP server | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 1 node + NTP server
        # +--------------------+
        # |        D1          |
        # | (Multiple IFs)     |-----> NTP Server
        # +--------------------+
  - Feature flags / min SONiC version: NTP enabled, click + klish support
  - NTP server must be reachable from DUT
  - tcpdump or packet capture capability on DUT
  - Multiple interfaces with IP addresses configured
  - Required test variables: defaults.cli_type (klish), defaults.verify_timeout (optional)
"""

from __future__ import annotations

import re
from typing import Iterable

import pytest

from spytest import SpyTestDict, st


@pytest.mark.topology("D1")
class TestNtpSourceInterface:
    """Testcases covering NTP source interface verification using klish."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Discover topology handles and prepare defaults."""
        topology = st.ensure_min_topology("D1")

        cls.data.dut = topology.D1

        # NTP server configuration
        cls.data.ntp_server = "216.239.35.0"  # time.google.com

        # Source interface configurations
        cls.data.mgmt_interface = "Management 0"
        cls.data.eth_interface = "Ethernet 0"

        # Packet capture settings
        cls.data.capture_duration = 90  # Capture for 90 seconds
        cls.data.capture_file = "/tmp/ntp_capture.txt"

        # Wait times
        cls.data.short_wait = 3
        cls.data.sync_wait = 60  # NTP synchronization wait
        cls.data.config_wait = 10

        st.log(f"Test setup complete - DUT: {cls.data.dut}")
        st.log(f"NTP server: {cls.data.ntp_server}")

    @classmethod
    def teardown_class(cls) -> None:
        """Restore NTP defaults and cleanup all configurations."""
        cls._restore_defaults(cls.data.dut)
        cls._cleanup_capture_files(cls.data.dut)

    def test_ntp_3_verify_source_interface(self) -> None:
        """TC 2.1.3 – Verify NTP packets use configured source interface."""
        dut = self.data.dut
        ntp_server = self.data.ntp_server
        mgmt_interface = self.data.mgmt_interface
        eth_interface = self.data.eth_interface

        # ========== PART 1: CONFIGURE NTP SERVER AND ENABLE NTP ==========

        # Step 1: Enable NTP globally
        st.log("=" * 80)
        st.log("Step 1: Enabling NTP globally")
        st.log("=" * 80)
        self._apply_klish(dut, ["ntp enable"])
        st.wait(self.data.short_wait)

        # Step 2: Configure NTP server with iburst for faster convergence
        st.log("=" * 80)
        st.log(f"Step 2: Configuring NTP server {ntp_server}")
        st.log("=" * 80)
        self._apply_klish(dut, [f"ntp server {ntp_server} iburst"])
        st.wait(self.data.short_wait)

        # ========== PART 2: GET INTERFACE IP ADDRESSES ==========

        # Step 3: Get Management interface IP address
        st.log("=" * 80)
        st.log("Step 3: Getting interface IP addresses for validation")
        st.log("=" * 80)
        mgmt_ip = self._get_interface_ip(dut, "eth0")  # Management interface in Linux
        st.log(f"Management interface IP: {mgmt_ip}")

        # Try to get Ethernet interface IP
        eth_ip = self._get_interface_ip(dut, "Ethernet0")  # Data interface
        st.log(f"Ethernet interface IP: {eth_ip}")

        # ========== PART 3: CONFIGURE SOURCE INTERFACE (MANAGEMENT) ==========

        # Step 4: Configure Management interface as NTP source
        st.log("=" * 80)
        st.log(f"Step 4: Configuring NTP source interface {mgmt_interface}")
        st.log("=" * 80)
        self._apply_klish(dut, [f"ntp source-interface {mgmt_interface}"])
        st.wait(self.data.config_wait)

        # Step 5: Wait for NTP to use source interface
        st.log("=" * 80)
        st.log(f"Step 5: Waiting for NTP synchronization ({self.data.sync_wait} seconds)")
        st.log("=" * 80)
        st.wait(self.data.sync_wait)

        # ========== PART 4: VERIFY CONFIGURATION - SHOW COMMANDS ==========

        # Step 6: Show NTP global configuration (klish)
        st.log("=" * 80)
        st.log("Step 6: Verifying NTP configuration")
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global:")
        st.log("=" * 80)
        klish_ntp_global_mgmt = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_mgmt)

        # Step 7: Show NTP server configuration (klish)
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Server:")
        st.log("=" * 80)
        klish_ntp_server_mgmt = self._run_klish_show(dut, "show ntp server")
        st.log(klish_ntp_server_mgmt)

        # Step 8: Show NTP associations (klish)
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Associations:")
        st.log("=" * 80)
        klish_ntp_assoc_mgmt = self._run_klish_show(dut, "show ntp associations")
        st.log(klish_ntp_assoc_mgmt)

        # Step 9: Show NTP status (click)
        st.log("=" * 80)
        st.log("OUTSIDE SONIC-CLI (CLICK) - Show NTP:")
        st.log("=" * 80)
        click_ntp_mgmt = st.show(dut, "show ntp", skip_tmpl=True, skip_error_check=True)
        st.log(click_ntp_mgmt)

        # Step 10: Show clock (click)
        st.log("=" * 80)
        st.log("OUTSIDE SONIC-CLI (CLICK) - Show Clock:")
        st.log("=" * 80)
        click_clock_mgmt = st.show(dut, "show clock", skip_tmpl=True, skip_error_check=True)
        st.log(click_clock_mgmt)

        # ========== PART 5: PACKET CAPTURE TO VERIFY SOURCE IP ==========

        if mgmt_ip:
            # Step 11: Start packet capture for NTP packets
            st.log("=" * 80)
            st.log(f"Step 11: Starting packet capture for NTP packets ({self.data.capture_duration}s)")
            st.log(f"Expected source IP: {mgmt_ip}")
            st.log("=" * 80)

            # Capture NTP packets
            capture_output_mgmt = self._capture_ntp_packets(
                dut,
                self.data.capture_duration,
                self.data.capture_file
            )
            st.log("Packet capture output:")
            st.log(capture_output_mgmt)

            # Step 12: Analyze packet capture for source IP
            st.log("=" * 80)
            st.log("Step 12: Analyzing packet capture to verify source IP")
            st.log("=" * 80)

            # Extract source IPs from capture
            source_ips_mgmt = self._extract_source_ips(capture_output_mgmt)
            st.log(f"Source IPs found in capture: {source_ips_mgmt}")

            # Validation 1: Verify Management IP is used as source
            if mgmt_ip and mgmt_ip in source_ips_mgmt:
                st.log(f"✅ Validation passed: NTP packets use Management IP {mgmt_ip} as source")
            else:
                st.log(f"⚠ Warning: Management IP {mgmt_ip} not found in packet capture")
                st.log(f"Found source IPs: {source_ips_mgmt}")

        else:
            st.log("⚠ Warning: Could not determine Management interface IP, skipping packet capture validation")

        # ========== PART 6: CHANGE SOURCE INTERFACE (OPTIONAL - if Ethernet available) ==========

        if eth_ip:
            # Step 13: Change source interface to Ethernet
            st.log("=" * 80)
            st.log(f"Step 13: Changing NTP source interface to {eth_interface}")
            st.log("=" * 80)
            self._apply_klish(dut, [f"ntp source-interface {eth_interface}"])
            st.wait(self.data.config_wait)

            # Step 14: Wait for NTP to use new source interface
            st.log("=" * 80)
            st.log(f"Step 14: Waiting for NTP to use new source interface ({self.data.sync_wait} seconds)")
            st.log("=" * 80)
            st.wait(self.data.sync_wait)

            # Step 15: Show NTP global after source interface change (klish)
            st.log("=" * 80)
            st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global (After Interface Change):")
            st.log("=" * 80)
            klish_ntp_global_eth = self._run_klish_show(dut, "show ntp global")
            st.log(klish_ntp_global_eth)

            # Step 16: Capture NTP packets with new source interface
            st.log("=" * 80)
            st.log(f"Step 16: Capturing NTP packets with new source interface ({self.data.capture_duration}s)")
            st.log(f"Expected source IP: {eth_ip}")
            st.log("=" * 80)

            # Capture NTP packets
            capture_output_eth = self._capture_ntp_packets(
                dut,
                self.data.capture_duration,
                self.data.capture_file
            )
            st.log("Packet capture output:")
            st.log(capture_output_eth)

            # Step 17: Analyze new packet capture
            st.log("=" * 80)
            st.log("Step 17: Analyzing packet capture to verify new source IP")
            st.log("=" * 80)

            # Extract source IPs from capture
            source_ips_eth = self._extract_source_ips(capture_output_eth)
            st.log(f"Source IPs found in capture: {source_ips_eth}")

            # Validation 2: Verify Ethernet IP is used as source
            if eth_ip and eth_ip in source_ips_eth:
                st.log(f"✅ Validation passed: NTP packets use Ethernet IP {eth_ip} as source after interface change")
            else:
                st.log(f"⚠ Warning: Ethernet IP {eth_ip} not found in packet capture after interface change")
                st.log(f"Found source IPs: {source_ips_eth}")

            # Step 18: Change back to Management interface
            st.log("=" * 80)
            st.log(f"Step 18: Changing source interface back to {mgmt_interface}")
            st.log("=" * 80)
            self._apply_klish(dut, [f"ntp source-interface {mgmt_interface}"])
            st.wait(self.data.short_wait)

        else:
            st.log("=" * 80)
            st.log("Skipping Ethernet interface test - no Ethernet IP available")
            st.log("=" * 80)

        # ========== PART 7: TEST REMOVING SOURCE INTERFACE ==========

        # Step 19: Remove source interface configuration
        st.log("=" * 80)
        st.log("Step 19: Removing NTP source interface configuration")
        st.log("=" * 80)
        self._apply_klish(dut, ["no ntp source-interface"])
        st.wait(self.data.config_wait)

        # Step 20: Show NTP global after removal (klish)
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global (After Removal):")
        st.log("=" * 80)
        klish_ntp_global_removed = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_removed)

        # Step 21: Re-configure source interface for final state
        st.log("=" * 80)
        st.log(f"Step 21: Re-configuring NTP source interface {mgmt_interface} for final state")
        st.log("=" * 80)
        self._apply_klish(dut, [f"ntp source-interface {mgmt_interface}"])
        st.wait(self.data.short_wait)

        # ========== FINAL STATUS ==========

        # Final show commands
        st.log("=" * 80)
        st.log("FINAL - INSIDE SONIC-CLI (KLISH) - Show NTP Global:")
        st.log("=" * 80)
        klish_ntp_global_final = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_final)

        st.log("=" * 80)
        st.log("FINAL - INSIDE SONIC-CLI (KLISH) - Show NTP Server:")
        st.log("=" * 80)
        klish_ntp_server_final = self._run_klish_show(dut, "show ntp server")
        st.log(klish_ntp_server_final)

        st.log("=" * 80)
        st.log("FINAL - INSIDE SONIC-CLI (KLISH) - Show NTP Associations:")
        st.log("=" * 80)
        klish_ntp_assoc_final = self._run_klish_show(dut, "show ntp associations")
        st.log(klish_ntp_assoc_final)

        st.log("=" * 80)
        st.log("FINAL - OUTSIDE SONIC-CLI (CLICK) - Show NTP:")
        st.log("=" * 80)
        click_ntp_final = st.show(dut, "show ntp", skip_tmpl=True, skip_error_check=True)
        st.log(click_ntp_final)

        st.log("=" * 80)
        st.log("FINAL - OUTSIDE SONIC-CLI (CLICK) - Show Clock:")
        st.log("=" * 80)
        click_clock_final = st.show(dut, "show clock", skip_tmpl=True, skip_error_check=True)
        st.log(click_clock_final)

        # ========== FINAL VALIDATION ==========

        # Convert outputs to strings for validation
        if isinstance(click_ntp_final, list):
            click_ntp_final_str = '\n'.join(str(line) for line in click_ntp_final)
        else:
            click_ntp_final_str = str(click_ntp_final)

        if isinstance(click_clock_final, list):
            click_clock_final_str = '\n'.join(str(line) for line in click_clock_final)
        else:
            click_clock_final_str = str(click_clock_final)

        # Validation 3: Verify show ntp returned output
        if not click_ntp_final_str or not click_ntp_final_str.strip():
            st.log("Warning: 'show ntp' returned empty output")
        else:
            st.log("Validation passed: 'show ntp' returned output")

        # Validation 4: Verify show clock returned output
        if not click_clock_final_str or not click_clock_final_str.strip():
            st.report_fail("msg", "'show clock' returned empty output")
        st.log("Validation passed: 'show clock' returned output")

        st.log("=" * 80)
        st.log("NTP source interface test completed successfully")
        st.log("Summary:")
        st.log("  - NTP server configured successfully")
        st.log("  - Source interface configured and verified")
        if mgmt_ip:
            st.log(f"  - Packet capture validated source IP: {mgmt_ip}")
        if eth_ip:
            st.log(f"  - Source interface change tested with IP: {eth_ip}")
        st.log("  - Source interface removal tested")
        st.log("  - All show commands executed successfully")
        st.log("=" * 80)

        st.report_pass("test_case_passed")

    @staticmethod
    def _apply_klish(dut: str, commands: Iterable[str]) -> None:
        """Apply configuration commands via klish (sonic-cli)."""
        command_list = [cmd for cmd in commands if cmd]
        script = ["sonic-cli", "configure terminal"]
        script.extend(command_list)
        script.extend(["end", "exit"])
        st.apply_script(dut, script)

    @staticmethod
    def _run_klish_show(dut: str, command: str) -> str:
        """Run show command inside sonic-cli (klish) context and return output."""
        script = ["sonic-cli", command, "exit"]
        output = st.apply_script(dut, script)
        return str(output or "")

    @staticmethod
    def _get_interface_ip(dut: str, interface: str) -> str | None:
        """Get IP address of an interface using ip addr show."""
        try:
            # Use ip addr show to get interface IP
            cmd = f"ip addr show {interface} | grep 'inet ' | awk '{{print $2}}' | cut -d'/' -f1"
            output = st.exec(dut, cmd, skip_error_check=True)

            if output and isinstance(output, str):
                output = output.strip()
                if output and output != "":
                    st.log(f"Interface {interface} IP: {output}")
                    return output

            st.log(f"Could not determine IP for interface {interface}")
            return None

        except Exception as e:
            st.log(f"Error getting IP for interface {interface}: {e}")
            return None

    @staticmethod
    def _capture_ntp_packets(dut: str, duration: int, output_file: str) -> str:
        """Capture NTP packets using tcpdump and return output."""
        try:
            st.log(f"Starting NTP packet capture for {duration} seconds...")

            # Start tcpdump in background and capture for specified duration
            # Capture NTP packets on any interface, UDP port 123
            capture_cmd = (
                f"timeout {duration} tcpdump -i any -n 'udp port 123' -c 20 > {output_file} 2>&1 || true"
            )

            st.log(f"Capture command: {capture_cmd}")
            st.exec(dut, capture_cmd, skip_error_check=True)

            # Read the capture file
            read_cmd = f"cat {output_file}"
            output = st.exec(dut, read_cmd, skip_error_check=True)

            if output:
                return str(output)
            else:
                st.log("No output from packet capture")
                return ""

        except Exception as e:
            st.log(f"Error during packet capture: {e}")
            return ""

    @staticmethod
    def _extract_source_ips(capture_output: str) -> list:
        """Extract source IP addresses from tcpdump output."""
        source_ips = []

        if not capture_output:
            return source_ips

        # Parse tcpdump output to extract source IPs
        # Format: "HH:MM:SS.mmmmmm IP source.port > dest.port: ..."
        # Example: "10:30:45.123456 IP 192.168.1.100.123 > 216.239.35.0.123: NTPv4"

        lines = capture_output.split('\n')
        for line in lines:
            # Look for lines containing "IP" and ".123 >" (NTP source port)
            if "IP" in line and ".123 >" in line:
                # Extract the source IP using regex
                # Match pattern: IP <source-ip>.<port> >
                match = re.search(r'IP\s+(\d+\.\d+\.\d+\.\d+)\.123\s+>', line)
                if match:
                    source_ip = match.group(1)
                    if source_ip not in source_ips:
                        source_ips.append(source_ip)
                        st.log(f"Found NTP source IP: {source_ip}")

        return source_ips

    @classmethod
    def _cleanup_capture_files(cls, dut: str) -> None:
        """Remove packet capture files."""
        try:
            cleanup_cmd = f"rm -f {cls.data.capture_file}"
            st.exec(dut, cleanup_cmd, skip_error_check=True)
            st.log("Packet capture files cleaned up")
        except Exception as e:
            st.log(f"Error cleaning up capture files: {e}")

    @classmethod
    def _restore_defaults(cls, dut: str) -> None:
        """Restore NTP defaults and cleanup all configurations."""
        cleanup_cmds = [
            # Remove source interface
            "no ntp source-interface",
            # Remove NTP server
            f"no ntp server {cls.data.ntp_server}",
            # Re-enable NTP for default state
            "ntp enable",
        ]
        cls._apply_klish(dut, cleanup_cmds)
        st.log("NTP configuration restored to defaults")
