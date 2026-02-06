#!/bin/bash

# ==========================================================
# SM_ISCLI REGRESSION - FEATURE WISE SINGLE-RUN SPYTEST BATCHES
# Each SpyTest call = One Dashboard Batch
# Logs: ./logs/SM_ISCLI_<DATE>/<FEATURE>/<TIME>/
# ==========================================================

DATE_DIR=$(date +%Y%m%d)
TIME_STAMP=$(date +%H%M%S)

BASE_LOG="./logs/SM_ISCLI_${DATE_DIR}"

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
      --ifname-type native

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
# BATCH-5 : Management IP Route
# ==========================================================

run_batch "SM_ISCLI_8_MGMT_IP_ROUTE" "./testbeds/ztp_standalone.yaml" \
system/management/test_management_ip_route.py


# ==========================================================
# BATCH-6 : Management Interface Config
# ==========================================================

run_batch "SM_ISCLI_43_SM_ISCLI_61_MGMT_INTERFACE_CONFIG" "./testbeds/ztp_standalone.yaml" \
system/management/test_management_interface_config.py


# ==========================================================
# BATCH-7 : VLAN Basic Config
# ==========================================================

run_batch "SM_ISCLI_42_SM_ISCLI_68_VLAN_BASIC_CONFIG" "./testbeds/ztp_standalone.yaml" \
system/management/test_vlan_basic_config.py


# ==========================================================
# BATCH-8 : SM_ISCLI_16 - Interface IP No-Op
# ==========================================================

run_batch "SM_ISCLI_16_IP_NOOP" "./testbeds/testbed_vs_1node.yaml" \
system/interface/test_sm_iscli_16_ip_noop.py


# ==========================================================
# BATCH-9 : VLAN Interface Lifecycle
# ==========================================================

run_batch "SM_ISCLI_60_VLAN_INTERFACE_LIFECYCLE" "./testbeds/ztp_standalone.yaml" \
switching/test_vlan_interface_lifecycle.py


# ==========================================================
# BATCH-10 : Switching Mode
# ==========================================================

run_batch "SM_ISCLI_59_SWITCHING_MODE" "./testbeds/ztp_standalone.yaml" \
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
# BATCH-13 : SM_ISCLI_10 - BGP Update-Source Format
# ==========================================================

run_batch "SM_ISCLI_10_UPDATE_SOURCE" "./testbeds/testbed_vs_2d.yaml" \
routing/bgp/test_sm_iscli_10_update_source_format.py


# ==========================================================
# BATCH-14 : SM_ISCLI_13 - BGP IBGP Multipath
# ==========================================================

run_batch "SM_ISCLI_13_IBGP_MULTIPATH" "./testbeds/testbed_vs_2d.yaml" \
routing/bgp/test_sm_iscli_13_ibgp_multipath.py


# ==========================================================
# BATCH-15 : SM_ISCLI_15 - BGP Network IP Conflict
# ==========================================================

run_batch "SM_ISCLI_15_BGP_NETWORK_CONFLICT" "./testbeds/testbed_vs_2d.yaml" \
routing/bgp/test_sm_iscli_15_bgp_network_ip_conflict.py


# ==========================================================
# BATCH-16 : BGP Remote AS Internal External
# ==========================================================

run_batch "SM_ISCLI_41_BGP_REMOTE_AS_INTERNAL_EXTERNAL" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_bgp_remote_as_internal_external.py


# ==========================================================
# BATCH-17 : BGP VRF Validation
# ==========================================================

run_batch "SM_ISCLI_82_BGP_VRF_VALIDATION" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_bgp_vrf_validation.py


# ==========================================================
# BATCH-18 : Hostname Validation
# ==========================================================

run_batch "SM_ISCLI_74_HOSTNAME_VALIDATION" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_hostname_validation.py


# ==========================================================
# BATCH-19 : IP Route SVI
# ==========================================================

run_batch "SM_ISCLI_29_IP_ROUTE_SVI" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_ip_route_svi.py


# ==========================================================
# BATCH-20 : Port Breakout
# ==========================================================

run_batch "SM_ISCLI_46_PORT_BREAKOUT" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_port_breakout.py


# ==========================================================
# BATCH-21 : Remove VLAN Interface
# ==========================================================

run_batch "SM_ISCLI_60_REMOVE_VLAN_INTERFACE" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_remove_vlan_interface.py


# ==========================================================
# BATCH-22 : Show IP Interface
# ==========================================================

run_batch "SM_ISCLI_12_SHOW_IP_INTERFACE" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_show_ip_interface.py


# ==========================================================
# BATCH-23 : Show Run Interface
# ==========================================================

run_batch "SM_ISCLI_33_SHOW_RUN_INTERFACE" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_show_run_interface.py


# ==========================================================
# BATCH-24 : Show Running Config
# ==========================================================

run_batch "SM_ISCLI_54_SHOW_RUNNING_CONFIG" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_show_running_config.py


# ==========================================================
# BATCH-25 : VRF Interface Validation
# ==========================================================

run_batch "SM_ISCLI_73_VRF_INTERFACE_VALIDATION" "./testbeds/testbed_vs_2d.yaml" \
Bug-fix/test_vrf_interface_validation.py


# ==========================================================
# BATCH-26 : SM_ISCLI_19 - Grep Filter Effectiveness
# ==========================================================

run_batch "SM_ISCLI_19_GREP_FILTER" "./testbeds/testbed_vs_1node.yaml" \
system/cli/test_sm_iscli_19_grep_filter.py


# ==========================================================
# BATCH-27 : SM_ISCLI_20 - OSPF Loopback Without IP
# ==========================================================

run_batch "SM_ISCLI_20_OSPF_LOOPBACK_NO_IP" "./testbeds/testbed_vs_2d.yaml" \
routing/ospf/test_sm_iscli_20_ospf_loopback_no_ip.py


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


