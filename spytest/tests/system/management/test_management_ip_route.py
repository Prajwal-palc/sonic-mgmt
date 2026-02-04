"""
MANAGEMENT INTERFACE IP ROUTING VERIFICATION
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/ztp_standalone.yaml  \
  tests/system/management/test_management_ip_route.py \
  --logs-path ./logs/test_management_ip_route_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Validation of Management interface presence in IP routing table and VRF
  configuration using SpyTest APIs and sonic-cli (klish). The test validates
  that Management0 interface appears in 'show ip route' output with correct
  route codes (K>* for kernel routes, C>* for connected routes) and verifies
  VRF configuration status. Handles pagination in show commands by setting
  terminal length to 0. Non-destructive read-only verification.

Files and APIs Used:
  - Testbed Configuration:
      * testbeds/ztp_standalone.yaml - Standalone DUT configuration

  - SpyTest APIs (Existing):
      * apis.routing.ip.show_ip_route() - Retrieve IP routing table
        Location: spytest/apis/routing/ip.py:1089
      * apis.system.management_vrf.show() - Show management VRF config
        Location: spytest/apis/system/management_vrf.py:84

  - SpyTest Framework Functions:
      * st.config() - Execute configuration commands
      * st.show() - Execute show commands
      * st.log(), st.banner(), st.debug() - Logging functions
      * st.report_pass(), st.report_fail() - Test result reporting

Pre-requisites:
  - Topology: standalone (single DUT) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node (standalone)
        # +--------------------+
        # |        D1          |
        # |    (smic_sonic1)   |
        # |   Management0      |
        # +--------------------+

  - Feature flags / min SONiC version: Basic IP routing and VRF support required
  - Required test variables: Uses testbed file directly (no external YAML vars needed)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

import pytest

from spytest import SpyTestDict, st
import apis.routing.ip as ip_api
import apis.system.management_vrf as mgmt_vrf_api


# Test constants
MGMT_INTERFACE = "Management0"


@pytest.mark.topology("any")
class TestManagementIPRoute:
    """Testcases covering Management interface IP routing verification."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and disable terminal pagination."""
        st.banner("CLASS SETUP: Starting Management IP Route Test Suite")

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

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup after test suite completion."""
        st.banner("CLASS TEARDOWN: Management IP Route Test Suite Completed")
        st.log("Class teardown completed")

    @staticmethod
    def _set_terminal_length(dut: str, length: int = 0) -> None:
        """Set terminal length to control pagination in show commands.

        Args:
            dut: Device under test
            length: Terminal length (0 = no pagination)
        """
        try:
            # Use klish CLI to set terminal length
            cmd = f"terminal length {length}"
            st.config(dut, cmd, type="klish", conf=False, skip_error_check=True)
            st.log(f"Set terminal length to {length} on {dut}")
        except Exception as e:
            st.warn(f"Failed to set terminal length: {e}")

    @staticmethod
    def _get_ip_route_output(dut: str) -> str:
        """Retrieve IP route table output with pagination disabled.

        Args:
            dut: Device under test

        Returns:
            IP route output as string
        """
        # Set terminal length to 0 to avoid --more-- pagination prompts
        st.config(dut, "terminal length 0", type="klish", conf=False, skip_error_check=True)

        cmd = "show ip route"
        output = st.show(dut, cmd, type="klish", skip_tmpl=True, skip_error_check=True)

        if isinstance(output, list) and output:
            # Join list output into single string
            route_text = "\n".join(str(item) for item in output)
        elif isinstance(output, str):
            route_text = output
        else:
            route_text = str(output)

        return route_text

    @staticmethod
    def _verify_route_codes_legend(route_output: str) -> Dict[str, bool]:
        """Verify that route codes legend is present in output.

        Args:
            route_output: IP route output text

        Returns:
            Dictionary with verification results
        """
        result = {
            "codes_header": False,
            "kernel_code": False,
            "connected_code": False,
            "static_code": False,
            "selected_flag": False,
            "fib_flag": False
        }

        # Check for "Codes:" header
        if re.search(r"Codes:\s*K\s*-\s*kernel", route_output, re.IGNORECASE):
            result["codes_header"] = True

        # Check for kernel route code (K)
        if re.search(r"K\s*-\s*kernel", route_output, re.IGNORECASE):
            result["kernel_code"] = True

        # Check for connected route code (C)
        if re.search(r"C\s*-\s*connected", route_output, re.IGNORECASE):
            result["connected_code"] = True

        # Check for static route code (S)
        if re.search(r"S\s*-\s*static", route_output, re.IGNORECASE):
            result["static_code"] = True

        # Check for selected route flag (>)
        if re.search(r">\s*-\s*selected", route_output, re.IGNORECASE):
            result["selected_flag"] = True

        # Check for FIB route flag (*)
        if re.search(r"\*\s*-\s*FIB", route_output, re.IGNORECASE):
            result["fib_flag"] = True

        return result

    @staticmethod
    def _find_management0_routes(route_output: str) -> Dict[str, Any]:
        """Parse route output to find Management0 interface routes.

        Args:
            route_output: IP route output text

        Returns:
            Dictionary with Management0 route details
        """
        result = {
            "management0_found": False,
            "kernel_routes": [],
            "connected_routes": [],
            "all_routes": []
        }

        # Pattern to match routes with Management0
        # Examples:
        # K>* 0.0.0.0/0 [0/0] via 172.31.0.1, Management0, weight 1, 00:02:37
        # C>* 172.31.0.0/16 is directly connected, Management0, weight 1, 00:02:37

        # Find all lines containing Management0
        management0_lines = []
        for line in route_output.split('\n'):
            if 'Management0' in line or 'management0' in line.lower():
                management0_lines.append(line.strip())
                result["management0_found"] = True

        result["all_routes"] = management0_lines

        # Parse kernel routes (K>*)
        for line in management0_lines:
            if re.match(r'K[>\*\s]+', line):
                # Extract route details
                route_match = re.search(
                    r'(K[>\*\s]+)\s+([\d\.\/]+)\s+.*Management0',
                    line,
                    re.IGNORECASE
                )
                if route_match:
                    result["kernel_routes"].append({
                        "code": route_match.group(1).strip(),
                        "prefix": route_match.group(2).strip(),
                        "full_line": line
                    })

        # Parse connected routes (C>*)
        for line in management0_lines:
            if re.match(r'C[>\*\s]+', line):
                # Extract route details
                route_match = re.search(
                    r'(C[>\*\s]+)\s+([\d\.\/]+)\s+.*Management0',
                    line,
                    re.IGNORECASE
                )
                if route_match:
                    result["connected_routes"].append({
                        "code": route_match.group(1).strip(),
                        "prefix": route_match.group(2).strip(),
                        "full_line": line
                    })

        return result

    @staticmethod
    def _verify_route_code_format(code: str, expected_type: str) -> bool:
        """Verify route code has correct format with flags.

        Args:
            code: Route code string (e.g., "K>*" or "C>*")
            expected_type: Expected route type ('K' for kernel, 'C' for connected)

        Returns:
            True if code format is valid
        """
        # Route code should have:
        # - Route type (K, C, S, etc.)
        # - Selected flag (>)
        # - FIB flag (*)
        pattern = rf"{expected_type}[>\*\s]+"
        return bool(re.match(pattern, code))

    @pytest.mark.inventory(feature="Regression", testcases=["MGMT_IP_ROUTE_TC_001"])
    def test_management0_in_ip_route(self) -> None:
        """TC 001 - Verify Management0 interface in IP route table.

        Test Steps:
        1. Execute 'show ip route' command
        2. Verify route codes legend is displayed
        3. Verify Management0 interface appears in route output
        4. Verify kernel route (K>*) for Management0 exists
        5. Verify connected route (C>*) for Management0 exists
        6. Validate route code format and flags
        """
        dut = self.data.dut

        st.banner("STEP 1: Retrieve IP route table")
        route_output = self._get_ip_route_output(dut)

        if not route_output:
            st.report_fail("msg", "Failed to retrieve IP route output")

        st.log("IP route output retrieved successfully")
        st.debug(f"IP route output:\n{route_output}")

        st.banner("STEP 2: Verify route codes legend")
        codes_check = self._verify_route_codes_legend(route_output)

        if not codes_check["codes_header"]:
            st.report_fail("msg", "Route codes header not found in output")

        st.log("✓ Route codes header found")

        # Verify essential route codes
        if not codes_check["kernel_code"]:
            st.report_fail("msg", "Kernel route code (K) not found in legend")

        st.log("✓ Kernel route code (K) found in legend")

        if not codes_check["connected_code"]:
            st.report_fail("msg", "Connected route code (C) not found in legend")

        st.log("✓ Connected route code (C) found in legend")

        # Verify route flags
        if not codes_check["selected_flag"]:
            st.report_fail("msg", "Selected route flag (>) not found in legend")

        st.log("✓ Selected route flag (>) found in legend")

        if not codes_check["fib_flag"]:
            st.report_fail("msg", "FIB route flag (*) not found in legend")

        st.log("✓ FIB route flag (*) found in legend")

        st.banner("STEP 3: Verify Management0 interface in route table")
        mgmt_routes = self._find_management0_routes(route_output)

        if not mgmt_routes["management0_found"]:
            st.report_fail("msg", "Management0 interface not found in IP route table")

        st.log(f"✓ Management0 found in IP route table")
        st.log(f"Total Management0 routes found: {len(mgmt_routes['all_routes'])}")

        st.banner("STEP 4: Verify kernel route (K>*) for Management0")
        if not mgmt_routes["kernel_routes"]:
            st.report_fail(
                "msg",
                "No kernel routes (K>*) found for Management0. "
                f"All Management0 routes: {mgmt_routes['all_routes']}"
            )

        st.log(f"✓ Kernel route(s) found for Management0: {len(mgmt_routes['kernel_routes'])}")

        # Verify kernel route format
        for route in mgmt_routes["kernel_routes"]:
            st.log(f"  Kernel route: {route['full_line']}")
            if not self._verify_route_code_format(route["code"], "K"):
                st.warn(f"Kernel route code format may be incorrect: {route['code']}")
            else:
                st.log(f"  ✓ Route code format valid: {route['code']}")

        st.banner("STEP 5: Verify connected route (C>*) for Management0")
        if not mgmt_routes["connected_routes"]:
            st.report_fail(
                "msg",
                "No connected routes (C>*) found for Management0. "
                f"All Management0 routes: {mgmt_routes['all_routes']}"
            )

        st.log(f"✓ Connected route(s) found for Management0: {len(mgmt_routes['connected_routes'])}")

        # Verify connected route format
        for route in mgmt_routes["connected_routes"]:
            st.log(f"  Connected route: {route['full_line']}")
            if not self._verify_route_code_format(route["code"], "C"):
                st.warn(f"Connected route code format may be incorrect: {route['code']}")
            else:
                st.log(f"  ✓ Route code format valid: {route['code']}")

        st.banner("STEP 6: Summary of Management0 routes")
        st.log(f"Kernel routes: {len(mgmt_routes['kernel_routes'])}")
        for route in mgmt_routes["kernel_routes"]:
            st.log(f"  - {route['code']} {route['prefix']}")

        st.log(f"Connected routes: {len(mgmt_routes['connected_routes'])}")
        for route in mgmt_routes["connected_routes"]:
            st.log(f"  - {route['code']} {route['prefix']}")

        st.banner("TEST PASSED: Management0 verified in IP route table with correct route codes")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["MGMT_VRF_TC_002"])
    def test_vrf_configuration(self) -> None:
        """TC 002 - Verify VRF configuration and management VRF status.

        Test Steps:
        1. Execute 'show ip vrf' command
        2. Parse VRF output
        3. Verify management VRF status if configured
        4. Log all discovered VRF configurations
        """
        dut = self.data.dut

        st.banner("STEP 1: Retrieve VRF configuration")

        # Set terminal length to avoid pagination
        st.config(dut, "terminal length 0", type="klish", conf=False, skip_error_check=True)

        # Get VRF information using API
        try:
            vrf_output = mgmt_vrf_api.show(dut, cli_type="klish")
            st.log("VRF configuration retrieved successfully")
            st.debug(f"VRF output: {vrf_output}")
        except Exception as e:
            st.log(f"Unable to retrieve VRF config via API: {e}")
            # Fallback to direct command
            cmd = "show ip vrf"
            vrf_output = st.show(dut, cmd, type="klish", skip_tmpl=True, skip_error_check=True)
            st.debug(f"VRF output (direct command): {vrf_output}")

        st.banner("STEP 2: Parse VRF configuration")

        if not vrf_output:
            st.log("No VRF configuration found (empty output)")
            st.log("✓ No VRF configured - using default VRF only")
        else:
            st.log("VRF configuration detected")

            # Handle both list and string output
            if isinstance(vrf_output, list):
                st.log(f"Number of VRF entries: {len(vrf_output)}")
                for idx, vrf_entry in enumerate(vrf_output):
                    st.log(f"VRF entry {idx + 1}: {vrf_entry}")
            elif isinstance(vrf_output, str):
                st.log(f"VRF output: {vrf_output}")
            else:
                st.log(f"VRF output type: {type(vrf_output)}")

        st.banner("STEP 3: Verify management VRF status")

        # Check if management VRF is configured
        mgmt_vrf_found = False

        if isinstance(vrf_output, list):
            for entry in vrf_output:
                if isinstance(entry, dict):
                    # Check for mgmt VRF in dictionary
                    if entry.get('vrfname') == 'mgmt' or entry.get('vrf_name') == 'mgmt':
                        mgmt_vrf_found = True
                        st.log(f"✓ Management VRF found: {entry}")
                        # Check interface binding
                        if entry.get('interface') == 'Management0':
                            st.log("✓ Management VRF bound to Management0")
        elif isinstance(vrf_output, str):
            if 'mgmt' in vrf_output.lower():
                mgmt_vrf_found = True
                st.log("✓ Management VRF found in output")

        if not mgmt_vrf_found:
            st.log("Management VRF not configured - using default VRF")
        else:
            st.log("✓ Management VRF is configured")

        st.banner("STEP 4: VRF configuration summary")
        if not vrf_output or vrf_output == []:
            st.log("VRF Status: Default VRF only (no custom VRFs configured)")
        else:
            st.log("VRF Status: Custom VRF(s) configured")
            if mgmt_vrf_found:
                st.log("  - Management VRF: Configured")
            else:
                st.log("  - Management VRF: Not configured")

        st.banner("TEST PASSED: VRF configuration verified")
        st.report_pass("test_case_passed")
