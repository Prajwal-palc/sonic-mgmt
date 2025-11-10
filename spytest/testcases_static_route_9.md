# Test Case: ECMP Route Validation (Static) IPv6 Static Route Configuration

**Test Case ID:** TC-IP-STATIC-IPV6-009
**Feature:** IPv6 Static Routing
**Sub-feature:** ECMP (Equal-Cost Multi-Path) Route Validation
**Test Plan Section:** 2.1.9

---

## Test Objective

Configure and verify ECMP (Equal-Cost Multi-Path) route validation for IPv6 static routes on DUT. Validate that multiple next-hops for the same destination prefix are installed correctly, load balancing distributes traffic across multiple paths, and the system handles next-hop failures gracefully by automatically failing over to remaining active paths. Test enable/disable functionality at both global configuration mode and interface mode, and verify route persistence and recovery.

---

## Topology Requirements

**Topology:** Three-node (D1-D2-D3) for ECMP validation
**Testbed File:** `/home/adminuser/draksha/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
**Supported Platforms:** Hardware and Virtual

**Note:** For ECMP testing with 3 nodes, the testbed may need to be extended from the base 2-node configuration, or ECMP can be simulated using multiple paths via D2 (loopback interfaces or subinterfaces on D2).

```
# Topology - ECMP Configuration with Multiple Next-Hops
# +--------------------------------+                       +--------------------------------+
# |        smic_sonic1 (D1)        |                       |        smic_sonic2 (D2)        |
# |        (DUT - Source)          |                       |     (Intermediate Router)      |
# |                                |   Path 1 (Ethernet4)  |                                |
# | IPv6: 2001:db8:10::1/64        |=======================| IPv6: 2001:db8:10::2/64        |
# |                                |                       |                                |
# |                                |   Path 2 (Ethernet8)  | IPv6: 2001:db8:11::2/64        |
# | IPv6: 2001:db8:11::1/64        |=======================|                                |
# |                                |                       | Loopback: 2001:db8:20::1/128   |
# +--------------------------------+                       +--------------------------------+
#
# Static Route on D1:
#   2001:db8:20::/64 via 2001:db8:10::2  (Next-hop 1 - Path via Ethernet4)
#   2001:db8:20::/64 via 2001:db8:11::2  (Next-hop 2 - Path via Ethernet8)
#
# Both routes have equal cost -> ECMP entry created
# Traffic to 2001:db8:20::/64 load-balanced across both paths
```

**Device Details from Testbed:**
- **D1 (smic_sonic1):** Management IP: 192.168.100.142
- **D2 (smic_sonic2):** Management IP: 192.168.100.97
- **Data Plane Links:** Ethernet4 (existing in testbed), Ethernet8 (may need configuration)

---

## Pre-requisites

1. SONiC devices with IPv6 routing enabled
2. FRR routing daemon running (for static route support)
3. Klish CLI access and Click CLI access
4. Admin/sudo privileges for privileged commands
5. At least two physical/logical paths between D1 and destination network
6. IPv6 forwarding enabled globally and on relevant interfaces
7. Sufficient interface resources for multiple ECMP paths
8. Traffic generation capability for load balancing validation (ping, iperf, or TGen)

---

## Test Variables

Variables should be loaded from: `spytest/vars/routing/static/vars_static_ipv6_ecmp.yaml`

**Recommended variable file structure:**
```yaml
min_topology: ["D1D2:2"]  # Two links between D1 and D2 for ECMP

# ECMP path configuration
ecmp_paths:
  path1:
    D1_interface: Ethernet4
    D1_ipv6: "2001:db8:10::1/64"
    D2_interface: Ethernet4
    D2_ipv6: "2001:db8:10::2/64"

  path2:
    D1_interface: Ethernet8
    D1_ipv6: "2001:db8:11::1/64"
    D2_interface: Ethernet8
    D2_ipv6: "2001:db8:11::2/64"

# Destination network (simulated on D2 loopback)
destination:
  prefix: "2001:db8:20::/64"
  test_ip: "2001:db8:20::1"
  location: "D2 loopback0"
  loopback_config:
    interface: "Loopback0"
    ipv6: "2001:db8:20::1/128"

# ECMP static routes on D1
ecmp_routes:
  route1:
    prefix: "2001:db8:20::/64"
    nexthop: "2001:db8:10::2"
    interface: "Ethernet4"

  route2:
    prefix: "2001:db8:20::/64"
    nexthop: "2001:db8:11::2"
    interface: "Ethernet8"

# Traffic test parameters
traffic:
  ping_count: 100
  ping_interval: 0.2
  stream_duration: 30
  expected_load_balance_tolerance: 0.2  # 20% tolerance (40%-60% split acceptable)
```

---

## Test Case Details

### Phase 1: Environment Setup and Pre-Configuration

**Sub-test 1.1: Configure IPv6 on Path 1 Interfaces**

**Test Steps:**
```bash
# On D1 (smic_sonic1)
configure terminal
interface Ethernet4
ipv6 address 2001:db8:10::1/64
no shutdown
exit
exit

# On D2 (smic_sonic2)
configure terminal
interface Ethernet4
ipv6 address 2001:db8:10::2/64
no shutdown
exit
exit
```

**Validation Commands:**
- `show ipv6 interface Ethernet4`
- `show ipv6 interface brief`
- `show interface status Ethernet4`
- `ping ipv6 2001:db8:10::2` (from D1 to D2)

**Expected Result:**
- Ethernet4 configured with IPv6 on both devices
- Interfaces are operationally up
- Ping between D1 and D2 succeeds on Path 1

---

**Sub-test 1.2: Configure IPv6 on Path 2 Interfaces**

**Test Steps:**
```bash
# On D1
configure terminal
interface Ethernet8
ipv6 address 2001:db8:11::1/64
no shutdown
exit
exit

# On D2
configure terminal
interface Ethernet8
ipv6 address 2001:db8:11::2/64
no shutdown
exit
exit
```

**Validation Commands:**
- `show ipv6 interface Ethernet8`
- `show ipv6 interface brief`
- `show interface status Ethernet8`
- `ping ipv6 2001:db8:11::2` (from D1 to D2)

**Expected Result:**
- Ethernet8 configured with IPv6 on both devices
- Interfaces are operationally up
- Ping between D1 and D2 succeeds on Path 2
- Both paths are independently reachable

---

**Sub-test 1.3: Configure Destination Network on D2**

**Test Steps:**
```bash
# On D2 - Create loopback interface for destination network
configure terminal
interface Loopback0
ipv6 address 2001:db8:20::1/128
no shutdown
exit
exit

# Verify loopback configuration
show ipv6 interface Loopback0
show ipv6 route 2001:db8:20::1
```

**Expected Result:**
- Loopback0 interface created on D2
- IPv6 address 2001:db8:20::1/128 configured
- Local connected route exists in D2's routing table
- Loopback interface is operationally up

---

### Phase 2: Configure ECMP Static Routes

**Sub-test 2.1: Configure First Static Route (Next-Hop 1)**

**Test Steps:**
```bash
# On D1
configure terminal
ipv6 route 2001:db8:20::/64 2001:db8:10::2
exit

# Verify single route installation
show ipv6 route 2001:db8:20::/64
show ipv6 route static
```

**Validation Commands:**
- `show ipv6 route 2001:db8:20::/64`
- `show ipv6 route static`
- `show running-config | include "ipv6 route 2001:db8:20"`
- `sudo vtysh -c "show ipv6 route 2001:db8:20::/64"`

**Expected Result:**
- Single static route to 2001:db8:20::/64 is installed
- Next-hop: 2001:db8:10::2 (via Ethernet4)
- Route type: Static (S)
- Route is active and reachable
- Running-config contains the route command

---

**Sub-test 2.2: Test Reachability with Single Path**

**Test Steps:**
```bash
# On D1 - Test basic reachability before adding ECMP
ping ipv6 2001:db8:20::1 -c 5

# Check which interface is used
show interfaces Ethernet4 counters
show interfaces Ethernet8 counters
```

**Expected Result:**
- Ping to 2001:db8:20::1 succeeds (100% success rate)
- Traffic egresses only via Ethernet4 (Path 1)
- Ethernet4 counters increment (TX packets increase)
- Ethernet8 counters do NOT increment (no traffic on Path 2 yet)

---

**Sub-test 2.3: Configure Second Static Route (Next-Hop 2) - Create ECMP**

**Test Steps:**
```bash
# On D1 - Add second route with equal cost
configure terminal
ipv6 route 2001:db8:20::/64 2001:db8:11::2
exit

# Verify ECMP entry creation
show ipv6 route 2001:db8:20::/64
show ipv6 route static
```

**Validation Commands:**
- `show ipv6 route 2001:db8:20::/64`
- `show ipv6 route static`
- `show running-config | include "ipv6 route 2001:db8:20"`
- `sudo vtysh -c "show ipv6 route 2001:db8:20::/64"`

**Expected Result:**
- **ECMP entry created for 2001:db8:20::/64**
- **Two next-hops appear under the same route:**
  - Next-hop 1: 2001:db8:10::2 via Ethernet4
  - Next-hop 2: 2001:db8:11::2 via Ethernet8
- Both next-hops have equal cost (no preference)
- Route type: Static (S)
- Both routes are active simultaneously
- Running-config shows both route commands

**Example Output:**
```
S>* 2001:db8:20::/64 [1/0] via 2001:db8:10::2, Ethernet4
  *                         via 2001:db8:11::2, Ethernet8
```

---

**Sub-test 2.4: Verify ECMP in Forwarding Table (CEF/FIB)**

**Test Steps:**
```bash
# On D1 - Check forwarding information base
sudo vtysh -c "show ipv6 route 2001:db8:20::/64"
sudo vtysh -c "show ipv6 fib 2001:db8:20::/64"

# Alternative: Check kernel routing table
sudo ip -6 route show 2001:db8:20::/64
```

**Expected Result:**
- FIB (Forwarding Information Base) shows multiple next-hops
- Both next-hops are installed for load sharing
- Kernel routing table reflects ECMP entry
- Load balancing is enabled for this prefix

---

**Sub-test 2.5: Save ECMP Configuration**

**Test Steps:**
```bash
# On D1
write memory

# Verify both routes are saved
show running-config | include "ipv6 route 2001:db8:20"
```

**Expected Result:**
- Configuration saved successfully
- Both static routes persist in running-config
- Routes will survive device reload

---

### Phase 3: ECMP Load Balancing Validation

**Sub-test 3.1: Verify Interface Status Before Traffic Test**

**Test Steps:**
```bash
# On D1 - Check interface operational status
show interface status Ethernet4
show interface status Ethernet8

# Check IPv6 interface status
show ipv6 interface brief | include "Ethernet4\|Ethernet8"

# Record baseline counters
show interfaces Ethernet4 counters
show interfaces Ethernet8 counters
```

**Expected Result:**
- Both Ethernet4 and Ethernet8 are operationally up
- Both interfaces have IPv6 enabled
- Baseline counters recorded for comparison
- No errors or drops on either interface

---

**Sub-test 3.2: Send Ping Traffic and Verify Load Balancing**

**Test Steps:**
```bash
# On D1 - Clear interface counters
sudo sonic-clear counters

# Send multiple pings to trigger ECMP hashing
ping ipv6 2001:db8:20::1 -c 100 -i 0.2

# Immediately check interface counters after ping
show interfaces Ethernet4 counters
show interfaces Ethernet8 counters
```

**Validation Commands:**
- `show interfaces Ethernet4 counters`
- `show interfaces Ethernet8 counters`
- `show interfaces counters | include "Ethernet4\|Ethernet8"`

**Expected Result:**
- Ping succeeds with high success rate (>95%)
- **Both Ethernet4 and Ethernet8 counters increment**
- **Traffic is distributed across both interfaces**
- Load distribution approximately balanced (within 40%-60% range per interface)
- TX packet counts on both interfaces are non-zero
- RX packet counts (ping replies) also distributed

**Note:** Exact distribution depends on ECMP hashing algorithm (per-packet or per-flow). For ICMP ping with varying packet IDs, expect some distribution.

---

**Sub-test 3.3: Test with Traffic Streams (Enhanced Load Balancing)**

**Test Steps:**
```bash
# On D1 - Generate varied traffic to test ECMP hashing
# Option 1: Use multiple ping sessions with different source ports (if available)

# Option 2: Use scripted ping variations
for i in {1..50}; do
  ping ipv6 2001:db8:20::1 -c 2 -i 0.1 &
done
wait

# Check counter distribution
show interfaces Ethernet4 counters detailed
show interfaces Ethernet8 counters detailed
```

**Expected Result:**
- Multiple traffic flows trigger ECMP load balancing
- Both interfaces show significantly increased counters
- Traffic distribution is more balanced with multiple flows
- ECMP hashing spreads flows across available paths
- No significant errors or packet loss

---

**Sub-test 3.4: Verify Load Balancing Statistics**

**Test Steps:**
```bash
# On D1 - Analyze interface statistics
show interfaces Ethernet4 counters | include "TX"
show interfaces Ethernet8 counters | include "TX"

# Calculate distribution percentage
# Expected: Each interface carries 40%-60% of total traffic
```

**Expected Result:**
- TX packet/byte counts on both interfaces
- Load distribution within acceptable tolerance (40%-60% per path)
- No interface is completely idle
- No significant counter errors (CRC, drops, etc.)

---

### Phase 4: ECMP Route Verification Commands

**Sub-test 4.1: Verify Static Route Configuration**

**Test Steps:**
```bash
# On D1
show ipv6 route
show ipv6 route static
show ipv6 route 2001:db8:20::/64
```

**Expected Result:**
1. **`show ipv6 route`**
   - Complete IPv6 routing table displayed
   - ECMP entry for 2001:db8:20::/64 visible

2. **`show ipv6 route static`**
   - Filters to show only static routes
   - Both ECMP routes listed for same prefix

3. **`show ipv6 route 2001:db8:20::/64`**
   - Specific route details shown
   - Multiple next-hops listed:
     - 2001:db8:10::2 via Ethernet4
     - 2001:db8:11::2 via Ethernet8
   - Both marked as active (*)

---

**Sub-test 4.2: Verify Interface Counter Distribution**

**Test Steps:**
```bash
# On D1
show interface counters
show interfaces Ethernet4 counters
show interfaces Ethernet8 counters
```

**Expected Result:**
- Both next-hop interfaces show active traffic
- TX/RX counters indicate bidirectional traffic
- Counters demonstrate load sharing behavior

---

**Sub-test 4.3: Verify Running Configuration**

**Test Steps:**
```bash
# On D1
configure terminal
show running-config | include "ipv6 route"
exit

# Alternative view
show running-config interface Ethernet4
show running-config interface Ethernet8
```

**Expected Result:**
- Running-config shows both static route entries:
  ```
  ipv6 route 2001:db8:20::/64 2001:db8:10::2
  ipv6 route 2001:db8:20::/64 2001:db8:11::2
  ```
- Interface configurations show IPv6 addresses and enabled state

---

**Sub-test 4.4: Verify with sudo vtysh Commands**

**Test Steps:**
```bash
# On D1
sudo vtysh -c "show ipv6 route 2001:db8:20::/64"
sudo vtysh -c "show ipv6 route static"
sudo vtysh -c "show running-config | section ipv6 route"
```

**Expected Result:**
- vtysh output matches standard CLI output
- FRR routing daemon perspective shows ECMP correctly
- Both next-hops installed in FRR routing table

---

**Sub-test 4.5: Verify with Kernel Routing Commands**

**Test Steps:**
```bash
# On D1 - Check kernel routing table
sudo ip -6 route show 2001:db8:20::/64
sudo ip -6 route list

# Check specific route details
sudo ip -6 route get 2001:db8:20::1
```

**Expected Result:**
- Kernel routing table shows ECMP entry
- Multiple nexthop entries for same destination
- Route resolution shows ECMP behavior

---

### Phase 5: Next-Hop Failure Simulation

**Sub-test 5.1: Simulate First Next-Hop Failure (Shutdown Ethernet4)**

**Test Steps:**
```bash
# On D1 - Shutdown first ECMP path
configure terminal
interface Ethernet4
shutdown
exit
exit

# Verify interface status
show interface status Ethernet4
show ipv6 interface brief | include Ethernet4
```

**Validation Commands:**
- `show interface status Ethernet4`
- `show ipv6 route 2001:db8:20::/64`
- `show ipv6 route static`

**Expected Result:**
- Ethernet4 goes to "Down/Down" state
- Interface is administratively disabled
- IPv6 on Ethernet4 becomes inactive

---

**Sub-test 5.2: Verify Automatic Failover to Second Path**

**Test Steps:**
```bash
# On D1 (with Ethernet4 down)
show ipv6 route 2001:db8:20::/64

# Verify only one next-hop is active
show ipv6 route static

# Test connectivity with failover
ping ipv6 2001:db8:20::1 -c 10
```

**Expected Result:**
- **ECMP route automatically updates**
- **Only one next-hop remains active:** 2001:db8:11::2 via Ethernet8
- First next-hop (2001:db8:10::2 via Ethernet4) is removed or marked inactive
- **Ping still succeeds** (traffic uses remaining active path)
- **No manual intervention required for failover**
- Packet loss minimal during transition (maybe 1-2 packets)

**Example Output:**
```
S>* 2001:db8:20::/64 [1/0] via 2001:db8:11::2, Ethernet8
```

---

**Sub-test 5.3: Verify Traffic Uses Only Active Path**

**Test Steps:**
```bash
# On D1 - Clear counters and send traffic
sudo sonic-clear counters

# Send traffic
ping ipv6 2001:db8:20::1 -c 20

# Check counters
show interfaces Ethernet4 counters
show interfaces Ethernet8 counters
```

**Expected Result:**
- Ethernet4 counters do NOT increment (interface is down)
- Ethernet8 counters increment significantly
- 100% of traffic uses Ethernet8 (the only active path)
- Connectivity is maintained via single path

---

**Sub-test 5.4: Test Second Path Failure (Shutdown Ethernet8)**

**Test Steps:**
```bash
# On D1 - Shutdown second ECMP path (now the only active path)
configure terminal
interface Ethernet8
shutdown
exit
exit

# Verify both paths are down
show interface status | include "Ethernet4\|Ethernet8"
show ipv6 route 2001:db8:20::/64

# Test connectivity
ping ipv6 2001:db8:20::1 -c 5
```

**Expected Result:**
- Both Ethernet4 and Ethernet8 are down
- Route 2001:db8:20::/64 may still be in routing table but marked inactive
- **Ping fails** (destination unreachable or 100% packet loss)
- No active next-hops available for the route

---

### Phase 6: Interface Re-enable and ECMP Recovery

**Sub-test 6.1: Re-enable First Interface (Ethernet4)**

**Test Steps:**
```bash
# On D1
configure terminal
interface Ethernet4
no shutdown
exit
exit

# Wait for interface to come up
sleep 5

# Verify interface recovery
show interface status Ethernet4
show ipv6 interface Ethernet4
```

**Expected Result:**
- Ethernet4 returns to "Up/Up" state
- IPv6 address is active on Ethernet4
- Link-local and global IPv6 addresses are operational

---

**Sub-test 6.2: Verify Single Path Recovery**

**Test Steps:**
```bash
# On D1 (Ethernet4 up, Ethernet8 still down)
show ipv6 route 2001:db8:20::/64

# Test connectivity
ping ipv6 2001:db8:20::1 -c 10
```

**Expected Result:**
- Route 2001:db8:20::/64 has one active next-hop: 2001:db8:10::2 via Ethernet4
- Ping succeeds (connectivity restored)
- Traffic uses Ethernet4 path

---

**Sub-test 6.3: Re-enable Second Interface (Ethernet8)**

**Test Steps:**
```bash
# On D1
configure terminal
interface Ethernet8
no shutdown
exit
exit

# Wait for interface to stabilize
sleep 5

# Verify interface recovery
show interface status Ethernet8
show ipv6 interface Ethernet8
```

**Expected Result:**
- Ethernet8 returns to "Up/Up" state
- IPv6 address is active on Ethernet8
- Both ECMP paths are now operationally up

---

**Sub-test 6.4: Verify ECMP Route Re-establishment**

**Test Steps:**
```bash
# On D1 (both interfaces now up)
show ipv6 route 2001:db8:20::/64
show ipv6 route static

# Verify ECMP is restored
sudo vtysh -c "show ipv6 route 2001:db8:20::/64"
```

**Expected Result:**
- **ECMP entry is automatically re-established**
- **Two next-hops are active again:**
  - 2001:db8:10::2 via Ethernet4
  - 2001:db8:11::2 via Ethernet8
- Both next-hops appear under the same route
- Equal-cost behavior restored
- No manual route reconfiguration required

---

**Sub-test 6.5: Verify Load Balancing After Recovery**

**Test Steps:**
```bash
# On D1 - Clear counters
sudo sonic-clear counters

# Send traffic to verify load balancing
ping ipv6 2001:db8:20::1 -c 100 -i 0.2

# Check counter distribution
show interfaces Ethernet4 counters
show interfaces Ethernet8 counters
```

**Expected Result:**
- Both interfaces show incremented counters
- Traffic distributes across both paths
- Load balancing behavior is fully restored
- No residual effects from previous failures
- ECMP operates normally after recovery

---

### Phase 7: Enable/Disable in Global Configuration Mode

**Sub-test 7.1: Disable First ECMP Route in Config Mode**

**Test Steps:**
```bash
# On D1
configure terminal
no ipv6 route 2001:db8:20::/64 2001:db8:10::2
exit

# Verify route removal
show ipv6 route 2001:db8:20::/64
show running-config | include "ipv6 route 2001:db8:20"
```

**Expected Result:**
- First static route is removed from configuration
- ECMP entry degraded to single path
- Only one route remains: 2001:db8:20::/64 via 2001:db8:11::2
- Running-config shows only one route command
- Traffic still works via remaining path

---

**Sub-test 7.2: Re-enable First ECMP Route in Config Mode**

**Test Steps:**
```bash
# On D1
configure terminal
ipv6 route 2001:db8:20::/64 2001:db8:10::2
exit

# Verify ECMP restoration
show ipv6 route 2001:db8:20::/64
show running-config | include "ipv6 route 2001:db8:20"
```

**Expected Result:**
- ECMP entry is re-created
- Two next-hops active again
- Running-config shows both route commands
- Load balancing functionality restored

---

**Sub-test 7.3: Disable Second ECMP Route in Config Mode**

**Test Steps:**
```bash
# On D1
configure terminal
no ipv6 route 2001:db8:20::/64 2001:db8:11::2
exit

# Verify single route remains
show ipv6 route 2001:db8:20::/64
ping ipv6 2001:db8:20::1 -c 5
```

**Expected Result:**
- Second route removed from routing table
- Single route remains via 2001:db8:10::2
- Ping succeeds using single remaining path

---

**Sub-test 7.4: Re-enable Second ECMP Route and Verify ECMP**

**Test Steps:**
```bash
# On D1
configure terminal
ipv6 route 2001:db8:20::/64 2001:db8:11::2
exit

# Verify full ECMP restoration
show ipv6 route 2001:db8:20::/64
write memory
```

**Expected Result:**
- ECMP fully restored with both next-hops
- Configuration saved successfully
- System ready for further testing

---

**Sub-test 7.5: Disable Both ECMP Routes (Remove All Paths)**

**Test Steps:**
```bash
# On D1
configure terminal
no ipv6 route 2001:db8:20::/64 2001:db8:10::2
no ipv6 route 2001:db8:20::/64 2001:db8:11::2
exit

# Verify complete route removal
show ipv6 route 2001:db8:20::/64
ping ipv6 2001:db8:20::1 -c 3
```

**Expected Result:**
- No static routes to 2001:db8:20::/64 exist
- Route lookup for 2001:db8:20::/64 shows no matching entry
- Ping fails (network unreachable)

---

**Sub-test 7.6: Re-enable Both ECMP Routes Simultaneously**

**Test Steps:**
```bash
# On D1 - Add both routes in same configuration session
configure terminal
ipv6 route 2001:db8:20::/64 2001:db8:10::2
ipv6 route 2001:db8:20::/64 2001:db8:11::2
exit

# Verify ECMP creation
show ipv6 route 2001:db8:20::/64
ping ipv6 2001:db8:20::1 -c 10
```

**Expected Result:**
- ECMP entry created with both next-hops
- Both routes installed simultaneously
- Ping succeeds with load balancing

---

### Phase 8: Enable/Disable at Interface Level

**Sub-test 8.1: Disable Interface in Config Mode (Ethernet4)**

**Test Steps:**
```bash
# On D1
configure terminal
interface Ethernet4
shutdown
exit
exit

# Verify ECMP behavior with one path down
show interface status Ethernet4
show ipv6 route 2001:db8:20::/64
```

**Expected Result:**
- Ethernet4 is administratively down
- Static route via Ethernet4 becomes inactive or removed from active table
- One next-hop remains active (via Ethernet8)
- Traffic automatically uses remaining path

---

**Sub-test 8.2: Re-enable Interface in Config Mode**

**Test Steps:**
```bash
# On D1
configure terminal
interface Ethernet4
no shutdown
exit
exit

sleep 5

# Verify ECMP restoration
show interface status Ethernet4
show ipv6 route 2001:db8:20::/64
```

**Expected Result:**
- Ethernet4 returns to operational status
- ECMP entry is re-established
- Both next-hops active again
- Load balancing restored

---

**Sub-test 8.3: Multiple Interface Shutdown/No-Shutdown Cycles**

**Test Steps:**
```bash
# On D1 - Test multiple cycles
# Cycle 1: Shutdown and restore Ethernet8
configure terminal
interface Ethernet8
shutdown
exit
exit
show ipv6 route 2001:db8:20::/64
ping ipv6 2001:db8:20::1 -c 5

configure terminal
interface Ethernet8
no shutdown
exit
exit
sleep 5
show ipv6 route 2001:db8:20::/64

# Cycle 2: Shutdown and restore Ethernet4
configure terminal
interface Ethernet4
shutdown
exit
exit
show ipv6 route 2001:db8:20::/64

configure terminal
interface Ethernet4
no shutdown
exit
exit
sleep 5
show ipv6 route 2001:db8:20::/64
```

**Expected Result:**
- Each shutdown removes one ECMP path
- Connectivity maintained via remaining path
- Each no-shutdown restores ECMP entry
- System handles multiple cycles correctly
- No configuration corruption or route instability

---

### Phase 9: Comprehensive Show Command Validation

**Sub-test 9.1: Standard CLI Route Commands**

**Test Steps:**
```bash
# On D1 - Comprehensive route validation
show ipv6 route
show ipv6 route static
show ipv6 route 2001:db8:20::/64
show running-config | include "ipv6 route"
```

**Expected Result:**
1. **`show ipv6 route`** - Full routing table with ECMP entry visible
2. **`show ipv6 route static`** - Both ECMP static routes listed
3. **`show ipv6 route 2001:db8:20::/64`** - Detailed ECMP information:
   - Multiple next-hops under same prefix
   - Equal cost indicated
   - Both paths active
4. **`show running-config | include "ipv6 route"`** - Configuration commands visible

---

**Sub-test 9.2: Interface Status and Counter Commands**

**Test Steps:**
```bash
# On D1
show interface status
show interface status Ethernet4
show interface status Ethernet8
show interfaces counters
show interfaces Ethernet4 counters
show interfaces Ethernet8 counters
```

**Expected Result:**
- Both interfaces show "Up/Up" operational status
- Interface counters show traffic distribution
- Counters reflect ECMP load balancing behavior

---

**Sub-test 9.3: sudo vtysh Route Validation Commands**

**Test Steps:**
```bash
# On D1
sudo vtysh -c "show ipv6 route"
sudo vtysh -c "show ipv6 route static"
sudo vtysh -c "show ipv6 route 2001:db8:20::/64"
sudo vtysh -c "show running-config | section ipv6 route"
```

**Expected Result:**
- vtysh output matches standard CLI
- FRR routing daemon shows ECMP correctly
- Both next-hops visible in FRR routing table
- Configuration section shows both route commands

---

**Sub-test 9.4: sudo System and Kernel Commands**

**Test Steps:**
```bash
# On D1
sudo ip -6 route show 2001:db8:20::/64
sudo ip -6 route list
sudo ip -6 route get 2001:db8:20::1

# Check IPv6 neighbor discovery for next-hops
sudo ip -6 neigh show 2001:db8:10::2
sudo ip -6 neigh show 2001:db8:11::2
```

**Expected Result:**
- Kernel routing table shows ECMP entry
- Multiple nexthop entries for destination
- `ip -6 route get` shows ECMP resolution
- Neighbor entries exist for both next-hops (reachable state)

---

**Sub-test 9.5: Ping and Connectivity Validation**

**Test Steps:**
```bash
# On D1
ping ipv6 2001:db8:20::1 -c 5
ping ipv6 2001:db8:20::1 -c 100

# Alternative: ping with specific interface (should work from either)
ping ipv6 2001:db8:20::1 -c 5 -I Ethernet4
ping ipv6 2001:db8:20::1 -c 5 -I Ethernet8
```

**Expected Result:**
- Standard ping succeeds with ECMP load balancing
- Extended ping (100 packets) shows consistent reachability
- Interface-specific pings may work (depends on routing policy)
- No packet loss under normal conditions

---

**Sub-test 9.6: Write Memory and Configuration Persistence**

**Test Steps:**
```bash
# On D1
write memory

# Verify saved configuration
show running-config | include "ipv6 route 2001:db8:20"
```

**Expected Result:**
- Configuration saved successfully
- Both ECMP routes persist in running-config
- Configuration will survive device reload

---

## Complete Show Command List

### Standard Klish/Click CLI Commands

#### IPv6 Route Commands
1. `show ipv6 route` - Display complete IPv6 routing table
2. `show ipv6 route static` - Display only static IPv6 routes
3. `show ipv6 route 2001:db8:20::/64` - Display specific route (ECMP entry)
4. `show running-config | include "ipv6 route"` - Show static route configuration

#### Interface Status Commands
5. `show interface status` - All interface operational status
6. `show interface status Ethernet4` - Specific interface status
7. `show interface status Ethernet8` - Specific interface status
8. `show ipv6 interface brief` - IPv6 interface summary
9. `show ipv6 interface Ethernet4` - Detailed IPv6 interface info
10. `show ipv6 interface Ethernet8` - Detailed IPv6 interface info

#### Interface Counter Commands
11. `show interfaces counters` - All interface traffic counters
12. `show interfaces Ethernet4 counters` - Ethernet4 traffic counters
13. `show interfaces Ethernet8 counters` - Ethernet8 traffic counters
14. `show interfaces counters detailed` - Detailed counter statistics
15. `show interfaces Ethernet4 counters detailed` - Detailed Ethernet4 stats
16. `show interfaces Ethernet8 counters detailed` - Detailed Ethernet8 stats

#### Connectivity Test Commands
17. `ping ipv6 2001:db8:20::1` - Basic IPv6 ping
18. `ping ipv6 2001:db8:20::1 -c 100` - Extended ping for load balancing test

#### Configuration Commands
19. `write memory` - Save configuration
20. `show running-config interface Ethernet4` - Interface configuration
21. `show running-config interface Ethernet8` - Interface configuration

### Privileged/Sudo Commands

#### sudo vtysh Commands (FRR Routing Daemon)
1. `sudo vtysh -c "show ipv6 route"` - IPv6 routes from FRR perspective
2. `sudo vtysh -c "show ipv6 route static"` - Static routes via FRR
3. `sudo vtysh -c "show ipv6 route 2001:db8:20::/64"` - Specific route via FRR
4. `sudo vtysh -c "show ipv6 fib 2001:db8:20::/64"` - FIB entry for ECMP route
5. `sudo vtysh -c "show running-config | section ipv6 route"` - FRR route config

#### sudo System Commands (Kernel Routing)
6. `sudo ip -6 route show` - Kernel IPv6 routing table
7. `sudo ip -6 route show 2001:db8:20::/64` - Specific kernel route
8. `sudo ip -6 route list` - List all IPv6 routes
9. `sudo ip -6 route get 2001:db8:20::1` - Route lookup and resolution
10. `sudo ip -6 neigh show` - IPv6 neighbor cache (next-hop reachability)
11. `sudo ip -6 neigh show 2001:db8:10::2` - Specific next-hop neighbor entry
12. `sudo ip -6 neigh show 2001:db8:11::2` - Specific next-hop neighbor entry

#### sudo Traffic Commands
13. `sudo sonic-clear counters` - Clear all interface counters
14. `sudo ping6 2001:db8:20::1` - Direct IPv6 ping via kernel

---

## Expected Results Summary

### ECMP Route Installation

| Route Configuration | Next-Hops | Expected Behavior |
|---------------------|-----------|-------------------|
| Single route configured | 2001:db8:10::2 only | Single path, no ECMP |
| Both routes configured | 2001:db8:10::2 AND 2001:db8:11::2 | **ECMP entry created** |
| One interface down | Only reachable next-hop | Single path, automatic failover |
| Both interfaces down | None | Route inactive, ping fails |
| Both interfaces restored | Both next-hops | **ECMP automatically re-established** |

### ECMP Load Balancing Behavior

✅ **With ECMP Active (Both Paths Up)**
- Two static routes for same prefix (2001:db8:20::/64) installed and active
- Both next-hops appear under same route entry with equal cost
- CEF/FIB entries show both next-hops available for load sharing
- Ping or traffic distributes across both interfaces
- Interface counters on both Ethernet4 and Ethernet8 increment
- Load distribution approximately balanced (40%-60% per interface acceptable)

✅ **During Next-Hop Failure**
- When one path fails (interface down), the other remains active automatically
- Routing table updates to show only active next-hop
- Traffic seamlessly fails over to remaining path
- Connectivity maintained with minimal packet loss
- No manual intervention required

✅ **After Restoration**
- When failed interface is re-enabled, ECMP entry is re-established
- Both next-hops become active again automatically
- Load balancing behavior resumes
- System returns to normal ECMP operation

### Interface Status Validation

1. **Both Interfaces Operational**
   - ✅ show interface status: Ethernet4 "Up/Up", Ethernet8 "Up/Up"
   - ✅ ECMP with two active next-hops
   - ✅ Traffic load-balanced across both paths

2. **One Interface Down (Ethernet4 shutdown)**
   - ✅ show interface status: Ethernet4 "Down/Down", Ethernet8 "Up/Up"
   - ✅ Single active next-hop: 2001:db8:11::2 via Ethernet8
   - ✅ Traffic uses only Ethernet8

3. **Both Interfaces Down**
   - ✅ show interface status: Both "Down/Down"
   - ✅ No active next-hops
   - ✅ Ping fails (network unreachable)

### Traffic Distribution Validation

**Expected Counter Behavior:**

1. **ECMP Active (Both Paths Up)**
   ```
   Ethernet4 TX packets: ~5000 (approximately 50% of traffic)
   Ethernet8 TX packets: ~5000 (approximately 50% of traffic)
   ```

2. **Single Path Active (Ethernet4 down)**
   ```
   Ethernet4 TX packets: 0 (interface down)
   Ethernet8 TX packets: 10000 (100% of traffic)
   ```

3. **After ECMP Recovery**
   ```
   Both interfaces show balanced traffic distribution again
   ```

### Configuration Persistence

✅ **Running Configuration**
- Both route commands visible: `ipv6 route 2001:db8:20::/64 2001:db8:10::2`
- And: `ipv6 route 2001:db8:20::/64 2001:db8:11::2`
- Persists after `write memory`
- Survives device reboot

✅ **Enable/Disable Behavior**
- Global config mode: `no ipv6 route...` removes route, `ipv6 route...` adds back
- Interface mode: `shutdown` deactivates path, `no shutdown` reactivates
- Multiple cycles supported without configuration corruption

---

## Test Execution Command

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/routing/static/test_static_ipv6_ecmp.py \
  --logs-path ./logs/test_ipv6_ecmp_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

---

## Test Data and Prerequisites Checklist

### Prerequisites Checklist

- [ ] Testbed file available at `/home/adminuser/draksha/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- [ ] Both DUTs accessible via SSH (D1: 192.168.100.142, D2: 192.168.100.97)
- [ ] At least two physical/logical links between D1 and D2 (Ethernet4, Ethernet8)
- [ ] IPv6 forwarding enabled on both devices
- [ ] FRR routing daemon running
- [ ] Admin/sudo access available
- [ ] ECMP support enabled in kernel and routing daemon
- [ ] Sufficient interface resources for test topology

### Test Data Summary

**D1 (smic_sonic1) Configuration:**
- Ethernet4: 2001:db8:10::1/64
- Ethernet8: 2001:db8:11::1/64
- Static Route 1: 2001:db8:20::/64 via 2001:db8:10::2
- Static Route 2: 2001:db8:20::/64 via 2001:db8:11::2

**D2 (smic_sonic2) Configuration:**
- Ethernet4: 2001:db8:10::2/64
- Ethernet8: 2001:db8:11::2/64
- Loopback0: 2001:db8:20::1/128

**Test Destination:** 2001:db8:20::1

---

## Cleanup Steps

After test completion:

```bash
# On D1
configure terminal

# Remove ECMP static routes
no ipv6 route 2001:db8:20::/64 2001:db8:10::2
no ipv6 route 2001:db8:20::/64 2001:db8:11::2

# Remove interface configurations (optional - restore to baseline)
interface Ethernet4
no ipv6 address 2001:db8:10::1/64
exit

interface Ethernet8
no ipv6 address 2001:db8:11::1/64
exit

exit

# Verify cleanup
show ipv6 route 2001:db8:20::/64
# Should show no matching route

# On D2
configure terminal

# Remove loopback
no interface Loopback0

# Remove interface configurations (optional)
interface Ethernet4
no ipv6 address 2001:db8:10::2/64
exit

interface Ethernet8
no ipv6 address 2001:db8:11::2/64
exit

exit
```

---

## Related Test Cases

- **TC-IP-STATIC-IPV6-001:** Basic IPv6 static route configuration
- **TC-IP-STATIC-IPV6-002:** IPv6 static route with interface specification
- **TC-IP-STATIC-IPV6-003:** IPv6 static route with administrative distance
- **TC-IP-STATIC-IPV6-008:** IPv6 static route with management VRF
- **TC-IP-STATIC-IPV6-009:** IPv6 ECMP route validation (this test)
- **TC-IP-STATIC-005:** IPv4 ECMP route validation

---

## Test Case Status

- **Author:** Generated from test plan 2.1.9
- **Test Case ID:** TC-IP-STATIC-IPV6-009
- **Status:** Ready for Implementation
- **Priority:** P1 (High - Core routing functionality)
- **Automation:** Suitable for automated testing with traffic validation
- **Estimated Duration:** 60-75 minutes (manual execution)
- **Complexity:** High (requires multiple paths, traffic analysis, failure simulation)

---

## Important Notes

### ECMP Specific Considerations

1. **ECMP Hashing Algorithm**
   - SONiC/FRR uses flow-based hashing by default
   - Hash typically based on: src/dst IPv6 address, protocol, src/dst port
   - ICMP ping may not distribute perfectly (single flow)
   - For better distribution, use varied traffic (multiple source ports, destinations)

2. **Load Balancing Tolerance**
   - Perfect 50/50 split is rare in practice
   - Accept 40/60 to 60/40 distribution as normal
   - Per-flow hashing means some flows may prefer one path
   - Per-packet hashing (if enabled) gives better distribution but may cause reordering

3. **Next-Hop Reachability**
   - Both next-hops must be directly reachable (single-hop neighbors)
   - Neighbor discovery (ND) must succeed for both next-hops
   - Check neighbor cache: `sudo ip -6 neigh show`
   - Stale neighbor entries may affect ECMP behavior

4. **ECMP Maximum Paths**
   - SONiC typically supports up to 32-64 ECMP paths
   - This test uses 2 paths (minimal ECMP)
   - Can be extended to 3+ paths for comprehensive testing

5. **Failover Timing**
   - Interface down detected quickly (physical link failure)
   - Next-hop unreachability may take longer (depends on ND timers)
   - Expect 1-3 seconds for failover convergence
   - Some packet loss during transition is acceptable

6. **Traffic Generator Recommendations**
   - For accurate load balancing validation, use traffic generator if available
   - Simple ping may not trigger optimal ECMP distribution
   - Consider iperf3, scapy, or hardware TGen for production testing

7. **Kernel vs FRR Consistency**
   - Always verify ECMP in both FRR and kernel routing tables
   - Discrepancies indicate control/data plane issues
   - Use `sudo vtysh -c "show ipv6 route"` and `sudo ip -6 route show`

---

## Success Criteria

### Test Passes If:

- ✅ Two static routes for same prefix (2001:db8:20::/64) install successfully
- ✅ Both next-hops appear under same route entry (ECMP created)
- ✅ CEF/FIB entries show both next-hops for load sharing
- ✅ Interface counters on both Ethernet4 and Ethernet8 increment during traffic
- ✅ Traffic distributes approximately evenly across both paths (40%-60% tolerance)
- ✅ When one path fails (interface shutdown), other remains active automatically
- ✅ Connectivity maintained during single-path failure
- ✅ When failed path restored, ECMP re-establishes automatically
- ✅ Both global config mode and interface mode enable/disable work correctly
- ✅ Configuration persists after `write memory`
- ✅ CLI outputs consistent across klish, vtysh, and kernel routing

### Test Fails If:

- ❌ ECMP entry not created (routes installed as separate entries)
- ❌ Only one next-hop used despite both interfaces being up
- ❌ Interface counters show traffic on only one path (no load balancing)
- ❌ Load distribution extremely unbalanced (>80% on single path)
- ❌ Failover doesn't occur when one path fails
- ❌ ECMP not re-established after failed path recovery
- ❌ Enable/disable commands don't affect routing behavior
- ❌ Configuration inconsistencies between FRR and kernel
- ❌ Ping fails when at least one path is available
- ❌ Interface state changes don't trigger route updates

---

## References

- SONiC Static Routing HLD
- FRR Documentation: IPv6 Static Routes and ECMP
- Linux Kernel IPv6 Routing: Multipath Routes
- RFC 2991: Multipath Issues in Unicast and Multicast Next-Hop Selection
- Test Plan Section: 2.1.9 - Configure and verify ECMP Route Validation (Static) IPv6
- Related Test Cases: TC-IP-STATIC-IPV6-001 through TC-IP-STATIC-IPV6-008
