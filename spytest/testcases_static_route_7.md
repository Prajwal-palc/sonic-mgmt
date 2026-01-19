# Test Case: IPv6 Static Route - VRF Configuration and Validation

**Test Case ID:** TC-IP-STATIC-IPV6-007
**Feature:** IPv6 Static Routing
**Sub-feature:** VRF-based IPv6 Static Routes
**Test Plan Section:** 2.1.7

---

## Test Objective

Configure and verify IPv6 static routes in non-default VRF (VRF BLUE). Validate route installation, traffic forwarding, VRF isolation, and state consistency across multiple CLI interfaces. Verify enable/disable functionality at both global configuration and interface levels, and confirm track-based route withdrawal behavior.

---

## Topology Requirements

**Topology:** Two-node (D1-D2) with VRF support
**Testbed File:** `/home/adminuser/draksha/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
**Supported Platforms:** Hardware and Virtual

```
# Topology - 2 nodes with VRF BLUE
# +--------------------------------+                       +--------------------------------+
# |        smic_sonic1 (D1)        |                       |        smic_sonic2 (D2)        |
# | Eth4 2001:db8:1::1/64          |=======================| Eth4 2001:db8:1::2/64          |
# | (member of VRF BLUE)           |                       | (member of VRF BLUE)           |
# | Static routes in VRF BLUE      |                       | Lo0  2001:db8:100::1/128       |
# |                                |                       | (member of VRF BLUE)           |
# +--------------------------------+                       +--------------------------------+
```

**Device Details from Testbed:**
- **D1 (smic_sonic1):** 192.168.100.142
- **D2 (smic_sonic2):** 192.168.100.97
- **Interconnect:** Ethernet4 on both devices

---

## Pre-requisites

1. SONiC devices with IPv6 routing enabled
2. VRF support enabled in SONiC build
3. Track object support (for track-based route tests)
4. Klish CLI access and Click CLI access
5. Admin/sudo privileges for privileged commands
6. Management reachability to both devices
7. Interface Ethernet4 available and operationally capable

---

## Test Variables

Variables should be loaded from: `spytest/vars/routing/static/vars_static_ipv6_vrf.yaml`

**Recommended variable file structure:**
```yaml
min_topology: ["D1D2:1"]

interfaces:
  D1_D2_link:
    D1: Ethernet4
    D2: Ethernet4
    D1_ipv6: 2001:db8:1::1/64
    D2_ipv6: 2001:db8:1::2/64

  D2_loopback:
    interface: Loopback0
    ipv6: 2001:db8:100::1/128

vrf:
  name: BLUE

routes:
  remote_network:
    prefix: 2001:db8:100::/64
    nexthop: 2001:db8:1::2

  blackhole_network:
    prefix: 2001:db8:200::/64

  track_network:
    prefix: 2001:db8:300::/64
    nexthop: 2001:db8:1::2
    track_id: 10

track_config:
  track_id: 10
  type: ip_sla
```

---

## Test Case Details

### Phase 1: VRF Creation and Interface Assignment

**Sub-test 1.1: Create VRF BLUE**

**Test Steps:**
```bash
# On both D1 and D2
configure terminal
ip vrf BLUE
exit
```

**Validation Commands:**
- `show vrf`
- `show running-config | grep vrf`
- `sudo vtysh -c "show vrf"`

**Expected Result:**
- VRF BLUE is created and visible in show output
- VRF status is active
- VRF appears in both standard CLI and vtysh output

---

**Sub-test 1.2: Assign Interface to VRF BLUE**

**Test Steps:**
```bash
# On D1
configure terminal
interface Ethernet4
ipv6 address 2001:db8:1::1/64
ip vrf forwarding BLUE
no shutdown
exit

# On D2
configure terminal
interface Ethernet4
ipv6 address 2001:db8:1::2/64
ip vrf forwarding BLUE
no shutdown
exit
```

**Validation Commands:**
- `show ipv6 interface brief vrf BLUE`
- `show vrf BLUE`
- `show interface Ethernet4`
- `show running-config interface Ethernet4`
- `sudo vtysh -c "show ipv6 interface brief vrf BLUE"`

**Expected Result:**
- Ethernet4 is assigned to VRF BLUE on both devices
- IPv6 addresses are configured correctly
- Interface is operationally up
- Interface does NOT appear in default VRF routing table

---

**Sub-test 1.3: Configure Loopback in VRF BLUE (D2 only)**

**Test Steps:**
```bash
# On D2
configure terminal
interface Loopback0
ipv6 address 2001:db8:100::1/128
ip vrf forwarding BLUE
no shutdown
exit
```

**Validation Commands:**
- `show ipv6 interface brief vrf BLUE`
- `show ipv6 interface Loopback0`

**Expected Result:**
- Loopback0 is created in VRF BLUE
- IPv6 address is assigned
- Interface is up

---

### Phase 2: IPv6 Static Route Configuration in VRF

**Sub-test 2.1: Configure Basic IPv6 Static Route in VRF BLUE**

**Test Steps:**
```bash
# On D1
configure terminal
ipv6 route vrf BLUE 2001:db8:100::/64 2001:db8:1::2
exit
```

**Validation Commands:**
- `show ipv6 route vrf BLUE`
- `show ipv6 route vrf BLUE 2001:db8:100::/64`
- `show running-config | include "ipv6 route vrf"`
- `sudo vtysh -c "show ipv6 route vrf BLUE"`
- `sudo vtysh -c "show ipv6 route vrf BLUE 2001:db8:100::/64"`

**Expected Result:**
- Route 2001:db8:100::/64 is installed in VRF BLUE routing table
- Next-hop is 2001:db8:1::2
- Route type is Static (S)
- Route appears in running configuration
- Route is visible via vtysh commands

---

**Sub-test 2.2: Verify VRF Isolation (No Route Leakage)**

**Test Steps:**
```bash
# On D1 - Check default VRF
show ipv6 route
show ipv6 route 2001:db8:100::/64
```

**Expected Result:**
- Route 2001:db8:100::/64 does NOT appear in default VRF
- Only VRF BLUE routing table contains the static route
- Complete VRF isolation is maintained

---

**Sub-test 2.3: Configure IPv6 Static Route with Interface in VRF**

**Test Steps:**
```bash
# On D1
configure terminal
ipv6 route vrf BLUE 2001:db8:101::/64 Ethernet4
exit
```

**Validation Commands:**
- `show ipv6 route vrf BLUE 2001:db8:101::/64`
- `show running-config | grep "ipv6 route vrf BLUE"`

**Expected Result:**
- Route is installed with outgoing interface Ethernet4
- Route is specific to VRF BLUE

---

**Sub-test 2.4: Configure IPv6 Static Route with Interface + Next-Hop in VRF**

**Test Steps:**
```bash
# On D1
configure terminal
ipv6 route vrf BLUE 2001:db8:102::/64 Ethernet4 2001:db8:1::2
exit
```

**Validation Commands:**
- `show ipv6 route vrf BLUE 2001:db8:102::/64`

**Expected Result:**
- Route is installed with both interface and next-hop
- Route is in VRF BLUE only

---

### Phase 3: IPv6 Static Route with Advanced Attributes in VRF

**Sub-test 3.1: Static Route with Administrative Distance in VRF**

**Test Steps:**
```bash
# On D1
configure terminal
ipv6 route vrf BLUE 2001:db8:103::/64 2001:db8:1::2 distance 50
exit
```

**Validation Commands:**
- `show ipv6 route vrf BLUE 2001:db8:103::/64`
- `show running-config | grep "distance 50"`

**Expected Result:**
- Route is installed with administrative distance 50
- Route preference reflects the configured distance

---

**Sub-test 3.2: Static Route with Tag in VRF**

**Test Steps:**
```bash
# On D1
configure terminal
ipv6 route vrf BLUE 2001:db8:104::/64 2001:db8:1::2 tag 100
exit
```

**Validation Commands:**
- `show ipv6 route vrf BLUE 2001:db8:104::/64`
- `show running-config | grep "tag 100"`

**Expected Result:**
- Route is installed with tag 100
- Tag value is stored and displayed correctly

---

**Sub-test 3.3: IPv6 Blackhole Route in VRF**

**Test Steps:**
```bash
# On D1
configure terminal
ipv6 route vrf BLUE 2001:db8:200::/64 blackhole
exit
```

**Validation Commands:**
- `show ipv6 route vrf BLUE 2001:db8:200::/64`
- `show ipv6 route vrf BLUE | grep blackhole`
- `ping ipv6 2001:db8:200::1 vrf BLUE` (should fail/timeout)

**Expected Result:**
- Route is installed as blackhole type in VRF BLUE
- Traffic to 2001:db8:200::/64 is dropped
- Ping fails with 100% packet loss

---

**Sub-test 3.4: Static Route with Track Object in VRF**

**Test Steps:**
```bash
# On D1 - Configure track object first
configure terminal
track 10 ip sla 10
exit

# Configure static route with track
ipv6 route vrf BLUE 2001:db8:300::/64 2001:db8:1::2 track 10
exit
```

**Validation Commands:**
- `show track`
- `show ipv6 route vrf BLUE 2001:db8:300::/64`
- `show running-config | grep "track 10"`

**Expected Result:**
- Track object 10 is configured
- Route is installed with track dependency
- Route state follows track object state

---

**Sub-test 3.5: Verify Track-Based Route Withdrawal**

**Test Steps:**
```bash
# Simulate track object failure (method depends on track type)
# For IP SLA track, stop the monitored service or configure SLA to fail

# Check route status
show ipv6 route vrf BLUE 2001:db8:300::/64
show track 10
```

**Expected Result:**
- When track object goes down, route is withdrawn from routing table
- When track object comes up, route is re-installed
- Route state directly correlates with track object state

---

### Phase 4: Traffic Validation in VRF

**Sub-test 4.1: IPv6 Reachability Test in VRF**

**Test Steps:**
```bash
# From D1, ping D2's loopback in VRF BLUE
ping ipv6 2001:db8:100::1 vrf BLUE -c 5
```

**Expected Result:**
- Ping succeeds with 0% packet loss
- Traffic is forwarded correctly via static route in VRF BLUE
- No traffic leaks to default VRF

---

**Sub-test 4.2: Verify IPv6 Traffic Statistics in VRF**

**Test Steps:**
```bash
# On D1
show ipv6 traffic vrf BLUE
show interfaces Ethernet4 counters
```

**Expected Result:**
- IPv6 traffic statistics show packets sent/received
- Interface counters increment during traffic tests
- Traffic is isolated to VRF BLUE

---

**Sub-test 4.3: Validate with sudo vtysh IPv6 Traffic Command**

**Test Steps:**
```bash
# On D1
sudo vtysh -c "show ipv6 traffic"
```

**Expected Result:**
- Traffic statistics are visible via vtysh
- Values match standard CLI output

---

### Phase 5: Enable/Disable Static Route in VRF

**Sub-test 5.1: Disable Static Route in Global Config Mode**

**Test Steps:**
```bash
# On D1
configure terminal
no ipv6 route vrf BLUE 2001:db8:100::/64 2001:db8:1::2
exit

# Verify removal
show ipv6 route vrf BLUE 2001:db8:100::/64
ping ipv6 2001:db8:100::1 vrf BLUE -c 3
```

**Expected Result:**
- Route is removed from VRF BLUE routing table
- Ping fails (destination unreachable)
- Running config no longer shows the route

---

**Sub-test 5.2: Re-enable Static Route in VRF**

**Test Steps:**
```bash
# On D1
configure terminal
ipv6 route vrf BLUE 2001:db8:100::/64 2001:db8:1::2
exit

# Verify addition
show ipv6 route vrf BLUE 2001:db8:100::/64
ping ipv6 2001:db8:100::1 vrf BLUE -c 3
```

**Expected Result:**
- Route is re-installed in VRF BLUE
- Ping succeeds
- Route visible in show commands

---

**Sub-test 5.3: Disable Interface in VRF (Interface-Level Disable)**

**Test Steps:**
```bash
# On D1
configure terminal
interface Ethernet4
shutdown
exit

# Check route status
show ipv6 route vrf BLUE
show ipv6 route vrf BLUE 2001:db8:100::/64
show interface Ethernet4
```

**Expected Result:**
- Interface Ethernet4 goes down
- Static routes using Ethernet4 as next-hop or interface become inactive
- Routes remain in config but are not installed in forwarding table

---

**Sub-test 5.4: Re-enable Interface in VRF**

**Test Steps:**
```bash
# On D1
configure terminal
interface Ethernet4
no shutdown
exit

# Verify route restoration
show interface Ethernet4
show ipv6 route vrf BLUE 2001:db8:100::/64
ping ipv6 2001:db8:100::1 vrf BLUE -c 3
```

**Expected Result:**
- Interface Ethernet4 comes up
- Static routes become active again
- Ping succeeds

---

### Phase 6: Comprehensive Show Command Validation

**Sub-test 6.1: Validate All Standard CLI Show Commands**

**Test Steps and Expected Results:**

1. **`show vrf`**
   - VRF BLUE is listed
   - Associated interfaces shown (Ethernet4)
   - VRF state is active

2. **`show ipv6 route vrf BLUE`**
   - All IPv6 routes in VRF BLUE displayed
   - Static routes marked with 'S'
   - Connected routes marked with 'C'
   - Next-hops are correct

3. **`show ipv6 route vrf BLUE 2001:db8:100::/64`**
   - Specific route details displayed
   - Next-hop: 2001:db8:1::2
   - Route type: Static
   - Administrative distance shown

4. **`show running-config`**
   - VRF BLUE configuration present
   - Interface VRF assignments visible
   - All static routes in VRF BLUE listed
   - Track configurations shown

5. **`show ipv6 interface brief vrf BLUE`**
   - Only interfaces in VRF BLUE listed
   - IPv6 addresses correct
   - Interface states shown

6. **`show ipv6 traffic`**
   - IPv6 packet statistics displayed
   - Counters for various IPv6 protocol types
   - Values should increment during traffic tests

7. **`show track`**
   - Track object 10 status displayed
   - Associated routes shown
   - Track type and state visible

---

**Sub-test 6.2: Validate All sudo vtysh Show Commands**

**Test Steps and Expected Results:**

1. **`sudo vtysh -c "show vrf"`**
   - VRF BLUE listed with same details as standard CLI
   - Interface associations correct

2. **`sudo vtysh -c "show ipv6 route vrf BLUE"`**
   - All routes in VRF BLUE displayed
   - Output format may differ slightly from standard CLI
   - All route entries match standard CLI output

3. **`sudo vtysh -c "show ipv6 route vrf BLUE 2001:db8:100::/64"`**
   - Specific route details match standard CLI
   - FRR routing daemon perspective

4. **`sudo vtysh -c "show ipv6 interface brief vrf BLUE"`**
   - Interfaces in VRF BLUE shown
   - Values consistent with standard CLI

5. **`sudo vtysh -c "show ipv6 traffic"`**
   - Traffic statistics displayed
   - Should match or closely correlate with standard CLI values

6. **`sudo vtysh -c "show running-config"`**
   - Complete FRR configuration
   - VRF definitions present
   - Static routes in VRF BLUE visible

---

### Phase 7: Configuration Persistence and Cleanup

**Sub-test 7.1: Save Configuration**

**Test Steps:**
```bash
# Save running config
write memory
# or
copy running-config startup-config
```

**Expected Result:**
- Configuration saved successfully
- Config persists after device reload (optional verification)

---

**Sub-test 7.2: Cleanup - Remove Static Routes**

**Test Steps:**
```bash
# On D1
configure terminal
no ipv6 route vrf BLUE 2001:db8:100::/64 2001:db8:1::2
no ipv6 route vrf BLUE 2001:db8:101::/64 Ethernet4
no ipv6 route vrf BLUE 2001:db8:102::/64 Ethernet4 2001:db8:1::2
no ipv6 route vrf BLUE 2001:db8:103::/64 2001:db8:1::2 distance 50
no ipv6 route vrf BLUE 2001:db8:104::/64 2001:db8:1::2 tag 100
no ipv6 route vrf BLUE 2001:db8:200::/64 blackhole
no ipv6 route vrf BLUE 2001:db8:300::/64 2001:db8:1::2 track 10
exit
```

**Validation:**
- `show ipv6 route vrf BLUE` (should show only connected routes)

---

**Sub-test 7.3: Cleanup - Remove VRF Configuration**

**Test Steps:**
```bash
# On both D1 and D2
configure terminal
interface Ethernet4
no ip vrf forwarding BLUE
exit

# On D2
interface Loopback0
no ip vrf forwarding BLUE
exit

# Remove VRF
no ip vrf BLUE
exit
```

**Validation:**
- `show vrf` (VRF BLUE should be removed)
- `show running-config | grep BLUE` (no VRF BLUE references)

---

## Summary of Validations

### Functional Requirements Validated

✅ **VRF Creation and Management**
   - VRF BLUE created successfully
   - Interfaces assigned to VRF
   - VRF visible in show commands

✅ **IPv6 Static Route Installation in VRF**
   - Routes installed in VRF BLUE routing table
   - Multiple route types supported (nexthop, interface, blackhole)
   - Advanced attributes (distance, tag, track) work correctly

✅ **VRF Isolation**
   - No route leakage between default VRF and VRF BLUE
   - Traffic confined to respective VRF
   - Routing tables completely separate

✅ **Traffic Forwarding in VRF**
   - IPv6 traffic forwards correctly within VRF BLUE
   - Reachability confirmed via ping tests
   - Blackhole routes drop traffic as expected

✅ **Enable/Disable Functionality**
   - Routes can be removed and re-added in global config mode
   - Interface shutdown affects route availability
   - Interface no shutdown restores route functionality

✅ **Track-Based Route Control**
   - Routes associated with track objects
   - Route withdrawn when track object down
   - Route restored when track object up

✅ **Show Command Consistency**
   - All standard CLI show commands work correctly
   - All sudo vtysh show commands work correctly
   - Output consistent across both CLI methods

✅ **Configuration Persistence**
   - Running config reflects all VRF and route configurations
   - Configuration can be saved and restored

---

## Test Execution Command

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/routing/static/test_static_ipv6_vrf.py \
  --logs-path ./logs/test_ipv6_static_vrf_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

---

## Notes

1. **VRF Support:** Ensure SONiC build includes VRF support (CONFIG_VRF=y in kernel)
2. **Track Objects:** Track functionality requires IP SLA or interface tracking configured
3. **CLI Differences:** Some show command output formats may vary between Klish and Click CLI
4. **FRR Integration:** VRF routing is managed by FRR (Free Range Routing) daemon
5. **Management VRF:** Management VRF is separate and should not be confused with data plane VRFs

---

## References

- SONiC VRF HLD: Virtual Routing and Forwarding
- FRR Documentation: VRF Configuration
- Test Plan Section: 2.1.7 - Configure and verify IPv6 Static Route – VRF
- Related Test Cases: TC-IP-STATIC-IPV6-001 through TC-IP-STATIC-IPV6-006

---

## Test Case Status

- **Status:** Ready for Implementation
- **Priority:** High
- **Automation:** Suitable for automated testing
- **Estimated Duration:** 45-60 minutes (manual execution)
