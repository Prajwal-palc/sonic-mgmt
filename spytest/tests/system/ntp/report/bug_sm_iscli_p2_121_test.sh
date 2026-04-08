#!/bin/bash
# Manual Test Script for SM_ISCLI_P2_121
# Bug: show ntp associations refid not showing upstream NTP source IP
# Issue: SMCI IS-CLI refid field doesn't display upstream NTP source IP like Broadcom does

DEVICE="192.168.100.147"
USER="admin"
PASS="root@123"
LOG="/tmp/bug_sm_iscli_p2_121_test.log"

# Clear log
> "$LOG"

echo "=================================================================================" | tee -a "$LOG"
echo "BUG SM_ISCLI_P2_121 MANUAL TEST - NTP Associations Refid Field Validation" | tee -a "$LOG"
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG"
echo "Device: $DEVICE" | tee -a "$LOG"
echo "Bug Claim: 'show ntp associations' refid not showing upstream NTP source IP" | tee -a "$LOG"
echo "Expected: refid should display IP address of upstream NTP source" | tee -a "$LOG"
echo "=================================================================================" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# STEP 1: Cleanup existing configuration
echo "=== STEP 1: Cleanup existing NTP configuration ===" | tee -a "$LOG"
printf "configure terminal\nno ntp server 192.168.100.175\nno ntp server time.google.com\nno ntp server 216.239.35.12\nno ntp server 10.10.10.99\nno ntp source-interface\nexit\n" | \
sshpass -p "$PASS" ssh -tt -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $USER@$DEVICE "sonic-cli" 2>&1 | tee -a "$LOG"
sleep 2

# STEP 2: Configure NTP server with public Google NTP (should sync quickly)
echo "" | tee -a "$LOG"
echo "=== STEP 2: Configure NTP server (216.239.35.12 - time4.google.com) ===" | tee -a "$LOG"
printf "configure terminal\nntp server 216.239.35.12\nntp enable\nexit\nshow ntp server\nexit\n" | \
sshpass -p "$PASS" ssh -tt -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $USER@$DEVICE "sonic-cli" 2>&1 | tee -a "$LOG"
sleep 3

# STEP 3: Wait for initial NTP poll cycle (minimum 8 seconds for first poll)
echo "" | tee -a "$LOG"
echo "=== STEP 3: Waiting 30 seconds for NTP synchronization to start... ===" | tee -a "$LOG"
sleep 30

# STEP 4: Check show ntp associations output (klish mode - CRITICAL TEST)
echo "" | tee -a "$LOG"
echo "=== STEP 4: CRITICAL TEST - Verify 'show ntp associations' refid field (klish mode) ===" | tee -a "$LOG"
echo "Expected: refid should display upstream NTP source IP address" | tee -a "$LOG"
printf "show ntp associations\nexit\n" | \
sshpass -p "$PASS" ssh -tt -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $USER@$DEVICE "sonic-cli" 2>&1 | tee -a "$LOG"
sleep 2

# STEP 5: Wait additional time for better synchronization
echo "" | tee -a "$LOG"
echo "=== STEP 5: Waiting additional 30 seconds for better synchronization... ===" | tee -a "$LOG"
sleep 30

# STEP 6: Check show ntp associations again (after more sync time)
echo "" | tee -a "$LOG"
echo "=== STEP 6: Verify 'show ntp associations' after extended sync time ===" | tee -a "$LOG"
printf "show ntp associations\nexit\n" | \
sshpass -p "$PASS" ssh -tt -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $USER@$DEVICE "sonic-cli" 2>&1 | tee -a "$LOG"
sleep 2

# STEP 7: Compare with click mode output (backend comparison)
echo "" | tee -a "$LOG"
echo "=== STEP 7: Backend verification - Click mode 'show ntp' ===" | tee -a "$LOG"
echo "Expected: Click mode should display refid field with IP address" | tee -a "$LOG"
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $USER@$DEVICE "show ntp" 2>&1 | tee -a "$LOG"
sleep 2

# STEP 8: Check chronyd sources directly
echo "" | tee -a "$LOG"
echo "=== STEP 8: Backend verification - chronyc sources (raw chronyd output) ===" | tee -a "$LOG"
echo "Expected: chronyd sources should show refid with IP address" | tee -a "$LOG"
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $USER@$DEVICE "sudo chronyc sources -v" 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=================================================================================" | tee -a "$LOG"
echo "TEST COMPLETED - Review log at: $LOG" | tee -a "$LOG"
echo "=================================================================================" | tee -a "$LOG"
echo "" | tee -a "$LOG"
echo "ANALYSIS CHECKLIST:" | tee -a "$LOG"
echo "1. Check STEP 4 & STEP 6 - klish 'show ntp associations' refid field" | tee -a "$LOG"
echo "   - If refid is EMPTY or shows '.INIT.' only -> BUG CONFIRMED" | tee -a "$LOG"
echo "   - If refid shows IP address (e.g., 129.6.15.28) -> BUG NOT PRESENT" | tee -a "$LOG"
echo "2. Check STEP 7 - click mode 'show ntp' refid field" | tee -a "$LOG"
echo "   - Compare refid field between klish and click modes" | tee -a "$LOG"
echo "3. Check STEP 8 - chronyd sources refid field (ground truth)" | tee -a "$LOG"
echo "   - Confirms what chronyd actually knows about upstream NTP source" | tee -a "$LOG"
echo "4. Look for discrepancy: If chronyd/click show refid but klish doesn't -> BUG" | tee -a "$LOG"
echo "=================================================================================" | tee -a "$LOG"
