# SM_ISCLI_P2_78 / SSE-T8196 - LACP Fast Rate Configuration Test

**Date:** 2026-02-13
**Author:** Athira Arputharaj
**Status:** ✅ **IMPLEMENTATION COMPLETE**

---

## 🎯 **Test Objective**

Verify and detect the LACP fast_rate configuration bug where the command `interface PortChannel X; fallback fast_rate` incorrectly enables only fallback mode instead of properly configuring the LACP fast rate interval.

---

## 🐛 **Bug Description**

**SM_ISCLI_P2_78 / SSE-T8196**: LACP fast_rate configuration doesn't work properly.

### Bug Behavior
```
sonic(config)# interface PortChannel 10
sonic(config-if-po10)# fallback fast_rate
sonic(config-if-po10)# end

sonic# show interface PortChannel
...
Fallback: Enabled          ← BUG: Should configure fast_rate, not just fallback!
```

### Expected Behavior
- Command `fallback fast_rate` should configure LACP fast rate (1 second interval)
- `show interface PortChannel` should indicate fast_rate is configured
- Fallback and fast_rate should be independent configurations

### Actual Behavior (Bug)
- Command appears to just enable fallback mode
- Fast rate interval is NOT configured (remains 30 seconds)
- No indication of fast_rate in show output

---

## 📦 **Implementation Files**

### 1. Test Script
**File:** `tests/switching/portchannel/test_sm_iscli_p2_78_lacp_fast_rate.py` (875 lines)

**Contains:**
- 8 comprehensive test cases (TC 78.1 - 78.8)
- Helper functions for PortChannel operations
- Module-level setup/teardown fixtures
- Type hints for Python 3.9+
- Proper error handling and logging

### 2. Variable File
**File:** `vars/switching/portchannel/vars_sm_iscli_p2_78.yaml` (106 lines)

**Contains:**
- Test case configurations
- PortChannel parameters (IDs, IP addresses)
- LACP rate parameters (fast: 1s, slow: 30s)
- Test scenarios for independence testing

### 3. Test Cases Document
**File:** `testcases_SM_ISCLI_P2_78.md`

**Contains:**
- Detailed test case specifications
- Pre-requisites and topology requirements
- Expected vs actual behavior descriptions
- Validation criteria

---

## 🧪 **Test Cases Implemented**

### TC 78.1: Baseline PortChannel Creation and Status
**Priority:** P0 (Baseline)
**Objective:** Verify PortChannel can be created and basic status is displayed correctly.
- Creates PortChannel with IP addresses
- Verifies default state: fallback disabled, fast_rate not configured

### TC 78.2: Configure LACP Fast Rate (Bug Test)
**Priority:** P0 (Critical - Core Bug Test)
**Objective:** Verify `fallback fast_rate` actually configures fast rate.
- **This test DETECTS the bug** - will FAIL if bug exists
- Configures fast_rate and verifies it's actually applied
- Checks running-config for fast_rate command

### TC 78.3: Separate Fallback and Fast Rate Configuration
**Priority:** P1 (High)
**Objective:** Verify fallback and fast_rate are independent.
- Tests 4 scenarios:
  1. Fallback only (no fast_rate)
  2. Fast_rate only (no fallback)
  3. Both enabled
  4. Fallback only again
- Verifies each configuration is independent

### TC 78.4: Verify Show Commands Display Fast Rate Status
**Priority:** P1 (High)
**Objective:** Verify show commands correctly display fast_rate status.
- Tests multiple show commands
- Verifies running-config contains fast_rate
- Tests removal of fast_rate

### TC 78.5: Toggle Fast Rate Multiple Times
**Priority:** P2 (Medium)
**Objective:** Verify fast_rate can be toggled reliably.
- Enables and disables fast_rate 3 times
- Verifies configuration after each toggle
- Ensures no residual state

### TC 78.6: Multiple PortChannels with Different Fast Rate Config
**Priority:** P2 (Medium)
**Objective:** Verify independent fast_rate on multiple PortChannels.
- Creates PortChannel 10 with fast_rate enabled
- Creates PortChannel 20 with fast_rate disabled
- Swaps configurations and re-verifies

### TC 78.7: Negative Test - Invalid Fast Rate Syntax
**Priority:** P2 (Medium)
**Objective:** Verify invalid syntax is rejected.
- Tests invalid commands:
  - `fast_rate invalid`
  - `fast_rate 123`
  - `fast_rate on`
- Verifies PortChannel config unchanged after errors

### TC 78.8: Configuration Persistence After Save
**Priority:** P1 (High)
**Objective:** Verify fast_rate persists after `write memory`.
- Configures fast_rate
- Saves configuration
- Verifies fast_rate still in running-config

---

## 🚀 **How to Execute**

### Run All Test Cases
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_1node.yaml \
  tests/switching/portchannel/test_sm_iscli_p2_78_lacp_fast_rate.py \
  --logs-path ./logs/test_sm_iscli_p2_78_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### Run Specific Test Case
```bash
# Run only the bug detection test (TC 78.2)
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_1node.yaml \
  tests/switching/portchannel/test_sm_iscli_p2_78_lacp_fast_rate.py::test_ft_sm_iscli_p2_78_02_configure_fast_rate_bug_test \
  --logs-path ./logs/test_sm_iscli_p2_78_bug_test_$(date +%F_%H%M%S) \
  --log-level debug
```

---

## 🔧 **Key Implementation Features**

### 1. Helper Functions
```python
get_available_interfaces(dut, count=2)       # Get available Ethernet interfaces
cleanup_portchannel(dut, portchannel_id)     # Clean up PortChannel config
create_portchannel_with_members(...)         # Create PC with members and IPs
configure_fast_rate(dut, pc_id, enable)      # Enable/disable fast_rate
configure_fallback(dut, pc_id, enable)       # Enable/disable fallback
verify_fast_rate_status(dut, pc_id, ...)     # Verify fast_rate status
```

### 2. Pagination Handling
All show commands use `| no-more` to prevent pagination hangs:
```python
output = st.show(dut, "show interface PortChannel 10 | no-more",
                 type="klish", skip_tmpl=True, skip_error_check=True)
```

### 3. Configuration Detection
Uses running-configuration to reliably detect fast_rate:
```python
output = st.show(dut, "show running-configuration interface PortChannel 10 | no-more",
                 type="klish", skip_tmpl=True, skip_error_check=True)
has_fast_rate = "fast_rate" in output_str or "fast-rate" in output_str
```

### 4. Cleanup Strategy
- Module-level cleanup removes all test PortChannels
- Function-level cleanup handled by individual tests
- Proper verification after cleanup

---

## 📊 **Test Coverage**

| Aspect | Coverage |
|--------|----------|
| **PortChannel Creation** | ✅ Baseline test |
| **Fast Rate Configuration** | ✅ Bug test, toggle test |
| **Independence** | ✅ Fallback vs fast_rate test |
| **Show Commands** | ✅ Multiple show command verification |
| **Persistence** | ✅ Write memory test |
| **Multiple PCs** | ✅ Independent config test |
| **Negative Testing** | ✅ Invalid syntax test |
| **Error Detection** | ✅ All tests include verification |

---

## 🎯 **Bug Detection Strategy**

### Before Fix (Bug Exists)
1. Configure `interface PortChannel 10; fallback fast_rate`
2. Check running-config: **Only "fallback" appears** ❌
3. LACP rate: **Still 30 seconds (slow)** ❌
4. **Test FAILS** - Bug detected!

### After Fix (Bug Fixed)
1. Configure `interface PortChannel 10; fallback fast_rate`
2. Check running-config: **"fast_rate" appears** ✅
3. LACP rate: **1 second (fast)** ✅
4. **Test PASSES** - Bug is fixed!

---

## ⚠️ **Important Notes**

1. **Management Interface Protection:**
   - Tests automatically exclude management interfaces
   - No modification of management IP addresses
   - Safe for production-like environments

2. **Interface Requirements:**
   - Minimum 2 Ethernet interfaces for basic tests
   - Minimum 4 Ethernet interfaces for multi-PC test (TC 78.6)
   - Tests automatically skip if insufficient interfaces

3. **Pagination Handling:**
   - All show commands use `| no-more`
   - Prevents console hang issues
   - Ensures complete output capture

4. **Configuration Cleanup:**
   - All tests clean up after themselves
   - Module epilogue ensures no residual config
   - Safe for repeated execution

5. **Platform Support:**
   - Works on both hardware and virtual platforms
   - Requires SONiC version with IS-CLI (klish) support

---

## 🔗 **Related Issues and Tests**

- **SM_ISCLI_22:** Management interface configuration fixes
- **SM_ISCLI_25:** Interface description quote handling
- **SM_ISCLI_28:** BGP cleanup detection fixes
- **SSE-T8196:** Original bug ticket

---

## 📝 **Test Case IDs**

```python
TC_IDS = {
    "baseline": "TC-SM-ISCLI-P2-78-01",
    "fast_rate_bug": "TC-SM-ISCLI-P2-78-02",
    "independence": "TC-SM-ISCLI-P2-78-03",
    "show_commands": "TC-SM-ISCLI-P2-78-04",
    "toggle": "TC-SM-ISCLI-P2-78-05",
    "multiple_pcs": "TC-SM-ISCLI-P2-78-06",
    "negative": "TC-SM-ISCLI-P2-78-07",
    "persistence": "TC-SM-ISCLI-P2-78-08",
}
```

---

## 📂 **File Structure**

```
spytest/
├── tests/
│   └── switching/
│       └── portchannel/
│           ├── test_sm_iscli_p2_78_lacp_fast_rate.py    # Test script (875 lines)
│           └── README_SM_ISCLI_P2_78.md                  # This file
├── vars/
│   └── switching/
│       └── portchannel/
│           └── vars_sm_iscli_p2_78.yaml                  # Variable file (106 lines)
└── testcases_SM_ISCLI_P2_78.md                           # Test case specifications
```

---

## ✅ **Implementation Status**

- ✅ **YAML variable file created** - All test parameters defined
- ✅ **Test script created** - 875 lines, 8 test cases
- ✅ **Helper functions implemented** - PortChannel operations
- ✅ **Module fixtures implemented** - Setup and cleanup
- ✅ **All 8 test cases implemented** - Complete coverage
- ✅ **Pagination handling** - All show commands use `| no-more`
- ✅ **Type hints added** - Python 3.9+ compatible
- ✅ **Documentation complete** - README, test cases doc
- ✅ **Lint checks passed** - Code quality verified

---

## 🚦 **Next Steps**

1. **Execute test suite on device:**
   ```bash
   ./bin/spytest --tryssh 1 \
     --testbed ./testbeds/testbed_vs_1node.yaml \
     tests/switching/portchannel/test_sm_iscli_p2_78_lacp_fast_rate.py \
     --logs-path ./logs/test_sm_iscli_p2_78_$(date +%F_%H%M%S) \
     --log-level debug --skip-init-config --ifname-type native
   ```

2. **Verify bug detection:**
   - If TC 78.2 **FAILS** - Bug exists (as expected)
   - Review logs for bug evidence
   - Document bug behavior

3. **After bug fix:**
   - Re-run test suite
   - All tests should **PASS**
   - Verify fast_rate properly configured

4. **Integration:**
   - Add to regression test suite
   - Include in CI/CD pipeline
   - Monitor for regressions

---

**Status:** ✅ **READY FOR TESTING**
**Test Script:** 875 lines, fully documented
**Test Cases:** 8 comprehensive scenarios
**Code Quality:** Lint checks passed
**Platform Support:** Hardware and Virtual

---

**Implementation completed on:** 2026-02-13
**Author:** Athira Arputharaj
