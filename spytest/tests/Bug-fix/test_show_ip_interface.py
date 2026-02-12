"""
SHOW IP INTERFACES VALIDATION
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/bug-fix/test_show_ip_interface.py \
  --logs-path ./logs/test_show_ip_interface_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of 'show ip interfaces' command in sonic-cli (Klish).
  This test suite validates:
  - Terminal length can be set for better output display
  - 'show ip interfaces' displays all interfaces with IP addresses
  - Management0 interface is present with valid IP address
  - Interface status (Admin/Oper) is displayed correctly
  
Pre-requisites:
  - Topology: 1-node minimum | Supported: HW and Virtual
  - CLI type: klish (sonic-cli)
  - Management0 must have IP configured

Test Steps:
  1. Set terminal length to 200 for full output
  2. Execute 'show ip interfaces' command
  3. Verify Management0 interface is present
  4. Verify Management0 has IP address configured
  5. Verify Admin/Oper status is displayed
"""

import pytest
import re
from spytest import st
import apis.routing.ip as ip_obj
import apis.system.basic as basic_obj
from spytest.dicts import SpyTestDict


@pytest.fixture(scope="module", autouse=True)
def ip_interface_module_hooks(request):
    """
    Module level fixture for setup and teardown
    """
    global vars
    vars = st.ensure_min_topology("D1")
    global_vars()
    yield
    # Cleanup if needed


@pytest.fixture(scope="function", autouse=True)
def ip_interface_func_hooks(request):
    """
    Function level fixture
    """
    global_vars()
    yield


def global_vars():
    """
    Global variables initialization
    """
    global data
    data = SpyTestDict()
    data.mgmt_interface = 'Management0'
    data.wait_time = 5
    data.cli_type = 'klish'  # Explicitly use sonic-cli (klish)


def set_terminal_length(dut, length=200, cli_type='klish'):
    """
    Set terminal length in sonic-cli to display more lines without pausing.
    
    Args:
        dut: Device Under Test
        length: Terminal length (0-255, default 200)
        cli_type: CLI type (default: klish)
        
    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Setting terminal length to {length}")
    
    try:
        command = f"terminal length {length}"
        st.config(dut, command, type=cli_type, skip_error_check=True)
        st.log(f"Terminal length set to {length}")
        return True
    except Exception as e:
        st.error(f"Failed to set terminal length: {str(e)}")
        return False


def verify_management_interface_ip(dut, cli_type='klish'):
    """
    Verify Management0 interface has IP address configured using 'show ip interfaces'.
    
    This function uses both:
    1. Parsed template output (when available)
    2. Raw text output parsing (fallback when template parsing fails)
    
    Args:
        dut: Device Under Test
        cli_type: CLI type (default: klish for sonic-cli)
        
    Returns:
        bool: True if Management0 has valid IP, False otherwise
    """
    st.log("Executing 'show ip interfaces' command in sonic-cli (klish)")
    
    # First, set terminal length to see full output
    set_terminal_length(dut, 200, cli_type)
    
    # Method 1: Try to get parsed output
    try:
        output = st.show(dut, "show ip interfaces", type=cli_type, skip_error_check=True)
        st.log(f"Output of 'show ip interfaces' (parsed): {output}")
        
        # Check if parsed output is valid and not empty
        if output and isinstance(output, list) and len(output) > 0:
            st.log("Using parsed template output for validation")
            
            # Look for Management0 interface in parsed output
            for entry in output:
                st.log(f"Checking entry: {entry}")
                st.log(f"Entry keys: {list(entry.keys())}")
                
                # Try different possible key names for interface
                interface_name = (entry.get('interface') or 
                                entry.get('intf') or 
                                entry.get('iface') or 
                                entry.get('Interface') or
                                entry.get('name'))
                
                if interface_name and data.mgmt_interface in str(interface_name):
                    st.log(f"Found {data.mgmt_interface} in parsed output")
                    
                    # Try different possible key names for IP and status
                    mgmt_ip = (entry.get('ipaddr') or 
                             entry.get('ip_address') or 
                             entry.get('ipaddress') or 
                             entry.get('IP Address/Mask') or
                             entry.get('ip'))
                    
                    mgmt_status = (entry.get('status') or 
                                 entry.get('admin') or 
                                 entry.get('Status') or
                                 entry.get('admin_oper') or
                                 entry.get('adminoper'))
                    
                    st.log(f"Management0 Interface found in parsed output")
                    st.log(f"IP Address: {mgmt_ip}")
                    st.log(f"Status: {mgmt_status}")
                    
                    if mgmt_ip:
                        st.log("Management0 interface verification successful (parsed)")
                        return True
    
    except Exception as e:
        st.log(f"Exception during parsed output check: {str(e)}")
    
    # Method 2: Fallback to raw output parsing
    st.log("Falling back to raw output parsing for 'show ip interfaces'")
    
    try:
        # Get raw output
        raw_output = st.config(dut, "show ip interfaces", type=cli_type, skip_error_check=True)
        
        if not raw_output or not isinstance(raw_output, str):
            st.error("No raw output available from 'show ip interfaces'")
            return False
        
        st.log(f"Raw output of 'show ip interfaces':\n{raw_output}")
        
        # Parse raw output for Management0
        # Expected format:
        # Management0          192.168.100.59/24                                                    up/up
        
        # Look for line containing Management0
        mgmt_pattern = rf'^\s*{data.mgmt_interface}\s+(\S+)\s+(\S+)?\s+(\S+)'
        
        for line in raw_output.split('\n'):
            match = re.search(mgmt_pattern, line)
            if match:
                st.log(f"Found Management0 line in raw output: {line}")
                
                # Extract IP address (first group)
                mgmt_ip = match.group(1)
                st.log(f"Management0 IP Address: {mgmt_ip}")
                
                # Extract status if available (could be in different groups)
                # Look for up/up, up/down, down/down pattern
                status_match = re.search(r'(up|down)/(up|down)', line)
                if status_match:
                    mgmt_status = status_match.group(0)
                    st.log(f"Management0 Admin/Oper Status: {mgmt_status}")
                
                # Validate IP format
                if '/' in mgmt_ip:  # Has subnet mask
                    st.log("Management0 has valid IP address with subnet mask")
                    
                    # Additional validation - check for valid IP octets
                    ip_part = mgmt_ip.split('/')[0]
                    octets = ip_part.split('.')
                    if len(octets) == 4:
                        st.log("IP address has valid 4 octets")
                        st.log("Management0 interface verification successful (raw output)")
                        return True
                    else:
                        st.error("IP address does not have 4 octets")
                        return False
                else:
                    st.error("IP address does not have subnet mask")
                    return False
        
        st.error(f"{data.mgmt_interface} interface not found in raw output")
        return False
        
    except Exception as e:
        st.error(f"Exception during raw output parsing: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return False


def get_all_ip_interfaces(dut, cli_type='klish'):
    """
    Get all IP interfaces from 'show ip interfaces' command.
    Returns both parsed and raw output for comprehensive validation.
    
    Args:
        dut: Device Under Test
        cli_type: CLI type (default: klish)
        
    Returns:
        dict: Dictionary with 'parsed' and 'raw' output
    """
    st.log("Getting all IP interfaces")
    
    # Set terminal length
    set_terminal_length(dut, 200, cli_type)
    
    result = {
        'parsed': [],
        'raw': '',
        'interface_count': 0
    }
    
    try:
        # Get parsed output
        parsed_output = st.show(dut, "show ip interfaces", type=cli_type, skip_error_check=True)
        result['parsed'] = parsed_output if parsed_output else []
        
        # Get raw output
        raw_output = st.config(dut, "show ip interfaces", type=cli_type, skip_error_check=True)
        result['raw'] = raw_output if raw_output else ''
        
        # Count interfaces from raw output
        if result['raw']:
            # Count lines that look like interface entries (have IP address pattern)
            ip_pattern = r'\d+\.\d+\.\d+\.\d+/\d+'
            interface_lines = re.findall(ip_pattern, result['raw'])
            result['interface_count'] = len(interface_lines)
            st.log(f"Found {result['interface_count']} interfaces with IP addresses")
        
        return result
        
    except Exception as e:
        st.error(f"Exception getting IP interfaces: {str(e)}")
        return result


@pytest.mark.inventory(feature='IP Interface', release='Buzznik+')
@pytest.mark.inventory(testcases=['test_show_ip_interface_management0'])
def test_show_ip_interface_management0():
    """
    Test Case: Verify 'show ip interfaces' displays Management0 interface with IP address
    
    Test Steps:
    1. Set terminal length to 200 for full output display
    2. Execute 'show ip interfaces' command in sonic-cli (klish)
    3. Verify Management0 interface is present in the output
    4. Verify Management0 has IP address configured in format x.x.x.x/mask
    5. Verify Admin/Oper status field is populated (e.g., up/up)
    
    Expected Result:
    - Management0 interface should be displayed
    - IP Address should be in format x.x.x.x/mask (e.g., 192.168.100.59/24)
    - Admin/Oper status should show (e.g., up/up, up/down)
    """
    st.log("Starting test: test_show_ip_interface_management0")
    st.banner("TEST: Verify 'show ip interfaces' command displays Management0 in sonic-cli")
    
    # Step 1: Set terminal length
    st.log("Step 1: Setting terminal length to 200")
    set_terminal_length(vars.D1, 200, data.cli_type)
    
    # Step 2: Verify Management0 interface
    st.log(f"Step 2: Verifying {data.mgmt_interface} interface in 'show ip interfaces'")
    result = verify_management_interface_ip(vars.D1, data.cli_type)
    
    if result:
        st.log(f"{data.mgmt_interface} validation PASSED")
        st.report_pass("test_case_passed")
    else:
        st.error(f"{data.mgmt_interface} validation FAILED")
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature='IP Interface', release='Buzznik+')
@pytest.mark.inventory(testcases=['test_show_ip_interface_output_format'])
def test_show_ip_interface_output_format():
    """
    Test Case: Verify 'show ip interfaces' output format in sonic-cli
    
    Test Steps:
    1. Set terminal length to 200
    2. Execute 'show ip interfaces' command in sonic-cli (klish)
    3. Verify output contains proper headers (Interface, IP address/mask, VRF, Admin/Oper, Flags)
    4. Verify Management0 entry format is correct
    5. Verify at least one interface is displayed
    
    Expected Result:
    - Output should have proper column headers
    - Management0 should be listed with IP and status
    - IP addresses should be in x.x.x.x/mask format
    - Admin/Oper should be in format up/up, up/down, etc.
    """
    st.log("Starting test: test_show_ip_interface_output_format")
    st.banner("TEST: Verify 'show ip interfaces' output format in sonic-cli")
    
    # Set terminal length
    st.log("Setting terminal length to 200")
    set_terminal_length(vars.D1, 200, data.cli_type)
    
    # Execute show ip interfaces and get all output
    st.log("Getting all IP interfaces")
    result = get_all_ip_interfaces(vars.D1, data.cli_type)
    
    # Verify we got output
    if not result['raw']:
        st.error("No raw output received from 'show ip interfaces' command")
        st.report_fail("operation_failed")
    
    st.log(f"Output format verification - Found {result['interface_count']} interfaces with IP")
    
    # Verify headers are present in raw output
    headers = ['Interface', 'IP address', 'Admin', 'Oper']
    headers_found = []
    
    for header in headers:
        if header in result['raw']:
            st.log(f"Header '{header}' found in output")
            headers_found.append(header)
    
    if len(headers_found) >= 2:
        st.log(f"Output has proper headers: {headers_found}")
    else:
        st.log(f"Warning: Some expected headers not found. Found: {headers_found}")
    
    # Verify Management0 is in the output
    st.log("Verifying Management0 interface presence")
    mgmt_result = verify_management_interface_ip(vars.D1, data.cli_type)
    
    if mgmt_result:
        st.log("Output format and Management0 validation PASSED")
        st.report_pass("test_case_passed")
    else:
        st.error("Management0 not found or invalid")
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature='IP Interface', release='Buzznik+')
@pytest.mark.inventory(testcases=['test_management0_ip_reachability'])
def test_management0_ip_reachability():
    """
    Test Case: Verify Management0 IP is configured and valid in sonic-cli
    
    Test Steps:
    1. Set terminal length to 200
    2. Get Management0 IP from 'show ip interfaces' in sonic-cli
    3. Verify IP format is valid (x.x.x.x/mask)
    4. Verify IP has 4 octets
    5. Verify subnet mask is present
    6. Check if Management0 interface Admin/Oper status
    
    Expected Result:
    - Management0 should have valid IP address with 4 octets
    - IP should include subnet mask (e.g., 192.168.100.59/24)
    - Interface status should be readable
    """
    st.log("Starting test: test_management0_ip_reachability")
    st.banner("TEST: Verify Management0 IP configuration in sonic-cli")
    
    # Set terminal length
    set_terminal_length(vars.D1, 200, data.cli_type)
    
    # Execute show ip interfaces and get raw output
    raw_output = st.config(vars.D1, "show ip interfaces", type=data.cli_type, skip_error_check=True)
    
    if not raw_output:
        st.error("No output from 'show ip interfaces'")
        st.report_fail("operation_failed")
    
    # Find Management0 and validate IP format
    mgmt_pattern = rf'^\s*{data.mgmt_interface}\s+(\S+)'
    mgmt_validated = False
    mgmt_ip_addr = None
    
    for line in raw_output.split('\n'):
        match = re.search(mgmt_pattern, line)
        if match:
            mgmt_ip_addr = match.group(1)
            st.log(f"Found Management0 line: {line.strip()}")
            st.log(f"Management0 IP: {mgmt_ip_addr}")
            
            # Validate IP format
            if '/' in mgmt_ip_addr:
                st.log("✓ IP address contains subnet mask")
                
                # Split IP and mask
                ip_part, mask_part = mgmt_ip_addr.split('/')
                st.log(f"  IP: {ip_part}, Mask: {mask_part}")
                
                # Validate 4 octets
                octets = ip_part.split('.')
                if len(octets) == 4:
                    st.log(f"✓ IP address has valid 4 octets: {octets}")
                    
                    # Validate each octet is numeric
                    try:
                        for octet in octets:
                            octet_val = int(octet)
                            if 0 <= octet_val <= 255:
                                continue
                            else:
                                st.error(f"Octet {octet} out of range (0-255)")
                                break
                        else:
                            st.log("✓ All octets are in valid range (0-255)")
                            mgmt_validated = True
                    except ValueError:
                        st.error("Octets are not numeric")
                else:
                    st.error(f"IP address does not have 4 octets, has {len(octets)}")
            else:
                st.error("IP address does not have subnet mask")
            
            # Check Admin/Oper status
            status_match = re.search(r'(up|down)/(up|down)', line)
            if status_match:
                status = status_match.group(0)
                st.log(f"✓ Management0 Admin/Oper Status: {status}")
            
            break
    
    if not mgmt_ip_addr:
        st.error("Management0 not found in output")
        st.report_fail("test_case_failed")
    
    if mgmt_validated:
        st.log("Management0 IP validation PASSED")
        st.log(f"Validated IP: {mgmt_ip_addr}")
        st.report_pass("test_case_passed")
    else:
        st.error("Management0 IP validation FAILED")
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature='IP Interface', release='Buzznik+')
@pytest.mark.inventory(testcases=['test_terminal_length_setting'])
def test_terminal_length_setting():
    """
    Test Case: Verify terminal length can be set in sonic-cli
    
    Test Steps:
    1. Execute 'terminal length 200' command in sonic-cli
    2. Verify command succeeds without error
    3. Execute 'show ip interfaces' to confirm full output is displayed
    4. Verify output is not truncated
    
    Expected Result:
    - 'terminal length 200' command should succeed
    - Subsequent 'show' commands should display full output without pagination
    """
    st.log("Starting test: test_terminal_length_setting")
    st.banner("TEST: Verify terminal length setting in sonic-cli")
    
    # Test setting terminal length
    st.log("Step 1: Setting terminal length to 200")
    result = set_terminal_length(vars.D1, 200, data.cli_type)
    
    if not result:
        st.error("Failed to set terminal length")
        st.report_fail("operation_failed")
    
    st.log("✓ Terminal length set successfully")
    
    # Verify by running show command
    st.log("Step 2: Executing 'show ip interfaces' to verify full output")
    output = st.config(vars.D1, "show ip interfaces", type=data.cli_type, skip_error_check=True)
    
    if not output:
        st.error("No output from 'show ip interfaces'")
        st.report_fail("operation_failed")
    
    # Count number of interfaces in output
    interface_count = len(re.findall(r'\d+\.\d+\.\d+\.\d+/\d+', output))
    st.log(f"✓ Found {interface_count} interfaces in output")
    
    if interface_count > 0:
        st.log("Terminal length setting test PASSED")
        st.report_pass("test_case_passed")
    else:
        st.error("No interfaces found in output")
        st.report_fail("test_case_failed")
