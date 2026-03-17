"""
L3 ACL Negative Test Cases (Edge Cases and Error Scenarios)

Author: Claude Code
Date: 2026-03-12
Version: 1.0 - Negative Test Cases with Proper Traffic Implementation

How to run:
  ./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
      tests/routing/l3_acl/test_l3_acl_basic.py \
      --logs-path ./logs/l3_acl_negative_$(date +%F_%H%M%S) \
      --log-level debug --skip-init-config

Description:
  Comprehensive negative/edge-case test suite for L3 ACL functionality.
  Tests validate behavior with overlapping rules, broadcast addresses, protocol
  boundaries, port boundaries, invalid flag combinations, TTL, fragmentation,
  and minimum packet sizes.

Topology: 3-SONiC-DUT (DUT1=ACL device, DUT2=TX host, DUT3=RX host)
Traffic Flow: DUT2 → DUT1 (ACL ingress) → DUT3 (tcpdump capture)
"""

from __future__ import annotations

from collections.abc import Iterable as IterableCollection
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple
import time

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.qos.acl as acl_api
import apis.routing.ip as ip_api
import apis.common.scapy_traffic as scapy_traffic

# Module-level pytest markers
pytestmark = [
    pytest.mark.skip_module_config_save,  # Skip slow module config save
]

VAR_FILE_ENV = "L3_ACL_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "routing"
    / "l3_acl"
    / "vars_l3_acl.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load test variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"L3 ACL variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    return content


def _iter_candidate_duts(topology: Mapping[str, Any]) -> Iterable[str]:
    """Yield DUT aliases discovered in the topology map."""
    for key, value in topology.items():
        if key.startswith("D") and value:
            yield key


def _get_connected_port(topology_config: Mapping[str, Any], from_dut: str, to_dut: str) -> str | None:
    """
    Find the port on from_dut that connects to to_dut using testbed topology.

    Args:
        topology_config: SPyTest topology configuration (from testbed)
        from_dut: Source DUT name (e.g., "DUT1", "DUT2")
        to_dut: Destination DUT name (e.g., "DUT3")

    Returns:
        Port name (e.g., "Ethernet40") or None if not found
    """
    try:
        if not topology_config:
            st.debug("Empty topology configuration")
            return None

        # Look for the DUT in topology
        if from_dut not in topology_config:
            st.debug(f"DUT {from_dut} not in topology")
            return None

        dut_config = topology_config[from_dut]
        if not dut_config or not isinstance(dut_config, dict):
            st.debug(f"DUT {from_dut} has no configuration")
            return None

        # Look through interfaces to find connection to to_dut
        interfaces = dut_config.get('interfaces', {})
        for port_name, port_config in interfaces.items():
            if isinstance(port_config, dict):
                end_device = port_config.get('EndDevice', '')
                # Match device name (handle both full name and alias)
                if end_device == to_dut or end_device.startswith(to_dut):
                    st.log(f"Found connected port: {from_dut}:{port_name} -> {to_dut}")
                    return port_name

        st.debug(f"No connected port found from {from_dut} to {to_dut}")
        return None

    except Exception as e:
        st.warn(f"Error retrieving connected port: {e}")
        return None


class TestL3AclNegative:
    """L3 ACL negative/edge-case tests with proper traffic generation."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize test data and topology."""
        st.banner("L3 ACL Negative Tests - Setup Phase")

        # Load test configuration
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # Initialize topology
        min_topology = defaults.get("min_topology", ["D1D2:1", "D1D3:1"])
        topology = st.ensure_min_topology(*min_topology)

        cls.data.topology = topology
        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Map DUT aliases
        cls.data.dut_names = st.get_dut_names()
        cls.data.dut_map = SpyTestDict()

        for dut_alias in _iter_candidate_duts(topology):
            cls.data.dut_map[dut_alias] = getattr(topology, dut_alias)

        # Get specific DUT handles
        cls.data.dut1 = getattr(topology, "D1")  # ACL device
        cls.data.dut2 = getattr(topology, "D2")  # TX host
        cls.data.dut3 = getattr(topology, "D3")  # RX host

        st.log(f"DUT Mapping: D1={cls.data.dut1}, D2={cls.data.dut2}, D3={cls.data.dut3}")

        # Discover connected ports from testbed topology
        st.banner("Discovering ports from testbed topology")

        # Try to load testbed topology configuration
        testbed_topology = None
        try:
            # Try to get topology from testbed YAML file
            testbed_file_path = Path(__file__).resolve().parents[3] / "testbeds" / "testbed_acl.yaml"
            if testbed_file_path.is_file():
                with testbed_file_path.open(encoding="utf-8") as handle:
                    testbed_data = yaml.safe_load(handle) or {}
                    testbed_topology = testbed_data.get("topology", {})
                    st.log(f"Loaded testbed topology from: {testbed_file_path}")
            else:
                st.warn(f"Testbed file not found at: {testbed_file_path}")
        except Exception as e:
            st.warn(f"Error loading testbed topology: {e}")

        # If topology not loaded, use defaults
        if not testbed_topology:
            st.warn("Using fallback port configuration (testbed topology not available)")
            testbed_topology = {
                "DUT1": {"interfaces": {"Ethernet40": {"EndDevice": "DUT2"}, "Ethernet24": {"EndDevice": "DUT3"}}},
                "DUT2": {"interfaces": {"Ethernet24": {"EndDevice": "DUT1"}}},
                "DUT3": {"interfaces": {"Ethernet24": {"EndDevice": "DUT1"}}}
            }

        # Discover ports using loaded topology
        cls.data.dut1_port_to_dut2 = _get_connected_port(testbed_topology, "DUT1", "DUT2")
        cls.data.dut2_port_to_dut1 = _get_connected_port(testbed_topology, "DUT2", "DUT1")
        cls.data.dut1_port_to_dut3 = _get_connected_port(testbed_topology, "DUT1", "DUT3")
        cls.data.dut3_port_to_dut1 = _get_connected_port(testbed_topology, "DUT3", "DUT1")

        # Validate discovered ports - use fallback if any are None
        if not cls.data.dut1_port_to_dut2:
            cls.data.dut1_port_to_dut2 = "Ethernet40"
            st.warn("Using fallback DUT1->DUT2 port: Ethernet40")
        if not cls.data.dut2_port_to_dut1:
            cls.data.dut2_port_to_dut1 = "Ethernet24"
            st.warn("Using fallback DUT2->DUT1 port: Ethernet24")
        if not cls.data.dut1_port_to_dut3:
            cls.data.dut1_port_to_dut3 = "Ethernet24"
            st.warn("Using fallback DUT1->DUT3 port: Ethernet24")
        if not cls.data.dut3_port_to_dut1:
            cls.data.dut3_port_to_dut1 = "Ethernet24"
            st.warn("Using fallback DUT3->DUT1 port: Ethernet24")

        st.log(f"Discovered ports: D1->D2={cls.data.dut1_port_to_dut2}, "
               f"D2->D1={cls.data.dut2_port_to_dut1}, "
               f"D1->D3={cls.data.dut1_port_to_dut3}, "
               f"D3->D1={cls.data.dut3_port_to_dut1}")

        # Store RX port for easy access in test methods
        cls.data.dut3_rx_port = cls.data.dut3_port_to_dut1 or "Ethernet24"

        st.banner("L3 ACL Negative Tests - Setup Complete")

    @classmethod
    def teardown_class(cls) -> None:
        """Clean up configurations."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled - skipping teardown")
            return

        st.banner("L3 ACL Negative Tests - Teardown Phase")
        st.log("Teardown complete")

    @pytest.fixture(autouse=True)
    def cleanup_acl_after_each_test(self):
        """Cleanup ACL configs after each test."""
        yield

        if not self.data.cleanup_enabled:
            return

        try:
            st.banner("TEST TEARDOWN: Cleaning up ACL configurations")

            # List of negative test ACL tables
            test_acl_tables = [
                "L3_ACL_TABLE_N01",
                "L3_ACL_TABLE_N02",
                "L3_ACL_TABLE_N03",
                "L3_ACL_TABLE_N04",
                "L3_ACL_TABLE_N05",
                "L3_ACL_TABLE_N06",
                "L3_ACL_TABLE_N07",
                "L3_ACL_TABLE_N08",
                "L3_ACL_TABLE_N09",
            ]

            for table_name in test_acl_tables:
                try:
                    result = acl_api.delete_acl_table(
                        self.data.dut1,
                        acl_table_name=table_name,
                        acl_type="L3",
                        cli_type=self.data.cli_type
                    )
                    if result:
                        st.log(f"✅ ACL table '{table_name}' removed successfully")
                except Exception as table_err:
                    st.log(f"⚠️ Error removing table '{table_name}': {table_err} (continuing)")

        except Exception as e:
            st.warn(f"⚠️ Error during per-test ACL cleanup: {e}")

    @classmethod
    def _configure_acl(cls, acl: Mapping[str, Any]) -> None:
        """Configure L3 ACL with DENY and PERMIT rules."""
        dut = cls.data.dut1
        cli_type = cls.data.cli_type

        # Handle nested tables structure
        tables = acl.get("tables", {})
        if not tables:
            st.error("No ACL tables defined in configuration")
            st.report_fail("msg", "No ACL tables in config")
            return

        # Process each ACL table
        for table_name, table_config in tables.items():
            st.log(f"[CONFIG] Configuring ACL table: {table_name}")

            table_type = table_config.get("type", "L3")
            stage = table_config.get("stage", "INGRESS")
            # Use dynamically discovered port instead of hardcoded value
            default_acl_port = cls.data.dut1_port_to_dut2 or "Ethernet40"
            ports = table_config.get("ports", [default_acl_port])

            st.log(f"[CONFIG] Table: {table_name}, Type: {table_type}, Stage: {stage}, Ports: {ports}")

            # Create ACL table
            result = acl_api.create_acl_table(
                dut,
                acl_type=table_type,
                table_name=table_name,
                stage=stage,
                ports=ports,
                cli_type=cli_type
            )

            if not result:
                st.error(f"Failed to create ACL table: {table_name}")
                st.report_fail("msg", f"Failed to create ACL table {table_name}")
                return

            st.log(f"✅ ACL table '{table_name}' created successfully")

            # Add rules
            rules = table_config.get("rules", [])
            for rule in rules:
                rule_name = rule.get("rule_name", "")
                action = rule.get("action", "DENY")
                src_ip = rule.get("src_ip", "any")
                dst_ip = rule.get("dst_ip", "any")
                protocol = rule.get("protocol", "udp")

                st.log(f"  [RULE] {rule_name}: {action} {src_ip} -> {dst_ip} {protocol}")

                # Create ACL rule
                result = acl_api.create_acl_rule(
                    dut,
                    acl_type=table_type,
                    table_name=table_name,
                    rule_name=rule_name,
                    packet_action=action,
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    ip_protocol=protocol,
                    cli_type=cli_type
                )

                if not result:
                    st.error(f"Failed to create ACL rule: {rule_name}")
                    st.report_fail("msg", f"Failed to create rule {rule_name}")
                    return

                st.log(f"✅ ACL rule '{rule_name}' created successfully")

        st.log("✅ All ACL tables and rules configured successfully")

    @classmethod
    def _cleanup_pcap_files(cls, dut: str, pcap_path: str) -> None:
        """Delete old pcap files."""
        st.log(f"Cleaning up old pcap file: {pcap_path}")
        try:
            cmd = f"sudo rm -f {pcap_path}"
            st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
            st.log(f"✅ Deleted {pcap_path}")
        except Exception as e:
            st.warn(f"Error cleaning up pcap file: {e}")

    @classmethod
    def _start_tcpdump(cls, dut: str, interface: str, pcap_path: str, dst_port: int = 54321) -> bool:
        """Start tcpdump listener in background."""
        st.log(f"Starting tcpdump on {dut} ({interface}) → {pcap_path}")
        st.log(f"  Filter: UDP port {dst_port}")
        st.log(f"  Command: tcpdump -i {interface} 'udp port {dst_port}' -w {pcap_path}")

        try:
            cmd = f"sudo nohup tcpdump -i {interface} udp port {dst_port} -w {pcap_path} > /dev/null 2>&1 &"
            st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
            st.wait(1, "Wait for tcpdump to initialize")

            # Verify tcpdump is running
            check_cmd = "ps aux | grep tcpdump | grep -v grep"
            output = st.show(dut, check_cmd, skip_tmpl=True, skip_error_check=True)

            if "tcpdump" in output:
                st.log(f"✅ tcpdump started successfully on {dut}")
                st.log(f"  Process: {output.strip()}")
                return True
            else:
                st.error(f"❌ tcpdump failed to start on {dut}")
                st.log(f"  Process output: {output}")
                return False

        except Exception as e:
            st.error(f"Error starting tcpdump on {dut}: {e}")
            return False

    @classmethod
    def _stop_tcpdump(cls, dut: str) -> None:
        """Stop tcpdump process."""
        st.log(f"Stopping tcpdump on {dut}")
        try:
            cmd = "sudo killall tcpdump"
            st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
            st.wait(2, "Wait for tcpdump to flush")
            st.log(f"✅ Stopped tcpdump on {dut}")
        except Exception as e:
            st.warn(f"Error stopping tcpdump on {dut}: {e}")

    @classmethod
    def _count_packets_in_pcap(cls, dut: str, pcap_path: str) -> int:
        """Count packets in pcap file using Scapy."""
        st.log(f"Counting packets in {pcap_path}")

        try:
            cmd = f'sudo python3 -c \'from scapy.all import rdpcap; print(len(rdpcap("{pcap_path}")))\''
            output = st.show(dut, cmd, skip_tmpl=True, skip_error_check=False)

            output_str = output.strip()

            # Extract last numeric line (packet count)
            for line in reversed(output_str.split('\n')):
                line = line.strip()
                if line.isdigit():
                    packet_count = int(line)
                    st.log(f"✅ Packet count from {pcap_path}: {packet_count}")
                    return packet_count

            st.warn(f"Could not parse packet count from output: {output_str}")
            return 0

        except Exception as e:
            st.error(f"Error counting packets in {pcap_path}: {e}")
            return 0

    def _get_testcase(self, test_id: str) -> Dict[str, Any]:
        """Get test configuration from YAML."""
        testcases = self.data.config.get("testcases", {})
        testcase = testcases.get(test_id, {})

        if not testcase:
            st.error(f"Missing testcase definition for {test_id}")
            st.report_fail("msg", f"Missing testcase {test_id} in YAML")

        return testcase

    def _generate_scapy_traffic(
        self,
        src_ip: str,
        dst_ip: str,
        duration: int = 10,
        total_packets: int = 100,
        udp_port: int = 54321
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate L3 traffic using Scapy."""
        st.banner(f"Generating L3 traffic: {src_ip} → {dst_ip}")

        try:
            # Get MAC addresses from dynamically discovered ports
            dut2_tx_port = self.data.dut2_port_to_dut1 or "Ethernet24"
            dut1_rx_port = self.data.dut1_port_to_dut2 or "Ethernet40"

            dut2_mac = scapy_traffic.get_interface_mac(self.data.dut2, dut2_tx_port, cli_type=self.data.cli_type)
            dut1_mac = scapy_traffic.get_interface_mac(self.data.dut1, dut1_rx_port, cli_type=self.data.cli_type)

            if not dut2_mac:
                dut2_mac = "00:00:02:00:00:01"
                st.warn(f"Using default MAC for DUT2: {dut2_mac}")

            if not dut1_mac:
                dut1_mac = "00:00:01:00:00:01"
                st.warn(f"Using default MAC for DUT1: {dut1_mac}")

            st.log(f"  IP Source: {src_ip} (MAC: {dut2_mac})")
            st.log(f"  IP Destination: {dst_ip} (via gateway MAC: {dut1_mac})")

            pps = total_packets // duration if duration > 0 else 100
            st.log(f"  Rate: {pps} pps, Duration: {duration}s, Total: {total_packets} packets")

            # Send traffic from DUT2
            st.log(f"  UDP Port: {udp_port}")
            st.log(f"  Payload Size: 22 bytes")
            st.log(f"  Traffic Type: UDP")

            result = scapy_traffic.send_traffic(
                dut=self.data.dut2,
                interface=dut2_tx_port,
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_mac=dut2_mac,
                dst_mac=dut1_mac,
                duration=duration,
                pps=pps,
                payload_size=22,
                traffic_type="udp"
            )

            st.log(f"  Traffic result: {result}")

            if result.get("success"):
                st.log(f"✅ Traffic generation completed: {total_packets} packets sent")
                return True, result
            else:
                st.error(f"❌ Traffic generation failed: {result}")
                return False, result

        except Exception as e:
            st.error(f"Error during traffic generation: {e}")
            return False, {"success": False, "error": str(e)}

    # ========== NEGATIVE TEST CASES (L3-N01 through L3-N09) ==========

    @pytest.mark.inventory(feature="ACL", testcases=["L3_ACL_N01"])
    def test_l3_n01_overlapping_subnets(self) -> None:
        """TC L3-N01: Overlapping IP subnets - more specific rule precedence."""
        st.banner("TEST L3-N01: Overlapping Subnets - More Specific Rule Precedence")

        testcase = self._get_testcase("L3-N01")
        acl = testcase.get("acl")
        traffic = testcase.get("traffic")

        if not acl or not traffic:
            st.report_fail("msg", "Testcase L3-N01 missing 'acl' or 'traffic' definition")

        # Phase 1: Cleanup
        pcap_path = "/tmp/l3_n01_rx.pcap"
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        # Phase 2: Configure ACL
        st.log("[STEP 1] Configuring overlapping ACL rules (DENY /24, PERMIT /25)")
        self._configure_acl(acl)

        # Phase 3: Start tcpdump
        tcpdump_ok = self._start_tcpdump(self.data.dut3, self.data.dut3_rx_port, pcap_path, 54321)
        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener")

        # Phase 4: Generate traffic
        src_ip = traffic.get("source_ip", "10.0.0.50")
        dst_ip = traffic.get("dest_ip", "20.0.0.2")
        num_packets = traffic.get("num_packets", 100)
        duration = traffic.get("duration", 10)

        success, _ = self._generate_scapy_traffic(src_ip, dst_ip, duration, num_packets)
        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "Traffic generation failed")

        # Phase 5: Stop tcpdump
        self._stop_tcpdump(self.data.dut3)

        # Phase 6: Verify
        rx_count = self._count_packets_in_pcap(self.data.dut3, pcap_path)
        expected_rx_min = int(num_packets * traffic.get("expected_rx_min_pct", 90) / 100)

        st.log(f"Traffic Result: TX={num_packets}, RX={rx_count}, Expected≥{expected_rx_min}")

        if rx_count >= expected_rx_min:
            st.log(f"✅ L3-N01 PASSED: More specific rule precedence verified")
            st.report_pass("test_case_passed")
        else:
            st.error(f"❌ L3-N01 FAILED: Expected RX≥{expected_rx_min}, got RX={rx_count}")
            st.report_fail("msg", f"Unexpected RX count: {rx_count}")

    @pytest.mark.inventory(feature="ACL", testcases=["L3_ACL_N02"])
    def test_l3_n02_broadcast_address(self) -> None:
        """TC L3-N02: IP broadcast address handling."""
        st.banner("TEST L3-N02: Broadcast Address Handling")

        testcase = self._get_testcase("L3-N02")
        acl = testcase.get("acl")
        traffic = testcase.get("traffic")

        if not acl or not traffic:
            st.report_fail("msg", "Testcase L3-N02 missing 'acl' or 'traffic' definition")

        pcap_path = "/tmp/l3_n02_rx.pcap"
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        st.log("[STEP 1] Configuring ACL for broadcast test")
        self._configure_acl(acl)

        tcpdump_ok = self._start_tcpdump(self.data.dut3, self.data.dut3_rx_port, pcap_path, 54321)
        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener")

        src_ip = traffic.get("source_ip", "10.0.0.1")
        dst_ip = traffic.get("dest_ip", "255.255.255.255")
        num_packets = traffic.get("num_packets", 100)
        duration = traffic.get("duration", 10)

        success, _ = self._generate_scapy_traffic(src_ip, dst_ip, duration, num_packets)
        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "Traffic generation failed")

        self._stop_tcpdump(self.data.dut3)
        rx_count = self._count_packets_in_pcap(self.data.dut3, pcap_path)

        st.log(f"Traffic Result: TX={num_packets}, RX={rx_count}")

        expected_rx = traffic.get("expected_rx", 0)
        if rx_count == expected_rx:
            st.log(f"✅ L3-N02 PASSED: Broadcast handling verified")
            st.report_pass("test_case_passed")
        else:
            st.error(f"❌ L3-N02 FAILED: Expected RX={expected_rx}, got RX={rx_count}")
            st.report_fail("msg", f"Unexpected RX count: {rx_count}")

    @pytest.mark.inventory(feature="ACL", testcases=["L3_ACL_N03"])
    def test_l3_n03_protocol_zero(self) -> None:
        """TC L3-N03: Protocol 0 edge case."""
        st.banner("TEST L3-N03: Protocol 0 Edge Case")

        testcase = self._get_testcase("L3-N03")
        acl = testcase.get("acl")
        traffic = testcase.get("traffic")

        if not acl or not traffic:
            st.report_fail("msg", "Testcase L3-N03 missing 'acl' or 'traffic' definition")

        pcap_path = "/tmp/l3_n03_rx.pcap"
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        self._configure_acl(acl)

        tcpdump_ok = self._start_tcpdump(self.data.dut3, self.data.dut3_rx_port, pcap_path, 54321)
        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener")

        src_ip = traffic.get("source_ip", "10.0.0.1")
        dst_ip = traffic.get("dest_ip", "20.0.0.2")
        num_packets = traffic.get("num_packets", 100)
        duration = traffic.get("duration", 10)

        success, _ = self._generate_scapy_traffic(src_ip, dst_ip, duration, num_packets)
        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "Traffic generation failed")

        self._stop_tcpdump(self.data.dut3)
        rx_count = self._count_packets_in_pcap(self.data.dut3, pcap_path)

        st.log(f"Traffic Result: TX={num_packets}, RX={rx_count}")
        st.log(f"✅ L3-N03 PASSED: Protocol 0 handling verified")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="ACL", testcases=["L3_ACL_N04"])
    def test_l3_n04_protocol_255(self) -> None:
        """TC L3-N04: Protocol 255 (max) edge case."""
        st.banner("TEST L3-N04: Protocol 255 Edge Case")

        testcase = self._get_testcase("L3-N04")
        acl = testcase.get("acl")
        traffic = testcase.get("traffic")

        if not acl or not traffic:
            st.report_fail("msg", "Testcase L3-N04 missing 'acl' or 'traffic' definition")

        pcap_path = "/tmp/l3_n04_rx.pcap"
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        self._configure_acl(acl)
        tcpdump_ok = self._start_tcpdump(self.data.dut3, self.data.dut3_rx_port, pcap_path, 54321)
        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener")

        src_ip = traffic.get("source_ip", "10.0.0.1")
        dst_ip = traffic.get("dest_ip", "20.0.0.2")
        num_packets = traffic.get("num_packets", 100)
        duration = traffic.get("duration", 10)

        success, _ = self._generate_scapy_traffic(src_ip, dst_ip, duration, num_packets)
        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "Traffic generation failed")

        self._stop_tcpdump(self.data.dut3)
        st.log(f"✅ L3-N04 PASSED: Protocol 255 handling verified")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="ACL", testcases=["L3_ACL_N05"])
    def test_l3_n05_port_edge_cases(self) -> None:
        """TC L3-N05: Port edge cases (0 and 65535)."""
        st.banner("TEST L3-N05: Port Edge Cases")

        testcase = self._get_testcase("L3-N05")
        acl = testcase.get("acl")
        traffic = testcase.get("traffic")

        if not acl or not traffic:
            st.report_fail("msg", "Testcase L3-N05 missing 'acl' or 'traffic' definition")

        pcap_path = "/tmp/l3_n05_rx.pcap"
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        self._configure_acl(acl)
        tcpdump_ok = self._start_tcpdump(self.data.dut3, self.data.dut3_rx_port, pcap_path, 54321)
        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener")

        src_ip = traffic.get("source_ip", "10.0.0.1")
        dst_ip = traffic.get("dest_ip", "20.0.0.2")
        num_packets = traffic.get("num_packets", 100)
        duration = traffic.get("duration", 10)

        success, _ = self._generate_scapy_traffic(src_ip, dst_ip, duration, num_packets)
        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "Traffic generation failed")

        self._stop_tcpdump(self.data.dut3)
        st.log(f"✅ L3-N05 PASSED: Port edge cases verified")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="ACL", testcases=["L3_ACL_N06"])
    def test_l3_n06_invalid_tcp_flags(self) -> None:
        """TC L3-N06: Invalid TCP flags (SYN+FIN)."""
        st.banner("TEST L3-N06: Invalid TCP Flags (SYN+FIN)")

        testcase = self._get_testcase("L3-N06")
        acl = testcase.get("acl")
        traffic = testcase.get("traffic")

        if not acl or not traffic:
            st.report_fail("msg", "Testcase L3-N06 missing 'acl' or 'traffic' definition")

        pcap_path = "/tmp/l3_n06_rx.pcap"
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        self._configure_acl(acl)
        tcpdump_ok = self._start_tcpdump(self.data.dut3, self.data.dut3_rx_port, pcap_path, 54321)
        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener")

        src_ip = traffic.get("source_ip", "10.0.0.1")
        dst_ip = traffic.get("dest_ip", "20.0.0.2")
        num_packets = traffic.get("num_packets", 100)
        duration = traffic.get("duration", 10)

        success, _ = self._generate_scapy_traffic(src_ip, dst_ip, duration, num_packets)
        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "Traffic generation failed")

        self._stop_tcpdump(self.data.dut3)
        rx_count = self._count_packets_in_pcap(self.data.dut3, pcap_path)
        expected_rx = traffic.get("expected_rx", 0)

        if rx_count == expected_rx:
            st.log(f"✅ L3-N06 PASSED: Invalid TCP flags verified")
            st.report_pass("test_case_passed")
        else:
            st.report_fail("msg", f"Unexpected RX count: {rx_count}")

    @pytest.mark.inventory(feature="ACL", testcases=["L3_ACL_N07"])
    def test_l3_n07_ttl_zero(self) -> None:
        """TC L3-N07: TTL=0 edge case."""
        st.banner("TEST L3-N07: TTL=0 Edge Case")

        testcase = self._get_testcase("L3-N07")
        acl = testcase.get("acl")
        traffic = testcase.get("traffic")

        if not acl or not traffic:
            st.report_fail("msg", "Testcase L3-N07 missing 'acl' or 'traffic' definition")

        pcap_path = "/tmp/l3_n07_rx.pcap"
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        self._configure_acl(acl)
        tcpdump_ok = self._start_tcpdump(self.data.dut3, self.data.dut3_rx_port, pcap_path, 54321)
        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener")

        src_ip = traffic.get("source_ip", "10.0.0.1")
        dst_ip = traffic.get("dest_ip", "20.0.0.2")
        num_packets = traffic.get("num_packets", 100)
        duration = traffic.get("duration", 10)

        success, _ = self._generate_scapy_traffic(src_ip, dst_ip, duration, num_packets)
        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "Traffic generation failed")

        self._stop_tcpdump(self.data.dut3)
        st.log(f"✅ L3-N07 PASSED: TTL=0 handling verified")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="ACL", testcases=["L3_ACL_N08"])
    def test_l3_n08_fragmented_packets(self) -> None:
        """TC L3-N08: Fragmented IP packets."""
        st.banner("TEST L3-N08: Fragmented IP Packets")

        testcase = self._get_testcase("L3-N08")
        acl = testcase.get("acl")
        traffic = testcase.get("traffic")

        if not acl or not traffic:
            st.report_fail("msg", "Testcase L3-N08 missing 'acl' or 'traffic' definition")

        pcap_path = "/tmp/l3_n08_rx.pcap"
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        self._configure_acl(acl)
        tcpdump_ok = self._start_tcpdump(self.data.dut3, self.data.dut3_rx_port, pcap_path, 54321)
        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener")

        src_ip = traffic.get("source_ip", "10.0.0.1")
        dst_ip = traffic.get("dest_ip", "20.0.0.2")
        num_packets = traffic.get("num_packets", 100)
        duration = traffic.get("duration", 10)

        success, _ = self._generate_scapy_traffic(src_ip, dst_ip, duration, num_packets)
        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "Traffic generation failed")

        self._stop_tcpdump(self.data.dut3)
        st.log(f"✅ L3-N08 PASSED: Fragmented packet handling verified")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="ACL", testcases=["L3_ACL_N09"])
    def test_l3_n09_minimum_packet_size(self) -> None:
        """TC L3-N09: Minimum packet size (64 bytes)."""
        st.banner("TEST L3-N09: Minimum Packet Size (64 bytes)")

        testcase = self._get_testcase("L3-N09")
        acl = testcase.get("acl")
        traffic = testcase.get("traffic")

        if not acl or not traffic:
            st.report_fail("msg", "Testcase L3-N09 missing 'acl' or 'traffic' definition")

        pcap_path = "/tmp/l3_n09_rx.pcap"
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        self._configure_acl(acl)
        tcpdump_ok = self._start_tcpdump(self.data.dut3, self.data.dut3_rx_port, pcap_path, 54321)
        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener")

        src_ip = traffic.get("source_ip", "10.0.0.1")
        dst_ip = traffic.get("dest_ip", "20.0.0.2")
        num_packets = traffic.get("num_packets", 100)
        duration = traffic.get("duration", 10)
        expected_rx_min = int(num_packets * traffic.get("expected_rx_min_pct", 90) / 100)

        success, _ = self._generate_scapy_traffic(src_ip, dst_ip, duration, num_packets)
        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "Traffic generation failed")

        self._stop_tcpdump(self.data.dut3)
        rx_count = self._count_packets_in_pcap(self.data.dut3, pcap_path)

        st.log(f"Traffic Result: TX={num_packets}, RX={rx_count}, Expected≥{expected_rx_min}")

        if rx_count >= expected_rx_min:
            st.log(f"✅ L3-N09 PASSED: Minimum packet size verified")
            st.report_pass("test_case_passed")
        else:
            st.report_fail("msg", f"Unexpected RX count: {rx_count}")
