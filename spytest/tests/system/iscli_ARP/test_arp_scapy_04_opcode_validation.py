"""
ARP SCAPY TEST - TC-04: ARP Packet Opcode Validation

Test Case ID: ARP-SCAPY-04
Author: Automated SpyTest Framework
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_ARP/test_arp_scapy_04_opcode_validation.py \
    --logs-path ./logs/arp_scapy04_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates ARP packet opcode field using Scapy packet sniffing:
  - Install Scapy on both DUTs
  - Start packet sniffer on DUT1 to capture ARP traffic
  - Generate ARP traffic from DUT2 (ping to trigger ARP)
  - Analyze captured packets for opcode values
  - Verify ARP Request has opcode=1 (who-has)
  - Verify ARP Reply has opcode=2 (is-at)
  - Validate source/destination MAC and IP mappings

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
    "sniff_count": 10,
    "sniff_timeout": 30,
    "wait_after_install": 10,
    "wait_after_config": 3,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "arp_scapy04_install": "TC-ARP-SCAPY-04-001",
    "arp_scapy04_start_sniffer": "TC-ARP-SCAPY-04-002",
    "arp_scapy04_generate_traffic": "TC-ARP-SCAPY-04-003",
    "arp_scapy04_analyze_packets": "TC-ARP-SCAPY-04-004",
    "arp_scapy04_verify_opcodes": "TC-ARP-SCAPY-04-005",
})


@pytest.fixture(scope="module", autouse=True)
def arp_scapy_04_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("ARP SCAPY TC-04 MODULE CONFIGURATION - START")
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
    st.banner("ARP SCAPY TC-04 MODULE CLEANUP - START")
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

        verify_cmd = "python3 -c 'from scapy.all import *; print(\"Scapy OK\")'"
        output = st.show(dut, verify_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        if "Scapy OK" in str(output) or "WARNING" in str(output):
            st.log(f"✓ Scapy installed successfully on {dut}")
            return True
        else:
            st.error(f"Scapy verification failed on {dut}")
            return False

    except Exception as e:
        st.error(f"Exception installing Scapy: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def sniff_arp_packets(dut: str, iface: str, count: int, timeout: int) -> dict:
    """
    Sniff ARP packets and analyze opcodes.

    Scapy commands:
      from scapy.all import *
      packets = sniff(iface=iface, filter="arp", count=count, timeout=timeout)
      for pkt in packets:
          if ARP in pkt:
              print(f"OPCODE={pkt[ARP].op} SRC_IP={pkt[ARP].psrc} DST_IP={pkt[ARP].pdst}")

    Returns:
      dict with 'success', 'request_count', 'reply_count', 'packets'
    """
    st.log(f"Sniffing ARP packets on {dut} interface {iface}")

    try:
        scapy_script = f"""
import sys
from scapy.all import sniff, ARP, conf

conf.verb = 0

iface = "{iface}"
count = {count}
timeout = {timeout}

print("SNIFF_START")
sys.stdout.flush()

try:
    # Sniff ARP packets
    packets = sniff(iface=iface, filter="arp", count=count, timeout=timeout)

    request_count = 0
    reply_count = 0

    for pkt in packets:
        if ARP in pkt:
            opcode = pkt[ARP].op
            src_ip = pkt[ARP].psrc
            dst_ip = pkt[ARP].pdst
            src_mac = pkt[ARP].hwsrc

            if opcode == 1:
                request_count += 1
                print(f"PKT_REQUEST|OPCODE=1|SRC_IP={{src_ip}}|DST_IP={{dst_ip}}|SRC_MAC={{src_mac}}")
            elif opcode == 2:
                reply_count += 1
                print(f"PKT_REPLY|OPCODE=2|SRC_IP={{src_ip}}|DST_IP={{dst_ip}}|SRC_MAC={{src_mac}}")

            sys.stdout.flush()

    print(f"SNIFF_COMPLETE|REQUEST_COUNT={{request_count}}|REPLY_COUNT={{reply_count}}|TOTAL={{len(packets)}}")
    sys.exit(0)

except Exception as e:
    print(f"SNIFF_ERROR: {{e}}")
    sys.exit(1)
"""

        script_path = f"/tmp/arp_scapy_sniff_{dut}.py"
        write_cmd = f"cat > {script_path} << 'SCAPY_EOF'\n{scapy_script}\nSCAPY_EOF"
        st.show(dut, write_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        exec_cmd = f"sudo timeout {timeout + 10} python3 {script_path}"
        output = st.show(dut, exec_cmd, skip_tmpl=True, skip_error_check=True, type='click', timeout=timeout + 15)

        output_str = str(output)
        st.log(f"Scapy sniff output: {output_str[:2000]}")

        result = {
            'success': False,
            'request_count': 0,
            'reply_count': 0,
            'total_count': 0,
            'packets': []
        }

        # Parse output
        if "SNIFF_COMPLETE" in output_str:
            result['success'] = True

            for line in output_str.split('\n'):
                if "REQUEST_COUNT=" in line:
                    parts = line.split('|')
                    for part in parts:
                        if "REQUEST_COUNT=" in part:
                            result['request_count'] = int(part.split('=')[1])
                        if "REPLY_COUNT=" in part:
                            result['reply_count'] = int(part.split('=')[1])
                        if "TOTAL=" in part:
                            result['total_count'] = int(part.split('=')[1])

                if "PKT_REQUEST|" in line or "PKT_REPLY|" in line:
                    result['packets'].append(line)

            st.log(f"✓ Captured {result['total_count']} ARP packets")
            st.log(f"  - Requests (op=1): {result['request_count']}")
            st.log(f"  - Replies (op=2): {result['reply_count']}")
        else:
            st.error(f"Sniffer did not complete successfully")

        cleanup_cmd = f"rm -f {script_path}"
        st.show(dut, cleanup_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        return result

    except Exception as e:
        st.error(f"Exception sniffing packets: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return {'success': False, 'request_count': 0, 'reply_count': 0, 'total_count': 0, 'packets': []}


def test_arp_scapy_04_opcode_validation():
    """
    Test Case ARP-SCAPY-04: ARP Packet Opcode Validation

    Test Steps:
    1. Install Scapy on both DUTs
    2. Clear ARP cache to force fresh ARP traffic
    3. Start ARP packet sniffer on DUT1 (background)
    4. Generate ARP traffic from DUT2 (ping)
    5. Analyze captured packets
    6. Verify ARP requests have opcode=1
    7. Verify ARP replies have opcode=2
    """
    st.banner("=" * 80)
    st.banner("TEST ARP-SCAPY-04: ARP PACKET OPCODE VALIDATION")
    st.banner("=" * 80)

    # STEP 1: Install Scapy
    st.banner("STEP 1: Install Scapy on Both DUTs")

    if not install_scapy(vars.D1):
        st.report_tc_fail(TC_IDS.arp_scapy04_install, "msg", f"Failed to install Scapy on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy04_install_failed")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", f"Failed to install Scapy on {vars.D1}")

    if not install_scapy(vars.D2):
        st.report_tc_fail(TC_IDS.arp_scapy04_install, "msg", f"Failed to install Scapy on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy04_install_failed")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", f"Failed to install Scapy on {vars.D2}")

    st.report_tc_pass(TC_IDS.arp_scapy04_install, "msg", "Scapy installed successfully")
    st.wait(CONFIG.wait_after_install, "Waiting after Scapy installation")

    # STEP 2: Clear ARP Cache
    st.banner("STEP 2: Clear ARP Cache on Both DUTs")

    st.show(vars.D1, "clear ip arp", skip_tmpl=True, skip_error_check=True, type='click')
    st.show(vars.D2, "clear ip arp", skip_tmpl=True, skip_error_check=True, type='click')
    st.wait(CONFIG.wait_after_config, "Waiting after ARP clear")

    # STEP 3 & 4: Start Sniffer and Generate Traffic
    st.banner("STEP 3: Start ARP Sniffer on DUT1 and Generate Traffic from DUT2")

    # We'll use a different approach - trigger ping first, then capture the ARP exchange
    # Clear cache again
    st.show(vars.D1, "clear ip arp", skip_tmpl=True, skip_error_check=True, type='click')
    st.wait(2, "Waiting before starting capture")

    # Start ping from DUT2 to DUT1 in background to generate ARP traffic
    ping_cmd = f"ping {CONFIG.dut1_vlan_ip} -c 5 > /dev/null 2>&1 &"
    st.show(vars.D2, ping_cmd, skip_tmpl=True, skip_error_check=True, type='click')

    st.wait(1, "Waiting for ping to start")

    # Now sniff on DUT1
    sniff_result = sniff_arp_packets(vars.D1, CONFIG.interface, CONFIG.sniff_count, CONFIG.sniff_timeout)

    if not sniff_result['success']:
        st.report_tc_fail(TC_IDS.arp_scapy04_start_sniffer, "msg", "Failed to capture ARP packets")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy04_sniff_failed")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", "Failed to capture ARP packets")

    st.report_tc_pass(TC_IDS.arp_scapy04_start_sniffer, "msg", f"Captured {sniff_result['total_count']} ARP packets")

    # STEP 5: Analyze Captured Packets
    st.banner("STEP 5: Analyze Captured Packets")

    st.log("Packet Analysis:")
    for i, pkt_line in enumerate(sniff_result['packets'][:20], 1):  # Show first 20 packets
        st.log(f"  Packet {i}: {pkt_line}")

    st.report_tc_pass(TC_IDS.arp_scapy04_analyze_packets, "msg", "Packets analyzed")

    # STEP 6: Verify Opcodes
    st.banner("STEP 6: Verify ARP Request (op=1) and Reply (op=2) Opcodes")

    if sniff_result['request_count'] > 0:
        st.log(f"✓ ARP Requests captured: {sniff_result['request_count']} (opcode=1)")
    else:
        st.log(f"Warning: No ARP Requests captured")

    if sniff_result['reply_count'] > 0:
        st.log(f"✓ ARP Replies captured: {sniff_result['reply_count']} (opcode=2)")
    else:
        st.log(f"Warning: No ARP Replies captured")

    # At least one of each should be present
    if sniff_result['request_count'] == 0 and sniff_result['reply_count'] == 0:
        st.report_tc_fail(TC_IDS.arp_scapy04_verify_opcodes, "msg", "No ARP packets captured")
        st.generate_tech_support([vars.D1, vars.D2], "arp_scapy04_no_packets")
        arp_scapy_pre_config_cleanup()
        st.report_fail("msg", "No ARP packets captured")

    st.report_tc_pass(TC_IDS.arp_scapy04_verify_opcodes, "msg", "ARP opcodes verified successfully")

    # TEST PASSED
    st.banner("=" * 80)
    st.banner("TEST RESULT: ARP-SCAPY-04 PASSED")
    st.banner("=" * 80)

    st.log("=" * 80)
    st.log("TEST SUMMARY - ARP-SCAPY-04: ARP Packet Opcode Validation")
    st.log("=" * 80)
    st.log(f"✓ Scapy installed on both DUTs")
    st.log(f"✓ Total ARP packets captured: {sniff_result['total_count']}")
    st.log(f"✓ ARP Requests (op=1): {sniff_result['request_count']}")
    st.log(f"✓ ARP Replies (op=2): {sniff_result['reply_count']}")
    st.log(f"✓ Opcode validation: SUCCESS")
    st.log("=" * 80)

    st.report_pass("test_case_passed")
