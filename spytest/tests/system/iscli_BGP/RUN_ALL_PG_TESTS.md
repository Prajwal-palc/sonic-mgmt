# BGP Peer-Group Tests - Complete Suite (PG-11 to PG-15)

All test scripts are now available! Here's the complete list:

## ✅ Test Files Created

### 1. test_bgp_pg11_scale.py - PG-11: Peer-Group Scale (50 Neighbors)
### 2. test_bgp_pg12_rr_client.py - PG-12: Route-Reflector Client Defaults
### 3. test_bgp_pg13_different_remote_as.py - PG-13: Different remote-as Per Subset
### 4. test_bgp_pg14_evpn_inheritance.py - PG-14: EVPN Specific Config Inheritance
### 5. test_bgp_pg15_removal_effect.py - PG-15: Peer-Group Removal Effect

---

## Quick Run Commands

### Run Individual Tests:

```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

# PG-11: Scale Test (50 neighbors)
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_pg11_scale.py \
  --logs-path ./logs/bgp_pg11_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

# PG-12: Route-Reflector Client
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_pg12_rr_client.py \
  --logs-path ./logs/bgp_pg12_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

# PG-13: Different remote-as
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_pg13_different_remote_as.py \
  --logs-path ./logs/bgp_pg13_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

# PG-14: EVPN Inheritance
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_pg14_evpn_inheritance.py \
  --logs-path ./logs/bgp_pg14_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

# PG-15: Peer-Group Removal
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_pg15_removal_effect.py \
  --logs-path ./logs/bgp_pg15_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

---

## Run ALL Tests Together:

```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_pg11_scale.py \
  tests/system/iscli_BGP/test_bgp_pg12_rr_client.py \
  tests/system/iscli_BGP/test_bgp_pg13_different_remote_as.py \
  tests/system/iscli_BGP/test_bgp_pg14_evpn_inheritance.py \
  tests/system/iscli_BGP/test_bgp_pg15_removal_effect.py \
  --logs-path ./logs/bgp_peergroup_all_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

---

## Test Summary

| Test ID | File | Description | Test Cases |
|---------|------|-------------|------------|
| **PG-11** | test_bgp_pg11_scale.py | Mass-assign 50 neighbors | 3 test cases |
| **PG-12** | test_bgp_pg12_rr_client.py | Route-reflector client defaults | 4 test cases |
| **PG-13** | test_bgp_pg13_different_remote_as.py | Different remote-as per subset | 4 test cases |
| **PG-14** | test_bgp_pg14_evpn_inheritance.py | EVPN config inheritance | 4 test cases |
| **PG-15** | test_bgp_pg15_removal_effect.py | Peer-group removal effect | 4 test cases |

**Total**: 5 test files, 19 test cases

---

## Test Details

### PG-11: Peer-Group Scale Test
**Test Cases**:
- TC-BGP-PG-11-001: Peer-group creation
- TC-BGP-PG-11-002: Mass neighbor assignment (50 neighbors)
- TC-BGP-PG-11-003: Configuration inheritance verification

**What it validates**:
- Peer-group can handle large number of neighbors (50)
- Configuration inheritance across all members
- BGP process stability with scale

---

### PG-12: Route-Reflector Client Defaults
**Test Cases**:
- TC-BGP-PG-12-001: RR client peer-group creation
- TC-BGP-PG-12-002: Neighbor configuration
- TC-BGP-PG-12-003: Route-reflector client verification
- TC-BGP-PG-12-004: BGP session check

**What it validates**:
- route-reflector-client configured in peer-group
- Setting inherited by all peer-group members
- iBGP route-reflector functionality

---

### PG-13: Different remote-as Per Subset
**Test Cases**:
- TC-BGP-PG-13-001: Peer-group template creation (no remote-as)
- TC-BGP-PG-13-002: Subset assignment with different AS
- TC-BGP-PG-13-003: Configuration inheritance verification
- TC-BGP-PG-13-004: BGP session check

**What it validates**:
- Peer-group as template (no remote-as in peer-group)
- Different neighbors with different remote-as values
- All inherit peer-group settings except remote-as
- eBGP session establishment (AS 65001 <-> AS 65002)

---

### PG-14: EVPN Specific Config Inheritance
**Test Cases**:
- TC-BGP-PG-14-001: EVPN peer-group creation
- TC-BGP-PG-14-002: EVPN neighbor configuration
- TC-BGP-PG-14-003: EVPN configuration inheritance
- TC-BGP-PG-14-004: EVPN BGP session check

**What it validates**:
- L2VPN EVPN address-family support
- EVPN-specific settings (route-reflector-client, send-community extended)
- Overlay (loopback) and underlay (Ethernet4) configuration
- EVPN session establishment

**Note**: Includes pytest.skip if L2VPN EVPN not supported

---

### PG-15: Peer-Group Removal Effect
**Test Cases**:
- TC-BGP-PG-15-001: Peer-group setup with neighbors
- TC-BGP-PG-15-002: Verify configuration BEFORE deletion
- TC-BGP-PG-15-003: Peer-group deletion attempt (protection model)
- TC-BGP-PG-15-004: Verify configuration AFTER deletion

**What it validates**:
- Protection model: peer-group cannot be deleted while in use
- Proper deletion sequence: remove from neighbors → delete peer-group
- Neighbors lose inherited settings after peer-group deletion
- BGP process remains stable after peer-group removal

---

## Testbed Requirements

**File**: `/home/adminuser/draksha/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`

**Devices**:
- DUT1: 192.168.100.203 (smic_sonic1) - admin/YourPaSsWoRd
- DUT2: 192.168.100.196 (smic_sonic2) - admin/YourPaSsWoRd

**Connection**: Ethernet4 <--> Ethernet4

**Topology**:
```
DUT1 (192.168.100.203)  <--> DUT2 (192.168.100.196)
Router-ID: 1.1.1.1           Router-ID: 2.2.2.2
AS: 65001                    AS: 65001 (or 65002 for PG-13)
Ethernet4: 10.1.1.1/24       Ethernet4: 10.1.1.2/24
Loopback0: 1.1.1.1/32        Loopback0: 2.2.2.2/32 (for PG-14)
```

---

## Results Location

After test execution:
```
/home/adminuser/draksha/sonic-mgmt/spytest/logs/<test_name>_<timestamp>/
├── dashboard.html              # Test dashboard
├── summary.txt                 # Quick summary
├── results.html                # Detailed results
├── consolidated_report.html    # Aggregated report
├── dlog-D1-smic_sonic1.log    # Device 1 logs
├── dlog-D2-smic_sonic2.log    # Device 2 logs
└── module_test_bgp_pgXX.log   # Module logs
```

---

## Test Markers

All tests are marked for easy filtering:

```bash
# Run only scale tests
./bin/spytest --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/ -m scale

# Run only EVPN tests
./bin/spytest --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/ -m evpn

# Run only route-reflector tests
./bin/spytest --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/ -m route_reflector

# Run only removal tests
./bin/spytest --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/ -m removal
```

---

## Common Issues & Solutions

### Issue 1: L2VPN EVPN Not Supported (PG-14)
**Solution**: Test will automatically skip with message:
```
SKIPPED [1] L2VPN EVPN not supported in this SONiC build
```

### Issue 2: Peer-Group Deletion Fails (PG-15)
**Expected**: This is the protection model behavior
**Solution**: Remove peer-group from neighbors first, then delete

### Issue 3: BGP Session Not Establishing
**Check**:
1. IP connectivity: `ping 10.1.1.2`
2. Interface status: `show interface status Ethernet4`
3. BGP configuration: `show running-configuration bgp`
4. BGP summary: `show bgp ipv4 unicast summary`

### Issue 4: Timers Not Showing in Config
**Info**: Some SONiC versions don't display all inherited settings explicitly
**Solution**: Test validates using show commands and presence checks

---

## Validation Commands Used

All tests include comprehensive validation using:

```bash
# Interface validation
show ip interface Ethernet4
show interface status Ethernet4

# BGP configuration validation
show running-configuration bgp
show bgp peer-group
show bgp peer-group <NAME>

# BGP session validation
show bgp summary
show bgp ipv4 unicast summary
show bgp ipv4 unicast neighbors <IP>

# EVPN validation (PG-14)
show bgp l2vpn evpn summary
show bgp l2vpn evpn neighbors <IP>
```

---

## Success Criteria

### All Tests PASS if:
1. ✅ Interfaces configured with correct IP addresses
2. ✅ BGP routers configured with router-ID
3. ✅ Peer-groups created with specific settings
4. ✅ Neighbors assigned to peer-groups
5. ✅ Configuration inheritance verified
6. ✅ BGP sessions establish (or appropriate state)
7. ✅ show commands return expected output
8. ✅ Cleanup completes successfully

---

## Quick Start

```bash
# Navigate to SPyTest directory
cd /home/adminuser/draksha/sonic-mgmt/spytest

# Run a single test (e.g., PG-11)
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_pg11_scale.py \
  --logs-path ./logs/bgp_pg11_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

# Check results
cat ./logs/bgp_pg11_<timestamp>/summary.txt
```

---

## All Tests Are Ready to Run! 🚀

**Created**: 5 automated test scripts
**Test Cases**: 19 total
**Framework**: SPyTest with BGP/IP APIs
**Validation**: Comprehensive show command checks
**Topology**: 2-device (Ethernet4 connection)

Execute tests and check the logs directory for results!
