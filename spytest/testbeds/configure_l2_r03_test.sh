#!/bin/bash
################################################################################
# L2-R03 Test Configuration Script
################################################################################

set -e

# Device credentials
D1_IP="192.168.100.119"
D1_USER="admin"
D1_PASS="sonic@123"

D2_IP="192.168.100.140"
D2_USER="admin"
D2_PASS="broadcom"

D3_IP="192.168.100.173"
D3_USER="admin"
D3_PASS="sonic@123"

echo "=== Configuring D1 for L2 Mode ==="
sshpass -p "$D1_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    ${D1_USER}@${D1_IP} << 'ENDSSH'
sudo config interface ip remove Ethernet272 10.1.1.2/24 2>/dev/null || true
sudo config interface ip remove Ethernet513 10.1.2.1/24 2>/dev/null || true
sudo config interface ipv6 disable use-link-local-only Ethernet272 2>/dev/null || true
sudo config interface ipv6 disable use-link-local-only Ethernet513 2>/dev/null || true
sudo config vlan add 100 2>/dev/null || true
sudo config vlan member add 100 Ethernet272 -u
sudo config vlan member add 100 Ethernet513 -u
sudo config save -y
sleep 2
show vlan brief
ENDSSH

echo ""
echo "=== Configuring D2 for L2 Mode ==="
sshpass -p "$D2_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    ${D2_USER}@${D2_IP} << 'ENDSSH'
sudo config interface ip remove Ethernet64 10.1.1.1/24 2>/dev/null || true
sudo config interface ipv6 disable use-link-local-only Ethernet64 2>/dev/null || true
sudo config vlan add 100 2>/dev/null || echo "VLAN 100 already exists"
sudo config vlan member add 100 Ethernet64 -u 2>/dev/null || echo "Ethernet64 already in VLAN 100"
sudo config save -y
sleep 2
show vlan brief
ENDSSH

echo ""
echo "=== Configuring D3 for L2 Mode ==="
sshpass -p "$D3_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    ${D3_USER}@${D3_IP} << 'ENDSSH'
sudo config interface ip remove Ethernet513 10.1.2.2/24 2>/dev/null || true
sudo config interface ipv6 disable use-link-local-only Ethernet513 2>/dev/null || true
sudo config vlan add 100 2>/dev/null || true
sudo config vlan member add 100 Ethernet513 -u
sudo config save -y
sleep 2
show vlan brief
ENDSSH

echo ""
echo "=== L2 Configuration Complete ==="
