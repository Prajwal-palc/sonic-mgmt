"""
Test ID: 4.17.6
Test Case: Verify ARP on VLAN Interface
Test Item: Functional
Test Objective: Validate that ARP works correctly on VLAN-tagged interfaces
"""

import pytest
from spytest import st
from spytest.dicts import SpyTestDict

data = SpyTestDict()
CONFIG = SpyTestDict()

# Test Configuration
CONFIG.dut1_interface = "Ethernet36"
CONFIG.dut2_interface = "Ethernet36"
CONFIG.vlan_id = "100"
CONFIG.dut1_vlan_interface = f"Vlan{CONFIG.vlan_id}"
CONFIG.dut2_vlan_interface = f"Vlan{CONFIG.vlan_id}"
CONFIG.dut1_ip = "10.6.1.1/24"
CONFIG.dut2_ip = "10.6.1.2/24"
CONFIG.script_file = "/tmp/scenario6_vlan_arp.py"
CONFIG.pcap_file = "~/scenario6.pcap"


@pytest.fixture(scope="module", autouse=True)
def arp_vlan_module_hooks(request):
    """
    Module-level fixture for ARP VLAN test setup and cleanup
    """
    global vars, data
    vars = st.ensure_min_topology("D1D2:2")
    data.cli_type = st.get_ui_type()

    st.log("=" * 80)
    st.log("ARP VLAN Test - Module Setup")
    st.log("=" * 80)

    arp_pre_config()
    yield
    arp_pre_config_cleanup()

    st.log("=" * 80)
    st.log("ARP VLAN Test - Module Cleanup Complete")
    st.log("=" * 80)


def arp_pre_config():
    """
    Pre-configuration for ARP VLAN test
    """
    try:
        st.log("Configuring VLAN interfaces for ARP VLAN test...")

        # Create VLAN and add interfaces on both DUTs
        configure_vlan(vars.D1, CONFIG.vlan_id, CONFIG.dut1_interface, CONFIG.dut1_ip)
        configure_vlan(vars.D2, CONFIG.vlan_id, CONFIG.dut2_interface, CONFIG.dut2_ip)

        st.log("Pre-configuration completed")

    except Exception as e:
        st.error(f"Exception in pre-config: {str(e)}")


def arp_pre_config_cleanup():
    """
    Cleanup configuration after test
    """
    try:
        st.log("Cleaning up ARP VLAN test configuration...")

        # Remove VLAN configuration
        cleanup_vlan(vars.D1, CONFIG.vlan_id, CONFIG.dut1_interface)
        cleanup_vlan(vars.D2, CONFIG.vlan_id, CONFIG.dut2_interface)

        # Remove Scapy script
        remove_file(vars.D1, CONFIG.script_file)
        remove_file(vars.D2, CONFIG.pcap_file)

        st.log("Cleanup completed")

    except Exception as e:
        st.error(f"Exception in cleanup: {str(e)}")


def configure_vlan(dut: str, vlan_id: str, interface: str, ip_address: str) -> bool:
    """
    Configure VLAN interface
    """
    try:
        st.log(f"Configuring VLAN {vlan_id} on {dut}")

        commands = [
            "configure terminal",
            f"vlan {vlan_id}",
            "exit",
            f"interface {interface}",
            "switchport mode trunk",
            f"switchport trunk allowed vlan {vlan_id}",
            "exit",
            f"interface Vlan{vlan_id}",
            f"ip address {ip_address}",
            "no shutdown",
            "exit",
            "exit"
        ]

        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure VLAN on {dut}: {str(e)}")
        return False


def cleanup_vlan(dut: str, vlan_id: str, interface: str) -> bool:
    """
    Remove VLAN configuration
    """
    try:
        st.log(f"Cleaning up VLAN {vlan_id} on {dut}")

        commands = [
            "configure terminal",
            f"no interface Vlan{vlan_id}",
            f"interface {interface}",
            "no switchport mode trunk",
            "exit",
            f"no vlan {vlan_id}",
            "exit"
        ]

        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        return True

    except Exception as e:
        st.error(f"Failed to cleanup VLAN on {dut}: {str(e)}")
        return False


def get_interface_mac(dut: str, interface: str) -> str:
    """
    Get MAC address of an interface
    """
    try:
        cmd = f"show interface {interface} | grep 'address is'"
        output = st.show(dut, cmd, type=data.cli_type, skip_error_check=True)

        if isinstance(output, str) and "address is" in output:
            mac = output.split("address is")[1].strip().split()[0]
            st.log(f"{dut} {interface} MAC: {mac}")
            return mac

        cmd_direct = f"show interface {interface}"
        output_direct = st.exec_ssh(dut, cmd_direct)
        if "address is" in str(output_direct):
            mac = str(output_direct).split("address is")[1].strip().split()[0]
            st.log(f"{dut} {interface} MAC (fallback): {mac}")
            return mac

        st.error(f"Could not extract MAC for {dut} {interface}")
        return "00:00:00:00:00:00"

    except Exception as e:
        st.error(f"Failed to get MAC for {interface} on {dut}: {str(e)}")
        return "00:00:00:00:00:00"


def create_scapy_script(dut: str, script_path: str, script_content: str) -> bool:
    """
    Create a Scapy script file on the DUT
    """
    try:
        st.log(f"Creating Scapy script on {dut}: {script_path}")
        script_encoded = script_content.replace("'", "'\\''")
        cmd = f"printf '{script_encoded}' > {script_path}"
        st.exec_ssh(dut, cmd)

        verify_cmd = f"test -f {script_path} && echo 'SUCCESS' || echo 'FAILED'"
        result = st.exec_ssh(dut, verify_cmd)

        if 'SUCCESS' in str(result):
            st.log(f"Scapy script created successfully: {script_path}")
            return True
        else:
            st.error(f"Failed to create Scapy script: {script_path}")
            return False

    except Exception as e:
        st.error(f"Exception creating Scapy script: {str(e)}")
        return False


def run_scapy_script(dut: str, script_path: str) -> bool:
    """
    Execute Scapy script on the DUT
    """
    try:
        st.log(f"Executing Scapy script on {dut}: {script_path}")
        cmd = f"sudo python3 {script_path}"
        output = st.exec_ssh(dut, cmd, timeout=30)
        st.log(f"Scapy script output: {output}")
        return True

    except Exception as e:
        st.error(f"Failed to execute Scapy script: {str(e)}")
        return False


def start_tcpdump(dut: str, interface: str, pcap_file: str) -> bool:
    """
    Start tcpdump packet capture
    """
    try:
        st.log(f"Starting tcpdump on {dut} {interface}")
        st.exec_ssh(dut, f"sudo rm -f {pcap_file}")
        cmd = f"sudo tcpdump -i {interface} arp -nn -e -v -w {pcap_file} &"
        st.exec_ssh(dut, cmd)
        st.wait(2)
        st.log("tcpdump started")
        return True

    except Exception as e:
        st.error(f"Failed to start tcpdump: {str(e)}")
        return False


def stop_tcpdump(dut: str) -> bool:
    """
    Stop tcpdump process
    """
    try:
        st.log(f"Stopping tcpdump on {dut}")
        cmd = "sudo pkill tcpdump"
        st.exec_ssh(dut, cmd)
        st.wait(2)
        st.log("tcpdump stopped")
        return True

    except Exception as e:
        st.error(f"Failed to stop tcpdump: {str(e)}")
        return False


def verify_arp_in_pcap(dut: str, pcap_file: str, src_ip: str, dst_ip: str) -> bool:
    """
    Verify ARP packets in tcpdump capture
    """
    try:
        st.log(f"Verifying ARP in pcap file: {pcap_file}")
        cmd = f"sudo tcpdump -r {pcap_file} -nn -e -v"
        output = st.exec_ssh(dut, cmd, timeout=30)
        st.log(f"Pcap contents: {output}")

        output_str = str(output).lower()

        if src_ip in output_str and dst_ip in output_str:
            st.log("ARP packets found in capture")
            return True
        else:
            st.error("ARP packets NOT found in capture")
            return False

    except Exception as e:
        st.error(f"Failed to verify ARP in pcap: {str(e)}")
        return False


def verify_arp_entry(dut: str, ip_address: str, expected_mac: str, interface: str) -> bool:
    """
    Verify ARP entry in ARP table
    """
    try:
        st.log(f"Verifying ARP entry on {dut} for {ip_address}")
        cmd = f"show ip arp | grep {ip_address}"
        output = st.show(dut, cmd, type=data.cli_type, skip_error_check=True)
        st.log(f"ARP table output: {output}")

        output_str = str(output).lower()

        if ip_address in output_str:
            st.log(f"ARP entry found for {ip_address}")
            return True
        else:
            st.error(f"ARP entry NOT found for {ip_address}")
            return False

    except Exception as e:
        st.error(f"Failed to verify ARP entry: {str(e)}")
        return False


def remove_file(dut: str, file_path: str) -> bool:
    """
    Remove a file from the DUT
    """
    try:
        cmd = f"sudo rm -f {file_path}"
        st.exec_ssh(dut, cmd)
        st.log(f"Removed file: {file_path}")
        return True
    except Exception as e:
        st.error(f"Failed to remove file {file_path}: {str(e)}")
        return False


def test_arp_vlan():
    """
    Test ID: 4.17.6
    Test Case: Verify ARP on VLAN Interface

    Expected Result:
    ARP works correctly on VLAN-tagged interface, ARP table populated with correct entry
    """

    result = True

    try:
        st.log("=" * 80)
        st.log("Test: Verify ARP on VLAN Interface")
        st.log("=" * 80)

        dut1_ip_only = CONFIG.dut1_ip.split('/')[0]
        dut2_ip_only = CONFIG.dut2_ip.split('/')[0]

        # Get DUT1 VLAN interface MAC
        st.log("Step 1: Getting DUT1 VLAN interface MAC address")
        dut1_mac = get_interface_mac(vars.D1, CONFIG.dut1_vlan_interface)

        if dut1_mac == "00:00:00:00:00:00":
            st.error("Failed to get DUT1 MAC address")
            result = False

        # Create ARP request Scapy script on DUT1
        st.log("Step 2: Creating ARP request Scapy script on DUT1")

        scapy_script = f"""from scapy.all import *

iface = "{CONFIG.dut1_vlan_interface}"
src_ip = "{dut1_ip_only}"
src_mac = "{dut1_mac}"
dst_ip = "{dut2_ip_only}"

print(f"[*] Scenario 6: ARP on VLAN Interface")
print(f"[*] Sending ARP request on VLAN {CONFIG.vlan_id}")

arp_req = Ether(src=src_mac, dst="ff:ff:ff:ff:ff:ff") / ARP(
    op=1,
    hwsrc=src_mac,
    psrc=src_ip,
    hwdst="00:00:00:00:00:00",
    pdst=dst_ip
)

sendp(arp_req, iface=iface, verbose=True, count=5)
print("[+] ARP request sent")
"""

        if not create_scapy_script(vars.D1, CONFIG.script_file, scapy_script):
            st.error("Failed to create Scapy script")
            result = False

        # Start tcpdump on DUT2
        st.log("Step 3: Starting tcpdump on DUT2")
        if not start_tcpdump(vars.D2, CONFIG.dut2_vlan_interface, CONFIG.pcap_file):
            st.error("Failed to start tcpdump")
            result = False

        # Execute ARP script on DUT1
        st.log("Step 4: Executing ARP script on DUT1")
        if not run_scapy_script(vars.D1, CONFIG.script_file):
            st.error("Failed to execute Scapy script")
            result = False

        st.wait(3)

        # Stop tcpdump
        st.log("Step 5: Stopping tcpdump on DUT2")
        stop_tcpdump(vars.D2)
        st.wait(2)

        # Verify ARP packets in capture
        st.log("Step 6: Verifying ARP packets in capture")
        if not verify_arp_in_pcap(vars.D2, CONFIG.pcap_file, dut1_ip_only, dut2_ip_only):
            st.error("ARP verification in pcap failed")
            result = False

        # Verify ARP entry in DUT2 table
        st.log("Step 7: Verifying ARP entry in DUT2 table")
        if not verify_arp_entry(vars.D2, dut1_ip_only, dut1_mac, CONFIG.dut2_vlan_interface):
            st.error("ARP entry verification failed")
            result = False

        # Report result
        if result:
            st.report_pass("test_case_passed")
        else:
            st.report_fail("test_case_failed", "One or more verification steps failed")

    except Exception as e:
        st.log(f"Exception in test execution: {str(e)}")
        st.report_fail("test_case_failed", str(e))

    finally:
        stop_tcpdump(vars.D2)
        st.log("Test execution completed")
