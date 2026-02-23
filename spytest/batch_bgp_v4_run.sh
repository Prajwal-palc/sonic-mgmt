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
      --ifname-type native \
      --get-tech-support none

    RC=$?
    echo " Batch ${FEATURE} completed with RC=${RC}"

    if [ ${RC} -ne 0 ]; then
        echo " WARNING: Batch ${FEATURE} failed. Continuing to next batch."
    fi
}



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
          --ifname-type native \
          --get-tech-support none

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

run_bgp_batch "BGP_IPV4_FEATURES" "./testbeds/testbed_vs2_4node.yaml" \
    routing/BGP/test_bgp_ipv4_basic.py \
    routing/BGP/test_bgp_svi_ipv4.py \
    routing/BGP/test_bgp_portchannel_ipv4.py \
    routing/BGP/test_bgp_loopback_ipv4.py \
    routing/BGP/test_bgp_med_weight.py \
    routing/BGP/test_bgp_ipv4_basic_ebgp.py \
    routing/BGP/test_bgp_svi_ipv4_ebgp.py \
    routing/BGP/test_bgp_portchannel_ipv4_ebgp.py \
    routing/BGP/test_bgp_loopback_ipv4_ebgp.py \
    routing/BGP/test_bgp_ebgp_connected_static_redistribution.py \
    routing/BGP/test_bgp_advanced_features.py \
    routing/BGP/test_ipv4_bgp_route_reflector.py



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

DASHBOARD_FILE="${DASHBOARD_DIR}/bgp_v4_regression_dashboard_${DATE_DIR}_${TIME_STAMP}.html"

python3 dashboard/scripts/generate_graphical_dashboard.py \
    --log-root ${BASE_LOG} \
    --out ${DASHBOARD_FILE} \
    --name "BGP V4 Regression - ${DATE_DIR}"

echo "=============================================="
echo " Dashboard Generation Complete"
echo "=============================================="
echo "Dashboard available at:"
echo "file://$(pwd)/${DASHBOARD_FILE}"

# Copy dashboard to user directory
USER_DASHBOARD_DIR="${HOME}/Dashboard/BGP_V4_REGRESSION"
mkdir -p "${USER_DASHBOARD_DIR}"
cp "${DASHBOARD_FILE}" "${USER_DASHBOARD_DIR}/"

echo "Dashboard copy saved to:"
echo "file://${USER_DASHBOARD_DIR}/BGP_v4_regression_dashboard_${DATE_DIR}_${TIME_STAMP}.html"
