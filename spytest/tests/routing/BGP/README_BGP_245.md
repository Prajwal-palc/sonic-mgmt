# BGP Test ID 2.4.5: Session Recovery After Interface Flap

## Overview

This test suite validates BGP session resilience and recovery after interface flap events. It covers 6 comprehensive scenarios testing eBGP, iBGP, numbered/unnumbered interfaces, multihop configurations, and BFD-enabled sessions.

## Files

- **Test Script**: `test_bgp_session_recovery_after_interface_flap.py`
- **Variables File**: `vars_bgp_session_recovery_after_interface_flap.yaml`
- **Documentation**: `../../Doc/bgp_245.md`

## Test Cases

| Test ID | Description | Scenario | Recovery SLO |
|---------|-------------|----------|--------------|
| 2.4.5.1 | eBGP IPv4 numbered - flap on DUT1 | Direct eBGP peering, local side flap | ≤ 10 seconds |
| 2.4.5.2 | eBGP IPv4 numbered - flap on DUT2 | Direct eBGP peering, peer side flap | ≤ 10 seconds |
| 2.4.5.3 | iBGP IPv4 numbered - flap on DUT1 | iBGP peering, local side flap | ≤ 10 seconds |
| 2.4.5.4 | iBGP IPv4 unnumbered - flap on DUT1 | Unnumbered iBGP with extended-nexthop | ≤ 10 seconds |
| 2.4.5.5 | eBGP multihop - flap underlay | Loopback-based multihop, underlay flap | ≤ 10 seconds |
| 2.4.5.6 | eBGP with BFD - faster recovery | BFD-enabled for sub-second detection | < 5 seconds |

## Topology Requirements

### Minimal Topology
- **DUTs**: 2 (D1, D2)
- **Links**: 1 (Ethernet4 ↔ Ethernet4)
- **Testbed**: `testbed_vs_2node.yaml`

### Topology Diagram

```
┌─────────────────┐                           ┌─────────────────┐
│  smic_sonic1    │      Ethernet4 Link       │  smic_sonic2    │
│    (DUT1)       ├───────────────────────────┤    (DUT2)       │
│                 │                           │                 │
│ AS 65001/65002  │   10.0.0.1/30 ↔ 10.0.0.2/30│ AS 65001/65002  │
│ Lo0: 1.1.1.1/32 │                           │ Lo0: 2.2.2.2/32 │
└─────────────────┘                           └─────────────────┘
```

## How to Run

### Run All Tests

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_session_recovery_after_interface_flap.py \
  --logs-path ./logs/bgp_245_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### Run Specific Test Case

```bash
# Test 2.4.5.1 - eBGP numbered flap on DUT1
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_session_recovery_after_interface_flap.py::TestBgpSessionRecoveryAfterInterfaceFlap::test_ebgp_ipv4_numbered_flap_dut1 \
  --logs-path ./logs/bgp_245_1_$(date +%F_%H%M%S) \
  --log-level debug

# Test 2.4.5.6 - eBGP with BFD
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_session_recovery_after_interface_flap.py::TestBgpSessionRecoveryAfterInterfaceFlap::test_ebgp_bfd_faster_recovery \
  --logs-path ./logs/bgp_245_6_$(date +%F_%H%M%S) \
  --log-level debug
```

### Using Custom Variables File

```bash
export BGP_245_VAR_FILE=/path/to/custom/vars.yaml

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_session_recovery_after_interface_flap.py \
  --logs-path ./logs/bgp_245_custom_$(date +%F_%H%M%S) \
  --log-level debug
```

## Configuration Parameters

### Default Settings (from YAML)

```yaml
defaults:
  cli_type: klish              # BGP requires klish mode
  verify_timeout: 90           # Verification timeout (seconds)
  establish_timeout: 90        # BGP session establishment timeout
  downtime_slo: 10            # Maximum recovery time SLO (seconds)
  flap_hold_time: 3           # Interface shutdown duration (seconds)
  keepalive: 60               # BGP keepalive timer
  hold: 180                   # BGP hold timer
  cleanup: true               # Auto-cleanup after tests
  min_topology:
    - "D1D2:1"                # Minimum topology requirement
```

### Test-Specific Parameters

Each test case in the YAML defines:
- **interfaces**: Interface IP addresses and configurations
- **loopbacks**: Loopback configurations (for multihop tests)
- **static_routes**: Static routes (for multihop tests)
- **routers**: BGP router AS numbers and router IDs
- **neighbors**: BGP neighbor configurations
- **bfd**: BFD configurations (for test 2.4.5.6)
- **flap**: Interface flap parameters (which DUT, which interface)

## Test Methodology

### Test Flow

1. **Setup Phase**
   - Configure interface IP addresses
   - Configure loopback interfaces (if needed)
   - Configure static routes (for multihop)
   - Configure BGP routers with AS numbers
   - Configure BGP neighbors
   - Enable BFD (for test 2.4.5.6)

2. **Pre-check Phase**
   - Wait for BGP sessions to establish (up to 90 seconds)
   - Verify all sessions reach Established state

3. **Stimulus Phase**
   - Shutdown specified interface
   - Wait for flap_hold_time (3 seconds)
   - Bring interface back up (no shutdown)

4. **Verification Phase**
   - Start timer when interface comes up
   - Poll BGP session status (0.5 second intervals)
   - Measure time until session returns to Established
   - Validate recovery time meets SLO

5. **Cleanup Phase**
   - Remove BFD configurations
   - Remove BGP neighbors
   - Remove BGP routers
   - Remove static routes
   - Remove loopback IPs
   - Remove interface IPs

### Recovery Time Measurement

```python
# Pseudo-code for recovery measurement
interface_up_time = time.time()

while time.time() - interface_up_time < max_timeout:
    if bgp_session_is_established():
        recovery_time = time.time() - interface_up_time
        break
    sleep(0.5)

assert recovery_time <= downtime_slo
```

## Expected Results

### Pass Criteria

✅ **Test passes if:**
1. BGP session successfully establishes in pre-check (within 90 seconds)
2. BGP session goes down during interface shutdown
3. BGP session recovers to Established after interface no-shutdown
4. Recovery time ≤ 10 seconds (for tests 2.4.5.1-2.4.5.5)
5. Recovery time < 5 seconds (for test 2.4.5.6 with BFD)
6. No unexpected errors or exceptions

### Fail Criteria

❌ **Test fails if:**
1. BGP session fails to establish during pre-check
2. BGP session does not go down during interface shutdown
3. BGP session does not recover after interface restoration
4. Recovery time exceeds SLO
5. Configuration errors occur
6. BGP enters unexpected states

## Performance Benchmarks

### Expected Recovery Times

| Test | Scenario | Typical Recovery | Max SLO |
|------|----------|------------------|---------|
| 2.4.5.1 | eBGP numbered (DUT1 flap) | 5-8 seconds | 10 seconds |
| 2.4.5.2 | eBGP numbered (DUT2 flap) | 5-8 seconds | 10 seconds |
| 2.4.5.3 | iBGP numbered | 6-9 seconds | 10 seconds |
| 2.4.5.4 | iBGP unnumbered | 6-10 seconds | 10 seconds |
| 2.4.5.5 | eBGP multihop | 7-10 seconds | 10 seconds |
| 2.4.5.6 | eBGP with BFD | **2-4 seconds** | 5 seconds |

### BFD Performance Advantage

- **Without BFD**: Recovery depends on BGP timers (typically 5-10 seconds)
- **With BFD**: Fast failure detection (~1 second) + quick recovery (~2-4 seconds total)
- **Improvement**: ~50-70% faster convergence

## Troubleshooting

### Common Issues

#### Issue 1: BGP Session Fails to Establish

**Symptoms:**
- Pre-check fails
- Session stays in Idle or Active state

**Solutions:**
```bash
# Check interface status
show interface Ethernet4

# Check IP connectivity
ping 10.0.0.2 source 10.0.0.1

# Check BGP configuration
show running-config | grep bgp

# Check BGP logs
docker exec -it bgp cat /var/log/frr/bgpd.log | tail -50
```

#### Issue 2: Recovery Time Exceeds SLO

**Symptoms:**
- Session recovers but takes > 10 seconds
- Consistent slow recovery

**Solutions:**
```bash
# Check system load
show system cpu
show system memory

# Check interface statistics for errors
show interface counters Ethernet4

# Verify BGP timers
show ip bgp neighbor 10.0.0.2 | grep -i timer

# Consider tuning BGP timers (in YAML):
keepalive: 30
hold: 90
```

#### Issue 3: Unnumbered BGP Fails (Test 2.4.5.4)

**Symptoms:**
- Unnumbered session does not establish
- Missing IPv6 link-local addresses

**Solutions:**
```bash
# Check IPv6 link-local addresses
show ipv6 interface Ethernet4

# Verify extended-nexthop capability
show ip bgp neighbor Ethernet4 | grep "extended nexthop"

# Check SONiC version (unnumbered BGP may require specific version)
show version
```

#### Issue 4: BFD Not Working (Test 2.4.5.6)

**Symptoms:**
- Recovery time with BFD similar to without BFD
- BFD session not established

**Solutions:**
```bash
# Check if BFD daemon is running
docker exec -it bgp ps aux | grep bfd

# Check BFD peer status
show bfd peers

# Check platform support (some platforms may not support BFD)
# If BFD is not supported, test 2.4.5.6 can be skipped
```

## Platform Support

### Supported Platforms

- **Virtual**: SONiC-VS (Virtual Switch)
- **Hardware**: Most SONiC-supported platforms
- **CLI Modes**: klish (recommended), click/vtysh

### Feature Requirements

- **BGP**: Required (all tests)
- **Unnumbered BGP**: Optional (test 2.4.5.4)
- **BFD**: Optional (test 2.4.5.6 - skip if not supported)

### Known Limitations

1. **Virtual Environments**: Recovery times may be 1-2 seconds slower due to CPU scheduling
2. **BFD Support**: Not all platforms support BFD; test 2.4.5.6 may need to be skipped
3. **Unnumbered BGP**: Requires specific SONiC version with extended-nexthop support
4. **Timing Variability**: Recovery times may vary ±2 seconds depending on system load

## Logs and Artifacts

### Log Locations

```
logs/bgp_245_<timestamp>/
├── result.xml              # Pytest result XML
├── result.html             # HTML test report
├── spytest.log            # Main SpyTest log
├── dut_<name>.log         # Per-DUT logs
└── bgp/
    ├── show_ip_bgp_summary.txt
    ├── show_interface_ethernet4.txt
    └── show_bfd_peers.txt
```

### Useful Debug Commands

```bash
# BGP session status
show ip bgp summary
show ip bgp neighbor <ip>

# Interface status
show interface Ethernet4
show interface status Ethernet4

# BFD status
show bfd peers
show bfd peer <ip>

# BGP logs
docker exec -it bgp cat /var/log/frr/bgpd.log | grep -i "established\|idle\|active"

# Routing table
show ip route
```

## References

### Documentation
- [BGP Test 2.4.5 Specification](../../Doc/bgp_245.md)
- [SpyTest Coding Guidelines](../../../spy_test_coding_guideline.md)

### Standards
- RFC 4271: Border Gateway Protocol 4 (BGP-4)
- RFC 5880: Bidirectional Forwarding Detection (BFD)
- RFC 5881: BFD for IPv4 and IPv6 (Single Hop)

### Related Tests
- Test 2.4.1: IPv4 Neighbor Session Establishment
- Test 2.4.2: IPv6 Neighbor Session Establishment
- Test 2.4.3: Incorrect AS Number Prevents Session

## Maintenance

### Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-07 | QA Team | Initial implementation |

### Contact

For questions or issues, please contact the SONiC testing team.

---

**Last Updated**: 2025-11-07
**Test ID**: 2.4.5
**Status**: Active
