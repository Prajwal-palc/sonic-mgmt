# Port Breakout Test Suite - Complete File Index

All files created for Port Breakout test automation.

## Test Scripts (20 files)

### Main Test Scripts
1. `test_port_breakout_basic_modes.py` - PB-F-001 (All 11 breakout modes)
2. `test_port_breakout_stress_test.py` - PB-F-002 (Sequential transitions)
3. `test_port_breakout_multi_port.py` - PB-F-003 (Multi-port concurrent)

### Individual Test Scripts (PB-F-004 to PB-F-020)
4. `test_pb_f_004_revert_to_default.py` - Revert to default mode
5. `test_pb_f_005_ip_configuration.py` - IP address configuration
6. `test_pb_f_006_mtu_configuration.py` - MTU/jumbo frames
7. `test_pb_f_007_shutdown_operations.py` - Shutdown/no shutdown
8. `test_pb_f_008_multiple_speed_grades.py` - Speed grades
9. `test_pb_f_009_asymmetric_breakout.py` - Asymmetric breakout
10. `test_pb_f_010_vlan_configuration.py` - VLAN configuration
11. `test_pb_f_011_vlan_isolation.py` - VLAN isolation
12. `test_pb_f_012_portchannel_lag.py` - PortChannel/LAG
13. `test_pb_f_013_portchannel_member_flap.py` - PortChannel member flap
14. `test_pb_f_014_lldp_discovery.py` - LLDP discovery
15. `test_pb_f_015_config_persistence.py` - Config persistence
16. `test_pb_f_016_basic_connectivity.py` - Basic connectivity
17. `test_pb_f_017_traffic_stability.py` - Traffic stability
18. `test_pb_f_018_dependencies_check.py` - Dependencies check
19. `test_pb_f_019_complete_verification.py` - Complete verification
20. `test_pb_f_020_error_handling.py` - Error handling

## Documentation Files (5 files)

1. `QUICKSTART.md` - Get started in 5 minutes
2. `SETUP_GUIDE.md` - Complete installation guide
3. `README.md` - Test case descriptions and usage
4. `PORT_BREAKOUT_DELIVERY_SUMMARY.md` - Delivery summary
5. `FILE_INDEX.md` - This file

## Configuration Files (2 files)

### In spytest root directory:
1. `requirements_breakout.txt` - Python package requirements
2. `setup_breakout_tests.sh` - Automated setup script

## Usage Order

### First Time Setup:
1. Read `QUICKSTART.md` for 5-minute setup
2. Run `setup_breakout_tests.sh` for automated installation
3. Read `SETUP_GUIDE.md` for detailed instructions

### Running Tests:
1. Activate venv: `source spytest_venv/bin/activate`
2. Configure testbed (see `SETUP_GUIDE.md`)
3. Run individual tests or full suite
4. See `README.md` for all run commands

### Reference:
- `PORT_BREAKOUT_DELIVERY_SUMMARY.md` - Complete overview
- `README.md` - Test descriptions
- `SETUP_GUIDE.md` - Troubleshooting

## File Locations

```
/home/claudeuser/draksha/sonic-mgmt/spytest/
├── setup_breakout_tests.sh          (Automated setup script)
├── requirements_breakout.txt        (Package requirements)
├── spytest_venv/                    (Virtual environment - created by setup)
├── testbeds/
│   └── testbed_breakout.yaml       (Device configuration - you create this)
├── logs/                            (Test results - created automatically)
└── tests/system/ISCLI_Port_Breakout/
    ├── QUICKSTART.md                (5-minute start guide)
    ├── SETUP_GUIDE.md               (Complete setup)
    ├── README.md                    (Test descriptions)
    ├── PORT_BREAKOUT_DELIVERY_SUMMARY.md
    ├── FILE_INDEX.md                (This file)
    ├── test_port_breakout_basic_modes.py
    ├── test_port_breakout_stress_test.py
    ├── test_port_breakout_multi_port.py
    ├── test_pb_f_004_revert_to_default.py
    ├── test_pb_f_005_ip_configuration.py
    ├── test_pb_f_006_mtu_configuration.py
    ├── test_pb_f_007_shutdown_operations.py
    ├── test_pb_f_008_multiple_speed_grades.py
    ├── test_pb_f_009_asymmetric_breakout.py
    ├── test_pb_f_010_vlan_configuration.py
    ├── test_pb_f_011_vlan_isolation.py
    ├── test_pb_f_012_portchannel_lag.py
    ├── test_pb_f_013_portchannel_member_flap.py
    ├── test_pb_f_014_lldp_discovery.py
    ├── test_pb_f_015_config_persistence.py
    ├── test_pb_f_016_basic_connectivity.py
    ├── test_pb_f_017_traffic_stability.py
    ├── test_pb_f_018_dependencies_check.py
    ├── test_pb_f_019_complete_verification.py
    └── test_pb_f_020_error_handling.py
```

## Quick Commands

### Setup
```bash
cd /home/claudeuser/draksha/sonic-mgmt/spytest
./setup_breakout_tests.sh
```

### Activate Environment
```bash
source spytest_venv/bin/activate
```

### Run Tests
```bash
# Single test
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_breakout.yaml \
  tests/system/ISCLI_Port_Breakout/test_pb_f_004_revert_to_default.py

# All tests
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_breakout.yaml \
  tests/system/ISCLI_Port_Breakout/
```

---

**Total Files:** 27 (20 test scripts + 5 docs + 2 config files)

**Status:** ✅ ALL FILES CREATED

**Last Updated:** March 31, 2026
