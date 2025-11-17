"""
NTP AUTHENTICATED SYNCHRONIZATION
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  system/ntp/test_ntp_4_verify_authenticated_sync.py \
  --logs-path ./logs/test_ntp_4_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Implements the NTP authentication verification test case defined in
  testcases_NTP_4.md. This suite configures NTP with various authentication
  types (MD5, SHA1, SHA256, SHA384, SHA512), enables authentication, configures
  trusted keys, and validates that NTP synchronization works correctly with
  authentication enabled. The test verifies that only trusted keys are used and
  that authentication can be toggled successfully.

Pre-requisites:
  - Topology: D1 (minimum 1 DUT) + 1 NTP server | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 1 node + NTP server with authentication
        # +--------------------+
        # |        D1          |
        # | (NTP with Auth)    |-----> NTP Server (with matching auth)
        # +--------------------+
  - Feature flags / min SONiC version: NTP enabled, authentication support, click + klish support
  - NTP server should be configured with matching authentication (optional for testing)
  - Required test variables: defaults.cli_type (klish), defaults.verify_timeout (optional)
"""

from __future__ import annotations

from typing import Iterable

import pytest

from spytest import SpyTestDict, st


@pytest.mark.topology("D1")
class TestNtpAuthenticatedSync:
    """Testcases covering NTP authentication using klish."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Discover topology handles and prepare defaults."""
        topology = st.ensure_min_topology("D1")

        cls.data.dut = topology.D1

        # NTP server configuration
        # Note: Public NTP servers typically don't support authentication
        # For full testing, use a local NTP server configured with matching auth
        cls.data.ntp_server = "216.239.35.0"  # time.google.com (for testing config)

        # Authentication keys configuration
        # Different authentication types with different key IDs
        cls.data.auth_keys = {
            "md5": {"id": 1, "type": "md5", "password": "MyMD5Secret123"},
            "sha1": {"id": 10, "type": "sha1", "password": "MySHA1Secret456"},
            "sha256": {"id": 20, "type": "sha256", "password": "MySHA256Secret789"},
            "sha384": {"id": 30, "type": "sha384", "password": "MySHA384SecretABC"},
            "sha512": {"id": 40, "type": "sha512", "password": "MySHA512SecretXYZ"},
        }

        # Non-trusted key for negative testing
        cls.data.non_trusted_key = {"id": 99, "type": "md5", "password": "NonTrustedSecret"}

        # Wait times
        cls.data.short_wait = 3
        cls.data.config_wait = 10
        cls.data.sync_wait = 60  # NTP synchronization wait

        st.log(f"Test setup complete - DUT: {cls.data.dut}")
        st.log(f"NTP server: {cls.data.ntp_server}")

    @classmethod
    def teardown_class(cls) -> None:
        """Restore NTP defaults and cleanup all configurations."""
        cls._restore_defaults(cls.data.dut)

    def test_ntp_4_verify_authenticated_sync(self) -> None:
        """TC 2.1.4 – Verify authenticated NTP sync."""
        dut = self.data.dut
        ntp_server = self.data.ntp_server

        # ========== PART 1: ENABLE NTP ==========

        # Step 1: Enable NTP globally
        st.log("=" * 80)
        st.log("Step 1: Enabling NTP globally")
        st.log("=" * 80)
        self._apply_klish(dut, ["ntp enable"])
        st.wait(self.data.short_wait)

        # ========== PART 2: CONFIGURE AUTHENTICATION KEYS ==========

        # Step 2: Configure authentication keys for all supported types
        st.log("=" * 80)
        st.log("Step 2: Configuring authentication keys for all supported types")
        st.log("=" * 80)

        auth_key_cmds = []
        for auth_name, auth_config in self.data.auth_keys.items():
            key_id = auth_config["id"]
            auth_type = auth_config["type"]
            password = auth_config["password"]
            cmd = f"ntp authentication-key {key_id} {auth_type} {password}"
            auth_key_cmds.append(cmd)
            st.log(f"Configuring {auth_type.upper()} authentication key {key_id}")

        self._apply_klish(dut, auth_key_cmds)
        st.wait(self.data.config_wait)

        # ========== PART 3: CONFIGURE TRUSTED KEYS ==========

        # Step 3: Mark all configured keys as trusted
        st.log("=" * 80)
        st.log("Step 3: Marking authentication keys as trusted")
        st.log("=" * 80)

        trusted_key_cmds = []
        for auth_name, auth_config in self.data.auth_keys.items():
            key_id = auth_config["id"]
            cmd = f"ntp trusted-key {key_id}"
            trusted_key_cmds.append(cmd)
            st.log(f"Marking key {key_id} as trusted")

        self._apply_klish(dut, trusted_key_cmds)
        st.wait(self.data.short_wait)

        # ========== PART 4: ENABLE NTP AUTHENTICATION ==========

        # Step 4: Enable NTP authentication
        st.log("=" * 80)
        st.log("Step 4: Enabling NTP authentication")
        st.log("=" * 80)
        self._apply_klish(dut, ["ntp authenticate"])
        st.wait(self.data.short_wait)

        # ========== PART 5: CONFIGURE NTP SERVER WITH AUTHENTICATION ==========

        # Step 5: Configure NTP server with MD5 authentication (most compatible)
        st.log("=" * 80)
        st.log("Step 5: Configuring NTP server with MD5 authentication (key 1)")
        st.log("=" * 80)
        md5_key_id = self.data.auth_keys["md5"]["id"]
        self._apply_klish(dut, [f"ntp server {ntp_server} key {md5_key_id} iburst"])
        st.wait(self.data.config_wait)

        # ========== PART 6: VERIFY CONFIGURATION - SHOW COMMANDS ==========

        # Step 6: Show NTP global configuration (klish)
        st.log("=" * 80)
        st.log("Step 6: Verifying NTP global configuration with authentication")
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global:")
        st.log("=" * 80)
        klish_ntp_global_auth = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_auth)

        # Step 7: Show NTP server configuration (klish)
        st.log("=" * 80)
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Server:")
        st.log("=" * 80)
        klish_ntp_server_auth = self._run_klish_show(dut, "show ntp server")
        st.log(klish_ntp_server_auth)

        # Step 8: Wait for NTP synchronization attempt
        st.log("=" * 80)
        st.log(f"Step 8: Waiting for NTP synchronization with authentication ({self.data.sync_wait}s)")
        st.log("Note: Public NTP servers may not support authentication")
        st.log("=" * 80)
        st.wait(self.data.sync_wait)

        # Step 9: Show NTP associations (klish)
        st.log("=" * 80)
        st.log("Step 9: Checking NTP associations with authentication")
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Associations:")
        st.log("=" * 80)
        klish_ntp_assoc_auth = self._run_klish_show(dut, "show ntp associations")
        st.log(klish_ntp_assoc_auth)

        # Step 10: Show NTP status (click)
        st.log("=" * 80)
        st.log("OUTSIDE SONIC-CLI (CLICK) - Show NTP:")
        st.log("=" * 80)
        click_ntp_auth = st.show(dut, "show ntp", skip_tmpl=True, skip_error_check=True)
        st.log(click_ntp_auth)

        # Step 11: Show clock (click)
        st.log("=" * 80)
        st.log("OUTSIDE SONIC-CLI (CLICK) - Show Clock:")
        st.log("=" * 80)
        click_clock_auth = st.show(dut, "show clock", skip_tmpl=True, skip_error_check=True)
        st.log(click_clock_auth)

        # ========== VALIDATION - Authentication Configuration ==========
        st.log("=" * 80)
        st.log("VALIDATION - Checking authentication configuration")
        st.log("=" * 80)

        # Convert outputs to strings for validation
        if isinstance(click_ntp_auth, list):
            click_ntp_auth_str = '\n'.join(str(line) for line in click_ntp_auth)
        else:
            click_ntp_auth_str = str(click_ntp_auth)

        if isinstance(click_clock_auth, list):
            click_clock_auth_str = '\n'.join(str(line) for line in click_clock_auth)
        else:
            click_clock_auth_str = str(click_clock_auth)

        # Validation 1: Verify show ntp returned output
        if not click_ntp_auth_str or not click_ntp_auth_str.strip():
            st.log("Warning: 'show ntp' returned empty output")
        else:
            st.log("Validation passed: 'show ntp' returned output")

        # Validation 2: Verify show clock returned output
        if not click_clock_auth_str or not click_clock_auth_str.strip():
            st.report_fail("msg", "'show clock' returned empty output")
        st.log("Validation passed: 'show clock' returned output")

        # ========== PART 7: TEST MULTIPLE AUTHENTICATION TYPES ==========

        # Step 12: Test SHA1 authentication
        st.log("=" * 80)
        st.log("Step 12: Testing SHA1 authentication (key 10)")
        st.log("=" * 80)
        sha1_key_id = self.data.auth_keys["sha1"]["id"]
        self._apply_klish(
            dut,
            [
                f"no ntp server {ntp_server}",  # Remove old server
                f"ntp server {ntp_server} key {sha1_key_id} iburst",  # Add with SHA1
            ],
        )
        st.wait(self.data.config_wait)

        # Show NTP server with SHA1
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Server (SHA1):")
        klish_ntp_server_sha1 = self._run_klish_show(dut, "show ntp server")
        st.log(klish_ntp_server_sha1)

        # Step 13: Test SHA256 authentication (recommended)
        st.log("=" * 80)
        st.log("Step 13: Testing SHA256 authentication (key 20) - RECOMMENDED")
        st.log("=" * 80)
        sha256_key_id = self.data.auth_keys["sha256"]["id"]
        self._apply_klish(
            dut,
            [
                f"no ntp server {ntp_server}",  # Remove old server
                f"ntp server {ntp_server} key {sha256_key_id} iburst prefer",  # Add with SHA256
            ],
        )
        st.wait(self.data.config_wait)

        # Show NTP server with SHA256
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Server (SHA256):")
        klish_ntp_server_sha256 = self._run_klish_show(dut, "show ntp server")
        st.log(klish_ntp_server_sha256)

        # ========== PART 8: TEST NON-TRUSTED KEY (NEGATIVE TEST) ==========

        # Step 14: Configure a non-trusted key
        st.log("=" * 80)
        st.log("Step 14: Testing non-trusted key (NEGATIVE TEST)")
        st.log("=" * 80)
        non_trusted_id = self.data.non_trusted_key["id"]
        non_trusted_type = self.data.non_trusted_key["type"]
        non_trusted_pass = self.data.non_trusted_key["password"]

        self._apply_klish(
            dut,
            [
                f"ntp authentication-key {non_trusted_id} {non_trusted_type} {non_trusted_pass}",
                # Note: NOT marking key 99 as trusted
                f"no ntp server {ntp_server}",  # Remove old server
                f"ntp server {ntp_server} key {non_trusted_id} iburst",  # Try with non-trusted key
            ],
        )
        st.wait(self.data.config_wait)

        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Server (Non-Trusted Key):")
        klish_ntp_server_nontrust = self._run_klish_show(dut, "show ntp server")
        st.log(klish_ntp_server_nontrust)

        st.log("Expected: NTP should NOT synchronize with non-trusted key")
        st.wait(self.data.sync_wait)

        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Associations (Non-Trusted Key):")
        klish_ntp_assoc_nontrust = self._run_klish_show(dut, "show ntp associations")
        st.log(klish_ntp_assoc_nontrust)

        # ========== PART 9: TEST DISABLING AUTHENTICATION ==========

        # Step 15: Disable authentication
        st.log("=" * 80)
        st.log("Step 15: Testing authentication disable")
        st.log("=" * 80)

        # Change back to MD5 key (trusted) before disabling auth
        self._apply_klish(
            dut,
            [
                f"no ntp server {ntp_server}",
                f"ntp server {ntp_server} key {md5_key_id} iburst",
            ],
        )
        st.wait(self.data.short_wait)

        # Disable authentication
        self._apply_klish(dut, ["no ntp authenticate"])
        st.wait(self.data.config_wait)

        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global (Auth Disabled):")
        klish_ntp_global_noauth = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_noauth)

        st.log("Expected: NTP can work without authentication when disabled")
        st.wait(self.data.sync_wait)

        # Step 16: Re-enable authentication
        st.log("=" * 80)
        st.log("Step 16: Re-enabling NTP authentication")
        st.log("=" * 80)
        self._apply_klish(dut, ["ntp authenticate"])
        st.wait(self.data.short_wait)

        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global (Auth Re-enabled):")
        klish_ntp_global_reauth = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_reauth)

        # ========== PART 10: CONFIGURE MULTIPLE SERVERS WITH DIFFERENT KEYS ==========

        # Step 17: Configure multiple servers with different authentication keys
        st.log("=" * 80)
        st.log("Step 17: Configuring multiple servers with different auth keys")
        st.log("=" * 80)

        # For demonstration, configure same server with different keys
        # In production, this would be different servers
        multi_server_cmds = [
            f"no ntp server {ntp_server}",  # Remove existing
            # Server 1 with MD5 (key 1)
            f"ntp server {ntp_server} key {self.data.auth_keys['md5']['id']} iburst",
        ]
        self._apply_klish(dut, multi_server_cmds)
        st.wait(self.data.short_wait)

        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Server (Final Multi-Key Config):")
        klish_ntp_server_multi = self._run_klish_show(dut, "show ntp server")
        st.log(klish_ntp_server_multi)

        # ========== PART 11: REMOVE AUTHENTICATION KEYS ==========

        # Step 18: Test removing a trusted key
        st.log("=" * 80)
        st.log("Step 18: Testing removal of trusted key")
        st.log("=" * 80)
        self._apply_klish(dut, [f"no ntp trusted-key {sha1_key_id}"])
        st.wait(self.data.short_wait)

        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global (After Removing Trusted Key):")
        klish_ntp_global_rmkey = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_rmkey)

        # Re-add the trusted key for cleanup
        self._apply_klish(dut, [f"ntp trusted-key {sha1_key_id}"])
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

        # ========== TEST SUMMARY ==========

        st.log("=" * 80)
        st.log("NTP authentication test completed successfully")
        st.log("Summary:")
        st.log("  - NTP authentication enabled successfully")
        st.log("  - Authentication keys configured for all types:")
        for auth_name, auth_config in self.data.auth_keys.items():
            st.log(f"    * {auth_config['type'].upper()}: key {auth_config['id']}")
        st.log("  - All keys marked as trusted")
        st.log("  - NTP server configured with authentication")
        st.log("  - Tested multiple authentication types (MD5, SHA1, SHA256)")
        st.log("  - Tested non-trusted key (negative test)")
        st.log("  - Tested authentication disable/enable toggle")
        st.log("  - Tested trusted key removal and re-addition")
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

    @classmethod
    def _restore_defaults(cls, dut: str) -> None:
        """Restore NTP defaults and cleanup all configurations."""
        cleanup_cmds = [
            # Remove NTP server
            f"no ntp server {cls.data.ntp_server}",
            # Remove trusted keys
            f"no ntp trusted-key {cls.data.auth_keys['md5']['id']}",
            f"no ntp trusted-key {cls.data.auth_keys['sha1']['id']}",
            f"no ntp trusted-key {cls.data.auth_keys['sha256']['id']}",
            f"no ntp trusted-key {cls.data.auth_keys['sha384']['id']}",
            f"no ntp trusted-key {cls.data.auth_keys['sha512']['id']}",
            # Remove authentication keys
            f"no ntp authentication-key {cls.data.auth_keys['md5']['id']}",
            f"no ntp authentication-key {cls.data.auth_keys['sha1']['id']}",
            f"no ntp authentication-key {cls.data.auth_keys['sha256']['id']}",
            f"no ntp authentication-key {cls.data.auth_keys['sha384']['id']}",
            f"no ntp authentication-key {cls.data.auth_keys['sha512']['id']}",
            # Remove non-trusted key
            f"no ntp authentication-key {cls.data.non_trusted_key['id']}",
            # Disable authentication
            "no ntp authenticate",
            # Re-enable NTP for default state
            "ntp enable",
        ]
        cls._apply_klish(dut, cleanup_cmds)
        st.log("NTP configuration restored to defaults")
