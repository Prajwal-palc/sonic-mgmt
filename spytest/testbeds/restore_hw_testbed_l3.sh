#!/bin/bash
################################################################################
# Hardware Testbed L3 Routing Restoration Script
################################################################################
# Purpose: Restore hardware SONiC switches to L3 routing mode
# Testbed: testbed_acl_hw.yaml
# Use Case: Revert from L2 ACL testing (VLAN mode) back to L3 routing mode
#
# Usage:
#   chmod +x restore_hw_testbed_l3.sh
#   ./restore_hw_testbed_l3.sh
#
# Created: 2026-03-18
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

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

################################################################################
# Restore D1 to L3 Mode
################################################################################

restore_d1() {
    print_header "Restoring D1 to L3 Routing Mode - 192.168.100.119"

    sshpass -p "$D1_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D1_USER}@${D1_IP} << 'ENDSSH'
#!/bin/bash

echo "=== Step 1: Remove VLAN members ==="
sudo config vlan member del 100 Ethernet272 2>/dev/null || true
sudo config vlan member del 100 Ethernet513 2>/dev/null || true

echo ""
echo "=== Step 2: Delete VLAN 100 ==="
sudo config vlan del 100 2>/dev/null || true

echo ""
echo "=== Step 3: Remove any ACL configuration ==="
sudo config acl remove table L2_ACL_TEST_DEST_DENY 2>/dev/null || true
sudo config acl remove table L2_ACL_TEST_DENY 2>/dev/null || true
sudo config acl remove table L2_ACL_TEST 2>/dev/null || true

echo ""
echo "=== Step 4: Add L3 IP addresses ==="
sudo config interface ip add Ethernet272 10.1.1.2/24
sudo config interface ip add Ethernet513 10.1.2.1/24

echo ""
echo "=== Step 5: Ensure interfaces are up ==="
sudo config interface startup Ethernet272
sudo config interface startup Ethernet513

echo ""
echo "=== Step 6: Save configuration ==="
sudo config save -y

echo ""
echo "=== Verification ==="
echo "Interface Status:"
show interface status Ethernet272
echo "---"
show interface status Ethernet513

echo ""
echo "IP Configuration:"
show ip interfaces | grep -E 'Ethernet272|Ethernet513'

echo ""
echo "✓ D1 restored to L3 routing mode"
ENDSSH

    if [ $? -eq 0 ]; then
        print_info "D1 restored successfully"
    else
        print_warn "D1 restoration completed with warnings"
    fi
    echo ""
}

################################################################################
# Restore D2 to L3 Mode
################################################################################

restore_d2() {
    print_header "Restoring D2 to L3 Routing Mode - 192.168.100.140"

    sshpass -p "$D2_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D2_USER}@${D2_IP} << 'ENDSSH'
#!/bin/bash

echo "=== Step 1: Remove VLAN member ==="
sudo config vlan member del 100 Ethernet64 2>/dev/null || true

echo ""
echo "=== Step 2: Delete VLAN 100 ==="
sudo config vlan del 100 2>/dev/null || true

echo ""
echo "=== Step 3: Add L3 IP address ==="
sudo config interface ip add Ethernet64 10.1.1.1/24

echo ""
echo "=== Step 4: Ensure interface is up ==="
sudo config interface startup Ethernet64

echo ""
echo "=== Step 5: Save configuration ==="
sudo config save -y

echo ""
echo "=== Verification ==="
echo "Interface Status:"
show interface status Ethernet64

echo ""
echo "IP Configuration:"
show ip interfaces | grep Ethernet64

echo ""
echo "✓ D2 restored to L3 routing mode"
ENDSSH

    if [ $? -eq 0 ]; then
        print_info "D2 restored successfully"
    else
        print_warn "D2 restoration completed with warnings"
    fi
    echo ""
}

################################################################################
# Restore D3 to L3 Mode
################################################################################

restore_d3() {
    print_header "Restoring D3 to L3 Routing Mode - 192.168.100.173"

    sshpass -p "$D3_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D3_USER}@${D3_IP} << 'ENDSSH'
#!/bin/bash

echo "=== Step 1: Remove VLAN member ==="
sudo config vlan member del 100 Ethernet513 2>/dev/null || true

echo ""
echo "=== Step 2: Delete VLAN 100 ==="
sudo config vlan del 100 2>/dev/null || true

echo ""
echo "=== Step 3: Add L3 IP address ==="
sudo config interface ip add Ethernet513 10.1.2.2/24

echo ""
echo "=== Step 4: Ensure interface is up ==="
sudo config interface startup Ethernet513

echo ""
echo "=== Step 5: Save configuration ==="
sudo config save -y

echo ""
echo "=== Verification ==="
echo "Interface Status:"
show interface status Ethernet513

echo ""
echo "IP Configuration:"
show ip interfaces | grep Ethernet513

echo ""
echo "✓ D3 restored to L3 routing mode"
ENDSSH

    if [ $? -eq 0 ]; then
        print_info "D3 restored successfully"
    else
        print_warn "D3 restoration completed with warnings"
    fi
    echo ""
}

################################################################################
# Print Summary
################################################################################

print_summary() {
    print_header "Restoration Summary"

    cat << EOF
Hardware Testbed L3 Routing Restoration Complete!

Original Topology (L3 Routing):
  ┌──────────────┐                    ┌──────────────┐                    ┌──────────────┐
  │   DUT2       │                    │   DUT1       │                    │   DUT3       │
  │  (TX Host)   │                    │ (ACL Device) │                    │  (RX Host)   │
  │    8023      │                    │    8011      │                    │    8010      │
  │              │                    │              │                    │              │
  │ Ethernet64 ◄─┼────────────────────┼─ Ethernet272 │                    │              │
  │ 10.1.1.1/24  │                    │ 10.1.1.2/24  │                    │              │
  │              │   (L3 routing)     │              │                    │              │
  │              │                    │              │                    │              │
  │              │                    │ Ethernet513──┼────────────────────┼──► Ethernet513
  │              │                    │ 10.1.2.1/24  │   (L3 routing)     │ 10.1.2.2/24  │
  │              │                    │              │                    │              │
  └──────────────┘                    └──────────────┘                    └──────────────┘

IP Configuration:
  - D1 (192.168.100.119):
    * Ethernet272: 10.1.1.2/24
    * Ethernet513: 10.1.2.1/24
  - D2 (192.168.100.140):
    * Ethernet64: 10.1.1.1/24
  - D3 (192.168.100.173):
    * Ethernet513: 10.1.2.2/24

Subnets:
  - TX Subnet: 10.1.1.0/24 (D2: 10.1.1.1, D1: 10.1.1.2)
  - RX Subnet: 10.1.2.0/24 (D1: 10.1.2.1, D3: 10.1.2.2)

Testbed is now ready for L3 ACL testing with:
  ./bin/spytest --testbed testbeds/testbed_acl_hw.yaml \\
      tests/routing/l3_acl/test_l3_acl.py \\
      --logs-path ./logs/l3_acl_hw_\$(date +%F_%H%M%S)

EOF
}

################################################################################
# Main Execution
################################################################################

main() {
    clear
    print_header "Hardware Testbed L3 Routing Restoration Script"
    echo ""

    # Restore all devices
    restore_d1
    restore_d2
    restore_d3

    # Print summary
    print_summary

    print_info "Hardware testbed is back to L3 routing mode!"
    echo ""
}

# Run main function
main "$@"
