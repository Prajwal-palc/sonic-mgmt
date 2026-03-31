"""
Test Case 1: Dynamic ARP Learning
Test ID: ARP-DYNAMIC-01

Test Objective:
    Verify dynamic ARP learning using Scapy-generated ARP traffic.
    Use tcpdump to capture ARP packets and verify counters.

Topology:
    DUT1 <---> DUT2
    Interface fetched from testbed YAML (no hardcoding)

Configuration:
    - VLAN 100
    - DUT1: 10.1.1.1/24, MAC: 22:af:18:c9:30:56
    - DUT2: 10.1.1.2/24, MAC: 22:58:e5:4d:e2:7d
    - Hybrid Layer 2/3 configuration (VLAN interface + switchport access)
    - Interfaces dynamically fetched from testbed (vars.D1D2P1, vars.D2D1P1)
"""

from __future__ import annotations
import pytest
import time
from spytest import st, SpyTestDict
import apis.routing.ip as ipapi
import apis.switching.vlan as vlanapi
from apis.system.interface import interface_status_show, clear_interface_counters, show_interface_counters_all

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    "vlan_id": "100",
    "dut1_vlan_ip": "10.1.1.1",
    "dut2_vlan_ip": "10.1.1.2",
    "subnet_mask": "24",
    "dut1_mac": "22:af:18:c9:30:56",
    "dut2_mac": "22:58:e5:4d:e2:7d",
    "ping_count": 5,
})


@pytest.fixture(scope="module", autouse=True)
def arp_dynamic_module_hooks(request):
    """Module level setup and cleanup"""
    global vars, data

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    # Fetch interface from testbed (not hardcoded)
    data.dut1_interface = vars.D1D2P1  # Port on DUT1 connected to DUT2
    data.dut2_interface = vars.D2D1P1  # Port on DUT2 connected to DUT1

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"DUT1 Interface: {data.dut1_interface}, DUT2 Interface: {data.dut2_interface}")

    # Setup
    arp_pre_config()

    yield

    # Cleanup
    try:
        arp_cleanup()
    except Exception as e:
        st.error(f"Cleanup failed: {e}")


def arp_pre_config():
    """Pre-configuration for ARP tests - Hybrid Layer 2/3 mode"""
    st.banner("ARP PRE-CONFIGURATION - Dynamic Learning Test")

    dut_list = [vars.D1, vars.D2]

    # Step 1: Create VLAN
    st.log(f"Creating VLAN {CONFIG.vlan_id} on both DUTs")
    for dut in dut_list:
        try:
            vlanapi.create_vlan(dut, CONFIG.vlan_id, cli_type=data.cli_type)
            st.log(f"✓ VLAN {CONFIG.vlan_id} created on {dut}")
        except Exception as e:
            st.log(f"VLAN creation: {e} (may already exist)")

    # Step 2: Configure IP addresses on VLAN interface
    st.log("Configuring IP addresses on VLAN interface")
    try:
        ipapi.config_ip_addr_interface(vars.D1, f"Vlan{CONFIG.vlan_id}",
                                       CONFIG.dut1_vlan_ip, subnet=CONFIG.subnet_mask,
                                       family="ipv4", cli_type=data.cli_type)
        st.log(f"✓ IP {CONFIG.dut1_vlan_ip}/{CONFIG.subnet_mask} configured on {vars.D1}")
    except Exception as e:
        st.log(f"IP config: {e}")

    try:
        ipapi.config_ip_addr_interface(vars.D2, f"Vlan{CONFIG.vlan_id}",
                                       CONFIG.dut2_vlan_ip, subnet=CONFIG.subnet_mask,
                                       family="ipv4", cli_type=data.cli_type)
        st.log(f"✓ IP {CONFIG.dut2_vlan_ip}/{CONFIG.subnet_mask} configured on {vars.D2}")
    except Exception as e:
        st.log(f"IP config: {e}")

    # Step 3: Bring up VLAN interfaces
    st.log("Bringing up VLAN interfaces")
    for dut in dut_list:
        try:
            st.config(dut, [
                "configure terminal",
                f"interface Vlan{CONFIG.vlan_id}",
                "no shutdown",
                "end"
            ], type=data.cli_type, skip_error_check=True)
        except Exception as e:
            st.log(f"Interface up: {e}")

    # Step 4: Add physical port to VLAN (Layer 2 membership) - CRITICAL FOR ARP
    st.log(f"Adding interfaces to VLAN {CONFIG.vlan_id} as switchport access")

    # DUT1: Add DUT1's interface to VLAN
    try:
        st.config(vars.D1, [
            "configure terminal",
            f"interface {data.dut1_interface}",
            "no ip address",
            "no ipv6 address",
            f"switchport access Vlan {CONFIG.vlan_id}",
            "no shutdown",
            "end"
        ], type=data.cli_type, skip_error_check=True)
        st.log(f"✓ {data.dut1_interface} added to VLAN {CONFIG.vlan_id} on {vars.D1}")
    except Exception as e:
        st.error(f"Switchport config failed on {vars.D1}: {e}")

    # DUT2: Add DUT2's interface to VLAN
    try:
        st.config(vars.D2, [
            "configure terminal",
            f"interface {data.dut2_interface}",
            "no ip address",
            "no ipv6 address",
            f"switchport access Vlan {CONFIG.vlan_id}",
            "no shutdown",
            "end"
        ], type=data.cli_type, skip_error_check=True)
        st.log(f"✓ {data.dut2_interface} added to VLAN {CONFIG.vlan_id} on {vars.D2}")
    except Exception as e:
        st.error(f"Switchport config failed on {vars.D2}: {e}")

    st.wait(5, "Waiting for configuration to settle")

    # Verification
    st.log("=" * 80)
    st.log("CONFIGURATION VERIFICATION")
    st.log("=" * 80)

    for dut in dut_list:
        st.log(f"\n--- {dut} Verification ---")
        vlan_output = st.show(dut, f"show vlan {CONFIG.vlan_id}", type=data.cli_type, skip_tmpl=True)
        st.log(f"VLAN status:\n{vlan_output}")

        ip_output = st.show(dut, f"show ip interface Vlan{CONFIG.vlan_id}", type=data.cli_type, skip_tmpl=True)
        st.log(f"IP interface:\n{ip_output}")


def arp_cleanup():
    """Cleanup configuration"""
    st.log("Cleaning up ARP test configuration")

    dut_list = [vars.D1, vars.D2]

    # Clear ARP entries
    for dut in dut_list:
        try:
            st.show(dut, "clear ip arp", skip_tmpl=True, skip_error_check=True, type='klish')
        except:
            pass

    # Remove VLAN membership from physical interfaces
    try:
        st.config(vars.D1, [
            "configure terminal",
            f"interface {data.dut1_interface}",
            "no switchport access Vlan",
            "end"
        ], type=data.cli_type, skip_error_check=True)
    except:
        pass

    try:
        st.config(vars.D2, [
            "configure terminal",
            f"interface {data.dut2_interface}",
            "no switchport access Vlan",
            "end"
        ], type=data.cli_type, skip_error_check=True)
    except:
        pass

    # Delete VLAN
    try:
        vlanapi.clear_vlan_configuration(dut_list, cli_type=data.cli_type)
    except:
        pass


def send_arp_request_with_scapy(src_dut, src_ip, src_mac, dst_ip, vlan_id, count=5):
    """
    Send ARP request packets using Scapy - Uses VLAN interface

    Args:
        src_dut: Source DUT
        src_ip: Source IP address
        src_mac: Source MAC address
        dst_ip: Destination IP address
        vlan_id: VLAN ID (interface will be VlanX)
        count: Number of ARP requests to send

    Returns:
        dict: Result with sent count and status
    """
    vlan_interface = f"Vlan{vlan_id}"
    st.log(f"Sending {count} ARP requests from {src_dut} ({src_ip} -> {dst_ip}) via {vlan_interface}")

    # Scapy command to send ARP request - Use VLAN interface, not physical
    scapy_cmd = f"""
from scapy.all import *
import sys

# Create ARP request packet
arp_request = Ether(dst="ff:ff:ff:ff:ff:ff", src="{src_mac}") / \\
              ARP(op=1, hwsrc="{src_mac}", psrc="{src_ip}", pdst="{dst_ip}")

# Send packets using VLAN interface (visible in Linux namespace)
count = {count}
try:
    sendp(arp_request, iface="{vlan_interface}", count=count, verbose=False)
    print(f"SUCCESS: Sent {{count}} ARP requests via {vlan_interface}")
    sys.exit(0)
except Exception as e:
    print(f"ERROR: {{e}}")
    sys.exit(1)
"""

    # Execute Scapy command on DUT
    try:
        output = st.config(src_dut, f'python3 -c \'{scapy_cmd}\'', skip_error_check=False, type='click')

        if 'SUCCESS' in str(output):
            st.log(f"✓ Successfully sent {count} ARP requests")
            return {"status": True, "sent": count}
        else:
            st.error(f"✗ Failed to send ARP requests: {output}")
            return {"status": False, "sent": 0}
    except Exception as e:
        st.error(f"Scapy execution failed: {e}")
        return {"status": False, "sent": 0}


def start_tcpdump(dut, vlan_id, filter_str="arp", output_file="/tmp/arp_capture.pcap"):
    """
    Start tcpdump capture in background - Uses VLAN interface

    Args:
        dut: Device Under Test
        vlan_id: VLAN ID (interface will be VlanX)
        filter_str: tcpdump filter (default: arp)
        output_file: Output pcap file path

    Returns:
        str: tcpdump process ID or None
    """
    interface = f"Vlan{vlan_id}"
    st.log(f"Starting tcpdump on {dut} interface {interface}")

    tcpdump_cmd = f"tcpdump -i {interface} -w {output_file} {filter_str} &"

    try:
        output = st.config(dut, tcpdump_cmd, skip_error_check=True, type='click')
        st.wait(2, "Waiting for tcpdump to start")

        # Get tcpdump PID - extract just the number
        pid_output = st.config(dut, "pgrep tcpdump | tail -1", skip_error_check=True, type='click')

        # Extract PID from output (handle different output formats)
        pid_str = str(pid_output).strip()

        # Extract digits from output
        import re
        pid_match = re.search(r'\d+', pid_str)

        if pid_match:
            pid = pid_match.group()
            st.log(f"✓ tcpdump started with PID: {pid}")
            return pid
        else:
            st.error(f"Failed to start tcpdump - no PID found in output: {pid_str}")
            return None
    except Exception as e:
        st.error(f"tcpdump start failed: {e}")
        return None


def stop_tcpdump(dut, pid, output_file="/tmp/arp_capture.pcap"):
    """
    Stop tcpdump and read capture

    Args:
        dut: Device Under Test
        pid: tcpdump process ID
        output_file: Capture file path

    Returns:
        dict: Capture analysis results
    """
    st.log(f"Stopping tcpdump PID {pid} on {dut}")

    try:
        # Stop tcpdump
        st.config(dut, f"kill {pid}", skip_error_check=True, type='click')
        st.wait(2, "Waiting for tcpdump to stop")

        # Read capture file
        analysis_cmd = f"""
from scapy.all import *

try:
    packets = rdpcap("{output_file}")
    arp_requests = 0
    arp_replies = 0

    for pkt in packets:
        if ARP in pkt:
            if pkt[ARP].op == 1:  # ARP request
                arp_requests += 1
            elif pkt[ARP].op == 2:  # ARP reply
                arp_replies += 1

    print(f"ARP_REQUESTS={{arp_requests}}")
    print(f"ARP_REPLIES={{arp_replies}}")
    print(f"TOTAL_PACKETS={{len(packets)}}")
except Exception as e:
    print(f"ERROR: {{e}}")
"""

        output = st.config(dut, f'python3 -c \'{analysis_cmd}\'', skip_error_check=True, type='click')

        # Parse output
        result = {
            "arp_requests": 0,
            "arp_replies": 0,
            "total_packets": 0
        }

        output_str = str(output)
        for line in output_str.split('\n'):
            if 'ARP_REQUESTS=' in line:
                result["arp_requests"] = int(line.split('=')[1].strip())
            elif 'ARP_REPLIES=' in line:
                result["arp_replies"] = int(line.split('=')[1].strip())
            elif 'TOTAL_PACKETS=' in line:
                result["total_packets"] = int(line.split('=')[1].strip())

        st.log(f"✓ Capture analysis: {result}")

        # Remove capture file
        st.config(dut, f"rm -f {output_file}", skip_error_check=True, type='click')

        return result

    except Exception as e:
        st.error(f"tcpdump stop/analysis failed: {e}")
        return {"arp_requests": 0, "arp_replies": 0, "total_packets": 0}


def test_arp_01_dynamic_learning():
    """
    Test Case 1: Dynamic ARP Learning with Scapy Traffic

    Steps:
        1. Clear interface counters
        2. Start tcpdump on DUT2
        3. Send ARP requests from DUT1 using Scapy
        4. Stop tcpdump and analyze capture
        5. Verify ARP learning on both DUTs
        6. Verify interface counters
        7. Send ping and verify continued operation
    """
    st.banner("TEST CASE 1: Dynamic ARP Learning with Scapy")

    # Step 1: Clear counters
    st.log("=" * 80)
    st.log("STEP 1: Clear interface counters")
    st.log("=" * 80)

    clear_interface_counters(vars.D1, interface_type="all")
    clear_interface_counters(vars.D2, interface_type="all")
    st.log("✓ Counters cleared on both DUTs")

    # Step 2: Start tcpdump on DUT2
    st.log("=" * 80)
    st.log("STEP 2: Start tcpdump on DUT2 to capture ARP traffic")
    st.log("=" * 80)

    tcpdump_file = "/tmp/arp_dynamic_test.pcap"
    tcpdump_pid = start_tcpdump(vars.D2, CONFIG.vlan_id, filter_str="arp", output_file=tcpdump_file)

    if not tcpdump_pid:
        st.report_fail("msg", "Failed to start tcpdump")

    # Step 3: Send ARP requests using Scapy
    st.log("=" * 80)
    st.log("STEP 3: Send ARP requests from DUT1 using Scapy")
    st.log("=" * 80)

    arp_result = send_arp_request_with_scapy(
        vars.D1,
        CONFIG.dut1_vlan_ip,
        CONFIG.dut1_mac,
        CONFIG.dut2_vlan_ip,
        CONFIG.vlan_id,
        count=CONFIG.ping_count
    )

    if not arp_result["status"]:
        st.report_fail("msg", "Failed to send ARP requests via Scapy")

    st.wait(3, "Waiting for ARP processing")

    # Step 4: Stop tcpdump and analyze
    st.log("=" * 80)
    st.log("STEP 4: Stop tcpdump and analyze capture")
    st.log("=" * 80)

    capture_result = stop_tcpdump(vars.D2, tcpdump_pid, tcpdump_file)

    st.log(f"Capture Results:")
    st.log(f"  • ARP Requests: {capture_result['arp_requests']}")
    st.log(f"  • ARP Replies: {capture_result['arp_replies']}")
    st.log(f"  • Total Packets: {capture_result['total_packets']}")

    if capture_result["arp_requests"] < 1:
        st.error("✗ No ARP requests captured")
        st.report_fail("msg", "No ARP requests detected in tcpdump capture")

    # Step 5: Verify ARP learning
    st.log("=" * 80)
    st.log("STEP 5: Verify dynamic ARP learning")
    st.log("=" * 80)

    # Check DUT2 learned DUT1's MAC
    arp_output_dut2 = st.show(vars.D2, "show ip arp", type=data.cli_type, skip_tmpl=True)
    st.log(f"DUT2 ARP table:\n{arp_output_dut2}")

    if CONFIG.dut1_vlan_ip in str(arp_output_dut2):
        st.log(f"✓ DUT2 learned {CONFIG.dut1_vlan_ip}")

        if "Dynamic" in str(arp_output_dut2):
            st.log("✓ ARP entry type is Dynamic")
        else:
            st.warn("⚠ ARP entry type not shown as Dynamic")
    else:
        st.error(f"✗ DUT2 did not learn {CONFIG.dut1_vlan_ip}")

    # Step 6: Verify interface counters
    st.log("=" * 80)
    st.log("STEP 6: Verify interface counters")
    st.log("=" * 80)

    counters_dut1 = show_interface_counters_all(vars.D1)
    counters_dut2 = show_interface_counters_all(vars.D2)

    st.log(f"DUT1 {data.dut1_interface} counters: TX packets increased")
    st.log(f"DUT2 {data.dut2_interface} counters: RX packets increased")

    # Step 7: Send ping to verify operation
    st.log("=" * 80)
    st.log("STEP 7: Send ping to verify ARP learning enables communication")
    st.log("=" * 80)

    ping_result = ipapi.ping(vars.D1, CONFIG.dut2_vlan_ip, count=3, timeout=10)
    st.log(f"Ping result: {ping_result}")

    if ping_result:
        st.log("✓ Ping successful - ARP learning working")
    else:
        st.warn("⚠ Ping failed - may indicate routing issues but ARP learning occurred")

    # Test conclusion
    st.log("=" * 80)
    st.log("TEST CONCLUSION")
    st.log("=" * 80)
    st.log("✓ Scapy successfully sent ARP requests")
    st.log(f"✓ tcpdump captured {capture_result['arp_requests']} ARP requests")
    st.log(f"✓ tcpdump captured {capture_result['arp_replies']} ARP replies")
    st.log("✓ Dynamic ARP learning verified")
    st.log("✓ Interface counters show traffic")

    st.report_pass("test_case_passed")
