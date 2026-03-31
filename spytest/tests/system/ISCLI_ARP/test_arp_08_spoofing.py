"""
Test ID: 4.17.8
Test Case: Verify ARP Spoofing Attack
Test Item: Security/Negative
Test Objective: Validate system behavior when receiving malicious ARP packets with fake MAC addresses
"""

import pytest
from spytest import st
from spytest.dicts import SpyTestDict

data = SpyTestDict()
CONFIG = SpyTestDict()

# Test Configuration
CONFIG.dut1_interface = "Ethernet32"
CONFIG.dut2_interface = "Ethernet32"
CONFIG.dut1_ip = "10.8.1.1/24"
CONFIG.dut2_ip = "10.8.1.2/24"
CONFIG.fake_mac = "aa:bb:cc:dd:ee:ff"  # Malicious MAC
CONFIG.script_file = "/tmp/scenario8_spoofing.py"
CONFIG.pcap_file = "~/scenario8.pcap"


@pytest.fixture(scope="module", autouse=True)
def arp_spoofing_module_hooks(request):
    """
    Module-level fixture for ARP Spoofing test setup and cleanup
    """
    global vars, data
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()

    st.log("=" * 80)
    st.log("ARP Spoofing Test - Module Setup")
    st.log("=" * 80)

    arp_pre_config()
    yield
    arp_pre_config_cleanup()

    st.log("=" * 80)
    st.log("ARP Spoofing Test - Module Cleanup Complete")
    st.log("=" * 80)


def arp_pre_config():
    """
    Pre-configuration for ARP Spoofing test
    """
    try:
        st.log("Configuring routed interfaces for ARP Spoofing test...")

        configure_routed_interface(vars.D1, CONFIG.dut1_interface, CONFIG.dut1_ip)
        configure_routed_interface(vars.D2, CONFIG.dut2_interface, CONFIG.dut2_ip)

        st.log("Pre-configuration completed")

    except Exception as e:
        st.error(f"Exception in pre-config: {str(e)}")


def arp_pre_config_cleanup():
    """
    Cleanup configuration after test
    """
    try:
        st.log("Cleaning up ARP Spoofing test configuration...")

        cleanup_routed_interface(vars.D1, CONFIG.dut1_interface)
        cleanup_routed_interface(vars.D2, CONFIG.dut2_interface)

        remove_file(vars.D2, CONFIG.script_file)
        remove_file(vars.D1, CONFIG.pcap_file)

        st.log("Cleanup completed")

    except Exception as e:
        st.error(f"Exception in cleanup: {str(e)}")


def configure_routed_interface(dut: str, interface: str, ip_address: str) -> bool:
    """
    Configure interface in routed mode with IP address
    """
    try:
        st.log(f"Configuring {dut} {interface} with {ip_address}")

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
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure {interface} on {dut}: {str(e)}")
        return False


def cleanup_routed_interface(dut: str, interface: str) -> bool:
    """
    Remove IP configuration from interface
    """
    try:
        st.log(f"Cleaning up {dut} {interface}")

        commands = [
            "configure terminal",
            f"interface {interface}",
            "no ip address",
            "exit",
            "exit"
        ]

        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        return True

    except Exception as e:
        st.error(f"Failed to cleanup {interface} on {dut}: {str(e)}")
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


def verify_spoofed_arp_in_pcap(dut: str, pcap_file: str, fake_mac: str) -> bool:
    """
    Verify spoofed ARP packets in tcpdump capture
    """
    try:
        st.log(f"Verifying spoofed ARP in pcap file: {pcap_file}")
        cmd = f"sudo tcpdump -r {pcap_file} -nn -e -v"
        output = st.exec_ssh(dut, cmd, timeout=30)
        st.log(f"Pcap contents: {output}")

        output_str = str(output).lower()

        if fake_mac.lower() in output_str:
            st.log("Spoofed ARP packets found in capture")
            return True
        else:
            st.error("Spoofed ARP packets NOT found in capture")
            return False

    except Exception as e:
        st.error(f"Failed to verify spoofed ARP in pcap: {str(e)}")
        return False


def verify_arp_entry_not_spoofed(dut: str, ip_address: str, fake_mac: str) -> bool:
    """
    Verify that ARP entry was NOT updated with fake MAC (security check)
    """
    try:
        st.log(f"Verifying ARP entry on {dut} for {ip_address}")
        cmd = f"show ip arp | grep {ip_address}"
        output = st.show(dut, cmd, type=data.cli_type, skip_error_check=True)
        st.log(f"ARP table output: {output}")

        output_str = str(output).lower()
        fake_mac_lower = fake_mac.lower()

        if fake_mac_lower in output_str:
            st.error(f"ARP entry WAS spoofed with fake MAC - SECURITY ISSUE!")
            return False
        else:
            st.log(f"ARP entry NOT spoofed - system properly handled malicious ARP")
            return True

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


def test_arp_spoofing():
    """
    Test ID: 4.17.8
    Test Case: Verify ARP Spoofing Attack

    Expected Result:
    System detects/logs spoofed ARP or properly handles malicious packets without compromising security
    """

    result = True

    try:
        st.log("=" * 80)
        st.log("Test: Verify ARP Spoofing Attack")
        st.log("=" * 80)

        dut1_ip_only = CONFIG.dut1_ip.split('/')[0]
        dut2_ip_only = CONFIG.dut2_ip.split('/')[0]

        # Get DUT2 real MAC
        st.log("Step 1: Getting DUT2 interface real MAC address")
        dut2_real_mac = get_interface_mac(vars.D2, CONFIG.dut2_interface)

        # Create spoofed ARP Scapy script on DUT2
        st.log("Step 2: Creating spoofed ARP Scapy script on DUT2")

        scapy_script = f"""from scapy.all import *

iface = "{CONFIG.dut2_interface}"
src_ip = "{dut2_ip_only}"
src_mac = "{CONFIG.fake_mac}"
dst_ip = "{dut1_ip_only}"

print(f"[*] Scenario 8: ARP Spoofing Attack")
print(f"[*] Sending spoofed ARP with fake MAC: {CONFIG.fake_mac}")

spoofed_arp = Ether(src=src_mac, dst="ff:ff:ff:ff:ff:ff") / ARP(
    op=2,
    hwsrc=src_mac,
    psrc=src_ip,
    hwdst="ff:ff:ff:ff:ff:ff",
    pdst=dst_ip
)

sendp(spoofed_arp, iface=iface, verbose=True, count=5)
print("[+] Spoofed ARP packets sent")
"""

        if not create_scapy_script(vars.D2, CONFIG.script_file, scapy_script):
            st.error("Failed to create Scapy script")
            result = False

        # Start tcpdump on DUT1
        st.log("Step 3: Starting tcpdump on DUT1")
        if not start_tcpdump(vars.D1, CONFIG.dut1_interface, CONFIG.pcap_file):
            st.error("Failed to start tcpdump")
            result = False

        # Execute spoofed ARP script on DUT2
        st.log("Step 4: Executing spoofed ARP script on DUT2")
        if not run_scapy_script(vars.D2, CONFIG.script_file):
            st.error("Failed to execute Scapy script")
            result = False

        st.wait(3)

        # Stop tcpdump
        st.log("Step 5: Stopping tcpdump on DUT1")
        stop_tcpdump(vars.D1)
        st.wait(2)

        # Verify spoofed ARP packets were received
        st.log("Step 6: Verifying spoofed ARP packets in capture")
        if not verify_spoofed_arp_in_pcap(vars.D1, CONFIG.pcap_file, CONFIG.fake_mac):
            st.log("Spoofed ARP packets not captured - may have been filtered")

        # Verify DUT1 ARP table was NOT corrupted with fake MAC
        st.log("Step 7: Verifying ARP table was NOT corrupted")
        if not verify_arp_entry_not_spoofed(vars.D1, dut2_ip_only, CONFIG.fake_mac):
            st.error("SECURITY ISSUE: ARP table was spoofed!")
            result = False
        else:
            st.log("Security test PASSED: ARP table not corrupted by spoofed packets")

        # Report result
        if result:
            st.report_pass("test_case_passed")
        else:
            st.report_fail("test_case_failed", "Security verification failed")

    except Exception as e:
        st.log(f"Exception in test execution: {str(e)}")
        st.report_fail("test_case_failed", str(e))

    finally:
        stop_tcpdump(vars.D1)
        st.log("Test execution completed")
