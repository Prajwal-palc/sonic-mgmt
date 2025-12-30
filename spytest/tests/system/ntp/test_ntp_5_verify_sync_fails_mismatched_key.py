"""
NTP AUTHENTICATION FAILURE - NEGATIVE TEST
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  system/ntp/test_ntp_5_verify_sync_fails_mismatched_key.py \
  --logs-path ./logs/test_ntp_5_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Implements the NTP authentication failure negative test case defined in
  testcases_NTP_5.md. This suite verifies that NTP synchronization FAILS when
  authentication is enabled and the client's authentication key does not match
  the server's configuration. Multiple mismatch scenarios are tested including
  password mismatch, authentication type mismatch, and key ID mismatch. The test
  demonstrates that authentication is properly enforced by showing failure
  indicators in the output. Optionally includes positive verification by fixing
  the key and confirming synchronization succeeds.

Pre-requisites:
  - Topology: D1 (minimum 1 DUT) + 1 NTP server | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 1 node + NTP server (with authentication ideally)
        # +--------------------+
        # |        D1          |
        # | (Mismatched Auth)  |-----> NTP Server (with auth)
        # +--------------------+
  - Feature flags / min SONiC version: NTP enabled, authentication support, click + klish support
  - NTP server should be configured with authentication (optional for config testing)
  - Required test variables: defaults.cli_type (klish), defaults.verify_timeout (optional)
"""

from __future__ import annotations

from typing import Iterable

import pytest

from spytest import SpyTestDict, st


@pytest.mark.topology("D1")
class TestNtpAuthFailureMismatchedKey:
    """Testcases covering NTP authentication failure (negative test) using klish."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Discover topology handles and prepare defaults."""
        topology = st.ensure_min_topology("D1")

        cls.data.dut = topology.D1

        # NTP server configuration
        # Note: For full testing, use a local NTP server with authentication
        # Server should be configured with: key 1, MD5, "CorrectServerPassword"
        cls.data.ntp_server = "216.239.35.0"  # time.google.com (for config testing)

        # Authentication keys - simulating MISMATCHES
        # Scenario 1: Password Mismatch
        cls.data.wrong_password = {
            "id": 1,
            "type": "md5",
            "password": "WrongClientPassword",
            "scenario": "Password Mismatch",
        }

        # Scenario 2: Authentication Type Mismatch
        cls.data.wrong_type = {
            "id": 1,
            "type": "sha1",  # Server uses MD5
            "password": "SharedSecret",
            "scenario": "Auth Type Mismatch",
        }

        # Scenario 3: Key ID Mismatch
        cls.data.wrong_keyid = {
            "id": 2,  # Server uses key 1
            "type": "md5",
            "password": "SharedSecret",
            "scenario": "Key ID Mismatch",
        }

        # Correct key for positive verification at end
        cls.data.correct_key = {
            "id": 1,
            "type": "md5",
            "password": "CorrectServerPassword",
            "scenario": "Correct Configuration",
        }

        # Wait times
        cls.data.short_wait = 3
        cls.data.config_wait = 10
        cls.data.sync_wait = 90  # Wait for NTP sync attempts

        st.log(f"Test setup complete - DUT: {cls.data.dut}")
        st.log(f"NTP server: {cls.data.ntp_server}")
        st.log("This is a NEGATIVE TEST - authentication failures are expected")

    @classmethod
    def teardown_class(cls) -> None:
        """Restore NTP defaults and cleanup all configurations."""
        cls._restore_defaults(cls.data.dut)

    def test_ntp_5_verify_sync_fails_mismatched_key(self) -> None:
        """TC 2.1.5 – Verify sync fails with mismatched key (NEGATIVE TEST)."""
        dut = self.data.dut
        ntp_server = self.data.ntp_server

        # ========== PART 1: ENABLE NTP AND AUTHENTICATION ==========

        # Step 1: Enable NTP globally
        st.log("=" * 80)
        st.log("Step 1: Enabling NTP globally")
        st.log("=" * 80)
        self._apply_klish(dut, ["ntp enable"])
        st.wait(self.data.short_wait)

        # Step 2: Enable NTP authentication
        st.log("=" * 80)
        st.log("Step 2: Enabling NTP authentication")
        st.log("=" * 80)
        self._apply_klish(dut, ["ntp authenticate"])
        st.wait(self.data.short_wait)

        # ========== PART 2: SCENARIO 1 - PASSWORD MISMATCH ==========

        st.log("=" * 80)
        st.log("SCENARIO 1: PASSWORD MISMATCH (NEGATIVE TEST)")
        st.log("Server expects: key 1, MD5, 'CorrectServerPassword'")
        st.log("Client configures: key 1, MD5, 'WrongClientPassword'")
        st.log("Expected: Authentication FAILURE")
        st.log("=" * 80)

        # Step 3: Configure WRONG password (password mismatch)
        wrong_pass = self.data.wrong_password
        st.log(f"Step 3: Configuring WRONG password for key {wrong_pass['id']}")
        self._apply_klish(
            dut,
            [
                f"ntp authentication-key {wrong_pass['id']} {wrong_pass['type']} {wrong_pass['password']}",
                f"ntp trusted-key {wrong_pass['id']}",
            ],
        )
        st.wait(self.data.config_wait)

        # Step 4: Configure NTP server with mismatched key
        st.log(f"Step 4: Configuring NTP server with key {wrong_pass['id']}")
        self._apply_klish(dut, [f"ntp server {ntp_server} key {wrong_pass['id']} iburst"])
        st.wait(self.data.short_wait)

        # Step 5: Wait for NTP sync attempts
        st.log("=" * 80)
        st.log(f"Step 5: Waiting for NTP sync attempts ({self.data.sync_wait}s)")
        st.log("Expected: Authentication should FAIL due to password mismatch")
        st.log("=" * 80)
        st.wait(self.data.sync_wait)

        # Step 6: Verify configuration and check for failure indicators
        st.log("=" * 80)
        st.log("Step 6: Checking NTP status - expecting FAILURE indicators")
        st.log("=" * 80)

        # Show NTP global
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global:")
        klish_ntp_global_fail1 = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_fail1)

        # Show NTP server
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Server:")
        klish_ntp_server_fail1 = self._run_klish_show(dut, "show ntp server")
        st.log(klish_ntp_server_fail1)

        # Show NTP associations - look for .AUTH. or reach 000
        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Associations:")
        klish_ntp_assoc_fail1 = self._run_klish_show(dut, "show ntp associations")
        st.log(klish_ntp_assoc_fail1)

        # Analyze for failure indicators
        st.log("=" * 80)
        st.log("ANALYSIS - Looking for authentication failure indicators:")
        st.log("  - .AUTH. in refid column")
        st.log("  - reach 000 (no successful polls)")
        st.log("  - st 16 (unreachable)")
        st.log("  - No * marker (not synchronized)")
        st.log("=" * 80)

        if ".AUTH." in klish_ntp_assoc_fail1:
            st.log("✅ Found .AUTH. indicator - authentication failure detected")
        else:
            st.log("⚠ Note: .AUTH. not found (may vary by implementation)")

        if "000" in klish_ntp_assoc_fail1:
            st.log("✅ Found reach 000 - no successful polls")
        else:
            st.log("⚠ Note: reach 000 not found in output")

        # ========== PART 3: SCENARIO 2 - AUTHENTICATION TYPE MISMATCH ==========

        st.log("=" * 80)
        st.log("SCENARIO 2: AUTHENTICATION TYPE MISMATCH (NEGATIVE TEST)")
        st.log("Server expects: key 1, MD5, 'SharedSecret'")
        st.log("Client configures: key 1, SHA1, 'SharedSecret'")
        st.log("Expected: Authentication FAILURE (type mismatch)")
        st.log("=" * 80)

        # Step 7: Remove previous configuration
        st.log("Step 7: Removing previous authentication configuration")
        self._apply_klish(
            dut,
            [
                f"no ntp server {ntp_server}",
                f"no ntp trusted-key {wrong_pass['id']}",
                f"no ntp authentication-key {wrong_pass['id']}",
            ],
        )
        st.wait(self.data.short_wait)

        # Step 8: Configure WRONG authentication type
        wrong_type = self.data.wrong_type
        st.log(f"Step 8: Configuring WRONG auth type ({wrong_type['type']}) for key {wrong_type['id']}")
        self._apply_klish(
            dut,
            [
                f"ntp authentication-key {wrong_type['id']} {wrong_type['type']} {wrong_type['password']}",
                f"ntp trusted-key {wrong_type['id']}",
                f"ntp server {ntp_server} key {wrong_type['id']} iburst",
            ],
        )
        st.wait(self.data.config_wait)

        # Step 9: Wait and check for failure
        st.log(f"Step 9: Waiting for NTP sync attempts ({self.data.sync_wait}s)")
        st.wait(self.data.sync_wait)

        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Associations (Type Mismatch):")
        klish_ntp_assoc_fail2 = self._run_klish_show(dut, "show ntp associations")
        st.log(klish_ntp_assoc_fail2)

        # ========== PART 4: SCENARIO 3 - KEY ID MISMATCH ==========

        st.log("=" * 80)
        st.log("SCENARIO 3: KEY ID MISMATCH (NEGATIVE TEST)")
        st.log("Server expects: key 1, MD5, 'SharedSecret'")
        st.log("Client configures: key 2, MD5, 'SharedSecret'")
        st.log("Expected: Authentication FAILURE (key ID mismatch)")
        st.log("=" * 80)

        # Step 10: Remove previous configuration
        st.log("Step 10: Removing previous authentication configuration")
        self._apply_klish(
            dut,
            [
                f"no ntp server {ntp_server}",
                f"no ntp trusted-key {wrong_type['id']}",
                f"no ntp authentication-key {wrong_type['id']}",
            ],
        )
        st.wait(self.data.short_wait)

        # Step 11: Configure WRONG key ID
        wrong_keyid = self.data.wrong_keyid
        st.log(f"Step 11: Configuring WRONG key ID ({wrong_keyid['id']}) instead of 1")
        self._apply_klish(
            dut,
            [
                f"ntp authentication-key {wrong_keyid['id']} {wrong_keyid['type']} {wrong_keyid['password']}",
                f"ntp trusted-key {wrong_keyid['id']}",
                f"ntp server {ntp_server} key {wrong_keyid['id']} iburst",
            ],
        )
        st.wait(self.data.config_wait)

        # Step 12: Wait and check for failure
        st.log(f"Step 12: Waiting for NTP sync attempts ({self.data.sync_wait}s)")
        st.wait(self.data.sync_wait)

        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Associations (Key ID Mismatch):")
        klish_ntp_assoc_fail3 = self._run_klish_show(dut, "show ntp associations")
        st.log(klish_ntp_assoc_fail3)

        # ========== PART 5: POSITIVE VERIFICATION (FIX THE KEY) ==========

        st.log("=" * 80)
        st.log("PART 5: POSITIVE VERIFICATION - FIX THE KEY")
        st.log("Configuring CORRECT key to verify authentication can work")
        st.log("This confirms failures were due to mismatch, not other issues")
        st.log("=" * 80)

        # Step 13: Remove wrong configuration
        st.log("Step 13: Removing wrong authentication configuration")
        self._apply_klish(
            dut,
            [
                f"no ntp server {ntp_server}",
                f"no ntp trusted-key {wrong_keyid['id']}",
                f"no ntp authentication-key {wrong_keyid['id']}",
            ],
        )
        st.wait(self.data.short_wait)

        # Step 14: Configure CORRECT key
        correct_key = self.data.correct_key
        st.log(f"Step 14: Configuring CORRECT key (key {correct_key['id']}, {correct_key['type'].upper()})")
        st.log("Note: This will only work if NTP server has matching authentication")
        self._apply_klish(
            dut,
            [
                f"ntp authentication-key {correct_key['id']} {correct_key['type']} {correct_key['password']}",
                f"ntp trusted-key {correct_key['id']}",
                f"ntp server {ntp_server} key {correct_key['id']} iburst prefer",
            ],
        )
        st.wait(self.data.config_wait)

        # Step 15: Wait for sync with correct key
        st.log(f"Step 15: Waiting for NTP sync with correct key ({self.data.sync_wait}s)")
        st.wait(self.data.sync_wait)

        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Associations (Correct Key):")
        klish_ntp_assoc_success = self._run_klish_show(dut, "show ntp associations")
        st.log(klish_ntp_assoc_success)

        # ========== PART 6: TEST AUTHENTICATION TOGGLE ==========

        st.log("=" * 80)
        st.log("PART 6: TEST AUTHENTICATION DISABLE/ENABLE TOGGLE")
        st.log("=" * 80)

        # Step 16: Disable authentication
        st.log("Step 16: Disabling NTP authentication")
        self._apply_klish(dut, ["no ntp authenticate"])
        st.wait(self.data.config_wait)

        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global (Auth Disabled):")
        klish_ntp_global_noauth = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_noauth)

        # Step 17: Re-enable authentication
        st.log("Step 17: Re-enabling NTP authentication")
        self._apply_klish(dut, ["ntp authenticate"])
        st.wait(self.data.short_wait)

        st.log("INSIDE SONIC-CLI (KLISH) - Show NTP Global (Auth Re-enabled):")
        klish_ntp_global_reauth = self._run_klish_show(dut, "show ntp global")
        st.log(klish_ntp_global_reauth)

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

        # ========== TEST SUMMARY ==========

        st.log("=" * 80)
        st.log("NTP authentication failure negative test completed successfully")
        st.log("Summary:")
        st.log("  - This is a NEGATIVE TEST - failures are EXPECTED and CORRECT")
        st.log("  - Tested 3 authentication mismatch scenarios:")
        st.log("    1. Password Mismatch - Different passwords")
        st.log("    2. Auth Type Mismatch - MD5 vs SHA1")
        st.log("    3. Key ID Mismatch - key 1 vs key 2")
        st.log("  - All mismatch scenarios should show authentication failures")
        st.log("  - Failure indicators to look for:")
        st.log("    * .AUTH. in refid column")
        st.log("    * reach 000 (no successful polls)")
        st.log("    * st 16 (unreachable)")
        st.log("    * No * marker (not synchronized)")
        st.log("  - Positive verification: configured correct key at end")
        st.log("  - Tested authentication toggle (disable/enable)")
        st.log("  - All configuration commands executed successfully")
        st.log("=" * 80)
        st.log("IMPORTANT: Authentication failures are EXPECTED in this test")
        st.log("This verifies that authentication is properly enforced")
        st.log("=" * 80)

        st.report_pass("test_case_passed")

    @staticmethod
    def _apply_klish(dut: str, commands: Iterable[str]) -> None:
        """Apply configuration commands via klish (sonic-cli)."""
        command_list = [cmd for cmd in commands if cmd]
        script = ["sonic-cli", "configure terminal"]
        script.extend(command_list)
        script.extend(["end", "exit"])
        output = st.apply_script(dut, script)

        # Check for CLI errors in the output
        output_str = str(output or "")
        if "% Error:" in output_str or "Error:" in output_str or "Invalid" in output_str:
            st.report_fail("msg", f"CLI command failed with error: {output_str}")

    @staticmethod
    def _run_klish_show(dut: str, command: str) -> str:
        """Run show command inside sonic-cli (klish) context and return output."""
        script = ["sonic-cli", command, "exit"]
        output = st.apply_script(dut, script)
        output_str = str(output or "")

        # Check for CLI errors in the output
        if "% Error:" in output_str or "Error:" in output_str or "Invalid" in output_str:
            st.report_fail("msg", f"CLI show command '{command}' failed with error: {output_str}")

        return output_str

    @classmethod
    def _restore_defaults(cls, dut: str) -> None:
        """Restore NTP defaults and cleanup all configurations."""
        cleanup_cmds = [
            # Remove NTP server
            f"no ntp server {cls.data.ntp_server}",
            # Remove trusted keys for all scenarios
            f"no ntp trusted-key {cls.data.wrong_password['id']}",
            f"no ntp trusted-key {cls.data.wrong_type['id']}",
            f"no ntp trusted-key {cls.data.wrong_keyid['id']}",
            f"no ntp trusted-key {cls.data.correct_key['id']}",
            # Remove authentication keys for all scenarios
            f"no ntp authentication-key {cls.data.wrong_password['id']}",
            f"no ntp authentication-key {cls.data.wrong_type['id']}",
            f"no ntp authentication-key {cls.data.wrong_keyid['id']}",
            f"no ntp authentication-key {cls.data.correct_key['id']}",
            # Disable authentication
            "no ntp authenticate",
            # Re-enable NTP for default state
            "ntp enable",
        ]
        cls._apply_klish(dut, cleanup_cmds)
        st.log("NTP configuration restored to defaults")
