# Test Cases - OSPF ECMP Scalability Validation

## Test Case ID: TC_ECMP_2.4.5

### Test Case Name
Scalability with Many OSPF ECMP Routes

### Test Objective
Validate that the system can handle a large number of OSPF ECMP routes without performance degradation or resource exhaustion. Test includes advertising many equal-cost prefixes from multiple neighbors, monitoring CPU and memory utilization during normal operation and under stress, and verifying system stability and smooth recovery after OSPF adjacency flaps. Ensure that all ECMP routes are correctly installed, system resources remain stable, and convergence is smooth even with high route counts.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_5node_ecmp_scale.yaml`
- **Topology**: 5 nodes (1 DUT + 4 OSPF neighbors)
- **Device Under Test (DUT)**: Primary router under test
- **OSPF Neighbors**: Neighbor1, Neighbor2, Neighbor3, Neighbor4
- **Test Network**: OSPF Area 0 (Backbone)

### Topology Diagram

```
           [Neighbor1]      [Neighbor2]      [Neighbor3]      [Neighbor4]
           Each advertises 1000+ prefixes with equal cost
                |               |               |               |
                | Cost=10        | Cost=10       | Cost=10       | Cost=10
                | Ethernet0      | Ethernet4     | Ethernet8     | Ethernet12
                |               |               |               |
                +---------------+-------+-------+---------------+
                                        |
                                   +----+----+
                                   |   DUT   |
                                   | (Router)|
                                   +---------+

Result: 4-way ECMP for each of 1000+ destination prefixes
Total ECMP routes: 1000+ routes × 4 paths each = 4000+ next-hop entries
```

### Interface Configuration

**DUT Interfaces**:
- **Ethernet0**: Connected to Neighbor1 (10.0.0.0/31, IP: 10.0.0.1)
- **Ethernet4**: Connected to Neighbor2 (10.0.4.0/31, IP: 10.0.4.1)
- **Ethernet8**: Connected to Neighbor3 (10.0.8.0/31, IP: 10.0.8.1)
- **Ethernet12**: Connected to Neighbor4 (10.0.12.0/31, IP: 10.0.12.1)
- **Loopback0**: 1.1.1.1/32 (Router ID)

**OSPF Configuration**:
- Area: 0.0.0.0 (Backbone Area)
- Network Type: Point-to-Point
- Hello Interval: 10 seconds
- Dead Interval: 40 seconds
- All interfaces in Area 0

**Scale Parameters**:
- **Prefixes per neighbor**: 1000 prefixes (configurable: 100, 500, 1000, 2000)
- **Total prefixes**: 1000 (all neighbors advertise same prefixes)
- **ECMP paths per prefix**: 4 (one via each neighbor)
- **Total ECMP entries**: 1000 routes × 4 next-hops = 4000 entries
- **Prefix range**: 192.168.0.0/24 through 192.171.231.0/24

### Prerequisites
1. All 5 devices accessible via SSH
2. SONiC OS installed on all devices
3. Access to sonic-cli (klish) on all devices
4. OSPF routing protocol support enabled
5. Sufficient memory for routing table (minimum 2GB recommended)
6. Sufficient CPU capacity for route processing
7. All interfaces physically connected
8. Route table capacity: Support for 1000+ routes

---

## Test Procedure

### Step 1: Initial Setup - Configure DUT Interfaces
**Objective**: Configure IP addresses on all DUT interfaces

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure Ethernet0 (to Neighbor1)
interface Ethernet0
ip address 10.0.0.1/31
no shutdown
exit

# Configure Ethernet4 (to Neighbor2)
interface Ethernet4
ip address 10.0.4.1/31
no shutdown
exit

# Configure Ethernet8 (to Neighbor3)
interface Ethernet8
ip address 10.0.8.1/31
no shutdown
exit

# Configure Ethernet12 (to Neighbor4)
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
- All 4 neighbor-facing interfaces configured
- All interfaces operational (up/up)
- Loopback configured for router ID

---

### Step 2: Configure OSPF on DUT
**Objective**: Enable OSPF routing protocol on DUT

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure OSPF process
router ospf
router-id 1.1.1.1
network 10.0.0.0/31 area 0.0.0.0
network 10.0.4.0/31 area 0.0.0.0
network 10.0.8.0/31 area 0.0.0.0
network 10.0.12.0/31 area 0.0.0.0
network 1.1.1.1/32 area 0.0.0.0
exit

# Configure OSPF interface parameters (all neighbors)
interface Ethernet0
ip ospf network point-to-point
ip ospf hello-interval 10
ip ospf dead-interval 40
exit

interface Ethernet4
ip ospf network point-to-point
ip ospf hello-interval 10
ip ospf dead-interval 40
exit

interface Ethernet8
ip ospf network point-to-point
ip ospf hello-interval 10
ip ospf dead-interval 40
exit

interface Ethernet12
ip ospf network point-to-point
ip ospf hello-interval 10
ip ospf dead-interval 40
exit

# Exit configuration mode
exit
```

**Expected Result**:
- OSPF process enabled with router ID 1.1.1.1
- All neighbor links added to OSPF Area 0
- OSPF interface parameters configured

---

### Step 3: Configure OSPF Neighbors to Advertise Scale Prefixes
**Objective**: Configure each neighbor to advertise 1000 equal-cost prefixes

**Configuration Strategy**:
Each neighbor will advertise the same set of prefixes (192.168.0.0/24 - 192.171.231.0/24) with the same cost, resulting in 4-way ECMP for each prefix.

**Example Configuration (Neighbor1)**:
```bash
# On Neighbor1
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

# Configure OSPF
router ospf
router-id 2.2.2.2
network 10.0.0.0/31 area 0.0.0.0
network 2.2.2.2/32 area 0.0.0.0

# Advertise scale prefixes (method 1: using route redistribution)
# Create loopback interfaces for each prefix range
# Or use static routes + redistribution

exit

# Configure OSPF interface
interface Ethernet0
ip ospf network point-to-point
ip ospf hello-interval 10
ip ospf dead-interval 40
ip ospf cost 10
exit

exit
```

**Alternative Method - Using Route Redistribution**:
```bash
# Create static routes for scale testing
# Configure 1000 static routes
ip route 192.168.0.0/24 Null0
ip route 192.168.1.0/24 Null0
ip route 192.168.2.0/24 Null0
# ... (repeat for 1000 prefixes)
ip route 192.171.231.0/24 Null0

# Redistribute static into OSPF
router ospf
redistribute static
exit
```

**Automated Script for Scale Prefix Configuration**:
```python
#!/usr/bin/env python3
"""
Generate OSPF scale prefix configuration
Creates 1000 static routes for redistribution into OSPF
"""

def generate_scale_routes(start_octet=168, count=1000):
    """Generate static route commands"""
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
routes = generate_scale_routes(start_octet=168, count=1000)
print("configure terminal")
for route in routes:
    print(route)
print("router ospf")
print("redistribute static")
print("exit")
print("exit")
```

**Execute on all 4 neighbors** with same prefix set to create ECMP.

**Expected Result**:
- Each neighbor advertises 1000 prefixes
- All neighbors advertising same prefixes with equal cost
- DUT should receive 1000 prefixes via 4 paths each

---

### Step 4: Verify OSPF Neighbor Adjacencies
**Objective**: Verify all 4 OSPF neighbors are in FULL state

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Check OSPF neighbors
show ip ospf neighbor

# Count neighbors
show ip ospf neighbor | count
```

**Expected Result**:
- Four OSPF neighbors visible
- All neighbors in "FULL" state
- Neighbor IDs: 2.2.2.2, 3.3.3.3, 4.4.4.4, 5.5.5.5

**Sample Output**:
```
Neighbor ID     Pri State           Dead Time Address         Interface
2.2.2.2         1   Full/DROther    00:00:35  10.0.0.0        Ethernet0
3.3.3.3         1   Full/DROther    00:00:38  10.0.4.0        Ethernet4
4.4.4.4         1   Full/DROther    00:00:32  10.0.8.0        Ethernet8
5.5.5.5         1   Full/DROther    00:00:36  10.0.12.0       Ethernet12
```

---

### Step 5: Baseline - Verify OSPF Route Installation
**Objective**: Verify that all 1000 ECMP routes are installed

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Show OSPF routes
show ip route ospf

# Count OSPF routes
show ip route ospf | count

# Show sample route to verify ECMP
show ip route 192.168.0.0/24

# Show route summary
show ip route summary
```

**Expected Result**:
- 1000 OSPF routes installed
- Each route has 4 next-hops (ECMP)
- Total next-hop entries: ~4000

**Sample ECMP Route Output**:
```
O    192.168.0.0/24 [110/20]
       via 10.0.0.0, Ethernet0, weight 1, 00:05:23
       via 10.0.4.0, Ethernet4, weight 1, 00:05:23
       via 10.0.8.0, Ethernet8, weight 1, 00:05:23
       via 10.0.12.0, Ethernet12, weight 1, 00:05:23
```

**Validation Points**:
1. Route count = 1000 (or configured scale)
2. Each route has 4 next-hops
3. All routes show OSPF origin (O)
4. Metric consistent across routes (cost 20)

---

### Step 6: Baseline Resource Monitoring - CPU & Memory
**Objective**: Establish baseline CPU and memory utilization with all routes installed

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Show processes (CPU and memory)
show processes

# Show process CPU usage
show processes cpu

# Show process memory usage
show processes memory

# Show system memory
show system memory

# Monitor over time (repeat 5 times with 10-second intervals)
show processes | grep -E "CPU|MEM"
```

**Expected Result**:
- CPU utilization < 30% under steady state
- Memory utilization < 60% of available
- No process consuming excessive resources
- Stable resource usage (not increasing)

**Sample Output**:
```
PID    Name              CPU %    MEM %    Status
--------------------------------------------------
1234   ospfd             5.2      3.1      Running
1235   bgpd              2.1      2.4      Running
1236   zebra             3.4      4.2      Running
...

System Memory:
Total: 8192 MB
Used:  3200 MB (39%)
Free:  4992 MB (61%)

CPU Usage:
User:   8.5%
System: 4.2%
Idle:   87.3%
```

**Record baseline metrics**:
- OSPF daemon CPU: _____%
- OSPF daemon Memory: _____%
- Total system CPU: _____%
- Total system Memory: _____%

---

### Step 7: Stress Test - Monitor Resources During Route Processing
**Objective**: Monitor CPU and memory during active OSPF route processing

**Procedure**:
1. Start continuous monitoring
2. Trigger route recalculation (change OSPF cost)
3. Monitor CPU spike during SPF calculation
4. Verify return to baseline

**Commands (Execute on DUT)**:
```bash
# Start monitoring in background (script or manual)
# Monitor CPU/memory every 5 seconds for 2 minutes

# Terminal 1: Continuous monitoring
while true; do
  date
  sonic-cli -c "show processes cpu" | grep ospfd
  sonic-cli -c "show system memory"
  sleep 5
done

# Terminal 2: Trigger SPF recalculation
sonic-cli
configure terminal
interface Ethernet0
ip ospf cost 15
exit
# Wait 30 seconds
interface Ethernet0
ip ospf cost 10
exit
exit
```

**Expected Result**:
- CPU spike during SPF calculation (< 50% spike)
- Memory stable (no significant increase)
- Return to baseline within 30 seconds
- No process crashes or hangs

**Acceptable Metrics**:
- Peak CPU during SPF: < 60%
- Peak memory during SPF: < 70%
- Recovery time to baseline: < 60 seconds
- No OOM (Out of Memory) errors

---

### Step 8: Route Count Validation
**Objective**: Verify exact route count and ECMP distribution

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Count total OSPF routes
show ip route ospf | count

# Sample multiple routes to verify ECMP
show ip route 192.168.0.0/24
show ip route 192.168.100.0/24
show ip route 192.170.50.0/24

# Check for any routes with less than 4 next-hops
show ip route ospf | grep -v "via.*via.*via.*via"

# Show OSPF database summary
show ip ospf database summary
```

**Expected Result**:
- Exact count: 1000 routes (or configured scale)
- All routes have 4 next-hops (no partial ECMP)
- No routes missing next-hops
- OSPF database contains all LSAs

**Validation Script** (to verify all routes have 4 next-hops):
```python
#!/usr/bin/env python3
"""
Verify all OSPF routes have correct number of ECMP paths
"""

def verify_ecmp_routes(route_output, expected_nexthops=4):
    """Parse route output and verify ECMP"""
    routes_checked = 0
    routes_with_correct_ecmp = 0
    routes_with_incorrect_ecmp = []

    current_route = None
    nexthop_count = 0

    for line in route_output.split('\n'):
        if line.startswith('O '):
            # New OSPF route
            if current_route and nexthop_count != expected_nexthops:
                routes_with_incorrect_ecmp.append(
                    (current_route, nexthop_count)
                )

            current_route = line.split()[1]
            nexthop_count = 1  # First next-hop on same line
            routes_checked += 1

        elif 'via' in line:
            # Additional next-hop
            nexthop_count += 1

    # Check last route
    if current_route and nexthop_count != expected_nexthops:
        routes_with_incorrect_ecmp.append(
            (current_route, nexthop_count)
        )
    else:
        routes_with_correct_ecmp += 1

    print(f"Routes checked: {routes_checked}")
    print(f"Routes with correct ECMP ({expected_nexthops} paths): {routes_with_correct_ecmp}")
    print(f"Routes with incorrect ECMP: {len(routes_with_incorrect_ecmp)}")

    if routes_with_incorrect_ecmp:
        print("\nRoutes with incorrect ECMP:")
        for route, count in routes_with_incorrect_ecmp:
            print(f"  {route}: {count} next-hops (expected {expected_nexthops})")
        return False

    return True
```

---

### Step 9: Adjacency Flap Test - Single Neighbor
**Objective**: Flap one OSPF adjacency and monitor recovery

**Commands (Execute on DUT)**:
```bash
# Record pre-flap state
sonic-cli
show ip ospf neighbor
show ip route ospf | count

# Note timestamp: T0
# Shutdown interface to Neighbor1
configure terminal
interface Ethernet0
shutdown
exit
exit

# Monitor OSPF neighbors
# Wait for neighbor to go down
show ip ospf neighbor

# Monitor route changes
show ip route ospf | count

# Wait 30 seconds, then bring interface back up
# Note timestamp: T1
configure terminal
interface Ethernet0
no shutdown
exit
exit

# Monitor recovery
# Note timestamp when neighbor returns to FULL: T2
show ip ospf neighbor

# Verify routes restored
show ip route ospf | count

# Note timestamp when all routes restored: T3
```

**Expected Result**:
- Neighbor down detected within dead interval (40 seconds)
- Routes updated: 4-way ECMP → 3-way ECMP
- No route loss (all 1000 routes maintained via 3 paths)
- Neighbor recovery: < 50 seconds
- Routes restored to 4-way ECMP
- CPU spike during reconvergence < 50%
- Memory stable throughout

**Convergence Metrics**:
- Detection time: T1 - T0 ≤ 40 seconds (dead interval)
- Route update time: < 10 seconds after detection
- Recovery time: T2 - T1 < 50 seconds
- Route restoration: T3 - T2 < 10 seconds

---

### Step 10: Adjacency Flap Test - Multiple Neighbors
**Objective**: Flap multiple adjacencies simultaneously

**Commands (Execute on DUT)**:
```bash
# Shutdown 2 interfaces simultaneously
sonic-cli
configure terminal
interface Ethernet0
shutdown
exit
interface Ethernet4
shutdown
exit
exit

# Monitor system
show ip ospf neighbor
show ip route ospf | count
show processes cpu

# Wait 30 seconds
# Bring interfaces back up
configure terminal
interface Ethernet0
no shutdown
exit
interface Ethernet4
no shutdown
exit
exit

# Monitor recovery
show ip ospf neighbor
show ip route ospf | count
show processes cpu
```

**Expected Result**:
- Both neighbors go down
- Routes updated: 4-way ECMP → 2-way ECMP
- All 1000 routes maintained (via 2 remaining neighbors)
- CPU spike during reconvergence < 70%
- Memory stable
- Both neighbors recover
- Routes restored to 4-way ECMP
- System remains stable throughout

---

### Step 11: Sustained Load Test - Monitor Over Time
**Objective**: Monitor system stability over extended period

**Procedure**:
1. Monitor for 30 minutes with all routes installed
2. Check for resource leaks
3. Verify route stability

**Monitoring Script**:
```bash
#!/bin/bash
# Sustained monitoring for 30 minutes

LOG_FILE="ecmp_scale_monitor.log"
DURATION=1800  # 30 minutes
INTERVAL=60    # 1 minute

echo "Starting sustained monitoring for $((DURATION/60)) minutes" | tee -a $LOG_FILE
START_TIME=$(date +%s)

while [ $(($(date +%s) - START_TIME)) -lt $DURATION ]; do
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

    # Get metrics
    OSPF_NEIGHBORS=$(sonic-cli -c "show ip ospf neighbor" | grep Full | wc -l)
    ROUTE_COUNT=$(sonic-cli -c "show ip route ospf" | grep "^O" | wc -l)
    CPU_OSPFD=$(sonic-cli -c "show processes cpu" | grep ospfd | awk '{print $3}')
    MEM_TOTAL=$(sonic-cli -c "show system memory" | grep "Total:" | awk '{print $2}')
    MEM_USED=$(sonic-cli -c "show system memory" | grep "Used:" | awk '{print $2}')

    # Log metrics
    echo "$TIMESTAMP | Neighbors: $OSPF_NEIGHBORS | Routes: $ROUTE_COUNT | CPU: $CPU_OSPFD% | Mem: $MEM_USED/$MEM_TOTAL" | tee -a $LOG_FILE

    sleep $INTERVAL
done

echo "Monitoring complete" | tee -a $LOG_FILE
```

**Expected Result**:
- Neighbor count stable at 4
- Route count stable at 1000
- CPU utilization stable (no increase over time)
- Memory utilization stable (no leak)
- No unexpected neighbor flaps
- No route instability

**Acceptable Drift**:
- CPU variation: < 5%
- Memory variation: < 10%
- No neighbor state changes
- No route count changes

---

### Step 12: Rapid Adjacency Flapping
**Objective**: Test system stability under rapid adjacency changes

**Commands**:
```bash
# Rapidly flap one interface 10 times
for i in {1..10}; do
    sonic-cli -c "configure terminal; interface Ethernet0; shutdown; exit; exit"
    sleep 2
    sonic-cli -c "configure terminal; interface Ethernet0; no shutdown; exit; exit"
    sleep 5
done

# Monitor system after rapid flapping
sonic-cli
show ip ospf neighbor
show ip route ospf | count
show processes cpu
show system memory
```

**Expected Result**:
- System handles rapid flaps without crash
- Final state: All neighbors in FULL
- All routes restored to 4-way ECMP
- CPU returns to baseline
- Memory stable (no leak from repeated flaps)
- No routing protocol instability

---

### Step 13: Scale Increase Test (Optional)
**Objective**: Test with higher route counts if capacity allows

**Procedure**:
1. Current: 1000 routes
2. Increase to: 2000 routes
3. Monitor installation and resources

**Commands (on neighbors - add additional 1000 routes)**:
```bash
# Add more static routes for redistribution
# Routes 192.172.0.0/24 through 192.175.231.0/24

# Monitor on DUT
sonic-cli
show ip route ospf | count
show processes cpu
show system memory
```

**Expected Result**:
- System handles increased scale
- Route installation time reasonable
- CPU spike during installation < 80%
- Memory sufficient for scale
- System stable with increased route count

**Resource Limits**:
- Document maximum routes supported
- Document CPU/memory at maximum scale
- Identify any performance degradation points

---

### Step 14: Route Churn Test
**Objective**: Test system under continuous route changes

**Procedure**:
1. Continuously add/remove routes on neighbors
2. Monitor DUT route table churn
3. Verify system stability

**Script (execute on neighbor)**:
```bash
#!/bin/bash
# Route churn test - add and remove routes continuously

for cycle in {1..20}; do
    echo "Cycle $cycle: Adding routes"
    # Add 100 routes
    for i in {0..99}; do
        sonic-cli -c "configure terminal; ip route 192.180.$i.0/24 Null0; exit"
    done

    sleep 30

    echo "Cycle $cycle: Removing routes"
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
watch -n 5 'sonic-cli -c "show ip route ospf | count; show processes cpu | grep ospfd"'
```

**Expected Result**:
- System handles route churn
- Route count fluctuates as expected
- CPU elevated but not excessive (< 60%)
- Memory stable
- No protocol instability
- System remains responsive

---

### Step 15: Final State Verification
**Objective**: Verify system returns to stable baseline state

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify all neighbors up
show ip ospf neighbor

# Verify route count
show ip route ospf | count

# Sample routes to verify ECMP
show ip route 192.168.0.0/24
show ip route 192.168.50.0/24
show ip route 192.170.100.0/24

# Verify resources returned to baseline
show processes cpu
show system memory

# Check for any errors
show logging | grep -i error | tail -50

# Verify OSPF statistics
show ip ospf statistics
```

**Expected Result**:
- 4 OSPF neighbors in FULL state
- 1000 OSPF routes with 4-way ECMP
- CPU at baseline (< 30%)
- Memory at baseline (< 60%)
- No errors in logs
- System stable and responsive

---

## Validation Points

### OSPF Route Scalability Validation (klish mode via sonic-cli)

**Primary Commands**:
- `show ip route ospf`
- `show processes`

**Validation Criteria**:

#### 1. Route Installation
- **All routes installed**: 1000 routes (100% success)
- **ECMP distribution**: 4 next-hops per route
- **Total next-hop entries**: ~4000
- **Route origin**: OSPF (O)
- **Metric consistency**: All routes same metric

#### 2. Resource Utilization - Baseline
- **CPU - OSPF daemon**: < 10% steady state
- **CPU - System total**: < 30% steady state
- **Memory - OSPF daemon**: < 5% of total
- **Memory - System total**: < 60% of total
- **No resource leaks**: Stable over time

#### 3. Resource Utilization - Under Stress
- **CPU spike during SPF**: < 60% peak
- **CPU spike during adjacency flap**: < 70% peak
- **Memory during route processing**: < 70% peak
- **Recovery to baseline**: < 60 seconds
- **System responsiveness**: Maintained throughout

#### 4. Adjacency Flap Recovery
- **Detection time**: < 40 seconds (dead interval)
- **Route update time**: < 10 seconds after detection
- **Neighbor recovery time**: < 50 seconds
- **Route restoration time**: < 10 seconds after neighbor up
- **Zero route loss**: All routes maintained via remaining neighbors

#### 5. System Stability
- **No crashes**: System remains operational
- **No hangs**: CLI remains responsive
- **No memory leaks**: Memory stable over time
- **No CPU runaway**: CPU returns to baseline
- **No routing loops**: Traffic forwarding correct

#### 6. Smooth Recovery
- **Graceful degradation**: ECMP reduces smoothly (4→3→2→1 paths)
- **Automatic restoration**: ECMP increases smoothly (1→2→3→4 paths)
- **No manual intervention**: System self-heals
- **Traffic continuity**: Minimal packet loss

---

## Expected Overall Results

### Success Criteria

#### 1. Route Installation Success
- 100% of configured routes installed (1000/1000)
- All routes have correct ECMP (4 next-hops each)
- Installation time reasonable (< 5 minutes for 1000 routes)
- No route installation failures

#### 2. Resource Efficiency
- **CPU baseline**: < 30% system, < 10% OSPF daemon
- **CPU under stress**: < 70% peak, recovery < 60 seconds
- **Memory baseline**: < 60% system, < 5% OSPF daemon
- **Memory under stress**: < 80% peak, no leaks
- **Stable over time**: No resource growth over 30+ minutes

#### 3. Fast Convergence (Single Adjacency Flap)
- Failure detection: < 40 seconds (dead interval)
- ECMP update: 4 → 3 paths < 10 seconds
- Neighbor recovery: < 50 seconds
- ECMP restoration: 3 → 4 paths < 10 seconds
- Total down time: < 100 seconds

#### 4. Resilience (Multiple Adjacency Flaps)
- System handles 2 simultaneous flaps
- ECMP degrades smoothly: 4 → 2 paths
- All routes maintained (no route loss)
- Recovery smooth: 2 → 4 paths
- System remains stable

#### 5. Sustained Stability
- Stable over 30+ minutes continuous operation
- No neighbor flapping
- No route instability
- No resource leaks
- No performance degradation

#### 6. Rapid Flap Tolerance
- Handles 10+ rapid flaps without crash
- Returns to stable state
- No permanent damage
- Resources recover to baseline

### Performance Benchmarks

#### Route Processing
- **Installation rate**: > 200 routes/second
- **Total installation time**: < 5 seconds for 1000 routes
- **SPF calculation**: < 2 seconds for 1000 routes
- **FIB programming**: < 3 seconds for 4000 next-hop entries

#### Convergence Times
- **Single neighbor**: < 50 seconds total
- **Multiple neighbors**: < 60 seconds total
- **Full recovery**: < 100 seconds including stabilization

#### Resource Limits
- **Maximum routes tested**: 1000-2000 routes
- **Maximum ECMP width**: 4 paths (can test 8, 16 if supported)
- **CPU headroom**: 40%+ available under normal load
- **Memory headroom**: 30%+ available with full route table

### Failure Indicators

**Test should fail if**:
1. Not all routes installed (< 100% success rate)
2. Some routes missing ECMP paths (< 4 next-hops)
3. CPU exceeds 80% for extended periods (> 2 minutes)
4. Memory exceeds 90% at any time
5. System crash or hang during test
6. Convergence time > 120 seconds
7. Routes lost during adjacency flap
8. Memory leak detected (continuous growth)
9. CLI becomes unresponsive
10. Routing loops or blackholes detected

---

## Test Execution Summary Template

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
| CPU (OSPF daemon) | < 10% | ___% | Pass/Fail |
| CPU (System) | < 30% | ___% | Pass/Fail |
| Memory (OSPF daemon) | < 5% | ___% | Pass/Fail |
| Memory (System) | < 60% | ___% | Pass/Fail |

### Resource Utilization - Under Stress

| Event | CPU Peak | Memory Peak | Recovery Time | Result |
|-------|----------|-------------|---------------|--------|
| SPF recalculation | < 60% | < 70% | < 60s | Pass/Fail |
| Single neighbor flap | < 70% | < 70% | < 60s | Pass/Fail |
| Multiple neighbor flap | < 80% | < 80% | < 90s | Pass/Fail |
| Rapid flapping | < 80% | < 80% | < 120s | Pass/Fail |

### Convergence Testing

| Test | Detection | Route Update | Recovery | Total | Result |
|------|-----------|--------------|----------|-------|--------|
| Single flap | < 40s | < 10s | < 50s | < 100s | Pass/Fail |
| Dual flap | < 40s | < 15s | < 60s | < 115s | Pass/Fail |

### Stability Testing

| Test | Duration | CPU Drift | Memory Drift | Failures | Result |
|------|----------|-----------|--------------|----------|--------|
| Sustained load | 30 min | < 5% | < 10% | 0 | Pass/Fail |
| Rapid flapping | 10 cycles | Recovers | Stable | 0 | Pass/Fail |
| Route churn | 20 cycles | < 60% | < 70% | 0 | Pass/Fail |

---

## Cleanup Steps

After test completion, remove OSPF configuration and scale routes:

```bash
# On DUT
sonic-cli
configure terminal

# Remove OSPF
no router ospf

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
show ip route ospf
show ip ospf neighbor

exit
```

**On Neighbors** - Remove static routes and OSPF:
```bash
# Remove OSPF redistribution
sonic-cli
configure terminal
router ospf
no redistribute static
exit
no router ospf

# Remove static routes (script recommended)
# no ip route 192.168.0.0/24 Null0
# ... (repeat for all 1000 routes)

exit
```

---

## Notes

1. **All OSPF commands must be executed in klish mode via sonic-cli**

2. **Scale Testing Recommendations**:
   - Start with 100 routes to verify setup
   - Increase to 500 routes
   - Target scale: 1000 routes
   - Maximum scale (if capacity): 2000+ routes

3. **Resource Monitoring Best Practices**:
   - Establish baseline before testing
   - Monitor continuously during stress tests
   - Allow time for stabilization between tests
   - Record all measurements for trending

4. **OSPF Scalability Factors**:
   - LSA count impacts memory
   - Route count impacts FIB size
   - ECMP width impacts next-hop table
   - SPF calculation time scales with topology size

5. **CPU Utilization Components**:
   - SPF calculation: Dijkstra algorithm on LSA database
   - Route installation: Programming FIB
   - LSA processing: Receiving and validating updates
   - Keepalives: Hello/dead interval timers

6. **Memory Utilization Components**:
   - OSPF database: LSAs from all neighbors
   - Routing table: Installed routes
   - FIB: Forwarding information base
   - Next-hop table: ECMP next-hop entries

7. **Convergence Optimization**:
   - Reduce hello/dead intervals (faster detection, more overhead)
   - Enable BFD (sub-second detection)
   - Increase SPF delay/hold timers (dampen rapid changes)
   - Tune max-LSA limits

8. **Common Issues**:
   - **Memory exhaustion**: Increase system memory
   - **Slow SPF**: Reduce LSA database size
   - **High CPU**: Tune hello intervals, reduce route churn
   - **Route not installing**: Check FIB capacity, verify ECMP support

9. **Testing Variations**:
   - **ECMP width**: Test with 2, 4, 8, 16 paths
   - **Route count**: Test with 100, 500, 1000, 2000, 5000 routes
   - **Prefix length**: Test /24, /32, mixed
   - **Area type**: Test Area 0, stub areas, NSSA

10. **Performance Tuning**:
    - Increase OSPF process priority
    - Tune kernel routing table size
    - Optimize FIB hardware programming
    - Consider route summarization

---

## Additional Validation Commands

For comprehensive testing:

```bash
# OSPF detailed information
show ip ospf
show ip ospf database
show ip ospf database summary
show ip ospf route
show ip ospf interface

# Route table analysis
show ip route summary
show ip route statistics
show ip fib

# Resource monitoring
show processes
show processes cpu
show processes memory
show system memory
show system cpu

# Performance metrics
show interface counters
show interface counters rate

# Logging and debugging
show logging | grep ospf
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
OSPF ECMP Scalability Test Automation

Automates:
1. Route installation verification
2. Resource monitoring
3. Adjacency flap testing
4. Results reporting
"""

import time
import subprocess
from collections import defaultdict

class OspfScaleTest:
    def __init__(self, dut, expected_routes=1000, expected_ecmp=4):
        self.dut = dut
        self.expected_routes = expected_routes
        self.expected_ecmp = expected_ecmp
        self.results = defaultdict(dict)

    def verify_route_installation(self):
        """Verify all routes installed with correct ECMP"""
        # Get route count
        output = self.cli_command("show ip route ospf | count")
        route_count = self.parse_count(output)

        self.results['installation']['route_count'] = route_count
        self.results['installation']['success_rate'] = (
            route_count / self.expected_routes * 100
        )

        # Verify ECMP on sample routes
        ecmp_correct = self.verify_ecmp_paths()
        self.results['installation']['ecmp_correct'] = ecmp_correct

        return route_count == self.expected_routes and ecmp_correct

    def monitor_resources(self, duration=60):
        """Monitor CPU and memory over time"""
        samples = []
        interval = 5

        for _ in range(duration // interval):
            cpu = self.get_cpu_usage()
            mem = self.get_memory_usage()
            samples.append({'cpu': cpu, 'mem': mem, 'time': time.time()})
            time.sleep(interval)

        self.results['resources']['samples'] = samples
        self.results['resources']['cpu_max'] = max(s['cpu'] for s in samples)
        self.results['resources']['mem_max'] = max(s['mem'] for s in samples)

        return samples

    def test_adjacency_flap(self, interface):
        """Test single adjacency flap"""
        start = time.time()

        # Shutdown interface
        self.cli_command(f"configure terminal; interface {interface}; shutdown; exit; exit")

        # Wait for convergence
        converged = self.wait_for_route_count(self.expected_routes, timeout=60)
        convergence_time = time.time() - start

        # Restore interface
        self.cli_command(f"configure terminal; interface {interface}; no shutdown; exit; exit")

        # Wait for recovery
        recovered = self.wait_for_ecmp_restoration(timeout=60)
        recovery_time = time.time() - start

        self.results['flap'][interface] = {
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
        report.append("OSPF ECMP SCALABILITY TEST REPORT")
        report.append("=" * 80)

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
        report.append("\nAdjacency Flap Tests:")
        for intf, result in self.results['flap'].items():
            report.append(f"  {intf}:")
            report.append(f"    Convergence: {result['convergence_time']:.1f}s")
            report.append(f"    Recovery: {result['recovery_time']:.1f}s")

        return "\n".join(report)

# Usage
test = OspfScaleTest(dut='192.168.1.1', expected_routes=1000, expected_ecmp=4)
test.verify_route_installation()
test.monitor_resources(duration=300)
test.test_adjacency_flap('Ethernet0')
print(test.generate_report())
```

---

## References

- **Testbed Configuration**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_5node_ecmp_scale.yaml`
- **Test ID**: 2.4.5
- **Test Category**: ECMP - OSPF Route Scalability
- **Priority**: High
- **Automation**: Highly recommended
- **Related Test Cases**:
  - TC_ECMP_2.4.4 (OSPF ECMP Basic)
  - TC_ECMP_2.4.1 (Basic ECMP)
- **Related Standards**:
  - RFC 2328 (OSPF Version 2)
  - RFC 2991 (Multipath Issues)
  - RFC 4915 (OSPF Multiple Interfaces)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 2.4.5 - Scalability with many OSPF ECMP routes
