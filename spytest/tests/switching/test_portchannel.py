import pytest
from spytest import st, SpyTestDict

import apis.switching.portchannel as portchannel_obj
import apis.switching.vlan as vlan_obj
import apis.system.interface as intf_obj
import apis.system.logging as slog
from apis.system.reboot import config_save, config_save_reload
import apis.system.lldp as lldp_obj
import apis.system.basic as basic_obj
import apis.routing.ip as ip_obj
import apis.routing.arp as arp_obj
import apis.system.port as port_obj
import apis.system.rest as rest_obj

from utilities.parallel import exec_all, exec_parallel, ensure_no_exception
from utilities.common import ExecAllFunc
from utilities.common import random_vlan_list, poll_wait

vars = dict()
data = SpyTestDict()


@pytest.fixture(scope="module", autouse=True)
def portchannel_module_hooks(request):
    # add things at the start of this module
    global vars
    data.module_unconfig = False
    data.portchannel_name = "PortChannel7"
    data.portchannel_name2 = "PortChannel8"
    data.vlan = (random_vlan_list(count=2))
    data.vid = data.vlan[0]
    data.vlan_id = data.vlan[1]
    data.cli_type_click = "click"
    vars = st.ensure_min_topology("D1D2:4")
    data.lag_up = 'Up'
    data.lag_down = 'Dw'
    data.graceful_restart_config = False
    data.my_dut_list = st.get_dut_names()[0:2]
    data.dut1 = st.get_dut_names()[0]
    data.dut2 = st.get_dut_names()[1]
    data.members_dut1 = [vars.D1D2P1, vars.D1D2P2, vars.D1D2P3, vars.D1D2P4]
    data.members_dut2 = [vars.D2D1P1, vars.D2D1P2, vars.D2D1P3, vars.D2D1P4]
    data.rest_url = "/restconf/data/sonic-portchannel:sonic-portchannel"
    exec_all(True, [[dut_config]], first_on_main=True)
    yield
    module_unconfig()

def dut_config():
    st.log('Creating port-channel and adding members in both DUTs')
    portchannel_obj.config_portchannel(data.dut1, data.dut2, data.portchannel_name, data.members_dut1,
                                           data.members_dut2, "add")
    st.log('Creating random VLAN in both the DUTs')
    if False in create_vlan_using_thread([vars.D1, vars.D2], [[data.vid], [data.vid]]):
        st.report_fail('vlan_create_fail', data.vid)
    st.log('Adding Port-Channel as tagged member to the random VLAN')
    if False in add_vlan_member_using_thread([vars.D1, vars.D2], [data.vid, data.vid],
                                        [[data.portchannel_name], [data.portchannel_name]]):
        st.report_fail('vlan_tagged_member_fail', data.portchannel_name, data.vid)


def module_unconfig():
    if not data.module_unconfig:
        data.module_unconfig = True
        st.log('Module config Cleanup')
        vlan_obj.clear_vlan_configuration([data.dut1, data.dut2])
        portchannel_obj.clear_portchannel_configuration([data.dut1, data.dut2])



@pytest.fixture(scope="function", autouse=True)
def portchannel_func_hooks(request):
    if st.get_func_name(request) == 'test_ft_portchannel_with_vlan_variations':
        dict1 = {"portchannel": data.portchannel_name, "members": [data.members_dut1[2],
                                            data.members_dut1[3]], "flag": 'del'}
        dict2 = {"portchannel": data.portchannel_name, "members": [data.members_dut2[2],
                                            data.members_dut2[3]], "flag": 'del'}
        output = exec_parallel(True, [vars.D1, vars.D2], portchannel_obj.add_del_portchannel_member, [dict1, dict2])
        ensure_no_exception(output[1])
    yield
    if st.get_func_name(request) == 'test_ft_portchannel_with_vlan_variations':
        dict1 = {"portchannel": data.portchannel_name, "members": [data.members_dut1[2],
                                                                   data.members_dut1[3]], "flag": 'add'}
        dict2 = {"portchannel": data.portchannel_name, "members": [data.members_dut2[2],
                                                                   data.members_dut2[3]], "flag": 'add'}
        output = exec_parallel(True, [vars.D1, vars.D2], portchannel_obj.add_del_portchannel_member, [dict1, dict2])
        ensure_no_exception(output[1])

def graceful_restart_prolog():
    dict1 = {'portchannel': data.portchannel_name, 'members': [vars.D1D2P3, vars.D1D2P4]}
    dict2 = {'portchannel': data.portchannel_name, 'members': [vars.D2D1P3, vars.D2D1P4]}
    exceptions = exec_parallel(True, [vars.D1, vars.D2], portchannel_obj.delete_portchannel_member, [dict1, dict2])[1]
    ensure_no_exception(exceptions)
    dict1 = {'portchannel_list': data.portchannel_name2}
    dict2 = {'portchannel_list': data.portchannel_name2}
    exceptions = exec_parallel(True, [vars.D1, vars.D2], portchannel_obj.create_portchannel, [dict1, dict2])[1]
    ensure_no_exception(exceptions)
    dict1 = {'portchannel': data.portchannel_name2, 'members': [vars.D1D2P3, vars.D1D2P4]}
    dict2 = {'portchannel': data.portchannel_name2, 'members': [vars.D2D1P3, vars.D2D1P4]}
    exceptions = exec_parallel(True, [vars.D1, vars.D2], portchannel_obj.add_portchannel_member, [dict1, dict2])[1]
    ensure_no_exception(exceptions)


def verify_portchannel_status(delay=2):
    dict1 = {'portchannel': data.portchannel_name, 'members_list': data.members_dut1, 'iter_delay': delay}
    dict2 = {'portchannel': data.portchannel_name, 'members_list': data.members_dut2, 'iter_delay': delay}
    output = exec_parallel(True, [vars.D1, vars.D2], verify_portchannel_cum_member_status, [dict1, dict2])
    ensure_no_exception(output[1])

def create_vlan_using_thread(dut_list, vlan_list, thread = True):
    sub_list = [[vlan_obj.create_vlan, dut, vlan_list[cnt]] for cnt, dut in enumerate(dut_list, start=0)]
    [output, exceptions] = exec_all(thread, sub_list)
    ensure_no_exception(exceptions)
    return output


def add_vlan_member_using_thread(dut_list, vlan_list, port_list, tagged = True):
    sub_list = []
    sub_list.append([vlan_obj.add_vlan_member, dut_list[0], vlan_list[0], port_list[0], tagged, False])
    sub_list.append([vlan_obj.add_vlan_member, dut_list[1], vlan_list[1], port_list[1], tagged, False])
    [output, exceptions] = exec_all(True, sub_list)
    ensure_no_exception(exceptions)
    return output

def verify_portchannel_cum_member_status(dut, portchannel, members_list, iter_count=10, iter_delay=2, state='up'):
    i = 1
    while i <= iter_count:
        st.log("Checking iteration {}".format(i))
        st.wait(iter_delay)
        if not portchannel_obj.verify_portchannel_member_state(dut, portchannel, members_list, state='up'):
            i += 1
            if i == iter_count:
                st.report_fail("portchannel_member_verification_failed", portchannel, dut, members_list)
        else:
            break


def check_lldp_neighbors(dut, port, ipaddress, hostname):
    try:
        lldp_value = lldp_obj.get_lldp_neighbors(dut, interface=port)[0]
    except Exception:
        st.error("No LLDP entries are found")
        return False
    lldp_value_dut2 = lldp_value['chassis_mgmt_ip']
    try:
        if not ipaddress[0] == lldp_value_dut2 :
            st.error("Entries are not matching")
            return False
    except Exception:
        st.error("Entries are not matching")
        return False
    lldp_value_hostname = lldp_value['chassis_name']
    if not hostname == lldp_value_hostname:
        st.error("Host name is not matching")
        return False
    return True

def get_mgmt_ip_using_thread(dut_list, mgmt_list, thread=True):
    sub_list = [[basic_obj.get_ifconfig_inet, dut, mgmt_list[cnt]] for cnt, dut in enumerate(dut_list, start=0)]
    [output, exceptions] = exec_all(thread, sub_list)
    ensure_no_exception(exceptions)
    return output

def get_hostname_using_thread(dut_list, thread=True):
    sub_list = [[basic_obj.get_hostname, dut] for dut in dut_list]
    [output, exceptions] = exec_all(thread, sub_list)
    ensure_no_exception(exceptions)
    return output

def verify_portchannel_rest(dut,json_data):
    get_resp = rest_obj.get_rest(dut,rest_url=data.rest_url)
    return rest_obj.verify_rest(get_resp["output"],json_data)

def verify_graceful_restart_syslog(dut):
    count_msg1 = slog.get_logging_count(dut, severity="NOTICE", filter_list=[
        "teamd#teammgrd: :- sig_handler: --- Received SIGTERM. Terminating PortChannels gracefully"])
    count_msg2 = slog.get_logging_count(dut, severity="NOTICE",
                           filter_list=["teamd#teammgrd: :- sig_handler: --- PortChannels terminated gracefully"])
    if not (count_msg1 == 1 and count_msg2 == 1):
        st.error('SYSLOG message is not observed for graceful restart')
        return False
    return True


def test_ft_member_state_after_interchanged_the_members_across_portchannels():
    """
    Author: vishnuvardhan.talluri@broadcom.com
    scenario; Verify that the LAG members in DUT are not UP when LAG members between two different Lags are
    interchanged
    :return:
    """
    verify_portchannel_status()
    portchannel_name_second = "PortChannel102"
    result_state = True

    # Remove 2 members from portchannel
    dict1 = {'portchannel': data.portchannel_name, 'members': data.members_dut1[2:]}
    dict2 = {'portchannel': data.portchannel_name, 'members': data.members_dut2[2:]}
    output = exec_parallel(True, [vars.D1, vars.D2], portchannel_obj.delete_portchannel_member, [dict1, dict2])
    ensure_no_exception(output[1])
    # add second portchannel
    portchannel_obj.config_portchannel(data.dut1, data.dut2, portchannel_name_second, data.members_dut1[2:],
                                       data.members_dut2[2:], "add")
    dict1 = {'interfaces': portchannel_name_second, 'operation': "startup", 'skip_verify': True}
    output = exec_parallel(True, [vars.D1, vars.D2], intf_obj.interface_operation, [dict1, dict1])
    ensure_no_exception(output[1])
    if not (output[0][0] and output[0][1]):
        st.report_fail('interface_admin_startup_fail', portchannel_name_second)
    #Verify portchannel is up
    dict1 = {'portchannel': portchannel_name_second, 'members': data.members_dut1[2:]}
    dict2 = {'portchannel': portchannel_name_second, 'members': data.members_dut2[2:]}
    output = exec_parallel(True, [vars.D1, vars.D2], portchannel_obj.verify_portchannel_and_member_status, [dict1, dict2])
    ensure_no_exception(output[1])
    if not (output[0][0] and output[0][1]):
        result_state = False
    # Interchange ports from one portchannel to another portchannel
    portchannel_obj.delete_portchannel_member(data.dut1, data.portchannel_name, data.members_dut1[0])
    portchannel_obj.delete_portchannel_member(data.dut1, portchannel_name_second, data.members_dut1[2])
    # Wait 3 times the lacp long timeout period to allow dut members to go down
    st.wait(90)
    output1 = portchannel_obj.verify_portchannel_member_state(data.dut2, data.portchannel_name, data.members_dut2[0], "down")
    if not output1:
        output1 = portchannel_obj.verify_portchannel_member_state(data.dut2, data.portchannel_name,
                                                                  data.members_dut2[0], "down")
    output2 = portchannel_obj.verify_portchannel_member_state(data.dut2, portchannel_name_second, data.members_dut2[2], "down")
    if not (output1 and output2):
        result_state = False
    # swapping the ports in DUT1 only
    output1 = portchannel_obj.add_portchannel_member(data.dut1, data.portchannel_name, data.members_dut1[2])
    output2 = portchannel_obj.add_portchannel_member(data.dut1, portchannel_name_second, data.members_dut1[0])
    if not (output1 and output2):
        result_state = False
    # Wait for few seconds after converge and ensure member ports states proper
    st.wait(5)
    # Verify portchannel member state with provided state
    dict1 = {'portchannel': data.portchannel_name, 'members_list': data.members_dut1[2], 'state': "down"}
    dict2 = {'portchannel': data.portchannel_name, 'members_list': data.members_dut2[0], 'state': "down"}
    output = exec_parallel(True, [vars.D1, vars.D2], portchannel_obj.verify_portchannel_member_state, [dict1, dict2])
    ensure_no_exception(output[1])
    if not (output[0][0] and output[0][1]):
        result_state = False
    dict1 = {'portchannel': portchannel_name_second, 'members_list': data.members_dut1[0], 'state': "down"}
    dict2 = {'portchannel': portchannel_name_second, 'members_list': data.members_dut2[2], 'state': "down"}
    output = exec_parallel(True, [vars.D1, vars.D2], portchannel_obj.verify_portchannel_member_state, [dict1, dict2])
    ensure_no_exception(output[1])
    if not (output[0][0] and output[0][1]):
        result_state = False
    dict1 = {'portchannel': data.portchannel_name, 'members_list': data.members_dut1[1]}
    dict2 = {'portchannel': data.portchannel_name, 'members_list': data.members_dut2[1]}
    output = exec_parallel(True, [vars.D1, vars.D2], portchannel_obj.verify_portchannel_member_state, [dict1, dict2])
    ensure_no_exception(output[1])
    if not (output[0][0] and output[0][1]):
        result_state = False
    dict1 = {'portchannel': portchannel_name_second, 'members_list': data.members_dut1[3]}
    dict2 = {'portchannel': portchannel_name_second, 'members_list': data.members_dut2[3]}
    output = exec_parallel(True, [vars.D1, vars.D2], portchannel_obj.verify_portchannel_member_state, [dict1, dict2])
    ensure_no_exception(output[1])
    if not (output[0][0] and output[0][1]):
        result_state = False
    # ensuring module config
    portchannel_obj.config_portchannel(data.dut1, data.dut2, portchannel_name_second,
                                       [data.members_dut1[0], data.members_dut1[3]], data.members_dut2[2:], 'delete')
    dict1 = {'portchannel': data.portchannel_name,
             'members': [data.members_dut1[0], data.members_dut1[3]]}
    dict2 = {'portchannel': data.portchannel_name, 'members': data.members_dut2[2:]}
    output = exec_parallel(True, [vars.D1, vars.D2], portchannel_obj.add_portchannel_member, [dict1, dict2])
    ensure_no_exception(output[1])
    if not (output[0][0] and output[0][1]):
        result_state = False
    if result_state:
        st.report_pass("operation_successful")
    else:
        st.report_fail("portchannel_member_state_failed")


@pytest.mark.portchannel_with_vlan_variations
@pytest.mark.community
@pytest.mark.community_pass
def test_ft_portchannel_with_vlan_variations():
    '''
    Author: Jagadish <pchvsai.durga@broadcom.com>
    This test case covers below test scenarios/tests
    FtOpSoSwLagFn041 : Verify that port-channel is up or not when port-channel created followed by add it to VLAN and
    then making the port-channel up.
    FtOpSoSwLagFn042 : Verify that port-channel is up when port-channel is created, making the port-channel up and then
    adding the port-channel to VLAN
    '''
    dict1 = {'portchannel': data.portchannel_name, 'members_list': [data.members_dut1[0], data.members_dut1[1]]}
    dict2 = {'portchannel': data.portchannel_name, 'members_list': [data.members_dut2[0], data.members_dut2[1]]}
    output = exec_parallel(True, [vars.D1, vars.D2], verify_portchannel_cum_member_status, [dict1, dict2])
    ensure_no_exception(output[1])
    portchannel_obj.config_portchannel(data.dut1, data.dut2, data.portchannel_name2, [data.members_dut1[2], data.members_dut1[3]],
                                           [data.members_dut2[2], data.members_dut2[3]], "add")
    dict1 = {'portchannel': data.portchannel_name2, 'members_list': [data.members_dut1[2], data.members_dut1[3]]}
    dict2 = {'portchannel': data.portchannel_name2, 'members_list': [data.members_dut2[2], data.members_dut2[3]]}
    output = exec_parallel(True, [vars.D1, vars.D2], verify_portchannel_cum_member_status, [dict1, dict2])
    ensure_no_exception(output[1])
    vlan_obj.create_vlan_and_add_members(vlan_data=[{"dut": [vars.D1,vars.D2], "vlan_id":data.vlan_id, "tagged":data.portchannel_name2}])
    dict1 = {'portchannel': data.portchannel_name2, 'members_list': [data.members_dut1[2], data.members_dut1[3]]}
    dict2 = {'portchannel': data.portchannel_name2, 'members_list': [data.members_dut2[2], data.members_dut2[3]]}
    output = exec_parallel(True, [vars.D1, vars.D2], verify_portchannel_cum_member_status, [dict1, dict2])
    ensure_no_exception(output[1])
    #Clean up
    dict1 = {"vlan": data.vlan_id, "port_list": data.portchannel_name2, "tagging_mode": True}
    dict2 = {"vlan": data.vlan_id, "port_list": data.portchannel_name2, "tagging_mode": True}
    output = exec_parallel(True, [vars.D1, vars.D2], vlan_obj.delete_vlan_member, [dict1, dict2])
    ensure_no_exception(output[1])
    dict1 = {"vlan_list": data.vlan_id}
    dict2 = {"vlan_list": data.vlan_id}
    output = exec_parallel(True, [vars.D1, vars.D2], vlan_obj.delete_vlan, [dict1, dict2])
    if not portchannel_obj.config_portchannel(data.dut1, data.dut2, data.portchannel_name2, [data.members_dut1[2], data.members_dut1[3]],
                                           [data.members_dut2[2], data.members_dut2[3]], "del"):
        st.report_fail("portchannel_deletion_failed", data.portchannel_name2)
    ensure_no_exception(output[1])
    st.report_pass('test_case_passed')


def test_ft_lacp_graceful_restart_with_cold_boot():
    '''
    This test case covers below test scenarios/tests
    scenario-1: Verify the LACP graceful restart functionality with cold reboot.
    '''
    if not data.graceful_restart_config:
        graceful_restart_prolog()
    data.graceful_restart_config = True
    [output, exceptions] = exec_all(True, [ExecAllFunc(poll_wait, portchannel_obj.verify_portchannel_details, 7, vars.D1, [data.portchannel_name, data.portchannel_name2], [data.lag_up, data.lag_up], [[vars.D1D2P1, vars.D1D2P2], [vars.D1D2P3, vars.D1D2P4]], [None, None]), ExecAllFunc(poll_wait, portchannel_obj.verify_portchannel_details, 7, vars.D2, [data.portchannel_name, data.portchannel_name2], [data.lag_up, data.lag_up], [[vars.D2D1P1, vars.D2D1P2], [vars.D2D1P3, vars.D2D1P4]], [None, None])])
    ensure_no_exception(exceptions)
    if False in output:
        st.report_fail('portchannel_member_state_failed')
    config_save(vars.D2)
    slog.clear_logging(vars.D2)
    [output, exceptions] = exec_all(True, [ExecAllFunc(st.reboot, vars.D2), ExecAllFunc(poll_wait, portchannel_obj.verify_portchannel_details, 60, vars.D1, [data.portchannel_name, data.portchannel_name2], [data.lag_down, data.lag_down], [None, None], [[vars.D1D2P1, vars.D1D2P2], [vars.D1D2P3, vars.D1D2P4]])])
    ensure_no_exception(exceptions)
    if False in output:
        st.report_fail('portchannel_member_state_failed')
    if not poll_wait(verify_graceful_restart_syslog, 60, vars.D2):
        st.report_fail('failed_to_generate_lacp_graceful_restart_log_in_syslog')
    [output, exceptions] = exec_all(True, [ExecAllFunc(poll_wait, portchannel_obj.verify_portchannel_details, 7, vars.D1, [data.portchannel_name, data.portchannel_name2], [data.lag_up, data.lag_up], [[vars.D1D2P1, vars.D1D2P2], [vars.D1D2P3, vars.D1D2P4]], [None, None]), ExecAllFunc(poll_wait, portchannel_obj.verify_portchannel_details, 7, vars.D2, [data.portchannel_name, data.portchannel_name2], [data.lag_up, data.lag_up], [[vars.D2D1P1, vars.D2D1P2], [vars.D2D1P3, vars.D2D1P4]], [None, None])])
    ensure_no_exception(exceptions)
    if False in output:
        st.report_fail('portchannel_member_state_failed')
    st.report_pass('verify_lacp_graceful_restart_success', 'with cold reboot')


def test_ft_lacp_graceful_restart_with_save_reload():
    '''
    This test case covers below test scenarios/tests
    scenario-1: Verify the LACP graceful restart functionality with config save and reload.
    '''
    if not data.graceful_restart_config:
        graceful_restart_prolog()
    data.graceful_restart_config = True
    [output, exceptions] = exec_all(True, [ExecAllFunc(poll_wait, portchannel_obj.verify_portchannel_details, 7, vars.D1, [data.portchannel_name, data.portchannel_name2], [data.lag_up, data.lag_up], [[vars.D1D2P1, vars.D1D2P2], [vars.D1D2P3, vars.D1D2P4]], [None, None]), ExecAllFunc(poll_wait, portchannel_obj.verify_portchannel_details, 7, vars.D2, [data.portchannel_name, data.portchannel_name2], [data.lag_up, data.lag_up], [[vars.D2D1P1, vars.D2D1P2], [vars.D2D1P3, vars.D2D1P4]], [None, None])])
    ensure_no_exception(exceptions)
    slog.clear_logging(vars.D2)
    if False in output:
        st.report_fail('portchannel_member_state_failed')
    [output, exceptions] = exec_all(True, [ExecAllFunc(config_save_reload, vars.D2), ExecAllFunc(poll_wait, portchannel_obj.verify_portchannel_details, 120, vars.D1, [data.portchannel_name, data.portchannel_name2], [data.lag_down, data.lag_down], [None, None], [[vars.D1D2P1, vars.D1D2P2], [vars.D1D2P3, vars.D1D2P4]])])
    ensure_no_exception(exceptions)
    if False in output:
        st.report_fail('portchannel_member_state_failed')
    if not poll_wait(verify_graceful_restart_syslog, 60, vars.D2):
        st.report_fail('failed_to_generate_lacp_graceful_restart_log_in_syslog')
    [output, exceptions] = exec_all(True, [ExecAllFunc(poll_wait, portchannel_obj.verify_portchannel_details, 7, vars.D1, [data.portchannel_name, data.portchannel_name2], [data.lag_up, data.lag_up], [[vars.D1D2P1, vars.D1D2P2], [vars.D1D2P3, vars.D1D2P4]], [None, None]), ExecAllFunc(poll_wait, portchannel_obj.verify_portchannel_details, 7, vars.D2, [data.portchannel_name, data.portchannel_name2], [data.lag_up, data.lag_up], [[vars.D2D1P1, vars.D2D1P2], [vars.D2D1P3, vars.D2D1P4]], [None, None])])
    ensure_no_exception(exceptions)
    if False in output:
        st.report_fail('portchannel_member_state_failed')
    st.report_pass('verify_lacp_graceful_restart_success', 'with config save reload')
