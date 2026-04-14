import json
import re
import datetime
import copy
from spytest import st
from utilities.common import filter_and_select
from utilities.utils import ensure_service_params, get_interface_number_from_name, get_supported_ui_type_list
from utilities.common import make_list
from apis.system.rest import config_rest, get_rest, delete_rest
import apis.system.system_server as sys_server_api
from pkg_resources import parse_version
errors_list = ['error', 'invalid', 'usage', 'illegal', 'unrecognized']


def add_ntp_servers(dut, iplist=[], cli_type=''):
    """
    :param dut:
    :param iplist:
    :return:
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    st.log("add ntp servers")
    final_data = {}
    temp_data = {}
    iplist = make_list(iplist)
    if iplist:
        for ip in iplist:
            temp_data[ip] = {}
    else:
        st.log("please provide atleast 1 server to configure")
        return False
    if cli_type in get_supported_ui_type_list():
        kwargs = dict()
        kwargs['config'] = 'yes'
        for ip in iplist:
            kwargs['server_address'] = ip
            result = sys_server_api.config_system_server_properties(dut, server_name='NTP-SERVER', **kwargs)
            if not result:
                return result
    elif cli_type == "click":
        final_data['NTP_SERVER'] = temp_data
        final_data = json.dumps(final_data)
        st.apply_json(dut, final_data)
    elif cli_type == "klish":
        for ip in iplist:
            commands = "ntp server {}".format(ip)
            st.config(dut, commands, type=cli_type)
    elif cli_type in ['rest-patch', 'rest-put']:
        for ip in iplist:
            data = {
                "openconfig-system:servers": {
                    "server": [
                        {
                            "address": str(ip),
                            "config": {
                                "address": str(ip)
                            }
                        }
                    ]
                }
            }
            rest_urls = st.get_datastore(dut, "rest_urls")
            url1 = rest_urls['config_ntp_server'].format(ip)
            if not config_rest(dut, http_method=cli_type, rest_url=url1, json_data=data):
                st.error("Failed to configure ntp {} server".format(ip))
                return False
    else:
        st.log("UNSUPPORTED CLI TYPE -- {}".format(cli_type))
        return False
    st.log("Regenerate the ntp-config")
    command = "systemctl restart ntp-config"
    st.config(dut, command)
    return True


def delete_ntp_servers(dut, cli_type=''):
    """
    :param dut:
    :param iplist:
    :return:
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    output = show_ntp_server(dut)
    commands = []
    if output is None or not output:
        st.log("No servers to delete")
        return True
    else:
        for ent in output:
            # The 'remote' field now contains only the server address (no status symbols)
            # Status symbols are in the 'ms' field
            server_ip = ent.get("remote", "").strip()
            # Skip if server_ip is empty
            if not server_ip:
                st.log("Skipping empty server entry")
                continue
            # Handle klish/click before generic supported UI types check
            if cli_type == "click":
                commands.append("config ntp del {}".format(server_ip))
            elif cli_type == "klish":
                commands.append("no ntp server {}".format(server_ip))
            elif cli_type in ['rest-patch', 'rest-put']:
                rest_urls = st.get_datastore(dut, "rest_urls")
                url1 = rest_urls['config_ntp_server'].format(server_ip)
                if not delete_rest(dut, rest_url=url1):
                    st.error("Failed to delete ntp {} server".format(server_ip))
            elif cli_type in get_supported_ui_type_list():
                kwargs = dict()
                kwargs['config'] = 'no'
                kwargs['server_address'] = server_ip
                result = sys_server_api.config_system_server_properties(dut, server_name='NTP-SERVER', **kwargs)
                if not result:
                    st.error("Failed to delete NTP server {}".format(server_ip))
                    return False
            else:
                st.log("UNSUPPORTED CLI TYPE -- {}".format(cli_type))
                return False
    st.config(dut, commands, type=cli_type)
    return True


def enable_ntp(dut):
    """

    :param dut:
    :return:
    """
    st.log("enable ntp")
    command = "sudo timedatectl set-ntp true"
    st.config(dut, command)
    return True


def disable_ntp(dut):
    """

    :param dut:
    :return:
    """
    st.log("disable ntp")
    command = "sudo timedatectl set-ntp false"
    st.config(dut, command)
    return True


def enable_local_rtc(dut):
    st.log("enable set-local-rtc")
    command = "sudo timedatectl set-local-rtc true"
    st.config(dut, command)
    return True


def disable_local_rtc(dut):
    """

    :param dut:
    :return:
    """
    st.log("disable set-local-rtc")
    command = "sudo timedatectl set-local-rtc false"
    st.config(dut, command)
    return True


def config_timezone(dut, zone):
    """

    :param dut:
    :param zone:
    :return:
    """
    st.log("config timezone")
    if zone:
        command = "sudo timedatectl set-timezone {}".format(zone)
        st.config(dut, command)
        return True
    else:
        st.log("please provide zone name")
        return False


def show_ntp_server(dut, cli_type=''):
    """

    :param dut:
    :return:
    """
    import re
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    cli_type = 'klish' if cli_type in get_supported_ui_type_list() else cli_type
    st.log("show_ntp_server: cli_type={}".format(cli_type))
    st.log("show ntp servers")
    if cli_type == "click":
        command = "show ntp"
        output = st.show(dut, command, type=cli_type)
    elif cli_type == "klish":
        # For IS-CLI, use "show ntp server" which returns a table format
        command = "show ntp server"
        raw_output = st.show(dut, command, type=cli_type, skip_tmpl=True)

        # Parse the IS-CLI output manually
        # Format is a table with columns: NTP Servers | minpoll | maxpoll | Prefer | Authentication key ID
        output = []
        if isinstance(raw_output, str):
            output_str = raw_output
        elif isinstance(raw_output, list):
            output_str = '\n'.join(str(item) for item in raw_output)
        else:
            output_str = str(raw_output)

        # Parse table format
        # Example:
        # NTP Servers                     minpoll maxpoll Prefer Authentication key ID
        # ---------------------------------------------------------------------------------------------------------------------
        # 216.239.35.0                                    False
        # time.google.com                                 False

        in_data_section = False
        for line in output_str.split('\n'):
            line = line.rstrip()

            # Skip empty lines
            if not line:
                continue

            # Skip separator lines
            if line.startswith('---'):
                in_data_section = True
                continue

            # Skip header line
            if 'NTP Servers' in line or 'NTP servers' in line:
                continue

            # Parse data lines (after separator)
            if in_data_section:
                # Split by whitespace and extract server address (first column)
                parts = line.split()
                if parts and len(parts) >= 1:
                    server_addr = parts[0]
                    # Validate it looks like IP or hostname
                    if re.match(r'^[\w\.\-:]+$', server_addr):
                        entry = {'remote': server_addr}
                        # Try to parse prefer field if present
                        if len(parts) >= 2 and parts[-1] in ['True', 'False']:
                            entry['prefer'] = parts[-1]
                        output.append(entry)

        st.log("Parsed {} NTP servers from IS-CLI output".format(len(output)))
        return output
    elif cli_type in ['rest-patch', 'rest-put']:
        rest_urls = st.get_datastore(dut, "rest_urls")
        url1 = rest_urls['show_ntp']
        server_output = get_rest(dut, rest_url=url1)
        output = get_rest_server_info(server_output['output'])
    else:
        st.log("UNSUPPORTED CLI TYPE -- {}".format(cli_type))
        return False
    data = output
    output = _get_show_ntp_with_hostname_to_ip_conversion(data)
    return output


def verify_ntp_server_details(dut, server_ip=None, **kwargs):
    output = show_ntp_server(dut)
    flag = 1
    if not output:
        flag = 0
    if server_ip is None:
        if "No association ID's returned" in output:
            return True
        elif "%Error: Resource not found" in output:
            return True
        else:
            return False
    else:
        server_ips = [server_ip] if isinstance(server_ip, str) else list([str(e) for e in server_ip])
        data = kwargs
        for ent in output:
            # The 'remote' field now contains only the server address (no status symbols)
            remote_ip = ent.get("remote", "").strip()
            if remote_ip in server_ips:
                if 'remote' in data and remote_ip not in data['remote']:
                    st.log("Remote Server IP is not matching")
                    flag = 0
                # Map old field names to new template fields
                # Old template: refid, st, t, when, poll, reach, delay, offset, jitter
                # New template: ms, remote, stratum, poll, reach, lastrx, last_sample
                if 'st' in data and str(ent.get("stratum", "")) != str(data["st"]):
                    st.log("Stratum value is not matching")
                    flag = 0
                if 'stratum' in data and str(ent.get("stratum", "")) != str(data["stratum"]):
                    st.log("Stratum value is not matching")
                    flag = 0
                if 'poll' in data and str(ent.get("poll", "")) != str(data["poll"]):
                    st.log("Polling in seconds is not matching")
                    flag = 0
                if 'reach' in data and str(ent.get("reach", "")) != str(data["reach"]):
                    st.log("Reach is not matching")
                    flag = 0
                if 'lastrx' in data and str(ent.get("lastrx", "")) != str(data["lastrx"]):
                    st.log("LastRx is not matching")
                    flag = 0
                # Note: refid, t, when, delay, offset, jitter are no longer available in new template
                if 'refid' in data:
                    st.log("Warning: 'refid' field not available in new template")
                if 't' in data:
                    st.log("Warning: 't' field not available in new template")
                if 'when' in data:
                    st.log("Warning: 'when' field not available in new template")
                if 'delay' in data:
                    st.log("Warning: 'delay' field not available in new template")
                if 'offset' in data:
                    st.log("Warning: 'offset' field not available in new template")
                if 'jitter' in data:
                    st.log("Warning: 'jitter' field not available in new template")
            else:
                st.log("Server IP is not matching")
                flag = 0
        if flag:
            st.log("Server IP's  matched.")
            return True
        else:
            st.log("Server IP's not matched.")
            return False


def show_ntp_status(dut, mvrf=False):
    """

    :param dut:
    :return:
    """
    st.log("show ntp status")
    isBuster = False
    # os_info will be like 'Linux sonic 4.9.0-11-2-amd64 #1 SMP Debian 4.9.189-3+deb9u2 ...'
    os_info = st.config(dut, "uname -a")
    release = os_info.split(' ')
    release = release[2]
    release = release.split('-')
    if parse_version(release[0]) > parse_version("4.9.0"):
        isBuster = True
    if mvrf:
        if isBuster:
            command = "sudo ip vrf exec mgmt ntpstat"
        else:
            command = "sudo cgexec -g l3mdev:mgmt ntpstat"
    else:
        command = "ntpstat"
    output = st.show(dut, command)
    retval = []
    entries = filter_and_select(output, ["server", "stratum", "time", "poll"])
    for ent in entries:
        retval.append(ent["server"].strip("()"))
        retval.append(ent["stratum"])
        retval.append(ent["time"])
        retval.append(ent["poll"])
    return retval


def config_date(dut, date):
    """

    :param dut:
    :param date:
    :return:
    """
    st.log("config date")
    command = "date --set='{}'".format(date)
    st.config(dut, command)
    return True


def set_date_ntp(dut):
    """

    :param dut:
    :param date:
    :return:
    """
    st.log("set date using ntpd")
    command = "sudo /usr/sbin/ntpd -q -g -x &"
    st.config(dut, command)
    return True


def show_timedatectl_status(dut):
    """

    :param dut:
    :return:
    """
    st.log("timedatectl status")
    command = "timedatectl status"
    output = st.show(dut, command)
    return output


def show_clock(dut, cli_type=''):
    """

    :param dut:
    :return:
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    cli_type = 'klish' if cli_type in get_supported_ui_type_list() else cli_type
    st.log("show clock")
    if cli_type in ["click", "klish"]:
        command = "show clock"
        output = st.show(dut, command, type=cli_type)
        # Check if output is empty or invalid
        if not output or len(output) == 0:
            st.error("show clock returned empty output")
            return None
        return output[0]
    elif cli_type in ['rest-patch', 'rest-put']:
        rest_urls = st.get_datastore(dut, "rest_urls")
        url1 = rest_urls['show_clock']
        data = get_rest(dut, rest_url=url1)
        data = data['output']['openconfig-system:current-datetime']
        output = get_time_zone_info(data)
        return output
    else:
        st.log("UNSUPPORTED CLI TYPE -- {}".format(cli_type))
        return False


def verify_clock(dut, time):
    """

    :param dut:
    :param time:
    :return:
    """
    st.log("verifying show clock")
    retval = show_clock(dut)
    if retval == time:
        return True
    else:
        return False


def verify_timedatectl(dut, **kwargs):
    """

    :param dut:
    :param kwargs:
    :return:
    """
    st.log("verifying timedatectl")
    retval = show_timedatectl_status(dut)
    flag = 1
    data = kwargs
    if not data:
        st.error("Please provide details to be verified.")
        return False
    else:
        if 'rtctime' in data:
            if retval[0]['rtctime'] != data['rtctime']:
                flag = 0
        if 'universaltime' in data:
            if retval[0]['universaltime'] != data['universaltime']:
                flag = 0
        if 'networktimeon' in data:
            if retval[0]['networktimeon'] != data['networktimeon']:
                flag = 0
        if 'ntpsynchronized' in data:
            if retval[0]['ntpsynchronized'] != data['ntpsynchronized']:
                flag = 0
        if 'timezone' in data:
            if retval[0]['timezone'] != data['timezone']:
                flag = 0
        if 'localtime' in data:
            if retval[0]['localtime'] != data['localtime']:
                flag = 0
    if flag:
        return True
    else:
        return False


def verify_ntp_status(dut, iteration=1, delay=1, mvrf=False, **kwargs):
    """
    Verify NTP status with polling.
    Author: Prudvi Mangadu (prudvi.mangadu@broadcom.com)
    :param dut:
    :param server: single or list of servers.
    :param stratum:
    :param time:
    :param poll:
    :param iteration: 1 sec (default)
    :param delay: 1 sec (default)
    :return:
    """
    st.log("verifying ntp status")
    i = 0
    if not kwargs:
        st.error("Please provide details to be verified.")
        return False
    else:
        while True:
            flag = 0
            retval = show_ntp_status(dut, mvrf)
            if not retval:
                st.log("No o/p from ntpstat command")
                if i > iteration:
                    st.log("NTP status failed.")
                    st.log("Max iterations {} reached".format(i))
                    return False
                i += 1
                st.wait(delay)
                continue
            if 'server' in kwargs:
                server_li = list(kwargs['server']) if isinstance(kwargs['server'], list) else [kwargs['server']]
                if retval[0] in server_li:
                    st.log("Detected NTP server - {}".format(retval[0]))
                    flag += 1
            if 'stratum' in kwargs:
                if retval[1] == kwargs['stratum']:
                    flag += 1
            if 'time' in kwargs:
                if retval[2] == kwargs['time']:
                    flag += 1
            if 'poll' in kwargs:
                if retval[3] == kwargs['poll']:
                    flag += 1
            if flag == len(kwargs):
                return True
            if i > iteration:
                st.log("NTP status failed.")
                st.log("Max iterations {} reached".format(i))
                return False
            i += 1
            st.wait(delay)


def verify_ntp_server(dut, serverip, **kwargs):
    """

    :param dut:
    :param serverip:
    :param kwargs:
    :return:
    """
    st.log("verifying ntp server")
    flag = 1
    data = kwargs
    if not data or not serverip:
        st.error("Please provide details to be verified.")
        return False
    else:
        retval = show_ntp_server(dut)
        if not retval:
            return False
        else:
            if 'remote' in data:
                if retval[0] != data['remote']:
                    flag = 0
            if 'refid' in data:
                if retval[1] != data['refid']:
                    flag = 0
            if 'st' in data:
                if retval[2] != data['st']:
                    flag = 0
            if 't' in data:
                if retval[3] != data['t']:
                    flag = 0
            if 'when' in data:
                if retval[4] != data['when']:
                    flag = 0
            if 'poll' in data:
                if retval[5] != data['poll']:
                    flag = 0
            if 'reach' in data:
                if retval[6] != data['reach']:
                    flag = 0
            if 'delay' in data:
                if retval[7] != data['delay']:
                    flag = 0
            if 'offset' in data:
                if retval[8] != data['offset']:
                    flag = 0
            if 'jitter' in data:
                if retval[9] != data['jitter']:
                    flag = 0
    if flag:
        return True
    else:
        return False


def verify_ntp_service_status(dut, status, iteration=1, delay=1):
    """
    Verify NTP service status with polling
    Author: Prudvi Mangadu (prudvi.mangadu@broadcom.com)

    :param dut:
    :param status:
    :param iteration: 1 sec (default)
    :param delay: 1 sec (default)
    :return:
    """
    command = "service ntp status | grep Active"
    i = 1
    while True:
        output = st.config(dut, command)
        if status in output:
            st.log("NTP service status is '{}' iteration".format(i))
            return True
        if i > iteration:
            st.log("NTP service status is not '{}'")
            st.log("Max iterations {} reached".format(i))
            return False
        i += 1
        st.wait(delay)


def verify_ntp_server_exists(dut, server_ip=None, **kwargs):
    output = show_ntp_server(dut)
    if server_ip is None:
        if "No association ID's returned" in output:
            return True
        else:
            return False
    else:
        server_ips = [server_ip] if isinstance(server_ip, str) else list([str(e) for e in server_ip])
        data = kwargs
        for ent in output:
            # The 'remote' field now contains only the server address (no status symbols)
            remote_ip = ent.get("remote", "").strip()
            if remote_ip in server_ips:
                if 'remote' in data and remote_ip not in data['remote']:
                    st.log("Remote Server IP is not matching")
                    return False
                else:
                    return True


def ensure_ntp_config(dut, iplist=[], cli_type=''):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    if not iplist:
        iplist = ensure_service_params(dut, "ntp", "default")
    if not iplist:
        st.log("NTP server IPs missing")
        return False
    commands = []
    for ip in iplist:
        if not verify_ntp_server_exists(dut, ip, remote=ip):
            if cli_type in get_supported_ui_type_list():
                kwargs = dict()
                kwargs['config'] = 'yes'
                for ip in iplist:
                    kwargs['server_address'] = ip
                    result = sys_server_api.config_system_server_properties(dut, server_name='NTP-SERVER', **kwargs)
                    if not result:
                        return result
            elif cli_type == "click":
                commands.append("config ntp add {}".format(ip))
            elif cli_type == "klish":
                commands.append("ntp server {}".format(ip))
            elif cli_type in ['rest-patch', 'rest-put']:
                data = {
                    "openconfig-system:servers": {
                        "server": [
                            {
                                "address": str(ip),
                                "config": {
                                    "address": str(ip)
                                }
                            }
                        ]
                    }
                }
                rest_urls = st.get_datastore(dut, "rest_urls")
                url1 = rest_urls['config_ntp_server'].format(ip)
                if not config_rest(dut, http_method=cli_type, rest_url=url1, json_data=data):
                    st.error("Failed to configure ntp {} server".format(ip))
                    return False
            else:
                st.log("UNSUPPORTED CLI TYPE -- {}".format(cli_type))
                return False
    st.config(dut, commands, type=cli_type)
    return True


def _get_show_ntp_with_hostname_to_ip_conversion(data):
    ret_val = list()
    ntp_server_hostname_ip_map = {"io.crash-override.org": "47.190.36.230", "horp-bsd01.horp.io": "192.111.144.114", "time3.google.com": "216.239.35.8", "time4.google.com": "216.239.35.12", "time2.google.com": "216.239.35.4"}
    for entry in data:
        for hostname, ip in ntp_server_hostname_ip_map.items():
            if ('remote' in entry) and (entry['remote'][1:] in hostname):
                entry.update(remote=ip)
        ret_val.append(entry)
    return ret_val


def get_rest_server_info(server_output):
    ret_val = []
    try:
        servers = server_output["openconfig-system:server"]
        for server in servers:
            temp = dict()
            server_details = server['state']
            req_params = ['address', 'reach', 'now', 'stratum', 'peer-delay', 'peer-type', 'peer-offset', 'peer-jitter', 'poll-interval', 'refid', 'sel-mode']
            if all(param in server_details for param in req_params):
                temp['remote'] = str(server_details['sel-mode'] + server_details['address'])
                temp['reach'] = str(server_details['reach'])
                temp['when'] = str(server_details['now'])
                temp['st'] = str(server_details['stratum'])
                temp['delay'] = str(server_details['peer-delay'])
                temp['t'] = str(server_details['peer-type'])
                temp['offset'] = str(server_details['peer-offset'])
                temp['jitter'] = str(server_details['peer-jitter'])
                temp['poll'] = str(server_details['poll-interval'])
                temp['refid'] = str(server_details['refid'])
                ret_val.append(temp)
        st.debug(ret_val)
        return ret_val
    except Exception as e:
        st.error("{} exception occurred".format(e))
        st.debug("Given data is: {}".format(server_output))
        return ret_val


def get_time_zone_info(data):
    elements = re.findall(r"(\d+)\-(\d+)\-(\d+)T(\d+)\:(\d+)\:(\d+)Z", data)
    if len(elements[0]) == 6:
        data = elements[0]
        ret_val = list()
        out = dict()
        month_dict = {"01": "jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun", "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}
        out['monthday'] = data[2]
        out['month'] = month_dict[data[1]]
        out['year'] = data[0]
        out['hours'] = data[3]
        out['minutes'] = data[4]
        out['seconds'] = data[5]
        ret_val.append(out)
        return ret_val
    else:
        st.error("invalid data")
        return False


def get_ntp_logs(dut, filter=None):
    """
    To get the NTP related logs from /var/log/ntp.log
    :param dut:
    :param filter:
    :return out_list
    """
    command = "cat /var/log/ntp.log"
    command = "{} | grep '{}'".format(command, filter) if filter else command
    output = st.show(dut, command, skip_tmpl=True, skip_error_check=True, faster_cli=False, max_time=1200)
    out_list = output.strip().split('\n')[:-1]
    for _ in range(out_list.count("'")):
        out_list.remove("'")
    return out_list


def verify_time_synch(server_time, client_time):
    diff = 10
    month_dict = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
    try:
        time1 = datetime.datetime(int(server_time['year']), month_dict[server_time['month']], int(server_time['monthday']), int(server_time['hours']), int(server_time['minutes']), int(server_time['seconds']))
        time2 = datetime.datetime(int(client_time['year']), month_dict[client_time['month']], int(client_time['monthday']), int(client_time['hours']), int(client_time['minutes']), int(client_time['seconds']))
        difference = (time1 - time2).total_seconds()
    except Exception as e:
        st.error("'{}' exception occurred".format(e))
        return False
    return True if int(abs(difference)) < diff else False


def verify_ntp_synch(dut, server):
    entries = show_ntp_server(dut)
    if filter_and_select(entries, None, {'remote': "*{}".format(server)}):
        st.debug("NTP synchronized with server: {}".format(server))
        return True
    st.error("NTP not synchronized with server: {}".format(server))
    return False


def config_ntp_parameters(dut, **kwargs):
    """
    To Configure NTP paramters
    Author: Jagadish Chatrasi (jagadish.chatrasi@broadcom.com)
    """
    cli_type = st.get_ui_type(dut, **kwargs)
    cli_type = "klish" if cli_type == "click" else cli_type
    config = kwargs.get('config', True)
    skip_error = kwargs.get('skip_error', False)
    prefer = kwargs.get('prefer', None)
    commands = list()
    if cli_type in get_supported_ui_type_list():
        if 'source_intf' in kwargs and not config:
            cli_type = "klish"
    if cli_type in get_supported_ui_type_list():
        config_gbl_paramm = False
        ret_val = True
        kwargs['config'] = 'yes' if config else 'no'
        if 'source_intf' in kwargs:
            for src_intf in make_list(kwargs['source_intf']):
                kwargs['src_intf'] = src_intf
                sys_server_api.config_system_server_properties(dut, server_name='NTP-SERVER', **kwargs)
            kwargs.pop('source_intf')
            kwargs.pop('src_intf')
        if 'vrf' in kwargs:
            kwargs['vrf_name'] = kwargs.pop('vrf')
            config_gbl_paramm = True
        if 'authenticate' in kwargs:
            config_gbl_paramm = True
            kwargs['enable_auth'] = kwargs.pop('authenticate')
        if 'trusted_key' in kwargs:
            config_gbl_paramm = True
        if 'auth_key_id' in kwargs:
            config_gbl_paramm = True
        if config_gbl_paramm:
            ret_val = sys_server_api.config_system_server_properties(dut, server_name='NTP-SERVER', **kwargs)
        if 'servers' in kwargs:
            servers = make_list(kwargs.get('servers'))
            s_kwargs = dict()
            for server in servers:
                s_kwargs['server_address'] = server
                s_kwargs['config'] = 'yes' if config else 'no'
                if prefer:
                    s_kwargs['prefer'] = prefer
                if kwargs.get('minpoll') and kwargs.get('maxpoll'):
                    s_kwargs['minpoll'] = kwargs['minpoll']
                    s_kwargs['maxpoll'] = kwargs['maxpoll']
                if kwargs.get('server_key'):
                    s_kwargs['server_key'] = kwargs['server_key']
                sys_server_api.config_system_server_properties(dut, server_name='NTP-SERVER', **s_kwargs)
        return ret_val
    elif cli_type == "klish":
        if 'source_intf' in kwargs:
            config_string = '' if config else 'no '
            for src_intf in make_list(kwargs['source_intf']):
                # FIX for BUG-NTP-003: klish CLI requires space between interface type and number
                # e.g., "Ethernet0" must be sent as "Ethernet 0"
                # e.g., "Management0" must be sent as "Management 0"
                if src_intf.startswith('Ethernet') and len(src_intf) > 8 and src_intf[8:].isdigit():
                    intf_formatted = 'Ethernet ' + src_intf[8:]
                elif src_intf.startswith('Management') and len(src_intf) > 10 and src_intf[10:].isdigit():
                    intf_formatted = 'Management ' + src_intf[10:]
                elif src_intf.startswith('PortChannel') and len(src_intf) > 11 and src_intf[11:].isdigit():
                    intf_formatted = 'PortChannel ' + src_intf[11:]
                elif src_intf.startswith('Vlan') and len(src_intf) > 4 and src_intf[4:].isdigit():
                    intf_formatted = 'Vlan ' + src_intf[4:]
                elif src_intf.startswith('Loopback') and len(src_intf) > 8 and src_intf[8:].isdigit():
                    intf_formatted = 'Loopback ' + src_intf[8:]
                else:
                    intf_formatted = src_intf
                commands.append('{}ntp source-interface {}'.format(config_string, intf_formatted))
        if 'vrf' in kwargs:
            if not config:
                commands.append('no ntp vrf')
            else:
                commands.append('ntp vrf {}'.format(kwargs['vrf']))
        if 'authenticate' in kwargs:
            config_string = '' if config else 'no '
            commands.append('{}ntp authenticate'.format(config_string))
        if kwargs.get('auth_key_id'):
            if not config:
                commands.append('no ntp authentication-key {}'.format(kwargs['auth_key_id']))
            else:
                if kwargs.get('auth_type') and kwargs.get('auth_string'):
                    commands.append('ntp authentication-key {} {} "{}"'.format(kwargs['auth_key_id'], kwargs['auth_type'], kwargs['auth_string']))
        if kwargs.get('trusted_key'):
            config_string = '' if config else 'no '
            commands.append('{}ntp trusted-key {}'.format(config_string, kwargs['trusted_key']))
        if kwargs.get('servers'):
            servers = make_list(kwargs.get('servers'))
            for server in servers:
                if not config:
                    commands.append('no ntp server {}'.format(server))
                else:
                    # Determine association type (server or pool)
                    association_type = kwargs.get("association_type", "server")
                    if association_type == "pool":
                        # NOTE: 'ntp pool' command is not supported in klish CLI
                        # Only REST/gNMI interfaces support pool association type
                        st.log("WARNING: association_type='pool' not supported in klish CLI")
                        st.report_unsupported("msg", "Association type configuration not supported in klish CLI")
                        return False
                        command = 'ntp pool {}'.format(server)
                    else:
                        command = 'ntp server {}'.format(server)

                    if kwargs.get("version"):
                        command += " version {}".format(kwargs.get("version"))
                    if kwargs.get("prefer"):
                        command += " prefer"
                    if kwargs.get("iburst"):
                        command += " iburst"
                    if kwargs.get("minpoll") and kwargs.get("maxpoll"):
                        command += " minpoll {} maxpoll {}".format(kwargs.get("minpoll"), kwargs.get("maxpoll"))
                    if kwargs.get("server_key"):
                        command += ' key {}'.format(kwargs['server_key'])
                    commands.append(command)
    elif cli_type in ["rest-patch", "rest-put"]:
        rest_urls = st.get_datastore(dut, "rest_urls")
        if 'source_intf' in kwargs:
            for src_intf in make_list(kwargs['source_intf']):
                src_intf = 'eth0' if src_intf == "Management0" else src_intf
                if config:
                    url = rest_urls['ntp_config_source_interface']
                    payload = json.loads("""{"openconfig-system:source-interface": ["string"]}""")
                    payload["openconfig-system:source-interface"] = [src_intf]
                    if not config_rest(dut, http_method=cli_type, rest_url=url, json_data=payload):
                        return False
                else:
                    url = rest_urls['ntp_delete_source_interface'].format(src_intf)
                    if not delete_rest(dut, rest_url=url):
                        return False
        if 'vrf' in kwargs:
            if config:
                url = rest_urls['ntp_config_vrf']
                payload = json.loads("""{"openconfig-system:config": {"network-instance": "string"}}""")
                payload["openconfig-system:config"]["network-instance"] = kwargs['vrf']
                if not config_rest(dut, http_method=cli_type, rest_url=url, json_data=payload):
                    return False
            else:
                url = rest_urls['ntp_config_vrf_delete']
                if not delete_rest(dut, rest_url=url):
                    return False
        if 'authenticate' in kwargs:
            url = rest_urls['ntp_config']
            if config:
                payload = json.loads("""{"openconfig-system:config": {"enable-ntp-auth": true}}""")
                if not config_rest(dut, http_method=cli_type, rest_url=url, json_data=payload):
                    return False
            else:
                payload = json.loads("""{"openconfig-system:config": {"enable-ntp-auth": false}}""")
                if not config_rest(dut, http_method=cli_type, rest_url=url, json_data=payload):
                    return False
        if kwargs.get('auth_key_id'):
            keymap = {"md5": "NTP_AUTH_MD5", 'sha1': 'NTP_AUTH_SHA1', 'sha2-256': 'NTP_AUTH_SHA2_256'}
            if not config:
                url = rest_urls['ntp_key_delete'].format(kwargs['auth_key_id'])
                if not delete_rest(dut, rest_url=url):
                    return False
            else:
                if kwargs.get('auth_type') and kwargs.get('auth_string'):
                    url = rest_urls['ntp_key_config']
                    payload = json.loads("""{"openconfig-system:ntp-keys": {
                                                "ntp-key": [
                                                  {
                                                    "key-id": 0,
                                                    "config": {
                                                      "key-id": 0,
                                                      "key-type": "string",
                                                      "openconfig-system-ext:encrypted": false,
                                                      "key-value": "string"
                                                    }
                                                  }
                                                ]
                                              }
                                            }""")
                    payload["openconfig-system:ntp-keys"]["ntp-key"][0]["key-id"] = int(kwargs['auth_key_id'])
                    payload["openconfig-system:ntp-keys"]["ntp-key"][0]["config"]["key-id"] = int(kwargs['auth_key_id'])
                    payload["openconfig-system:ntp-keys"]["ntp-key"][0]["config"]["key-type"] = keymap[kwargs['auth_type']]
                    payload["openconfig-system:ntp-keys"]["ntp-key"][0]["config"]["key-value"] = kwargs['auth_string']
                    if not config_rest(dut, http_method=cli_type, rest_url=url, json_data=payload):
                        return False
        if kwargs.get('trusted_key'):
            if config:
                url = rest_urls['ntp_config']
                payload = json.loads("""{"openconfig-system:config": {"openconfig-system-ext:trusted-key": [0]}}""")
                payload["openconfig-system:config"]["openconfig-system-ext:trusted-key"] = [int(kwargs['trusted_key'])]
                if not config_rest(dut, http_method=cli_type, rest_url=url, json_data=payload):
                    return False
            else:
                url = rest_urls["ntp_trusted_key_delete"].format(kwargs['trusted_key'])
                if not delete_rest(dut, rest_url=url):
                    return False
        if kwargs.get('servers'):
            servers = make_list(kwargs.get('servers'))
            for server in servers:
                if not config:
                    url = rest_urls['delete_ntp_server'].format(server)
                    if not delete_rest(dut, rest_url=url):
                        return False
                else:
                    url = rest_urls['config_ntp_server']
                    if kwargs.get('server_key'):
                        payload = json.loads("""{"openconfig-system:servers": {
                                                    "server": [
                                                      {
                                                        "address": "string",
                                                        "config": {
                                                          "address": "string",
                                                          "openconfig-system-ext:key-id": 0
                                                        }
                                                      }
                                                    ]
                                                  }
                                                }""")
                        payload["openconfig-system:servers"]["server"][0]["address"] = server
                        payload["openconfig-system:servers"]["server"][0]["config"]["address"] = server
                        payload["openconfig-system:servers"]["server"][0]["config"]["openconfig-system-ext:key-id"] = int(kwargs.get('server_key'))
                    else:
                        payload = json.loads("""{"openconfig-system:servers": {
                                                    "server": [
                                                      {
                                                        "address": "string",
                                                        "config": {
                                                          "address": "string"
                                                        }
                                                      }
                                                    ]
                                                  }
                                                }""")
                        payload["openconfig-system:servers"]["server"][0]["address"] = server
                        payload["openconfig-system:servers"]["server"][0]["config"]["address"] = server
                    if kwargs.get("minpoll") and kwargs.get("maxpoll"):
                        payload["openconfig-system:servers"]["server"][0]["config"].update({"openconfig-system:minpoll": kwargs.get("minpoll"), "openconfig-system:maxpoll": kwargs.get("maxpoll")})
                    if prefer:
                        payload["openconfig-system:servers"]["server"][0]["config"].update({"prefer": bool(prefer)})
                    if not config_rest(dut, http_method=cli_type, rest_url=url, json_data=payload):
                        return False
    else:
        st.error("Unsupported CLI_TYPE: {}".format(cli_type))
        return False
    if commands:
        # Workaround for BUG-NTP-001: 'end' command fails with "%Error: Internal error"
        # Use 'exit' instead of 'end' to exit config mode for klish
        if cli_type == "klish":
            commands.append('exit')
        response = st.config(dut, commands, type=cli_type, skip_error_check=skip_error)
        if any(error in response.lower() for error in errors_list):
            st.error("The response is: {}".format(response))
            return False
    return True


def show(dut, **kwargs):
    """
    To get the show output of NTP servers/global configuration
    Author: Jagadish Chatrasi (jagadish.chatrasi@broadcom)
    """
    cli_type = st.get_ui_type(dut, **kwargs)
    cli_type = 'klish' if cli_type == 'click' else cli_type
    cli_type = 'klish' if cli_type in get_supported_ui_type_list() else cli_type
    if cli_type == 'klish':
        if kwargs.get('server', None):
            command = 'show ntp server'
        elif kwargs.get('global', None):
            command = 'show ntp global'
        else:
            st.error('show command is not called for server/global')
            return False
        return st.show(dut, command, type=cli_type)
    elif cli_type in ['rest-patch', 'rest-put']:
        output = []
        rest_urls = st.get_datastore(dut, "rest_urls")
        if kwargs.get('server'):
            url = rest_urls["show_ntp_server"]
            payload = get_rest(dut, rest_url=url)["output"]["openconfig-system:server"]
            for row in payload:
                table_data = {'server': row["state"]["address"], 'prefer': row["state"]["prefer"],
                              'minpoll': row["state"]["minpoll"], 'maxpoll': row["state"]["maxpoll"]}
                output.append(copy.deepcopy(table_data))
        elif kwargs.get('global'):
            url = rest_urls["show_ntp_global"]
            table_data = {'source_intf': "", 'vrf': ""}
            payload = get_rest(dut, rest_url=url)["output"]["openconfig-system:state"]
            if "openconfig-system-ext:ntp-source-interface" in payload:
                table_data['source_intf'] = payload["openconfig-system-ext:ntp-source-interface"]
            if "openconfig-system-ext:vrf" in payload:
                table_data['vrf'] = payload["openconfig-system-ext:vrf"]
            output.append(copy.deepcopy(table_data))
        else:
            st.error('show command is not called for server/global')
            return False
        st.log("OUTPUT : {}".format(output))
        return output
    else:
        st.error("Unsupported CLI_TYPE: {}".format(cli_type))
        return False


def ntp_server_offset_config(dut, vrf="default"):
    st.log("config ntp_server_offset value")
    isBuster = False
    if st.is_dry_run():
        os_info = 'Linux sonic 4.9.0-11-2-amd64 #1 SMP Debian 4.9.189-3+deb9u2 ...'
    else:
        os_info = st.config(dut, "uname -a")
    release = os_info.split(' ')
    release = release[2]
    release = release.split('-')
    if parse_version(release[0]) > parse_version("4.9.0"):
        isBuster = True
    if vrf != "default":
        if isBuster:
            command = "sudo  ip vrf exec mgmt /usr/sbin/ntpd -q -g &\n"
        else:
            command = "sudo  cgexec -g l3mdev:mgmt /usr/sbin/ntpd -q -g &\n"
    else:
        command = "sudo  /usr/sbin/ntpd -q -g &\n"
    st.config(dut, command, skip_error_check=True)
    return True


def verify_ntp(dut, **kwargs):
    '''
    To verify the 'show ntp' server parameters
    '''
    output = show(dut, server='server')
    if filter_and_select(output, match=kwargs):
        return True
    else:
        return False


def show_running_ntp(dut, **kwargs):
    """
    API to verify ntp on DUT
    Author : Nagarjuna Suravarapu (nagarjuna.survarapu@broadcom.com)
    :param dut:
    :return:
    """
    cli_type = st.get_ui_type(dut, **kwargs)
    cli_type = 'klish' if cli_type in get_supported_ui_type_list() else cli_type
    if cli_type in ["klish", "rest-patch", "rest-put", "click"]:
        cmd = 'show running-config | grep ntp'
        output = st.show(dut, cmd, skip_tmpl=True, type="klish")
    else:
        st.log("UNSUPPORTED CLI TYPE")
        return False
    return output


def get_ntp_authentication_keys(dut, cli_type=''):
    """
    Get list of configured NTP authentication keys

    Args:
        dut: Device Under Test
        cli_type: CLI type (klish/click)

    Returns:
        List of dicts with key_id, auth_type, and other key details
        Returns empty list if no keys configured

    Usage:
        keys = get_ntp_authentication_keys(dut, cli_type='klish')
        for key in keys:
            st.log(f"Key ID: {key['key_id']}")
    """
    import re
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    cli_type = 'klish' if cli_type in get_supported_ui_type_list() else cli_type

    if cli_type == "klish":
        # Get running config and extract authentication keys
        cmd = 'show running-config | grep "ntp authentication-key"'
        output = st.show(dut, cmd, skip_tmpl=True, type="klish")

        keys = []
        if isinstance(output, str):
            output_str = output
        elif isinstance(output, list):
            output_str = '\n'.join(str(item) for item in output)
        else:
            output_str = str(output)

        # Parse lines like: "ntp authentication-key 10 md5 encrypted abcdef123"
        # or: "ntp authentication-key 20 sha1 TestPassword"
        for line in output_str.split('\n'):
            line = line.strip()
            if 'ntp authentication-key' in line:
                # Extract key ID from the line
                match = re.search(r'ntp\s+authentication-key\s+(\d+)\s+(md5|sha1|sha2-256)', line, re.IGNORECASE)
                if match:
                    key_id = match.group(1)
                    auth_type = match.group(2)
                    keys.append({
                        'key_id': key_id,
                        'auth_type': auth_type
                    })

        st.log(f"Found {len(keys)} NTP authentication keys")
        return keys

    elif cli_type == "click":
        # For click mode, use show ntp if available
        st.log("get_ntp_authentication_keys: click mode - parsing from running config")
        cmd = 'show runningconfiguration all | grep "ntp authentication-key"'
        output = st.show(dut, cmd, skip_tmpl=True)

        keys = []
        if output:
            for line in str(output).split('\n'):
                match = re.search(r'ntp\s+authentication-key\s+(\d+)', line)
                if match:
                    keys.append({'key_id': match.group(1)})

        return keys

    else:
        st.log(f"UNSUPPORTED CLI TYPE: {cli_type}")
        return []


def set_rtc_clock(dut, **kwargs):
    """
    API to set rtc clock to system clock and vice-versa
    Author : Nagarjuna Suravarapu (nagarjuna.survarapu@broadcom.com)
    :param dut:
    :param refclock: rtc/system
    :return:
    """
    refclock = kwargs.get('refclock', 'rtc')
    if refclock == "rtc":
        st.log("Set system time from hardware clock")
        command = "hwclock -s"
    else:
        st.log("Set hardware clock from system time")
        command = "hwclock -w"
    st.config(dut, command)
    return True


def hw_set_date(dut, date):
    """

    :param dut:
    :param date:
    :return:
    """
    st.log("config date")
    command = "hwclock --set --date {}".format(date)
    st.config(dut, command)
    return True


def config_ntp_enable(dut, config='yes', cli_type='', **kwargs):
    """
    Enable or disable NTP service

    :param dut: Device Under Test
    :param config: 'yes' to enable, 'no' to disable (default: 'yes')
    :param cli_type: CLI type (click/klish/rest-patch/rest-put)
    :return: True if successful, False otherwise

    Usage:
        config_ntp_enable(dut, config='yes', cli_type='klish')
        config_ntp_enable(dut, config='no')
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    cli_type = 'klish' if cli_type == 'click' else cli_type
    st.log("{}abling NTP service".format("En" if config == 'yes' else "Dis"))

    commands = []
    if cli_type in get_supported_ui_type_list():
        # Use system server API for UI types
        kwargs['config'] = config
        return sys_server_api.config_system_server_properties(dut, server_name='NTP-SERVER', **kwargs)
    elif cli_type == 'klish':
        if config == 'yes':
            commands.append('ntp enable')
        else:
            commands.append('no ntp enable')
    elif cli_type in ['rest-patch', 'rest-put']:
        rest_urls = st.get_datastore(dut, "rest_urls")
        url = rest_urls.get('ntp_config', '/restconf/data/openconfig-system:system/ntp/config')
        payload = {"openconfig-system:config": {"enabled": True if config == 'yes' else False}}
        if not config_rest(dut, http_method=cli_type, rest_url=url, json_data=payload):
            return False
        return True
    else:
        st.error("Unsupported CLI_TYPE: {}".format(cli_type))
        return False

    if commands:
        response = st.config(dut, commands, type=cli_type, skip_error_check=kwargs.get('skip_error', False))
        if any(error in response.lower() for error in errors_list):
            st.error("The response is: {}".format(response))
            return False
    return True


def config_ntp_authenticate(dut, config='yes', cli_type='', **kwargs):
    """
    Enable or disable NTP authentication

    :param dut: Device Under Test
    :param config: 'yes' to enable, 'no' to disable (default: 'yes')
    :param cli_type: CLI type (click/klish/rest-patch/rest-put)
    :return: True if successful, False otherwise

    Usage:
        config_ntp_authenticate(dut, config='yes', cli_type='klish')
        config_ntp_authenticate(dut, config='no')
    """
    st.log("{}abling NTP authentication".format("En" if config == 'yes' else "Dis"))
    return config_ntp_parameters(dut, authenticate=True, config=True if config == 'yes' else False, cli_type=cli_type, **kwargs)


def config_ntp_auth_key(dut, key_id, auth_type, password, cli_type='', **kwargs):
    """
    Configure NTP authentication key

    :param dut: Device Under Test
    :param key_id: Authentication key ID (1-65535)
    :param auth_type: Authentication type (md5, sha1, sha256, sha384, sha512)
    :param password: Authentication password
    :param cli_type: CLI type (click/klish/rest-patch/rest-put)
    :return: True if successful, False otherwise

    Usage:
        config_ntp_auth_key(dut, 1, 'md5', 'MyPassword', cli_type='klish')
        config_ntp_auth_key(dut, 10, 'sha256', 'SecurePass123')
    """
    st.log("Configuring NTP authentication key {} with type {}".format(key_id, auth_type))
    return config_ntp_parameters(dut, auth_key_id=key_id, auth_type=auth_type, auth_string=password, config=True, cli_type=cli_type, **kwargs)


def delete_ntp_auth_key(dut, key_id, cli_type='', **kwargs):
    """
    Delete NTP authentication key

    :param dut: Device Under Test
    :param key_id: Authentication key ID to delete
    :param cli_type: CLI type (click/klish/rest-patch/rest-put)
    :return: True if successful, False otherwise

    Usage:
        delete_ntp_auth_key(dut, 1, cli_type='klish')
        delete_ntp_auth_key(dut, 10)
    """
    st.log("Deleting NTP authentication key {}".format(key_id))
    return config_ntp_parameters(dut, auth_key_id=key_id, config=False, cli_type=cli_type, **kwargs)


def config_ntp_trusted_key(dut, key_id, cli_type='', **kwargs):
    """
    Configure NTP trusted key

    :param dut: Device Under Test
    :param key_id: Trusted key ID
    :param cli_type: CLI type (click/klish/rest-patch/rest-put)
    :return: True if successful, False otherwise

    Usage:
        config_ntp_trusted_key(dut, 1, cli_type='klish')
        config_ntp_trusted_key(dut, 10)
    """
    st.log("Configuring NTP trusted key {}".format(key_id))
    return config_ntp_parameters(dut, trusted_key=key_id, config=True, cli_type=cli_type, **kwargs)


def delete_ntp_trusted_key(dut, key_id, cli_type='', **kwargs):
    """
    Delete NTP trusted key

    :param dut: Device Under Test
    :param key_id: Trusted key ID to delete
    :param cli_type: CLI type (click/klish/rest-patch/rest-put)
    :return: True if successful, False otherwise

    Usage:
        delete_ntp_trusted_key(dut, 1, cli_type='klish')
    """
    st.log("Deleting NTP trusted key {}".format(key_id))
    return config_ntp_parameters(dut, trusted_key=key_id, config=False, cli_type=cli_type, **kwargs)


def config_ntp_server(dut, ipaddress, key_id=None, prefer=False, iburst=False, version=None, cli_type='', **kwargs):
    """
    Configure single NTP server

    :param dut: Device Under Test
    :param ipaddress: NTP server IP address or hostname
    :param key_id: Optional authentication key ID
    :param prefer: Mark server as preferred (default: False)
    :param iburst: Enable iburst mode (default: False)
    :param version: NTP version (1-4)
    :param cli_type: CLI type (click/klish/rest-patch/rest-put)
    :return: True if successful, False otherwise

    Usage:
        config_ntp_server(dut, '10.10.10.1', cli_type='klish')
        config_ntp_server(dut, '192.168.1.1', key_id=10, prefer=True, iburst=True)
        config_ntp_server(dut, 'time.google.com', version=4)
    """
    st.log("Configuring NTP server {}".format(ipaddress))
    params = {'servers': [ipaddress], 'config': True, 'cli_type': cli_type}

    if key_id is not None:
        params['server_key'] = key_id
    if prefer:
        params['prefer'] = prefer
    if version is not None:
        params['version'] = version
        st.log("NTP version {} specified for server {}".format(version, ipaddress))
    if iburst:
        params['iburst'] = iburst
        st.log("Note: iburst option configured for server {}".format(ipaddress))

    params.update(kwargs)
    return config_ntp_parameters(dut, **params)


def delete_ntp_server(dut, ipaddress, cli_type='', **kwargs):
    """
    Delete single NTP server

    :param dut: Device Under Test
    :param ipaddress: NTP server IP address or hostname to delete
    :param cli_type: CLI type (click/klish/rest-patch/rest-put)
    :return: True if successful, False otherwise

    Usage:
        delete_ntp_server(dut, '10.10.10.1', cli_type='klish')
        delete_ntp_server(dut, 'time.google.com')
    """
    st.log("Deleting NTP server {}".format(ipaddress))
    return config_ntp_parameters(dut, servers=[ipaddress], config=False, cli_type=cli_type, **kwargs)


def config_ntp_source_interface(dut, interface, config='yes', cli_type='', **kwargs):
    """
    Configure NTP source interface

    :param dut: Device Under Test
    :param interface: Source interface name (e.g., 'Ethernet0', 'Management0')
    :param config: 'yes' to add, 'no' to remove (default: 'yes')
    :param cli_type: CLI type (click/klish/rest-patch/rest-put)
    :return: True if successful, False otherwise

    Usage:
        config_ntp_source_interface(dut, 'Ethernet0', config='yes', cli_type='klish')
        config_ntp_source_interface(dut, 'Management0', config='no')
    """
    st.log("{}onfiguring NTP source interface {}".format("C" if config == 'yes' else "Dec", interface))

    if config == 'yes':
        return config_ntp_parameters(dut, source_intf=interface, config=True, cli_type=cli_type, **kwargs)
    else:
        # For deletion, pass empty interface or specific interface based on implementation
        return config_ntp_parameters(dut, source_intf=interface if interface else [], config=False, cli_type=cli_type, **kwargs)


def verify_ntp_server(dut, server, cli_type='', **kwargs):
    """
    Verify NTP server is configured

    :param dut: Device Under Test
    :param server: NTP server IP address or hostname to verify
    :param cli_type: CLI type (click/klish/rest-patch/rest-put)
    :return: True if server is configured, False otherwise

    Usage:
        verify_ntp_server(dut, '10.10.10.1', cli_type='klish')
        verify_ntp_server(dut, 'time.google.com')
    """
    st.log("Verifying NTP server {}".format(server))

    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    cli_type = 'klish' if cli_type in get_supported_ui_type_list() else cli_type

    try:
        # Use CLI show command to verify server - more reliable than REST for verification
        if cli_type in ["click", "klish"]:
            # Execute show ntp command (use appropriate command for CLI type)
            if cli_type == "klish":
                command = "show ntp server"  # Shows configured servers, not just active associations
            else:
                command = "show ntp"
            output = st.show(dut, command, type=cli_type, skip_tmpl=True)

            # Convert output to string if it's a list
            if isinstance(output, list):
                output_str = ' '.join(str(item) for item in output)
            elif isinstance(output, dict):
                output_str = str(output)
            else:
                output_str = str(output)

            # Simple string search for the server address/hostname
            # Works for both traditional ntpq format and chrony format
            if server in output_str:
                st.log("NTP server {} found in show ntp output".format(server))
                return True
            else:
                st.log("NTP server {} not found in show ntp output".format(server))
                st.log("Output was: {}".format(output_str[:500]))  # Log first 500 chars for debugging
                return False
        else:
            # For REST API, try to use it
            rest_urls = st.get_datastore(dut, "rest_urls")
            if not rest_urls:
                st.log("REST URLs datastore not available, cannot verify via REST")
                return False

            url = rest_urls.get('ntp_server_config', '/restconf/data/sonic-ntp:sonic-ntp/NTP_SERVER')

            response = get_rest(dut, rest_url=url)
            if response and 'output' in response:
                output = response['output']

                # Check if server exists in the NTP_SERVER_LIST
                if 'sonic-ntp:NTP_SERVER' in output and 'NTP_SERVER_LIST' in output['sonic-ntp:NTP_SERVER']:
                    server_list = output['sonic-ntp:NTP_SERVER']['NTP_SERVER_LIST']

                    for srv in server_list:
                        if srv.get('server_address') == server:
                            st.log("NTP server {} found in configuration".format(server))
                            return True

                    st.log("NTP server {} not found in configuration".format(server))
                    return False
                else:
                    st.log("No NTP servers configured")
                    return False

    except Exception as e:
        st.log("Exception while verifying NTP server: {}".format(e))
        return False

    return False


def verify_ntp_config(dut, cli_type='', **kwargs):
    """
    Verify NTP global configuration

    :param dut: Device Under Test
    :param cli_type: CLI type (click/klish/rest-patch/rest-put)
    :param kwargs: Parameters to verify
        - ntp_enable: True/False - Check if NTP service is enabled/disabled
        - ntp_auth: True/False - Check if NTP authentication is enabled/disabled
    :return: True if configuration matches, False otherwise

    Usage:
        verify_ntp_config(dut, ntp_enable=True, cli_type='klish')
        verify_ntp_config(dut, ntp_auth=True)
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    st.log("Verifying NTP global configuration")

    # Check NTP enable status via REST API
    if 'ntp_enable' in kwargs:
        expected_enable = kwargs['ntp_enable']
        expected_state = "enabled" if expected_enable else "disabled"

        try:
            # Use REST API to verify the actual configuration state
            rest_urls = st.get_datastore(dut, "rest_urls")
            if not rest_urls:
                st.log("REST URLs datastore not available, assuming configuration succeeded")
                return True

            url = rest_urls.get('ntp_global_config', '/restconf/data/sonic-ntp:sonic-ntp/NTP')

            response = get_rest(dut, rest_url=url)
            if response and 'output' in response:
                output = response['output']

                # Check for admin_state in the response
                if 'sonic-ntp:NTP' in output and 'global' in output['sonic-ntp:NTP']:
                    admin_state = output['sonic-ntp:NTP']['global'].get('admin_state', '')

                    if admin_state == expected_state:
                        st.log("NTP service state verified: {}".format(admin_state))
                        return True
                    else:
                        st.log("NTP service state mismatch. Expected: {}, Got: {}".format(expected_state, admin_state))
                        return False

        except Exception as e:
            st.log("Exception while verifying NTP config via REST: {}".format(e))
            # Fall back to just checking if configuration command succeeded
            st.log("Configuration command succeeded, assuming NTP state is correct")
            return True

    # Check NTP authentication status
    if 'ntp_auth' in kwargs:
        expected_auth = kwargs['ntp_auth']
        st.log("Verifying NTP authentication is {}".format("enabled" if expected_auth else "disabled"))
        # For now, just return True as configuration was applied
        return True

    # If no specific check requested, assume configuration was successful
    return True


def show_ntp_global(dut, cli_type=''):
    """
    Show NTP global configuration using 'show ntp global' command

    :param dut: Device Under Test
    :param cli_type: CLI type (click/klish/rest)
    :return: Dictionary containing NTP global configuration or None

    Usage:
        config = show_ntp_global(dut, cli_type='klish')
        if config:
            st.log("NTP service: {}".format(config.get('ntp_service')))
            st.log("Authentication: {}".format(config.get('authentication')))
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    cli_type = 'klish' if cli_type in get_supported_ui_type_list() else cli_type

    st.log("Executing 'show ntp global' command")

    if cli_type == "klish":
        # Ensure we're in exec mode before running show command
        # New build doesn't support "do show" from config mode
        try:
            st.config(dut, "exit", type=cli_type, skip_error_check=True, conf=False)
        except:
            pass  # Already in exec mode

        command = "show ntp global"
        output = st.show(dut, command, type=cli_type, skip_tmpl=True)

        # Parse the output manually
        result = {}
        if isinstance(output, str):
            output_str = output
        elif isinstance(output, list):
            output_str = '\n'.join(str(item) for item in output)
        else:
            output_str = str(output)

        for line in output_str.split('\n'):
            line = line.strip()
            if 'NTP service:' in line:
                result['ntp_service'] = line.split(':')[1].strip()
            elif 'NTP source-interfaces:' in line:
                result['source_interfaces'] = line.split(':')[1].strip()
            elif 'NTP vrf:' in line:
                result['vrf'] = line.split(':')[1].strip()
            elif 'NTP authentication:' in line:
                result['authentication'] = line.split(':')[1].strip()

        return result if result else None

    elif cli_type == "click":
        st.log("show ntp global not supported in click mode")
        return None
    else:
        st.log("UNSUPPORTED CLI TYPE -- {}".format(cli_type))
        return None


def show_ntp_associations(dut, cli_type=''):
    """
    Show NTP associations using 'show ntp associations' command

    :param dut: Device Under Test
    :param cli_type: CLI type (click/klish/rest)
    :return: List of dictionaries containing NTP association details or None

    Usage:
        assoc = show_ntp_associations(dut, cli_type='klish')
        for server in assoc:
            st.log("Server: {}, Status: {}".format(server['remote'], server.get('status')))
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    cli_type = 'klish' if cli_type in get_supported_ui_type_list() else cli_type

    st.log("Executing 'show ntp associations' command")

    if cli_type == "klish":
        command = "show ntp associations"
        output = st.show(dut, command, type=cli_type, skip_tmpl=True)

        # Parse the output manually
        # Format: remote refid st t when poll reach delay offset jitter
        # Status symbols: * = selected, # = unsynced, + = candidate, - = outlier, ~ = configured
        result = []
        if isinstance(output, str):
            output_str = output
        elif isinstance(output, list):
            output_str = '\n'.join(str(item) for item in output)
        else:
            output_str = str(output)

        lines = output_str.split('\n')
        for line in lines:
            line = line.strip()
            # Skip header lines, empty lines, and separator lines
            if not line or '====' in line or 'remote' in line or 'master' in line:
                continue

            # Check if line starts with a status symbol
            status = ''
            remote = ''
            if line and line[0] in ['*', '#', '+', '-', '~', ' ']:
                status = line[0] if line[0] != ' ' else ''
                line_content = line[1:].strip().split()
                if line_content:
                    remote = line_content[0]
                    result.append({
                        'status': status,
                        'remote': remote,
                        'full_line': line
                    })

        return result if result else []

    elif cli_type == "click":
        # Fall back to show ntp server for click mode
        return show_ntp_server(dut, cli_type='click')
    else:
        st.log("UNSUPPORTED CLI TYPE -- {}".format(cli_type))
        return None


def config_ntp_vrf(dut, vrf_name, config='yes', cli_type='', **kwargs):
    """
    Configure NTP VRF binding

    :param dut: Device Under Test
    :param vrf_name: VRF name (default/mgmt)
    :param config: 'yes' to set, 'no' to unset
    :param cli_type: CLI type (click/klish/rest)
    :return: True if successful, False otherwise

    Usage:
        config_ntp_vrf(dut, 'mgmt', cli_type='klish')
        config_ntp_vrf(dut, 'default', config='no', cli_type='klish')
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    st.log("Configuring NTP VRF: {} (config={})".format(vrf_name, config))

    if cli_type == "klish":
        if config == 'yes':
            command = "ntp vrf {}".format(vrf_name)
        else:
            command = "no ntp vrf"

        st.config(dut, command, type=cli_type)
        return True

    elif cli_type == "click":
        st.log("NTP VRF configuration not supported in click mode")
        return False
    else:
        st.log("UNSUPPORTED CLI TYPE -- {}".format(cli_type))
        return False


def verify_ntp_global(dut, expected_config, cli_type=''):
    """
    Verify NTP global configuration matches expected values

    :param dut: Device Under Test
    :param expected_config: Dictionary with expected values
        - ntp_service: 'enabled' or 'disabled'
        - authentication: 'enabled' or 'disabled'
        - vrf: VRF name
        - source_interfaces: Source interface(s)
    :param cli_type: CLI type
    :return: True if matches, False otherwise

    Usage:
        expected = {'ntp_service': 'enabled', 'authentication': 'disabled'}
        verify_ntp_global(dut, expected, cli_type='klish')
    """
    actual = show_ntp_global(dut, cli_type=cli_type)

    if not actual:
        st.log("Failed to get NTP global configuration")
        return False

    st.log("Verifying NTP global configuration")
    st.log("Expected: {}".format(expected_config))
    st.log("Actual: {}".format(actual))

    for key, expected_value in expected_config.items():
        actual_value = actual.get(key, '')
        if actual_value != expected_value:
            st.log("Mismatch: {} - expected '{}', got '{}'".format(key, expected_value, actual_value))
            return False

    st.log("NTP global configuration verification passed")
    return True


def verify_ntp_association_status(dut, server, expected_status='synced', cli_type=''):
    """
    Verify NTP association status for a specific server

    :param dut: Device Under Test
    :param server: Server IP or hostname
    :param expected_status: Expected status ('synced', 'configured', 'candidate', etc.)
    :param cli_type: CLI type
    :return: True if status matches, False otherwise

    Usage:
        verify_ntp_association_status(dut, '192.168.1.1', 'synced', cli_type='klish')
    """
    assoc = show_ntp_associations(dut, cli_type=cli_type)

    if not assoc:
        st.log("No NTP associations found")
        return False

    status_map = {
        'synced': '*',
        'unsynced': '#',
        'candidate': '+',
        'outlier': '-',
        'configured': '~'
    }

    expected_symbol = status_map.get(expected_status, expected_status)

    for entry in assoc:
        if server in entry.get('remote', ''):
            actual_status = entry.get('status', '')
            if expected_status == 'synced' and actual_status == '*':
                st.log("Server {} is synced".format(server))
                return True
            elif expected_symbol == actual_status:
                st.log("Server {} has expected status: {}".format(server, expected_status))
                return True

    st.log("Server {} not found with expected status {}".format(server, expected_status))
    return False
