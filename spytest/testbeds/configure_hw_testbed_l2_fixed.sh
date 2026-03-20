#!/bin/bash
################################################################################
# Hardware Testbed L2 ACL Configuration Script - FIXED VERSION
################################################################################
# Purpose: Configure hardware SONiC switches for L2 ACL testing using proper
#          VLAN API commands (config vlan member add -u) instead of direct
#          CONFIG_DB manipulation
# Testbed: testbed_acl_hw.yaml
# Issue Fixed: Previous script used sonic-db-cli which didn't initialize data plane
# Solution: Use 'config vlan member add <vlan> <port> -u' for untagged members
#
# Usage:
#   chmod +x configure_hw_testbed_l2_fixed.sh
#   ./configure_hw_testbed_l2_fixed.sh
#
# Created: 2026-03-20
################################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  $1${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

################################################################################
# Configure D1 (ACL Device)
################################################################################

configure_d1() {
    print_header "Configuring D1 (ACL Device) - 192.168.100.119"

    sshpass -p "$D1_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D1_USER}@${D1_IP} << 'ENDSSH'
#!/bin/bash

echo "=== Step 1: Remove L3 IP addresses ==="
sudo config interface ip remove Ethernet272 10.1.1.2/24 2>/dev/null || true
sudo config interface ip remove Ethernet513 10.1.2.1/24 2>/dev/null || true

echo ""
echo "=== Step 2: Create VLAN 100 ==="
sudo config vlan add 100

echo ""
echo "=== Step 3: Add VLAN members using proper API (untagged) ==="
# KEY FIX: Use 'config vlan member add' with -u flag for untagged
sudo config vlan member add 100 Ethernet272 -u
sudo config vlan member add 100 Ethernet513 -u

echo ""
echo "=== Step 4: Ensure interfaces are up ==="
sudo config interface startup Ethernet272
sudo config interface startup Ethernet513

echo ""
echo "=== Step 5: Save configuration ==="
sudo config save -y

echo ""
echo "=== Step 6: Wait for configuration to apply ==="
sleep 5

echo ""
echo "=== Verification ==="
echo "VLAN Configuration:"
show vlan brief

echo ""
echo "Interface Status:"
show interface status Ethernet272
echo "---"
show interface status Ethernet513

echo ""
echo "✓ D1 configured with proper VLAN API"
ENDSSH

    if [ $? -eq 0 ]; then
        print_info "D1 configured successfully"
    else
        print_error "D1 configuration failed"
        return 1
    fi
    echo ""
}

################################################################################
# Configure D2 (TX Device)
################################################################################

configure_d2() {
    print_header "Configuring D2 (TX Device) - 192.168.100.140"

    sshpass -p "$D2_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D2_USER}@${D2_IP} << 'ENDSSH'
#!/bin/bash

echo "=== Step 1: Remove L3 IP address ==="
sudo config interface ip remove Ethernet64 10.1.1.1/24 2>/dev/null || true

echo ""
echo "=== Step 2: Create VLAN 100 ==="
sudo config vlan add 100

echo ""
echo "=== Step 3: Add VLAN member using proper API (untagged) ==="
sudo config vlan member add 100 Ethernet64 -u

echo ""
echo "=== Step 4: Ensure interface is up ==="
sudo config interface startup Ethernet64

echo ""
echo "=== Step 5: Save configuration ==="
sudo config save -y

echo ""
echo "=== Step 6: Wait for configuration to apply ==="
sleep 5

echo ""
echo "=== Verification ==="
echo "VLAN Configuration:"
show vlan brief

echo ""
echo "Interface Status:"
show interface status Ethernet64

echo ""
echo "✓ D2 configured with proper VLAN API"
ENDSSH

    if [ $? -eq 0 ]; then
        print_info "D2 configured successfully"
    else
        print_error "D2 configuration failed"
        return 1
    fi
    echo ""
}

################################################################################
# Configure D3 (RX Device)
################################################################################

configure_d3() {
    print_header "Configuring D3 (RX Device) - 192.168.100.173"

    sshpass -p "$D3_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D3_USER}@${D3_IP} << 'ENDSSH'
#!/bin/bash

echo "=== Step 1: Remove L3 IP address ==="
sudo config interface ip remove Ethernet513 10.1.2.2/24 2>/dev/null || true

echo ""
echo "=== Step 2: Create VLAN 100 ==="
sudo config vlan add 100

echo ""
echo "=== Step 3: Add VLAN member using proper API (untagged) ==="
sudo config vlan member add 100 Ethernet513 -u

echo ""
echo "=== Step 4: Ensure interface is up ==="
sudo config interface startup Ethernet513

echo ""
echo "=== Step 5: Save configuration ==="
sudo config save -y

echo ""
echo "=== Step 6: Wait for configuration to apply ==="
sleep 5

echo ""
echo "=== Verification ==="
echo "VLAN Configuration:"
show vlan brief

echo ""
echo "Interface Status:"
show interface status Ethernet513

echo ""
echo "Interface MAC Address:"
ip link show Ethernet513 | grep -i "link/ether"

echo ""
echo "✓ D3 configured with proper VLAN API"
ENDSSH

    if [ $? -eq 0 ]; then
        print_info "D3 configured successfully"
    else
        print_error "D3 configuration failed"
        return 1
    fi
    echo ""
}

################################################################################
# Verify L2 Forwarding
################################################################################

verify_mac_learning() {
    print_header "Verifying MAC Learning on D1"

    sshpass -p "$D1_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D1_USER}@${D1_IP} "show mac" 2>/dev/null

    echo ""
}

################################################################################
# Print Configuration Summary
################################################################################

print_summary() {
    print_header "L2 Configuration Complete - Ready for Testing"

    cat << EOF
Hardware Testbed L2 ACL Configuration Complete!

Configuration Method Used:
  ✓ PROPER VLAN API: 'config vlan member add <vlan> <port> -u'
  ✗ BROKEN METHOD: 'sonic-db-cli CONFIG_DB HSET ...' (old script)

Key Difference:
  - Using 'config vlan member add' properly initializes the data plane
  - Direct CONFIG_DB manipulation creates valid config but no forwarding

Topology (L2 Switching):
  ┌──────────────┐                    ┌──────────────┐                    ┌──────────────┐
  │   D2 (8023)  │                    │   D1 (8011)  │                    │   D3 (8010)  │
  │  TX Device   │                    │ ACL Device   │                    │  RX Device   │
  │              │                    │              │                    │              │
  │ Ethernet64 ◄─┼────────────────────┼─ Ethernet272 │                    │              │
  │ VLAN 100     │                    │ VLAN 100     │                    │              │
  │ (untagged)   │   (L2 switching)   │ (ingress)    │                    │              │
  │              │                    │              │                    │              │
  │              │                    │ Ethernet513──┼────────────────────┼──► Ethernet513
  │              │                    │ VLAN 100     │   (L2 switching)   │ VLAN 100     │
  │              │                    │ (egress)     │                    │ (untagged)   │
  └──────────────┘                    └──────────────┘                    └──────────────┘

Next Steps:
  1. Verify L2 forwarding with baseline test (no ACL)
  2. If baseline works, proceed with L2-R02 ACL testing
  3. Test dynamic ACL modification while traffic flows

EOF
}

################################################################################
# Main Execution
################################################################################

main() {
    clear
    print_header "Hardware Testbed L2 ACL Configuration (FIXED)"
    echo ""
    print_info "Using proper VLAN API: 'config vlan member add -u'"
    echo ""

    # Configure all devices
    configure_d1 || exit 1
    configure_d2 || exit 1
    configure_d3 || exit 1

    # Verify MAC learning
    verify_mac_learning

    # Print summary
    print_summary

    print_info "Hardware testbed configured for L2 ACL testing!"
    print_info "Testbed should now have working L2 forwarding."
    echo ""
}

# Run main function
main "$@"
