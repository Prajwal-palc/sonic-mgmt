# BGP Test ID 4.1.4: Route-refresh During Policy Change

## Overview

This test suite validates BGP route-refresh capability during policy changes. It covers 10 comprehensive subtests that ensure BGP route-refresh and soft-reconfiguration mechanisms work correctly when policies (route-maps) are modified without tearing down BGP sessions.

## Test Files

- **Specification:** `Doc/bgp_414.md` - Detailed test specifications with CLI examples
- **Test Script:** `tests/routing/BGP/test_bgp_route_refresh_policy_change.py` - Python test implementation
- **Configuration:** `tests/routing/BGP/vars_bgp_route_refresh_policy_change.yaml` - Test variables and topology

## Test Coverage

### Test Cases

1. **4.1.4.1** - Basic route-refresh (inbound policy change) - IPv4
2. **4.1.4.2** - Basic route-refresh (outbound policy change) - IPv4
3. **4.1.4.3** - Soft-reconfiguration (inbound policy)
4. **4.1.4.4** - Route-refresh when neighbor lacks capability
5. **4.1.4.5** - IPv6 route-refresh and policy change
6. **4.1.4.6** - Large-scale route-refresh (thousands of routes)
7. **4.1.4.7** - Concurrent policy changes from both peers
8. **4.1.4.8** - Negative: malformed route-refresh messages
9. **4.1.4.9** - Route-refresh capability negotiation
10. **4.1.4.10** - Diagnostics & logging capture

## Requirements

### Topology

- **Testbed:** `./testbeds/testbed_vs_2node.yaml`
- **Minimum Topology:** 2 DUTs with 1 direct link (D1D2:1)
- **Support:** Hardware and Virtual environments

```
     D1 (DUT1)                          D2 (DUT2)
┌─────────────────┐              ┌─────────────────┐
│  AS 65001       │              │  AS 65002       │
│  10.1.1.1/24    │═════════════►│  10.1.1.2/24    │
│  Ethernet4      │              │  Ethernet4      │
└─────────────────┘              └─────────────────┘
```

### Prerequisites

- SONiC image with BGP support
- FRRouting (FRR) with route-refresh capability
- Python 3.7+
- SpyTest framework

### CLI Modes

- **Configuration:** klish mode
- **Show commands:** click mode

## Installation

No special installation required. The test suite is part of the sonic-mgmt SpyTest framework.

## Configuration

### Default Variables

Edit `tests/routing/BGP/vars_bgp_route_refresh_policy_change.yaml` to customize:

```yaml
defaults:
  cli_type_config: "klish"    # CLI for configuration
  cli_type_show: "click"      # CLI for show commands
  verify_timeout: 120         # Timeout for verification (seconds)
  cleanup: true               # Enable cleanup after tests
  min_topology:
    - "D1D2:1"                # Minimum topology requirement

  global_config:
    d1_interface: "Ethernet4"
    d2_interface: "Ethernet4"
    d1_ipv4: "10.1.1.1/24"
    d2_ipv4: "10.1.1.2/24"
    d1_asn: 65001
    d2_asn: 65002
```

### Environment Variables

You can override the variable file location:

```bash
export BGP_414_VAR_FILE="/path/to/custom/vars.yaml"
```

## Usage

### Running All Tests

```bash
cd /home/adminuser/sonic-mgmt-spytest/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_route_refresh_policy_change.py \
  --logs-path ./logs/test_bgp_414_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### Running Specific Tests

#### Run Single Test Case

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_route_refresh_policy_change.py::TestBgpRouteRefreshPolicyChange::test_bgp_route_refresh_inbound_policy_ipv4 \
  --logs-path ./logs/test_bgp_414_1_$(date +%F_%H%M%S) \
  --log-level debug
```

#### Run IPv6 Tests Only

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_route_refresh_policy_change.py::TestBgpRouteRefreshPolicyChange::test_bgp_route_refresh_ipv6 \
  --logs-path ./logs/test_bgp_414_ipv6_$(date +%F_%H%M%S) \
  --log-level debug
```

#### Run Multiple Specific Tests

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_route_refresh_policy_change.py::TestBgpRouteRefreshPolicyChange::test_bgp_route_refresh_inbound_policy_ipv4 \
  tests/routing/BGP/test_bgp_route_refresh_policy_change.py::TestBgpRouteRefreshPolicyChange::test_bgp_route_refresh_outbound_policy_ipv4 \
  --logs-path ./logs/test_bgp_414_basic_$(date +%F_%H%M%S) \
  --log-level debug
```

### Running with Custom Variables

```bash
export BGP_414_VAR_FILE="./custom_bgp_414_vars.yaml"

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_route_refresh_policy_change.py \
  --logs-path ./logs/test_bgp_414_custom_$(date +%F_%H%M%S) \
  --log-level debug
```

## Test Execution Flow

### Setup Phase (per suite)

1. Load test variables from YAML
2. Verify minimum topology requirements
3. Map DUT aliases (D1, D2) to actual devices
4. Initialize tracking structures for cleanup

### Per-Test Execution

1. **Setup BGP Session**
   - Configure BGP routers with AS numbers
   - Establish BGP neighbors
   - Advertise test prefixes

2. **Apply Policy Changes**
   - Create prefix-lists
   - Configure route-maps with match/set clauses
   - Apply route-maps to BGP neighbors (inbound/outbound)

3. **Trigger Route-Refresh**
   - Execute soft reconfiguration commands
   - Wait for refresh completion

4. **Verification**
   - Verify BGP session remains Established
   - Check RIB for policy application
   - Validate no unexpected session resets

5. **Cleanup**
   - Remove route-maps
   - Remove prefix-lists
   - Remove network advertisements
   - Verify clean state

## Verification Methods

### BGP Session Verification

```python
# Verify session is Established
show ip bgp summary
show ipv6 bgp summary

# Check neighbor status
show ip bgp neighbors <neighbor-ip>
```

### Route Verification

```python
# Check specific prefix in BGP RIB
show ip bgp <prefix>
show bgp ipv6 unicast <prefix>

# Verify advertised routes
show ip bgp neighbors <neighbor-ip> advertised-routes

# Verify received routes
show ip bgp neighbors <neighbor-ip> received-routes
```

### Capability Verification

```python
# Check route-refresh capability
show bgp neighbor <neighbor-ip> capabilities
```

## Troubleshooting

### Common Issues

#### 1. BGP Session Not Establishing

**Problem:** BGP session stays in Active or Idle state

**Solution:**
- Check IP connectivity: `ping 10.1.1.2`
- Verify interfaces are up: `show interface status`
- Check BGP configuration: `show running-config | grep bgp`
- Review logs: `show logging | grep BGP`

#### 2. Route-Refresh Not Working

**Problem:** Policy changes not applied after soft reconfiguration

**Solution:**
- Verify route-refresh capability: `show bgp neighbor <ip> capabilities`
- Check if soft-reconfiguration is enabled: `show ip bgp neighbors <ip>`
- Try hard reset if needed: `clear bgp ipv4 unicast <neighbor-ip>`

#### 3. Prefix Not Filtered

**Problem:** Route-map deny not removing prefix from RIB

**Solution:**
- Verify prefix-list matches correctly: `show ip prefix-list <name>`
- Check route-map configuration: `show route-map <name>`
- Ensure route-map is applied: `show ip bgp neighbors <ip> | grep "route-map"`
- Trigger refresh: `clear bgp ipv4 unicast <ip> soft in`

#### 4. Test Cleanup Issues

**Problem:** Residual configuration remains after test

**Solution:**
- Manually remove BGP config: `no router bgp <asn>`
- Remove route-maps: `no route-map <name>`
- Remove prefix-lists: `no ip prefix-list <name>`
- Set `cleanup: true` in YAML variables

### Debug Mode

Enable detailed logging:

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_route_refresh_policy_change.py \
  --logs-path ./logs/test_bgp_414_debug_$(date +%F_%H%M%S) \
  --log-level debug \
  --pdb
```

### Packet Capture

For test 4.1.4.10 (diagnostics), packet captures are automatically collected:

```bash
# Start manual capture if needed
sudo tcpdump -i Ethernet4 -w /tmp/bgp_refresh.pcap tcp port 179

# Analyze capture
tcpdump -r /tmp/bgp_refresh.pcap -A | grep -i "route-refresh"
wireshark /tmp/bgp_refresh.pcap
```

## Expected Results

### Success Criteria

- ✅ All BGP sessions establish successfully
- ✅ Route-refresh completes without session teardown
- ✅ Policies applied correctly to incoming/outgoing routes
- ✅ No unexpected session resets or flaps
- ✅ IPv4 and IPv6 route-refresh work correctly
- ✅ Soft-reconfiguration functions properly
- ✅ Cleanup leaves DUTs in clean state

### Performance Benchmarks

- **Small-scale (< 100 routes):** Route-refresh < 10 seconds
- **Large-scale (5000 routes):** Route-refresh < 60 seconds
- **CPU usage:** Should not exceed 80% during refresh
- **Memory increase:** Should not exceed 20% baseline

## Output Files

### Log Files

```
./logs/test_bgp_414_<timestamp>/
├── results.log              # Test execution results
├── session.log              # SpyTest session log
├── D1/
│   ├── cli.log             # CLI commands executed on D1
│   └── syslog.log          # System logs from D1
└── D2/
    ├── cli.log             # CLI commands executed on D2
    └── syslog.log          # System logs from D2
```

### Result Formats

- **HTML Report:** `results_<timestamp>.html`
- **JUnit XML:** `results_<timestamp>.xml` (use `--junit-xml` option)
- **JSON Report:** `results_<timestamp>.json` (use `--json-report` option)

## Known Limitations

1. **Test 4.1.4.6 (Large-scale):** Requires significant memory and may timeout on virtual environments
2. **Test 4.1.4.8 (Malformed messages):** Requires special BGP test tools, may be skipped in some setups
3. **CLI prompt detection:** klish mode may have timing issues after BGP commands
4. **Unnumbered interfaces:** Not fully supported, requires additional API work

## References

### RFCs

- **RFC 2918** - Route Refresh Capability for BGP-4
- **RFC 7313** - Enhanced Route Refresh Capability for BGP-4
- **RFC 4271** - A Border Gateway Protocol 4 (BGP-4)

### Documentation

- [SONiC BGP Documentation](https://github.com/Azure/SONiC/wiki/BGP)
- [FRRouting BGP Guide](https://docs.frrouting.org/en/latest/bgp.html)
- [SpyTest Framework Guide](https://github.com/Azure/sonic-mgmt/blob/master/spytest/Doc/intro.md)

## Contributing

To add new test cases:

1. Update `Doc/bgp_414.md` with test specification
2. Add test case definition to `vars_bgp_route_refresh_policy_change.yaml`
3. Implement test method in `test_bgp_route_refresh_policy_change.py`
4. Follow coding guidelines in `spy_test_coding_guideline.md`
5. Ensure cleanup is implemented
6. Update this README with new test details

## Support

For issues or questions:

1. Check logs in `./logs/` directory
2. Review test specification in `Doc/bgp_414.md`
3. Consult SpyTest documentation
4. Contact: Athira (test author)

## Version History

- **v1.0** (2025) - Initial implementation
  - 10 test cases covering route-refresh scenarios
  - IPv4 and IPv6 support
  - Klish and click CLI support
  - Comprehensive cleanup and diagnostics

---

**Last Updated:** 2025-11-20
**Author:** Athira
**Test Suite:** BGP Route-Refresh (Test ID 4.1.4)
