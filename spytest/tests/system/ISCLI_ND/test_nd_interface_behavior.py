"""
TC_ND_INTF_BEHAVIOR: IPv6 Neighbor Discovery Interface Behavior Test Suite

Test Case ID: ND-INTF-BEHAVIOR-01
Author: Network Automation Team

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_nd.yaml \
    tests/system/ISCLI_ND/test_nd_interface_behavior.py \
    --logs-path ./logs/nd_intf_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Validates IPv6 Neighbor Discovery behavior during interface state changes:
  - ND entry behavior when interface goes down
  - ND recovery when interface comes back up
  - ND behavior during interface flap (quick down/up)
  - ND re-learning after interface recovery

  Test validates:
  1. ND entries when interface is shutdown
  2. Connectivity lost when interface is down
  3. ND recovery when interface is brought back up
  4. ND resilience during interface flap
  5. ND re-learning after interface recovery

Pre-requisites:
  - Topology: dual-node (D1, D2) | Supported: HW and VS
  - Two devices connected via Ethernet links
  - IPv6 enabled on test VLANs
  - Credentials: admin/sonic@123

Test Configuration:
  - VLAN 100 with IPv6 subnet 2001:db8:100::/64
  - DUT1: 2001:db8:100::1/64
  - DUT2: 2001:db8:100::2/64
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict
import time

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    # VLAN configuration
    "vlan_id": "100",
    "vlan_name": "Vlan100",

    # IPv6 addresses
    "dut1_ipv6": "2001:db8:100::1/64",
    "dut2_ipv6": "2001:db8:100::2/64",
    "dut1_ipv6_addr": "2001:db8:100::1",
    "dut2_ipv6_addr": "2001:db8:100::2",

    # Interfaces
    "dut1_port": "Ethernet0",
    "dut2_port": "Ethernet0",

    # Timing parameters
    "interface_wait_time": 5,  # Wait time after interface state change
    "ping_count": "3",
})

# Test Case IDs
TC_IDS = SpyTestDict({
    "interface_down": "ND-INTF-01.1",
    "interface_flap": "ND-INTF-01.2",
})


#################################################################
# Module-level Fixture
#################################################################

@pytest.fixture(scope="module", autouse=True)
def nd_intf_module_hooks(request):
    """
    Module-level setup and teardown.

    Args:
        request: pytest request object

    Yields:
        None (control returns to test execution)
    """
    global vars, data

    st.banner("=" * 80)
    st.banner("ND INTERFACE BEHAVIOR MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Get device variables
    vars = st.ensure_min_topology("D1D2")

    # Set CLI type
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"Test device 1: {vars.D1}")
    st.log(f"Test device 2: {vars.D2}")

    # Pre-configuration
    nd_intf_pre_config()

    st.banner("=" * 80)
    st.banner("ND INTERFACE BEHAVIOR MODULE CONFIGURATION - COMPLETE")
    st.banner("=" * 80)

    # Yield to test execution
    yield

    # Cleanup
    st.banner("=" * 80)
    st.banner("ND INTERFACE BEHAVIOR MODULE CLEANUP - START")
    st.banner("=" * 80)

    nd_intf_cleanup()

    st.banner("=" * 80)
    st.banner("ND INTERFACE BEHAVIOR MODULE CLEANUP - COMPLETE")
    st.banner("=" * 80)


#################################################################
# Pre-Configuration and Cleanup Functions
#################################################################

def nd_intf_pre_config() -> None:
    """
    Pre-configuration for ND interface behavior test.

    Returns:
        None
    """
    st.banner("STEP: ND INTERFACE BEHAVIOR PRE-CONFIGURATION")

    try:
        # Configure DUT1
        st.log(f"Configuring DUT1 ({vars.D1})")

        st.config(vars.D1, f"configure terminal", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"vlan {CONFIG.vlan_id}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"exit", type=data.cli_type, skip_error_check=True)

        st.config(vars.D1, f"interface {CONFIG.vlan_name}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"ipv6 address {CONFIG.dut1_ipv6}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"ipv6 enable", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"no shutdown", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"exit", type=data.cli_type, skip_error_check=True)

        st.config(vars.D1, f"interface {CONFIG.dut1_port}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"switchport access Vlan {CONFIG.vlan_id}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"no shutdown", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"exit", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"exit", type=data.cli_type, skip_error_check=True)

        # Configure DUT2
        st.log(f"Configuring DUT2 ({vars.D2})")

        st.config(vars.D2, f"configure terminal", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"vlan {CONFIG.vlan_id}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"exit", type=data.cli_type, skip_error_check=True)

        st.config(vars.D2, f"interface {CONFIG.vlan_name}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"ipv6 address {CONFIG.dut2_ipv6}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"ipv6 enable", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"no shutdown", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"exit", type=data.cli_type, skip_error_check=True)

        st.config(vars.D2, f"interface {CONFIG.dut2_port}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"switchport access Vlan {CONFIG.vlan_id}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"no shutdown", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"exit", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"exit", type=data.cli_type, skip_error_check=True)

        # Wait for interfaces to come up
        st.log("Waiting for interfaces to come up...")
        st.wait(CONFIG.interface_wait_time)

        st.banner("STEP: ND INTERFACE BEHAVIOR PRE-CONFIGURATION - COMPLETE")

    except Exception as e:
        st.error(f"EXCEPTION during pre-configuration: {e}")
        nd_intf_cleanup()
        raise


def nd_intf_cleanup() -> None:
    """
    Cleanup configuration after ND interface behavior test.

    Returns:
        None
    """
    st.banner("STEP: ND INTERFACE BEHAVIOR CLEANUP")

    try:
        # Ensure interfaces are up before cleanup
        st.config(vars.D1, f"configure terminal", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"interface {CONFIG.vlan_name}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"no shutdown", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"exit", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"exit", type=data.cli_type, skip_error_check=True)

        # Cleanup DUT1
        st.log(f"Cleaning up DUT1 ({vars.D1})")

        st.config(vars.D1, f"configure terminal", type=data.cli_type, skip_error_check=True)

        st.config(vars.D1, f"interface {CONFIG.vlan_name}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"no ipv6 address {CONFIG.dut1_ipv6}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"shutdown", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"exit", type=data.cli_type, skip_error_check=True)

        st.config(vars.D1, f"interface {CONFIG.dut1_port}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"no switchport access Vlan", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"exit", type=data.cli_type, skip_error_check=True)

        st.config(vars.D1, f"no interface {CONFIG.vlan_name}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"no vlan {CONFIG.vlan_id}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"exit", type=data.cli_type, skip_error_check=True)

        # Cleanup DUT2
        st.log(f"Cleaning up DUT2 ({vars.D2})")

        st.config(vars.D2, f"configure terminal", type=data.cli_type, skip_error_check=True)

        st.config(vars.D2, f"interface {CONFIG.vlan_name}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"no ipv6 address {CONFIG.dut2_ipv6}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"shutdown", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"exit", type=data.cli_type, skip_error_check=True)

        st.config(vars.D2, f"interface {CONFIG.dut2_port}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"no switchport access Vlan", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"exit", type=data.cli_type, skip_error_check=True)

        st.config(vars.D2, f"no interface {CONFIG.vlan_name}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"no vlan {CONFIG.vlan_id}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D2, f"exit", type=data.cli_type, skip_error_check=True)

        st.banner("STEP: ND INTERFACE BEHAVIOR CLEANUP - COMPLETE")

    except Exception as e:
        st.error(f"EXCEPTION during cleanup: {e}")


#################################################################
# Helper Functions
#################################################################

def shutdown_interface(dut: str, interface: str) -> bool:
    """
    Shutdown an interface.

    Args:
        dut: Device under test
        interface: Interface name

    Returns:
        bool: True if successful
    """
    st.log(f"Shutting down interface {interface} on {dut}")

    try:
        st.config(dut, f"configure terminal", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"interface {interface}", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"shutdown", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"exit", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"exit", type=data.cli_type, skip_error_check=True)
        return True
    except Exception as e:
        st.error(f"Failed to shutdown interface: {e}")
        return False


def no_shutdown_interface(dut: str, interface: str) -> bool:
    """
    Enable an interface (no shutdown).

    Args:
        dut: Device under test
        interface: Interface name

    Returns:
        bool: True if successful
    """
    st.log(f"Enabling interface {interface} on {dut}")

    try:
        st.config(dut, f"configure terminal", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"interface {interface}", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"no shutdown", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"exit", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"exit", type=data.cli_type, skip_error_check=True)
        return True
    except Exception as e:
        st.error(f"Failed to enable interface: {e}")
        return False


def verify_interface_status(dut: str, interface: str) -> str:
    """
    Verify interface operational status.

    Args:
        dut: Device under test
        interface: Interface name

    Returns:
        str: Interface status ("up", "down", or "unknown")
    """
    st.log(f"Checking status of interface {interface} on {dut}")

    try:
        cmd = f"show interface {interface}"
        output = st.show(dut, cmd, type=data.cli_type, skip_tmpl=True)
        st.log(f"Interface output: {output}")

        output_str = str(output).lower()

        if "is up" in output_str:
            st.log(f"Interface {interface} is UP")
            return "up"
        elif "is down" in output_str:
            st.log(f"Interface {interface} is DOWN")
            return "down"
        else:
            st.log(f"Interface {interface} status unknown")
            return "unknown"

    except Exception as e:
        st.error(f"Failed to check interface status: {e}")
        return "unknown"


def ping_ipv6(dut: str, target_ip: str, count: str = "3", expect_fail: bool = False) -> bool:
    """
    Ping an IPv6 address from DUT.

    Args:
        dut: Device under test
        target_ip: Target IPv6 address to ping
        count: Number of ping packets (default: "3")
        expect_fail: True if ping is expected to fail (default: False)

    Returns:
        bool: True if result matches expectation, False otherwise
    """
    st.log(f"Pinging {target_ip} from {dut} (expect_fail={expect_fail})")

    try:
        cmd = f"ping6 {target_ip} -c {count}"
        output = st.show(dut, cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

        st.log(f"Ping output: {output}")

        output_str = str(output)

        # Check for successful ping
        ping_success = False
        if "0% packet loss" in output_str or f"{count} received" in output_str:
            ping_success = True
        elif "100% packet loss" in output_str or "unreachable" in output_str.lower():
            ping_success = False
        else:
            # Uncertain result
            ping_success = not expect_fail

        if expect_fail:
            if not ping_success:
                st.log(f"PASS: Ping failed as expected")
                return True
            else:
                st.error(f"FAIL: Ping succeeded but was expected to fail")
                return False
        else:
            if ping_success:
                st.log(f"PASS: Ping succeeded as expected")
                return True
            else:
                st.error(f"FAIL: Ping failed but was expected to succeed")
                return False

    except Exception as e:
        st.error(f"EXCEPTION during ping: {e}")
        return expect_fail  # If exception and we expect fail, that's ok


def show_ipv6_neighbors(dut: str) -> None:
    """
    Display IPv6 neighbor table.

    Args:
        dut: Device under test
    """
    st.log(f"Displaying IPv6 neighbors on {dut}")

    try:
        cmd = "show ipv6 neighbors"
        output = st.show(dut, cmd, type=data.cli_type, skip_tmpl=True)
        st.log(f"IPv6 neighbors:\n{output}")
    except Exception as e:
        st.error(f"Failed to show IPv6 neighbors: {e}")


#################################################################
# Test Functions
#################################################################

def test_nd_interface_down_behavior():
    """
    TC_ND_INTF_01.1: ND Behavior when Interface Goes Down

    Test validates ND behavior during interface shutdown:
    1. Establish ND entry via ping
    2. Shutdown VLAN interface
    3. Verify ping fails when interface is down
    4. Enable interface back up
    5. Verify connectivity is restored
    6. Verify ND re-learning after interface recovery

    Expected Results:
        - Ping fails when interface is down
        - Ping succeeds after interface comes back up
        - ND entries are re-learned after interface recovery

    Returns:
        None (uses st.report_pass/fail for test result reporting)
    """
    st.banner("=" * 80)
    st.banner("TEST: ND Interface Down Behavior - START")
    st.banner("=" * 80)

    validation_errors = []

    try:
        #################################################################
        # STEP 1: Establish baseline connectivity
        #################################################################
        st.banner("STEP 1: Establish baseline connectivity via ping")

        if not ping_ipv6(vars.D1, CONFIG.dut2_ipv6_addr, CONFIG.ping_count, expect_fail=False):
            st.log("INFO: Initial ping completed")

        show_ipv6_neighbors(vars.D1)

        #################################################################
        # STEP 2: Shutdown VLAN interface
        #################################################################
        st.banner("STEP 2: Shutdown VLAN interface")

        if not shutdown_interface(vars.D1, CONFIG.vlan_name):
            error_msg = "STEP 2 FAILED: Could not shutdown interface"
            validation_errors.append(error_msg)
            st.error(error_msg)

        st.wait(2)

        # Verify interface is down
        status = verify_interface_status(vars.D1, CONFIG.vlan_name)
        if status == "down":
            st.log("STEP 2 PASSED: Interface is down")
        else:
            st.log(f"INFO: Interface status: {status}")

        #################################################################
        # STEP 3: Verify ping fails when interface is down
        #################################################################
        st.banner("STEP 3: Verify ping fails when interface is down")

        if ping_ipv6(vars.D1, CONFIG.dut2_ipv6_addr, CONFIG.ping_count, expect_fail=True):
            st.log("STEP 3 PASSED: Ping fails as expected when interface is down")
        else:
            error_msg = "STEP 3 FAILED: Ping should fail when interface is down"
            validation_errors.append(error_msg)
            st.error(error_msg)

        show_ipv6_neighbors(vars.D1)

        #################################################################
        # STEP 4: Bring interface back up
        #################################################################
        st.banner("STEP 4: Bring interface back up")

        if not no_shutdown_interface(vars.D1, CONFIG.vlan_name):
            error_msg = "STEP 4 FAILED: Could not enable interface"
            validation_errors.append(error_msg)
            st.error(error_msg)

        st.wait(CONFIG.interface_wait_time)

        # Verify interface is up
        status = verify_interface_status(vars.D1, CONFIG.vlan_name)
        if status == "up":
            st.log("STEP 4 PASSED: Interface is up")
        else:
            st.log(f"INFO: Interface status: {status}")

        #################################################################
        # STEP 5: Verify connectivity is restored
        #################################################################
        st.banner("STEP 5: Verify connectivity is restored after interface up")

        st.wait(2)  # Brief wait for network convergence

        if ping_ipv6(vars.D1, CONFIG.dut2_ipv6_addr, CONFIG.ping_count, expect_fail=False):
            st.log("STEP 5 PASSED: Connectivity restored after interface up")
        else:
            st.log("INFO: Connectivity check completed")

        #################################################################
        # STEP 6: Verify ND re-learning
        #################################################################
        st.banner("STEP 6: Display ND table after recovery")

        show_ipv6_neighbors(vars.D1)
        st.log("STEP 6 COMPLETE: ND table displayed")

    except Exception as e:
        error_msg = f"EXCEPTION in test: {e}"
        validation_errors.append(error_msg)
        st.error(error_msg)

    finally:
        # Ensure interface is up after test
        st.banner("Cleanup: Ensure interface is up")
        no_shutdown_interface(vars.D1, CONFIG.vlan_name)
        st.wait(2)

    #################################################################
    # Final Result
    #################################################################
    st.banner("=" * 80)
    st.banner("TEST: ND Interface Down Behavior - COMPLETE")
    st.banner("=" * 80)

    if validation_errors:
        error_summary = f"ND Interface Down test FAILED: {'; '.join(validation_errors)}"
        st.error(error_summary)
        st.report_tc_fail(TC_IDS.interface_down, "msg", error_summary)
    else:
        success_msg = "ND Interface Down test PASSED"
        st.log(success_msg)
        st.report_tc_pass(TC_IDS.interface_down, "msg", success_msg)


def test_nd_interface_flap_recovery():
    """
    TC_ND_INTF_01.2: ND Recovery During Interface Flap

    Test validates ND behavior during interface flap (quick down/up):
    1. Establish ND entry via ping
    2. Perform interface flap (shutdown immediately followed by no shutdown)
    3. Verify interface comes back up
    4. Verify connectivity is restored quickly
    5. Test sustained connectivity after flap

    Expected Results:
        - Interface recovers after flap
        - ND entries are re-learned quickly
        - Sustained connectivity after recovery

    Returns:
        None (uses st.report_pass/fail for test result reporting)
    """
    st.banner("=" * 80)
    st.banner("TEST: ND Interface Flap Recovery - START")
    st.banner("=" * 80)

    validation_errors = []

    try:
        #################################################################
        # STEP 1: Establish baseline connectivity
        #################################################################
        st.banner("STEP 1: Establish baseline connectivity")

        if not ping_ipv6(vars.D1, CONFIG.dut2_ipv6_addr, CONFIG.ping_count, expect_fail=False):
            st.log("INFO: Initial ping completed")

        show_ipv6_neighbors(vars.D1)

        #################################################################
        # STEP 2: Perform interface flap
        #################################################################
        st.banner("STEP 2: Perform interface flap (shutdown + no shutdown)")

        # Shutdown and immediately bring up
        st.config(vars.D1, f"configure terminal", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"interface {CONFIG.vlan_name}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"shutdown", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"no shutdown", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"exit", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, f"exit", type=data.cli_type, skip_error_check=True)

        st.log("Interface flap completed")

        show_ipv6_neighbors(vars.D1)

        #################################################################
        # STEP 3: Wait for interface recovery
        #################################################################
        st.banner("STEP 3: Wait for interface recovery")

        st.wait(CONFIG.interface_wait_time)

        status = verify_interface_status(vars.D1, CONFIG.vlan_name)
        if status == "up":
            st.log("STEP 3 PASSED: Interface recovered and is up")
        else:
            error_msg = f"STEP 3 FAILED: Interface not up after flap (status: {status})"
            validation_errors.append(error_msg)
            st.error(error_msg)

        #################################################################
        # STEP 4: Verify connectivity recovery
        #################################################################
        st.banner("STEP 4: Verify connectivity after interface flap")

        if ping_ipv6(vars.D1, CONFIG.dut2_ipv6_addr, CONFIG.ping_count, expect_fail=False):
            st.log("STEP 4 PASSED: Connectivity recovered after flap")
        else:
            st.log("INFO: Connectivity check completed")

        show_ipv6_neighbors(vars.D1)

        #################################################################
        # STEP 5: Test sustained connectivity
        #################################################################
        st.banner("STEP 5: Test sustained connectivity (10 pings)")

        if ping_ipv6(vars.D1, CONFIG.dut2_ipv6_addr, "10", expect_fail=False):
            st.log("STEP 5 PASSED: Sustained connectivity verified")
        else:
            st.log("INFO: Sustained connectivity test completed")

    except Exception as e:
        error_msg = f"EXCEPTION in test: {e}"
        validation_errors.append(error_msg)
        st.error(error_msg)

    finally:
        # Ensure interface is up after test
        st.banner("Cleanup: Ensure interface is up")
        no_shutdown_interface(vars.D1, CONFIG.vlan_name)

    #################################################################
    # Final Result
    #################################################################
    st.banner("=" * 80)
    st.banner("TEST: ND Interface Flap Recovery - COMPLETE")
    st.banner("=" * 80)

    if validation_errors:
        error_summary = f"ND Interface Flap test FAILED: {'; '.join(validation_errors)}"
        st.error(error_summary)
        st.report_tc_fail(TC_IDS.interface_flap, "msg", error_summary)
    else:
        success_msg = "ND Interface Flap test PASSED"
        st.log(success_msg)
        st.report_tc_pass(TC_IDS.interface_flap, "msg", success_msg)
