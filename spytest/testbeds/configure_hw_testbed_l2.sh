#!/bin/bash
################################################################################
# Hardware Testbed L2 ACL Pre-Configuration Script
################################################################################
# Purpose: Configure hardware SONiC switches for L2 ACL testing
# Testbed: testbed_acl_hw.yaml
# Topology: 3 Hardware SONiC DUTs (D1, D2, D3) with Broadcom ASICs
#
# Devices:
#   D1 (8011): 192.168.100.119 - ACL Device (Supermicro SSE-T8196)
#   D2 (8023): 192.168.100.140 - TX Traffic Generator (Celestica DS3000)
#   D3 (8010): 192.168.100.173 - RX Traffic Receiver (Supermicro SSE-T8164)
#
# Configuration:
#   VLAN 100 - L2 switching for ACL testing
#   D1: Ethernet272 (ingress from D2), Ethernet513 (egress to D3)
#   D2: Ethernet64 (connected to D1)
#   D3: Ethernet513 (connected to D1)
#
# Usage:
#   chmod +x configure_hw_testbed_l2.sh
#   ./configure_hw_testbed_l2.sh
#
# Created: 2026-03-18
################################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# VLAN configuration
VLAN_ID="100"

# Interface mapping
D1_INGRESS="Ethernet272"  # Connected to D2:Ethernet64
D1_EGRESS="Ethernet513"   # Connected to D3:Ethernet513
D2_INTERFACE="Ethernet64" # Connected to D1:Ethernet272
D3_INTERFACE="Ethernet513" # Connected to D1:Ethernet513

################################################################################
# Functions
################################################################################

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

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

################################################################################
# Verify Device Connectivity
################################################################################

verify_connectivity() {
    print_header "Verifying Device Connectivity"

    print_step "Checking D1 (192.168.100.119)..."
    if sshpass -p "$D1_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=5 ${D1_USER}@${D1_IP} "hostname" > /dev/null 2>&1; then
        print_info "D1 is reachable"
    else
        print_error "D1 is not reachable"
        exit 1
    fi

    print_step "Checking D2 (192.168.100.140)..."
    if sshpass -p "$D2_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=5 ${D2_USER}@${D2_IP} "hostname" > /dev/null 2>&1; then
        print_info "D2 is reachable"
    else
        print_error "D2 is not reachable"
        exit 1
    fi

    print_step "Checking D3 (192.168.100.173)..."
    if sshpass -p "$D3_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=5 ${D3_USER}@${D3_IP} "hostname" > /dev/null 2>&1; then
        print_info "D3 is reachable"
    else
        print_error "D3 is not reachable"
        exit 1
    fi

    echo ""
    print_info "All devices are reachable!"
    echo ""
}

################################################################################
# Backup Current Configuration
################################################################################

backup_configuration() {
    print_header "Backing Up Current Configuration"

    BACKUP_DIR="./hw_testbed_backups_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    print_step "Backing up D1 configuration..."
    sshpass -p "$D1_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D1_USER}@${D1_IP} "show runningconfiguration all" > "${BACKUP_DIR}/d1_config_backup.txt" 2>/dev/null || true

    print_step "Backing up D2 configuration..."
    sshpass -p "$D2_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D2_USER}@${D2_IP} "show runningconfiguration all" > "${BACKUP_DIR}/d2_config_backup.txt" 2>/dev/null || true

    print_step "Backing up D3 configuration..."
    sshpass -p "$D3_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D3_USER}@${D3_IP} "show runningconfiguration all" > "${BACKUP_DIR}/d3_config_backup.txt" 2>/dev/null || true

    print_info "Configuration backups saved to: $BACKUP_DIR"
    echo ""
}

################################################################################
# Configure D1 (ACL Device)
################################################################################

configure_d1() {
    print_header "Configuring D1 (ACL Device) - 192.168.100.119"

    print_step "Configuring D1 for L2 switching..."

    sshpass -p "$D1_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D1_USER}@${D1_IP} << 'ENDSSH'
#!/bin/bash

echo "=== Step 1: Shutdown interfaces ==="
sudo config interface shutdown Ethernet272
sudo config interface shutdown Ethernet513

echo ""
echo "=== Step 2: Remove existing IP configuration ==="
sudo config interface ip remove Ethernet272 10.1.1.2/24 2>/dev/null || true
sudo config interface ip remove Ethernet513 10.1.2.1/24 2>/dev/null || true

echo ""
echo "=== Step 3: Remove from CONFIG_DB INTERFACE table ==="
sudo sonic-db-cli CONFIG_DB DEL "INTERFACE|Ethernet272" 2>/dev/null || true
sudo sonic-db-cli CONFIG_DB DEL "INTERFACE|Ethernet272|10.1.1.2/24" 2>/dev/null || true
sudo sonic-db-cli CONFIG_DB DEL "INTERFACE|Ethernet513" 2>/dev/null || true
sudo sonic-db-cli CONFIG_DB DEL "INTERFACE|Ethernet513|10.1.2.1/24" 2>/dev/null || true

echo ""
echo "=== Step 4: Delete VLAN 100 if it exists ==="
sudo config vlan del 100 2>/dev/null || true

echo ""
echo "=== Step 5: Create VLAN 100 ==="
sudo config vlan add 100

echo ""
echo "=== Step 6: Add interfaces to VLAN 100 ==="
# Add using sonic-db-cli to bypass checks
sudo sonic-db-cli CONFIG_DB HSET "VLAN_MEMBER|Vlan100|Ethernet272" "tagging_mode" "untagged"
sudo sonic-db-cli CONFIG_DB HSET "VLAN_MEMBER|Vlan100|Ethernet513" "tagging_mode" "untagged"

echo ""
echo "=== Step 7: Startup interfaces ==="
sudo config interface startup Ethernet272
sudo config interface startup Ethernet513

echo ""
echo "=== Step 8: Save configuration ==="
sudo config save -y

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
echo "✓ D1 configuration complete"
ENDSSH

    if [ $? -eq 0 ]; then
        print_info "D1 configured successfully"
    else
        print_warn "D1 configuration completed with warnings"
    fi
    echo ""
}

################################################################################
# Configure D2 (TX Traffic Generator)
################################################################################

configure_d2() {
    print_header "Configuring D2 (TX Traffic Generator) - 192.168.100.140"

    print_step "Configuring D2 for L2 switching..."

    sshpass -p "$D2_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D2_USER}@${D2_IP} << 'ENDSSH'
#!/bin/bash

echo "=== Step 1: Shutdown interface ==="
sudo config interface shutdown Ethernet64

echo ""
echo "=== Step 2: Remove existing IP configuration ==="
sudo config interface ip remove Ethernet64 10.1.1.1/24 2>/dev/null || true

echo ""
echo "=== Step 3: Remove from CONFIG_DB INTERFACE table ==="
sudo sonic-db-cli CONFIG_DB DEL "INTERFACE|Ethernet64" 2>/dev/null || true
sudo sonic-db-cli CONFIG_DB DEL "INTERFACE|Ethernet64|10.1.1.1/24" 2>/dev/null || true

echo ""
echo "=== Step 4: Delete VLAN 100 if it exists ==="
sudo config vlan del 100 2>/dev/null || true

echo ""
echo "=== Step 5: Create VLAN 100 ==="
sudo config vlan add 100

echo ""
echo "=== Step 6: Add Ethernet64 to VLAN 100 ==="
sudo sonic-db-cli CONFIG_DB HSET "VLAN_MEMBER|Vlan100|Ethernet64" "tagging_mode" "untagged"

echo ""
echo "=== Step 7: Startup interface ==="
sudo config interface startup Ethernet64

echo ""
echo "=== Step 8: Save configuration ==="
sudo config save -y

echo ""
echo "=== Verification ==="
echo "VLAN Configuration:"
show vlan brief

echo ""
echo "Interface Status:"
show interface status Ethernet64

echo ""
echo "✓ D2 configuration complete"
ENDSSH

    if [ $? -eq 0 ]; then
        print_info "D2 configured successfully"
    else
        print_warn "D2 configuration completed with warnings"
    fi
    echo ""
}

################################################################################
# Configure D3 (RX Traffic Receiver)
################################################################################

configure_d3() {
    print_header "Configuring D3 (RX Traffic Receiver) - 192.168.100.173"

    print_step "Configuring D3 for L2 switching..."

    sshpass -p "$D3_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D3_USER}@${D3_IP} << 'ENDSSH'
#!/bin/bash

echo "=== Step 1: Shutdown interface ==="
sudo config interface shutdown Ethernet513

echo ""
echo "=== Step 2: Remove existing IP configuration ==="
sudo config interface ip remove Ethernet513 10.1.2.2/24 2>/dev/null || true

echo ""
echo "=== Step 3: Remove from CONFIG_DB INTERFACE table ==="
sudo sonic-db-cli CONFIG_DB DEL "INTERFACE|Ethernet513" 2>/dev/null || true
sudo sonic-db-cli CONFIG_DB DEL "INTERFACE|Ethernet513|10.1.2.2/24" 2>/dev/null || true

echo ""
echo "=== Step 4: Delete VLAN 100 if it exists ==="
sudo config vlan del 100 2>/dev/null || true

echo ""
echo "=== Step 5: Create VLAN 100 ==="
sudo config vlan add 100

echo ""
echo "=== Step 6: Add Ethernet513 to VLAN 100 ==="
sudo sonic-db-cli CONFIG_DB HSET "VLAN_MEMBER|Vlan100|Ethernet513" "tagging_mode" "untagged"

echo ""
echo "=== Step 7: Startup interface ==="
sudo config interface startup Ethernet513

echo ""
echo "=== Step 8: Save configuration ==="
sudo config save -y

echo ""
echo "=== Verification ==="
echo "VLAN Configuration:"
show vlan brief

echo ""
echo "Interface Status:"
show interface status Ethernet513

echo ""
echo "✓ D3 configuration complete"
ENDSSH

    if [ $? -eq 0 ]; then
        print_info "D3 configured successfully"
    else
        print_warn "D3 configuration completed with warnings"
    fi
    echo ""
}

################################################################################
# Verify Configuration
################################################################################

verify_configuration() {
    print_header "Verifying Final Configuration"

    print_step "Checking D1 VLAN configuration..."
    echo "D1 VLAN Status:"
    sshpass -p "$D1_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D1_USER}@${D1_IP} "show vlan brief" 2>/dev/null

    echo ""
    print_step "Checking D2 VLAN configuration..."
    echo "D2 VLAN Status:"
    sshpass -p "$D2_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D2_USER}@${D2_IP} "show vlan brief" 2>/dev/null

    echo ""
    print_step "Checking D3 VLAN configuration..."
    echo "D3 VLAN Status:"
    sshpass -p "$D3_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D3_USER}@${D3_IP} "show vlan brief" 2>/dev/null

    echo ""
}

################################################################################
# Verify L2 Connectivity
################################################################################

verify_l2_connectivity() {
    print_header "Verifying L2 Connectivity"

    print_step "Checking MAC address learning on D1..."
    echo "D1 MAC Address Table:"
    sshpass -p "$D1_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${D1_USER}@${D1_IP} "show mac" 2>/dev/null

    echo ""
    print_info "L2 connectivity will be verified during test execution"
    echo ""
}

################################################################################
# Print Summary
################################################################################

print_summary() {
    print_header "Configuration Summary"

    cat << EOF
Hardware Testbed L2 ACL Configuration Complete!

Topology:
  ┌──────────────┐                    ┌──────────────┐                    ┌──────────────┐
  │   DUT2       │                    │   DUT1       │                    │   DUT3       │
  │  (TX Host)   │                    │ (ACL Device) │                    │  (RX Host)   │
  │    8023      │                    │    8011      │                    │    8010      │
  │              │                    │              │                    │              │
  │ Ethernet64 ◄─┼────────────────────┼─ Ethernet272 │                    │              │
  │ VLAN 100     │                    │ VLAN 100     │                    │              │
  │              │   (L2 switching)   │ (ACL ingress)│                    │              │
  │              │                    │              │                    │              │
  │              │                    │ Ethernet513──┼────────────────────┼──► Ethernet513
  │              │                    │ VLAN 100     │   (L2 switching)   │ VLAN 100     │
  │              │                    │ (egress)     │                    │              │
  └──────────────┘                    └──────────────┘                    └──────────────┘

VLAN Configuration:
  - VLAN ID: 100
  - D1 Members: Ethernet272 (untagged), Ethernet513 (untagged)
  - D2 Members: Ethernet64 (untagged)
  - D3 Members: Ethernet513 (untagged)

Device Information:
  - D1 (192.168.100.119): Supermicro SSE-T8196 (Broadcom ASIC)
  - D2 (192.168.100.140): Celestica DS3000 (Broadcom ASIC)
  - D3 (192.168.100.173): Supermicro SSE-T8164 (Broadcom ASIC)

Next Steps:
  1. Verify L2 connectivity between devices
  2. Run L2 ACL test suite:
     cd /home/hp_test/Athira/Palc-sonic/sonic-mgmt/spytest
     ./bin/spytest --testbed testbeds/testbed_acl_hw.yaml \\
         tests/switching/l2_acl/test_l2_acl.py \\
         --logs-path ./logs/l2_acl_hw_\$(date +%F_%H%M%S)

  3. Or run manual L2-03 test to verify destination MAC ACL filtering works on hardware

Configuration backups saved to: $BACKUP_DIR

EOF
}

################################################################################
# Main Execution
################################################################################

main() {
    clear
    print_header "Hardware Testbed L2 ACL Pre-Configuration Script"
    echo ""

    # Check for sshpass
    if ! command -v sshpass &> /dev/null; then
        print_error "sshpass is not installed. Please install it first:"
        echo "  sudo apt-get install sshpass"
        exit 1
    fi

    # Verify connectivity
    verify_connectivity

    # Backup current configuration
    backup_configuration

    # Configure all devices
    configure_d1
    configure_d2
    configure_d3

    # Verify configuration
    verify_configuration

    # Verify L2 connectivity
    verify_l2_connectivity

    # Print summary
    print_summary

    print_info "Hardware testbed is ready for L2 ACL testing!"
    echo ""
}

# Run main function
main "$@"
