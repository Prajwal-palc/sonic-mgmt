# Static Route (Blackhole) Test Cases

## TC-IP-STATIC-BH-001 - Configure and validate IPv4 static blackhole routing
**Purpose**: Confirm that a globally and interface-scoped static blackhole route drops traffic as expected and that show commands reflect enable/disable operations.

**Preconditions**:
- Access to the DUT defined as `smic_sonic1` in `testbeds/testbed_2vs.yaml`; management reachability confirmed.
- Interface `Ethernet4` on `smic_sonic1` is available for configuration (per the testbed topology).
- Ability to run privileged CLI commands (`configure terminal`, `do show ...`, and `sudo vtysh`).

**Test Steps**:
1. Enter global configuration mode and create an IPv4 static blackhole route (example prefix `192.0.2.0/24`):
   - `ip route 192.0.2.0/24 Null0`
2. Validate the route immediately by collecting:
   - `show ip route`
   - `show ip route static`
   - `show running-config | section ip route`
3. Disable the blackhole route to confirm removal, then re-enable it:
   - `no ip route 192.0.2.0/24 Null0`
   - Re-run the three show commands to confirm the absence of the entry.
   - Reapply `ip route 192.0.2.0/24 Null0` and repeat the show commands to confirm restoration.
4. Move to interface configuration for `Ethernet4` and exercise interface-level control (shut/no shut or platform-specific blackhole toggles, as supported):
   - `interface Ethernet4`
   - Apply the interface blackhole/static discard command or administrative disable/enable sequence required by the platform (e.g., `shutdown` / `no shutdown` if that is how interface-scoped discard is implemented).
   - After each toggle, execute the same three show commands to verify state reflections.
5. Repeat all show validation in privileged mode:
   - `sudo vtysh -c "show ip route"`
   - `sudo vtysh -c "show running-config"`
6. Generate traffic toward the blackholed prefix from a connected host or from the DUT (`ping 192.0.2.1 source <interface>`).
7. Observe the routing table entries in real time to confirm the route type is displayed as `blackhole`/`Null0`.
8. Verify that ICMP echo requests receive no replies, demonstrating that traffic to the Null0 next hop is being dropped.

**Expected Results**:
- Static route appears in the routing table and is flagged as blackhole/Null0 in both regular and sudo `show` commands.
- Running configuration reflects the correct state after each enable/disable toggle.
- Traffic destined to the blackholed subnet receives no ICMP replies, confirming drop behavior.

**Cleanup**:
- Remove the static route from global configuration.
- Restore interface `Ethernet4` to its baseline configuration if any changes were made.
