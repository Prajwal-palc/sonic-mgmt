#!/bin/bash

# ==========================================================
# FULL REGRESSION - FEATURE WISE SINGLE-RUN SPYTEST BATCHES
# Each SpyTest call = One Dashboard Batch
# Logs: ./logs/<DATE>/<FEATURE>/<TIME>/
#
# Usage:
#   ./batch_full_run.sh                    # Run all batches
#   ./batch_full_run.sh --list             # List available batches
#   ./batch_full_run.sh --features A,B,C   # Run specific batches
#   ./batch_full_run.sh --features BGP_NEG_FLAP_RR,SYS_NTP
# ==========================================================

DATE_DIR=$(date +%Y%m%d)
TIME_STAMP=$(date +%H%M%S)

BASE_LOG="./logs/PalC-Sonic/${DATE_DIR}"

mkdir -p "${BASE_LOG}"

# ==========================================================
# AVAILABLE FEATURE BATCHES (alphabetically for easy reference)
# ==========================================================
declare -A BATCH_NAMES=(
    ["A"]="BGP_NEG_FLAP_RR"
    ["B"]="BGP_IPV4_FEATURES"
    ["C"]="BGP_ISCLI_BESTPATH"
    ["D"]="BGP_ISCLI_CAPABILITY"
    ["E"]="BGP_ISCLI_EVPN"
    ["F"]="BGP_ISCLI_PG_ADV"
    ["G"]="OSPF_ISCLI_MASTER"
    ["H"]="PORTCHANNEL_ISCLI"
    ["I"]="VLAN_ISCLI"
    ["J"]="HW_INTERFACE_EVENTS"
    ["K"]="SYS_INTERFACE_EVENTS"
    ["L"]="SYS_AAA"
    ["M"]="SYS_NTP"
    ["N"]="STATIC_ROUTING"
)

# ==========================================================
# COMMAND-LINE ARGUMENT PARSING
# ==========================================================

show_usage() {
    echo "=============================================="
    echo " Full Regression Test Suite - Selective Mode"
    echo "=============================================="
    echo ""
    echo "Usage:"
    echo "  $0                          # Run all batches"
    echo "  $0 --list                   # List available batches"
    echo "  $0 --help                   # Show this help"
    echo "  $0 --features <batches>     # Run specific batches"
    echo ""
    echo "Examples:"
    echo "  $0 --features A,B,C         # Run batches A, B, C"
    echo "  $0 --features BGP_NEG_FLAP_RR,SYS_NTP"
    echo "  $0 --features BGP           # Run all BGP batches (A-F)"
    echo ""
    echo "Available Batches:"
    echo "  A = BGP_NEG_FLAP_RR         (BGP Negative/Flap/RR/Restart)"
    echo "  B = BGP_IPV4_FEATURES       (BGP IPv4 iBGP/eBGP Features)"
    echo "  C = BGP_ISCLI_BESTPATH      (BGP isCLI Best Path)"
    echo "  D = BGP_ISCLI_CAPABILITY    (BGP isCLI Capability)"
    echo "  E = BGP_ISCLI_EVPN          (BGP isCLI EVPN)"
    echo "  F = BGP_ISCLI_PG_ADV        (BGP isCLI Peer Group Advanced)"
    echo "  G = OSPF_ISCLI_MASTER       (OSPF isCLI Master)"
    echo "  H = PORTCHANNEL_ISCLI       (PortChannel isCLI)"
    echo "  I = VLAN_ISCLI              (VLAN isCLI)"
    echo "  J = HW_INTERFACE_EVENTS     (Hardware Interface Events)"
    echo "  K = SYS_INTERFACE_EVENTS    (System Interface Events)"
    echo "  L = SYS_AAA                 (System AAA)"
    echo "  M = SYS_NTP                 (System NTP)"
    echo "  N = STATIC_ROUTING          (Static Route Tests - IPv4/IPv6)"
    echo ""
    echo "Special Keywords:"
    echo "  BGP      = Run all BGP batches (A-F)"
    echo "  OSPF     = Run OSPF batches (G)"
    echo "  ROUTING  = Run routing batches (A-G, N)"
    echo "  SYSTEM   = Run system batches (L-M)"
    echo "  ALL      = Run all batches"
    echo ""
}

list_batches() {
    echo "=============================================="
    echo " Available Feature Batches"
    echo "=============================================="
    for key in $(echo "${!BATCH_NAMES[@]}" | tr ' ' '\n' | sort); do
        printf "  [%s] %-25s\n" "$key" "${BATCH_NAMES[$key]}"
    done
    echo ""
}

# Parse command-line arguments
SELECTED_BATCHES=()
RUN_ALL=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --list|-l)
            list_batches
            exit 0
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        --features|-f)
            if [[ -z "$2" ]]; then
                echo "ERROR: --features requires argument"
                show_usage
                exit 1
            fi
            RUN_ALL=false
            IFS=',' read -ra FEATURES <<< "$2"
            for feature in "${FEATURES[@]}"; do
                feature=$(echo "$feature" | xargs)  # Trim whitespace

                # Handle special keywords
                if [[ "$feature" == "BGP" ]]; then
                    SELECTED_BATCHES+=(A B C D E F)
                elif [[ "$feature" == "OSPF" ]]; then
                    SELECTED_BATCHES+=(G)
                elif [[ "$feature" == "ROUTING" ]]; then
                    SELECTED_BATCHES+=(A B C D E F G N)
                elif [[ "$feature" == "SYSTEM" ]]; then
                    SELECTED_BATCHES+=(L M)
                elif [[ "$feature" == "ALL" ]]; then
                    RUN_ALL=true
                    break
                # Handle letter codes (A, B, C, etc.)
                elif [[ ${BATCH_NAMES[$feature]+_} ]]; then
                    SELECTED_BATCHES+=("$feature")
                # Handle full names (BGP_NEG_FLAP_RR, etc.)
                else
                    # Find the key for this batch name
                    found=false
                    for key in "${!BATCH_NAMES[@]}"; do
                        if [[ "${BATCH_NAMES[$key]}" == "$feature" ]]; then
                            SELECTED_BATCHES+=("$key")
                            found=true
                            break
                        fi
                    done
                    if [[ "$found" == "false" ]]; then
                        echo "WARNING: Unknown batch '$feature', skipping"
                    fi
                fi
            done
            shift 2
            ;;
        *)
            echo "ERROR: Unknown option $1"
            show_usage
            exit 1
            ;;
    esac
done

# Display selected batches
if [[ "$RUN_ALL" == "true" ]]; then
    echo "=============================================="
    echo " FULL REGRESSION STARTED (ALL BATCHES)"
    echo " DATE : ${DATE_DIR}"
    echo "=============================================="
else
    echo "=============================================="
    echo " SELECTIVE REGRESSION STARTED"
    echo " DATE : ${DATE_DIR}"
    echo " SELECTED BATCHES:"
    for batch in "${SELECTED_BATCHES[@]}"; do
        echo "   [$batch] ${BATCH_NAMES[$batch]}"
    done
    echo "=============================================="
fi

# ==========================================================
# Helper function to check if batch should run
# ==========================================================
should_run_batch() {
    local batch_letter=$1

    if [[ "$RUN_ALL" == "true" ]]; then
        return 0  # Run
    fi

    # Check if batch letter is in selected list
    for selected in "${SELECTED_BATCHES[@]}"; do
        if [[ "$selected" == "$batch_letter" ]]; then
            return 0  # Run
        fi
    done

    return 1  # Skip
}

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

if should_run_batch "A"; then
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
else
    echo "Skipping Batch A (BGP_NEG_FLAP_RR) - not selected"
fi


# ==========================================================
# BATCH-B : BGP IPv4 iBGP/eBGP Feature Tests
# ==========================================================

if should_run_batch "B"; then
    # First part: 2-node tests
    run_batch "BGP_IPV4_FEATURES" "./testbeds/dlink_2node.yaml" \
    routing/BGP/test_bgp_ipv4_basic.py \
    routing/BGP/test_bgp_svi_ipv4.py \
    routing/BGP/test_bgp_portchannel_ipv4.py \
    routing/BGP/test_bgp_loopback_ipv4.py \
    routing/BGP/test_bgp_ipv4_basic_ebgp.py \
    routing/BGP/test_bgp_svi_ipv4_ebgp.py \
    routing/BGP/test_bgp_portchannel_ipv4_ebgp.py \
    routing/BGP/test_bgp_loopback_ipv4_ebgp.py \
    routing/BGP/test_bgp_ebgp_connected_static_redistribution.py

    # Second part: 3-node RR tests (requires 3RR testbed)
    #run_batch "BGP_IPV4_FEATURES_3RR" "./testbeds/testbed_vs_3rr.yaml" \
    #routing/BGP/test_bgp_advanced_features.py \
    #routing/BGP/test_ipv4_bgp_route_reflector.py \
    #routing/BGP/test_bgp_med_weight.py
else
    echo "Skipping Batch B (BGP_IPV4_FEATURES) - not selected"
fi


# ==========================================================
# BATCH-C : BGP isCLI Best Path
# ==========================================================

if should_run_batch "C"; then
    run_batch "BGP_ISCLI_BESTPATH" "./testbeds/dlink_2node.yaml" \
    system/iscli_BGP/test_bgp50_localpref_selection.py \
    system/iscli_BGP/test_bgp51_aspath_selection.py \
    system/iscli_BGP/test_bgp52_med_selection.py \
    system/iscli_BGP/test_bgp55_ibgp_ebgp_selection.py \
    system/iscli_BGP/test_bgp56_origin_code_selection.py \
    system/iscli_BGP/test_bgp57_router_id_tiebreak.py \
    system/iscli_BGP/test_bgp58_nexthop_reachability.py
else
    echo "Skipping Batch C (BGP_ISCLI_BESTPATH) - not selected"
fi


# ==========================================================
# BATCH-D : BGP isCLI Capability
# ==========================================================

if should_run_batch "D"; then
    run_batch "BGP_ISCLI_CAPABILITY" "./testbeds/dlink_2node.yaml" \
    system/iscli_BGP/test_bgp76_capability_negotiation.py \
    system/iscli_BGP/test_bgp78_extended_nexthop.py
else
    echo "Skipping Batch D (BGP_ISCLI_CAPABILITY) - not selected"
fi


# ==========================================================
# BATCH-E : BGP isCLI EVPN
# ==========================================================

if should_run_batch "E"; then
    run_batch "BGP_ISCLI_EVPN" "./testbeds/dlink_2node.yaml" \
    system/iscli_BGP/test_evpn04_type5_routes.py
else
    echo "Skipping Batch E (BGP_ISCLI_EVPN) - not selected"
fi


# ==========================================================
# BATCH-F : BGP isCLI Peer Group Advanced
# ==========================================================

if should_run_batch "F"; then
    run_batch "BGP_ISCLI_PG_ADV" "./testbeds/dlink_2node.yaml" \
    system/iscli_BGP/test_bgp_pg16_pkt_queue.py \
    system/iscli_BGP/test_bgp_pg17_allowas_in.py \
    system/iscli_BGP/test_bgp_pg18_conflict_detection.py \
    system/iscli_BGP/test_bgp_pg19_passive_mode.py \
    system/iscli_BGP/test_bgp_pg20_routemap_override.py
else
    echo "Skipping Batch F (BGP_ISCLI_PG_ADV) - not selected"
fi


# ==========================================================
# BATCH-G : OSPF isCLI MASTER
# ==========================================================

if should_run_batch "G"; then
    run_batch "OSPF_ISCLI_MASTER" "./testbeds/testbed_4node.yaml" \
    #routing/isCLI/testcases_OSPF_1_iscli_Basic_2_node_Reboot.py \
    routing/isCLI/testcases_OSPF_2_iscli_Basic_4_node.py \
    #routing/isCLI/testcases_OSPF_2_iscli_Basic_4_node_Reboot.py \
    routing/isCLI/testcases_OSPF_3_iscli_Basic_4_node_Vlan.py \
    #routing/isCLI/testcases_OSPF_3_iscli_Basic_4_node_Vlan_Reboot.py \
    routing/isCLI/testcases_OSPF_4_iscli_Basic_4_node_PortChannel.py \
    #routing/isCLI/testcases_OSPF_4_iscli_Basic_4_node_PortChannel_Reboot.py \
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
else
    echo "Skipping Batch G (OSPF_ISCLI_MASTER) - not selected"
fi


# ==========================================================
# BATCH-H : PortChannel isCLI
# ==========================================================

if should_run_batch "H"; then
    run_batch "PORTCHANNEL_ISCLI" "./testbeds/dlink_2node.yaml" \
    switching/iscli_PortChannel/test_interface_1_iscli_portchannel.py
    #switching/iscli_PortChannel/test_interface_2_iscli_portchannel_Reboot.py
else
    echo "Skipping Batch H (PORTCHANNEL_ISCLI) - not selected"
fi


# ==========================================================
# BATCH-I : VLAN isCLI
# ==========================================================

if should_run_batch "I"; then
    run_batch "VLAN_ISCLI" "./testbeds/dlink_2node.yaml" \
    switching/iscli_Vlan/test_interface_1_iscli_vlan.py \
    switching/iscli_Vlan/test_interface_2_iscli_vlan_ip.py
    #switching/iscli_Vlan/test_interface_1_iscli_vlan_reboot.py \
    #switching/iscli_Vlan/test_interface_2_iscli_vlan_ip_reboot.py
else
    echo "Skipping Batch I (VLAN_ISCLI) - not selected"
fi


# ==========================================================
# BATCH-J : Hardware Interface Events
# ==========================================================

if should_run_batch "J"; then
    run_batch "HW_INTERFACE_EVENTS" "./testbeds/dlink_1node.yaml" \
    system/iscli_Hardware/test_interface_1_iscli_events_admin_up_down_HW.py \
    system/iscli_Hardware/test_interface_3_iscli_events_description_HW.py \
    system/iscli_Hardware/test_interface_2_iscli_vlan_ip_HW.py \
    system/iscli_Hardware/test_interface_2_iscli_events_mtu_change_HW.py \
    system/iscli_Hardware/test_interface_1_iscli_vlan_HW.py \
    system/iscli_Hardware/test_interface_1_iscli_portchannel_HW.py \
    system/iscli_Hardware/test_interface_5_iscli_events_ipv6_address_HW.py \
    system/iscli_Hardware/test_interface_4_iscli_events_ip_address_HW.py
else
    echo "Skipping Batch J (HW_INTERFACE_EVENTS) - not selected"
fi


# ==========================================================
# BATCH-K : System Interface Events
# ==========================================================

if should_run_batch "K"; then
    run_batch "SYS_INTERFACE_EVENTS" "./testbeds/dlink_2node.yaml" \
    system/iscli_interface_events/test_interface_1_iscli_events_admin_up_down.py \
    system/iscli_interface_events/test_interface_2_iscli_events_mtu_change.py \
    system/iscli_interface_events/test_interface_3_iscli_events_description.py \
    system/iscli_interface_events/test_interface_4_iscli_events_ip_address.py \
    system/iscli_interface_events/test_interface_5_iscli_events_ipv6_address.py
else
    echo "Skipping Batch K (SYS_INTERFACE_EVENTS) - not selected"
fi

# ==========================================================
# BATCH-L : System AAA
# ==========================================================

if should_run_batch "L"; then
    run_batch "SYS_AAA" "./testbeds/dlink_1node.yaml" \
    system/AAA/test_aaa_auth.py
else
    echo "Skipping Batch L (SYS_AAA) - not selected"
fi


# ==========================================================
# BATCH-M : System NTP
# ==========================================================

if should_run_batch "M"; then
    # NTP Server Setup
    echo "Setting up NTP server for batch M..."
    sudo ./tests/system/ntp/setup_ntp_server.sh

    # Verify Setup
    ./tests/system/ntp/verify_ntp_server.sh
    ./tests/system/ntp/fix_ntp_server.sh

    export NTP_ISCLI_VAR_FILE=./tests/system/ntp/vars_ntp_iscli_local.yaml
    run_batch "SYS_NTP" "./testbeds/dlink_1node.yaml" \
    system/ntp/test_ntp_iscli.py
else
    echo "Skipping Batch M (SYS_NTP) - not selected"
fi


# ==========================================================
# BATCH-N : Static Routing Tests (IPv4/IPv6)
# ==========================================================

if should_run_batch "N"; then
    run_batch "STATIC_ROUTING" "./testbeds/dlink_1node.yaml" \
    routing/static/test_sm_iscli_7.py \
    routing/static/test_static_route_basic.py \
    routing/static/test_static_route_basic_klish.py \
    routing/static/test_static_route_blackhole.py \
    routing/static/test_static_route_mgmt_vrf_klish.py \
    routing/static/test_static_route_vrf_klish.py \
    routing/static/test_static_ipv6_route_basic_1.py \
    routing/static/test_static_ipv6_negative.py \
    routing/static/test_static_ipv6_blackhole.py \
    routing/static/test_static_ipv6_ecmp.py \
    routing/static/test_static_ipv6_scale.py \
    routing/static/test_static_ipv6_vrf.py \
    routing/static/test_static_ipv6_mgmt_vrf.py
else
    echo "Skipping Batch N (STATIC_ROUTING) - not selected"
fi


echo "=============================================="
if [[ "$RUN_ALL" == "true" ]]; then
    echo " FULL REGRESSION COMPLETED"
else
    echo " SELECTIVE REGRESSION COMPLETED"
fi
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
