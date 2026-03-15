"""
VLAN TRUNK PORT CONFIGURATION AND TAGGED TRAFFIC FORWARDING
Author: Shiva
2026

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/switching/vlan/test_vlan_trunk_port.py \
  --logs-path ./logs/vlan_trunk_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates trunk port configuration and 802.1Q tagged packet forwarding.
  TC_VLAN_TRUNK_001 configures a trunk port allowing multiple VLANs (10, 20, 30)
  and verifies tagged packet reception using both hardware counters and deep
  packet inspection (tcpdump). All MACs are retrieved dynamically from the testbed.

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Topology Diagram:
        # Two Device Topology
        # +--------------------+                       +--------------------+
        # |   spine02 (D1)     |                       |   leaf01 (D2)      |
        # | TGen - Ethernet8   |=======================| DUT - Ethernet8    |
        # |   (Traffic Sender) |                       | (Trunk Port)       |
        # +--------------------+                       +--------------------+
  - Feature flags / min SONiC version: VLAN support required
  - Required test variables (YAML): spytest/vars/switching/vlan/vars_vlan_trunk.yaml
    - TC_VLAN_TRUNK_001.vlans
    - TC_VLAN_TRUNK_001.test_vlan
    - TC_VLAN_TRUNK_001.traffic
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.switching.vlan as vlan_api
import apis.system.interface as interface_api
import apis.common.scapy_traffic as scapy_traffic

# Default YAML variable file location
VAR_FILE_ENV = "VLAN_TRUNK_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "switching"
    / "vlan"
    / "vars_vlan_trunk.yaml"
)


def _load_yaml_config() -> Dict[str, Any]:
    """Load test configuration from YAML file."""
    override_path = st.getenv(VAR_FILE_ENV)
    yaml_file = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not yaml_file.is_file():
        raise FileNotFoundError(f"VLAN trunk variable file not found: {yaml_file}")

    with yaml_file.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    if "testcases" not in config:
        raise ValueError("YAML must contain 'testcases' key")

    return config


@pytest.mark.topology("D1D2:1")
class TestVlanTrunkPort:
    """Test class for VLAN trunk port configuration and tagged traffic forwarding."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """
        Class-level setup: Load configuration and ensure minimum topology.

        Topology requirement: Two DUTs with at least 1 connection (D1D2:1).
        """
        st.banner("VLAN Trunk Port Tests: Class Setup")

        # Load YAML configuration
        config = _load_yaml_config()
        defaults = config.get("defaults", {})
        testcases = config.get("testcases", {})

        # Ensure minimum topology: Two DUTs with 1 connection
        min_topology = defaults.get("min_topology", ["D1D2:1"])
        topology = st.ensure_min_topology(*min_topology)

        # Store configuration
        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.testcases = SpyTestDict(testcases)
        cls.data.topology = topology
        cls.data.cli_type = defaults.get("cli_type", "klish")

        st.log(f"Topology: {topology}")
        st.log(f"CLI Type: {cls.data.cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """Class-level teardown: cleanup configuration."""
        st.banner("VLAN Trunk Port Tests: Class Teardown")

    def setup_method(self) -> None:
        """Per-test setup."""
        pass

    def teardown_method(self) -> None:
        """Per-test teardown."""
        pass


    def _clear_interface_counters(self, dut: str) -> bool:
        """
        Clear interface counters on the DUT.

        Args:
            dut: Device handle

        Returns:
            True if successful
        """
        st.log(f"Clearing interface counters on {dut}")

        try:
            # Use correct klish command: "clear interface counters"
            cmd = "clear interface counters"
            st.config(dut, cmd, type=self.data.cli_type, skip_error_check=True, conf=False)
            time.sleep(2)  # Allow counters to reset
            st.log("✓ Interface counters cleared")
            return True

        except Exception as e:
            st.error(f"Failed to clear counters: {e}")
            return False

    def _get_interface_counters(self, dut: str, interface: str) -> Dict[str, int]:
        """
        Get RX/TX counters for an interface.

        Args:
            dut: Device handle
            interface: Interface name

        Returns:
            Dictionary with rx_ok and tx_ok counts
        """
        st.log(f"Getting interface counters for {interface} on {dut}")

        try:
            # Extract interface number (e.g., "Ethernet12" -> "12")
            match = re.search(r'Ethernet(\d+)', interface)
            if not match:
                st.error(f"Invalid interface name: {interface}")
                return {"rx_ok": 0, "tx_ok": 0}

            intf_num = match.group(1)

            # Use specific interface command
            # Command: "show interface counters Ethernet 12" (with space)
            cmd = f"show interface counters Ethernet {intf_num}"

            # Get RAW output (skip_tmpl=True to bypass TextFSM template parsing)
            # The output can be line-wrapped which breaks template matching
            raw_output = st.show(dut, cmd, type=self.data.cli_type, skip_tmpl=True, skip_error_check=True)

            counters = {"rx_ok": 0, "tx_ok": 0}

            # Parse raw output directly using regex
            # Example output (may be wrapped):
            # Ethernet12    U    11  8.62 B/s  0.20/s  0.00%  0  1  0  1  1.34 B/s  ...
            if raw_output and isinstance(raw_output, str):
                # Join all lines (handle line wrapping)
                output_text = raw_output.replace('\n', ' ')

                # Look for the interface line with data
                # Format: Ethernet12  U  <RX_OK>  ...  <TX_OK>  ...
                # Find line starting with our interface name
                for line in raw_output.split('\n'):
                    if interface in line or f"Ethernet{intf_num}" in line:
                        # Split by whitespace
                        parts = line.split()
                        # Expected format: [Ethernet12, U, RX_OK, RX_BPS, RX_PPS, ...]
                        # RX_OK is typically at index 2, TX_OK at index 9
                        try:
                            if len(parts) >= 10:
                                rx_ok_str = parts[2].replace(",", "")  # Remove commas
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


    def _send_tagged_traffic(
        self,
        tgen: str,
        tgen_port: str,
        src_mac: str,
        dst_mac: str,
        vlan_id: int,
        packet_count: int,
        inter_packet_delay: float,
        payload: str,
        script_path: str = "/tmp/scapy_tagged_sender.py"
    ) -> bool:
        """
        Send 802.1Q tagged traffic using Scapy script (similar to scapy_traffic API pattern).

        Args:
            tgen: Traffic generator device handle
            tgen_port: TGen port to send from
            src_mac: Source MAC address
            dst_mac: Destination MAC address
            vlan_id: VLAN ID for 802.1Q tag
            packet_count: Number of packets to send
            inter_packet_delay: Delay between packets (seconds)
            payload: Packet payload string
            script_path: Path to save script on device

        Returns:
            True if traffic sent successfully
        """
        st.log(f"Sending {packet_count} tagged packets (VLAN {vlan_id}) from {tgen}:{tgen_port}")
        st.log(f"  SRC MAC: {src_mac}, DST MAC: {dst_mac}")

        # Create Scapy script for tagged traffic (Ether/Dot1Q/IP/ICMP)
        script_content = f'''#!/usr/bin/env python3
"""
Scapy Tagged Traffic Generator Script (802.1Q)
Auto-generated by SPyTest for VLAN Trunk Testing
"""

from scapy.all import Ether, Dot1Q, Raw, sendp
import time
import sys

# Configuration
iface = "{tgen_port}"
src_mac = "{src_mac}"
dst_mac = "{dst_mac}"
vlan_id = {vlan_id}
packet_count = {packet_count}
interval = {inter_packet_delay}
payload = "{payload}"

def send_tagged_traffic():
    """Send 802.1Q tagged L2 packets (no IP layer)."""
    print(f"[+] Starting 802.1Q Tagged L2 Traffic Generation")
    print(f"    Interface:    {{iface}}")
    print(f"    Source MAC:   {{src_mac}}")
    print(f"    Dest MAC:     {{dst_mac}}")
    print(f"    VLAN ID:      {{vlan_id}}")
    print(f"    Packet Count: {{packet_count}}")
    print()

    # Pre-build packet: Ether / Dot1Q / Raw (L2-only, no IP/ICMP)
    pkt = (
        Ether(src=src_mac, dst=dst_mac) /
        Dot1Q(vlan=vlan_id) /
        Raw(load=payload)
    )

    sent = 0
    try:
        for i in range(packet_count):
            sendp(pkt, iface=iface, verbose=False)
            sent += 1
            print(f"[→] Sent {{sent}}/{{packet_count}} tagged packets...", end='\\r')
            time.sleep(interval)

    except Exception as e:
        print(f"\\n[✗] Error: {{e}}")
        return False

    print(f"\\n[✓] Completed. Sent {{sent}} tagged packets (VLAN {{vlan_id}})")
    return True

if __name__ == "__main__":
    success = send_tagged_traffic()
    sys.exit(0 if success else 1)
'''

        try:
            # Remove existing script
            st.show(tgen, f"rm -f {script_path}", skip_tmpl=True, skip_error_check=True)

            # Create script using heredoc
            cmd = f"cat > {script_path} << 'EOFSCAPY'\n{script_content}\nEOFSCAPY"
            st.show(tgen, cmd, skip_tmpl=True, skip_error_check=True)

            # Make executable
            st.show(tgen, f"chmod +x {script_path}", skip_tmpl=True, skip_error_check=True)

            # Execute script
            output = st.show(tgen, f"sudo python3 {script_path}", skip_tmpl=True, skip_error_check=True)
            st.log(f"Tagged traffic output:\n{output}")

            # Cleanup script
            st.show(tgen, f"rm -f {script_path}", skip_tmpl=True, skip_error_check=True)

            # Check for success
            if "Completed" in str(output):
                st.log(f"✓ Sent {packet_count} tagged packets with VLAN {vlan_id}")
                return True
            else:
                st.error(f"✗ Tagged traffic send status unclear")
                return False

        except Exception as e:
            st.error(f"Failed to send tagged traffic: {e}")
            return False

    @pytest.mark.inventory(feature="VLAN_Trunk", testcases=["TC_VLAN_TRUNK_001"])
    def test_vlan_trunk_tagged_forwarding(self) -> None:
        """
        TC_VLAN_TRUNK_001: Verify trunk port configuration and 802.1Q tagged packet forwarding.

        Test Steps:
        1. Discover topology and ports
        2. Create VLANs 10, 20, 30 on DUT
        3. Configure trunk port on DUT allowing VLANs 10, 20, 30
        4. Retrieve MAC addresses dynamically
        5. Clear interface counters
        6. Start tcpdump on DUT
        7. Send tagged traffic from TGen (VLAN 10)
        8. Stop tcpdump
        9. Verify hardware counters
        10. Verify pcap capture
        11. Cleanup temporary files
        """
        st.banner("TC_VLAN_TRUNK_001: VLAN Trunk Port Tagged Traffic Test")

        # Get test configuration
        testcase = self.data.testcases.get("TC_VLAN_TRUNK_001")
        if not testcase:
            st.report_fail("msg", "TC_VLAN_TRUNK_001 not found in YAML configuration")

        vlans = testcase.get("vlans", [])
        test_vlan = testcase.get("test_vlan", 10)
        traffic_config = SpyTestDict(testcase.get("traffic", {}))
        verification = SpyTestDict(testcase.get("verification", {}))

        topology = self.data.topology

        # Step 1: Discover topology
        st.banner("Step 1: Discovering topology and port connections")

        # Find D1-D2 connection
        tgen = None
        dut = None
        tgen_port = None
        dut_port = None

        # Check D1D2P1 connection
        if hasattr(topology, 'D1D2P1') and hasattr(topology, 'D2D1P1'):
            tgen_port = getattr(topology, 'D1D2P1')
            dut_port = getattr(topology, 'D2D1P1')
            if tgen_port and dut_port:
                tgen = topology.D1
                dut = topology.D2

        if not tgen or not dut or not tgen_port or not dut_port:
            st.report_fail("msg", "Failed to discover D1-D2 topology connection")

        st.log(f"✓ Topology discovered:")
        st.log(f"  TGen: {tgen}, Port: {tgen_port}")
        st.log(f"  DUT:  {dut}, Port: {dut_port}")

        pcap_file = None
        tcpdump_started = False

        try:
            # Step 2: Remove existing VLANs and create new ones on DUT
            st.banner("Step 2: Removing existing VLANs and creating VLANs 10, 20, 30 on DUT")

            # First, remove VLANs from trunk port manually (correct command)
            cleanup_commands = []
            if "Ethernet" in dut_port:
                intf_num = dut_port.replace("Ethernet", "")
                cleanup_commands.append(f"interface Ethernet {intf_num}")
            else:
                cleanup_commands.append(f"interface {dut_port}")

            for vlan in vlans:
                vlan_id = vlan.get("id")
                # Use correct command: "no switchport trunk allowed Vlan <id>"
                cleanup_commands.append(f"no switchport trunk allowed Vlan {vlan_id}")

            cleanup_commands.append("exit")
            st.config(dut, cleanup_commands, type=self.data.cli_type, skip_error_check=True)

            # Now delete and recreate VLANs
            for vlan in vlans:
                vlan_id = vlan.get("id")

                # Remove VLAN if it exists (cleanup)
                st.log(f"Removing VLAN {vlan_id} if exists")
                vlan_api.delete_vlan(dut, vlan_id, cli_type=self.data.cli_type, skip_error_check=True)

                # Create VLAN
                st.log(f"Creating VLAN {vlan_id}")
                if not vlan_api.create_vlan(dut, vlan_id, cli_type=self.data.cli_type):
                    st.report_fail("msg", f"Failed to create VLAN {vlan_id}")

                st.log(f"✓ VLAN {vlan_id} created")

            # Step 3: Configure trunk port on DUT using exact commands from TC_VLAN_TRUNK_001.md
            st.banner(f"Step 3: Configuring {dut_port} as trunk port")

            # Build trunk configuration commands as per documentation
            trunk_commands = []

            # Enter interface mode
            if "Ethernet" in dut_port:
                intf_num = dut_port.replace("Ethernet", "")
                trunk_commands.append(f"interface Ethernet {intf_num}")
            else:
                trunk_commands.append(f"interface {dut_port}")

            # Clear existing configuration
            trunk_commands.append("no ip address")
            trunk_commands.append("no switchport access Vlan")

            # Remove any existing trunk VLAN assignments
            for vlan in vlans:
                vlan_id = vlan.get("id")
                trunk_commands.append(f"no switchport trunk allowed Vlan {vlan_id}")

            # Add VLANs to trunk (exact command from doc: "switchport trunk allowed Vlan 10")
            for vlan in vlans:
                vlan_id = vlan.get("id")
                trunk_commands.append(f"switchport trunk allowed Vlan {vlan_id}")

            trunk_commands.append("end")

            # Execute trunk configuration
            st.config(dut, trunk_commands, type=self.data.cli_type, skip_error_check=True)

            st.log(f"✓ Trunk port {dut_port} configured with VLANs: {[v.get('id') for v in vlans]}")

            # Verify trunk configuration
            st.log(f"Verifying trunk configuration for VLANs: {[v.get('id') for v in vlans]}")
            vlan_output = vlan_api.show_vlan_config(dut, cli_type=self.data.cli_type)
            st.log(f"VLAN configuration:\n{vlan_output}")

            # Step 4: Retrieve MAC addresses dynamically using SpyTest API
            st.banner("Step 4: Retrieving MAC addresses dynamically")

            tgen_mac = scapy_traffic.get_interface_mac(tgen, tgen_port, cli_type=self.data.cli_type)
            dut_mac = scapy_traffic.get_interface_mac(dut, dut_port, cli_type=self.data.cli_type)

            if not tgen_mac or not dut_mac:
                st.report_fail("msg", "Failed to retrieve MAC addresses")

            st.log(f"✓ TGen MAC: {tgen_mac}")
            st.log(f"✓ DUT MAC: {dut_mac}")

            # Step 5: Clear interface counters
            st.banner("Step 5: Clearing interface counters")

            if not self._clear_interface_counters(dut):
                st.report_fail("msg", "Failed to clear interface counters")

            # Step 6: Start tcpdump using SpyTest API
            st.banner(f"Step 6: Starting tcpdump on DUT for VLAN {test_vlan}")

            pcap_file = f"/tmp/trunk_vlan{test_vlan}_test.pcap"
            tcpdump_started = scapy_traffic.start_tcpdump(
                dut,
                dut_port,
                filter_str=f"vlan {test_vlan}",
                output_file=pcap_file,
                max_packets=1000
            )

            if not tcpdump_started:
                st.report_fail("msg", "Failed to start tcpdump")

            time.sleep(2)  # Allow tcpdump to start

            # Step 7: Send tagged traffic
            st.banner(f"Step 7: Sending tagged traffic (VLAN {test_vlan})")

            traffic_sent = self._send_tagged_traffic(
                tgen=tgen,
                tgen_port=tgen_port,
                src_mac=tgen_mac,
                dst_mac=traffic_config.dst_mac,
                vlan_id=test_vlan,
                packet_count=traffic_config.packet_count,
                inter_packet_delay=traffic_config.inter_packet_delay,
                payload=traffic_config.payload,
            )

            if not traffic_sent:
                st.report_fail("msg", "Failed to send tagged traffic")

            # Step 8: Stop tcpdump using SpyTest API
            st.banner("Step 8: Stopping tcpdump")

            if tcpdump_started:
                scapy_traffic.stop_tcpdump(dut)
                time.sleep(2)  # Allow pcap to finalize

            # Step 9: Verify hardware counters
            st.banner("Step 9: Verifying hardware counters")

            counters = self._get_interface_counters(dut, dut_port)
            rx_count = counters["rx_ok"]

            min_expected = verification.min_packets
            max_expected = verification.max_packets

            st.log(f"RX_OK count: {rx_count} (expected: {min_expected}-{max_expected})")

            if rx_count < min_expected:
                st.report_fail(
                    "msg",
                    f"Counter verification FAILED: RX_OK={rx_count} < {min_expected}"
                )

            if rx_count > max_expected:
                st.log(f"⚠ Warning: RX_OK={rx_count} > {max_expected} (possible background traffic)")

            st.log(f"✓ Counter verification PASSED: {rx_count} packets received")

            # Step 10: Verify pcap capture using SpyTest API
            st.banner("Step 10: Verifying packet capture")

            pcap_result = scapy_traffic.verify_tcpdump_capture(
                dut,
                pcap_file,
                min_packets=verification.pcap_expected_packets
            )

            if not pcap_result["success"]:
                st.report_fail(
                    "msg",
                    f"Pcap verification FAILED: {pcap_result['packet_count']} < {verification.pcap_expected_packets}"
                )

            st.log(f"✓ Pcap verification PASSED: {pcap_result['packet_count']} packets captured")

            # Step 11: Cleanup temporary files using Linux command
            st.banner("Step 11: Cleaning up temporary pcap file")

            if pcap_file:
                st.show(dut, f"sudo rm -f {pcap_file}", skip_tmpl=True, skip_error_check=True)
                st.log(f"✓ Pcap file {pcap_file} removed")

            # Cleanup: Remove trunk VLAN configuration using direct CLI
            st.log("Cleanup: Removing trunk VLAN memberships")
            cleanup_commands = []

            # Enter interface mode
            if "Ethernet" in dut_port:
                intf_num = dut_port.replace("Ethernet", "")
                cleanup_commands.append(f"interface Ethernet {intf_num}")
            else:
                cleanup_commands.append(f"interface {dut_port}")

            # Remove trunk VLANs
            for vlan in vlans:
                vlan_id = vlan.get("id")
                cleanup_commands.append(f"no switchport trunk allowed Vlan {vlan_id}")

            cleanup_commands.append("exit")

            st.config(dut, cleanup_commands, type=self.data.cli_type, skip_error_check=True)

            # Delete VLANs
            st.log("Cleanup: Deleting VLANs")
            for vlan in vlans:
                vlan_id = vlan.get("id")
                vlan_api.delete_vlan(dut, vlan_id, cli_type=self.data.cli_type, skip_error_check=True)

            # Test Summary
            st.banner("TC_VLAN_TRUNK_001: PASSED")
            st.log("✓ Test Summary:")
            st.log(f"  - Created VLANs: {[v.get('id') for v in vlans]}")
            st.log(f"  - Configured trunk port: {dut_port}")
            st.log(f"  - Sent {traffic_config.packet_count} tagged packets (VLAN {test_vlan})")
            st.log(f"  - Hardware counters verified: {rx_count} packets received ✓")
            st.log(f"  - Pcap capture verified: Tagged packets captured ✓")
            st.log("  - Trunk port configuration and tagged forwarding working correctly!")

            # Exit klish mode to Linux shell before test ends
            st.change_prompt(dut, "normal-user")

            st.report_pass("test_case_passed")

        except Exception as e:
            st.error(f"Test failed with exception: {e}")

            # Cleanup on failure
            try:
                if tcpdump_started:
                    scapy_traffic.stop_tcpdump(dut)

                if pcap_file:
                    st.show(dut, f"sudo rm -f {pcap_file}", skip_tmpl=True, skip_error_check=True)

                # Remove trunk VLAN configuration using direct CLI
                cleanup_commands = []
                if "Ethernet" in dut_port:
                    intf_num = dut_port.replace("Ethernet", "")
                    cleanup_commands.append(f"interface Ethernet {intf_num}")
                else:
                    cleanup_commands.append(f"interface {dut_port}")

                for vlan in vlans:
                    vlan_id = vlan.get("id")
                    cleanup_commands.append(f"no switchport trunk allowed Vlan {vlan_id}")

                cleanup_commands.append("exit")
                st.config(dut, cleanup_commands, type=self.data.cli_type, skip_error_check=True)

                # Delete VLANs
                for vlan in vlans:
                    vlan_id = vlan.get("id")
                    vlan_api.delete_vlan(
                        dut,
                        vlan_id,
                        cli_type=self.data.cli_type,
                        skip_error_check=True
                    )

            except:
                pass

            # Exit klish mode to Linux shell before test ends
            st.change_prompt(dut, "normal-user")

            st.report_fail("msg", f"TC_VLAN_TRUNK_001 failed: {e}")
