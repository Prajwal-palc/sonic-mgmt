# Test Plan: ECMP6 - BGP-Learned Prefixes with Multipath

## Overview

### Test Objective
Validate Equal-Cost Multi-Path (ECMP) routing functionality for BGP-learned prefixes with multipath configuration enabled. This test ensures that routes learned via multiple BGP peers (both iBGP and eBGP) with equal attributes are installed as ECMP entries and traffic is distributed equally across all available paths.

### Test Scope
- BGP neighbor establishment (iBGP and eBGP)
- BGP multipath configuration (maximum-paths)
- Route learning from multiple peers with equal attributes
- ECMP route installation in RIB and FIB
- Traffic load balancing across ECMP paths
- Convergence behavior on peer shutdown
- Traffic rerouting and recovery

### Topology
```
        Peer1 (eBGP)
            |
            | AS 65001
            |
    Peer2 --+-- DUT (AS 65000)
   (iBGP)   |
            |
            | AS 65002
            |
        Peer3 (eBGP)
```

**Node Configuration:**
- **DUT**: Primary device under test (AS 65000)
- **Peer1**: eBGP neighbor (AS 65001) - advertises same prefixes
- **Peer2**: iBGP neighbor (AS 65000) - advertises same prefixes
- **Peer3**: eBGP neighbor (AS 65002) - advertises same prefixes
- **Total Nodes**: 4 (1 DUT + 3 BGP peers)

### CLI Type
- **Type**: klish
- **Access Method**: sonic-cli

### Key Validation Commands
```bash
sonic-cli
show ip bgp
show ip bgp summary
show ip route
show ip route bgp
exit
```

---

## Test Environment Setup

### Prerequisites
1. All devices must be running SONiC with BGP support
2. IP connectivity established between DUT and all peers
3. Loopback interfaces configured on all devices
4. BGP routing process must be enabled on all devices

### Initial Configuration

#### DUT Configuration (AS 65000)
```bash
sonic-cli
configure terminal

# Configure router BGP
router bgp 65000
  router-id 10.0.0.1

  # Enable BGP multipath (critical for ECMP)
  maximum-paths 3
  maximum-paths ibgp 3

  # eBGP neighbor to Peer1 (AS 65001)
  neighbor 192.168.1.2 remote-as 65001
  neighbor 192.168.1.2 description eBGP-Peer1

  # iBGP neighbor to Peer2 (AS 65000)
  neighbor 10.1.1.2 remote-as 65000
  neighbor 10.1.1.2 description iBGP-Peer2
  neighbor 10.1.1.2 update-source Loopback0

  # eBGP neighbor to Peer3 (AS 65002)
  neighbor 192.168.3.2 remote-as 65002
  neighbor 192.168.3.2 description eBGP-Peer3

  # Address family configuration
  address-family ipv4 unicast
    neighbor 192.168.1.2 activate
    neighbor 10.1.1.2 activate
    neighbor 192.168.3.2 activate
  exit-address-family
exit

# Configure interfaces
interface Ethernet0
  ip address 192.168.1.1/24
  no shutdown
exit

interface Ethernet4
  ip address 10.1.1.1/24
  no shutdown
exit

interface Ethernet8
  ip address 192.168.3.1/24
  no shutdown
exit

interface Loopback0
  ip address 10.0.0.1/32
exit

exit
exit
```

#### Peer1 Configuration (AS 65001 - eBGP)
```bash
sonic-cli
configure terminal

router bgp 65001
  router-id 10.0.1.1
  neighbor 192.168.1.1 remote-as 65000

  address-family ipv4 unicast
    # Advertise test prefixes
    network 172.16.0.0/24
    network 172.16.1.0/24
    network 172.16.2.0/24
    neighbor 192.168.1.1 activate
  exit-address-family
exit

interface Ethernet0
  ip address 192.168.1.2/24
  no shutdown
exit

exit
exit
```

#### Peer2 Configuration (AS 65000 - iBGP)
```bash
sonic-cli
configure terminal

router bgp 65000
  router-id 10.0.2.1
  neighbor 10.1.1.1 remote-as 65000
  neighbor 10.1.1.1 update-source Loopback0

  address-family ipv4 unicast
    # Advertise same test prefixes with equal attributes
    network 172.16.0.0/24
    network 172.16.1.0/24
    network 172.16.2.0/24
    neighbor 10.1.1.1 activate
    neighbor 10.1.1.1 next-hop-self
  exit-address-family
exit

interface Ethernet0
  ip address 10.1.1.2/24
  no shutdown
exit

interface Loopback0
  ip address 10.0.2.1/32
exit

exit
exit
```

#### Peer3 Configuration (AS 65002 - eBGP)
```bash
sonic-cli
configure terminal

router bgp 65002
  router-id 10.0.3.1
  neighbor 192.168.3.1 remote-as 65000

  address-family ipv4 unicast
    # Advertise same test prefixes
    network 172.16.0.0/24
    network 172.16.1.0/24
    network 172.16.2.0/24
    neighbor 192.168.3.1 activate
  exit-address-family
exit

interface Ethernet0
  ip address 192.168.3.2/24
  no shutdown
exit

exit
exit
```

---

## Test Cases

### Test Case 6.1: BGP Neighbor Establishment and Route Learning

**Test ID**: ECMP6.1
**Priority**: P0
**Description**: Verify BGP neighbor establishment with all three peers (2 eBGP + 1 iBGP) and route learning

#### Test Steps

1. **Verify BGP process is running on DUT**
   ```bash
   sonic-cli
   show ip bgp summary
   ```

   **Expected Output**:
   ```
   BGP router identifier 10.0.0.1, local AS number 65000

   Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd
   10.1.1.2        4 65000      15      18        0    0    0 00:10:25            3
   192.168.1.2     4 65001      12      15        0    0    0 00:10:22            3
   192.168.3.2     4 65002      13      16        0    0    0 00:10:20            3

   Total number of neighbors 3
   ```

2. **Verify all neighbors are in Established state**
   ```bash
   show ip bgp neighbors
   ```

   **Expected Output**:
   - All three neighbors show "BGP state = Established"
   - Peer1 (192.168.1.2): remote AS 65001, state Established
   - Peer2 (10.1.1.2): remote AS 65000 (iBGP), state Established
   - Peer3 (192.168.3.2): remote AS 65002, state Established

3. **Verify routes are learned from all three peers**
   ```bash
   show ip bgp
   ```

   **Expected Output**:
   ```
   BGP table version is 6, local router ID is 10.0.0.1
   Status codes: s suppressed, d damped, h history, * valid, > best, = multipath,
                 i internal, r RIB-failure, S Stale, R Removed
   Origin codes: i - IGP, e - EGP, ? - incomplete

      Network          Next Hop            Metric LocPrf Weight Path
   *= 172.16.0.0/24    192.168.1.2              0             0 65001 i
   *=                  192.168.3.2              0             0 65002 i
   *>                  10.1.1.2                 0    100      0 i
   *= 172.16.1.0/24    192.168.1.2              0             0 65001 i
   *=                  192.168.3.2              0             0 65002 i
   *>                  10.1.1.2                 0    100      0 i
   *= 172.16.2.0/24    192.168.1.2              0             0 65001 i
   *=                  192.168.3.2              0             0 65002 i
   *>                  10.1.1.2                 0    100      0 i
   ```

4. **Verify multipath configuration**
   ```bash
   show running-config router bgp
   ```

   **Expected Output**:
   ```
   router bgp 65000
    maximum-paths 3
    maximum-paths ibgp 3
   ```

#### Pass Criteria
- All 3 BGP neighbors reach Established state
- Each neighbor advertises 3 prefixes (172.16.0.0/24, 172.16.1.0/24, 172.16.2.0/24)
- BGP table shows multiple paths (marked with '=') for each prefix
- Multipath is configured with value of 3 or higher

---

### Test Case 6.2: ECMP Route Installation with 3-Way Multipath

**Test ID**: ECMP6.2
**Priority**: P0
**Description**: Verify that BGP routes with equal attributes are installed as ECMP entries in the routing table

#### Test Steps

1. **Check BGP routing table for multipath entries**
   ```bash
   sonic-cli
   show ip bgp 172.16.0.0/24
   ```

   **Expected Output**:
   ```
   BGP routing table entry for 172.16.0.0/24
   Paths: (3 available, best #1, table default)
     Multipath: eBGP iBGP
     65001
       192.168.1.2 from 192.168.1.2 (10.0.1.1)
         Origin IGP, metric 0, valid, external, multipath
         Last update: 00:15:30 ago
     65002
       192.168.3.2 from 192.168.3.2 (10.0.3.1)
         Origin IGP, metric 0, valid, external, multipath
         Last update: 00:15:28 ago
     Local
       10.1.1.2 from 10.1.1.2 (10.0.2.1)
         Origin IGP, metric 0, locpref 100, valid, internal, multipath, best
         Last update: 00:15:32 ago
   ```

2. **Verify ECMP entries in IP routing table**
   ```bash
   show ip route 172.16.0.0/24
   ```

   **Expected Output**:
   ```
   Codes: K - kernel route, C - connected, S - static, R - RIP,
          O - OSPF, I - IS-IS, B - BGP, E - EIGRP, N - NHRP,
          T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
          F - PBR, f - OpenFabric,
          > - selected route, * - FIB route, q - queued route, r - rejected route

   B>* 172.16.0.0/24 [20/0] via 192.168.1.2, Ethernet0, 00:15:30
     *                      via 10.1.1.2, Ethernet4, 00:15:32
     *                      via 192.168.3.2, Ethernet8, 00:15:28
   ```

3. **Verify all three prefixes are installed as ECMP**
   ```bash
   show ip route bgp
   ```

   **Expected Output**:
   ```
   B>* 172.16.0.0/24 [20/0] via 192.168.1.2, Ethernet0, 00:16:10
     *                      via 10.1.1.2, Ethernet4, 00:16:12
     *                      via 192.168.3.2, Ethernet8, 00:16:08
   B>* 172.16.1.0/24 [20/0] via 192.168.1.2, Ethernet0, 00:16:10
     *                      via 10.1.1.2, Ethernet4, 00:16:12
     *                      via 192.168.3.2, Ethernet8, 00:16:08
   B>* 172.16.2.0/24 [20/0] via 192.168.1.2, Ethernet0, 00:16:10
     *                      via 10.1.1.2, Ethernet4, 00:16:12
     *                      via 192.168.3.2, Ethernet8, 00:16:08
   ```

4. **Count total next-hops installed**
   ```bash
   show ip route bgp | grep "172.16"
   ```

   **Expected**: 3 prefixes × 3 next-hops each = 9 total next-hop entries

#### Pass Criteria
- Each BGP prefix (172.16.0.0/24, 172.16.1.0/24, 172.16.2.0/24) shows exactly 3 paths in BGP table
- All paths are marked as "multipath" in BGP table
- IP routing table shows all 3 next-hops for each prefix with '*' (installed in FIB)
- Total of 9 next-hop entries across 3 ECMP routes

---

### Test Case 6.3: Traffic Load Balancing Verification

**Test ID**: ECMP6.3
**Priority**: P0
**Description**: Verify traffic is distributed equally across all three ECMP paths

#### Test Steps

1. **Generate traffic using Scapy from traffic generator**

   **Traffic Generation Script** (run on external traffic generator):
   ```python
   #!/usr/bin/env python3
   from scapy.all import *
   import time

   def generate_ecmp_traffic(dst_prefix="172.16.0.0/24", count=3000, rate=100):
       """
       Generate traffic to destination prefix with varying source IPs
       to trigger ECMP hashing across multiple paths.

       Args:
           dst_prefix: Destination network (default: 172.16.0.0/24)
           count: Number of packets to send (default: 3000)
           rate: Packets per second (default: 100)
       """
       dst_net = ipaddress.IPv4Network(dst_prefix)
       dst_ip = str(dst_net.network_address + 10)  # Use 172.16.0.10

       packets = []
       for i in range(count):
           # Vary source IP to create different flows for ECMP hashing
           src_ip = f"200.0.{(i // 256) % 256}.{i % 256}"
           src_port = 1024 + (i % 10000)
           dst_port = 80

           pkt = Ether()/IP(src=src_ip, dst=dst_ip)/TCP(sport=src_port, dport=dst_port)/"TestPayload"
           packets.append(pkt)

       print(f"Sending {count} packets to {dst_ip}")
       sendp(packets, iface="eth0", inter=1.0/rate, verbose=False)
       print("Traffic generation complete")

   if __name__ == "__main__":
       # Generate 3000 packets at 100 pps (30 seconds duration)
       generate_ecmp_traffic(dst_prefix="172.16.0.0/24", count=3000, rate=100)
   ```

2. **Monitor interface counters before traffic**
   ```bash
   sonic-cli
   show interface counters
   exit
   ```

   Record baseline TX packet counts on:
   - Ethernet0 (to Peer1)
   - Ethernet4 (to Peer2)
   - Ethernet8 (to Peer3)

3. **Start traffic generation** (run Scapy script above)

4. **Monitor interface counters during traffic**
   ```bash
   sonic-cli
   show interface counters | grep -E "Ethernet0|Ethernet4|Ethernet8"
   ```

   **Expected Output** (example):
   ```
   Ethernet0      3.2 GB   2.1 GB     45032850    51023400    1020    980        0        0
   Ethernet4      3.1 GB   2.0 GB     44898720    50887250    1005    995        0        0
   Ethernet8      3.2 GB   2.1 GB     45156980    51145680    1030    970        0        0
   ```

5. **Calculate traffic distribution**

   Collect TX packet delta on each interface:
   - Interface Ethernet0: ~1000 packets
   - Interface Ethernet4: ~1000 packets
   - Interface Ethernet8: ~1000 packets

   **Expected**: Approximately equal distribution (±10% variance acceptable)

6. **Verify no packet drops**
   ```bash
   show interface counters errors
   ```

   **Expected**: Zero errors and drops on all ECMP interfaces

#### Pass Criteria
- Traffic is distributed across all 3 ECMP paths
- Each path carries approximately 33% of total traffic (±10% variance)
- No packet drops or errors observed
- Total packets sent = sum of packets across all three egress interfaces

---

### Test Case 6.4: BGP Peer Shutdown and Convergence

**Test ID**: ECMP6.4
**Priority**: P0
**Description**: Verify fast convergence when one BGP peer is shutdown and traffic reroutes to remaining ECMP paths

#### Test Steps

1. **Establish baseline with all peers up**
   ```bash
   sonic-cli
   show ip bgp summary
   show ip route 172.16.0.0/24
   ```

   **Expected**: 3 neighbors Established, 3 next-hops for each route

2. **Start continuous traffic** (using Scapy script from Test 6.3)

3. **Record timestamp and shutdown Peer1 (eBGP)**

   On Peer1 device:
   ```bash
   sonic-cli
   configure terminal
   router bgp 65001
     neighbor 192.168.1.1 shutdown
   exit
   exit
   exit
   ```

   **Timestamp**: T0

4. **Monitor BGP neighbor status on DUT**
   ```bash
   sonic-cli
   show ip bgp summary
   ```

   **Expected Output**:
   ```
   Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd
   10.1.1.2        4 65000      45      48        0    0    0 00:35:25            3
   192.168.1.2     4 65001      42      45        0    0    0 00:00:05        Idle
   192.168.3.2     4 65002      43      46        0    0    0 00:35:20            3
   ```

5. **Verify route convergence**
   ```bash
   show ip route 172.16.0.0/24
   ```

   **Expected Output**:
   ```
   B>* 172.16.0.0/24 [20/0] via 10.1.1.2, Ethernet4, 00:00:08
     *                      via 192.168.3.2, Ethernet8, 00:00:08
   ```

   **Timestamp**: T1

   **Convergence Time** = T1 - T0 (should be < 5 seconds for BGP hold timer)

6. **Verify traffic continues on remaining paths**
   ```bash
   show interface counters | grep -E "Ethernet4|Ethernet8"
   ```

   **Expected**: Traffic now split between Ethernet4 and Ethernet8 (~50% each)

7. **Verify no traffic on failed path**
   ```bash
   show interface counters | grep Ethernet0
   ```

   **Expected**: TX counter stopped incrementing after T0

8. **Check for packet loss during convergence**

   From traffic generator, monitor packets sent vs received.

   **Expected**: Minimal packet loss (< 1% during convergence window)

#### Pass Criteria
- BGP neighbor transitions to Idle/Connect state within hold timer period
- Routes converge to 2-way ECMP within 5 seconds
- Traffic automatically reroutes to remaining 2 paths
- Packet loss during convergence is less than 1%
- No traffic sent on failed Ethernet0 interface after convergence

---

### Test Case 6.5: BGP Peer Restoration and Traffic Recovery

**Test ID**: ECMP6.5
**Priority**: P0
**Description**: Verify that ECMP is fully restored when the shutdown BGP peer is brought back up

#### Test Steps

1. **Verify current state (Peer1 is shutdown from Test 6.4)**
   ```bash
   sonic-cli
   show ip bgp summary
   ```

   **Expected**: 2 neighbors Established (Peer2, Peer3), 1 neighbor Idle (Peer1)

2. **Verify 2-way ECMP is active**
   ```bash
   show ip route 172.16.0.0/24
   ```

   **Expected Output**:
   ```
   B>* 172.16.0.0/24 [20/0] via 10.1.1.2, Ethernet4, 00:05:30
     *                      via 192.168.3.2, Ethernet8, 00:05:30
   ```

3. **Re-enable Peer1 BGP neighbor**

   On Peer1 device:
   ```bash
   sonic-cli
   configure terminal
   router bgp 65001
     no neighbor 192.168.1.1 shutdown
   exit
   exit
   exit
   ```

   **Timestamp**: T0

4. **Monitor BGP neighbor re-establishment**
   ```bash
   sonic-cli
   show ip bgp summary
   ```

   **Expected Output** (after convergence):
   ```
   Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd
   10.1.1.2        4 65000      55      58        0    0    0 00:45:25            3
   192.168.1.2     4 65001      48      51        0    0    0 00:00:15            3
   192.168.3.2     4 65002      53      56        0    0    0 00:45:20            3
   ```

   **Timestamp**: T1

   **Re-establishment Time** = T1 - T0

5. **Verify 3-way ECMP is restored**
   ```bash
   show ip route 172.16.0.0/24
   ```

   **Expected Output**:
   ```
   B>* 172.16.0.0/24 [20/0] via 192.168.1.2, Ethernet0, 00:00:18
     *                      via 10.1.1.2, Ethernet4, 00:00:18
     *                      via 192.168.3.2, Ethernet8, 00:00:18
   ```

6. **Verify all three paths are in BGP multipath**
   ```bash
   show ip bgp 172.16.0.0/24
   ```

   **Expected**: All 3 paths marked as "multipath"

7. **Verify traffic is redistributed across all three paths**
   ```bash
   show interface counters | grep -E "Ethernet0|Ethernet4|Ethernet8"
   ```

   **Expected**: All three interfaces show increasing TX counters with approximately equal distribution

8. **Confirm no errors during restoration**
   ```bash
   show interface counters errors
   ```

   **Expected**: Zero errors on all interfaces

#### Pass Criteria
- BGP neighbor successfully re-establishes within 30 seconds
- All 3 routes are re-learned and installed as ECMP
- Routing table shows 3-way ECMP restored for all prefixes
- Traffic distribution returns to ~33% per path
- No packet drops or errors during restoration

---

### Test Case 6.6: iBGP Multipath Validation

**Test ID**: ECMP6.6
**Priority**: P1
**Description**: Verify iBGP multipath functionality when multiple iBGP peers advertise the same prefix

#### Test Steps

1. **Modify configuration to add second iBGP peer**

   On DUT:
   ```bash
   sonic-cli
   configure terminal
   router bgp 65000
     neighbor 10.1.2.2 remote-as 65000
     neighbor 10.1.2.2 description iBGP-Peer4
     neighbor 10.1.2.2 update-source Loopback0

     address-family ipv4 unicast
       neighbor 10.1.2.2 activate
     exit-address-family
   exit
   exit
   exit
   ```

2. **Configure Peer4 as second iBGP neighbor**

   On new Peer4 device:
   ```bash
   sonic-cli
   configure terminal
   router bgp 65000
     router-id 10.0.4.1
     neighbor 10.1.1.1 remote-as 65000
     neighbor 10.1.1.1 update-source Loopback0

     address-family ipv4 unicast
       network 172.16.10.0/24
       neighbor 10.1.1.1 activate
       neighbor 10.1.1.1 next-hop-self
     exit-address-family
   exit
   exit
   exit
   ```

3. **Also configure Peer2 to advertise same prefix**

   On Peer2:
   ```bash
   sonic-cli
   configure terminal
   router bgp 65000
     address-family ipv4 unicast
       network 172.16.10.0/24
     exit-address-family
   exit
   exit
   exit
   ```

4. **Verify iBGP multipath is configured**
   ```bash
   sonic-cli
   show running-config router bgp
   ```

   **Expected**:
   ```
   router bgp 65000
    maximum-paths ibgp 3
   ```

5. **Check BGP table for iBGP multipath**
   ```bash
   show ip bgp 172.16.10.0/24
   ```

   **Expected Output**:
   ```
   BGP routing table entry for 172.16.10.0/24
   Paths: (2 available, best #1, table default)
     Multipath: iBGP
     Local
       10.1.1.2 from 10.1.1.2 (10.0.2.1)
         Origin IGP, metric 0, locpref 100, valid, internal, multipath, best
     Local
       10.1.2.2 from 10.1.2.2 (10.0.4.1)
         Origin IGP, metric 0, locpref 100, valid, internal, multipath
   ```

6. **Verify iBGP ECMP in routing table**
   ```bash
   show ip route 172.16.10.0/24
   ```

   **Expected Output**:
   ```
   B>* 172.16.10.0/24 [200/0] via 10.1.1.2, Ethernet4, 00:02:15
     *                        via 10.1.2.2, Ethernet12, 00:02:15
   ```

7. **Verify both iBGP paths are used**

   Generate traffic to 172.16.10.0/24 and monitor counters:
   ```bash
   show interface counters | grep -E "Ethernet4|Ethernet12"
   ```

   **Expected**: Both interfaces show traffic distribution

#### Pass Criteria
- iBGP multipath configuration is set to 3 or higher
- Multiple iBGP peers can advertise same prefix
- BGP table shows both iBGP paths as "multipath"
- Routing table installs both iBGP next-hops as ECMP
- Traffic is distributed across iBGP multipath

---

### Test Case 6.7: eBGP Multipath with AS Path Prepending

**Test ID**: ECMP6.7
**Priority**: P1
**Description**: Verify that AS path prepending prevents ECMP installation (unequal AS path length)

#### Test Steps

1. **Configure AS path prepending on Peer1**

   On Peer1:
   ```bash
   sonic-cli
   configure terminal
   route-map PREPEND_AS permit 10
     set as-path prepend 65001 65001
   exit

   router bgp 65001
     address-family ipv4 unicast
       neighbor 192.168.1.1 route-map PREPEND_AS out
     exit-address-family
   exit
   exit
   exit
   ```

2. **Clear BGP session to apply route-map**
   ```bash
   sonic-cli
   clear ip bgp 192.168.1.2 soft out
   exit
   ```

3. **Verify AS path difference in BGP table**

   On DUT:
   ```bash
   sonic-cli
   show ip bgp 172.16.0.0/24
   ```

   **Expected Output**:
   ```
   BGP routing table entry for 172.16.0.0/24
   Paths: (3 available, best #1, table default)
     65001 65001 65001
       192.168.1.2 from 192.168.1.2 (10.0.1.1)
         Origin IGP, metric 0, valid, external
         Last update: 00:00:30 ago
     65002
       192.168.3.2 from 192.168.3.2 (10.0.3.1)
         Origin IGP, metric 0, valid, external, multipath
         Last update: 00:50:28 ago
     Local
       10.1.1.2 from 10.1.1.2 (10.0.2.1)
         Origin IGP, metric 0, locpref 100, valid, internal, multipath, best
         Last update: 00:50:32 ago
   ```

   Note: Peer1 path (AS 65001 prepended) is NOT marked as multipath

4. **Verify routing table uses only equal-length AS paths**
   ```bash
   show ip route 172.16.0.0/24
   ```

   **Expected Output**:
   ```
   B>* 172.16.0.0/24 [20/0] via 10.1.1.2, Ethernet4, 00:01:00
     *                      via 192.168.3.2, Ethernet8, 00:01:00
   ```

   Note: Only 2 next-hops (Peer2 and Peer3) installed; Peer1 excluded due to longer AS path

5. **Remove AS path prepending**

   On Peer1:
   ```bash
   sonic-cli
   configure terminal
   router bgp 65001
     address-family ipv4 unicast
       no neighbor 192.168.1.1 route-map PREPEND_AS out
     exit-address-family
   exit
   exit
   exit
   ```

6. **Verify 3-way ECMP is restored**
   ```bash
   sonic-cli
   show ip route 172.16.0.0/24
   exit
   ```

   **Expected**: All 3 next-hops restored

#### Pass Criteria
- AS path prepending creates unequal AS path lengths
- BGP paths with longer AS path are NOT included in ECMP
- Only paths with equal AS path length participate in ECMP
- Removing prepending restores all paths to ECMP
- ECMP behavior strictly follows BGP best path selection rules

---

## Expected Outputs Summary

### Key Validation Points

1. **BGP Neighbor Status**
   - All neighbors in Established state
   - Prefix count matches advertised routes
   - No flapping or instability

2. **BGP Multipath Configuration**
   - `maximum-paths` set to 3 or higher for eBGP
   - `maximum-paths ibgp` set to 3 or higher for iBGP
   - Configuration persists across reloads

3. **ECMP Route Installation**
   - Multiple next-hops visible in `show ip route`
   - All next-hops marked with '*' (installed in FIB)
   - Correct number of ECMP paths based on configuration

4. **Load Balancing**
   - Traffic distributed approximately equally across all paths
   - Variance within acceptable range (±10%)
   - No single path overloaded

5. **Convergence Metrics**
   - Peer failure detected within hold timer (default: 180s, recommended: 30s)
   - Routes converge to remaining paths within 5 seconds
   - Packet loss during convergence < 1%
   - Restoration completes within 30 seconds

6. **Route Attributes**
   - Equal AS path length for eBGP multipath
   - Equal local preference, MED, origin for all paths
   - iBGP requires same IGP metric to next-hop (optional)

---

## Traffic Generation Details

### Scapy Traffic Script for Load Balancing

```python
#!/usr/bin/env python3
"""
BGP ECMP Load Balancing Traffic Generator
Generates varied traffic flows to test ECMP distribution
"""

from scapy.all import *
import time
import argparse
import ipaddress

def generate_varied_flows(dst_network, num_flows=1000, pps=100, duration=30):
    """
    Generate traffic with varied 5-tuple to exercise ECMP hashing.

    Args:
        dst_network: Destination prefix (e.g., "172.16.0.0/24")
        num_flows: Number of unique flows to generate
        pps: Packets per second per flow
        duration: Duration in seconds
    """
    dst_net = ipaddress.IPv4Network(dst_network)
    dst_base = int(dst_net.network_address)

    # Create flow list
    flows = []
    for i in range(num_flows):
        flow = {
            'src_ip': f"200.{(i >> 16) & 0xFF}.{(i >> 8) & 0xFF}.{i & 0xFF}",
            'dst_ip': str(ipaddress.IPv4Address(dst_base + (i % 10) + 10)),
            'src_port': 10000 + (i % 50000),
            'dst_port': 80 + (i % 100),
            'proto': 'TCP' if i % 2 == 0 else 'UDP'
        }
        flows.append(flow)

    print(f"Generating {num_flows} flows to {dst_network}")
    print(f"Rate: {pps} pps per flow, Duration: {duration}s")

    start_time = time.time()
    packets_sent = 0

    while (time.time() - start_time) < duration:
        for flow in flows:
            if flow['proto'] == 'TCP':
                pkt = Ether()/IP(src=flow['src_ip'], dst=flow['dst_ip'])/\
                      TCP(sport=flow['src_port'], dport=flow['dst_port'])/\
                      Raw(load="X" * 100)
            else:
                pkt = Ether()/IP(src=flow['src_ip'], dst=flow['dst_ip'])/\
                      UDP(sport=flow['src_port'], dport=flow['dst_port'])/\
                      Raw(load="X" * 100)

            sendp(pkt, iface="eth0", verbose=False)
            packets_sent += 1

            if packets_sent % (pps * num_flows) == 0:
                time.sleep(1)  # Maintain rate

    print(f"Traffic generation complete. Sent {packets_sent} packets")
    return packets_sent

def monitor_traffic_distribution(interfaces, duration=10):
    """
    Monitor traffic distribution across ECMP interfaces.

    Args:
        interfaces: List of interface names (e.g., ["Ethernet0", "Ethernet4", "Ethernet8"])
        duration: Monitoring duration in seconds
    """
    print(f"Monitoring traffic distribution for {duration} seconds...")

    # This would integrate with SONiC CLI or SNMP to collect counters
    # Placeholder implementation
    baseline = {}
    for intf in interfaces:
        baseline[intf] = get_interface_counter(intf)  # Would call actual CLI

    time.sleep(duration)

    results = {}
    for intf in interfaces:
        current = get_interface_counter(intf)
        results[intf] = current - baseline[intf]

    # Calculate distribution
    total = sum(results.values())
    print(f"\nTraffic Distribution:")
    for intf, count in results.items():
        percentage = (count / total * 100) if total > 0 else 0
        print(f"  {intf}: {count} packets ({percentage:.2f}%)")

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BGP ECMP Traffic Generator")
    parser.add_argument("--dst-network", default="172.16.0.0/24", help="Destination network")
    parser.add_argument("--flows", type=int, default=1000, help="Number of flows")
    parser.add_argument("--pps", type=int, default=100, help="Packets per second")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds")

    args = parser.parse_args()

    generate_varied_flows(
        dst_network=args.dst_network,
        num_flows=args.flows,
        pps=args.pps,
        duration=args.duration
    )
```

---

## Troubleshooting Guide

### Issue 1: BGP Neighbors Not Establishing

**Symptoms**:
- Neighbor stuck in Idle, Connect, or Active state
- No routes learned from peers

**Diagnosis**:
```bash
sonic-cli
show ip bgp summary
show ip bgp neighbors <neighbor-ip>
exit
```

**Common Causes**:
1. IP connectivity issue between DUT and peer
2. BGP port (TCP 179) blocked by firewall
3. Incorrect AS number configuration
4. Authentication mismatch (if MD5 configured)

**Resolution**:
```bash
# Verify IP connectivity
ping <neighbor-ip>

# Check BGP configuration
sonic-cli
show running-config router bgp

# Verify correct AS numbers
show ip bgp summary

# Check for errors in BGP log
show logging | grep BGP
exit
```

### Issue 2: Routes Learned but ECMP Not Installed

**Symptoms**:
- BGP table shows multiple paths
- Only one path installed in routing table
- Paths not marked as "multipath"

**Diagnosis**:
```bash
sonic-cli
show ip bgp <prefix>
show ip route <prefix>
show running-config router bgp | grep maximum-paths
exit
```

**Common Causes**:
1. `maximum-paths` not configured or set to 1
2. BGP attributes not equal (AS path, local pref, MED, origin)
3. Different next-hop reachability (IGP metrics differ for iBGP)

**Resolution**:
```bash
sonic-cli
configure terminal
router bgp <as-number>
  maximum-paths 4         # For eBGP multipath
  maximum-paths ibgp 4    # For iBGP multipath
exit
exit
exit
```

For attribute issues, verify:
```bash
sonic-cli
show ip bgp <prefix>
exit
```

Check that all paths have:
- Same AS path length
- Same local preference
- Same MED value
- Same origin code

### Issue 3: Unequal Load Distribution

**Symptoms**:
- ECMP installed correctly
- Traffic not distributed equally across paths
- Some paths carrying significantly more/less traffic

**Diagnosis**:
```bash
sonic-cli
show interface counters | grep -E "Ethernet0|Ethernet4|Ethernet8"
show interface counters rate
exit
```

**Common Causes**:
1. Insufficient flow diversity (few flows, hash to same path)
2. Hash polarization
3. Hardware limitation in load balancing algorithm

**Resolution**:
- Increase number of traffic flows with varied 5-tuple
- Adjust ECMP hash algorithm if supported:
  ```bash
  sonic-cli
  configure terminal
  # Configure ECMP hash (platform-specific)
  exit
  exit
  ```
- Verify traffic has sufficient entropy in hash fields (src IP, dst IP, src port, dst port, protocol)

### Issue 4: Slow Convergence on Peer Failure

**Symptoms**:
- Convergence takes longer than expected (> 10 seconds)
- Packet loss exceeds acceptable threshold
- Routes slow to withdraw

**Diagnosis**:
```bash
sonic-cli
show ip bgp neighbors <neighbor-ip>
exit
```

Check hold timer and keepalive values.

**Common Causes**:
1. Long BGP hold timer (default: 180s)
2. BFD not enabled for fast failure detection
3. Slow route processing

**Resolution**:
```bash
sonic-cli
configure terminal
router bgp <as-number>
  # Reduce timers (keepalive 10s, hold 30s)
  neighbor <neighbor-ip> timers 10 30

  # Enable BFD for sub-second detection
  neighbor <neighbor-ip> bfd
exit
exit
exit
```

### Issue 5: iBGP Multipath Not Working

**Symptoms**:
- iBGP routes learned from multiple peers
- Only one iBGP route installed
- Routes not marked as multipath

**Diagnosis**:
```bash
sonic-cli
show ip bgp <prefix>
show running-config router bgp | grep "maximum-paths ibgp"
exit
```

**Common Causes**:
1. `maximum-paths ibgp` not configured
2. Different IGP metrics to iBGP next-hops
3. Different local preference values

**Resolution**:
```bash
sonic-cli
configure terminal
router bgp <as-number>
  maximum-paths ibgp 4
exit
exit
exit
```

For iBGP multipath, ensure:
- All iBGP peers have equal local preference
- IGP metrics to next-hops are equal (if IGP multipath required)
- Route reflector configuration does not affect path selection

### Issue 6: AS Path Prepending Prevents ECMP

**Symptoms**:
- Some BGP paths not included in ECMP
- AS path length varies between paths
- Fewer next-hops than expected

**Diagnosis**:
```bash
sonic-cli
show ip bgp <prefix>
exit
```

Look for different AS path lengths in output.

**Common Causes**:
1. AS path prepending applied via route-map
2. Paths through different AS topologies

**Resolution**:
- Verify no AS path prepending is configured:
  ```bash
  sonic-cli
  show running-config route-map
  exit
  ```
- Ensure all eBGP peers have same AS path length
- Remove unnecessary AS path prepending if ECMP desired

---

## Performance Benchmarks

### Expected Metrics

| Metric | Target | Acceptable Range | Critical Threshold |
|--------|--------|------------------|-------------------|
| BGP neighbor establishment time | < 10s | 5s - 15s | > 30s |
| Route installation time (per prefix) | < 1s | < 2s | > 5s |
| ECMP convergence on peer failure | < 5s | < 10s | > 30s |
| Load balancing variance | ±5% | ±10% | > ±20% |
| Packet loss during convergence | < 0.5% | < 1% | > 5% |
| Peer restoration time | < 30s | < 60s | > 120s |
| CPU utilization (steady state) | < 10% | < 20% | > 50% |
| Memory utilization | < 30% | < 50% | > 80% |

### Scalability Notes

- This test uses 3 prefixes for functional validation
- Production deployments may have thousands of BGP routes
- For scale testing:
  - Increase number of advertised prefixes
  - Monitor control plane performance
  - Validate RIB/FIB capacity
  - Test BGP convergence with large route tables

---

## Configuration Backup and Restore

### Save Configuration

```bash
sonic-cli
copy running-config startup-config
exit

# Backup to external location
sudo cp /etc/sonic/config_db.json /tmp/config_backup_ecmp6_$(date +%Y%m%d).json
```

### Restore Configuration

```bash
# Restore from backup
sudo cp /tmp/config_backup_ecmp6_20250117.json /etc/sonic/config_db.json

# Reload configuration
sudo config reload -y
```

---

## References

### SONiC BGP Documentation
- BGP Configuration Guide: https://github.com/sonic-net/SONiC/wiki/BGP-Configuration
- FRR BGP Documentation: http://docs.frrouting.org/en/latest/bgp.html

### BGP ECMP RFCs
- RFC 4271: Border Gateway Protocol 4
- RFC 4456: BGP Route Reflection
- RFC 7911: Advertisement of Multiple Paths in BGP

### Related Test Plans
- ECMP4: OSPF ECMP Route Install & Forwarding
- ECMP5: OSPF ECMP Scalability Testing

---

## Appendix

### Complete DUT Configuration Example

```bash
sonic-cli
configure terminal

# BGP Configuration
router bgp 65000
  router-id 10.0.0.1

  # ECMP Configuration
  maximum-paths 4
  maximum-paths ibgp 4

  # Neighbor Configuration
  neighbor 192.168.1.2 remote-as 65001
  neighbor 192.168.1.2 description eBGP-Peer1-AS65001
  neighbor 192.168.1.2 timers 10 30

  neighbor 10.1.1.2 remote-as 65000
  neighbor 10.1.1.2 description iBGP-Peer2
  neighbor 10.1.1.2 update-source Loopback0
  neighbor 10.1.1.2 timers 10 30

  neighbor 192.168.3.2 remote-as 65002
  neighbor 192.168.3.2 description eBGP-Peer3-AS65002
  neighbor 192.168.3.2 timers 10 30

  # Address Family
  address-family ipv4 unicast
    neighbor 192.168.1.2 activate
    neighbor 10.1.1.2 activate
    neighbor 10.1.1.2 next-hop-self
    neighbor 192.168.3.2 activate

    # Optional: Advertise local networks
    network 10.0.0.0/24
  exit-address-family
exit

# Interface Configuration
interface Ethernet0
  description Link-to-Peer1
  mtu 9100
  ip address 192.168.1.1/24
  no shutdown
exit

interface Ethernet4
  description Link-to-Peer2
  mtu 9100
  ip address 10.1.1.1/24
  no shutdown
exit

interface Ethernet8
  description Link-to-Peer3
  mtu 9100
  ip address 192.168.3.1/24
  no shutdown
exit

interface Loopback0
  ip address 10.0.0.1/32
exit

exit
exit

# Save configuration
copy running-config startup-config
```

### Test Execution Checklist

- [ ] Verify physical connectivity between all devices
- [ ] Configure IP addresses on all interfaces
- [ ] Enable BGP on DUT and all peers
- [ ] Configure correct AS numbers (iBGP and eBGP)
- [ ] Enable BGP multipath (maximum-paths)
- [ ] Verify BGP neighbor establishment
- [ ] Confirm route learning from all peers
- [ ] Validate ECMP installation in routing table
- [ ] Generate traffic using Scapy script
- [ ] Monitor load distribution across paths
- [ ] Test peer shutdown scenarios
- [ ] Measure convergence time
- [ ] Test peer restoration
- [ ] Validate iBGP multipath (if applicable)
- [ ] Test AS path attribute variations
- [ ] Document all results
- [ ] Save configuration backups

---

**Document Version**: 1.0
**Last Updated**: 2025-01-17
**Test Plan Status**: Ready for Implementation
