# BGP Test ID 2.4.1 - Generation Summary

## Generated Files

### 1. Test Script
**File**: `tests/routing/BGP/test_bgp_ipv4_neighbor_session_establishment.py`
- **Lines**: ~650
- **Test Methods**: 8 (one per sub-testcase)
- **CLI Support**: Both click and klish modes
- **Features**:
  - Complete test class following SpyTest conventions
  - Comprehensive setup/teardown with cleanup
  - DUT alias resolution (D1, D2 from topology)
  - Configuration helpers for interfaces, loopbacks, static routes, BGP
  - Verification using `show ip bgp summary`
  - Proper error handling and reporting

### 2. Variables File
**File**: `tests/routing/BGP/vars_bgp_ipv4_neighbor_session_establishment.yaml`
- **Lines**: ~300
- **Test Definitions**: 8 complete testcases
- **Features**:
  - Configurable defaults (CLI type, timeouts, cleanup)
  - Per-testcase configuration data
  - Interface, loopback, static route, and BGP neighbor definitions
  - Supports both numbered and unnumbered scenarios
  - Supports both iBGP and eBGP scenarios
  - Topology-aware (D1, D2 aliases)

### 3. Documentation
**File**: `Doc/bgp_241.md` (already existed)
- **Lines**: ~850
- **Sub-testcases**: 8 detailed specifications
- **CLI Examples**: Both click and klish for all scenarios
- **Verification Commands**: Comprehensive validation steps
- **Expected Results**: Detailed success criteria

### 4. README
**File**: `tests/routing/BGP/README_BGP_241.md`
- **Lines**: ~350
- **Content**:
  - How to run the tests
  - Test coverage details
  - Troubleshooting guide
  - Extension guide
  - API dependencies

## Test Coverage Matrix

| Test ID | Scenario | Peering Type | Interface Type | AS Relationship | Status |
|---------|----------|--------------|----------------|-----------------|--------|
| 2.4.1.1 | Loopback-Based | Numbered | Loopback | iBGP (65001) | ✓ Implemented |
| 2.4.1.2 | Loopback-Based | Unnumbered | Loopback | iBGP (65001) | ✓ Implemented |
| 2.4.1.3 | Loopback-Based | Numbered | Loopback | eBGP (65001-65002) | ✓ Implemented |
| 2.4.1.4 | Loopback-Based | Unnumbered | Loopback | eBGP (65001-65002) | ✓ Implemented |
| 2.4.1.5 | Direct B2B | Numbered | Physical | iBGP (65001) | ✓ Implemented |
| 2.4.1.6 | Direct B2B | Unnumbered | Physical | iBGP (65001) | ✓ Implemented |
| 2.4.1.7 | Direct B2B | Numbered | Physical | eBGP (65001-65002) | ✓ Implemented |
| 2.4.1.8 | Direct B2B | Unnumbered | Physical | eBGP (65001-65002) | ✓ Implemented |

## Quick Start

### 1. Navigate to SpyTest Directory
```bash
cd /home/adminuser/sonic-mgmt-spytest/sonic-mgmt/spytest
```

### 2. Run All Tests
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/routing/BGP/test_bgp_ipv4_neighbor_session_establishment.py \
  --logs-path ./logs/test_bgp_241_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### 3. Run Single Test
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/routing/BGP/test_bgp_ipv4_neighbor_session_establishment.py::TestBgpIpv4NeighborSessionEstablishment::test_ibgp_ipv4_numbered_loopback \
  --logs-path ./logs/test_bgp_241_1_$(date +%F_%H%M%S) \
  --log-level debug
```

## Test Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│ setup_class()                                               │
│ - Load YAML variables                                       │
│ - Ensure minimum topology (D1D2:1)                         │
│ - Map DUT aliases (D1→smic_sonic1, D2→smic_sonic2)        │
└─────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │ For each test method:                   │
        └─────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ setup_method()                                              │
│ - Initialize tracking lists                                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │ For each CLI type (click, klish):      │
        └─────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ _execute_testcase()                                         │
│ 1. Configure interface IPs                                  │
│ 2. Configure loopback IPs (if needed)                      │
│ 3. Configure static routes (if needed)                     │
│ 4. Configure BGP routers                                    │
│ 5. Configure BGP neighbors                                  │
│ 6. Wait 10 seconds for stabilization                       │
│ 7. Verify BGP sessions (Established state)                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ teardown_method()                                           │
│ - Remove BGP neighbors                                      │
│ - Remove BGP routers                                        │
│ - Remove static routes                                      │
│ - Remove loopback IPs                                       │
│ - Remove interface IPs                                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Report: test_case_passed or test_case_failed              │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Topology Awareness
- Uses DUT aliases (D1, D2) from testbed YAML
- Automatically maps to actual device names
- Portable across different testbeds

### 2. CLI Type Support
- Tests run with both `click` and `klish` modes
- Configurable via YAML: `cli_type: "click,klish"`
- Each test runs twice (once per CLI type)

### 3. Complete Cleanup
- Teardown removes all configurations in reverse order
- Ensures clean state for next test
- No manual cleanup required

### 4. Comprehensive Configuration
- Interface IP addressing
- Loopback interfaces
- Static routes (for loopback reachability)
- BGP routers (AS, router-ID)
- BGP neighbors (numbered and unnumbered)
- Update-source and eBGP-multihop

### 5. Robust Verification
- Polls for BGP Established state
- Configurable timeout (default 120 seconds)
- Uses SpyTest's `st.poll_wait()` for reliability
- Clear error messages on failure

## Implementation Details

### Test Class Structure
```python
@pytest.mark.topology("any")
class TestBgpIpv4NeighborSessionEstablishment:
    data = SpyTestDict()  # Shared class data

    @classmethod
    def setup_class(cls)  # Load config once

    def setup_method(self)  # Per-test init
    def teardown_method(self)  # Per-test cleanup

    # Helper methods
    def _resolve_dut()
    def _configure_interface_ip()
    def _configure_loopback_ip()
    def _configure_static_route()
    def _configure_bgp_router()
    def _configure_bgp_neighbor()
    def _configure_bgp_neighbor_interface()
    def _verify_bgp_session_established()
    def _execute_testcase()  # Main test logic

    # 8 test methods (one per sub-testcase)
    def test_ibgp_ipv4_numbered_loopback()
    def test_ibgp_ipv4_unnumbered_loopback()
    def test_ebgp_ipv4_numbered_loopback()
    def test_ebgp_ipv4_unnumbered_loopback()
    def test_ibgp_ipv4_numbered_direct()
    def test_ibgp_ipv4_unnumbered_direct()
    def test_ebgp_ipv4_numbered_direct()
    def test_ebgp_ipv4_unnumbered_direct()
```

### YAML Structure
```yaml
defaults:
  cli_type: "click,klish"
  verify_timeout: 120
  cleanup: true
  min_topology: ["D1D2:1"]

testcases:
  "2.4.1.1":
    title: "..."
    interfaces: [...]       # Interface configurations
    loopbacks: [...]        # Loopback configurations
    static_routes: [...]    # Static route configurations
    bgp_routers: [...]      # BGP router configurations
    bgp_neighbors: [...]    # BGP neighbor configurations
```

## API Usage

### BGP APIs (apis.routing.bgp)
- `config_bgp_router()` - Configure BGP router context
- `create_bgp_neighbor()` - Add BGP neighbor
- `delete_bgp_neighbor()` - Remove BGP neighbor
- `verify_bgp_summary()` - Verify BGP session state
- `config_bgp()` - Generic BGP configuration (update-source, multihop, etc.)
- `config_router_bgp_mode()` - Enable/disable BGP

### IP APIs (apis.routing.ip)
- `config_ip_addr_interface()` - Add/remove IP addresses
- `create_static_route()` - Add static routes
- `delete_static_route()` - Remove static routes

## Verification Strategy

Each test verifies:
1. **Configuration Applied**: APIs return success
2. **BGP Session State**: `show ip bgp summary` shows Established
3. **Timeout Compliance**: Session establishes within 120 seconds
4. **Cleanup Success**: All configuration removed in teardown

## Expected Test Results

### Success Criteria
- All 8 tests pass with both click and klish
- BGP sessions reach Established state
- No configuration residue after tests
- Execution time < 10 minutes per test

### Sample Output
```
Test: test_ibgp_ipv4_numbered_loopback
  CLI Type: click
    ✓ Interfaces configured
    ✓ Loopbacks configured
    ✓ Static routes configured
    ✓ BGP routers configured
    ✓ BGP neighbors configured
    ✓ Sessions established
    ✓ Cleanup successful
  CLI Type: klish
    ✓ Interfaces configured
    ✓ Loopbacks configured
    ✓ Static routes configured
    ✓ BGP routers configured
    ✓ BGP neighbors configured
    ✓ Sessions established
    ✓ Cleanup successful
  Result: PASSED
```

## Customization Options

### Change CLI Types
Edit `vars_bgp_ipv4_neighbor_session_establishment.yaml`:
```yaml
defaults:
  cli_type: "klish"  # Test only klish
  # or
  cli_type: "click"  # Test only click
```

### Adjust Timeouts
```yaml
defaults:
  verify_timeout: 180  # 3 minutes
  keepalive: 30        # 30 seconds
  hold: 90             # 90 seconds
```

### Disable Cleanup (for debugging)
```yaml
defaults:
  cleanup: false
```

### Change AS Numbers
```yaml
testcases:
  "2.4.1.3":
    bgp_routers:
      - dut: "D1"
        local_asn: 64512  # Change AS
```

## Files Location

```
sonic-mgmt-spytest/sonic-mgmt/spytest/
├── Doc/
│   └── bgp_241.md (existing documentation)
├── tests/routing/BGP/
│   ├── test_bgp_ipv4_neighbor_session_establishment.py (NEW)
│   ├── vars_bgp_ipv4_neighbor_session_establishment.yaml (NEW)
│   └── README_BGP_241.md (NEW)
└── BGP_241_GENERATION_SUMMARY.md (THIS FILE)
```

## Next Steps

1. **Review Files**
   - Check test script for any customizations needed
   - Verify YAML variables match your environment

2. **Test Execution**
   - Run a single test first to verify setup
   - Then run all tests
   - Check logs for any issues

3. **Integration**
   - Add to CI/CD pipeline if needed
   - Create test report templates
   - Document any environment-specific requirements

## Notes

- All files follow SpyTest coding guidelines
- Code is PEP8 compliant
- Type hints used throughout
- Comprehensive error handling
- Detailed logging for debugging
- Both HW and Virtual topology supported

---

**Generated**: 2025-11-05
**Based on**: Doc/bgp_241.md
**Template**: spy_test_coding_guideline.md
**Total Files**: 4
**Total Lines**: ~2150
**Test Coverage**: 100% (8/8 sub-testcases)
