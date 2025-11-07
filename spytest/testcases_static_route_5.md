# Static Route IPv6 Basic CLI Test Cases

## TC-IP-STATIC-IPV6-001 - Configure and verify IPv6 Static Route – Basic CLI on DUT

**Purpose**: Validate IPv6 static route configuration, forwarding, and removal using basic CLI commands on DUT. Confirm that static routes can be enabled/disabled at both global configuration and interface levels, and that show commands accurately reflect route state in both standard and management VRF contexts.

**Preconditions**:
- Access to two DUTs defined as `smic_sonic1` (D1) and `smic_sonic2` (D2) in `testbeds/testbed_2vs.yaml`
- Management reachability confirmed for both devices
- Interface `Ethernet4` on both DUTs available for IPv6 configuration (per testbed topology)
- IPv6 routing enabled on both devices
- Ability to run privileged CLI commands (`configure terminal`, `do show ...`, and `sudo vtysh`)

**Test Steps**:

### Phase 1: IPv6 Interface Configuration

1. **Configure IPv6 Addressing on Transit Interfaces**:
   - On D1, enter interface configuration mode for Ethernet4:
     ```
     configure terminal
     interface Ethernet4
     ipv6 address 2001:db8:1::1/64
     no shutdown
     exit
     ```
   - On D2, configure Ethernet4 with IPv6 address:
     ```
     configure terminal
     interface Ethernet4
     ipv6 address 2001:db8:1::2/64
     no shutdown
     exit
     ```
   - Verify interface is up and IPv6 addressing is configured:
     - `show ipv6 interface Ethernet4`
     - `show interface status Ethernet4`

2. **Configure IPv6 Address on Remote Interface** (D2 only):
   - Create a loopback or use another interface on D2 for reachability testing:
     ```
     interface Loopback0
     ipv6 address 2001:db8:100::1/128
     no shutdown
     exit
     ```
   - Verify: `show ipv6 interface Loopback0`

### Phase 2: IPv6 Static Route - Global Configuration Mode

3. **Add IPv6 Static Route on D1**:
   - Configure static route to D2's remote network via D2's transit interface:
     ```
     configure terminal
     ipv6 route 2001:db8:100::/64 2001:db8:1::2
     exit
     ```

4. **Validate Route Installation** (Standard CLI):
   - Execute: `show ipv6 route`
     - Confirm route `2001:db8:100::/64` is present
     - Verify next-hop is `2001:db8:1::2`
     - Verify route type is `S` (static)
   - Execute: `show ipv6 route static`
     - Confirm only static routes are displayed
   - Execute: `show running-config | include ipv6 route`
     - Verify route appears in running configuration

5. **Validate Route via VRF Management Context** (if applicable):
   - Execute: `show ipv6 route vrf mgmt`
     - Confirm the static route is NOT present in management VRF (VRF isolation)
   - Execute management VRF-specific checks if device supports separate management plane

6. **Validate Route via Privileged Mode** (sudo vtysh):
   - Execute: `sudo vtysh -c "show ipv6 route"`
     - Confirm route `2001:db8:100::/64` is visible
     - Verify next-hop matches configuration
   - Execute: `sudo vtysh -c "show ipv6 route vrf mgmt"`
     - Verify management VRF isolation (route should not appear here)
   - Execute: `sudo vtysh -c "show running-config | section ipv6 route"`
     - Confirm configuration persistence

### Phase 3: Traffic Validation

7. **Send IPv6 Traffic** (Reachability Test):
   - From D1, ping the remote IPv6 address on D2:
     ```
     ping6 2001:db8:100::1 -c 5
     ```
   - Expected: 0% packet loss, confirming static route is forwarding traffic
   - Verify with: `show ipv6 neighbors` (neighbor discovery should show D2's link-local on Ethernet4)

8. **Validate Traffic Statistics** (Optional):
   - Execute: `show interfaces counters` on Ethernet4
   - Confirm TX/RX packet counts increasing during ping

### Phase 4: Route Disable/Enable in Global Configuration

9. **Disable Static Route**:
   - Remove the static route:
     ```
     configure terminal
     no ipv6 route 2001:db8:100::/64 2001:db8:1::2
     exit
     ```

10. **Verify Route Removal**:
    - Execute: `show ipv6 route`
      - Confirm route `2001:db8:100::/64` is no longer present
    - Execute: `show ipv6 route static`
      - Confirm no static routes to this destination
    - Execute: `show running-config | include ipv6 route`
      - Verify route is removed from running config
    - Execute: `sudo vtysh -c "show ipv6 route"`
      - Confirm route absence in vtysh output

11. **Test Post-Removal Traffic Behavior**:
    - From D1, attempt to ping the remote IPv6 address:
      ```
      ping6 2001:db8:100::1 -c 5
      ```
    - Expected: 100% packet loss or "Network is unreachable" error
    - Confirms route removal prevents forwarding

12. **Re-enable Static Route**:
    - Re-add the static route:
      ```
      configure terminal
      ipv6 route 2001:db8:100::/64 2001:db8:1::2
      exit
      ```
    - Repeat validation steps from **Phase 2** (steps 4-6)
    - Repeat traffic test from **Phase 3** (step 7) - should succeed again

### Phase 5: Route Disable/Enable at Interface Level

13. **Disable Interface** (Ethernet4 on D1):
    - Shutdown the transit interface:
      ```
      configure terminal
      interface Ethernet4
      shutdown
      exit
      ```

14. **Verify Route Behavior with Interface Down**:
    - Execute: `show ipv6 route`
      - Route `2001:db8:100::/64` may still appear but be marked as inactive/down
    - Execute: `show interface status Ethernet4`
      - Confirm interface is administratively down
    - From D1, attempt to ping:
      ```
      ping6 2001:db8:100::1 -c 3
      ```
    - Expected: 100% packet loss (interface down prevents forwarding)

15. **Re-enable Interface**:
    - Bring the interface back up:
      ```
      configure terminal
      interface Ethernet4
      no shutdown
      exit
      ```

16. **Verify Route Recovery**:
    - Wait for interface to come up (check: `show interface status Ethernet4`)
    - Execute: `show ipv6 route`
      - Confirm route `2001:db8:100::/64` is active again
    - Execute: `ping6 2001:db8:100::1 -c 5`
      - Expected: 0% packet loss, traffic resumes

### Phase 6: VRF Isolation and State Consistency

17. **Verify VRF Isolation**:
    - Execute: `show ipv6 route vrf mgmt`
      - Confirm management VRF routing table does NOT contain the static route
    - Execute: `sudo vtysh -c "show ipv6 route vrf mgmt"`
      - Re-confirm via vtysh that VRF isolation is maintained

18. **Verify State Consistency Across CLI Methods**:
    - Compare outputs of:
      - `show ipv6 route` (klish/click CLI)
      - `sudo vtysh -c "show ipv6 route"` (vtysh privileged)
    - Confirm both show identical route entries for `2001:db8:100::/64`
    - Execute: `show running-config | section ipv6`
      - Confirm configuration persistence
    - Execute: `sudo vtysh -c "show running-config | section ipv6"`
      - Confirm consistency between CLI contexts

19. **Final Traffic Validation**:
    - From D1, perform extended ping test:
      ```
      ping6 2001:db8:100::1 -c 10 -i 0.5
      ```
    - Expected: 0% packet loss across all packets
    - Verify: `show ipv6 neighbors` shows stable neighbor entry for D2

**Expected Results**:

1. **Route Installation**:
   - Configured IPv6 static route appears in `show ipv6 route` output
   - Route is flagged with type `S` (static)
   - Next-hop IP address matches configured value (`2001:db8:1::2`)
   - Route appears in both standard CLI and `sudo vtysh` outputs

2. **Forwarding / Reachability**:
   - `ping6` to remote network succeeds with 0% packet loss when route is active
   - IPv6 neighbor discovery functions correctly
   - Traffic statistics show packet transmission on Ethernet4

3. **Route Removal**:
   - `no ipv6 route ...` command successfully removes route from routing table
   - Route disappears from all show commands (`show ipv6 route`, running-config, vtysh)
   - Configuration persistence is maintained

4. **Post-Removal Traffic Behavior**:
   - `ping6` fails with 100% packet loss after route removal
   - Error message indicates "Network is unreachable" or similar
   - Confirms proper route removal and forwarding plane update

5. **VRF Isolation**:
   - Static route configured in default VRF does NOT appear in `show ipv6 route vrf mgmt`
   - Management VRF maintains separate routing table
   - No cross-VRF route leakage observed

6. **State Consistency**:
   - Route state is identical across all CLI access methods:
     - Standard CLI (`show ipv6 route`)
     - Privileged vtysh (`sudo vtysh -c "show ipv6 route"`)
     - Running configuration (`show running-config`)
   - Interface shutdown/no-shutdown properly affects route reachability
   - Route re-appears after interface recovery

7. **Interface-Level Control**:
   - Interface `shutdown` causes route to become inactive/unreachable
   - Interface `no shutdown` restores route functionality
   - Traffic forwarding resumes immediately after interface recovery

**Cleanup**:

1. Remove IPv6 static route from D1:
   ```
   configure terminal
   no ipv6 route 2001:db8:100::/64 2001:db8:1::2
   exit
   ```

2. Remove IPv6 addressing from interfaces on both DUTs:
   ```
   configure terminal
   interface Ethernet4
   no ipv6 address 2001:db8:1::1/64
   exit
   ```
   (Repeat for D2 with appropriate IP)

3. Remove Loopback0 on D2 (if created):
   ```
   configure terminal
   no interface Loopback0
   exit
   ```

4. Verify cleanup:
   - Execute: `show ipv6 route` (should show only connected/local routes)
   - Execute: `show running-config | section ipv6` (verify no test config remains)
   - Execute: `show interface status` (verify interfaces in expected baseline state)

5. Save configuration if required:
   ```
   write memory
   ```
   Or use `copy running-config startup-config` depending on platform

**Notes**:
- This test case validates both SONiC click (vtysh) and klish CLI modes
- Test assumes bidirectional connectivity on Ethernet4 between D1 and D2
- IPv6 routing must be enabled globally on both devices
- Some platforms may require `ipv6 enable` on interfaces before address configuration
- Management VRF behavior may vary by platform/version; adjust validation accordingly
