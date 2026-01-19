# Test Cases

## TC-IP-STATIC-001 - Verify static route reachability via DUT2
**Purpose**: Ensure DUT1 reaches the 30.1.1.0/24 network via a static route that points to DUT2 as the next hop.

**Preconditions**:
- DUT1 and DUT2 are online, reachable over their management interfaces, and able to configure Ethernet ports.
- Ethernet32 connects DUT1 and DUT2 physically and is administratively up.
- Ethernet36 on DUT2 is connected to the 30.1.1.0/24 network (direct link or loopback).

**Test Steps**:
1. On DUT1, configure Ethernet32 with IP address `20.1.1.3/24`.
2. On DUT2, configure Ethernet32 with IP address `20.1.1.4/24`.
3. On DUT2, configure Ethernet36 with IP address `30.1.1.3/24`.
4. On DUT1, add a static route to `30.1.1.0/24` with next hop `20.1.1.4`.
5. From DUT1, ping `30.1.1.3` and observe the results.

**Expected Result**:
- Ping from DUT1 to `30.1.1.3` succeeds, demonstrating traffic reaches the remote network through the static route via DUT2.

**Cleanup** (optional):
- Remove the static route and interface IP configurations if needed to restore the baseline state.

## TC-IP-STATIC-002 - Validate failure without the static route
**Purpose**: Demonstrate that DUT1 loses reachability to 30.1.1.0/24 when the static route toward DUT2 is absent.

**Preconditions**:
- Interface IPs from steps 1-3 in `TC-IP-STATIC-001` are configured and link status is up.

**Test Steps**:
1. Ensure no static route to `30.1.1.0/24` exists on DUT1 (remove if present).
2. From DUT1, ping `30.1.1.3`.

**Expected Result**:
- Ping to `30.1.1.3` fails because DUT1 lacks a route to the 30.1.1.0/24 network.

**Cleanup** (optional):
- None required; proceed directly to `TC-IP-STATIC-003` to restore connectivity.

## TC-IP-STATIC-003 - Validate recovery after restoring the static route
**Purpose**: Confirm that adding the static route back on DUT1 restores connectivity to 30.1.1.0/24.

**Preconditions**:
- `TC-IP-STATIC-002` completed and ping failure confirmed.

**Test Steps**:
1. On DUT1, add a static route to `30.1.1.0/24` with next hop `20.1.1.4`.
2. From DUT1, ping `30.1.1.3`.

**Expected Result**:
- Ping to `30.1.1.3` succeeds once the static route is present again.

**Cleanup** (optional):
- Remove the static route if subsequent tests require a no-route state.

## TC-IP-STATIC-004 - Validate behavior with incorrect next hop
**Purpose**: Verify that an incorrect next-hop configuration prevents reachability and that correcting it restores traffic.

**Preconditions**:
- Interface IPs from steps 1-3 in `TC-IP-STATIC-001` are configured and operational.

**Test Steps**:
1. On DUT1, configure the static route to `30.1.1.0/24` using an invalid next hop (for example, `20.1.1.5`).
2. From DUT1, ping `30.1.1.3` and observe the result.
3. Replace the static route with the correct next hop `20.1.1.4`.
4. Repeat the ping from DUT1 to `30.1.1.3`.

**Expected Result**:
- Ping fails while the next hop is invalid and succeeds after correcting the next hop address.

**Cleanup** (optional):
- Leave the correct static route in place if more testing will be performed, or remove it to revert to a clean baseline.

## TC-IP-STATIC-005 - Validate link-down impact on the static route
**Purpose**: Ensure the static route becomes unusable when the physical link toward the next hop (Ethernet32) is administratively down.

**Preconditions**:
- Configuration and successful ping outcomes from `TC-IP-STATIC-001` are in place.

**Test Steps**:
1. On DUT1, shut down Ethernet32 to simulate a link failure toward DUT2.
2. From DUT1, ping `30.1.1.3`.
3. Re-enable Ethernet32 on DUT1.
4. Repeat the ping from DUT1 to `30.1.1.3`.

**Expected Result**:
- Ping fails while Ethernet32 is down and succeeds once the interface is re-enabled, proving dependency on the physical path.

**Cleanup** (optional):
- Ensure Ethernet32 remains enabled and the static route is present for subsequent tests.

## TC-IP-STATIC-006 - Validate static route persistence after reboot
**Purpose**: Confirm the static route toward 30.1.1.0/24 survives a routing-service restart or device reboot on DUT1.

**Preconditions**:
- Configuration and successful ping outcomes from `TC-IP-STATIC-001` are in place.
- Ability to safely restart the routing process or reboot DUT1 during the maintenance window.

**Test Steps**:
1. Save the running configuration on DUT1, if required by the platform.
2. Restart the routing service or reboot DUT1 according to operational procedures.
3. After DUT1 returns to service, verify the static route to `30.1.1.0/24` is present in the routing table.
4. From DUT1, ping `30.1.1.3`.

**Expected Result**:
- Static route remains configured after the restart and ping to `30.1.1.3` succeeds without additional intervention.

**Cleanup** (optional):
- None, unless the reboot was only for test purposes and should be rolled back to a previous state.

## TC-IP-STATIC-007 - Validate forwarding-plane programming of the static route
**Purpose**: Ensure the static route is installed in both the control-plane routing table and the forwarding-plane (hardware FIB) on DUT1.

**Preconditions**:
- Configuration and successful ping outcomes from `TC-IP-STATIC-001` are in place.
- Access to commands that display forwarding-plane programming (for example, `show ip fib` or equivalent).

**Test Steps**:
1. On DUT1, display the control-plane routing table and confirm the entry for `30.1.1.0/24` with next hop `20.1.1.4`.
2. Display the forwarding-plane or hardware table and confirm the same route is programmed with the correct next-hop interface.
3. From DUT1, ping `30.1.1.3` while monitoring forwarding counters, if available.

**Expected Result**:
- Route appears in both control-plane and forwarding-plane views and ping to `30.1.1.3` succeeds, indicating the route is actively used for forwarding.

**Cleanup** (optional):
- None required; retain the configuration for continued testing or operations.

## TC-IP-STATIC-008 - Validate neighbor resolution for the static route next hop
**Purpose**: Confirm DUT1 learns the Layer 2 neighbor entry for `20.1.1.4` when forwarding traffic via the static route.

**Preconditions**:
- Configuration and successful ping outcomes from `TC-IP-STATIC-001` are in place.
- Access to commands that display and clear ARP/neighbor cache entries.

**Test Steps**:
1. On DUT1, clear the neighbor/ARP entry associated with `20.1.1.4`.
2. From DUT1, ping `30.1.1.3`.
3. Inspect the neighbor/ARP table on DUT1 for the entry corresponding to `20.1.1.4`.

**Expected Result**:
- Ping to `30.1.1.3` succeeds and a fresh neighbor entry for `20.1.1.4` is populated on DUT1.

**Cleanup** (optional):
- None required; neighbor cache can remain populated for subsequent tests.

## TC-IP-STATIC-009 - Validate live traffic impact when removing the static route
**Purpose**: Demonstrate that active traffic fails immediately when the static route is deleted and resumes once it is restored.

**Preconditions**:
- Configuration and successful ping outcomes from `TC-IP-STATIC-001` are in place.

**Test Steps**:
1. Start a continuous ping from DUT1 to `30.1.1.3`.
2. While the ping runs, delete the static route to `30.1.1.0/24` on DUT1.
3. Observe the ping behavior for failures.
4. Re-add the static route with next hop `20.1.1.4`.
5. Continue monitoring the ping for recovery.

**Expected Result**:
- Ping transitions to failure immediately after the route removal and recovers after the static route is re-added.

**Cleanup** (optional):
- Stop the continuous ping once normal operation is confirmed.

## TC-IP-STATIC-010 - Validate no regression on the directly connected subnet
**Purpose**: Ensure adding the static route does not affect communication within the directly connected `20.1.1.0/24` subnet.

**Preconditions**:
- Interface IPs from steps 1-3 in `TC-IP-STATIC-001` are configured and link status is up.

**Test Steps**:
1. Before adding the static route, from DUT1 ping `20.1.1.4` to confirm baseline connectivity on the local subnet.
2. On DUT1, add the static route to `30.1.1.0/24` with next hop `20.1.1.4`.
3. Repeat the ping from DUT1 to `20.1.1.4`.

**Expected Result**:
- Ping to `20.1.1.4` succeeds both before and after the static route is added, confirming no side effects on local subnet reachability.

**Cleanup** (optional):
- Remove the static route if a clean baseline is required for other scenarios.

## TC-IP-STATIC-011 - Validate alternate static route utilization
**Purpose**: Ensure DUT1 can forward traffic to 30.1.1.0/24 through an alternate next hop when the primary static route is replaced.

**Preconditions**:
- Interface IPs from steps 1-3 in `TC-IP-STATIC-001` are configured.
- A secondary next hop (for example, `20.1.1.6`) is reachable from DUT1 and leads to DUT2 or an equivalent transit device that can reach `30.1.1.0/24`.

**Test Steps**:
1. Remove the static route to `30.1.1.0/24` via `20.1.1.4` on DUT1.
2. Configure a static route to `30.1.1.0/24` with next hop `20.1.1.6`.
3. From DUT1, ping `30.1.1.3`.
4. Optionally, restore the original static route via `20.1.1.4` after validation.

**Expected Result**:
- Ping to `30.1.1.3` succeeds via the alternate next hop, demonstrating DUT1 honors the updated static route.

**Cleanup** (optional):
- Reinstate the primary static route if the network design depends on it.

## TC-IP-STATIC-012 - Validate failure when DUT2 loses the destination network
**Purpose**: Verify that DUT1 loses reachability to 30.1.1.0/24 when DUT2 no longer provides access to that network, even though the static route remains configured.

**Preconditions**:
- Configuration and successful ping outcomes from `TC-IP-STATIC-001` are in place.
- Ability to administratively disable Ethernet36 or remove the `30.1.1.3/24` address on DUT2.

**Test Steps**:
1. On DUT2, remove or shut down the interface providing access to `30.1.1.0/24` (for example, disable Ethernet36 or remove the IP address).
2. From DUT1, ping `30.1.1.3`.
3. Restore the interface or IP configuration on DUT2.
4. Repeat the ping from DUT1 to `30.1.1.3`.

**Expected Result**:
- Ping fails while DUT2 lacks connectivity to the destination network and succeeds again once the network is restored, highlighting the dependency on DUT2's configuration.

**Cleanup** (optional):
- Ensure Ethernet36 and all required IP addresses are re-enabled to return the environment to its baseline state.

## TC-IP-STATIC-013 - Validate forwarding counters for static route traffic
**Purpose**: Confirm that traffic forwarded via the static route increments interface or route-specific forwarding counters on DUT1.

**Preconditions**:
- Configuration and successful ping outcomes from `TC-IP-STATIC-001` are in place.
- Access to interface and/or route forwarding statistics (for example, `show interface counters`, `show ip route stats`).

**Test Steps**:
1. On DUT1, clear the relevant interface or route counters associated with Ethernet32 and the `30.1.1.0/24` static route.
2. From DUT1, send a fixed number of pings (for example, `ping 30.1.1.3 count 10`).
3. Re-check the counters on DUT1.

**Expected Result**:
- Counters associated with Ethernet32 and/or the static route increase in alignment with the generated traffic, demonstrating that packets are forwarded using the static route.

**Cleanup** (optional):
- None required; counters can remain incremented for ongoing monitoring.

## TC-IP-STATIC-014 - Validate static route failover with backup next hop
**Purpose**: Ensure DUT1 maintains reachability to 30.1.1.0/24 when a backup static route with higher administrative distance is configured and the primary path fails.

**Preconditions**:
- A secondary path to DUT2 or an alternate transit device is available (for example, next hop `20.1.1.6` reachable via a different interface).
- Ability to administratively shut down the primary link on DUT1.

**Test Steps**:
1. On DUT1, configure two static routes to `30.1.1.0/24`: primary via next hop `20.1.1.4` with lower administrative distance, and backup via next hop `20.1.1.6` with higher administrative distance.
2. From DUT1, ping `30.1.1.3` to verify the primary route is in use.
3. Shut down Ethernet32 on DUT1 to simulate primary link failure.
4. Continue pinging `30.1.1.3` and verify traffic shifts to the backup next hop (for example, by checking routing table or traceroute output).
5. Re-enable Ethernet32 and ensure the primary static route is reinstated for subsequent traffic.

**Expected Result**:
- Connectivity to `30.1.1.3` persists during the primary link failure, showing failover to the backup static route, and reverts to the primary path once the link is restored.

**Cleanup** (optional):
- Remove the backup static route if it is only required for this test, and confirm Ethernet32 is left enabled.

## TC-IP-STATIC-015 - Validate configuration rollback restores baseline state
**Purpose**: Ensure that using the platform's configuration rollback mechanism removes the static route and returns DUT1 to the baseline no-route condition.

**Preconditions**:
- Configuration and successful ping outcomes from `TC-IP-STATIC-001` are in place.
- The platform supports transactional commits with rollback (for example, `config save` / `config rollback`).

**Test Steps**:
1. Save the current configuration snapshot on DUT1.
2. Remove the static route to `30.1.1.0/24` via `20.1.1.4`.
3. Initiate a rollback to the previously saved configuration.
4. Verify the static route is present again in the routing table.
5. From DUT1, ping `30.1.1.3` to confirm connectivity.

**Expected Result**:
- Rollback restores the static route and ping to `30.1.1.3` succeeds, demonstrating configuration recovery.

**Cleanup** (optional):
- None; the rollback leaves the device at the saved baseline.

## TC-IP-STATIC-016 - Validate static route preference over a dynamic route
**Purpose**: Confirm that a static route takes precedence over a dynamically learned route to the same prefix, and that removing the static route causes traffic to use the dynamic path.

**Preconditions**:
- Dynamic routing protocol (for example, OSPF or BGP) established between DUT1 and DUT2, advertising `30.1.1.0/24` toward DUT1.
- Interface IPs from steps 1-3 in `TC-IP-STATIC-001` are configured.

**Test Steps**:
1. Ensure DUT1 learns `30.1.1.0/24` dynamically from DUT2 and verify ping to `30.1.1.3` succeeds.
2. Configure a static route to `30.1.1.0/24` via `20.1.1.4` on DUT1.
3. Verify the routing table prefers the static route and ping `30.1.1.3` to confirm traffic still succeeds.
4. Remove the static route on DUT1.
5. Confirm the routing table falls back to the dynamic route and ping `30.1.1.3` again.

**Expected Result**:
- Static route overrides the dynamic advertisement when present, and removing it causes traffic to revert seamlessly to the dynamic route without loss of connectivity.

**Cleanup** (optional):
- Leave the dynamic routing configuration intact, and add back the static route only if required for operational purposes.

## TC-IP-STATIC-017 - Validate logging for static route lifecycle events
**Purpose**: Ensure that adding or removing the static route generates the expected syslog or monitoring events for operational visibility.

**Preconditions**:
- Centralized logging or on-box syslog is enabled and accessible.
- Configuration from `TC-IP-STATIC-001` is in place.

**Test Steps**:
1. Clear or bookmark the logging buffer on DUT1.
2. Remove the static route to `30.1.1.0/24` via `20.1.1.4`.
3. Add the static route back on DUT1.
4. Review the log buffer or external syslog server for entries indicating the route removal and addition.

**Expected Result**:
- Log messages accurately reflect both removal and re-addition of the static route with correct timestamps and identifiers.

**Cleanup** (optional):
- Leave the static route configured for subsequent tests.

## TC-IP-STATIC-018 - Validate telemetry/SNMP reporting of the static route
**Purpose**: Verify that the static route appears in exported telemetry or SNMP data for network monitoring tools.

**Preconditions**:
- Telemetry streaming or SNMP polling is configured for DUT1.
- Configuration from `TC-IP-STATIC-001` is in place and connectivity is working.

**Test Steps**:
1. From the monitoring system, initiate a telemetry or SNMP poll focusing on the routing table.
2. Confirm the `30.1.1.0/24` static route with next hop `20.1.1.4` is reported.
3. Remove the static route on DUT1.
4. Repeat the telemetry/SNMP check to verify the route entry is removed from the exported data.
5. Re-add the static route and confirm it reappears in the monitoring output.

**Expected Result**:
- Telemetry/SNMP reflects the presence or absence of the static route in near real-time, ensuring monitoring systems stay in sync with configuration changes.

**Cleanup** (optional):
- Restore the static route configuration to maintain baseline connectivity.

## TC-IP-STATIC-019 - Validate automation workflow idempotency
**Purpose**: Confirm that the automation playbook or script used to configure the static route is idempotent and leaves the system unchanged when re-run.

**Preconditions**:
- An automation workflow (for example, Ansible playbook or Python script) exists to configure the static route and interface IPs.
- Test environment from `TC-IP-STATIC-001` is available.

**Test Steps**:
1. Execute the automation workflow to configure the interfaces and static route.
2. Verify the configuration and connectivity (ping `30.1.1.3`).
3. Re-run the automation workflow without making manual changes.
4. Confirm no configuration drift or duplicate entries are introduced.
5. Optionally, remove the static route manually and run the workflow again to ensure it reinstates the configuration.

**Expected Result**:
- Re-running the automation workflow detects the existing configuration, makes no unnecessary changes, and restores the static route if it is missing.

**Cleanup** (optional):
- Leave the environment configured or remove the static route if the lab requires a clean state.

## TC-IP-STATIC-020 - Validate ACL impact on static route traffic
**Purpose**: Ensure that ACLs applied on Ethernet32 or in the routing path do not block traffic destined for `30.1.1.3`, and confirm the ACL can intentionally block it when required.

**Preconditions**:
- Configuration from `TC-IP-STATIC-001` is in place.
- Ability to apply and remove ACLs on the relevant interfaces.

**Test Steps**:
1. Confirm baseline connectivity from DUT1 to `30.1.1.3` with no ACL applied.
2. Apply an ACL on Ethernet32 (or the relevant interface) that permits ICMP traffic to `30.1.1.3`.
3. Ping `30.1.1.3` from DUT1 to confirm connectivity remains.
4. Modify the ACL to deny ICMP traffic to `30.1.1.3`.
5. Repeat the ping to `30.1.1.3` and observe the failure.
6. Remove or revert the ACL to restore normal traffic.

**Expected Result**:
- Ping succeeds when ACL permits the traffic and fails when denied, demonstrating ACL control over static-route forwarding while confirming no unintended blockage in the permit state.

**Cleanup** (optional):
- Remove restrictive ACL entries to return the network to its baseline configuration.

## TC-IP-STATIC-021 - Validate forwarding path using packet capture
**Purpose**: Confirm that ICMP traffic from DUT1 to `30.1.1.3` traverses Ethernet32 toward DUT2 by observing packets on the wire.

**Preconditions**:
- Configuration from `TC-IP-STATIC-001` is in place.
- Packet capture capability is available on the Ethernet32 link (for example, SPAN/mirror port or inline tap).

**Test Steps**:
1. Start a packet capture on the Ethernet32 segment between DUT1 and DUT2, filtering for ICMP packets.
2. From DUT1, ping `30.1.1.3`.
3. Stop the capture and analyze the trace for ICMP echo requests sourced from `20.1.1.3` and replies sourced from `30.1.1.3`.

**Expected Result**:
- Capture shows the ICMP exchanges on Ethernet32, verifying the static route forwards traffic along the expected path.

**Cleanup** (optional):
- Disable the SPAN/mirror session or remove the tap to restore normal monitoring state.

## TC-IP-STATIC-022 - Validate high-rate traffic forwarding stability
**Purpose**: Ensure the static route sustains high-rate traffic without drops or excessive CPU utilization on DUT1.

**Preconditions**:
- Traffic generator or tool (for example, iPerf or IXIA) capable of sourcing traffic from DUT1 toward `30.1.1.3`.
- Monitoring tools to observe interface utilization and CPU load on DUT1.

**Test Steps**:
1. Establish baseline CPU and interface statistics on DUT1.
2. Generate sustained high-rate traffic from DUT1 toward `30.1.1.3` using the static route path.
3. Monitor packet loss, interface counters, and CPU utilization during the test.
4. After the traffic run, verify the static route remains in the forwarding table.

**Expected Result**:
- Traffic flows without significant drops, CPU remains within acceptable limits, and the static route stays active throughout the stress test.

**Cleanup** (optional):
- Stop traffic generation and reset interface counters if required.

## TC-IP-STATIC-023 - Validate policy-based routing interaction
**Purpose**: Confirm that policy-based routing (PBR) rules do not unintentionally override the static route unless explicitly configured to do so.

**Preconditions**:
- Configuration from `TC-IP-STATIC-001` is in place.
- Capability to configure PBR/route-map on DUT1.

**Test Steps**:
1. Verify baseline connectivity from DUT1 to `30.1.1.3` using the static route.
2. Apply a PBR policy that matches unrelated traffic and sends it to a different next hop, ensuring the policy does not match the `30.1.1.3` destination.
3. Ping `30.1.1.3` to confirm traffic still follows the static route.
4. Modify the PBR policy to match traffic destined for `30.1.1.3` and redirect it to an alternate next hop.
5. Attempt to reach `30.1.1.3` again and observe the result.
6. Remove or revert the PBR configuration.

**Expected Result**:
- Ping succeeds while PBR does not match the static-route traffic and fails or follows the new path when PBR explicitly redirects it, demonstrating predictable interaction between PBR and static routing.

**Cleanup** (optional):
- Remove PBR rules to return DUT1 to the baseline static-routing behavior.
