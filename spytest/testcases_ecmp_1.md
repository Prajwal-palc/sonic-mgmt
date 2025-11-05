# ECMP Functionality — 2 Equal-Cost Static Routes Test Plan

## Topology
- **DUT**: vs_sonic_1 (192.168.100.248)
  - Ethernet32 ↔ vs_sonic_2:Ethernet32
  - Ethernet12 ↔ vs_sonic_3:Ethernet28
- **NH1**: vs_sonic_2 (192.168.100.172)
- **NH2**: vs_sonic_3 (192.168.100.151)

## IP Addressing
- DUT–NH1: 10.0.0.0/31 (DUT: 10.0.0.0, NH1: 10.0.0.1)
- DUT–NH2: 10.0.0.2/31 (DUT: 10.0.0.2, NH2: 10.0.0.3)
- Test destination: 203.0.113.0/24 (sunk on NH1 & NH2 via Null0)

---

| Testcase ID | Purpose | Preconditions | Execution Steps | Expected Result |
| --- | --- | --- | --- | --- |
| ECMP_01_001 | Configure DUT uplink interfaces | DUT CLI access; mgmt reachability to vs_sonic_1 | 1. Execute `sudo config interface startup Ethernet32`.<br>2. Execute `sudo config interface startup Ethernet12`.<br>3. Verify with `show interfaces status`. | Both Ethernet32 and Ethernet12 are admin up and operationally up. |
| ECMP_01_002 | Configure L3 addressing on DUT uplinks towards NH1 and NH2 | ECMP_01_001 passed; IP addresses 10.0.0.0/31 and 10.0.0.2/31 are unused | 1. Execute `sudo config interface ip add Ethernet32 10.0.0.0/31`.<br>2. Execute `sudo config interface ip add Ethernet12 10.0.0.2/31`.<br>3. Verify with `show ip interfaces`. | Ethernet32 configured with 10.0.0.0/31 and Ethernet12 configured with 10.0.0.2/31; interfaces remain operational. |
| ECMP_01_003 | Provision two equal-cost static routes to 203.0.113.0/24 | ECMP_01_002 passed | 1. Execute `sudo config route add 203.0.113.0/24 10.0.0.1`.<br>2. Execute `sudo config route add 203.0.113.0/24 10.0.0.3`.<br>3. Optionally execute `sudo config save -y` to persist. | Both static routes accepted without errors. |
| ECMP_01_004 | Verify ECMP route installation in FRR and kernel routing tables | ECMP_01_003 passed | 1. Execute `vtysh -c "show ip route 203.0.113.0/24"`.<br>2. Execute `ip route show 203.0.113.0/24`.<br>3. Execute `show arp` to check neighbor resolution. | FRR displays route with two next-hops (10.0.0.1 and 10.0.0.3); kernel route table shows nexthop via both interfaces with equal cost; ARP entries for both NH1 and NH2 are resolved. |
| ECMP_01_005 | Configure NH1 uplink interface | CLI access to vs_sonic_2; mgmt reachability | 1. Execute `sudo config interface startup Ethernet32`.<br>2. Verify with `show interfaces status`. | Ethernet32 on NH1 is admin up and operationally up. |
| ECMP_01_006 | Configure L3 addressing on NH1 towards DUT | ECMP_01_005 passed; IP 10.0.0.1/31 is unused | 1. Execute `sudo config interface ip add Ethernet32 10.0.0.1/31`.<br>2. Verify with `show ip interfaces`.<br>3. Check connectivity with `ping 10.0.0.0 -c 3`. | Ethernet32 configured with 10.0.0.1/31; ping to DUT (10.0.0.0) succeeds. |
| ECMP_01_007 | Configure Null0 route on NH1 for test destination | ECMP_01_006 passed; FRR access available | 1. Execute `sudo vtysh -c "conf t" -c "ip route 203.0.113.0/24 Null0"`.<br>2. Optionally execute `sudo config save -y`.<br>3. Verify with `vtysh -c "show ip route 203.0.113.0/24"`. | Static route to 203.0.113.0/24 via Null0 is installed in FRR; traffic to this prefix will be silently discarded on NH1. |
| ECMP_01_008 | Configure NH2 uplink interface | CLI access to vs_sonic_3; mgmt reachability | 1. Execute `sudo config interface startup Ethernet28`.<br>2. Verify with `show interfaces status`. | Ethernet28 on NH2 is admin up and operationally up. |
| ECMP_01_009 | Configure L3 addressing on NH2 towards DUT | ECMP_01_008 passed; IP 10.0.0.3/31 is unused | 1. Execute `sudo config interface ip add Ethernet28 10.0.0.3/31`.<br>2. Verify with `show ip interfaces`.<br>3. Check connectivity with `ping 10.0.0.2 -c 3`. | Ethernet28 configured with 10.0.0.3/31; ping to DUT (10.0.0.2) succeeds. |
| ECMP_01_010 | Configure Null0 route on NH2 for test destination | ECMP_01_009 passed; FRR access available | 1. Execute `sudo vtysh -c "conf t" -c "ip route 203.0.113.0/24 Null0"`.<br>2. Optionally execute `sudo config save -y`.<br>3. Verify with `vtysh -c "show ip route 203.0.113.0/24"`. | Static route to 203.0.113.0/24 via Null0 is installed in FRR; traffic to this prefix will be silently discarded on NH2. |
| ECMP_01_011 | Enable port counter polling on DUT | All previous configuration steps passed | 1. Execute `sudo counterpoll port enable` on DUT.<br>2. Verify polling is enabled with `counterpoll show`. | Port counter polling is enabled; status shows "Enabled" for port counters. |
| ECMP_01_012 | Generate diverse traffic flows to test destination | Traffic host connected to DUT ingress; Scapy or traffic generator available; ECMP_01_011 passed | 1. Clear interface counters: `show interfaces counters -c`.<br>2. Execute Scapy script to generate many 5-tuple-diverse flows to 203.0.113.0/24 (vary src IP, src port, dst IP within /24).<br>3. Send traffic for sufficient duration (e.g., 30-60 seconds, ~10K+ packets). | Traffic generator successfully sends diverse flows to 203.0.113.0/24 range; no errors from generator. |
| ECMP_01_013 | Verify ECMP load distribution across both next-hops | ECMP_01_012 in progress or completed | 1. During/after traffic, execute `show interfaces counters` on DUT.<br>2. Record TX packet/byte counts for Ethernet32 and Ethernet12.<br>3. Calculate distribution ratio. | Egress counters on both Ethernet32 (to NH1) and Ethernet12 (to NH2) increase; distribution is roughly balanced (40%-60% split acceptable, ideally closer to 50%-50%). |
| ECMP_01_014 | Verify ingress traffic on NH1 and NH2 | ECMP_01_013 passed; access to NH1 and NH2 | 1. On vs_sonic_2, execute `show interfaces counters` and check RX on Ethernet32.<br>2. On vs_sonic_3, execute `show interfaces counters` and check RX on Ethernet28. | RX counters on NH1:Ethernet32 and NH2:Ethernet28 show incremental traffic matching DUT's egress; confirms packets reached both next-hops. |
| ECMP_01_015 | Simulate next-hop failure by shutting down NH1 link | ECMP_01_013 passed; ability to modify NH1 config | 1. On vs_sonic_2 (NH1), execute `sudo config interface shutdown Ethernet32`.<br>2. Wait 2-3 seconds for convergence.<br>3. On DUT, execute `vtysh -c "show ip route 203.0.113.0/24"`. | Ethernet32 on NH1 goes down; DUT routing table updates to show only 10.0.0.3 (NH2) as active next-hop for 203.0.113.0/24. |
| ECMP_01_016 | Verify fast convergence and traffic continuity after NH1 failure | ECMP_01_015 completed; traffic still running or restart | 1. Clear counters: `show interfaces counters -c` on DUT.<br>2. Resume/continue traffic to 203.0.113.0/24.<br>3. Monitor counters: `show interfaces counters` on DUT.<br>4. Check Ethernet32 (failed path) and Ethernet12 (active path) TX counters. | Traffic now exits only via Ethernet12 (to NH2); Ethernet32 TX counters show no new increments; minimal packet loss observed (convergence <1s); all traffic successfully rerouted. |
| ECMP_01_017 | Restore NH1 link and verify ECMP reconvergence | ECMP_01_016 passed | 1. On vs_sonic_2, execute `sudo config interface startup Ethernet32`.<br>2. Wait 2-3 seconds for neighbor re-establishment.<br>3. On DUT, execute `vtysh -c "show ip route 203.0.113.0/24"`.<br>4. Optionally restart traffic and check counters. | Ethernet32 on NH1 comes back up; DUT routing table shows both next-hops (10.0.0.1 and 10.0.0.3) active again; if traffic running, load balancing resumes across both paths. |
| ECMP_01_018 | Clean up DUT configuration | All test scenarios completed | 1. Execute `sudo config route del 203.0.113.0/24 10.0.0.1`.<br>2. Execute `sudo config route del 203.0.113.0/24 10.0.0.3`.<br>3. Execute `sudo config interface ip remove Ethernet32 10.0.0.0/31`.<br>4. Execute `sudo config interface ip remove Ethernet12 10.0.0.2/31`.<br>5. Optionally execute `sudo config save -y`. | All static routes to 203.0.113.0/24 removed; IP addresses removed from Ethernet32 and Ethernet12; verify with `show ip route` and `show ip interfaces`. |
| ECMP_01_019 | Clean up NH1 configuration | ECMP_01_018 completed | 1. Execute `sudo vtysh -c "conf t" -c "no ip route 203.0.113.0/24 Null0"` on vs_sonic_2.<br>2. Execute `sudo config interface ip remove Ethernet32 10.0.0.1/31`.<br>3. Optionally execute `sudo config save -y`.<br>4. Verify with `vtysh -c "show ip route 203.0.113.0/24"` and `show ip interfaces`. | Null0 route removed from NH1; IP address removed from Ethernet32; routing table and interface config clean. |
| ECMP_01_020 | Clean up NH2 configuration | ECMP_01_019 completed | 1. Execute `sudo vtysh -c "conf t" -c "no ip route 203.0.113.0/24 Null0"` on vs_sonic_3.<br>2. Execute `sudo config interface ip remove Ethernet28 10.0.0.3/31`.<br>3. Optionally execute `sudo config save -y`.<br>4. Verify with `vtysh -c "show ip route 203.0.113.0/24"` and `show ip interfaces`. | Null0 route removed from NH2; IP address removed from Ethernet28; routing table and interface config clean. |

---

## Pass/Fail Criteria

### PASS
- ECMP forms successfully with 2 next-hops (10.0.0.1 and 10.0.0.3)
- Egress traffic on Ethernet32 and Ethernet12 grows roughly evenly with diverse flows (±10-15% variance acceptable)
- After NH1 failure, traffic continues via NH2 with minimal loss (convergence time <1 second)
- ECMP reconverges when failed link is restored
- All cleanup steps execute without errors

### FAIL
- ECMP does not form (only single next-hop in routing table)
- Significant hashing bias observed (>70% traffic via one path with many flows)
- Prolonged loss or no traffic rerouting after NH1 failure (convergence >2 seconds)
- Persistent configuration or routing table entries after cleanup
- Interface or routing errors during any configuration step

---

## Notes
- If FRR version prefers `blackhole` keyword, use `ip route 203.0.113.0/24 blackhole` instead of `Null0`
- For reply-based traffic verification, replace Null0 with anycast /32 addresses on NH1/NH2 loopbacks
- Traffic generation requires minimum 100+ flows with varied 5-tuple to properly exercise ECMP hash
- Counter polling interval should be consistent (2-5 seconds) for accurate measurements
- Save configurations (`config save -y`) if testing across reboots or for persistent setups
