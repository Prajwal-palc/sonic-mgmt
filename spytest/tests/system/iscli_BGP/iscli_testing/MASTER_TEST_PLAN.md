# SM IS-CLI Drop 1 - Testing Plan
**Project**: SONiC Management IS-CLI Development
**Drop**: Drop 1
**Target Date**: 26-Dec-2025
**Test Plan Created**: 29-Dec-2025

---

## Executive Summary

This document outlines the complete testing strategy for 4 in-progress IS-CLI features:
- **LLDP** (Link Layer Discovery Protocol)
- **Hostname** Configuration
- **NTP** (Network Time Protocol)
- **Clear ARP/ND** (Clear ARP and Neighbor Discovery)

---

## Testing Objectives

1. **Functional Validation**: Verify all CLI commands work as specified
2. **Error Handling**: Test invalid inputs, edge cases, and error messages
3. **Integration**: Ensure commands integrate properly with SONiC system
4. **Performance**: Verify commands execute within acceptable time limits
5. **Documentation**: Validate help text and command syntax

---

## Test Environment Requirements

### Hardware/Virtual Environment
- SONiC switch (physical or virtual)
- Minimum 2 network interfaces for LLDP testing
- Network connectivity for NTP testing
- Access to sudo/admin privileges

### Software Requirements
- SONiC OS (latest build with IS-CLI features)
- Python 3.x
- pytest framework
- Docker (for service validation)
- Redis CLI (for database verification)

### Network Requirements
- Internet access for NTP server testing
- LLDP-capable neighbor devices
- Management VRF configured

---

## Test Schedule

| Feature | Unit Testing | Integration Testing | Regression Testing | Target Completion |
|---------|-------------|---------------------|-------------------|-------------------|
| LLDP | 29-Dec | 30-Dec | 31-Dec | 31-Dec-2025 |
| Hostname | 29-Dec | 30-Dec | 31-Dec | 31-Dec-2025 |
| NTP | 29-Dec | 30-Dec | 31-Dec | 31-Dec-2025 |
| Clear ARP/ND | 29-Dec | 30-Dec | 31-Dec | 31-Dec-2025 |

---

## Test Categories

### 1. Functional Tests
- Command execution with valid parameters
- Expected output validation
- State changes verification

### 2. Negative Tests
- Invalid parameters
- Missing arguments
- Permission errors
- Service not running scenarios

### 3. Integration Tests
- Multi-command sequences
- Feature interaction testing
- Configuration persistence
- Service restart scenarios

### 4. Performance Tests
- Command execution time
- Resource utilization
- Concurrent command execution

---

## Success Criteria

### LLDP Feature
- [ ] All show commands return proper data
- [ ] Feature enable/disable works correctly
- [ ] JSON output is valid and properly formatted
- [ ] Verbose mode provides additional details
- [ ] Service status reflects configuration changes
- [ ] LLDP packets transmitted/received after enable

### Hostname Feature
- [ ] Hostname change command executes successfully
- [ ] New hostname persists after reboot
- [ ] Hostname appears in prompt
- [ ] Configuration saved to CONFIG_DB
- [ ] Invalid hostnames rejected with proper error

### NTP Feature
- [ ] NTP server/pool add/delete works
- [ ] Show NTP displays correct information
- [ ] VRF support functions properly
- [ ] Time synchronization occurs
- [ ] chrony service integrates correctly
- [ ] Configuration persists in CONFIG_DB

### Clear ARP/ND Feature
- [ ] sonic-clear arp removes ARP entries
- [ ] sonic-clear ndp removes IPv6 neighbors
- [ ] Specific interface clearing works
- [ ] All interfaces clearing works
- [ ] Entries repopulate after clearing
- [ ] No system instability after clear

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Service crashes during testing | High | Test in isolated environment first |
| Configuration loss | Medium | Backup config before testing |
| Network disruption | Medium | Use non-production testbed |
| Time sync issues with NTP | Low | Use multiple NTP sources |

---

## Deliverables

1. Test execution scripts (Python/pytest)
2. Test results documentation
3. Bug reports (if issues found)
4. Test coverage report
5. Regression test suite
6. User documentation validation

---

## Approval & Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Test Lead | | | |
| Developer | | | |
| QA Manager | | | |

---

## Notes

- All tests should be automated where possible
- Manual verification required for visual outputs
- Document any deviations from specification
- Track test execution time for performance baseline
