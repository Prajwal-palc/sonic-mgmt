# Static Route VRF Test Cases

## TC-IP-STATIC-VRF-001 - Configure and verify IPv4 Static Route in VRF

**Purpose**: Validate IPv4 static route configuration within a non-default VRF, ensuring proper route installation, traffic forwarding, and VRF isolation (no cross-VRF leakage).

**Preconditions**:
- Access to two DUTs defined as `smic_sonic1` (D1) and `smic_sonic2` (D2) in `testbeds/testbed_2vs.yaml`
- Management reachability confirmed for both devices
- Interface `Ethernet4` on both DUTs available for configuration
- VRF feature support on both devices
- Ability to run privileged CLI commands (klish CLI and `sudo vtysh`)

**Test Steps**:

1. **Create Non-Default VRF**:
   - Enter configuration mode on D1
   - Create VRF instance (example: `Vrf-RED`)
   - Command: `ip vrf Vrf-RED`
   - Verify VRF creation with: `show ip vrf`

2. **Configure Loopback Interface in VRF**:
   - Create Loopback interface on D1 (example: `Loopback10`)
   - Assign IP address to Loopback (example: `192.0.2.1/32`)
   - Bind Loopback to VRF: `ip vrf forwarding Vrf-RED`
   - Commands:
     ```
     interface Loopback10
     ip address 192.0.2.1/32
     ip vrf forwarding Vrf-RED
     ```

3. **Configure Interface IP Addressing**:
   - Configure Ethernet4 on D1 with IP address (example: `10.0.24.1/31`)
   - Bind Ethernet4 to VRF-RED
   - Configure Ethernet4 on D2 with IP address (example: `10.0.24.0/31`)
   - Verify interface is up and IP addressing is correct

4. **Configure Static Route in VRF**:
   - On D1, configure static route in VRF-RED
   - Destination network: `198.51.100.0/24`
   - Next-hop: `10.0.24.0` (D2's interface IP)
   - Command: `ip route vrf Vrf-RED 198.51.100.0/24 10.0.24.0`

5. **Verify Route in VRF Routing Table** (klish CLI):
   - Execute: `show ip route vrf Vrf-RED`
   - Confirm route `198.51.100.0/24` is visible
   - Verify next-hop is `10.0.24.0`
   - Verify route type is `S` (static)
   - Verify route is NOT visible in global routing table: `show ip route` (should not show this VRF route)

6. **Verify Route in VRF** (vtysh CLI):
   - Execute: `sudo vtysh -c "show ip route vrf Vrf-RED"`
   - Confirm route `198.51.100.0/24` is present
   - Verify next-hop matches configuration

7. **Verify VRF Configuration**:
   - Execute: `show ip vrf Vrf-RED`
   - Confirm VRF exists and shows bound interfaces
   - Execute: `sudo vtysh -c "show vrf Vrf-RED"`
   - Verify consistency between klish and vtysh outputs

8. **Verify Running Configuration**:
   - Execute: `show running-config | section ip route`
   - Confirm VRF static route is present in configuration
   - Verify format: `ip route vrf Vrf-RED 198.51.100.0/24 10.0.24.0`

9. **Test VRF Isolation (No Cross-VRF Leakage)**:
   - Verify route is NOT present in global routing table
   - Execute: `show ip route 198.51.100.0/24` (without VRF parameter)
   - Expected: Route should not be found or should indicate it's in a VRF
   - This confirms traffic stays within VRF routing context

10. **Traffic Forwarding Verification** (if test network available):
    - From D1, ping destination in VRF: `ping 198.51.100.1 vrf Vrf-RED`
    - Expected: Traffic should be forwarded via the static route
    - Note: This step may be limited by test topology

11. **Route Removal and Cleanup Verification**:
    - Remove static route: `no ip route vrf Vrf-RED 198.51.100.0/24 10.0.24.0`
    - Verify route is removed: `show ip route vrf Vrf-RED`
    - Confirm route no longer appears in routing table

**Expected Results**:
1. VRF `Vrf-RED` is successfully created and visible in `show ip vrf`
2. Loopback interface is successfully bound to VRF
3. Interface Ethernet4 on D1 is successfully bound to VRF-RED
4. Static route `198.51.100.0/24` via `10.0.24.0` is successfully installed in VRF-RED routing table
5. Route is visible in `show ip route vrf Vrf-RED` (both klish and vtysh)
6. Route is correctly associated with VRF-RED, not the global routing table
7. No cross-VRF leakage: route does NOT appear in global routing table (`show ip route` without VRF parameter)
8. Running configuration correctly reflects VRF and static route configuration
9. Route can be successfully removed and verified absent
10. Traffic forwarding uses the VRF-specific route (if applicable to topology)

**Cleanup**:
- Remove static route from VRF: `no ip route vrf Vrf-RED 198.51.100.0/24 10.0.24.0`
- Unbind interface from VRF: `no ip vrf forwarding Vrf-RED` (on Ethernet4 and Loopback10)
- Remove Loopback interface IP: `no ip address 192.0.2.1/32`
- Delete VRF: `no ip vrf Vrf-RED`
- Restore interfaces to baseline configuration

**Notes**:
- This test validates VRF-aware static routing
- Ensures proper VRF isolation and prevents routing leaks
- Compatible with SONiC klish CLI and FRR vtysh
- Test uses 2-node topology with minimum Ethernet4 connectivity
