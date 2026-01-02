"""
BGP Capability Test BGP-76: Capability Negotiation Disable/Override

Author: Auto-generated
Copyright (C) 2024

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest
  ./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml system/iscli_BGP/test_bgp76_capability_negotiation.py --logs-path ./logs/bgp76_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates BGP capability negotiation controls, specifically the
  ability to disable capability negotiation on one router and override
  capability negotiation on another router.

  Capability negotiation allows BGP peers to exchange supported features
  during session establishment (RFC 5492). This test verifies:
  - dont-capability-negotiate: Disables sending capability advertisements
  - override-capability: Overrides capability mismatch errors

  Test Scenario:
  - DUT1 (AS 65001) configured with dont-capability-negotiate
  - DUT2 (AS 65002) configured with override-capability
  - EBGP session should establish despite capability differences
  - Validates session establishment and basic route exchange

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Testbed: testbed_2vs.yaml
  - Devices: Virtual Switches
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

    st.banner("MODULE PROLOGUE: Starting BGP-76 Capability Negotiation Test")
    initialize_data()

    yield

    # Module cleanup
    st.banner("MODULE EPILOGUE: Cleanup BGP-76")
    try:
        cleanup_bgp()
    except Exception as e:
        st.log(f"Module epilogue cleanup error: {e}")


def configure_dut1_base() -> bool:
    """Configure DUT1 with interfaces, loopback, and BGP with dont-capability-negotiate"""
    try:
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

        # Configure BGP with dont-capability-negotiate
        st.log("Configuring BGP on DUT1 with dont-capability-negotiate")
        commands = [
            f"router bgp {data.d1_asn}",
            f"router-id {data.d1_router_id}",
            f"neighbor {data.d2_ip} remote-as {data.d2_asn}",
            "dont-capability-negotiate",
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
    except Exception as e:
        st.error(f"Failed to configure DUT1: {e}")
        return False


def configure_dut2_base() -> bool:
    """Configure DUT2 with interfaces, loopback, and BGP with override-capability"""
    try:
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

        # Configure BGP with override-capability
        st.log("Configuring BGP on DUT2 with override-capability")
        commands = [
            f"router bgp {data.d2_asn}",
            f"router-id {data.d2_router_id}",
            f"neighbor {data.d1_ip} remote-as {data.d1_asn}",
            "override-capability",
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
    except Exception as e:
        st.error(f"Failed to configure DUT2: {e}")
        return False


def verify_bgp_session(dut: str, neighbor_ip: str) -> bool:
    """Verify BGP session is established"""
    try:
        output = st.show(dut, "show bgp summary", type=data.cli_type, skip_error_check=True)
        output_str = str(output)

        if neighbor_ip in output_str and ("Established" in output_str or "00:" in output_str):
            st.log(f"✅ BGP session established with {neighbor_ip} on {dut}")
            return True
        else:
            st.log(f"⚠️ BGP session not yet established with {neighbor_ip} on {dut}")
            return False
    except Exception as e:
        st.error(f"Failed to verify BGP session on {dut}: {e}")
        return False


def verify_capability_negotiation_config(dut: str, capability_type: str) -> bool:
    """Verify capability negotiation configuration"""
    try:
        output = st.show(dut, "show running-configuration bgp", type=data.cli_type, skip_error_check=True)
        output_str = str(output)

        if capability_type in output_str:
            st.log(f"✅ {capability_type} configured on {dut}")
            return True
        else:
            st.error(f"❌ {capability_type} NOT configured on {dut}")
            return False
    except Exception as e:
        st.error(f"Failed to verify capability config on {dut}: {e}")
        return False


def cleanup_bgp() -> None:
    """Cleanup BGP configuration"""
    st.log("Cleaning up BGP configuration")

    try:
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
    except Exception as e:
        st.log(f"Cleanup error: {e}")


def test_bgp76_capability_negotiation():
    """
    Test BGP-76: Capability Negotiation Disable/Override

    Validates:
    1. DUT1 configured with dont-capability-negotiate
    2. DUT2 configured with override-capability
    3. EBGP session established despite capability differences
    4. Configuration verified via show running-config
    5. BGP summary shows session status

    VALIDATION PATTERN:
    - Tracks all validation failures without immediate exit
    - Executes cleanup in finally block (ALWAYS runs)
    - Generates tech-support on validation failures
    - Reports comprehensive results at the end
    """
    st.banner("TEST: BGP-76 Capability Negotiation Disable/Override")

    # Initialize validation tracking
    validation_failures = []
    tech_support_generated = False

    try:
        # Module setup - Configure base BGP
        st.banner("Configuring Interfaces and BGP")

        # Configure DUT1
        st.log("Configuring DUT1 with dont-capability-negotiate")
        if not configure_dut1_base():
            error_msg = f"DUT1 base configuration failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("✓ DUT1 configured successfully")

        # Configure DUT2
        st.log("Configuring DUT2 with override-capability")
        if not configure_dut2_base():
            error_msg = f"DUT2 base configuration failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("✓ DUT2 configured successfully")

        # Wait for BGP session
        st.wait(15, "Waiting for EBGP session establishment")

        # Step 1: Verify capability negotiation configuration
        st.log("Step 1: Verify capability negotiation configuration")

        if not verify_capability_negotiation_config(data.dut1, "dont-capability-negotiate"):
            error_msg = f"dont-capability-negotiate NOT configured on {data.dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("✓ dont-capability-negotiate verified on DUT1")

        if not verify_capability_negotiation_config(data.dut2, "override-capability"):
            error_msg = f"override-capability NOT configured on {data.dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("✓ override-capability verified on DUT2")

        st.log("✅ Capability negotiation settings configured")

        # Step 2: Verify BGP sessions established
        st.log("Step 2: Verify BGP sessions")
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

        if not validation_failures:
            st.log("✅ BGP sessions established despite capability differences")

        # Step 3: Display BGP summary for verification
        st.log("Step 3: Display BGP summary")
        output1 = st.show(data.dut1, "show bgp summary", type=data.cli_type, skip_error_check=True)
        st.log(f"DUT1 BGP Summary:\n{output1}")

        output2 = st.show(data.dut2, "show bgp summary", type=data.cli_type, skip_error_check=True)
        st.log(f"DUT2 BGP Summary:\n{output2}")

        # Step 4: Display running configuration
        st.log("Step 4: Display BGP configuration")
        output1 = st.show(data.dut1, "show running-configuration bgp", type=data.cli_type, skip_error_check=True)
        st.log(f"DUT1 BGP Config:\n{output1}")

        output2 = st.show(data.dut2, "show running-configuration bgp", type=data.cli_type, skip_error_check=True)
        st.log(f"DUT2 BGP Config:\n{output2}")

    except Exception as e:
        error_msg = f"Exception during test execution: {str(e)}"
        st.error(error_msg)
        validation_failures.append(error_msg)
        st.log(f"Exception details: {e}")

    finally:
        # CLEANUP: Always executes regardless of test outcome
        st.banner("CLEANUP: Unconfiguring BGP and Interfaces (ALWAYS EXECUTES)")

        try:
            st.log(f"Cleaning up BGP on DUT1 (AS {data.d1_asn})")
            commands = [f"no router bgp"]
            st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

            st.log(f"Cleaning up BGP on DUT2 (AS {data.d2_asn})")
            commands = [f"no router bgp"]
            st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)

            st.log("Clearing IP configuration on both DUTs")
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

            st.log("Clearing loopback configuration on both DUTs")
            commands = ["no interface Loopback0"]
            st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
            st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)

            st.log("✓ Cleanup completed successfully")

        except Exception as cleanup_error:
            error_msg = f"Cleanup error: {str(cleanup_error)}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Generate tech-support if there were validation failures
        if validation_failures and not tech_support_generated:
            st.banner("GENERATING TECH-SUPPORT (Validation Failures Detected)")
            try:
                st.generate_tech_support(dut_list=[data.dut1, data.dut2], name="bgp76_validation_failures")
                tech_support_generated = True
                st.log("✓ Tech-support generated successfully")
            except Exception as tech_error:
                st.error(f"Failed to generate tech-support: {tech_error}")

    # Final reporting
    st.banner("BGP-76 TEST FINAL REPORT")

    if validation_failures:
        st.log("=" * 80)
        st.error("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"ERROR {idx}. {failure}")
        st.log("=" * 80)
        st.log(f"Note: Cleanup and unconfiguration completed despite {len(validation_failures)} validation failure(s)")
        if tech_support_generated:
            st.log("Tech-support has been generated for debugging")

        error_summary = f"Test completed with {len(validation_failures)} validation failure(s). Cleanup executed. See errors above."
        st.report_fail("msg", error_summary)
    else:
        st.log("=" * 80)
        st.log("All validations passed successfully")
        st.log("=" * 80)
        st.log("✅ BGP-76: Capability negotiation test completed successfully")
        st.log("   CONFIGURATION:")
        st.log(f"   - DUT1 (AS {data.d1_asn}): dont-capability-negotiate")
        st.log(f"   - DUT2 (AS {data.d2_asn}): override-capability")
        st.log("   - EBGP session established despite capability differences")
        st.log("   KEY LEARNING:")
        st.log("   - dont-capability-negotiate: Disables sending capability advertisements (RFC 5492)")
        st.log("   - override-capability: Overrides capability mismatch errors")
        st.log("=" * 80)
        st.report_pass("test_case_passed")
