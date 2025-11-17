"""
NTP CLOCK DRIFT DETECTION AND CORRECTION
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_2vs.yaml  \
  tests/system/ntp/test_ntp_7_verify_ntp_detects_corrects_clock_drift.py \
  --logs-path ./logs/test_ntp_7_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  This test validates NTP's core functionality of detecting and automatically
  correcting clock drift when the system clock is manually skewed. The suite
  applies forward and backward clock drifts (±5 minutes), then monitors NTP's
  automatic correction process over time. Each test verifies that NTP detects
  the large offset, gradually corrects the clock back to accurate time without
  manual intervention, and maintains synchronization throughout the correction
  process. All configuration is done via klish (sonic-cli) and validates NTP's
  slewing mechanism for drift correction.

Pre-requisites:
  - Topology: D1 (single DUT) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 DUT + NTP Server
        # +--------------------+                   +------------------+
        # |        dut1        |                   |   NTP Server     |
        # | (time client)      |<===============>  |  (time source)   |
        # +--------------------+                   +------------------+

  - Reachable NTP server providing accurate time
  - Root/admin access to manually change system clock
  - Test duration: 30-60 minutes per test (to observe full drift correction)
  - Note: This test is time-intensive due to monitoring requirements
"""

from __future__ import annotations

import re
import time
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Dict, List

import pytest

from spytest import SpyTestDict, st


@pytest.mark.topology("D1")
class TestNtpClockDriftCorrection:
    """
    Test suite for NTP clock drift detection and automatic correction.

    This suite validates that NTP can detect manual clock changes and
    automatically correct the system time back to accurate time from
    the NTP server without any manual intervention.
    """

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """
        Setup: Ensure minimum topology, configure NTP, and wait for initial sync.

        This method:
        1. Verifies minimum topology (D1)
        2. Configures NTP server with iburst for faster initial sync
        3. Enables NTP
        4. Waits for initial synchronization (up to 10 minutes)
        5. Records baseline time and NTP status
        """
        topology = st.ensure_min_topology("D1")
        cls.data.dut = topology.D1

        # NTP server configuration (using Google public NTP server)
        cls.data.ntp_server = "216.239.35.0"

        # Wait times (in seconds)
        cls.data.wait_short = 3
        cls.data.wait_config = 10
        cls.data.wait_initial_sync = 600  # 10 minutes for initial synchronization
        cls.data.wait_drift_settle = 120  # 2 minutes after applying drift
        cls.data.wait_monitor_interval = 120  # 2 minutes between monitoring checks
        cls.data.wait_full_correction = 1800  # 30 minutes for full correction

        # Drift parameters
        cls.data.drift_forward_minutes = 5  # +5 minutes
        cls.data.drift_backward_minutes = 5  # -5 minutes
        cls.data.drift_forward_seconds = cls.data.drift_forward_minutes * 60  # 300s
        cls.data.drift_backward_seconds = cls.data.drift_backward_minutes * 60  # 300s

        # Correction thresholds
        cls.data.offset_threshold_large = 250  # Large offset (> 250 seconds indicates drift)
        cls.data.offset_threshold_corrected = 5  # Corrected offset (< 5 seconds)
        cls.data.offset_threshold_final = 1  # Final offset (< 1 second)

        # Monitoring parameters
        cls.data.monitor_iterations = 15  # Monitor for 15 iterations
        cls.data.correction_progress_threshold = 0.5  # Expect at least 50% reduction

        st.log("=" * 80)
        st.log("Starting NTP Clock Drift Test Suite Setup")
        st.log("=" * 80)

        dut = cls.data.dut

        # Configure NTP server and enable NTP using klish
        st.log(f"Step 1: Configuring NTP server {cls.data.ntp_server} with iburst")
        cls._apply_klish(
            dut,
            [
                f"ntp server {cls.data.ntp_server} iburst",
                "ntp enable",
            ],
        )
        st.wait(cls.data.wait_config)

        # Wait for initial synchronization
        st.log(f"Step 2: Waiting {cls.data.wait_initial_sync}s for initial NTP synchronization...")
        st.wait(cls.data.wait_initial_sync)

        # Verify initial synchronization
        st.log("Step 3: Verifying initial NTP synchronization")
        sync_achieved = cls._verify_initial_sync(dut)

        if not sync_achieved:
            st.warn(
                "Initial NTP synchronization not fully achieved within timeout. "
                "Proceeding with tests, but drift correction may take longer."
            )
        else:
            st.log("Initial NTP synchronization successful")

        # Record baseline
        st.log("Step 4: Recording baseline time and NTP status")
        baseline_data = cls._record_baseline(dut)
        cls.data.baseline = baseline_data
        st.log(f"Baseline recorded: {baseline_data}")

        st.log("=" * 80)
        st.log("NTP Clock Drift Test Suite Setup Complete")
        st.log("=" * 80)

    @classmethod
    def teardown_class(cls) -> None:
        """
        Teardown: Remove NTP configuration and restore system to clean state.

        This method:
        1. Disables NTP
        2. Removes NTP server configuration
        3. Logs final NTP status
        """
        st.log("=" * 80)
        st.log("Starting NTP Clock Drift Test Suite Teardown")
        st.log("=" * 80)

        dut = cls.data.dut

        # Show final NTP status
        st.log("Final NTP Status:")
        final_klish_global = cls._run_klish_show(dut, "show ntp global")
        st.log(final_klish_global)

        final_klish_associations = cls._run_klish_show(dut, "show ntp associations")
        st.log(final_klish_associations)

        # Remove NTP configuration
        st.log("Removing NTP configuration")
        cls._apply_klish(
            dut,
            [
                "no ntp enable",
                f"no ntp server {cls.data.ntp_server}",
            ],
        )
        st.wait(cls.data.wait_config)

        st.log("=" * 80)
        st.log("NTP Clock Drift Test Suite Teardown Complete")
        st.log("=" * 80)

    @staticmethod
    def _apply_klish(dut: str, commands: Iterable[str]) -> None:
        """
        Apply klish configuration commands via sonic-cli.

        Args:
            dut: Device under test
            commands: Iterable of klish commands to execute
        """
        command_list = [cmd for cmd in commands if cmd]
        if not command_list:
            return

        script = ["sonic-cli", "configure terminal"]
        script.extend(command_list)
        script.extend(["end", "exit"])

        st.apply_script(dut, script)

    @staticmethod
    def _run_klish_show(dut: str, command: str) -> str:
        """
        Execute a klish show command and return output as string.

        Args:
            dut: Device under test
            command: Show command to execute (e.g., "show ntp global")

        Returns:
            Command output as string
        """
        script = ["sonic-cli", command, "exit"]
        output = st.apply_script(dut, script)
        return str(output or "")

    @classmethod
    def _verify_initial_sync(cls, dut: str) -> bool:
        """
        Verify that NTP has achieved initial synchronization.

        Args:
            dut: Device under test

        Returns:
            True if synchronized, False otherwise
        """
        # Check klish show ntp associations
        klish_associations = cls._run_klish_show(dut, "show ntp associations")
        st.log("NTP Associations (klish):")
        st.log(klish_associations)

        # Check click show ntp
        click_ntp = st.show(dut, "show ntp", skip_tmpl=True, skip_error_check=True)
        if isinstance(click_ntp, list):
            click_ntp_str = "\n".join(str(line) for line in click_ntp)
        else:
            click_ntp_str = str(click_ntp)
        st.log("NTP Status (click):")
        st.log(click_ntp_str)

        # Look for synchronization indicators
        # - '*' marker in associations
        # - 'synchronised' in status
        # - reach value of 377 (all polls successful)

        is_synced = False

        # Check for synchronization markers
        if "*" in klish_associations or "synchronised" in click_ntp_str.lower():
            is_synced = True
        elif "reach" in klish_associations.lower():
            # Check reach value - 377 (octal) = all 8 polls successful
            reach_match = re.search(r"reach\s+(\d+)", klish_associations, re.IGNORECASE)
            if reach_match:
                reach_value = int(reach_match.group(1), 8 if reach_match.group(1).startswith("0") else 10)
                # Accept reach > 0 as initial sync indicator
                if reach_value > 0:
                    is_synced = True

        return is_synced

    @classmethod
    def _record_baseline(cls, dut: str) -> Dict[str, Any]:
        """
        Record baseline time and NTP status before applying drift.

        Args:
            dut: Device under test

        Returns:
            Dictionary containing baseline data
        """
        baseline = {}

        # Record system time
        clock_output = st.show(dut, "show clock", skip_tmpl=True, skip_error_check=True)
        if isinstance(clock_output, list):
            clock_str = "\n".join(str(line) for line in clock_output)
        else:
            clock_str = str(clock_output)
        baseline["system_time"] = clock_str.strip()
        baseline["timestamp"] = time.time()

        # Record NTP associations
        associations = cls._run_klish_show(dut, "show ntp associations")
        baseline["associations"] = associations

        # Extract baseline offset
        offset = cls._extract_offset_from_associations(associations)
        baseline["offset"] = offset

        return baseline

    @staticmethod
    def _extract_offset_from_associations(associations_output: str) -> float:
        """
        Extract NTP offset value from associations output.

        Args:
            associations_output: Output from 'show ntp associations'

        Returns:
            Offset in seconds (float), or 0.0 if not found
        """
        # Look for offset column in associations output
        # Format: remote refid st t when poll reach delay offset jitter
        # Example: *192.168.1.1 .GPS. 1 u 32 64 377 0.123 0.456 0.789

        lines = associations_output.split("\n")
        for line in lines:
            # Skip header lines
            if "offset" in line.lower() or "===" in line or not line.strip():
                continue

            # Look for lines with server entries
            if re.search(r"\d+\.\d+\.\d+\.\d+", line):
                # Extract offset (typically 9th column)
                parts = line.split()
                if len(parts) >= 9:
                    try:
                        offset = float(parts[8])
                        return offset
                    except (ValueError, IndexError):
                        continue

        return 0.0

    @staticmethod
    def _apply_clock_drift(dut: str, drift_minutes: int) -> Dict[str, Any]:
        """
        Manually skew the system clock by specified minutes.

        Args:
            dut: Device under test
            drift_minutes: Number of minutes to skew (positive = forward, negative = backward)

        Returns:
            Dictionary containing drift application details
        """
        drift_data = {}

        # Record time before drift
        time_before = st.show(dut, "show clock", skip_tmpl=True, skip_error_check=True)
        if isinstance(time_before, list):
            time_before_str = "\n".join(str(line) for line in time_before)
        else:
            time_before_str = str(time_before)
        drift_data["time_before"] = time_before_str.strip()
        drift_data["timestamp_before"] = time.time()

        # Apply drift using date command
        if drift_minutes > 0:
            drift_cmd = f'date -s "+{drift_minutes} minutes"'
            drift_data["direction"] = "forward"
        else:
            drift_cmd = f'date -s "{drift_minutes} minutes"'
            drift_data["direction"] = "backward"

        st.log(f"Applying clock drift: {drift_cmd}")
        drift_result = st.config(dut, drift_cmd, skip_error_check=True)
        st.log(f"Drift command result: {drift_result}")

        # Record time after drift
        time.sleep(2)  # Brief wait for command to take effect
        time_after = st.show(dut, "show clock", skip_tmpl=True, skip_error_check=True)
        if isinstance(time_after, list):
            time_after_str = "\n".join(str(line) for line in time_after)
        else:
            time_after_str = str(time_after)
        drift_data["time_after"] = time_after_str.strip()
        drift_data["timestamp_after"] = time.time()
        drift_data["drift_minutes"] = drift_minutes

        st.log(f"Clock before drift: {drift_data['time_before']}")
        st.log(f"Clock after drift: {drift_data['time_after']}")

        return drift_data

    @classmethod
    def _monitor_drift_correction(
        cls, dut: str, expected_offset_sign: str, iterations: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Monitor NTP drift correction over time.

        Args:
            dut: Device under test
            expected_offset_sign: Expected offset sign ('positive' or 'negative')
            iterations: Number of monitoring iterations (default: 15)

        Returns:
            List of monitoring snapshots, each containing timestamp, offset, and status
        """
        monitoring_data = []

        st.log("=" * 80)
        st.log(f"Starting drift correction monitoring ({iterations} iterations)")
        st.log(f"Monitoring interval: {cls.data.wait_monitor_interval}s")
        st.log(f"Expected offset sign: {expected_offset_sign}")
        st.log("=" * 80)

        for iteration in range(1, iterations + 1):
            st.log(f"\n--- Monitoring Iteration {iteration}/{iterations} ---")

            snapshot = {}
            snapshot["iteration"] = iteration
            snapshot["timestamp"] = time.time()
            snapshot["time_str"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Get NTP associations
            associations = cls._run_klish_show(dut, "show ntp associations")
            snapshot["associations"] = associations
            st.log(f"NTP Associations:\n{associations}")

            # Extract offset
            offset = cls._extract_offset_from_associations(associations)
            snapshot["offset"] = offset
            st.log(f"Extracted Offset: {offset} seconds")

            # Get NTP status (click)
            click_ntp = st.show(dut, "show ntp", skip_tmpl=True, skip_error_check=True)
            if isinstance(click_ntp, list):
                click_ntp_str = "\n".join(str(line) for line in click_ntp)
            else:
                click_ntp_str = str(click_ntp)
            snapshot["ntp_status"] = click_ntp_str
            st.log(f"NTP Status:\n{click_ntp_str}")

            # Get system clock
            clock_output = st.show(dut, "show clock", skip_tmpl=True, skip_error_check=True)
            if isinstance(clock_output, list):
                clock_str = "\n".join(str(line) for line in clock_output)
            else:
                clock_str = str(clock_output)
            snapshot["system_time"] = clock_str.strip()
            st.log(f"System Time: {clock_str.strip()}")

            # Check synchronization status
            is_synced = "*" in associations or "synchronised" in click_ntp_str.lower()
            snapshot["is_synced"] = is_synced
            st.log(f"Synchronized: {is_synced}")

            monitoring_data.append(snapshot)

            # Check if correction is complete
            if abs(offset) < cls.data.offset_threshold_corrected:
                st.log(
                    f"Offset is below correction threshold ({cls.data.offset_threshold_corrected}s). "
                    "Drift correction appears complete."
                )
                # Continue monitoring for a few more iterations to confirm stability
                if iteration >= 3:
                    st.log("Correction confirmed stable. Ending monitoring.")
                    break

            # Wait before next iteration (except on last iteration)
            if iteration < iterations:
                st.log(f"Waiting {cls.data.wait_monitor_interval}s before next check...")
                st.wait(cls.data.wait_monitor_interval)

        st.log("=" * 80)
        st.log("Drift correction monitoring complete")
        st.log("=" * 80)

        return monitoring_data

    @staticmethod
    def _validate_drift_correction(
        monitoring_data: List[Dict[str, Any]],
        expected_offset_sign: str,
        offset_threshold_large: float,
        offset_threshold_corrected: float,
    ) -> bool:
        """
        Validate that drift correction occurred successfully.

        Args:
            monitoring_data: List of monitoring snapshots
            expected_offset_sign: Expected offset sign ('positive' or 'negative')
            offset_threshold_large: Threshold for large offset (seconds)
            offset_threshold_corrected: Threshold for corrected offset (seconds)

        Returns:
            True if drift correction succeeded, False otherwise
        """
        if not monitoring_data:
            st.error("No monitoring data collected")
            return False

        # Get first and last snapshots
        first_snapshot = monitoring_data[0]
        last_snapshot = monitoring_data[-1]

        initial_offset = first_snapshot.get("offset", 0.0)
        final_offset = last_snapshot.get("offset", 0.0)

        st.log("\n" + "=" * 80)
        st.log("DRIFT CORRECTION VALIDATION")
        st.log("=" * 80)
        st.log(f"Initial offset: {initial_offset} seconds")
        st.log(f"Final offset: {final_offset} seconds")
        st.log(f"Expected offset sign: {expected_offset_sign}")
        st.log(f"Large offset threshold: ±{offset_threshold_large} seconds")
        st.log(f"Corrected offset threshold: ±{offset_threshold_corrected} seconds")

        # Validation criteria:
        # 1. Initial offset should be large (indicating drift was detected)
        # 2. Final offset should be small (indicating correction occurred)
        # 3. Offset sign should match expected direction
        # 4. Offset magnitude should decrease over time

        validations = {}

        # Check 1: Initial offset is large
        initial_offset_abs = abs(initial_offset)
        validations["large_initial_offset"] = initial_offset_abs > offset_threshold_large
        st.log(f"Check 1 - Large initial offset (>{offset_threshold_large}s): {validations['large_initial_offset']}")
        st.log(f"  -> Initial offset magnitude: {initial_offset_abs}s")

        # Check 2: Final offset is small (corrected)
        final_offset_abs = abs(final_offset)
        validations["small_final_offset"] = final_offset_abs < offset_threshold_corrected
        st.log(f"Check 2 - Small final offset (<{offset_threshold_corrected}s): {validations['small_final_offset']}")
        st.log(f"  -> Final offset magnitude: {final_offset_abs}s")

        # Check 3: Offset sign matches expected direction
        if expected_offset_sign == "negative":
            # Forward drift: local clock ahead, so offset should be negative
            validations["correct_offset_sign"] = initial_offset < 0
            st.log(f"Check 3 - Negative offset (forward drift): {validations['correct_offset_sign']}")
            st.log(f"  -> Initial offset: {initial_offset}s")
        elif expected_offset_sign == "positive":
            # Backward drift: local clock behind, so offset should be positive
            validations["correct_offset_sign"] = initial_offset > 0
            st.log(f"Check 3 - Positive offset (backward drift): {validations['correct_offset_sign']}")
            st.log(f"  -> Initial offset: {initial_offset}s")
        else:
            validations["correct_offset_sign"] = True  # Unknown sign, skip validation
            st.log("Check 3 - Offset sign validation skipped (unknown expected sign)")

        # Check 4: Offset magnitude decreased
        offset_reduction = initial_offset_abs - final_offset_abs
        offset_reduction_percent = (
            (offset_reduction / initial_offset_abs * 100) if initial_offset_abs > 0 else 0
        )
        validations["offset_decreased"] = offset_reduction > 0
        st.log(f"Check 4 - Offset magnitude decreased: {validations['offset_decreased']}")
        st.log(f"  -> Offset reduction: {offset_reduction}s ({offset_reduction_percent:.1f}%)")

        # Check 5: Synchronization re-established
        final_synced = last_snapshot.get("is_synced", False)
        validations["final_synced"] = final_synced
        st.log(f"Check 5 - Synchronization re-established: {validations['final_synced']}")

        # Overall success
        all_checks_passed = all(validations.values())
        st.log("=" * 80)
        st.log(f"OVERALL VALIDATION RESULT: {'PASS' if all_checks_passed else 'FAIL'}")
        st.log("=" * 80)

        # Log detailed monitoring progression
        st.log("\nMonitoring Progression:")
        st.log(f"{'Iteration':<10} {'Offset (s)':<15} {'Synced':<10} {'Timestamp':<20}")
        st.log("-" * 60)
        for snapshot in monitoring_data:
            st.log(
                f"{snapshot['iteration']:<10} "
                f"{snapshot['offset']:<15.3f} "
                f"{str(snapshot.get('is_synced', False)):<10} "
                f"{snapshot['time_str']:<20}"
            )

        return all_checks_passed

    @pytest.mark.inventory(feature="Regression", testcases=["NTP_TC2.1.7.1"])
    def test_ntp_7_forward_drift_correction(self) -> None:
        """
        Test Case 2.1.7.1: Verify NTP detects and corrects forward clock drift (+5 minutes).

        Procedure:
        1. System already synchronized with NTP server (setup_class)
        2. Manually advance clock by 5 minutes
        3. Monitor NTP offset and correction over time
        4. Verify offset shows ~-300 seconds initially (local clock ahead)
        5. Verify offset gradually decreases toward zero
        6. Verify clock is corrected back to accurate time
        7. Verify synchronization is maintained/re-established

        Expected Result:
        - Large negative offset detected immediately after drift (~-300s)
        - Offset gradually decreases over 10-30 minutes
        - Final offset is small (< 5 seconds)
        - System remains synchronized or re-synchronizes
        - No manual intervention required
        """
        dut = self.data.dut

        st.log("\n" + "=" * 80)
        st.log("TEST CASE 2.1.7.1: Forward Clock Drift Correction (+5 minutes)")
        st.log("=" * 80)

        # Step 1: Apply forward drift (+5 minutes)
        st.log(f"\nStep 1: Applying forward clock drift (+{self.data.drift_forward_minutes} minutes)")
        drift_data = self._apply_clock_drift(dut, self.data.drift_forward_minutes)
        st.log(f"Drift applied: {drift_data['direction']}, {drift_data['drift_minutes']} minutes")

        # Wait for drift to settle and NTP to detect it
        st.log(f"\nStep 2: Waiting {self.data.wait_drift_settle}s for NTP to detect drift...")
        st.wait(self.data.wait_drift_settle)

        # Step 2: Monitor drift correction
        st.log("\nStep 3: Monitoring drift correction process")
        monitoring_data = self._monitor_drift_correction(
            dut, expected_offset_sign="negative", iterations=self.data.monitor_iterations
        )

        # Step 3: Validate correction
        st.log("\nStep 4: Validating drift correction")
        correction_success = self._validate_drift_correction(
            monitoring_data,
            expected_offset_sign="negative",
            offset_threshold_large=self.data.offset_threshold_large,
            offset_threshold_corrected=self.data.offset_threshold_corrected,
        )

        # Report result
        if correction_success:
            st.report_pass("test_case_passed")
        else:
            st.report_fail(
                "msg",
                "NTP failed to detect or correct forward clock drift within expected timeframe",
            )

    @pytest.mark.inventory(feature="Regression", testcases=["NTP_TC2.1.7.2"])
    def test_ntp_7_backward_drift_correction(self) -> None:
        """
        Test Case 2.1.7.2: Verify NTP detects and corrects backward clock drift (-5 minutes).

        Procedure:
        1. System already synchronized with NTP server (setup_class)
        2. Manually move clock back by 5 minutes
        3. Monitor NTP offset and correction over time
        4. Verify offset shows ~+300 seconds initially (local clock behind)
        5. Verify offset gradually decreases toward zero
        6. Verify clock is corrected back to accurate time
        7. Verify synchronization is maintained/re-established

        Expected Result:
        - Large positive offset detected immediately after drift (~+300s)
        - Offset gradually decreases over 10-30 minutes
        - Final offset is small (< 5 seconds)
        - System remains synchronized or re-synchronizes
        - No manual intervention required
        """
        dut = self.data.dut

        st.log("\n" + "=" * 80)
        st.log("TEST CASE 2.1.7.2: Backward Clock Drift Correction (-5 minutes)")
        st.log("=" * 80)

        # Step 1: Apply backward drift (-5 minutes)
        st.log(f"\nStep 1: Applying backward clock drift (-{self.data.drift_backward_minutes} minutes)")
        drift_data = self._apply_clock_drift(dut, -self.data.drift_backward_minutes)
        st.log(f"Drift applied: {drift_data['direction']}, {drift_data['drift_minutes']} minutes")

        # Wait for drift to settle and NTP to detect it
        st.log(f"\nStep 2: Waiting {self.data.wait_drift_settle}s for NTP to detect drift...")
        st.wait(self.data.wait_drift_settle)

        # Step 2: Monitor drift correction
        st.log("\nStep 3: Monitoring drift correction process")
        monitoring_data = self._monitor_drift_correction(
            dut, expected_offset_sign="positive", iterations=self.data.monitor_iterations
        )

        # Step 3: Validate correction
        st.log("\nStep 4: Validating drift correction")
        correction_success = self._validate_drift_correction(
            monitoring_data,
            expected_offset_sign="positive",
            offset_threshold_large=self.data.offset_threshold_large,
            offset_threshold_corrected=self.data.offset_threshold_corrected,
        )

        # Report result
        if correction_success:
            st.report_pass("test_case_passed")
        else:
            st.report_fail(
                "msg",
                "NTP failed to detect or correct backward clock drift within expected timeframe",
            )
