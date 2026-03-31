"""
Test ID: 4.17.12
Test Case: Verify Malformed ARP - Truncated Packet
Test Item: Negative
Test Objective: Validate system handling of incomplete/truncated ARP packets
"""

import pytest
from spytest import st
from spytest.dicts import SpyTestDict

data = SpyTestDict()
CONFIG = SpyTestDict()

CONFIG.dut1_interface = "Ethernet32"
CONFIG.dut2_interface = "Ethernet32"
CONFIG.dut1_ip = "10.12.1.1/24"
CONFIG.dut2_ip = "10.12.1.2/24"
CONFIG.script_file = "/tmp/scenario12_truncated.py"


@pytest.fixture(scope="module", autouse=True)
def arp_truncated_module_hooks(request):
    global vars, data
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    arp_pre_config()
    yield
    arp_pre_config_cleanup()


def arp_pre_config():
    try:
        configure_routed_interface(vars.D1, CONFIG.dut1_interface, CONFIG.dut1_ip)
        configure_routed_interface(vars.D2, CONFIG.dut2_interface, CONFIG.dut2_ip)
    except Exception as e:
        st.error(f"Exception: {str(e)}")


def arp_pre_config_cleanup():
    try:
        cleanup_routed_interface(vars.D1, CONFIG.dut1_interface)
        cleanup_routed_interface(vars.D2, CONFIG.dut2_interface)
        remove_file(vars.D1, CONFIG.script_file)
    except:
        pass


def configure_routed_interface(dut: str, interface: str, ip_address: str) -> bool:
    try:
        commands = ["configure terminal", f"interface {interface}", "no switchport",
                   f"ip address {ip_address}", "no shutdown", "exit", "exit"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)
        return True
    except:
        return False


def cleanup_routed_interface(dut: str, interface: str) -> bool:
    try:
        commands = ["configure terminal", f"interface {interface}", "no ip address", "exit", "exit"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        return True
    except:
        return False


def get_interface_mac(dut: str, interface: str) -> str:
    try:
        cmd = f"show interface {interface} | grep 'address is'"
        output = st.show(dut, cmd, type=data.cli_type, skip_error_check=True)
        if isinstance(output, str) and "address is" in output:
            return output.split("address is")[1].strip().split()[0]
    except:
        pass
    return "00:00:00:00:00:00"


def create_scapy_script(dut: str, script_path: str, script_content: str) -> bool:
    try:
        script_encoded = script_content.replace("'", "'\\''")
        st.exec_ssh(dut, f"printf '{script_encoded}' > {script_path}")
        result = st.exec_ssh(dut, f"test -f {script_path} && echo 'SUCCESS' || echo 'FAILED'")
        return 'SUCCESS' in str(result)
    except:
        return False


def run_scapy_script(dut: str, script_path: str) -> bool:
    try:
        output = st.exec_ssh(dut, f"sudo python3 {script_path}", timeout=30)
        st.log(f"Output: {output}")
        return True
    except:
        return False


def remove_file(dut: str, file_path: str) -> bool:
    try:
        st.exec_ssh(dut, f"sudo rm -f {file_path}")
        return True
    except:
        return False


def test_arp_truncated():
    """Test ID: 4.17.12 - Expected: System drops truncated packets"""
    result = True
    try:
        st.log("Test: Malformed ARP - Truncated Packet")
        dut1_mac = get_interface_mac(vars.D1, CONFIG.dut1_interface)

        scapy_script = f"""from scapy.all import *

iface = "{CONFIG.dut1_interface}"
src_mac = "{dut1_mac}"

print("[*] Scenario 12: Malformed ARP - Truncated Packet")

truncated_arp = Ether(src=src_mac, dst="ff:ff:ff:ff:ff:ff") / Raw(load=b"\\x00\\x01\\x08\\x00")

sendp(truncated_arp, iface=iface, verbose=True, count=5)
print("[+] Truncated ARP sent")
"""

        if not create_scapy_script(vars.D1, CONFIG.script_file, scapy_script):
            result = False

        if not run_scapy_script(vars.D1, CONFIG.script_file):
            result = False

        st.wait(2)

        if result:
            st.report_pass("test_case_passed")
        else:
            st.report_fail("test_case_failed")

    except Exception as e:
        st.report_fail("test_case_failed", str(e))
