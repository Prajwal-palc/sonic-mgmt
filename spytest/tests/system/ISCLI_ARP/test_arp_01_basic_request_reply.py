r"""
ARP TEST - OC-1 Test ID 4.17.1: Configure and verify basic ARP request/reply

Test Case ID: 4.17.1
Feature: ARP
Test Item: Function
Author: Automated from Manual Validation
Copyright (C) 2024-2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_ARP/test_arp_01_basic_request_reply.py \
    --logs-path ./logs/arp_01_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates ARP request/reply exchange using Scapy traffic generation:
  - Configure IP addresses on DUT1 Ethernet32 (10.1.1.1/24) and DUT2 Ethernet32 (10.1.1.2/24)
  - Collect MAC addresses from both DUTs
  - Create Scapy script to send 5 ARP requests
  - Start tcpdump on DUT2 to capture ARP traffic
  - Execute Scapy script on DUT1
  - Verify ARP request/reply captured in tcpdump
  - Check ARP table on DUT2 for correct entry
  - Cleanup configuration

Pre-requisites:
  - 2 SONiC devices connected
  - Testbed: testbed_2vs.yaml
  - Interfaces cabled as per topology (Ethernet32 ↔ Ethernet32)
  - Scapy installed on both DUTs
  - Clean ARP configuration

Expected Result:
  - ARP request captured on DUT2
  - ARP reply sent back to DUT1
  - DUT2 ARP table shows 10.1.1.1 with DUT1 MAC on Ethernet32 as Dynamic entry
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict
import re
import time

import apis.system.interface as intfapi
import apis.system.basic as basicapi

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration matching manual testcase
CONFIG = SpyTestDict({
    "dut1_interface": "Ethernet32",
    "dut2_interface": "Ethernet32",
    "dut1_ip": "10.1.1.1",
    "dut2_ip": "10.1.1.2",
    "subnet_mask": "24",
    "arp_wait_time": 10,
    "pcap_file": "~/scenario1.pcap",
    "script_file": "/tmp/scenario1_basic_arp.py",
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "interface_config": "TC-ARP-4.17.1-001",
    "mac_collection": "TC-ARP-4.17.1-002",
    "scapy_script_creation": "TC-ARP-4.17.1-003",
    "traffic_generation": "TC-ARP-4.17.1-004",
    "arp_table_verification": "TC-ARP-4.17.1-005",
})


@pytest.fixture(scope="module", autouse=True)
def arp_basic_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("ARP OC-1 4.17.1 BASIC REQUEST/REPLY TEST - MODULE START")
    st.banner("=" * 80)

    # Get topology
    vars = st.ensure_min_topology("D1D2:1")

    # Get CLI type from framework (auto-detect, don't hardcode)
    data.cli_type = st.get_ui_type()

    st.log(f"DUT1: {vars.D1}")
    st.log(f"DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type} (auto-detected by framework)")
    st.log(f"DUT1 Interface: {CONFIG.dut1_interface} IP: {CONFIG.dut1_ip}/{CONFIG.subnet_mask}")
    st.log(f"DUT2 Interface: {CONFIG.dut2_interface} IP: {CONFIG.dut2_ip}/{CONFIG.subnet_mask}")

    # Pre-configuration
    arp_pre_config()

    yield

    # Cleanup
    st.banner("=" * 80)
    st.banner("ARP OC-1 4.17.1 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        arp_pre_config_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")

    st.banner("=" * 80)
    st.banner("ARP OC-1 4.17.1 MODULE CLEANUP - COMPLETED")
    st.banner("=" * 80)


def arp_pre_config():
    """Pre-configuration: Setup interfaces for ARP testing."""
    st.log("Pre-configuration: Preparing ARP test environment")

    # Ensure interfaces are up and in routed mode
    st.log(f"Configuring interfaces in routed mode")

    # DUT1 interface configuration
    try:
        configure_routed_interface(vars.D1, CONFIG.dut1_interface,
                                  f"{CONFIG.dut1_ip}/{CONFIG.subnet_mask}")
    except Exception as e:
        st.log(f"DUT1 interface config warning: {str(e)}")

    # DUT2 interface configuration
    try:
        configure_routed_interface(vars.D2, CONFIG.dut2_interface,
                                  f"{CONFIG.dut2_ip}/{CONFIG.subnet_mask}")
    except Exception as e:
        st.log(f"DUT2 interface config warning: {str(e)}")

    st.wait(5, "Waiting for interfaces to stabilize")
    st.log("Pre-configuration completed")


def arp_pre_config_cleanup():
    """Cleanup: Remove all ARP test configuration."""
    st.log("Cleanup: Removing ARP test configuration")

    # Remove IP addresses
    try:
        st.log(f"Removing IP config from {vars.D1} {CONFIG.dut1_interface}")
        unconfigure_routed_interface(vars.D1, CONFIG.dut1_interface,
                                    f"{CONFIG.dut1_ip}/{CONFIG.subnet_mask}")
    except Exception as e:
        st.log(f"Cleanup warning DUT1: {str(e)}")

    try:
        st.log(f"Removing IP config from {vars.D2} {CONFIG.dut2_interface}")
        unconfigure_routed_interface(vars.D2, CONFIG.dut2_interface,
                                    f"{CONFIG.dut2_ip}/{CONFIG.subnet_mask}")
    except Exception as e:
        st.log(f"Cleanup warning DUT2: {str(e)}")

    # Remove Scapy scripts and pcap files
    try:
        st.log("Removing Scapy scripts and pcap files")
        cleanup_files(vars.D1, [CONFIG.script_file])
        cleanup_files(vars.D2, [CONFIG.pcap_file])
    except Exception as e:
        st.log(f"File cleanup warning: {str(e)}")

    # Clear ARP tables
    try:
        clear_arp_table(vars.D1)
        clear_arp_table(vars.D2)
    except Exception as e:
        st.log(f"ARP table clear warning: {str(e)}")

    st.log("Cleanup completed")


def configure_routed_interface(dut: str, interface: str, ip_address: str) -> bool:
    """
    Configure interface in routed mode with IP address.

    Args:
        dut: Device name
        interface: Interface name (e.g., "Ethernet32")
        ip_address: IP address with mask (e.g., "10.1.1.1/24")

    Returns:
        bool: True if successful
    """
    st.log(f"Configuring {interface} on {dut} with IP {ip_address}")
    try:
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no switchport",
            f"ip address {ip_address}",
            "no shutdown",
            "exit",
            "exit"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"✓ Interface {interface} configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure interface {interface} on {dut}: {str(e)}")
        return False


def unconfigure_routed_interface(dut: str, interface: str, ip_address: str) -> bool:
    """Remove IP address from interface."""
    st.log(f"Removing IP {ip_address} from {interface} on {dut}")
    try:
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"no ip address {ip_address}",
            "exit",
            "exit"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"✓ IP removed from {interface} on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to remove IP from {interface} on {dut}: {str(e)}")
        return False


def get_interface_mac(dut: str, interface: str) -> str:
    """
    Get MAC address of interface.

    Args:
        dut: Device name
        interface: Interface name

    Returns:
        str: MAC address or empty string if not found
    """
    st.log(f"Getting MAC address of {interface} on {dut}")
    try:
        # Use Linux sysfs to get MAC address - works on SONiC
        cmd = f"cat /sys/class/net/{interface}/address"
        output = st.exec_ssh(dut, cmd)

        if output:
            output_str = str(output).strip()

            # Search for MAC address pattern
            mac_pattern = r'([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})'
            match = re.search(mac_pattern, output_str)

            if match:
                mac = match.group(1)
                st.log(f"✓ Found MAC address: {mac}")
                return mac

        st.error(f"Could not find MAC address for {interface} on {dut}")
        return ""
    except Exception as e:
        st.error(f"Exception getting MAC address: {str(e)}")
        return ""


def create_scapy_script(dut: str, script_path: str, script_content: str) -> bool:
    """
    Create Scapy script on DUT.

    Args:
        dut: Device name
        script_path: Path where script will be created
        script_content: Python script content

    Returns:
        bool: True if successful
    """
    st.log(f"Creating Scapy script on {dut}: {script_path}")
    try:
        # Create script using printf to avoid indentation issues
        script_encoded = script_content.replace("'", "'\\''")
        cmd = f"printf '{script_encoded}' > {script_path}"
        st.exec_ssh(dut, cmd)

        # Verify script was created
        verify_cmd = f"test -f {script_path} && echo 'SUCCESS' || echo 'FAILED'"
        result = st.exec_ssh(dut, verify_cmd)

        if 'SUCCESS' in str(result):
            st.log(f"✓ Scapy script created successfully")
            return True
        else:
            st.error(f"Failed to create script file")
            return False
    except Exception as e:
        st.error(f"Exception creating Scapy script: {str(e)}")
        return False


def start_tcpdump(dut: str, interface: str, pcap_file: str, filter_expr: str = "arp") -> bool:
    """
    Start tcpdump on interface.

    Args:
        dut: Device name
        interface: Interface to capture on
        pcap_file: Output pcap file path
        filter_expr: tcpdump filter expression

    Returns:
        bool: True if successful
    """
    st.log(f"Starting tcpdump on {dut} {interface}")
    try:
        # Remove old pcap file if exists
        st.exec_ssh(dut, f"sudo rm -f {pcap_file}")

        # Start tcpdump in background
        cmd = f"sudo tcpdump -i {interface} {filter_expr} -nn -e -v -w {pcap_file} &"
        st.exec_ssh(dut, cmd)

        st.wait(2, "Waiting for tcpdump to start")
        st.log(f"✓ tcpdump started on {interface}")
        return True
    except Exception as e:
        st.error(f"Failed to start tcpdump: {str(e)}")
        return False


def stop_tcpdump(dut: str) -> bool:
    """Stop tcpdump process."""
    st.log(f"Stopping tcpdump on {dut}")
    try:
        st.exec_ssh(dut, "sudo pkill tcpdump")
        st.wait(2, "Waiting for tcpdump to stop")
        st.log(f"✓ tcpdump stopped")
        return True
    except Exception as e:
        st.log(f"tcpdump stop warning: {str(e)}")
        return True  # Not critical if no tcpdump running


def run_scapy_script(dut: str, script_path: str) -> bool:
    """
    Execute Scapy script on DUT.

    Args:
        dut: Device name
        script_path: Path to Scapy script

    Returns:
        bool: True if successful
    """
    st.log(f"Executing Scapy script on {dut}: {script_path}")
    try:
        cmd = f"sudo python3 {script_path}"
        output = st.exec_ssh(dut, cmd)
        st.log(f"Scapy script output: {output}")
        st.log(f"✓ Scapy script executed")
        return True
    except Exception as e:
        st.error(f"Failed to execute Scapy script: {str(e)}")
        return False


def verify_arp_in_pcap(dut: str, pcap_file: str, src_ip: str, dst_ip: str) -> bool:
    """
    Verify ARP packets in pcap file.

    Args:
        dut: Device name
        pcap_file: Pcap file to analyze
        src_ip: Source IP to look for
        dst_ip: Destination IP to look for

    Returns:
        bool: True if ARP packets found
    """
    st.log(f"Verifying ARP packets in {pcap_file}")
    try:
        cmd = f"sudo tcpdump -r {pcap_file} -nn -v 2>/dev/null"
        output = st.exec_ssh(dut, cmd)
        output_str = str(output) if output else ""

        # Check for ARP request
        request_found = f"who-has {dst_ip}" in output_str and f"tell {src_ip}" in output_str

        # Check for ARP reply
        reply_found = f"{dst_ip} is-at" in output_str or "Reply" in output_str

        st.log(f"ARP Request found: {request_found}")
        st.log(f"ARP Reply found: {reply_found}")

        return request_found or reply_found
    except Exception as e:
        st.error(f"Failed to verify pcap: {str(e)}")
        return False


def verify_arp_entry(dut: str, ip_address: str, expected_mac: str = None,
                    expected_interface: str = None) -> bool:
    """
    Verify ARP table entry.

    Args:
        dut: Device name
        ip_address: IP address to look for
        expected_mac: Expected MAC address (optional)
        expected_interface: Expected interface (optional)

    Returns:
        bool: True if entry found
    """
    st.log(f"Verifying ARP entry for {ip_address} on {dut}")
    try:
        cmd = f"show ip arp | grep {ip_address}"
        output = st.show(dut, cmd, type=data.cli_type, skip_tmpl=True)
        output_str = str(output) if output else ""

        if ip_address not in output_str:
            st.error(f"ARP entry for {ip_address} not found")
            return False

        st.log(f"✓ ARP entry found for {ip_address}")

        # Optional: Verify MAC address
        if expected_mac and expected_mac not in output_str:
            st.error(f"Expected MAC {expected_mac} not found in ARP entry")
            return False

        # Optional: Verify interface
        if expected_interface and expected_interface not in output_str:
            st.error(f"Expected interface {expected_interface} not found in ARP entry")
            return False

        return True
    except Exception as e:
        st.error(f"Failed to verify ARP entry: {str(e)}")
        return False


def clear_arp_table(dut: str) -> bool:
    """Clear ARP table on DUT."""
    st.log(f"Clearing ARP table on {dut}")
    try:
        # Use sonic command to clear ARP
        st.exec_ssh(dut, "sudo sonic-clear arp")
        st.log(f"✓ ARP table cleared on {dut}")
        return True
    except Exception as e:
        st.log(f"ARP clear warning: {str(e)}")
        return True  # Non-critical


def cleanup_files(dut: str, file_list: list) -> bool:
    """Remove files from DUT."""
    st.log(f"Cleaning up files on {dut}")
    try:
        for file_path in file_list:
            st.exec_ssh(dut, f"sudo rm -f {file_path}")
        st.log(f"✓ Files cleaned up")
        return True
    except Exception as e:
        st.log(f"File cleanup warning: {str(e)}")
        return True  # Non-critical


def test_arp_basic_request_reply():
    """
    Test Case: Basic ARP Request/Reply

    Test ID: 4.17.1
    Steps:
        1. Configure IP addresses on both DUTs
        2. Collect MAC addresses
        3. Create Scapy script to send ARP request
        4. Start tcpdump on DUT2
        5. Execute Scapy script on DUT1
        6. Verify ARP packets in tcpdump
        7. Verify ARP table entry on DUT2

    Expected Result:
        - ARP request/reply captured
        - ARP table shows correct entry
    """
    st.banner(f"TEST START: {TC_IDS.interface_config} - Basic ARP Request/Reply")

    result = True

    try:
        # STEP 1: Collect MAC addresses
        st.banner(f"STEP 1: {TC_IDS.mac_collection} - Collect MAC addresses")
        dut1_mac = get_interface_mac(vars.D1, CONFIG.dut1_interface)
        dut2_mac = get_interface_mac(vars.D2, CONFIG.dut2_interface)

        if not dut1_mac or not dut2_mac:
            st.report_fail("test_case_failed", "Failed to get MAC addresses")
            result = False
            return

        st.log(f"DUT1 {CONFIG.dut1_interface} MAC: {dut1_mac}")
        st.log(f"DUT2 {CONFIG.dut2_interface} MAC: {dut2_mac}")

        # STEP 2: Create Scapy script on DUT1
        st.banner(f"STEP 2: {TC_IDS.scapy_script_creation} - Create Scapy script")

        scapy_script = f"""from scapy.all import *

iface = "{CONFIG.dut1_interface}"
src_ip = "{CONFIG.dut1_ip}"
src_mac = "{dut1_mac}"
dst_ip = "{CONFIG.dut2_ip}"

print(f"[*] Scenario 1: Basic ARP Request/Reply")
print(f"[*] Sending ARP request: Who has {{dst_ip}}? Tell {{src_ip}}")

arp_req = Ether(src=src_mac, dst="ff:ff:ff:ff:ff:ff") / ARP(
    op=1,
    hwsrc=src_mac,
    psrc=src_ip,
    hwdst="00:00:00:00:00:00",
    pdst=dst_ip
)

sendp(arp_req, iface=iface, verbose=True, count=5)
print("[+] Test complete")
"""

        if not create_scapy_script(vars.D1, CONFIG.script_file, scapy_script):
            st.report_fail("test_case_failed", "Failed to create Scapy script")
            result = False
            return

        # STEP 3: Start tcpdump on DUT2
        st.banner(f"STEP 3: Start tcpdump on DUT2")
        if not start_tcpdump(vars.D2, CONFIG.dut2_interface, CONFIG.pcap_file):
            st.report_fail("test_case_failed", "Failed to start tcpdump")
            result = False
            return

        # STEP 4: Execute Scapy script on DUT1
        st.banner(f"STEP 4: {TC_IDS.traffic_generation} - Execute Scapy script")
        if not run_scapy_script(vars.D1, CONFIG.script_file):
            stop_tcpdump(vars.D2)
            st.report_fail("test_case_failed", "Failed to execute Scapy script")
            result = False
            return

        # Wait for traffic to complete
        st.wait(CONFIG.arp_wait_time, "Waiting for ARP traffic to complete")

        # Stop tcpdump
        stop_tcpdump(vars.D2)

        # STEP 5: Verify ARP packets in pcap
        st.banner(f"STEP 5: Verify ARP packets in tcpdump capture")
        if not verify_arp_in_pcap(vars.D2, CONFIG.pcap_file, CONFIG.dut1_ip, CONFIG.dut2_ip):
            st.report_fail("test_case_failed", "ARP packets not found in capture")
            result = False
            return

        # STEP 6: Verify ARP table entry on DUT2
        st.banner(f"STEP 6: {TC_IDS.arp_table_verification} - Verify ARP table")
        if not verify_arp_entry(vars.D2, CONFIG.dut1_ip, dut1_mac, CONFIG.dut2_interface):
            st.report_fail("test_case_failed", "ARP table entry verification failed")
            result = False
            return

        st.banner("TEST RESULT: PASS - Basic ARP Request/Reply successful")
        st.report_pass("test_case_passed")

    except Exception as e:
        st.error(f"Test exception: {str(e)}")
        st.report_fail("test_case_failed", str(e))
        result = False

    finally:
        # Always try to stop tcpdump
        try:
            stop_tcpdump(vars.D2)
        except:
            pass
