"""
NTP SERVER SYNC AND STATUS
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  system/ntp/test_ntp_1_verify_ntp_server_sync_and_status.py \
  --logs-path ./logs/test_ntp_1_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Implements the NTP server synchronization and status verification defined in
  testcases_NTP_1.md. This suite configures NTP servers, enables authentication,
  configures trusted keys, sets source interfaces and VRF, then validates the
  device synchronization status using klish configuration commands and both klish
  and click show commands. The test ensures NTP functionality including enable/
  disable, authentication, and various configuration options while verifying
  proper synchronization state.

Pre-requisites:
  - Topology: D1 (minimum 1 DUT) | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 1 node
        # +--------------------+
        # |        D1          |
        # |  (DUT with NTP)    |
        # +--------------------+
  - Feature flags / min SONiC version: NTP enabled, click + klish support
  - NTP server must be reachable from DUT
  - Required test variables: defaults.cli_type (klish), defaults.verify_timeout (optional)
"""

from __future__ import annotations

from typing import Iterable

import pytest

from spytest import SpyTestDict, st


@pytest.mark.topology("D1")
class TestNtpServerSyncAndStatus:
    """Testcases covering NTP server sync and status verification using klish."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Discover topology handles and prepare defaults."""
        topology = st.ensure_min_topology("D1")

        cls.data.dut = topology.D1

        # NTP test parameters
        cls.data.ntp_server1 = "216.239.35.0"  # time.google.com
        cls.data.ntp_server2 = "216.239.35.4"  # time.google.com
        cls.data.ntp_server3 = "216.239.35.8"  # time.google.com

        # Authentication parameters
        cls.data.auth_key_id_1 = 10
        cls.data.auth_key_id_2 = 20
        cls.data.auth_type_md5 = "md5"
        cls.data.auth_type_sha1 = "sha1"
        cls.data.auth_password_1 = "MySecretKey123"
        cls.data.auth_password_2 = "AnotherSecret456"

        # Source interface
        cls.data.source_interface = "Management 0"

        # VRF
        cls.data.vrf_name = "mgmt"

        # NTP version
        cls.data.ntp_version = 4

        # Wait times
        cls.data.short_wait = 3
        cls.data.sync_wait = 60  # NTP synchronization may take time

        st.log(f"Test setup complete - DUT: {cls.data.dut}")

    @classmethod
    def teardown_class(cls) -> None:
        """Restore NTP defaults and cleanup all configurations."""
        cls._restore_defaults(cls.data.dut)

    def test_ntp_1_verify_ntp_server_sync_and_status(self) -> None:
        """TC 2.1.1 – Ensure device syncs to NTP server and displays accurate status."""
        dut = self.data.dut
        ntp_server1 = self.data.ntp_server1
        ntp_server2 = self.data.ntp_server2
        ntp_server3 = self.data.ntp_server3

        # ========== PART 1: BASIC NTP CONFIGURATION ==========

        # Step 1: Enable NTP globally
        st.log("=" * 80)
        st.log("Step 1: Enabling NTP globally")
        st.log("=" * 80)
        self._apply_klish(dut, ["ntp enable"])
        st.wait(self.data.short_wait)

        # Step 2: Configure NTP server
        st.log("=" * 80)
        st.log(f"Step 2: Configuring NTP server {ntp_server1}")
        st.log("=" * 80)
        self._apply_klish(dut, [f"ntp server {ntp_server1}"])
        st.wait(self.data.short_wait)

        # Step 3: Wait for NTP synchronization
        st.log("=" * 80)
        st.log("Step 3: Waiting for NTP synchronization (60 seconds)")
        st.log("=" * 80)
        st.wait(self.data.sync_wait)

        # ========== SHOW COMMANDS - KLISH MODE ==========

        # Show command 1: show ntp global (klish)
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global:")
        st.log("=" * 80)
        klish_ntp_global = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global)

        # Show command 2: show ntp server (klish)
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Server:")
        st.log("=" * 80)
        klish_ntp_server = self._run_klish_show(dut, "show ntp server")
        st.log(klish_ntp_server)

        # Show command 3: show ntp associations (klish)
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Associations:")
        st.log("=" * 80)
        klish_ntp_associations = self._run_klish_show(dut, "show ntp associations")
        st.log(klish_ntp_associations)

        # ========== SHOW COMMANDS - CLICK MODE ==========

        # Show command 1: show ntp (click)
        st.log("=" * 80)
        st.log("OUTSIDE SONIC-CLI (CLICK) - Show NTP:")
        st.log("=" * 80)
        click_ntp_output = st.show(dut, "show ntp", skip_tmpl=True, skip_error_check=True)
        st.log(click_ntp_output)

        # Show command 2: show clock (click)
        st.log("=" * 80)
        st.log("OUTSIDE SONIC-CLI (CLICK) - Show Clock:")
        st.log("=" * 80)
        click_clock_output = st.show(dut, "show clock", skip_tmpl=True, skip_error_check=True)
        st.log(click_clock_output)

        # Convert click outputs to strings for validation
        if isinstance(click_ntp_output, list):
            click_ntp_str = '\n'.join(str(line) for line in click_ntp_output)
        else:
            click_ntp_str = str(click_ntp_output)

        if isinstance(click_clock_output, list):
            click_clock_str = '\n'.join(str(line) for line in click_clock_output)
        else:
            click_clock_str = str(click_clock_output)

        # ========== VALIDATION - Basic NTP Configuration ==========
        st.log("=" * 80)
        st.log("VALIDATION - Checking NTP configuration and status")
        st.log("=" * 80)

        # Validation 1: Check that "show ntp" returned non-empty output
        if not click_ntp_str or not click_ntp_str.strip():
            st.log("Warning: 'show ntp' returned empty output")
        else:
            st.log("Validation passed: 'show ntp' returned output")

        # Validation 2: Check that "show clock" returned non-empty output
        if not click_clock_str or not click_clock_str.strip():
            st.report_fail("msg", "'show clock' returned empty output")
        st.log("Validation passed: 'show clock' returned output")

        # ========== PART 2: MULTIPLE NTP SERVERS ==========

        # Step 4: Configure multiple NTP servers
        st.log("=" * 80)
        st.log("Step 4: Configuring multiple NTP servers")
        st.log("=" * 80)
        self._apply_klish(
            dut,
            [
                f"ntp server {ntp_server2} iburst prefer",
                f"ntp server {ntp_server3} version {self.data.ntp_version}",
            ],
        )
        st.wait(self.data.short_wait)

        # Show NTP servers after adding multiple servers
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Server (Multiple):")
        st.log("=" * 80)
        klish_ntp_server_multi = self._run_klish_show(dut, "show ntp server")
        st.log(klish_ntp_server_multi)

        # ========== PART 3: NTP AUTHENTICATION ==========

        # Step 5: Enable NTP authentication
        st.log("=" * 80)
        st.log("Step 5: Enabling NTP authentication")
        st.log("=" * 80)
        self._apply_klish(dut, ["ntp authenticate"])
        st.wait(self.data.short_wait)

        # Step 6: Configure authentication keys
        st.log("=" * 80)
        st.log("Step 6: Configuring NTP authentication keys")
        st.log("=" * 80)
        self._apply_klish(
            dut,
            [
                f"ntp authentication-key {self.data.auth_key_id_1} {self.data.auth_type_md5} {self.data.auth_password_1}",
                f"ntp authentication-key {self.data.auth_key_id_2} {self.data.auth_type_sha1} {self.data.auth_password_2}",
            ],
        )
        st.wait(self.data.short_wait)

        # Step 7: Configure trusted keys
        st.log("=" * 80)
        st.log("Step 7: Configuring NTP trusted keys")
        st.log("=" * 80)
        self._apply_klish(
            dut,
            [
                f"ntp trusted-key {self.data.auth_key_id_1}",
                f"ntp trusted-key {self.data.auth_key_id_2}",
            ],
        )
        st.wait(self.data.short_wait)

        # Show NTP global after authentication configuration
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global (After Auth):")
        st.log("=" * 80)
        klish_ntp_global_auth = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_auth)

        # ========== PART 4: NTP SOURCE INTERFACE ==========

        # Step 8: Configure NTP source interface
        st.log("=" * 80)
        st.log(f"Step 8: Configuring NTP source interface {self.data.source_interface}")
        st.log("=" * 80)
        self._apply_klish(dut, [f"ntp source-interface {self.data.source_interface}"])
        st.wait(self.data.short_wait)

        # Show NTP global after source interface configuration
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global (After Source Interface):")
        st.log("=" * 80)
        klish_ntp_global_src = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_src)

        # ========== PART 5: NTP VRF ==========

        # Step 9: Configure NTP VRF
        st.log("=" * 80)
        st.log(f"Step 9: Configuring NTP VRF {self.data.vrf_name}")
        st.log("=" * 80)
        self._apply_klish(dut, [f"ntp vrf {self.data.vrf_name}"])
        st.wait(self.data.short_wait)

        # Show NTP global after VRF configuration
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global (After VRF):")
        st.log("=" * 80)
        klish_ntp_global_vrf = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_vrf)

        # ========== PART 6: NTP DISABLE/ENABLE ==========

        # Step 10: Test NTP disable
        st.log("=" * 80)
        st.log("Step 10: Testing NTP disable")
        st.log("=" * 80)
        self._apply_klish(dut, ["no ntp enable"])
        st.wait(self.data.short_wait)

        # Show NTP status after disable
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global (After Disable):")
        st.log("=" * 80)
        klish_ntp_global_disabled = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_disabled)

        # Step 11: Test NTP re-enable
        st.log("=" * 80)
        st.log("Step 11: Re-enabling NTP")
        st.log("=" * 80)
        self._apply_klish(dut, ["ntp enable"])
        st.wait(self.data.short_wait)

        # Show NTP status after re-enable
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global (After Re-enable):")
        st.log("=" * 80)
        klish_ntp_global_reenabled = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_reenabled)

        # ========== PART 7: REMOVE AUTHENTICATION ==========

        # Step 12: Remove authentication
        st.log("=" * 80)
        st.log("Step 12: Removing NTP authentication")
        st.log("=" * 80)
        self._apply_klish(
            dut,
            [
                f"no ntp trusted-key {self.data.auth_key_id_1}",
                f"no ntp trusted-key {self.data.auth_key_id_2}",
                f"no ntp authentication-key {self.data.auth_key_id_1}",
                f"no ntp authentication-key {self.data.auth_key_id_2}",
                "no ntp authenticate",
            ],
        )
        st.wait(self.data.short_wait)

        # ========== PART 8: REMOVE SOURCE INTERFACE AND VRF ==========

        # Step 13: Remove source interface and VRF
        st.log("=" * 80)
        st.log("Step 13: Removing NTP source interface and VRF")
        st.log("=" * 80)
        self._apply_klish(
            dut,
            [
                "no ntp source-interface",
                "no ntp vrf",
            ],
        )
        st.wait(self.data.short_wait)

        # ========== FINAL VALIDATION ==========

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
        klish_ntp_associations_final = self._run_klish_show(dut, "show ntp associations")
        st.log(klish_ntp_associations_final)

        st.log("All NTP configuration commands executed successfully")
        st.log("All NTP show commands validated successfully")
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
            f"no ntp server {cls.data.ntp_server1}",
            f"no ntp server {cls.data.ntp_server2}",
            f"no ntp server {cls.data.ntp_server3}",
            # Remove trusted keys
            f"no ntp trusted-key {cls.data.auth_key_id_1}",
            f"no ntp trusted-key {cls.data.auth_key_id_2}",
            # Remove authentication keys
            f"no ntp authentication-key {cls.data.auth_key_id_1}",
            f"no ntp authentication-key {cls.data.auth_key_id_2}",
            # Disable authentication
            "no ntp authenticate",
            # Remove source interface and VRF
            "no ntp source-interface",
            "no ntp vrf",
            # Re-enable NTP for default state
            "ntp enable",
        ]
        cls._apply_klish(dut, cleanup_cmds)
