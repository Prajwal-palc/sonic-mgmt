"""
SM_ISCLI_11: BGP Graceful Restart Config Commands

Test Case ID: SM_ISCLI_11
Bug: BGP Graceful Restart commands missing/working
Priority: P2

Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/hp_test/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_SNMP/test_sm_iscli_11_bgp_graceful_restart.py \
    --logs-path ./logs/sm_iscli_11_$(date +%Y%m%d_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates BGP Graceful Restart configuration commands in IS-CLI.

  Expected Behavior:
  - graceful-restart commands should be accepted
  - Configuration should appear in running-config
  - BGP session should establish with GR capability

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Testbed: testbed_2vs.yaml
  - Credentials: admin/test@123

Note:
  - IMPORTANT: Uses validation_failures tracking to ensure cleanup always runs
  - Tech-support generated automatically on any validation failure
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
    "asn": "65001",
    "interface": "Ethernet0",
    "subnet_mask": "24",
    
    "dut1_ip": "10.0.0.1",
    "dut1_router_id": "1.1.1.1",
    "dut1_loopback_ip": "1.1.1.1/32",
    
    "dut2_ip": "10.0.0.2",
    "dut2_router_id": "2.2.2.2",
    "dut2_loopback_ip": "2.2.2.2/32",
    
    "gr_restart_time": "120",
    "gr_stalepath_time": "360",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("SM_ISCLI_11: MODULE PROLOGUE - BGP Graceful Restart Test")

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"

    yield

    st.banner("SM_ISCLI_11: MODULE EPILOGUE - Cleanup")
    cleanup_all(vars.D1)
    cleanup_all(vars.D2)


def configure_interface(dut: str, ip_address: str) -> bool:
    """Configure interface with IP."""
    try:
        st.log(f"Configuring {CONFIG.interface} on {dut}")
        
        ipapi.config_ip_addr_interface(dut, CONFIG.interface, ip_address,
                                       subnet=CONFIG.subnet_mask, family="ipv4", cli_type=data.cli_type)
        
        commands = [f"interface {CONFIG.interface}", "no shutdown", "exit"]
        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True
    except Exception as e:
        st.error(f"Interface config failed on {dut}: {e}")
        return False


def configure_loopback(dut: str, loopback_ip: str) -> bool:
    """Configure loopback interface."""
    try:
        commands = [
            "interface Loopback0",
            f"ip address {loopback_ip}",
            "exit"
        ]
        st.config(dut, commands, type=data.cli_type)
        return True
    except Exception as e:
        st.error(f"Loopback config failed on {dut}: {e}")
        return False


def configure_bgp_with_gr(dut: str, router_id: str, neighbor_ip: str) -> bool:
    """Configure BGP with Graceful Restart."""
    try:
        st.log(f"Configuring BGP with GR on {dut}")
        
        commands = [
            f"router bgp {CONFIG.asn}",
            f"router-id {router_id}",
            f"neighbor {neighbor_ip} remote-as {CONFIG.asn}",
            
            # Graceful Restart commands - may be entered at neighbor or router level
            f"graceful-restart restart-time {CONFIG.gr_restart_time}",
            f"graceful-restart stalepath-time {CONFIG.gr_stalepath_time}",
            
            "address-family ipv4 unicast",
            f"neighbor {neighbor_ip} activate",
            "exit-address-family",
            "exit"
        ]
        
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)
        return True
    except Exception as e:
        st.error(f"BGP GR config failed on {dut}: {e}")
        return False


def verify_gr_config(dut: str) -> bool:
    """Verify Graceful Restart in configuration."""
    try:
        output = st.show(dut, "show running-configuration bgp", type=data.cli_type)
        output_str = str(output)
        
        checks_passed = 0
        if "graceful-restart restart-time" in output_str:
            st.log("✅ GR restart-time found")
            checks_passed += 1
        if "graceful-restart stalepath-time" in output_str:
            st.log("✅ GR stalepath-time found")
            checks_passed += 1
            
        return checks_passed == 2
    except Exception as e:
        st.error(f"GR verification failed on {dut}: {e}")
        return False


def cleanup_all(dut: str) -> None:
    """Cleanup all configuration."""
    try:
        commands = [f"no router bgp {CONFIG.asn}"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        
        ipapi.delete_ip_interface(dut, CONFIG.interface, 
                                  f"{CONFIG.dut1_ip if dut == vars.D1 else CONFIG.dut2_ip}/{CONFIG.subnet_mask}",
                                  family="ipv4", cli_type=data.cli_type, skip_error=True)
        
        commands = ["no interface Loopback0"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"Cleanup on {dut}: {e}")


def test_sm_iscli_11_bgp_graceful_restart():
    """
    SM_ISCLI_11: Test BGP Graceful Restart configuration.

    Test Steps:
    1. Configure interfaces and loopbacks
    2. Configure BGP with Graceful Restart
    3. Verify GR appears in running-config
    4. Cleanup

    IMPORTANT: Uses validation_failures tracking for cleanup and tech-support.
    """
    st.banner("TEST: SM_ISCLI_11 - BGP Graceful Restart")

    validation_failures = []
    tech_support_generated = False

    try:
        # Step 1: Configure interfaces
        st.log("STEP 1: Configure interfaces")
        if not configure_interface(vars.D1, CONFIG.dut1_ip):
            validation_failures.append(f"Interface config failed on {vars.D1}")
        if not configure_interface(vars.D2, CONFIG.dut2_ip):
            validation_failures.append(f"Interface config failed on {vars.D2}")

        # Step 2: Configure loopbacks
        st.log("STEP 2: Configure loopbacks")
        if not configure_loopback(vars.D1, CONFIG.dut1_loopback_ip):
            validation_failures.append(f"Loopback config failed on {vars.D1}")
        if not configure_loopback(vars.D2, CONFIG.dut2_loopback_ip):
            validation_failures.append(f"Loopback config failed on {vars.D2}")

        # Step 3: Configure BGP with GR
        st.log("STEP 3: Configure BGP with Graceful Restart")
        if not configure_bgp_with_gr(vars.D1, CONFIG.dut1_router_id, CONFIG.dut2_ip):
            validation_failures.append(f"BGP GR config failed on {vars.D1}")
        if not configure_bgp_with_gr(vars.D2, CONFIG.dut2_router_id, CONFIG.dut1_ip):
            validation_failures.append(f"BGP GR config failed on {vars.D2}")

        # Step 4: Verify GR configuration
        st.log("STEP 4: Verify Graceful Restart configuration")
        st.wait(5)
        if not verify_gr_config(vars.D1):
            validation_failures.append(f"GR verification failed on {vars.D1}")
        if not verify_gr_config(vars.D2):
            validation_failures.append(f"GR verification failed on {vars.D2}")

        st.log("✅ SM_ISCLI_11 Test execution completed")

    except Exception as e:
        validation_failures.append(f"Exception: {str(e)}")

    finally:
        # CLEANUP
        st.banner("=" * 80)
        st.banner("CLEANUP (ALWAYS EXECUTES)")
        st.banner("=" * 80)

        try:
            cleanup_all(vars.D1)
            cleanup_all(vars.D2)
            st.log("✓ Cleanup completed")
        except Exception as cleanup_error:
            validation_failures.append(f"Cleanup error: {str(cleanup_error)}")

        # Generate tech-support if failures
        if validation_failures and not tech_support_generated:
            st.banner("GENERATING TECH-SUPPORT")
            try:
                st.generate_tech_support([vars.D1, vars.D2], "sm_iscli_11_failures")
                tech_support_generated = True
            except Exception as ts_error:
                st.error(f"Tech-support generation failed: {str(ts_error)}")

        # Report results
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES:")
            for idx, failure in enumerate(validation_failures, 1):
                st.error(f"{idx}. {failure}")
            st.log("!" * 80)
            st.report_fail("msg", f"Test completed with {len(validation_failures)} validation failure(s)")
        else:
            st.log("✅ SM_ISCLI_11 Test PASSED: BGP Graceful Restart configured successfully")
            st.report_pass("test_case_passed")
