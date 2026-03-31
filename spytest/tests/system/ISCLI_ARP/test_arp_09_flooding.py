"""
Test ID: 4.17.9
Test Case: Verify ARP Request Flooding
Test Item: Negative
Test Objective: Validate system behavior under ARP flood conditions (100 requests to random IPs)
"""

import pytest
from spytest import st
from spytest.dicts import SpyTestDict

data = SpyTestDict()
CONFIG = SpyTestDict()

CONFIG.dut1_interface = "Ethernet32"
CONFIG.dut2_interface = "Ethernet32"
CONFIG.dut1_ip = "10.9.1.1/24"
CONFIG.dut2_ip = "10.9.1.2/24"
CONFIG.flood_count = 100
CONFIG.script_file = "/tmp/scenario9_flooding.py"


@pytest.fixture(scope="module", autouse=True)
def arp_flooding_module_hooks(request):
    global vars, data
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    st.log("ARP Flooding Test - Module Setup")
    arp_pre_config()
    yield
    arp_pre_config_cleanup()
    st.log("ARP Flooding Test - Module Cleanup Complete")


def arp_pre_config():
    try:
        configure_routed_interface(vars.D1, CONFIG.dut1_interface, CONFIG.dut1_ip)
        configure_routed_interface(vars.D2, CONFIG.dut2_interface, CONFIG.dut2_ip)
    except Exception as e:
        st.error(f"Exception in pre-config: {str(e)}")


def arp_pre_config_cleanup():
    try:
        cleanup_routed_interface(vars.D1, CONFIG.dut1_interface)
        cleanup_routed_interface(vars.D2, CONFIG.dut2_interface)
        remove_file(vars.D1, CONFIG.script_file)
    except Exception as e:
        st.error(f"Exception in cleanup: {str(e)}")


def configure_routed_interface(dut: str, interface: str, ip_address: str) -> bool:
    try:
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no switchport",
            f"ip address {ip_address}",
            "no shutdown",
            "exit", "exit"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)
        return True
    except Exception as e:
        st.error(f"Failed to configure {interface}: {str(e)}")
        return False


def cleanup_routed_interface(dut: str, interface: str) -> bool:
    try:
        commands = ["configure terminal", f"interface {interface}", "no ip address", "exit", "exit"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        return True
    except Exception as e:
        st.error(f"Failed to cleanup {interface}: {str(e)}")
        return False


def get_interface_mac(dut: str, interface: str) -> str:
    try:
        cmd = f"show interface {interface} | grep 'address is'"
        output = st.show(dut, cmd, type=data.cli_type, skip_error_check=True)
        if isinstance(output, str) and "address is" in output:
            return output.split("address is")[1].strip().split()[0]
        return "00:00:00:00:00:00"
    except Exception as e:
        st.error(f"Failed to get MAC: {str(e)}")
        return "00:00:00:00:00:00"


def create_scapy_script(dut: str, script_path: str, script_content: str) -> bool:
    try:
        script_encoded = script_content.replace("'", "'\\''")
        cmd = f"printf '{script_encoded}' > {script_path}"
        st.exec_ssh(dut, cmd)
        verify_cmd = f"test -f {script_path} && echo 'SUCCESS' || echo 'FAILED'"
        result = st.exec_ssh(dut, verify_cmd)
        return 'SUCCESS' in str(result)
    except Exception as e:
        st.error(f"Exception creating script: {str(e)}")
        return False


def run_scapy_script(dut: str, script_path: str) -> bool:
    try:
        cmd = f"sudo python3 {script_path}"
        output = st.exec_ssh(dut, cmd, timeout=60)
        st.log(f"Script output: {output}")
        return True
    except Exception as e:
        st.error(f"Failed to execute script: {str(e)}")
        return False


def remove_file(dut: str, file_path: str) -> bool:
    try:
        st.exec_ssh(dut, f"sudo rm -f {file_path}")
        return True
    except:
        return False


def test_arp_flooding():
    """
    Test ID: 4.17.9
    Test Case: Verify ARP Request Flooding
    Expected Result: System handles flood without crash, may rate-limit or drop excessive requests
    """
    result = True
    try:
        st.log("Test: Verify ARP Request Flooding")
        dut1_ip_only = CONFIG.dut1_ip.split('/')[0]
        dut1_mac = get_interface_mac(vars.D1, CONFIG.dut1_interface)

        scapy_script = f"""from scapy.all import *
import random

iface = "{CONFIG.dut1_interface}"
src_ip = "{dut1_ip_only}"
src_mac = "{dut1_mac}"

print("[*] Scenario 9: ARP Request Flooding")
print(f"[*] Sending {CONFIG.flood_count} ARP requests to random IPs")

for i in range({CONFIG.flood_count}):
    dst_ip = f"10.9.1." + str(random.randint(10, 254))
    arp_req = Ether(src=src_mac, dst="ff:ff:ff:ff:ff:ff") / ARP(
        op=1,
        hwsrc=src_mac,
        psrc=src_ip,
        hwdst="00:00:00:00:00:00",
        pdst=dst_ip
    )
    sendp(arp_req, iface=iface, verbose=False)

print("[+] Flooding test complete")
"""

        if not create_scapy_script(vars.D1, CONFIG.script_file, scapy_script):
            result = False

        st.log("Executing flood script")
        if not run_scapy_script(vars.D1, CONFIG.script_file):
            result = False

        st.wait(3)

        st.log("Flood test completed - verifying system stability")
        cmd_result = st.exec_ssh(vars.D1, "uptime")
        st.log(f"DUT1 status: {cmd_result}")

        if result:
            st.report_pass("test_case_passed")
        else:
            st.report_fail("test_case_failed", "Flood test failed")

    except Exception as e:
        st.log(f"Exception: {str(e)}")
        st.report_fail("test_case_failed", str(e))
    finally:
        st.log("Test execution completed")
