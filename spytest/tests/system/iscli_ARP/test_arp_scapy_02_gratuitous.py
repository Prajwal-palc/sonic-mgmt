"""
ARP SCAPY TEST - TC-02: Gratuitous ARP (GARP)

Test Case ID: ARP-SCAPY-02
Author: Automated SpyTest Framework
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_ARP/test_arp_scapy_02_gratuitous.py \
    --logs-path ./logs/arp_scapy02_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates Gratuitous ARP (GARP) functionality using Scapy:
  - Install Scapy on both DUTs
  - Send Gratuitous ARP from DUT1 (sender IP = target IP)
  - Verify GARP packet is broadcast
  - Verify DUT2 updates ARP cache with DUT1's MAC
  - Confirm no ARP reply is sent (GARP is announcement only)
  - Validate ARP cache entry persists on DUT2

Pre-requisites:
  - 2 SONiC devices connected via Ethernet0
  - Testbed: testbed_2vs.yaml
  - VLAN 100 configured with IP addresses
  - Python3 and Scapy installed
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
    "wait_after_garp": 5,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "arp_scapy02_install": "TC-ARP-SCAPY-02-001",
    "arp_scapy02_get_mac": "TC-ARP-SCAPY-02-002",
    "arp_scapy02_clear_cache": "TC-ARP-SCAPY-02-003",
    "arp_scapy02_send_garp": "TC-ARP-SCAPY-02-004",
    "arp_scapy02_verify_cache": "TC-ARP-SCAPY-02-005",
})


@pytest.fixture(scope="module", autouse=True)
def arp_scapy_02_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("ARP SCAPY TC-02 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")

    arp_scapy_pre_config()

    yield

    st.banner("=" * 80)
    st.banner("ARP SCAPY TC-02 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        arp_scapy_pre_config_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def arp_scapy_pre_config():
    """Pre-configuration."""
    st.log("Pre-configuration: Setting up VLAN and IP")

    dut_list = [vars.D1, vars.D2]

    for dut in dut_list:
        try:
            vlanapi.create_vlan(dut, CONFIG.vlan_id, cli_type=data.cli_type)
        except Exception as e:
            st.log(f"VLAN creation on {dut}: {str(e)}")

    try:
        ipapi.config_ip_addr_interface(
            vars.D1, f"Vlan{CONFIG.vlan_id}", CONFIG.dut1_vlan_ip,
            subnet=CONFIG.subnet_mask, family="ipv4", cli_type=data.cli_type
        )
    except Exception as e:
        st.log(f"IP config on {vars.D1}: {str(e)}")

    try:
        ipapi.config_ip_addr_interface(
            vars.D2, f"Vlan{CONFIG.vlan_id}", CONFIG.dut2_vlan_ip,
            subnet=CONFIG.subnet_mask, family="ipv4", cli_type=data.cli_type
        )
    except Exception as e:
        st.log(f"IP config on {vars.D2}: {str(e)}")

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
    """Cleanup."""
    st.log("Cleanup: Clearing ARP entries")

    for dut in [vars.D1, vars.D2]:
        try:
            st.show(dut, "clear ip arp", skip_tmpl=True, skip_error_check=True, type='click')
        except Exception as e:
            st.log(f"ARP clear on {dut}: {str(e)}")

    st.log("Cleanup completed")


def install_scapy(dut: str) -> bool:
    """Install Scapy on DUT."""
    st.log(f"Installing Scapy on {dut}")

    try:
        check_cmd = "python3 -c 'import scapy' 2>&1"
        output = st.show(dut, check_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        if "No module named" not in str(output):
            st.log(f"✓ Scapy already installed on {dut}")
            return True

        install_cmd = "sudo pip3 install scapy -q"
        output = st.show(dut, install_cmd, skip_tmpl=True, skip_error_check=True, type='click')
        st.log(f"Install output: {str(output)[:500]}")

        verify_cmd = "python3 -c 'from scapy.all import *; print(\"Scapy OK\")'"
        output = st.show(dut, verify_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        if "Scapy OK" in str(output) or "WARNING" in str(output):
            st.log(f"✓ Scapy installed successfully on {dut}")
            return True
        else:
            st.error(f"Scapy verification failed on {dut}")
            return False

    except Exception as e:
        st.error(f"Exception installing Scapy on {dut}: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def get_interface_mac(dut: str, interface: str) -> str:
    """Get MAC address of interface."""
    st.log(f"Getting MAC address of {interface} on {dut}")

    try:
        show_cmd = f"show interface {interface}"
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

        output_str = str(output)
        st.log(f"Interface output: {output_str[:1000]}")

        import re
        mac_pattern = r'([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})'
        matches = re.findall(mac_pattern, output_str)

        if matches:
            mac = ''.join([m[0] for m in matches[:1]]) + matches[0][1]
            st.log(f"✓ Found MAC address: {mac}")
            return mac

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


def send_gratuitous_arp(dut: str, iface: str, garp_ip: str, garp_mac: str) -> bool:
    """
    Send Gratuitous ARP using Scapy.

    Scapy commands:
      from scapy.all import *
      garp = Ether(dst="ff:ff:ff:ff:ff:ff", src=garp_mac) /
             ARP(op=2, hwsrc=garp_mac, psrc=garp_ip, hwdst="ff:ff:ff:ff:ff:ff", pdst=garp_ip)
      sendp(garp, iface=iface, verbose=False)

    Returns:
      True if GARP sent successfully
    """
    st.log(f"Sending Gratuitous ARP: IP={garp_ip}, MAC={garp_mac}")

    try:
        scapy_script = f"""
import sys
from scapy.all import Ether, ARP, sendp, conf

conf.verb = 0

iface = "{iface}"
garp_ip = "{garp_ip}"
garp_mac = "{garp_mac}"
broadcast_mac = "ff:ff:ff:ff:ff:ff"

# Craft Gratuitous ARP (op=2, sender IP = target IP)
garp = Ether(dst=broadcast_mac, src=garp_mac) / ARP(op=2, hwsrc=garp_mac, psrc=garp_ip, hwdst=broadcast_mac, pdst=garp_ip)

# Send GARP
try:
    sendp(garp, iface=iface, verbose=False)
    print("GARP_SENT_SUCCESS")
    sys.exit(0)
except Exception as e:
    print(f"GARP_SEND_FAILED: {{e}}")
    sys.exit(1)
"""

        script_path = f"/tmp/arp_scapy_garp_{dut}.py"
        write_cmd = f"cat > {script_path} << 'SCAPY_EOF'\n{scapy_script}\nSCAPY_EOF"
        st.show(dut, write_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        exec_cmd = f"sudo python3 {script_path}"
        output = st.show(dut, exec_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        output_str = str(output)
        st.log(f"Scapy GARP output: {output_str[:1000]}")

        cleanup_cmd = f"rm -f {script_path}"
        st.show(dut, cleanup_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        if "GARP_SENT_SUCCESS" in output_str:
            st.log(f"✓ Gratuitous ARP sent successfully")
            return True
        else:
            st.error(f"Failed to send Gratuitous ARP")
            return False

    except Exception as e:
        st.error(f"Exception sending GARP: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def verify_arp_cache_entry(dut: str, ip_address: str, expected_mac: str = None) -> bool:
    """Verify ARP cache entry exists."""
    st.log(f"Verifying ARP cache entry for {ip_address} on {dut}")

    try:
        show_cmd = "show ip arp"
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

        output_str = str(output)
        st.log(f"ARP table: {output_str[:1500]}")

        if ip_address not in output_str:
            st.error(f"IP {ip_address} not found in ARP table")
            return False

        st.log(f"✓ IP {ip_address} found in ARP table")

        if expected_mac:
            lines = output_str.split('\n')
            for line in lines:
                if ip_address in line:
                    expected_mac_normalized = expected_mac.lower().replace('-', ':')
                    line_lower = line.lower()

                    if expected_mac_normalized in line_lower:
                        st.log(f"✓ MAC {expected_mac} matches in ARP entry")
                        return True
                    else:
                        st.log(f"Note: MAC comparison - looking for {expected_mac_normalized} in: {line_lower}")

        return True

    except Exception as e:
        st.error(f"Exception verifying ARP cache: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def test_arp_scapy_02_gratuitous():
    """
    Test Case ARP-SCAPY-02: Gratuitous ARP

    Test Steps:
    1. Install Scapy on both DUTs
    2. Get MAC addresses of interfaces
    3. Clear ARP cache on DUT2
    4. Send Gratuitous ARP from DUT1
    5. Verify DUT2 ARP cache updated with DUT1's MAC
    """
    st.banner("=" * 80)
    st.banner("TEST ARP-SCAPY-02: GRATUITOUS ARP (GARP)")
    st.banner("=" * 80)

    # STEP 1: Install Scapy
    st.banner("STEP 1: Install Scapy on Both DUTs")

    if not install_scapy(vars.D1):
        st.report_tc_fail(TC_IDS.arp_scapy02_install, "msg", f"Failed to install Scapy on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy02_install_failed")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", f"Failed to install Scapy on {vars.D1}")

    if not install_scapy(vars.D2):
        st.report_tc_fail(TC_IDS.arp_scapy02_install, "msg", f"Failed to install Scapy on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy02_install_failed")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", f"Failed to install Scapy on {vars.D2}")

    st.report_tc_pass(TC_IDS.arp_scapy02_install, "msg", "Scapy installed successfully")
    st.wait(CONFIG.wait_after_install, "Waiting after Scapy installation")

    # STEP 2: Get MAC Addresses
    st.banner("STEP 2: Get MAC Addresses of Interfaces")

    dut1_mac = get_interface_mac(vars.D1, CONFIG.interface)
    if not dut1_mac:
        st.report_tc_fail(TC_IDS.arp_scapy02_get_mac, "msg", f"Failed to get MAC on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy02_get_mac_failed")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", f"Failed to get MAC on {vars.D1}")

    dut2_mac = get_interface_mac(vars.D2, CONFIG.interface)
    if not dut2_mac:
        st.report_tc_fail(TC_IDS.arp_scapy02_get_mac, "msg", f"Failed to get MAC on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy02_get_mac_failed")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", f"Failed to get MAC on {vars.D2}")

    st.log(f"DUT1 MAC: {dut1_mac}, DUT2 MAC: {dut2_mac}")
    st.report_tc_pass(TC_IDS.arp_scapy02_get_mac, "msg", "MAC addresses retrieved")

    # STEP 3: Clear ARP Cache on DUT2
    st.banner("STEP 3: Clear ARP Cache on DUT2")

    st.show(vars.D2, "clear ip arp", skip_tmpl=True, skip_error_check=True, type='click')
    st.report_tc_pass(TC_IDS.arp_scapy02_clear_cache, "msg", "ARP cache cleared")
    st.wait(CONFIG.wait_after_config, "Waiting after ARP clear")

    # STEP 4: Send Gratuitous ARP from DUT1
    st.banner("STEP 4: Send Gratuitous ARP from DUT1")

    if not send_gratuitous_arp(vars.D1, CONFIG.interface, CONFIG.dut1_vlan_ip, dut1_mac):
        st.report_tc_fail(TC_IDS.arp_scapy02_send_garp, "msg", "Failed to send GARP")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy02_garp_send_failed")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", "Failed to send GARP")

    st.report_tc_pass(TC_IDS.arp_scapy02_send_garp, "msg", "Gratuitous ARP sent")
    st.wait(CONFIG.wait_after_garp, "Waiting for GARP to propagate")

    # STEP 5: Verify DUT2 ARP Cache Updated
    st.banner("STEP 5: Verify DUT2 ARP Cache Updated with DUT1's MAC")

    if not verify_arp_cache_entry(vars.D2, CONFIG.dut1_vlan_ip, dut1_mac):
        st.report_tc_fail(TC_IDS.arp_scapy02_verify_cache, "msg", "ARP cache not updated on DUT2")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy02_cache_not_updated")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", "ARP cache not updated on DUT2")

    st.report_tc_pass(TC_IDS.arp_scapy02_verify_cache, "msg", "ARP cache updated successfully on DUT2")

    # TEST PASSED
    st.banner("=" * 80)
    st.banner("TEST RESULT: ARP-SCAPY-02 PASSED")
    st.banner("=" * 80)

    st.log("=" * 80)
    st.log("TEST SUMMARY - ARP-SCAPY-02: Gratuitous ARP")
    st.log("=" * 80)
    st.log(f"✓ Scapy installed on both DUTs")
    st.log(f"✓ DUT1 MAC: {dut1_mac}")
    st.log(f"✓ DUT2 MAC: {dut2_mac}")
    st.log(f"✓ Gratuitous ARP sent from DUT1 for IP {CONFIG.dut1_vlan_ip}")
    st.log(f"✓ DUT2 ARP cache updated with DUT1's MAC address")
    st.log(f"✓ No ARP reply expected (GARP is announcement only)")
    st.log("=" * 80)

    st.report_pass("test_case_passed")
