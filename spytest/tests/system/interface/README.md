# Interface IS-CLI Bugs Verification Suite

## Overview

This directory contains test cases and automation for verifying 13 interface-related bugs in SMCI SONiC IS-CLI implementation.

## Files

1. **test_plan_interface_bugs.md** - Comprehensive test plan with detailed test cases
2. **test_interface_iscli_bugs.py** - SPyTest automation script
3. **README.md** - This file

## Bug Coverage

| Bug ID | Description | Priority | Status |
|--------|-------------|----------|--------|
| SM_ISCLI_1 | Interface ordering in show run incorrect | High | Automated |
| SM_ISCLI_8 | Management static IP assignment fails | Critical | Automated |
| SM_ISCLI_12 | Management port missing from show ip interface | High | Automated |
| SM_ISCLI_22 | Management shown as eth0 instead of Management0 | Medium | Automated |
| SM_ISCLI_25 | Description without quotes breaks copy/paste | Medium | Automated |
| SM_ISCLI_31 | Management IP missing from show ip interfaces | High | Automated |
| SM_ISCLI_32 | Loopback allows non-/32 subnets | Medium | Automated |
| SM_ISCLI_33 | Show interface has incomplete information | High | Pending |
| SM_ISCLI_34 | Duplicate IP validation missing | Medium | Automated |
| SM_ISCLI_35 | Speed auto command missing | Low | Pending |
| SM_ISCLI_36 | Standalone link training missing | Medium | Pending |
| SM_ISCLI_59 | Multiple management/routing display issues | High | Pending |
| SM_ISCLI_61 | Show interface management syntax broken | Medium | Pending |
| SM_ISCLI_62 | IPv6 autoconfig enabled by default | Medium | Pending |

## Quick Start

### Running All Automated Tests

```bash
cd /home/hp_test/Athira/Palc-sonic/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed testbeds/testbed_vs_1node.yaml \
  tests/system/interface/test_interface_iscli_bugs.py \
  --logs-path ./logs/interface_bugs_$(date +%F_%H%M%S) \
  --log-level info --skip-init-config --ifname-type native
```

### Running Specific Bug Test

```bash
# Test bug SM_ISCLI_1 (interface ordering)
./bin/spytest --tryssh 1 \
  --testbed testbeds/testbed_vs_1node.yaml \
  -k "test_interface_001" \
  tests/system/interface/test_interface_iscli_bugs.py \
  --logs-path ./logs/bug_sm_iscli_1 \
  --log-level debug
```

### Running by Bug ID Marker

```bash
# Run all tests for a specific bug
./bin/spytest --tryssh 1 \
  --testbed testbeds/testbed_vs_1node.yaml \
  -m "bug_SM_ISCLI_12" \
  tests/system/interface/test_interface_iscli_bugs.py \
  --logs-path ./logs/bug_test
```

### Running by Test Class

```bash
# Run all show command tests
./bin/spytest --tryssh 1 \
  --testbed testbeds/testbed_vs_1node.yaml \
  tests/system/interface/test_interface_iscli_bugs.py::TestInterfaceShowCommands \
  --logs-path ./logs/show_cmd_tests
```

## Interactive Testing Workflow

Before automation, tests should be run interactively to verify behavior:

### Step 1: Review Test Plan
Read `test_plan_interface_bugs.md` for detailed test steps

### Step 2: Manual Test Execution
For each test case:
1. Log into device IS-CLI
2. Follow test steps in test plan
3. Document actual results
4. Capture screenshots/logs
5. Update test plan with findings

### Step 3: Run Automated Tests
Execute tests one by one to verify automation logic

### Step 4: Document Results
Update test plan with:
- Pass/Fail status
- Bug confirmation
- Logs location
- Screenshots

## Test Execution Best Practices

### Safety Considerations

⚠️ **WARNING**: Some tests modify management configuration
- TC-008 changes management IP address
- Always have console access or alternative connection
- Tests include safety measures, but use caution

### Recommended Test Order

1. **Read-only tests first** (safer):
   - TC-001: Show run ordering
   - TC-012: Show ip interface management
   - TC-022: Management naming
   - TC-031: Show ip interfaces

2. **Configuration tests** (minimal risk):
   - TC-025: Description quotes
   - TC-032: Loopback validation
   - TC-034: Duplicate IP validation

3. **High-risk tests last** (with backup access):
   - TC-008: Management static IP

### Test Isolation

Each test is designed to:
- Save state before modifications
- Restore state after completion
- Clean up temporary configurations
- Handle errors gracefully

## Test Results

Results are saved in `--logs-path` directory:
- `results.html` - HTML test report
- `summary.txt` - Quick summary
- `dlog-D1-*.log` - Device command logs
- `module_test_interface_iscli_bugs.log` - Module logs

## Development Workflow

### Adding New Tests

1. Add test case to test plan document
2. Implement test function in Python script
3. Add appropriate markers:
   ```python
   @pytest.mark.interface_bugs
   @pytest.mark.bug_SM_ISCLI_XX
   def test_interface_0XX_description():
       ...
   ```
4. Test interactively
5. Update documentation

### Test Function Template

```python
@pytest.mark.interface_bugs
@pytest.mark.bug_SM_ISCLI_XX
def test_interface_0XX_test_name(self):
    """
    TC-0XX: Test description
    Bug ID: SM_ISCLI_XX
    Description: Detailed bug description
    """
    st.log("\n" + "="*80)
    st.log(f"TEST: {BUG_IDS.TC_0XX} - Test Name")
    st.log("="*80)

    dut = data.dut
    cli_type = data.cli_type

    st.banner("STEP 1: Step description")
    # Test logic here

    st.banner("STEP 2: Verification")
    # Verification logic

    # Report result
    if success:
        st.report_pass("test_case_passed")
    else:
        st.report_fail("msg", f"Bug {BUG_IDS.TC_0XX} confirmed")
```

## Known Limitations

1. **Virtual SONiC Testing**:
   - Some hardware-specific tests may not work on vSONiC
   - TC-033 (detailed interface info) requires physical connections
   - TC-036 (link training) requires long DAC cables

2. **Management IP Tests**:
   - TC-008 can disrupt SSH connection
   - Requires console access for safety
   - May timeout on connection loss

3. **Timing Dependencies**:
   - Some configurations need time to apply
   - Wait times included in tests
   - May need adjustment for different platforms

## Troubleshooting

### Test Hangs or Timeouts
- Check device connectivity
- Verify IS-CLI is accessible
- Check for pagination issues
- Increase timeout values

### Connection Lost During Test
- Likely TC-008 (management IP test)
- Access device via console
- Check management IP configuration
- Restore original IP if needed

### Test Fails Unexpectedly
1. Check logs in `--logs-path` directory
2. Review device command log (dlog file)
3. Verify device state
4. Check for recent software changes

### Permission Issues
- Verify SSH key authentication
- Check user permissions
- Confirm device access credentials

## CI/CD Integration

### Jenkins Pipeline Example

```groovy
stage('Interface Bug Tests') {
    steps {
        sh '''
            cd /home/hp_test/Athira/Palc-sonic/sonic-mgmt/spytest
            ./bin/spytest --tryssh 1 \
              --testbed testbeds/testbed_vs_1node.yaml \
              tests/system/interface/test_interface_iscli_bugs.py \
              --logs-path ./logs/interface_bugs_${BUILD_NUMBER} \
              --log-level info
        '''
    }
    post {
        always {
            publishHTML([
                reportDir: 'logs/interface_bugs_${BUILD_NUMBER}',
                reportFiles: 'results.html',
                reportName: 'Interface Bug Test Results'
            ])
        }
    }
}
```

## Reporting Issues

When reporting test failures:
1. Include bug ID (SM_ISCLI_XX)
2. Attach test log files
3. Include device software version
4. Note test environment (HW/Virtual)
5. Provide steps to reproduce

## Future Enhancements

- [ ] Complete remaining test implementations (TC-033, 035, 036, 059, 061, 062)
- [ ] Add TextFSM templates for output parsing
- [ ] Implement parameterized tests for multiple interfaces
- [ ] Add performance benchmarking
- [ ] Create HTML test report customization
- [ ] Add screenshot capture for failures
- [ ] Implement automated bug report generation

## Support

For questions or issues:
- Review test plan documentation
- Check SPyTest framework documentation in `Doc/` directory
- Contact: Athira (athira@palcnetworks.com)

## License

Copyright (C) 2026, PalC Networks
