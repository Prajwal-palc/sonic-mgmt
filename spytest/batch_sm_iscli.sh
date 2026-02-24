#!/bin/bash

# ==========================================================
# SM_ISCLI REGRESSION - FEATURE WISE SINGLE-RUN SPYTEST BATCHES
# Each SpyTest call = One Dashboard Batch
# Logs: ./logs/SM_ISCLI_<DATE>/<FEATURE>/<TIME>/
# ==========================================================

DATE_DIR=$(date +%Y%m%d)
TIME_STAMP=$(date +%H%M%S)

# Create SM_ISCLI_Report directory to organize all SM_ISCLI logs
SM_ISCLI_REPORT_ROOT="./logs/SM_ISCLI_Report"
BASE_LOG="${SM_ISCLI_REPORT_ROOT}/SM_ISCLI_${DATE_DIR}"

mkdir -p "${BASE_LOG}"

echo "=============================================="
echo " SM_ISCLI REGRESSION STARTED"
echo " DATE : ${DATE_DIR}"
echo "=============================================="

run_batch () {
    FEATURE=$1
    TESTBED=$2
    shift 2
    TESTS="$@"

    LOG_PATH="${BASE_LOG}/${FEATURE}/${TIME_STAMP}"
    mkdir -p "${LOG_PATH}"

    echo "----------------------------------------------"
    echo " Running Batch: ${FEATURE}"
    echo " Testbed     : ${TESTBED}"
    echo " Logs        : ${LOG_PATH}"
    echo "----------------------------------------------"

    ./bin/spytest --tryssh 1 \
      --testbed "${TESTBED}" \
      ${TESTS} \
      --logs-path "${LOG_PATH}" \
      --log-level debug \
      --skip-init-config \
      --ifname-type native \
      --get-tech-support none

    RC=$?
    echo " Batch ${FEATURE} completed with RC=${RC}"

    if [ ${RC} -ne 0 ]; then
        echo " WARNING: Batch ${FEATURE} failed. Continuing to next batch."
    fi
}

# ==========================================================
# BATCH-1 : SM_ISCLI_7 - Static Route Tests
# ==========================================================

run_batch "SM_ISCLI_7_STATIC_ROUTES" "./testbeds/testbed_vs_1node.yaml" \
routing/static/test_sm_iscli_7.py


# ==========================================================
# BATCH-2 : SM_ISCLI_4 - eBGP Multihop
# ==========================================================

run_batch "SM_ISCLI_4_EBGP_MULTIHOP" "./testbeds/testbed_vs_2d.yaml" \
system/SM_ISCLI/test_sm_iscli_4_ebgp_multihop.py


# ==========================================================
# BATCH-3 : SM_ISCLI_5 - BGP L2VPN EVPN Output
# ==========================================================

run_batch "SM_ISCLI_5_BGP_L2VPN_EVPN" "./testbeds/testbed_vs_2d.yaml" \
system/SM_ISCLI/test_sm_iscli_5_bgp_l2vpn_evpn_output.py


# ==========================================================
# BATCH-4 : SM_ISCLI_6 - BGP Timers
# ==========================================================

run_batch "SM_ISCLI_6_BGP_TIMERS" "./testbeds/testbed_vs_2d.yaml" \
system/SM_ISCLI/test_sm_iscli_6_bgp_timers.py


# ==========================================================
# BATCH-5 : SM_ISCLI_59 - Management IP Route
# ==========================================================

run_batch "SM_ISCLI_59_MGMT_IP_ROUTE" "./testbeds/ztp_standalone.yaml" \
system/management/test_management_ip_route.py


# ==========================================================
# BATCH-6 : SM_ISCLI_43, SM_ISCLI_61 - Management Interface Config
# ==========================================================

run_batch "SM_ISCLI_43_SM_ISCLI_61_MGMT_INTERFACE_CONFIG" "./testbeds/ztp_standalone.yaml" \
system/management/test_management_interface_config.py


# ==========================================================
# BATCH-7 : SM_ISCLI_42, SM_ISCLI_68 - VLAN Basic Config
# ==========================================================

run_batch "SM_ISCLI_42_SM_ISCLI_68_VLAN_BASIC_CONFIG" "./testbeds/ztp_standalone.yaml" \
system/management/test_vlan_basic_config.py


# ==========================================================
# BATCH-8 : SM_ISCLI_16 - Interface IP No-Op
# ==========================================================

run_batch "SM_ISCLI_16_IP_NOOP" "./testbeds/testbed_vs_1node.yaml" \
system/interface/test_sm_iscli_16_ip_noop.py


# ==========================================================
# BATCH-9 : SM_ISCLI_60 - VLAN Interface Lifecycle
# ==========================================================

run_batch "SM_ISCLI_60_VLAN_INTERFACE_LIFECYCLE" "./testbeds/ztp_standalone.yaml" \
switching/test_vlan_interface_lifecycle.py


# ==========================================================
# BATCH-10 : SM_ISCLI_66 - Switching Mode
# ==========================================================

run_batch "SM_ISCLI_66_SWITCHING_MODE" "./testbeds/ztp_standalone.yaml" \
switching/test_switching_mode.py


# ==========================================================
# BATCH-11 : SM_ISCLI_8 - Management Static IP
# ==========================================================

run_batch "SM_ISCLI_8_MGMT_STATIC_IP" "./testbeds/testbed_vs_2d.yaml" \
system/SM_ISCLI/test_sm_iscli_8_management_static_ip.py


# ==========================================================
# BATCH-12 : SM_ISCLI_9 - L2VPN EVPN Order
# ==========================================================

run_batch "SM_ISCLI_9_L2VPN_EVPN_ORDER" "./testbeds/testbed_vs_2d.yaml" \
system/SM_ISCLI/test_sm_iscli_9_l2vpn_evpn_order.py


# ==========================================================
# BATCH-13 : SM_ISCLI_11 - BGP Graceful Restart
# ==========================================================

run_batch "SM_ISCLI_11_BGP_GRACEFUL_RESTART" "./testbeds/testbed_vs_2d.yaml" \
system/SM_ISCLI/test_sm_iscli_11_bgp_graceful_restart.py


# ==========================================================
# BATCH-14 : SM_ISCLI_12 - Management Port Visible
# ==========================================================

run_batch "SM_ISCLI_12_MGMT_PORT_VISIBLE" "./testbeds/testbed_vs_2d.yaml" \
system/SM_ISCLI/test_sm_iscli_12_management_port_visible.py


# ==========================================================
# BATCH-15 : SM_ISCLI_10 - BGP Update-Source Format
# ==========================================================

run_batch "SM_ISCLI_10_UPDATE_SOURCE" "./testbeds/testbed_vs_2d.yaml" \
routing/bgp/test_sm_iscli_10_update_source_format.py


# ==========================================================
# BATCH-16 : SM_ISCLI_13 - BGP IBGP Multipath
# ==========================================================

run_batch "SM_ISCLI_13_IBGP_MULTIPATH" "./testbeds/testbed_vs_2d.yaml" \
routing/bgp/test_sm_iscli_13_ibgp_multipath.py


# ==========================================================
# BATCH-17 : SM_ISCLI_15 - BGP Network IP Conflict
# ==========================================================

run_batch "SM_ISCLI_15_BGP_NETWORK_CONFLICT" "./testbeds/testbed_vs_2d.yaml" \
routing/bgp/test_sm_iscli_15_bgp_network_ip_conflict.py


# ==========================================================
# BATCH-18 : SM_ISCLI_41 - BGP Remote AS Internal External
# ==========================================================

run_batch "SM_ISCLI_41_BGP_REMOTE_AS_INTERNAL_EXTERNAL" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_bgp_remote_as_internal_external.py


# ==========================================================
# BATCH-19 : SM_ISCLI_82 - BGP VRF Validation
# ==========================================================

run_batch "SM_ISCLI_82_BGP_VRF_VALIDATION" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_bgp_vrf_validation.py


# ==========================================================
# BATCH-20 : SM_ISCLI_74 - Hostname Validation
# ==========================================================

run_batch "SM_ISCLI_74_HOSTNAME_VALIDATION" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_hostname_validation.py


# ==========================================================
# BATCH-21 : SM_ISCLI_29 - IP Route SVI
# ==========================================================

run_batch "SM_ISCLI_29_IP_ROUTE_SVI" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_ip_route_svi.py


# ==========================================================
# BATCH-22 : SM_ISCLI_46 - Port Breakout
# ==========================================================

run_batch "SM_ISCLI_46_PORT_BREAKOUT" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_port_breakout.py


# ==========================================================
# BATCH-23 : SM_ISCLI_60 - Remove VLAN Interface
# ==========================================================

run_batch "SM_ISCLI_60_REMOVE_VLAN_INTERFACE" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_remove_vlan_interface.py


# ==========================================================
# BATCH-24 : SM_ISCLI_12 - Show IP Interface
# ==========================================================

run_batch "SM_ISCLI_12_SHOW_IP_INTERFACE" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_show_ip_interface.py


# ==========================================================
# BATCH-25 : SM_ISCLI_33 - Show Run Interface
# ==========================================================

run_batch "SM_ISCLI_33_SHOW_RUN_INTERFACE" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_show_run_interface.py


# ==========================================================
# BATCH-26 : SM_ISCLI_54 - Show Running Config
# ==========================================================

run_batch "SM_ISCLI_54_SHOW_RUNNING_CONFIG" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_show_running_config.py


# ==========================================================
# BATCH-27 : SM_ISCLI_73 - VRF Interface Validation
# ==========================================================

run_batch "SM_ISCLI_73_VRF_INTERFACE_VALIDATION" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_vrf_interface_validation.py


# ==========================================================
# BATCH-28 : SM_ISCLI_19 - Grep Filter Effectiveness
# ==========================================================

run_batch "SM_ISCLI_19_GREP_FILTER" "./testbeds/testbed_vs_1node.yaml" \
system/cli/test_sm_iscli_19_grep_filter.py


# ==========================================================
# BATCH-29 : SM_ISCLI_20 - OSPF Loopback Without IP
# ==========================================================

run_batch "SM_ISCLI_20_OSPF_LOOPBACK_NO_IP" "./testbeds/testbed_vs_2d.yaml" \
routing/ospf/test_sm_iscli_20_ospf_loopback_no_ip.py


# ==========================================================
# BATCH-30 : SM_ISCLI_34, SM_ISCLI_32, SM_ISCLI_31 - Interface IP Config Validation
# ==========================================================

run_batch "SM_ISCLI_34_SM_ISCLI_32_SM_ISCLI_31_INTERFACE_IP_CONFIG" "./testbeds/ztp_standalone.yaml" \
system/interface/test_interface_ip_config_validation.py


# ==========================================================
# BATCH-31 : SM_ISCLI_24 - sonic-cli -c Flag Test
# ==========================================================

run_batch "SM_ISCLI_24_SONIC_CLI_C_FLAG" "./testbeds/testbed_vs_1node.yaml" \
system/cli/test_sm_iscli_24_sonic_cli_c_flag.py


# ==========================================================
# BATCH-32 : SM_ISCLI_23 - Route Map Show Running Config
# ==========================================================

run_batch "SM_ISCLI_23_ROUTE_MAP_SHOW_RUN" "./testbeds/testbed_vs_1node.yaml" \
routing/test_sm_iscli_23_route_map_show_run.py


# ==========================================================
# BATCH-33 : SM_ISCLI_82 - BGP VRF Unconfigurations
# ==========================================================

run_batch "SM_ISCLI_82_BGP_VRF_UNCONFIG" "./testbeds/testbed_2vs.yaml" \
system/SM_ISCLI/test_sm_iscli_82_bgp_vrf_unconfigurations.py


# ==========================================================
# BATCH-34 : SM_ISCLI_48, SM_ISCLI_49, SM_ISCLI_51 - IPv4 ACL CLI Validation
# ==========================================================

run_batch "SM_ISCLI_48_SM_ISCLI_49_SM_ISCLI_51_IPV4_ACL_CLI" "./testbeds/ztp_standalone.yaml" \
qos/acl/test_ipv4_acl_cli_validation.py


# ==========================================================
# BATCH-35 : SM_ISCLI_69 - VLAN Negative Member Tests
# ==========================================================

run_batch "SM_ISCLI_69_VLAN_NEGATIVE_MEMBER" "./testbeds/testbed_vs_2d.yaml" \
switching/vlan/test_vlan_negative_member.py


# ==========================================================
# BATCH-36 : SM_ISCLI_76 - Show IP Route Filtering
# ==========================================================

run_batch "SM_ISCLI_76_SHOW_IP_ROUTE_FILTERING" "./testbeds/testbed_vs_2d.yaml" \
routing/ipv4/test_show_ip_route_filtering.py


# ==========================================================
# BATCH-37 : SM_ISCLI_21 - OSPF Network Removal
# ==========================================================

run_batch "SM_ISCLI_21_OSPF_NETWORK_REMOVAL" "./testbeds/testbed_vs_2d.yaml" \
routing/ospf/test_ospf_network_removal.py


# ==========================================================
# BATCH-38 : SM_ISCLI_27 - BGP Peergroup Activate
# ==========================================================

run_batch "SM_ISCLI_27_BGP_PEERGROUP_ACTIVATE" "./testbeds/testbed_vs_2d.yaml" \
routing/bgp/test_bgp_peergroup_activate.py


# ==========================================================
# BATCH-39 : SM_ISCLI_52 - LLDP CLI Validation
# ==========================================================

run_batch "SM_ISCLI_52_LLDP_CLI_VALIDATION" "./testbeds/testbed_vs_1node.yaml" \
system/lldp/test_lldp_cli_validation.py


# ==========================================================
# BATCH-40 : SM_ISCLI_53 - Hostname Config Verification
# ==========================================================

run_batch "SM_ISCLI_53_HOSTNAME_CONFIG_VERIFICATION" "./testbeds/testbed_vs_1node.yaml" \
system/hostname/test_hostname_config_verification.py


# ==========================================================
# BATCH-41 : SM_ISCLI_70 - BGP IPv6 CLI Validation
# ==========================================================

run_batch "SM_ISCLI_70_BGP_IPV6_CLI_VALIDATION" "./testbeds/testbed_vs_2d.yaml" \
routing/bgp/test_bgp_ipv6_cli_validation.py


# ==========================================================
# BATCH-42 : SM_ISCLI_72 - IPv6 Interface Enable/Disable
# ==========================================================

run_batch "SM_ISCLI_72_IPV6_INTERFACE_ENABLE_DISABLE" "./testbeds/testbed_vs_1node.yaml" \
system/ipv6/test_ipv6_interface_enable_disable.py


# ==========================================================
# BATCH-43 : SM_ISCLI_76 - IP Route Show Commands
# ==========================================================

run_batch "SM_ISCLI_76_IP_ROUTE_SHOW_COMMANDS" "./testbeds/ztp_standalone.yaml" \
system/ip_route_cli/test_ip_route_show_commands.py


# ==========================================================
# BATCH-44 : SM_ISCLI_77 - VRF CLI Negative Tests
# ==========================================================

run_batch "SM_ISCLI_77_VRF_CLI_NEGATIVE" "./testbeds/ztp_standalone.yaml" \
system/vrf/test_vrf_cli_negative.py


# ==========================================================
# BATCH-45 : SM_ISCLI_25 - Interface Description Quotes
# ==========================================================

run_batch "SM_ISCLI_25_INTERFACE_DESC_QUOTES" "./testbeds/testbed_vs_1node.yaml" \
system/cli/test_sm_iscli_25_interface_description_quotes.py


# ==========================================================
# BATCH-46 : SM_ISCLI_78 - Loopback Interface Configuration
# ==========================================================

run_batch "SM_ISCLI_78_LOOPBACK_INTERFACE_CONFIG" "./testbeds/ztp_standalone.yaml" \
system/interface/test_loopback_interface_config.py


# ==========================================================
# BATCH-47 : SM_ISCLI_26 - Platform and Interface CLI
# ==========================================================

run_batch "SM_ISCLI_26_PLATFORM_INTERFACE_CLI" "./testbeds/testbed_vs_1node.yaml" \
system/cli/test_sm_iscli_26_platform_interface_cli.py


# ==========================================================
# BATCH-48 : SM_ISCLI_28 - BGP Show Configuration
# ==========================================================

run_batch "SM_ISCLI_28_BGP_SHOW_CONFIG" "./testbeds/testbed_vs_1node.yaml" \
routing/bgp/test_sm_iscli_28_bgp_show_config.py


# ==========================================================
# BATCH-49 : SM_ISCLI_VRF_BASIC - VRF Basic Config
# ==========================================================

run_batch "SM_ISCLI_VRF_BASIC" "./testbeds/ztp_standalone.yaml" \
system/vrf/test_vrf_basic.py


# ==========================================================
# BATCH-50 : SM_ISCLI_P2_78 - LACP Fast Rate Bug
# ==========================================================

run_batch "SM_ISCLI_P2_78_LACP_FAST_RATE" "./testbeds/testbed_vs_1node.yaml" \
switching/portchannel/test_sm_iscli_p2_78_lacp_fast_rate.py


# ==========================================================
# BATCH-51 : SM_ISCLI_VRF_INTERFACE_NEGATIVE - VRF Interface Negative Tests
# ==========================================================

run_batch "SM_ISCLI_VRF_INTERFACE_NEGATIVE" "./testbeds/ztp_standalone.yaml" \
system/vrf/test_vrf_interface_negative.py


# ==========================================================
# BATCH-52 : SM_ISCLI_VRF_LOOPBACK_PORTCHANNEL_NEGATIVE - VRF Loopback/PortChannel Negative
# ==========================================================

run_batch "SM_ISCLI_VRF_LOOPBACK_PORTCHANNEL_NEGATIVE" "./testbeds/ztp_standalone.yaml" \
system/vrf/test_vrf_loopback_portchannel_negative.py


# ==========================================================
# BATCH-53 : VRF Ping Tests
# ==========================================================

run_batch "SM_ISCLI_VRF_PING" "./testbeds/ztp_standalone.yaml" \
routing/vrf/test_vrf_ping.py


# ==========================================================
# BATCH-54 : VRF IP Interface Tests
# ==========================================================

run_batch "SM_ISCLI_VRF_IP_INTERFACE" "./testbeds/ztp_standalone.yaml" \
routing/vrf/test_vrf_ip_interface.py


# ==========================================================
# BATCH-55 : IP Prefix List Tests
# ==========================================================

run_batch "SM_ISCLI_IP_PREFIX_LIST" "./testbeds/ztp_standalone.yaml" \
routing/prefix_list/test_ip_prefix_list.py


# ==========================================================
# BATCH-56 : ARP Table Verification
# ==========================================================

run_batch "SM_ISCLI_ARP_TABLE_VERIFICATION" "./testbeds/ztp_standalone.yaml" \
routing/arp/test_arp_table_verification.py


# ==========================================================
# BATCH-57 : Interface CLI Verification
# ==========================================================

run_batch "SM_ISCLI_INTERFACE_CLI_VERIFICATION" "./testbeds/ztp_standalone.yaml" \
system/interface/test_interface_cli_verification.py


# ==========================================================
# BATCH-58 : Route Map Dependency Tests
# ==========================================================

run_batch "SM_ISCLI_ROUTE_MAP_DEPENDENCY" "./testbeds/ztp_standalone.yaml" \
routing/route_map/test_route_map_dependency.py


# ==========================================================
# BATCH-59 : VLAN SVI Removal Tests
# ==========================================================

run_batch "SM_ISCLI_P2_42_VLAN_SVI_REMOVAL" "./testbeds/testbed_2vs.yaml" \
system/iscli_BGP/test_vlan_iscli_p2_42_svi_removal.py


# ==========================================================
# BATCH-60 : VLAN Switchport Trunk Tests
# ==========================================================

run_batch "SM_ISCLI_P2_39_SWITCHPORT_TRUNK_VLAN" "./testbeds/testbed_2vs.yaml" \
system/iscli_BGP/test_vlan_iscli_p2_39_switchport_trunk_vlan.py


# ==========================================================
# BATCH-61 : VRF Binding Tests
# ==========================================================

run_batch "SM_ISCLI_13_VRF_BINDING" "./testbeds/testbed_2vs.yaml" \
system/iscli_BGP/test_sm_iscli_13_vrf_binding.py


# ==========================================================
# BATCH-62 : BGP VRF Instance Tests
# ==========================================================

run_batch "SM_ISCLI_P2_32_BGP_VRF_INSTANCE" "./testbeds/testbed_2vs.yaml" \
system/iscli_BGP/test_bgp_p2_32_vrf_instance.py


# ==========================================================
# BATCH-63 : SM_ISCLI_44 - Copy Command Tests
# ==========================================================

run_batch "SM_ISCLI_44_COPY_COMMAND" "./testbeds/testbed_vs_3rr.yaml" \
system/management/test_sm_iscli44_copy_command.py \
-k "not test_iscli_copy_startup_to_running"


# ==========================================================
# BATCH-64 : SM_ISCLI_40 - BGP eBGP Requires Policy
# ==========================================================

run_batch "SM_ISCLI_40_BGP_EBGP_REQUIRES_POLICY" "./testbeds/testbed_vs_3rr.yaml" \
routing/BGP/test_sm_iscli40_bgp_ebgp_requires_policy.py


# ==========================================================
# BATCH-65 : SM_ISCLI_45 - Write Erase Command Tests
# ==========================================================

run_batch "SM_ISCLI_45_WRITE_ERASE_COMMAND" "./testbeds/testbed_vs_1node.yaml" \
system/management/test_sm_iscli45_write_erase.py


echo "=============================================="
echo " SM_ISCLI REGRESSION COMPLETED"
echo " Logs Root : ${BASE_LOG}"
echo "=============================================="

# Generate Graphical Dashboard
echo "=============================================="
echo " Generating Graphical Dashboard"
echo "=============================================="

# Create dashboard directory in logs
DASHBOARD_DIR="${BASE_LOG}/dashboard"
mkdir -p "${DASHBOARD_DIR}"

DASHBOARD_FILE="${DASHBOARD_DIR}/sm_iscli_dashboard_${DATE_DIR}_${TIME_STAMP}.html"

python3 dashboard/scripts/generate_graphical_dashboard.py \
    --log-root ${BASE_LOG} \
    --out ${DASHBOARD_FILE} \
    --name "SM_ISCLI Regression - ${DATE_DIR}"

echo "=============================================="
echo " Dashboard Generation Complete"
echo "=============================================="
echo "Dashboard available at:"
echo "file://$(pwd)/${DASHBOARD_FILE}"

# Copy dashboard to user directory
USER_DASHBOARD_DIR="${HOME}/Dashboard/SM_ISCLI"
mkdir -p "${USER_DASHBOARD_DIR}"
cp "${DASHBOARD_FILE}" "${USER_DASHBOARD_DIR}/"

echo "Dashboard copy saved to:"
echo "file://${USER_DASHBOARD_DIR}/sm_iscli_dashboard_${DATE_DIR}_${TIME_STAMP}.html"

# Generate Failure Analysis CSV Report
echo "=============================================="
echo " Generating Failure Analysis CSV Report"
echo "==============================================="

FAILURE_CSV="${BASE_LOG}/SM_ISCLI_${DATE_DIR}_failure_analysis_${TIME_STAMP}.csv"

python3 ./utils/generate_failure_analysis.py \
    "${BASE_LOG}" \
    "${FAILURE_CSV}"

if [ -f "${FAILURE_CSV}" ]; then
    echo "==============================================="
    echo " Failure Analysis Report Generated"
    echo "==============================================="
    echo "Failure CSV available at:"
    echo "$(pwd)/${FAILURE_CSV}"

    # Copy failure analysis CSV to user directory
    cp "${FAILURE_CSV}" "${USER_DASHBOARD_DIR}/"
    echo ""
    echo "Failure CSV copy saved to:"
    echo "${USER_DASHBOARD_DIR}/SM_ISCLI_${DATE_DIR}_failure_analysis_${TIME_STAMP}.csv"
else
    echo "Note: No failures found or error generating failure analysis report"
fi

# Generate Test Details Report
echo "=============================================="
echo " Generating Test Details Report"
echo "=============================================="

TEST_DETAILS_CSV="${BASE_LOG}/SM_ISCLI_${DATE_DIR}_test_details_${TIME_STAMP}.csv"

python3 dashboard/scripts/generate_test_details_report.py \
    --log-root "${BASE_LOG}" \
    --out "${TEST_DETAILS_CSV}"

if [ -f "${TEST_DETAILS_CSV}" ]; then
    echo "=============================================="
    echo " Test Details Report Generated"
    echo "=============================================="
    echo "Test Details CSV available at:"
    echo "$(pwd)/${TEST_DETAILS_CSV}"

    # Copy test details CSV to user directory
    cp "${TEST_DETAILS_CSV}" "${USER_DASHBOARD_DIR}/"
    echo ""
    echo "Test Details CSV copy saved to:"
    echo "${USER_DASHBOARD_DIR}/SM_ISCLI_${DATE_DIR}_test_details_${TIME_STAMP}.csv"
else
    echo "Note: Error generating test details report"
fi

# Generate Historical Trend Dashboard
echo "=============================================="
echo " Generating Historical Trend Dashboard"
echo "=============================================="

HISTORICAL_DASHBOARD="${DASHBOARD_DIR}/sm_iscli_historical_${DATE_DIR}_${TIME_STAMP}.html"

# Use SM_ISCLI_Report root directory for historical data
python3 dashboard/scripts/generate_historical_dashboard.py \
    --log-root "${SM_ISCLI_REPORT_ROOT}" \
    --out "${HISTORICAL_DASHBOARD}" \
    --name "SM_ISCLI Historical Trends"

if [ -f "${HISTORICAL_DASHBOARD}" ]; then
    echo "=============================================="
    echo " Historical Dashboard Generated"
    echo "=============================================="
    echo "Historical Dashboard available at:"
    echo "file://$(pwd)/${HISTORICAL_DASHBOARD}"

    # Copy historical dashboard to user directory
    ATHIRA_DASHBOARD_DIR="${HOME}/Athira/Dashboard"
    mkdir -p "${ATHIRA_DASHBOARD_DIR}"
    cp "${HISTORICAL_DASHBOARD}" "${ATHIRA_DASHBOARD_DIR}/"
    echo ""
    echo "Historical Dashboard copy saved to:"
    echo "file://${ATHIRA_DASHBOARD_DIR}/sm_iscli_historical_${DATE_DIR}_${TIME_STAMP}.html"
else
    echo "Note: Error generating historical dashboard"
fi


