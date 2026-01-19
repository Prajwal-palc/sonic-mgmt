# Test Case: Management VRF IPv6 Static Route Configuration and Validation

**Test Case ID:** TC-IP-STATIC-IPV6-008
**Feature:** IPv6 Static Routing
**Sub-feature:** Management VRF Static Routes - IPv6
**Test Plan Section:** 2.1.8

---

## Test Objective

Configure and verify Management VRF static routes for IPv6. Validate that management VRF static routes are used exclusively for management traffic (ping, SSH, SNMP), maintain proper VRF isolation from data plane routes, and verify enable/disable functionality at both global configuration and interface levels. Confirm route visibility and state consistency across multiple CLI interfaces.

---

## Topology Requirements

**Topology:** Two-node (D1-D2) with Management VRF support
**Testbed File:** `/home/adminuser/draksha/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
**Supported Platforms:** Hardware and Virtual

```
# Topology - 2 nodes with Management VRF
# +--------------------------------+                       +--------------------------------+
# |        smic_sonic1 (D1)        |                       |        smic_sonic2 (D2)        |
# | Mgmt IP: 192.168.100.142       |                       | Mgmt IP: 192.168.100.97        |
# | eth0: mgmt interface           |                       | eth0: mgmt interface           |
# | Management VRF configured      |                       | Management VRF configured      |
# |                                |   Management Network  |                                |
# |                                |=======================|                                |
# | Eth4: Data plane interface     |   Data Plane Network  | Eth4: Data plane interface     |
# +--------------------------------+                       +--------------------------------+
```

**Device Details from Testbed:**
- **D1 (smic_sonic1):** Management IP: 192.168.100.142
- **D2 (smic_sonic2):** Management IP: 192.168.100.97
- **Data Plane Interconnect:** Ethernet4 on both devices
- **Management Interface:** eth0 (out-of-band management)

---

## Pre-requisites

1. SONiC devices with IPv6 routing enabled
2. Management VRF support enabled (default in SONiC)
3. Management interface (eth0) configured with IPv6 addressing
4. Klish CLI access and Click CLI access
5. Admin/sudo privileges for privileged commands
6. Management reachability to both devices via out-of-band network
7. IPv6 forwarding enabled for management VRF

---

## Test Variables

Variables should be loaded from: `spytest/vars/routing/static/vars_static_ipv6_mgmt.yaml`

**Recommended variable file structure:**
```yaml
min_topology: ["D1D2:1"]

# Management VRF configuration
mgmt_vrf:
  name: mgmt
  description: "Management VRF for out-of-band management"

# Management interface IPv6 configuration
mgmt_interfaces:
  D1_mgmt:
    interface: eth0
    ipv6: "2001:db8:mgmt::142/64"
    ipv6_gateway: "2001:db8:mgmt::1"

  D2_mgmt:
    interface: eth0
    ipv6: "2001:db8:mgmt::97/64"
    ipv6_gateway: "2001:db8:mgmt::1"

# Data plane interfaces (should NOT be in mgmt VRF)
data_interfaces:
  D1_D2_link:
    D1: Ethernet4
    D2: Ethernet4
    D1_ipv6: "2001:db8:data::1/64"
    D2_ipv6: "2001:db8:data::2/64"

# Management VRF static routes
mgmt_routes:
  remote_mgmt_network:
    prefix: "2001:db8:external::/48"
    nexthop: "2001:db8:mgmt::254"

  specific_mgmt_host:
    prefix: "2001:db8:nms::100/128"
    nexthop: "2001:db8:mgmt::254"

# Test destinations for validation
test_destinations:
  mgmt_ping_target: "2001:db8:external::1"
  data_ping_target: "2001:db8:data::100"
```

---

## Test Case Details

### Phase 1: Verify Management VRF Pre-Configuration

**Sub-test 1.1: Verify Management VRF Exists**

**Test Steps:**
```bash
# On both D1 and D2
show vrf
show vrf | include mgmt
show running-config | section vrf
```

**Validation Commands:**
- `show vrf`
- `show vrf mgmt`
- `sudo vtysh -c "show vrf"`

**Expected Result:**
- Management VRF named "mgmt" exists by default
- VRF status is active
- Management interface (eth0) is assigned to mgmt VRF
- Separate routing table exists for mgmt VRF

---

**Sub-test 1.2: Verify Management Interface Configuration**

**Test Steps:**
```bash
# On D1
show ipv6 interface brief
show ipv6 interface eth0
show interface status eth0

# Verify interface is in mgmt VRF
show running-config interface eth0
```

**Validation Commands:**
- `show ipv6 interface brief`
- `show ipv6 interface eth0`
- `show vrf mgmt`
- `sudo vtysh -c "show ipv6 interface brief vrf mgmt"`

**Expected Result:**
- eth0 interface exists and is operationally up
- eth0 is assigned to management VRF
- IPv6 address is configured on eth0 (management IPv6)
- Interface does NOT appear in default/data VRF routing table

---

### Phase 2: Configure IPv6 Static Routes in Management VRF

**Sub-test 2.1: Configure Basic IPv6 Management Static Route**

**Test Steps:**
```bash
# On D1
configure terminal
ipv6 route vrf mgmt 2001:db8:external::/48 2001:db8:mgmt::254
exit
```

**Validation Commands:**
- `show ipv6 route vrf mgmt`
- `show ipv6 route vrf mgmt 2001:db8:external::/48`
- `show running-config | include "ipv6 route vrf mgmt"`
- `sudo vtysh -c "show ipv6 route vrf mgmt"`

**Expected Result:**
- Route 2001:db8:external::/48 is installed in mgmt VRF routing table
- Next-hop is 2001:db8:mgmt::254 (via management network)
- Route type is Static (S)
- Route appears in running configuration
- Route is visible via vtysh commands

---

**Sub-test 2.2: Configure Specific Host Route in Management VRF**

**Test Steps:**
```bash
# On D1 - Route to specific management server/NMS
configure terminal
ipv6 route vrf mgmt 2001:db8:nms::100/128 2001:db8:mgmt::254
exit
```

**Validation Commands:**
- `show ipv6 route vrf mgmt 2001:db8:nms::100/128`
- `show running-config | grep "ipv6 route vrf mgmt"`

**Expected Result:**
- Specific /128 host route is installed
- Route uses management network gateway as next-hop
- Route is in mgmt VRF only

---

**Sub-test 2.3: Configure Management Route with Interface Specification**

**Test Steps:**
```bash
# On D1
configure terminal
ipv6 route vrf mgmt 2001:db8:backup::/48 eth0 2001:db8:mgmt::253
exit
```

**Validation Commands:**
- `show ipv6 route vrf mgmt 2001:db8:backup::/48`
- `show running-config | section "ipv6 route"`

**Expected Result:**
- Route is installed with both interface (eth0) and next-hop
- Route is specific to management VRF

---

**Sub-test 2.4: Save Management VRF Configuration**

**Test Steps:**
```bash
# Save configuration
write memory
# Verify persistence
show running-config | include "ipv6 route vrf mgmt"
```

**Expected Result:**
- All management VRF static routes persist in running-config
- Configuration saved successfully to startup-config

---

### Phase 3: Verify VRF Isolation (Critical Security Requirement)

**Sub-test 3.1: Verify Management Routes NOT in Data VRF**

**Test Steps:**
```bash
# On D1 - Check default/data VRF routing table
show ipv6 route
show ipv6 route 2001:db8:external::/48
show ipv6 route 2001:db8:nms::100/128
```

**Expected Result:**
- Management VRF routes do NOT appear in default VRF
- Only data plane routes visible in default routing table
- Complete VRF isolation is maintained
- No route leakage between management and data VRFs

---

**Sub-test 3.2: Verify Data Routes NOT in Management VRF**

**Test Steps:**
```bash
# On D1 - Check mgmt VRF routing table
show ipv6 route vrf mgmt

# Verify data plane routes are absent from mgmt VRF
# (assuming you configured some data plane routes on Ethernet4)
```

**Expected Result:**
- Data plane routes do NOT appear in management VRF
- Only management routes and connected mgmt interfaces visible
- Bidirectional VRF isolation confirmed

---

**Sub-test 3.3: Validate VRF Routing Table Separation**

**Test Steps:**
```bash
# On D1
show ipv6 route vrf mgmt | count
show ipv6 route | count

# Compare route counts and entries
sudo vtysh -c "show ipv6 route vrf mgmt"
sudo vtysh -c "show ipv6 route"
```

**Expected Result:**
- Different route counts in mgmt vs default VRF
- No overlapping routes between tables
- Each VRF maintains independent routing decisions

---

### Phase 4: Management Traffic Validation

**Sub-test 4.1: Test IPv6 Ping via Management VRF**

**Test Steps:**
```bash
# On D1 - Ping destination in external management network
ping ipv6 2001:db8:external::1 vrf mgmt -c 5

# Alternative: Use interface-specific ping
sudo ping6 -I eth0 2001:db8:external::1 -c 5
```

**Expected Result:**
- Ping succeeds with 0% packet loss
- Traffic uses management VRF routing table
- Traffic egresses via eth0 (management interface)
- No traffic on data plane interfaces (Ethernet4)

---

**Sub-test 4.2: Verify Management Interface Counters**

**Test Steps:**
```bash
# Before traffic test
show interfaces eth0 counters

# Send traffic via management VRF
ping ipv6 2001:db8:external::1 vrf mgmt -c 10

# After traffic test
show interfaces eth0 counters
```

**Expected Result:**
- eth0 TX/RX counters increment during ping
- Data plane interface (Ethernet4) counters do NOT increment
- Traffic is isolated to management VRF

---

**Sub-test 4.3: Test Management Traffic from Default VRF (Negative Test)**

**Test Steps:**
```bash
# On D1 - Try to reach management-only destination from data VRF
ping ipv6 2001:db8:external::1 -c 3
# (without "vrf mgmt" parameter - uses default VRF)
```

**Expected Result:**
- Ping FAILS (destination unreachable or 100% packet loss)
- Default VRF does not have route to management-only networks
- Confirms VRF isolation prevents cross-VRF traffic leakage

---

### Phase 5: Show Command Validation (Standard CLI)

**Sub-test 5.1: Verify VRF Status Commands**

**Test Steps:**
```bash
# On D1
show vrf | include mgmt
show vrf mgmt
```

**Expected Result:**
1. **`show vrf | include mgmt`**
   - Management VRF "mgmt" is listed
   - Shows associated interface: eth0
   - VRF state: Active

2. **`show vrf mgmt`**
   - Detailed mgmt VRF information
   - Route distinguisher (if configured)
   - Member interfaces listed

---

**Sub-test 5.2: Verify IPv6 Interface Commands**

**Test Steps:**
```bash
# On D1
show ipv6 interface brief
show ipv6 interface eth0
show ipv6 interface brief vrf mgmt
```

**Expected Result:**
1. **`show ipv6 interface brief`**
   - Lists all IPv6-enabled interfaces
   - Shows interface status and IPv6 addresses
   - eth0 should be present with mgmt IPv6 address

2. **`show ipv6 interface eth0`**
   - Detailed IPv6 information for eth0
   - Link-local address, global address
   - IPv6 is enabled, ND is operational

3. **`show ipv6 interface brief vrf mgmt`**
   - Shows only interfaces in management VRF (eth0)
   - Does NOT show data plane interfaces

---

**Sub-test 5.3: Verify IPv6 Route Commands for Management VRF**

**Test Steps:**
```bash
# On D1
show ipv6 route vrf mgmt
show ipv6 route vrf mgmt 2001:db8:external::/48
show ipv6 route vrf mgmt static
show running-config | include "ipv6 route vrf mgmt"
```

**Expected Result:**
1. **`show ipv6 route vrf mgmt`**
   - Displays complete mgmt VRF routing table
   - Shows static routes: 2001:db8:external::/48, 2001:db8:nms::100/128, etc.
   - Shows connected routes for eth0
   - All routes specific to management VRF

2. **`show ipv6 route vrf mgmt 2001:db8:external::/48`**
   - Specific route details displayed
   - Next-hop: 2001:db8:mgmt::254
   - Route type: Static (S)
   - Outgoing interface: eth0

3. **`show ipv6 route vrf mgmt static`**
   - Filters to show only static routes in mgmt VRF
   - All manually configured mgmt routes listed

4. **`show running-config | include "ipv6 route vrf mgmt"`**
   - Configuration syntax visible
   - All static routes in mgmt VRF shown
   - Verify persistence in running-config

---

**Sub-test 5.4: Verify Ping Commands in Management VRF**

**Test Steps:**
```bash
# On D1
ping ipv6 vrf mgmt 2001:db8:external::1 -c 5
ping ipv6 2001:db8:mgmt::254 vrf mgmt
```

**Expected Result:**
1. **`ping ipv6 vrf mgmt <destination>`**
   - Ping uses management VRF routing table
   - Traffic egresses via eth0
   - Successful ping to reachable mgmt destinations

2. **Standard ping (without VRF)**
   - Should fail to reach management-only destinations
   - Confirms VRF isolation

---

### Phase 6: Show Command Validation (Sudo/vtysh)

**Sub-test 6.1: Validate sudo vtysh Route Commands**

**Test Steps:**
```bash
# On D1
sudo vtysh -c "show vrf"
sudo vtysh -c "show ipv6 route vrf mgmt"
sudo vtysh -c "show ipv6 route vrf mgmt 2001:db8:external::/48"
sudo vtysh -c "show running-config | section ipv6 route"
```

**Expected Result:**
1. **`sudo vtysh -c "show vrf"`**
   - Management VRF listed with same details as standard CLI
   - Interface associations correct (eth0)

2. **`sudo vtysh -c "show ipv6 route vrf mgmt"`**
   - All mgmt VRF routes displayed
   - Output from FRR routing daemon perspective
   - Should match standard CLI output

3. **`sudo vtysh -c "show ipv6 route vrf mgmt 2001:db8:external::/48"`**
   - Specific route details match standard CLI
   - Next-hop and outgoing interface correct

4. **`sudo vtysh -c "show running-config | section ipv6 route"`**
   - FRR configuration shows static routes
   - Management VRF routes visible with "vrf mgmt" keyword

---

**Sub-test 6.2: Validate sudo Interface and Ping Commands**

**Test Steps:**
```bash
# On D1
sudo vtysh -c "show ipv6 interface brief vrf mgmt"
sudo ping6 -I eth0 2001:db8:external::1 -c 5
sudo traceroute6 -i eth0 2001:db8:external::1
```

**Expected Result:**
1. **`sudo vtysh -c "show ipv6 interface brief vrf mgmt"`**
   - Interfaces in mgmt VRF shown
   - Values consistent with standard CLI

2. **`sudo ping6 -I eth0 <destination>`**
   - Direct ping via eth0 interface
   - Uses kernel routing table for mgmt VRF
   - Should succeed to management destinations

3. **`sudo traceroute6 -i eth0 <destination>`**
   - Shows IPv6 path via management network
   - Hops visible through management infrastructure

---

### Phase 7: Enable/Disable in Global Configuration Mode

**Sub-test 7.1: Disable Management VRF Static Route**

**Test Steps:**
```bash
# On D1
configure terminal
no ipv6 route vrf mgmt 2001:db8:external::/48 2001:db8:mgmt::254
exit

# Verify removal
show ipv6 route vrf mgmt 2001:db8:external::/48
ping ipv6 vrf mgmt 2001:db8:external::1 -c 3
```

**Expected Result:**
- Route 2001:db8:external::/48 is removed from mgmt VRF routing table
- Route no longer appears in `show ipv6 route vrf mgmt`
- Running-config updated (route configuration removed)
- Ping to 2001:db8:external::1 FAILS (network unreachable)

---

**Sub-test 7.2: Re-enable Management VRF Static Route**

**Test Steps:**
```bash
# On D1
configure terminal
ipv6 route vrf mgmt 2001:db8:external::/48 2001:db8:mgmt::254
exit

# Verify addition
show ipv6 route vrf mgmt 2001:db8:external::/48
ping ipv6 vrf mgmt 2001:db8:external::1 -c 5
```

**Expected Result:**
- Route is re-installed in mgmt VRF routing table
- Route visible in all show commands
- Running-config updated with route configuration
- Ping to 2001:db8:external::1 SUCCEEDS

---

**Sub-test 7.3: Multiple Enable/Disable Cycles**

**Test Steps:**
```bash
# On D1
# Cycle 1
configure terminal
no ipv6 route vrf mgmt 2001:db8:nms::100/128
exit
show ipv6 route vrf mgmt 2001:db8:nms::100/128

configure terminal
ipv6 route vrf mgmt 2001:db8:nms::100/128 2001:db8:mgmt::254
exit
show ipv6 route vrf mgmt 2001:db8:nms::100/128

# Cycle 2
configure terminal
no ipv6 route vrf mgmt 2001:db8:nms::100/128
ipv6 route vrf mgmt 2001:db8:nms::100/128 2001:db8:mgmt::254
exit
```

**Expected Result:**
- Route can be removed and re-added multiple times
- Configuration persists correctly after each change
- Routing behavior is consistent across cycles

---

### Phase 8: Enable/Disable at Interface Level

**Sub-test 8.1: Disable Management Interface (eth0)**

**Test Steps:**
```bash
# On D1
configure terminal
interface eth0
shutdown
exit

# Verify interface status
show interface status eth0
show ipv6 interface brief
```

**Expected Result:**
- eth0 interface goes administratively down
- `show interface status eth0` shows "Down/Down"
- IPv6 on eth0 becomes inactive

---

**Sub-test 8.2: Verify Route Behavior with Interface Down**

**Test Steps:**
```bash
# On D1 (with eth0 still shutdown)
show ipv6 route vrf mgmt
show ipv6 route vrf mgmt 2001:db8:external::/48

# Attempt traffic
ping ipv6 vrf mgmt 2001:db8:external::1 -c 3
```

**Expected Result:**
- Static routes in mgmt VRF may still be present in routing table
- Routes may be marked as inactive/down (next-hop unreachable)
- Ping FAILS (100% packet loss or network unreachable)
- Traffic cannot egress because eth0 is down

---

**Sub-test 8.3: Re-enable Management Interface**

**Test Steps:**
```bash
# On D1
configure terminal
interface eth0
no shutdown
exit

# Wait for interface to come up
show interface status eth0
show ipv6 interface eth0
```

**Expected Result:**
- eth0 interface comes back up
- `show interface status eth0` shows "Up/Up"
- IPv6 addressing is restored
- Link-local and global IPv6 addresses are active

---

**Sub-test 8.4: Verify Route Recovery After Interface Up**

**Test Steps:**
```bash
# On D1 (after eth0 is up)
show ipv6 route vrf mgmt
show ipv6 route vrf mgmt 2001:db8:external::/48

# Test traffic
ping ipv6 vrf mgmt 2001:db8:external::1 -c 5
sudo ping6 -I eth0 2001:db8:mgmt::254 -c 3
```

**Expected Result:**
- All mgmt VRF static routes become active again
- Routes are no longer marked as down
- Ping to management destinations SUCCEEDS
- Traffic forwarding fully restored
- Interface counters increment during traffic tests

---

### Phase 9: Management Traffic Types Validation

**Sub-test 9.1: Test SSH via Management VRF (Connectivity Test)**

**Test Steps:**
```bash
# From external management station (if available)
# SSH to device D1 via management IP
ssh admin@2001:db8:mgmt::142

# Alternatively, from D1 to another management host
# (if external host is reachable via mgmt static route)
ssh admin@2001:db8:external::100
```

**Expected Result:**
- SSH connection uses management VRF
- Connection succeeds via eth0 interface
- Management traffic isolated from data plane

---

**Sub-test 9.2: Verify Management Traffic Statistics**

**Test Steps:**
```bash
# On D1
show ipv6 traffic
show interfaces eth0 counters detailed

# Generate management traffic
ping ipv6 vrf mgmt 2001:db8:external::1 -c 50

# Check counters again
show interfaces eth0 counters detailed
show ipv6 traffic
```

**Expected Result:**
1. **`show ipv6 traffic`**
   - IPv6 packet statistics for all interfaces
   - Counters increment during management traffic

2. **Interface Counters for eth0 (Management VRF)**
   - TX/RX byte counters increase during mgmt traffic
   - Packet counters reflect management traffic volume
   - No unexpected errors or drops

3. **Data VRF Interface Counters (Ethernet4)**
   - Should NOT increment during management-only traffic
   - Confirms traffic isolation to mgmt VRF

---

**Sub-test 9.3: Validate Data VRF Routes Remain Unaffected**

**Test Steps:**
```bash
# On D1
# Verify data plane routing is independent
show ipv6 route
show ipv6 interface Ethernet4

# If data plane routes configured, test them
ping ipv6 <data-plane-destination> -c 5
# (without vrf mgmt - uses default VRF)
```

**Expected Result:**
- Data VRF routing table is completely independent
- Management VRF configuration does NOT affect data routes
- Data plane connectivity works normally
- Traffic separation maintained

---

### Phase 10: Configuration Persistence and State Validation

**Sub-test 10.1: Verify Running Configuration**

**Test Steps:**
```bash
# On D1
show running-config | section vrf
show running-config | include "ipv6 route vrf mgmt"
show running-config interface eth0
```

**Expected Result:**
1. **VRF Configuration Section**
   - Management VRF "mgmt" defined
   - VRF members listed (eth0)

2. **IPv6 Route Configuration**
   - All static routes in mgmt VRF visible
   - Correct syntax: `ipv6 route vrf mgmt <prefix> <nexthop>`
   - Reflects current active configuration

3. **Interface Configuration (eth0)**
   - IPv6 address configured
   - VRF membership shown: `ip vrf forwarding mgmt`
   - Interface is enabled (no shutdown)

---

**Sub-test 10.2: Save and Verify Configuration Persistence**

**Test Steps:**
```bash
# On D1
write memory
# or
copy running-config startup-config

# Verify save was successful
show running-config | include "write memory"
```

**Expected Result:**
- Configuration saved successfully
- Message: "Configuration saved to /etc/sonic/config_db.json" (or similar)
- All mgmt VRF routes will persist after device reboot

---

**Sub-test 10.3: Validate State Consistency Across CLI Methods**

**Test Steps:**
```bash
# On D1 - Compare outputs from different CLI methods

# Standard CLI
show ipv6 route vrf mgmt

# vtysh CLI
sudo vtysh -c "show ipv6 route vrf mgmt"

# Kernel routing table
sudo ip -6 route show table mgmt
# or
sudo ip -6 route show vrf mgmt
```

**Expected Result:**
- All three methods show consistent routing information
- Route entries match across CLI interfaces
- Next-hops are identical
- No discrepancies between control plane (FRR) and data plane (kernel)

---

## Complete Show Command List

### Standard Klish/Click CLI Commands

#### VRF Commands
1. `show vrf` - Display all VRFs
2. `show vrf | include mgmt` - Filter for management VRF only
3. `show vrf mgmt` - Show detailed mgmt VRF information

#### IPv6 Interface Commands
4. `show ipv6 interface brief` - All IPv6 interfaces summary
5. `show ipv6 interface eth0` - Detailed eth0 IPv6 information
6. `show ipv6 interface brief vrf mgmt` - IPv6 interfaces in mgmt VRF only
7. `show interface status eth0` - Physical/operational status of eth0

#### IPv6 Route Commands (Management VRF)
8. `show ipv6 route vrf mgmt` - Complete mgmt VRF routing table
9. `show ipv6 route vrf mgmt <prefix>` - Specific route in mgmt VRF
10. `show ipv6 route vrf mgmt static` - Only static routes in mgmt VRF
11. `show running-config | include "ipv6 route vrf mgmt"` - Static route config

#### Traffic and Statistics Commands
12. `show ipv6 traffic` - IPv6 protocol statistics
13. `show interfaces eth0 counters` - Interface traffic counters
14. `show interfaces eth0 counters detailed` - Detailed interface statistics

#### Ping Commands
15. `ping ipv6 vrf mgmt <destination>` - Ping via mgmt VRF
16. `ping ipv6 <destination>` - Ping via default VRF (for negative tests)

### Privileged/Sudo Commands

#### sudo vtysh Commands
1. `sudo vtysh -c "show vrf"` - VRF information via FRR
2. `sudo vtysh -c "show ipv6 route vrf mgmt"` - Mgmt VRF routes via FRR
3. `sudo vtysh -c "show ipv6 route vrf mgmt <prefix>"` - Specific route via FRR
4. `sudo vtysh -c "show ipv6 interface brief vrf mgmt"` - Interfaces via FRR
5. `sudo vtysh -c "show running-config | section ipv6 route"` - FRR route config

#### sudo System Commands
6. `sudo ping6 -I eth0 <destination>` - Direct IPv6 ping via eth0
7. `sudo traceroute6 -i eth0 <destination>` - IPv6 traceroute via eth0
8. `sudo ip -6 route show vrf mgmt` - Kernel routing table for mgmt VRF
9. `sudo ip -6 route show table mgmt` - Alternative kernel table view

---

## Expected Results Summary

### Route Installation in Management VRF

| Route Prefix | Next-Hop | Interface | VRF | Expected Behavior |
|--------------|----------|-----------|-----|-------------------|
| 2001:db8:external::/48 | 2001:db8:mgmt::254 | eth0 (implicit) | mgmt | Installed, reachable |
| 2001:db8:nms::100/128 | 2001:db8:mgmt::254 | eth0 (implicit) | mgmt | Installed, reachable |
| 2001:db8:backup::/48 | 2001:db8:mgmt::253 | eth0 (explicit) | mgmt | Installed, reachable |

### VRF Isolation Validation

✅ **Management VRF Routes (vrf mgmt)**
   - Visible in: `show ipv6 route vrf mgmt`
   - NOT visible in: `show ipv6 route` (default VRF)
   - Used for: Management traffic only (SSH, SNMP, NMS communication)

✅ **Data VRF Routes (default VRF)**
   - Visible in: `show ipv6 route`
   - NOT visible in: `show ipv6 route vrf mgmt`
   - Used for: Data plane traffic only

✅ **Route Isolation Maintained**
   - No cross-VRF route leakage
   - Ping from default VRF to mgmt-only destinations FAILS
   - Ping from mgmt VRF to data-only destinations FAILS (if not leaked)

### Management Traffic Validation

1. **Management VRF Static Routes**
   - ✅ Routes visible only in `show ipv6 route vrf mgmt`
   - ✅ Routes NOT in default routing table
   - ✅ Route type: Static (S)
   - ✅ Next-hop via management network gateway

2. **Management Traffic Works via Management VRF**
   - ✅ Ping to external mgmt destinations succeeds (via `ping ipv6 vrf mgmt`)
   - ✅ SSH connections via management IP work
   - ✅ SNMP queries via management IP work (if configured)
   - ✅ Traffic egresses via eth0 (management interface)

3. **Route Isolation Maintained**
   - ✅ No cross-VRF route leakage observed
   - ✅ Management routes confined to mgmt VRF
   - ✅ Data routes confined to default VRF
   - ✅ Negative tests confirm isolation (ping from wrong VRF fails)

4. **Interface Counters for Management VRF**
   - ✅ eth0 counters increment during mgmt traffic
   - ✅ Data plane interface counters do NOT increment during mgmt traffic
   - ✅ Traffic statistics confirm VRF isolation

5. **Data VRF Routes Remain Unaffected**
   - ✅ Data plane routing table unchanged by mgmt VRF config
   - ✅ Data traffic forwarding continues normally
   - ✅ Complete independence between mgmt and data VRFs

### Enable/Disable Functionality

1. **Global Configuration Mode Enable/Disable**
   - ✅ `no ipv6 route vrf mgmt ...` removes route from table
   - ✅ Ping fails after route removal
   - ✅ `ipv6 route vrf mgmt ...` re-adds route successfully
   - ✅ Ping succeeds after route re-addition
   - ✅ Multiple enable/disable cycles work correctly

2. **Interface Mode Enable/Disable**
   - ✅ `interface eth0` → `shutdown` brings interface down
   - ✅ Routes remain in config but become inactive
   - ✅ Ping fails when interface is down
   - ✅ `interface eth0` → `no shutdown` brings interface up
   - ✅ Routes become active automatically
   - ✅ Ping succeeds after interface recovery

### CLI Consistency

1. ✅ Klish CLI shows routes correctly (`show ipv6 route vrf mgmt`)
2. ✅ vtysh shows same routes (`sudo vtysh -c "show ipv6 route vrf mgmt"`)
3. ✅ Kernel routing table matches (`sudo ip -6 route show vrf mgmt`)
4. ✅ Running-config shows all static route commands
5. ✅ Configuration persists after `write memory`

---

## Test Execution Command

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/routing/static/test_static_ipv6_mgmt_vrf.py \
  --logs-path ./logs/test_ipv6_static_mgmt_vrf_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

---

## Test Data and Prerequisites Checklist

### Prerequisites Checklist

- [ ] Testbed file available at `/home/adminuser/draksha/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- [ ] Both DUTs accessible via SSH
- [ ] IPv6 forwarding enabled on both DUTs
- [ ] Management VRF support available (default in SONiC)
- [ ] Management interface (eth0) configured with IPv6
- [ ] Management network provides IPv6 connectivity
- [ ] Admin/sudo access available
- [ ] External management destinations available for testing (or use gateway as test target)

### Test Data Requirements

- **Management VRF Name:** mgmt (default)
- **Management Interface:** eth0
- **Device Management IPs:**
  - D1: 192.168.100.142 (IPv4), 2001:db8:mgmt::142 (IPv6)
  - D2: 192.168.100.97 (IPv4), 2001:db8:mgmt::97 (IPv6)
- **Management Gateway:** 2001:db8:mgmt::254 (or actual mgmt network gateway)
- **Test Destinations:**
  - External network: 2001:db8:external::/48
  - Specific host: 2001:db8:nms::100/128
  - Backup network: 2001:db8:backup::/48

---

## Cleanup Steps

After test completion:

```bash
# On D1
configure terminal

# Remove all management VRF static routes
no ipv6 route vrf mgmt 2001:db8:external::/48 2001:db8:mgmt::254
no ipv6 route vrf mgmt 2001:db8:nms::100/128 2001:db8:mgmt::254
no ipv6 route vrf mgmt 2001:db8:backup::/48 eth0 2001:db8:mgmt::253

exit

# Verify cleanup
show ipv6 route vrf mgmt
# Should show only connected routes for eth0

# Note: Do NOT remove the management VRF itself or eth0 configuration
# These are part of the base system management infrastructure
```

---

## Related Test Cases

- **TC-IP-STATIC-IPV6-001:** Basic IPv6 static route configuration
- **TC-IP-STATIC-IPV6-006:** IPv6 static route with blackhole
- **TC-IP-STATIC-IPV6-007:** IPv6 static route with data VRF
- **TC-IP-STATIC-IPV6-008:** IPv6 static route with management VRF (this test)
- **TC-IP-STATIC-004:** IPv4 management VRF static routes

---

## Test Case Status

- **Author:** Generated from test plan 2.1.8
- **Status:** Ready for Implementation
- **Priority:** P1 (High - Management plane critical)
- **Automation:** Suitable for automated testing
- **Estimated Duration:** 40-50 minutes (manual execution)

---

## Important Notes

### Management VRF Specific Considerations

1. **Management VRF is Pre-configured**
   - The "mgmt" VRF exists by default in SONiC
   - eth0 is automatically assigned to management VRF
   - Do NOT delete or modify the mgmt VRF itself during testing

2. **Security Isolation**
   - Management VRF provides critical security isolation
   - Management traffic (SSH, SNMP) must NOT leak to data plane
   - Data traffic must NOT leak to management plane
   - VRF isolation is a security requirement, not just a feature

3. **Interface Naming**
   - Management interface is typically named "eth0" (not "Ethernet0")
   - This is an out-of-band management interface
   - Different from data plane interfaces (Ethernet0, Ethernet4, etc.)

4. **Traffic Types via Management VRF**
   - SSH connections to device
   - SNMP queries/traps
   - NMS (Network Management System) communication
   - Syslog to remote servers
   - NTP synchronization (if configured)
   - TACACS+/RADIUS authentication (if configured)

5. **Testing Limitations**
   - Some management destinations may not be available in test environment
   - Can use management gateway as ping target for basic reachability
   - SSH/SNMP tests may require external infrastructure

6. **Route Persistence**
   - Management VRF routes persist across reboots (if saved)
   - Critical for maintaining remote management access
   - Always verify `write memory` after configuration changes

---

## Success Criteria

### Test Passes If:

- ✅ All management VRF static routes install successfully
- ✅ Routes visible only in `show ipv6 route vrf mgmt` (not in default VRF)
- ✅ Management traffic (ping via mgmt VRF) works correctly
- ✅ VRF isolation strictly maintained (no route leakage)
- ✅ Interface counters for eth0 increment during mgmt traffic
- ✅ Data VRF routes completely unaffected by mgmt VRF configuration
- ✅ Enable/disable works in both global config and interface mode
- ✅ CLI consistency across klish, vtysh, and kernel routing tables
- ✅ Configuration persists after save
- ✅ Interface shutdown/no-shutdown properly affects mgmt routes

### Test Fails If:

- ❌ Any management VRF route fails to install
- ❌ Routes leak between management and data VRFs
- ❌ Ping via mgmt VRF fails to reach valid destinations
- ❌ Data plane traffic affected by mgmt VRF configuration
- ❌ Interface counters show cross-VRF traffic leakage
- ❌ Enable/disable doesn't work correctly
- ❌ CLI outputs are inconsistent between different methods
- ❌ Routes don't survive interface state changes
- ❌ Configuration doesn't persist after save

---

## References

- SONiC Management Framework HLD
- SONiC VRF HLD: Virtual Routing and Forwarding
- FRR Documentation: VRF Configuration
- Linux VRF Documentation
- Test Plan Section: 2.1.8 - Configure and verify Management VRF Static Route-IPv6
- Related Test Cases: TC-IP-STATIC-IPV6-001 through TC-IP-STATIC-IPV6-007
