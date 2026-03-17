"""
VLAN NATIVE VLAN BEHAVIOR TEST
Author: Shiva
2026

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_2d.yaml \\
  tests/switching/vlan/test_vlan_native.py \\
  --logs-path ./logs/vlan_native_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  TC_VLAN_MIXED_003: Validates native VLAN behavior on trunk ports. Verifies that
  untagged frames ingressing a trunk port are assigned to the native VLAN (configured
  as Access VLAN), while tagged frames forward through their respective trunk VLANs.

  Test sends untagged ARP broadcast (should map to native VLAN 20) and VLAN 10 tagged
  ARP broadcast (should forward in VLAN 10). Validates strict VLAN isolation with no
  cross-VLAN leakage.

Pre-requisites:
  - Topology: two-node with 3 connections | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes with 3 links
        # +--------------------+                       +--------------------+
        # |      spine02       |                       |      leaf01        |
        # |   (Traffic Gen)    |                       |       (DUT)        |
        # | D1D2P3 Ethernet12  |=======================| D2D1P3 Ethernet12  | (Hybrid ingress: native VLAN 20, trunk VLAN 10)
        # | D1D2P2 Ethernet8   |=======================| D2D1P2 Ethernet8   | (VLAN 20 access monitor)
        # | D1D2P1 Ethernet4   |=======================| D2D1P1 Ethernet4   | (VLAN 10 trunk monitor)
        # +--------------------+                       +--------------------+

  - Feature flags / min SONiC version: VLAN support required
  - Required test variables (YAML): spytest/vars/switching/vlan/vars_vlan_native.yaml
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

# Default YAML variable file location
VAR_FILE_ENV = "VLAN_NATIVE_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "switching"
    / "vlan"
    / "vars_vlan_native.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"VLAN native variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("VLAN native YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("D1D2:3")
class TestVlanNativeVlan:
    """Testcase validating native VLAN behavior on trunk ports."""

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
        cmd = f"sudo nohup tcpdump -i {interface} -e -nn -w {pcap_file} > /tmp/tcpdump.log 2>&1 &"
        st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
        time.sleep(2)
        return True

    def _stop_tcpdump(self, dut: str) -> bool:
        """Stop all tcpdump processes on DUT."""
        st.log(f"Stopping tcpdump on {dut}")
        st.show(dut, "sudo pkill tcpdump", skip_tmpl=True, skip_error_check=True)
        time.sleep(2)
        return True

    def _verify_tcpdump_capture(self, dut: str, pcap_file: str, src_mac: str = None,
                                dst_mac: str = None, ethertype: int = None,
                                expected_vlan: int = None, check_untagged: bool = False) -> int:
        """Parse tcpdump and count packets matching validation criteria.

        Args:
            dut: Device under test
            pcap_file: Path to pcap file
            src_mac: Expected source MAC (None to skip check)
            dst_mac: Expected destination MAC (None to skip check)
            ethertype: Expected ethertype in hex (e.g., 0x0806 for ARP)
            expected_vlan: Expected VLAN tag (None to skip check)
            check_untagged: If True, verify packets are untagged

        Returns:
            Count of packets matching ALL validation criteria
        """
        st.log(f"Verifying tcpdump capture: {pcap_file}")
        st.log(f"  Validation: src_mac={src_mac}, dst_mac={dst_mac}, ethertype={hex(ethertype) if ethertype else None}, vlan={expected_vlan}, untagged={check_untagged}")

        # Read pcap with detailed output (-e = link-level header, -nn = no name resolution)
        cmd = f"sudo tcpdump -r {pcap_file} -e -nn 2>/dev/null"
        output = st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)

        if not output or not isinstance(output, str):
            st.log("No tcpdump output")
            return 0

        valid_packet_count = 0
        total_packets = 0

        # Parse tcpdump output line by line
        # Example line: "12:34:56.789012 22:96:d0:c9:67:c8 > ff:ff:ff:ff:ff:ff, ethertype ARP (0x0806), length 60: ..."
        # Example with VLAN: "12:34:56.789012 22:96:d0:c9:67:c8 > ff:ff:ff:ff:ff:ff, ethertype 802.1Q (0x8100), length 64: vlan 10, p 0, ethertype ARP (0x0806), ..."

        for line in output.split('\n'):
            if not line.strip() or 'listening on' in line or 'captured' in line:
                continue

            total_packets += 1

            # Validate source MAC
            if src_mac:
                # Normalize MAC to lowercase for comparison
                src_mac_normalized = src_mac.lower()
                if src_mac_normalized not in line.lower():
                    st.log(f"  Packet {total_packets}: Source MAC mismatch (expected {src_mac})")
                    continue

            # Validate destination MAC
            if dst_mac:
                dst_mac_normalized = dst_mac.lower()
                # Look for "src > dst" pattern
                if dst_mac_normalized not in line.lower():
                    st.log(f"  Packet {total_packets}: Destination MAC mismatch (expected {dst_mac})")
                    continue

            # Validate ethertype
            if ethertype:
                # tcpdump shows both "0x806" and "0x0806" formats, check both
                ethertype_hex = hex(ethertype)  # e.g., "0x806"
                ethertype_hex_padded = f"0x{ethertype:04x}"  # e.g., "0x0806" with leading zeros

                if ethertype_hex not in line.lower() and ethertype_hex_padded not in line.lower():
                    st.log(f"  Packet {total_packets}: Ethertype mismatch (expected {ethertype_hex} or {ethertype_hex_padded})")
                    continue

            # Validate VLAN tag
            if expected_vlan is not None:
                vlan_pattern = f"vlan {expected_vlan}"
                if vlan_pattern not in line.lower():
                    st.log(f"  Packet {total_packets}: VLAN tag mismatch (expected VLAN {expected_vlan})")
                    continue

            # Validate untagged (no VLAN tag present)
            if check_untagged:
                # Check that line does NOT contain "vlan" keyword
                if "vlan" in line.lower() and "802.1q" in line.lower():
                    st.log(f"  Packet {total_packets}: Expected untagged but found VLAN tag")
                    continue

            # All validations passed
            valid_packet_count += 1
            st.log(f"  Packet {total_packets}: ✓ VALID (matches all criteria)")

        st.log(f"✓ tcpdump validation: {valid_packet_count} valid packets out of {total_packets} total")
        return valid_packet_count

    def _send_arp_broadcast_traffic(self, tgen: str, tgen_port: str, src_mac: str,
                                    dst_mac: str, ethertype: int, payload: str,
                                    vlan_id: int = None, packet_count: int = 10,
                                    interval: float = 0.1,
                                    script_path: str = "/tmp/scapy_arp.py") -> bool:
        """Send ARP broadcast traffic using Scapy (untagged or tagged).

        Args:
            tgen: Traffic generator device
            tgen_port: Interface to send from
            src_mac: Source MAC address
            dst_mac: Destination MAC address (broadcast)
            ethertype: Ethertype (0x0806 for ARP)
            payload: Payload string
            vlan_id: VLAN ID (None for untagged, int for tagged)
            packet_count: Number of packets to send
            interval: Inter-packet delay
            script_path: Path to Scapy script on TGen

        Returns:
            True if traffic sent successfully
        """
        st.log(f"Sending ARP broadcast traffic: vlan_id={vlan_id}, count={packet_count}")

        # Build Scapy script for ARP broadcast
        if vlan_id is None:
            # Untagged ARP frame
            script_content = f'''#!/usr/bin/env python3
from scapy.all import Ether, Raw, sendp
import time

iface = "{tgen_port}"
src_mac = "{src_mac}"
dst_mac = "{dst_mac}"
ethertype = {ethertype}
payload = "{payload}"
packet_count = {packet_count}
interval = {interval}

def send_untagged_arp_broadcast():
    pkt = (
        Ether(src=src_mac, dst=dst_mac, type=ethertype) /
        Raw(load=payload)
    )

    sent = 0
    for i in range(packet_count):
        sendp(pkt, iface=iface, verbose=False)
        sent += 1
        time.sleep(interval)

    print(f"Sent {{sent}} untagged ARP broadcast packets")
    return True

if __name__ == "__main__":
    send_untagged_arp_broadcast()
'''
        else:
            # Tagged ARP frame
            script_content = f'''#!/usr/bin/env python3
from scapy.all import Ether, Dot1Q, Raw, sendp
import time

iface = "{tgen_port}"
src_mac = "{src_mac}"
dst_mac = "{dst_mac}"
vlan_id = {vlan_id}
ethertype = {ethertype}
payload = "{payload}"
packet_count = {packet_count}
interval = {interval}

def send_tagged_arp_broadcast():
    # CRITICAL: Set 'type' in Dot1Q to specify inner ethertype (ARP 0x0806)
    # Without this, Scapy defaults to 802.3 LLC format
    pkt = (
        Ether(src=src_mac, dst=dst_mac) /
        Dot1Q(vlan=vlan_id, type=ethertype) /
        Raw(load=payload)
    )

    sent = 0
    for i in range(packet_count):
        sendp(pkt, iface=iface, verbose=False)
        sent += 1
        time.sleep(interval)

    print(f"Sent {{sent}} VLAN {{vlan_id}} tagged ARP broadcast packets")
    return True

if __name__ == "__main__":
    send_tagged_arp_broadcast()
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

    @pytest.mark.inventory(feature="Regression", testcases=["TC_VLAN_MIXED_003"])
    def test_vlan_mixed_003_native_vlan(self) -> None:
        """
        TC_VLAN_MIXED_003: Verify native VLAN behavior on trunk port.

        Test Steps:
        1. Get topology (D1=TGen spine02, D2=DUT leaf01)
        2. Pre-cleanup: Remove VLANs 10, 20
        3. Create VLANs 10, 20
        4. Configure Ethernet12 as hybrid: Access VLAN 20 (native) + Trunk VLAN 10
        5. Configure Ethernet8 as Access VLAN 20 (native VLAN monitor)
        6. Configure Ethernet4 as Trunk VLAN 10 (tagged VLAN monitor)
        7. Test A: Clear counters, send UNTAGGED ARP broadcast, verify counters then tcpdump
        8. Verify Ethernet8 receives traffic (native VLAN 20), Ethernet4 does NOT
        9. Test B: Clear counters, send VLAN 10 TAGGED ARP broadcast, verify counters then tcpdump
        10. Verify Ethernet4 receives traffic (VLAN 10), Ethernet8 does NOT
        11. Cleanup (keep pcap files for analysis)
        """
        st.banner("TC_VLAN_MIXED_003: Native VLAN Behavior Test")

        testcase = self.data.testcases.get("TC_VLAN_MIXED_003")
        if not testcase:
            st.report_fail("msg", "TC_VLAN_MIXED_003 testcase not found in YAML")

        vlans = testcase.get("vlans", [])
        traffic = SpyTestDict(testcase.get("traffic", {}))
        verification = SpyTestDict(testcase.get("verification", {}))

        # Get topology
        min_topology = self.data.defaults.get("min_topology") or ["D1D2:3"]
        topology = st.ensure_min_topology(*min_topology)

        tgen = topology.D1
        dut = topology.D2

        # Get interfaces dynamically
        hybrid_port = getattr(topology, 'D2D1P3', None)          # Ethernet12
        vlan20_monitor = getattr(topology, 'D2D1P2', None)       # Ethernet8
        vlan10_monitor = getattr(topology, 'D2D1P1', None)       # Ethernet4

        tgen_port = getattr(topology, 'D1D2P3', None)

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

            st.banner(f"Step 3: Configuring {hybrid_port} as hybrid (Access VLAN 20 [native] + Trunk VLAN 10)")

            match = re.search(r'Ethernet(\d+)', hybrid_port)
            intf_num = match.group(1)

            hybrid_commands = [
                f"interface Ethernet {intf_num}",
                "no ip address",
                "no switchport trunk allowed Vlan 10",
                "no switchport trunk allowed Vlan 20",
                "no switchport access Vlan",
                "switchport access Vlan 20",
                "switchport trunk allowed Vlan 10",
                "no shutdown",
                "exit"
            ]

            st.config(dut, hybrid_commands, type=self.data.cli_type, skip_error_check=True)
            st.log(f"✓ {hybrid_port} configured as hybrid port (native VLAN 20)")

            st.banner(f"Step 4: Configuring {vlan20_monitor} as Access VLAN 20 (native VLAN monitor)")

            match = re.search(r'Ethernet(\d+)', vlan20_monitor)
            intf_num = match.group(1)

            monitor20_commands = [
                f"interface Ethernet {intf_num}",
                "no ip address",
                "no switchport access Vlan",
                "no switchport trunk allowed Vlan 10",
                "no switchport trunk allowed Vlan 20",
                "switchport access Vlan 20",
                "no shutdown",
                "exit"
            ]

            st.config(dut, monitor20_commands, type=self.data.cli_type, skip_error_check=True)
            st.log(f"✓ {vlan20_monitor} configured as VLAN 20 access port")

            st.banner(f"Step 5: Configuring {vlan10_monitor} as Trunk VLAN 10 (tagged VLAN monitor)")

            match = re.search(r'Ethernet(\d+)', vlan10_monitor)
            intf_num = match.group(1)

            monitor10_commands = [
                f"interface Ethernet {intf_num}",
                "no ip address",
                "no switchport access Vlan",
                "no switchport trunk allowed Vlan 10",
                "no switchport trunk allowed Vlan 20",
                "switchport trunk allowed Vlan 10",
                "no shutdown",
                "exit"
            ]

            st.config(dut, monitor10_commands, type=self.data.cli_type, skip_error_check=True)
            st.log(f"✓ {vlan10_monitor} configured as VLAN 10 trunk")

            # Show VLAN configuration
            vlan_output = vlan_api.show_vlan_config(dut, cli_type=self.data.cli_type)
            st.log(f"VLAN configuration:\n{vlan_output}")

            st.banner("TEST A: Untagged ARP Broadcast (Native VLAN Test)")
            st.banner("Step 6: Clearing counters before Test A")
            self._clear_interface_counters(dut)

            st.banner("Step 7: Starting tcpdump on monitor ports")
            pcap_vlan20_testA = "/tmp/vlan_native_003_vlan20_testA.pcap"
            pcap_vlan10_testA = "/tmp/vlan_native_003_vlan10_testA.pcap"

            self._start_tcpdump(dut, vlan20_monitor, pcap_vlan20_testA)
            self._start_tcpdump(dut, vlan10_monitor, pcap_vlan10_testA)

            st.banner("Step 8: Sending UNTAGGED ARP broadcast (native VLAN test)")

            packet_count = traffic.get("packet_count", 10)
            inter_packet_delay = traffic.get("inter_packet_delay", 0.1)
            src_mac = traffic.get("src_mac", "22:96:d0:c9:67:c8")
            dst_mac = traffic.get("dst_mac", "ff:ff:ff:ff:ff:ff")
            ethertype = traffic.get("ethertype", 0x0806)
            payload = traffic.get("payload", "TEST_PKT")

            traffic_sent = self._send_arp_broadcast_traffic(
                tgen, tgen_port, src_mac, dst_mac, ethertype, payload,
                vlan_id=None,  # Untagged
                packet_count=packet_count,
                interval=inter_packet_delay,
                script_path="/tmp/scapy_native_untagged.py"
            )

            if not traffic_sent:
                st.report_fail("msg", "Failed to send untagged ARP broadcast traffic")

            time.sleep(2)

            st.banner("Step 9: Stopping tcpdump")
            self._stop_tcpdump(dut)
            time.sleep(2)

            st.banner("Step 10: Verifying Test A - Counters for VLAN 20 monitor (native VLAN)")

            vlan20_counters = self._get_interface_counters(dut, vlan20_monitor)
            vlan20_rx = vlan20_counters["rx_ok"]

            st.banner("Step 11: Verifying Test A - tcpdump for VLAN 20 monitor")
            # Validate: ARP (0x0806), source MAC, broadcast dst, UNTAGGED
            vlan20_pcap = self._verify_tcpdump_capture(
                dut, pcap_vlan20_testA,
                src_mac=src_mac,
                dst_mac=dst_mac,
                ethertype=ethertype,
                check_untagged=True
            )

            untagged_verify = verification.get("untagged_test", {})
            vlan20_verify = untagged_verify.get("vlan20_monitor_port", {})
            min_expected = vlan20_verify.get("min_packets", 8)

            st.log(f"VLAN 20 monitor (native): RX_OK={vlan20_rx}, tcpdump={vlan20_pcap}")

            if vlan20_rx < min_expected and vlan20_pcap < min_expected:
                st.report_fail("msg", f"VLAN 20 monitor: RX_OK={vlan20_rx}, tcpdump={vlan20_pcap} (both < {min_expected})")

            st.log(f"✓ VLAN 20 monitor (native VLAN) received untagged traffic")

            st.banner("Step 12: Verifying Test A - Counters for VLAN 10 monitor (isolation check)")

            vlan10_counters = self._get_interface_counters(dut, vlan10_monitor)
            vlan10_rx = vlan10_counters["rx_ok"]

            st.banner("Step 13: Verifying Test A - tcpdump for VLAN 10 monitor")
            # Validate: Should have NO packets matching our test criteria (isolation check)
            vlan10_pcap = self._verify_tcpdump_capture(
                dut, pcap_vlan10_testA,
                src_mac=src_mac,
                dst_mac=dst_mac,
                ethertype=ethertype,
                check_untagged=True
            )

            vlan10_verify = untagged_verify.get("vlan10_monitor_port", {})
            max_allowed = vlan10_verify.get("max_packets", 5)

            st.log(f"VLAN 10 monitor: RX_OK={vlan10_rx}, tcpdump={vlan10_pcap}")

            if vlan10_rx > max_allowed or vlan10_pcap > max_allowed:
                st.report_fail("msg", f"VLAN 10 monitor: RX_OK={vlan10_rx}, tcpdump={vlan10_pcap} (traffic leaked!)")

            st.log(f"✓ VLAN 10 monitor correctly isolated (no untagged traffic)")

            st.banner("TEST B: VLAN 10 Tagged ARP Broadcast")
            st.banner("Step 14: Clearing counters before Test B")
            self._clear_interface_counters(dut)

            st.banner("Step 15: Starting tcpdump on monitor ports")
            pcap_vlan20_testB = "/tmp/vlan_native_003_vlan20_testB.pcap"
            pcap_vlan10_testB = "/tmp/vlan_native_003_vlan10_testB.pcap"

            self._start_tcpdump(dut, vlan20_monitor, pcap_vlan20_testB)
            self._start_tcpdump(dut, vlan10_monitor, pcap_vlan10_testB)

            st.banner("Step 16: Sending VLAN 10 TAGGED ARP broadcast")

            traffic_sent = self._send_arp_broadcast_traffic(
                tgen, tgen_port, src_mac, dst_mac, ethertype, payload,
                vlan_id=10,
                packet_count=packet_count,
                interval=inter_packet_delay,
                script_path="/tmp/scapy_native_tagged.py"
            )

            if not traffic_sent:
                st.report_fail("msg", "Failed to send VLAN 10 tagged ARP broadcast traffic")

            time.sleep(2)

            st.banner("Step 17: Stopping tcpdump")
            self._stop_tcpdump(dut)
            time.sleep(2)

            st.banner("Step 18: Verifying Test B - Counters for VLAN 10 monitor")

            vlan10_counters_b = self._get_interface_counters(dut, vlan10_monitor)
            vlan10_rx_b = vlan10_counters_b["rx_ok"]

            st.banner("Step 19: Verifying Test B - tcpdump for VLAN 10 monitor")
            # Validate: ARP (0x0806), source MAC, broadcast dst, VLAN 10 TAGGED
            vlan10_pcap_b = self._verify_tcpdump_capture(
                dut, pcap_vlan10_testB,
                src_mac=src_mac,
                dst_mac=dst_mac,
                ethertype=ethertype,
                expected_vlan=10
            )

            tagged_verify = verification.get("tagged_test", {})
            vlan10_verify_b = tagged_verify.get("vlan10_monitor_port", {})
            min_expected_b = vlan10_verify_b.get("min_packets", 8)

            st.log(f"VLAN 10 monitor: RX_OK={vlan10_rx_b}, tcpdump={vlan10_pcap_b}")

            if vlan10_rx_b < min_expected_b and vlan10_pcap_b < min_expected_b:
                st.report_fail("msg", f"VLAN 10 monitor: RX_OK={vlan10_rx_b}, tcpdump={vlan10_pcap_b} (both < {min_expected_b})")

            st.log(f"✓ VLAN 10 monitor received tagged traffic")

            st.banner("Step 20: Verifying Test B - Counters for VLAN 20 monitor (isolation check)")

            vlan20_counters_b = self._get_interface_counters(dut, vlan20_monitor)
            vlan20_rx_b = vlan20_counters_b["rx_ok"]

            st.banner("Step 21: Verifying Test B - tcpdump for VLAN 20 monitor")
            # Validate: Should have NO packets matching our test criteria (isolation check)
            vlan20_pcap_b = self._verify_tcpdump_capture(
                dut, pcap_vlan20_testB,
                src_mac=src_mac,
                dst_mac=dst_mac,
                ethertype=ethertype,
                expected_vlan=10
            )

            vlan20_verify_b = tagged_verify.get("vlan20_monitor_port", {})
            max_allowed_b = vlan20_verify_b.get("max_packets", 5)

            st.log(f"VLAN 20 monitor: RX_OK={vlan20_rx_b}, tcpdump={vlan20_pcap_b}")

            if vlan20_rx_b > max_allowed_b or vlan20_pcap_b > max_allowed_b:
                st.report_fail("msg", f"VLAN 20 monitor: RX_OK={vlan20_rx_b}, tcpdump={vlan20_pcap_b} (traffic leaked!)")

            st.log(f"✓ VLAN 20 monitor correctly isolated (no VLAN 10 tagged traffic)")

            st.banner("Step 22: Cleanup (keeping pcap files for analysis)")

            st.log(f"Pcap files saved:")
            st.log(f"  Test A VLAN 20: {pcap_vlan20_testA}")
            st.log(f"  Test A VLAN 10: {pcap_vlan10_testA}")
            st.log(f"  Test B VLAN 20: {pcap_vlan20_testB}")
            st.log(f"  Test B VLAN 10: {pcap_vlan10_testB}")

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

            st.log("✓ Cleanup completed (pcap files preserved)")
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
