# Static Route Test Case

## TC-IP-STATIC-001 - Configure and verify IPv4 static route on DUT1 via DUT2
**Purpose**: Validate that DUT1 reaches the 30.1.1.0/24 network by installing a static route that points to DUT2 as the next hop.

**Preconditions**:
- DUT1 and DUT2 are reachable over management and have privilege to run configuration commands.
- Ethernet32 interconnects DUT1 and DUT2 and is administratively enabled on both devices.
- Ethernet36 on DUT2 connects to the 30.1.1.0/24 network (direct link, loopback, or simulated host).
- Configuration access (CLI/automation) is available to apply interface IPs and static routes.

**Test Steps**:
1. On DUT1, configure Ethernet32 with IP `20.1.1.3/24`.
2. On DUT2, configure Ethernet32 with IP `20.1.1.4/24`.
3. On DUT2, configure Ethernet36 with IP `30.1.1.3/24`.
4. On DUT1, add a static route to `30.1.1.0/24` with next hop `20.1.1.4`.
5. Verify on DUT1 that the static route is present:
   - `show ip route 30.1.1.0`
   - `show ip route static`
6. From DUT1, ping `30.1.1.3` and record the success rate and RTT statistics.
7. Optional: On DUT2, capture traffic (e.g., `tcpdump`) on Ethernet32 to confirm ICMP requests arrive via the static route.

**Expected Results**:
- Static route to `30.1.1.0/24` appears in the routing table on DUT1 with next hop `20.1.1.4`.
- ICMP ping from DUT1 to `30.1.1.3` succeeds, proving reachability across the configured path.
- Traffic monitoring on DUT2 (if performed) shows ICMP echo request/reply traversing Ethernet32.

**Cleanup**:
- Remove the static route from DUT1.
- Restore Ethernet32 and Ethernet36 IP configurations on both devices if they differ from the baseline.
