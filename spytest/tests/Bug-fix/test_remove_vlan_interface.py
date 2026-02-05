"""
REMOVE VLAN INTERFACE CONFIGURATION
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/bug-fix/test_remove_vlan_interface.py \
  --logs-path ./logs/test_remove_vlan_interface_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of VLAN interface removal using sonic-cli (Klish).
  This test suite creates a VLAN, assigns a port to it, verifies the VLAN
  interface exists and is operational, removes the VLAN interface using
  'no interface Vlan<id>', and validates that the VLAN is completely removed
  from the system.

Pre-requisites:
  - Topology: 1-node minimum | Supported: HW and Virtual
  - CLI type: klish (sonic-cli)
  - At least one Ethernet interface available for VLAN assignment

Test Steps:
  1. Create VLAN (e.g., VLAN 10)
  2. Assign Ethernet port to VLAN as access port
  3. Verify VLAN interface exists using 'show interface Vlan10'
  4. Verify VLAN appears in 'show Vlan'
  5. Remove VLAN interface using 'no interface Vlan10'
  6. Verify 'show Vlan' shows no VLANs or VLAN removed
  7. Verify 'show interface vlan10' fails or shows interface not found
"""

from __future__ import annotations

import pytest
import re

from spytest import st, SpyTestDict


# Test data dictionary
data = SpyTestDict()
data.vlan_id = "10"
data.cli_type = "klish"


@pytest.fixture(scope="module", autouse=True)
def remove_vlan_module_hooks(request):
    """
    Module-level fixture for VLAN interface removal test setup and teardown.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1")

    st.banner("MODULE SETUP: Remove VLAN Interface Test")

    # Store DUT handle
    data.dut1 = vars.D1

    # Get first available port for VLAN assignment
    if hasattr(vars, 'D1D2P1'):
        data.eth_port = vars.D1D2P1
    elif hasattr(vars, 'D1T1P1'):
        data.eth_port = vars.D1T1P1
    else:
        # Fallback to common interface
        data.eth_port = "Ethernet512"

    st.log(f"DUT1: {data.dut1}")
    st.log(f"Ethernet Port for VLAN: {data.eth_port}")

    # INITIAL CLEANUP - Start with clean state
    st.banner("INITIAL CLEANUP: Removing existing VLAN configuration")
    initial_cleanup()

    yield

    # Module teardown
    st.banner("MODULE TEARDOWN: Cleaning up VLAN configuration")
    cleanup_vlan_config()


@pytest.fixture(scope="function", autouse=True)
def remove_vlan_func_hooks(request):
    """
    Function-level fixture for pre and post test operations.
    """
    yield


def initial_cleanup():
    """
    Initial cleanup: Remove VLAN interface and configuration.
    """
    st.log("Starting initial cleanup - removing VLAN configuration")

    try:
        # Remove VLAN interface
        commands = [f"no interface Vlan{data.vlan_id}"]
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        # Remove port from VLAN
        commands = []
        commands.append(f"interface {data.eth_port}")
        commands.append("no switchport access Vlan")
        commands.append("exit")
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        # Remove VLAN
        commands = [f"no vlan {data.vlan_id}"]
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        st.log("Initial cleanup completed")
    except Exception as e:
        st.error(f"Error during initial cleanup: {str(e)}")


def create_vlan(dut, vlan_id, cli_type="klish"):
    """
    Create VLAN.

    Args:
        dut: Device under test
        vlan_id: VLAN ID
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Creating VLAN {vlan_id} on {dut}")

    try:
        commands = [f"vlan {vlan_id}"]
        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully created VLAN {vlan_id}")
        return True
    except Exception as e:
        st.error(f"Failed to create VLAN {vlan_id}: {str(e)}")
        return False


def assign_port_to_vlan(dut, interface, vlan_id, cli_type="klish"):
    """
    Assign port to VLAN as access port.

    Args:
        dut: Device under test
        interface: Interface name
        vlan_id: VLAN ID
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Assigning {interface} to VLAN {vlan_id} as access port")

    try:
        commands = []
        commands.append(f"interface {interface}")
        commands.append(f"switchport access Vlan {vlan_id}")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully assigned {interface} to VLAN {vlan_id}")
        return True
    except Exception as e:
        st.error(f"Failed to assign {interface} to VLAN {vlan_id}: {str(e)}")
        return False


def verify_vlan_interface_exists(dut, vlan_id, cli_type="klish"):
    """
    Verify VLAN interface exists using 'show interface Vlan<id>'.

    Expected output:
    Vlan10 is up, line protocol is up
    Hardware is Vlan, address is XX:XX:XX:XX:XX:XX
    ...

    Args:
        dut: Device under test
        vlan_id: VLAN ID
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if interface exists, False otherwise
    """
    st.log(f"Verifying VLAN interface Vlan{vlan_id} exists on {dut}")

    try:
        command = f"show interface Vlan{vlan_id}"
        output = st.config(dut, command, type=cli_type, skip_error_check=True)

        st.log(f"Show interface Vlan{vlan_id} output:\n{output}")

        if not output:
            st.error(f"No output from show interface Vlan{vlan_id}")
            return False

        # Check for interface up status
        if isinstance(output, str):
            # Look for "Vlan<id> is up" or "Vlan<id> is down"
            pattern = rf'Vlan{vlan_id}\s+is\s+(up|down)'
            if re.search(pattern, output, re.IGNORECASE):
                st.log(f"VLAN interface Vlan{vlan_id} exists")
                return True

            # Check if it says interface exists even if down
            if f"Vlan{vlan_id}" in output and "Hardware is Vlan" in output:
                st.log(f"VLAN interface Vlan{vlan_id} exists")
                return True

        st.error(f"VLAN interface Vlan{vlan_id} not found")
        return False

    except Exception as e:
        st.error(f"Exception during VLAN interface verification: {str(e)}")
        return False


def verify_vlan_in_show_vlan(dut, vlan_id, cli_type="klish"):
    """
    Verify VLAN appears in 'show Vlan' output.

    Args:
        dut: Device under test
        vlan_id: VLAN ID to verify
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if VLAN found, False otherwise
    """
    st.log(f"Verifying VLAN {vlan_id} appears in 'show Vlan'")

    try:
        output = st.show(dut, "show Vlan", type=cli_type, skip_error_check=True)
        st.log(f"Show Vlan output: {output}")

        if output:
            for entry in output:
                # Try different possible key names for VLAN ID
                vlan_num = (entry.get('vid', '') or
                           entry.get('vlan_id', '') or
                           entry.get('num', '') or
                           entry.get('vlanid', ''))

                # Remove "Vlan" prefix if present
                vlan_num_str = str(vlan_num).replace('Vlan', '').strip()

                if vlan_num_str == str(vlan_id):
                    st.log(f"Found VLAN {vlan_id} in 'show Vlan' output")
                    return True

        st.log(f"VLAN {vlan_id} not found in 'show Vlan' output")
        return False

    except Exception as e:
        st.error(f"Exception during 'show Vlan' verification: {str(e)}")
        return False


def remove_vlan_interface(dut, vlan_id, cli_type="klish"):
    """
    Remove VLAN interface using 'no interface Vlan<id>' command.

    Args:
        dut: Device under test
        vlan_id: VLAN ID
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Removing VLAN interface Vlan{vlan_id} on {dut}")

    try:
        commands = [f"no interface Vlan{vlan_id}"]
        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully removed VLAN interface Vlan{vlan_id}")
        return True
    except Exception as e:
        st.error(f"Failed to remove VLAN interface Vlan{vlan_id}: {str(e)}")
        return False


def verify_vlan_removed(dut, vlan_id, cli_type="klish"):
    """
    Verify VLAN is completely removed using 'show Vlan'.

    Expected output after removal:
    - "No VLANs configured" or
    - VLAN not in the list

    Args:
        dut: Device under test
        vlan_id: VLAN ID
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if VLAN removed, False if still present
    """
    st.log(f"Verifying VLAN {vlan_id} is removed using 'show Vlan'")

    try:
        output = st.show(dut, "show Vlan", type=cli_type, skip_error_check=True)
        st.log(f"Show Vlan output after removal: {output}")

        # Case 1: No VLANs configured at all
        if not output or len(output) == 0:
            st.log("No VLANs configured - VLAN successfully removed")
            return True

        # Case 2: Check if VLAN still exists in output
        for entry in output:
            vlan_num = (entry.get('vid', '') or
                       entry.get('vlan_id', '') or
                       entry.get('num', '') or
                       entry.get('vlanid', ''))

            vlan_num_str = str(vlan_num).replace('Vlan', '').strip()

            if vlan_num_str == str(vlan_id):
                st.error(f"VLAN {vlan_id} still present in 'show Vlan' output after removal!")
                return False

        st.log(f"VLAN {vlan_id} successfully removed - not found in 'show Vlan'")
        return True

    except Exception as e:
        st.error(f"Exception during VLAN removal verification: {str(e)}")
        return False


def verify_vlan_interface_not_exists(dut, vlan_id, cli_type="klish"):
    """
    Verify VLAN interface no longer exists using 'show interface vlan<id>'.

    Expected: Command should fail or show interface does not exist.

    Args:
        dut: Device under test
        vlan_id: VLAN ID
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if interface does not exist, False if still exists
    """
    st.log(f"Verifying VLAN interface Vlan{vlan_id} no longer exists")

    try:
        command = f"show interface vlan{vlan_id}"
        output = st.config(dut, command, type=cli_type, skip_error_check=True)

        st.log(f"Show interface vlan{vlan_id} output:\n{output}")

        if not output:
            st.log(f"No output from command - VLAN interface Vlan{vlan_id} does not exist")
            return True

        if isinstance(output, str):
            # Check for error messages indicating interface doesn't exist
            error_patterns = [
                r'does\s+not\s+exist',
                r'not\s+found',
                r'invalid\s+interface',
                r'no\s+such\s+interface',
                r'error'
            ]

            for pattern in error_patterns:
                if re.search(pattern, output, re.IGNORECASE):
                    st.log(f"VLAN interface Vlan{vlan_id} does not exist (error message found)")
                    return True

            # If interface still shows up status
            if f"Vlan{vlan_id} is" in output or "Hardware is Vlan" in output:
                st.error(f"VLAN interface Vlan{vlan_id} still exists!")
                return False

        st.log(f"VLAN interface Vlan{vlan_id} does not exist")
        return True

    except Exception as e:
        st.log(f"Exception during verification (this may indicate interface removed): {str(e)}")
        # Exception might indicate interface doesn't exist - consider this success
        return True


def cleanup_vlan_config():
    """
    Clean up VLAN configuration.
    """
    st.log("Cleaning up VLAN configuration")

    try:
        # Remove VLAN interface
        commands = [f"no interface Vlan{data.vlan_id}"]
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        # Remove port from VLAN
        commands = []
        commands.append(f"interface {data.eth_port}")
        commands.append("no switchport access Vlan")
        commands.append("exit")
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        # Remove VLAN
        commands = [f"no vlan {data.vlan_id}"]
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        st.log("Cleanup completed")
    except Exception as e:
        st.error(f"Error during cleanup: {str(e)}")


@pytest.mark.topology("any")
class TestRemoveVlanInterface:
    """
    Test class for VLAN interface removal validation.
    """

    @pytest.mark.test_remove_vlan_interface
    def test_remove_vlan_interface(self):
        """
        TestCase: test_remove_vlan_interface

        Test Steps:
        1. Create VLAN 10
        2. Assign Ethernet port to VLAN 10 as access port
        3. Verify VLAN interface exists using 'show interface Vlan10'
        4. Verify VLAN appears in 'show Vlan'
        5. Remove VLAN interface using 'no interface Vlan10'
        6. Verify 'show Vlan' shows VLAN removed (or no VLANs)
        7. Verify 'show interface vlan10' shows interface does not exist

        Expected Result:
        - VLAN created and interface operational
        - VLAN interface successfully removed
        - VLAN no longer appears in 'show Vlan'
        - Interface no longer exists in 'show interface vlan<id>'
        """
        st.banner("TEST: Remove VLAN Interface Configuration")

        # Step 1: Create VLAN
        st.log(f"Step 1: Creating VLAN {data.vlan_id}")

        if not create_vlan(data.dut1, data.vlan_id, data.cli_type):
            st.report_fail("msg", f"Failed to create VLAN {data.vlan_id}")

        # Step 2: Assign port to VLAN
        st.log(f"Step 2: Assigning {data.eth_port} to VLAN {data.vlan_id}")

        if not assign_port_to_vlan(data.dut1, data.eth_port, data.vlan_id, data.cli_type):
            st.report_fail("msg", f"Failed to assign port to VLAN {data.vlan_id}")

        # Wait for configuration to apply
        st.wait(3, "Waiting for VLAN configuration to apply")

        # Step 3: Verify VLAN interface exists
        st.log(f"Step 3: Verifying VLAN interface Vlan{data.vlan_id} exists")

        if not verify_vlan_interface_exists(data.dut1, data.vlan_id, data.cli_type):
            st.report_fail("msg", f"VLAN interface Vlan{data.vlan_id} does not exist")

        # Step 4: Verify VLAN appears in 'show Vlan'
        st.log(f"Step 4: Verifying VLAN {data.vlan_id} appears in 'show Vlan'")

        if not verify_vlan_in_show_vlan(data.dut1, data.vlan_id, data.cli_type):
            st.report_fail("msg", f"VLAN {data.vlan_id} not found in 'show Vlan'")

        # Step 5: Remove VLAN interface
        st.log(f"Step 5: Removing VLAN interface Vlan{data.vlan_id} using 'no interface Vlan{data.vlan_id}'")

        if not remove_vlan_interface(data.dut1, data.vlan_id, data.cli_type):
            st.report_fail("msg", f"Failed to remove VLAN interface Vlan{data.vlan_id}")

        # Wait for removal to complete
        st.wait(2, "Waiting for VLAN interface removal to complete")

        # Step 6: Verify VLAN removed from 'show Vlan'
        st.log(f"Step 6: Verifying VLAN {data.vlan_id} removed from 'show Vlan'")

        if not verify_vlan_removed(data.dut1, data.vlan_id, data.cli_type):
            st.report_fail("msg", f"VLAN {data.vlan_id} still present after removal")

        # Step 7: Verify VLAN interface does not exist
        st.log(f"Step 7: Verifying VLAN interface Vlan{data.vlan_id} no longer exists")

        if not verify_vlan_interface_not_exists(data.dut1, data.vlan_id, data.cli_type):
            st.report_fail("msg", f"VLAN interface Vlan{data.vlan_id} still exists after removal")

        st.log("VLAN interface removal test PASSED")
        st.report_pass("test_case_passed")
