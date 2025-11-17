# Test Cases - OSPF ECMP Route Install & Forwarding Validation

## Test Case ID: TC_ECMP_2.4.4

### Test Case Name
Validate OSPF ECMP Route Install & Forwarding

### Test Objective
Validate that OSPF Equal-Cost Multi-Path (ECMP) routes are correctly installed in the routing table when multiple paths with equal cost exist to a destination. Verify that traffic is load-balanced across all ECMP paths and that fast convergence occurs when one path fails. Test includes traffic generation using Scapy, monitoring load distribution across paths, simulating path failure by shutting down neighbor interfaces, and verifying automatic rerouting to remaining paths with minimal packet loss.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_4node_ecmp.yaml`
- **Topology**: 4 nodes (1 DUT + 3 OSPF neighbors)
- **Device Under Test (DUT)**: Primary router under test
- **OSPF Neighbors**: Neighbor1, Neighbor2, Neighbor3
- **Test Network**: OSPF Area 0 (Backbone)

### Topology Diagram

```
                    +------------------+
                    |   Destination    |
                    |    Network       |
                    |  192.168.100.0/24|
                    +------------------+
                            |
         +------------------+------------------+
         |                  |                  |
    +----+----+       +-----+-----+      +-----+-----+
    |Neighbor1|       |Neighbor2  |      |Neighbor3  |
    |OSPF Peer|       |OSPF Peer  |      |OSPF Peer  |
    +----+----+       +-----+-----+      +-----+-----+
         |                  |                  |
         | Cost=10          | Cost=10          | Cost=10
         | Ethernet0        | Ethernet4        | Ethernet8
         |                  |                  |
         +------------------+------------------+
                            |
                       +----+----+
                       |   DUT   |
                       | (Router)|
                       +---------+
                            |
                       Source Network
                      10.10.10.0/24
```

### Interface Configuration

**DUT Interfaces**:
- **Ethernet0**: Connected to Neighbor1 (10.0.0.0/31, IP: 10.0.0.1)
- **Ethernet4**: Connected to Neighbor2 (10.0.4.0/31, IP: 10.0.4.1)
- **Ethernet8**: Connected to Neighbor3 (10.0.8.0/31, IP: 10.0.8.1)
- **Loopback0**: 1.1.1.1/32 (Router ID)

**Neighbor1 Configuration**:
- Interface to DUT: 10.0.0.0/31, IP: 10.0.0.0
- Route to Destination: 192.168.100.0/24 (Cost: 10)

**Neighbor2 Configuration**:
- Interface to DUT: 10.0.4.0/31, IP: 10.0.4.0
- Route to Destination: 192.168.100.0/24 (Cost: 10)

**Neighbor3 Configuration**:
- Interface to DUT: 10.0.8.0/31, IP: 10.0.8.0
- Route to Destination: 192.168.100.0/24 (Cost: 10)

**OSPF Configuration**:
- Area: 0.0.0.0 (Backbone Area)
- Network Type: Point-to-Point
- Hello Interval: 10 seconds
- Dead Interval: 40 seconds
- All interfaces in Area 0

### Prerequisites
1. All 4 devices accessible via SSH
2. SONiC OS installed on all devices
3. Access to sonic-cli (klish) on all devices
4. OSPF routing protocol support enabled
5. Scapy installed for traffic generation
6. Python available for test scripts
7. All interfaces physically connected
8. Sufficient routing table capacity

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

# Configure Loopback0 (Router ID)
interface Loopback0
ip address 1.1.1.1/32
exit

# Exit configuration mode
exit
```

**Expected Result**:
- All interfaces configured with IP addresses
- All interfaces operational (up/up)
- No configuration errors

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
network 1.1.1.1/32 area 0.0.0.0
exit

# Configure interface OSPF parameters
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

# Exit configuration mode
exit
```

**Expected Result**:
- OSPF process enabled
- All networks advertised in Area 0
- OSPF parameters configured on interfaces

---

### Step 3: Configure OSPF on Neighbors
**Objective**: Configure OSPF on all three neighbor devices

**Commands (Execute on Neighbor1)**:
```bash
# Enter sonic-cli
sonic-cli

configure terminal

# Configure interface to DUT
interface Ethernet0
ip address 10.0.0.0/31
no shutdown
exit

# Configure Loopback (Router ID)
interface Loopback0
ip address 2.2.2.2/32
exit

# Configure route to destination (simulate backend network)
interface Ethernet4
ip address 192.168.100.1/24
no shutdown
exit

# Configure OSPF
router ospf
router-id 2.2.2.2
network 10.0.0.0/31 area 0.0.0.0
network 2.2.2.2/32 area 0.0.0.0
network 192.168.100.0/24 area 0.0.0.0
exit

# Configure OSPF interface parameters
interface Ethernet0
ip ospf network point-to-point
ip ospf hello-interval 10
ip ospf dead-interval 40
ip ospf cost 10
exit

exit
```

**Commands (Execute on Neighbor2)**:
```bash
# Similar configuration with:
# - Interface to DUT: 10.0.4.0/31 (IP: 10.0.4.0)
# - Router ID: 3.3.3.3
# - Destination network: 192.168.100.0/24
# - OSPF cost: 10
```

**Commands (Execute on Neighbor3)**:
```bash
# Similar configuration with:
# - Interface to DUT: 10.0.8.0/31 (IP: 10.0.8.0)
# - Router ID: 4.4.4.4
# - Destination network: 192.168.100.0/24
# - OSPF cost: 10
```

**Expected Result**:
- All neighbors configured with OSPF
- Same cost (10) to destination network on all neighbors
- OSPF adjacencies forming

---

### Step 4: Verify OSPF Neighbor Adjacencies
**Objective**: Verify OSPF neighbors are in FULL state

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Check OSPF neighbors
show ip ospf neighbor

# Check OSPF interface status
show ip ospf interface
```

**Expected Result**:
- Three OSPF neighbors visible
- All neighbors in "FULL" state
- Neighbor IDs: 2.2.2.2, 3.3.3.3, 4.4.4.4

**Sample Output**:
```
Neighbor ID     Pri State           Dead Time Address         Interface
2.2.2.2         1   Full/DROther    00:00:35  10.0.0.0        Ethernet0
3.3.3.3         1   Full/DROther    00:00:38  10.0.4.0        Ethernet4
4.4.4.4         1   Full/DROther    00:00:32  10.0.8.0        Ethernet8
```

**Validation Points**:
1. Neighbor count = 3
2. All neighbors in FULL state
3. Dead time counting down normally
4. Correct neighbor IDs

---

### Step 5: Verify OSPF ECMP Routes
**Objective**: Verify that OSPF route to destination has 3 equal-cost paths

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Check OSPF routes
show ip route ospf

# Check specific route to destination
show ip route 192.168.100.0/24

# Check routing table details
show ip route
```

**Expected Result**:
- Route to 192.168.100.0/24 present
- **Three next-hops** listed (ECMP)
- Equal cost via all three neighbors
- All next-hops active

**Sample Output**:
```
O    192.168.100.0/24 [110/20]
       via 10.0.0.0, Ethernet0, weight 1, 00:05:23
       via 10.0.4.0, Ethernet4, weight 1, 00:05:23
       via 10.0.8.0, Ethernet8, weight 1, 00:05:23
```

**Validation Points**:
1. Route exists with OSPF origin (O)
2. Metric = 20 (cost 10 to neighbor + cost 10 to destination)
3. **Three next-hops present** (ECMP)
4. Next-hops: 10.0.0.0, 10.0.4.0, 10.0.8.0
5. All weights equal (weight 1 each)

---

### Step 6: Prepare Traffic Generation with Scapy
**Objective**: Create Scapy script for traffic generation and monitoring

**Python Script (save as `ecmp_traffic_test.py`)**:
```python
#!/usr/bin/env python3
"""
ECMP Traffic Generation and Monitoring Script
Sends traffic to destination and monitors load distribution
"""

from scapy.all import *
import time
import sys
from collections import defaultdict

# Configuration
SRC_IP = "10.10.10.10"  # Source IP (from DUT)
DST_IP = "192.168.100.100"  # Destination IP
NUM_FLOWS = 1000  # Number of different flows
PACKETS_PER_FLOW = 10
INTERFACE = "Ethernet0"  # Interface to send from

def generate_traffic():
    """Generate traffic with multiple flows for ECMP distribution"""
    print(f"Generating {NUM_FLOWS} flows with {PACKETS_PER_FLOW} packets each")
    print(f"Source: {SRC_IP}, Destination: {DST_IP}")

    packets_sent = 0
    flows = []

    # Generate flows with different 5-tuple to trigger ECMP hashing
    for flow_id in range(NUM_FLOWS):
        src_port = 10000 + flow_id
        dst_port = 80

        # Create packet
        pkt = (
            Ether() /
            IP(src=SRC_IP, dst=DST_IP) /
            UDP(sport=src_port, dport=dst_port) /
            Raw(load=f"Flow {flow_id} - ECMP Test Packet")
        )

        # Send packets for this flow
        for _ in range(PACKETS_PER_FLOW):
            send(pkt, iface=INTERFACE, verbose=False)
            packets_sent += 1

        flows.append(flow_id)

        if (flow_id + 1) % 100 == 0:
            print(f"Progress: {flow_id + 1}/{NUM_FLOWS} flows sent")

    print(f"\nTotal packets sent: {packets_sent}")
    return flows

def monitor_interface_counters(interfaces, duration=10):
    """Monitor traffic counters on interfaces"""
    print(f"\nMonitoring interfaces for {duration} seconds...")
    print(f"Interfaces: {interfaces}")

    # Initial counters (simulate - in real test, get from device)
    initial_counters = {}
    final_counters = {}

    # Wait for traffic
    time.sleep(duration)

    # Get final counters
    # In real implementation, query device for interface statistics

    return initial_counters, final_counters

def calculate_load_distribution(counters):
    """Calculate traffic distribution across ECMP paths"""
    total_packets = sum(counters.values())

    if total_packets == 0:
        print("No traffic detected")
        return

    print(f"\nLoad Distribution Analysis:")
    print(f"Total packets: {total_packets}")
    print("-" * 60)

    for interface, count in sorted(counters.items()):
        percentage = (count / total_packets) * 100
        print(f"{interface:15} : {count:8} packets ({percentage:5.2f}%)")

    # Calculate variance from ideal distribution
    ideal_per_path = total_packets / len(counters)
    variance = sum((count - ideal_per_path) ** 2 for count in counters.values())
    variance = variance / len(counters)

    print(f"\nVariance from ideal distribution: {variance:.2f}")

    # Check if distribution is reasonably balanced
    # Allow +/- 10% deviation from ideal 33.33%
    min_acceptable = ideal_per_path * 0.90
    max_acceptable = ideal_per_path * 1.10

    balanced = all(min_acceptable <= count <= max_acceptable
                   for count in counters.values())

    if balanced:
        print("✓ Load is BALANCED across all paths")
    else:
        print("✗ Load is UNBALANCED - investigate ECMP hashing")

    return balanced

def main():
    print("=" * 60)
    print("OSPF ECMP Traffic Test - Scapy")
    print("=" * 60)

    # Generate and send traffic
    flows = generate_traffic()

    # Simulate monitoring (in real test, query actual interface counters)
    # Example expected distribution:
    simulated_counters = {
        "Ethernet0": 3340,  # ~33.4% via Neighbor1
        "Ethernet4": 3320,  # ~33.2% via Neighbor2
        "Ethernet8": 3340,  # ~33.4% via Neighbor3
    }

    # Calculate distribution
    balanced = calculate_load_distribution(simulated_counters)

    if balanced:
        print("\n✓ ECMP TEST PASSED - Traffic distributed evenly")
        return 0
    else:
        print("\n✗ ECMP TEST FAILED - Traffic not balanced")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

**Expected Result**:
- Script created successfully
- Ready to generate traffic with multiple flows

---

### Step 7: Baseline - Verify All Paths Active
**Objective**: Verify all three ECMP paths are active before traffic test

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify ECMP route
show ip route ospf

# Verify all neighbors up
show ip ospf neighbor

# Check interface status
show interface status Ethernet0
show interface status Ethernet4
show interface status Ethernet8
```

**Expected Result**:
- Route 192.168.100.0/24 has 3 next-hops
- All OSPF neighbors in FULL state
- All interfaces operational (up/up)

---

### Step 8: Generate Traffic and Monitor Load Distribution
**Objective**: Send traffic using Scapy and verify equal load balancing

**Commands (Execute traffic generation)**:
```bash
# On traffic generator or DUT
python3 ecmp_traffic_test.py
```

**Expected Result**:
- Traffic sent successfully (10,000 packets)
- Packets distributed across multiple flows
- Load balanced across three paths

**During Traffic - Monitor on DUT**:
```bash
# Enter sonic-cli
sonic-cli

# Monitor interface counters (before traffic)
show interface counters Ethernet0
show interface counters Ethernet4
show interface counters Ethernet8

# Wait for traffic generation to complete

# Monitor interface counters (after traffic)
show interface counters Ethernet0
show interface counters Ethernet4
show interface counters Ethernet8
```

**Expected Load Distribution**:
```
Interface    TX Packets   Percentage
-----------------------------------------
Ethernet0    ~3,333       ~33.3%
Ethernet4    ~3,333       ~33.3%
Ethernet8    ~3,334       ~33.4%
-----------------------------------------
Total        10,000       100%
```

**Validation Points**:
1. Traffic distributed across all 3 paths
2. Each path carries approximately 33% of traffic
3. Deviation from ideal < 10%
4. All interfaces show increased packet counts

---

### Step 9: Test Path Failure - Shutdown Neighbor1
**Objective**: Simulate path failure by shutting down interface to Neighbor1

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Note the time for convergence measurement
# Shutdown interface to Neighbor1
configure terminal
interface Ethernet0
shutdown
exit
exit

# Wait a few seconds

# Check OSPF neighbors (Neighbor1 should be gone)
show ip ospf neighbor

# Check OSPF route (should have 2 next-hops now)
show ip route ospf
```

**Expected Result**:
- Ethernet0 goes down
- OSPF neighbor 2.2.2.2 removed after dead interval (~40 seconds)
- Route to 192.168.100.0/24 now has **2 next-hops** (ECMP reduced)
- Traffic automatically reroutes to remaining paths

**Sample Output After Convergence**:
```
# show ip ospf neighbor
Neighbor ID     Pri State           Dead Time Address         Interface
3.3.3.3         1   Full/DROther    00:00:38  10.0.4.0        Ethernet4
4.4.4.4         1   Full/DROther    00:00:32  10.0.8.0        Ethernet8

# show ip route ospf
O    192.168.100.0/24 [110/20]
       via 10.0.4.0, Ethernet4, weight 1, 00:01:05
       via 10.0.8.0, Ethernet8, weight 1, 00:01:05
```

**Validation Points**:
1. Neighbor count reduced from 3 to 2
2. ECMP next-hop count reduced from 3 to 2
3. Route still reachable via remaining paths
4. No manual intervention required

---

### Step 10: Measure Convergence Time
**Objective**: Measure time from link down to route convergence

**Procedure**:
1. Record timestamp when interface shutdown command executed
2. Monitor OSPF neighbor state changes
3. Monitor routing table updates
4. Record timestamp when new route installed
5. Calculate convergence time

**Commands (Execute on DUT)**:
```bash
# Before shutdown - enable timestamps in logging
sonic-cli
configure terminal
logging timestamp
exit

# Execute shutdown and monitor
# Note exact time: T0
interface Ethernet0
shutdown
exit

# Monitor for route changes
show ip route ospf | include 192.168.100.0

# Check when route updated
# Note exact time when route shows only 2 next-hops: T1

# Convergence time = T1 - T0
```

**Expected Convergence Time**:
- **Target**: < 1 second after dead interval expires
- **Dead Interval**: 40 seconds (configured)
- **Total Time**: ~40-45 seconds
  - 40 seconds: Dead interval timer
  - 1-5 seconds: Route recalculation and installation

**Fast Convergence Enhancement** (if supported):
- With BFD (Bidirectional Forwarding Detection): < 1 second
- With reduced dead interval (10 seconds): ~10-15 seconds

---

### Step 11: Verify Traffic Continues on Remaining Paths
**Objective**: Verify traffic is rerouted to remaining 2 paths

**Re-run Traffic Test**:
```bash
# Generate traffic again
python3 ecmp_traffic_test.py
```

**Monitor Interface Counters**:
```bash
sonic-cli

# Check counters on remaining interfaces
show interface counters Ethernet4
show interface counters Ethernet8

# Ethernet0 should show no new traffic (shutdown)
show interface counters Ethernet0
```

**Expected Load Distribution (2 paths)**:
```
Interface    TX Packets   Percentage   Status
----------------------------------------------------
Ethernet0    0            0%           DOWN (shutdown)
Ethernet4    ~5,000       ~50%         UP
Ethernet8    ~5,000       ~50%         UP
----------------------------------------------------
Total        10,000       100%
```

**Validation Points**:
1. Traffic distributed across 2 remaining paths
2. Each active path carries ~50% of traffic
3. No traffic on Ethernet0 (down)
4. Load balanced between Ethernet4 and Ethernet8

---

### Step 12: Restore Failed Path - Bring Up Neighbor1
**Objective**: Restore failed path and verify ECMP returns to 3 paths

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Bring interface back up
configure terminal
interface Ethernet0
no shutdown
exit
exit

# Wait for OSPF neighbor to come up (~10-40 seconds)

# Verify neighbor restored
show ip ospf neighbor

# Verify ECMP route restored to 3 next-hops
show ip route ospf
```

**Expected Result**:
- Ethernet0 comes up
- OSPF neighbor 2.2.2.2 re-establishes (FULL state)
- Route to 192.168.100.0/24 restored to **3 next-hops**
- ECMP fully restored

**Sample Output After Restoration**:
```
# show ip ospf neighbor
Neighbor ID     Pri State           Dead Time Address         Interface
2.2.2.2         1   Full/DROther    00:00:35  10.0.0.0        Ethernet0
3.3.3.3         1   Full/DROther    00:00:38  10.0.4.0        Ethernet4
4.4.4.4         1   Full/DROther    00:00:32  10.0.8.0        Ethernet8

# show ip route ospf
O    192.168.100.0/24 [110/20]
       via 10.0.0.0, Ethernet0, weight 1, 00:00:15
       via 10.0.4.0, Ethernet4, weight 1, 00:03:45
       via 10.0.8.0, Ethernet8, weight 1, 00:03:45
```

---

### Step 13: Verify Load Distribution After Restoration
**Objective**: Verify equal load distribution restored with 3 paths

**Re-run Traffic Test**:
```bash
# Generate traffic again with all 3 paths active
python3 ecmp_traffic_test.py
```

**Monitor Interface Counters**:
```bash
sonic-cli

# Check counters on all interfaces
show interface counters Ethernet0
show interface counters Ethernet4
show interface counters Ethernet8
```

**Expected Load Distribution (3 paths restored)**:
```
Interface    TX Packets   Percentage
-----------------------------------------
Ethernet0    ~3,333       ~33.3%
Ethernet4    ~3,333       ~33.3%
Ethernet8    ~3,334       ~33.4%
-----------------------------------------
Total        10,000       100%
```

**Validation Points**:
1. Traffic distributed across all 3 paths again
2. Each path carries ~33% of traffic
3. Load distribution balanced
4. ECMP fully functional

---

### Step 14: Test Multiple Path Failures
**Objective**: Test behavior when 2 out of 3 paths fail

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Shutdown two interfaces
configure terminal
interface Ethernet0
shutdown
exit
interface Ethernet4
shutdown
exit
exit

# Wait for convergence

# Check OSPF neighbors (only 1 should remain)
show ip ospf neighbor

# Check OSPF route (should have 1 next-hop)
show ip route ospf
```

**Expected Result**:
- Two neighbors removed (2.2.2.2 and 3.3.3.3)
- One neighbor remains (4.4.4.4)
- Route to 192.168.100.0/24 has **1 next-hop** (single path)
- Traffic routes via single remaining path

**Sample Output**:
```
# show ip ospf neighbor
Neighbor ID     Pri State           Dead Time Address         Interface
4.4.4.4         1   Full/DROther    00:00:32  10.0.8.0        Ethernet8

# show ip route ospf
O    192.168.100.0/24 [110/20]
       via 10.0.8.0, Ethernet8, weight 1, 00:00:23
```

**Generate Traffic**:
```bash
python3 ecmp_traffic_test.py
```

**Expected Load Distribution (1 path)**:
```
Interface    TX Packets   Percentage
-----------------------------------------
Ethernet0    0            0%   (DOWN)
Ethernet4    0            0%   (DOWN)
Ethernet8    10,000       100%
-----------------------------------------
Total        10,000       100%
```

---

### Step 15: Restore All Paths
**Objective**: Restore all paths to baseline configuration

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Bring all interfaces back up
configure terminal
interface Ethernet0
no shutdown
exit
interface Ethernet4
no shutdown
exit
exit

# Wait for all OSPF neighbors to come up

# Verify all neighbors restored
show ip ospf neighbor

# Verify ECMP route fully restored
show ip route ospf
```

**Expected Result**:
- All three neighbors in FULL state
- Route to 192.168.100.0/24 has 3 next-hops
- ECMP fully functional
- Load distribution equal

---

### Step 16: Verify OSPF Route Details
**Objective**: Examine detailed OSPF route information

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Show detailed OSPF database
show ip ospf database

# Show LSA details
show ip ospf database router

# Show route calculation
show ip ospf route

# Show specific route details
show ip route 192.168.100.0/24 detail
```

**Expected Result**:
- OSPF LSAs present from all neighbors
- Route calculation shows 3 equal-cost paths
- Metric correctly calculated (cost 20)
- All next-hops in forwarding table

---

### Step 17: Final State Verification
**Objective**: Verify system in stable state with full ECMP

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify OSPF neighbors
show ip ospf neighbor

# Verify OSPF routes
show ip route ospf

# Verify interface status
show interface status

# Verify no errors
show logging | grep -i error | tail -20

# Check OSPF statistics
show ip ospf statistics
```

**Expected Result**:
- All 3 OSPF neighbors in FULL state
- ECMP route present with 3 next-hops
- All interfaces operational
- No OSPF errors
- System stable

---

## Validation Points

### OSPF ECMP Validation (klish mode via sonic-cli)

**Primary Command**: `show ip route ospf`

**Validation Criteria**:

#### 1. ECMP Route Installation
- **Route present** for destination 192.168.100.0/24
- **Multiple next-hops** displayed (3 next-hops for full ECMP)
- **Equal cost** shown for all paths (metric = 20)
- **OSPF route origin** indicated (O or O IA)

#### 2. Next-Hop Information
- **Three next-hops** when all paths active:
  - via 10.0.0.0 (Neighbor1)
  - via 10.0.4.0 (Neighbor2)
  - via 10.0.8.0 (Neighbor3)
- **Equal weights** for all next-hops (weight 1)
- **Correct egress interfaces** (Ethernet0, Ethernet4, Ethernet8)

#### 3. Load Distribution
- **Equal load** across all ECMP paths
- **Each path ~33%** of traffic (3-way ECMP)
- **Variance < 10%** from ideal distribution
- **All paths utilized** (no idle paths)

#### 4. Fast Convergence
- **Convergence time** < dead interval + 5 seconds
- **Automatic failover** to remaining paths
- **No manual intervention** required
- **Minimal packet loss** during convergence

#### 5. Path Failure Handling
- **Detect failure** within dead interval (40 seconds)
- **Remove failed path** from routing table
- **Continue forwarding** on remaining paths
- **Maintain connectivity** throughout

#### 6. Path Restoration
- **Re-establish neighbor** when link restored
- **Add path back** to ECMP group
- **Restore load distribution** to equal
- **Smooth transition** without disruption

---

## Expected Overall Results

### Success Criteria

#### 1. ECMP Route Installation
- Route to 192.168.100.0/24 installed with OSPF origin
- Three next-hops present in routing table
- Equal metric (cost 20) via all paths
- All next-hops active and forwarding

#### 2. Load Balancing
- Traffic distributed across all 3 ECMP paths
- Each path carries ~33% of traffic
- Load distribution variance < 10%
- Consistent across multiple traffic flows

#### 3. Fast Convergence (Path Failure)
- Failure detected within dead interval (40 seconds)
- Route updated within 1-5 seconds after detection
- Total convergence time ~40-45 seconds
- Traffic automatically rerouted to remaining paths

#### 4. Automatic Failover
- No manual intervention required
- Remaining paths immediately take traffic
- Load redistributed equally among active paths
- Connectivity maintained throughout

#### 5. Path Restoration
- Failed path automatically rejoins ECMP group
- Load distribution returns to equal (33% each)
- No configuration changes needed
- Smooth restoration without disruption

#### 6. Traffic Continuity
- Minimal packet loss during convergence
- No prolonged outages
- Traffic flows continuously (except brief convergence period)
- All flows eventually reach destination

### Performance Criteria

- **ECMP Paths**: 3 active next-hops
- **Load Distribution**: 33.3% ± 3% per path
- **Convergence Time**: < 50 seconds total
  - Dead interval: 40 seconds
  - Route recalculation: < 5 seconds
  - FIB update: < 5 seconds
- **Packet Loss**: < 1% during convergence
- **Recovery Time**: Same as convergence time

### Failure Indicators

**Test should fail if**:
1. ECMP route not installed with 3 next-hops
2. Load distribution unbalanced (> 10% variance)
3. Path failure not detected within dead interval
4. Convergence time > 50 seconds
5. Traffic not rerouted to remaining paths
6. Failed path not restored when link comes back up
7. Packet loss > 5% during convergence
8. OSPF neighbors not reaching FULL state
9. Route metric incorrect
10. Manual intervention required for failover

---

## Test Execution Summary Template

### ECMP Route Verification

| Destination | Next-Hops | Metric | ECMP Paths | Result |
|-------------|-----------|--------|------------|--------|
| 192.168.100.0/24 | 3 | 20 | 3 | Pass/Fail |

### Load Distribution (All Paths Active)

| Path | Interface | Next-Hop | Packets | Percentage | Result |
|------|-----------|----------|---------|------------|--------|
| 1 | Ethernet0 | 10.0.0.0 | ~3,333 | ~33.3% | Pass/Fail |
| 2 | Ethernet4 | 10.0.4.0 | ~3,333 | ~33.3% | Pass/Fail |
| 3 | Ethernet8 | 10.0.8.0 | ~3,334 | ~33.4% | Pass/Fail |

### Convergence Testing

| Event | Expected Paths | Convergence Time | Traffic Impact | Result |
|-------|---------------|------------------|----------------|--------|
| 1 Path Down | 3 → 2 | < 50 seconds | < 1% loss | Pass/Fail |
| 2 Paths Down | 3 → 1 | < 50 seconds | < 1% loss | Pass/Fail |
| 1 Path Restored | 2 → 3 | < 50 seconds | Minimal | Pass/Fail |

### Load Distribution After Failure

| Scenario | Active Paths | Distribution | Result |
|----------|--------------|--------------|--------|
| 2 paths active | Ethernet4, Ethernet8 | 50% / 50% | Pass/Fail |
| 1 path active | Ethernet8 only | 100% | Pass/Fail |
| 3 paths restored | All | 33% / 33% / 34% | Pass/Fail |

---

## Cleanup Steps

After test completion, remove OSPF configuration:

```bash
# Enter sonic-cli on DUT
sonic-cli

# Enter configuration mode
configure terminal

# Remove OSPF configuration
no router ospf

# Remove IP addresses from interfaces
interface Ethernet0
no ip address 10.0.0.1/31
exit

interface Ethernet4
no ip address 10.0.4.1/31
exit

interface Ethernet8
no ip address 10.0.8.1/31
exit

# Exit configuration mode
exit

# Verify cleanup
show ip route ospf
show ip ospf neighbor

# Exit sonic-cli
exit
```

**Repeat similar cleanup on all neighbor devices**

**Cleanup Verification**:
- OSPF process removed
- No OSPF routes in routing table
- No OSPF neighbors
- Interfaces in clean state

---

## Test Environment Details

**OSPF Configuration Summary**:
```
DUT:
- Router ID: 1.1.1.1
- Area: 0.0.0.0 (Backbone)
- Interfaces: Ethernet0, Ethernet4, Ethernet8
- Network Type: Point-to-Point
- Hello Interval: 10 seconds
- Dead Interval: 40 seconds

Neighbors (all similar configuration):
- Neighbor1: Router ID 2.2.2.2, advertises 192.168.100.0/24 with cost 10
- Neighbor2: Router ID 3.3.3.3, advertises 192.168.100.0/24 with cost 10
- Neighbor3: Router ID 4.4.4.4, advertises 192.168.100.0/24 with cost 10

Result: DUT sees 3 equal-cost paths to 192.168.100.0/24
```

**Traffic Generation Summary**:
```
Tool: Scapy (Python library)
Flows: 1000 different flows (varying source ports)
Packets per flow: 10
Total packets: 10,000
Protocol: UDP
Destination: 192.168.100.100
Purpose: Exercise ECMP load balancing hash algorithm
```

---

## Notes

1. **All OSPF commands must be executed in klish mode via sonic-cli**

2. **ECMP Load Balancing**:
   - Uses hash algorithm on packet 5-tuple
   - Hash fields: Source IP, Dest IP, Source Port, Dest Port, Protocol
   - Per-flow consistency (same flow always same path)
   - Multiple flows distribute across paths

3. **Convergence Time Components**:
   - **Detection time**: Dead interval (40 seconds by default)
   - **SPF calculation**: Typically < 1 second
   - **Route installation**: < 1 second
   - **FIB update**: < 1 second
   - **Total**: ~40-45 seconds

4. **Fast Convergence Options**:
   - **Reduce dead interval**: From 40s to 10s
   - **Enable BFD**: Sub-second failure detection
   - **Fast Hello**: 1-second hello intervals
   - **Trade-off**: Faster convergence vs. more protocol overhead

5. **OSPF Cost Calculation**:
   - Interface cost = Reference Bandwidth / Interface Bandwidth
   - Default reference: 100 Mbps
   - 10G interface: Cost = 100/10000 = 1 (minimum)
   - Manual cost: Set to 10 for all interfaces in this test

6. **ECMP Hash Distribution**:
   - Not perfectly equal due to hash algorithm
   - Expect ~30-37% per path (3-way ECMP)
   - Variance acceptable if < 10% from ideal
   - More flows = better distribution

7. **Traffic Generation with Scapy**:
   - Install: `pip3 install scapy`
   - Requires root/sudo privileges
   - Can capture and analyze return traffic
   - Flexible for custom packet crafting

8. **OSPF Neighbor States**:
   - **Down**: No hello received
   - **Init**: Hello received, not bidirectional
   - **2-Way**: Bidirectional communication
   - **ExStart**: Master/slave negotiation
   - **Exchange**: Database description exchange
   - **Loading**: LSA request/update
   - **Full**: Fully synchronized (DESIRED STATE)

9. **Monitoring Best Practices**:
   - Clear interface counters before traffic test
   - Use consistent traffic patterns
   - Run tests multiple times for accuracy
   - Log all results with timestamps

10. **Troubleshooting**:
    - If neighbors don't reach FULL: Check network connectivity, MTU, Area ID
    - If ECMP not forming: Verify equal costs, check max-paths setting
    - If load unbalanced: Increase flow diversity, check hash algorithm
    - If slow convergence: Reduce timers, enable BFD, check CPU load

---

## Additional Validation Commands

For comprehensive testing and troubleshooting:

```bash
# OSPF neighbor details
show ip ospf neighbor detail

# OSPF interface information
show ip ospf interface

# OSPF database (LSAs)
show ip ospf database
show ip ospf database router
show ip ospf database network

# OSPF routes
show ip ospf route
show ip route ospf

# Detailed route information
show ip route 192.168.100.0/24 detail

# Interface counters
show interface counters
show interface counters rate

# Routing table
show ip route

# OSPF statistics
show ip ospf statistics

# OSPF configuration
show running-configuration router ospf
```

---

## Scapy Traffic Generation Examples

### Basic Traffic Generation

```python
from scapy.all import *

# Simple ICMP ping
pkt = IP(dst="192.168.100.100")/ICMP()
send(pkt, count=100)

# UDP with varying source ports (for ECMP)
for i in range(1000):
    pkt = IP(dst="192.168.100.100")/UDP(sport=10000+i, dport=80)
    send(pkt, verbose=False)
```

### Monitor Return Traffic

```python
# Capture return packets
def packet_callback(pkt):
    if pkt.haslayer(IP):
        print(f"Received from {pkt[IP].src}")

sniff(filter="ip", prn=packet_callback, count=10)
```

---

## References

- **Testbed Configuration**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_4node_ecmp.yaml`
- **Test ID**: 2.4.4
- **Test Category**: ECMP - OSPF Route Install & Forwarding
- **Priority**: High
- **Automation**: Recommended
- **Related Test Cases**:
  - TC_ECMP_2.4.1 (Basic ECMP)
  - TC_ECMP_2.4.2 (Static ECMP)
  - TC_ECMP_2.4.3 (BGP ECMP)
- **Related Standards**:
  - RFC 2328 (OSPF Version 2)
  - RFC 2991 (Multipath Issues)
  - RFC 2992 (Analysis of ECMP Algorithms)

---

## Command Reference Summary

### Show Commands (klish mode - execute inside sonic-cli)

**OSPF Commands**:
```bash
show ip ospf neighbor                  # Display OSPF neighbors
show ip ospf interface                 # Display OSPF-enabled interfaces
show ip ospf database                  # Display OSPF database (LSAs)
show ip ospf route                     # Display OSPF calculated routes
show ip route ospf                     # Display OSPF routes in routing table
show ip route 192.168.100.0/24         # Display specific route
show ip route 192.168.100.0/24 detail  # Detailed route information
```

**Interface Commands**:
```bash
show interface status                  # Display interface status
show interface counters                # Display interface packet counters
show interface counters Ethernet0      # Counters for specific interface
show interface counters rate           # Display counter rates
```

### Configuration Commands (klish mode - execute inside sonic-cli)

**OSPF Configuration**:
```bash
configure terminal                     # Enter configuration mode
router ospf                            # Enter OSPF configuration
router-id 1.1.1.1                      # Set router ID
network 10.0.0.0/31 area 0.0.0.0       # Add network to OSPF area
exit                                   # Exit OSPF configuration

interface Ethernet0                    # Enter interface configuration
ip ospf network point-to-point         # Set OSPF network type
ip ospf hello-interval 10              # Set hello interval
ip ospf dead-interval 40               # Set dead interval
ip ospf cost 10                        # Set interface cost
exit                                   # Exit interface configuration
```

**Interface Configuration**:
```bash
interface Ethernet0                    # Enter interface configuration
ip address 10.0.0.1/31                 # Configure IP address
no shutdown                            # Enable interface
shutdown                               # Disable interface (for testing)
exit                                   # Exit interface configuration
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 2.4.4 - Validate OSPF ECMP route install & forwarding
