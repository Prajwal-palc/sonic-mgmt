#!/bin/bash
# Manual Setup Commands for NTP Server
# Copy and paste these commands one by one into your terminal

echo "==================================================================="
echo "NTP Server Setup - Manual Installation"
echo "==================================================================="
echo ""
echo "Please run these commands in your terminal:"
echo ""

cat << 'EOF'

# ============================================
# STEP 1: Install Chrony NTP Server
# ============================================
sudo apt-get update
sudo apt-get install -y chrony

# ============================================
# STEP 2: Backup Original Configuration
# ============================================
sudo cp /etc/chrony/chrony.conf /etc/chrony/chrony.conf.backup.$(date +%Y%m%d_%H%M%S)

# ============================================
# STEP 3: Create Chrony Configuration
# ============================================
sudo tee /etc/chrony/chrony.conf > /dev/null << 'CHRONY_CONF'
# NTP Server Configuration for Test Environment
pool 2.debian.pool.ntp.org iburst
pool time.google.com iburst
server 0.pool.ntp.org iburst
server 1.pool.ntp.org iburst

# Allow NTP client access from local network
allow 192.168.100.0/24
allow 192.168.0.0/16

# Serve time even if not synchronized
local stratum 10

driftfile /var/lib/chrony/chrony.drift
rtcsync
makestep 1 3
logdir /var/log/chrony
keyfile /etc/chrony/chrony.keys
cmdport 323
CHRONY_CONF

# ============================================
# STEP 4: Create Authentication Keys
# ============================================
sudo tee /etc/chrony/chrony.keys > /dev/null << 'KEYS'
1 MD5 TestKey123
10 SHA256 CompleteKey
15 SHA256 TestAuthKey
20 SHA1 SimpleKey
25 SHA384 SecureKey456
30 SHA512 VerySecureKey789
KEYS

sudo chmod 640 /etc/chrony/chrony.keys
sudo chown root:root /etc/chrony/chrony.keys

# ============================================
# STEP 5: Enable and Start Chrony
# ============================================
sudo systemctl enable chrony
sudo systemctl restart chrony

# ============================================
# STEP 6: Wait and Verify
# ============================================
sleep 3
sudo systemctl status chrony | head -15

echo ""
echo "✓ NTP Server Setup Complete!"
echo ""
echo "Verify with:"
echo "  chronyc sources"
echo "  chronyc tracking"
echo "  sudo ss -ulnp | grep :123"
echo ""

EOF
