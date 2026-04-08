#!/bin/bash
# Verification script for NTP server setup
# Tests connectivity between test machine and DUT

set -e

NTP_SERVER="192.168.100.175"
DUT_IP="192.168.100.147"
DUT_USER="admin"
DUT_PASS="root@123"

echo "========================================="
echo "NTP Server Verification"
echo "========================================="
echo ""

# Test 1: Check if chrony is running on test machine
echo "[Test 1/5] Checking chrony service status..."
if systemctl is-active --quiet chrony; then
    echo "✓ Chrony service is running"
else
    echo "✗ Chrony service is NOT running"
    echo "  Run: sudo bash setup_ntp_server.sh"
    exit 1
fi

# Test 2: Check if NTP port is listening
echo ""
echo "[Test 2/5] Checking NTP port (UDP 123)..."
if sudo netstat -ulnp 2>/dev/null | grep -q ":123" || sudo ss -ulnp 2>/dev/null | grep -q ":123"; then
    echo "✓ NTP server is listening on UDP port 123"
    sudo ss -ulnp | grep :123 | head -1
else
    echo "✗ NTP port 123 is NOT listening"
    exit 1
fi

# Test 3: Check chrony sources
echo ""
echo "[Test 3/5] Checking NTP upstream sources..."
chronyc sources || true

# Test 4: Check chrony tracking
echo ""
echo "[Test 4/5] Checking NTP synchronization status..."
chronyc tracking || true

# Test 5: Test NTP query from localhost
echo ""
echo "[Test 5/5] Testing NTP query to local server..."
if command -v ntpdate >/dev/null 2>&1; then
    ntpdate -q $NTP_SERVER || echo "  (This may fail if system time is already synced)"
elif command -v chronyc >/dev/null 2>&1; then
    echo "  Using chronyc for verification..."
    chronyc -h $NTP_SERVER tracking 2>&1 || echo "  (chronyc remote query may not work)"
else
    echo "  ⚠ ntpdate not installed. Skipping NTP query test."
    echo "  Install with: sudo apt-get install ntpdate"
fi

# Test 6: Connectivity check to DUT
echo ""
echo "[Test 6/7] Testing network connectivity to DUT..."
if ping -c 2 -W 2 $DUT_IP >/dev/null 2>&1; then
    echo "✓ DUT is reachable at $DUT_IP"
else
    echo "✗ Cannot reach DUT at $DUT_IP"
    echo "  Check if DUT is powered on and network is configured"
fi

# Test 7: SSH connectivity to DUT
echo ""
echo "[Test 7/7] Testing SSH connection to DUT..."
if command -v sshpass >/dev/null 2>&1; then
    if sshpass -p "$DUT_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
        $DUT_USER@$DUT_IP "echo 'SSH connection successful'" 2>/dev/null; then
        echo "✓ SSH connection to DUT successful"

        # Try to query NTP from DUT
        echo ""
        echo "Testing NTP query from DUT to NTP server..."
        sshpass -p "$DUT_PASS" ssh -o StrictHostKeyChecking=no \
            $DUT_USER@$DUT_IP "ntpdate -q $NTP_SERVER 2>&1 || chronyc sources 2>&1 || echo 'NTP query tools not available on DUT'" | head -10
    else
        echo "✗ Cannot SSH to DUT"
        echo "  Check credentials and SSH service on DUT"
    fi
else
    echo "  ⚠ sshpass not installed. Cannot test SSH automatically."
    echo "  Install with: sudo apt-get install sshpass"
    echo "  Or test manually: ssh $DUT_USER@$DUT_IP"
fi

echo ""
echo "========================================="
echo "Verification Summary"
echo "========================================="
echo "NTP Server: $NTP_SERVER"
echo "DUT IP: $DUT_IP"
echo ""
echo "Next steps:"
echo "1. If all tests passed, you can run tests with local NTP server"
echo "2. Set environment variable to use local config:"
echo "   export NTP_ISCLI_VAR_FILE=tests/system/ntp/vars_ntp_iscli_local.yaml"
echo "3. Run tests:"
echo "   ./bin/spytest --testbed ./testbeds/testbed_vs_1node_ntp.yaml \\"
echo "     system/ntp/test_ntp_iscli.py \\"
echo "     --logs-path ./logs/test_ntp_local_\$(date +%F_%H%M%S)"
echo ""
