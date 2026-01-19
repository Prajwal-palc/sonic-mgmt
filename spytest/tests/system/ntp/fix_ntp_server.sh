#!/bin/bash
# Fix NTP Server Issues
# Run this to fix the chrony setup problems

set -e

echo "========================================="
echo "Fixing NTP Server Configuration"
echo "========================================="
echo ""

# Fix 1: Correct ownership on chrony.keys file
echo "[1/4] Fixing chrony.keys ownership..."
sudo chown root:root /etc/chrony/chrony.keys
sudo chmod 640 /etc/chrony/chrony.keys
echo "✓ Fixed"

# Fix 2: Restart chrony service
echo ""
echo "[2/4] Restarting chrony service..."
sudo systemctl restart chrony
sleep 2
echo "✓ Restarted"

# Fix 3: Check service status
echo ""
echo "[3/4] Checking service status..."
if systemctl is-active --quiet chrony; then
    echo "✓ Chrony is running"
    systemctl status chrony --no-pager | head -5
else
    echo "✗ Chrony failed to start"
    echo "Checking logs..."
    sudo journalctl -u chrony -n 20 --no-pager
    exit 1
fi

# Fix 4: Verify NTP port is listening
echo ""
echo "[4/4] Verifying NTP port 123..."
sleep 1
if sudo ss -ulnp | grep -q ":123"; then
    echo "✓ NTP port 123 is listening"
    sudo ss -ulnp | grep :123
else
    echo "✗ Port 123 is still not listening"
    echo "Checking what's wrong..."
    sudo journalctl -u chrony -n 30 --no-pager
    exit 1
fi

echo ""
echo "========================================="
echo "NTP Server Fix Complete!"
echo "========================================="
echo ""
echo "Testing NTP server..."
chronyc sources
echo ""
chronyc tracking
echo ""
echo "✓ All fixed! NTP server is ready."
echo ""
echo "Next: Run tests with:"
echo "  export NTP_ISCLI_VAR_FILE=tests/system/ntp/vars_ntp_iscli_local.yaml"
echo "  ./bin/spytest --testbed ./testbeds/testbed_vs_1node_ntp.yaml system/ntp/test_ntp_iscli.py --logs-path ./logs/test_ntp_local_\$(date +%F_%H%M%S)"
