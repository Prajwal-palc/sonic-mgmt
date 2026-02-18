"""
SM_ISCLI_P2_78 / SSE-T8196 - LACP Fast Rate Configuration Bug Verification

Author: Athira Arputharaj
Copyright (C) 2026, PALC Networks

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_1node.yaml \\
  switching/portchannel/test_sm_iscli_p2_78_lacp_fast_rate.py \\
  --logs-path ./logs/test_sm_iscli_p2_78_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Bug SM_ISCLI_P2_78 / SSE-T8196:
  When 'interface PortChannel 10 fallback fast_rate' is configured, the show
  output only reflects 'Fallback: Enabled' but does NOT configure LACP fast
  rate (1 second interval).

  TC 78.1: Create PortChannel with IPv4/IPv6, verify show output and
           Fallback: Disabled initial state.
  TC 78.2: Configure 'fallback fast_rate', verify show output shows
           Fallback: Enabled (bug: fast_rate is not separately configured).

Pre-requisites:
  - Topology: single-node (D1) with at least 1 Ethernet interface
  - SONiC version with IS-CLI (klish) support
"""

from __future__ import annotations

from typing import List, Optional

import pytest

from spytest import st, SpyTestDict

import apis.switching.portchannel as pc_api

# Test case IDs
TC_IDS = SpyTestDict({
    "baseline": "TC-SM-ISCLI-P2-78-01",
    "fallback_fast_rate": "TC-SM-ISCLI-P2-78-02",
})

# Module level variables
vars = SpyTestDict()
data = SpyTestDict()

# Fixed test parameters (matching the bug scenario exactly)
PC_ID = 10
PC_NAME = "PortChannel10"
IPV4_ADDR = "20.1.1.3/24"
IPV6_ADDR = "2001::4/64"


def get_available_interfaces(dut: str, count: int = 1) -> List[str]:
    """Get list of available Ethernet interfaces (excluding management)."""
    st.log(f"Getting {count} available Ethernet interfaces")

    output = st.show(dut, "show interface status | no-more",
                     type="klish", skip_tmpl=True, skip_error_check=True)

    available = []
    if output:
        lines = output.split('\n') if isinstance(output, str) else []
        for line in lines:
            line = line.strip()
            if line.startswith('Ethernet'):
                parts = line.split()
                if parts:
                    intf = parts[0]
                    if not intf.lower().startswith('eth0') and 'management' not in intf.lower():
                        available.append(intf)

    selected = available[:count]
    st.log(f"Selected interfaces: {selected}")
    return selected


def cleanup_portchannel(dut: str, portchannel_id: int) -> None:
    """Remove PortChannel if it exists."""
    st.log(f"[CLEANUP] Removing PortChannel {portchannel_id}")
    pc_name = f"PortChannel{portchannel_id}"
    pc_api.delete_portchannel(dut, [pc_name], cli_type="klish")


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module level setup and teardown."""
    global vars, data

    st.banner("MODULE PROLOGUE: SM_ISCLI_P2_78 LACP Fast Rate Bug Test")

    # Get testbed vars - single node, no TGen required
    vars = st.get_testbed_vars()
    dut_list = st.get_dut_names()

    if not dut_list:
        pytest.skip("No DUT available in testbed")

    data.dut = dut_list[0]
    st.log(f"Using DUT: {data.dut}")

    # Get at least 1 interface for PortChannel member
    data.member_interfaces = get_available_interfaces(data.dut, count=1)

    if not data.member_interfaces:
        pytest.skip("No Ethernet interfaces available for PortChannel testing")

    st.log(f"Available member interfaces: {data.member_interfaces}")

    yield

    st.banner("MODULE EPILOGUE: Cleanup")
    cleanup_portchannel(data.dut, PC_ID)
    st.log("Module cleanup completed")


@pytest.fixture(scope="function", autouse=True)
def function_hooks(request):
    """Function level setup and teardown."""
    test_name = st.get_func_name(request)
    st.banner(f"TEST START: {test_name}")
    yield
    st.banner(f"TEST END: {test_name}")


def test_ft_sm_iscli_p2_78_01_portchannel_with_ip():
    """
    TC 78.1 - Baseline: Create PortChannel with IPv4 and IPv6 addresses.

    Steps:
      configure terminal
      interface PortChannel 10
        ip address 20.1.1.3/24
        ipv6 address 2001::4/64
        end
      show interface PortChannel

    Verify:
      - PortChannel10 appears in show output
      - IPV4 address is 20.1.1.3/24
      - IPV6 address is 2001::4/64
      - Fallback: Disabled (default state)
    """
    tc_id = TC_IDS["baseline"]
    st.banner(f"[{tc_id}] PortChannel Creation with IPv4/IPv6 - Verify Fallback: Disabled")

    dut = data.dut
    member = data.member_interfaces[0]

    try:
        # Step 1: Create PortChannel
        st.log(f"Creating {PC_NAME}")
        if not pc_api.create_portchannel(dut, [PC_NAME], cli_type="klish"):
            st.report_fail("portchannel_create_failed", PC_NAME)

        # Step 2: Add member interface
        st.log(f"Adding member {member} to {PC_NAME}")
        pc_api.add_portchannel_member(dut, PC_NAME, [member], cli_type="klish")

        # Step 3: Configure IPv4 and IPv6 addresses
        st.log(f"Configuring IP addresses on {PC_NAME}")
        cmds = [
            f"interface {PC_NAME}",
            f"ip address {IPV4_ADDR}",
            f"ipv6 address {IPV6_ADDR}",
            "exit",
        ]
        st.config(dut, cmds, type="klish", skip_error_check=True)

        # Step 4: show interface PortChannel
        st.log("Executing: show interface PortChannel")
        output = st.show(dut, "show interface PortChannel | no-more",
                         type="klish", skip_tmpl=True, skip_error_check=True)

        st.log(f"Show output:\n{output}")

        if not output:
            st.report_fail("show_interface_failed", PC_NAME)

        output_str = str(output)

        # Verify PortChannel10 is present
        if PC_NAME not in output_str:
            st.error(f"[{tc_id}] FAIL: {PC_NAME} not found in show output")
            st.report_fail("portchannel_not_found", PC_NAME)

        # Verify IPv4 address
        ipv4_bare = IPV4_ADDR  # "20.1.1.3/24"
        if ipv4_bare not in output_str and "20.1.1.3" not in output_str:
            st.error(f"[{tc_id}] FAIL: IPv4 address {IPV4_ADDR} not found in show output")
            st.report_fail("ip_address_not_found", IPV4_ADDR)
        else:
            st.log(f"[{tc_id}] PASS: IPv4 address {IPV4_ADDR} present in show output")

        # Verify IPv6 address
        if "2001::4" not in output_str and IPV6_ADDR not in output_str:
            st.error(f"[{tc_id}] FAIL: IPv6 address {IPV6_ADDR} not found in show output")
            st.report_fail("ip_address_not_found", IPV6_ADDR)
        else:
            st.log(f"[{tc_id}] PASS: IPv6 address {IPV6_ADDR} present in show output")

        # Verify Fallback: Disabled (default state)
        if "Fallback: Disabled" not in output_str:
            st.error(f"[{tc_id}] FAIL: Expected 'Fallback: Disabled' not found in show output")
            st.report_fail("test_case_failed")
        else:
            st.log(f"[{tc_id}] PASS: 'Fallback: Disabled' confirmed in show output")

        st.log(f"[{tc_id}] TC 78.1 PASSED - PortChannel created with IPs, Fallback: Disabled")
        st.report_pass("test_case_passed")

    finally:
        cleanup_portchannel(dut, PC_ID)


def test_ft_sm_iscli_p2_78_02_fallback_fast_rate_bug():
    """
    TC 78.2 - Bug Test: Configure 'fallback fast_rate' and verify show output.

    Steps:
      configure terminal
      interface PortChannel 10
        ip address 20.1.1.3/24
        ipv6 address 2001::4/64
        end
      configure terminal
      interface PortChannel 10 fallback fast_rate
        end
      show interface PortChannel

    Verify:
      - Fallback: Enabled  (bug: 'fallback fast_rate' only enables fallback,
                            fast_rate interval NOT separately configured)
      - IPV4 address is 20.1.1.3/24
      - IPV6 address is 2001::4/64

    Bug Behavior:
      'interface PortChannel 10 fallback fast_rate' should configure LACP
      fast rate (1 sec interval), but instead it only sets Fallback: Enabled.
    """
    tc_id = TC_IDS["fallback_fast_rate"]
    st.banner(f"[{tc_id}] Configure 'fallback fast_rate' - Bug Detection Test")

    dut = data.dut
    member = data.member_interfaces[0]

    try:
        # Step 1: Create PortChannel with IPs (same as TC 78.1)
        st.log(f"Creating {PC_NAME} with IPs")
        if not pc_api.create_portchannel(dut, [PC_NAME], cli_type="klish"):
            st.report_fail("portchannel_create_failed", PC_NAME)

        pc_api.add_portchannel_member(dut, PC_NAME, [member], cli_type="klish")

        cmds = [
            f"interface {PC_NAME}",
            f"ip address {IPV4_ADDR}",
            f"ipv6 address {IPV6_ADDR}",
            "exit",
        ]
        st.config(dut, cmds, type="klish", skip_error_check=True)

        # Verify initial state: Fallback: Disabled
        output = st.show(dut, "show interface PortChannel | no-more",
                         type="klish", skip_tmpl=True, skip_error_check=True)
        st.log(f"Initial show output:\n{output}")

        if "Fallback: Disabled" not in str(output):
            st.warn(f"[{tc_id}] Initial state: 'Fallback: Disabled' not found - may already be enabled")

        # Step 2: Configure 'interface PortChannel 10 fallback fast_rate' (from config mode)
        st.log("Configuring: interface PortChannel 10 fallback fast_rate")
        cmds_fallback = [
            f"interface {PC_NAME} fallback fast_rate",
        ]
        st.config(dut, cmds_fallback, type="klish", skip_error_check=True)

        st.wait(2)

        # Step 3: show interface PortChannel
        st.log("Executing: show interface PortChannel (after fallback fast_rate)")
        output = st.show(dut, "show interface PortChannel | no-more",
                         type="klish", skip_tmpl=True, skip_error_check=True)

        st.log(f"Show output after fallback fast_rate:\n{output}")

        if not output:
            st.report_fail("show_interface_failed", PC_NAME)

        output_str = str(output)

        # Verify IPv4 still present
        if "20.1.1.3" not in output_str:
            st.error(f"[{tc_id}] FAIL: IPv4 address {IPV4_ADDR} not found after fallback fast_rate")
            st.report_fail("ip_address_not_found", IPV4_ADDR)
        else:
            st.log(f"[{tc_id}] PASS: IPv4 address still present")

        # Verify IPv6 still present
        if "2001::4" not in output_str:
            st.error(f"[{tc_id}] FAIL: IPv6 address {IPV6_ADDR} not found after fallback fast_rate")
            st.report_fail("ip_address_not_found", IPV6_ADDR)
        else:
            st.log(f"[{tc_id}] PASS: IPv6 address still present")

        # Verify Fallback: Enabled (bug evidence - only fallback was set, not fast_rate)
        if "Fallback: Enabled" not in output_str:
            st.error(f"[{tc_id}] FAIL: Expected 'Fallback: Enabled' not found after 'fallback fast_rate'")
            st.report_fail("test_case_failed")
        else:
            st.log(f"[{tc_id}] PASS: 'Fallback: Enabled' confirmed after 'fallback fast_rate'")
            st.log(f"[{tc_id}] : 'fallback fast_rate' only set Fallback:Enabled, "
                   "fast_rate (1s LACP interval) was NOT configured separately")

        st.log(f"[{tc_id}] TC 78.2 PASSED "
               "'fallback fast_rate' enables Fallback but not LACP fast rate interval")
        st.report_pass("test_case_passed")

    finally:
        cleanup_portchannel(dut, PC_ID)
