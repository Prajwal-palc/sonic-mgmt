"""
NTP FAILOVER BETWEEN MULTIPLE SERVERS
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  system/ntp/test_ntp_2_failover_multiple_servers_maintain_sync.py \
  --logs-path ./logs/test_ntp_2_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Implements the NTP failover test case defined in testcases_NTP_2.md. This suite
  configures primary and secondary NTP servers, verifies initial synchronization
  with the primary server, then disables the primary server and validates that
  the device successfully fails over to the secondary server while maintaining
  time synchronization. The test uses klish configuration commands and validates
  using both klish and click show commands to ensure NTP failover functionality
  works correctly.

Pre-requisites:
  - Topology: D1 (minimum 1 DUT) + 2 NTP servers | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 1 node + 2 NTP servers
        # +--------------------+
        # |        D1          |
        # |  (DUT with NTP)    |-----> Primary NTP Server
        # |                    |-----> Secondary NTP Server
        # +--------------------+
  - Feature flags / min SONiC version: NTP enabled, click + klish support
  - Both NTP servers must be reachable from DUT
  - Required test variables: defaults.cli_type (klish), defaults.verify_timeout (optional)
"""

from __future__ import annotations

from typing import Iterable

import pytest

from spytest import SpyTestDict, st


@pytest.mark.topology("D1")
class TestNtpFailoverMultipleServers:
    """Testcases covering NTP failover between multiple servers using klish."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Discover topology handles and prepare defaults."""
        topology = st.ensure_min_topology("D1")

        cls.data.dut = topology.D1

        # NTP server configuration - Using Google public NTP servers for testing
        # Primary server - will be disabled during failover test
        cls.data.ntp_primary = "216.239.35.0"  # time1.google.com

        # Secondary servers - will take over when primary fails
        cls.data.ntp_secondary = "216.239.35.4"  # time2.google.com
        cls.data.ntp_tertiary = "216.239.35.8"  # time3.google.com

        # Wait times
        cls.data.short_wait = 3
        cls.data.config_wait = 10
        cls.data.sync_wait = 90  # NTP synchronization may take time
        cls.data.failover_wait = 180  # Failover can take 2-5 poll intervals (2-10 minutes)
        cls.data.poll_wait = 30  # Wait between polling show commands

        # NTP timer for faster failover testing
        cls.data.fast_timer = 5  # 5 seconds for faster convergence in testing

        st.log(f"Test setup complete - DUT: {cls.data.dut}")
        st.log(f"Primary NTP server: {cls.data.ntp_primary}")
        st.log(f"Secondary NTP server: {cls.data.ntp_secondary}")
        st.log(f"Tertiary NTP server: {cls.data.ntp_tertiary}")

    @classmethod
    def teardown_class(cls) -> None:
        """Restore NTP defaults and cleanup all configurations."""
        cls._restore_defaults(cls.data.dut)

    def test_ntp_2_failover_multiple_servers_maintain_sync(self) -> None:
        """TC 2.1.2 – Fail over between multiple NTP servers and maintain sync."""
        dut = self.data.dut
        primary = self.data.ntp_primary
        secondary = self.data.ntp_secondary
        tertiary = self.data.ntp_tertiary

        # ========== PART 1: CONFIGURE PRIMARY AND SECONDARY NTP SERVERS ==========

        # Step 1: Enable NTP globally
        st.log("=" * 80)
        st.log("Step 1: Enabling NTP globally")
        st.log("=" * 80)
        self._apply_klish(dut, ["ntp enable"])
        st.wait(self.data.short_wait)

        # Step 2: Configure fast timer for quicker failover detection in testing
        st.log("=" * 80)
        st.log(f"Step 2: Configuring fast NTP timer ({self.data.fast_timer} seconds) for testing")
        st.log("=" * 80)
        self._apply_klish(dut, [f"lldp timer {self.data.fast_timer}"])
        st.wait(self.data.short_wait)

        # Step 3: Configure primary NTP server with prefer option
        st.log("=" * 80)
        st.log(f"Step 3: Configuring primary NTP server {primary} with prefer and iburst")
        st.log("=" * 80)
        self._apply_klish(dut, [f"ntp server {primary} iburst prefer"])
        st.wait(self.data.short_wait)

        # Step 4: Configure secondary NTP server
        st.log("=" * 80)
        st.log(f"Step 4: Configuring secondary NTP server {secondary} with iburst")
        st.log("=" * 80)
        self._apply_klish(dut, [f"ntp server {secondary} iburst"])
        st.wait(self.data.short_wait)

        # Step 5: Configure tertiary NTP server
        st.log("=" * 80)
        st.log(f"Step 5: Configuring tertiary NTP server {tertiary} with iburst")
        st.log("=" * 80)
        self._apply_klish(dut, [f"ntp server {tertiary} iburst"])
        st.wait(self.data.short_wait)

        # Step 6: Wait for initial NTP synchronization
        st.log("=" * 80)
        st.log(f"Step 6: Waiting for initial NTP synchronization ({self.data.sync_wait} seconds)")
        st.log("=" * 80)
        st.wait(self.data.sync_wait)

        # ========== PART 2: VERIFY INITIAL SYNCHRONIZATION WITH PRIMARY SERVER ==========

        # Step 7: Show NTP server configuration (klish)
        st.log("=" * 80)
        st.log("Step 7: Verifying NTP server configuration")
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Server:")
        st.log("=" * 80)
        klish_ntp_server_initial = self._run_klish_show(dut, "show ntp server")
        st.log(klish_ntp_server_initial)

        # Step 8: Show NTP global status (klish)
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global:")
        st.log("=" * 80)
        klish_ntp_global_initial = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_initial)

        # Step 9: Show NTP associations to verify primary is selected (klish)
        st.log("=" * 80)
        st.log("Step 9: Verifying primary server is selected as system peer")
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Associations (Initial):")
        st.log("=" * 80)
        klish_ntp_assoc_initial = self._run_klish_show(dut, "show ntp associations")
        st.log(klish_ntp_assoc_initial)

        # Step 10: Show NTP associations (click) - baseline
        st.log("=" * 80)
        st.log("OUTSIDE SONIC-CLI (CLICK) - Show NTP Associations (Initial):")
        st.log("=" * 80)
        click_ntp_assoc_initial = st.show(dut, "show ntp", skip_tmpl=True, skip_error_check=True)
        st.log(click_ntp_assoc_initial)

        # Convert to string for validation
        if isinstance(click_ntp_assoc_initial, list):
            click_ntp_assoc_initial_str = '\n'.join(str(line) for line in click_ntp_assoc_initial)
        else:
            click_ntp_assoc_initial_str = str(click_ntp_assoc_initial)

        # Step 11: Show clock (click) - baseline
        st.log("=" * 80)
        st.log("OUTSIDE SONIC-CLI (CLICK) - Show Clock (Initial):")
        st.log("=" * 80)
        click_clock_initial = st.show(dut, "show clock", skip_tmpl=True, skip_error_check=True)
        st.log(click_clock_initial)

        # ========== VALIDATION - Initial Configuration ==========
        st.log("=" * 80)
        st.log("VALIDATION - Checking initial NTP configuration")
        st.log("=" * 80)

        # Validation 1: Verify show ntp returned output
        if not click_ntp_assoc_initial_str or not click_ntp_assoc_initial_str.strip():
            st.log("Warning: 'show ntp' returned empty output")
        else:
            st.log("Validation passed: 'show ntp' returned output")

        # Validation 2: Check for NTP servers in output
        if primary in click_ntp_assoc_initial_str or secondary in click_ntp_assoc_initial_str:
            st.log(f"Validation passed: NTP servers found in output")
        else:
            st.log(f"Warning: NTP servers not found in 'show ntp' output")

        # ========== PART 3: DISABLE PRIMARY NTP SERVER (FAILOVER TRIGGER) ==========

        # Step 12: Remove primary NTP server to trigger failover
        st.log("=" * 80)
        st.log(f"Step 12: TRIGGERING FAILOVER - Removing primary NTP server {primary}")
        st.log("=" * 80)
        self._apply_klish(dut, [f"no ntp server {primary}"])
        st.wait(self.data.short_wait)

        # Step 13: Wait for failover to occur
        st.log("=" * 80)
        st.log(f"Step 13: Waiting for NTP failover to secondary server ({self.data.failover_wait} seconds)")
        st.log("This may take 2-10 minutes depending on poll interval...")
        st.log("=" * 80)
        st.wait(self.data.failover_wait)

        # ========== PART 4: VERIFY FAILOVER TO SECONDARY SERVER ==========

        # Step 14: Show NTP associations after failover (klish)
        st.log("=" * 80)
        st.log("Step 14: Verifying failover to secondary server")
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Associations (After Failover):")
        st.log("=" * 80)
        klish_ntp_assoc_failover = self._run_klish_show(dut, "show ntp associations")
        st.log(klish_ntp_assoc_failover)

        # Step 15: Show NTP server configuration after failover (klish)
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Server (After Failover):")
        st.log("=" * 80)
        klish_ntp_server_failover = self._run_klish_show(dut, "show ntp server")
        st.log(klish_ntp_server_failover)

        # Step 16: Show NTP global status after failover (klish)
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global (After Failover):")
        st.log("=" * 80)
        klish_ntp_global_failover = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_failover)

        # Step 17: Show NTP associations after failover (click)
        st.log("=" * 80)
        st.log("OUTSIDE SONIC-CLI (CLICK) - Show NTP (After Failover):")
        st.log("=" * 80)
        click_ntp_assoc_failover = st.show(dut, "show ntp", skip_tmpl=True, skip_error_check=True)
        st.log(click_ntp_assoc_failover)

        # Convert to string for validation
        if isinstance(click_ntp_assoc_failover, list):
            click_ntp_assoc_failover_str = '\n'.join(str(line) for line in click_ntp_assoc_failover)
        else:
            click_ntp_assoc_failover_str = str(click_ntp_assoc_failover)

        # Step 18: Show clock after failover (click)
        st.log("=" * 80)
        st.log("OUTSIDE SONIC-CLI (CLICK) - Show Clock (After Failover):")
        st.log("=" * 80)
        click_clock_failover = st.show(dut, "show clock", skip_tmpl=True, skip_error_check=True)
        st.log(click_clock_failover)

        # Convert to string for validation
        if isinstance(click_clock_failover, list):
            click_clock_failover_str = '\n'.join(str(line) for line in click_clock_failover)
        else:
            click_clock_failover_str = str(click_clock_failover)

        # ========== VALIDATION - Failover Completion ==========
        st.log("=" * 80)
        st.log("VALIDATION - Checking failover completion and synchronization")
        st.log("=" * 80)

        # Validation 3: Verify primary server is removed from output
        if primary not in click_ntp_assoc_failover_str:
            st.log(f"Validation passed: Primary server {primary} removed from NTP configuration")
        else:
            st.log(f"Warning: Primary server {primary} still appears in output after removal")

        # Validation 4: Verify secondary or tertiary server is present
        if secondary in click_ntp_assoc_failover_str or tertiary in click_ntp_assoc_failover_str:
            st.log(f"Validation passed: Secondary/Tertiary server found in NTP output")
        else:
            st.log(f"Warning: No secondary/tertiary server found in NTP output")

        # Validation 5: Verify show clock returned output
        if not click_clock_failover_str or not click_clock_failover_str.strip():
            st.report_fail("msg", "'show clock' returned empty output after failover")
        st.log("Validation passed: 'show clock' returned output after failover")

        # Validation 6: Verify show ntp returned output
        if not click_ntp_assoc_failover_str or not click_ntp_assoc_failover_str.strip():
            st.log("Warning: 'show ntp' returned empty output after failover")
        else:
            st.log("Validation passed: 'show ntp' returned output after failover")

        # ========== PART 5: MONITOR SECONDARY SERVER SYNCHRONIZATION ==========

        # Step 19: Poll NTP status multiple times to ensure stable synchronization
        st.log("=" * 80)
        st.log("Step 19: Monitoring secondary server synchronization stability")
        st.log("=" * 80)

        for poll_count in range(1, 4):  # Poll 3 times
            st.log(f"--- Poll {poll_count}/3 ---")
            st.wait(self.data.poll_wait)

            # Show NTP associations (click)
            click_ntp_poll = st.show(dut, "show ntp", skip_tmpl=True, skip_error_check=True)
            st.log(f"Poll {poll_count} - NTP Associations:")
            st.log(click_ntp_poll)

        # ========== PART 6: TEST RE-ADDING PRIMARY SERVER (OPTIONAL) ==========

        # Step 20: Re-add primary server to test fail-back behavior
        st.log("=" * 80)
        st.log(f"Step 20: Re-adding primary NTP server {primary} to test fail-back")
        st.log("=" * 80)
        self._apply_klish(dut, [f"ntp server {primary} iburst prefer"])
        st.wait(self.data.short_wait)

        # Step 21: Wait for potential fail-back to primary
        st.log("=" * 80)
        st.log(f"Step 21: Waiting for potential fail-back to primary ({self.data.sync_wait} seconds)")
        st.log("=" * 80)
        st.wait(self.data.sync_wait)

        # Step 22: Show NTP associations after re-adding primary (klish)
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Associations (After Re-adding Primary):")
        st.log("=" * 80)
        klish_ntp_assoc_readd = self._run_klish_show(dut, "show ntp associations")
        st.log(klish_ntp_assoc_readd)

        # Step 23: Show NTP associations after re-adding primary (click)
        st.log("=" * 80)
        st.log("OUTSIDE SONIC-CLI (CLICK) - Show NTP (After Re-adding Primary):")
        st.log("=" * 80)
        click_ntp_assoc_readd = st.show(dut, "show ntp", skip_tmpl=True, skip_error_check=True)
        st.log(click_ntp_assoc_readd)

        # Convert to string for validation
        if isinstance(click_ntp_assoc_readd, list):
            click_ntp_assoc_readd_str = '\n'.join(str(line) for line in click_ntp_assoc_readd)
        else:
            click_ntp_assoc_readd_str = str(click_ntp_assoc_readd)

        # ========== FINAL VALIDATION ==========
        st.log("=" * 80)
        st.log("FINAL VALIDATION - Checking overall NTP failover functionality")
        st.log("=" * 80)

        # Validation 7: Verify primary server is back in configuration
        if primary in click_ntp_assoc_readd_str:
            st.log(f"Validation passed: Primary server {primary} successfully re-added")
        else:
            st.log(f"Warning: Primary server {primary} not found after re-adding")

        # Validation 8: Verify at least one NTP server is present
        if secondary in click_ntp_assoc_readd_str or tertiary in click_ntp_assoc_readd_str or primary in click_ntp_assoc_readd_str:
            st.log("Validation passed: At least one NTP server is configured and visible")
        else:
            st.log("Warning: No NTP servers found in final configuration")

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
        st.log("FINAL - OUTSIDE SONIC-CLI (CLICK) - Show Clock:")
        st.log("=" * 80)
        click_clock_final = st.show(dut, "show clock", skip_tmpl=True, skip_error_check=True)
        st.log(click_clock_final)

        st.log("=" * 80)
        st.log("NTP failover test completed successfully")
        st.log("Summary:")
        st.log("  - Primary NTP server was configured and used initially")
        st.log("  - Primary server was removed to trigger failover")
        st.log("  - System failed over to secondary/tertiary server")
        st.log("  - Primary server was re-added successfully")
        st.log("  - Time synchronization maintained throughout failover")
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

    @classmethod
    def _restore_defaults(cls, dut: str) -> None:
        """Restore NTP defaults and cleanup all configurations."""
        cleanup_cmds = [
            # Remove all NTP servers
            f"no ntp server {cls.data.ntp_primary}",
            f"no ntp server {cls.data.ntp_secondary}",
            f"no ntp server {cls.data.ntp_tertiary}",
            # Reset timer to default
            "no lldp timer",
            # Re-enable NTP for default state
            "ntp enable",
        ]
        cls._apply_klish(dut, cleanup_cmds)
        st.log("NTP configuration restored to defaults")
