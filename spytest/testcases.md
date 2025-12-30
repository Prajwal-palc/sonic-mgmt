# Test Cases

## TC_STATIC_ROUTE_001 – Verify static route via DUT2

**Purpose**
- Validate reachability to DUT2's secondary network via a static route configured on DUT1.

**Preconditions**
- DUT1 and DUT2 have management reachability.
- Interfaces `Ethernet32` and `Ethernet36` are available and administratively up on the respective devices.

**Test Steps**
1. On DUT1, configure `Ethernet32` with IP `20.1.1.3/24`.
2. On DUT2, configure `Ethernet32` with IP `20.1.1.4/24`.
3. On DUT2, configure `Ethernet36` with IP `30.1.1.3/24`.
4. On DUT1, add a static route to `30.1.1.0/24` via next hop `20.1.1.4` on `Ethernet32`.
5. From DUT1, ping `30.1.1.3` and capture the results.

**Expected Result**
- Ping from DUT1 to `30.1.1.3` succeeds, confirming traffic is forwarded through the static route to DUT2.

**Cleanup**
- Remove the static route on DUT1.
- Restore previous interface configurations on both DUTs if required.
