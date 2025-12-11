# BGP Peer-Group Automated Test Scripts

This directory contains automated test scripts for BGP peer-group functionality validation.

## Test Scripts

### ✅ Completed

| Test File | Test ID | Description |
|-----------|---------|-------------|
| `test_bgp_pg01_peergroup_creation.py` | PG-01 | Basic peer-group creation and neighbor attachment |
| `test_bgp_pg02_attribute_inheritance.py` | PG-02 | Timer attribute inheritance from peer-group |

### 🔄 To Be Created

| Test File | Test ID | Description | Manual Validation |
|-----------|---------|-------------|-------------------|
| `test_bgp_pg03_attribute_override.py` | PG-03 | Override peer-group attributes on neighbor | ✅ Validated |
| `test_bgp_pg04_af_level_settings.py` | PG-04 | Address-family level settings | ✅ Validated |
| `test_bgp_pg05_routemap_inheritance.py` | PG-05 | Route-map policy inheritance | ✅ Validated |
| `test_bgp_pg06_password_inheritance.py` | PG-06 | MD5 password inheritance | ✅ Validated |

## Test Environment

- **Testbed**: `testbeds/testbed_2vs.yaml`
- **Topology**: 2-device iBGP (D1 ↔ D2 via Ethernet4)
- **Devices**:
  - D1 (smic_sonic1): 192.168.100.196
  - D2 (smic_sonic2): 192.168.100.247
- **Configuration**:
  - Interface: Ethernet4
  - D1 IP: 10.1.1.1/24
  - D2 IP: 10.1.1.2/24
  - BGP AS: 65001
  - Router IDs: 1.1.1.1, 2.2.2.2

## Running Tests

### Run Single Test
```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_pg01_peergroup_creation.py \
  --logs-path ./logs/pg01_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### Run All BGP PG Tests
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_pg*.py \
  --logs-path ./logs/bgp_peergroup_all_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

## Test Details

### PG-01: Peer-Group Creation (✅ Implemented)
**File**: `test_bgp_pg01_peergroup_creation.py`

**Test Flow**:
1. Configure IP addresses on Ethernet4
2. Configure BGP routers with router-ids
3. Create basic BGP neighbors
4. Verify initial BGP session
5. Create peer-group "1"
6. Attach neighbors to peer-group
7. Verify BGP session with peer-group
8. Verify peer-group membership

**Expected Result**:
- Peer-group created successfully
- Neighbors show "Member of peer-group 1"
- BGP session state: Established

---

### PG-02: Attribute Inheritance (✅ Implemented)
**File**: `test_bgp_pg02_attribute_inheritance.py`

**Test Flow**:
1. Configure IP and BGP basics
2. Create peer-group with timers (keepalive=30, holdtime=90)
3. Attach neighbors to peer-group
4. Verify BGP session establishment
5. Verify timer inheritance

**Expected Result**:
- Timers inherited: keepalive=30, holdtime=90
- BGP session state: Established

---

### PG-03: Attribute Override (Manual Validated, Script Pending)
**Manual Commands Summary**:
```
# DUT1 - Override timers to 10/30
peer-group 1
  timers 60 180
neighbor 10.1.1.2
  peer-group 1
  timers 10 30  # Override

# DUT2 - Inherit timers 60/180
peer-group 1
  timers 60 180
neighbor 10.1.1.1
  peer-group 1  # No override
```

**Expected Result**:
- D1 neighbor: timers 10/30 (overridden)
- D2 neighbor: timers 60/180 (inherited)
- BGP session established

---

### PG-04: AF-Level Settings (Manual Validated, Script Pending)
**Manual Commands Summary**:
```
peer-group 1
  remote-as 65001
  address-family ipv4 unicast
    activate
neighbor 10.1.1.X
  peer-group 1
  description "Peer with AF inheritance"
```

**Expected Result**:
- IPv4 unicast AF activated for neighbors
- BGP session established

---

### PG-05: Route-Map Inheritance (Manual Validated, Script Pending)
**Manual Commands Summary**:
```
route-map RM_IN permit 10
  set local-preference 200
route-map RM_OUT permit 10
  set metric 100

peer-group 1
  address-family ipv4 unicast
    route-map RM_IN in
    route-map RM_OUT out
```

**Expected Result**:
- Route-maps applied to neighbors via peer-group
- Routes show modified local-preference values

**Note**: `network` command had errors in manual test - may need to be in address-family context

---

### PG-06: Password Inheritance (Manual Validated, Script Pending)
**Manual Commands Summary**:
```
peer-group 1
  password bgp_secret_password
neighbor 10.1.1.X
  peer-group 1
```

**Expected Result**:
- BGP session established with MD5 authentication
- Password inherited from peer-group
- Failover test: password mismatch causes session failure

---

## Manual Validation Results

All 6 test cases have been manually validated:
- **PG-01**: ✅ PASSED - Peer-group created, neighbors attached
- **PG-02**: ✅ PASSED - Timers inherited (30/90)
- **PG-03**: ✅ PASSED - Timers overridden on D1 (10/30), inherited on D2 (60/180)
- **PG-04**: ✅ PASSED - AF-level settings inherited
- **PG-05**: ✅ PASSED - Route-maps inherited (RM_IN/RM_OUT)
- **PG-06**: ✅ PASSED - Password inherited, session established

## Documentation

Related documentation in `/bgp_peergroup_tests/`:
- `BGP_PEERGROUP_MANUAL_CONFIG.md` - Complete manual configuration guide
- `QUICK_CLI_COMMANDS.md` - Quick reference for PG-03, PG-04, PG-05
- `COPY_PASTE_COMMANDS.txt` - Copy-paste ready commands
- `PG05_CORRECTED_COMMANDS.txt` - Corrected PG-05 commands
- `PG05_STEP_BY_STEP.txt` - Step-by-step PG-05 guide
- `README.md` - Overview of all test cases

## Known Issues / Notes

1. **update-source** command is NOT supported in peer-group context
2. Route-maps must be applied at **peer-group AF level**, not global AF level
3. **network** command may need to be in address-family context (caused errors in PG-05 manual test)

## Next Steps

1. ✅ PG-01 and PG-02 scripts created
2. 🔄 Create PG-03 script (attribute override)
3. 🔄 Create PG-04 script (AF-level settings)
4. 🔄 Create PG-05 script (route-map inheritance)
5. 🔄 Create PG-06 script (password inheritance)
6. Test all scripts against live devices
7. Document results

## Support

For questions or issues:
- Check manual configuration guides in `/bgp_peergroup_tests/`
- Review manual validation results (all tests passed)
- Check device logs: `show logging | grep -i bgp`

---

**Last Updated**: December 11, 2025
**Status**: 2/6 scripts completed, 4/6 pending (all manually validated)
