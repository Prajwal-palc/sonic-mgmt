"""
VLAN TRUNK PORT SEGREGATION TESTS
Author: Shiva
2026

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_2d.yaml \\
  tests/switching/vlan/test_vlan_trunk_segregation.py \\
  --logs-path ./logs/vlan_trunk_seg_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  TC_VLAN_TRUNK_002: Validates VLAN 10 traffic segregation on trunk ports
  TC_VLAN_TRUNK_003: Validates VLAN 20 traffic segregation on trunk ports

  Both tests configure a trunk port carrying VLANs 10 and 20, with two access ports
  (one in VLAN 10, one in VLAN 20). Tests send VLAN-tagged ICMP traffic and verify:
  - Correct VLAN access port receives traffic (counters + tcpdump)
  - Other VLAN access port does NOT receive traffic (counters + tcpdump)

Pre-requisites:
  - Topology: two-node with 3 connections | Supported: HW and Virtual
  - Feature flags / min SONiC version: VLAN support required
  - Required test variables (YAML): spytest/vars/switching/vlan/vars_vlan_trunk_002.yaml
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
VAR_FILE_ENV = "VLAN_TRUNK_SEG_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "switching"
    / "vlan"
    / "vars_vlan_trunk_002.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"VLAN trunk segregation variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("VLAN trunk segregation YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("D1D2:3")
class TestVlanTrunkSegregation:
    """Testcases validating VLAN segregation on trunk ports."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        min_topology = defaults.get("min_topology") or ["D1D2:3"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

    @classmethod
    def teardown_class(cls) -> None:
        """Clean up VLANs and port configurations after the suite completes."""
        if not cls.data.cleanup_enabled:
            return

    def setup_method(self) -> None:
        """Reset per-test bookkeeping."""
        pass

    def teardown_method(self) -> None:
        """Remove VLANs and reset port configurations after each test."""
        if not self.data.cleanup_enabled:
            return

    def _clear_interface_counters(self, dut: str) -> bool:
        """Clear interface counters on the DUT."""
        st.log(f"Clearing interface counters on {dut}")

        try:
            cmd = "clear interface counters"
            st.config(dut, cmd, type=self.data.cli_type, skip_error_check=True, conf=False)
            time.sleep(2)
            st.log("✓ Interface counters cleared")
            return True

        except Exception as e:
            st.error(f"Failed to clear counters: {e}")
            return False

    def _get_interface_counters(self, dut: str, interface: str) -> Dict[str, int]:
        """Get RX/TX counters for an interface, parsing raw output to handle line wrapping."""
        st.log(f"Getting interface counters for {interface} on {dut}")

        try:
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
                        try:
                            if len(parts) >= 10:
                                rx_ok_str = parts[2].replace(",", "")
                                tx_ok_str = parts[9].replace(",", "")
                                counters["rx_ok"] = int(rx_ok_str)
                                counters["tx_ok"] = int(tx_ok_str)
                                break
                        except (ValueError, IndexError) as e:
                            st.log(f"Failed to parse line: {line}, error: {e}")
                            continue

            st.log(f"✓ Counters for {interface}: RX_OK={counters['rx_ok']}, TX_OK={counters['tx_ok']}")
            return counters

        except Exception as e:
            st.error(f"Failed to get counters for {interface}: {e}")
            return {"rx_ok": 0, "tx_ok": 0}

    def _start_tcpdump(self, dut: str, interface: str, vlan_id: int, pcap_file: str) -> bool:
        """Start tcpdump on the DUT interface to capture ICMP traffic."""
        st.log(f"Starting tcpdump on {dut}:{interface} (VLAN {vlan_id} filter)")

        try:
            st.show(dut, f"sudo rm -f {pcap_file}", skip_tmpl=True, skip_error_check=True)

            cmd = f"sudo nohup tcpdump -i {interface} icmp -w {pcap_file} > /tmp/tcpdump.log 2>&1 &"
            st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)

            time.sleep(2)
            st.log(f"✓ tcpdump started on {interface}")
            return True

        except Exception as e:
            st.error(f"Failed to start tcpdump: {e}")
            return False

    def _stop_tcpdump(self, dut: str) -> bool:
        """Stop tcpdump on the DUT."""
        st.log(f"Stopping tcpdump on {dut}")

        try:
            st.show(dut, "sudo pkill tcpdump", skip_tmpl=True, skip_error_check=True)
            time.sleep(2)
            st.log("✓ tcpdump stopped")
            return True

        except Exception as e:
            st.error(f"Failed to stop tcpdump: {e}")
            return False

    def _verify_tcpdump_capture(self, dut: str, pcap_file: str) -> int:
        """Verify tcpdump captured packets and return packet count."""
        st.log(f"Verifying tcpdump capture: {pcap_file}")

        try:
            cmd = f"sudo tcpdump -r {pcap_file} 2>/dev/null | wc -l"
            output = st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)

            packet_count = 0
            if output and isinstance(output, str):
                match = re.search(r'(\d+)', output)
                if match:
                    packet_count = int(match.group(1))

            st.log(f"✓ tcpdump captured {packet_count} packets")
            return packet_count

        except Exception as e:
            st.error(f"Failed to verify tcpdump capture: {e}")
            return 0

    def _send_tagged_icmp_traffic(
        self,
        tgen: str,
        tgen_port: str,
        src_mac: str,
        dst_mac: str,
        src_ip: str,
        dst_ip: str,
        vlan_id: int,
        packet_count: int,
        inter_packet_delay: float,
        script_path: str
    ) -> bool:
        """Send 802.1Q tagged ICMP traffic using Scapy on the traffic generator."""
        st.log(f"Sending {packet_count} VLAN {vlan_id} tagged ICMP packets from {tgen}:{tgen_port}")
        st.log(f"  SRC: {src_mac} / {src_ip}")
        st.log(f"  DST: {dst_mac} / {dst_ip}")

        script_content = f'''#!/usr/bin/env python3
"""Scapy VLAN ICMP Traffic Generator - Auto-generated by SPyTest"""

from scapy.all import Ether, Dot1Q, IP, ICMP, sendp
import time
import sys

iface = "{tgen_port}"
src_mac = "{src_mac}"
dst_mac = "{dst_mac}"
src_ip = "{src_ip}"
dst_ip = "{dst_ip}"
vlan_id = {vlan_id}
packet_count = {packet_count}
interval = {inter_packet_delay}

def send_tagged_icmp_traffic():
    """Send 802.1Q tagged ICMP packets."""
    print(f"[+] Starting VLAN {{vlan_id}} ICMP Traffic Generation")
    print(f"    Interface:    {{iface}}")
    print(f"    Source:       {{src_mac}} / {{src_ip}}")
    print(f"    Destination:  {{dst_mac}} / {{dst_ip}}")
    print(f"    Packet Count: {{packet_count}}")
    print()

    pkt = (
        Ether(src=src_mac, dst=dst_mac) /
        Dot1Q(vlan=vlan_id) /
        IP(src=src_ip, dst=dst_ip) /
        ICMP()
    )

    sent = 0
    try:
        for i in range(packet_count):
            sendp(pkt, iface=iface, verbose=False)
            sent += 1
            print(f"[→] Sent {{sent}}/{{packet_count}} packets...", end='\\r')
            time.sleep(interval)

    except Exception as e:
        print(f"\\n[✗] Error: {{e}}")
        return False

    print(f"\\n[✓] Completed. Sent {{sent}} ICMP packets (VLAN {{vlan_id}})")
    return True

if __name__ == "__main__":
    success = send_tagged_icmp_traffic()
    sys.exit(0 if success else 1)
'''

        try:
            st.show(tgen, f"rm -f {script_path}", skip_tmpl=True, skip_error_check=True)

            cmd = f"cat > {script_path} << 'EOFSCAPY'\n{script_content}\nEOFSCAPY"
            st.show(tgen, cmd, skip_tmpl=True, skip_error_check=True)

            st.show(tgen, f"chmod +x {script_path}", skip_tmpl=True, skip_error_check=True)

            output = st.show(tgen, f"sudo python3 {script_path}", skip_tmpl=True, skip_error_check=True)
            st.log(f"Traffic generation output:\n{output}")

            st.show(tgen, f"rm -f {script_path}", skip_tmpl=True, skip_error_check=True)

            st.log(f"✓ Sent {packet_count} VLAN {vlan_id} tagged ICMP packets")
            return True

        except Exception as e:
            st.error(f"Failed to send ICMP traffic: {e}")
            return False

    @pytest.mark.inventory(feature="Regression", testcases=["TC_VLAN_TRUNK_002"])
    def test_vlan_trunk_002_vlan10_segregation(self) -> None:
        """
        TC_VLAN_TRUNK_002: Verify VLAN 10 traffic reaches VLAN 10 access port only.

        Test Steps:
        1. Discover topology and port connections
        2. Create VLANs 10 and 20 on DUT
        3. Configure Ethernet12 as trunk port (VLANs 10, 20)
        4. Configure Ethernet8 as access port VLAN 10
        5. Configure Ethernet4 as access port VLAN 20
        6. Clear interface counters
        7. Start tcpdump on both access ports
        8. Send VLAN 10 tagged ICMP traffic from TGen
        9. Stop tcpdump
        10. Verify Ethernet8 receives traffic (counters + tcpdump)
        11. Verify Ethernet4 does NOT receive traffic (counters + tcpdump)
        12. Cleanup
        """
        st.banner("TC_VLAN_TRUNK_002: VLAN 10 Traffic Segregation Test")

        testcase = self.data.testcases.get("TC_VLAN_TRUNK_002")
        if not testcase:
            st.report_fail("msg", "TC_VLAN_TRUNK_002 testcase not found in YAML")

        vlans = testcase.get("vlans", [])
        ports = SpyTestDict(testcase.get("ports", {}))
        traffic = SpyTestDict(testcase.get("traffic", {}))
        verification = SpyTestDict(testcase.get("verification", {}))

        st.banner("Step 1: Discovering topology")

        topology = self.data.topology
        tgen = topology.D1
        dut = topology.D2

        trunk_port = getattr(topology, 'D2D1P1', None)
        access_vlan10_port = getattr(topology, 'D2D1P2', None)
        access_vlan20_port = getattr(topology, 'D2D1P3', None)

        if not trunk_port or not access_vlan10_port or not access_vlan20_port:
            st.report_fail("msg", "Failed to discover topology (need 3 links)")

        tgen_trunk_port = getattr(topology, 'D1D2P1', None)

        st.log(f"✓ Topology: TGen={tgen}, DUT={dut}")
        st.log(f"  Trunk: {trunk_port}, Access VLAN10: {access_vlan10_port}, Access VLAN20: {access_vlan20_port}")

        try:
            st.banner("Step 2: Creating VLANs on DUT")

            cleanup_commands = []
            for port in [trunk_port, access_vlan10_port, access_vlan20_port]:
                if "Ethernet" in port:
                    intf_num = port.replace("Ethernet", "")
                    cleanup_commands.append(f"interface Ethernet {intf_num}")
                    cleanup_commands.append("no switchport access Vlan")
                    for vlan in vlans:
                        vlan_id = vlan.get("id")
                        cleanup_commands.append(f"no switchport trunk allowed Vlan {vlan_id}")
                    cleanup_commands.append("exit")

            st.config(dut, cleanup_commands, type=self.data.cli_type, skip_error_check=True)

            for vlan in vlans:
                vlan_id = vlan.get("id")
                vlan_api.delete_vlan(dut, vlan_id, cli_type=self.data.cli_type, skip_error_check=True)

                if not vlan_api.create_vlan(dut, vlan_id, cli_type=self.data.cli_type):
                    st.report_fail("msg", f"Failed to create VLAN {vlan_id}")

                st.log(f"✓ VLAN {vlan_id} created")

            st.banner(f"Step 3: Configuring trunk port {trunk_port}")

            trunk_commands = []
            if "Ethernet" in trunk_port:
                intf_num = trunk_port.replace("Ethernet", "")
                trunk_commands.append(f"interface Ethernet {intf_num}")

            trunk_commands.append("no ip address")
            trunk_commands.append("no switchport access Vlan")

            for vlan in vlans:
                vlan_id = vlan.get("id")
                trunk_commands.append(f"switchport trunk allowed Vlan {vlan_id}")

            trunk_commands.append("end")
            st.config(dut, trunk_commands, type=self.data.cli_type, skip_error_check=True)

            st.log(f"✓ Trunk port configured with VLANs: {[v['id'] for v in vlans]}")

            st.banner(f"Step 4: Configuring access port {access_vlan10_port} (VLAN 10)")

            access10_commands = []
            if "Ethernet" in access_vlan10_port:
                intf_num = access_vlan10_port.replace("Ethernet", "")
                access10_commands.append(f"interface Ethernet {intf_num}")

            access10_commands.append("no ip address")
            access10_commands.append("no switchport trunk allowed Vlan 10")
            access10_commands.append("switchport access Vlan 10")
            access10_commands.append("end")

            st.config(dut, access10_commands, type=self.data.cli_type, skip_error_check=True)
            st.log(f"✓ {access_vlan10_port} configured as VLAN 10 access port")

            st.banner(f"Step 5: Configuring access port {access_vlan20_port} (VLAN 20)")

            access20_commands = []
            if "Ethernet" in access_vlan20_port:
                intf_num = access_vlan20_port.replace("Ethernet", "")
                access20_commands.append(f"interface Ethernet {intf_num}")

            access20_commands.append("no ip address")
            access20_commands.append("no switchport trunk allowed Vlan 20")
            access20_commands.append("switchport access Vlan 20")
            access20_commands.append("end")

            st.config(dut, access20_commands, type=self.data.cli_type, skip_error_check=True)
            st.log(f"✓ {access_vlan20_port} configured as VLAN 20 access port")

            vlan_output = vlan_api.show_vlan_config(dut, cli_type=self.data.cli_type)
            st.log(f"VLAN configuration:\n{vlan_output}")

            st.banner("Step 6: Clearing interface counters")
            self._clear_interface_counters(dut)

            st.banner("Step 7: Starting tcpdump on access ports")

            pcap_vlan10 = "/tmp/vlan_trunk_002_vlan10.pcap"
            pcap_vlan20 = "/tmp/vlan_trunk_002_vlan20.pcap"

            self._start_tcpdump(dut, access_vlan10_port, 10, pcap_vlan10)
            self._start_tcpdump(dut, access_vlan20_port, 20, pcap_vlan20)

            st.banner("Step 8: Sending VLAN 10 tagged ICMP traffic")

            packet_count = traffic.get("packet_count", 20)
            vlan_id = traffic.get("vlan_id", 10)
            dst_mac = traffic.get("dst_mac", "ff:ff:ff:ff:ff:ff")
            src_ip = traffic.get("src_ip", "192.168.10.1")
            dst_ip = traffic.get("dst_ip", "192.168.10.2")
            inter_packet_delay = traffic.get("inter_packet_delay", 0.05)

            src_mac = "00:11:22:33:44:55"
            script_path = "/tmp/scapy_vlan_002.py"

            traffic_sent = self._send_tagged_icmp_traffic(
                tgen, tgen_trunk_port, src_mac, dst_mac,
                src_ip, dst_ip, vlan_id, packet_count,
                inter_packet_delay, script_path
            )

            if not traffic_sent:
                st.report_fail("msg", "Failed to send ICMP traffic")

            time.sleep(2)

            st.banner("Step 9: Stopping tcpdump")
            self._stop_tcpdump(dut)
            time.sleep(2)

            st.banner("Step 10: Verifying VLAN 10 access port receives traffic")

            vlan10_counters = self._get_interface_counters(dut, access_vlan10_port)
            vlan10_rx = vlan10_counters["rx_ok"]

            vlan10_pcap_count = self._verify_tcpdump_capture(dut, pcap_vlan10)

            vlan10_verify = verification.get("vlan10_access_port", {})
            min_expected = vlan10_verify.get("min_packets", 15)

            st.log(f"VLAN 10 access port: RX_OK={vlan10_rx}, tcpdump={vlan10_pcap_count}")

            if vlan10_rx < min_expected and vlan10_pcap_count < min_expected:
                st.report_fail("msg", f"VLAN 10 port: RX_OK={vlan10_rx}, tcpdump={vlan10_pcap_count} (both < {min_expected})")

            st.log(f"✓ VLAN 10 port received traffic: RX_OK={vlan10_rx}, tcpdump={vlan10_pcap_count}")

            st.banner("Step 11: Verifying VLAN 20 access port does NOT receive traffic")

            vlan20_counters = self._get_interface_counters(dut, access_vlan20_port)
            vlan20_rx = vlan20_counters["rx_ok"]

            vlan20_pcap_count = self._verify_tcpdump_capture(dut, pcap_vlan20)

            vlan20_verify = verification.get("vlan20_access_port", {})
            max_allowed = vlan20_verify.get("max_packets", 5)

            st.log(f"VLAN 20 access port: RX_OK={vlan20_rx}, tcpdump={vlan20_pcap_count}")

            if vlan20_rx > max_allowed or vlan20_pcap_count > max_allowed:
                st.report_fail("msg", f"VLAN 20 port: RX_OK={vlan20_rx}, tcpdump={vlan20_pcap_count} (traffic leaked!)")

            st.log(f"✓ VLAN 20 port correctly rejected traffic: RX_OK={vlan20_rx}, tcpdump={vlan20_pcap_count}")

            st.banner("Step 12: Cleanup")

            st.show(dut, f"sudo rm -f {pcap_vlan10} {pcap_vlan20}", skip_tmpl=True, skip_error_check=True)

            for port in [access_vlan10_port, access_vlan20_port]:
                if "Ethernet" in port:
                    intf_num = port.replace("Ethernet", "")
                    st.config(dut, [f"interface Ethernet {intf_num}", "no switchport access Vlan", "exit"],
                             type=self.data.cli_type, skip_error_check=True)

            if "Ethernet" in trunk_port:
                intf_num = trunk_port.replace("Ethernet", "")
                trunk_cleanup = [f"interface Ethernet {intf_num}"]
                for vlan in vlans:
                    trunk_cleanup.append(f"no switchport trunk allowed Vlan {vlan.get('id')}")
                trunk_cleanup.append("exit")
                st.config(dut, trunk_cleanup, type=self.data.cli_type, skip_error_check=True)

            for vlan in vlans:
                vlan_api.delete_vlan(dut, vlan.get("id"), cli_type=self.data.cli_type, skip_error_check=True)

            st.log("✓ Cleanup completed")
            st.report_pass("test_case_passed")

        except Exception as e:
            st.error(f"Test failed: {e}")

            if self.data.cleanup_enabled:
                self._stop_tcpdump(dut)

                for port in [access_vlan10_port, access_vlan20_port, trunk_port]:
                    if "Ethernet" in port:
                        intf_num = port.replace("Ethernet", "")
                        cleanup_cmds = [f"interface Ethernet {intf_num}", "no switchport access Vlan"]
                        for vlan in vlans:
                            cleanup_cmds.append(f"no switchport trunk allowed Vlan {vlan.get('id')}")
                        cleanup_cmds.append("exit")
                        st.config(dut, cleanup_cmds, type=self.data.cli_type, skip_error_check=True)

                for vlan in vlans:
                    vlan_api.delete_vlan(dut, vlan.get("id"), cli_type=self.data.cli_type, skip_error_check=True)

            st.report_fail("msg", f"Test failed: {e}")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_VLAN_TRUNK_003"])
    def test_vlan_trunk_003_vlan20_segregation(self) -> None:
        """
        TC_VLAN_TRUNK_003: Verify VLAN 20 traffic reaches VLAN 20 access port only.

        Test Steps: Same as TC_002 but with VLAN 20 traffic
        """
        st.banner("TC_VLAN_TRUNK_003: VLAN 20 Traffic Segregation Test")

        testcase = self.data.testcases.get("TC_VLAN_TRUNK_003")
        if not testcase:
            st.report_fail("msg", "TC_VLAN_TRUNK_003 testcase not found in YAML")

        vlans = testcase.get("vlans", [])
        ports = SpyTestDict(testcase.get("ports", {}))
        traffic = SpyTestDict(testcase.get("traffic", {}))
        verification = SpyTestDict(testcase.get("verification", {}))

        st.banner("Step 1: Discovering topology")

        topology = self.data.topology
        tgen = topology.D1
        dut = topology.D2

        trunk_port = getattr(topology, 'D2D1P1', None)
        access_vlan10_port = getattr(topology, 'D2D1P2', None)
        access_vlan20_port = getattr(topology, 'D2D1P3', None)

        if not trunk_port or not access_vlan10_port or not access_vlan20_port:
            st.report_fail("msg", "Failed to discover topology (need 3 links)")

        tgen_trunk_port = getattr(topology, 'D1D2P1', None)

        st.log(f"✓ Topology: TGen={tgen}, DUT={dut}")
        st.log(f"  Trunk: {trunk_port}, Access VLAN10: {access_vlan10_port}, Access VLAN20: {access_vlan20_port}")

        try:
            st.banner("Step 2: Creating VLANs on DUT")

            cleanup_commands = []
            for port in [trunk_port, access_vlan10_port, access_vlan20_port]:
                if "Ethernet" in port:
                    intf_num = port.replace("Ethernet", "")
                    cleanup_commands.append(f"interface Ethernet {intf_num}")
                    cleanup_commands.append("no switchport access Vlan")
                    for vlan in vlans:
                        vlan_id = vlan.get("id")
                        cleanup_commands.append(f"no switchport trunk allowed Vlan {vlan_id}")
                    cleanup_commands.append("exit")

            st.config(dut, cleanup_commands, type=self.data.cli_type, skip_error_check=True)

            for vlan in vlans:
                vlan_id = vlan.get("id")
                vlan_api.delete_vlan(dut, vlan_id, cli_type=self.data.cli_type, skip_error_check=True)

                if not vlan_api.create_vlan(dut, vlan_id, cli_type=self.data.cli_type):
                    st.report_fail("msg", f"Failed to create VLAN {vlan_id}")

                st.log(f"✓ VLAN {vlan_id} created")

            st.banner(f"Step 3: Configuring trunk port {trunk_port}")

            trunk_commands = []
            if "Ethernet" in trunk_port:
                intf_num = trunk_port.replace("Ethernet", "")
                trunk_commands.append(f"interface Ethernet {intf_num}")

            trunk_commands.append("no ip address")
            trunk_commands.append("no switchport access Vlan")

            for vlan in vlans:
                vlan_id = vlan.get("id")
                trunk_commands.append(f"switchport trunk allowed Vlan {vlan_id}")

            trunk_commands.append("end")
            st.config(dut, trunk_commands, type=self.data.cli_type, skip_error_check=True)

            st.log(f"✓ Trunk port configured with VLANs: {[v['id'] for v in vlans]}")

            st.banner(f"Step 4: Configuring access port {access_vlan10_port} (VLAN 10)")

            access10_commands = []
            if "Ethernet" in access_vlan10_port:
                intf_num = access_vlan10_port.replace("Ethernet", "")
                access10_commands.append(f"interface Ethernet {intf_num}")

            access10_commands.append("no ip address")
            access10_commands.append("no switchport trunk allowed Vlan 10")
            access10_commands.append("switchport access Vlan 10")
            access10_commands.append("end")

            st.config(dut, access10_commands, type=self.data.cli_type, skip_error_check=True)
            st.log(f"✓ {access_vlan10_port} configured as VLAN 10 access port")

            st.banner(f"Step 5: Configuring access port {access_vlan20_port} (VLAN 20)")

            access20_commands = []
            if "Ethernet" in access_vlan20_port:
                intf_num = access_vlan20_port.replace("Ethernet", "")
                access20_commands.append(f"interface Ethernet {intf_num}")

            access20_commands.append("no ip address")
            access20_commands.append("no switchport trunk allowed Vlan 20")
            access20_commands.append("switchport access Vlan 20")
            access20_commands.append("end")

            st.config(dut, access20_commands, type=self.data.cli_type, skip_error_check=True)
            st.log(f"✓ {access_vlan20_port} configured as VLAN 20 access port")

            vlan_output = vlan_api.show_vlan_config(dut, cli_type=self.data.cli_type)
            st.log(f"VLAN configuration:\n{vlan_output}")

            st.banner("Step 6: Clearing interface counters")
            self._clear_interface_counters(dut)

            st.banner("Step 7: Starting tcpdump on access ports")

            pcap_vlan10 = "/tmp/vlan_trunk_003_vlan10.pcap"
            pcap_vlan20 = "/tmp/vlan_trunk_003_vlan20.pcap"

            self._start_tcpdump(dut, access_vlan10_port, 10, pcap_vlan10)
            self._start_tcpdump(dut, access_vlan20_port, 20, pcap_vlan20)

            st.banner("Step 8: Sending VLAN 20 tagged ICMP traffic")

            packet_count = traffic.get("packet_count", 20)
            vlan_id = traffic.get("vlan_id", 20)
            dst_mac = traffic.get("dst_mac", "ff:ff:ff:ff:ff:ff")
            src_ip = traffic.get("src_ip", "192.168.20.1")
            dst_ip = traffic.get("dst_ip", "192.168.20.2")
            inter_packet_delay = traffic.get("inter_packet_delay", 0.05)

            src_mac = "00:11:22:33:44:66"
            script_path = "/tmp/scapy_vlan_003.py"

            traffic_sent = self._send_tagged_icmp_traffic(
                tgen, tgen_trunk_port, src_mac, dst_mac,
                src_ip, dst_ip, vlan_id, packet_count,
                inter_packet_delay, script_path
            )

            if not traffic_sent:
                st.report_fail("msg", "Failed to send ICMP traffic")

            time.sleep(2)

            st.banner("Step 9: Stopping tcpdump")
            self._stop_tcpdump(dut)
            time.sleep(2)

            st.banner("Step 10: Verifying VLAN 20 access port receives traffic")

            vlan20_counters = self._get_interface_counters(dut, access_vlan20_port)
            vlan20_rx = vlan20_counters["rx_ok"]

            vlan20_pcap_count = self._verify_tcpdump_capture(dut, pcap_vlan20)

            vlan20_verify = verification.get("vlan20_access_port", {})
            min_expected = vlan20_verify.get("min_packets", 15)

            st.log(f"VLAN 20 access port: RX_OK={vlan20_rx}, tcpdump={vlan20_pcap_count}")

            if vlan20_rx < min_expected and vlan20_pcap_count < min_expected:
                st.report_fail("msg", f"VLAN 20 port: RX_OK={vlan20_rx}, tcpdump={vlan20_pcap_count} (both < {min_expected})")

            st.log(f"✓ VLAN 20 port received traffic: RX_OK={vlan20_rx}, tcpdump={vlan20_pcap_count}")

            st.banner("Step 11: Verifying VLAN 10 access port does NOT receive traffic")

            vlan10_counters = self._get_interface_counters(dut, access_vlan10_port)
            vlan10_rx = vlan10_counters["rx_ok"]

            vlan10_pcap_count = self._verify_tcpdump_capture(dut, pcap_vlan10)

            vlan10_verify = verification.get("vlan10_access_port", {})
            max_allowed = vlan10_verify.get("max_packets", 5)

            st.log(f"VLAN 10 access port: RX_OK={vlan10_rx}, tcpdump={vlan10_pcap_count}")

            if vlan10_rx > max_allowed or vlan10_pcap_count > max_allowed:
                st.report_fail("msg", f"VLAN 10 port: RX_OK={vlan10_rx}, tcpdump={vlan10_pcap_count} (traffic leaked!)")

            st.log(f"✓ VLAN 10 port correctly rejected traffic: RX_OK={vlan10_rx}, tcpdump={vlan10_pcap_count}")

            st.banner("Step 12: Cleanup")

            st.show(dut, f"sudo rm -f {pcap_vlan10} {pcap_vlan20}", skip_tmpl=True, skip_error_check=True)

            for port in [access_vlan10_port, access_vlan20_port]:
                if "Ethernet" in port:
                    intf_num = port.replace("Ethernet", "")
                    st.config(dut, [f"interface Ethernet {intf_num}", "no switchport access Vlan", "exit"],
                             type=self.data.cli_type, skip_error_check=True)

            if "Ethernet" in trunk_port:
                intf_num = trunk_port.replace("Ethernet", "")
                trunk_cleanup = [f"interface Ethernet {intf_num}"]
                for vlan in vlans:
                    trunk_cleanup.append(f"no switchport trunk allowed Vlan {vlan.get('id')}")
                trunk_cleanup.append("exit")
                st.config(dut, trunk_cleanup, type=self.data.cli_type, skip_error_check=True)

            for vlan in vlans:
                vlan_api.delete_vlan(dut, vlan.get("id"), cli_type=self.data.cli_type, skip_error_check=True)

            st.log("✓ Cleanup completed")
            st.report_pass("test_case_passed")

        except Exception as e:
            st.error(f"Test failed: {e}")

            if self.data.cleanup_enabled:
                self._stop_tcpdump(dut)

                for port in [access_vlan10_port, access_vlan20_port, trunk_port]:
                    if "Ethernet" in port:
                        intf_num = port.replace("Ethernet", "")
                        cleanup_cmds = [f"interface Ethernet {intf_num}", "no switchport access Vlan"]
                        for vlan in vlans:
                            cleanup_cmds.append(f"no switchport trunk allowed Vlan {vlan.get('id')}")
                        cleanup_cmds.append("exit")
                        st.config(dut, cleanup_cmds, type=self.data.cli_type, skip_error_check=True)

                for vlan in vlans:
                    vlan_api.delete_vlan(dut, vlan.get("id"), cli_type=self.data.cli_type, skip_error_check=True)

            st.report_fail("msg", f"Test failed: {e}")
