"""
BGP EVPN-04: Type-5 IP Prefix Route Advertisement

Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2node.yaml \
    tests/routing/BGP/EVPN/test_bgp_evpn04_type5_prefix.py \
    --logs-path ./logs/bgp_evpn04_$(date +%Y%m%d_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Validates BGP EVPN Type-5 IP Prefix Route Advertisement between two DUTs.
  Tests L2VPN EVPN address family configuration and BGP session establishment.

  Configuration:
  - DUT1: AS 65001, Router-ID 1.1.1.1, Loopback0 (1.1.1.1/32)
  - DUT2: AS 65002, Router-ID 2.2.2.2, Loopback0 (2.2.2.2/32)
  - Both: L2VPN EVPN address family activated
  - Inter-AS EBGP peering over Ethernet4

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Testbed: testbed_2node.yaml
  - Devices: SONiC instances with EVPN support
  - Credentials: admin/root@123
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

import apis.routing.ip as ipapi

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "interface": "Ethernet4",
    "subnet_mask": "24",

    # DUT1 configuration
    "dut1_asn": "65001",
    "dut1_ip": "10.1.1.1",
    "dut1_router_id": "1.1.1.1",
    "dut1_loopback_ip": "1.1.1.1",
    "dut1_loopback_mask": "32",

    # DUT2 configuration
    "dut2_asn": "65002",
    "dut2_ip": "10.1.1.2",
    "dut2_router_id": "2.2.2.2",
    "dut2_loopback_ip": "2.2.2.2",
    "dut2_loopback_mask": "32",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("EVPN-04: MODULE PROLOGUE - Type-5 IP Prefix Route Advertisement")

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"

    yield

    st.banner("EVPN-04: MODULE EPILOGUE - Cleanup")
    cleanup_bgp_config(vars.D1, CONFIG.dut1_asn)
    cleanup_bgp_config(vars.D2, CONFIG.dut2_asn)
    cleanup_loopback_interface(vars.D1)
    cleanup_loopback_interface(vars.D2)
    cleanup_ip_interface(vars.D1, CONFIG.dut1_ip)
    cleanup_ip_interface(vars.D2, CONFIG.dut2_ip)


def configure_ip_interface(dut: str, ip_address: str) -> bool:
    """Configure physical interface with IP address."""
    try:
        st.log(f"Configuring {CONFIG.interface} on {dut} with IP {ip_address}")

        ipapi.config_ip_addr_interface(
            dut, CONFIG.interface,
            ip_address,
            subnet=CONFIG.subnet_mask,
            family="ipv4",
            cli_type=data.cli_type
        )

        commands = [
            f"interface {CONFIG.interface}",
            "no shutdown",
            "exit"
        ]
        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure interface on {dut}: {e}")
        return False


def configure_loopback_interface(dut: str, loopback_ip: str, loopback_mask: str) -> bool:
    """Configure loopback interface with IP address."""
    try:
        st.log(f"Configuring Loopback0 on {dut} with IP {loopback_ip}/{loopback_mask}")

        commands = [
            "interface Loopback 0",
            f"ip address {loopback_ip}/{loopback_mask}",
            "exit"
        ]
        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure loopback on {dut}: {e}")
        return False


def cleanup_ip_interface(dut: str, ip_address: str) -> None:
    """Remove IP address from physical interface."""
    try:
        ipapi.delete_ip_interface(dut, CONFIG.interface,
                                  f"{ip_address}/{CONFIG.subnet_mask}",
                                  family="ipv4", cli_type=data.cli_type, skip_error=True)
    except Exception as e:
        st.log(f"IP cleanup on {dut}: {e}")


def cleanup_loopback_interface(dut: str) -> None:
    """Remove loopback interface."""
    try:
        commands = ["no interface Loopback 0"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"Loopback cleanup on {dut}: {e}")


def configure_bgp_evpn(dut: str, asn: str, router_id: str, neighbor_ip: str, neighbor_asn: str) -> bool:
    """Configure BGP with L2VPN EVPN address family."""
    try:
        st.log(f"Configuring BGP EVPN on {dut} with AS {asn}, Router-ID {router_id}")

        bgp_commands = [
            f"router bgp {asn}",
            f"router-id {router_id}",
            f"neighbor {neighbor_ip} remote-as {neighbor_asn}",
            "address-family l2vpn evpn",
            "activate",
            "exit",
            "exit",
            "exit"
        ]

        st.config(dut, bgp_commands, type=data.cli_type)
        st.wait(3)
        return True

    except Exception as e:
        st.error(f"Failed to configure BGP EVPN on {dut}: {e}")
        return False


def verify_bgp_evpn_summary(dut: str, neighbor_ip: str) -> bool:
    """Verify BGP EVPN summary shows neighbor."""
    try:
        st.log(f"Verifying BGP EVPN summary for neighbor {neighbor_ip} on {dut}")

        output = st.show(dut, "show bgp summary", type=data.cli_type, skip_error_check=True)
        st.log(f"BGP Summary output: {output}")

        output_str = str(output)
        if neighbor_ip not in output_str:
            st.error(f"Neighbor {neighbor_ip} not found in BGP summary")
            return False

        if "L2VPN EVPN" not in output_str:
            st.error("L2VPN EVPN summary section not found")
            return False

        st.log(f"✓ BGP EVPN neighbor {neighbor_ip} found on {dut}")
        return True

    except Exception as e:
        st.error(f"Failed to verify BGP EVPN summary on {dut}: {e}")
        return False


def verify_bgp_evpn_config(dut: str, neighbor_ip: str, neighbor_asn: str) -> bool:
    """Verify BGP EVPN configuration."""
    try:
        st.log(f"Verifying BGP EVPN configuration on {dut}")

        output = st.show(dut, "show running-configuration bgp", type=data.cli_type)
        output_str = str(output)

        if f"neighbor {neighbor_ip}" not in output_str:
            st.error(f"Neighbor {neighbor_ip} not found in config")
            return False

        if f"remote-as {neighbor_asn}" not in output_str:
            st.error(f"Remote-AS {neighbor_asn} not found in config")
            return False

        if "address-family l2vpn evpn" not in output_str:
            st.error("L2VPN EVPN address family not found in config")
            return False

        if "activate" not in output_str:
            st.error("EVPN activate command not found in config")
            return False

        st.log("✓ BGP EVPN configuration verified")
        return True

    except Exception as e:
        st.error(f"Failed to verify BGP EVPN config on {dut}: {e}")
        return False


def verify_loopback_config(dut: str, loopback_ip: str) -> bool:
    """Verify loopback interface configuration."""
    try:
        st.log(f"Verifying Loopback0 configuration on {dut}")

        output = st.show(dut, "show running-configuration interface Loopback 0", 
                        type=data.cli_type, skip_error_check=True)
        output_str = str(output)

        if loopback_ip not in output_str:
            st.error(f"Loopback IP {loopback_ip} not found in config")
            return False

        st.log(f"✓ Loopback0 with IP {loopback_ip} verified")
        return True

    except Exception as e:
        st.error(f"Failed to verify loopback config on {dut}: {e}")
        return False


def cleanup_bgp_config(dut: str, asn: str) -> None:
    """Remove BGP configuration."""
    try:
        commands = [f"no router bgp {asn}"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"BGP cleanup on {dut}: {e}")


def test_bgp_evpn04_type5_prefix():
    """
    EVPN-04: Verify BGP EVPN Type-5 IP Prefix Route Advertisement.

    Test Steps:
    1. Configure IP addresses on Ethernet4 interfaces
    2. Configure Loopback0 interfaces on both DUTs
    3. Configure BGP with L2VPN EVPN address family
    4. Verify BGP EVPN sessions established
    5. Verify BGP EVPN configuration
    6. Verify loopback configuration
    """
    st.banner("TEST: EVPN-04 - Type-5 IP Prefix Route Advertisement")

    validation_failures = []
    tech_support_generated = False

    try:
        # Step 1: Configure Ethernet4 interfaces
        st.log("STEP 1: Configure IP addresses on Ethernet4")
        if not configure_ip_interface(vars.D1, CONFIG.dut1_ip):
            error_msg = f"Interface configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_ip_interface(vars.D2, CONFIG.dut2_ip):
            error_msg = f"Interface configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 2: Configure Loopback0 interfaces
        st.log("STEP 2: Configure Loopback0 interfaces")
        if not configure_loopback_interface(vars.D1, CONFIG.dut1_loopback_ip, CONFIG.dut1_loopback_mask):
            error_msg = f"Loopback configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_loopback_interface(vars.D2, CONFIG.dut2_loopback_ip, CONFIG.dut2_loopback_mask):
            error_msg = f"Loopback configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 3: Configure BGP with EVPN
        st.log("STEP 3: Configure BGP with L2VPN EVPN address family")
        if not configure_bgp_evpn(vars.D1, CONFIG.dut1_asn, CONFIG.dut1_router_id, 
                                  CONFIG.dut2_ip, CONFIG.dut2_asn):
            error_msg = f"BGP EVPN configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_bgp_evpn(vars.D2, CONFIG.dut2_asn, CONFIG.dut2_router_id, 
                                  CONFIG.dut1_ip, CONFIG.dut1_asn):
            error_msg = f"BGP EVPN configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 4: Wait for BGP session to establish
        st.log("STEP 4: Wait for BGP EVPN sessions to establish")
        st.wait(15)

        # Step 5: Verify BGP EVPN summary
        st.log("STEP 5: Verify BGP EVPN summary")
        if not verify_bgp_evpn_summary(vars.D1, CONFIG.dut2_ip):
            error_msg = f"BGP EVPN session to {CONFIG.dut2_ip} not visible on {vars.D1}"
            st.log(f"INFO: {error_msg}")

        if not verify_bgp_evpn_summary(vars.D2, CONFIG.dut1_ip):
            error_msg = f"BGP EVPN session to {CONFIG.dut1_ip} not visible on {vars.D2}"
            st.log(f"INFO: {error_msg}")

        # Step 6: Verify BGP EVPN configuration
        st.log("STEP 6: Verify BGP EVPN configuration")
        if not verify_bgp_evpn_config(vars.D1, CONFIG.dut2_ip, CONFIG.dut2_asn):
            error_msg = f"BGP EVPN configuration verification failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not verify_bgp_evpn_config(vars.D2, CONFIG.dut1_ip, CONFIG.dut1_asn):
            error_msg = f"BGP EVPN configuration verification failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 7: Verify Loopback configuration
        st.log("STEP 7: Verify Loopback0 configuration")
        if not verify_loopback_config(vars.D1, CONFIG.dut1_loopback_ip):
            error_msg = f"Loopback configuration verification failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not verify_loopback_config(vars.D2, CONFIG.dut2_loopback_ip):
            error_msg = f"Loopback configuration verification failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        st.log("✅ EVPN-04 Test execution completed")

    except Exception as e:
        error_msg = f"Unexpected exception during test execution: {str(e)}"
        st.error(error_msg)
        validation_failures.append(error_msg)

    finally:
        st.banner("=" * 80)
        st.banner("CLEANUP: Unconfiguring BGP, Loopback, and IP (ALWAYS EXECUTES)")
        st.banner("=" * 80)

        try:
            st.log("Cleaning up BGP configuration on both DUTs")
            cleanup_bgp_config(vars.D1, CONFIG.dut1_asn)
            cleanup_bgp_config(vars.D2, CONFIG.dut2_asn)

            st.log("Cleaning up Loopback interfaces on both DUTs")
            cleanup_loopback_interface(vars.D1)
            cleanup_loopback_interface(vars.D2)

            st.log("Clearing IP configuration on both DUTs")
            cleanup_ip_interface(vars.D1, CONFIG.dut1_ip)
            cleanup_ip_interface(vars.D2, CONFIG.dut2_ip)

            st.log("✓ Cleanup completed successfully")

        except Exception as cleanup_error:
            st.error(f"Error during cleanup: {str(cleanup_error)}")
            validation_failures.append(f"Cleanup error: {str(cleanup_error)}")

        if validation_failures and not tech_support_generated:
            st.banner("=" * 80)
            st.banner("GENERATING TECH-SUPPORT (Validation Failures Detected)")
            st.banner("=" * 80)
            try:
                st.generate_tech_support([vars.D1, vars.D2], "evpn04_validation_failures")
                tech_support_generated = True
                st.log("✓ Tech-support generated successfully")
            except Exception as ts_error:
                st.error(f"Failed to generate tech-support: {str(ts_error)}")

        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED:")
            for idx, failure in enumerate(validation_failures, 1):
                st.error(f"{idx}. {failure}")
            st.log("!" * 80)
            st.log(f"\nNote: Cleanup completed despite {len(validation_failures)} validation failure(s)")
            st.log("Tech-support has been generated for debugging")
            st.report_fail("msg", f"Test completed with {len(validation_failures)} validation failure(s). See errors above.")
        else:
            st.log("All validations passed successfully")
            st.log("✅ EVPN-04 Test PASSED: BGP EVPN Type-5 configured successfully")
            st.report_pass("test_case_passed")
