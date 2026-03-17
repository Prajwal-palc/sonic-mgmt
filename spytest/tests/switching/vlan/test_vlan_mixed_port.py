"""
VLAN MIXED/HYBRID PORT CONFIGURATION AND TRAFFIC TESTS
Author: Shiva
2026

How to run:
  # TC_001 only (single DUT)
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_2d.yaml \\
  tests/switching/vlan/test_vlan_mixed_port.py::TestVlanMixedPort::test_vlan_mixed_001_hybrid_config \\
  --logs-path ./logs/vlan_mixed_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

  # TC_002 only (two DUTs with traffic)
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_2d.yaml \\
  tests/switching/vlan/test_vlan_mixed_port.py::TestVlanMixedPort::test_vlan_mixed_002_hybrid_traffic \\
  --logs-path ./logs/vlan_mixed_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  TC_VLAN_MIXED_001: Validates hybrid port configuration (Access + Trunk on same interface)
  TC_VLAN_MIXED_002: Validates mixed port L2 traffic handling (untagged and tagged)

  TC_001 configures single interface as both Access VLAN 10 (untagged) and Trunk VLAN 20 (tagged).
  TC_002 sends L2 broadcast traffic to verify untagged frames map to Access VLAN and tagged frames
  forward through Trunk VLAN, with strict isolation between VLANs.

Pre-requisites:
  - Topology: TC_001: single DUT (D2), TC_002: two-node with 3 connections | Supported: HW and Virtual
  - Topology Diagram:
        # TC_001: Single DUT
        # +--------------------+
        # |       leaf01       |
        # |     Ethernet8      |
        # +--------------------+

        # TC_002: Two nodes with 3 links
        # +--------------------+                       +--------------------+
        # |      spine02       |                       |      leaf01        |
        # |   (Traffic Gen)    |                       |       (DUT)        |
        # | D1D2P1 Ethernet4   |=======================| D2D1P1 Ethernet4   | (Hybrid ingress)
        # | D1D2P2 Ethernet8   |=======================| D2D1P2 Ethernet8   | (VLAN 20 monitor)
        # | D1D2P3 Ethernet12  |=======================| D2D1P3 Ethernet12  | (VLAN 10 monitor)
        # +--------------------+                       +--------------------+

  - Feature flags / min SONiC version: VLAN support required
  - Required test variables (YAML): spytest/vars/switching/vlan/vars_vlan_mixed.yaml
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.switching.vlan as vlan_api
import apis.system.interface as interface_api

# Default YAML variable file location
VAR_FILE_ENV = "VLAN_MIXED_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "switching"
    / "vlan"
    / "vars_vlan_mixed.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"VLAN mixed port variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("VLAN mixed port YAML must contain key 'testcases'")

    return content


class TestVlanMixedPort:
    """Testcases validating VLAN mixed/hybrid port configuration and traffic handling."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        st.log(f"✓ Test setup complete. CLI type: {cls.data.cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup after test suite completes."""
        st.log("Test suite teardown complete")

    def _clear_interface_counters(self, dut: str) -> None:
        """Clear interface counters on DUT."""
        st.log(f"Clearing interface counters on {dut}")
        cmd = "clear interface counters"
        st.show(dut, cmd, type=self.data.cli_type, skip_tmpl=True, skip_error_check=True)
        time.sleep(2)

    def _get_interface_counters(self, dut: str, interface: str) -> Dict[str, int]:
        """Get RX_OK and TX_OK counters for an interface using raw parsing."""
        match = re.search(r'Ethernet(\d+)', interface)
        if not match:
            st.error(f"Invalid interface name: {interface}")
            return {"rx_ok": 0, "tx_ok": 0}

        intf_num = match.group(1)
        cmd = f"show interface counters Ethernet {intf_num}"

        raw_output = st.show(dut, cmd, type=self.data.cli_type, skip_tmpl=True, skip_error_check=True)

        counters = {"rx_ok": 0, "tx_ok": 0}
        if raw_output and isinstance(raw_output, str):
            for line in raw_output.split('\n'):
                if interface in line or f"Ethernet{intf_num}" in line:
                    parts = line.split()
                    if len(parts) >= 10:
                        try:
                            counters["rx_ok"] = int(parts[2].replace(",", ""))
                            counters["tx_ok"] = int(parts[9].replace(",", ""))
                        except (ValueError, IndexError):
                            pass
                        break

        st.log(f"Counters for {interface}: RX_OK={counters['rx_ok']}, TX_OK={counters['tx_ok']}")
        return counters

    def _start_tcpdump(self, dut: str, interface: str, pcap_file: str) -> bool:
        """Start tcpdump capture on interface."""
        st.log(f"Starting tcpdump on {dut} {interface} -> {pcap_file}")
        st.show(dut, f"sudo rm -f {pcap_file}", skip_tmpl=True, skip_error_check=True)
        cmd = f"sudo nohup tcpdump -i {interface} -e -w {pcap_file} > /tmp/tcpdump.log 2>&1 &"
        st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
        time.sleep(2)
        return True

    def _stop_tcpdump(self, dut: str) -> bool:
        """Stop all tcpdump processes on DUT."""
        st.log(f"Stopping tcpdump on {dut}")
        st.show(dut, "sudo pkill tcpdump", skip_tmpl=True, skip_error_check=True)
        time.sleep(2)
        return True

    def _verify_tcpdump_capture(self, dut: str, pcap_file: str) -> int:
        """Count packets in pcap file."""
        st.log(f"Verifying tcpdump capture: {pcap_file}")
        cmd = f"sudo tcpdump -r {pcap_file} 2>/dev/null | wc -l"
        output = st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)

        packet_count = 0
        if output and isinstance(output, str):
            match = re.search(r'(\d+)', output)
            if match:
                packet_count = int(match.group(1))

        st.log(f"✓ tcpdump captured {packet_count} packets")
        return packet_count

    def _send_l2_broadcast_traffic(self, tgen: str, tgen_port: str, src_mac: str,
                                   vlan_id: int = None, packet_count: int = 20,
                                   interval: float = 0.05, payload: str = "TEST",
                                   script_path: str = "/tmp/scapy_l2.py") -> bool:
        """Send L2 broadcast traffic using Scapy (untagged or tagged).

        Args:
            tgen: Traffic generator device
            tgen_port: Interface to send from
            src_mac: Source MAC address
            vlan_id: VLAN ID (None for untagged, int for tagged)
            packet_count: Number of packets to send
            interval: Inter-packet delay
            payload: Payload string
            script_path: Path to Scapy script on TGen

        Returns:
            True if traffic sent successfully
        """
        st.log(f"Sending L2 broadcast traffic: vlan_id={vlan_id}, count={packet_count}")

        # Build Scapy script for L2 broadcast
        if vlan_id is None:
            # Untagged frame
            script_content = f'''#!/usr/bin/env python3
from scapy.all import Ether, Raw, sendp
import time

iface = "{tgen_port}"
src_mac = "{src_mac}"
dst_mac = "ff:ff:ff:ff:ff:ff"
payload = "{payload}"
packet_count = {packet_count}
interval = {interval}

def send_untagged_l2_broadcast():
    pkt = (
        Ether(src=src_mac, dst=dst_mac) /
        Raw(load=payload)
    )

    sent = 0
    for i in range(packet_count):
        sendp(pkt, iface=iface, verbose=False)
        sent += 1
        time.sleep(interval)

    print(f"Sent {{sent}} untagged L2 broadcast packets")
    return True

if __name__ == "__main__":
    send_untagged_l2_broadcast()
'''
        else:
            # Tagged frame
            script_content = f'''#!/usr/bin/env python3
from scapy.all import Ether, Dot1Q, Raw, sendp
import time

iface = "{tgen_port}"
src_mac = "{src_mac}"
dst_mac = "ff:ff:ff:ff:ff:ff"
vlan_id = {vlan_id}
payload = "{payload}"
packet_count = {packet_count}
interval = {interval}

def send_tagged_l2_broadcast():
    pkt = (
        Ether(src=src_mac, dst=dst_mac) /
        Dot1Q(vlan=vlan_id) /
        Raw(load=payload)
    )

    sent = 0
    for i in range(packet_count):
        sendp(pkt, iface=iface, verbose=False)
        sent += 1
        time.sleep(interval)

    print(f"Sent {{sent}} VLAN {{vlan_id}} tagged L2 broadcast packets")
    return True

if __name__ == "__main__":
    send_tagged_l2_broadcast()
'''

        # Write script to TGen
        write_cmd = f"cat > {script_path} << 'SCAPY_SCRIPT_EOF'\n{script_content}\nSCAPY_SCRIPT_EOF"
        st.show(tgen, write_cmd, skip_tmpl=True, skip_error_check=True)

        # Make executable
        st.show(tgen, f"chmod +x {script_path}", skip_tmpl=True, skip_error_check=True)

        # Execute script
        exec_cmd = f"sudo python3 {script_path}"
        output = st.show(tgen, exec_cmd, skip_tmpl=True, skip_error_check=True)

        if output and "Sent" in output:
            st.log(f"✓ Traffic sent successfully")
            return True
        else:
            st.error("Failed to send traffic")
            return False

    def _verify_vlan_hybrid_membership(self, dut: str, vlan_id: int, interface: str,
                                       expected_type: str, expected_status: str) -> bool:
        """Verify interface membership type (A=Access, T=Tagged) and VLAN status.

        Args:
            dut: Device under test
            vlan_id: VLAN ID to check
            interface: Interface name
            expected_type: Expected membership type ("A" or "T")
            expected_status: Expected VLAN status ("Up" or "Down")

        Returns:
            True if verification passes
        """
        st.log(f"Verifying VLAN {vlan_id} membership: {interface}, type={expected_type}, status={expected_status}")

        cmd = f"show Vlan {vlan_id}"
        raw_output = st.show(dut, cmd, type=self.data.cli_type, skip_tmpl=True, skip_error_check=True)

        if not raw_output:
            st.error("Failed to get show Vlan output")
            return False

        st.log(f"Show Vlan output:\n{raw_output}")

        # Parse output to find VLAN line
        for line in raw_output.split('\n'):
            if f"Vlan{vlan_id}" in line or f"VLAN{vlan_id}" in line:
                parts = line.split()
                if len(parts) >= 4:
                    status = parts[1]
                    membership_type = parts[2]
                    port = parts[3] if len(parts) > 3 else ""

                    st.log(f"Parsed: status={status}, type={membership_type}, port={port}")

                    if status != expected_status:
                        st.error(f"VLAN {vlan_id} status is {status}, expected {expected_status}")
                        return False

                    if membership_type != expected_type:
                        st.error(f"VLAN {vlan_id} membership type is {membership_type}, expected {expected_type}")
                        return False

                    if interface not in line:
                        st.error(f"Interface {interface} not found in VLAN {vlan_id} membership")
                        return False

                    st.log(f"✓ VLAN {vlan_id} verification passed")
                    return True

        st.error(f"Could not find VLAN {vlan_id} in output")
        return False

    @pytest.mark.topology("D2:1")
    @pytest.mark.inventory(feature="Regression", testcases=["TC_VLAN_MIXED_001"])
    def test_vlan_mixed_001_hybrid_config(self) -> None:
        """
        TC_VLAN_MIXED_001: Verify mixed/hybrid port configuration (Access + Trunk).

        Test Steps:
        1. Get single DUT (leaf01/D2)
        2. Pre-cleanup: Remove VLANs 10, 20 if exist
        3. Create VLANs 10, 20
        4. Configure Ethernet8 as Access VLAN 10 (untagged)
        5. Verify show Vlan: VLAN 10 has Ethernet8 as A (Access)
        6. Add Trunk VLAN 20 to same interface
        7. Verify show Vlan: VLAN 10 has Ethernet8 as A, VLAN 20 has Ethernet8 as T (Tagged)
        8. Cleanup
        """
        st.banner("TC_VLAN_MIXED_001: Mixed/Hybrid Port Configuration Test")

        testcase = self.data.testcases.get("TC_VLAN_MIXED_001")
        if not testcase:
            st.report_fail("msg", "TC_VLAN_MIXED_001 testcase not found in YAML")

        vlans = testcase.get("vlans", [])
        verification = SpyTestDict(testcase.get("verification", {}))

        # Get topology
        min_topology = testcase.get("min_topology") or ["D2:1"]
        topology = st.ensure_min_topology(*min_topology)

        dut = topology.D2
        test_interface = "Ethernet8"

        try:
            st.banner("Step 1: Pre-cleanup - Remove VLANs if exist")
            for vlan in vlans:
                vlan_id = vlan.get("id")
                vlan_api.delete_vlan(dut, vlan_id, cli_type=self.data.cli_type, skip_error_check=True)
            st.log("✓ Pre-cleanup completed")

            st.banner("Step 2: Creating VLANs 10, 20")
            for vlan in vlans:
                vlan_id = vlan.get("id")
                if not vlan_api.create_vlan(dut, vlan_id, cli_type=self.data.cli_type):
                    st.report_fail("msg", f"Failed to create VLAN {vlan_id}")
                st.log(f"✓ VLAN {vlan_id} created")

            st.banner(f"Step 3: Configuring {test_interface} as Access VLAN 10")

            match = re.search(r'Ethernet(\d+)', test_interface)
            intf_num = match.group(1)

            access_commands = [
                f"interface Ethernet {intf_num}",
                "no ip address",
                "no switchport trunk allowed Vlan 10",
                "no switchport trunk allowed Vlan 20",
                "switchport access Vlan 10",
                "no shutdown",
                "end"
            ]

            st.config(dut, access_commands, type=self.data.cli_type, skip_error_check=True)
            st.log(f"✓ {test_interface} configured as Access VLAN 10")

            st.banner("Step 4: Verifying VLAN 10 membership (Access)")

            vlan10_verify = verification.get("vlan10_membership", {})
            if not self._verify_vlan_hybrid_membership(
                dut, 10, test_interface,
                vlan10_verify.get("expected_type", "A"),
                vlan10_verify.get("expected_status", "Up")
            ):
                st.report_fail("msg", "VLAN 10 Access membership verification failed")

            st.log(f"✓ VLAN 10 verified: {test_interface} is Access (A) member")

            st.banner(f"Step 5: Adding Trunk VLAN 20 to {test_interface}")

            trunk_commands = [
                f"interface Ethernet {intf_num}",
                "switchport trunk allowed Vlan 20",
                "end"
            ]

            st.config(dut, trunk_commands, type=self.data.cli_type, skip_error_check=True)
            st.log(f"✓ Trunk VLAN 20 added to {test_interface}")

            st.banner("Step 6: Verifying hybrid configuration (Access VLAN 10 + Trunk VLAN 20)")

            # Verify VLAN 10 still shows as Access
            if not self._verify_vlan_hybrid_membership(
                dut, 10, test_interface,
                vlan10_verify.get("expected_type", "A"),
                vlan10_verify.get("expected_status", "Up")
            ):
                st.report_fail("msg", "VLAN 10 Access membership lost after adding Trunk VLAN 20")

            st.log(f"✓ VLAN 10 still shows {test_interface} as Access (A)")

            # Verify VLAN 20 shows as Tagged
            vlan20_verify = verification.get("vlan20_membership", {})
            if not self._verify_vlan_hybrid_membership(
                dut, 20, test_interface,
                vlan20_verify.get("expected_type", "T"),
                vlan20_verify.get("expected_status", "Up")
            ):
                st.report_fail("msg", "VLAN 20 Tagged membership verification failed")

            st.log(f"✓ VLAN 20 verified: {test_interface} is Tagged (T) member")

            st.banner("Step 7: Cleanup")

            cleanup_commands = [
                f"interface Ethernet {intf_num}",
                "no switchport access Vlan",
                "no switchport trunk allowed Vlan 20",
                "exit"
            ]
            st.config(dut, cleanup_commands, type=self.data.cli_type, skip_error_check=True)

            for vlan in vlans:
                vlan_api.delete_vlan(dut, vlan.get("id"), cli_type=self.data.cli_type, skip_error_check=True)

            st.log("✓ Cleanup completed")
            st.report_pass("test_case_passed")

        except Exception as e:
            st.error(f"Test failed: {e}")

            if self.data.cleanup_enabled:
                st.log("Performing cleanup after failure")

                if test_interface:
                    match = re.search(r'Ethernet(\d+)', test_interface)
                    if match:
                        intf_num = match.group(1)
                        cleanup_cmds = [
                            f"interface Ethernet {intf_num}",
                            "no switchport access Vlan",
                            "no switchport trunk allowed Vlan 10",
                            "no switchport trunk allowed Vlan 20",
                            "exit"
                        ]
                        st.config(dut, cleanup_cmds, type=self.data.cli_type, skip_error_check=True)

                for vlan in vlans:
                    vlan_api.delete_vlan(dut, vlan.get("id"), cli_type=self.data.cli_type, skip_error_check=True)

            st.report_fail("msg", f"Test failed: {e}")

    @pytest.mark.topology("D1D2:3")
    @pytest.mark.inventory(feature="Regression", testcases=["TC_VLAN_MIXED_002"])
    def test_vlan_mixed_002_hybrid_traffic(self) -> None:
        """
        TC_VLAN_MIXED_002: Verify mixed port L2 traffic handling (untagged and tagged).

        Test Steps:
        1. Get topology (D1=TGen spine02, D2=DUT leaf01)
        2. Pre-cleanup: Remove VLANs 10, 20
        3. Create VLANs 10, 20
        4. Configure Ethernet4 as hybrid: Access VLAN 20 + Trunk VLAN 10
        5. Configure Ethernet8 as Trunk VLAN 20 (monitor)
        6. Configure Ethernet12 as Trunk VLAN 10 (monitor)
        7. Test A: Send UNTAGGED L2 broadcast
        8. Verify Ethernet8 receives traffic (VLAN 20), Ethernet12 does NOT
        9. Test B: Send VLAN 10 TAGGED L2 broadcast
        10. Verify Ethernet12 receives traffic (VLAN 10), Ethernet8 does NOT
        11. Cleanup
        """
        st.banner("TC_VLAN_MIXED_002: Mixed Port L2 Traffic Handling Test")

        testcase = self.data.testcases.get("TC_VLAN_MIXED_002")
        if not testcase:
            st.report_fail("msg", "TC_VLAN_MIXED_002 testcase not found in YAML")

        vlans = testcase.get("vlans", [])
        traffic = SpyTestDict(testcase.get("traffic", {}))
        verification = SpyTestDict(testcase.get("verification", {}))

        # Get topology
        min_topology = testcase.get("min_topology") or ["D1D2:3"]
        topology = st.ensure_min_topology(*min_topology)

        tgen = topology.D1
        dut = topology.D2

        # Get interfaces dynamically
        hybrid_port = getattr(topology, 'D2D1P1', None)          # Ethernet4
        vlan20_monitor = getattr(topology, 'D2D1P2', None)       # Ethernet8
        vlan10_monitor = getattr(topology, 'D2D1P3', None)       # Ethernet12

        tgen_port = getattr(topology, 'D1D2P1', None)

        if not all([hybrid_port, vlan20_monitor, vlan10_monitor, tgen_port]):
            st.report_fail("msg", "Failed to discover topology (need 3 links)")

        st.log(f"✓ Topology: TGen={tgen}, DUT={dut}")
        st.log(f"  Hybrid: {hybrid_port}, VLAN20 Monitor: {vlan20_monitor}, VLAN10 Monitor: {vlan10_monitor}")

        try:
            st.banner("Step 1: Pre-cleanup - Remove VLANs if exist")
            for vlan in vlans:
                vlan_id = vlan.get("id")
                vlan_api.delete_vlan(dut, vlan_id, cli_type=self.data.cli_type, skip_error_check=True)
            st.log("✓ Pre-cleanup completed")

            st.banner("Step 2: Creating VLANs 10, 20")
            for vlan in vlans:
                vlan_id = vlan.get("id")
                if not vlan_api.create_vlan(dut, vlan_id, cli_type=self.data.cli_type):
                    st.report_fail("msg", f"Failed to create VLAN {vlan_id}")
                st.log(f"✓ VLAN {vlan_id} created")

            st.banner(f"Step 3: Configuring {hybrid_port} as hybrid (Access VLAN 20 + Trunk VLAN 10)")

            match = re.search(r'Ethernet(\d+)', hybrid_port)
            intf_num = match.group(1)

            hybrid_commands = [
                f"interface Ethernet {intf_num}",
                "no ip address",
                "no switchport trunk allowed Vlan 10",
                "no switchport trunk allowed Vlan 20",
                "switchport access Vlan 20",
                "switchport trunk allowed Vlan 10",
                "no shutdown",
                "exit"
            ]

            st.config(dut, hybrid_commands, type=self.data.cli_type, skip_error_check=True)
            st.log(f"✓ {hybrid_port} configured as hybrid port")

            st.banner(f"Step 4: Configuring {vlan20_monitor} as Trunk VLAN 20 (monitor)")

            match = re.search(r'Ethernet(\d+)', vlan20_monitor)
            intf_num = match.group(1)

            monitor20_commands = [
                f"interface Ethernet {intf_num}",
                "no ip address",
                "no switchport access Vlan",
                "switchport trunk allowed Vlan 20",
                "no shutdown",
                "exit"
            ]

            st.config(dut, monitor20_commands, type=self.data.cli_type, skip_error_check=True)
            st.log(f"✓ {vlan20_monitor} configured as VLAN 20 trunk")

            st.banner(f"Step 5: Configuring {vlan10_monitor} as Trunk VLAN 10 (monitor)")

            match = re.search(r'Ethernet(\d+)', vlan10_monitor)
            intf_num = match.group(1)

            monitor10_commands = [
                f"interface Ethernet {intf_num}",
                "no ip address",
                "no switchport access Vlan",
                "switchport trunk allowed Vlan 10",
                "no shutdown",
                "exit"
            ]

            st.config(dut, monitor10_commands, type=self.data.cli_type, skip_error_check=True)
            st.log(f"✓ {vlan10_monitor} configured as VLAN 10 trunk")

            # Show VLAN configuration
            vlan_output = vlan_api.show_vlan_config(dut, cli_type=self.data.cli_type)
            st.log(f"VLAN configuration:\n{vlan_output}")

            st.banner("TEST A: Untagged L2 Broadcast Traffic")
            st.banner("Step 6: Clearing counters before Test A")
            self._clear_interface_counters(dut)

            st.banner("Step 7: Starting tcpdump on monitor ports")
            pcap_vlan20_testA = "/tmp/vlan_mixed_002_vlan20_testA.pcap"
            pcap_vlan10_testA = "/tmp/vlan_mixed_002_vlan10_testA.pcap"

            self._start_tcpdump(dut, vlan20_monitor, pcap_vlan20_testA)
            self._start_tcpdump(dut, vlan10_monitor, pcap_vlan10_testA)

            st.banner("Step 8: Sending UNTAGGED L2 broadcast traffic")

            packet_count = traffic.get("packet_count", 20)
            inter_packet_delay = traffic.get("inter_packet_delay", 0.05)
            src_mac = "00:11:22:33:44:55"
            untagged_payload = traffic.get("untagged", {}).get("payload", "MIXED_PORT_UNTAGGED_PAYLOAD")

            traffic_sent = self._send_l2_broadcast_traffic(
                tgen, tgen_port, src_mac,
                vlan_id=None,  # Untagged
                packet_count=packet_count,
                interval=inter_packet_delay,
                payload=untagged_payload,
                script_path="/tmp/scapy_mixed_untagged.py"
            )

            if not traffic_sent:
                st.report_fail("msg", "Failed to send untagged L2 broadcast traffic")

            time.sleep(2)

            st.banner("Step 9: Stopping tcpdump")
            self._stop_tcpdump(dut)
            time.sleep(2)

            st.banner("Step 10: Verifying Test A - Untagged traffic on VLAN 20 monitor")

            vlan20_counters = self._get_interface_counters(dut, vlan20_monitor)
            vlan20_pcap = self._verify_tcpdump_capture(dut, pcap_vlan20_testA)

            untagged_verify = verification.get("untagged_test", {})
            vlan20_verify = untagged_verify.get("vlan20_monitor_port", {})
            min_expected = vlan20_verify.get("min_packets", 15)

            st.log(f"VLAN 20 monitor: RX_OK={vlan20_counters['rx_ok']}, tcpdump={vlan20_pcap}")

            if vlan20_counters["rx_ok"] < min_expected and vlan20_pcap < min_expected:
                st.report_fail("msg", f"VLAN 20 monitor: RX_OK={vlan20_counters['rx_ok']}, tcpdump={vlan20_pcap} (both < {min_expected})")

            st.log(f"✓ VLAN 20 monitor received untagged traffic")

            st.banner("Step 11: Verifying Test A - No traffic on VLAN 10 monitor (isolation)")

            vlan10_counters = self._get_interface_counters(dut, vlan10_monitor)
            vlan10_pcap = self._verify_tcpdump_capture(dut, pcap_vlan10_testA)

            vlan10_verify = untagged_verify.get("vlan10_monitor_port", {})
            max_allowed = vlan10_verify.get("max_packets", 5)

            st.log(f"VLAN 10 monitor: RX_OK={vlan10_counters['rx_ok']}, tcpdump={vlan10_pcap}")

            if vlan10_counters["rx_ok"] > max_allowed or vlan10_pcap > max_allowed:
                st.report_fail("msg", f"VLAN 10 monitor: RX_OK={vlan10_counters['rx_ok']}, tcpdump={vlan10_pcap} (traffic leaked!)")

            st.log(f"✓ VLAN 10 monitor correctly isolated (no untagged traffic)")

            st.banner("TEST B: VLAN 10 Tagged L2 Broadcast Traffic")
            st.banner("Step 12: Clearing counters before Test B")
            self._clear_interface_counters(dut)

            st.banner("Step 13: Starting tcpdump on monitor ports")
            pcap_vlan20_testB = "/tmp/vlan_mixed_002_vlan20_testB.pcap"
            pcap_vlan10_testB = "/tmp/vlan_mixed_002_vlan10_testB.pcap"

            self._start_tcpdump(dut, vlan20_monitor, pcap_vlan20_testB)
            self._start_tcpdump(dut, vlan10_monitor, pcap_vlan10_testB)

            st.banner("Step 14: Sending VLAN 10 TAGGED L2 broadcast traffic")

            tagged_vlan10 = traffic.get("tagged_vlan10", {})
            vlan10_id = tagged_vlan10.get("vlan_id", 10)
            tagged_payload = tagged_vlan10.get("payload", "MIXED_PORT_TAGGED_PAYLOAD")

            traffic_sent = self._send_l2_broadcast_traffic(
                tgen, tgen_port, src_mac,
                vlan_id=vlan10_id,
                packet_count=packet_count,
                interval=inter_packet_delay,
                payload=tagged_payload,
                script_path="/tmp/scapy_mixed_tagged.py"
            )

            if not traffic_sent:
                st.report_fail("msg", "Failed to send VLAN 10 tagged L2 broadcast traffic")

            time.sleep(2)

            st.banner("Step 15: Stopping tcpdump")
            self._stop_tcpdump(dut)
            time.sleep(2)

            st.banner("Step 16: Verifying Test B - VLAN 10 tagged traffic on VLAN 10 monitor")

            vlan10_counters_b = self._get_interface_counters(dut, vlan10_monitor)
            vlan10_pcap_b = self._verify_tcpdump_capture(dut, pcap_vlan10_testB)

            tagged_verify = verification.get("tagged_test", {})
            vlan10_verify_b = tagged_verify.get("vlan10_monitor_port", {})
            min_expected_b = vlan10_verify_b.get("min_packets", 15)

            st.log(f"VLAN 10 monitor: RX_OK={vlan10_counters_b['rx_ok']}, tcpdump={vlan10_pcap_b}")

            if vlan10_counters_b["rx_ok"] < min_expected_b and vlan10_pcap_b < min_expected_b:
                st.report_fail("msg", f"VLAN 10 monitor: RX_OK={vlan10_counters_b['rx_ok']}, tcpdump={vlan10_pcap_b} (both < {min_expected_b})")

            st.log(f"✓ VLAN 10 monitor received tagged traffic")

            st.banner("Step 17: Verifying Test B - No traffic on VLAN 20 monitor (isolation)")

            vlan20_counters_b = self._get_interface_counters(dut, vlan20_monitor)
            vlan20_pcap_b = self._verify_tcpdump_capture(dut, pcap_vlan20_testB)

            vlan20_verify_b = tagged_verify.get("vlan20_monitor_port", {})
            max_allowed_b = vlan20_verify_b.get("max_packets", 5)

            st.log(f"VLAN 20 monitor: RX_OK={vlan20_counters_b['rx_ok']}, tcpdump={vlan20_pcap_b}")

            if vlan20_counters_b["rx_ok"] > max_allowed_b or vlan20_pcap_b > max_allowed_b:
                st.report_fail("msg", f"VLAN 20 monitor: RX_OK={vlan20_counters_b['rx_ok']}, tcpdump={vlan20_pcap_b} (traffic leaked!)")

            st.log(f"✓ VLAN 20 monitor correctly isolated (no VLAN 10 tagged traffic)")

            st.banner("Step 18: Cleanup")

            # Remove pcap files
            st.show(dut, f"sudo rm -f {pcap_vlan20_testA} {pcap_vlan10_testA} {pcap_vlan20_testB} {pcap_vlan10_testB}",
                   skip_tmpl=True, skip_error_check=True)

            # Remove port configurations
            for port in [hybrid_port, vlan20_monitor, vlan10_monitor]:
                match = re.search(r'Ethernet(\d+)', port)
                if match:
                    intf_num = match.group(1)
                    cleanup_cmds = [
                        f"interface Ethernet {intf_num}",
                        "no switchport access Vlan",
                        "no switchport trunk allowed Vlan 10",
                        "no switchport trunk allowed Vlan 20",
                        "exit"
                    ]
                    st.config(dut, cleanup_cmds, type=self.data.cli_type, skip_error_check=True)

            # Delete VLANs
            for vlan in vlans:
                vlan_api.delete_vlan(dut, vlan.get("id"), cli_type=self.data.cli_type, skip_error_check=True)

            st.log("✓ Cleanup completed")
            st.report_pass("test_case_passed")

        except Exception as e:
            st.error(f"Test failed: {e}")

            if self.data.cleanup_enabled:
                st.log("Performing cleanup after failure")

                self._stop_tcpdump(dut)

                for port in [hybrid_port, vlan20_monitor, vlan10_monitor]:
                    if port:
                        match = re.search(r'Ethernet(\d+)', port)
                        if match:
                            intf_num = match.group(1)
                            cleanup_cmds = [
                                f"interface Ethernet {intf_num}",
                                "no switchport access Vlan",
                                "no switchport trunk allowed Vlan 10",
                                "no switchport trunk allowed Vlan 20",
                                "exit"
                            ]
                            st.config(dut, cleanup_cmds, type=self.data.cli_type, skip_error_check=True)

                for vlan in vlans:
                    vlan_api.delete_vlan(dut, vlan.get("id"), cli_type=self.data.cli_type, skip_error_check=True)

            st.report_fail("msg", f"Test failed: {e}")
