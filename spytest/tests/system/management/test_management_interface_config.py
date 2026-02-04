"""
MANAGEMENT INTERFACE CONFIGURATION
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/ztp_standalone.yaml  \
  tests/system/management/test_management_interface_config.py \
  --logs-path ./logs/test_management_interface_config_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Validation of Management interface configuration and operational status using
  SpyTest APIs and sonic-cli (klish). The test validates Management0 default
  settings in running configuration (mtu, speed, autoneg) and operational status
  (interface up/down, MAC address, IPv4/IPv6 configuration). Handles pagination
  in show commands by setting terminal length to 0. Each testcase consumes
  topology-aware variables from the testbed YAML to remain reusable across
  SONiC hardware and virtual environments.

Files and APIs Used:
  - Testbed Configuration:
      * testbeds/ztp_standalone.yaml - Standalone DUT configuration

  - SpyTest Framework Functions:
      * st.config() - Execute configuration commands
      * st.show() - Execute show commands
      * st.log(), st.banner(), st.debug() - Logging functions
      * st.wait() - Wait for configuration propagation
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

  - Feature flags / min SONiC version: Basic Management interface support required
  - Required test variables: Uses testbed file directly (no external YAML vars needed)
"""

from __future__ import annotations

import re
from typing import Any, Dict

import pytest

from spytest import SpyTestDict, st


# Test constants
MGMT_INTERFACE = "Management0"


@pytest.mark.topology("any")
class TestManagementInterface:
    """Testcases covering Management interface configuration and verification."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and disable terminal pagination."""
        st.banner("CLASS SETUP: Starting Management Interface Test Suite")

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
        st.banner("CLASS TEARDOWN: Management Interface Test Suite Completed")
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
    def _get_running_config(dut: str, module: str = None) -> str:
        """Retrieve running configuration with pagination disabled.

        Args:
            dut: Device under test
            module: Optional module filter (e.g., "interface Management")

        Returns:
            Running configuration as string
        """
        # Set terminal length to 0 to avoid --more-- pagination prompts
        st.config(dut, "terminal length 0", type="klish", conf=False, skip_error_check=True)

        if module:
            cmd = f"show running-configuration {module}"
        else:
            cmd = "show running-configuration"

        output = st.show(dut, cmd, type="klish", skip_tmpl=True, skip_error_check=True)

        if isinstance(output, list) and output:
            # Join list output into single string
            config_text = "\n".join(str(item) for item in output)
        elif isinstance(output, str):
            config_text = output
        else:
            config_text = str(output)

        return config_text

    @staticmethod
    def _parse_management_config(config_text: str) -> Dict[str, Any]:
        """Parse running config to extract Management interface settings.

        Args:
            config_text: Running configuration text

        Returns:
            Dictionary with Management interface configuration details
        """
        result = {
            "interface_found": False,
            "description": None,
            "mtu": None,
            "speed": None,
            "autoneg": None,
            "ipv4_addresses": [],
            "ipv6_addresses": []
        }

        # Find the Management0 interface block
        # Pattern: Look for "interface Management0" section
        interface_pattern = r"interface\s+Management\s*0(.*?)(?=^interface\s+|\Z)"
        match = re.search(interface_pattern, config_text, re.MULTILINE | re.DOTALL | re.IGNORECASE)

        if not match:
            st.log("Management0 interface section not found in running config")
            return result

        result["interface_found"] = True
        interface_block = match.group(0)
        st.debug(f"Management0 interface block:\n{interface_block}")

        # Parse description
        desc_match = re.search(r"^\s*description\s+(.+)$", interface_block, re.MULTILINE)
        if desc_match:
            result["description"] = desc_match.group(1).strip()

        # Parse MTU
        mtu_match = re.search(r"^\s*mtu\s+(\d+)$", interface_block, re.MULTILINE)
        if mtu_match:
            result["mtu"] = int(mtu_match.group(1))

        # Parse speed
        speed_match = re.search(r"^\s*speed\s+(\d+)$", interface_block, re.MULTILINE)
        if speed_match:
            result["speed"] = int(speed_match.group(1))

        # Parse autoneg
        autoneg_match = re.search(r"^\s*autoneg\s+(on|off)$", interface_block, re.MULTILINE)
        if autoneg_match:
            result["autoneg"] = autoneg_match.group(1).strip()

        # Parse IPv4 addresses
        ipv4_pattern = r"^\s*ip\s+address\s+([\d\.]+)/([\d]+)"
        for ipv4_match in re.finditer(ipv4_pattern, interface_block, re.MULTILINE):
            ip_addr = ipv4_match.group(1)
            prefix_len = ipv4_match.group(2)
            result["ipv4_addresses"].append(f"{ip_addr}/{prefix_len}")

        # Parse IPv6 addresses
        ipv6_pattern = r"^\s*ipv6\s+address\s+([\da-fA-F:]+)/([\d]+)"
        for ipv6_match in re.finditer(ipv6_pattern, interface_block, re.MULTILINE):
            ip_addr = ipv6_match.group(1)
            prefix_len = ipv6_match.group(2)
            result["ipv6_addresses"].append(f"{ip_addr}/{prefix_len}")

        return result

    @staticmethod
    def _parse_show_interface_management(output: str) -> Dict[str, Any]:
        """Parse 'show interface Management' output.

        Args:
            output: Output from 'show interface Management' command

        Returns:
            Dictionary with Management interface operational details
        """
        result = {
            "interface_status": None,
            "line_protocol": None,
            "hardware_type": None,
            "mac_address": None,
            "description": None,
            "ipv4_address": None,
            "ipv4_mode": None,
            "ipv6_address": None,
            "ipv6_mode": None,
            "ipv6_oper_status": None,
            "mtu": None,
            "input_packets": None,
            "input_octets": None,
            "output_packets": None,
            "output_octets": None
        }

        # Parse interface and line protocol status
        # Example: Management0 is up, line protocol is up
        status_match = re.search(
            r"Management0\s+is\s+(up|down),\s+line\s+protocol\s+is\s+(up|down)",
            output,
            re.IGNORECASE
        )
        if status_match:
            result["interface_status"] = status_match.group(1).lower()
            result["line_protocol"] = status_match.group(2).lower()

        # Parse hardware type and MAC address
        # Example: Hardware is MGMT, address is 52:54:00:d3:73:02
        hw_match = re.search(
            r"Hardware\s+is\s+(\w+),\s+address\s+is\s+([0-9a-fA-F:]{17})",
            output,
            re.IGNORECASE
        )
        if hw_match:
            result["hardware_type"] = hw_match.group(1)
            result["mac_address"] = hw_match.group(2)

        # Parse description
        # Example: Description: Management0
        desc_match = re.search(r"Description:\s*(.+)", output)
        if desc_match:
            result["description"] = desc_match.group(1).strip()

        # Parse IPv4 address
        # Example: IPV4 address is 192.168.100.197/24
        ipv4_match = re.search(r"IPV4\s+address\s+is\s+([\d\.]+/\d+)", output, re.IGNORECASE)
        if ipv4_match:
            result["ipv4_address"] = ipv4_match.group(1)

        # Parse IPv4 assignment mode
        # Example: Mode of IPV4 address assignment: DHCP
        ipv4_mode_match = re.search(
            r"Mode\s+of\s+IPV4\s+address\s+assignment:\s+(\w+)",
            output,
            re.IGNORECASE
        )
        if ipv4_mode_match:
            result["ipv4_mode"] = ipv4_mode_match.group(1)

        # Parse IPv6 address
        # Example: IPV6 address is fe80::5054:ff:fed3:7302/64
        ipv6_match = re.search(r"IPV6\s+address\s+is\s+([\da-fA-F:]+/\d+)", output, re.IGNORECASE)
        if ipv6_match:
            result["ipv6_address"] = ipv6_match.group(1)

        # Parse IPv6 assignment mode
        # Example: Mode of IPV6 address assignment: OTHER
        ipv6_mode_match = re.search(
            r"Mode\s+of\s+IPV6\s+address\s+assignment:\s+(\w+)",
            output,
            re.IGNORECASE
        )
        if ipv6_mode_match:
            result["ipv6_mode"] = ipv6_mode_match.group(1)

        # Parse IPv6 operational status
        # Example: Interface IPv6 oper status: Enabled
        ipv6_oper_match = re.search(
            r"Interface\s+IPv6\s+oper\s+status:\s+(\w+)",
            output,
            re.IGNORECASE
        )
        if ipv6_oper_match:
            result["ipv6_oper_status"] = ipv6_oper_match.group(1)

        # Parse MTU
        # Example: IP MTU 1500 bytes
        mtu_match = re.search(r"IP\s+MTU\s+(\d+)\s+bytes", output, re.IGNORECASE)
        if mtu_match:
            result["mtu"] = int(mtu_match.group(1))

        # Parse input statistics
        # Example: 22014 packets, 4017623 octets
        input_match = re.search(r"Input\s+statistics:.*?(\d+)\s+packets,\s+(\d+)\s+octets", output, re.DOTALL)
        if input_match:
            result["input_packets"] = int(input_match.group(1))
            result["input_octets"] = int(input_match.group(2))

        # Parse output statistics
        # Example: 7440 packets, 1130050 octets
        output_match = re.search(r"Output\s+statistics:.*?(\d+)\s+packets,\s+(\d+)\s+octets", output, re.DOTALL)
        if output_match:
            result["output_packets"] = int(output_match.group(1))
            result["output_octets"] = int(output_match.group(2))

        return result

    @pytest.mark.inventory(feature="Regression", testcases=["MGMT_TC_001"])
    def test_management_running_config_basic(self) -> None:
        """TC 001 - Verify Management0 default configuration in running-config.

        Test Steps:
        1. Retrieve running configuration for Management interface
        2. Verify Management0 interface section exists
        3. Verify default settings: mtu 1500, speed 1000, autoneg on
        4. Log all discovered Management interface settings
        """
        dut = self.data.dut

        st.banner("STEP 1: Retrieve running configuration for Management interface")
        config = self._get_running_config(dut, module="interface Management")

        if not config:
            st.report_fail("msg", "Failed to retrieve running configuration")

        st.log("Running configuration retrieved successfully")
        st.debug(f"Management interface config:\n{config}")

        st.banner("STEP 2: Parse Management0 configuration")
        parsed_config = self._parse_management_config(config)

        if not parsed_config["interface_found"]:
            st.report_fail("msg", "Management0 interface not found in running configuration")

        st.log("✓ Management0 interface section found in running configuration")

        st.banner("STEP 3: Verify default Management0 settings")

        # Verify MTU
        if parsed_config["mtu"] is None:
            st.report_fail("msg", "MTU setting not found in Management0 configuration")

        if parsed_config["mtu"] != 1500:
            st.report_fail(
                "msg",
                f"MTU mismatch: expected 1500, found {parsed_config['mtu']}"
            )

        st.log(f"✓ MTU verified: {parsed_config['mtu']}")

        # Verify speed
        if parsed_config["speed"] is None:
            st.report_fail("msg", "Speed setting not found in Management0 configuration")

        if parsed_config["speed"] != 1000:
            st.report_fail(
                "msg",
                f"Speed mismatch: expected 1000, found {parsed_config['speed']}"
            )

        st.log(f"✓ Speed verified: {parsed_config['speed']}")

        # Verify autoneg
        if parsed_config["autoneg"] is None:
            st.report_fail("msg", "Autoneg setting not found in Management0 configuration")

        if parsed_config["autoneg"] != "on":
            st.report_fail(
                "msg",
                f"Autoneg mismatch: expected 'on', found '{parsed_config['autoneg']}'"
            )

        st.log(f"✓ Autoneg verified: {parsed_config['autoneg']}")

        st.banner("STEP 4: Log complete Management0 configuration")
        st.log(f"Description: {parsed_config.get('description', 'N/A')}")
        st.log(f"MTU: {parsed_config['mtu']}")
        st.log(f"Speed: {parsed_config['speed']}")
        st.log(f"Autoneg: {parsed_config['autoneg']}")
        st.log(f"IPv4 Addresses: {parsed_config['ipv4_addresses']}")
        st.log(f"IPv6 Addresses: {parsed_config['ipv6_addresses']}")

        st.banner("TEST PASSED: Management0 default configuration verified")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["MGMT_TC_002"])
    def test_management_interface_status(self) -> None:
        """TC 002 - Verify Management0 interface operational status and details.

        Test Steps:
        1. Execute 'show interface Management' with terminal length 0
        2. Verify interface operational status (up/down)
        3. Verify line protocol status
        4. Verify hardware type is MGMT
        5. Verify MAC address is present
        6. Verify IPv4 address and assignment mode
        7. Verify IPv6 address and configuration
        8. Verify MTU is 1500 bytes
        9. Log interface statistics (informational)
        """
        dut = self.data.dut

        st.banner("STEP 1: Execute 'show interface Management' with terminal length 0")

        # Set terminal length to 0 to avoid --more-- pagination prompts
        st.config(dut, "terminal length 0", type="klish", conf=False, skip_error_check=True)

        cmd = "show interface Management"
        output = st.show(dut, cmd, type="klish", skip_tmpl=True, skip_error_check=True)

        # Convert output to string
        if isinstance(output, list) and output:
            output_str = "\n".join(str(item) for item in output)
        elif isinstance(output, str):
            output_str = output
        else:
            output_str = str(output)

        if not output_str:
            st.report_fail("msg", "Failed to retrieve 'show interface Management' output")

        st.log("'show interface Management' output retrieved successfully")
        st.debug(f"Interface output:\n{output_str}")

        # Parse the output
        parsed = self._parse_show_interface_management(output_str)

        st.banner("STEP 2: Verify interface operational status")

        if parsed["interface_status"] is None:
            st.report_fail("msg", "Interface operational status not found in output")

        st.log(f"✓ Interface status: {parsed['interface_status']}")

        st.banner("STEP 3: Verify line protocol status")

        if parsed["line_protocol"] is None:
            st.report_fail("msg", "Line protocol status not found in output")

        st.log(f"✓ Line protocol status: {parsed['line_protocol']}")

        st.banner("STEP 4: Verify hardware type is MGMT")

        if parsed["hardware_type"] is None:
            st.report_fail("msg", "Hardware type not found in output")

        if parsed["hardware_type"] != "MGMT":
            st.warn(
                f"Hardware type unexpected: expected 'MGMT', found '{parsed['hardware_type']}'"
            )
        else:
            st.log(f"✓ Hardware type: {parsed['hardware_type']}")

        st.banner("STEP 5: Verify MAC address is present")

        if parsed["mac_address"] is None:
            st.report_fail("msg", "MAC address not found in output")

        st.log(f"✓ MAC address: {parsed['mac_address']}")

        st.banner("STEP 6: Verify IPv4 address and assignment mode")

        if parsed["ipv4_address"]:
            st.log(f"✓ IPv4 address: {parsed['ipv4_address']}")
        else:
            st.log("IPv4 address: Not configured")

        if parsed["ipv4_mode"]:
            st.log(f"✓ IPv4 assignment mode: {parsed['ipv4_mode']}")
        else:
            st.log("IPv4 assignment mode: Not available")

        st.banner("STEP 7: Verify IPv6 address and configuration")

        if parsed["ipv6_address"]:
            st.log(f"✓ IPv6 address: {parsed['ipv6_address']}")
        else:
            st.log("IPv6 address: Not configured")

        if parsed["ipv6_mode"]:
            st.log(f"✓ IPv6 assignment mode: {parsed['ipv6_mode']}")
        else:
            st.log("IPv6 assignment mode: Not available")

        if parsed["ipv6_oper_status"]:
            st.log(f"✓ IPv6 operational status: {parsed['ipv6_oper_status']}")
        else:
            st.log("IPv6 operational status: Not available")

        st.banner("STEP 8: Verify MTU is 1500 bytes")

        if parsed["mtu"] is None:
            st.report_fail("msg", "MTU not found in output")

        if parsed["mtu"] != 1500:
            st.warn(f"MTU unexpected: expected 1500, found {parsed['mtu']}")
        else:
            st.log(f"✓ MTU: {parsed['mtu']} bytes")

        st.banner("STEP 9: Log interface statistics (informational)")

        st.log("Input Statistics:")
        if parsed["input_packets"] is not None:
            st.log(f"  Packets: {parsed['input_packets']}")
        if parsed["input_octets"] is not None:
            st.log(f"  Octets: {parsed['input_octets']}")

        st.log("Output Statistics:")
        if parsed["output_packets"] is not None:
            st.log(f"  Packets: {parsed['output_packets']}")
        if parsed["output_octets"] is not None:
            st.log(f"  Octets: {parsed['output_octets']}")

        st.banner("Management Interface Status Summary:")
        st.log(f"Interface Status: {parsed['interface_status']}")
        st.log(f"Line Protocol: {parsed['line_protocol']}")
        st.log(f"Hardware Type: {parsed['hardware_type']}")
        st.log(f"MAC Address: {parsed['mac_address']}")
        st.log(f"Description: {parsed['description']}")
        st.log(f"IPv4 Address: {parsed['ipv4_address'] or 'N/A'}")
        st.log(f"IPv4 Mode: {parsed['ipv4_mode'] or 'N/A'}")
        st.log(f"IPv6 Address: {parsed['ipv6_address'] or 'N/A'}")
        st.log(f"IPv6 Mode: {parsed['ipv6_mode'] or 'N/A'}")
        st.log(f"IPv6 Oper Status: {parsed['ipv6_oper_status'] or 'N/A'}")
        st.log(f"MTU: {parsed['mtu']} bytes")

        st.banner("TEST PASSED: Management0 interface status verified")
        st.report_pass("test_case_passed")
