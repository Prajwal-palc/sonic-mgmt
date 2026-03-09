# DUT Configuration Guide for L3 ACL Testing

## Overview

This guide provides step-by-step instructions to configure the DUT (Device Under Test) for L3 ACL traffic testing. The DUT must be a SONiC system (Virtual or Hardware) with Port1 and Port2 configured for L3 routing between the 10.0.0.0/24 and 20.0.0.0/24 subnets.

## Architecture

```
TX Host (10.0.0.1)     RX Host (20.0.0.2)
        ↓                      ↑
      eth0                   eth1
        │                      │
        ├─────[ DUT ]──────────┤
        │   Port1   Port2      │
        │  (ACL IN)            │
        ↓                      ↓
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

## Step 2: Configure L3 Addresses on DUT Ports

Port1 and Port2 must be configured with IP addresses in the same subnets as TX and RX hosts, respectively.

```bash
DUT# configure terminal
DUT# interface Port1
DUT# ip address 10.0.0.254/24
DUT# exit

DUT# interface Port2
DUT# ip address 20.0.0.254/24
DUT# exit

DUT# end
```

Verify configuration:

```bash
DUT# show ip interface brief
Interface      IP Address        Status
─────────────────────────────────────────
Port1          10.0.0.254/24     up/up
Port2          20.0.0.254/24     up/up
...
```

## Step 3: Enable L3 Routing (if needed)

For VS, ensure L3 routing is enabled:

```bash
DUT# configure terminal
DUT# (config) ip forwarding
DUT# end
```

Verify routing is enabled:

```bash
DUT# show system ip forwarding
IP Forwarding: Enabled
```

## Step 4: Verify Routing Between Subnets

Check that both subnets are in the routing table:

```bash
DUT# show ip route
Destination         Next Hop        Interface
─────────────────────────────────────────────
10.0.0.0/24         0.0.0.0         Port1
20.0.0.0/24         0.0.0.0         Port2
```

If routes are missing, they should be added automatically after configuring IPs. If not, add static routes:

```bash
DUT# configure terminal
DUT# ip route 10.0.0.0/24 Port1
DUT# ip route 20.0.0.0/24 Port2
DUT# end
```

## Step 5: Verify End-to-End Connectivity (No ACLs)

Before running ACL tests, verify basic connectivity by sending a ping from TX to DUT Port1:

```bash
# On TX Host:
$ ip addr show eth0
inet 10.0.0.1/24 scope global eth0

$ ping 10.0.0.254 -c 3
PING 10.0.0.254 (10.0.0.254) 56(84) bytes of data.
64 bytes from 10.0.0.254: icmp_seq=1 ttl=64 time=1.23 ms
```

Also verify TX→DUT→RX path (forward direction):

```bash
# On TX Host:
$ python3 -c "
from scapy.all import *
pkt = Ether(src='00:aa:aa:aa:aa:01', dst='00:bb:bb:bb:bb:02')/IP(src='10.0.0.1', dst='20.0.0.2')/ICMP()
sendp(pkt, iface='eth0', verbose=True)
"

# On RX Host (run in parallel):
$ sudo tcpdump -i eth1 'src 10.0.0.1' -c 1
tcpdump: listening on eth1, link-type EN10MB (Ethernet), snapshot length 65535 bytes
10:23:45.123456 IP 10.0.0.1 > 20.0.0.2: ICMP echo request, id 0, seq 0, length 8
1 packet captured
```

If RX does not see packets:
- Check DUT routing: `show ip route 10.0.0.0/24` and `show ip route 20.0.0.0/24`
- Verify Port1/Port2 are UP: `show interface status Port1 Port2`
- Check no ACL rules are applied: `show acl` (should be empty)
- Check for dropped packets: `show interface counters | grep -E "Port[12]"`

## Step 6: Save Configuration

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
| Port1 Status | UP | `show interface status Port1` |
| Port2 Status | UP | `show interface status Port2` |
| Port1 IP | 10.0.0.254/24 | `show ip interface brief` |
| Port2 IP | 20.0.0.254/24 | `show ip interface brief` |
| Route 10.0.0.0/24 | Direct via Port1 | `show ip route 10.0.0.0/24` |
| Route 20.0.0.0/24 | Direct via Port2 | `show ip route 20.0.0.0/24` |
| End-to-end connectivity | Working | `tcpdump` on RX captures TX packets |
| No ACLs applied | Yes | `show acl` returns empty |

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

## Test Case Configuration (Per-Test ACL Rules)

Each ACL test case requires specific ACL rules to be configured on the DUT. Refer to the individual test case documentation in `acl-l3.md` for ACL rule configuration.

Example for L3-01 (Deny source IP 10.0.0.99):

```bash
DUT# configure terminal
DUT# ip access-list L3-01-BLOCK-SOURCE
DUT(acl)# 10 deny ip host 10.0.0.99 any
DUT(acl)# 20 permit ip any any
DUT(acl)# exit
DUT# interface Port1
DUT# ip access-group L3-01-BLOCK-SOURCE in
DUT# end
```

After each test, remove the ACL:

```bash
DUT# configure terminal
DUT# interface Port1
DUT# no ip access-group L3-01-BLOCK-SOURCE in
DUT# end
```

## Troubleshooting

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Port status DOWN | `show interface status` shows DOWN | `configure terminal` → `interface PortX` → `no shutdown` → `end` |
| No routes visible | `show ip route` doesn't show 10.0.0.0/24 or 20.0.0.0/24 | Verify IP addresses are configured (`show ip interface brief`); add static routes if needed |
| RX Host sees 0 packets | All tests fail immediately | Check DUT routing; verify eth0/eth1 are configured on hosts; check cables |
| ACL rules not taking effect | Packets still pass after ACL config | Verify ACL is applied to Port1 ingress: `show interface Port1 \| grep -i acl` |
| MTU mismatch | Packets truncated or dropped | Set same MTU on all devices: `ip link set eth0 mtu 1500` on hosts; configure on DUT |

## Advanced Configuration (Optional)

### Enable VLAN Tagging (if testing VLAN ACLs)

```bash
DUT# configure terminal
DUT# interface Port1
DUT# switchport mode trunk
DUT# switchport trunk allowed vlan 1,10,100
DUT# exit
```

### Enable Port Mirroring (for packet capture)

```bash
DUT# mirror session mirror1
DUT(mirror)# source interface Port1
DUT(mirror)# destination interface Port3  # Or Cpu interface
DUT(mirror)# end
```

Then capture traffic on mirrored port with tcpdump.

### Monitor ACL Statistics

```bash
DUT# show acl table
DUT# show acl rule TABLENAME
DUT# show acl counters TABLENAME
```

