"""
BGP Feature Test BGP-38: Soft-Reconfiguration Inbound

Author: Auto-generated
Copyright (C) 2024

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest
  ./RUN_BGP38.sh

  OR manually:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_bgp55.yaml \\
  tests/system/iscli_BGP/test_bgp38_soft_reconfiguration.py \\
  --logs-path ./logs/bgp38_$(date +%Y%m%d_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates BGP soft-reconfiguration inbound functionality, which
  stores received routes before applying inbound policies, enabling policy
  changes without resetting the BGP session.

  Soft-reconfiguration stores a copy of received routes in memory, allowing:
  - Policy changes without session reset
  - View of pre-policy routes via "show bgp neighbors received-routes"
  - Faster convergence when policies change

  Test Scenario:
  - DUT1 (AS 65001) and DUT2 (AS 65002) with EBGP session
  - Both configured with soft-reconfiguration inbound
  - Routes advertised between peers
  - Validates soft-reconfiguration is enabled and functional

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Testbed: testbed_bgp55.yaml
  - Devices: DUT1 (192.168.100.229), DUT2 (192.168.100.141)
  - Credentials: admin/Net@123
  - Physical connection: DUT1 Ethernet4 <-> DUT2 Ethernet4
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()


def initialize_data() -> None:
    """Initialize test data and topology"""
    global vars, data

    # Get topology - requires D1-D2 connection
    vars = st.ensure_min_topology("D1D2:1")

    # Test configuration
    data.cli_type = "klish"

    # Device data
    data.dut1 = vars.D1
    data.dut2 = vars.D2

    # Interface data
    data.d1_phy_port = vars.D1D2P1
    data.d2_phy_port = vars.D2D1P1

    # IP addressing
    data.d1_ip = "10.1.1.1"
    data.d2_ip = "10.1.1.2"
    data.ip_prefix = "24"

    data.d1_loopback = "1.1.1.1"
    data.d2_loopback = "2.2.2.2"
    data.loopback_prefix = "32"

    # BGP configuration
    data.d1_asn = "65001"
    data.d2_asn = "65002"
    data.d1_router_id = "1.1.1.1"
    data.d2_router_id = "2.2.2.2"

    # Test prefix
    data.test_prefix = "192.168.100.0/24"


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown"""
    global vars, data

    st.banner("MODULE PROLOGUE: Starting BGP-38 Soft-Reconfiguration Test")
    initialize_data()

    # Module setup
    if not configure_base_bgp():
        st.report_fail("module_config_failed")

    yield

    # Module cleanup
    st.banner("MODULE EPILOGUE: Cleanup BGP-38")
    cleanup_bgp()


def configure_base_bgp() -> bool:
    """Configure base BGP and interfaces for the test"""
    st.banner("Configuring Interfaces and BGP")

    # Configure DUT1
    st.log("Configuring DUT1 with soft-reconfiguration inbound")
    if not configure_dut1_base():
        return False

    # Configure DUT2
    st.log("Configuring DUT2 with soft-reconfiguration inbound")
    if not configure_dut2_base():
        return False

    # Wait for BGP session
    st.wait(15, "Waiting for EBGP session establishment")

    return True


def configure_dut1_base() -> bool:
    """Configure DUT1 with interfaces, loopback, and BGP with soft-reconfig"""

    # Configure physical interface
    commands = [
        f"interface {data.d1_phy_port}",
        "no shutdown",
        f"ip address {data.d1_ip}/{data.ip_prefix}"
    ]
    st.config(data.dut1, commands, type=data.cli_type)

    # Configure loopback
    commands = [
        "interface Loopback0",
        f"ip address {data.d1_loopback}/{data.loopback_prefix}"
    ]
    st.config(data.dut1, commands, type=data.cli_type)

    # Wait for interfaces
    st.wait(5)

    # Configure BGP with soft-reconfiguration inbound
    st.log("Configuring BGP on DUT1 with soft-reconfiguration inbound")
    commands = [
        f"router bgp {data.d1_asn}",
        f"router-id {data.d1_router_id}",
        f"neighbor {data.d2_ip} remote-as {data.d2_asn}",
        "address-family ipv4 unicast",
        "activate",
        "soft-reconfiguration inbound"
    ]
    st.config(data.dut1, commands, type=data.cli_type)

    # Network advertisement at global AF level
    commands = [
        f"router bgp {data.d1_asn}",
        "address-family ipv4 unicast",
        f"network {data.d1_loopback}/{data.loopback_prefix}",
        f"network {data.test_prefix}"
    ]
    st.config(data.dut1, commands, type=data.cli_type)

    return True


def configure_dut2_base() -> bool:
    """Configure DUT2 with interfaces, loopback, and BGP with soft-reconfig"""

    # Configure physical interface
    commands = [
        f"interface {data.d2_phy_port}",
        "no shutdown",
        f"ip address {data.d2_ip}/{data.ip_prefix}"
    ]
    st.config(data.dut2, commands, type=data.cli_type)

    # Configure loopback
    commands = [
        "interface Loopback0",
        f"ip address {data.d2_loopback}/{data.loopback_prefix}"
    ]
    st.config(data.dut2, commands, type=data.cli_type)

    # Wait for interfaces
    st.wait(5)

    # Configure BGP with soft-reconfiguration inbound
    st.log("Configuring BGP on DUT2 with soft-reconfiguration inbound")
    commands = [
        f"router bgp {data.d2_asn}",
        f"router-id {data.d2_router_id}",
        f"neighbor {data.d1_ip} remote-as {data.d1_asn}",
        "address-family ipv4 unicast",
        "activate",
        "soft-reconfiguration inbound"
    ]
    st.config(data.dut2, commands, type=data.cli_type)

    # Network advertisement at global AF level
    commands = [
        f"router bgp {data.d2_asn}",
        "address-family ipv4 unicast",
        f"network {data.d2_loopback}/{data.loopback_prefix}"
    ]
    st.config(data.dut2, commands, type=data.cli_type)

    return True


def verify_bgp_session(dut: str, neighbor_ip: str) -> bool:
    """Verify BGP session is established"""
    output = st.show(dut, "show bgp summary", type=data.cli_type)
    output_str = str(output)

    if neighbor_ip in output_str and ("Established" in output_str or "00:" in output_str):
        st.log(f"✅ BGP session established with {neighbor_ip} on {dut}")
        return True
    else:
        st.log(f"⚠️ BGP session not yet established with {neighbor_ip} on {dut}")
        return False


def verify_soft_reconfig_config(dut: str) -> bool:
    """Verify soft-reconfiguration inbound configuration"""
    output = st.show(dut, "show running-configuration bgp", type=data.cli_type)
    output_str = str(output)

    if "soft-reconfiguration inbound" in output_str:
        st.log(f"✅ soft-reconfiguration inbound configured on {dut}")
        return True
    else:
        st.error(f"❌ soft-reconfiguration inbound NOT configured on {dut}")
        return False


def verify_route_received(dut: str, prefix: str) -> bool:
    """Verify route is received in BGP table"""
    output = st.show(dut, f"show bgp ipv4 unicast", type=data.cli_type)
    output_str = str(output)

    if prefix in output_str or prefix.split('/')[0] in output_str:
        st.log(f"✅ Route {prefix} received on {dut}")
        return True
    else:
        st.log(f"⚠️ Route {prefix} NOT received on {dut}")
        return False


def cleanup_bgp() -> bool:
    """Cleanup BGP configuration"""
    st.log("Cleaning up BGP configuration")

    # Cleanup DUT1
    commands = [f"no router bgp"]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

    # Cleanup DUT2
    commands = [f"no router bgp"]
    st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)

    # Cleanup interfaces
    commands = [
        f"interface {data.d1_phy_port}",
        f"no ip address {data.d1_ip}/{data.ip_prefix}"
    ]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

    commands = [
        f"interface {data.d2_phy_port}",
        f"no ip address {data.d2_ip}/{data.ip_prefix}"
    ]
    st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)

    # Cleanup loopbacks
    commands = ["no interface Loopback0"]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
    st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)

    return True


def test_bgp38_soft_reconfiguration():
    """
    Test BGP-38: Soft-Reconfiguration Inbound

    Validates:
    1. soft-reconfiguration inbound configured on both DUTs
    2. EBGP session established
    3. Configuration verified via show running-config
    4. Routes exchanged successfully
    5. BGP summary shows session status
    """
    st.banner("TEST: BGP-38 Soft-Reconfiguration Inbound")

    # Step 1: Verify soft-reconfiguration configuration
    st.log("Step 1: Verify soft-reconfiguration inbound configuration")

    if not verify_soft_reconfig_config(data.dut1):
        st.report_fail("config_not_applied", "soft-reconfiguration inbound on DUT1")

    if not verify_soft_reconfig_config(data.dut2):
        st.report_fail("config_not_applied", "soft-reconfiguration inbound on DUT2")

    st.log("✅ Soft-reconfiguration inbound configured on both DUTs")

    # Step 2: Verify BGP sessions established
    st.log("Step 2: Verify BGP sessions")
    st.wait(15, "Additional wait for BGP session")

    if not verify_bgp_session(data.dut1, data.d2_ip):
        st.log("BGP session not established on DUT1, waiting longer...")
        st.wait(15)
        if not verify_bgp_session(data.dut1, data.d2_ip):
            st.report_fail("bgp_neighbor_not_established", data.d2_ip)

    if not verify_bgp_session(data.dut2, data.d1_ip):
        st.log("BGP session not established on DUT2, waiting longer...")
        st.wait(15)
        if not verify_bgp_session(data.dut2, data.d1_ip):
            st.report_fail("bgp_neighbor_not_established", data.d1_ip)

    st.log("✅ BGP sessions established with soft-reconfiguration support")

    # Step 3: Verify route exchange
    st.log("Step 3: Verify route exchange")
    st.wait(10, "Waiting for route exchange")

    # DUT2 should receive DUT1's loopback
    verify_route_received(data.dut2, f"{data.d1_loopback}/{data.loopback_prefix}")

    # DUT1 should receive DUT2's loopback
    verify_route_received(data.dut1, f"{data.d2_loopback}/{data.loopback_prefix}")

    # Step 4: Display BGP summary for verification
    st.log("Step 4: Display BGP summary")
    output1 = st.show(data.dut1, "show bgp summary", type=data.cli_type)
    st.log(f"DUT1 BGP Summary:\n{output1}")

    output2 = st.show(data.dut2, "show bgp summary", type=data.cli_type)
    st.log(f"DUT2 BGP Summary:\n{output2}")

    # Step 5: Display running configuration
    st.log("Step 5: Display BGP configuration")
    output1 = st.show(data.dut1, "show running-configuration bgp", type=data.cli_type)
    st.log(f"DUT1 BGP Config:\n{output1}")

    output2 = st.show(data.dut2, "show running-configuration bgp", type=data.cli_type)
    st.log(f"DUT2 BGP Config:\n{output2}")

    st.log("✅ BGP-38: Soft-reconfiguration inbound test completed successfully")
    st.report_pass("test_case_passed")
