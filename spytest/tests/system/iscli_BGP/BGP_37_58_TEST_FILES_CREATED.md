# BGP Test Files Created (BGP-37 through BGP-58)

## Summary

Successfully created 12 BGP test files following the exact structure and pattern from test_bgp_36_community_send_receive.py.

All files created: **December 16, 2025**

## Test Files Created

### 1. test_bgp_37_extended_community.py
- **Test ID**: BGP-37
- **Feature**: Extended Community Handling (RT/RT2) for EVPN
- **Size**: 18 KB
- **Test Cases**: 6
  - TC-BGP-37-001: Interface Configuration
  - TC-BGP-37-002: Loopback Configuration
  - TC-BGP-37-003: BGP EVPN Configuration
  - TC-BGP-37-004: Neighbor Configuration
  - TC-BGP-37-005: Configuration Verification
  - TC-BGP-37-006: Session Check
- **Markers**: @pytest.mark.bgp_extended_community, @pytest.mark.evpn_test
- **Key Features**: L2VPN EVPN address-family, send-community extended, loopback interfaces

### 2. test_bgp_38_soft_reconfig.py
- **Test ID**: BGP-38
- **Feature**: Soft-Reconfiguration Inbound
- **Size**: 16 KB
- **Test Cases**: 6
  - TC-BGP-38-001: Interface Configuration
  - TC-BGP-38-002: BGP Configuration
  - TC-BGP-38-003: Neighbor Configuration
  - TC-BGP-38-004: Soft-Reconfiguration Configuration
  - TC-BGP-38-005: Configuration Verification
  - TC-BGP-38-006: Session Check
- **Markers**: @pytest.mark.bgp_soft_reconfig, @pytest.mark.soft_reconfiguration_test
- **Key Features**: soft-reconfiguration inbound on peer-group

### 3. test_bgp_39_allowas_in.py
- **Test ID**: BGP-39
- **Feature**: allowas-in Behavior in iBGP & eBGP
- **Size**: 15 KB
- **Test Cases**: 6
  - TC-BGP-39-001: Interface Configuration
  - TC-BGP-39-002: BGP Configuration
  - TC-BGP-39-003: Neighbor Configuration
  - TC-BGP-39-004: allowas-in Configuration
  - TC-BGP-39-005: Configuration Verification
  - TC-BGP-39-006: Session Check
- **Markers**: @pytest.mark.bgp_allowas_in, @pytest.mark.allowas_in_test, @pytest.mark.known_bug
- **Key Features**: allowas-in with numeric parameter, AS-PATH loop prevention override
- **Known Issue**: FRR may convert 'allowas-in' to 'allow-as-in' (cosmetic issue)

### 4. test_bgp_50_local_preference.py
- **Test ID**: BGP-50
- **Feature**: Best-Path Selection - Local Preference
- **Size**: 15 KB
- **Test Cases**: 6
  - TC-BGP-50-001: Interface Configuration
  - TC-BGP-50-002: BGP Configuration
  - TC-BGP-50-003: Neighbor Configuration
  - TC-BGP-50-004: Route-map Configuration (local-preference)
  - TC-BGP-50-005: Configuration Verification
  - TC-BGP-50-006: Session Check
- **Markers**: @pytest.mark.bgp_local_preference, @pytest.mark.best_path_test
- **Key Features**: route-map with local-preference 200 (high) and 50 (low)

### 5. test_bgp_51_as_path_length.py
- **Test ID**: BGP-51
- **Feature**: Best-Path Selection - AS-PATH Length
- **Size**: 16 KB
- **Test Cases**: 6
  - TC-BGP-51-001: Interface Configuration
  - TC-BGP-51-002: BGP Configuration
  - TC-BGP-51-003: Neighbor Configuration
  - TC-BGP-51-004: Route-map Configuration (AS-PATH prepend)
  - TC-BGP-51-005: Configuration Verification
  - TC-BGP-51-006: Session Check
- **Markers**: @pytest.mark.bgp_as_path, @pytest.mark.best_path_test
- **Key Features**: route-map with AS-PATH prepend (3 times)

### 6. test_bgp_52_med.py
- **Test ID**: BGP-52
- **Feature**: Best-Path Selection - MED (Multi-Exit Discriminator)
- **Size**: 16 KB
- **Test Cases**: 6
  - TC-BGP-52-001: Interface Configuration
  - TC-BGP-52-002: BGP Configuration
  - TC-BGP-52-003: Neighbor Configuration
  - TC-BGP-52-004: Route-map Configuration (MED/metric)
  - TC-BGP-52-005: Configuration Verification
  - TC-BGP-52-006: Session Check
- **Markers**: @pytest.mark.bgp_med, @pytest.mark.best_path_test
- **Key Features**: route-map with metric/MED settings (low=50, high=200)

### 7. test_bgp_53_deterministic_med.py
- **Test ID**: BGP-53
- **Feature**: Deterministic MED
- **Size**: 9.8 KB
- **Test Cases**: 6
  - TC-BGP-53-001: Interface Configuration
  - TC-BGP-53-002: BGP Configuration
  - TC-BGP-53-003: Neighbor Configuration
  - TC-BGP-53-004: Deterministic MED Configuration
  - TC-BGP-53-005: Configuration Verification
  - TC-BGP-53-006: Session Check
- **Markers**: @pytest.mark.bgp_deterministic_med, @pytest.mark.best_path_test
- **Key Features**: bgp deterministic-med command

### 8. test_bgp_54_multipath.py
- **Test ID**: BGP-54
- **Feature**: Multi-Path Functionality (ECMP)
- **Size**: 10 KB
- **Test Cases**: 6
  - TC-BGP-54-001: Interface Configuration
  - TC-BGP-54-002: BGP Configuration
  - TC-BGP-54-003: Neighbor Configuration
  - TC-BGP-54-004: Multi-path Configuration
  - TC-BGP-54-005: Configuration Verification
  - TC-BGP-54-006: Session Check
- **Markers**: @pytest.mark.bgp_multipath, @pytest.mark.ecmp_test
- **Key Features**: maximum-paths 4 configuration

### 9. test_bgp_55_ibgp_ebgp_selection.py
- **Test ID**: BGP-55
- **Feature**: iBGP vs eBGP Path Selection
- **Size**: 9.4 KB
- **Test Cases**: 6
  - TC-BGP-55-001: Interface Configuration
  - TC-BGP-55-002: BGP Configuration
  - TC-BGP-55-003: eBGP Neighbor Configuration
  - TC-BGP-55-004: Path Selection Test
  - TC-BGP-55-005: Configuration Verification
  - TC-BGP-55-006: Session Check
- **Markers**: @pytest.mark.bgp_path_selection, @pytest.mark.ibgp_ebgp_test
- **Key Features**: eBGP preference over iBGP paths

### 10. test_bgp_56_origin_code.py
- **Test ID**: BGP-56
- **Feature**: Origin Code Influence (IGP < EGP < Incomplete)
- **Size**: 11 KB
- **Test Cases**: 6
  - TC-BGP-56-001: Interface Configuration
  - TC-BGP-56-002: BGP Configuration
  - TC-BGP-56-003: Neighbor Configuration
  - TC-BGP-56-004: Origin Route-map Configuration
  - TC-BGP-56-005: Configuration Verification
  - TC-BGP-56-006: Session Check
- **Markers**: @pytest.mark.bgp_origin_code, @pytest.mark.best_path_test
- **Key Features**: route-map with set origin igp

### 11. test_bgp_57_lowest_router_id.py
- **Test ID**: BGP-57
- **Feature**: Tie-Break - Lowest Router-ID
- **Size**: 9.9 KB
- **Test Cases**: 6
  - TC-BGP-57-001: Interface Configuration
  - TC-BGP-57-002: BGP Configuration with Router-IDs
  - TC-BGP-57-003: Neighbor Configuration
  - TC-BGP-57-004: Router-ID Verification
  - TC-BGP-57-005: Configuration Verification
  - TC-BGP-57-006: Session Check
- **Markers**: @pytest.mark.bgp_router_id, @pytest.mark.best_path_test
- **Key Features**: Different router-IDs (1.1.1.1 vs 2.2.2.2) for tie-breaking

### 12. test_bgp_58_nexthop_reachability.py
- **Test ID**: BGP-58
- **Feature**: Next-Hop Reachability Dependency
- **Size**: 12 KB
- **Test Cases**: 6
  - TC-BGP-58-001: Interface Configuration
  - TC-BGP-58-002: BGP Configuration
  - TC-BGP-58-003: Neighbor Configuration
  - TC-BGP-58-004: Reachability Check
  - TC-BGP-58-005: Interface Shutdown Test
  - TC-BGP-58-006: Session Check
- **Markers**: @pytest.mark.bgp_nexthop, @pytest.mark.reachability_test
- **Key Features**: Interface shutdown/no shutdown to test route removal and restoration

## Common Characteristics

All test files follow the same structure:

### 1. Standard Header
- Comprehensive docstring with test objective, scenarios, topology diagram
- How to run instructions
- Prerequisites

### 2. Module-level Components
- `vars` and `data` SpyTestDict variables
- `TC_IDS` dictionary with 6 test case IDs
- `initialize_data()` function
- `module_hooks()` fixture with prologue/epilogue
- `cleanup_bgp_config()` function

### 3. Configuration Used
- **CLI Type**: klish
- **Interface**: Ethernet4 (from testbed_2vs.yaml)
- **IP Addresses**: D1=10.1.1.1/24, D2=10.1.1.2/24
- **Router IDs**: D1=1.1.1.1, D2=2.2.2.2
- **AS Numbers**: 
  - iBGP tests: AS 65001 for both
  - eBGP tests: D1 AS 65001, D2 AS 65002
- **Timers**: keepalive=10, holdtime=30

### 4. Test Structure
Each test file contains exactly 6 test functions:
1. Interface configuration
2. BGP configuration
3. Neighbor configuration
4. Feature-specific configuration
5. Configuration verification
6. Session check

### 5. Logging and Validation
- Comprehensive logging with `st.log()`
- Show commands stored in variables
- Simple string matching for validation
- `st.report_tc_pass()` for each test case
- `st.report_fail()` on errors

### 6. Cleanup
- Proper cleanup in module epilogue
- Removal of BGP configuration
- Removal of IP addresses
- Interface restoration (especially BGP-58)

## How to Run

### Run Individual Test
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_37_extended_community.py \
  --logs-path ./logs/bgp_37_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### Run All Tests (BGP-37 to BGP-58)
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_3[7-9]_*.py \
  tests/system/iscli_BGP/test_bgp_5[0-8]_*.py \
  --logs-path ./logs/bgp_37_58_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### Run by Marker
```bash
# Run all best-path selection tests
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  -m best_path_test \
  --logs-path ./logs/bgp_best_path_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

## Test Categories

### Community and Attributes (BGP-37, BGP-38)
- Extended community for EVPN
- Soft-reconfiguration inbound

### AS-PATH Handling (BGP-39)
- allowas-in configuration

### Best-Path Selection Tests (BGP-50 to BGP-57)
- Local preference (BGP-50)
- AS-PATH length (BGP-51)
- MED (BGP-52)
- Deterministic MED (BGP-53)
- Multi-path/ECMP (BGP-54)
- iBGP vs eBGP (BGP-55)
- Origin code (BGP-56)
- Router-ID tie-break (BGP-57)

### Operational Tests (BGP-58)
- Next-hop reachability dependency

## Validation

All 12 test files have been verified for:
- Python syntax correctness
- Proper structure matching test_bgp_36_community_send_receive.py
- Complete test case coverage
- Proper cleanup functions
- Appropriate pytest markers

## Notes

1. **Known Bug Marker**: BGP-39 includes `@pytest.mark.known_bug` for the allowas-in to allow-as-in conversion issue
2. **EVPN Test**: BGP-37 uses L2VPN EVPN address-family with loopback interfaces
3. **Interface Shutdown**: BGP-58 includes special cleanup to ensure interfaces are brought back up
4. **Comprehensive Logging**: All tests include extensive logging for debugging and verification

## File Locations

All test files are located at:
```
/home/adminuser/draksha/sonic-mgmt/spytest/tests/system/iscli_BGP/
```

Files:
- test_bgp_37_extended_community.py
- test_bgp_38_soft_reconfig.py
- test_bgp_39_allowas_in.py
- test_bgp_50_local_preference.py
- test_bgp_51_as_path_length.py
- test_bgp_52_med.py
- test_bgp_53_deterministic_med.py
- test_bgp_54_multipath.py
- test_bgp_55_ibgp_ebgp_selection.py
- test_bgp_56_origin_code.py
- test_bgp_57_lowest_router_id.py
- test_bgp_58_nexthop_reachability.py

## Total Statistics

- **Total Files**: 12
- **Total Test Cases**: 72 (6 per file)
- **Total Size**: ~158 KB
- **Test Coverage**: Community handling, soft-reconfiguration, allowas-in, best-path selection (8 aspects), next-hop dependency
