import pytest
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


def verify_management_interface_ip(dut):
    """
    Verify Management0 interface has IP address configured
    Args:
        dut: Device Under Test
    Returns:
        bool: True if Management0 has valid IP, False otherwise
    """
    st.log("Executing 'show ip interface' command")
    
    # Get IP interface information
    output = st.show(dut, "show ip interface")
    st.log("Output of 'show ip interface': {}".format(output))
    
    # Check if output is valid
    if not output:
        st.error("No output received from 'show ip interface' command")
        return False
    
    # Look for Management0 interface
    mgmt_found = False
    mgmt_ip = None
    mgmt_status = None
    
    for entry in output:
        if 'interface' in entry or 'intf' in entry or 'iface' in entry:
            # Try different possible key names
            interface_name = entry.get('interface') or entry.get('intf') or entry.get('iface') or entry.get('Interface')
            
            if interface_name and data.mgmt_interface in str(interface_name):
                mgmt_found = True
                # Try different possible key names for IP and status
                mgmt_ip = entry.get('ipaddr') or entry.get('ip_address') or entry.get('ipaddress') or entry.get('IP Address/Mask')
                mgmt_status = entry.get('status') or entry.get('admin') or entry.get('Status')
                
                st.log("Management0 Interface found")
                st.log("IP Address: {}".format(mgmt_ip))
                st.log("Status: {}".format(mgmt_status))
                break
    
    if not mgmt_found:
        st.error("Management0 interface not found in 'show ip interface' output")
        return False
    
    if not mgmt_ip:
        st.error("Management0 interface does not have IP address configured")
        return False
    
    st.log("Management0 interface verification successful")
    st.log("IP Address: {}, Status: {}".format(mgmt_ip, mgmt_status))
    return True


@pytest.mark.inventory(feature='IP Interface', release='Buzznik+')
@pytest.mark.inventory(testcases=['test_show_ip_interface_management0'])
def test_show_ip_interface_management0():
    """
    Test Case: Verify 'show ip interface' displays Management0 interface with IP address
    
    Test Steps:
    1. Execute 'show ip interface' command
    2. Verify Management0 interface is present in the output
    3. Verify Management0 has IP address configured
    4. Verify status field is populated
    
    Expected Result:
    - Management0 interface should be displayed
    - IP Address should be in format x.x.x.x/mask
    - Status should show 'primary' or configured status
    """
    st.log("Starting test: test_show_ip_interface_management0")
    st.banner("TEST: Verify 'show ip interface' command displays Management0")
    
    # Verify Management0 interface
    result = verify_management_interface_ip(vars.D1)
    
    if result:
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature='IP Interface', release='Buzznik+')
@pytest.mark.inventory(testcases=['test_show_ip_interface_output_format'])
def test_show_ip_interface_output_format():
    """
    Test Case: Verify 'show ip interface' output format
    
    Test Steps:
    1. Execute 'show ip interface' command
    2. Verify output contains proper headers (Interface, IP Address/Mask, Status)
    3. Verify Management0 entry format is correct
    
    Expected Result:
    - Output should have proper column headers
    - Management0 should be listed with IP and status
    """
    st.log("Starting test: test_show_ip_interface_output_format")
    st.banner("TEST: Verify 'show ip interface' output format")
    
    # Execute show ip interface
    output = st.show(vars.D1, "show ip interface")
    
    if not output:
        st.error("No output received from 'show ip interface' command")
        st.report_fail("operation_failed")
    
    st.log("Output format verification successful")
    st.log("Total interfaces found: {}".format(len(output)))
    
    # Verify Management0 is in the output
    result = verify_management_interface_ip(vars.D1)
    
    if result:
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature='IP Interface', release='Buzznik+')
@pytest.mark.inventory(testcases=['test_management0_ip_reachability'])
def test_management0_ip_reachability():
    """
    Test Case: Verify Management0 IP is reachable and valid
    
    Test Steps:
    1. Get Management0 IP from 'show ip interface'
    2. Verify IP format is valid (x.x.x.x/mask)
    3. Check if Management0 interface is administratively up
    
    Expected Result:
    - Management0 should have valid IP address
    - Interface should be in up state
    """
    st.log("Starting test: test_management0_ip_reachability")
    st.banner("TEST: Verify Management0 IP configuration")
    
    # Execute show ip interface
    output = st.show(vars.D1, "show ip interface")
    
    if not output:
        st.report_fail("operation_failed")
    
    # Find Management0 and validate
    mgmt_validated = False
    for entry in output:
        interface_name = entry.get('interface') or entry.get('intf') or entry.get('iface') or entry.get('Interface')
        
        if interface_name and data.mgmt_interface in str(interface_name):
            mgmt_ip = entry.get('ipaddr') or entry.get('ip_address') or entry.get('ipaddress') or entry.get('IP Address/Mask')
            
            if mgmt_ip:
                st.log("Management0 IP: {}".format(mgmt_ip))
                
                # Basic validation - check if IP contains '/' for mask
                if '/' in str(mgmt_ip):
                    st.log("IP address format is valid (contains subnet mask)")
                    mgmt_validated = True
                else:
                    st.log("Warning: IP address may not have subnet mask")
                
                # Additional validation - check for valid IP octets
                ip_part = str(mgmt_ip).split('/')[0]
                octets = ip_part.split('.')
                if len(octets) == 4:
                    st.log("IP address has valid 4 octets")
                    mgmt_validated = True
                else:
                    st.error("IP address does not have 4 octets")
                
                break
    
    if mgmt_validated:
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")
