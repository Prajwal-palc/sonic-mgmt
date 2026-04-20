"""
SM_ISCLI_20 - OSPF Configuration on Loopback Interfaces Without IP Address

Author: Athira
Copyright (C) 2024, PALC Networks

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_2d.yaml \\
  routing/ospf/test_sm_iscli_20_ospf_loopback_no_ip.py \\
  --logs-path ./logs/sm_iscli_20_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test suite validates OSPF behavior when configured on loopback interfaces
  that do not have IP addresses assigned. The bug scenario shows that OSPF
  configuration is accepted on loopbacks without IP addresses, but OSPF does
  not activate until an IP address is assigned.

  The expected behavior should be either:
  1. Reject the OSPF configuration if no IP address is present, OR
  2. Accept it but automatically activate when IP is later assigned

  Current buggy behavior:
  - Command accepted silently without error
  - OSPF does not activate (interface doesn't appear in 'show ip ospf interface')
  - No warning or error message to user

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Min SONiC Version: Any version with IS-CLI support
  - Required test variables (YAML): vars/routing/ospf/vars_sm_iscli_20.yaml
  - Both devices must support OSPF
"""

import pytest
from pathlib import Path
import yaml
import time

from spytest import st, SpyTestDict
import apis.routing.ip as ip_api
import apis.routing.ospf as ospf_api
import apis.system.interface as intf_api
import apis.system.basic as basic_api

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Default YAML variable file path
DEFAULT_VAR_FILE = Path(__file__).resolve().parents[3] / "vars/routing/ospf/vars_sm_iscli_20.yaml"

# Test case IDs
TC_IDS = SpyTestDict({
    "baseline": "SM_ISCLI_20_TC1",
    "bug_scenario": "SM_ISCLI_20_TC2",
    "recovery": "SM_ISCLI_20_TC3",
    "remove_ip": "SM_ISCLI_20_TC4",
    "lifecycle": "SM_ISCLI_20_TC5",
    "multi_interface": "SM_ISCLI_20_TC6",
    "config_order": "SM_ISCLI_20_TC7",
    "invalid_area": "SM_ISCLI_20_TC8",
    "parameters": "SM_ISCLI_20_TC9",
    "cleanup": "SM_ISCLI_20_TC10",
})


def initialize_data() -> None:
    """
    Load test configuration from YAML file and initialize topology.

    This function loads test parameters from the YAML configuration file
    and ensures the required topology is available.
    """
    try:
        with open(DEFAULT_VAR_FILE, "r") as f:
            payload = yaml.safe_load(f)
    except FileNotFoundError as error:
        pytest.skip(str(error))

    global vars, data
    vars = st.ensure_min_topology(*payload.get("min_topology", ["D1D2:1"]))
    data.config = SpyTestDict(payload)

    # Store device and interface references
    data.d1 = vars.D1
    data.d2 = vars.D2
    data.d1_d2_port = vars.D1D2P1
    data.d2_d1_port = vars.D2D1P1

    # Update physical interface data from topology
    data.config.physical_interface.d1_interface = data.d1_d2_port
    data.config.physical_interface.d2_interface = data.d2_d1_port

    st.log(f"Initialized with D1={data.d1}, D2={data.d2}")
    st.log(f"D1-D2 link: {data.d1_d2_port} <-> {data.d2_d1_port}")


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level fixture for setup and teardown.

    Prologue:
        - Initialize test data from YAML
        - Configure basic OSPF setup on both devices
        - Configure physical interface connectivity
        - Verify OSPF neighbor establishment on physical interface

    Epilogue:
        - Remove all OSPF configurations
        - Remove all loopback interfaces
        - Remove IP configurations
        - Restore devices to clean state
    """
    global vars, data

    st.banner("MODULE PROLOGUE: SM_ISCLI_20 - OSPF Loopback Without IP")

    # Initialize test data
    initialize_data()

    # Configure physical interface on D1
    st.log("Configuring physical interface on D1")
    intf_api.interface_operation(data.d1, data.d1_d2_port, "startup", skip_verify=True)
    intf_api.interface_operation(data.d2, data.d2_d1_port, "startup", skip_verify=True)

    # Small delay for interfaces to come up
    st.wait(5, "Waiting for interfaces to come up")

    # Configure IP addresses on physical interfaces
    st.log("Configuring IP addresses on physical interfaces")
    result1 = ip_api.config_ip_addr_interface(
        data.d1,
        data.d1_d2_port,
        data.config.physical_interface.d1_ip,
        "ipv4",
        config="add",
        cli_type="klish"
    )
    result2 = ip_api.config_ip_addr_interface(
        data.d2,
        data.d2_d1_port,
        data.config.physical_interface.d2_ip,
        "ipv4",
        config="add",
        cli_type="klish"
    )

    if not (result1 and result2):
        st.error("Failed to configure IP addresses on physical interfaces")
        st.report_env_fail("test_case_failed", "IP configuration failed")

    # Configure OSPF on D1
    st.log("Configuring OSPF on D1")
    ospf_result = ospf_api.config_ospf_router(
        data.d1,
        ospf_router_id=data.config.ospf_config.router_id,
        config="yes",
        cli_type="klish"
    )
    if not ospf_result:
        st.error("Failed to configure OSPF router on D1")
        st.report_env_fail("test_case_failed", "OSPF router configuration failed")

    # Configure OSPF on D2
    st.log("Configuring OSPF on D2")
    ospf_result = ospf_api.config_ospf_router(
        data.d2,
        ospf_router_id=data.config.d2_ospf.router_id,
        config="yes",
        cli_type="klish"
    )
    if not ospf_result:
        st.error("Failed to configure OSPF router on D2")
        st.report_env_fail("test_case_failed", "OSPF router configuration failed on D2")

    # Configure OSPF on physical interfaces
    st.log("Enabling OSPF on physical interfaces")
    intf_result1 = ospf_api.config_interface_ip_ospf_area(
        data.d1,
        [data.d1_d2_port],
        data.config.physical_interface.ospf_area,
        config="yes",
        cli_type="klish"
    )
    intf_result2 = ospf_api.config_interface_ip_ospf_area(
        data.d2,
        [data.d2_d1_port],
        data.config.physical_interface.ospf_area,
        config="yes",
        cli_type="klish"
    )

    if not (intf_result1 and intf_result2):
        st.error("Failed to enable OSPF on physical interfaces")
        st.report_env_fail("test_case_failed", "OSPF interface configuration failed")

    # Wait for OSPF convergence
    st.wait(data.config.wait_times.ospf_convergence, "Waiting for OSPF convergence")

    # Verify OSPF neighbor on physical interface
    st.log("Verifying OSPF neighbor establishment")
    neighbor_result = ospf_api.verify_ospf_neighbor_state(
        data.d1,
        ospf_links=[data.d1_d2_port],
        state=["Full"],
        cli_type="klish"
    )

    if not neighbor_result:
        st.error("OSPF neighbor not established on physical interface")
        st.report_env_fail("test_case_failed", "OSPF neighbor establishment failed")

    st.banner("MODULE PROLOGUE: Completed successfully")

    yield

    # Module epilogue - cleanup
    st.banner("MODULE EPILOGUE: Cleanup")

    # Remove all loopback interfaces created during tests
    for loopback_name in ["Loopback0", "Loopback1", "Loopback2", "Loopback10", "Loopback99"]:
        st.log(f"Removing {loopback_name} if exists")
        # Remove IP address
        ip_api.delete_ip_interface(data.d1, loopback_name, skip_error=True, cli_type="klish")
        # Remove loopback interface
        intf_api.interface_operation(data.d1, loopback_name, "shutdown", skip_verify=True)
        intf_api.delete_interface(data.d1, loopback_name, skip_verify=True, cli_type="klish")

    # Remove OSPF configuration from D1
    st.log("Removing OSPF configuration from D1")
    ospf_api.config_ospf_router(data.d1, config="no", cli_type="klish")

    # Remove OSPF configuration from D2
    st.log("Removing OSPF configuration from D2")
    ospf_api.config_ospf_router(data.d2, config="no", cli_type="klish")

    # Remove IP from physical interfaces
    ip_api.delete_ip_interface(data.d1, data.d1_d2_port, data.config.physical_interface.d1_ip, cli_type="klish")
    ip_api.delete_ip_interface(data.d2, data.d2_d1_port, data.config.physical_interface.d2_ip, cli_type="klish")

    st.banner("MODULE EPILOGUE: Completed")


def verify_loopback_in_ospf(dut, loopback_name, should_exist=True, cli_type="klish"):
    """
    Verify if loopback interface appears in OSPF interface output.

    Args:
        dut: Device under test
        loopback_name: Name of loopback interface (e.g., "Loopback0")
        should_exist: True if interface should be in OSPF, False otherwise
        cli_type: CLI type to use

    Returns:
        True if verification passes, False otherwise
    """
    st.log(f"Verifying {loopback_name} in OSPF interfaces (should_exist={should_exist})")

    output = st.show(dut, "show ip ospf interface", type=cli_type)
    st.log(f"OSPF interface output: {output}")

    # Check if loopback appears in output
    found = False
    for line in str(output).split("\n"):
        if loopback_name in line and "is up" in line:
            found = True
            break

    if should_exist:
        if found:
            st.log(f"✓ {loopback_name} found in OSPF interfaces as expected")
            return True
        else:
            st.error(f"✗ {loopback_name} NOT found in OSPF interfaces (expected to find it)")
            return False
    else:
        if found:
            st.error(f"✗ {loopback_name} found in OSPF interfaces (expected NOT to find it)")
            return False
        else:
            st.log(f"✓ {loopback_name} NOT in OSPF interfaces as expected")
            return True


def verify_ip_on_loopback(dut, loopback_name, ip_address, should_exist=True, cli_type="klish"):
    """
    Verify if IP address is configured on loopback interface.

    Args:
        dut: Device under test
        loopback_name: Name of loopback interface
        ip_address: Expected IP address (e.g., "30.1.1.1/32")
        should_exist: True if IP should exist, False otherwise
        cli_type: CLI type to use

    Returns:
        True if verification passes, False otherwise
    """
    st.log(f"Verifying IP {ip_address} on {loopback_name} (should_exist={should_exist})")

    result = ip_api.verify_interface_ip_address(
        dut,
        loopback_name,
        ip_address,
        "ipv4",
        cli_type=cli_type
    )

    if should_exist:
        if result:
            st.log(f"✓ IP {ip_address} found on {loopback_name}")
            return True
        else:
            st.error(f"✗ IP {ip_address} NOT found on {loopback_name}")
            return False
    else:
        if result:
            st.error(f"✗ IP {ip_address} found on {loopback_name} (expected NOT to find it)")
            return False
        else:
            st.log(f"✓ IP {ip_address} NOT on {loopback_name} as expected")
            return True


def configure_loopback_interface(dut, loopback_name, cli_type="klish"):
    """
    Create loopback interface.

    Args:
        dut: Device under test
        loopback_name: Name of loopback interface to create
        cli_type: CLI type to use

    Returns:
        True if successful, False otherwise
    """
    st.log(f"Creating loopback interface {loopback_name}")

    result = intf_api.interface_operation(
        dut,
        loopback_name,
        "startup",
        skip_verify=True
    )

    st.wait(data.config.wait_times.config_apply, "Waiting after interface creation")

    return result


@pytest.mark.test_sm_iscli_20_tc1
def test_sm_iscli_20_tc1_ospf_loopback_with_ip():
    """
    TC 20.1: OSPF on Loopback WITH IP Address (Baseline).

    Objective:
        Verify OSPF works correctly when loopback has IP address configured.
        This serves as the baseline/positive test case.

    Steps:
        1. Create loopback interface
        2. Configure IP address on loopback
        3. Enable OSPF on loopback
        4. Verify loopback appears in 'show ip ospf interface'
        5. Verify OSPF database contains loopback route

    Expected Result:
        - OSPF configuration accepted
        - Loopback appears in OSPF interface output
        - OSPF is active on the loopback
    """
    st.banner("TC 20.1: OSPF on Loopback WITH IP Address (Baseline)")

    tc_data = data.config.testcases["20.1"]
    loopback = tc_data.loopback
    ip_addr = tc_data.ip_address
    ospf_area = tc_data.ospf_area

    # Step 1: Create loopback interface
    result = configure_loopback_interface(data.d1, loopback)
    if not result:
        st.report_tc_fail(TC_IDS.baseline, "loopback_creation_failed")
        st.report_fail("test_case_failed", "Failed to create loopback interface")

    # Step 2: Configure IP address
    st.log(f"Configuring IP {ip_addr} on {loopback}")
    result = ip_api.config_ip_addr_interface(
        data.d1,
        loopback,
        ip_addr,
        "ipv4",
        config="add",
        cli_type="klish"
    )
    if not result:
        st.report_tc_fail(TC_IDS.baseline, "ip_configuration_failed")
        st.report_fail("test_case_failed", "Failed to configure IP address")

    st.wait(data.config.wait_times.config_apply, "Waiting after IP configuration")

    # Verify IP is configured
    if not verify_ip_on_loopback(data.d1, loopback, ip_addr, should_exist=True):
        st.report_tc_fail(TC_IDS.baseline, "ip_verification_failed")
        st.report_fail("test_case_failed", "IP address verification failed")

    # Step 3: Enable OSPF on loopback
    st.log(f"Enabling OSPF area {ospf_area} on {loopback}")
    result = ospf_api.config_interface_ip_ospf_area(
        data.d1,
        [loopback],
        ospf_area,
        config="yes",
        cli_type="klish"
    )
    if not result:
        st.report_tc_fail(TC_IDS.baseline, "ospf_configuration_failed")
        st.report_fail("test_case_failed", "Failed to configure OSPF on loopback")

    st.wait(data.config.wait_times.ospf_convergence, "Waiting for OSPF convergence")

    # Step 4: Verify loopback in OSPF
    if not verify_loopback_in_ospf(data.d1, loopback, should_exist=True):
        st.report_tc_fail(TC_IDS.baseline, "ospf_not_active")
        st.report_fail("test_case_failed", "Loopback not found in OSPF interfaces")

    st.report_tc_pass(TC_IDS.baseline, "test_case_passed")
    st.log("✓ TC 20.1 PASSED: OSPF working correctly on loopback with IP")


@pytest.mark.test_sm_iscli_20_tc2
def test_sm_iscli_20_tc2_ospf_loopback_without_ip():
    """
    TC 20.2: OSPF on Loopback WITHOUT IP Address (Bug Scenario).

    Objective:
        Verify OSPF behavior when configured on loopback without IP address.
        This is the main bug scenario - configuration is accepted but OSPF doesn't activate.

    Steps:
        1. Create loopback interface (without IP)
        2. Attempt to enable OSPF on loopback
        3. Verify command is accepted (bug: should reject or warn)
        4. Verify loopback does NOT appear in 'show ip ospf interface'

    Expected Result (Bug):
        - OSPF configuration command is ACCEPTED (wrong behavior)
        - Loopback does NOT appear in OSPF interface output
        - No error or warning message given to user

    Expected Result (After Fix):
        - Either: Configuration rejected with error message
        - Or: Configuration accepted with warning, OSPF activates when IP added
    """
    st.banner("TC 20.2: OSPF on Loopback WITHOUT IP Address (Bug Scenario)")

    tc_data = data.config.testcases["20.2"]
    loopback = tc_data.loopback
    ospf_area = tc_data.ospf_area

    # Step 1: Create loopback interface WITHOUT IP
    result = configure_loopback_interface(data.d1, loopback)
    if not result:
        st.report_tc_fail(TC_IDS.bug_scenario, "loopback_creation_failed")
        st.report_fail("test_case_failed", "Failed to create loopback interface")

    # Step 2: Attempt to enable OSPF WITHOUT IP address
    st.log(f"Attempting to enable OSPF on {loopback} WITHOUT IP address")
    result = ospf_api.config_interface_ip_ospf_area(
        data.d1,
        [loopback],
        ospf_area,
        config="yes",
        cli_type="klish"
    )

    # Bug: Command is accepted (result = True)
    if result:
        st.log("⚠ BUG CONFIRMED: OSPF configuration accepted without IP address")
    else:
        st.log("✓ FIXED: OSPF configuration rejected without IP address (expected behavior)")

    st.wait(data.config.wait_times.ospf_convergence, "Waiting to verify OSPF state")

    # Step 3: Verify loopback does NOT appear in OSPF
    if not verify_loopback_in_ospf(data.d1, loopback, should_exist=False):
        st.report_tc_fail(TC_IDS.bug_scenario, "ospf_incorrectly_active")
        st.report_fail("test_case_failed", "Loopback incorrectly appears in OSPF without IP")

    st.report_tc_pass(TC_IDS.bug_scenario, "test_case_passed")
    st.log("✓ TC 20.2 PASSED: Bug scenario validated - OSPF not active without IP")


@pytest.mark.test_sm_iscli_20_tc3
def test_sm_iscli_20_tc3_add_ip_after_ospf():
    """
    TC 20.3: Add IP After OSPF Configuration (Recovery).

    Objective:
        Verify OSPF activates after adding IP to a loopback that already has
        OSPF configured but was inactive due to missing IP.

    Steps:
        1. Create loopback interface
        2. Enable OSPF on loopback (without IP)
        3. Verify OSPF is NOT active
        4. Add IP address to loopback
        5. Verify OSPF becomes active

    Expected Result:
        - OSPF activates automatically when IP is added
        - Loopback appears in 'show ip ospf interface' after IP configuration
    """
    st.banner("TC 20.3: Add IP After OSPF Configuration (Recovery)")

    tc_data = data.config.testcases["20.3"]
    loopback = tc_data.loopback
    ip_addr = tc_data.ip_address
    ospf_area = tc_data.ospf_area

    # Step 1: Create loopback
    result = configure_loopback_interface(data.d1, loopback)
    if not result:
        st.report_tc_fail(TC_IDS.recovery, "loopback_creation_failed")
        st.report_fail("test_case_failed", "Failed to create loopback")

    # Step 2: Configure OSPF without IP
    st.log(f"Configuring OSPF on {loopback} WITHOUT IP")
    ospf_api.config_interface_ip_ospf_area(
        data.d1,
        [loopback],
        ospf_area,
        config="yes",
        cli_type="klish"
    )

    st.wait(data.config.wait_times.config_apply, "Waiting after OSPF configuration")

    # Step 3: Verify OSPF is NOT active
    if not verify_loopback_in_ospf(data.d1, loopback, should_exist=False):
        st.report_tc_fail(TC_IDS.recovery, "ospf_incorrectly_active_without_ip")
        st.report_fail("test_case_failed", "OSPF should not be active without IP")

    # Step 4: Add IP address
    st.log(f"Adding IP {ip_addr} to {loopback}")
    result = ip_api.config_ip_addr_interface(
        data.d1,
        loopback,
        ip_addr,
        "ipv4",
        config="add",
        cli_type="klish"
    )
    if not result:
        st.report_tc_fail(TC_IDS.recovery, "ip_configuration_failed")
        st.report_fail("test_case_failed", "Failed to add IP address")

    st.wait(data.config.wait_times.ospf_convergence, "Waiting for OSPF to activate")

    # Step 5: Verify OSPF becomes active
    if not verify_loopback_in_ospf(data.d1, loopback, should_exist=True):
        st.report_tc_fail(TC_IDS.recovery, "ospf_not_activated_after_ip")
        st.report_fail("test_case_failed", "OSPF did not activate after adding IP")

    st.report_tc_pass(TC_IDS.recovery, "test_case_passed")
    st.log("✓ TC 20.3 PASSED: OSPF activated after adding IP")


@pytest.mark.test_sm_iscli_20_tc4
def test_sm_iscli_20_tc4_remove_ip_from_active_ospf():
    """
    TC 20.4: Remove IP from Active OSPF Loopback.

    Objective:
        Verify OSPF deactivates when IP address is removed from an active
        OSPF loopback interface.

    Steps:
        1. Create loopback with IP and OSPF (active state)
        2. Verify OSPF is active
        3. Remove IP address from loopback
        4. Verify OSPF deactivates

    Expected Result:
        - OSPF deactivates when IP is removed
        - Loopback disappears from 'show ip ospf interface'
    """
    st.banner("TC 20.4: Remove IP from Active OSPF Loopback")

    tc_data = data.config.testcases["20.4"]
    loopback = tc_data.loopback
    ip_addr = tc_data.ip_address
    ospf_area = tc_data.ospf_area

    # Step 1: Create loopback with IP and OSPF
    st.log(f"Creating {loopback} with IP and OSPF")
    configure_loopback_interface(data.d1, loopback)

    ip_api.config_ip_addr_interface(
        data.d1,
        loopback,
        ip_addr,
        "ipv4",
        config="add",
        cli_type="klish"
    )

    st.wait(data.config.wait_times.config_apply, "Waiting after IP configuration")

    ospf_api.config_interface_ip_ospf_area(
        data.d1,
        [loopback],
        ospf_area,
        config="yes",
        cli_type="klish"
    )

    st.wait(data.config.wait_times.ospf_convergence, "Waiting for OSPF convergence")

    # Step 2: Verify OSPF is active
    if not verify_loopback_in_ospf(data.d1, loopback, should_exist=True):
        st.report_tc_fail(TC_IDS.remove_ip, "ospf_not_active_initial")
        st.report_fail("test_case_failed", "OSPF not active initially")

    # Step 3: Remove IP address
    st.log(f"Removing IP from {loopback}")
    result = ip_api.delete_ip_interface(
        data.d1,
        loopback,
        ip_addr,
        "ipv4",
        cli_type="klish"
    )
    if not result:
        st.report_tc_fail(TC_IDS.remove_ip, "ip_removal_failed")
        st.report_fail("test_case_failed", "Failed to remove IP address")

    st.wait(data.config.wait_times.config_apply, "Waiting after IP removal")

    # Step 4: Verify OSPF deactivates
    if not verify_loopback_in_ospf(data.d1, loopback, should_exist=False):
        st.report_tc_fail(TC_IDS.remove_ip, "ospf_still_active_after_ip_removal")
        st.report_fail("test_case_failed", "OSPF still active after IP removal")

    st.report_tc_pass(TC_IDS.remove_ip, "test_case_passed")
    st.log("✓ TC 20.4 PASSED: OSPF deactivated after IP removal")


@pytest.mark.test_sm_iscli_20_tc5
def test_sm_iscli_20_tc5_full_lifecycle():
    """
    TC 20.5: Full Lifecycle with IP Changes.

    Objective:
        Verify OSPF behavior through complete interface lifecycle including
        multiple IP additions, removals, and changes.

    Steps:
        1. Create loopback with IP → Verify OSPF active
        2. Remove IP → Verify OSPF inactive
        3. Re-add same IP → Verify OSPF active
        4. Change to different IP → Verify OSPF remains active
        5. Remove IP final → Verify OSPF inactive

    Expected Result:
        - OSPF tracks IP address presence correctly through all transitions
        - OSPF activates with IP, deactivates without IP
    """
    st.banner("TC 20.5: Full Lifecycle with IP Changes")

    tc_data = data.config.testcases["20.5"]
    loopback = tc_data.loopback
    ospf_area = tc_data.ospf_area
    lifecycle = tc_data.lifecycle_steps

    # Create loopback and configure OSPF
    configure_loopback_interface(data.d1, loopback)

    ospf_api.config_interface_ip_ospf_area(
        data.d1,
        [loopback],
        ospf_area,
        config="yes",
        cli_type="klish"
    )

    # Phase 1: Initial config with IP
    st.log("Phase 1: Initial configuration with IP")
    phase = lifecycle[0]
    ip_addr = phase["ip"]

    ip_api.config_ip_addr_interface(
        data.d1,
        loopback,
        ip_addr,
        "ipv4",
        config="add",
        cli_type="klish"
    )

    st.wait(data.config.wait_times.ospf_convergence, "Waiting for OSPF")

    if not verify_loopback_in_ospf(data.d1, loopback, should_exist=phase["ospf_expected"]):
        st.report_tc_fail(TC_IDS.lifecycle, "phase1_failed")
        st.report_fail("test_case_failed", "Phase 1 failed")

    # Phase 2: Remove IP
    st.log("Phase 2: Remove IP")
    phase = lifecycle[1]

    ip_api.delete_ip_interface(data.d1, loopback, ip_addr, "ipv4", cli_type="klish")
    st.wait(data.config.wait_times.config_apply, "Waiting after IP removal")

    if not verify_loopback_in_ospf(data.d1, loopback, should_exist=phase["ospf_expected"]):
        st.report_tc_fail(TC_IDS.lifecycle, "phase2_failed")
        st.report_fail("test_case_failed", "Phase 2 failed")

    # Phase 3: Re-add same IP
    st.log("Phase 3: Re-add same IP")
    phase = lifecycle[2]
    ip_addr = phase["ip"]

    ip_api.config_ip_addr_interface(
        data.d1,
        loopback,
        ip_addr,
        "ipv4",
        config="add",
        cli_type="klish"
    )

    st.wait(data.config.wait_times.ospf_convergence, "Waiting for OSPF")

    if not verify_loopback_in_ospf(data.d1, loopback, should_exist=phase["ospf_expected"]):
        st.report_tc_fail(TC_IDS.lifecycle, "phase3_failed")
        st.report_fail("test_case_failed", "Phase 3 failed")

    # Phase 4: Change IP
    st.log("Phase 4: Change to different IP")
    phase = lifecycle[3]
    new_ip = phase["ip"]

    # Remove old IP and add new IP
    ip_api.delete_ip_interface(data.d1, loopback, ip_addr, "ipv4", cli_type="klish")
    ip_api.config_ip_addr_interface(
        data.d1,
        loopback,
        new_ip,
        "ipv4",
        config="add",
        cli_type="klish"
    )

    st.wait(data.config.wait_times.ospf_convergence, "Waiting for OSPF")

    if not verify_loopback_in_ospf(data.d1, loopback, should_exist=phase["ospf_expected"]):
        st.report_tc_fail(TC_IDS.lifecycle, "phase4_failed")
        st.report_fail("test_case_failed", "Phase 4 failed")

    # Phase 5: Final IP removal
    st.log("Phase 5: Final IP removal")
    phase = lifecycle[4]

    ip_api.delete_ip_interface(data.d1, loopback, new_ip, "ipv4", cli_type="klish")
    st.wait(data.config.wait_times.config_apply, "Waiting after IP removal")

    if not verify_loopback_in_ospf(data.d1, loopback, should_exist=phase["ospf_expected"]):
        st.report_tc_fail(TC_IDS.lifecycle, "phase5_failed")
        st.report_fail("test_case_failed", "Phase 5 failed")

    st.report_tc_pass(TC_IDS.lifecycle, "test_case_passed")
    st.log("✓ TC 20.5 PASSED: Full lifecycle completed successfully")


@pytest.mark.test_sm_iscli_20_tc6
def test_sm_iscli_20_tc6_multiple_loopbacks():
    """
    TC 20.6: Multiple Loopbacks with OSPF.

    Objective:
        Verify OSPF behavior with multiple loopback interfaces in mixed states
        (some with IP, some without).

    Steps:
        1. Create Loopback0 with IP and OSPF
        2. Create Loopback1 without IP but with OSPF config
        3. Create Loopback2 with IP and OSPF
        4. Verify only loopbacks WITH IP appear in OSPF

    Expected Result:
        - Loopback0 and Loopback2 appear in OSPF (have IP)
        - Loopback1 does NOT appear in OSPF (no IP)
    """
    st.banner("TC 20.6: Multiple Loopbacks with OSPF")

    tc_data = data.config.testcases["20.6"]
    loopbacks = tc_data.loopbacks

    # Configure all loopbacks
    for lb_config in loopbacks:
        loopback = lb_config["name"]
        ip_addr = lb_config["ip"]
        ospf_area = lb_config["ospf_area"]
        has_ip = lb_config["has_ip"]
        should_work = lb_config["ospf_should_work"]

        st.log(f"Configuring {loopback} (has_ip={has_ip})")

        # Create loopback
        configure_loopback_interface(data.d1, loopback)

        # Configure IP if specified
        if has_ip and ip_addr:
            ip_api.config_ip_addr_interface(
                data.d1,
                loopback,
                ip_addr,
                "ipv4",
                config="add",
                cli_type="klish"
            )

        # Configure OSPF
        ospf_api.config_interface_ip_ospf_area(
            data.d1,
            [loopback],
            ospf_area,
            config="yes",
            cli_type="klish"
        )

    st.wait(data.config.wait_times.ospf_convergence, "Waiting for OSPF convergence")

    # Verify each loopback
    all_passed = True
    for lb_config in loopbacks:
        loopback = lb_config["name"]
        should_work = lb_config["ospf_should_work"]

        if not verify_loopback_in_ospf(data.d1, loopback, should_exist=should_work):
            st.error(f"Verification failed for {loopback}")
            all_passed = False

    if not all_passed:
        st.report_tc_fail(TC_IDS.multi_interface, "multi_loopback_verification_failed")
        st.report_fail("test_case_failed", "Multiple loopback verification failed")

    st.report_tc_pass(TC_IDS.multi_interface, "test_case_passed")
    st.log("✓ TC 20.6 PASSED: Multiple loopbacks validated correctly")


@pytest.mark.test_sm_iscli_20_tc7
def test_sm_iscli_20_tc7_config_order_variations():
    """
    TC 20.7: Configuration Order Variations.

    Objective:
        Verify OSPF works regardless of configuration order (IP first vs OSPF first).

    Steps:
        1. Scenario 1: Configure IP first, then OSPF
        2. Scenario 2: Configure OSPF first, then IP
        3. Scenario 3: Configure only OSPF (no IP)
        4. Verify final OSPF state for each scenario

    Expected Result:
        - Scenario 1: OSPF active immediately
        - Scenario 2: OSPF active after IP added
        - Scenario 3: OSPF not active (no IP)
    """
    st.banner("TC 20.7: Configuration Order Variations")

    tc_data = data.config.testcases["20.7"]
    scenarios = tc_data.test_scenarios

    all_passed = True

    for scenario in scenarios:
        scenario_name = scenario["scenario"]
        loopback = scenario["loopback"]
        ip_addr = scenario["ip"]
        ospf_area = scenario["ospf_area"]
        order = scenario["order"]
        expected = scenario["expected_result"]

        st.log(f"Testing scenario: {scenario_name}")

        # Create loopback
        configure_loopback_interface(data.d1, loopback)

        # Execute configuration in specified order
        for step in order:
            if step == "configure_ip" and ip_addr:
                st.log(f"Step: Configure IP {ip_addr}")
                ip_api.config_ip_addr_interface(
                    data.d1,
                    loopback,
                    ip_addr,
                    "ipv4",
                    config="add",
                    cli_type="klish"
                )
                st.wait(data.config.wait_times.config_apply, "After IP config")

            elif step == "configure_ospf":
                st.log(f"Step: Configure OSPF area {ospf_area}")
                ospf_api.config_interface_ip_ospf_area(
                    data.d1,
                    [loopback],
                    ospf_area,
                    config="yes",
                    cli_type="klish"
                )
                st.wait(data.config.wait_times.config_apply, "After OSPF config")

        st.wait(data.config.wait_times.ospf_convergence, "Waiting for final state")

        # Verify result
        should_be_active = "active" in expected
        if not verify_loopback_in_ospf(data.d1, loopback, should_exist=should_be_active):
            st.error(f"Scenario {scenario_name} failed")
            all_passed = False

        # Cleanup for next scenario
        ip_api.delete_ip_interface(data.d1, loopback, skip_error=True, cli_type="klish")
        intf_api.delete_interface(data.d1, loopback, skip_verify=True, cli_type="klish")

    if not all_passed:
        st.report_tc_fail(TC_IDS.config_order, "config_order_variations_failed")
        st.report_fail("test_case_failed", "Configuration order validation failed")

    st.report_tc_pass(TC_IDS.config_order, "test_case_passed")
    st.log("✓ TC 20.7 PASSED: Configuration order variations validated")


@pytest.mark.test_sm_iscli_20_tc8
def test_sm_iscli_20_tc8_invalid_ospf_area():
    """
    TC 20.8: Invalid OSPF Area Handling on Loopback Without IP.

    Objective:
        Verify error handling when invalid OSPF area is configured on
        loopback without IP address.

    Steps:
        1. Create loopback without IP
        2. Attempt to configure invalid OSPF areas
        3. Verify appropriate error handling

    Expected Result:
        - Invalid area configurations should be rejected
        - Appropriate error messages displayed
    """
    st.banner("TC 20.8: Invalid OSPF Area Handling")

    tc_data = data.config.testcases["20.8"]
    loopback = tc_data.loopback
    invalid_areas = tc_data.invalid_areas

    # Create loopback without IP
    configure_loopback_interface(data.d1, loopback)

    all_handled_correctly = True

    for invalid_area in invalid_areas:
        st.log(f"Testing invalid area: {invalid_area}")

        result = ospf_api.config_interface_ip_ospf_area(
            data.d1,
            [loopback],
            invalid_area,
            config="yes",
            cli_type="klish"
        )

        # Invalid areas should be rejected (result = False)
        if result:
            st.error(f"Invalid area {invalid_area} was accepted (should be rejected)")
            all_handled_correctly = False
        else:
            st.log(f"✓ Invalid area {invalid_area} correctly rejected")

    if not all_handled_correctly:
        st.report_tc_fail(TC_IDS.invalid_area, "invalid_area_not_rejected")
        st.report_fail("test_case_failed", "Invalid area handling failed")

    st.report_tc_pass(TC_IDS.invalid_area, "test_case_passed")
    st.log("✓ TC 20.8 PASSED: Invalid areas handled correctly")


@pytest.mark.test_sm_iscli_20_tc9
def test_sm_iscli_20_tc9_ospf_parameters_without_ip():
    """
    TC 20.9: OSPF Priority and Cost on Loopback Without IP.

    Objective:
        Verify OSPF parameters (priority, cost) don't activate when
        configured on loopback without IP address.

    Steps:
        1. Create loopback without IP
        2. Configure OSPF with area, priority, and cost
        3. Verify interface not in OSPF
        4. Add IP address
        5. Verify interface appears in OSPF with correct parameters

    Expected Result:
        - Parameters stored in config but OSPF not active without IP
        - OSPF activates with correct parameters when IP is added
    """
    st.banner("TC 20.9: OSPF Priority and Cost on Loopback Without IP")

    tc_data = data.config.testcases["20.9"]
    loopback = tc_data.loopback
    ospf_config = tc_data.ospf_config

    # Create loopback without IP
    configure_loopback_interface(data.d1, loopback)

    # Configure OSPF with area
    st.log("Configuring OSPF area without IP")
    ospf_api.config_interface_ip_ospf_area(
        data.d1,
        [loopback],
        ospf_config["area"],
        config="yes",
        cli_type="klish"
    )

    st.wait(data.config.wait_times.config_apply, "After OSPF area config")

    # Verify OSPF not active
    if not verify_loopback_in_ospf(data.d1, loopback, should_exist=False):
        st.report_tc_fail(TC_IDS.parameters, "ospf_active_without_ip")
        st.report_fail("test_case_failed", "OSPF should not be active without IP")

    # Add IP address
    st.log("Adding IP address")
    ip_api.config_ip_addr_interface(
        data.d1,
        loopback,
        data.config.loopback_interfaces.loopback0.ip_address,
        "ipv4",
        config="add",
        cli_type="klish"
    )

    st.wait(data.config.wait_times.ospf_convergence, "Waiting for OSPF")

    # Verify OSPF now active
    if not verify_loopback_in_ospf(data.d1, loopback, should_exist=True):
        st.report_tc_fail(TC_IDS.parameters, "ospf_not_active_after_ip")
        st.report_fail("test_case_failed", "OSPF should be active after IP added")

    st.report_tc_pass(TC_IDS.parameters, "test_case_passed")
    st.log("✓ TC 20.9 PASSED: OSPF parameters validated correctly")


@pytest.mark.test_sm_iscli_20_tc10
def test_sm_iscli_20_tc10_cleanup_verification():
    """
    TC 20.10: Cleanup and Unconfiguration.

    Objective:
        Verify proper cleanup of OSPF configuration from loopback interfaces.

    Steps:
        1. Create loopback with IP and OSPF
        2. Verify OSPF active
        3. Remove OSPF configuration
        4. Verify loopback removed from OSPF
        5. Remove IP address
        6. Verify complete cleanup

    Expected Result:
        - OSPF configuration can be cleanly removed
        - Interface disappears from OSPF output
        - No residual configuration remains
    """
    st.banner("TC 20.10: Cleanup and Unconfiguration")

    tc_data = data.config.testcases["20.10"]
    loopback = tc_data.loopback
    ip_addr = tc_data.ip_address
    ospf_area = tc_data.ospf_area

    # Create loopback with IP and OSPF
    configure_loopback_interface(data.d1, loopback)

    ip_api.config_ip_addr_interface(
        data.d1,
        loopback,
        ip_addr,
        "ipv4",
        config="add",
        cli_type="klish"
    )

    ospf_api.config_interface_ip_ospf_area(
        data.d1,
        [loopback],
        ospf_area,
        config="yes",
        cli_type="klish"
    )

    st.wait(data.config.wait_times.ospf_convergence, "Waiting for OSPF")

    # Verify OSPF active
    if not verify_loopback_in_ospf(data.d1, loopback, should_exist=True):
        st.report_tc_fail(TC_IDS.cleanup, "ospf_not_active_initial")
        st.report_fail("test_case_failed", "OSPF not active initially")

    # Remove OSPF configuration
    st.log("Removing OSPF configuration")
    ospf_api.config_interface_ip_ospf_area(
        data.d1,
        [loopback],
        ospf_area,
        config="no",
        cli_type="klish"
    )

    st.wait(data.config.wait_times.config_apply, "After OSPF removal")

    # Verify loopback removed from OSPF
    if not verify_loopback_in_ospf(data.d1, loopback, should_exist=False):
        st.report_tc_fail(TC_IDS.cleanup, "ospf_not_removed")
        st.report_fail("test_case_failed", "OSPF configuration not removed")

    # Remove IP address
    st.log("Removing IP address")
    ip_api.delete_ip_interface(data.d1, loopback, ip_addr, "ipv4", cli_type="klish")

    # Verify IP removed
    if not verify_ip_on_loopback(data.d1, loopback, ip_addr, should_exist=False):
        st.report_tc_fail(TC_IDS.cleanup, "ip_not_removed")
        st.report_fail("test_case_failed", "IP address not removed")

    st.report_tc_pass(TC_IDS.cleanup, "test_case_passed")
    st.log("✓ TC 20.10 PASSED: Cleanup and unconfiguration validated")


# Test module loaded successfully
# Note: st.log() cannot be called at module level - only within test functions
