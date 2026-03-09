# L2 DUT Configuration Guide for L2 ACL Testing

## Overview

This guide provides step-by-step instructions to configure the DUT (Device Under Test) for L2 ACL traffic testing. The DUT must be a SONiC system (Virtual or Hardware) with Port1 and Port2 configured in L2 switchport mode for MAC address-based switching and VLAN forwarding.

**Key Difference from L3 ACL**: L2 ACL tests use **L2 switchport mode** (not routed), **no IP addresses** on DUT ports, and **VLAN-based forwarding** (not IP routing).

## Architecture

```
TX Host (eth0: 10.0.0.1)     RX Host (eth1: 20.0.0.2)
        ↓                           ↑
    [Scapy TX]               [Scapy RX/sniff]
        │                           │
        │ Raw L2 frames              │
        ├─────[ DUT (L2 switch) ]────┤
        │   Port1    ↔    Port2      │
        │ (ACL IN)  (VLANs)          │
        ↓                           ↓
```

## Prerequisites

- SONiC system (VS or HW) with SSH access
- Admin/root credentials
- Port1 and Port2 are physically connected to TX and RX hosts respectively
- Both ports have link status UP (verify with `show interface status`)

## Step 1: Verify Port Status

First, check that Port1 and Port2 are operationally UP:

```bash
DUT# show interface status
NAME                 STATUS  SPEED   MTU
─────────────────────────────────────────
Port1                up      40G    1500
Port2                up      40G    1500
...
```

If ports show DOWN, bring them up:

```bash
DUT# configure terminal
DUT# interface Port1
DUT# no shutdown
DUT# exit
DUT# interface Port2
DUT# no shutdown
DUT# exit
DUT# end
```

## Step 2: Configure Ports in L2 Switchport Mode (Critical)

**IMPORTANT**: Unlike L3 ACL tests, L2 ACL tests require **switchport mode**, NOT routed mode.

```bash
DUT# configure terminal

# Configure Port1 as L2 switchport
DUT(config)# interface Port1
DUT(config-if)# switchport mode access
DUT(config-if)# no shutdown
DUT(config-if)# exit

# Configure Port2 as L2 switchport
DUT(config)# interface Port2
DUT(config-if)# switchport mode access
DUT(config-if)# no shutdown
DUT(config-if)# exit

DUT# end
```

Verify ports are in switchport mode:

```bash
DUT# show interface Port1 | grep -i mode
Switchport Mode: access

DUT# show interface Port2 | grep -i mode
Switchport Mode: access
```

## Step 3: Configure VLANs (Required for L2-06, L2-07 tests)

Create VLANs 10, 100, and 200 required for test cases:

```bash
DUT# configure terminal

# Create VLAN 10
DUT(config)# vlan 10
DUT(config-vlan)# exit

# Create VLAN 100
DUT(config)# vlan 100
DUT(config-vlan)# exit

# Create VLAN 200
DUT(config)# vlan 200
DUT(config-vlan)# exit

DUT# end
```

Verify VLANs were created:

```bash
DUT# show vlan brief
VLAN  Name                             Status    Ports
────────────────────────────────────────────────────────
1     default                          active    Port1, Port2
10    VLAN0010                         active
100   VLAN0100                         active
200   VLAN0200                         active
...
```

## Step 4: Configure Port VLAN Membership

For L2-01 to L2-05 tests (untagged frames), both Port1 and Port2 should be in VLAN 1 (the default):

```bash
DUT# configure terminal

# Assign Port1 to VLAN 1 (native)
DUT(config)# interface Port1
DUT(config-if)# switchport access vlan 1
DUT(config-if)# exit

# Assign Port2 to VLAN 1 (native)
DUT(config)# interface Port2
DUT(config-if)# switchport access vlan 1
DUT(config-if)# exit

DUT# end
```

For L2-06 and L2-07 tests (tagged frames with VLANs 10, 100, 200), configure ports to trunk mode (optional, advanced):

```bash
# Alternative: If using trunk mode for multiple VLANs
DUT# configure terminal
DUT(config)# interface Port1
DUT(config-if)# switchport mode trunk
DUT(config-if)# switchport trunk allowed vlan 1,10,100,200
DUT(config-if)# exit

DUT(config)# interface Port2
DUT(config-if)# switchport mode trunk
DUT(config-if)# switchport trunk allowed vlan 1,10,100,200
DUT(config-if)# exit

DUT# end
```

Verify VLAN membership:

```bash
DUT# show vlan brief
VLAN  Name                             Status    Ports
────────────────────────────────────────────────────────
1     default                          active    Port1, Port2
10    VLAN0010                         active
100   VLAN0100                         active
200   VLAN0200                         active
...
```

## Step 5: Enable MAC Address Learning (Verify Default Behavior)

DUT should have MAC address learning enabled by default. Verify:

```bash
DUT# show mac address-table
Legend: STATIC, DYNAMIC

  No.  Vlan  MacAddress         Port       Type
  ─────────────────────────────────────────────

# (Empty initially; will populate after traffic is sent)
```

Send traffic from TX host and verify MAC is learned:

```bash
# On TX Host (from terminal 1):
sudo python3 << 'EOF'
from scapy.all import *
pkt = Ether(src='00:aa:aa:aa:aa:01', dst='00:bb:bb:bb:bb:02')/IP(src='10.0.0.1', dst='20.0.0.2')/ICMP()
sendp(pkt, iface='eth0', verbose=True, count=3)
EOF

# On DUT (check MAC table after ~1 second):
DUT# show mac address-table
Legend: STATIC, DYNAMIC

  No.  Vlan  MacAddress         Port       Type
  ─────────────────────────────────────────────
  1    1     00:aa:aa:aa:aa:01  Port1      DYNAMIC
  2    1     00:bb:bb:bb:bb:02  Port2      DYNAMIC
```

If MACs are not learned, troubleshoot:
1. Check Port1/Port2 are UP: `show interface status`
2. Check VLAN membership: `show vlan brief`
3. Check for L2 ACLs blocking learning: `show acl`

## Step 6: Verify End-to-End L2 Switching (No ACLs)

Before running ACL tests, verify basic L2 switching by sending a frame from TX to RX:

```bash
# On RX Host (run first, in background):
sudo tcpdump -i eth1 'src 00:aa:aa:aa:aa:01' -c 1

# On TX Host (in another terminal):
sudo python3 << 'EOF'
from scapy.all import *
pkt = Ether(src='00:aa:aa:aa:aa:01', dst='00:bb:bb:bb:bb:02')/IP(src='10.0.0.1', dst='20.0.0.2')/ICMP()
sendp(pkt, iface='eth0', verbose=True)
EOF

# Expected on RX:
# 10:23:45.123456 00:aa:aa:aa:aa:01 > 00:bb:bb:bb:bb:02, ethertype IPv4 (0x0800), ...
```

If RX does not see packets:
- Check DUT Port1/Port2 are UP: `show interface status`
- Check ports are in same VLAN: `show vlan brief`
- Check no ACL rules are applied: `show acl` (should be empty)
- Check MAC table: `show mac address-table`
- Check for dropped packets: `show interface counters | grep -E "Port[12]"`

## Step 7: Configure Spanning Tree Protocol (Optional but Recommended)

If STP is enabled on DUT, ensure ports are in "forwarding" state:

```bash
DUT# show spanning-tree
Spanning tree enabled protocol rstp
Root ID    Priority    32769
           Address     52:54:00:7f:5d:2a
           This bridge is the root
           Hello Time   2 sec  Max Age 20 sec  Forward Delay 15 sec

Bridge ID  Priority    32769  (priority 32768 sys-id-ext 1)
           Address     52:54:00:7f:5d:2a
           Hello Time   2 sec  Max Age 20 sec  Forward Delay 15 sec

Interface        Role    State      Cost      Prio.Nbr Type
─────────────────────────────────────────────────────────────
Port1            Desg    Forwarding 20000     128.1    P2p,Edge
Port2            Desg    Forwarding 20000     128.2    P2p,Edge
```

If ports show "Blocking" state, wait for STP convergence (typically 30 seconds) or disable STP:

```bash
DUT# configure terminal
DUT(config)# no spanning-tree mode
DUT# end
```

## Step 8: Save Configuration

Save the DUT configuration to persist after reboot:

```bash
DUT# write memory
Building configuration...
[OK]
```

## Baseline Configuration Summary

After completing these steps, your DUT should have:

| Parameter | Value | Verify Command |
|-----------|-------|-----------------|
| Port1 Status | UP, Switchport mode | `show interface Port1 \| grep -E "Status\|Switchport"` |
| Port2 Status | UP, Switchport mode | `show interface Port2 \| grep -E "Status\|Switchport"` |
| Port1 VLAN | VLAN 1 (access) | `show interface Port1 switchport` |
| Port2 VLAN | VLAN 1 (access) | `show interface Port2 switchport` |
| VLANs 10/100/200 | Created | `show vlan brief` |
| MAC Learning | Enabled | `show mac address-table` (after traffic) |
| L2 Switching | Working | tcpdump confirms frames reach RX |
| No ACLs | Applied | `show acl` returns empty |

## Port Naming Notes

The above commands assume ports are named `Port1` and `Port2`. However, SONiC uses various port naming conventions:

- **Native names** (e.g., `Ethernet0`, `Ethernet4`): Physical port names from ASIC
- **Alias names** (e.g., `etp1`, `Eth1/1`): User-defined friendly names
- **Management port**: `Ethernet-Mgmt0` (management network, NOT for data traffic)

To check actual port names on your DUT:

```bash
DUT# show interface status | head -20
NAME              STATUS  SPEED      MTU
─────────────────────────────────────────────
Ethernet0         up      40G       1500
Ethernet4         up      40G       1500
Ethernet-Mgmt0    up      1G        1500
...
```

If ports are named differently (e.g., `Ethernet0`, `Ethernet4`), substitute these names in the configuration above.

## Test Case Configuration (Per-Test L2 ACL Rules)

Each L2 ACL test case requires specific L2 ACL rules to be configured on the DUT. Refer to individual test case documentation in `acl-l2.md` for L2 ACL rule configuration.

Example for L2-02 (Deny source MAC DE:AD:00:00:00:01):

```bash
DUT# configure terminal
DUT# ip access-list L2-02-BLOCK-MAC
DUT(acl)# 10 deny mac-address host DE:AD:00:00:00:01 any
DUT(acl)# 20 permit mac-address any any
DUT(acl)# exit

DUT# interface Port1
DUT# ip access-group L2-02-BLOCK-MAC in
DUT# end
```

After each test, remove the L2 ACL:

```bash
DUT# configure terminal
DUT# interface Port1
DUT# no ip access-group L2-02-BLOCK-MAC in
DUT# end
```

## Troubleshooting

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Port status DOWN | `show interface status` shows DOWN | `configure terminal` → `interface PortX` → `no shutdown` → `end` |
| Port not in switchport mode | `show interface PortX switchport` shows "No" | Configure: `interface PortX` → `switchport mode access` → `end` |
| VLANs missing | `show vlan brief` doesn't show 10/100/200 | Create VLANs: `vlan 10`, `vlan 100`, `vlan 200` in config mode |
| RX Host sees 0 packets | All tests fail immediately | Check DUT port status and VLAN membership |
| MAC not learned | `show mac address-table` is empty after traffic | Verify ports are UP and in same VLAN; check for ACL drop rules |
| ACL rules not taking effect | Packets still pass after ACL config | Verify ACL is applied to Port1 ingress: `show interface Port1 \| grep -i acl` |
| MTU mismatch | Packets truncated or dropped | Set same MTU on all devices: `ip link set eth0 mtu 1500` on hosts |
| STP blocking ports | Ports show "Blocking" state | Wait 30 seconds for convergence or `no spanning-tree mode` to disable |

## Advanced Configuration (Optional)

### Enable Port Mirroring (for packet capture)

```bash
DUT# mirror session mirror1
DUT(mirror)# source interface Port1
DUT(mirror)# destination interface Port3  # Or Cpu interface
DUT(mirror)# end
```

Then capture mirrored traffic with tcpdump on destination port.

### Monitor L2 ACL Statistics

```bash
DUT# show access-list
DUT# show acl table
DUT# show acl counters
```

### Enable Detailed VLAN Debugging

```bash
DUT# debug vlan
DUT# debug bridge
```

Then check `show system logs` for VLAN switching decisions.

