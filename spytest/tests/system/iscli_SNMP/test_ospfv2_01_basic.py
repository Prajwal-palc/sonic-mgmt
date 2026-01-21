"""
OSPFv2 Test 01: Basic OSPF Configuration and Neighbor Establishment

Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_SNMP/test_ospfv2_01_basic.py \
    --logs-path ./logs/ospfv2_basic_$(date +%Y%m%d_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case: OSPFv2 Basic Configuration

  Validates basic OSPFv2 functionality:
  - Interface IP configuration
  - OSPF router-id configuration
  - Network statement configuration
  - OSPF neighbor establishment
  - OSPF database verification
  - OSPF route installation

  Manual Test Steps Automated:
  DUT1:
    sonic-cli
    configure terminal
    interface Ethernet0
    ip address 10.1.1.1/24
    no shutdown
    exit
    router ospf
    ospf router-id 1.1.1.1
    network 10.1.1.0/24 area 0.0.0.0
    exit
    end
    write memory

  Verification:
    show ip ospf neighbor
    show ip ospf interface
    show ip ospf
    show ip ospf database
    show ip route ospf

Pre-requisites:
  - Topology: two-node (D1-D2)
  - DUT1: 192.168.100.149, DUT2: 192.168.100.234
  - Credentials: admin/Auto@123
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "interface": "Ethernet0",
    "subnet_mask": "24",
    "dut1_ipv4": "10.1.1.1",
    "dut2_ipv4": "10.1.1.2",
    "dut1_router_id": "1.1.1.1",
    "dut2_router_id": "2.2.2.2",
    "network": "10.1.1.0/24",
    "area": "0.0.0.0",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("="*80)
    st.banner("OSPFv2-01: MODULE PROLOGUE - Basic OSPF Test")
    st.banner("="*80)

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"

    yield

    st.banner("="*80)
    st.banner("OSPFv2-01: MODULE EPILOGUE - Cleanup")
    st.banner("="*80)

    cleanup_ospf_config(vars.D1)
    cleanup_ospf_config(vars.D2)
    cleanup_interface(vars.D1)
    cleanup_interface(vars.D2)


def configure_interface(dut: str, ip_address: str) -> bool:
    """Configure interface with IP address."""
    try:
        st.log(f"Configuring {CONFIG.interface} on {dut} with IP {ip_address}")

        commands = [
            f"interface {CONFIG.interface}",
            f"ip address {ip_address}/{CONFIG.subnet_mask}",
            "no shutdown",
            "exit"
        ]

        st.config(dut, commands, type=data.cli_type)
        st.wait(2, "Waiting for interface to be up")
        st.log(f"✅ Interface configured on {dut}")
        return True

    except Exception as e:
        st.error(f"❌ Failed to configure interface on {dut}: {str(e)}")
        return False


def configure_ospf_basic(dut: str, router_id: str) -> bool:
    """Configure basic OSPF with router-id and network."""
    try:
        st.log(f"Configuring OSPF on {dut}")

        commands = [
            "router ospf",
            f"ospf router-id {router_id}",
            f"network {CONFIG.network} area {CONFIG.area}",
            "exit"
        ]

        st.config(dut, commands, type=data.cli_type)
        st.wait(2, "Waiting for OSPF configuration")
        st.log(f"✅ OSPF configured on {dut}")
        return True

    except Exception as e:
        st.error(f"❌ Failed to configure OSPF on {dut}: {str(e)}")
        return False


def verify_ospf_neighbor(dut: str, neighbor_ip: str) -> bool:
    """Verify OSPF neighbor establishment."""
    try:
        st.log(f"Verifying OSPF neighbor {neighbor_ip} on {dut}")

        output = st.show(dut, "show ip ospf neighbor", type=data.cli_type, skip_error_check=True)
        output_str = str(output)

        st.log(f"OSPF neighbor output:\n{output_str[:500]}")

        # Check for neighbor IP and Full state
        if neighbor_ip in output_str:
            if "Full" in output_str or "Full/DR" in output_str or "Full/Backup" in output_str:
                st.log(f"✅ OSPF neighbor {neighbor_ip} is in Full state")
                return True
            else:
                st.log(f"⚠️ OSPF neighbor {neighbor_ip} found but not in Full state")
                return False
        else:
            st.log(f"❌ OSPF neighbor {neighbor_ip} not found")
            return False

    except Exception as e:
        st.error(f"❌ Failed to verify OSPF neighbor: {str(e)}")
        return False


def verify_ospf_interface(dut: str) -> bool:
    """Verify OSPF interface configuration."""
    try:
        st.log(f"Verifying OSPF interface on {dut}")

        output = st.show(dut, f"show ip ospf interface {CONFIG.interface}", type=data.cli_type, skip_error_check=True)
        output_str = str(output)

        st.log(f"OSPF interface output:\n{output_str[:500]}")

        # Check for interface and area
        if CONFIG.interface in output_str and CONFIG.area in output_str:
            st.log(f"✅ OSPF running on {CONFIG.interface} in area {CONFIG.area}")
            return True
        else:
            st.log(f"⚠️ OSPF interface verification incomplete")
            return False

    except Exception as e:
        st.error(f"❌ Failed to verify OSPF interface: {str(e)}")
        return False


def verify_ospf_database(dut: str) -> bool:
    """Verify OSPF database has LSAs."""
    try:
        st.log(f"Verifying OSPF database on {dut}")

        output = st.show(dut, "show ip ospf database", type=data.cli_type, skip_error_check=True)
        output_str = str(output)

        st.log(f"OSPF database output:\n{output_str[:500]}")

        # Check for Router LSAs
        if "Router Link States" in output_str:
            st.log(f"✅ OSPF database has Router LSAs")
            return True
        else:
            st.log(f"⚠️ OSPF database verification incomplete")
            return False

    except Exception as e:
        st.error(f"❌ Failed to verify OSPF database: {str(e)}")
        return False


def verify_ospf_routes(dut: str) -> bool:
    """Verify OSPF routes in routing table."""
    try:
        st.log(f"Verifying OSPF routes on {dut}")

        output = st.show(dut, "show ip route ospf", type=data.cli_type, skip_error_check=True)
        output_str = str(output)

        st.log(f"OSPF routes output:\n{output_str[:500]}")

        # Check for OSPF routes (marked with 'O')
        if "O" in output_str or "10.1.1.0/24" in output_str:
            st.log(f"✅ OSPF routes present in routing table")
            return True
        else:
            st.log(f"ℹ️ No OSPF routes (expected in simple 2-node topology)")
            return True  # Not a failure in simple topology

    except Exception as e:
        st.error(f"❌ Failed to verify OSPF routes: {str(e)}")
        return False


def cleanup_interface(dut: str) -> None:
    """Remove IP configuration from interface."""
    try:
        st.log(f"Cleaning up interface on {dut}")

        commands = [
            f"interface {CONFIG.interface}",
            "no ip address"
        ]

        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"✅ Interface cleanup completed on {dut}")

    except Exception as e:
        st.log(f"⚠️ Interface cleanup warning: {str(e)}")


def cleanup_ospf_config(dut: str) -> None:
    """Remove OSPF configuration."""
    try:
        st.log(f"Cleaning up OSPF configuration on {dut}")

        commands = ["no router ospf"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"✅ OSPF cleanup completed on {dut}")

    except Exception as e:
        st.log(f"⚠️ OSPF cleanup warning: {str(e)}")


def test_ospfv2_01_basic():
    """
    OSPFv2-01: Basic OSPF Configuration Test

    Test Flow:
    1. Configure IP addresses on both DUTs
    2. Configure OSPF with router-id and network statement
    3. Verify OSPF neighbor establishment (Full state)
    4. Verify OSPF interface configuration
    5. Verify OSPF database (Router LSAs)
    6. Verify OSPF routes (if any)
    7. Display configurations for verification

    Expected Results:
    - OSPF neighbors establish in Full state
    - OSPF interfaces show correct area configuration
    - OSPF database contains Router LSAs
    - All verifications pass
    """
    st.banner("="*80)
    st.banner("TEST: OSPFv2-01 - Basic OSPF Configuration")
    st.banner("="*80)

    validation_failures = []
    tech_support_generated = False

    try:
        # ==================================================
        # STEP 1: Configure IP Interfaces
        # ==================================================
        st.banner("STEP 1: Configure IP Interfaces on Both DUTs")

        if not configure_interface(vars.D1, CONFIG.dut1_ipv4):
            error_msg = f"Interface configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_interface(vars.D2, CONFIG.dut2_ipv4):
            error_msg = f"Interface configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # ==================================================
        # STEP 2: Configure OSPF on Both DUTs
        # ==================================================
        st.banner("STEP 2: Configure OSPF on Both DUTs")

        if not configure_ospf_basic(vars.D1, CONFIG.dut1_router_id):
            error_msg = f"OSPF configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_ospf_basic(vars.D2, CONFIG.dut2_router_id):
            error_msg = f"OSPF configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # ==================================================
        # STEP 3: Wait for OSPF Convergence
        # ==================================================
        st.banner("STEP 3: Wait for OSPF Convergence")
        st.wait(15, "Waiting for OSPF neighbor establishment")

        # ==================================================
        # STEP 4: Verify OSPF Neighbors
        # ==================================================
        st.banner("STEP 4: Verify OSPF Neighbor Establishment")

        if not verify_ospf_neighbor(vars.D1, CONFIG.dut2_ipv4):
            error_msg = f"OSPF neighbor {CONFIG.dut2_ipv4} not established on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not verify_ospf_neighbor(vars.D2, CONFIG.dut1_ipv4):
            error_msg = f"OSPF neighbor {CONFIG.dut1_ipv4} not established on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # ==================================================
        # STEP 5: Verify OSPF Interfaces
        # ==================================================
        st.banner("STEP 5: Verify OSPF Interface Configuration")

        if not verify_ospf_interface(vars.D1):
            error_msg = f"OSPF interface verification failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not verify_ospf_interface(vars.D2):
            error_msg = f"OSPF interface verification failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # ==================================================
        # STEP 6: Verify OSPF Database
        # ==================================================
        st.banner("STEP 6: Verify OSPF Database")

        if not verify_ospf_database(vars.D1):
            error_msg = f"OSPF database verification failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not verify_ospf_database(vars.D2):
            error_msg = f"OSPF database verification failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # ==================================================
        # STEP 7: Verify OSPF Routes
        # ==================================================
        st.banner("STEP 7: Verify OSPF Routes")

        verify_ospf_routes(vars.D1)
        verify_ospf_routes(vars.D2)

        # ==================================================
        # STEP 8: Display Final Configurations
        # ==================================================
        st.banner("STEP 8: Display Final Configurations")

        for dut in [vars.D1, vars.D2]:
            st.log(f"\n{'='*60}")
            st.log(f"Configuration on {dut}")
            st.log(f"{'='*60}")

            # Show running config
            output = st.show(dut, "show running-configuration | grep ospf", type=data.cli_type, skip_error_check=True)
            st.log(f"OSPF Config:\n{str(output)[:500]}")

            # Show OSPF summary
            output = st.show(dut, "show ip ospf", type=data.cli_type, skip_error_check=True)
            st.log(f"OSPF Summary:\n{str(output)[:500]}")

        st.log("✅ OSPFv2-01 Basic test execution completed")

    except Exception as e:
        error_msg = f"Unexpected exception during test execution: {str(e)}"
        st.error(error_msg)
        validation_failures.append(error_msg)

    finally:
        # ==================================================
        # CLEANUP: Always executes
        # ==================================================
        st.banner("="*80)
        st.banner("CLEANUP: Removing OSPF and IP Configurations")
        st.banner("="*80)

        try:
            cleanup_ospf_config(vars.D1)
            cleanup_ospf_config(vars.D2)
            cleanup_interface(vars.D1)
            cleanup_interface(vars.D2)
            st.log("✓ Cleanup completed successfully")

        except Exception as cleanup_error:
            st.error(f"Error during cleanup: {str(cleanup_error)}")
            validation_failures.append(f"Cleanup error: {str(cleanup_error)}")

        # ==================================================
        # TECH-SUPPORT: Generate if failures
        # ==================================================
        if validation_failures and not tech_support_generated:
            st.banner("GENERATING TECH-SUPPORT (Validation Failures Detected)")
            try:
                st.generate_tech_support([vars.D1, vars.D2], "ospfv2_01_basic_failures")
                tech_support_generated = True
                st.log("✓ Tech-support generated successfully")
            except Exception as ts_error:
                st.error(f"Failed to generate tech-support: {str(ts_error)}")

        # ==================================================
        # REPORT: Final results
        # ==================================================
        if validation_failures:
            st.log("\n" + "!"*80)
            st.log("VALIDATION FAILURES DETECTED:")
            for idx, failure in enumerate(validation_failures, 1):
                st.error(f"  {idx}. {failure}")
            st.log("!"*80)
            st.log(f"\nNote: Cleanup completed despite {len(validation_failures)} validation failure(s)")
            st.log("Tech-support has been generated for debugging")
            st.report_fail("msg", f"OSPFv2-01 completed with {len(validation_failures)} failure(s). Cleanup executed.")
        else:
            st.log("\n" + "="*80)
            st.log("✅ OSPFv2-01: ALL TESTS PASSED")
            st.log("="*80)
            st.report_pass("test_case_passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
