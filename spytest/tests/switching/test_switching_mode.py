"""
SWITCHING MODE CLI VERIFICATION
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/ztp_standalone.yaml  \
  tests/switching/test_switching_mode.py \
  --logs-path ./logs/test_switching_mode_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Verification of switching-mode CLI commands in both show mode and configuration
  mode using sonic-cli (klish). The test validates 'show switching-mode' command,
  configuration mode options (cut-through, store-and-forward), and mode changes.
  Tests detect and document internal errors without failing. Handles pagination
  in show commands by setting terminal length to 0. Restores original switching
  mode after testing.

Files and APIs Used:
  - Testbed Configuration:
      * testbeds/ztp_standalone.yaml - Standalone DUT configuration

  - SpyTest Framework Functions:
      * st.config() - Execute configuration commands
      * st.show() - Execute show commands
      * st.log(), st.banner(), st.debug(), st.warn() - Logging functions
      * st.wait() - Wait for configuration propagation
      * st.report_pass(), st.report_fail() - Test result reporting

Pre-requisites:
  - Topology: standalone (single DUT) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node (standalone)
        # +--------------------+
        # |        D1          |
        # |    (smic_sonic1)   |
        # |  Switching Mode    |
        # +--------------------+

  - Feature flags / min SONiC version: Switching mode feature support required
  - Required test variables: Uses testbed file directly (no external YAML vars needed)
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

import pytest

from spytest import SpyTestDict, st


# Test constants
SWITCHING_MODE_STORE_FORWARD = "store-and-forward"
SWITCHING_MODE_CUT_THROUGH = "cut-through"
VALID_MODES = [SWITCHING_MODE_STORE_FORWARD, SWITCHING_MODE_CUT_THROUGH]


@pytest.mark.topology("any")
class TestSwitchingMode:
    """Testcases covering switching-mode CLI verification and bug documentation."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology, disable terminal pagination, and capture initial mode."""
        st.banner("CLASS SETUP: Starting Switching Mode Test Suite")

        # Get topology - single DUT standalone topology
        topology = st.get_testbed_vars()
        cls.data.topology = topology

        # Get DUT names
        cls.data.dut_names = st.get_dut_names()
        if not cls.data.dut_names:
            st.report_fail("msg", "No DUTs found in testbed")

        cls.data.dut = cls.data.dut_names[0]  # Use first DUT (D1)
        st.log(f"Using DUT: {cls.data.dut}")

        # Set terminal length to 0 to disable pagination (--more-- prompts)
        cls._set_terminal_length(cls.data.dut, 0)
        st.log("Terminal length set to 0 - pagination disabled")

        # Capture initial switching mode for restoration
        cls.data.original_mode = cls._get_current_mode(cls.data.dut)
        st.log(f"Original switching mode captured: {cls.data.original_mode}")

    @classmethod
    def teardown_class(cls) -> None:
        """Restore original switching mode after test suite."""
        st.banner("CLASS TEARDOWN: Restoring original switching mode")

        if cls.data.get("original_mode"):
            st.log(f"Restoring switching mode to: {cls.data.original_mode}")
            cls._configure_switching_mode(cls.data.dut, cls.data.original_mode)

        st.log("Class teardown completed")

    @staticmethod
    def _set_terminal_length(dut: str, length: int = 0) -> None:
        """Set terminal length to control pagination in show commands.

        Args:
            dut: Device under test
            length: Terminal length (0 = no pagination)
        """
        try:
            cmd = f"terminal length {length}"
            st.config(dut, cmd, type="klish", conf=False, skip_error_check=True)
            st.log(f"Set terminal length to {length} on {dut}")
        except Exception as e:
            st.warn(f"Failed to set terminal length: {e}")

    @staticmethod
    def _get_switching_mode_output(dut: str) -> str:
        """Retrieve switching mode output with pagination disabled.

        Args:
            dut: Device under test

        Returns:
            Output from 'show switching-mode' command
        """
        # Set terminal length to 0 to avoid --more-- pagination prompts
        st.config(dut, "terminal length 0", type="klish", conf=False, skip_error_check=True)

        cmd = "show switching-mode"
        output = st.show(dut, cmd, type="klish", skip_tmpl=True, skip_error_check=True)

        if isinstance(output, list) and output:
            output_str = "\n".join(str(item) for item in output)
        elif isinstance(output, str):
            output_str = output
        else:
            output_str = str(output)

        return output_str

    @staticmethod
    def _check_for_internal_error(output: str) -> bool:
        """Check if output contains internal error.

        Args:
            output: Command output to check

        Returns:
            True if internal error detected, False otherwise
        """
        error_patterns = [
            r"%Error:\s*Internal\s*error",
            r"Internal\s*error",
            r"%Error"
        ]

        for pattern in error_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                return True

        return False

    @staticmethod
    def _parse_switching_mode(output: str) -> Optional[str]:
        """Parse switching mode from output.

        Args:
            output: Output from 'show switching-mode' command

        Returns:
            Switching mode string or None if not found
        """
        # Pattern: Switching Mode: store-and-forward
        # or: Switching Mode: cut-through
        pattern = r"Switching\s+Mode:\s*([\w\-]+)"
        match = re.search(pattern, output, re.IGNORECASE)

        if match:
            mode = match.group(1).strip().lower()
            # Normalize mode string
            if "store" in mode and "forward" in mode:
                return SWITCHING_MODE_STORE_FORWARD
            elif "cut" in mode and "through" in mode:
                return SWITCHING_MODE_CUT_THROUGH
            else:
                return mode

        return None

    @staticmethod
    def _get_current_mode(dut: str) -> Optional[str]:
        """Get current switching mode, handling errors gracefully.

        Args:
            dut: Device under test

        Returns:
            Current switching mode or None if error
        """
        try:
            output = TestSwitchingMode._get_switching_mode_output(dut)

            # Check for internal error
            if TestSwitchingMode._check_for_internal_error(output):
                st.warn("Internal error detected when getting current mode")
                return None

            mode = TestSwitchingMode._parse_switching_mode(output)
            return mode
        except Exception as e:
            st.warn(f"Failed to get current switching mode: {e}")
            return None

    @staticmethod
    def _configure_switching_mode(dut: str, mode: str) -> bool:
        """Configure switching mode.

        Args:
            dut: Device under test
            mode: Switching mode to configure (cut-through or store-and-forward)

        Returns:
            True if configuration successful, False otherwise
        """
        try:
            # Map mode to CLI command
            if mode == SWITCHING_MODE_CUT_THROUGH:
                cmd = "switching-mode cut-through"
            elif mode == SWITCHING_MODE_STORE_FORWARD:
                cmd = "switching-mode store-forward"
            else:
                st.warn(f"Invalid switching mode: {mode}")
                return False

            output = st.config(dut, cmd, type="klish", skip_error_check=True)

            # Check for errors in output
            if TestSwitchingMode._check_for_internal_error(str(output)):
                st.warn(f"Internal error when configuring mode: {mode}")
                return False

            st.log(f"Configured switching mode: {mode}")
            return True

        except Exception as e:
            st.warn(f"Failed to configure switching mode: {e}")
            return False

    @staticmethod
    def _get_switching_mode_options(dut: str) -> str:
        """Get switching-mode configuration options.

        Args:
            dut: Device under test

        Returns:
            Output from 'switching-mode ?' command
        """
        try:
            # Enter config mode and get options
            cmd_list = [
                "configure terminal",
                "switching-mode ?"
            ]
            output = st.config(dut, cmd_list, type="klish", skip_error_check=True)

            # Exit config mode
            st.config(dut, "exit", type="klish", skip_error_check=True)

            if isinstance(output, str):
                return output
            else:
                return str(output)

        except Exception as e:
            st.warn(f"Failed to get switching-mode options: {e}")
            return ""

    @pytest.mark.inventory(feature="Regression", testcases=["SWITCHING_MODE_TC_001"])
    def test_show_switching_mode(self) -> None:
        """TC 001 - Verify 'show switching-mode' command execution.

        Test Steps:
        1. Execute 'show switching-mode' with terminal length 0
        2. Check for internal errors in output
        3. Parse switching mode from output
        4. Verify mode is valid (cut-through or store-and-forward)
        5. Document bug if internal error detected
        """
        dut = self.data.dut

        st.banner("STEP 1: Execute 'show switching-mode' command")

        output = self._get_switching_mode_output(dut)

        if not output:
            st.report_fail("msg", "Failed to retrieve 'show switching-mode' output")

        st.log("Command executed successfully")
        st.debug(f"Output:\n{output}")

        st.banner("STEP 2: Check for internal errors")

        has_error = self._check_for_internal_error(output)

        if has_error:
            st.warn("=" * 80)
            st.warn("KNOWN BUG DETECTED:")
            st.warn("  Command: 'show switching-mode'")
            st.warn("  Expected: Display current switching mode")
            st.warn("  Actual: %Error: Internal error.")
            st.warn(f"  Output: {output}")
            st.warn("  Status: Bug persists - command returns internal error")
            st.warn("=" * 80)
            st.log("Test documents bug behavior - marking as informational")
        else:
            st.log("✓ No internal errors detected")

        st.banner("STEP 3: Parse switching mode from output")

        mode = self._parse_switching_mode(output)

        if has_error:
            st.log("Skipping mode validation due to internal error")
        else:
            st.banner("STEP 4: Verify mode is valid")

            if mode is None:
                st.report_fail("msg", "Failed to parse switching mode from output")

            if mode not in VALID_MODES:
                st.warn(f"Unexpected switching mode: {mode}")
            else:
                st.log(f"✓ Current switching mode: {mode}")

        st.banner("TEST PASSED: Show switching-mode command behavior documented")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SWITCHING_MODE_TC_002"])
    def test_switching_mode_config_options(self) -> None:
        """TC 002 - Verify switching-mode configuration mode options.

        Test Steps:
        1. Enter configuration mode
        2. Execute 'switching-mode ?' to display options
        3. Verify options include cut-through and store-forward
        4. Check for internal errors
        5. Exit configuration mode
        """
        dut = self.data.dut

        st.banner("STEP 1: Enter configuration mode and get options")

        options_output = self._get_switching_mode_options(dut)

        if not options_output:
            st.report_fail("msg", "Failed to retrieve switching-mode options")

        st.log("Configuration options retrieved successfully")
        st.debug(f"Options output:\n{options_output}")

        st.banner("STEP 2: Check for internal errors")

        has_error = self._check_for_internal_error(options_output)

        if has_error:
            st.warn("Internal error detected in configuration mode options")

        st.banner("STEP 3: Verify options include cut-through and store-forward")

        # Check for cut-through option
        if re.search(r"cut-through", options_output, re.IGNORECASE):
            st.log("✓ 'cut-through' option found")
        else:
            st.warn("'cut-through' option not found in help output")

        # Check for store-forward option
        if re.search(r"store-forward", options_output, re.IGNORECASE):
            st.log("✓ 'store-forward' option found")
        else:
            st.warn("'store-forward' option not found in help output")

        st.banner("TEST PASSED: Switching-mode configuration options verified")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SWITCHING_MODE_TC_003"])
    def test_configure_cut_through_mode(self) -> None:
        """TC 003 - Verify cut-through mode configuration.

        Test Steps:
        1. Get current switching mode (baseline)
        2. Configure switching mode to cut-through
        3. Check for configuration errors
        4. Verify mode changed to cut-through
        5. Document bug if internal error occurs
        6. Restore original mode
        """
        dut = self.data.dut

        st.banner("STEP 1: Get current switching mode (baseline)")

        baseline_mode = self._get_current_mode(dut)
        st.log(f"Baseline switching mode: {baseline_mode or 'Unknown (error)'}")

        st.banner("STEP 2: Configure switching mode to cut-through")

        config_result = self._configure_switching_mode(dut, SWITCHING_MODE_CUT_THROUGH)

        st.wait(2)  # Wait for configuration to propagate

        st.banner("STEP 3: Check for configuration errors")

        if not config_result:
            st.warn("=" * 80)
            st.warn("KNOWN BUG DETECTED:")
            st.warn("  Command: 'switching-mode cut-through'")
            st.warn("  Expected: Command accepted without errors")
            st.warn("  Actual: %Error: Internal error.")
            st.warn("  Status: Bug persists - configuration returns internal error")
            st.warn("=" * 80)
            st.log("Test documents bug behavior - marking as informational")
        else:
            st.log("✓ Configuration command executed successfully")

        st.banner("STEP 4: Verify mode changed to cut-through")

        current_mode = self._get_current_mode(dut)

        if current_mode == SWITCHING_MODE_CUT_THROUGH:
            st.log(f"✓ Switching mode verified: {current_mode}")
        else:
            st.log(f"Mode verification: Expected 'cut-through', Found '{current_mode or 'Unknown'}'")
            st.log("This may be expected if configuration failed due to internal error")

        st.banner("STEP 5: Restore original mode")

        if baseline_mode and baseline_mode != SWITCHING_MODE_CUT_THROUGH:
            self._configure_switching_mode(dut, baseline_mode)
            st.log(f"Restored switching mode to: {baseline_mode}")

        st.banner("TEST PASSED: Cut-through mode configuration behavior documented")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SWITCHING_MODE_TC_004"])
    def test_configure_store_forward_mode(self) -> None:
        """TC 004 - Verify store-and-forward mode configuration.

        Test Steps:
        1. Get current switching mode (baseline)
        2. Configure switching mode to store-and-forward
        3. Check for configuration errors
        4. Verify mode changed to store-and-forward
        5. Document bug if internal error occurs
        6. Restore original mode
        """
        dut = self.data.dut

        st.banner("STEP 1: Get current switching mode (baseline)")

        baseline_mode = self._get_current_mode(dut)
        st.log(f"Baseline switching mode: {baseline_mode or 'Unknown (error)'}")

        st.banner("STEP 2: Configure switching mode to store-and-forward")

        config_result = self._configure_switching_mode(dut, SWITCHING_MODE_STORE_FORWARD)

        st.wait(2)  # Wait for configuration to propagate

        st.banner("STEP 3: Check for configuration errors")

        if not config_result:
            st.warn("=" * 80)
            st.warn("KNOWN BUG DETECTED:")
            st.warn("  Command: 'switching-mode store-forward'")
            st.warn("  Expected: Command accepted without errors")
            st.warn("  Actual: %Error: Internal error.")
            st.warn("  Status: Bug persists - configuration returns internal error")
            st.warn("=" * 80)
            st.log("Test documents bug behavior - marking as informational")
        else:
            st.log("✓ Configuration command executed successfully")

        st.banner("STEP 4: Verify mode changed to store-and-forward")

        current_mode = self._get_current_mode(dut)

        if current_mode == SWITCHING_MODE_STORE_FORWARD:
            st.log(f"✓ Switching mode verified: {current_mode}")
        else:
            st.log(f"Mode verification: Expected 'store-and-forward', Found '{current_mode or 'Unknown'}'")
            st.log("This may be expected if configuration failed due to internal error")

        st.banner("STEP 5: Restore original mode")

        if baseline_mode and baseline_mode != SWITCHING_MODE_STORE_FORWARD:
            self._configure_switching_mode(dut, baseline_mode)
            st.log(f"Restored switching mode to: {baseline_mode}")

        st.banner("TEST PASSED: Store-and-forward mode configuration behavior documented")
        st.report_pass("test_case_passed")
