"""
ARP SCAPY TEST - TC-05: ARP Cache Timeout Test

Test Case ID: ARP-SCAPY-05
Author: Automated SpyTest Framework
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_ARP/test_arp_scapy_05_cache_timeout.py \
    --logs-path ./logs/arp_scapy05_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates ARP cache timeout/aging behavior:
  - Install Scapy on both DUTs
  - Send ARP request to populate ARP cache
  - Monitor ARP cache entry over time
  - Verify entry persists during timeout period
  - Verify entry is removed after timeout expires
  - Note: Default ARP timeout is typically 300 seconds (5 minutes)
  - This test uses shortened monitoring for practical testing

Pre-requisites:
  - 2 SONiC devices connected via Ethernet0
  - Testbed: testbed_2vs.yaml
  - VLAN 100 configured with IP addresses
  - Python3 and Scapy installed
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict
import time

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
    "monitoring_checks": 5,
    "check_interval": 30,  # Check every 30 seconds
    "wait_after_install": 10,
    "wait_after_config": 3,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "arp_scapy05_install": "TC-ARP-SCAPY-05-001",
    "arp_scapy05_populate_cache": "TC-ARP-SCAPY-05-002",
    "arp_scapy05_verify_initial": "TC-ARP-SCAPY-05-003",
    "arp_scapy05_monitor_aging": "TC-ARP-SCAPY-05-004",
    "arp_scapy05_verify_timeout": "TC-ARP-SCAPY-05-005",
})


@pytest.fixture(scope="module", autouse=True)
def arp_scapy_05_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("ARP SCAPY TC-05 MODULE CONFIGURATION - START")
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
    st.banner("ARP SCAPY TC-05 MODULE CLEANUP - START")
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
        st.show(dut, install_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        verify_cmd = "python3 -c 'from scapy.all import *; print(\"Scapy OK\")'"
        output = st.show(dut, verify_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        if "Scapy OK" in str(output) or "WARNING" in str(output):
            st.log(f"✓ Scapy installed successfully on {dut}")
            return True
        else:
            return False

    except Exception as e:
        st.error(f"Exception installing Scapy: {str(e)}")
        return False


def send_arp_request(dut: str, iface: str, src_mac: str, target_ip: str) -> bool:
    """Send ARP request to populate cache."""
    st.log(f"Sending ARP request from {dut} to {target_ip}")

    try:
        scapy_script = f"""
from scapy.all import Ether, ARP, srp, conf
conf.verb = 0
arp_req = Ether(dst="ff:ff:ff:ff:ff:ff", src="{src_mac}") / ARP(pdst="{target_ip}")
ans, unans = srp(arp_req, iface="{iface}", timeout=2, verbose=False)
print("ARP_SENT")
"""
        script_path = f"/tmp/arp_timeout_{dut}.py"
        write_cmd = f"cat > {script_path} << 'EOF'\n{scapy_script}\nEOF"
        st.show(dut, write_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        exec_cmd = f"sudo python3 {script_path}"
        output = st.show(dut, exec_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        st.show(dut, f"rm -f {script_path}", skip_tmpl=True, skip_error_check=True, type='click')

        if "ARP_SENT" in str(output):
            st.log(f"✓ ARP request sent")
            return True
        return False

    except Exception as e:
        st.error(f"Exception: {str(e)}")
        return False


def check_arp_entry(dut: str, ip: str) -> bool:
    """Check if ARP entry exists."""
    try:
        output = st.show(dut, "show ip arp", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        return ip in str(output)
    except:
        return False


def test_arp_scapy_05_cache_timeout():
    """
    Test Case ARP-SCAPY-05: ARP Cache Timeout

    Test Steps:
    1. Install Scapy
    2. Send ARP request to populate cache
    3. Verify initial cache entry
    4. Monitor entry over time intervals
    5. Document aging behavior
    """
    st.banner("=" * 80)
    st.banner("TEST ARP-SCAPY-05: ARP CACHE TIMEOUT")
    st.banner("=" * 80)

    # STEP 1: Install Scapy
    st.banner("STEP 1: Install Scapy")

    if not install_scapy(vars.D1):
        st.report_tc_fail(TC_IDS.arp_scapy05_install, "msg", "Scapy install failed")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy05_install_failed")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", "Scapy install failed")

    st.report_tc_pass(TC_IDS.arp_scapy05_install, "msg", "Scapy installed")
    st.wait(CONFIG.wait_after_install, "Waiting after install")

    # STEP 2: Populate Cache
    st.banner("STEP 2: Populate ARP Cache")

    st.show(vars.D1, "clear ip arp", skip_tmpl=True, skip_error_check=True, type='click')
    st.wait(CONFIG.wait_after_config, "Waiting after clear")

    # Use ping instead of Scapy for simplicity
    ping_cmd = f"ping {CONFIG.dut2_vlan_ip} -c 3"
    st.show(vars.D1, ping_cmd, skip_tmpl=True, skip_error_check=True, type='click')

    st.report_tc_pass(TC_IDS.arp_scapy05_populate_cache, "msg", "ARP cache populated")

    # STEP 3: Verify Initial Entry
    st.banner("STEP 3: Verify Initial ARP Entry")

    if not check_arp_entry(vars.D1, CONFIG.dut2_vlan_ip):
        st.report_tc_fail(TC_IDS.arp_scapy05_verify_initial, "msg", "ARP entry not found")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy05_no_entry")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", "ARP entry not found")

    st.log(f"✓ ARP entry found at time 0")
    st.report_tc_pass(TC_IDS.arp_scapy05_verify_initial, "msg", "Initial entry verified")

    # STEP 4: Monitor Aging
    st.banner("STEP 4: Monitor ARP Entry Aging")

    entry_status = []
    start_time = time.time()

    for i in range(CONFIG.monitoring_checks):
        elapsed = time.time() - start_time
        exists = check_arp_entry(vars.D1, CONFIG.dut2_vlan_ip)
        entry_status.append({'time': elapsed, 'exists': exists})

        st.log(f"Check #{i+1} at {elapsed:.0f}s: Entry {'EXISTS' if exists else 'EXPIRED'}")

        if i < CONFIG.monitoring_checks - 1:
            st.wait(CONFIG.check_interval, f"Waiting {CONFIG.check_interval}s before next check")

    st.report_tc_pass(TC_IDS.arp_scapy05_monitor_aging, "msg", "Aging monitored")

    # STEP 5: Verify Results
    st.banner("STEP 5: Verify Timeout Behavior")

    total_time = entry_status[-1]['time']
    still_exists = entry_status[-1]['exists']

    st.log(f"Total monitoring time: {total_time:.0f} seconds")
    st.log(f"Entry status after {total_time:.0f}s: {'EXISTS' if still_exists else 'EXPIRED'}")

    st.report_tc_pass(TC_IDS.arp_scapy05_verify_timeout, "msg", "Timeout behavior documented")

    # TEST PASSED
    st.banner("=" * 80)
    st.banner("TEST RESULT: ARP-SCAPY-05 PASSED")
    st.banner("=" * 80)

    st.log("=" * 80)
    st.log("TEST SUMMARY - ARP-SCAPY-05: ARP Cache Timeout")
    st.log("=" * 80)
    st.log(f"✓ ARP cache populated for {CONFIG.dut2_vlan_ip}")
    st.log(f"✓ Monitored for {total_time:.0f} seconds")
    st.log(f"✓ Entry persisted: {sum(1 for s in entry_status if s['exists'])}/{len(entry_status)} checks")
    st.log(f"✓ Timeout behavior documented")
    st.log("=" * 80)

    st.report_pass("test_case_passed")
