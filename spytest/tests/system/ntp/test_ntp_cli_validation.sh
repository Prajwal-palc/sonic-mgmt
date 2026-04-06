#!/bin/bash

# NTP CLI Command Validation Script
# Tests all basic NTP commands from ntp.xml on device
# Device: 192.168.100.245 (smic_sonic1)
# Date: 2026-04-02

DEVICE_IP="192.168.100.245"
USERNAME="admin"
PASSWORD="root@123"
LOG_FILE="/tmp/ntp_cli_validation_$(date +%F_%H%M%S).log"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "NTP CLI Command Validation Test"
echo "Device: $DEVICE_IP"
echo "Log: $LOG_FILE"
echo "========================================"
echo ""

# Helper function to execute SSH command
exec_ssh() {
    local cmd="$1"
    local mode="$2"  # "click" or "klish"

    if [ "$mode" = "klish" ]; then
        # For klish mode, use sonic-cli with TTY allocation
        sshpass -p "$PASSWORD" ssh -t -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $USERNAME@$DEVICE_IP "sonic-cli" << EOF 2>&1
$cmd
exit
EOF
    else
        # For click mode, direct command execution
        sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $USERNAME@$DEVICE_IP "$cmd" 2>&1
    fi
}

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test function
test_command() {
    local test_name="$1"
    local command="$2"
    local mode="$3"  # "click" or "klish"
    local expect_success="$4"  # "yes" or "no"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    echo "[$TOTAL_TESTS] Testing: $test_name" | tee -a "$LOG_FILE"
    echo "    Command: $command" | tee -a "$LOG_FILE"
    echo "    Mode: $mode" | tee -a "$LOG_FILE"

    OUTPUT=$(exec_ssh "$command" "$mode" 2>&1)
    EXIT_CODE=$?

    echo "    Output:" | tee -a "$LOG_FILE"
    echo "$OUTPUT" | sed 's/^/        /' | tee -a "$LOG_FILE"

    # Check for errors
    if echo "$OUTPUT" | grep -iq "error\|failed\|invalid\|not found"; then
        if [ "$expect_success" = "no" ]; then
            echo -e "    ${YELLOW}[EXPECTED FAIL]${NC}" | tee -a "$LOG_FILE"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo -e "    ${RED}[FAILED]${NC}" | tee -a "$LOG_FILE"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        if [ "$expect_success" = "yes" ] || [ -z "$expect_success" ]; then
            echo -e "    ${GREEN}[PASSED]${NC}" | tee -a "$LOG_FILE"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo -e "    ${YELLOW}[UNEXPECTED SUCCESS]${NC}" | tee -a "$LOG_FILE"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    fi

    echo "" | tee -a "$LOG_FILE"
    sleep 2
}

echo "========================================" | tee -a "$LOG_FILE"
echo "PHASE 1: SHOW COMMANDS (Click Mode)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Show commands in click mode
test_command "Show NTP Status" "show ntp" "click" "yes"
test_command "Show Running Config NTP" "show runningconfiguration ntp" "click" "yes"

echo "========================================" | tee -a "$LOG_FILE"
echo "PHASE 2: SHOW COMMANDS (Klish Mode)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Show commands in klish mode
test_command "Show NTP Global" "show ntp global" "klish" "yes"
test_command "Show NTP Server" "show ntp server" "klish" "yes"
test_command "Show NTP Associations" "show ntp associations" "klish" "yes"

echo "========================================" | tee -a "$LOG_FILE"
echo "PHASE 3: NTP ENABLE/DISABLE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Test NTP enable/disable in klish mode
test_command "Disable NTP Service" "configure terminal
no ntp enable
end" "klish" "yes"

test_command "Enable NTP Service" "configure terminal
ntp enable
end" "klish" "yes"

test_command "Verify NTP Enabled" "show ntp global" "klish" "yes"

echo "========================================" | tee -a "$LOG_FILE"
echo "PHASE 4: AUTHENTICATION" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Test authentication commands
test_command "Configure Auth Key MD5" "configure terminal
ntp authentication-key 10 md5 TestKey123
end" "klish" "yes"

test_command "Configure Auth Key SHA256" "configure terminal
ntp authentication-key 20 sha256 SecureKey456
end" "klish" "yes"

test_command "Configure Trusted Key 10" "configure terminal
ntp trusted-key 10
end" "klish" "yes"

test_command "Enable NTP Authentication" "configure terminal
ntp authenticate
end" "klish" "yes"

test_command "Verify Authentication Config" "show ntp global" "klish" "yes"

test_command "Disable NTP Authentication" "configure terminal
no ntp authenticate
end" "klish" "yes"

test_command "Delete Trusted Key" "configure terminal
no ntp trusted-key 10
end" "klish" "yes"

test_command "Delete Auth Key 10" "configure terminal
no ntp authentication-key 10
end" "klish" "yes"

test_command "Delete Auth Key 20" "configure terminal
no ntp authentication-key 20
end" "klish" "yes"

echo "========================================" | tee -a "$LOG_FILE"
echo "PHASE 5: NTP SERVER CONFIGURATION" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Test NTP server configuration
test_command "Configure Basic NTP Server" "configure terminal
ntp server 172.16.1.1
end" "klish" "yes"

test_command "Verify Server Added" "show ntp server" "klish" "yes"

test_command "Configure Server with Version" "configure terminal
ntp server 172.16.1.2 version 4
end" "klish" "yes"

test_command "Configure Server with IBurst" "configure terminal
ntp server 172.16.1.3 iburst
end" "klish" "yes"

test_command "Configure Server with Prefer" "configure terminal
ntp server 172.16.1.4 prefer
end" "klish" "yes"

test_command "Verify Multiple Servers" "show ntp server" "klish" "yes"

test_command "Delete NTP Server" "configure terminal
no ntp server 172.16.1.1
end" "klish" "yes"

test_command "Verify Server Deleted" "show ntp server" "klish" "yes"

echo "========================================" | tee -a "$LOG_FILE"
echo "PHASE 6: SOURCE INTERFACE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Test source interface configuration
test_command "Configure Source Interface Ethernet0" "configure terminal
ntp source-interface Ethernet 0
end" "klish" "yes"

test_command "Verify Source Interface" "show ntp global" "klish" "yes"

test_command "Delete Source Interface" "configure terminal
no ntp source-interface
end" "klish" "yes"

test_command "Verify Source Removed" "show ntp global" "klish" "yes"

echo "========================================" | tee -a "$LOG_FILE"
echo "PHASE 7: VRF CONFIGURATION" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Test VRF configuration (may require mgmt VRF to exist)
test_command "Configure NTP VRF Default" "configure terminal
ntp vrf default
end" "klish" "yes"

test_command "Verify VRF Config" "show ntp global" "klish" "yes"

test_command "Delete NTP VRF" "configure terminal
no ntp vrf
end" "klish" "yes"

echo "========================================" | tee -a "$LOG_FILE"
echo "PHASE 8: CLEANUP" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Cleanup all NTP configuration
test_command "Delete Remaining Servers" "configure terminal
no ntp server 172.16.1.2
no ntp server 172.16.1.3
no ntp server 172.16.1.4
end" "klish" "yes"

test_command "Disable NTP" "configure terminal
no ntp enable
end" "klish" "yes"

test_command "Verify Clean State" "show ntp global" "klish" "yes"

echo "========================================" | tee -a "$LOG_FILE"
echo "TEST SUMMARY" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Total Tests: $TOTAL_TESTS" | tee -a "$LOG_FILE"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}" | tee -a "$LOG_FILE"
echo -e "${RED}Failed: $FAILED_TESTS${NC}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}" | tee -a "$LOG_FILE"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED!${NC}" | tee -a "$LOG_FILE"
    exit 1
fi
