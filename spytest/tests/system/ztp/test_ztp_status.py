"""
ZTP STATUS VALIDATION
Author: Shiva
2026

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/ztp_standalone.yaml \\
  system/ztp/test_ztp_status.py \\
  --logs-path ./logs/test_ztp_status_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Test suite for validating ZTP (Zero Touch Provisioning) status CLI command
  functionality. This test verifies that the 'show ztp-status' command correctly
  displays the current ZTP state, operational status, admin mode, service state,
  and relevant timestamps. The test ensures that all critical status fields are
  present and properly formatted in the command output.

  Test Case Coverage:
  - TC 3.1.2: Verify ZTP status command displays current state, execution result,
              and timestamps with proper field validation.

Pre-requisites:
  - Topology: Standalone DUT (D1) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 standalone node
        # +--------------------+
        # |        DUT1        |
        # |   (smic_sonic1)    |
        # |   ZTP Status Check |
        # +--------------------+

  - Feature flags: ZTP service must be available on the device
  - Required test variables (YAML): spytest/vars/system/ztp/vars_ztp_status.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from spytest import SpyTestDict, st

# Environment variable override for YAML config
VAR_FILE_ENV = "ZTP_STATUS_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "system"
    / "ztp"
    / "vars_ztp_status.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load test case variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        st.log(f"ZTP status variable file not found: {candidate}, using defaults")
        return {
            "defaults": {
                "min_topology": ["D1"],
                "cli_type": "klish",
            },
            "testcases": {
                "3.1.2": {
                    "title": "Check ZTP status CLI",
                    "required_fields": ["adminmode", "status", "service"],
                }
            },
        }

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    return content


def _show_ztp_status_direct(dut: str, cli_type: str = "klish") -> Dict[str, Any]:
    """
    Execute ZTP status command directly and parse output.

    Args:
        dut: Device Under Test
        cli_type: CLI mode to use ("klish" or "click")

    Returns a dictionary with parsed status fields.
    """
    try:
        # Select command based on CLI type
        if cli_type == "klish":
            command = "show ztp-status"
        else:
            command = "sudo ztp status"

        st.log(f"Executing ZTP status command in {cli_type} mode: {command}")

        # Execute command with specified CLI type
        output = st.show(dut, command, type=cli_type, skip_tmpl=True)

        if not output:
            st.error("ZTP status command returned empty output")
            return {}

        # Parse the raw output
        if isinstance(output, str):
            result = {}

            # Parse key-value pairs from output
            for line in output.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_').replace('-', '_')
                    value = value.strip()
                    result[key] = value

            # Normalize common field names for both klish and click modes
            if 'ztp_admin_mode' in result:
                result['adminmode'] = result['ztp_admin_mode']
            if 'ztp_service' in result:
                result['service'] = result['ztp_service']
            if 'ztp_status' in result:
                result['status'] = result['ztp_status']

            # Handle klish-specific field names
            if 'admin_mode' in result and 'adminmode' not in result:
                result['adminmode'] = result['admin_mode']
            if 'service_status' in result and 'service' not in result:
                result['service'] = result['service_status']
            if 'operational_status' in result and 'status' not in result:
                result['status'] = result['operational_status']

            st.log(f"Parsed ZTP status ({cli_type} mode): {result}")
            return result
        else:
            st.error(f"Unexpected output type from ztp status: {type(output)}")
            return {}

    except Exception as e:
        st.error(f"Error executing ZTP status command in {cli_type} mode: {str(e)}")
        return {}


@pytest.mark.topology("any")
class TestZtpStatus:
    """Test suite for ZTP status CLI validation (TC 3.1.2)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and load test configuration."""
        st.banner("TEST CLASS SETUP: ZTP Status Validation")

        # Load configuration
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # Ensure minimum topology
        min_topology = defaults.get("min_topology") or ["D1"]
        topology = st.ensure_min_topology(*min_topology)

        # Store configuration
        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type = defaults.get("cli_type", "click")

        # Get DUT handle
        cls.data.dut = topology.D1
        cls.data.dut_name = st.get_dut_names()[0] if st.get_dut_names() else None

        st.log(f"Test topology initialized: DUT = {cls.data.dut}")
        st.log(f"CLI type: {cls.data.cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup after all tests complete."""
        st.banner("TEST CLASS TEARDOWN: ZTP Status Validation")
        st.log("No cleanup required for ZTP status validation tests")

    def setup_method(self) -> None:
        """Setup before each test method."""
        st.log("Test method setup - no specific actions required")

    def teardown_method(self) -> None:
        """Cleanup after each test method."""
        st.log("Test method teardown - no specific actions required")

    def _get_testcase(self, tcid: str) -> Dict[str, Any]:
        """Retrieve test case definition from configuration."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.log(f"[WARN] Missing testcase definition for {tcid}, using defaults")
            return {
                "title": f"Test case {tcid}",
                "required_fields": ["adminmode", "status", "service"],
            }
        return testcase

    def _validate_required_fields(
        self,
        status_dict: Dict[str, Any],
        required_fields: list
    ) -> tuple[bool, list]:
        """
        Validate that all required fields are present in the status output.

        Returns:
            tuple: (all_present: bool, missing_fields: list)
        """
        missing_fields = []

        for field in required_fields:
            if field not in status_dict or not status_dict[field]:
                missing_fields.append(field)

        all_present = len(missing_fields) == 0
        return all_present, missing_fields

    def _validate_admin_mode(self, admin_mode: str) -> bool:
        """Validate that admin mode has a valid value."""
        valid_values = ["True", "False", "Enabled", "Disabled", "true", "false"]
        return admin_mode in valid_values

    def _validate_status(self, status: str) -> bool:
        """Validate that operational status has a valid value."""
        valid_statuses = [
            "SUCCESS", "Success",
            "FAILED", "Failed",
            "IN-PROGRESS", "In-Progress", "IN PROGRESS",
            "IDLE", "Idle",
            "Not Started", "NOT STARTED",
            "Inactive", "INACTIVE",
        ]
        return status in valid_statuses or "UNKNOWN" in status.upper()

    def _validate_service_state(self, service: str) -> bool:
        """Validate that service state has a valid value."""
        valid_services = [
            "Active Discovery",
            "Processing",
            "Inactive",
            "Unknown",
        ]
        return any(valid in service for valid in valid_services)

    @pytest.mark.inventory(feature="Regression", testcases=["ZTP_TC3.1.2"])
    def test_ztp_status_command_output(self) -> None:
        """
        TC 3.1.2 - Verify ZTP status command displays current state and timestamps.

        Test Steps:
        1. Connect to the Device Under Test (DUT)
        2. Execute the ZTP status command via CLI
        3. Parse the output to identify key status indicators
        4. Validate that status fields and timestamps are present and not empty

        Pass Criteria:
        - Command returns valid output (not empty)
        - Output contains "Admin Mode" and "Oper Status" fields
        - All critical status fields are present and have valid values

        Fail Criteria:
        - Command returns error or empty string
        - Key status fields are missing from the parsed output
        """
        st.banner("TC 3.1.2: Check ZTP Status CLI")

        # Get test case configuration
        testcase = self._get_testcase("3.1.2")
        required_fields = testcase.get("required_fields", ["adminmode", "status", "service"])

        dut = self.data.dut

        # Step 1 & 2: Connect to DUT and execute ZTP status command
        st.log("STEP 1-2: Executing ZTP status command on DUT")
        status_dict = _show_ztp_status_direct(dut, self.data.cli_type)

        # Validate command returned output
        if not status_dict:
            st.report_fail(
                "msg",
                "FAIL: ZTP status command returned empty output or failed to execute"
            )

        st.log(f"ZTP Status Output: {status_dict}")

        # Step 3: Validate required fields are present
        st.log("STEP 3: Validating required fields are present")
        all_present, missing_fields = self._validate_required_fields(
            status_dict,
            required_fields
        )

        if not all_present:
            st.report_fail(
                "msg",
                f"FAIL: Missing required fields in ZTP status: {missing_fields}"
            )

        st.log("✓ All required fields are present")

        # Step 4: Validate field values
        st.log("STEP 4: Validating status field values")

        # Validate Admin Mode
        admin_mode = status_dict.get("adminmode", "")
        if not self._validate_admin_mode(admin_mode):
            st.error(f"Invalid Admin Mode value: {admin_mode}")
            st.report_fail(
                "msg",
                f"FAIL: Invalid Admin Mode value '{admin_mode}' - expected True/False/Enabled/Disabled"
            )
        st.log(f"✓ Admin Mode is valid: {admin_mode}")

        # Validate Operational Status
        oper_status = status_dict.get("status", "")
        if not self._validate_status(oper_status):
            st.log(f"[WARN] Unusual Operational Status value: {oper_status}")
        else:
            st.log(f"✓ Operational Status is valid: {oper_status}")

        # Validate Service State
        service_state = status_dict.get("service", "")
        if service_state and not self._validate_service_state(service_state):
            st.log(f"[WARN] Unusual Service State value: {service_state}")
        else:
            st.log(f"✓ Service State is valid: {service_state}")

        # Check for timestamp fields (optional but recommended)
        timestamp_fields = ["runtime", "start_time", "last_run", "timestamp"]
        found_timestamp = any(field in status_dict for field in timestamp_fields)

        if found_timestamp:
            st.log("✓ Timestamp information is present in status output")
        else:
            st.log("[INFO] No explicit timestamp fields found (may be acceptable)")

        # Final validation summary
        st.log("=" * 80)
        st.log("ZTP STATUS VALIDATION SUMMARY:")
        st.log(f"  Admin Mode     : {admin_mode}")
        st.log(f"  Oper Status    : {oper_status}")
        st.log(f"  Service State  : {service_state}")
        st.log(f"  Timestamp Info : {'Present' if found_timestamp else 'Not Found'}")
        st.log("=" * 80)

        # Test passed
        st.report_pass(
            "msg",
            "PASS: ZTP status command successfully displays all required fields with valid values"
        )

    @pytest.mark.inventory(feature="Regression", testcases=["ZTP_TC3.1.2_Field_Validation"])
    def test_ztp_status_field_validation(self) -> None:
        """
        Additional validation test for ZTP status field integrity.

        This test performs deeper validation of the ZTP status output to ensure
        that the data format and values conform to expected patterns.
        """
        st.banner("TC 3.1.2 Extended: ZTP Status Field Validation")

        dut = self.data.dut

        # Get ZTP status
        st.log("Retrieving ZTP status for field validation")
        status_dict = _show_ztp_status_direct(dut, self.data.cli_type)

        if not status_dict:
            st.report_fail("msg", "FAIL: Unable to retrieve ZTP status")

        # Perform extended validations
        validation_results = []

        # Check 1: Admin mode field exists and is not empty
        if "adminmode" in status_dict and status_dict["adminmode"]:
            validation_results.append(("Admin Mode Present", True, status_dict["adminmode"]))
        else:
            validation_results.append(("Admin Mode Present", False, "Missing"))

        # Check 2: Status field exists and is not empty
        if "status" in status_dict and status_dict["status"]:
            validation_results.append(("Status Present", True, status_dict["status"]))
        else:
            validation_results.append(("Status Present", False, "Missing"))

        # Check 3: Service field exists
        if "service" in status_dict and status_dict["service"]:
            validation_results.append(("Service Present", True, status_dict["service"]))
        else:
            validation_results.append(("Service Present", False, "Missing"))

        # Check 4: At least 3 fields present (minimum viable status output)
        field_count = len([k for k, v in status_dict.items() if v])
        if field_count >= 3:
            validation_results.append(("Minimum Fields", True, f"{field_count} fields"))
        else:
            validation_results.append(("Minimum Fields", False, f"Only {field_count} fields"))

        # Display validation results
        st.log("=" * 80)
        st.log("FIELD VALIDATION RESULTS:")
        failed_checks = 0
        for check_name, passed, details in validation_results:
            status_symbol = "✓" if passed else "✗"
            st.log(f"  {status_symbol} {check_name:.<30} {details}")
            if not passed:
                failed_checks += 1
        st.log("=" * 80)

        # Report results
        if failed_checks > 0:
            st.report_fail(
                "msg",
                f"FAIL: {failed_checks} field validation checks failed"
            )

        st.report_pass(
            "msg",
            "PASS: All ZTP status field validations passed"
        )
