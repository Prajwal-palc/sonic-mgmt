# Test Case: IPv6 Static Route - Blackhole CLI Validation

**Test Case ID:** TC-IP-STATIC-IPV6-006
**Feature:** IPv6 Static Routing
**Sub-feature:** Blackhole Routes with Advanced Attributes
**Test Plan Section:** 2.1.6

---

## Test Objective

Configure and verify IPv6 static routes with blackhole functionality, including advanced attributes such as tags, administrative distance, track objects, and next-hop VRF. Validate route installation, traffic dropping behavior, and state consistency across multiple CLI interfaces.

---

## Topology Requirements

**Topology:** Two-node (D1-D2) with VRF support
**Testbed File:** `/home/adminuser/draksha/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
**Supported Platforms:** Hardware and Virtual

```
# Topology - 2 nodes with VRF
# +---------------------------+                       +---------------------------+
# |        dut1 (D1)          |                       |        dut2 (D2)          |
# | Eth4 2001:db8:1::1/64     |=======================| Eth4 2001:db8:1::2/64     |
# | VRF BLUE configured       |                       | Lo0  2001:db8:100::1/128  |
# |                           |                       | VRF BLUE configured       |
# +---------------------------+                       +---------------------------+
```

---

## Pre-requisites

1. SONiC devices with IPv6 routing enabled
2. VRF support (for VRF-based tests)
3. Track object support (for track-based tests)
4. Klish CLI access
5. Admin/sudo privileges for privileged commands

---

## Test Case Details

### Phase 1: Interface and Base Configuration

**Test Steps:**

1. **Configure IPv6 addressing on transit interfaces**
   - DUT1 Ethernet4: `2001:db8:1::1/64`
   - DUT2 Ethernet4: `2001:db8:1::2/64`

2. **Configure loopback interface on DUT2**
   - DUT2 Loopback0: `2001:db8:100::1/128`

3. **Configure VRF BLUE on both DUTs**
   ```
   config t
   ip vrf BLUE
   exit
   ```

4. **Verify interface status**
   ```
   show ipv6 interface brief
   show interfaces Ethernet4
   ```

**Expected Result:**
- All interfaces are operationally up
- IPv6 addresses are assigned correctly
- VRF BLUE is created and active

---

### Phase 2: IPv6 Static Route Configuration - Multiple Types

**Sub-test 2.1: Basic IPv6 Static Route with Next-Hop**

**Test Steps:**
```
config t
ipv6 route 2001:db8:200::/64 2001:db8:1::2
exit
```

**Validation Commands:**
- `show ipv6 route`
- `show ipv6 route 2001:db8:200::/64`

**Expected Result:**
- Route installed with next-hop `2001:db8:1::2`
- Route type: Static (S)
- Traffic to `2001:db8:200::1` should forward to next-hop

---

**Sub-test 2.2: Static Route with Outgoing Interface**

**Test Steps:**
```
config t
ipv6 route 2001:db8:201::/64 Ethernet4
exit
```

**Validation Commands:**
- `show ipv6 route 2001:db8:201::/64`
- `show running-config | include ipv6 route`

**Expected Result:**
- Route installed with outgoing interface `Ethernet4`
- No specific next-hop IP shown

---

**Sub-test 2.3: Static Route with Interface + Next-Hop**

**Test Steps:**
```
config t
ipv6 route 2001:db8:202::/64 Ethernet4 2001:db8:1::2
exit
```

**Validation Commands:**
- `show ipv6 route 2001:db8:202::/64`

**Expected Result:**
- Route installed with both interface `Ethernet4` and next-hop `2001:db8:1::2`

---

**Sub-test 2.4: Static Route with Blackhole**

**Test Steps:**
```
config t
ipv6 route 2001:db8:203::/64 blackhole
exit
```

**Validation Commands:**
- `show ipv6 route 2001:db8:203::/64`
- `show ipv6 route | grep blackhole`
- `ping ipv6 2001:db8:203::1`

**Expected Result:**
- Route installed as blackhole type
- Ping to destination fails (100% packet loss)
- No ICMP unreachable message returned

---

**Sub-test 2.5: Static Route with Tag**

**Test Steps:**
```
config t
ipv6 route 2001:db8:204::/64 2001:db8:1::2 tag 100
exit
```

**Validation Commands:**
- `show ipv6 route 2001:db8:204::/64`
- Verify tag value in route output

**Expected Result:**
- Route installed with tag `100`
- Tag visible in detailed route output

---

**Sub-test 2.6: Static Route with Administrative Distance**

**Test Steps:**
```
config t
ipv6 route 2001:db8:205::/64 2001:db8:1::2 preference 200
exit
```

**Validation Commands:**
- `show ipv6 route 2001:db8:205::/64`

**Expected Result:**
- Route installed with administrative distance `200`
- Lower preference routes take priority if available

---

**Sub-test 2.7: Static Route with Track Object**

**Test Steps:**
```
config t
track 1 interface Ethernet4 line-protocol
exit
ipv6 route 2001:db8:206::/64 2001:db8:1::2 track 1
exit
```

**Validation Commands:**
- `show track`
- `show ipv6 route 2001:db8:206::/64`

**Expected Result:**
- Track object `1` is up when Ethernet4 is up
- Route is installed when track object is up
- Route is removed when track object goes down (interface shutdown)

---

**Sub-test 2.8: Static Route with Next-Hop VRF**

**Test Steps:**
```
config t
ipv6 route vrf BLUE 2001:db8:207::/64 2001:db8:1::2
exit
```

**Validation Commands:**
- `show ipv6 route vrf BLUE`
- `show ipv6 route vrf BLUE 2001:db8:207::/64`

**Expected Result:**
- Route installed in VRF BLUE routing table
- Route NOT visible in default/global routing table
- VRF isolation maintained

---

**Sub-test 2.9: Save Configuration**

**Test Steps:**
```
copy running-config startup-config
```

**Validation Commands:**
- `show running-config | include ipv6 route`

**Expected Result:**
- All configured routes persist in running-config
- Configuration saved successfully

---

### Phase 3: Routing Table Verification

**Test Steps:**

1. **Check complete IPv6 routing table**
   ```
   show ipv6 route
   ```

2. **Verify static routes only**
   ```
   show ipv6 route static
   ```

3. **Verify VRF routing table**
   ```
   show ipv6 route vrf BLUE
   ```

4. **Check running configuration**
   ```
   show running-config | include ipv6 route
   ```

**Expected Result:**
- All 8+ static routes visible in routing table
- Blackhole route (2001:db8:203::/64) shows blackhole attribute
- VRF route (2001:db8:207::/64) only in VRF BLUE table
- Routes with tags show tag values
- Routes with custom preference show correct distance

---

### Phase 4: Blackhole Route Validation

**Test Steps:**

1. **Verify blackhole route installation**
   ```
   show ipv6 route 2001:db8:203::/64
   ```

2. **Test traffic to blackhole destination**
   ```
   ping ipv6 2001:db8:203::1 count 5
   ```

3. **Verify no forwarding occurs**
   - Check IPv6 traffic counters before and after ping
   ```
   show ipv6 traffic
   ```

4. **Verify no ICMP unreachable generated**
   - Observe ping output for silence (no unreachable messages)

**Expected Result:**
- Blackhole route visible in routing table
- Ping shows 100% packet loss
- No ICMP unreachable messages sent
- Traffic is silently dropped at routing layer

---

### Phase 5: Track Object Dynamic Behavior

**Test Steps:**

1. **Verify track object status**
   ```
   show track
   ```

2. **Shutdown tracked interface**
   ```
   config t
   interface Ethernet4
   shutdown
   exit
   exit
   ```

3. **Verify route removal**
   ```
   show ipv6 route 2001:db8:206::/64
   ```

4. **Re-enable interface**
   ```
   config t
   interface Ethernet4
   no shutdown
   exit
   exit
   ```

5. **Verify route reinstallation**
   ```
   show ipv6 route 2001:db8:206::/64
   ```

**Expected Result:**
- Track object initially shows "Up" state
- Route 2001:db8:206::/64 present when track is up
- Track object changes to "Down" when interface shutdown
- Route 2001:db8:206::/64 removed from routing table
- Track object returns to "Up" when interface re-enabled
- Route automatically reinstalled

---

### Phase 6: Privileged Command Validation (sudo/vtysh)

**Test Steps:**

1. **Check IPv6 routes via kernel**
   ```
   sudo vtysh -c "show ipv6 route"
   ```

2. **Check system-level IPv6 routing table**
   ```
   sudo ip -6 route show
   ```

3. **Verify VRF routes**
   ```
   sudo vtysh -c "show ipv6 route vrf BLUE"
   ```

4. **Test traceroute to blackhole**
   ```
   sudo traceroute6 2001:db8:203::1
   ```

5. **Test traceroute to valid route**
   ```
   sudo traceroute6 2001:db8:100::1
   ```

**Expected Result:**
- vtysh shows same routes as klish CLI
- System kernel routing table contains all routes
- Blackhole route visible in kernel table with "blackhole" attribute
- Traceroute to blackhole destination shows immediate failure
- Traceroute to valid destination shows hops

---

### Phase 7: Route Priority and Selection

**Test Steps:**

1. **Configure duplicate route with different preference**
   ```
   config t
   ipv6 route 2001:db8:200::/64 2001:db8:1::3 preference 250
   exit
   ```

2. **Verify active route selection**
   ```
   show ipv6 route 2001:db8:200::/64
   ```

3. **Remove higher priority route**
   ```
   config t
   no ipv6 route 2001:db8:200::/64 2001:db8:1::2
   exit
   ```

4. **Verify backup route activation**
   ```
   show ipv6 route 2001:db8:200::/64
   ```

**Expected Result:**
- Route with lower preference value (default 1) is active
- Higher preference route (250) is backup
- Backup route activates when primary is removed
- Only one active route per prefix shown in FIB

---

### Phase 8: Config Mode Enable/Disable

**Test Steps:**

1. **Remove blackhole route**
   ```
   config t
   no ipv6 route 2001:db8:203::/64 blackhole
   exit
   ```

2. **Verify removal**
   ```
   show ipv6 route 2001:db8:203::/64
   ```

3. **Test traffic (should timeout/fail differently)**
   ```
   ping ipv6 2001:db8:203::1 count 3
   ```

4. **Re-add blackhole route**
   ```
   config t
   ipv6 route 2001:db8:203::/64 blackhole
   exit
   ```

5. **Verify restoration**
   ```
   show ipv6 route 2001:db8:203::/64
   ```

**Expected Result:**
- Route successfully removed from routing table
- Traffic behavior changes (may get unreachable or timeout)
- Route successfully re-added
- Blackhole behavior restored

---

### Phase 9: Interface Mode Enable/Disable

**Test Steps:**

1. **Verify interface-based route is active**
   ```
   show ipv6 route 2001:db8:201::/64
   ```

2. **Shutdown interface**
   ```
   config t
   interface Ethernet4
   shutdown
   exit
   exit
   ```

3. **Verify route becomes inactive**
   ```
   show ipv6 route 2001:db8:201::/64
   show ipv6 interface brief
   ```

4. **Test traffic (should fail)**
   ```
   ping ipv6 2001:db8:201::1 count 3
   ```

5. **Re-enable interface**
   ```
   config t
   interface Ethernet4
   no shutdown
   exit
   exit
   ```

6. **Verify route restoration**
   ```
   show ipv6 route 2001:db8:201::/64
   ```

**Expected Result:**
- Route visible when interface is up
- Route removed/inactive when interface is down
- Traffic fails when interface is down
- Route automatically restored when interface comes back up

---

### Phase 10: VRF Isolation Validation

**Test Steps:**

1. **Verify VRF route isolation**
   ```
   show ipv6 route vrf BLUE
   show ipv6 route
   ```

2. **Confirm route in VRF only**
   - Route 2001:db8:207::/64 should only appear in VRF BLUE
   - Should NOT appear in default/global table

3. **Test cross-VRF leak (negative test)**
   ```
   ping ipv6 2001:db8:207::1
   ```

4. **Verify VRF traffic statistics**
   ```
   show ipv6 traffic
   ```

**Expected Result:**
- VRF BLUE contains route 2001:db8:207::/64
- Global routing table does NOT contain this route
- Ping from global VRF fails (no route)
- VRF isolation properly maintained

---

## Complete Show Command List

### Standard Klish CLI Commands

1. `show ipv6 route` - Display entire IPv6 routing table
2. `show ipv6 route static` - Show only static routes
3. `show ipv6 route <prefix>` - Show specific route (e.g., 2001:db8:203::/64)
4. `show ipv6 route vrf BLUE` - Show VRF-specific routing table
5. `show running-config | include ipv6 route` - Show static route configuration
6. `show ipv6 interface brief` - Show IPv6 interface status and addresses
7. `show interfaces <int>` - Show detailed interface information (e.g., Ethernet4)
8. `show ipv6 traffic` - Show IPv6 protocol statistics
9. `show track` - Show track object status
10. `ping ipv6 <dest>` - Test IPv6 reachability (e.g., ping ipv6 2001:db8:203::1)

### Privileged/Sudo Commands

1. `sudo vtysh -c "show ipv6 route"` - Show routes via FRR vtysh
2. `sudo vtysh -c "show ipv6 route vrf BLUE"` - Show VRF routes via vtysh
3. `sudo ip -6 route show` - Show kernel IPv6 routing table
4. `sudo traceroute6 <dest>` - Trace IPv6 route path (e.g., sudo traceroute6 2001:db8:203::1)

---

## Expected Results Summary

### Route Installation

| Route Type | Prefix | Next-Hop/Attribute | Expected Behavior |
|------------|--------|-------------------|-------------------|
| Basic Next-Hop | 2001:db8:200::/64 | 2001:db8:1::2 | Route installed, traffic forwarded |
| Interface | 2001:db8:201::/64 | Ethernet4 | Route via interface only |
| Interface + NH | 2001:db8:202::/64 | Eth4 + 2001:db8:1::2 | Route with both attributes |
| **Blackhole** | **2001:db8:203::/64** | **blackhole** | **Traffic silently dropped** |
| With Tag | 2001:db8:204::/64 | NH + tag 100 | Route with tag visible |
| With Preference | 2001:db8:205::/64 | NH + pref 200 | Route with AD 200 |
| With Track | 2001:db8:206::/64 | NH + track 1 | Dynamic route based on track |
| VRF Route | 2001:db8:207::/64 | NH in VRF BLUE | Route in VRF table only |

### Blackhole Route Behavior

1. ✅ Route visible in `show ipv6 route` with blackhole attribute
2. ✅ Traffic to blackhole destination shows 100% packet loss
3. ✅ NO ICMP unreachable messages generated
4. ✅ Silent drop at routing layer (not forwarded to interface)
5. ✅ Blackhole visible in kernel routing table (`ip -6 route`)

### Advanced Attribute Validation

1. **Tag (100):**
   - ✅ Tag value visible in `show ipv6 route <prefix>` detailed output
   - ✅ Can be used for route filtering/policy

2. **Administrative Preference (200):**
   - ✅ Affects route selection priority
   - ✅ Lower value = higher priority
   - ✅ Default static route preference is 1

3. **Track Object (track 1):**
   - ✅ Route installed when track object is UP
   - ✅ Route removed when track object is DOWN
   - ✅ Dynamic behavior based on interface state
   - ✅ `show track` displays object status

4. **VRF (BLUE):**
   - ✅ Route only in VRF BLUE routing table
   - ✅ NOT visible in global routing table
   - ✅ VRF isolation maintained
   - ✅ Cross-VRF traffic blocked

### Traffic Validation

1. **To Blackhole Route (2001:db8:203::1):**
   - ✅ Ping fails (100% loss)
   - ✅ No ICMP unreachable
   - ✅ Traceroute shows immediate failure

2. **To Valid Routes:**
   - ✅ Ping succeeds (0% loss)
   - ✅ Traceroute shows path

3. **Interface Down Scenario:**
   - ✅ Interface-based routes removed
   - ✅ Traffic fails
   - ✅ Routes restored when interface up

### CLI Consistency

1. ✅ Klish CLI shows all routes correctly
2. ✅ vtysh shows same routes as klish
3. ✅ Kernel routing table (`ip -6 route`) matches
4. ✅ Running-config shows all static route commands
5. ✅ Configuration persists after save

---

## Test Execution Notes

### Prerequisites Checklist

- [ ] Testbed file available at specified path
- [ ] Both DUTs accessible via SSH
- [ ] IPv6 forwarding enabled on both DUTs
- [ ] VRF support available
- [ ] Track object feature available
- [ ] Admin/sudo access available

### Test Data Requirements

- Interface names from testbed YAML (typically Ethernet4)
- IPv6 addressing plan documented
- VRF name (BLUE)
- Track object ID (1)
- Tag value (100)
- Administrative distance (200)

### Cleanup Steps

After test completion:
```
config t
no ipv6 route 2001:db8:200::/64
no ipv6 route 2001:db8:201::/64
no ipv6 route 2001:db8:202::/64
no ipv6 route 2001:db8:203::/64 blackhole
no ipv6 route 2001:db8:204::/64
no ipv6 route 2001:db8:205::/64
no ipv6 route 2001:db8:206::/64
no ipv6 route vrf BLUE 2001:db8:207::/64
no track 1
no ip vrf BLUE
exit
```

---

## Related Test Cases

- **TC-IP-STATIC-IPV6-001:** Basic IPv6 static route configuration
- **TC-IP-STATIC-IPV6-002:** IPv6 static route with ECMP
- **TC-IP-STATIC-IPV6-003:** IPv6 static route with VRF
- **TC-IP-STATIC-IPV6-004:** IPv6 static route leak between VRFs
- **TC-IP-STATIC-IPV6-005:** IPv6 static route with management VRF
- **TC-IP-STATIC-IPV6-006:** IPv6 static route with blackhole (this test)

---

## Test Case Status

- **Author:** Generated from test plan 2.1.6
- **Status:** Draft
- **Priority:** P1 (High)
- **Automation:** Ready for implementation
- **Estimated Duration:** 30-45 minutes

---

## Notes

1. **Blackhole routes** drop traffic silently without generating ICMP unreachable messages
2. **Track objects** provide dynamic routing based on interface or object state
3. **VRF isolation** must be strictly maintained - routes should not leak between VRFs
4. **Administrative distance** default for static routes is 1 (higher priority than most dynamic protocols)
5. Some advanced features (track objects, VRF) may not be available on all SONiC versions
6. Test should validate both **configuration plane** (show running-config) and **data plane** (ping, traffic flow)

---

## Success Criteria

Test passes if:
- ✅ All 8 static route types install successfully
- ✅ Blackhole route drops traffic silently (100% loss, no ICMP unreachable)
- ✅ Track object dynamically controls route installation
- ✅ VRF isolation properly maintained
- ✅ Tag and preference attributes visible and functional
- ✅ CLI consistency across klish, vtysh, and kernel
- ✅ Interface enable/disable properly affects routes
- ✅ Configuration persists after save

Test fails if:
- ❌ Any route fails to install
- ❌ Blackhole route forwards traffic or generates ICMP
- ❌ Track object doesn't affect route state
- ❌ VRF routes leak to global table
- ❌ CLI outputs are inconsistent
- ❌ Routes don't survive interface state changes
- ❌ Configuration doesn't persist
