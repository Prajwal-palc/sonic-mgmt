"""
VLAN SVI L3 TRAFFIC TEST - TCPDUMP VERIFICATION

Author: Shiva
2026

How to run:
  ./bin/spytest --tryssh 1  \\
  --testbed ./testbeds/testbed_2vs.yaml  \\
  tests/switching/vlan/test_vlan_svi_l3_traffic_tcpdump.py  \\
  --logs-path ./logs/vlan_svi_tcpdump_$(date +%F_%H%M%S)  \\
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Bidirectional VLAN SVI L3 traffic validation using Scapy-based traffic generation
  and TCPDUMP packet capture verification. This test eliminates dependency on interface
  counters (which have TextFSM parsing issues with comma-formatted numbers) and instead
  uses pcap files for exact packet counting and deep packet inspection capabilities.

  The test configures VLAN 10 with SVI IP addresses (10.1.1.1/24 on DUT1, 10.1.1.2/24 on DUT2),
  sets physical ports as access ports, starts tcpdump listeners on both DUTs, generates
  bidirectional traffic (1000 packets @ 100 pps), and validates packet reception by reading
  pcap files using Scapy's rdpcap() function.

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: Virtual (tested with testbed_2vs.yaml)
  - Feature flags / min SONiC version: SONiC 202211 or later with Scapy and tcpdump support
  - Required test variables (YAML): spytest/vars/switching/vlan/vars_vlan_svi_l3_traffic_2dut.yaml
  - Topology Diagram:
        # Topology - 2 nodes with multiple links
        # +--------------------+                       +--------------------+
        # |        DUT1        |                       |        DUT2        |
        # |  (10.1.1.1/24)    |                       |  (10.1.1.2/24)    |
        # |                   |                       |                   |
        # | Eth8 (VLAN10)     |=======================| Eth8 (VLAN10)      |
        # | Eth12 (VLAN10)    |=======================| Eth12 (VLAN10)     |
        # +--------------------+                       +--------------------+
        #     ^                                               ^
        #     |                                               |
        #  tcpdump capture                               tcpdump capture
        #  /tmp/eth8_d1.pcap                            /tmp/eth8_d2.pcap

Benefits of Tcpdump Approach:
  - Eliminates TextFSM parsing issues with comma-formatted counter values
  - Provides exact packet counts (filters only UDP port 54321)
  - Enables deep packet inspection (MAC, IP, payload verification)
  - Creates forensic evidence (pcap files) for post-test analysis
  - More reliable than interface counters which include all traffic (LLDP, ARP, etc.)
"""

from __future__ import annotations

from collections.abc import Iterable as IterableCollection
from contextlib import contextmanager
from copy import deepcopy
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
import apis.routing.arp as arp_api
import apis.common.scapy_traffic as scapy_traffic

VAR_FILE_ENV = "VLAN_SVI_L3_TRAFFIC_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "switching"
    / "vlan"
    / "vars_vlan_svi_l3_traffic_2dut.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"VLAN SVI L3 Traffic variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "traffic_scenarios" not in content:
        raise ValueError("YAML must contain key 'traffic_scenarios'")

    return content


def _iter_candidate_duts(topology: Mapping[str, Any]) -> Iterable[str]:
    """Yield DUT aliases discovered in the topology map."""
    for key, value in topology.items():
        if key.startswith("D") and value:
            yield key


@pytest.mark.topology("any")
class TestVlanSviL3TrafficTcpdump:
    """Test VLAN SVI L3 bidirectional traffic with tcpdump-based packet verification."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and configure VLAN/SVI."""
        config = _load_yaml_data()
        defaults = config.get("defaults", {})
        min_topology = defaults.get("min_topology") or ["D1D2:1"]

        topology = st.ensure_min_topology(*min_topology)
        cls.data.topology = topology
        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Get DUT names and map
        cls.data.dut_names = st.get_dut_names()
        cls.data.dut_map = SpyTestDict()

        for dut_alias in _iter_candidate_duts(topology):
            cls.data.dut_map[dut_alias] = getattr(topology, dut_alias)

        # Initialize traffic tracking
        cls.data.configured_vlans = []
        cls.data.configured_svis = []

        # Configure VLAN and SVI on both DUTs
        cls._configure_vlan_and_svi()
        st.banner("VLAN and SVI configuration completed successfully")

        # CRITICAL: Return to Linux mode after setup
        st.log("Returning to Linux mode after setup on all DUTs")
        try:
            for dut in cls.data.dut_names:
                st.config(dut, "exit", type='klish', skip_error_check=True)
                st.log(f"✅ Returned to Linux mode on {dut}")
        except Exception as e:
            st.warn(f"Error returning to Linux mode after setup: {e}")

    @classmethod
    def teardown_class(cls) -> None:
        """Clean up VLAN and SVI configurations."""
        if not cls.data.cleanup_enabled:
            return

        cls._cleanup_all_vlan_and_svi()

        # CRITICAL: Return to Linux mode after cleanup
        st.log("Returning to Linux mode on all DUTs")
        try:
            for dut in cls.data.dut_names:
                st.config(dut, "exit", type='klish', skip_error_check=True)
                st.log(f"✅ Returned to Linux mode on {dut}")
        except Exception as e:
            st.warn(f"Error returning to Linux mode: {e}")

    @classmethod
    def _resolve_dut(cls, alias: str | None) -> str | None:
        """Translate a topology alias (e.g., D1) to the framework DUT handle."""
        if not alias:
            return None
        if alias in cls.data.dut_map:
            return cls.data.dut_map[alias]
        if alias in cls.data.dut_names:
            return alias
        st.warn(f"Unable to resolve DUT alias '{alias}'")
        return None

    @classmethod
    def _configure_vlan_and_svi(cls) -> None:
        """Configure VLAN and SVI with IP addresses on both DUTs."""
        vlan_config = cls.data.config.get("vlan_config", {})
        intf_config = cls.data.config.get("interface_config", {})
        vlan_id = vlan_config.get("vlan_id", 10)
        vlan_name = f"Vlan{vlan_id}"
        cli_type = cls.data.cli_type

        st.banner(f"Configuring VLAN {vlan_id} and SVI on both DUTs")

        for dut_alias in ["D1", "D2"]:
            dut = cls._resolve_dut(dut_alias)
            if not dut:
                st.error(f"Cannot resolve DUT for alias {dut_alias}")
                continue

            dut_key = "dut1" if dut_alias == "D1" else "dut2"
            dut_cfg = intf_config.get(dut_key, {})
            svi_ip = dut_cfg.get("svi_ip", "10.1.1.1" if dut_alias == "D1" else "10.1.1.2")
            svi_prefix = dut_cfg.get("svi_prefix", 24)
            access_ports = dut_cfg.get("access_ports", ["Ethernet8", "Ethernet12"])

            # Create VLAN
            st.log(f"Creating VLAN {vlan_id} on {dut}")
            vlan_api.create_vlan(dut, vlan_id, cli_type=cli_type)
            cls.data.configured_vlans.append((dut, vlan_id))

            # Add access ports to VLAN
            for port in access_ports:
                st.log(f"Adding {port} to VLAN {vlan_id} on {dut} (access mode)")
                vlan_api.add_vlan_member(dut, vlan_id, port, tagging_mode=False, cli_type=cli_type)

            # Configure SVI IP address
            svi_ip_with_prefix = f"{svi_ip}/{svi_prefix}"
            st.log(f"Configuring SVI {vlan_name} with IP {svi_ip_with_prefix} on {dut}")
            ip_api.config_ip_addr_interface(dut, vlan_name, svi_ip, svi_prefix, family="ipv4", cli_type=cli_type)
            cls.data.configured_svis.append((dut, vlan_name, svi_ip_with_prefix))

        st.wait(2, "Wait for VLAN and SVI configuration to take effect")

    @classmethod
    def _cleanup_all_vlan_and_svi(cls) -> None:
        """Remove all configured VLANs and SVIs."""
        st.banner("Cleaning up VLAN and SVI configurations")
        cli_type = cls.data.cli_type
        intf_config = cls.data.config.get("interface_config", {})

        for dut_alias in ["D1", "D2"]:
            dut = cls._resolve_dut(dut_alias)
            if not dut:
                continue

            dut_key = "dut1" if dut_alias == "D1" else "dut2"
            dut_cfg = intf_config.get(dut_key, {})
            access_ports = dut_cfg.get("access_ports", ["Ethernet8", "Ethernet12"])
            vlan_id = cls.data.config.get("vlan_config", {}).get("vlan_id", 10)
            vlan_name = f"Vlan{vlan_id}"

            # Remove IP from SVI
            try:
                st.log(f"Removing IP from {vlan_name} on {dut}")
                ip_api.config_ip_addr_interface(dut, vlan_name, family="ipv4", config="remove", cli_type=cli_type)
            except Exception as e:
                st.debug(f"Exception removing IP: {e}")

            # Remove access port membership
            for port in access_ports:
                try:
                    st.log(f"Removing {port} from VLAN {vlan_id} on {dut}")
                    vlan_api.delete_vlan_member(dut, vlan_id, port, tagging_mode=False, cli_type=cli_type)
                except Exception as e:
                    st.debug(f"Exception removing VLAN member: {e}")

            # Delete VLAN
            try:
                st.log(f"Deleting VLAN {vlan_id} on {dut}")
                vlan_api.delete_vlan(dut, vlan_id, cli_type=cli_type)
            except Exception as e:
                st.debug(f"Exception deleting VLAN: {e}")

    @classmethod
    def _cleanup_pcap_files(cls, dut: str, pcap_path: str) -> None:
        """
        Delete old pcap files to ensure clean slate.

        Args:
            dut: Device handle
            pcap_path: Full path to pcap file (e.g., /tmp/eth8_d1.pcap)
        """
        st.log(f"Cleaning up old pcap file: {pcap_path} on {dut}")
        try:
            cmd = f"sudo rm -f {pcap_path}"
            st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
            st.log(f"✅ Deleted {pcap_path} on {dut}")
        except Exception as e:
            st.warn(f"Error cleaning up pcap file on {dut}: {e}")

    @classmethod
    def _start_tcpdump(cls, dut: str, interface: str, pcap_path: str, dst_port: int = 54321) -> bool:
        """
        Start tcpdump listener in background.

        Args:
            dut: Device handle
            interface: Interface to capture on (e.g., Ethernet8)
            pcap_path: Full path to save pcap file (e.g., /tmp/eth8_d1.pcap)
            dst_port: UDP destination port to filter (default: 54321)

        Returns:
            True if tcpdump started successfully
        """
        st.log(f"Starting tcpdump on {dut} ({interface}) → {pcap_path}")
        st.log(f"  Filter: UDP port {dst_port}")

        try:
            # Start tcpdump in background with nohup
            # Filter: UDP traffic on specific port
            # Write to pcap file
            cmd = f"sudo nohup tcpdump -i {interface} udp port {dst_port} -w {pcap_path} > /dev/null 2>&1 &"
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
        """
        Stop tcpdump process cleanly.

        Args:
            dut: Device handle
        """
        st.log(f"Stopping tcpdump on {dut}")

        try:
            # Kill all tcpdump processes
            cmd = "sudo killall tcpdump"
            st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)

            # Wait for tcpdump to flush buffers and close file
            st.wait(2, "Wait for tcpdump to flush and close file")

            st.log(f"✅ Stopped tcpdump on {dut}")

        except Exception as e:
            st.warn(f"Error stopping tcpdump on {dut}: {e}")

    @classmethod
    def _count_packets_in_pcap(cls, dut: str, pcap_path: str) -> int:
        """
        Count packets in pcap file using Scapy's rdpcap().

        Args:
            dut: Device handle
            pcap_path: Full path to pcap file (e.g., /tmp/eth8_d1.pcap)

        Returns:
            Number of packets in pcap file, or 0 if error
        """
        st.log(f"Counting packets in {pcap_path} on {dut}")

        try:
            # Method 1: Using Scapy's rdpcap (preferred - exact count)
            cmd = f'sudo python3 -c "from scapy.all import rdpcap; print(len(rdpcap(\\"{pcap_path}\\")))"'
            output = st.show(dut, cmd, skip_tmpl=True, skip_error_check=False)

            # Parse output - find the last line that's just a number
            # CRITICAL: Don't use re.search which matches first digit (e.g., "3" from "python3.11" in warnings)
            output_str = output.strip()

            # Look for the last line that's purely numeric (the packet count)
            for line in reversed(output_str.split('\n')):
                line = line.strip()
                if line.isdigit():
                    packet_count = int(line)
                    st.log(f"✅ Packet count from {pcap_path}: {packet_count}")
                    return packet_count

            # Fallback: no pure numeric line found
            st.warn(f"Could not parse packet count from output: {output_str}")
            return 0

        except Exception as e:
            st.error(f"Error counting packets in {pcap_path} on {dut}: {e}")
            return 0

    @classmethod
    def _verify_packet_payload(cls, dut: str, pcap_path: str, packet_index: int = 0) -> Dict[str, Any]:
        """
        Deep packet inspection - verify packet contents (optional).

        Args:
            dut: Device handle
            pcap_path: Full path to pcap file
            packet_index: Index of packet to inspect (default: 0 for first packet)

        Returns:
            Dictionary with packet details (src_mac, dst_mac, src_ip, dst_ip, payload)
        """
        st.log(f"Inspecting packet #{packet_index} in {pcap_path} on {dut}")

        try:
            # Extract packet details using Scapy
            cmd = f'''sudo python3 -c "
from scapy.all import rdpcap, Ether, IP, UDP, Raw
pkts = rdpcap('{pcap_path}')
if len(pkts) > {packet_index}:
    pkt = pkts[{packet_index}]
    print('SRC_MAC:', pkt[Ether].src if Ether in pkt else 'N/A')
    print('DST_MAC:', pkt[Ether].dst if Ether in pkt else 'N/A')
    print('SRC_IP:', pkt[IP].src if IP in pkt else 'N/A')
    print('DST_IP:', pkt[IP].dst if IP in pkt else 'N/A')
    print('UDP_SPORT:', pkt[UDP].sport if UDP in pkt else 'N/A')
    print('UDP_DPORT:', pkt[UDP].dport if UDP in pkt else 'N/A')
    if Raw in pkt:
        print('PAYLOAD:', pkt[Raw].load[:20])
else:
    print('ERROR: Packet index out of range')
"'''

            output = st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
            st.log(f"Packet inspection output:\n{output}")

            # Parse output
            packet_details = {}
            for line in output.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    packet_details[key.strip()] = value.strip()

            return packet_details

        except Exception as e:
            st.error(f"Error inspecting packet: {e}")
            return {}

    def _generate_scapy_traffic(
        self,
        source_dut: str,
        dest_ip: str,
        source_ip: str,
        packet_size: int,
        duration: int,
        total_packets: int,
        source_interface: str = None,
        dest_dut: str = None,
        vlan_name: str = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate Layer 2 Scapy-based traffic using apis.common.scapy_traffic."""
        st.banner(f"Sending Layer 2 traffic via {source_interface}")
        st.log(f"  Source: {source_ip}")
        st.log(f"  Destination: {dest_ip}")
        st.log(f"  Interface: {source_interface}")
        st.log(f"  Rate: 100 pps, Duration: {duration}s, Total: {total_packets} packets")

        if not vlan_name:
            vlan_id = self.data.config.get("vlan_config", {}).get("vlan_id", 10)
            vlan_name = f"Vlan{vlan_id}"

        # Get MAC addresses from VLAN SVIs
        src_mac = scapy_traffic.get_interface_mac(source_dut, vlan_name, cli_type='klish')
        dst_mac = scapy_traffic.get_interface_mac(dest_dut, vlan_name, cli_type='klish')

        if not src_mac or not dst_mac:
            st.error("Failed to retrieve MAC addresses from VLAN SVIs")
            return False, {"success": False, "error": "MAC retrieval failed"}

        st.log(f"  Source: {source_ip} ({src_mac})")
        st.log(f"  Destination: {dest_ip} ({dst_mac})")

        pps = total_packets // duration if duration > 0 else 100

        st.log(f"Sending Scapy traffic from {source_dut}")

        # Generate Layer 2 traffic with Ethernet headers
        result = scapy_traffic.send_traffic(
            dut=source_dut,
            interface=source_interface,
            src_ip=source_ip,
            dst_ip=dest_ip,
            src_mac=src_mac,
            dst_mac=dst_mac,
            duration=duration,
            pps=pps,
            payload_size=packet_size - 42,  # Ethernet(14) + IP(20) + UDP(8) = 42 bytes overhead
            traffic_type="udp"
        )

        return result["success"], result

    @pytest.mark.inventory(
        feature="VLAN_SVI_L3_Traffic_Tcpdump",
        testcases=["VLAN_SVI_L3_Bidirectional_Tcpdump_Verification"]
    )
    def test_svi_bidirectional_traffic_tcpdump(self) -> None:
        """
        TC – Bidirectional SVI L3 traffic with tcpdump-based packet verification.

        This test demonstrates the complete tcpdump workflow:
        1. Cleanup old pcap files
        2. Start tcpdump listeners on both DUTs
        3. Generate bidirectional traffic (DUT1 ↔ DUT2)
        4. Stop tcpdump listeners
        5. Count packets using Scapy's rdpcap()
        6. Validate packet counts (≥1000 packets in each direction)
        7. Optional: Deep packet inspection for first packet
        """
        st.banner("Starting Bidirectional Traffic Test with Tcpdump Verification")

        # Get DUT handles
        dut1 = self._resolve_dut("D1")
        dut2 = self._resolve_dut("D2")

        if not dut1 or not dut2:
            st.report_fail("msg", "Unable to resolve DUT handles")

        # Get configuration
        intf_config = self.data.config.get("interface_config", {})
        dut1_cfg = intf_config.get("dut1", {})
        dut2_cfg = intf_config.get("dut2", {})
        dut1_svi_ip = dut1_cfg.get("svi_ip", "10.1.1.1")
        dut2_svi_ip = dut2_cfg.get("svi_ip", "10.1.1.2")
        dut1_access_ports = dut1_cfg.get("access_ports", ["Ethernet8", "Ethernet12"])
        dut2_access_ports = dut2_cfg.get("access_ports", ["Ethernet8", "Ethernet12"])

        # Traffic parameters
        total_packets = 1000
        duration = 10
        packet_size = 64
        udp_port = 54321

        # Pcap file paths
        pcap_d1 = "/tmp/eth8_d1.pcap"
        pcap_d2 = "/tmp/eth8_d2.pcap"

        # ===== PHASE 1: PREPARATION =====
        st.banner("PHASE 1: Cleaning up old pcap files")
        self._cleanup_pcap_files(dut1, pcap_d1)
        self._cleanup_pcap_files(dut2, pcap_d2)

        # ===== PHASE 2: START LISTENERS =====
        st.banner("PHASE 2: Starting tcpdump listeners")
        tcpdump1_ok = self._start_tcpdump(dut1, dut1_access_ports[0], pcap_d1, udp_port)
        tcpdump2_ok = self._start_tcpdump(dut2, dut2_access_ports[0], pcap_d2, udp_port)

        if not tcpdump1_ok or not tcpdump2_ok:
            st.report_fail("msg", "Failed to start tcpdump listeners")

        # ===== PHASE 3: GENERATE BIDIRECTIONAL TRAFFIC =====
        st.banner("PHASE 3: Generating bidirectional traffic")

        # DUT1 → DUT2
        st.log(f"Sending {total_packets} packets from DUT1 → DUT2")
        success1, result1 = self._generate_scapy_traffic(
            source_dut=dut1,
            dest_ip=dut2_svi_ip,
            source_ip=dut1_svi_ip,
            packet_size=packet_size,
            duration=duration,
            total_packets=total_packets,
            source_interface=dut1_access_ports[0],
            dest_dut=dut2,
        )

        # DUT2 → DUT1
        st.log(f"Sending {total_packets} packets from DUT2 → DUT1")
        success2, result2 = self._generate_scapy_traffic(
            source_dut=dut2,
            dest_ip=dut1_svi_ip,
            source_ip=dut2_svi_ip,
            packet_size=packet_size,
            duration=duration,
            total_packets=total_packets,
            source_interface=dut2_access_ports[0],
            dest_dut=dut1,
        )

        if not (success1 and success2):
            st.report_fail("msg", "Traffic generation failed")

        # ===== PHASE 4: STOP LISTENERS =====
        st.banner("PHASE 4: Stopping tcpdump listeners")
        self._stop_tcpdump(dut1)
        self._stop_tcpdump(dut2)

        # ===== PHASE 5: VALIDATE USING PCAP FILES =====
        st.banner("PHASE 5: Counting packets in pcap files")

        # Count packets received on DUT1 (from DUT2)
        rx_count_d1 = self._count_packets_in_pcap(dut1, pcap_d1)
        st.log(f"Packets received on DUT1 (from DUT2): {rx_count_d1}")

        # Count packets received on DUT2 (from DUT1)
        rx_count_d2 = self._count_packets_in_pcap(dut2, pcap_d2)
        st.log(f"Packets received on DUT2 (from DUT1): {rx_count_d2}")

        # ===== PHASE 6: ASSERTIONS =====
        st.banner("PHASE 6: Validating packet counts")

        all_passed = True

        # Validate DUT1 received packets from DUT2
        if rx_count_d1 < total_packets:
            loss_percent = ((total_packets - rx_count_d1) / total_packets) * 100
            st.log(f"⚠️  DUT1 received {rx_count_d1}/{total_packets} packets ({loss_percent:.1f}% loss)")
            if loss_percent > 20:  # Allow up to 20% packet loss
                st.error(f"❌ DUT1 packet loss exceeds threshold: {loss_percent:.1f}% > 20%")
                all_passed = False
            else:
                st.log(f"✅ DUT1 packet loss acceptable: {loss_percent:.1f}% ≤ 20%")
        else:
            st.log(f"✅ DUT1 received {rx_count_d1} packets (expected: {total_packets})")

        # Validate DUT2 received packets from DUT1
        if rx_count_d2 < total_packets:
            loss_percent = ((total_packets - rx_count_d2) / total_packets) * 100
            st.log(f"⚠️  DUT2 received {rx_count_d2}/{total_packets} packets ({loss_percent:.1f}% loss)")
            if loss_percent > 20:  # Allow up to 20% packet loss
                st.error(f"❌ DUT2 packet loss exceeds threshold: {loss_percent:.1f}% > 20%")
                all_passed = False
            else:
                st.log(f"✅ DUT2 packet loss acceptable: {loss_percent:.1f}% ≤ 20%")
        else:
            st.log(f"✅ DUT2 received {rx_count_d2} packets (expected: {total_packets})")

        # ===== OPTIONAL: DEEP PACKET INSPECTION =====
        if rx_count_d1 > 0:
            st.banner("OPTIONAL: Deep packet inspection (first packet on DUT1)")
            packet_details = self._verify_packet_payload(dut1, pcap_d1, packet_index=0)
            if packet_details:
                st.log(f"First packet details: {packet_details}")

        # ===== FINAL RESULT =====
        if all_passed:
            st.log("✅ Bidirectional traffic validation successful")
            st.report_pass("test_case_passed")
        else:
            st.error("❌ Bidirectional traffic validation failed")
            st.report_fail("msg", f"Packet loss exceeded threshold (DUT1: {rx_count_d1}, DUT2: {rx_count_d2})")

    @pytest.mark.inventory(
        feature="VLAN_SVI_L3_Traffic_Tcpdump",
        testcases=["VLAN_SVI_L3_Traffic_Bidirectional_64B_Tcpdump"]
    )
    def test_svi_l3_traffic_bidirectional_64b_tcpdump(self) -> None:
        """
        TC 2.1 – Bidirectional SVI L3 traffic with 64-byte packets (tcpdump verification).

        Small packet size test (64 bytes) to verify:
        - Minimum sized packet handling through VLAN SVI
        - Tcpdump captures small packets correctly
        - Traffic flows in both directions on VLAN member ports
        - 10 seconds duration, allowing 10-20% packet loss
        """
        st.banner("Bidirectional Traffic Test: 64-byte packets with Tcpdump")

        # Get DUT handles
        dut1 = self._resolve_dut("D1")
        dut2 = self._resolve_dut("D2")

        if not dut1 or not dut2:
            st.report_fail("msg", "Unable to resolve DUT handles")

        # Get configuration
        intf_config = self.data.config.get("interface_config", {})
        dut1_cfg = intf_config.get("dut1", {})
        dut2_cfg = intf_config.get("dut2", {})
        dut1_svi_ip = dut1_cfg.get("svi_ip", "10.1.1.1")
        dut2_svi_ip = dut2_cfg.get("svi_ip", "10.1.1.2")
        dut1_access_ports = dut1_cfg.get("access_ports", ["Ethernet8", "Ethernet12"])
        dut2_access_ports = dut2_cfg.get("access_ports", ["Ethernet8", "Ethernet12"])

        # Traffic parameters for 64B test
        total_packets = 1000
        duration = 10
        packet_size = 64  # Minimum Ethernet frame size
        udp_port = 54321

        # Pcap file paths
        pcap_d1 = "/tmp/eth8_d1_64b.pcap"
        pcap_d2 = "/tmp/eth8_d2_64b.pcap"

        # ===== PHASE 1: PREPARATION =====
        st.banner("PHASE 1: Cleanup old pcap files")
        self._cleanup_pcap_files(dut1, pcap_d1)
        self._cleanup_pcap_files(dut2, pcap_d2)

        # ===== PHASE 2: START LISTENERS =====
        st.banner("PHASE 2: Starting tcpdump listeners")
        tcpdump1_ok = self._start_tcpdump(dut1, dut1_access_ports[0], pcap_d1, udp_port)
        tcpdump2_ok = self._start_tcpdump(dut2, dut2_access_ports[0], pcap_d2, udp_port)

        if not tcpdump1_ok or not tcpdump2_ok:
            st.report_fail("msg", "Failed to start tcpdump listeners")

        # ===== PHASE 3: GENERATE BIDIRECTIONAL TRAFFIC =====
        st.banner("PHASE 3: Generating bidirectional traffic (64-byte packets)")

        # DUT1 → DUT2
        st.log(f"Sending {total_packets} x 64B packets from DUT1 → DUT2")
        success1, result1 = self._generate_scapy_traffic(
            source_dut=dut1,
            dest_ip=dut2_svi_ip,
            source_ip=dut1_svi_ip,
            packet_size=packet_size,
            duration=duration,
            total_packets=total_packets,
            source_interface=dut1_access_ports[0],
            dest_dut=dut2,
        )

        # DUT2 → DUT1
        st.log(f"Sending {total_packets} x 64B packets from DUT2 → DUT1")
        success2, result2 = self._generate_scapy_traffic(
            source_dut=dut2,
            dest_ip=dut1_svi_ip,
            source_ip=dut2_svi_ip,
            packet_size=packet_size,
            duration=duration,
            total_packets=total_packets,
            source_interface=dut2_access_ports[0],
            dest_dut=dut1,
        )

        if not (success1 and success2):
            st.report_fail("msg", "Traffic generation failed")

        # ===== PHASE 4: STOP LISTENERS =====
        st.banner("PHASE 4: Stopping tcpdump listeners")
        self._stop_tcpdump(dut1)
        self._stop_tcpdump(dut2)

        # ===== PHASE 5: VALIDATE USING PCAP FILES =====
        st.banner("PHASE 5: Counting packets in pcap files")

        rx_count_d1 = self._count_packets_in_pcap(dut1, pcap_d1)
        st.log(f"Packets received on DUT1 (from DUT2): {rx_count_d1}")

        rx_count_d2 = self._count_packets_in_pcap(dut2, pcap_d2)
        st.log(f"Packets received on DUT2 (from DUT1): {rx_count_d2}")

        # ===== PHASE 6: VALIDATE =====
        st.banner("PHASE 6: Validating packet counts")

        all_passed = True

        # Validate DUT1 received packets from DUT2
        if rx_count_d1 < total_packets:
            loss_percent = ((total_packets - rx_count_d1) / total_packets) * 100
            st.log(f"⚠️  DUT1 received {rx_count_d1}/{total_packets} packets ({loss_percent:.1f}% loss)")
            if loss_percent > 20:
                st.error(f"❌ DUT1 packet loss exceeds threshold: {loss_percent:.1f}% > 20%")
                all_passed = False
            else:
                st.log(f"✅ DUT1 packet loss acceptable: {loss_percent:.1f}% ≤ 20%")
        else:
            st.log(f"✅ DUT1 received {rx_count_d1} packets (expected: {total_packets})")

        # Validate DUT2 received packets from DUT1
        if rx_count_d2 < total_packets:
            loss_percent = ((total_packets - rx_count_d2) / total_packets) * 100
            st.log(f"⚠️  DUT2 received {rx_count_d2}/{total_packets} packets ({loss_percent:.1f}% loss)")
            if loss_percent > 20:
                st.error(f"❌ DUT2 packet loss exceeds threshold: {loss_percent:.1f}% > 20%")
                all_passed = False
            else:
                st.log(f"✅ DUT2 packet loss acceptable: {loss_percent:.1f}% ≤ 20%")
        else:
            st.log(f"✅ DUT2 received {rx_count_d2} packets (expected: {total_packets})")

        # ===== FINAL RESULT =====
        if all_passed:
            st.log("✅ 64-byte bidirectional traffic validation successful")
            st.report_pass("test_case_passed")
        else:
            st.error("❌ 64-byte bidirectional traffic validation failed")
            st.report_fail("msg", f"Packet loss exceeded threshold (DUT1: {rx_count_d1}, DUT2: {rx_count_d2})")

    @pytest.mark.inventory(
        feature="VLAN_SVI_L3_Traffic_Tcpdump",
        testcases=["VLAN_SVI_L3_Traffic_Bidirectional_1500B_Tcpdump"]
    )
    def test_svi_l3_traffic_bidirectional_1500b_tcpdump(self) -> None:
        """
        TC 2.3 – Bidirectional SVI L3 traffic with 1500-byte packets (tcpdump verification).

        Maximum packet size test (1500 bytes) to verify:
        - Maximum MTU packet handling through VLAN SVI
        - Tcpdump captures large packets correctly
        - No fragmentation issues on VLAN member ports
        - Traffic flows in both directions
        - 10 seconds duration, allowing 10-20% packet loss
        """
        st.banner("Bidirectional Traffic Test: 1500-byte packets with Tcpdump")

        # Get DUT handles
        dut1 = self._resolve_dut("D1")
        dut2 = self._resolve_dut("D2")

        if not dut1 or not dut2:
            st.report_fail("msg", "Unable to resolve DUT handles")

        # Get configuration
        intf_config = self.data.config.get("interface_config", {})
        dut1_cfg = intf_config.get("dut1", {})
        dut2_cfg = intf_config.get("dut2", {})
        dut1_svi_ip = dut1_cfg.get("svi_ip", "10.1.1.1")
        dut2_svi_ip = dut2_cfg.get("svi_ip", "10.1.1.2")
        dut1_access_ports = dut1_cfg.get("access_ports", ["Ethernet8", "Ethernet12"])
        dut2_access_ports = dut2_cfg.get("access_ports", ["Ethernet8", "Ethernet12"])

        # Traffic parameters for 1500B test
        total_packets = 1000
        duration = 10
        packet_size = 1500  # Maximum Ethernet payload size
        udp_port = 54321

        # Pcap file paths
        pcap_d1 = "/tmp/eth8_d1_1500b.pcap"
        pcap_d2 = "/tmp/eth8_d2_1500b.pcap"

        # ===== PHASE 1: PREPARATION =====
        st.banner("PHASE 1: Cleanup old pcap files")
        self._cleanup_pcap_files(dut1, pcap_d1)
        self._cleanup_pcap_files(dut2, pcap_d2)

        # ===== PHASE 2: START LISTENERS =====
        st.banner("PHASE 2: Starting tcpdump listeners")
        tcpdump1_ok = self._start_tcpdump(dut1, dut1_access_ports[0], pcap_d1, udp_port)
        tcpdump2_ok = self._start_tcpdump(dut2, dut2_access_ports[0], pcap_d2, udp_port)

        if not tcpdump1_ok or not tcpdump2_ok:
            st.report_fail("msg", "Failed to start tcpdump listeners")

        # ===== PHASE 3: GENERATE BIDIRECTIONAL TRAFFIC =====
        st.banner("PHASE 3: Generating bidirectional traffic (1500-byte packets)")

        # DUT1 → DUT2
        st.log(f"Sending {total_packets} x 1500B packets from DUT1 → DUT2")
        success1, result1 = self._generate_scapy_traffic(
            source_dut=dut1,
            dest_ip=dut2_svi_ip,
            source_ip=dut1_svi_ip,
            packet_size=packet_size,
            duration=duration,
            total_packets=total_packets,
            source_interface=dut1_access_ports[0],
            dest_dut=dut2,
        )

        # DUT2 → DUT1
        st.log(f"Sending {total_packets} x 1500B packets from DUT2 → DUT1")
        success2, result2 = self._generate_scapy_traffic(
            source_dut=dut2,
            dest_ip=dut1_svi_ip,
            source_ip=dut2_svi_ip,
            packet_size=packet_size,
            duration=duration,
            total_packets=total_packets,
            source_interface=dut2_access_ports[0],
            dest_dut=dut1,
        )

        if not (success1 and success2):
            st.report_fail("msg", "Traffic generation failed")

        # ===== PHASE 4: STOP LISTENERS =====
        st.banner("PHASE 4: Stopping tcpdump listeners")
        self._stop_tcpdump(dut1)
        self._stop_tcpdump(dut2)

        # ===== PHASE 5: VALIDATE USING PCAP FILES =====
        st.banner("PHASE 5: Counting packets in pcap files")

        rx_count_d1 = self._count_packets_in_pcap(dut1, pcap_d1)
        st.log(f"Packets received on DUT1 (from DUT2): {rx_count_d1}")

        rx_count_d2 = self._count_packets_in_pcap(dut2, pcap_d2)
        st.log(f"Packets received on DUT2 (from DUT1): {rx_count_d2}")

        # ===== PHASE 6: VALIDATE =====
        st.banner("PHASE 6: Validating packet counts")

        all_passed = True

        # Validate DUT1 received packets from DUT2
        if rx_count_d1 < total_packets:
            loss_percent = ((total_packets - rx_count_d1) / total_packets) * 100
            st.log(f"⚠️  DUT1 received {rx_count_d1}/{total_packets} packets ({loss_percent:.1f}% loss)")
            if loss_percent > 20:
                st.error(f"❌ DUT1 packet loss exceeds threshold: {loss_percent:.1f}% > 20%")
                all_passed = False
            else:
                st.log(f"✅ DUT1 packet loss acceptable: {loss_percent:.1f}% ≤ 20%")
        else:
            st.log(f"✅ DUT1 received {rx_count_d1} packets (expected: {total_packets})")

        # Validate DUT2 received packets from DUT1
        if rx_count_d2 < total_packets:
            loss_percent = ((total_packets - rx_count_d2) / total_packets) * 100
            st.log(f"⚠️  DUT2 received {rx_count_d2}/{total_packets} packets ({loss_percent:.1f}% loss)")
            if loss_percent > 20:
                st.error(f"❌ DUT2 packet loss exceeds threshold: {loss_percent:.1f}% > 20%")
                all_passed = False
            else:
                st.log(f"✅ DUT2 packet loss acceptable: {loss_percent:.1f}% ≤ 20%")
        else:
            st.log(f"✅ DUT2 received {rx_count_d2} packets (expected: {total_packets})")

        # ===== FINAL RESULT =====
        if all_passed:
            st.log("✅ 1500-byte bidirectional traffic validation successful")
            st.report_pass("test_case_passed")
        else:
            st.error("❌ 1500-byte bidirectional traffic validation failed")
            st.report_fail("msg", f"Packet loss exceeded threshold (DUT1: {rx_count_d1}, DUT2: {rx_count_d2})")
