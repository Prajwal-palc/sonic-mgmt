# BGP Peer-Group Test Scripts (PG-16 to PG-20) - README

**Created**: December 16, 2025
**Framework**: SPyTest
**CLI Type**: Klish
**Topology**: 2-Device (testbed_2vs.yaml)

---

## ✅ Test Scripts Created

### 1. test_bgp_pg16_pkt_queue.py
**Test ID**: PG-16
**Title**: Peer-Group subgroup-pkt-queue-max Behavior
**Description**: Validates peer-group configuration for packet queue optimization

**Test Cases**:
- TC-BGP-PG16-001: Interface configuration
- TC-BGP-PG16-002: Peer-group creation
- TC-BGP-PG16-003: Neighbor assignment
- TC-BGP-PG16-004: Configuration verification
- TC-BGP-PG16-005: BGP session check

**Run Command**:
```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_pg16_pkt_queue.py \
  --logs-path ./logs/bgp_pg16_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

---

### 2. test_bgp_pg17_allowas_in.py
**Test ID**: PG-17
**Title**: Peer-Group with allowas-in for Many Members
**Description**: Validates allowas-in configuration (with known SONiC bug documentation)

**KNOWN BUG DOCUMENTED**:
- allowas-in numeric parameter (1-10) converts to "origin"
- allowas-in not supported at peer-group level
- Must configure individually on each neighbor

**Test Cases**:
- TC-BGP-PG17-001: Interface configuration
- TC-BGP-PG17-002: Peer-group creation
- TC-BGP-PG17-003: Neighbor assignment
- TC-BGP-PG17-004: allowas-in configuration
- TC-BGP-PG17-005: Configuration verification

**Run Command**:
```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_pg17_allowas_in.py \
  --logs-path ./logs/bgp_pg17_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

**Markers**: `@pytest.mark.known_bug` applied to all tests

---

### 3. test_bgp_pg18_conflicting_settings.py
**Test ID**: PG-18
**Title**: Negative Test - Conflicting Peer-Group Settings Detection
**Description**: Validates detection of conflicting peer-group remote-AS (NEGATIVE TEST)

**KNOWN BUG DOCUMENTED**:
- SONiC does NOT validate peer-group remote-AS compatibility
- Conflicting assignment accepted without error
- Neighbor with AS 65001 can be assigned to peer-group with AS 65002

**Test Cases**:
- TC-BGP-PG18-001: Interface configuration
- TC-BGP-PG18-002: Peer-group creation (IBGP and EBGP groups)
- TC-BGP-PG18-003: Initial assignment to IBGP_GROUP
- TC-BGP-PG18-004: Conflicting assignment attempt (negative test)
- TC-BGP-PG18-005: Configuration verification

**Run Command**:
```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_pg18_conflicting_settings.py \
  --logs-path ./logs/bgp_pg18_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

**Markers**: `@pytest.mark.negative_test`, `@pytest.mark.known_bug`

---

### 4. test_bgp_pg19_passive_mode.py
**Test ID**: PG-19
**Title**: Peer-Group with Passive Mode and Transitions
**Description**: Validates passive mode configuration and active/passive peer behavior

**Test Cases**:
- TC-BGP-PG19-001: Interface configuration
- TC-BGP-PG19-002: Passive peer-group creation (DUT1)
- TC-BGP-PG19-003: Active peer-group creation (DUT2)
- TC-BGP-PG19-004: Neighbor configuration
- TC-BGP-PG19-005: BGP session check (passive/active)

**Run Command**:
```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_pg19_passive_mode.py \
  --logs-path ./logs/bgp_pg19_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

**Markers**: `@pytest.mark.passive_mode`

---

### 5. test_bgp_pg20_routemap_override.py
**Test ID**: PG-20
**Title**: Peer-Group with Neighbor-Specific Route-Map Override
**Description**: Validates route-map inheritance and neighbor-specific override

**Test Cases**:
- TC-BGP-PG20-001: Interface configuration
- TC-BGP-PG20-002: Route-map creation (peer-group and neighbor route-maps)
- TC-BGP-PG20-003: Peer-group with route-map
- TC-BGP-PG20-004: Neighbor route-map override
- TC-BGP-PG20-005: Configuration verification

**Run Command**:
```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_pg20_routemap_override.py \
  --logs-path ./logs/bgp_pg20_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

**Markers**: `@pytest.mark.routemap_override`

---

## 🚀 Run All Tests Together

```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_pg16_pkt_queue.py \
  tests/system/iscli_BGP/test_bgp_pg17_allowas_in.py \
  tests/system/iscli_BGP/test_bgp_pg18_conflicting_settings.py \
  tests/system/iscli_BGP/test_bgp_pg19_passive_mode.py \
  tests/system/iscli_BGP/test_bgp_pg20_routemap_override.py \
  --logs-path ./logs/bgp_pg16_to_pg20_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

---

## 📊 Test Summary

| Test ID | File | Test Cases | Markers | Known Bugs |
|---------|------|------------|---------|------------|
| **PG-16** | test_bgp_pg16_pkt_queue.py | 5 | packet_queue | None |
| **PG-17** | test_bgp_pg17_allowas_in.py | 5 | allowas_in, known_bug | allowas-in parameter conversion |
| **PG-18** | test_bgp_pg18_conflicting_settings.py | 5 | negative_test, known_bug | No remote-AS validation |
| **PG-19** | test_bgp_pg19_passive_mode.py | 5 | passive_mode | None |
| **PG-20** | test_bgp_pg20_routemap_override.py | 5 | routemap_override | None |

**Total**: 5 test files, 25 test cases

---

## 🔧 Testbed Configuration

**File**: `testbeds/testbed_2vs.yaml`

**Devices**:
- **D1** (smic_sonic1): 192.168.100.203
  - Username: admin
  - Password: YourPaSsWoRd

- **D2** (smic_sonic2): 192.168.100.196
  - Username: admin
  - Password: YourPaSsWoRd

**Topology**:
```
D1 (smic_sonic1)           D2 (smic_sonic2)
192.168.100.203            192.168.100.196
Router-ID: 1.1.1.1         Router-ID: 2.2.2.2
AS: 65001                  AS: 65001

Ethernet4 <--------------> Ethernet4
10.1.1.1/24                10.1.1.2/24
```

---

## 🎯 Test Framework Features

### Key Patterns Used:
1. **Module Fixtures**: Setup/teardown with `@pytest.fixture(scope="module", autouse=True)`
2. **Klish CLI Type**: All commands use `type="klish"` for SONiC CLI
3. **Direct st.config()**: Used for BGP configuration (no high-level BGP API)
4. **Direct st.show()**: Used for validation with `skip_tmpl=True`
5. **Simple Validation**: String matching on show command outputs
6. **Proper Cleanup**: Removes BGP config and IP addresses in epilogue

### Validation Commands Used:
```bash
# Interface validation
show ip interface Ethernet4
show interface status Ethernet4

# BGP configuration validation
show running-configuration bgp
show running-configuration route-map

# BGP operational validation
show bgp summary
show bgp ipv4 unicast summary
show bgp peer-group <NAME>
show bgp ipv4 unicast neighbors <IP>
```

---

## 📋 Test Case Markers

Run tests by marker:

### By Feature:
```bash
# Packet queue tests
./bin/spytest --testbed ./testbeds/testbed_2vs.yaml tests/system/iscli_BGP/ -m packet_queue

# allowas-in tests
./bin/spytest --testbed ./testbeds/testbed_2vs.yaml tests/system/iscli_BGP/ -m allowas_in

# Passive mode tests
./bin/spytest --testbed ./testbeds/testbed_2vs.yaml tests/system/iscli_BGP/ -m passive_mode

# Route-map override tests
./bin/spytest --testbed ./testbeds/testbed_2vs.yaml tests/system/iscli_BGP/ -m routemap_override
```

### By Type:
```bash
# Negative tests only
./bin/spytest --testbed ./testbeds/testbed_2vs.yaml tests/system/iscli_BGP/ -m negative_test

# Known bug tests only
./bin/spytest --testbed ./testbeds/testbed_2vs.yaml tests/system/iscli_BGP/ -m known_bug

# All BGP peer-group tests
./bin/spytest --testbed ./testbeds/testbed_2vs.yaml tests/system/iscli_BGP/ -m bgp_peergroup
```

---

## ⚠️ Known Bugs Documented

### Bug 1: allowas-in Parameter Conversion (PG-17)
**Status**: Documented in test with `@pytest.mark.known_bug`

**Issue**:
- Command: `allowas-in 3`
- Stored as: `allowas-in origin`
- Impact: Cannot configure count-based AS-PATH loop prevention

**Test Behavior**: Test validates the BUGGY behavior (parameter conversion)

**Files**: `test_bgp_pg17_allowas_in.py`, `ALLOWAS_IN_TEST_RESULTS.md`, `JIRA_BUG_REPORT_ALLOWAS_IN.md`

---

### Bug 2: No Remote-AS Validation (PG-18)
**Status**: Documented in test with `@pytest.mark.known_bug`, `@pytest.mark.negative_test`

**Issue**:
- Neighbor with remote-as 65001 can be assigned to peer-group with remote-as 65002
- No error message displayed
- Invalid/conflicting configuration accepted

**Test Behavior**: Negative test validates ABSENCE of validation (bug)

**File**: `test_bgp_pg18_conflicting_settings.py`

---

## 📁 Results Location

After test execution, results are available in:

```
<logs-path>/
├── dashboard.html                # Test dashboard
├── summary.txt                   # Quick summary
├── results.html                  # Detailed test results
├── consolidated_report.html      # Aggregated report
├── dlog-D1-smic_sonic1.log      # DUT1 command logs
├── dlog-D2-smic_sonic2.log      # DUT2 command logs
└── module_test_bgp_pg*.log      # Module execution logs
```

---

## ✅ Success Criteria

All tests PASS if:
1. ✅ Interfaces configured with correct IP addresses (10.1.1.1/24, 10.1.1.2/24)
2. ✅ BGP routers configured with router-ID (1.1.1.1, 2.2.2.2)
3. ✅ Peer-groups created with correct parameters
4. ✅ Neighbors assigned to peer-groups successfully
5. ✅ Configuration visible in `show running-configuration bgp`
6. ✅ BGP sessions appear in `show bgp summary` (or appropriate state)
7. ✅ Cleanup completes successfully

---

## 🔍 Debugging Tips

### Test Fails - Check:
1. **Device connectivity**: Can you SSH to 192.168.100.203 and 192.168.100.196?
2. **Interface status**: Are Ethernet4 ports up on both devices?
3. **IP configuration**: Run `show ip interface Ethernet4` on both DUTs
4. **BGP configuration**: Run `show running-configuration bgp`
5. **Logs**: Check `dlog-D1-smic_sonic1.log` for command outputs

### Common Issues:
- **IP already configured**: Previous test didn't clean up - manually remove IPs
- **BGP already running**: Previous test didn't clean up - run `no router bgp 65001`
- **Interface down**: Check physical connection or run `no shutdown`
- **Timeout**: Increase wait times in test (currently 5s for interface, 30s for BGP)

---

## 📚 Reference Files

**Test Structure Reference**:
- `tests/system/iscli_Vlan/test_vlan_traffic_scapy.py` - Template structure

**Testbed Configuration**:
- `testbeds/testbed_2vs.yaml` - Device topology

**SONiC CLI Configurations**:
- `BGP_ADVANCED_TEST_CONFIGS.md` - All manual CLI configurations
- `ALLOWAS_IN_TEST_RESULTS.md` - allowas-in bug analysis
- `JIRA_BUG_REPORT_ALLOWAS_IN.md` - Bug report template

**Other Test Scripts**:
- `test_bgp_pg01_peergroup_creation.py` through `test_bgp_pg15_removal_effect.py`

---

## 🎯 Quick Start

1. **Navigate to spytest directory**:
   ```bash
   cd /home/adminuser/draksha/sonic-mgmt/spytest
   ```

2. **Run a single test**:
   ```bash
   ./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml \
     tests/system/iscli_BGP/test_bgp_pg16_pkt_queue.py \
     --logs-path ./logs/test_$(date +%F_%H%M%S) \
     --log-level debug --skip-init-config --ifname-type native
   ```

3. **Check results**:
   ```bash
   cat ./logs/test_<timestamp>/summary.txt
   ```

4. **View detailed logs**:
   ```bash
   less ./logs/test_<timestamp>/dlog-D1-smic_sonic1.log
   ```

---

## ✨ Test Features

### Modern Python Practices:
- ✅ Type hints with `from __future__ import annotations`
- ✅ Clear function docstrings with Args/Returns
- ✅ Descriptive variable names
- ✅ Proper exception handling
- ✅ Comprehensive logging

### SPyTest Integration:
- ✅ Proper use of `st.config()` and `st.show()`
- ✅ Test case ID tracking with `TC_IDS`
- ✅ Module fixtures for setup/teardown
- ✅ Pytest markers for categorization
- ✅ `st.report_tc_pass()` / `st.report_tc_fail()` / `st.report_fail()`

### Validation:
- ✅ IP address verification on both devices
- ✅ Interface status checks
- ✅ BGP configuration string matching
- ✅ Peer-group existence validation
- ✅ Neighbor assignment verification
- ✅ BGP session status checks

---

**All 5 test scripts are ready to run!** 🚀

**Total Lines of Code**: ~2500+ lines across 5 test files

**Total Test Cases**: 25 comprehensive test cases

**Documented Bugs**: 2 critical bugs with Jira report templates

**Framework**: SPyTest with Klish CLI integration

**Ready for CI/CD Integration**: All tests follow standard SPyTest patterns
