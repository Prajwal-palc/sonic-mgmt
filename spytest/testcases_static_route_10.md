# Test Case: Negative IPv6 Static Route CLI Validation

**Test Case ID:** TC-IP-STATIC-IPV6-010
**Feature:** IPv6 Static Routing
**Sub-feature:** Negative Testing - Invalid Configuration Handling
**Test Plan Section:** 2.1.10

---

## Test Objective

Configure and verify negative test scenarios for IPv6 static routes on DUT. Validate that invalid prefixes, next-hops, and VRFs are properly rejected with appropriate error messages, duplicate routes are handled gracefully, and the system remains stable under invalid configuration attempts. Test rejection of malformed inputs at both global configuration mode and interface mode, ensuring routing processes do not crash and the routing table remains uncorrupted.

---

## Topology Requirements

**Topology:** Two-node (D1-D2) for negative testing
**Testbed File:** `/home/adminuser/draksha/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
**Supported Platforms:** Hardware and Virtual

```
# Topology - Negative Testing Configuration
# +--------------------------------+                       +--------------------------------+
# |        smic_sonic1 (D1)        |                       |        smic_sonic2 (D2)        |
# |            (DUT)               |                       |       (Peer Device)            |
# |                                |      Ethernet4        |                                |
# | IPv6: 2001:db8:10::1/64        |=======================| IPv6: 2001:db8:10::2/64        |
# | VRF: RED (configured)          |                       |                                |
# |                                |                       |                                |
# +--------------------------------+                       +--------------------------------+
#
# Test scenarios:
#   - Invalid prefix formats (malformed, out-of-range)
#   - Invalid next-hop addresses (non-routable, malformed)
#   - Non-existent VRF references
#   - Duplicate route handling
#   - Interface enable/disable operations with routes
```

**Device Details from Testbed:**
- **D1 (smic_sonic1):** Management IP: 192.168.100.142
- **D2 (smic_sonic2):** Management IP: 192.168.100.97
- **Data Plane Link:** Ethernet4 (between D1 and D2)

---

## Pre-requisites

1. SONiC devices with IPv6 routing enabled
2. FRR routing daemon running
3. Klish CLI and Click CLI access
4. Admin/sudo privileges for privileged commands
5. VRF support enabled (for VRF negative testing)
6. Clean routing table state before test execution
7. System logging enabled for error message validation

---

## Test Variables

Variables should be loaded from: `spytest/vars/routing/static/vars_static_ipv6_negative.yaml`

**Recommended variable file structure:**
```yaml
min_topology: ["D1D2:1"]  # Single link between D1 and D2

# Valid configuration (baseline)
valid_config:
  D1_interface: Ethernet4
  D1_ipv6: "2001:db8:10::1/64"
  D2_interface: Ethernet4
  D2_ipv6: "2001:db8:10::2/64"
  valid_nexthop: "2001:db8:10::2"
  valid_prefix: "2001:db8:20::/64"

# Test VRF
test_vrf:
  name: "RED"
  rd: "100:1"

# Invalid test cases
invalid_prefixes:
  - "2001:db8:xyz::/64"           # Invalid hex characters
  - "2001:db8::1::2/64"           # Double ::
  - "2001:gggg::/64"              # Invalid hex
  - "2001:db8::/256"              # Invalid prefix length
  - "2001:db8::/0"                # Invalid default route
  - "invalid_prefix"              # Completely malformed
  - "192.168.1.0/24"              # IPv4 in IPv6 command
  - "2001:db8:1234:5678:9abc:def0:1234:5678:90ab/64"  # Too long

invalid_nexthops:
  - "2001:db8:xyz::1"             # Invalid hex
  - "fe80::1"                     # Link-local without interface
  - "ff02::1"                     # Multicast address
  - "::1"                         # Loopback
  - "::"                          # Unspecified
  - "192.168.1.1"                 # IPv4 in IPv6 command
  - "2001:db8::gggg"              # Invalid hex
  - "not_an_ip"                   # Completely malformed

invalid_vrfs:
  - "NON_EXISTENT_VRF"
  - "vrf_999"
  - "INVALID-VRF"
  - ""                            # Empty string
  - "VRF WITH SPACES"

# Duplicate route scenarios
duplicate_routes:
  prefix: "2001:db8:30::/64"
  nexthop: "2001:db8:10::2"
  distance: 1
```

---

## Test Procedure

### Setup Phase

#### Step 1: Initial Configuration
**Action:**
```bash
# On D1 - Configure baseline IPv6 connectivity
configure terminal
interface Ethernet4
ipv6 address 2001:db8:10::1/64
no shutdown
exit

# On D2 - Configure peer interface
configure terminal
interface Ethernet4
ipv6 address 2001:db8:10::2/64
no shutdown
exit

# On D1 - Create test VRF for negative testing
configure terminal
vrf RED
exit

# Verify baseline connectivity
ping ipv6 2001:db8:10::2 count 3
```

**Expected Result:**
- Interfaces configured successfully
- VRF RED created
- IPv6 connectivity verified between D1 and D2

**Show Commands:**
```bash
show ipv6 interface brief
show vrf
show ipv6 route
```

---

### Test Case 1: Invalid Prefix Format Rejection

#### Test Case 1.1: Invalid Hexadecimal Characters in Prefix
**Action:**
```bash
# On D1 - Klish CLI
configure terminal
ipv6 route 2001:db8:xyz::/64 2001:db8:10::2
```

**Expected Result:**
- Command rejected with error: "Invalid IPv6 prefix format"
- Route NOT added to routing table
- No routing process restart

**Validation:**
```bash
show ipv6 route
show running-config | grep "ipv6 route"
show logging | grep -i error
```

#### Test Case 1.2: Invalid Prefix Length
**Action:**
```bash
# On D1 - Klish CLI
configure terminal
ipv6 route 2001:db8::/256 2001:db8:10::2
ipv6 route 2001:db8::/129 2001:db8:10::2
```

**Expected Result:**
- Command rejected with error: "Invalid prefix length (must be 0-128)"
- Routes NOT added to routing table

**Validation:**
```bash
show ipv6 route
show running-config | grep "ipv6 route"
```

#### Test Case 1.3: Malformed IPv6 Prefix
**Action:**
```bash
# On D1 - Klish CLI
configure terminal
ipv6 route invalid_prefix 2001:db8:10::2
ipv6 route 192.168.1.0/24 2001:db8:10::2
ipv6 route 2001:db8::1::2/64 2001:db8:10::2
```

**Expected Result:**
- All commands rejected with appropriate error messages
- No routes added to routing table
- System remains stable

**Validation:**
```bash
show ipv6 route
show process | grep bgp
show process | grep zebra
```

---

### Test Case 2: Invalid Next-Hop Address Rejection

#### Test Case 2.1: Invalid Next-Hop Format
**Action:**
```bash
# On D1 - Klish CLI
configure terminal
ipv6 route 2001:db8:20::/64 2001:db8:xyz::1
ipv6 route 2001:db8:20::/64 2001:db8::gggg
ipv6 route 2001:db8:20::/64 not_an_ip
```

**Expected Result:**
- Commands rejected with error: "Invalid IPv6 address format"
- No routes added

**Validation:**
```bash
show ipv6 route
show running-config | grep "ipv6 route"
show logging
```

#### Test Case 2.2: Non-Routable Next-Hop Addresses
**Action:**
```bash
# On D1 - Klish CLI
configure terminal
ipv6 route 2001:db8:20::/64 ::1
ipv6 route 2001:db8:20::/64 ::
ipv6 route 2001:db8:20::/64 ff02::1
```

**Expected Result:**
- Commands may be accepted but routes marked as unreachable
- Or rejected with warning about non-routable next-hop
- Routing table remains stable

**Validation:**
```bash
show ipv6 route
show ipv6 route 2001:db8:20::/64
```

#### Test Case 2.3: Link-Local Next-Hop Without Interface
**Action:**
```bash
# On D1 - Klish CLI
configure terminal
ipv6 route 2001:db8:20::/64 fe80::1
```

**Expected Result:**
- Command rejected or warning: "Link-local next-hop requires interface specification"

**Validation:**
```bash
show ipv6 route
show running-config | grep "ipv6 route"
```

#### Test Case 2.4: IPv4 Address as IPv6 Next-Hop
**Action:**
```bash
# On D1 - Klish CLI
configure terminal
ipv6 route 2001:db8:20::/64 192.168.1.1
```

**Expected Result:**
- Command rejected with error: "Invalid IPv6 address format"

**Validation:**
```bash
show ipv6 route
```

---

### Test Case 3: Non-Existent VRF Rejection

#### Test Case 3.1: Configure Route with Non-Existent VRF
**Action:**
```bash
# On D1 - Klish CLI
configure terminal
ipv6 route vrf NON_EXISTENT_VRF 2001:db8:20::/64 2001:db8:10::2
ipv6 route vrf vrf_999 2001:db8:20::/64 2001:db8:10::2
ipv6 route vrf INVALID-VRF 2001:db8:20::/64 2001:db8:10::2
```

**Expected Result:**
- Commands rejected with error: "VRF not found" or "VRF does not exist"
- No routes added to any routing table

**Validation:**
```bash
show vrf
show ipv6 route vrf RED
show running-config | grep "ipv6 route vrf"
```

#### Test Case 3.2: Query Non-Existent VRF
**Action:**
```bash
# On D1 - Klish CLI
show vrf | include NON_EXISTENT_VRF
show ipv6 route vrf NON_EXISTENT_VRF
```

**Expected Result:**
- Commands return empty result or "VRF not found"
- No system errors or crashes

---

### Test Case 4: Duplicate Route Handling

#### Test Case 4.1: Add Same Route Twice (Exact Duplicate)
**Action:**
```bash
# On D1 - Klish CLI
configure terminal
ipv6 route 2001:db8:30::/64 2001:db8:10::2
ipv6 route 2001:db8:30::/64 2001:db8:10::2
```

**Expected Result:**
- First command succeeds
- Second command either:
  - Silently ignored (idempotent)
  - Warning: "Route already exists"
  - Refreshes existing route
- Only ONE route entry in routing table
- No duplicate entries

**Validation:**
```bash
show ipv6 route 2001:db8:30::/64
show running-config | grep "ipv6 route 2001:db8:30::"
# Count occurrences (should be 1)
```

#### Test Case 4.2: Add Same Route with Different Distance
**Action:**
```bash
# On D1 - Klish CLI
configure terminal
ipv6 route 2001:db8:40::/64 2001:db8:10::2 10
ipv6 route 2001:db8:40::/64 2001:db8:10::2 20
```

**Expected Result:**
- Both routes installed (different administrative distances)
- Primary route (distance 10) is active
- Backup route (distance 20) is standby

**Validation:**
```bash
show ipv6 route 2001:db8:40::/64
# Should show both routes with different distances
```

#### Test Case 4.3: Add Same Route with Different Next-Hop (ECMP)
**Action:**
```bash
# On D1 - First configure second interface for ECMP
configure terminal
interface Ethernet8
ipv6 address 2001:db8:11::1/64
no shutdown
exit

# On D2 - Configure corresponding interface
configure terminal
interface Ethernet8
ipv6 address 2001:db8:11::2/64
no shutdown
exit

# On D1 - Add ECMP routes
configure terminal
ipv6 route 2001:db8:50::/64 2001:db8:10::2
ipv6 route 2001:db8:50::/64 2001:db8:11::2
```

**Expected Result:**
- Both routes installed as ECMP
- Single routing entry with multiple next-hops

**Validation:**
```bash
show ipv6 route 2001:db8:50::/64
# Should show both next-hops under same prefix
```

---

### Test Case 5: Interface Enable/Disable with Static Routes

#### Test Case 5.1: Add Route, Disable Interface (Global Config Mode)
**Action:**
```bash
# On D1 - Klish CLI
configure terminal
ipv6 route 2001:db8:60::/64 2001:db8:10::2
exit

# Verify route is active
show ipv6 route 2001:db8:60::/64

# Disable interface in config mode
configure terminal
interface Ethernet4
shutdown
exit
```

**Expected Result:**
- Route initially active
- After interface shutdown, route becomes inactive/unreachable
- Route configuration remains in running-config
- No system crash or routing process restart

**Validation:**
```bash
show ipv6 route 2001:db8:60::/64
show ipv6 interface brief
show running-config interface Ethernet4
show running-config | grep "ipv6 route 2001:db8:60::"
```

#### Test Case 5.2: Re-Enable Interface
**Action:**
```bash
# On D1 - Klish CLI
configure terminal
interface Ethernet4
no shutdown
exit

# Wait for interface to come up
sleep 5
```

**Expected Result:**
- Interface comes up
- Static route becomes active again
- Connectivity restored

**Validation:**
```bash
show ipv6 interface brief
show ipv6 route 2001:db8:60::/64
ping ipv6 2001:db8:10::2 count 3
```

#### Test Case 5.3: Interface-Level Operations with Multiple Routes
**Action:**
```bash
# On D1 - Add multiple routes via same next-hop
configure terminal
ipv6 route 2001:db8:70::/64 2001:db8:10::2
ipv6 route 2001:db8:71::/64 2001:db8:10::2
ipv6 route 2001:db8:72::/64 2001:db8:10::2
exit

# Verify all routes active
show ipv6 route | grep 2001:db8:7

# Disable interface
configure terminal
interface Ethernet4
shutdown
exit
```

**Expected Result:**
- All three routes become inactive when interface goes down
- All route configurations persist in running-config

**Validation:**
```bash
show ipv6 route | grep 2001:db8:7
show running-config | grep "ipv6 route 2001:db8:7"
```

---

### Test Case 6: VRF-Specific Negative Tests

#### Test Case 6.1: Add Route to VRF, Then Delete VRF
**Action:**
```bash
# On D1 - Add route to VRF RED
configure terminal
ipv6 route vrf RED 2001:db8:80::/64 2001:db8:10::2
exit

# Verify route in VRF
show ipv6 route vrf RED

# Attempt to delete VRF with active routes
configure terminal
no vrf RED
```

**Expected Result:**
- Route added to VRF successfully
- VRF deletion may be:
  - Rejected: "VRF has active routes"
  - Allowed: Routes automatically removed
- System remains stable

**Validation:**
```bash
show vrf
show ipv6 route vrf RED
show running-config | grep "vrf RED"
```

---

### Test Case 7: System Stability Validation

#### Test Case 7.1: Rapid Invalid Configuration Attempts
**Action:**
```bash
# On D1 - Send multiple invalid commands rapidly
for i in {1..20}; do
  configure terminal
  ipv6 route 2001:db8:invalid::/$i 2001:db8:10::xyz
  ipv6 route vrf NONEXIST 2001:db8::/$i 192.168.1.$i
  exit
done
```

**Expected Result:**
- All commands rejected
- No memory leaks
- No process crashes
- System responsive

**Validation:**
```bash
show process cpu-usage
show process memory
show ipv6 route
show logging | tail -50
```

#### Test Case 7.2: Verify Routing Process Health
**Action:**
```bash
# On D1
show process | grep bgp
show process | grep zebra
show process | grep staticd
```

**Expected Result:**
- All routing processes running
- No abnormal restarts
- Process uptime reasonable

---

### Test Case 8: Validation with Privileged Commands (sudo vtysh)

#### Test Case 8.1: Verify Kernel Routing Table After Invalid Attempts
**Action:**
```bash
# On D1
sudo vtysh -c "show ipv6 route"
sudo ip -6 route show
```

**Expected Result:**
- Kernel routing table consistent with SONiC routing table
- No orphaned or corrupted entries
- Only valid routes present

#### Test Case 8.2: Attempt Invalid Route via vtysh
**Action:**
```bash
# On D1
sudo vtysh -c "configure terminal" -c "ipv6 route 2001:db8:invalid::/64 2001:db8::xyz"
```

**Expected Result:**
- Command rejected with error
- No route added

**Validation:**
```bash
sudo vtysh -c "show ipv6 route" | grep invalid
```

---

### Test Case 9: Error Message Validation

#### Test Case 9.1: Verify Error Messages in Logs
**Action:**
```bash
# On D1 - Trigger various errors and check logging
configure terminal
ipv6 route 2001:db8:xyz::/64 2001:db8:10::2
ipv6 route vrf NONEXIST 2001:db8:20::/64 2001:db8:10::2
exit

# Check system logs
show logging | grep -i "invalid"
show logging | grep -i "error"
show logging | grep -i "failed"
```

**Expected Result:**
- Clear, descriptive error messages in logs
- Errors logged with appropriate severity
- No misleading or cryptic messages

---

### Cleanup Phase

**Action:**
```bash
# On D1 - Remove test configurations
configure terminal
no ipv6 route 2001:db8:30::/64 2001:db8:10::2
no ipv6 route 2001:db8:40::/64 2001:db8:10::2 10
no ipv6 route 2001:db8:40::/64 2001:db8:10::2 20
no ipv6 route 2001:db8:50::/64 2001:db8:10::2
no ipv6 route 2001:db8:50::/64 2001:db8:11::2
no ipv6 route 2001:db8:60::/64 2001:db8:10::2
no ipv6 route 2001:db8:70::/64 2001:db8:10::2
no ipv6 route 2001:db8:71::/64 2001:db8:10::2
no ipv6 route 2001:db8:72::/64 2001:db8:10::2
no vrf RED
exit

# Re-enable interfaces if disabled
configure terminal
interface Ethernet4
no shutdown
exit
interface Ethernet8
no shutdown
exit
```

---

## Complete Show Command Reference

### Klish CLI Commands (Regular)
```bash
show ipv6 route
show ipv6 route <prefix>
show ipv6 route vrf <vrf-name>
show vrf
show vrf | include RED
show running-config
show running-config | grep "ipv6 route"
show logging
show logging | grep -i error
show ipv6 traffic
show process
show process | grep bgp
show process | grep zebra
show ipv6 interface brief
show ipv6 interface Ethernet4
```

### Privileged Commands (sudo/vtysh)
```bash
sudo vtysh -c "show ipv6 route"
sudo vtysh -c "show running-config"
sudo ip -6 route show
sudo ip -6 route show | grep <prefix>
sudo vtysh -c "show ipv6 route vrf RED"
```

---

## Expected Results Summary

### Invalid Input Handling
1. **Invalid Prefixes:**
   - Malformed prefixes immediately rejected
   - Error message: "Invalid IPv6 prefix format"
   - No route added to routing table

2. **Invalid Next-Hops:**
   - Malformed next-hop addresses rejected
   - Error message: "Invalid IPv6 address format"
   - Non-routable addresses flagged or rejected

3. **Non-Existent VRF:**
   - Commands rejected immediately
   - Error message: "VRF not found" or "VRF does not exist"
   - No impact on existing VRF routing tables

### Duplicate Route Handling
1. **Exact Duplicates:**
   - Idempotent behavior (silently ignored or warning issued)
   - Single route entry maintained
   - No duplicate entries in routing table

2. **Different Distance:**
   - Both routes installed (primary and backup)
   - Lower distance route is active
   - Automatic failover if active route fails

3. **Different Next-Hop (ECMP):**
   - Multiple next-hops installed under single prefix
   - Load balancing enabled across paths

### System Stability
1. **No Crashes:**
   - All routing processes remain running
   - No unexpected process restarts
   - No kernel panics or system hangs

2. **No Routing Table Corruption:**
   - Routing table remains consistent
   - No orphaned entries
   - Kernel and application routing tables synchronized

3. **Resource Stability:**
   - No memory leaks from invalid commands
   - CPU usage normal
   - System responsive to commands

### Error Messages
1. **Clear and Descriptive:**
   - Error messages clearly indicate the problem
   - Suggest correct format or valid values
   - Logged with appropriate severity

2. **Logged Appropriately:**
   - Errors visible in `show logging`
   - Syslog entries created for significant errors
   - Debug information available if needed

---

## Test Execution Notes

### Test Duration
- **Estimated Time:** 45-60 minutes
- **Setup:** 5 minutes
- **Test Execution:** 40-50 minutes
- **Cleanup:** 5 minutes

### Dependencies
- Requires clean system state before execution
- VRF support must be enabled in SONiC build
- Admin/sudo access required for privileged commands
- System logging enabled for error validation

### Automation Considerations
- Test can be fully automated using SPyTest framework
- Error message validation requires regex pattern matching
- Process monitoring should include CPU and memory sampling
- Log analysis requires parsing syslog entries

### Risk Assessment
- **Risk Level:** Low (negative testing, no production impact expected)
- **Rollback:** Clean configuration automatically in cleanup phase
- **Safety:** All tests non-destructive, only testing CLI rejection

---

## Pass/Fail Criteria

### PASS Criteria
✓ All invalid prefixes rejected with appropriate error messages
✓ All invalid next-hops rejected or flagged as unreachable
✓ Non-existent VRF references rejected immediately
✓ Duplicate routes handled per design (idempotent or ECMP)
✓ No routing process crashes or restarts
✓ No routing table corruption (verified via show commands and kernel)
✓ System remains responsive and stable
✓ Error messages clear and actionable
✓ Configuration consistency maintained (running-config matches actual state)
✓ Interface enable/disable operations work correctly with static routes

### FAIL Criteria
✗ Invalid configuration accepted without error
✗ System crash or routing process restart
✗ Routing table corruption or inconsistency
✗ Memory leak or resource exhaustion
✗ Missing or unclear error messages
✗ Configuration inconsistency between CLI and kernel
✗ System becomes unresponsive
✗ Valid routes affected by invalid configuration attempts

---

## References

- **Test Plan:** Static Routing Test Plan Section 2.1.10
- **Feature:** IPv6 Static Routing
- **CLI Type:** Klish (primary), Click/vtysh (validation)
- **Variable File:** `spytest/vars/routing/static/vars_static_ipv6_negative.yaml`
- **Related Test Cases:** TC-IP-STATIC-IPV6-001 through TC-IP-STATIC-IPV6-009

---

## Revision History

| Version | Date       | Author | Description                              |
|---------|------------|--------|------------------------------------------|
| 1.0     | 2025-01-10 | Claude | Initial test case creation               |

---

## Test Execution Command

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/routing/static/test_static_ipv6_negative.py \
  --logs-path ./logs/test_ipv6_negative_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```
