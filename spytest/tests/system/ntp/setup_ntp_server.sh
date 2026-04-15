#!/bin/bash
# NTP Server Setup Script for Test Environment
# Run this on the test machine (192.168.100.175) to set up a local NTP server

set -e

echo "========================================="
echo "NTP Server Setup for Test Environment"
echo "========================================="
echo ""

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run with sudo"
    echo "Usage: sudo bash setup_ntp_server.sh"
    exit 1
fi

# Get the primary IP address
PRIMARY_IP=$(hostname -I | awk '{print $1}')
echo "Primary IP: $PRIMARY_IP"
echo "DUT IP: 192.168.100.147"
echo ""

# Install chrony (modern NTP implementation)
echo "[1/5] Installing chrony NTP server..."
apt-get update -qq
apt-get install -y chrony

# Backup original config
echo "[2/5] Backing up original chrony configuration..."
cp /etc/chrony/chrony.conf /etc/chrony/chrony.conf.backup.$(date +%Y%m%d_%H%M%S)

# Create new chrony configuration
echo "[3/5] Configuring chrony as NTP server..."
cat > /etc/chrony/chrony.conf << 'EOF'
# NTP Server Configuration for Test Environment
# Primary upstream NTP servers (public pools)
pool 2.debian.pool.ntp.org iburst
pool time.google.com iburst

# Fallback servers
server 0.pool.ntp.org iburst
server 1.pool.ntp.org iburst

# Allow NTP client access from local network
# Allow DUT and local subnet
allow 192.168.100.0/24
allow 192.168.0.0/16

# Serve time even if not synchronized to upstream (useful for isolated testing)
local stratum 10

# Record the rate at which the system clock gains/loses time
driftfile /var/lib/chrony/chrony.drift

# Enable kernel synchronization of the real-time clock (RTC)
rtcsync

# Step the system clock instead of slewing it if adjustment is larger than 1 second
makestep 1 3

# Log directory
logdir /var/log/chrony

# NTP authentication keys directory (for testing authenticated NTP)
keyfile /etc/chrony/chrony.keys

# Command port for chronyc
cmdport 323
EOF

# Create authentication keys file for testing
echo "[4/5] Creating NTP authentication keys..."
cat > /etc/chrony/chrony.keys << 'EOF'
# NTP Authentication Keys for Testing
# Format: <key_id> <hash_algorithm> <password>

# Test keys matching those used in test scripts
1 MD5 TestKey123
10 SHA256 CompleteKey
15 SHA256 TestAuthKey
20 SHA1 SimpleKey
25 SHA384 SecureKey456
30 SHA512 VerySecureKey789
EOF

chmod 640 /etc/chrony/chrony.keys
chown root:chrony /etc/chrony/chrony.keys

# Restart chrony service
echo "[5/5] Restarting chrony service..."
systemctl restart chrony
systemctl enable chrony

# Wait for service to start
sleep 2

# Verify service is running
if systemctl is-active --quiet chrony; then
    echo ""
    echo "✓ Chrony NTP server is running successfully!"
else
    echo ""
    echo "✗ Error: Chrony service failed to start"
    systemctl status chrony
    exit 1
fi

# Display status
echo ""
echo "========================================="
echo "NTP Server Status"
echo "========================================="
chronyc sources
echo ""
echo "========================================="
echo "NTP Server Configuration Summary"
echo "========================================="
echo "Server IP: $PRIMARY_IP"
echo "Listening on: UDP port 123 (NTP)"
echo "Allowed clients: 192.168.100.0/24"
echo "Authentication: Enabled with test keys"
echo ""
echo "Test from DUT with:"
echo "  ntpdate -q $PRIMARY_IP"
echo "  or"
echo "  chronyc tracking"
echo ""
echo "To verify NTP is accessible:"
echo "  sudo netstat -ulnp | grep :123"
echo "  sudo ss -ulnp | grep :123"
echo ""
echo "Setup complete!"
