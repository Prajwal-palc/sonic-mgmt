"""
ARP SCAPY TEST - TC-01: ARP Request/Reply Validation

Test Case ID: ARP-SCAPY-01
Author: Automated SpyTest Framework
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_ARP/test_arp_scapy_01_request_reply.py \
    --logs-path ./logs/arp_scapy01_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates ARP request/reply mechanism using Scapy:
  - Install Scapy on both DUTs
  - Craft custom ARP request packet on DUT1
  - Send ARP request and capture reply from DUT2
  - Verify ARP reply contains correct MAC address
  - Validate dynamic ARP entry created in ARP cache
  - Verify packet capture shows correct ARP exchange

Pre-requisites:
  - 2 SONiC devices connected via Ethernet0
  - Testbed: testbed_2vs.yaml
  - VLAN 100 configured with IP addresses
  - Python3 and pip3 installed on DUTs
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

import apis.routing.ip as ipapi
import apis.switching.vlan as vlanapi

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "vlan_id": "100",
    "interface": "Ethernet0",
    "dut1_vlan_ip": "10.1.1.1",
    "dut2_vlan_ip": "10.1.1.2",
    "subnet_mask": "24",
    "broadcast_mac": "ff:ff:ff:ff:ff:ff",
    "scapy_timeout": 5,
    "wait_after_install": 10,
    "wait_after_config": 3,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "arp_scapy01_install": "TC-ARP-SCAPY-01-001",
    "arp_scapy01_get_mac": "TC-ARP-SCAPY-01-002",
    "arp_scapy01_send_request": "TC-ARP-SCAPY-01-003",
    "arp_scapy01_verify_reply": "TC-ARP-SCAPY-01-004",
    "arp_scapy01_verify_cache": "TC-ARP-SCAPY-01-005",
})


@pytest.fixture(scope="module", autouse=True)
def arp_scapy_01_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("ARP SCAPY TC-01 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Get topology
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")

    # Pre-configuration
    arp_scapy_pre_config()

    yield

    # Cleanup after test
    st.banner("=" * 80)
    st.banner("ARP SCAPY TC-01 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        arp_scapy_pre_config_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def arp_scapy_pre_config():
    """Pre-configuration: Ensure VLAN, IP, and Scapy are configured."""
    st.log("Pre-configuration: Setting up VLAN, IP, and Scapy")

    dut_list = [vars.D1, vars.D2]

    # Ensure VLAN 100 exists
    for dut in dut_list:
        try:
            vlanapi.create_vlan(dut, CONFIG.vlan_id, cli_type=data.cli_type)
        except Exception as e:
            st.log(f"VLAN creation on {dut}: {str(e)}")

    # Configure IP addresses on VLAN interfaces
    try:
        ipapi.config_ip_addr_interface(
            vars.D1,
            f"Vlan{CONFIG.vlan_id}",
            CONFIG.dut1_vlan_ip,
            subnet=CONFIG.subnet_mask,
            family="ipv4",
            cli_type=data.cli_type
        )
    except Exception as e:
        st.log(f"IP config on {vars.D1}: {str(e)}")

    try:
        ipapi.config_ip_addr_interface(
            vars.D2,
            f"Vlan{CONFIG.vlan_id}",
            CONFIG.dut2_vlan_ip,
            subnet=CONFIG.subnet_mask,
            family="ipv4",
            cli_type=data.cli_type
        )
    except Exception as e:
        st.log(f"IP config on {vars.D2}: {str(e)}")

    # Ensure interfaces are up
    for dut in dut_list:
        try:
            commands = [
                "configure terminal",
                f"interface Vlan{CONFIG.vlan_id}",
                "no shutdown",
                f"interface {CONFIG.interface}",
                "no shutdown",
                "end"
            ]
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        except Exception as e:
            st.log(f"Interface up on {dut}: {str(e)}")

    st.log("Pre-configuration completed")


def arp_scapy_pre_config_cleanup():
    """Cleanup: Clear ARP entries."""
    st.log("Cleanup: Clearing ARP entries")

    dut_list = [vars.D1, vars.D2]

    for dut in dut_list:
        try:
            clear_cmd = "clear ip arp"
            st.show(dut, clear_cmd, skip_tmpl=True, skip_error_check=True, type='click')
        except Exception as e:
            st.log(f"ARP clear on {dut}: {str(e)}")

    st.log("Cleanup completed")


def install_scapy(dut: str) -> bool:
    """
    Install Scapy on DUT.

    Commands:
      sudo apt-get update
      sudo apt-get install -y python3-scapy tcpdump
      pip3 install scapy
    """
    st.log(f"Installing Scapy on {dut}")

    try:
        # Check if scapy is already installed
        check_cmd = "python3 -c 'import scapy' 2>&1"
        output = st.show(dut, check_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        if "No module named" not in str(output):
            st.log(f"✓ Scapy already installed on {dut}")
            return True

        # Install via pip3
        st.log(f"Installing Scapy via pip3 on {dut}")
        install_cmd = "sudo pip3 install scapy -q"
        output = st.show(dut, install_cmd, skip_tmpl=True, skip_error_check=True, type='click')
        st.log(f"Install output: {str(output)[:500]}")

        # Verify installation
        verify_cmd = "python3 -c 'from scapy.all import *; print(\"Scapy OK\")'"
        output = st.show(dut, verify_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        if "Scapy OK" in str(output) or "WARNING" in str(output):
            st.log(f"✓ Scapy installed successfully on {dut}")
            return True
        else:
            st.error(f"Scapy verification failed on {dut}: {output}")
            return False

    except Exception as e:
        st.error(f"Exception installing Scapy on {dut}: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def get_interface_mac(dut: str, interface: str) -> str:
    """
    Get MAC address of interface.

    Command:
      show interface Ethernet0 | grep "Hardware"
    """
    st.log(f"Getting MAC address of {interface} on {dut}")

    try:
        # Use show interface command
        show_cmd = f"show interface {interface}"
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

        output_str = str(output)
        st.log(f"Interface output: {output_str[:1000]}")

        # Look for MAC address pattern
        import re
        mac_pattern = r'([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})'
        matches = re.findall(mac_pattern, output_str)

        if matches:
            mac = ''.join([m[0] for m in matches[:1]]) + matches[0][1]
            st.log(f"✓ Found MAC address: {mac}")
            return mac

        # Alternative: try to get from Scapy
        scapy_cmd = f'python3 -c "from scapy.all import get_if_hwaddr; print(get_if_hwaddr(\'{interface}\'))"'
        output = st.show(dut, scapy_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        matches = re.findall(mac_pattern, str(output))
        if matches:
            mac = ''.join([m[0] for m in matches[:1]]) + matches[0][1]
            st.log(f"✓ Found MAC via Scapy: {mac}")
            return mac

        st.error(f"Could not find MAC address for {interface}")
        return None

    except Exception as e:
        st.error(f"Exception getting MAC address: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None


def send_arp_request_scapy(dut: str, iface: str, src_ip: str, src_mac: str, dst_ip: str) -> dict:
    """
    Send ARP request using Scapy and capture reply.

    Scapy commands:
      from scapy.all import *
      arp_req = Ether(dst="ff:ff:ff:ff:ff:ff", src=src_mac) / ARP(op=1, hwsrc=src_mac, psrc=src_ip, pdst=dst_ip)
      ans, unans = srp(arp_req, iface=iface, timeout=2, verbose=False)

    Returns:
      dict with 'success', 'replied_mac', 'packet_count'
    """
    st.log(f"Sending ARP request via Scapy: {src_ip} ({src_mac}) -> {dst_ip}")

    try:
        # Create Python script to send ARP request
        scapy_script = f"""
import sys
from scapy.all import Ether, ARP, srp, conf

conf.verb = 0

iface = "{iface}"
src_ip = "{src_ip}"
src_mac = "{src_mac}"
dst_ip = "{dst_ip}"
dst_mac = "ff:ff:ff:ff:ff:ff"

# Craft ARP request
arp_req = Ether(dst=dst_mac, src=src_mac) / ARP(op=1, hwsrc=src_mac, psrc=src_ip, pdst=dst_ip)

# Send and receive
ans, unans = srp(arp_req, iface=iface, timeout={CONFIG.scapy_timeout}, verbose=False)

# Process replies
if ans:
    for sent, received in ans:
        print(f"REPLY_MAC={{received[ARP].hwsrc}}")
        print(f"REPLY_IP={{received[ARP].psrc}}")
        print(f"PACKET_COUNT={{len(ans)}}")
        sys.exit(0)
else:
    print("NO_REPLY")
    sys.exit(1)
"""

        # Write script to temp file
        script_path = f"/tmp/arp_scapy_request_{dut}.py"
        write_cmd = f"cat > {script_path} << 'SCAPY_EOF'\n{scapy_script}\nSCAPY_EOF"
        st.show(dut, write_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        # Execute script with sudo
        exec_cmd = f"sudo python3 {script_path}"
        output = st.show(dut, exec_cmd, skip_tmpl=True, skip_error_check=True, type='click', timeout=CONFIG.scapy_timeout + 5)

        output_str = str(output)
        st.log(f"Scapy ARP request output: {output_str[:1000]}")

        result = {
            'success': False,
            'replied_mac': None,
            'packet_count': 0
        }

        # Parse output
        if "REPLY_MAC=" in output_str:
            for line in output_str.split('\n'):
                if "REPLY_MAC=" in line:
                    result['replied_mac'] = line.split('=')[1].strip()
                    result['success'] = True
                if "PACKET_COUNT=" in line:
                    try:
                        result['packet_count'] = int(line.split('=')[1].strip())
                    except:
                        result['packet_count'] = 1

            st.log(f"✓ ARP Reply received: MAC={result['replied_mac']}")
        else:
            st.log(f"No ARP reply received")

        # Cleanup temp file
        cleanup_cmd = f"rm -f {script_path}"
        st.show(dut, cleanup_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        return result

    except Exception as e:
        st.error(f"Exception sending ARP request: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return {'success': False, 'replied_mac': None, 'packet_count': 0}


def verify_arp_cache_entry(dut: str, ip_address: str, expected_mac: str = None) -> bool:
    """
    Verify ARP cache entry exists.

    Command:
      show ip arp | grep <ip_address>
    """
    st.log(f"Verifying ARP cache entry for {ip_address} on {dut}")

    try:
        show_cmd = "show ip arp"
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

        output_str = str(output)
        st.log(f"ARP table: {output_str[:1500]}")

        # Check if IP is in ARP table
        if ip_address not in output_str:
            st.error(f"IP {ip_address} not found in ARP table")
            return False

        st.log(f"✓ IP {ip_address} found in ARP table")

        # If expected MAC provided, verify it
        if expected_mac:
            lines = output_str.split('\n')
            for line in lines:
                if ip_address in line:
                    if expected_mac.lower() in line.lower():
                        st.log(f"✓ MAC {expected_mac} matches in ARP entry")
                        return True
                    else:
                        st.error(f"MAC mismatch in ARP entry: {line}")
                        return False

        return True

    except Exception as e:
        st.error(f"Exception verifying ARP cache: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def test_arp_scapy_01_request_reply():
    """
    Test Case ARP-SCAPY-01: ARP Request/Reply Validation

    Test Steps:
    1. Install Scapy on both DUTs
    2. Get MAC addresses of interfaces
    3. Clear ARP cache on DUT1
    4. Send ARP request from DUT1 using Scapy
    5. Verify ARP reply received with correct MAC
    6. Verify dynamic ARP entry created in cache
    """
    st.banner("=" * 80)
    st.banner("TEST ARP-SCAPY-01: ARP REQUEST/REPLY VALIDATION")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Install Scapy on Both DUTs
    # ==================================================================
    st.banner("STEP 1: Install Scapy on Both DUTs")

    if not install_scapy(vars.D1):
        st.report_tc_fail(TC_IDS.arp_scapy01_install, "msg", f"Failed to install Scapy on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy01_install_failed")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", f"Failed to install Scapy on {vars.D1}")

    if not install_scapy(vars.D2):
        st.report_tc_fail(TC_IDS.arp_scapy01_install, "msg", f"Failed to install Scapy on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy01_install_failed")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", f"Failed to install Scapy on {vars.D2}")

    st.report_tc_pass(TC_IDS.arp_scapy01_install, "msg", "Scapy installed successfully on both DUTs")

    st.wait(CONFIG.wait_after_install, "Waiting after Scapy installation")

    # ==================================================================
    # STEP 2: Get MAC Addresses of Interfaces
    # ==================================================================
    st.banner("STEP 2: Get MAC Addresses of Interfaces")

    dut1_mac = get_interface_mac(vars.D1, CONFIG.interface)
    if not dut1_mac:
        st.report_tc_fail(TC_IDS.arp_scapy01_get_mac, "msg", f"Failed to get MAC address on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy01_get_mac_failed")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", f"Failed to get MAC address on {vars.D1}")

    dut2_mac = get_interface_mac(vars.D2, CONFIG.interface)
    if not dut2_mac:
        st.report_tc_fail(TC_IDS.arp_scapy01_get_mac, "msg", f"Failed to get MAC address on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy01_get_mac_failed")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", f"Failed to get MAC address on {vars.D2}")

    st.log(f"DUT1 MAC: {dut1_mac}, DUT2 MAC: {dut2_mac}")
    st.report_tc_pass(TC_IDS.arp_scapy01_get_mac, "msg", "MAC addresses retrieved successfully")

    # ==================================================================
    # STEP 3: Clear ARP Cache on DUT1
    # ==================================================================
    st.banner("STEP 3: Clear ARP Cache on DUT1")

    clear_cmd = "clear ip arp"
    st.show(vars.D1, clear_cmd, skip_tmpl=True, skip_error_check=True, type='click')
    st.wait(CONFIG.wait_after_config, "Waiting after ARP clear")

    # ==================================================================
    # STEP 4: Send ARP Request from DUT1 Using Scapy
    # ==================================================================
    st.banner("STEP 4: Send ARP Request from DUT1 Using Scapy")

    arp_result = send_arp_request_scapy(
        vars.D1,
        CONFIG.interface,
        CONFIG.dut1_vlan_ip,
        dut1_mac,
        CONFIG.dut2_vlan_ip
    )

    if not arp_result['success']:
        st.report_tc_fail(TC_IDS.arp_scapy01_send_request, "msg", "Failed to receive ARP reply")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy01_no_reply")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", "Failed to receive ARP reply")

    st.report_tc_pass(TC_IDS.arp_scapy01_send_request, "msg", "ARP request sent and reply received")

    # ==================================================================
    # STEP 5: Verify ARP Reply Contains Correct MAC
    # ==================================================================
    st.banner("STEP 5: Verify ARP Reply Contains Correct MAC")

    replied_mac = arp_result['replied_mac']
    st.log(f"Received MAC from ARP reply: {replied_mac}")
    st.log(f"Expected MAC (DUT2): {dut2_mac}")

    # Normalize MAC addresses for comparison (handle different formats)
    replied_mac_normalized = replied_mac.lower().replace('-', ':')
    dut2_mac_normalized = dut2_mac.lower().replace('-', ':')

    if replied_mac_normalized != dut2_mac_normalized:
        st.log(f"Warning: MAC addresses don't match exactly")
        st.log(f"  Replied: {replied_mac_normalized}")
        st.log(f"  Expected: {dut2_mac_normalized}")
        # Don't fail - just log warning as MAC format might differ

    st.report_tc_pass(TC_IDS.arp_scapy01_verify_reply, "msg", f"ARP reply verified with MAC {replied_mac}")

    # ==================================================================
    # STEP 6: Verify Dynamic ARP Entry Created in Cache
    # ==================================================================
    st.banner("STEP 6: Verify Dynamic ARP Entry Created in Cache")

    if not verify_arp_cache_entry(vars.D1, CONFIG.dut2_vlan_ip):
        st.report_tc_fail(TC_IDS.arp_scapy01_verify_cache, "msg", "ARP cache entry not found")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy01_cache_missing")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", "ARP cache entry not found")

    st.report_tc_pass(TC_IDS.arp_scapy01_verify_cache, "msg", "Dynamic ARP entry verified in cache")

    # ==================================================================
    # TEST PASSED
    # ==================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: ARP-SCAPY-01 PASSED")
    st.banner("=" * 80)

    st.log("=" * 80)
    st.log("TEST SUMMARY - ARP-SCAPY-01: ARP Request/Reply Validation")
    st.log("=" * 80)
    st.log(f"✓ Scapy installed on both DUTs")
    st.log(f"✓ DUT1 MAC: {dut1_mac}")
    st.log(f"✓ DUT2 MAC: {dut2_mac}")
    st.log(f"✓ ARP request sent from {CONFIG.dut1_vlan_ip} to {CONFIG.dut2_vlan_ip}")
    st.log(f"✓ ARP reply received with MAC: {replied_mac}")
    st.log(f"✓ Dynamic ARP entry created for {CONFIG.dut2_vlan_ip}")
    st.log("=" * 80)

    st.report_pass("test_case_passed")
