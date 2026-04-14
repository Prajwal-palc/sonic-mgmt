"""
Test ID: 4.17.4
Test Case: Verify Static ARP Entry
Test Item: Functional
Test Objective: Validate that static ARP entries persist despite dynamic ARP replies
"""

import pytest
from spytest import st
from spytest.dicts import SpyTestDict

data = SpyTestDict()
CONFIG = SpyTestDict()

# Test Configuration
CONFIG.dut1_interface = "Ethernet32"
CONFIG.dut2_interface = "Ethernet32"
CONFIG.dut1_ip = "10.4.1.1/24"
CONFIG.dut2_ip = "10.4.1.2/24"
CONFIG.static_mac = "aa:bb:cc:dd:ee:ff"  # Static MAC to be configured
CONFIG.script_file = "/tmp/scenario4_static.py"
CONFIG.pcap_file = "~/scenario4.pcap"


@pytest.fixture(scope="module", autouse=True)
def arp_static_module_hooks(request):
    """
    Module-level fixture for ARP Static Entry test setup and cleanup
    """
    global vars, data
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()

    st.log("=" * 80)
    st.log("ARP Static Entry Test - Module Setup")
    st.log("=" * 80)

    arp_pre_config()
    yield
    arp_pre_config_cleanup()

    st.log("=" * 80)
    st.log("ARP Static Entry Test - Module Cleanup Complete")
    st.log("=" * 80)


def arp_pre_config():
    """
    Pre-configuration for ARP Static Entry test
    """
    try:
        st.log("Configuring routed interfaces for Static ARP test...")

        # Configure DUT1 Ethernet32
        result1 = configure_routed_interface(vars.D1, CONFIG.dut1_interface, CONFIG.dut1_ip)

        # Configure DUT2 Ethernet32
        result2 = configure_routed_interface(vars.D2, CONFIG.dut2_interface, CONFIG.dut2_ip)

        if result1 and result2:
            st.log("Pre-configuration completed successfully")
        else:
            st.error("Pre-configuration failed, but continuing...")

    except Exception as e:
        st.error(f"Exception in pre-config: {str(e)}")


def arp_pre_config_cleanup():
    """
    Cleanup configuration after test
    """
    try:
        st.log("Cleaning up ARP Static Entry test configuration...")

        # Remove static ARP entry
        dut2_ip_only = CONFIG.dut2_ip.split('/')[0]
        remove_static_arp(vars.D1, dut2_ip_only)

        # Remove interface configurations
        cleanup_routed_interface(vars.D1, CONFIG.dut1_interface)
        cleanup_routed_interface(vars.D2, CONFIG.dut2_interface)

        # Remove Scapy script
        remove_file(vars.D2, CONFIG.script_file)

        # Remove pcap file
        remove_file(vars.D2, CONFIG.pcap_file)

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


def add_static_arp(dut: str, ip_address: str, mac_address: str) -> bool:
    """
    Add a static ARP entry
    """
    try:
        st.log(f"Adding static ARP entry on {dut}: {ip_address} -> {mac_address}")

        cmd = f"sudo arp -s {ip_address} {mac_address}"
        output = st.exec_ssh(dut, cmd)

        st.log(f"Static ARP add output: {output}")
        st.wait(1)
        return True

    except Exception as e:
        st.error(f"Failed to add static ARP: {str(e)}")
        return False


def remove_static_arp(dut: str, ip_address: str) -> bool:
    """
    Remove a static ARP entry
    """
    try:
        st.log(f"Removing static ARP entry on {dut}: {ip_address}")

        cmd = f"sudo arp -d {ip_address}"
        output = st.exec_ssh(dut, cmd)

        st.log(f"Static ARP remove output: {output}")
        return True

    except Exception as e:
        st.error(f"Failed to remove static ARP: {str(e)}")
        return False


def verify_static_arp_entry(dut: str, ip_address: str, expected_mac: str) -> bool:
    """
    Verify that a static ARP entry exists with the expected MAC
    """
    try:
        st.log(f"Verifying static ARP entry on {dut} for {ip_address}")

        cmd = f"show ip arp | grep {ip_address}"
        output = st.show(dut, cmd, type=data.cli_type, skip_error_check=True)

        st.log(f"ARP table output: {output}")

        output_str = str(output).lower()
        expected_mac_lower = expected_mac.lower()

        if ip_address in output_str and expected_mac_lower in output_str:
            st.log(f"Static ARP entry verified: {ip_address} -> {expected_mac}")
            return True
        else:
            st.error(f"Static ARP entry NOT found or MAC mismatch")
            return False

    except Exception as e:
        st.error(f"Failed to verify static ARP entry: {str(e)}")
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

        # Fallback: try direct command
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

        # Escape single quotes in script content
        script_encoded = script_content.replace("'", "'\\''")

        # Use printf to create the script file
        cmd = f"printf '{script_encoded}' > {script_path}"
        st.exec_ssh(dut, cmd)

        # Verify file was created
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

        # Remove old pcap file if exists
        st.exec_ssh(dut, f"sudo rm -f {pcap_file}")

        # Start tcpdump in background
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


def test_arp_static_entry():
    """
    Test ID: 4.17.4
    Test Case: Verify Static ARP Entry

    Test Steps:
    1. Configure IP 10.4.1.1/24 on DUT1 Ethernet32 and 10.4.1.2/24 on DUT2 Ethernet32
    2. Add static ARP entry on DUT1: 10.4.1.2 -> aa:bb:cc:dd:ee:ff
    3. Verify static entry in ARP table
    4. Create Scapy script on DUT2 to send ARP reply with static MAC
    5. Start tcpdump on DUT2
    6. Execute script - DUT2 sends ARP reply
    7. Verify static entry remains unchanged on DUT1

    Expected Result:
    Static ARP entry remains unchanged on DUT1 despite receiving ARP reply,
    demonstrating static entry persistence
    """

    result = True

    try:
        st.log("=" * 80)
        st.log("Test: Verify Static ARP Entry")
        st.log("=" * 80)

        dut1_ip_only = CONFIG.dut1_ip.split('/')[0]
        dut2_ip_only = CONFIG.dut2_ip.split('/')[0]

        # Step 1: Add static ARP entry on DUT1
        st.log("Step 1: Adding static ARP entry on DUT1")
        if not add_static_arp(vars.D1, dut2_ip_only, CONFIG.static_mac):
            st.error("Failed to add static ARP entry")
            result = False

        st.wait(2)

        # Step 2: Verify static entry was added
        st.log("Step 2: Verifying static ARP entry was added")
        if not verify_static_arp_entry(vars.D1, dut2_ip_only, CONFIG.static_mac):
            st.error("Static ARP entry not found after adding")
            result = False

        # Step 3: Get DUT2 MAC (will be different from static MAC)
        st.log("Step 3: Getting DUT2 interface MAC address")
        dut2_mac = get_interface_mac(vars.D2, CONFIG.dut2_interface)

        # Step 4: Create ARP reply Scapy script on DUT2
        st.log("Step 4: Creating ARP reply Scapy script on DUT2")

        scapy_script = f"""from scapy.all import *

iface = "{CONFIG.dut2_interface}"
src_ip = "{dut2_ip_only}"
src_mac = "{CONFIG.static_mac}"
dst_ip = "{dut1_ip_only}"

print(f"[*] Scenario 4: Static ARP Entry")
print(f"[*] Sending ARP reply with static MAC")

arp_reply = Ether(src=src_mac, dst="ff:ff:ff:ff:ff:ff") / ARP(
    op=2,
    hwsrc=src_mac,
    psrc=src_ip,
    hwdst="ff:ff:ff:ff:ff:ff",
    pdst=dst_ip
)

sendp(arp_reply, iface=iface, verbose=True, count=3)
print("[+] ARP reply sent")
"""

        if not create_scapy_script(vars.D2, CONFIG.script_file, scapy_script):
            st.error("Failed to create Scapy script")
            result = False

        # Step 5: Start tcpdump on DUT2
        st.log("Step 5: Starting tcpdump on DUT2")
        if not start_tcpdump(vars.D2, CONFIG.dut2_interface, CONFIG.pcap_file):
            st.error("Failed to start tcpdump")
            result = False

        # Step 6: Execute ARP reply script on DUT2
        st.log("Step 6: Executing ARP reply script on DUT2")
        if not run_scapy_script(vars.D2, CONFIG.script_file):
            st.error("Failed to execute Scapy script")
            result = False

        st.wait(3)

        # Step 7: Stop tcpdump
        st.log("Step 7: Stopping tcpdump on DUT2")
        stop_tcpdump(vars.D2)

        st.wait(2)

        # Step 8: Verify static entry STILL exists with same MAC
        st.log("Step 8: Verifying static ARP entry is unchanged")
        if not verify_static_arp_entry(vars.D1, dut2_ip_only, CONFIG.static_mac):
            st.error("Static ARP entry changed or removed - Test FAILED")
            result = False
        else:
            st.log("Static ARP entry unchanged - Test PASSED")

        # Report result
        if result:
            st.report_pass("test_case_passed")
        else:
            st.report_fail("test_case_failed", "One or more verification steps failed")

    except Exception as e:
        st.log(f"Exception in test execution: {str(e)}")
        st.report_fail("test_case_failed", str(e))

    finally:
        # Ensure tcpdump is stopped
        stop_tcpdump(vars.D2)
        st.log("Test execution completed")
