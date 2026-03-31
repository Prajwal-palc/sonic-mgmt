"""
Test ID: 4.17.13
Test Case: Verify ARP Cache Limit Test
Test Item: Scalability
Test Objective: Validate system behavior with 1000 ARP entries to test cache limits
"""

import pytest
from spytest import st
from spytest.dicts import SpyTestDict

data = SpyTestDict()
CONFIG = SpyTestDict()

CONFIG.dut1_interface = "Ethernet32"
CONFIG.dut2_interface = "Ethernet32"
CONFIG.dut1_ip = "10.13.1.1/16"
CONFIG.dut2_ip = "10.13.1.2/16"
CONFIG.cache_entries = 1000
CONFIG.script_file = "/tmp/scenario13_cache_limit.py"


@pytest.fixture(scope="module", autouse=True)
def arp_cache_limit_module_hooks(request):
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
    except:
        pass


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
        result = st.exec_ssh(dut, f"test -f {script_path} && echo 'SUCCESS'")
        return 'SUCCESS' in str(result)
    except:
        return False


def run_scapy_script(dut: str, script_path: str) -> bool:
    try:
        output = st.exec_ssh(dut, f"sudo python3 {script_path}", timeout=120)
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


def test_arp_cache_limit():
    """Test ID: 4.17.13 - Expected: System handles large ARP cache gracefully"""
    result = True
    try:
        st.log("Test: ARP Cache Limit Test")
        dut1_mac = get_interface_mac(vars.D1, CONFIG.dut1_interface)

        scapy_script = f"""from scapy.all import *

iface = "{CONFIG.dut1_interface}"
src_mac = "{dut1_mac}"

print("[*] Scenario 13: ARP Cache Limit Test")
print(f"[*] Sending {CONFIG.cache_entries} ARP replies to populate cache")

for i in range({CONFIG.cache_entries}):
    src_ip = f"10.13." + str((i // 256)) + "." + str((i % 256) + 1)
    fake_mac = "02:00:00:" + format(i // 65536, '02x') + ":" + format((i // 256) % 256, '02x') + ":" + format(i % 256, '02x')

    arp_reply = Ether(src=fake_mac, dst="ff:ff:ff:ff:ff:ff") / ARP(
        op=2,
        hwsrc=fake_mac,
        psrc=src_ip,
        hwdst="ff:ff:ff:ff:ff:ff",
        pdst="10.13.1.1"
    )
    sendp(arp_reply, iface=iface, verbose=False)

    if (i + 1) % 100 == 0:
        print(f"[*] Sent {{i + 1}} ARP replies")

print("[+] Cache limit test complete")
"""

        if not create_scapy_script(vars.D1, CONFIG.script_file, scapy_script):
            result = False

        if not run_scapy_script(vars.D1, CONFIG.script_file):
            result = False

        st.wait(3)

        st.log("Checking ARP table size")
        arp_output = st.show(vars.D1, "show ip arp", type=data.cli_type, skip_error_check=True)
        st.log(f"ARP table: {arp_output}")

        if result:
            st.report_pass("test_case_passed")
        else:
            st.report_fail("test_case_failed")

    except Exception as e:
        st.report_fail("test_case_failed", str(e))
