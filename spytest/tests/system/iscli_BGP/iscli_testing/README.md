# IS-CLI Drop 1 Testing Framework

Complete testing suite for SONiC Management IS-CLI features in Drop 1.

---

## 📋 Project Overview

**Project**: SM IS-CLI Development
**Phase**: Drop 1
**Target Date**: 26-Dec-2025
**Status**: Testing Phase

### Features Under Test

| Feature ID | Feature Name | Commands | Status |
|------------|-------------|----------|--------|
| SM_ISCLI_DROP1_FEATURE5 | LLDP | show lldp, feature control | Testing/Verification |
| SM_ISCLI_DROP1_FEATURE6 | Hostname | config hostname | Unit Testing |
| SM_ISCLI_DROP1_FEATURE7 | NTP | ntp add/del, show ntp | Testing/Verification |
| SM_ISCLI_DROP1_FEATURE8 | Clear ARP/ND | sonic-clear arp/ndp | Unit Testing |

---

## 🚀 Quick Start

### 1. Run All Tests
```bash
cd /home/hp/draksha/sonic-mgmt/spytest/tests/system/iscli_BGP/iscli_testing
./scripts/run_all_tests.sh
```

### 2. Run Individual Feature
```bash
# LLDP
pytest lldp/test_lldp_iscli.py -v

# Hostname
pytest hostname/test_hostname_iscli.py -v

# NTP
pytest ntp/test_ntp_iscli.py -v

# Clear ARP/ND
pytest clear_arp_nd/test_clear_arp_nd_iscli.py -v
```

### 3. Run Specific Test
```bash
pytest lldp/test_lldp_iscli.py::TestLLDPBasicCommands::test_lldp_table -v
```

---

## 📁 Directory Structure

```
iscli_testing/
│
├── README.md                        # This file - overview and quick start
├── MASTER_TEST_PLAN.md             # Comprehensive test strategy and plan
├── QUICK_START_GUIDE.md            # Step-by-step testing guide
│
├── lldp/                           # LLDP Feature Tests
│   └── test_lldp_iscli.py         # 40+ test cases
│
├── hostname/                       # Hostname Feature Tests
│   └── test_hostname_iscli.py     # 25+ test cases
│
├── ntp/                           # NTP Feature Tests
│   └── test_ntp_iscli.py          # 35+ test cases
│
├── clear_arp_nd/                  # Clear ARP/ND Feature Tests
│   └── test_clear_arp_nd_iscli.py # 30+ test cases
│
├── scripts/                       # Automation Scripts
│   └── run_all_tests.sh          # Master test execution script
│
└── results/                       # Test Results & Reports
    ├── TEST_RESULTS_TEMPLATE.md  # Template for documenting results
    └── test_run_*.log            # Generated test logs
```

---

## 🧪 Test Coverage

### LLDP (SM_ISCLI_DROP1_FEATURE5)
**40+ Test Cases** covering:
- ✓ Basic show commands (table, neighbors, verbose)
- ✓ Feature enable/disable functionality
- ✓ Docker container integration
- ✓ Help commands and documentation
- ✓ Data filtering and grep operations
- ✓ Configuration persistence
- ✓ Negative test cases

**Key Commands Tested:**
```bash
show lldp table
show lldp neighbors [--verbose] [INTERFACE]
sudo config feature state lldp {enabled|disabled}
docker ps | grep lldp
show runningconfiguration all | grep lldp
```

### Hostname (SM_ISCLI_DROP1_FEATURE6)
**25+ Test Cases** covering:
- ✓ Basic hostname change operation
- ✓ CONFIG_DB persistence
- ✓ Running configuration updates
- ✓ Invalid hostname rejection (spaces, special chars, too long)
- ✓ Edge cases (max length, single char, case sensitivity)
- ✓ Permission requirements

**Key Commands Tested:**
```bash
hostname
sudo config hostname <new_hostname>
redis-cli -n 4 HGET 'DEVICE_METADATA|localhost' hostname
show runningconfiguration all | grep hostname
```

### NTP (SM_ISCLI_DROP1_FEATURE7)
**35+ Test Cases** covering:
- ✓ Show NTP status
- ✓ Add/delete NTP servers and pools
- ✓ VRF management support
- ✓ Chrony daemon integration
- ✓ CONFIG_DB persistence
- ✓ Time synchronization verification
- ✓ Negative tests (invalid servers, duplicates)

**Key Commands Tested:**
```bash
show ntp
sudo config ntp add [--association-type {server|pool}] <address>
sudo config ntp del <address>
chronyc tracking
chronyc sources
sudo ip vrf exec mgmt ping <server>
redis-cli -n 4 KEYS NTP_SERVER*
```

### Clear ARP/ND (SM_ISCLI_DROP1_FEATURE8)
**30+ Test Cases** covering:
- ✓ Clear all ARP entries
- ✓ Clear all NDP entries
- ✓ Entry repopulation verification
- ✓ System stability after clear
- ✓ Multiple consecutive clears
- ✓ Performance testing
- ✓ Negative tests

**Key Commands Tested:**
```bash
show arp
sonic-clear arp
show ndp
sonic-clear ndp
ip neigh flush dev <interface>
```

---

## 📊 Test Execution Workflow

```
┌─────────────────────┐
│ Prerequisites Check │
│  - pytest installed │
│  - SONiC system     │
│  - sudo access      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Run Test Suite     │
│  - Manual or Auto   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Collect Results    │
│  - Logs             │
│  - XML reports      │
│  - Screenshots      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Document Results   │
│  - Fill template    │
│  - List issues      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Create JIRA Tickets│
│  - For bugs found   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Update Status      │
│  - Project tracker  │
│  - Team notification│
└─────────────────────┘
```

---

## 🔍 Understanding Test Results

### Pass Criteria
Each feature is considered **READY FOR PRODUCTION** if:
- ✓ 90%+ test pass rate
- ✓ All critical functionality works
- ✓ No P1 bugs
- ✓ Configuration persists correctly
- ✓ No system instability

### Failure Investigation
When tests fail:
1. Check the detailed log in `results/test_run_*.log`
2. Manually reproduce the failure
3. Check docker logs (if applicable)
4. Verify CONFIG_DB state
5. Document in test results template
6. Create JIRA ticket with details

---

## 📝 Documentation

| Document | Purpose | When to Use |
|----------|---------|-------------|
| README.md (this) | Overview and quick reference | First time setup |
| MASTER_TEST_PLAN.md | Detailed test strategy | Planning testing approach |
| QUICK_START_GUIDE.md | Step-by-step instructions | During test execution |
| TEST_RESULTS_TEMPLATE.md | Results documentation | After test completion |

---

## 🛠️ Prerequisites

### Software Requirements
```bash
# Python 3 and pip
python3 --version
pip3 --version

# pytest
pip3 install pytest

# Optional but recommended
pip3 install pytest-html  # For HTML reports
pip3 install pytest-xdist # For parallel execution
```

### System Requirements
- SONiC OS with IS-CLI features installed
- Sudo/admin access
- Network connectivity (for NTP tests)
- At least one network interface (for LLDP tests)
- Redis access (for CONFIG_DB verification)

### Verify Environment
```bash
# Check SONiC version
cat /etc/sonic/sonic_version.yml

# Check available CLIs
show --help
config --help
sonic-clear --help

# Verify Docker
docker ps

# Verify Redis
redis-cli ping
```

---

## 🐛 Troubleshooting

### Common Issues & Solutions

**Issue**: Tests fail with "command not found"
```bash
# Solution: Ensure SONiC environment is loaded
source /etc/bash_completion.d/sonic-utilities.bash
```

**Issue**: Permission errors during testing
```bash
# Solution: Run with sudo or add user to required groups
sudo usermod -aG docker $USER
# Then re-login
```

**Issue**: LLDP tests fail - container not running
```bash
# Solution: Enable LLDP feature
sudo config feature state lldp enabled
sleep 5
docker ps | grep lldp
```

**Issue**: NTP tests fail - no internet
```bash
# Solution: Use local NTP server or skip sync tests
pytest ntp/test_ntp_iscli.py -m "not slow"
```

**Issue**: Hostname changes don't persist
```bash
# Solution: Check CONFIG_DB and config save
redis-cli -n 4 HGETALL 'DEVICE_METADATA|localhost'
sudo config save -y
```

---

## 📈 Advanced Usage

### Generate HTML Report
```bash
pytest lldp/test_lldp_iscli.py --html=results/lldp_report.html --self-contained-html
```

### Run Tests in Parallel
```bash
pip3 install pytest-xdist
pytest -n auto  # Uses all CPU cores
```

### Run Only Failed Tests
```bash
pytest --lf  # Last failed
pytest --ff  # Failed first, then others
```

### Custom Markers
```bash
# Run only slow tests
pytest -m slow

# Skip slow tests
pytest -m "not slow"

# Run specific category
pytest -k "negative"  # Only negative tests
```

### Verbose Output with Logs
```bash
pytest -v --tb=long --capture=no
```

---

## 📅 Timeline & Milestones

| Date | Milestone | Deliverable |
|------|-----------|-------------|
| 29-Dec | Test scripts complete | All 4 feature test files |
| 30-Dec | Unit testing done | Test results documented |
| 31-Dec | Integration testing | All features verified |
| 01-Jan | Regression testing | Final sign-off |
| 02-Jan | Bug fixes (if needed) | Issues resolved |

---

## ✅ Checklist Before Release

- [ ] All test scripts execute without errors
- [ ] Test pass rate ≥ 90% for each feature
- [ ] All critical bugs fixed
- [ ] Test results documented
- [ ] JIRA tickets created for known issues
- [ ] Code committed to SM repository
- [ ] Documentation updated
- [ ] Team sign-off obtained

---

## 📞 Support & Contact

For issues or questions:
1. Check QUICK_START_GUIDE.md troubleshooting section
2. Review test logs in results/ directory
3. Consult MASTER_TEST_PLAN.md for detailed specs
4. Contact development team

---

## 📚 Additional Resources

- **SONiC Documentation**: https://github.com/sonic-net/SONiC/wiki
- **pytest Documentation**: https://docs.pytest.org/
- **Project JIRA**: [Link to your JIRA board]
- **SM Repository**: [Link to your git repo]

---

## 🔄 Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 29-Dec-2025 | Initial test framework | System |

---

**Last Updated**: 29-Dec-2025
**Maintained By**: QA Team
**Project**: SM IS-CLI Drop 1
