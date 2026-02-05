#!/bin/bash

# ==========================================================
# FULL REGRESSION - FEATURE WISE SINGLE-RUN SPYTEST BATCHES
# Each SpyTest call = One Dashboard Batch
# Logs: ./logs/<DATE>/<FEATURE>/<TIME>/
# ==========================================================

DATE_DIR=$(date +%Y%m%d)
TIME_STAMP=$(date +%H%M%S)

BASE_LOG="./logs/${DATE_DIR}"

mkdir -p "${BASE_LOG}"

echo "=============================================="
echo " FULL REGRESSION STARTED"
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
# BATCH-A : BGP Negative / Flap / RR / Restart (3RR)
# ==========================================================

run_batch "BGP_NEG_FLAP_RR" "./testbeds/testbed_vs_3rr.yaml" \
routing/bgp/test_ipv4_bgp_link_flap.py \
routing/bgp/test_ipv4_bgp_daemon_restart.py \
routing/bgp/test_ipv6_bgp_daemon_restart.py \
routing/bgp/test_ipv4_bgp_route_reflector.py \
routing/bgp/test_ipv4_bgp_negative_password.py \
routing/bgp/test_ipv4_bgp_negative_nexthop.py \
routing/bgp/test_ipv4_bgp_negative_asn.py \
routing/bgp/test_ipv4_bgp_loopback_negative_updatesource.py \
routing/bgp/test_ipv6_bgp_route_reflector.py \
routing/bgp/test_ipv6_bgp_negative_password.py \
routing/bgp/test_ipv6_bgp_negative_asn.py \
routing/bgp/test_ipv6_bgp_loopback.py \
routing/bgp/test_ipv6_bgp_loopback_negative_updatesource.py \
routing/bgp/test_ipv6_bgp_link_flap.py \
routing/bgp/test_ipv6_bgp_interface_routes.py \
routing/bgp/test_ipv6_bgp_interface.py \
routing/bgp/test_ipv6_bgp_interface_ebgp.py \
routing/bgp/test_portchannel_ipv6_bgp.py


# ==========================================================
# BATCH-B : BGP IPv4 iBGP/eBGP Feature Tests
# Note: BGP docker restart is executed between tests to ensure clean state
# ==========================================================

run_bgp_batch () {
    FEATURE=$1
    TESTBED=$2
    shift 2
    TESTS=("$@")

    LOG_PATH="${BASE_LOG}/${FEATURE}/${TIME_STAMP}"
    mkdir -p "${LOG_PATH}"

    echo "----------------------------------------------"
    echo " Running BGP Batch: ${FEATURE}"
    echo " Testbed     : ${TESTBED}"
    echo " Tests       : ${#TESTS[@]} test files"
    echo " Logs        : ${LOG_PATH}"
    echo "----------------------------------------------"

    OVERALL_RC=0

    for TEST in "${TESTS[@]}"; do
        echo ""
        echo "==> Restarting BGP docker before test: ${TEST}"
        python3 ./restart_bgp_docker.py
        RESTART_RC=$?

        if [ ${RESTART_RC} -ne 0 ]; then
            echo " WARNING: BGP docker restart failed. Continuing with test anyway."
        else
            echo " ✓ BGP docker restart completed successfully"
        fi

        echo ""
        echo "==> Running test: ${TEST}"
        ./bin/spytest --tryssh 1 \
          --testbed "${TESTBED}" \
          "${TEST}" \
          --logs-path "${LOG_PATH}" \
          --log-level debug \
          --skip-init-config \
          --ifname-type native

        RC=$?
        echo " Test ${TEST} completed with RC=${RC}"

        if [ ${RC} -ne 0 ]; then
            echo " WARNING: Test ${TEST} failed."
            OVERALL_RC=${RC}
        fi
    done

    echo "----------------------------------------------"
    echo " Batch ${FEATURE} completed with RC=${OVERALL_RC}"
    echo "----------------------------------------------"

    if [ ${OVERALL_RC} -ne 0 ]; then
        echo " WARNING: Some tests in batch ${FEATURE} failed. Continuing to next batch."
    fi
}

run_bgp_batch "BGP_IPV4_FEATURES" "./testbeds/testbed_vs_2node.yaml" \
routing/BGP/test_bgp_ipv4_basic.py \
routing/BGP/test_bgp_svi_ipv4.py \
routing/BGP/test_bgp_portchannel_ipv4.py \
routing/BGP/test_bgp_loopback_ipv4.py \
routing/BGP/test_bgp_ipv4_basic_ebgp.py \
routing/BGP/test_bgp_svi_ipv4_ebgp.py \
routing/BGP/test_bgp_portchannel_ipv4_ebgp.py \
routing/BGP/test_bgp_loopback_ipv4_ebgp.py \
routing/BGP/test_bgp_ebgp_connected_static_redistribution.py \
routing/BGP/test_bgp_advanced_features.py \
routing/BGP/test_ipv4_bgp_route_reflector.py \
routing/BGP/test_bgp_med_weight.py


# ==========================================================
# BATCH-C : BGP isCLI Best Path
# ==========================================================

run_batch "BGP_ISCLI_BESTPATH" "./testbeds/testbed_2vs.yaml" \
system/iscli_BGP/test_bgp50_localpref_selection.py \
system/iscli_BGP/test_bgp51_aspath_selection.py \
system/iscli_BGP/test_bgp52_med_selection.py \
system/iscli_BGP/test_bgp55_ibgp_ebgp_selection.py \
system/iscli_BGP/test_bgp56_origin_code_selection.py \
system/iscli_BGP/test_bgp57_router_id_tiebreak.py \
system/iscli_BGP/test_bgp58_nexthop_reachability.py


# ==========================================================
# BATCH-D : BGP isCLI Capability
# ==========================================================

run_batch "BGP_ISCLI_CAPABILITY" "./testbeds/testbed_2vs.yaml" \
system/iscli_BGP/test_bgp76_capability_negotiation.py \
system/iscli_BGP/test_bgp78_extended_nexthop.py


# ==========================================================
# BATCH-E : BGP isCLI EVPN
# ==========================================================

run_batch "BGP_ISCLI_EVPN" "./testbeds/testbed_2vs.yaml" \
system/iscli_BGP/test_evpn04_type5_routes.py


# ==========================================================
# BATCH-F : BGP isCLI Peer Group Advanced
# ==========================================================

run_batch "BGP_ISCLI_PG_ADV" "./testbeds/testbed_2vs.yaml" \
system/iscli_BGP/test_bgp_pg16_pkt_queue.py \
system/iscli_BGP/test_bgp_pg17_allowas_in.py \
system/iscli_BGP/test_bgp_pg18_conflict_detection.py \
system/iscli_BGP/test_bgp_pg19_passive_mode.py \
system/iscli_BGP/test_bgp_pg20_routemap_override.py


# ==========================================================
# BATCH-G : OSPF isCLI MASTER
# ==========================================================

run_batch "OSPF_ISCLI_MASTER" "./testbeds/testbed_4node.yaml" \
routing/isCLI/testcases_OSPF_1_iscli_Basic_2_node_Reboot.py \
routing/isCLI/testcases_OSPF_2_iscli_Basic_4_node.py \
routing/isCLI/testcases_OSPF_2_iscli_Basic_4_node_Reboot.py \
routing/isCLI/testcases_OSPF_3_iscli_Basic_4_node_Vlan.py \
routing/isCLI/testcases_OSPF_3_iscli_Basic_4_node_Vlan_Reboot.py \
routing/isCLI/testcases_OSPF_4_iscli_Basic_4_node_PortChannel.py \
routing/isCLI/testcases_OSPF_4_iscli_Basic_4_node_PortChannel_Reboot.py \
routing/isCLI/testcases_OSPF_5_iscli_4_node_Backbone_connect_via_ABR_Eth.py \
routing/isCLI/testcases_OSPF_5_iscli_4_node_Backbone_connect_via_ABR_PC.py \
routing/isCLI/testcases_OSPF_5_iscli_4_node_Backbone_connect_via_ABR_Vlan.py \
routing/isCLI/testcases_OSPF_6_iscli_4_node_Area_ID_mismatch_prevents_adj_Eth.py \
routing/isCLI/testcases_OSPF_6_iscli_4_node_Area_ID_mismatch_prevents_adj_PC.py \
routing/isCLI/testcases_OSPF_6_iscli_4_node_Area_ID_mismatch_prevents_adj_Vlan.py \
routing/isCLI/testcases_OSPF_7_iscli_4_node_DR_BDR_elect_Eth.py \
routing/isCLI/testcases_OSPF_7_iscli_4_node_DR_BDR_elect_PC.py \
routing/isCLI/testcases_OSPF_7_iscli_4_node_DR_BDR_elect_VLAN.py \
routing/isCLI/testcases_OSPF_8_iscli_4_node_cost_attribute_affects_path_select_over_Eth.py \
routing/isCLI/testcases_OSPF_8_iscli_4_node_cost_attribute_affects_path_select_over_PC.py \
routing/isCLI/testcases_OSPF_8_iscli_4_node_cost_attribute_affects_path_select_over_Vlan.py \
routing/isCLI/testcases_OSPF_9_iscli_4_node_MD5_authentication_over_Eth.py \
routing/isCLI/testcases_OSPF_9_iscli_4_node_MD5_authentication_over_PC.py \
routing/isCLI/testcases_OSPF_9_iscli_4_node_MD5_authentication_over_Vlan.py \
routing/isCLI/testcases_OSPF_10_iscli_4_node_Type_1_LSAs_over_Eth.py \
routing/isCLI/testcases_OSPF_10_iscli_4_node_Type_1_LSAs_over_PC.py \
routing/isCLI/testcases_OSPF_10_iscli_4_node_Type_1_LSAs_over_Vlan.py \
routing/isCLI/testcases_OSPF_11_iscli_4_node_Type_5_external_LSAs_over_Eth.py \
routing/isCLI/testcases_OSPF_11_iscli_4_node_Type_5_external_LSAs_over_PC.py \
routing/isCLI/testcases_OSPF_11_iscli_4_node_Type_5_external_LSAs_over_Vlan.py \
routing/isCLI/testcases_OSPF_12_iscli_4_MTU_mismatch_prevents_adj_Eth.py \
routing/isCLI/testcases_OSPF_12_iscli_4_MTU_mismatch_prevents_adj_PC.py \
routing/isCLI/testcases_OSPF_12_iscli_4_MTU_mismatch_prevents_adj_VLAN.py \
routing/isCLI/testcases_OSPF_13_iscli_4_node_unnumbered_adj_loopback_over_Eth.py \
routing/isCLI/testcases_OSPF_13_iscli_4_node_unnumbered_adj_loopback_over_PC.py \
routing/isCLI/testcases_OSPF_13_iscli_4_node_unnumbered_adj_loopback_over_Vlan.py \
routing/isCLI/testcases_OSPF_14_iscli_4_node_OSPF_scalability_over_Eth.py \
routing/isCLI/testcases_OSPF_14_iscli_4_node_OSPF_scalability_over_PC.py \
routing/isCLI/testcases_OSPF_14_iscli_4_node_OSPF_scalability_over_Vlan.py \
routing/isCLI/testcases_OSPF_15_iscli_4_node_OSPF_per_VRF_over_Eth.py \
routing/isCLI/testcases_OSPF_15_iscli_4_node_OSPF_per_VRF_over_PC.py \
routing/isCLI/testcases_OSPF_15_iscli_4_node_OSPF_per_VRF_over_Vlan.py \
routing/isCLI/test_ospf_1_iscli_basic.py


# ==========================================================
# BATCH-H : PortChannel isCLI
# ==========================================================

run_batch "PORTCHANNEL_ISCLI" "./testbeds/testbed_2node.yaml" \
switching/iscli_PortChannel/test_interface_1_iscli_portchannel.py \
switching/iscli_PortChannel/test_interface_2_iscli_portchannel_Reboot.py


# ==========================================================
# BATCH-I : VLAN isCLI
# ==========================================================

run_batch "VLAN_ISCLI" "./testbeds/testbed_2node.yaml" \
switching/iscli_Vlan/test_interface_1_iscli_vlan.py \
switching/iscli_Vlan/test_interface_2_iscli_vlan_ip.py \
switching/iscli_Vlan/test_interface_1_iscli_vlan_reboot.py \
switching/iscli_Vlan/test_interface_2_iscli_vlan_ip_reboot.py


# ==========================================================
# BATCH-J : Hardware Interface Events
# ==========================================================

run_batch "HW_INTERFACE_EVENTS" "./testbeds/testbed_hw.yaml" \
system/iscli_Hardware/test_interface_1_iscli_events_admin_up_down_HW.py \
system/iscli_Hardware/test_interface_3_iscli_events_description_HW.py \
system/iscli_Hardware/test_interface_2_iscli_vlan_ip_HW.py \
system/iscli_Hardware/test_interface_2_iscli_events_mtu_change_HW.py \
system/iscli_Hardware/test_interface_1_iscli_vlan_HW.py \
system/iscli_Hardware/test_interface_1_iscli_portchannel_HW.py \
system/iscli_Hardware/test_interface_5_iscli_events_ipv6_address_HW.py \
system/iscli_Hardware/test_interface_4_iscli_events_ip_address_HW.py


# ==========================================================
# BATCH-K : System Interface Events
# ==========================================================

run_batch "SYS_INTERFACE_EVENTS" "./testbeds/testbed_2node.yaml" \
system/iscli_interface_events/test_interface_1_iscli_events_admin_up_down.py \
system/iscli_interface_events/test_interface_2_iscli_events_mtu_change.py \
system/iscli_interface_events/test_interface_3_iscli_events_description.py \
system/iscli_interface_events/test_interface_4_iscli_events_ip_address.py \
system/iscli_interface_events/test_interface_5_iscli_events_ipv6_address.py

# ==========================================================
# BATCH-L : System AAA
# ==========================================================

run_batch "SYS_AAA" "./testbeds/testbed_vs_1node.yaml" \
system/AAA/test_aaa_auth.py


# ==========================================================
# BATCH-M : System NTP
# ==========================================================

sudo ./tests/system/ntp/setup_ntp_server.sh

#Verify Setup
./tests/system/ntp/verify_ntp_server.sh
./tests/system/ntp/fix_ntp_server.sh

export NTP_ISCLI_VAR_FILE=./tests/system/ntp/vars_ntp_iscli_local.yaml
run_batch "SYS_NTP" "./testbeds/testbed_vs_1node.yaml" \
system/ntp/test_ntp_iscli.py


echo "=============================================="
echo " FULL REGRESSION COMPLETED"
echo " Logs Root : ${BASE_LOG}"
echo "=============================================="

# Generate Graphical Dashboard
echo "=============================================="
echo " Generating Graphical Dashboard"
echo "=============================================="

# Create dashboard directory in logs
DASHBOARD_DIR="${BASE_LOG}/dashboard"
mkdir -p "${DASHBOARD_DIR}"

DASHBOARD_FILE="${DASHBOARD_DIR}/full_regression_dashboard_${DATE_DIR}_${TIME_STAMP}.html"

python3 dashboard/scripts/generate_graphical_dashboard.py \
    --log-root ${BASE_LOG} \
    --out ${DASHBOARD_FILE} \
    --name "Full Regression - ${DATE_DIR}"

echo "=============================================="
echo " Dashboard Generation Complete"
echo "=============================================="
echo "Dashboard available at:"
echo "file://$(pwd)/${DASHBOARD_FILE}"

# Copy dashboard to user directory
USER_DASHBOARD_DIR="${HOME}/Dashboard/FULL_REGRESSION"
mkdir -p "${USER_DASHBOARD_DIR}"
cp "${DASHBOARD_FILE}" "${USER_DASHBOARD_DIR}/"

echo "Dashboard copy saved to:"
echo "file://${USER_DASHBOARD_DIR}/full_regression_dashboard_${DATE_DIR}_${TIME_STAMP}.html"
