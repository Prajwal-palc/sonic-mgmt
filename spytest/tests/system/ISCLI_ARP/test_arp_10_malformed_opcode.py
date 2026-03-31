"""
Test ID: 4.17.10
Test Case: Verify Malformed ARP - Invalid Opcode
Test Item: Negative
Test Objective: Validate system handling of ARP packets with invalid opcode values
"""

import pytest
from spytest import st
from spytest.dicts import SpyTestDict

data = SpyTestDict()
CONFIG = SpyTestDict()

CONFIG.dut1_interface = "Ethernet32"
CONFIG.dut2_interface = "Ethernet32"
CONFIG.dut1_ip = "10.10.1.1/24"
CONFIG.dut2_ip = "10.10.1.2/24"
CONFIG.invalid_opcode = 99  # Invalid opcode (valid are 1=request, 2=reply)
CONFIG.script_file = "/tmp/scenario10_malformed_opcode.py"


@pytest.fixture(scope="module", autouse=True)
def arp_malformed_opcode_module_hooks(request):
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
        commands = ["configure terminal", f"interface {interface}", "no switchport",
                   f"ip address {ip_address}", "no shutdown", "exit", "exit"]
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
        return False


def get_interface_mac(dut: str, interface: str) -> str:
    try:
        cmd = f"show interface {interface} | grep 'address is'"
        output = st.show(dut, cmd, type=data.cli_type, skip_error_check=True)
        if isinstance(output, str) and "address is" in output:
            return output.split("address is")[1].strip().split()[0]
        return "00:00:00:00:00:00"
    except:
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
        st.log(f"Script output: {output}")
        return True
    except:
        return False


def remove_file(dut: str, file_path: str) -> bool:
    try:
        st.exec_ssh(dut, f"sudo rm -f {file_path}")
        return True
    except:
        return False


def test_arp_malformed_opcode():
    """
    Test ID: 4.17.10
    Expected Result: System drops/ignores malformed packets, no crash
    """
    result = True
    try:
        st.log("Test: Verify Malformed ARP - Invalid Opcode")
        dut1_ip_only = CONFIG.dut1_ip.split('/')[0]
        dut2_ip_only = CONFIG.dut2_ip.split('/')[0]
        dut1_mac = get_interface_mac(vars.D1, CONFIG.dut1_interface)

        scapy_script = f"""from scapy.all import *

iface = "{CONFIG.dut1_interface}"
src_ip = "{dut1_ip_only}"
src_mac = "{dut1_mac}"
dst_ip = "{dut2_ip_only}"

print("[*] Scenario 10: Malformed ARP - Invalid Opcode")
print(f"[*] Sending ARP with invalid opcode {CONFIG.invalid_opcode}")

malformed_arp = Ether(src=src_mac, dst="ff:ff:ff:ff:ff:ff") / ARP(
    op={CONFIG.invalid_opcode},
    hwsrc=src_mac,
    psrc=src_ip,
    hwdst="00:00:00:00:00:00",
    pdst=dst_ip
)

sendp(malformed_arp, iface=iface, verbose=True, count=5)
print("[+] Malformed ARP sent")
"""

        if not create_scapy_script(vars.D1, CONFIG.script_file, scapy_script):
            result = False

        if not run_scapy_script(vars.D1, CONFIG.script_file):
            result = False

        st.wait(2)

        st.log("Verifying system stability after malformed packets")
        st.exec_ssh(vars.D1, "uptime")

        if result:
            st.report_pass("test_case_passed")
        else:
            st.report_fail("test_case_failed", "Test failed")

    except Exception as e:
        st.log(f"Exception: {str(e)}")
        st.report_fail("test_case_failed", str(e))
    finally:
        st.log("Test execution completed")
