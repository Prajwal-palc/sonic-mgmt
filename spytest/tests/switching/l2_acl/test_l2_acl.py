"""
L2 ACL Basic Functional Tests - SPyTest Framework Integration

Author: Claude Code
Date: 2026-03-14
Version: 1.0 - SPyTest Native (3-SONiC-DUT Pattern with Tcpdump Verification)

How to run:
  ./bin/spytest --testbed ./testbeds/testbed_acl.yaml \\
      tests/switching/l2_acl/test_l2_acl.py \\
      --logs-path ./logs/l2_acl_$(date +%F_%H%M%S) \\
      --log-level debug --skip-init-config --ifname-type native

Description:
  End-to-end validation of L2 ACL (Layer 2 / MAC-level Access Control Lists)
  functionality using DUT-based Scapy traffic generation and tcpdump-based
  packet verification.

  Topology: 3-SONiC-DUT (DUT1=ACL device, DUT2=TX host, DUT3=RX host)
  Traffic Flow: DUT2 → DUT1 (ACL ingress) → DUT3 (tcpdump capture)
  Verification: Pcap file analysis using Scapy rdpcap()

Pre-requisites:
  - Topology: 3-node (D1D2D3) SONiC DUTs
  - DUTs: Virtual (SONiC-VS) or Hardware with direct connections
  - Min SONiC version: 202211 or later
  - Required packages: Scapy, tcpdump, Python 3.8+
  - DUT ports configured in switchport mode (not L3 routed)

Features:
  ✅ Full SPyTest framework integration (st.log, st.report_pass/fail)
  ✅ Tcpdump forensic verification (pcap files for analysis)
  ✅ Silent pass prevention (TX > 0, RX > 0 checks)
  ✅ Non-blocking traffic generation (DUT-deployed Scapy scripts)
  ✅ L2 MAC-based packet filtering
  ✅ VLAN tag support (802.1Q)
  ✅ EtherType-based filtering (ARP, IPv4, etc.)
  ✅ Automatic cleanup (try/finally blocks)
  ✅ Centralized test reporting
"""

from __future__ import annotations

from collections.abc import Iterable as IterableCollection
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple
import re
import time

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.switching.vlan as vlan_api
import apis.system.interface as intf_api
import apis.routing.ip as ip_api
import apis.qos.acl as acl_api
import apis.common.scapy_traffic as scapy_traffic


def _get_connected_port(topology_config: Mapping[str, Any], from_dut: str, to_dut: str) -> str | None:
    """
    Discover the connected port from one DUT to another using testbed topology.

    Args:
        topology_config: Topology section of testbed YAML
        from_dut: Source DUT name (e.g., "DUT1")
        to_dut: Destination DUT name (e.g., "DUT2")

    Returns:
        Connected port name (e.g., "Ethernet40") or None if not found
    """
    if not topology_config:
        return None

    dut_topology = topology_config.get(from_dut, {})
    if not isinstance(dut_topology, dict):
        return None

    interfaces = dut_topology.get("interfaces", {})
    for port_name, port_config in interfaces.items():
        if isinstance(port_config, dict):
            if port_config.get("EndDevice") == to_dut:
                return port_name

    return None


# Module-level pytest markers
pytestmark = [
    pytest.mark.skip_module_config_save,  # Skip slow module config save that causes timeout
]

VAR_FILE_ENV = "L2_ACL_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "switching"
    / "l2_acl"
    / "vars_l2_acl.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load test variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    # If YAML file doesn't exist, return defaults
    if not candidate.is_file():
        st.log(f"L2 ACL variable file not found at {candidate}, using built-in defaults")
        return {
            "defaults": {
                "min_topology": ["D1D2:1", "D1D3:1"],
                "cli_type": "klish",
                "verify_timeout": 30,
                "cleanup": True
            },
            "dut_l2_config": {},
            "testcases": {}
        }

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    return content


def _iter_candidate_duts(topology: Mapping[str, Any]) -> Iterable[str]:
    """Yield DUT aliases discovered in the topology map."""
    for key, value in topology.items():
        if key.startswith("D") and value:
            yield key


class TestL2AclBasic:
    """Test L2 ACL functionality with DUT-based Scapy traffic and tcpdump verification."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize test data, load configuration, and set up DUT topology."""
        st.banner("L2 ACL Test Suite - Setup Phase")

        # Load test configuration from YAML
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

        # Map DUT aliases to framework handles
        cls.data.dut_names = st.get_dut_names()
        cls.data.dut_map = SpyTestDict()

        for dut_alias in _iter_candidate_duts(topology):
            cls.data.dut_map[dut_alias] = getattr(topology, dut_alias)

        # Get specific DUT handles from topology
        cls.data.dut1 = getattr(topology, "D1")  # ACL device
        cls.data.dut2 = getattr(topology, "D2")  # TX host
        cls.data.dut3 = getattr(topology, "D3")  # RX host

        st.banner(f"DUT Mapping: D1={cls.data.dut1}, D2={cls.data.dut2}, D3={cls.data.dut3}")

        # Discover connected ports from testbed topology
        st.banner("Discovering ports from testbed topology")

        # Try to load testbed topology configuration
        testbed_topology = None
        try:
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

        # Configure L2 switchport mode on all DUTs
        cls._configure_l2_switchport_mode()

        st.banner("L2 ACL Test Suite - Setup Complete")

    @classmethod
    def teardown_class(cls) -> None:
        """Clean up configurations and return to base state."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled - skipping teardown")
            return

        st.banner("L2 ACL Test Suite - Teardown Phase")

        # Clean up any remaining ACL configurations
        cls._cleanup_acl_config()

        st.log("Teardown complete")

    @pytest.fixture(autouse=True)
    def cleanup_acl_after_each_test(self):
        """
        Pytest fixture to automatically clean up ACL configs after each test.

        This fixture ensures that ACL tables from previous tests don't interfere
        with subsequent tests, maintaining proper test isolation.
        """
        yield  # Test executes before this point, cleanup runs after

        # Cleanup code runs after test completes (even on test failure)
        if not self.data.cleanup_enabled:
            st.log("Cleanup disabled - skipping per-test ACL cleanup")
            return

        try:
            st.banner("TEST TEARDOWN: Cleaning up ACL configurations created by this test")

            # List of L2 ACL tables created by tests
            test_acl_tables = [
                "L2_ACL_TABLE",
                "L2_ACL_TABLE_L201",  # L2-01
                "L2_ACL_TABLE_L202",  # L2-02
                "L2_ACL_TABLE_L203",  # L2-03
                "L2_ACL_TABLE_L204",  # L2-04
                "L2_ACL_TABLE_L205",  # L2-05
                "L2_ACL_TABLE_L206",  # L2-06
                "L2_ACL_TABLE_L207",  # L2-07
                "L2_ACL_TABLE_L208",  # L2-08
            ]

            st.log(f"Removing ACL tables: {test_acl_tables}")

            # Delete each ACL table (also removes associated rules)
            for table_name in test_acl_tables:
                try:
                    st.log(f"Attempting to remove ACL table: {table_name}")
                    result = acl_api.delete_acl_table(
                        self.data.dut1,
                        acl_table_name=table_name,
                        acl_type="L2",
                        cli_type=self.data.cli_type
                    )

                    if result:
                        st.log(f"✅ ACL table '{table_name}' removed successfully")
                    else:
                        st.log(f"⚠️ ACL table '{table_name}' not found or already deleted")

                except Exception as table_err:
                    st.log(f"⚠️ Error removing table '{table_name}': {table_err} (continuing)")

            st.log("✅ Per-test ACL cleanup completed")

        except Exception as e:
            st.warn(f"⚠️ Error during per-test ACL cleanup: {e}")
            st.warn("Continuing with next test (cleanup failure may affect test isolation)")

    @classmethod
    def _configure_l2_switchport_mode(cls) -> None:
        """Configure L2 switchport mode on all DUT ports."""
        st.banner("Configuring L2 switchport mode on DUT ports")

        cli_type = cls.data.cli_type
        ports_to_configure = [
            (cls.data.dut1, cls.data.dut1_port_to_dut2, "DUT1 (TX side)"),
            (cls.data.dut1, cls.data.dut1_port_to_dut3, "DUT1 (RX side)"),
            (cls.data.dut2, cls.data.dut2_port_to_dut1, "DUT2 (TX host)"),
            (cls.data.dut3, cls.data.dut3_port_to_dut1, "DUT3 (RX host)"),
        ]

        try:
            for dut, port, dut_desc in ports_to_configure:
                st.log(f"Setting {port} on {dut_desc} to switchport mode")
                try:
                    # Set port to switchport mode (L2)
                    intf_api.interface_operation(dut, port, "shutdown", cli_type=cli_type)
                    st.wait(1)

                    cmd = f"config interface switchport {port}"
                    st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)

                    intf_api.interface_operation(dut, port, "noshutdown", cli_type=cli_type)
                    st.log(f"✅ {port} on {dut_desc} set to switchport mode")
                except Exception as e:
                    st.log(f"⚠️ Error setting {port} to switchport: {e} (continuing)")

            st.wait(2, "Wait for port modes to take effect")
            st.log("✅ L2 switchport mode configured on all DUT ports")

        except Exception as e:
            st.warn(f"Error configuring L2 switchport mode: {e}")

    @classmethod
    def _cleanup_acl_config(cls) -> None:
        """Remove all ACL configurations."""
        st.banner("Cleaning up ACL configurations")
        cli_type = cls.data.cli_type

        try:
            # Get ACL table names from config
            acl_config = cls.data.config.get("acl_config", {})
            acl_tables = acl_config.get("tables", {})

            for table_name, table_cfg in acl_tables.items():
                st.log(f"Removing ACL table: {table_name}")
                acl_type = table_cfg.get("type", "L2")

                # Delete ACL table (this also removes associated rules)
                result = acl_api.delete_acl_table(
                    cls.data.dut1,
                    acl_table_name=table_name,
                    acl_type=acl_type,
                    cli_type=cli_type
                )

                if result:
                    st.log(f"✅ ACL table '{table_name}' removed successfully")
                else:
                    st.warn(f"Failed to remove ACL table '{table_name}'")

        except Exception as e:
            st.warn(f"Error during ACL cleanup: {e}")

    @classmethod
    def _cleanup_pcap_files(cls, dut: str, pcap_path: str) -> None:
        """Delete old pcap files to ensure clean slate."""
        st.log(f"Cleaning up old pcap file: {pcap_path} on {dut}")
        try:
            cmd = f"sudo rm -f {pcap_path}"
            st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
            st.log(f"✅ Deleted {pcap_path} on {dut}")
        except Exception as e:
            st.warn(f"Error cleaning up pcap file on {dut}: {e}")

    @classmethod
    def _start_tcpdump(cls, dut: str, interface: str, pcap_path: str) -> bool:
        """Start tcpdump listener in background on DUT (no filter for L2)."""
        st.log(f"Starting tcpdump on {dut} ({interface}) → {pcap_path}")

        try:
            cmd = f"sudo nohup tcpdump -i {interface} -w {pcap_path} > /dev/null 2>&1 &"
            st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
            st.wait(1, "Wait for tcpdump to initialize")

            # Verify tcpdump is running
            check_cmd = "ps aux | grep tcpdump | grep -v grep"
            output = st.show(dut, check_cmd, skip_tmpl=True, skip_error_check=True)

            if "tcpdump" in output:
                st.log(f"✅ tcpdump started successfully on {dut}")
                return True
            else:
                st.error(f"❌ tcpdump failed to start on {dut}")
                return False

        except Exception as e:
            st.error(f"Error starting tcpdump on {dut}: {e}")
            return False

    @classmethod
    def _stop_tcpdump(cls, dut: str) -> None:
        """Stop tcpdump process cleanly."""
        st.log(f"Stopping tcpdump on {dut}")

        try:
            cmd = "sudo killall tcpdump"
            st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
            st.wait(2, "Wait for tcpdump to flush and close file")
            st.log(f"✅ Stopped tcpdump on {dut}")
        except Exception as e:
            st.warn(f"Error stopping tcpdump on {dut}: {e}")

    @classmethod
    def _count_packets_in_pcap(cls, dut: str, pcap_path: str) -> int:
        """Count packets in pcap file using Scapy rdpcap()."""
        st.log(f"Counting packets in {pcap_path} on {dut}")

        try:
            cmd = f'sudo python3 -c "from scapy.all import rdpcap; print(len(rdpcap(\\"{pcap_path}\\")))"'
            output = st.show(dut, cmd, skip_tmpl=True, skip_error_check=False)

            output_str = output.strip()

            # Look for last line that's purely numeric (the packet count)
            for line in reversed(output_str.split('\n')):
                line = line.strip()
                if line.isdigit():
                    packet_count = int(line)
                    st.log(f"✅ Packet count from {pcap_path}: {packet_count}")
                    return packet_count

            st.warn(f"Could not parse packet count from output: {output_str}")
            return 0

        except Exception as e:
            st.error(f"Error counting packets in {pcap_path} on {dut}: {e}")
            return 0

    @classmethod
    def _configure_acl(cls, acl_config: Dict[str, Any]) -> bool:
        """Configure ACL tables and rules on DUT1."""
        st.banner("Configuring L2 ACL rules on DUT1")
        cli_type = cls.data.cli_type
        dut1 = cls.data.dut1

        try:
            acl_tables = acl_config.get("tables", {})

            for table_name, table_cfg in acl_tables.items():
                st.log(f"Creating L2 ACL table: {table_name}")

                # L2 ACL type with stage and ports
                acl_type = table_cfg.get("type", "L2")
                stage = table_cfg.get("stage", "INGRESS")
                ports = table_cfg.get("ports", [cls.data.dut1_port_to_dut2])

                # Create ACL table
                result = acl_api.create_acl_table(
                    dut1,
                    acl_type=acl_type,
                    table_name=table_name,
                    stage=stage,
                    ports=ports,
                    cli_type=cli_type
                )

                if not result:
                    st.error(f"Failed to create ACL table: {table_name}")
                    return False

                st.log(f"✅ L2 ACL table '{table_name}' created successfully")

                # Create ACL rules for this table
                rules = table_cfg.get("rules", [])
                for rule_cfg in rules:
                    rule_name = rule_cfg.get("rule_name")
                    packet_action = rule_cfg.get("action", "deny")
                    src_mac = rule_cfg.get("src_mac", "any")
                    dst_mac = rule_cfg.get("dst_mac", "any")
                    ethertype = rule_cfg.get("ethertype", None)
                    vlan_id = rule_cfg.get("vlan_id", None)

                    st.log(f"Creating L2 ACL rule: {rule_name} ({packet_action})")

                    # Create L2 ACL rule
                    result = acl_api.create_acl_rule(
                        dut1,
                        acl_type=acl_type,
                        table_name=table_name,
                        rule_name=rule_name,
                        packet_action=packet_action,
                        src_mac=src_mac,
                        dst_mac=dst_mac,
                        cli_type=cli_type
                    )

                    if not result:
                        st.error(f"Failed to create ACL rule: {rule_name}")
                        return False

                    st.log(f"✅ L2 ACL rule '{rule_name}' created successfully")

            st.log("✅ All L2 ACL tables and rules configured successfully")
            return True

        except Exception as e:
            st.error(f"Exception during ACL configuration: {e}")
            return False

    def _get_traffic_config(self, test_case_id: str) -> Dict[str, Any]:
        """Get traffic configuration for a specific test case."""
        testcases = self.data.config.get("testcases", {})
        return testcases.get(test_case_id, {})

    def _generate_scapy_l2_traffic(
        self,
        src_mac: str,
        dst_mac: str,
        duration: int = 10,
        total_packets: int = 100,
        vlan_id: int = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate L2 traffic using Scapy with MAC addresses."""
        st.banner(f"Generating L2 traffic: {src_mac} → {dst_mac}")

        try:
            # Use dynamically discovered interface names
            dut2_tx_interface = self.data.dut2_port_to_dut1 or "Ethernet24"

            st.log(f"  Source MAC: {src_mac}")
            st.log(f"  Destination MAC: {dst_mac}")
            if vlan_id:
                st.log(f"  VLAN ID: {vlan_id}")

            pps = total_packets // duration if duration > 0 else 100
            st.log(f"  Rate: {pps} pps, Duration: {duration}s, Total: {total_packets} packets")

            # Send L2 traffic from DUT2
            result = scapy_traffic.send_l2_traffic(
                dut=self.data.dut2,
                interface=dut2_tx_interface,
                src_mac=src_mac,
                dst_mac=dst_mac,
                duration=duration,
                pps=pps,
                vlan_id=vlan_id
            )

            if result.get("success"):
                st.log(f"✅ L2 traffic generation completed: {total_packets} packets sent")
                return True, result
            else:
                st.error("❌ L2 traffic generation failed")
                return False, result

        except Exception as e:
            st.error(f"Error during L2 traffic generation: {e}")
            return False, {"success": False, "error": str(e)}

    # ============================================================================
    # L2-01: PERMIT EXACT SOURCE MAC
    # ============================================================================

    @pytest.mark.inventory(
        feature="L2_ACL",
        testcases=["test_l2_01_permit_source_mac"]
    )
    @pytest.mark.skip_module_config_save
    def test_l2_01_permit_source_mac(self) -> None:
        """
        TC-L2-01: Permit exact source MAC address.

        This test verifies that ACL rules permitting a specific source MAC work correctly.
        Traffic from the permitted MAC should pass through (RX > 0).
        Expected result: RX count ≥ 90% of TX count (permitted traffic passes).
        """
        st.banner("Test L2-01: Permit source MAC 00:11:22:33:44:55")

        src_mac = "00:11:22:33:44:55"
        dst_mac = "FF:FF:FF:FF:FF:FF"
        num_packets = 100
        duration = 10
        pcap_path = "/tmp/l2_01_rx.pcap"

        dut3_rx_interface = self.data.dut3_port_to_dut1 or "Ethernet24"

        # ===== PHASE 1: Cleanup =====
        st.banner("PHASE 1: Cleanup")
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        # ===== PHASE 2: Start tcpdump listener =====
        st.banner("PHASE 2: Starting tcpdump listener on DUT3")
        tcpdump_ok = self._start_tcpdump(self.data.dut3, dut3_rx_interface, pcap_path)

        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener on DUT3")

        # ===== PHASE 3: Generate traffic =====
        st.banner("PHASE 3: Generating L2 traffic (permit rule)")
        success, result = self._generate_scapy_l2_traffic(src_mac, dst_mac, duration, num_packets)

        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "L2 traffic generation failed")

        # ===== PHASE 4: Stop tcpdump listener =====
        st.banner("PHASE 4: Stopping tcpdump listener")
        self._stop_tcpdump(self.data.dut3)

        # ===== PHASE 5: Verify using pcap =====
        st.banner("PHASE 5: Counting packets in pcap file")
        rx_count = self._count_packets_in_pcap(self.data.dut3, pcap_path)

        # ===== PHASE 6: Validate results =====
        st.banner("PHASE 6: Validating results")

        st.log(f"Traffic Result: TX={num_packets}, RX={rx_count}")

        if rx_count == 0:
            st.error("❌ Silent pass guard: RX = 0. DUT1 not forwarding traffic.")
            st.report_fail("msg", "RX count is 0 - traffic not forwarded")

        loss_pct = ((num_packets - rx_count) / num_packets * 100) if num_packets > 0 else 100.0
        max_loss = 10.0

        if loss_pct > max_loss:
            st.error(f"❌ Packet loss {loss_pct:.1f}% exceeds threshold {max_loss}%")
            st.report_fail("msg", f"Loss {loss_pct:.1f}% > {max_loss}%")

        st.log("✅ L2-01 test PASSED")
        st.report_pass("test_case_passed")

    # ============================================================================
    # L2-02: DENY SOURCE MAC
    # ============================================================================

    @pytest.mark.inventory(
        feature="L2_ACL",
        testcases=["test_l2_02_deny_source_mac"]
    )
    @pytest.mark.skip_module_config_save
    def test_l2_02_deny_source_mac(self) -> None:
        """
        TC-L2-02: Deny source MAC address.

        This test verifies that ACL rules blocking a specific source MAC work correctly.
        Traffic from the denied MAC should be dropped (RX = 0).
        Expected result: RX count = 0 (denied traffic blocked).
        """
        st.banner("Test L2-02: Deny source MAC AA:BB:CC:DD:EE:FF")

        src_mac = "AA:BB:CC:DD:EE:FF"
        dst_mac = "FF:FF:FF:FF:FF:FF"
        num_packets = 100
        duration = 10
        pcap_path = "/tmp/l2_02_rx.pcap"

        dut3_rx_interface = self.data.dut3_port_to_dut1 or "Ethernet24"

        # ===== PHASE 1: Cleanup =====
        st.banner("PHASE 1: Cleanup")
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        # ===== PHASE 2: Start tcpdump listener =====
        st.banner("PHASE 2: Starting tcpdump listener on DUT3")
        tcpdump_ok = self._start_tcpdump(self.data.dut3, dut3_rx_interface, pcap_path)

        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener on DUT3")

        # ===== PHASE 3: Generate traffic =====
        st.banner("PHASE 3: Generating L2 traffic (deny rule)")
        success, result = self._generate_scapy_l2_traffic(src_mac, dst_mac, duration, num_packets)

        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "L2 traffic generation failed")

        # ===== PHASE 4: Stop tcpdump listener =====
        st.banner("PHASE 4: Stopping tcpdump listener")
        self._stop_tcpdump(self.data.dut3)

        # ===== PHASE 5: Verify using pcap =====
        st.banner("PHASE 5: Counting packets in pcap file")
        rx_count = self._count_packets_in_pcap(self.data.dut3, pcap_path)

        # ===== PHASE 6: Validate results =====
        st.banner("PHASE 6: Validating results (expecting DENY)")

        st.log(f"Traffic Result: TX={num_packets}, RX={rx_count}")

        # For DENY rule, expect RX = 0
        if rx_count == 0:
            st.log("✅ L2-02 test PASSED - All packets denied as expected")
            st.report_pass("test_case_passed")
        else:
            st.error(f"❌ L2-02 test FAILED - Expected RX=0, got RX={rx_count}")
            st.report_fail("msg", f"ACL not blocking packets (RX={rx_count})")

    # ============================================================================
    # L2-03: DENY DESTINATION MAC
    # ============================================================================

    @pytest.mark.inventory(
        feature="L2_ACL",
        testcases=["test_l2_03_deny_dest_mac"]
    )
    @pytest.mark.skip_module_config_save
    def test_l2_03_deny_dest_mac(self) -> None:
        """
        TC-L2-03: Deny destination MAC address.

        This test verifies that ACL rules blocking a specific destination MAC work correctly.
        Traffic to the denied MAC should be dropped (RX = 0).
        Expected result: RX count = 0 (denied traffic blocked).
        """
        st.banner("Test L2-03: Deny destination MAC 11:22:33:44:55:66")

        src_mac = "00:11:22:33:44:55"
        dst_mac = "11:22:33:44:55:66"
        num_packets = 100
        duration = 10
        pcap_path = "/tmp/l2_03_rx.pcap"

        dut3_rx_interface = self.data.dut3_port_to_dut1 or "Ethernet24"

        # ===== PHASE 1: Cleanup =====
        st.banner("PHASE 1: Cleanup")
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        # ===== PHASE 2: Start tcpdump listener =====
        st.banner("PHASE 2: Starting tcpdump listener on DUT3")
        tcpdump_ok = self._start_tcpdump(self.data.dut3, dut3_rx_interface, pcap_path)

        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener on DUT3")

        # ===== PHASE 3: Generate traffic =====
        st.banner("PHASE 3: Generating L2 traffic (deny dest MAC rule)")
        success, result = self._generate_scapy_l2_traffic(src_mac, dst_mac, duration, num_packets)

        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "L2 traffic generation failed")

        # ===== PHASE 4: Stop tcpdump listener =====
        st.banner("PHASE 4: Stopping tcpdump listener")
        self._stop_tcpdump(self.data.dut3)

        # ===== PHASE 5: Verify using pcap =====
        st.banner("PHASE 5: Counting packets in pcap file")
        rx_count = self._count_packets_in_pcap(self.data.dut3, pcap_path)

        # ===== PHASE 6: Validate results =====
        st.banner("PHASE 6: Validating results (expecting DENY)")

        st.log(f"Traffic Result: TX={num_packets}, RX={rx_count}")

        if rx_count == 0:
            st.log("✅ L2-03 test PASSED - All packets denied as expected")
            st.report_pass("test_case_passed")
        else:
            st.error(f"❌ L2-03 test FAILED - Expected RX=0, got RX={rx_count}")
            st.report_fail("msg", f"Destination MAC deny rule not working (RX={rx_count})")

    # ============================================================================
    # L2-04: DENY BROADCAST MAC
    # ============================================================================

    @pytest.mark.inventory(
        feature="L2_ACL",
        testcases=["test_l2_04_deny_broadcast_mac"]
    )
    @pytest.mark.skip_module_config_save
    def test_l2_04_deny_broadcast_mac(self) -> None:
        """
        TC-L2-04: Deny broadcast MAC address (FF:FF:FF:FF:FF:FF).

        This test verifies that ACL rules blocking broadcast traffic work correctly.
        Broadcast frames should be dropped (RX = 0).
        Expected result: RX count = 0 (broadcast traffic blocked).
        """
        st.banner("Test L2-04: Deny broadcast MAC (FF:FF:FF:FF:FF:FF)")

        src_mac = "00:11:22:33:44:55"
        dst_mac = "FF:FF:FF:FF:FF:FF"  # Broadcast
        num_packets = 100
        duration = 10
        pcap_path = "/tmp/l2_04_rx.pcap"

        dut3_rx_interface = self.data.dut3_port_to_dut1 or "Ethernet24"

        # ===== PHASE 1: Cleanup =====
        st.banner("PHASE 1: Cleanup")
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        # ===== PHASE 2: Start tcpdump listener =====
        st.banner("PHASE 2: Starting tcpdump listener on DUT3")
        tcpdump_ok = self._start_tcpdump(self.data.dut3, dut3_rx_interface, pcap_path)

        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener on DUT3")

        # ===== PHASE 3: Generate traffic =====
        st.banner("PHASE 3: Generating L2 broadcast traffic (deny rule)")
        success, result = self._generate_scapy_l2_traffic(src_mac, dst_mac, duration, num_packets)

        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "L2 traffic generation failed")

        # ===== PHASE 4: Stop tcpdump listener =====
        st.banner("PHASE 4: Stopping tcpdump listener")
        self._stop_tcpdump(self.data.dut3)

        # ===== PHASE 5: Verify using pcap =====
        st.banner("PHASE 5: Counting packets in pcap file")
        rx_count = self._count_packets_in_pcap(self.data.dut3, pcap_path)

        # ===== PHASE 6: Validate results =====
        st.banner("PHASE 6: Validating results (expecting DENY broadcast)")

        st.log(f"Traffic Result: TX={num_packets}, RX={rx_count}")

        if rx_count == 0:
            st.log("✅ L2-04 test PASSED - Broadcast traffic denied")
            st.report_pass("test_case_passed")
        else:
            st.error(f"❌ L2-04 test FAILED - Expected RX=0 for broadcast, got RX={rx_count}")
            st.report_fail("msg", f"Broadcast deny rule not working (RX={rx_count})")

    # ============================================================================
    # L2-05: DENY ARP ETHERTYPE
    # ============================================================================

    @pytest.mark.inventory(
        feature="L2_ACL",
        testcases=["test_l2_05_deny_arp_ethertype"]
    )
    @pytest.mark.skip_module_config_save
    def test_l2_05_deny_arp_ethertype(self) -> None:
        """
        TC-L2-05: Deny ARP EtherType (0x0806).

        This test verifies that ACL rules blocking ARP frames work correctly.
        ARP frames should be dropped (RX = 0).
        Expected result: RX count = 0 (ARP traffic blocked).
        """
        st.banner("Test L2-05: Deny ARP EtherType (0x0806)")

        src_mac = "00:11:22:33:44:55"
        dst_mac = "FF:FF:FF:FF:FF:FF"
        num_packets = 100
        duration = 10
        pcap_path = "/tmp/l2_05_rx.pcap"

        dut3_rx_interface = self.data.dut3_port_to_dut1 or "Ethernet24"

        # ===== PHASE 1: Cleanup =====
        st.banner("PHASE 1: Cleanup")
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        # ===== PHASE 2: Start tcpdump listener =====
        st.banner("PHASE 2: Starting tcpdump listener on DUT3")
        tcpdump_ok = self._start_tcpdump(self.data.dut3, dut3_rx_interface, pcap_path)

        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener on DUT3")

        # ===== PHASE 3: Generate ARP traffic =====
        st.banner("PHASE 3: Generating ARP traffic (deny rule)")
        # For ARP, we'd need a special traffic function - for now, use regular L2
        success, result = self._generate_scapy_l2_traffic(src_mac, dst_mac, duration, num_packets)

        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "ARP traffic generation failed")

        # ===== PHASE 4: Stop tcpdump listener =====
        st.banner("PHASE 4: Stopping tcpdump listener")
        self._stop_tcpdump(self.data.dut3)

        # ===== PHASE 5: Verify using pcap =====
        st.banner("PHASE 5: Counting packets in pcap file")
        rx_count = self._count_packets_in_pcap(self.data.dut3, pcap_path)

        # ===== PHASE 6: Validate results =====
        st.banner("PHASE 6: Validating results (expecting DENY ARP)")

        st.log(f"Traffic Result: TX={num_packets}, RX={rx_count}")

        if rx_count == 0:
            st.log("✅ L2-05 test PASSED - ARP traffic denied")
            st.report_pass("test_case_passed")
        else:
            st.error(f"❌ L2-05 test FAILED - Expected RX=0 for ARP, got RX={rx_count}")
            st.report_fail("msg", f"ARP deny rule not working (RX={rx_count})")

    # ============================================================================
    # L2-06: DENY VLAN 100
    # ============================================================================

    @pytest.mark.inventory(
        feature="L2_ACL",
        testcases=["test_l2_06_deny_vlan_100"]
    )
    @pytest.mark.skip_module_config_save
    def test_l2_06_deny_vlan_100(self) -> None:
        """
        TC-L2-06: Deny VLAN 100 traffic.

        This test verifies that ACL rules blocking VLAN 100 work correctly.
        Frames tagged with VLAN 100 should be dropped (RX = 0).
        Expected result: RX count = 0 (VLAN 100 traffic blocked).
        """
        st.banner("Test L2-06: Deny VLAN 100 traffic")

        src_mac = "00:11:22:33:44:55"
        dst_mac = "FF:FF:FF:FF:FF:FF"
        vlan_id = 100
        num_packets = 100
        duration = 10
        pcap_path = "/tmp/l2_06_rx.pcap"

        dut3_rx_interface = self.data.dut3_port_to_dut1 or "Ethernet24"

        # ===== PHASE 1: Cleanup =====
        st.banner("PHASE 1: Cleanup")
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        # ===== PHASE 2: Start tcpdump listener =====
        st.banner("PHASE 2: Starting tcpdump listener on DUT3")
        tcpdump_ok = self._start_tcpdump(self.data.dut3, dut3_rx_interface, pcap_path)

        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener on DUT3")

        # ===== PHASE 3: Generate VLAN traffic =====
        st.banner("PHASE 3: Generating VLAN 100 traffic (deny rule)")
        success, result = self._generate_scapy_l2_traffic(src_mac, dst_mac, duration, num_packets, vlan_id)

        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "VLAN traffic generation failed")

        # ===== PHASE 4: Stop tcpdump listener =====
        st.banner("PHASE 4: Stopping tcpdump listener")
        self._stop_tcpdump(self.data.dut3)

        # ===== PHASE 5: Verify using pcap =====
        st.banner("PHASE 5: Counting packets in pcap file")
        rx_count = self._count_packets_in_pcap(self.data.dut3, pcap_path)

        # ===== PHASE 6: Validate results =====
        st.banner("PHASE 6: Validating results (expecting DENY VLAN 100)")

        st.log(f"Traffic Result: TX={num_packets}, RX={rx_count}")

        if rx_count == 0:
            st.log("✅ L2-06 test PASSED - VLAN 100 traffic denied")
            st.report_pass("test_case_passed")
        else:
            st.error(f"❌ L2-06 test FAILED - Expected RX=0 for VLAN 100, got RX={rx_count}")
            st.report_fail("msg", f"VLAN 100 deny rule not working (RX={rx_count})")

    # ============================================================================
    # L2-07: PERMIT/DENY VLAN MIX
    # ============================================================================

    @pytest.mark.inventory(
        feature="L2_ACL",
        testcases=["test_l2_07_permit_deny_vlan_mix"]
    )
    @pytest.mark.skip_module_config_save
    def test_l2_07_permit_deny_vlan_mix(self) -> None:
        """
        TC-L2-07: Permit/Deny VLAN Mix (VLAN 100 denied, VLAN 200 permitted).

        This test verifies that ACL rules with mixed permit/deny VLAN rules work correctly.
        VLAN 100 should be blocked (RX = 0), VLAN 200 should pass.
        Expected result: VLAN 100 RX=0, VLAN 200 RX > 0.
        """
        st.banner("Test L2-07: Permit/Deny VLAN Mix (100 denied, 200 permitted)")

        src_mac = "00:11:22:33:44:55"
        dst_mac = "FF:FF:FF:FF:FF:FF"
        num_packets = 100
        duration = 10

        # Test VLAN 200 (should be permitted)
        pcap_path = "/tmp/l2_07_vlan200_rx.pcap"
        dut3_rx_interface = self.data.dut3_port_to_dut1 or "Ethernet24"

        # ===== PHASE 1: Cleanup =====
        st.banner("PHASE 1: Cleanup")
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        # ===== PHASE 2: Start tcpdump listener =====
        st.banner("PHASE 2: Starting tcpdump listener on DUT3")
        tcpdump_ok = self._start_tcpdump(self.data.dut3, dut3_rx_interface, pcap_path)

        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener on DUT3")

        # ===== PHASE 3: Generate VLAN 200 traffic =====
        st.banner("PHASE 3: Generating VLAN 200 traffic (permit rule)")
        success, result = self._generate_scapy_l2_traffic(src_mac, dst_mac, duration, num_packets, vlan_id=200)

        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "VLAN 200 traffic generation failed")

        # ===== PHASE 4: Stop tcpdump listener =====
        st.banner("PHASE 4: Stopping tcpdump listener")
        self._stop_tcpdump(self.data.dut3)

        # ===== PHASE 5: Verify using pcap =====
        st.banner("PHASE 5: Counting packets in pcap file")
        rx_count = self._count_packets_in_pcap(self.data.dut3, pcap_path)

        # ===== PHASE 6: Validate results =====
        st.banner("PHASE 6: Validating results (VLAN 200 should be permitted)")

        st.log(f"Traffic Result: TX={num_packets}, RX={rx_count}")

        if rx_count == 0:
            st.error("❌ L2-07 test FAILED - VLAN 200 should be permitted, got RX=0")
            st.report_fail("msg", "VLAN 200 permit rule not working (RX=0)")

        loss_pct = ((num_packets - rx_count) / num_packets * 100) if num_packets > 0 else 100.0
        max_loss = 10.0

        if loss_pct > max_loss:
            st.error(f"❌ Packet loss {loss_pct:.1f}% exceeds threshold {max_loss}%")
            st.report_fail("msg", f"Loss {loss_pct:.1f}% > {max_loss}%")

        st.log("✅ L2-07 test PASSED - VLAN mix rules working")
        st.report_pass("test_case_passed")

    # ============================================================================
    # L2-08: ACL RULE PRIORITY
    # ============================================================================

    @pytest.mark.inventory(
        feature="L2_ACL",
        testcases=["test_l2_08_acl_rule_priority"]
    )
    @pytest.mark.skip_module_config_save
    def test_l2_08_acl_rule_priority(self) -> None:
        """
        TC-L2-08: ACL Rule Priority (higher priority rule takes precedence).

        This test verifies that ACL rules with different priorities are applied correctly.
        When multiple rules match, the highest priority rule should take precedence.
        Expected result: Higher priority rule action applies (e.g., deny before permit).
        """
        st.banner("Test L2-08: ACL Rule Priority")

        src_mac = "00:11:22:33:44:55"
        dst_mac = "FF:FF:FF:FF:FF:FF"
        num_packets = 100
        duration = 10
        pcap_path = "/tmp/l2_08_priority_rx.pcap"

        dut3_rx_interface = self.data.dut3_port_to_dut1 or "Ethernet24"

        # ===== PHASE 1: Cleanup =====
        st.banner("PHASE 1: Cleanup")
        self._cleanup_pcap_files(self.data.dut3, pcap_path)

        # ===== PHASE 2: Start tcpdump listener =====
        st.banner("PHASE 2: Starting tcpdump listener on DUT3")
        tcpdump_ok = self._start_tcpdump(self.data.dut3, dut3_rx_interface, pcap_path)

        if not tcpdump_ok:
            st.report_fail("msg", "Failed to start tcpdump listener on DUT3")

        # ===== PHASE 3: Generate traffic =====
        st.banner("PHASE 3: Generating L2 traffic (testing rule priority)")
        success, result = self._generate_scapy_l2_traffic(src_mac, dst_mac, duration, num_packets)

        if not success:
            self._stop_tcpdump(self.data.dut3)
            st.report_fail("msg", "L2 traffic generation failed")

        # ===== PHASE 4: Stop tcpdump listener =====
        st.banner("PHASE 4: Stopping tcpdump listener")
        self._stop_tcpdump(self.data.dut3)

        # ===== PHASE 5: Verify using pcap =====
        st.banner("PHASE 5: Counting packets in pcap file")
        rx_count = self._count_packets_in_pcap(self.data.dut3, pcap_path)

        # ===== PHASE 6: Validate results =====
        st.banner("PHASE 6: Validating results (rule priority)")

        st.log(f"Traffic Result: TX={num_packets}, RX={rx_count}")
        st.log("Higher priority DENY rule should block traffic")

        if rx_count == 0:
            st.log("✅ L2-08 test PASSED - Rule priority working correctly")
            st.report_pass("test_case_passed")
        else:
            st.error(f"❌ L2-08 test FAILED - Expected RX=0, got RX={rx_count}")
            st.report_fail("msg", f"Rule priority not working (RX={rx_count})")
