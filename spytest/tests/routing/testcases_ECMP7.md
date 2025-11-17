# Test Cases - Large-scale BGP ECMP

## Test Case ID: TC_ECMP_2.4.4

### Test Case Name
Large-scale BGP ECMP Validation

### Test Objective
Validate that the system can handle a large number of BGP ECMP routes with multipath enabled without performance degradation or instability. Test includes enabling BGP multipath, advertising many identical prefixes from multiple BGP peers with equal AS-PATH length, verifying ECMP next-hop installation, monitoring CPU and memory utilization under steady state and stress conditions, and testing peer flap convergence. Ensure that all ECMP routes are correctly installed, system resources remain stable, and smooth recovery occurs after BGP session flaps.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_5node_bgp_ecmp.yaml`
- **Topology**: 5 nodes (1 DUT + 4 BGP peers)
- **Device Under Test (DUT)**: Primary router under test
- **BGP Peers**: Peer1, Peer2, Peer3, Peer4
- **Test Network**: eBGP peering

### Topology Diagram

```
           [Peer1]          [Peer2]          [Peer3]          [Peer4]
         AS 65001         AS 65002         AS 65003         AS 65004
     Each advertises      Each advertises  Each advertises  Each advertises
     1000+ prefixes      1000+ prefixes   1000+ prefixes   1000+ prefixes
     (same prefixes)     (same prefixes)  (same prefixes)  (same prefixes)
            |                  |                 |                 |
            | eBGP             | eBGP            | eBGP            | eBGP
            | Ethernet0        | Ethernet4       | Ethernet8       | Ethernet12
            |                  |                 |                 |
            +------------------+-----------------+-----------------+
                                       |
                                  +----+----+
                                  |   DUT   |
                                  | AS 64512|
                                  | (Router)|
                                  +---------+

Result: 4-way ECMP for each of 1000+ destination prefixes
BGP multipath enabled to utilize all equal-cost paths
```

### Interface Configuration

**DUT Interfaces**:
- **Ethernet0**: Connected to Peer1 (10.0.0.0/31, IP: 10.0.0.1)
- **Ethernet4**: Connected to Peer2 (10.0.4.0/31, IP: 10.0.4.1)
- **Ethernet8**: Connected to Peer3 (10.0.8.0/31, IP: 10.0.8.1)
- **Ethernet12**: Connected to Peer4 (10.0.12.0/31, IP: 10.0.12.1)
- **Loopback0**: 1.1.1.1/32 (Router ID)

**DUT BGP Configuration**:
- **ASN**: 64512
- **Router ID**: 1.1.1.1
- **BGP Multipath**: Enabled (maximum-paths 4)
- **Peer Type**: eBGP (External BGP)

**BGP Peer Configuration**:
- **Peer1**: AS 65001, Neighbor 10.0.0.0
- **Peer2**: AS 65002, Neighbor 10.0.4.0
- **Peer3**: AS 65003, Neighbor 10.0.8.0
- **Peer4**: AS 65004, Neighbor 10.0.12.0

**Scale Parameters**:
- **Prefixes per peer**: 1000 prefixes (configurable: 100, 500, 1000, 2000)
- **Total unique prefixes**: 1000 (all peers advertise same prefixes)
- **ECMP paths per prefix**: 4 (one via each peer with equal AS-PATH length)
- **Total ECMP entries**: 1000 routes × 4 next-hops = 4000 entries
- **Prefix range**: 192.168.0.0/24 through 192.171.231.0/24

### Prerequisites
1. All 5 devices accessible via SSH
2. SONiC OS installed on all devices
3. Access to sonic-cli (klish) on all devices
4. BGP routing protocol support enabled
5. Sufficient memory for routing table (minimum 2GB recommended)
6. Sufficient CPU capacity for route processing
7. All interfaces physically connected
8. Route table capacity: Support for 1000+ routes

---

## Test Procedure

### Step 1: Initial Setup - Configure IP Addresses on DUT
**Objective**: Configure IP addresses on all DUT interfaces

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure Ethernet0 (to Peer1)
interface Ethernet0
ip address 10.0.0.1/31
no shutdown
exit

# Configure Ethernet4 (to Peer2)
interface Ethernet4
ip address 10.0.4.1/31
no shutdown
exit

# Configure Ethernet8 (to Peer3)
interface Ethernet8
ip address 10.0.8.1/31
no shutdown
exit

# Configure Ethernet12 (to Peer4)
interface Ethernet12
ip address 10.0.12.1/31
no shutdown
exit

# Configure Loopback0 (Router ID)
interface Loopback0
ip address 1.1.1.1/32
exit

# Exit configuration mode
exit
```

**Expected Result**:
- All 4 peer-facing interfaces configured
- All interfaces operational (up/up)
- Loopback configured for router ID

---

### Step 2: Configure BGP on DUT with Multipath Enabled
**Objective**: Enable BGP routing protocol on DUT with multipath support

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure BGP process
router bgp 64512
bgp router-id 1.1.1.1

# Enable BGP multipath (critical for ECMP)
maximum-paths 4

# Configure BGP neighbors (Peer1)
neighbor 10.0.0.0 remote-as 65001
neighbor 10.0.0.0 description Peer1
neighbor 10.0.0.0 activate

# Configure BGP neighbors (Peer2)
neighbor 10.0.4.0 remote-as 65002
neighbor 10.0.4.0 description Peer2
neighbor 10.0.4.0 activate

# Configure BGP neighbors (Peer3)
neighbor 10.0.8.0 remote-as 65003
neighbor 10.0.8.0 description Peer3
neighbor 10.0.8.0 activate

# Configure BGP neighbors (Peer4)
neighbor 10.0.12.0 remote-as 65004
neighbor 10.0.12.0 description Peer4
neighbor 10.0.12.0 activate

exit

# Exit configuration mode
exit
```

**Expected Result**:
- BGP process enabled with ASN 64512
- BGP multipath enabled (maximum-paths 4)
- Four eBGP neighbors configured
- Router ID set to 1.1.1.1

---

### Step 3: Configure BGP Peers to Advertise Scale Prefixes
**Objective**: Configure each BGP peer to advertise 1000 identical prefixes

**Configuration Strategy**:
Each peer will advertise the same set of prefixes (192.168.0.0/24 - 192.171.231.0/24) with equal AS-PATH length (single AS prepend), resulting in 4-way ECMP for each prefix.

**Example Configuration (Peer1 - AS 65001)**:
```bash
# On Peer1
sonic-cli
configure terminal

# Configure interface to DUT
interface Ethernet0
ip address 10.0.0.0/31
no shutdown
exit

# Configure Loopback
interface Loopback0
ip address 2.2.2.2/32
exit

# Configure BGP
router bgp 65001
bgp router-id 2.2.2.2

# Configure neighbor to DUT
neighbor 10.0.0.1 remote-as 64512
neighbor 10.0.0.1 description DUT
neighbor 10.0.0.1 activate

# Advertise prefixes via network statements or redistribution
# Option 1: Network statements (for smaller scale)
# network 192.168.0.0/24
# network 192.168.1.0/24
# ... (repeat for 1000 prefixes)

# Option 2: Redistribute static routes (recommended for scale)
redistribute static

exit
exit
```

**Create Static Routes for Advertisement (Peer1)**:
```bash
# Create 1000 static routes pointing to Null0
configure terminal

# Static routes for advertisement (range: 192.168.0.0/24 - 192.171.231.0/24)
ip route 192.168.0.0/24 Null0
ip route 192.168.1.0/24 Null0
ip route 192.168.2.0/24 Null0
# ... (repeat for 1000 prefixes)
ip route 192.171.231.0/24 Null0

exit
```

**Automated Script for Scale Prefix Configuration**:
```python
#!/usr/bin/env python3
"""
Generate BGP scale prefix configuration
Creates 1000 static routes for BGP redistribution
"""

def generate_bgp_scale_routes(start_octet=168, count=1000):
    """Generate static route commands for BGP advertisement"""
    routes = []
    current_octet = start_octet
    subnet = 0

    for i in range(count):
        route = f"ip route 192.{current_octet}.{subnet}.0/24 Null0"
        routes.append(route)

        subnet += 1
        if subnet >= 256:
            subnet = 0
            current_octet += 1

    return routes

# Generate configuration
print("configure terminal")
routes = generate_bgp_scale_routes(start_octet=168, count=1000)
for route in routes:
    print(route)
print("exit")
```

**Repeat Configuration on All 4 Peers**:
- **Peer2 (AS 65002)**: Configure with neighbor 10.0.4.1, advertise same 1000 prefixes
- **Peer3 (AS 65003)**: Configure with neighbor 10.0.8.1, advertise same 1000 prefixes
- **Peer4 (AS 65004)**: Configure with neighbor 10.0.12.1, advertise same 1000 prefixes

**Expected Result**:
- Each peer advertises 1000 identical prefixes
- All peers advertising same prefixes with equal AS-PATH length (1 AS hop)
- DUT receives 1000 prefixes via 4 different paths
- BGP multipath enabled to install all 4 paths

---

### Step 4: Verify BGP Neighbor Sessions
**Objective**: Verify all 4 BGP neighbors are in ESTABLISHED state

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Check BGP summary
show ip bgp summary

# Check specific neighbor details
show ip bgp neighbors 10.0.0.0
show ip bgp neighbors 10.0.4.0
show ip bgp neighbors 10.0.8.0
show ip bgp neighbors 10.0.12.0
```

**Expected Result**:
- Four BGP neighbors visible
- All neighbors in "ESTABLISHED" state
- Each neighbor advertising 1000+ prefixes
- Total prefixes received: 4000 (1000 unique prefixes × 4 peers)

**Sample Output**:
```
BGP router identifier 1.1.1.1, local AS number 64512
BGP table version is 5001

Neighbor        V    AS    MsgRcvd  MsgSent  TblVer  InQ  OutQ  Up/Down   State/PfxRcd
10.0.0.0        4  65001      1523     1520    5001    0     0  00:12:34  1000
10.0.4.0        4  65002      1521     1518    5001    0     0  00:12:31  1000
10.0.8.0        4  65003      1519     1516    5001    0     0  00:12:28  1000
10.0.12.0       4  65004      1517     1514    5001    0     0  00:12:25  1000

Total number of neighbors 4
Total number of Established sessions 4
```

**Validation Points**:
1. Neighbor count = 4
2. All neighbors in ESTABLISHED state
3. Each neighbor advertising 1000 prefixes
4. No neighbors in Idle, Connect, or Active state

---

### Step 5: Baseline - Verify BGP ECMP Route Installation
**Objective**: Verify that all 1000 BGP ECMP routes are installed with 4 next-hops each

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Show BGP routes
show ip bgp

# Count BGP routes
show ip bgp | count

# Show installed routes in routing table
show ip route bgp

# Count installed BGP routes
show ip route bgp | count

# Show sample route to verify ECMP
show ip bgp 192.168.0.0/24
show ip route 192.168.0.0/24

# Show route summary
show ip route summary
```

**Expected Result**:
- 1000 unique BGP prefixes in BGP table
- 4000 total paths (1000 prefixes × 4 paths each)
- All 1000 routes installed in routing table with ECMP
- Each route has 4 next-hops (multipath)

**Sample ECMP Route Output**:
```
# show ip bgp 192.168.0.0/24
BGP routing table entry for 192.168.0.0/24
Paths: (4 available, best #1, table default)
  Multipath: eBGP
  65001
    10.0.0.0 from 10.0.0.0 (2.2.2.2)
      Origin IGP, metric 0, valid, external, multipath, best
  65002
    10.0.4.0 from 10.0.4.0 (3.3.3.3)
      Origin IGP, metric 0, valid, external, multipath
  65003
    10.0.8.0 from 10.0.8.0 (4.4.4.4)
      Origin IGP, metric 0, valid, external, multipath
  65004
    10.0.12.0 from 10.0.12.0 (5.5.5.5)
      Origin IGP, metric 0, valid, external, multipath

# show ip route 192.168.0.0/24
B    192.168.0.0/24 [20/0]
       via 10.0.0.0, Ethernet0, weight 1, 00:05:23
       via 10.0.4.0, Ethernet4, weight 1, 00:05:23
       via 10.0.8.0, Ethernet8, weight 1, 00:05:23
       via 10.0.12.0, Ethernet12, weight 1, 00:05:23
```

**Validation Points**:
1. Route count = 1000 unique prefixes
2. Each route has 4 paths in BGP table
3. Each route has 4 next-hops in routing table (ECMP)
4. All routes show BGP origin (B)
5. Multipath indicator present
6. All next-hops have equal weight

---

### Step 6: Baseline Resource Monitoring - CPU & Memory
**Objective**: Establish baseline CPU and memory utilization with all BGP routes installed

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Show processes (CPU and memory) - PRIMARY VALIDATION COMMAND
show processes

# Show process CPU usage
show processes cpu

# Show process memory usage
show processes memory

# Show system memory
show system memory

# Show system CPU
show system cpu

# Monitor BGP-specific process
show processes | grep bgp
```

**Expected Result**:
- CPU utilization < 30% under steady state
- Memory utilization < 60% of available
- BGP daemon (bgpd) consuming reasonable resources
- No process consuming excessive resources
- Stable resource usage (not increasing over time)

**Sample Output**:
```
# show processes
PID    Name              CPU %    MEM %    VSZ       RSS      Status
------------------------------------------------------------------------
1234   bgpd              6.2      4.5      256000    184320   Running
1235   zebra             2.8      3.1      128000    98304    Running
1236   fpmsyncd          1.5      2.2      98304     73728    Running
1237   orchagent         3.1      4.8      204800    163840   Running
...

System Summary:
CPU Usage:
  User:   12.5%
  System: 6.8%
  Idle:   80.7%

Memory:
  Total: 8192 MB
  Used:  3584 MB (43.8%)
  Free:  4608 MB (56.2%)
  Buffers: 256 MB
  Cached: 1024 MB
```

**Record Baseline Metrics**:
- BGP daemon CPU: _____%
- BGP daemon Memory: _____%
- Zebra daemon CPU: _____%
- Total system CPU: _____%
- Total system Memory: _____%

---

### Step 7: Stress Test - Monitor Resources During BGP Route Processing
**Objective**: Monitor CPU and memory during active BGP route processing and reconvergence

**Procedure**:
1. Start continuous monitoring
2. Trigger route recalculation (clear BGP session)
3. Monitor CPU/memory spike during route re-learning
4. Verify return to baseline

**Commands (Execute on DUT)**:
```bash
# Terminal 1: Continuous monitoring
while true; do
  date
  sonic-cli -c "show processes | grep bgpd"
  sonic-cli -c "show system memory | grep Used"
  sonic-cli -c "show ip bgp summary | grep Total"
  sleep 5
done

# Terminal 2: Trigger BGP reconvergence (soft reset)
sonic-cli
clear ip bgp * soft
exit

# Wait 2 minutes for convergence and monitoring
```

**Expected Result**:
- CPU spike during route re-learning (< 60% spike)
- Memory stable or minimal increase
- Return to baseline within 2 minutes
- All routes re-learned and re-installed
- No process crashes or hangs
- BGP sessions remain ESTABLISHED

**Acceptable Metrics**:
- Peak CPU during reconvergence: < 70%
- Peak memory during reconvergence: < 75%
- Recovery time to baseline: < 120 seconds
- No OOM (Out of Memory) errors
- All 1000 routes re-installed with 4 next-hops

---

### Step 8: Verify ECMP Next-Hop Distribution
**Objective**: Verify exact route count and ECMP next-hop installation

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Count total BGP routes in routing table
show ip route bgp | count

# Sample multiple routes to verify ECMP (4 next-hops each)
show ip route 192.168.0.0/24
show ip route 192.168.100.0/24
show ip route 192.170.50.0/24

# Verify multipath in BGP table
show ip bgp 192.168.0.0/24 | grep -i multipath

# Check BGP multipath configuration
show running-configuration router bgp | grep maximum-paths
```

**Expected Result**:
- Exact count: 1000 routes in routing table
- All routes have 4 next-hops (no partial ECMP)
- BGP multipath enabled (maximum-paths 4 configured)
- All paths marked as "multipath" in BGP table
- Equal weight distribution (weight 1 for all next-hops)

**Validation Script** (to verify all routes have 4 next-hops):
```python
#!/usr/bin/env python3
"""
Verify all BGP routes have correct number of ECMP paths
"""

def verify_bgp_ecmp_routes(route_output, expected_nexthops=4):
    """Parse route output and verify ECMP next-hops"""
    routes_checked = 0
    routes_with_correct_ecmp = 0
    routes_with_incorrect_ecmp = []

    current_route = None
    nexthop_count = 0

    for line in route_output.split('\n'):
        if line.startswith('B '):
            # New BGP route
            if current_route and nexthop_count != expected_nexthops:
                routes_with_incorrect_ecmp.append(
                    (current_route, nexthop_count)
                )

            # Extract prefix
            current_route = line.split()[1]
            nexthop_count = 1  # First next-hop on same line
            routes_checked += 1

        elif 'via' in line and current_route:
            # Additional next-hop for current route
            nexthop_count += 1

    # Check last route
    if current_route:
        if nexthop_count == expected_nexthops:
            routes_with_correct_ecmp += 1
        else:
            routes_with_incorrect_ecmp.append(
                (current_route, nexthop_count)
            )

    print(f"Routes checked: {routes_checked}")
    print(f"Routes with correct ECMP ({expected_nexthops} NHs): {routes_with_correct_ecmp}")
    print(f"Routes with incorrect ECMP: {len(routes_with_incorrect_ecmp)}")

    if routes_with_incorrect_ecmp:
        print("\nRoutes with incorrect ECMP:")
        for route, count in routes_with_incorrect_ecmp[:10]:  # Show first 10
            print(f"  {route}: {count} next-hops (expected {expected_nexthops})")
        return False

    return True
```

---

### Step 9: Peer Flap Test - Single BGP Session
**Objective**: Flap one BGP session and monitor convergence and recovery

**Commands (Execute on DUT)**:
```bash
# Record pre-flap state
sonic-cli
show ip bgp summary
show ip route bgp | count

# Note timestamp: T0
# Shutdown BGP neighbor (Peer1)
configure terminal
router bgp 64512
neighbor 10.0.0.0 shutdown
exit
exit

# Monitor BGP sessions
show ip bgp summary

# Monitor route changes (should drop from 4-way to 3-way ECMP)
show ip route bgp | count
show ip route 192.168.0.0/24

# Wait 30 seconds

# Note timestamp: T1
# Restore BGP neighbor
configure terminal
router bgp 64512
no neighbor 10.0.0.0 shutdown
exit
exit

# Monitor recovery
# Note timestamp when neighbor reaches ESTABLISHED: T2
show ip bgp summary

# Verify routes restored to 4-way ECMP
show ip route 192.168.0.0/24

# Note timestamp when all routes restored: T3
show ip bgp summary
show ip route bgp | count
```

**Expected Result**:
- Neighbor shutdown detected immediately
- BGP session transitions: ESTABLISHED → Idle
- Routes updated: 4-way ECMP → 3-way ECMP
- All 1000 routes maintained via 3 remaining peers
- Neighbor recovery: < 30 seconds to ESTABLISHED
- Routes restored to 4-way ECMP
- CPU spike during reconvergence < 50%
- Memory stable throughout

**Convergence Metrics**:
- Shutdown detection: Immediate
- Route withdrawal time: < 5 seconds
- Neighbor re-establishment: T2 - T1 < 30 seconds
- Route restoration: T3 - T2 < 30 seconds
- Total recovery time: < 60 seconds

---

### Step 10: Peer Flap Test - Multiple BGP Sessions
**Objective**: Flap multiple BGP sessions simultaneously and verify stability

**Commands (Execute on DUT)**:
```bash
# Shutdown 2 BGP neighbors simultaneously
sonic-cli
configure terminal
router bgp 64512
neighbor 10.0.0.0 shutdown
neighbor 10.0.4.0 shutdown
exit
exit

# Monitor system
show ip bgp summary
show ip route bgp | count
show processes cpu
show system memory

# Verify routes now have 2-way ECMP (via Peer3 and Peer4)
show ip route 192.168.0.0/24

# Wait 30 seconds

# Restore both neighbors
configure terminal
router bgp 64512
no neighbor 10.0.0.0 shutdown
no neighbor 10.0.4.0 shutdown
exit
exit

# Monitor recovery
show ip bgp summary
show ip route bgp | count
show processes cpu

# Verify routes restored to 4-way ECMP
show ip route 192.168.0.0/24
```

**Expected Result**:
- Both neighbors go to Idle state
- Routes updated: 4-way ECMP → 2-way ECMP
- All 1000 routes maintained via 2 remaining peers
- CPU spike during reconvergence < 70%
- Memory stable
- Both neighbors recover to ESTABLISHED
- Routes restored to 4-way ECMP
- System remains stable throughout
- No route loss or blackholing

---

### Step 11: Sustained Load Test - Monitor Stability Over Time
**Objective**: Monitor system stability over extended period with all routes installed

**Procedure**:
1. Monitor for 30 minutes with all 1000 routes and 4 BGP sessions
2. Check for resource leaks
3. Verify route stability (no flapping)

**Monitoring Script**:
```bash
#!/bin/bash
# Sustained BGP ECMP monitoring for 30 minutes

LOG_FILE="bgp_ecmp_scale_monitor.log"
DURATION=1800  # 30 minutes
INTERVAL=60    # 1 minute

echo "Starting sustained BGP ECMP monitoring for $((DURATION/60)) minutes" | tee -a $LOG_FILE
START_TIME=$(date +%s)

while [ $(($(date +%s) - START_TIME)) -lt $DURATION ]; do
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

    # Get metrics
    BGP_ESTABLISHED=$(sonic-cli -c "show ip bgp summary" | grep -c "ESTABLISHED")
    ROUTE_COUNT=$(sonic-cli -c "show ip route bgp" | grep "^B" | wc -l)
    CPU_BGPD=$(sonic-cli -c "show processes" | grep bgpd | awk '{print $3}')
    MEM_USED=$(sonic-cli -c "show system memory" | grep "Used:" | awk '{print $2}')

    # Log metrics
    echo "$TIMESTAMP | BGP Sessions: $BGP_ESTABLISHED | Routes: $ROUTE_COUNT | BGP CPU: $CPU_BGPD% | Mem Used: $MEM_USED" | tee -a $LOG_FILE

    sleep $INTERVAL
done

echo "Monitoring complete" | tee -a $LOG_FILE
```

**Expected Result**:
- BGP session count stable at 4 ESTABLISHED
- Route count stable at 1000
- CPU utilization stable (no increase over time)
- Memory utilization stable (no leak)
- No unexpected BGP session flaps
- No route flapping or instability

**Acceptable Drift**:
- CPU variation: < 5%
- Memory variation: < 10%
- No BGP session state changes
- No route count changes

---

### Step 12: Rapid Session Flapping Test
**Objective**: Test system stability under rapid BGP session flapping

**Commands**:
```bash
# Rapidly flap one BGP session 10 times
for i in {1..10}; do
    echo "Flap iteration $i"
    sonic-cli -c "configure terminal; router bgp 64512; neighbor 10.0.0.0 shutdown; exit; exit"
    sleep 5
    sonic-cli -c "configure terminal; router bgp 64512; no neighbor 10.0.0.0 shutdown; exit; exit"
    sleep 15
done

# Monitor system after rapid flapping
sonic-cli
show ip bgp summary
show ip route bgp | count
show processes cpu
show system memory
show ip route 192.168.0.0/24
```

**Expected Result**:
- System handles rapid flaps without crash
- Final state: All 4 neighbors ESTABLISHED
- All routes restored to 4-way ECMP
- CPU returns to baseline
- Memory stable (no leak from repeated flaps)
- No BGP protocol instability
- No persistent route loss

---

### Step 13: Hard Reset Test - Interface Down
**Objective**: Test convergence when interface goes down (harder than graceful BGP shutdown)

**Commands (Execute on DUT)**:
```bash
# Bring down interface to Peer1 (simulates link failure)
sonic-cli
configure terminal
interface Ethernet0
shutdown
exit
exit

# Monitor BGP session (should transition to Idle)
show ip bgp summary

# Monitor route convergence
show ip route bgp | count
show ip route 192.168.0.0/24

# Wait for hold timer expiry and route withdrawal

# Restore interface
configure terminal
interface Ethernet0
no shutdown
exit
exit

# Monitor BGP session re-establishment
show ip bgp summary

# Verify route restoration
show ip route 192.168.0.0/24
show ip route bgp | count
```

**Expected Result**:
- Interface down detected immediately
- BGP session transitions to Idle after hold timer (default 180s, or configured)
- Routes withdrawn after session down
- ECMP updated: 4-way → 3-way
- Interface restored
- BGP session re-establishes
- Routes restored to 4-way ECMP
- Total recovery time depends on hold timer + session establishment

**Note**: BGP hold timer can be tuned for faster detection:
- Default hold timer: 180 seconds
- Aggressive tuning: 30-60 seconds
- With BFD: Sub-second detection

---

### Step 14: Route Churn Test (Optional)
**Objective**: Test system under continuous route changes from peers

**Procedure**:
1. Continuously advertise and withdraw additional routes from one peer
2. Monitor DUT route table churn handling
3. Verify system stability

**Script (execute on Peer1)**:
```bash
#!/bin/bash
# BGP route churn test - advertise and withdraw routes

for cycle in {1..20}; do
    echo "Cycle $cycle: Advertising additional routes"
    # Add 100 additional routes
    for i in {0..99}; do
        sonic-cli -c "configure terminal; ip route 192.180.$i.0/24 Null0; exit"
    done

    sleep 30

    echo "Cycle $cycle: Withdrawing routes"
    # Remove 100 routes
    for i in {0..99}; do
        sonic-cli -c "configure terminal; no ip route 192.180.$i.0/24 Null0; exit"
    done

    sleep 30
done
```

**Monitor on DUT**:
```bash
# Continuous monitoring during churn
watch -n 5 'sonic-cli -c "show ip bgp summary; show ip route bgp | count; show processes | grep bgpd"'
```

**Expected Result**:
- System handles route churn gracefully
- Route count fluctuates as expected (1000 baseline + up to 100 churn)
- CPU elevated but not excessive (< 60%)
- Memory stable
- No BGP session instability
- Base 1000 routes remain stable

---

### Step 15: Final State Verification
**Objective**: Verify system returns to stable baseline state after all tests

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify all BGP sessions up
show ip bgp summary

# Verify route count
show ip route bgp | count

# Sample routes to verify 4-way ECMP
show ip route 192.168.0.0/24
show ip route 192.168.50.0/24
show ip route 192.170.100.0/24

# Verify resources returned to baseline
show processes
show processes cpu
show system memory

# Check for any errors
show logging | grep -i error | tail -50
show logging | grep -i bgp | tail -50

# Verify BGP configuration
show running-configuration router bgp
```

**Expected Result**:
- 4 BGP neighbors in ESTABLISHED state
- 1000 BGP routes installed with 4-way ECMP
- CPU at baseline (< 30%)
- Memory at baseline (< 60%)
- No errors in logs
- BGP multipath enabled (maximum-paths 4)
- System stable and responsive

---

## Validation Points

### BGP ECMP Scalability Validation (klish mode via sonic-cli)

**Primary Commands**:
- `show ip bgp`
- `show processes`

**Validation Criteria**:

#### 1. BGP Session Establishment
- **All sessions ESTABLISHED**: 4 neighbors
- **Session stability**: No flapping
- **Prefixes received**: 1000 per peer
- **Total paths in BGP table**: 4000 (1000 × 4)

#### 2. ECMP Route Installation
- **All routes installed**: 1000 routes (100% success)
- **ECMP distribution**: 4 next-hops per route
- **Total next-hop entries**: ~4000
- **Route origin**: BGP (B)
- **Multipath enabled**: Verified in BGP table

#### 3. Resource Utilization - Baseline
- **CPU - BGP daemon**: < 10% steady state
- **CPU - System total**: < 30% steady state
- **Memory - BGP daemon**: < 5% of total
- **Memory - System total**: < 60% of total
- **No resource leaks**: Stable over 30+ minutes

#### 4. Resource Utilization - Under Stress
- **CPU spike during reconvergence**: < 70% peak
- **CPU spike during session flap**: < 70% peak
- **Memory during route processing**: < 75% peak
- **Recovery to baseline**: < 120 seconds
- **System responsiveness**: Maintained throughout

#### 5. Session Flap Recovery
- **Detection time**: Immediate (BGP shutdown) or hold timer (link down)
- **Route withdrawal time**: < 5 seconds
- **Session re-establishment**: < 30 seconds
- **Route restoration time**: < 30 seconds after session up
- **Zero route loss**: All routes maintained via remaining peers

#### 6. System Stability - No Instability
- **No crashes**: System remains operational
- **No hangs**: CLI remains responsive
- **No memory leaks**: Memory stable over time
- **No CPU runaway**: CPU returns to baseline
- **No routing loops**: Traffic forwarding correct
- **No route flapping**: Routes stable

#### 7. Fast Failover
- **Rapid detection**: Immediate session shutdown or hold-timer expiry
- **Quick route update**: < 5 seconds for route withdrawal
- **Fast ECMP adjustment**: < 10 seconds for ECMP path reduction
- **Quick recovery**: < 30 seconds for session re-establishment
- **Rapid restoration**: < 30 seconds for full ECMP restoration
- **Minimal downtime**: < 60 seconds total for single peer flap

---

## Expected Overall Results

### Key Expected Outputs

This test validates three critical aspects:

#### 1. Handles Many ECMP Entries
- **1000 routes × 4 paths = 4000 ECMP next-hop entries**
- All entries successfully installed in routing table
- All entries programmed to hardware FIB
- No FIB overflow or capacity issues
- Equal-cost load balancing functional across all paths
- System handles large-scale ECMP without degradation

#### 2. No Instability
- **BGP sessions stable**: No unexpected session flaps
- **Routes stable**: No route flapping or oscillation
- **System stable**: No crashes, hangs, or reboots
- **Performance stable**: No degradation over time
- **Memory stable**: No memory leaks
- **CPU stable**: Returns to baseline after events

#### 3. Fast Failover
- **Rapid peer failure detection**: Immediate (graceful) or hold-timer (link down)
- **Quick route withdrawal**: < 5 seconds
- **Fast ECMP path adjustment**: < 10 seconds
- **Automatic traffic reroute**: Traffic seamlessly shifts to remaining peers
- **Quick peer recovery**: < 30 seconds to ESTABLISHED
- **Fast route restoration**: < 30 seconds to full ECMP
- **Minimal downtime**: < 60 seconds total for single peer flap
- **Zero manual intervention**: System automatically converges

### Success Criteria

#### 1. Route Installation Success
- 100% of configured routes installed (1000/1000)
- All routes have correct ECMP (4 next-hops each)
- Installation time reasonable (< 5 minutes for 1000 routes)
- No route installation failures

#### 2. Handles Many ECMP Entries
- **1000 routes × 4 paths = 4000 ECMP entries**
- All entries installed in routing table
- All entries programmed to hardware FIB
- No FIB overflow or capacity issues
- Equal-cost load balancing functional

#### 3. No Instability
- **BGP sessions stable**: No unexpected flaps
- **Routes stable**: No route flapping
- **System stable**: No crashes or hangs
- **Performance stable**: No degradation over time
- **Memory stable**: No leaks
- **CPU stable**: Returns to baseline

#### 4. Resource Efficiency
- **CPU baseline**: < 30% system, < 10% BGP daemon
- **CPU under stress**: < 70% peak, recovery < 120 seconds
- **Memory baseline**: < 60% system, < 5% BGP daemon
- **Memory under stress**: < 80% peak, no leaks
- **Stable over time**: No resource growth over 30+ minutes

#### 5. Fast Convergence (Single Session Flap)
- Session shutdown: Immediate
- Route withdrawal: < 5 seconds
- ECMP update: 4 → 3 paths < 10 seconds
- Session recovery: < 30 seconds
- Route restoration: < 30 seconds
- Total recovery: < 60 seconds

#### 6. Resilience (Multiple Session Flaps)
- System handles 2 simultaneous flaps
- ECMP degrades smoothly: 4 → 2 paths
- All routes maintained (no route loss)
- Recovery smooth: 2 → 4 paths
- System remains stable

#### 7. Fast Failover Performance
- **Single peer failure**: < 30 seconds to reconverge
- **Multiple peer failure**: < 60 seconds to reconverge
- **Link failure detection**: Hold-timer or BFD-based
- **Automatic reroute**: Traffic seamlessly shifts to remaining peers
- **Zero manual intervention**: System self-heals
- **Minimal packet loss**: < 1% during failover

#### 8. Sustained Stability
- Stable over 30+ minutes continuous operation
- No BGP session flapping
- No route instability
- No resource leaks
- No performance degradation

### Performance Benchmarks

#### Route Processing
- **Installation rate**: > 200 routes/second
- **Total installation time**: < 5 seconds for 1000 routes
- **Route table lookup**: O(log n) performance
- **FIB programming**: < 3 seconds for 4000 next-hop entries

#### Convergence Times
- **Single session (graceful shutdown)**: < 30 seconds
- **Single session (link down)**: < hold-timer + 30 seconds
- **Multiple sessions**: < 60 seconds
- **Full recovery**: < 120 seconds including stabilization

#### Resource Limits
- **Maximum routes tested**: 1000 routes
- **Maximum ECMP width**: 4 paths (can test 8, 16, 32 if supported)
- **CPU headroom**: 40%+ available under normal load
- **Memory headroom**: 30%+ available with full route table

### Failure Indicators

**Test should fail if**:
1. Not all routes installed (< 100% success rate)
2. Some routes missing ECMP paths (< 4 next-hops)
3. CPU exceeds 80% for extended periods (> 2 minutes)
4. Memory exceeds 90% at any time
5. System crash or hang during test
6. BGP session instability (unexpected flaps)
7. Route flapping detected
8. Convergence time > 120 seconds
9. Routes lost during session flap
10. Memory leak detected (continuous growth)
11. CLI becomes unresponsive
12. Routing loops or blackholes detected

---

## Test Execution Summary Template

### BGP Session Validation

| Metric | Expected | Actual | Result |
|--------|----------|--------|--------|
| BGP sessions configured | 4 | ___ | Pass/Fail |
| Sessions ESTABLISHED | 4 | ___ | Pass/Fail |
| Prefixes received per peer | 1000 | ___ | Pass/Fail |
| Total paths in BGP table | 4000 | ___ | Pass/Fail |
| Multipath enabled | Yes | ___ | Pass/Fail |

### Route Installation Validation

| Metric | Expected | Actual | Result |
|--------|----------|--------|--------|
| Routes configured | 1000 | ___ | Pass/Fail |
| Routes installed | 1000 | ___ | Pass/Fail |
| Success rate | 100% | ___% | Pass/Fail |
| ECMP paths per route | 4 | ___ | Pass/Fail |
| Installation time | < 5 min | ___ min | Pass/Fail |

### Resource Utilization - Baseline

| Resource | Threshold | Actual | Result |
|----------|-----------|--------|--------|
| CPU (BGP daemon) | < 10% | ___% | Pass/Fail |
| CPU (System) | < 30% | ___% | Pass/Fail |
| Memory (BGP daemon) | < 5% | ___% | Pass/Fail |
| Memory (System) | < 60% | ___% | Pass/Fail |

### Resource Utilization - Under Stress

| Event | CPU Peak | Memory Peak | Recovery Time | Result |
|-------|----------|-------------|---------------|--------|
| BGP soft reset | < 70% | < 75% | < 120s | Pass/Fail |
| Single session flap | < 70% | < 75% | < 60s | Pass/Fail |
| Multiple session flap | < 80% | < 80% | < 90s | Pass/Fail |
| Rapid flapping | < 80% | < 80% | < 120s | Pass/Fail |

### Convergence Testing

| Test | Detection | Route Update | Recovery | Total | Result |
|------|-----------|--------------|----------|-------|--------|
| Single flap (graceful) | Immediate | < 5s | < 30s | < 60s | Pass/Fail |
| Dual flap (graceful) | Immediate | < 10s | < 30s | < 60s | Pass/Fail |
| Link down | Hold timer | < 5s | < 30s | Variable | Pass/Fail |

### Stability Testing

| Test | Duration | CPU Drift | Memory Drift | Failures | Result |
|------|----------|-----------|--------------|----------|--------|
| Sustained load | 30 min | < 5% | < 10% | 0 | Pass/Fail |
| Rapid flapping | 10 cycles | Recovers | Stable | 0 | Pass/Fail |
| Route churn | 20 cycles | < 60% | < 70% | 0 | Pass/Fail |

---

## Cleanup Steps

After test completion, remove BGP configuration and scale routes:

```bash
# On DUT
sonic-cli
configure terminal

# Remove BGP configuration
no router bgp 64512

# Remove interface IPs
interface Ethernet0
no ip address 10.0.0.1/31
exit

interface Ethernet4
no ip address 10.0.4.1/31
exit

interface Ethernet8
no ip address 10.0.8.1/31
exit

interface Ethernet12
no ip address 10.0.12.1/31
exit

exit

# Verify cleanup
show ip bgp summary
show ip route bgp

exit
```

**On BGP Peers** - Remove static routes and BGP:
```bash
# Remove BGP configuration
sonic-cli
configure terminal

# Remove static routes (script recommended for 1000 routes)
# no ip route 192.168.0.0/24 Null0
# ... (repeat for all 1000 routes)

# Remove BGP
no router bgp <AS-NUMBER>

exit

# Verify cleanup
show ip bgp summary
show ip route

exit
```

---

## Notes

1. **All BGP commands must be executed in klish mode via sonic-cli**

2. **BGP Multipath Configuration**:
   - Critical for ECMP: `maximum-paths 4`
   - Without multipath, only best path installed
   - Multipath applies to eBGP and iBGP separately
   - Maximum paths supported varies by platform (typically 4, 8, 16, 32, 64)

3. **BGP ECMP Requirements**:
   - **Equal AS-PATH length**: All paths must have same number of AS hops
   - **Equal MED** (if used): Multi-Exit Discriminator must match
   - **Equal LOCAL_PREF** (iBGP): Local preference must match
   - **Equal ORIGIN**: Origin attribute should match (IGP, EGP, Incomplete)
   - **Multipath enabled**: `maximum-paths` must be configured

4. **BGP Timers**:
   - **Keepalive**: Default 60 seconds (configurable)
   - **Hold timer**: Default 180 seconds (configurable)
   - **Connect retry**: Default 120 seconds
   - Aggressive tuning: keepalive 10s, hold 30s
   - With BFD: Sub-second failure detection

5. **Resource Monitoring Best Practices**:
   - Establish baseline before testing
   - Monitor continuously during stress tests
   - Allow time for stabilization between tests
   - Record all measurements for trending
   - Monitor both control plane (BGP) and data plane (FIB)

6. **BGP Scalability Factors**:
   - Number of routes impacts memory
   - Number of paths per route impacts FIB size
   - ECMP width impacts next-hop table
   - BGP update processing impacts CPU
   - Route churn rate impacts CPU

7. **CPU Utilization Components**:
   - BGP update processing: Receiving and validating updates
   - Best path calculation: Running decision process
   - Route installation: Programming FIB
   - Keepalive processing: Session maintenance
   - Policy evaluation: Route-maps, prefix-lists, filters

8. **Memory Utilization Components**:
   - BGP RIB (Routing Information Base): All received routes
   - BGP FIB subset: Best paths and multipath
   - Routing table: Installed routes
   - FIB: Forwarding information base
   - Next-hop table: ECMP next-hop entries

9. **Convergence Optimization**:
   - Reduce hold timer (faster detection, less stable)
   - Enable BFD (sub-second detection)
   - Tune BGP timers (keepalive/hold)
   - Consider route dampening for stability
   - Use prefix limits to prevent memory exhaustion

10. **Common Issues**:
    - **ECMP not forming**: Check AS-PATH length, MED, multipath config
    - **Memory exhaustion**: Increase system memory, use prefix limits
    - **Slow convergence**: Tune BGP timers, enable BFD
    - **High CPU**: Reduce route churn, tune update processing
    - **Route not installing**: Check FIB capacity, verify multipath support

11. **Testing Variations**:
    - **ECMP width**: Test with 2, 4, 8, 16, 32 paths
    - **Route count**: Test with 100, 500, 1000, 2000, 5000 routes
    - **Prefix length**: Test /24, /32, mixed
    - **BGP attributes**: Test with MED, LOCAL_PREF, communities
    - **Route policies**: Test with route-maps and filtering

12. **Performance Tuning**:
    - Increase BGP process priority
    - Tune kernel routing table size
    - Optimize FIB hardware programming
    - Consider route aggregation/summarization
    - Use BGP route refresh for graceful updates

---

## Additional Validation Commands

For comprehensive testing:

```bash
# BGP detailed information
show ip bgp summary
show ip bgp
show ip bgp neighbors
show ip bgp neighbors 10.0.0.0 advertised-routes
show ip bgp neighbors 10.0.0.0 received-routes

# Specific route analysis
show ip bgp 192.168.0.0/24
show ip bgp 192.168.0.0/24 bestpath

# Route table analysis
show ip route bgp
show ip route summary
show ip route 192.168.0.0/24 detail

# BGP statistics
show ip bgp statistics
show ip bgp neighbors 10.0.0.0 statistics

# Resource monitoring
show processes
show processes cpu
show processes memory
show system memory
show system cpu

# Configuration verification
show running-configuration router bgp
show running-configuration | grep maximum-paths

# Logging and debugging
show logging | grep bgp
show logging | grep -i error

# System health
show system status
show version
```

---

## Automation Script Template

```python
#!/usr/bin/env python3
"""
BGP ECMP Scalability Test Automation

Automates:
1. BGP session verification
2. Route installation verification
3. ECMP next-hop verification
4. Resource monitoring
5. Session flap testing
6. Results reporting
"""

import time
import subprocess
from collections import defaultdict

class BgpEcmpScaleTest:
    def __init__(self, dut, expected_routes=1000, expected_ecmp=4, expected_peers=4):
        self.dut = dut
        self.expected_routes = expected_routes
        self.expected_ecmp = expected_ecmp
        self.expected_peers = expected_peers
        self.results = defaultdict(dict)

    def verify_bgp_sessions(self):
        """Verify all BGP sessions are ESTABLISHED"""
        output = self.cli_command("show ip bgp summary")
        established_count = output.count("ESTABLISHED")

        self.results['bgp_sessions']['expected'] = self.expected_peers
        self.results['bgp_sessions']['actual'] = established_count
        self.results['bgp_sessions']['status'] = (
            established_count == self.expected_peers
        )

        return established_count == self.expected_peers

    def verify_route_installation(self):
        """Verify all routes installed with correct ECMP"""
        # Get route count
        output = self.cli_command("show ip route bgp | count")
        route_count = self.parse_count(output)

        self.results['installation']['route_count'] = route_count
        self.results['installation']['success_rate'] = (
            route_count / self.expected_routes * 100
        )

        # Verify ECMP on sample routes
        ecmp_correct = self.verify_ecmp_nexthops()
        self.results['installation']['ecmp_correct'] = ecmp_correct

        return route_count == self.expected_routes and ecmp_correct

    def verify_ecmp_nexthops(self):
        """Verify sample routes have correct number of next-hops"""
        sample_prefixes = [
            "192.168.0.0/24",
            "192.168.100.0/24",
            "192.170.50.0/24"
        ]

        for prefix in sample_prefixes:
            output = self.cli_command(f"show ip route {prefix}")
            nexthop_count = output.count("via")

            if nexthop_count != self.expected_ecmp:
                print(f"FAIL: {prefix} has {nexthop_count} NHs, expected {self.expected_ecmp}")
                return False

        return True

    def monitor_resources(self, duration=60):
        """Monitor CPU and memory over time"""
        samples = []
        interval = 5

        for _ in range(duration // interval):
            cpu = self.get_bgp_cpu_usage()
            mem = self.get_system_memory_usage()
            samples.append({'cpu': cpu, 'mem': mem, 'time': time.time()})
            time.sleep(interval)

        self.results['resources']['samples'] = samples
        self.results['resources']['cpu_max'] = max(s['cpu'] for s in samples)
        self.results['resources']['mem_max'] = max(s['mem'] for s in samples)

        return samples

    def test_session_flap(self, neighbor_ip):
        """Test single BGP session flap"""
        start = time.time()

        # Shutdown neighbor
        self.cli_command(
            f"configure terminal; router bgp {self.dut_asn}; "
            f"neighbor {neighbor_ip} shutdown; exit; exit"
        )

        # Wait for convergence
        converged = self.wait_for_route_stabilization(timeout=60)
        convergence_time = time.time() - start

        # Restore neighbor
        self.cli_command(
            f"configure terminal; router bgp {self.dut_asn}; "
            f"no neighbor {neighbor_ip} shutdown; exit; exit"
        )

        # Wait for recovery
        recovered = self.wait_for_session_established(neighbor_ip, timeout=60)
        recovery_time = time.time() - start

        self.results['flap'][neighbor_ip] = {
            'converged': converged,
            'convergence_time': convergence_time,
            'recovered': recovered,
            'recovery_time': recovery_time
        }

        return converged and recovered

    def generate_report(self):
        """Generate test report"""
        report = []
        report.append("=" * 80)
        report.append("BGP ECMP SCALABILITY TEST REPORT")
        report.append("=" * 80)

        # BGP session results
        report.append("\nBGP Sessions:")
        sess = self.results['bgp_sessions']
        report.append(f"  Expected: {sess['expected']}")
        report.append(f"  Actual: {sess['actual']}")
        report.append(f"  Status: {'PASS' if sess['status'] else 'FAIL'}")

        # Installation results
        report.append("\nRoute Installation:")
        inst = self.results['installation']
        report.append(f"  Routes installed: {inst['route_count']}/{self.expected_routes}")
        report.append(f"  Success rate: {inst['success_rate']:.1f}%")
        report.append(f"  ECMP correct: {inst['ecmp_correct']}")

        # Resource results
        report.append("\nResource Utilization:")
        res = self.results['resources']
        report.append(f"  Peak CPU: {res['cpu_max']:.1f}%")
        report.append(f"  Peak Memory: {res['mem_max']:.1f}%")

        # Flap results
        report.append("\nBGP Session Flap Tests:")
        for neighbor, result in self.results['flap'].items():
            report.append(f"  {neighbor}:")
            report.append(f"    Convergence: {result['convergence_time']:.1f}s")
            report.append(f"    Recovery: {result['recovery_time']:.1f}s")
            report.append(f"    Status: {'PASS' if result['recovered'] else 'FAIL'}")

        return "\n".join(report)

# Usage
test = BgpEcmpScaleTest(
    dut='192.168.1.1',
    expected_routes=1000,
    expected_ecmp=4,
    expected_peers=4
)

# Run tests
test.verify_bgp_sessions()
test.verify_route_installation()
test.monitor_resources(duration=300)
test.test_session_flap('10.0.0.0')

# Generate report
print(test.generate_report())
```

---

## References

- **Testbed Configuration**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_5node_bgp_ecmp.yaml`
- **Test ID**: TC_ECMP_2.4.4
- **Test Category**: ECMP - Large-scale BGP ECMP
- **Priority**: High
- **Automation**: Highly recommended
- **Related Test Cases**:
  - TC_ECMP_2.4.1 (Basic ECMP)
  - TC_ECMP_2.4.3 (BGP ECMP Basic)
  - TC_ECMP_2.4.5 (OSPF ECMP Scalability)
- **Related Standards**:
  - RFC 4271 (BGP-4)
  - RFC 4760 (Multiprotocol Extensions for BGP-4)
  - RFC 2991 (Multipath Issues)
  - RFC 7911 (Advertisement of Multiple Paths in BGP)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 2.4.4 - Large-scale BGP ECMP
