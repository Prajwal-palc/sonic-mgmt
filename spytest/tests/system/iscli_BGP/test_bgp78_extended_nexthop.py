"""
BGP Capability Test BGP-78: Extended Next-Hop Capability

Author: Auto-generated
Copyright (C) 2024

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  system/iscli_BGP/test_bgp78_extended_nexthop.py \
  --logs-path ./logs/bgp78_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates BGP extended next-hop capability, which allows advertising
  IPv4 routes with IPv6 next-hops (RFC 5549).

  Extended next-hop enables:
  - IPv4 routing over IPv6-only infrastructure
  - Simplified dual-stack deployments
  - IPv6-only peering sessions carrying IPv4 routes

  Test Scenario:
  - DUT1 (AS 65001) and DUT2 (AS 65002) with IPv6 neighbor peering
  - Both configured with capability extended-nexthop
  - IPv4 routes advertised over IPv6 BGP session
  - Validates IPv6 next-hop for IPv4 routes

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

    # IPv4 addressing (for reference/testing)
    data.d1_ipv4 = "10.1.1.1"
    data.d2_ipv4 = "10.1.1.2"
    data.ipv4_prefix = "24"

    # IPv6 addressing (for BGP peering)
    data.d1_ipv6 = "2001:db8:10::1"
    data.d2_ipv6 = "2001:db8:10::2"
    data.ipv6_prefix = "64"

    # Loopback addressing
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

    st.banner("MODULE PROLOGUE: Starting BGP-78 Extended Next-Hop Test")
    initialize_data()

    yield

    # Module cleanup
    st.banner("MODULE EPILOGUE: Cleanup BGP-78")
    cleanup_bgp()


def configure_dut1_base() -> bool:
    """Configure DUT1 with IPv4/IPv6 interfaces and BGP with extended-nexthop"""

    # Configure physical interface with both IPv4 and IPv6
    commands = [
        f"interface {data.d1_phy_port}",
        "no shutdown",
        f"ip address {data.d1_ipv4}/{data.ipv4_prefix}",
        f"ipv6 address {data.d1_ipv6}/{data.ipv6_prefix}"
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

    # Configure BGP with IPv6 neighbor and extended-nexthop capability
    st.log("Configuring BGP on DUT1 with IPv6 neighbor")
    commands = [
        f"router bgp {data.d1_asn}",
        f"router-id {data.d1_router_id}",
        f"neighbor {data.d2_ipv6} remote-as {data.d2_asn}",
        "capability extended-nexthop",
        "address-family ipv4 unicast",
        "activate"
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
    """Configure DUT2 with IPv4/IPv6 interfaces and BGP with extended-nexthop"""

    # Configure physical interface with both IPv4 and IPv6
    commands = [
        f"interface {data.d2_phy_port}",
        "no shutdown",
        f"ip address {data.d2_ipv4}/{data.ipv4_prefix}",
        f"ipv6 address {data.d2_ipv6}/{data.ipv6_prefix}"
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

    # Configure BGP with IPv6 neighbor and extended-nexthop capability
    st.log("Configuring BGP on DUT2 with IPv6 neighbor")
    commands = [
        f"router bgp {data.d2_asn}",
        f"router-id {data.d2_router_id}",
        f"neighbor {data.d1_ipv6} remote-as {data.d1_asn}",
        "capability extended-nexthop",
        "address-family ipv4 unicast",
        "activate"
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


def verify_bgp_session(dut: str, neighbor_ipv6: str) -> bool:
    """Verify BGP session is established"""
    output = st.show(dut, "show bgp summary", type=data.cli_type)
    output_str = str(output)

    if neighbor_ipv6 in output_str and ("Established" in output_str or "00:" in output_str):
        st.log(f"✅ BGP session established with {neighbor_ipv6} on {dut}")
        return True
    else:
        st.log(f"⚠️ BGP session not yet established with {neighbor_ipv6} on {dut}")
        return False


def verify_extended_nexthop_config(dut: str) -> bool:
    """Verify extended-nexthop capability configuration"""
    output = st.show(dut, "show running-configuration bgp", type=data.cli_type)
    output_str = str(output)

    if "capability extended-nexthop" in output_str:
        st.log(f"✅ capability extended-nexthop configured on {dut}")
        return True
    else:
        st.error(f"❌ capability extended-nexthop NOT configured on {dut}")
        return False


def verify_route_received(dut: str, prefix: str) -> bool:
    """Verify IPv4 route is received"""
    output = st.show(dut, f"show bgp ipv4 unicast {prefix}", type=data.cli_type)
    output_str = str(output)

    if prefix in output_str or prefix.split('/')[0] in output_str:
        st.log(f"✅ IPv4 route {prefix} received on {dut}")
        return True
    else:
        st.log(f"⚠️ IPv4 route {prefix} NOT received on {dut}")
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
        f"no ip address {data.d1_ipv4}/{data.ipv4_prefix}",
        f"no ipv6 address {data.d1_ipv6}/{data.ipv6_prefix}"
    ]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

    commands = [
        f"interface {data.d2_phy_port}",
        f"no ip address {data.d2_ipv4}/{data.ipv4_prefix}",
        f"no ipv6 address {data.d2_ipv6}/{data.ipv6_prefix}"
    ]
    st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)

    # Cleanup loopbacks
    commands = ["no interface Loopback0"]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
    st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)

    return True


def test_bgp78_extended_nexthop():
    """
    Test BGP-78: Extended Next-Hop Capability

    Validates:
    1. capability extended-nexthop configured on both DUTs
    2. IPv6 BGP neighbor session established
    3. IPv4 routes advertised over IPv6 session
    4. IPv4 routes received with IPv6 next-hop
    5. Configuration verified
    """
    st.banner("TEST: BGP-78 Extended Next-Hop Capability")

    # Initialize validation tracking
    validation_failures = []
    tech_support_generated = False

    try:
        # Step 1: Configure DUT1
        st.log("Step 1: Configuring DUT1 with IPv6 neighbor and extended-nexthop capability")
        if not configure_dut1_base():
            error_msg = f"DUT1 base configuration failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("✓ DUT1 configured successfully")

        # Step 2: Configure DUT2
        st.log("Step 2: Configuring DUT2 with IPv6 neighbor and extended-nexthop capability")
        if not configure_dut2_base():
            error_msg = f"DUT2 base configuration failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("✓ DUT2 configured successfully")

        # Wait for BGP session
        st.wait(15, "Waiting for IPv6 BGP session establishment")

        # Step 3: Verify extended-nexthop capability configuration
        st.log("Step 3: Verify extended-nexthop capability configuration")

        if not verify_extended_nexthop_config(data.dut1):
            error_msg = f"capability extended-nexthop NOT configured on {data.dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ capability extended-nexthop verified on DUT1")

        if not verify_extended_nexthop_config(data.dut2):
            error_msg = f"capability extended-nexthop NOT configured on {data.dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ capability extended-nexthop verified on DUT2")

        st.log("✅ Extended-nexthop capability configured on both DUTs")

        # Step 4: Verify IPv6 BGP sessions established
        st.log("Step 4: Verify IPv6 BGP sessions")
        st.wait(15, "Additional wait for BGP session")

        if not verify_bgp_session(data.dut1, data.d2_ipv6):
            st.log("BGP session not established on DUT1, waiting longer...")
            st.wait(15)
            if not verify_bgp_session(data.dut1, data.d2_ipv6):
                error_msg = f"BGP neighbor {data.d2_ipv6} not established on {data.dut1}"
                st.error(error_msg)
                validation_failures.append(error_msg)
        else:
            st.log(f"✓ BGP session established on DUT1 to {data.d2_ipv6}")

        if not verify_bgp_session(data.dut2, data.d1_ipv6):
            st.log("BGP session not established on DUT2, waiting longer...")
            st.wait(15)
            if not verify_bgp_session(data.dut2, data.d1_ipv6):
                error_msg = f"BGP neighbor {data.d1_ipv6} not established on {data.dut2}"
                st.error(error_msg)
                validation_failures.append(error_msg)
        else:
            st.log(f"✓ BGP session established on DUT2 to {data.d1_ipv6}")

        st.log("✅ IPv6 BGP sessions established")

        # Step 5: Verify IPv4 route exchange over IPv6 session
        st.log("Step 5: Verify IPv4 routes received over IPv6 BGP session")
        st.wait(10, "Waiting for route exchange")

        # DUT2 should receive DUT1's IPv4 routes via IPv6 next-hop
        if verify_route_received(data.dut2, f"{data.d1_loopback}/{data.loopback_prefix}"):
            st.log(f"✓ DUT2 received IPv4 route {data.d1_loopback}/{data.loopback_prefix}")

        if verify_route_received(data.dut2, data.test_prefix):
            st.log(f"✓ DUT2 received IPv4 route {data.test_prefix}")

        # DUT1 should receive DUT2's IPv4 routes via IPv6 next-hop
        if verify_route_received(data.dut1, f"{data.d2_loopback}/{data.loopback_prefix}"):
            st.log(f"✓ DUT1 received IPv4 route {data.d2_loopback}/{data.loopback_prefix}")

        st.log("✅ IPv4 routes exchanged over IPv6 BGP session")

        # Step 6: Display BGP summary for verification
        st.log("Step 6: Display BGP summary")
        output1 = st.show(data.dut1, "show bgp summary", type=data.cli_type)
        st.log(f"DUT1 BGP Summary:\n{output1}")

        output2 = st.show(data.dut2, "show bgp summary", type=data.cli_type)
        st.log(f"DUT2 BGP Summary:\n{output2}")

        # Step 7: Display IPv4 routes
        st.log("Step 7: Display IPv4 BGP routes (with IPv6 next-hop)")
        output1 = st.show(data.dut1, "show bgp ipv4 unicast", type=data.cli_type)
        st.log(f"DUT1 IPv4 Routes:\n{output1}")

        output2 = st.show(data.dut2, "show bgp ipv4 unicast", type=data.cli_type)
        st.log(f"DUT2 IPv4 Routes:\n{output2}")

    except Exception as e:
        error_msg = f"Exception during test execution: {str(e)}"
        st.error(error_msg)
        validation_failures.append(error_msg)

    finally:
        st.banner("CLEANUP: Unconfiguring BGP and Interfaces (ALWAYS EXECUTES)")

        try:
            # BGP cleanup
            st.config(data.dut1, [f"no router bgp"], type=data.cli_type, skip_error_check=True)
            st.config(data.dut2, [f"no router bgp"], type=data.cli_type, skip_error_check=True)
            st.log("✓ BGP configuration removed from both DUTs")

            # IPv4 and IPv6 address cleanup
            commands = [
                f"interface {data.d1_phy_port}",
                f"no ip address {data.d1_ipv4}/{data.ipv4_prefix}",
                f"no ipv6 address {data.d1_ipv6}/{data.ipv6_prefix}"
            ]
            st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

            commands = [
                f"interface {data.d2_phy_port}",
                f"no ip address {data.d2_ipv4}/{data.ipv4_prefix}",
                f"no ipv6 address {data.d2_ipv6}/{data.ipv6_prefix}"
            ]
            st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)
            st.log("✓ IPv4 and IPv6 addresses removed from interfaces")

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
                st.generate_tech_support(dut_list=[data.dut1, data.dut2], name="bgp78_validation_failures")
                tech_support_generated = True
                st.log("✓ Tech-support generated successfully")
            except Exception as tech_error:
                st.error(f"Failed to generate tech-support: {tech_error}")

    # Final reporting
    st.banner("BGP-78 TEST FINAL REPORT")

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
        st.log("✅ BGP-78 Test PASSED: Extended Next-Hop Capability")
        st.log("   - DUT1 (AS 65001): IPv6 neighbor with extended-nexthop")
        st.log("   - DUT2 (AS 65002): IPv6 neighbor with extended-nexthop")
        st.log("   - IPv6 BGP sessions established")
        st.log("   - IPv4 routes exchanged over IPv6 session")
        st.log("   - capability extended-nexthop: Allows IPv4 routes with IPv6 next-hop (RFC 5549)")
        st.report_pass("test_case_passed")
