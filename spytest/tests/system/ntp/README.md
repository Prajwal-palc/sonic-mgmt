# NTP IS-CLI Test Suite - Setup and Execution Guide

## Overview

This directory contains the NTP (Network Time Protocol) test automation suite for SONiC IS-CLI (Klish). The test suite validates NTP configuration, authentication, server management, and show commands. It includes comprehensive coverage for SSE-T8196 known issues and limitations.

## Test Files

- **`test_ntp_iscli.py`** - Main test suite with 33 supported test cases (includes Issue SSE-T8196 validations)
- **`test_ntp_iscli_unsupported.py`** - 9 unsupported test cases documenting SSE-T8196 limitations
- **`vars_ntp_iscli_local.yaml`** - Configuration for testing with local NTP server
- **`setup_ntp_server.sh`** - Script to set up local NTP server
- **`verify_ntp_server.sh`** - Script to verify NTP server is running correctly
- **`fix_ntp_server.sh`** - Script to fix common NTP server issues

## Prerequisites

### System Requirements
- Linux system with sudo access
- Python 3.8+
- SONiC virtual switch or hardware device
- Network connectivity between test host and DUT

### Dependencies
- SPyTest framework installed
- chrony (NTP daemon) - will be installed by setup script
- SSH access to DUT configured

## Quick Start

### 1. Setup Local NTP Server

Navigate to the NTP test directory:

```bash
cd /home/hp/Athira/sonic-mgmt/spytest/tests/system/ntp
```

Run the setup script with sudo:

```bash
sudo ./setup_ntp_server.sh
```

This script will:
- Install chrony NTP daemon
- Configure chrony as a local NTP server
- Allow NTP traffic through firewall
- Start and enable the NTP service

### 2. Verify NTP Server Setup

After setup, verify the NTP server is running correctly:

```bash
./verify_ntp_server.sh
```

Expected output should show:
- Chrony service is active and running
- Local NTP server listening on port 123
- System clock is synchronized
- NTP sources are configured

### 3. Fix NTP Server Issues (If Needed)

If verification fails or NTP server has issues:

```bash
sudo ./fix_ntp_server.sh
```

This script will:
- Restart the chrony service
- Check and fix firewall rules
- Verify NTP port availability
- Display service status and logs

## Running Tests

### Set Working Directory

Ensure you're in the spytest root directory:

```bash
cd /home/hp/Athira/sonic-mgmt/spytest
```

### Run Main Test Suite (32 Supported Tests)

Execute all 32 supported test cases:

```bash
export NTP_ISCLI_VAR_FILE=/home/hp/Athira/sonic-mgmt/spytest/tests/system/ntp/vars_ntp_iscli_local.yaml

./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_vs_1node_ntp.yaml \
    system/ntp/test_ntp_iscli.py \
    --logs-path ./logs/$(date +%d-%m-%Y)/test_ntp_iscli_$(date +%F_%H%M%S) \
    --log-level info --skip-init-config --ifname-type native
```

### Run Specific Test Case

To run a single test:

```bash
export NTP_ISCLI_VAR_FILE=/home/hp/Athira/sonic-mgmt/spytest/tests/system/ntp/vars_ntp_iscli_local.yaml

./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_vs_1node_ntp.yaml \
    system/ntp/test_ntp_iscli.py::TestNTPGlobalConfiguration::test_ntp_001_enable_ntp \
    --logs-path ./logs/$(date +%d-%m-%Y)/test_single_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native
```

### Run Unsupported Tests (For Future Reference)

To run the 6 unsupported test cases:

```bash
export NTP_ISCLI_VAR_FILE=/home/hp/Athira/sonic-mgmt/spytest/tests/system/ntp/vars_ntp_iscli_local.yaml

./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_vs_1node_ntp.yaml \
    system/ntp/test_ntp_iscli_unsupported.py \
    --logs-path ./logs/$(date +%d-%m-%Y)/test_ntp_unsupported_$(date +%F_%H%M%S) \
    --log-level info --skip-init-config --ifname-type native
```

## Test Suite Structure

### Main Test Suite (test_ntp_iscli.py)

**33 Supported Test Cases:**

1. **Global Configuration** (3 tests)
   - test_ntp_001_enable_ntp - Enable NTP service
   - test_ntp_002_disable_ntp - Disable NTP service
   - test_ntp_003_reenable_ntp - Re-enable NTP service

2. **Authentication** (5 tests)
   - test_ntp_003_enable_auth - Enable NTP authentication
   - test_ntp_004_disable_auth - Disable NTP authentication
   - test_ntp_005_auth_md5 - Test MD5 authentication
   - test_ntp_006_auth_sha1 - Test SHA1 authentication
   - test_ntp_007_auth_sha256 - Test SHA256 authentication

3. **Authentication Keys** (8 tests)
   - test_ntp_008_add_auth_key - Add authentication key
   - test_ntp_009_update_auth_key - Update authentication key
   - test_ntp_010_delete_auth_key - Delete authentication key
   - test_ntp_011_auth_key_md5 - MD5 key validation
   - test_ntp_012_auth_key_sha1 - SHA1 key validation
   - test_ntp_013_auth_key_sha256 - SHA256 key validation
   - test_ntp_014_auth_key_sha384 - SHA384 key validation
   - test_ntp_015_auth_key_sha512 - SHA512 key validation

4. **Trusted Keys** (4 tests)
   - test_ntp_016_add_trusted_key - Add trusted key
   - test_ntp_017_delete_trusted_key - Delete trusted key
   - test_ntp_018_multiple_trusted_keys - Multiple trusted keys
   - test_ntp_019_trusted_key_range - Trusted key range validation

5. **Server Configuration** (7 tests)
   - test_ntp_020_basic_server_ip - Configure server with IP
   - test_ntp_021_server_hostname - Configure server with hostname
   - test_ntp_026_server_iburst - Configure server with iburst
   - test_ntp_029_server_max_limit - Test max server limit (10)
   - test_ntp_030_delete_server - Delete NTP server
   - test_ntp_031_server_prefer - Configure preferred server
   - test_ntp_032_multiple_servers - Multiple server configuration

6. **Source Interface** (2 tests)
   - test_ntp_033_source_interface - Configure source interface
   - test_ntp_034_delete_source_interface - Delete source interface

7. **VRF Configuration** (1 test)
   - test_ntp_038_delete_vrf - Delete NTP VRF

8. **Show Commands** (4 tests)
   - test_ntp_039_show_ntp_global - Verify show ntp global (validates Issue SSE-T8196 #5)
   - test_ntp_040_show_ntp_server - Verify show ntp server
   - test_ntp_041_verify_running_config_display - Verify running-config display (validates Issue SSE-T8196 #6)
   - test_ntp_046_time_drift_correction - Validate NTP time drift correction

### Unsupported Tests (test_ntp_iscli_unsupported.py)

**9 Unsupported Test Cases (SSE-T8196 Issue Documentation):**

1. **test_ntp_025_server_association_server**
   - Reason: Association type attribute not in REST API response

2. **test_ntp_027_server_association_pool**
   - Reason: Pool association type not supported in klish CLI

3. **test_ntp_028_server_all_options**
   - Reason: Some options (iburst, association_type, key, prefer) not fully supported

4. **test_ntp_034_source_interface_vlan** ⭐ NEW
   - Issue: SSE-T8196 #2 - Can't set NTP "source-interface VLAN"
   - Tests: VLAN interfaces cannot be configured as source-interface

5. **test_ntp_036_config_vrf_without_mgmt**
   - Reason: Management VRF not defined in test configuration

6. **test_ntp_037_config_vrf_with_mgmt**
   - Reason: Management VRF not defined in test configuration

7. **test_ntp_041_show_ntp_associations**
   - Issue: SSE-T8196 #7 - Show ntp associations missing fields
   - Reason: NTP associations data not available - feature not fully implemented

8. **test_ntp_042_source_interface_management** ⭐ NEW
   - Issue: SSE-T8196 #4 - Cannot set Management0 as NTP source-interface
   - Tests: Management0 interface cannot be configured as source-interface

9. **test_ntp_043_multiple_source_interfaces** ⭐ NEW
   - Issue: SSE-T8196 #1 - Does not support multiple NTP source-interfaces
   - Tests: Only one source-interface allowed; individual deletion not supported

10. **test_ntp_044_enable_ntp_server_mode** ⭐ NEW
    - Issue: SSE-T8196 #3 - Switch does not support acting as an NTP server
    - Tests: SONiC can only act as NTP client, not NTP server

## Expected Test Results

### Main Test Suite (33 tests)
```
Total Tests: 33
PASSED: 33 (100%)
FAILED: 0 (0%)
UNSUPPORTED: 0 (0%)
SCRIPT ERRORS: 0 (0%)
Pass Rate: 100%
```

Note: Tests test_ntp_039 and test_ntp_041 include validation for SSE-T8196 issues #5 and #6.
They will PASS but log warnings documenting the known limitations.

### Unsupported Tests (10 tests)
```
Total Tests: 10
UNSUPPORTED: 10 (100%)
```

These tests document SSE-T8196 known limitations and will report as UNSUPPORTED.

## Configuration Files

### vars_ntp_iscli_local.yaml

Key configuration parameters:
- **local_ntp_server**: IP address of local NTP server (default: 192.168.100.175)
- **cli_type**: CLI type to use (default: klish)
- **min_topology**: Minimum topology required (default: D1:1 - single node)

Example structure:
```yaml
defaults:
  cli_type: klish
  local_ntp_server: 192.168.100.175
  cleanup: true
  verify_timeout: 30

testcases:
  # Test case specific configurations
  ...

ntp_servers:
  primary_server:
    address: 192.168.100.175
    iburst: true
  ...
```

## Testbed Configuration

### testbed_vs_1node_ntp.yaml

The testbed file should define:
- Device connection details (IP, credentials)
- Device type (sonic)
- Access protocol (ssh)
- Topology (single node for NTP tests)

Example:
```yaml
version: 2.0
devices:
  D1:
    device_type: sonic
    access:
      protocol: ssh
      ip: 192.168.100.100
      port: 22
    credentials:
      username: admin
      password: YourPaSsWoRd
```

## Logs and Results

### Log Directory Structure

Logs are stored in: `./logs/<date>/test_ntp_*_<timestamp>/`

Key log files:
- **`results.html`** - HTML test report with detailed results
- **`consolidated_report.html`** - Aggregated test results
- **`summary.txt`** - Quick text summary
- **`dlog-D1-<device>.log`** - Per-device command/output logs
- **`module_<modulename>.log`** - Per-test-module logs

### Viewing Results

1. **Quick Summary**:
   ```bash
   cat ./logs/<date>/test_ntp_*/summary.txt
   ```

2. **HTML Report**:
   Open `results.html` in a web browser for detailed results with pass/fail status

3. **Search for Failures**:
   ```bash
   grep -r "Report(Fail)" ./logs/<date>/test_ntp_*/
   ```

## Troubleshooting

### Common Issues

1. **NTP Server Not Running**
   ```bash
   sudo systemctl status chrony
   sudo systemctl start chrony
   ```

2. **Firewall Blocking NTP**
   ```bash
   sudo ufw allow 123/udp
   sudo ufw status
   ```

3. **Time Synchronization Issues**
   ```bash
   chronyc tracking
   chronyc sources
   ```

4. **Test Variable File Not Found**
   - Ensure `NTP_ISCLI_VAR_FILE` uses absolute path
   - Verify file exists: `ls -la $NTP_ISCLI_VAR_FILE`

5. **Device Connection Failures**
   - Check testbed file has correct device IP and credentials
   - Verify SSH connectivity: `ssh admin@<device-ip>`
   - Check device is reachable: `ping <device-ip>`

### Debug Mode

For detailed debugging, use `--log-level debug`:

```bash
./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_vs_1node_ntp.yaml \
    system/ntp/test_ntp_iscli.py \
    --logs-path ./logs/debug_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native
```

## Command-Line Options

### Essential Options

- `--tryssh 1` - Enable SSH connection attempts
- `--testbed <file>` - Specify testbed YAML file
- `--logs-path <path>` - Output directory for logs/results
- `--log-level <level>` - Logging level (info, debug, warning, error)
- `--skip-init-config` - Skip initial device configuration
- `--ifname-type native` - Use native interface names (Ethernet0, Ethernet4)

### Advanced Options

- `-n <num>` - Number of parallel workers
- `--file-mode` - Execute tests in file mode
- `-m <marker>` - Run tests with specific pytest marker
- `--test-suite <suite>` - Run predefined test suite

## Development and Maintenance

### Adding New Test Cases

1. Add test method to appropriate class in `test_ntp_iscli.py`
2. Follow naming convention: `test_ntp_<number>_<description>`
3. Include comprehensive docstring
4. Add test-specific configuration to `vars_ntp_iscli_local.yaml` if needed

### Moving Tests Back from Unsupported

When a feature is implemented:
1. Copy test method from `test_ntp_iscli_unsupported.py`
2. Paste into appropriate class in `test_ntp_iscli.py`
3. Remove unsupported documentation/comments
4. Update test logic if needed
5. Remove from unsupported file

### Linting

Run code quality checks:

```bash
cd /home/hp/Athira/sonic-mgmt/spytest
./bin/lint.sh tests/system/ntp/test_ntp_iscli.py
```

## Support and Contact

For issues or questions:
- Check logs in `./logs/` directory
- Review test output for specific error messages
- Verify NTP server setup is correct
- Ensure testbed configuration is accurate

## References

- [SPyTest Documentation](https://github.com/sonic-net/sonic-mgmt/tree/master/spytest)
- [SONiC NTP Configuration](https://github.com/sonic-net/SONiC/wiki/Configuration)
- [Chrony Documentation](https://chrony.tuxfamily.org/documentation.html)

---

**Last Updated**: January 23, 2026
**Test Suite Version**: 1.1
**Total Tests**: 43 (33 supported + 10 unsupported)
**SSE-T8196 Issue Coverage**: All 7 issues tested or documented
