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

BASE_LOG="./logs/${DATE_DIR}"

mkdir -p "${BASE_LOG}"

# ==========================================================
# AVAILABLE FEATURE BATCHES (alphabetically for easy reference)
# ==========================================================
declare -A BATCH_NAMES=(
    # Original Full Regression Batches (A-N)
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

    # SM_ISCLI Regression Batches (O-Z, then AA-BX)
    ["O"]="SM_ISCLI_7_STATIC_ROUTES"
    ["P"]="SM_ISCLI_4_EBGP_MULTIHOP"
    ["Q"]="SM_ISCLI_5_BGP_L2VPN_EVPN"
    ["R"]="SM_ISCLI_6_BGP_TIMERS"
    ["S"]="SM_ISCLI_59_MGMT_IP_ROUTE"
    ["T"]="SM_ISCLI_43_SM_ISCLI_61_MGMT_INTERFACE_CONFIG"
    ["U"]="SM_ISCLI_42_SM_ISCLI_68_VLAN_BASIC_CONFIG"
    ["V"]="SM_ISCLI_16_IP_NOOP"
    ["W"]="SM_ISCLI_60_VLAN_INTERFACE_LIFECYCLE"
    ["X"]="SM_ISCLI_66_SWITCHING_MODE"
    ["Y"]="SM_ISCLI_8_MGMT_STATIC_IP"
    ["Z"]="SM_ISCLI_9_L2VPN_EVPN_ORDER"
    ["AA"]="SM_ISCLI_11_BGP_GRACEFUL_RESTART"
    ["AB"]="SM_ISCLI_12_MGMT_PORT_VISIBLE"
    ["AC"]="SM_ISCLI_10_UPDATE_SOURCE"
    ["AD"]="SM_ISCLI_13_IBGP_MULTIPATH"
    ["AE"]="SM_ISCLI_15_BGP_NETWORK_CONFLICT"
    ["AF"]="SM_ISCLI_41_BGP_REMOTE_AS_INTERNAL_EXTERNAL"
    ["AG"]="SM_ISCLI_82_BGP_VRF_VALIDATION"
    ["AH"]="SM_ISCLI_74_HOSTNAME_VALIDATION"
    ["AI"]="SM_ISCLI_29_IP_ROUTE_SVI"
    ["AJ"]="SM_ISCLI_46_PORT_BREAKOUT"
    ["AK"]="SM_ISCLI_60_REMOVE_VLAN_INTERFACE"
    ["AL"]="SM_ISCLI_12_SHOW_IP_INTERFACE"
    ["AM"]="SM_ISCLI_33_SHOW_RUN_INTERFACE"
    ["AN"]="SM_ISCLI_54_SHOW_RUNNING_CONFIG"
    ["AO"]="SM_ISCLI_73_VRF_INTERFACE_VALIDATION"
    ["AP"]="SM_ISCLI_19_GREP_FILTER"
    ["AQ"]="SM_ISCLI_20_OSPF_LOOPBACK_NO_IP"
    ["AR"]="SM_ISCLI_34_SM_ISCLI_32_SM_ISCLI_31_INTERFACE_IP_CONFIG"
    ["AS"]="SM_ISCLI_24_SONIC_CLI_C_FLAG"
    ["AT"]="SM_ISCLI_23_ROUTE_MAP_SHOW_RUN"
    ["AU"]="SM_ISCLI_82_BGP_VRF_UNCONFIG"
    ["AV"]="SM_ISCLI_48_SM_ISCLI_49_SM_ISCLI_51_IPV4_ACL_CLI"
    ["AW"]="SM_ISCLI_69_VLAN_NEGATIVE_MEMBER"
    ["AX"]="SM_ISCLI_76_SHOW_IP_ROUTE_FILTERING"
    ["AY"]="SM_ISCLI_21_OSPF_NETWORK_REMOVAL"
    ["AZ"]="SM_ISCLI_27_BGP_PEERGROUP_ACTIVATE"
    ["BA"]="SM_ISCLI_52_LLDP_CLI_VALIDATION"
    ["BB"]="SM_ISCLI_53_HOSTNAME_CONFIG_VERIFICATION"
    ["BC"]="SM_ISCLI_70_BGP_IPV6_CLI_VALIDATION"
    ["BD"]="SM_ISCLI_72_IPV6_INTERFACE_ENABLE_DISABLE"
    ["BE"]="SM_ISCLI_76_IP_ROUTE_SHOW_COMMANDS"
    ["BF"]="SM_ISCLI_77_VRF_CLI_NEGATIVE"
    ["BG"]="SM_ISCLI_25_INTERFACE_DESC_QUOTES"
    ["BH"]="SM_ISCLI_78_LOOPBACK_INTERFACE_CONFIG"
    ["BI"]="SM_ISCLI_26_PLATFORM_INTERFACE_CLI"
    ["BJ"]="SM_ISCLI_28_BGP_SHOW_CONFIG"
    ["BK"]="SM_ISCLI_VRF_BASIC"
    ["BL"]="SM_ISCLI_P2_78_LACP_FAST_RATE"
    ["BM"]="SM_ISCLI_VRF_INTERFACE_NEGATIVE"
    ["BN"]="SM_ISCLI_VRF_LOOPBACK_PORTCHANNEL_NEGATIVE"
    ["BO"]="SM_ISCLI_VRF_PING"
    ["BP"]="SM_ISCLI_VRF_IP_INTERFACE"
    ["BQ"]="SM_ISCLI_IP_PREFIX_LIST"
    ["BR"]="SM_ISCLI_ARP_TABLE_VERIFICATION"
    ["BS"]="SM_ISCLI_INTERFACE_CLI_VERIFICATION"
    ["BT"]="SM_ISCLI_ROUTE_MAP_DEPENDENCY"
    ["BU"]="SM_ISCLI_P2_42_VLAN_SVI_REMOVAL"
    ["BV"]="SM_ISCLI_P2_39_SWITCHPORT_TRUNK_VLAN"
    ["BW"]="SM_ISCLI_13_VRF_BINDING"
    ["BX"]="SM_ISCLI_P2_32_BGP_VRF_INSTANCE"
    ["BY"]="SM_ISCLI_44_COPY_COMMAND"
    ["BZ"]="SM_ISCLI_40_BGP_EBGP_REQUIRES_POLICY"
    ["CA"]="SM_ISCLI_45_WRITE_ERASE_COMMAND"
    ["CB"]="SM_ISCLI_VRF_ROUTE_MAP_VALIDATION"
    ["CC"]="SM_ISCLI_IPV6_INTERFACE_REDIS_VALIDATION"
    ["CD"]="SM_ISCLI_MGMT_INTERFACE_IPV6_NEIGHBOR"
    ["CE"]="SM_ISCLI_MAC_ACL_COMPREHENSIVE"
    ["CF"]="SM_ISCLI_P2_161_162_LLDP_CLI_FIX"
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
    echo "  BGP       = Run all BGP batches (A-F)"
    echo "  OSPF      = Run OSPF batches (G)"
    echo "  ROUTING   = Run routing batches (A-G, N)"
    echo "  SYSTEM    = Run system batches (L-M)"
    echo "  SM_ISCLI  = Run all SM_ISCLI batches (O-CF, 70 batches total)"
    echo "  ALL       = Run all batches"
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
                elif [[ "$feature" == "SM_ISCLI" ]]; then
                    SELECTED_BATCHES+=(O P Q R S T U V W X Y Z AA AB AC AD AE AF AG AH AI AJ AK AL AM AN AO AP AQ AR AS AT AU AV AW AX AY AZ BA BB BC BD BE BF BG BH BI BJ BK BL BM BN BO BP BQ BR BS BT BU BV BW BX BY BZ CA CB CC CD CE CF)
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

if should_run_batch "B"; then
    # First part: 2-node tests
    run_bgp_batch "BGP_IPV4_FEATURES" "./testbeds/testbed_vs_2node.yaml" \
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
    run_bgp_batch "BGP_IPV4_FEATURES_3RR" "./testbeds/testbed_vs_3rr.yaml" \
    routing/BGP/test_bgp_advanced_features.py \
    routing/BGP/test_ipv4_bgp_route_reflector.py \
    routing/BGP/test_bgp_med_weight.py
else
    echo "Skipping Batch B (BGP_IPV4_FEATURES) - not selected"
fi


# ==========================================================
# BATCH-C : BGP isCLI Best Path
# ==========================================================

if should_run_batch "C"; then
    run_batch "BGP_ISCLI_BESTPATH" "./testbeds/testbed_2vs.yaml" \
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
    run_batch "BGP_ISCLI_CAPABILITY" "./testbeds/testbed_2vs.yaml" \
    system/iscli_BGP/test_bgp76_capability_negotiation.py \
    system/iscli_BGP/test_bgp78_extended_nexthop.py
else
    echo "Skipping Batch D (BGP_ISCLI_CAPABILITY) - not selected"
fi


# ==========================================================
# BATCH-E : BGP isCLI EVPN
# ==========================================================

if should_run_batch "E"; then
    run_batch "BGP_ISCLI_EVPN" "./testbeds/testbed_2vs.yaml" \
    system/iscli_BGP/test_evpn04_type5_routes.py
else
    echo "Skipping Batch E (BGP_ISCLI_EVPN) - not selected"
fi


# ==========================================================
# BATCH-F : BGP isCLI Peer Group Advanced
# ==========================================================

if should_run_batch "F"; then
    run_batch "BGP_ISCLI_PG_ADV" "./testbeds/testbed_2vs.yaml" \
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
else
    echo "Skipping Batch G (OSPF_ISCLI_MASTER) - not selected"
fi


# ==========================================================
# BATCH-H : PortChannel isCLI
# ==========================================================

if should_run_batch "H"; then
    run_batch "PORTCHANNEL_ISCLI" "./testbeds/testbed_2node.yaml" \
    switching/iscli_PortChannel/test_interface_1_iscli_portchannel.py \
    switching/iscli_PortChannel/test_interface_2_iscli_portchannel_Reboot.py
else
    echo "Skipping Batch H (PORTCHANNEL_ISCLI) - not selected"
fi


# ==========================================================
# BATCH-I : VLAN isCLI
# ==========================================================

if should_run_batch "I"; then
    run_batch "VLAN_ISCLI" "./testbeds/testbed_2node.yaml" \
    switching/iscli_Vlan/test_interface_1_iscli_vlan.py \
    switching/iscli_Vlan/test_interface_2_iscli_vlan_ip.py \
    switching/iscli_Vlan/test_interface_1_iscli_vlan_reboot.py \
    switching/iscli_Vlan/test_interface_2_iscli_vlan_ip_reboot.py
else
    echo "Skipping Batch I (VLAN_ISCLI) - not selected"
fi


# ==========================================================
# BATCH-J : Hardware Interface Events
# ==========================================================

if should_run_batch "J"; then
    run_batch "HW_INTERFACE_EVENTS" "./testbeds/testbed_hw.yaml" \
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
    run_batch "SYS_INTERFACE_EVENTS" "./testbeds/testbed_2node.yaml" \
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
    run_batch "SYS_AAA" "./testbeds/testbed_vs_1node.yaml" \
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
    run_batch "SYS_NTP" "./testbeds/testbed_vs_1node.yaml" \
    system/ntp/test_ntp_iscli.py
else
    echo "Skipping Batch M (SYS_NTP) - not selected"
fi


# ==========================================================
# BATCH-N : Static Routing Tests (IPv4/IPv6)
# ==========================================================

if should_run_batch "N"; then
    run_batch "STATIC_ROUTING" "./testbeds/testbed_vs_1node.yaml" \
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


# ==========================================================
# SM_ISCLI REGRESSION BATCHES (O-CF) - 70 Batches Total
# ==========================================================

# ==========================================================
# BATCH-O : SM_ISCLI_7 - Static Route Tests
# ==========================================================

if should_run_batch "O"; then
    run_batch "SM_ISCLI_7_STATIC_ROUTES" "./testbeds/testbed_vs_1node.yaml" \
    routing/static/test_sm_iscli_7.py
else
    echo "Skipping Batch O (SM_ISCLI_7_STATIC_ROUTES) - not selected"
fi


# ==========================================================
# BATCH-P : SM_ISCLI_4 - eBGP Multihop
# ==========================================================

if should_run_batch "P"; then
    run_batch "SM_ISCLI_4_EBGP_MULTIHOP" "./testbeds/testbed_vs_2d.yaml" \
    system/SM_ISCLI/test_sm_iscli_4_ebgp_multihop.py
else
    echo "Skipping Batch P (SM_ISCLI_4_EBGP_MULTIHOP) - not selected"
fi


# ==========================================================
# BATCH-Q : SM_ISCLI_5 - BGP L2VPN EVPN Output
# ==========================================================

if should_run_batch "Q"; then
    run_batch "SM_ISCLI_5_BGP_L2VPN_EVPN" "./testbeds/testbed_vs_2d.yaml" \
    system/SM_ISCLI/test_sm_iscli_5_bgp_l2vpn_evpn_output.py
else
    echo "Skipping Batch Q (SM_ISCLI_5_BGP_L2VPN_EVPN) - not selected"
fi


# ==========================================================
# BATCH-R : SM_ISCLI_6 - BGP Timers
# ==========================================================

if should_run_batch "R"; then
    run_batch "SM_ISCLI_6_BGP_TIMERS" "./testbeds/testbed_vs_2d.yaml" \
    system/SM_ISCLI/test_sm_iscli_6_bgp_timers.py
else
    echo "Skipping Batch R (SM_ISCLI_6_BGP_TIMERS) - not selected"
fi


# ==========================================================
# BATCH-S : SM_ISCLI_59 - Management IP Route
# ==========================================================

if should_run_batch "S"; then
    run_batch "SM_ISCLI_59_MGMT_IP_ROUTE" "./testbeds/ztp_standalone.yaml" \
    system/management/test_management_ip_route.py
else
    echo "Skipping Batch S (SM_ISCLI_59_MGMT_IP_ROUTE) - not selected"
fi


# ==========================================================
# BATCH-T : SM_ISCLI_43, SM_ISCLI_61 - Management Interface Config
# ==========================================================

if should_run_batch "T"; then
    run_batch "SM_ISCLI_43_SM_ISCLI_61_MGMT_INTERFACE_CONFIG" "./testbeds/ztp_standalone.yaml" \
    system/management/test_management_interface_config.py
else
    echo "Skipping Batch T (SM_ISCLI_43_SM_ISCLI_61_MGMT_INTERFACE_CONFIG) - not selected"
fi


# ==========================================================
# BATCH-U : SM_ISCLI_42, SM_ISCLI_68 - VLAN Basic Config
# ==========================================================

if should_run_batch "U"; then
    run_batch "SM_ISCLI_42_SM_ISCLI_68_VLAN_BASIC_CONFIG" "./testbeds/ztp_standalone.yaml" \
    system/management/test_vlan_basic_config.py
else
    echo "Skipping Batch U (SM_ISCLI_42_SM_ISCLI_68_VLAN_BASIC_CONFIG) - not selected"
fi


# ==========================================================
# BATCH-V : SM_ISCLI_16 - Interface IP No-Op
# ==========================================================

if should_run_batch "V"; then
    run_batch "SM_ISCLI_16_IP_NOOP" "./testbeds/testbed_vs_1node.yaml" \
    system/interface/test_sm_iscli_16_ip_noop.py
else
    echo "Skipping Batch V (SM_ISCLI_16_IP_NOOP) - not selected"
fi


# ==========================================================
# BATCH-W : SM_ISCLI_60 - VLAN Interface Lifecycle
# ==========================================================

if should_run_batch "W"; then
    run_batch "SM_ISCLI_60_VLAN_INTERFACE_LIFECYCLE" "./testbeds/ztp_standalone.yaml" \
    switching/test_vlan_interface_lifecycle.py
else
    echo "Skipping Batch W (SM_ISCLI_60_VLAN_INTERFACE_LIFECYCLE) - not selected"
fi


# ==========================================================
# BATCH-X : SM_ISCLI_66 - Switching Mode
# ==========================================================

if should_run_batch "X"; then
    run_batch "SM_ISCLI_66_SWITCHING_MODE" "./testbeds/ztp_standalone.yaml" \
    switching/test_switching_mode.py
else
    echo "Skipping Batch X (SM_ISCLI_66_SWITCHING_MODE) - not selected"
fi


# ==========================================================
# BATCH-Y : SM_ISCLI_8 - Management Static IP
# ==========================================================

if should_run_batch "Y"; then
    run_batch "SM_ISCLI_8_MGMT_STATIC_IP" "./testbeds/testbed_vs_2d.yaml" \
    system/SM_ISCLI/test_sm_iscli_8_management_static_ip.py
else
    echo "Skipping Batch Y (SM_ISCLI_8_MGMT_STATIC_IP) - not selected"
fi


# ==========================================================
# BATCH-Z : SM_ISCLI_9 - L2VPN EVPN Order
# ==========================================================

if should_run_batch "Z"; then
    run_batch "SM_ISCLI_9_L2VPN_EVPN_ORDER" "./testbeds/testbed_vs_2d.yaml" \
    system/SM_ISCLI/test_sm_iscli_9_l2vpn_evpn_order.py
else
    echo "Skipping Batch Z (SM_ISCLI_9_L2VPN_EVPN_ORDER) - not selected"
fi


# ==========================================================
# BATCH-AA : SM_ISCLI_11 - BGP Graceful Restart
# ==========================================================

if should_run_batch "AA"; then
    run_batch "SM_ISCLI_11_BGP_GRACEFUL_RESTART" "./testbeds/testbed_vs_2d.yaml" \
    system/SM_ISCLI/test_sm_iscli_11_bgp_graceful_restart.py
else
    echo "Skipping Batch AA (SM_ISCLI_11_BGP_GRACEFUL_RESTART) - not selected"
fi


# ==========================================================
# BATCH-AB : SM_ISCLI_12 - Management Port Visible
# ==========================================================

if should_run_batch "AB"; then
    run_batch "SM_ISCLI_12_MGMT_PORT_VISIBLE" "./testbeds/testbed_vs_2d.yaml" \
    system/SM_ISCLI/test_sm_iscli_12_management_port_visible.py
else
    echo "Skipping Batch AB (SM_ISCLI_12_MGMT_PORT_VISIBLE) - not selected"
fi


# ==========================================================
# BATCH-AC : SM_ISCLI_10 - BGP Update-Source Format
# ==========================================================

if should_run_batch "AC"; then
    run_batch "SM_ISCLI_10_UPDATE_SOURCE" "./testbeds/testbed_vs_2d.yaml" \
    routing/bgp/test_sm_iscli_10_update_source_format.py
else
    echo "Skipping Batch AC (SM_ISCLI_10_UPDATE_SOURCE) - not selected"
fi


# ==========================================================
# BATCH-AD : SM_ISCLI_13 - BGP IBGP Multipath
# ==========================================================

if should_run_batch "AD"; then
    run_batch "SM_ISCLI_13_IBGP_MULTIPATH" "./testbeds/testbed_vs_2d.yaml" \
    routing/bgp/test_sm_iscli_13_ibgp_multipath.py
else
    echo "Skipping Batch AD (SM_ISCLI_13_IBGP_MULTIPATH) - not selected"
fi


# ==========================================================
# BATCH-AE : SM_ISCLI_15 - BGP Network IP Conflict
# ==========================================================

if should_run_batch "AE"; then
    run_batch "SM_ISCLI_15_BGP_NETWORK_CONFLICT" "./testbeds/testbed_vs_2d.yaml" \
    routing/bgp/test_sm_iscli_15_bgp_network_ip_conflict.py
else
    echo "Skipping Batch AE (SM_ISCLI_15_BGP_NETWORK_CONFLICT) - not selected"
fi


# ==========================================================
# BATCH-AF : SM_ISCLI_41 - BGP Remote AS Internal External
# ==========================================================

if should_run_batch "AF"; then
    run_batch "SM_ISCLI_41_BGP_REMOTE_AS_INTERNAL_EXTERNAL" "./testbeds/testbed_vs_2d.yaml" \
    Bug-fix/test_bgp_remote_as_internal_external.py
else
    echo "Skipping Batch AF (SM_ISCLI_41_BGP_REMOTE_AS_INTERNAL_EXTERNAL) - not selected"
fi


# ==========================================================
# BATCH-AG : SM_ISCLI_82 - BGP VRF Validation
# ==========================================================

if should_run_batch "AG"; then
    run_batch "SM_ISCLI_82_BGP_VRF_VALIDATION" "./testbeds/testbed_vs_2d.yaml" \
    Bug-fix/test_bgp_vrf_validation.py
else
    echo "Skipping Batch AG (SM_ISCLI_82_BGP_VRF_VALIDATION) - not selected"
fi


# ==========================================================
# BATCH-AH : SM_ISCLI_74 - Hostname Validation
# ==========================================================

if should_run_batch "AH"; then
    run_batch "SM_ISCLI_74_HOSTNAME_VALIDATION" "./testbeds/testbed_vs_2d.yaml" \
    Bug-fix/test_hostname_validation.py
else
    echo "Skipping Batch AH (SM_ISCLI_74_HOSTNAME_VALIDATION) - not selected"
fi


# ==========================================================
# BATCH-AI : SM_ISCLI_29 - IP Route SVI
# ==========================================================

if should_run_batch "AI"; then
    run_batch "SM_ISCLI_29_IP_ROUTE_SVI" "./testbeds/testbed_vs_2d.yaml" \
    Bug-fix/test_ip_route_svi.py
else
    echo "Skipping Batch AI (SM_ISCLI_29_IP_ROUTE_SVI) - not selected"
fi


# ==========================================================
# BATCH-AJ : SM_ISCLI_46 - Port Breakout
# ==========================================================

if should_run_batch "AJ"; then
    run_batch "SM_ISCLI_46_PORT_BREAKOUT" "./testbeds/testbed_vs_2d.yaml" \
    Bug-fix/test_port_breakout.py
else
    echo "Skipping Batch AJ (SM_ISCLI_46_PORT_BREAKOUT) - not selected"
fi


# ==========================================================
# BATCH-AK : SM_ISCLI_60 - Remove VLAN Interface
# ==========================================================

if should_run_batch "AK"; then
    run_batch "SM_ISCLI_60_REMOVE_VLAN_INTERFACE" "./testbeds/testbed_vs_2d.yaml" \
    Bug-fix/test_remove_vlan_interface.py
else
    echo "Skipping Batch AK (SM_ISCLI_60_REMOVE_VLAN_INTERFACE) - not selected"
fi


# ==========================================================
# BATCH-AL : SM_ISCLI_12 - Show IP Interface
# ==========================================================

if should_run_batch "AL"; then
    run_batch "SM_ISCLI_12_SHOW_IP_INTERFACE" "./testbeds/testbed_vs_2d.yaml" \
    Bug-fix/test_show_ip_interface.py
else
    echo "Skipping Batch AL (SM_ISCLI_12_SHOW_IP_INTERFACE) - not selected"
fi


# ==========================================================
# BATCH-AM : SM_ISCLI_33 - Show Run Interface
# ==========================================================

if should_run_batch "AM"; then
    run_batch "SM_ISCLI_33_SHOW_RUN_INTERFACE" "./testbeds/testbed_vs_2d.yaml" \
    Bug-fix/test_show_run_interface.py
else
    echo "Skipping Batch AM (SM_ISCLI_33_SHOW_RUN_INTERFACE) - not selected"
fi


# ==========================================================
# BATCH-AN : SM_ISCLI_54 - Show Running Config
# ==========================================================

if should_run_batch "AN"; then
    run_batch "SM_ISCLI_54_SHOW_RUNNING_CONFIG" "./testbeds/testbed_vs_2d.yaml" \
    Bug-fix/test_show_running_config.py
else
    echo "Skipping Batch AN (SM_ISCLI_54_SHOW_RUNNING_CONFIG) - not selected"
fi


# ==========================================================
# BATCH-AO : SM_ISCLI_73 - VRF Interface Validation
# ==========================================================

if should_run_batch "AO"; then
    run_batch "SM_ISCLI_73_VRF_INTERFACE_VALIDATION" "./testbeds/testbed_vs_2d.yaml" \
    Bug-fix/test_vrf_interface_validation.py
else
    echo "Skipping Batch AO (SM_ISCLI_73_VRF_INTERFACE_VALIDATION) - not selected"
fi


# ==========================================================
# BATCH-AP : SM_ISCLI_19 - Grep Filter Effectiveness
# ==========================================================

if should_run_batch "AP"; then
    run_batch "SM_ISCLI_19_GREP_FILTER" "./testbeds/testbed_vs_1node.yaml" \
    system/cli/test_sm_iscli_19_grep_filter.py
else
    echo "Skipping Batch AP (SM_ISCLI_19_GREP_FILTER) - not selected"
fi


# ==========================================================
# BATCH-AQ : SM_ISCLI_20 - OSPF Loopback Without IP
# ==========================================================

if should_run_batch "AQ"; then
    run_batch "SM_ISCLI_20_OSPF_LOOPBACK_NO_IP" "./testbeds/testbed_vs_2d.yaml" \
    routing/ospf/test_sm_iscli_20_ospf_loopback_no_ip.py
else
    echo "Skipping Batch AQ (SM_ISCLI_20_OSPF_LOOPBACK_NO_IP) - not selected"
fi


# ==========================================================
# BATCH-AR : SM_ISCLI_34, SM_ISCLI_32, SM_ISCLI_31 - Interface IP Config Validation
# ==========================================================

if should_run_batch "AR"; then
    run_batch "SM_ISCLI_34_SM_ISCLI_32_SM_ISCLI_31_INTERFACE_IP_CONFIG" "./testbeds/ztp_standalone.yaml" \
    system/interface/test_interface_ip_config_validation.py
else
    echo "Skipping Batch AR (SM_ISCLI_34_SM_ISCLI_32_SM_ISCLI_31_INTERFACE_IP_CONFIG) - not selected"
fi


# ==========================================================
# BATCH-AS : SM_ISCLI_24 - sonic-cli -c Flag Test
# ==========================================================

if should_run_batch "AS"; then
    run_batch "SM_ISCLI_24_SONIC_CLI_C_FLAG" "./testbeds/testbed_vs_1node.yaml" \
    system/cli/test_sm_iscli_24_sonic_cli_c_flag.py
else
    echo "Skipping Batch AS (SM_ISCLI_24_SONIC_CLI_C_FLAG) - not selected"
fi


# ==========================================================
# BATCH-AT : SM_ISCLI_23 - Route Map Show Running Config
# ==========================================================

if should_run_batch "AT"; then
    run_batch "SM_ISCLI_23_ROUTE_MAP_SHOW_RUN" "./testbeds/testbed_vs_1node.yaml" \
    routing/test_sm_iscli_23_route_map_show_run.py
else
    echo "Skipping Batch AT (SM_ISCLI_23_ROUTE_MAP_SHOW_RUN) - not selected"
fi


# ==========================================================
# BATCH-AU : SM_ISCLI_82 - BGP VRF Unconfigurations
# ==========================================================

if should_run_batch "AU"; then
    run_batch "SM_ISCLI_82_BGP_VRF_UNCONFIG" "./testbeds/testbed_2vs.yaml" \
    system/SM_ISCLI/test_sm_iscli_82_bgp_vrf_unconfigurations.py
else
    echo "Skipping Batch AU (SM_ISCLI_82_BGP_VRF_UNCONFIG) - not selected"
fi


# ==========================================================
# BATCH-AV : SM_ISCLI_48, SM_ISCLI_49, SM_ISCLI_51 - IPv4 ACL CLI Validation
# ==========================================================

if should_run_batch "AV"; then
    run_batch "SM_ISCLI_48_SM_ISCLI_49_SM_ISCLI_51_IPV4_ACL_CLI" "./testbeds/ztp_standalone.yaml" \
    qos/acl/test_ipv4_acl_cli_validation.py
else
    echo "Skipping Batch AV (SM_ISCLI_48_SM_ISCLI_49_SM_ISCLI_51_IPV4_ACL_CLI) - not selected"
fi


# ==========================================================
# BATCH-AW : SM_ISCLI_69 - VLAN Negative Member Tests
# ==========================================================

if should_run_batch "AW"; then
    run_batch "SM_ISCLI_69_VLAN_NEGATIVE_MEMBER" "./testbeds/testbed_vs_2d.yaml" \
    switching/vlan/test_vlan_negative_member.py
else
    echo "Skipping Batch AW (SM_ISCLI_69_VLAN_NEGATIVE_MEMBER) - not selected"
fi


# ==========================================================
# BATCH-AX : SM_ISCLI_76 - Show IP Route Filtering
# ==========================================================

if should_run_batch "AX"; then
    run_batch "SM_ISCLI_76_SHOW_IP_ROUTE_FILTERING" "./testbeds/testbed_vs_2d.yaml" \
    routing/ipv4/test_show_ip_route_filtering.py
else
    echo "Skipping Batch AX (SM_ISCLI_76_SHOW_IP_ROUTE_FILTERING) - not selected"
fi


# ==========================================================
# BATCH-AY : SM_ISCLI_21 - OSPF Network Removal
# ==========================================================

if should_run_batch "AY"; then
    run_batch "SM_ISCLI_21_OSPF_NETWORK_REMOVAL" "./testbeds/testbed_vs_2d.yaml" \
    routing/ospf/test_ospf_network_removal.py
else
    echo "Skipping Batch AY (SM_ISCLI_21_OSPF_NETWORK_REMOVAL) - not selected"
fi


# ==========================================================
# BATCH-AZ : SM_ISCLI_27 - BGP Peergroup Activate
# ==========================================================

if should_run_batch "AZ"; then
    run_batch "SM_ISCLI_27_BGP_PEERGROUP_ACTIVATE" "./testbeds/testbed_vs_2d.yaml" \
    routing/bgp/test_bgp_peergroup_activate.py
else
    echo "Skipping Batch AZ (SM_ISCLI_27_BGP_PEERGROUP_ACTIVATE) - not selected"
fi


# ==========================================================
# BATCH-BA : SM_ISCLI_52 - LLDP CLI Validation
# ==========================================================

if should_run_batch "BA"; then
    run_batch "SM_ISCLI_52_LLDP_CLI_VALIDATION" "./testbeds/testbed_vs_1node.yaml" \
    system/lldp/test_lldp_cli_validation.py
else
    echo "Skipping Batch BA (SM_ISCLI_52_LLDP_CLI_VALIDATION) - not selected"
fi


# ==========================================================
# BATCH-BB : SM_ISCLI_53 - Hostname Config Verification
# ==========================================================

if should_run_batch "BB"; then
    run_batch "SM_ISCLI_53_HOSTNAME_CONFIG_VERIFICATION" "./testbeds/testbed_vs_1node.yaml" \
    system/hostname/test_hostname_config_verification.py
else
    echo "Skipping Batch BB (SM_ISCLI_53_HOSTNAME_CONFIG_VERIFICATION) - not selected"
fi


# ==========================================================
# BATCH-BC : SM_ISCLI_70 - BGP IPv6 CLI Validation
# ==========================================================

if should_run_batch "BC"; then
    run_batch "SM_ISCLI_70_BGP_IPV6_CLI_VALIDATION" "./testbeds/testbed_vs_2d.yaml" \
    routing/bgp/test_bgp_ipv6_cli_validation.py
else
    echo "Skipping Batch BC (SM_ISCLI_70_BGP_IPV6_CLI_VALIDATION) - not selected"
fi


# ==========================================================
# BATCH-BD : SM_ISCLI_72 - IPv6 Interface Enable/Disable
# ==========================================================

if should_run_batch "BD"; then
    run_batch "SM_ISCLI_72_IPV6_INTERFACE_ENABLE_DISABLE" "./testbeds/testbed_vs_1node.yaml" \
    system/ipv6/test_ipv6_interface_enable_disable.py
else
    echo "Skipping Batch BD (SM_ISCLI_72_IPV6_INTERFACE_ENABLE_DISABLE) - not selected"
fi


# ==========================================================
# BATCH-BE : SM_ISCLI_76 - IP Route Show Commands
# ==========================================================

if should_run_batch "BE"; then
    run_batch "SM_ISCLI_76_IP_ROUTE_SHOW_COMMANDS" "./testbeds/ztp_standalone.yaml" \
    system/ip_route_cli/test_ip_route_show_commands.py
else
    echo "Skipping Batch BE (SM_ISCLI_76_IP_ROUTE_SHOW_COMMANDS) - not selected"
fi


# ==========================================================
# BATCH-BF : SM_ISCLI_77 - VRF CLI Negative Tests
# ==========================================================

if should_run_batch "BF"; then
    run_batch "SM_ISCLI_77_VRF_CLI_NEGATIVE" "./testbeds/ztp_standalone.yaml" \
    system/vrf/test_vrf_cli_negative.py
else
    echo "Skipping Batch BF (SM_ISCLI_77_VRF_CLI_NEGATIVE) - not selected"
fi


# ==========================================================
# BATCH-BG : SM_ISCLI_25 - Interface Description Quotes
# ==========================================================

if should_run_batch "BG"; then
    run_batch "SM_ISCLI_25_INTERFACE_DESC_QUOTES" "./testbeds/testbed_vs_1node.yaml" \
    system/cli/test_sm_iscli_25_interface_description_quotes.py
else
    echo "Skipping Batch BG (SM_ISCLI_25_INTERFACE_DESC_QUOTES) - not selected"
fi


# ==========================================================
# BATCH-BH : SM_ISCLI_78 - Loopback Interface Configuration
# ==========================================================

if should_run_batch "BH"; then
    run_batch "SM_ISCLI_78_LOOPBACK_INTERFACE_CONFIG" "./testbeds/ztp_standalone.yaml" \
    system/interface/test_loopback_interface_config.py
else
    echo "Skipping Batch BH (SM_ISCLI_78_LOOPBACK_INTERFACE_CONFIG) - not selected"
fi


# ==========================================================
# BATCH-BI : SM_ISCLI_26 - Platform and Interface CLI
# ==========================================================

if should_run_batch "BI"; then
    run_batch "SM_ISCLI_26_PLATFORM_INTERFACE_CLI" "./testbeds/testbed_vs_1node.yaml" \
    system/cli/test_sm_iscli_26_platform_interface_cli.py
else
    echo "Skipping Batch BI (SM_ISCLI_26_PLATFORM_INTERFACE_CLI) - not selected"
fi


# ==========================================================
# BATCH-BJ : SM_ISCLI_28 - BGP Show Configuration
# ==========================================================

if should_run_batch "BJ"; then
    run_batch "SM_ISCLI_28_BGP_SHOW_CONFIG" "./testbeds/testbed_vs_1node.yaml" \
    routing/bgp/test_sm_iscli_28_bgp_show_config.py
else
    echo "Skipping Batch BJ (SM_ISCLI_28_BGP_SHOW_CONFIG) - not selected"
fi


# ==========================================================
# BATCH-BK : SM_ISCLI_VRF_BASIC - VRF Basic Config
# ==========================================================

if should_run_batch "BK"; then
    run_batch "SM_ISCLI_VRF_BASIC" "./testbeds/ztp_standalone.yaml" \
    system/vrf/test_vrf_basic.py
else
    echo "Skipping Batch BK (SM_ISCLI_VRF_BASIC) - not selected"
fi


# ==========================================================
# BATCH-BL : SM_ISCLI_P2_78 - LACP Fast Rate Bug
# ==========================================================

if should_run_batch "BL"; then
    run_batch "SM_ISCLI_P2_78_LACP_FAST_RATE" "./testbeds/testbed_vs_1node.yaml" \
    switching/portchannel/test_sm_iscli_p2_78_lacp_fast_rate.py
else
    echo "Skipping Batch BL (SM_ISCLI_P2_78_LACP_FAST_RATE) - not selected"
fi


# ==========================================================
# BATCH-BM : SM_ISCLI_VRF_INTERFACE_NEGATIVE - VRF Interface Negative Tests
# ==========================================================

if should_run_batch "BM"; then
    run_batch "SM_ISCLI_VRF_INTERFACE_NEGATIVE" "./testbeds/ztp_standalone.yaml" \
    system/vrf/test_vrf_interface_negative.py
else
    echo "Skipping Batch BM (SM_ISCLI_VRF_INTERFACE_NEGATIVE) - not selected"
fi


# ==========================================================
# BATCH-BN : SM_ISCLI_VRF_LOOPBACK_PORTCHANNEL_NEGATIVE - VRF Loopback/PortChannel Negative
# ==========================================================

if should_run_batch "BN"; then
    run_batch "SM_ISCLI_VRF_LOOPBACK_PORTCHANNEL_NEGATIVE" "./testbeds/ztp_standalone.yaml" \
    system/vrf/test_vrf_loopback_portchannel_negative.py
else
    echo "Skipping Batch BN (SM_ISCLI_VRF_LOOPBACK_PORTCHANNEL_NEGATIVE) - not selected"
fi


# ==========================================================
# BATCH-BO : VRF Ping Tests
# ==========================================================

if should_run_batch "BO"; then
    run_batch "SM_ISCLI_VRF_PING" "./testbeds/ztp_standalone.yaml" \
    routing/vrf/test_vrf_ping.py
else
    echo "Skipping Batch BO (SM_ISCLI_VRF_PING) - not selected"
fi


# ==========================================================
# BATCH-BP : VRF IP Interface Tests
# ==========================================================

if should_run_batch "BP"; then
    run_batch "SM_ISCLI_VRF_IP_INTERFACE" "./testbeds/ztp_standalone.yaml" \
    routing/vrf/test_vrf_ip_interface.py
else
    echo "Skipping Batch BP (SM_ISCLI_VRF_IP_INTERFACE) - not selected"
fi


# ==========================================================
# BATCH-BQ : IP Prefix List Tests
# ==========================================================

if should_run_batch "BQ"; then
    run_batch "SM_ISCLI_IP_PREFIX_LIST" "./testbeds/ztp_standalone.yaml" \
    routing/prefix_list/test_ip_prefix_list.py
else
    echo "Skipping Batch BQ (SM_ISCLI_IP_PREFIX_LIST) - not selected"
fi


# ==========================================================
# BATCH-BR : ARP Table Verification
# ==========================================================

if should_run_batch "BR"; then
    run_batch "SM_ISCLI_ARP_TABLE_VERIFICATION" "./testbeds/ztp_standalone.yaml" \
    routing/arp/test_arp_table_verification.py
else
    echo "Skipping Batch BR (SM_ISCLI_ARP_TABLE_VERIFICATION) - not selected"
fi


# ==========================================================
# BATCH-BS : Interface CLI Verification
# ==========================================================

if should_run_batch "BS"; then
    run_batch "SM_ISCLI_INTERFACE_CLI_VERIFICATION" "./testbeds/ztp_standalone.yaml" \
    system/interface/test_interface_cli_verification.py
else
    echo "Skipping Batch BS (SM_ISCLI_INTERFACE_CLI_VERIFICATION) - not selected"
fi


# ==========================================================
# BATCH-BT : Route Map Dependency Tests
# ==========================================================

if should_run_batch "BT"; then
    run_batch "SM_ISCLI_ROUTE_MAP_DEPENDENCY" "./testbeds/ztp_standalone.yaml" \
    routing/route_map/test_route_map_dependency.py
else
    echo "Skipping Batch BT (SM_ISCLI_ROUTE_MAP_DEPENDENCY) - not selected"
fi


# ==========================================================
# BATCH-BU : VLAN SVI Removal Tests
# ==========================================================

if should_run_batch "BU"; then
    run_batch "SM_ISCLI_P2_42_VLAN_SVI_REMOVAL" "./testbeds/testbed_2vs.yaml" \
    system/iscli_BGP/test_vlan_iscli_p2_42_svi_removal.py
else
    echo "Skipping Batch BU (SM_ISCLI_P2_42_VLAN_SVI_REMOVAL) - not selected"
fi


# ==========================================================
# BATCH-BV : VLAN Switchport Trunk Tests
# ==========================================================

if should_run_batch "BV"; then
    run_batch "SM_ISCLI_P2_39_SWITCHPORT_TRUNK_VLAN" "./testbeds/testbed_2vs.yaml" \
    system/iscli_BGP/test_vlan_iscli_p2_39_switchport_trunk_vlan.py
else
    echo "Skipping Batch BV (SM_ISCLI_P2_39_SWITCHPORT_TRUNK_VLAN) - not selected"
fi


# ==========================================================
# BATCH-BW : VRF Binding Tests
# ==========================================================

if should_run_batch "BW"; then
    run_batch "SM_ISCLI_13_VRF_BINDING" "./testbeds/testbed_2vs.yaml" \
    system/iscli_BGP/test_sm_iscli_13_vrf_binding.py
else
    echo "Skipping Batch BW (SM_ISCLI_13_VRF_BINDING) - not selected"
fi


# ==========================================================
# BATCH-BX : BGP VRF Instance Tests
# ==========================================================

if should_run_batch "BX"; then
    run_batch "SM_ISCLI_P2_32_BGP_VRF_INSTANCE" "./testbeds/testbed_2vs.yaml" \
    system/iscli_BGP/test_bgp_p2_32_vrf_instance.py
else
    echo "Skipping Batch BX (SM_ISCLI_P2_32_BGP_VRF_INSTANCE) - not selected"
fi


# ==========================================================
# BATCH-BY : SM_ISCLI_44 - Copy Command Tests
# ==========================================================

if should_run_batch "BY"; then
    run_batch "SM_ISCLI_44_COPY_COMMAND" "./testbeds/testbed_vs_3rr.yaml" \
    system/management/test_sm_iscli44_copy_command.py \
    -k "not test_iscli_copy_startup_to_running"
else
    echo "Skipping Batch BY (SM_ISCLI_44_COPY_COMMAND) - not selected"
fi


# ==========================================================
# BATCH-BZ : SM_ISCLI_40 - BGP eBGP Requires Policy
# ==========================================================

if should_run_batch "BZ"; then
    run_batch "SM_ISCLI_40_BGP_EBGP_REQUIRES_POLICY" "./testbeds/testbed_vs_3rr.yaml" \
    routing/BGP/test_sm_iscli40_bgp_ebgp_requires_policy.py
else
    echo "Skipping Batch BZ (SM_ISCLI_40_BGP_EBGP_REQUIRES_POLICY) - not selected"
fi


# ==========================================================
# BATCH-CA : SM_ISCLI_45 - Write Erase Command Tests
# ==========================================================

if should_run_batch "CA"; then
    run_batch "SM_ISCLI_45_WRITE_ERASE_COMMAND" "./testbeds/testbed_vs_1node.yaml" \
    system/management/test_sm_iscli45_write_erase.py
else
    echo "Skipping Batch CA (SM_ISCLI_45_WRITE_ERASE_COMMAND) - not selected"
fi


# ==========================================================
# BATCH-CB : VRF Route Map Validation
# ==========================================================

if should_run_batch "CB"; then
    run_batch "SM_ISCLI_VRF_ROUTE_MAP_VALIDATION" "./testbeds/ztp_standalone.yaml" \
    routing/test_vrf_route_map_validation.py
else
    echo "Skipping Batch CB (SM_ISCLI_VRF_ROUTE_MAP_VALIDATION) - not selected"
fi


# ==========================================================
# BATCH-CC : IPv6 Interface Redis Validation
# ==========================================================

if should_run_batch "CC"; then
    run_batch "SM_ISCLI_IPV6_INTERFACE_REDIS_VALIDATION" "./testbeds/ztp_standalone.yaml" \
    system/interface/test_ipv6_interface_redis_validation.py
else
    echo "Skipping Batch CC (SM_ISCLI_IPV6_INTERFACE_REDIS_VALIDATION) - not selected"
fi


# ==========================================================
# BATCH-CD : Management Interface IPv6 Neighbor
# ==========================================================

if should_run_batch "CD"; then
    run_batch "SM_ISCLI_MGMT_INTERFACE_IPV6_NEIGHBOR" "./testbeds/ztp_standalone.yaml" \
    system/interface/test_management_interface_ipv6_neighbor.py
else
    echo "Skipping Batch CD (SM_ISCLI_MGMT_INTERFACE_IPV6_NEIGHBOR) - not selected"
fi


# ==========================================================
# BATCH-CE : MAC ACL Comprehensive Tests
# ==========================================================

if should_run_batch "CE"; then
    run_batch "SM_ISCLI_MAC_ACL_COMPREHENSIVE" "./testbeds/ztp_standalone.yaml" \
    qos/acl/test_mac_acl_comprehensive.py
else
    echo "Skipping Batch CE (SM_ISCLI_MAC_ACL_COMPREHENSIVE) - not selected"
fi


# ==========================================================
# BATCH-CF : SM_ISCLI_P2_161_162 - LLDP CLI Fix
# ==========================================================

if should_run_batch "CF"; then
    run_batch "SM_ISCLI_P2_161_162_LLDP_CLI_FIX" "./testbeds/testbed_vs_1node.yaml" \
    system/SM_ISCLI/test_sm_iscli_p2_161_162_lldp_cli_fix.py
else
    echo "Skipping Batch CF (SM_ISCLI_P2_161_162_LLDP_CLI_FIX) - not selected"
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
