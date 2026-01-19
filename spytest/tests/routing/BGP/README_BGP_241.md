# BGP Test ID 2.4.1 - IPv4 Neighbor Session Establishment

## Overview
This test suite implements all 8 sub-testcases from **Test ID 2.4.1: IPv4 BGP Neighbor Session Establishment** as documented in `Doc/bgp_241.md`.

## Files Created

1. **Test Script**: `test_bgp_ipv4_neighbor_session_establishment.py`
   - Location: `tests/routing/BGP/`
   - Contains 8 test methods, one for each sub-testcase
   - Supports both `click` and `klish` (sonic-cli) modes
   - Implements proper setup/teardown with complete cleanup

2. **Variables File**: `vars_bgp_ipv4_neighbor_session_establishment.yaml`
   - Location: `tests/routing/BGP/`
   - Contains all configuration data for all 8 testcases
   - Topology-aware with DUT aliases (D1, D2)
   - Includes interface, loopback, static route, and BGP configurations

3. **Documentation**: `Doc/bgp_241.md`
   - Comprehensive documentation with all CLI commands
   - Both click and klish configurations
   - Verification commands and expected results

## Test Coverage

### Test ID 2.4.1.1 - iBGP IPv4 Numbered (Loopback-Based)
- ✓ Loopback interfaces with /32 addresses
- ✓ Static routes for loopback reachability
- ✓ iBGP peering (AS 65001 on both sides)
- ✓ Update-source Loopback0

### Test ID 2.4.1.2 - iBGP IPv4 Unnumbered (Loopback-Based)
- ✓ Loopback interfaces
- ✓ Unnumbered Ethernet4 referencing Loopback0
- ✓ iBGP peering using interface name
- ✓ Link-local addressing

### Test ID 2.4.1.3 - eBGP IPv4 Numbered (Loopback-Based)
- ✓ Loopback interfaces with /32 addresses
- ✓ Static routes for loopback reachability
- ✓ eBGP peering (AS 65001 and 65002)
- ✓ eBGP multihop 2
- ✓ Update-source Loopback0

### Test ID 2.4.1.4 - eBGP IPv4 Unnumbered (Loopback-Based)
- ✓ Loopback interfaces
- ✓ Unnumbered Ethernet4 referencing Loopback0
- ✓ eBGP peering using interface name
- ✓ Different AS numbers (65001, 65002)

### Test ID 2.4.1.5 - iBGP IPv4 Numbered (Direct Back-to-Back)
- ✓ Direct interface peering (10.0.24.1/30 - 10.0.24.2/30)
- ✓ iBGP peering (AS 65001 on both sides)
- ✓ No loopback required
- ✓ Router-ID from interface IP

### Test ID 2.4.1.6 - iBGP IPv4 Unnumbered (Direct Back-to-Back)
- ✓ Unnumbered direct peering
- ✓ iBGP using interface name
- ✓ No IP addressing required on Ethernet4
- ✓ Link-local addressing

### Test ID 2.4.1.7 - eBGP IPv4 Numbered (Direct Back-to-Back)
- ✓ Direct interface peering (10.0.24.1/30 - 10.0.24.2/30)
- ✓ eBGP peering (AS 65001 and 65002)
- ✓ Single-hop eBGP (no multihop needed)
- ✓ Router-ID from interface IP

### Test ID 2.4.1.8 - eBGP IPv4 Unnumbered (Direct Back-to-Back)
- ✓ Unnumbered direct peering
- ✓ eBGP using interface name
- ✓ Different AS numbers (65001, 65002)
- ✓ Link-local addressing for BGP transport

## How to Run

### Run All Tests
```bash
cd /home/adminuser/sonic-mgmt-spytest/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/routing/BGP/test_bgp_ipv4_neighbor_session_establishment.py \
  --logs-path ./logs/test_bgp_241_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### Run Specific Test
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/routing/BGP/test_bgp_ipv4_neighbor_session_establishment.py::TestBgpIpv4NeighborSessionEstablishment::test_ibgp_ipv4_numbered_loopback \
  --logs-path ./logs/test_bgp_241_1_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### Run with Specific CLI Type
To test only with klish:
```bash
# Edit vars_bgp_ipv4_neighbor_session_establishment.yaml
# Change: cli_type: "klish"

# Or set environment variable
export BGP_241_CLI_TYPE="klish"
```

### Override Variables File
```bash
export BGP_241_VAR_FILE="/path/to/custom/vars.yaml"
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_vs_2d.yaml ...
```

## Test Execution Flow

Each test follows this pattern:

1. **Setup Method**:
   - Initialize tracking lists for cleanup

2. **Test Execution**:
   - For each CLI type (click, klish):
     - Configure interface IPs
     - Configure loopback IPs (if needed)
     - Configure static routes (if needed)
     - Configure BGP routers
     - Configure BGP neighbors
     - Wait 10 seconds for stabilization
     - Verify BGP sessions reach Established state
     - Cleanup and reset for next CLI type

3. **Teardown Method**:
   - Remove BGP neighbors
   - Remove BGP routers
   - Remove static routes
   - Remove loopback IPs
   - Remove interface IPs

## Verification

Each test verifies:
- ✓ BGP session state = **Established**
- ✓ Session establishment within timeout (120 seconds default)
- ✓ Proper neighbor configuration
- ✓ Clean configuration and teardown

## Topology Requirements

### testbed_vs_2d.yaml
```yaml
topology:
  smic_sonic1:  # Mapped to D1
    interfaces:
      Ethernet4: {EndDevice: smic_sonic2, EndPort: Ethernet4}

  smic_sonic2:  # Mapped to D2
    interfaces:
      Ethernet4: {EndDevice: smic_sonic1, EndPort: Ethernet4}
```

### Minimum Requirements
- 2 DUTs (D1, D2)
- 1 interconnect link (Ethernet4 ↔ Ethernet4)
- BGP support in SONiC image
- Both click and klish CLI modes available

## Configuration Defaults

From `vars_bgp_ipv4_neighbor_session_establishment.yaml`:

```yaml
defaults:
  cli_type: "click,klish"  # Test both modes
  verify_timeout: 120      # BGP session establishment timeout
  cleanup: true            # Cleanup after each test
  keepalive: 60           # BGP keepalive timer
  hold: 180               # BGP hold timer
  min_topology:
    - "D1D2:1"            # 2 DUTs, 1 link
```

## Troubleshooting

### Test Fails to Find Variables File
- Ensure `vars_bgp_ipv4_neighbor_session_establishment.yaml` is in the same directory as the test script
- Or set environment variable: `export BGP_241_VAR_FILE="/path/to/vars.yaml"`

### BGP Session Does Not Establish
- Check interface status: `show interface Ethernet4`
- Check IP connectivity: `ping <neighbor-ip>`
- Check BGP configuration: `show running-config | grep bgp`
- Check BGP status: `show ip bgp summary`
- Check logs: View SpyTest logs in `--logs-path` directory

### Cleanup Issues
- Tests implement comprehensive cleanup in `teardown_method()`
- If cleanup fails, manually run: `no router bgp` on both DUTs
- Check for residual configuration: `show running-config`

## Extending the Tests

### Add New Testcase
1. Add entry to `vars_bgp_ipv4_neighbor_session_establishment.yaml`:
   ```yaml
   testcases:
     "2.4.1.9":
       title: "New Test Scenario"
       interfaces: [...]
       bgp_routers: [...]
       bgp_neighbors: [...]
   ```

2. Add test method to `test_bgp_ipv4_neighbor_session_establishment.py`:
   ```python
   @pytest.mark.inventory(feature="Regression", testcases=["BGP_2.4.1.9"])
   def test_new_scenario(self) -> None:
       """Test ID 2.4.1.9 - New Scenario."""
       for cli_type in self.data.cli_types:
           self._execute_testcase("2.4.1.9", cli_type)
           self.teardown_method()
           self.setup_method()
       st.report_pass("test_case_passed")
   ```

### Modify Timeout
Edit `vars_bgp_ipv4_neighbor_session_establishment.yaml`:
```yaml
defaults:
  verify_timeout: 180  # Increase to 3 minutes
```

### Test on Different Topology
1. Create new testbed YAML
2. Update min_topology if needed
3. Update interface names in variables file
4. Run with new testbed: `--testbed ./testbeds/your_testbed.yaml`

## API Dependencies

The test uses these SpyTest APIs:

- `apis.routing.bgp`: BGP configuration and verification
  - `config_bgp_router()`
  - `create_bgp_neighbor()`
  - `delete_bgp_neighbor()`
  - `verify_bgp_summary()`
  - `config_bgp()`

- `apis.routing.ip`: IP addressing
  - `config_ip_addr_interface()`
  - `create_static_route()`
  - `delete_static_route()`

## Expected Results

All tests should:
- ✓ Pass with both click and klish CLI types
- ✓ Complete within verify_timeout (default 120 seconds)
- ✓ Leave DUTs in clean state (no residual configuration)
- ✓ Report "test_case_passed" on success

## Related Documentation

- **Test Plan**: `Doc/bgp_241.md` - Detailed test case documentation with CLI commands
- **Coding Guidelines**: `spy_test_coding_guideline.md` - SpyTest coding standards
- **Testbed**: `testbeds/testbed_vs_2d.yaml` - Topology definition

## Support

For issues or questions:
1. Check SpyTest logs in the logs directory
2. Review test execution output
3. Consult `Doc/bgp_241.md` for expected configuration
4. Check BGP API documentation in `apis/routing/bgp.py`

---

**Last Updated**: 2025-11-05
**Test ID**: 2.4.1
**Total Sub-testcases**: 8
**Status**: Ready for execution
