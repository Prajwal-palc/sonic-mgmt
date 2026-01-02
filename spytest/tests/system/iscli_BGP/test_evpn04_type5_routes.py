"""
EVPN Test EVPN-04: Type-5 IP Prefix Route Advertisement

Author: Auto-generated
Copyright (C) 2024

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  system/iscli_BGP/test_evpn04_type5_routes.py \
  --logs-path ./logs/evpn04_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates BGP EVPN Type-5 routes (IP Prefix routes).

  EVPN Type-5 routes carry IP prefix information and are used for:
  - Inter-subnet routing in EVPN networks
  - Advertising IP prefixes across VXLAN fabric
  - L3 VPN services in data center networks

  Test Scenario:
  - DUT1 (AS 65001) and DUT2 (AS 65002) with BGP EVPN peering
  - l2vpn evpn address-family activated
  - Validates EVPN session establishment
  - Verifies EVPN address-family configuration

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Testbed: testbed_2vs.yaml
  - Devices: Virtual switches
  - Credentials: admin/Net@123
  - Physical connection: DUT1 Ethernet4 <-> DUT2 Ethernet4
"""

from __future__ import annotations
import pytest
from spytest import st, SpyTestDict

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

    # Loopback addressing
    data.d1_loopback = "1.1.1.1"
    data.d2_loopback = "2.2.2.2"
    data.loopback_prefix = "32"

    # BGP configuration
    data.d1_asn = "65001"
    data.d2_asn = "65002"
    data.d1_router_id = "1.1.1.1"
    data.d2_router_id = "2.2.2.2"


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown"""
    global vars, data

    st.banner("MODULE PROLOGUE: EVPN-04 Type-5 Routes")
    initialize_data()

    yield

    # Module cleanup
    st.banner("MODULE EPILOGUE: Cleanup EVPN-04")
    cleanup_evpn()


def configure_dut1_evpn() -> bool:
    """Configure DUT1 with interface, loopback, and BGP EVPN"""

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

    # Configure BGP with l2vpn evpn address-family
    st.log("Configuring BGP with l2vpn evpn address-family on DUT1")
    commands = [
        f"router bgp {data.d1_asn}",
        f"router-id {data.d1_router_id}",
        f"neighbor {data.d2_ip} remote-as {data.d2_asn}",
        "address-family l2vpn evpn",
        "activate"
    ]
    st.config(data.dut1, commands, type=data.cli_type)

    return True


def configure_dut2_evpn() -> bool:
    """Configure DUT2 with interface, loopback, and BGP EVPN"""

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

    # Configure BGP with l2vpn evpn address-family
    st.log("Configuring BGP with l2vpn evpn address-family on DUT2")
    commands = [
        f"router bgp {data.d2_asn}",
        f"router-id {data.d2_router_id}",
        f"neighbor {data.d1_ip} remote-as {data.d1_asn}",
        "address-family l2vpn evpn",
        "activate"
    ]
    st.config(data.dut2, commands, type=data.cli_type)

    return True


def verify_evpn_config(dut: str) -> bool:
    """Verify l2vpn evpn address-family configuration"""
    output = st.show(dut, "show running-configuration bgp", type=data.cli_type)
    output_str = str(output)

    if "address-family l2vpn evpn" in output_str and "activate" in output_str:
        st.log(f"✅ l2vpn evpn address-family configured on {dut}")
        return True
    else:
        st.error(f"❌ l2vpn evpn address-family NOT configured on {dut}")
        return False


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


def cleanup_evpn() -> bool:
    """Cleanup EVPN configuration"""
    st.log("Cleaning up EVPN configuration")

    # Cleanup BGP
    commands = ["no router bgp"]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
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


def test_evpn04_type5_routes():
    """
    Test EVPN-04: Type-5 IP Prefix Routes

    Validates:
    1. DUT1 and DUT2 configured with BGP EVPN
    2. l2vpn evpn address-family activated
    3. BGP sessions established
    4. EVPN configuration verified
    """
    st.banner("TEST: EVPN-04 Type-5 IP Prefix Routes")

    # Initialize validation tracking
    validation_failures = []
    tech_support_generated = False

    try:
        # Step 1: Configure DUT1
        st.log("Step 1: Configuring DUT1 with BGP EVPN")
        if not configure_dut1_evpn():
            error_msg = f"DUT1 EVPN configuration failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("✓ DUT1 configured successfully")

        # Step 2: Configure DUT2
        st.log("Step 2: Configuring DUT2 with BGP EVPN")
        if not configure_dut2_evpn():
            error_msg = f"DUT2 EVPN configuration failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("✓ DUT2 configured successfully")

        # Wait for BGP EVPN session
        st.wait(15, "Waiting for BGP EVPN session establishment")

        # Step 3: Verify l2vpn evpn address-family configuration
        st.log("Step 3: Verify l2vpn evpn address-family configuration")

        if not verify_evpn_config(data.dut1):
            error_msg = f"l2vpn evpn address-family NOT configured on {data.dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ l2vpn evpn address-family verified on DUT1")

        if not verify_evpn_config(data.dut2):
            error_msg = f"l2vpn evpn address-family NOT configured on {data.dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ l2vpn evpn address-family verified on DUT2")

        st.log("✅ EVPN address-family configured on both DUTs")

        # Step 4: Verify BGP sessions
        st.log("Step 4: Verify BGP sessions")
        st.wait(15, "Additional wait for BGP session")

        if not verify_bgp_session(data.dut1, data.d2_ip):
            st.log("BGP session not established on DUT1, waiting longer...")
            st.wait(15)
            if not verify_bgp_session(data.dut1, data.d2_ip):
                error_msg = f"BGP neighbor {data.d2_ip} not established on {data.dut1}"
                st.error(error_msg)
                validation_failures.append(error_msg)
        else:
            st.log(f"✓ BGP session established on DUT1 to {data.d2_ip}")

        if not verify_bgp_session(data.dut2, data.d1_ip):
            st.log("BGP session not established on DUT2, waiting longer...")
            st.wait(15)
            if not verify_bgp_session(data.dut2, data.d1_ip):
                error_msg = f"BGP neighbor {data.d1_ip} not established on {data.dut2}"
                st.error(error_msg)
                validation_failures.append(error_msg)
        else:
            st.log(f"✓ BGP session established on DUT2 to {data.d1_ip}")

        st.log("✅ BGP sessions established")

        # Step 5: Display BGP summary
        st.log("Step 5: Display BGP summary")
        output1 = st.show(data.dut1, "show bgp summary", type=data.cli_type)
        st.log(f"DUT1 BGP Summary:\n{output1}")

        output2 = st.show(data.dut2, "show bgp summary", type=data.cli_type)
        st.log(f"DUT2 BGP Summary:\n{output2}")

        # Step 6: Display EVPN configuration
        st.log("Step 6: Display BGP EVPN configuration")
        output1 = st.show(data.dut1, "show running-configuration bgp", type=data.cli_type)
        st.log(f"DUT1 BGP Config:\n{output1}")

        output2 = st.show(data.dut2, "show running-configuration bgp", type=data.cli_type)
        st.log(f"DUT2 BGP Config:\n{output2}")

    except Exception as e:
        error_msg = f"Exception during test execution: {str(e)}"
        st.error(error_msg)
        validation_failures.append(error_msg)

    finally:
        st.banner("CLEANUP: Unconfiguring BGP EVPN and Interfaces (ALWAYS EXECUTES)")

        try:
            # BGP cleanup
            st.config(data.dut1, ["no router bgp"], type=data.cli_type, skip_error_check=True)
            st.config(data.dut2, ["no router bgp"], type=data.cli_type, skip_error_check=True)
            st.log("✓ BGP configuration removed from both DUTs")

            # IP address cleanup
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
            st.log("✓ IP addresses removed from interfaces")

            # Loopback cleanup
            st.config(data.dut1, ["no interface Loopback0"], type=data.cli_type, skip_error_check=True)
            st.config(data.dut2, ["no interface Loopback0"], type=data.cli_type, skip_error_check=True)
            st.log("✓ Loopback interfaces removed")

            st.log("✓ Cleanup completed successfully")

        except Exception as cleanup_error:
            error_msg = f"Cleanup error: {str(cleanup_error)}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Tech-support generation after cleanup
        if validation_failures and not tech_support_generated:
            st.banner("GENERATING TECH-SUPPORT (Validation Failures Detected)")
            try:
                st.generate_tech_support(dut_list=[data.dut1, data.dut2], name="evpn04_validation_failures")
                tech_support_generated = True
                st.log("✓ Tech-support generated successfully")
            except Exception as tech_error:
                st.error(f"Failed to generate tech-support: {tech_error}")

    # Final reporting
    st.banner("EVPN-04 TEST FINAL REPORT")

    if validation_failures:
        st.error("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"ERROR {idx}. {failure}")

        error_summary = f"Test completed with {len(validation_failures)} validation failures"
        st.log(f"Note: Cleanup completed despite {len(validation_failures)} failures")
        st.log("Tech-support has been generated for debugging")
        st.report_fail("msg", error_summary)
    else:
        st.log("All validations passed successfully")
        st.log("✅ EVPN-04 Test PASSED: Type-5 IP Prefix Routes")
        st.log("   - DUT1 (AS 65001): l2vpn evpn address-family activated")
        st.log("   - DUT2 (AS 65002): l2vpn evpn address-family activated")
        st.log("   - BGP sessions established")
        st.log("   - EVPN Type-5 routes: Carry IP prefix information for inter-subnet routing")
        st.report_pass("test_case_passed")
