# Host Environment Setup Guide for L2 ACL Testing

## Overview

This guide provides step-by-step instructions to prepare the TX and RX hosts (external Linux systems) for L2 ACL traffic generation using Scapy. These hosts must be connected to the DUT's Port1 and Port2 respectively.

**Note**: Host network configuration for L2 ACL testing is identical to L3 ACL testing. See `/tests/routing/l3_acl/docs/host_setup.md` for the complete guide. This document highlights L2-specific differences.

## Quick Setup (5 minutes)

```bash
# 1. Install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-dev net-tools ethtool iputils-ping tcpdump
sudo pip3 install scapy --break-system-packages

# 2. Disable firewall
sudo ufw disable
sudo iptables -P INPUT ACCEPT
sudo iptables -P FORWARD ACCEPT
sudo iptables -P OUTPUT ACCEPT

# 3. Configure interfaces
cd /path/to/tests/switching/l2_acl/traffic/
sudo python3 setup_ports.py

# 4. Verify
sudo python3 setup_ports.py --verify
```

## Architecture

```
┌─────────────────┐        ┌─────────────────┐
│   TX Host       │        │   RX Host       │
│ (Linux, Scapy)  │        │ (Linux, Scapy)  │
│  eth0 (10.0.0.1)│        │  eth1 (20.0.0.2)│
│ MAC: AA:AA:...01│        │ MAC: BB:BB:...02│
└────────┬────────┘        └────────┬────────┘
         │                          │
         └──────────[ DUT (L2) ]────┘
              Port1    Port2
         (Switchport mode)
```

## Prerequisites

- Ubuntu 20.04 LTS or later
- Two separate Linux systems (or VMs)
- Python 3.8+
- Root/sudo access
- Network interfaces eth0 (TX) and eth1 (RX)

## Key Differences from L3 ACL Testing

| Aspect | L2 ACL | L3 ACL |
|--------|--------|--------|
| **IP Configuration** | Hosts get IPs (for management only) | Hosts get IPs (for L3 routing) |
| **Scapy Frames** | L2-only frames (MAC, EtherType, VLAN) | L2 + L3 frames (IP, TCP, UDP) |
| **DUT Port Mode** | Switchport (L2) | Routed (L3) |
| **VLAN Tags** | Native + tagged frames tested | Not tested |
| **MAC Learning** | Critical (DUT learns MAC addresses) | Not critical (IP-based) |

## Step-by-Step Configuration

### Step 1: System Preparation

Follow the same steps as in `/tests/routing/l3_acl/docs/host_setup.md` Step 1:
- Update system packages
- Install required tools (Python, net-tools, tcpdump)
- Check network interfaces

### Step 2: Disable Firewall

Follow the same steps as in `/tests/routing/l3_acl/docs/host_setup.md` Step 2:
- Disable UFW
- Reset iptables rules
- Disable SELinux (if applicable)

### Step 3: Install Scapy

Follow the same steps as in `/tests/routing/l3_acl/docs/host_setup.md` Step 3:
- Install via pip
- Verify version ≥ 2.4.4

### Step 4: Configure TX Host Network Interface (eth0)

Same as L3 ACL (refer to `/tests/routing/l3_acl/docs/host_setup.md` Step 4):

```bash
cd /path/to/tests/switching/l2_acl/traffic/
sudo python3 setup_ports.py
```

### Step 5: Configure RX Host Network Interface (eth1)

Same as L3 ACL (refer to `/tests/routing/l3_acl/docs/host_setup.md` Step 5):

```bash
# Verify
sudo python3 setup_ports.py --verify
# Expected: Both TX and RX show PASS
```

### Step 6: Grant Raw Socket Permissions

Same as L3 ACL (refer to `/tests/routing/l3_acl/docs/host_setup.md` Step 6):

```bash
# Option 1: Use sudo
sudo python3 l2_acl_traffic.py --list

# Option 2: Grant capability (permanent)
sudo setcap cap_net_raw=ep /usr/bin/python3
```

### Step 7: Verify Host Configuration

Run verification script:

```bash
sudo python3 setup_ports.py --verify

# Expected output:
# [PASS] TX  (eth0  )  exists=True  link=True  ip=True  mac=True
# [PASS] RX  (eth1  )  exists=True  link=True  ip=True  mac=True
```

### Step 8: Verify DUT Connectivity

**L2-specific check**: Verify DUT Port1 and Port2 are in same VLAN and switchport mode.

```bash
# On TX Host
ping 10.0.0.254 -c 3
# Expected: 3 packets received (or 0 if DUT has no IP; that's OK for L2 tests)

# Test L2 switching without IP (tcpdump-based verification)
sudo tcpdump -i eth1 'src 00:aa:aa:aa:aa:01' -c 1 &
sleep 1
sudo python3 << 'EOF'
from scapy.all import *
pkt = Ether(src='00:aa:aa:aa:aa:01', dst='00:bb:bb:bb:bb:02')/IP(src='10.0.0.1', dst='20.0.0.2')/ICMP()
sendp(pkt, iface='eth0', verbose=True)
EOF
# Expected: tcpdump captures frame from TX MAC

# If no frame captured, troubleshoot:
# 1. Check DUT Port1/Port2 are UP: show interface status
# 2. Check ports are in same VLAN: show vlan brief
# 3. Check no ACL is blocking: show acl (should be empty)
# 4. Check MAC learning: show mac address-table (should see TX MAC after traffic)
```

## L2-Specific Test Considerations

### Native vs Tagged VLAN Frames

**L2-01 to L2-05 tests** (Native VLAN, no tags):
```python
# Untagged frames - no Dot1Q layer
pkt = Ether(src='00:aa:aa:aa:aa:01', dst='00:bb:bb:bb:bb:02')/IP()/ICMP()
```

**L2-06 to L2-07 tests** (Tagged VLAN):
```python
# Tagged frames - include Dot1Q layer
pkt = Ether()/Dot1Q(vlan=10)/IP()/ICMP()
```

When running L2-06/L2-07 tests, ensure:
- DUT has VLANs 10, 100, 200 created
- DUT Port1/Port2 are in trunk mode or configured to accept these VLANs

### MAC Address Learning

After sending frames from TX, verify DUT learns the MAC address:

```bash
# On DUT:
show mac address-table
# Expected: TX MAC should appear in table after frame is sent from TX host
```

If DUT doesn't learn MAC:
- Check Port1 is UP and in switchport mode
- Check Port1 is in correct VLAN
- Check no L2 ACL is blocking traffic
- Check `show interface counters Port1` shows increasing RX count

### Broadcast and Multicast Frames

**L2-04 test** (Broadcast MAC):
```python
pkt = Ether(src='00:aa:aa:aa:aa:01', dst='FF:FF:FF:FF:FF:FF')/ARP()
```

**L2-N02 test** (Multicast MAC):
```python
pkt = Ether(src='00:aa:aa:aa:aa:01', dst='01:00:5E:00:00:01')/IP()
```

DUT behavior for broadcast/multicast may vary:
- Broadcast: May be dropped by default (security) or flooded
- Multicast: Usually flooded or dropped depending on configuration

## Troubleshooting L2-Specific Issues

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| "Interface eth0/eth1 not found" | Wrong interface names | Run `ip link show` to find actual names |
| RX sees 0 packets (even untagged frames) | DUT ports not in same VLAN | Check `show vlan brief` on DUT |
| RX sees 0 packets | DUT ports in routed mode, not switchport | Change DUT to switchport mode: `interface PortX` → `switchport mode access` |
| L2-06/L2-07 tests fail | VLANs 100/200 don't exist | Create VLANs on DUT: `vlan 100`, `vlan 200` |
| All tests fail | Frame switching not working | Check Port1/Port2 status and VLAN membership |
| MAC not learned on DUT | Port not in switchport mode | Verify `show interface PortX` shows "Switchport Mode: access" |
| Broadcast frame causes errors | Broadcast handling undefined | Check DUT ACL policy for broadcast (may drop by default) |

## Running L2 ACL Tests

### List Available Tests

```bash
sudo python3 l2_acl_traffic.py --list
```

### Run All Functional Tests

```bash
sudo python3 l2_acl_traffic.py
```

### Run Specific Tests

```bash
# Single test
sudo python3 l2_acl_traffic.py --tc L2-01

# Multiple tests
sudo python3 l2_acl_traffic.py --tc L2-01,L2-04,L2-06

# With custom parameters
sudo python3 l2_acl_traffic.py --tc L2-06 --timeout 10 --packet-count 20
```

### Run Full L2+L3 Suite

```bash
sudo python3 acl_test_runner.py --suite l2
# Or for both:
sudo python3 acl_test_runner.py
```

## Persistent Configuration

To make host interface configuration survive reboots, follow the same steps as in `/tests/routing/l3_acl/docs/host_setup.md` Step 9:
- Create netplan configuration, OR
- Create /etc/rc.local script

## Advanced: Network Isolation (Optional)

For L2 ACL testing, it may be useful to isolate test traffic from management traffic:

```bash
# Create separate bridge for test traffic (advanced)
sudo ip link add br-test type bridge
sudo ip link set eth0 master br-test
sudo ip link set eth1 master br-test
sudo ip link set br-test up

# Note: This bridges eth0/eth1 at the OS level (optional for advanced setups)
```

**Usually not necessary** - Scapy can handle both management and test traffic on same interfaces.

## Complete Checklist

```bash
# 1. System setup
[ ] sudo apt update && sudo apt upgrade -y
[ ] sudo apt install -y python3-pip python3-dev net-tools ethtool tcpdump

# 2. Scapy installation
[ ] sudo pip3 install scapy --break-system-packages
[ ] python3 -c "from scapy.all import *; print('OK')"

# 3. Firewall disabled
[ ] sudo ufw disable
[ ] sudo iptables -P INPUT ACCEPT; sudo iptables -P FORWARD ACCEPT

# 4. Interfaces configured
[ ] cd tests/switching/l2_acl/traffic/ && sudo python3 setup_ports.py
[ ] sudo python3 setup_ports.py --verify  # Both PASS

# 5. DUT connectivity verified
[ ] Ping 10.0.0.254 (or check tcpdump for frame arrival)
[ ] show mac address-table on DUT shows TX MAC after traffic

# 6. Ready for testing
[ ] sudo python3 l2_acl_traffic.py --tc L2-01

# ✅ All checks complete - ready for L2 ACL testing!
```

## For More Information

- **L2 DUT Setup**: See `l2_dut_setup.md`
- **L2 Test Plan**: See `acl-l2.md`
- **L2 Architecture Review**: See `review.md`
- **L3 Host Setup** (for reference): See `/tests/routing/l3_acl/docs/host_setup.md`

