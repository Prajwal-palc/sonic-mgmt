# Static Route CLI - Pytest Test Framework

## 🎯 Overview

This is a comprehensive pytest-based testing framework for SONiC Static Route CLI commands. The framework provides automated testing with professional reporting, detailed logging, and database snapshot capabilities.

**Framework Version**: 1.0
**Last Updated**: 2025-11-11

---

## ✨ Features

- ✅ **Modular Architecture**: Clean, extensible, and maintainable code structure
- ✅ **Configurable Parameters**: Host IP, Port, Username, Password all configurable via YAML
- ✅ **Multi-Device Support**: Test on multiple devices in parallel
- ✅ **Comprehensive Logging**: CLI commands, responses, and DB snapshots for each test
- ✅ **Professional Reports**: Multiple HTML and Markdown reports
- ✅ **Pytest Integration**: Full pytest support with markers, fixtures, and plugins
- ✅ **Database Snapshots**: Before/after snapshots for every test
- ✅ **Error Debugging**: Detailed error information for failed tests

---

## 📁 Directory Structure

```
/home/adminuser/draksha/cli/route_static/
├── config/
│   └── config.yaml                  # Main configuration file
├── helpers/
│   ├── __init__.py                  # Package init
│   ├── config_loader.py             # Configuration loader
│   ├── ssh_client.py                # SSH client for CLI execution
│   ├── db_helper.py                 # Database snapshot helper
│   └── logger.py                    # Logging utilities
├── scripts/
│   ├── conftest.py                  # Pytest fixtures and configuration
│   ├── test_route_static.py        # Main test cases
│   └── generate_reports.py         # Report generation module
├── logs/
│   ├── cli_output/                  # CLI command execution logs
│   ├── db_snapshots/                # Database snapshots (JSON)
│   └── pytest_execution.log         # Main pytest log
├── results/
│   ├── pytest_report_final.html             # Pytest HTML report
│   ├── route_static_cli_test_report.html    # Comprehensive CLI test report
│   ├── route_static_cli_summary.html        # Executive summary (HTML)
│   ├── route_static_summary.md              # Test summary (Markdown)
│   ├── route_static_execution_summary.md    # Execution details (Markdown)
│   └── test_results.json                    # JSON test results
├── requirements.txt                 # Python dependencies
├── pytest.ini                       # Pytest configuration
├── run_tests.sh                     # Automated test execution script
└── README.md                        # This file
```

---

## 🚀 Quick Start

### 1. Installation

```bash
cd /home/adminuser/draksha/cli/route_static

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configuration

Edit `config/config.yaml` to configure devices and test parameters:

```yaml
devices:
  - name: VS-1
    host: 192.168.100.97
    port: 22
    username: admin
    password: YourPaSsWoRd
    enabled: true
```

### 3. Run Tests

```bash
# Method 1: Using automated script (recommended)
./run_tests.sh

# Method 2: Direct pytest execution
pytest scripts/test_route_static.py -v
```

### 4. View Results

```bash
# View HTML reports
firefox results/pytest_report_final.html &
firefox results/route_static_cli_test_report.html &

# View Markdown reports
cat results/route_static_summary.md
```

---

## 📊 Generated Reports

### 1. pytest_report_final.html
**Pytest-native HTML report** with:
- Test execution summary
- Detailed test results
- Error stack traces
- Captured logs
- Test metadata

### 2. route_static_cli_test_report.html
**Comprehensive CLI test report** featuring:
- Executive dashboard with statistics
- Visual progress indicators
- Test results by category
- Device-wise results
- CLI commands tested
- Professional formatting

### 3. route_static_cli_summary.html
**Executive summary report** with:
- High-level statistics
- Pass/fail overview
- Test coverage summary

### 4. route_static_summary.md
**Markdown summary** including:
- Test statistics table
- Commands tested
- Results by device
- Overall conclusion

### 5. route_static_execution_summary.md
**Detailed execution summary** with:
- Test environment details
- Execution metrics
- Detailed test results by category
- Test artifacts locations

### 6. test_results.json
**Machine-readable JSON** containing:
- Complete test results
- Test metadata
- Timing information
- Error details

---

## 🧪 Test Coverage

### IPv4 Static Routes
- ✅ Configure route with next-hop IP
- ✅ Configure blackhole route
- ✅ Configure multiple routes
- ✅ Delete route with next-hop
- ✅ Delete blackhole route

### IPv6 Static Routes
- ✅ Configure route with next-hop IPv6
- ✅ Configure blackhole route
- ✅ Configure multiple routes
- ✅ Delete route with next-hop
- ✅ Delete blackhole route

### Route Verification
- ✅ Show IPv4 static routes
- ✅ Show IPv6 static routes
- ✅ Show running configuration

### Commands Tested

#### Configuration Commands
```bash
ip route 10.1.1.0/24 192.168.1.1
ip route 10.2.2.0/24 blackhole
ipv6 route 2001:db8:1::/64 2001:db8:100::1
ipv6 route 2001:db8:2::/64 blackhole
```

#### Deletion Commands
```bash
no ip route 10.1.1.0/24 192.168.1.1
no ip route 10.2.2.0/24 blackhole
no ipv6 route 2001:db8:1::/64 2001:db8:100::1
no ipv6 route 2001:db8:2::/64 blackhole
```

#### Show Commands
```bash
show ip route static
show ipv6 route static
show running-configuration
```

---

## 📝 Logging and Artifacts

### CLI Output Logs
**Location**: `logs/cli_output/`

Each test generates a detailed log file containing:
- Device information
- Test case name
- CLI commands executed
- Command output
- Verification command results
- Timestamps

**Format**: `{device}_{testcase}_{timestamp}.log`

### Database Snapshots
**Location**: `logs/db_snapshots/`

Before and after snapshots for each test containing:
- Running configuration
- IP routing table
- IPv6 routing table
- Static routes
- VRF information
- Interface status

**Format**: `{device}_{testcase}_{before|after}_{timestamp}.json`

### Pytest Execution Log
**Location**: `logs/pytest_execution.log`

Complete pytest execution log with:
- Test discovery
- Test execution flow
- SSH connection logs
- DB snapshot capture logs
- Cleanup operations
- Test timing information

---

## ⚙️ Configuration

### Device Configuration

```yaml
devices:
  - name: VS-1                    # Device name
    host: 192.168.100.97          # Device IP
    port: 22                      # SSH port
    username: admin               # SSH username
    password: YourPaSsWoRd        # SSH password
    enabled: true                 # Enable/disable device
```

### Test Data Configuration

```yaml
test_data:
  ipv4:
    prefixes:
      - 10.1.1.0/24
      - 10.2.2.0/24
    nexthops:
      - 192.168.1.1
      - 192.168.1.2
  ipv6:
    prefixes:
      - "2001:db8:1::/64"
      - "2001:db8:2::/64"
    nexthops:
      - "2001:db8:100::1"
      - "2001:db8:100::2"
```

### Execution Settings

```yaml
execution:
  cleanup_before_test: true     # Clean routes before each test
  cleanup_after_test: true      # Clean routes after each test
  capture_db_snapshot: true     # Capture DB snapshots
  parallel_execution: false     # Enable parallel execution
```

---

## 🎯 Advanced Usage

### Run Specific Test Categories

```bash
# Run only IPv4 tests
pytest scripts/test_route_static.py -v -m ipv4

# Run only IPv6 tests
pytest scripts/test_route_static.py -v -m ipv6

# Run only deletion tests
pytest scripts/test_route_static.py -v -m deletion

# Run only blackhole tests
pytest scripts/test_route_static.py -v -m blackhole
```

### Run Specific Test Classes

```bash
# Run IPv4 tests only
pytest scripts/test_route_static.py::TestIPv4StaticRoutes -v

# Run IPv6 tests only
pytest scripts/test_route_static.py::TestIPv6StaticRoutes -v

# Run deletion tests only
pytest scripts/test_route_static.py::TestRouteDeletion -v
```

### Run Specific Test Cases

```bash
# Run single test
pytest scripts/test_route_static.py::TestIPv4StaticRoutes::test_ipv4_route_with_nexthop -v
```

### Debugging

```bash
# Verbose output
pytest scripts/test_route_static.py -vv

# Show local variables on failure
pytest scripts/test_route_static.py -vv -l

# Stop on first failure
pytest scripts/test_route_static.py -x

# Drop into debugger on failure
pytest scripts/test_route_static.py --pdb
```

---

## 📦 Dependencies

### Core Dependencies

- **pytest** (≥7.4.0) - Testing framework
- **pytest-html** (≥4.1.1) - HTML report generation
- **pytest-json-report** (≥1.5.0) - JSON report generation
- **pytest-metadata** (≥3.0.0) - Test metadata
- **pytest-timeout** (≥2.2.0) - Test timeout management
- **paramiko** (≥3.4.0) - SSH connectivity
- **PyYAML** (≥6.0.1) - Configuration parsing
- **jinja2** (≥3.1.2) - Template rendering

### Full List

See `requirements.txt` for complete dependency list.

---

## 🔧 Customization

### Adding New Test Cases

Edit `scripts/test_route_static.py`:

```python
@pytest.mark.ipv4
def test_your_new_test(self, test_context, ipv4_test_data):
    """
    Your test description

    Test Steps:
        1. Step 1
        2. Step 2
    """
    ssh_client = test_context['ssh_client']
    cli_logger = test_context['cli_logger']
    logger = test_context['logger']

    # Your test implementation
    cli_command = "your cli command"
    result = ssh_client.execute_cli_command(cli_command)

    # Log and assert
    cli_logger.log_command(cli_command, result['output'], result['success'])
    assert result['success'], "Test failed"
```

### Adding New Devices

Edit `config/config.yaml`:

```yaml
devices:
  - name: VS-3
    host: 192.168.100.xxx
    port: 22
    username: admin
    password: password
    enabled: true
```

### Customizing Reports

Edit `scripts/generate_reports.py` to customize report templates.

---

## 📖 Documentation

### User Guide
**Location**: `/home/adminuser/draksha/route_static/docs/pytest_user_guide.md`

Comprehensive guide covering:
- Prerequisites
- Installation
- Configuration
- Test execution
- Report viewing
- Advanced usage
- Troubleshooting

### Test Plan
**Location**: `/home/adminuser/draksha/route_static/docs/cli_test_plan.md`

Original test plan with all 42 test cases.

---

## 🐛 Troubleshooting

### Connection Issues

```bash
# Test SSH connectivity
ssh admin@192.168.100.97

# Check configuration
cat config/config.yaml

# Increase timeout
# Edit config.yaml → ssh.timeout: 60
```

### Import Errors

```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Test Failures

```bash
# Check logs
tail -f logs/pytest_execution.log

# Check CLI output
ls -lh logs/cli_output/
cat logs/cli_output/VS-1_*.log

# Check DB snapshots
ls -lh logs/db_snapshots/
python3 -m json.tool logs/db_snapshots/VS-1_*.json
```

---

## 📞 Support

For issues or questions:

1. Review logs in `logs/` directory
2. Check test reports in `results/` directory
3. Consult user guide in `docs/pytest_user_guide.md`
4. Review pytest documentation: https://docs.pytest.org/

---

## 🎓 Best Practices

1. **Always activate virtual environment** before running tests
2. **Review configuration** before test execution
3. **Clean previous results** periodically: `./run_tests.sh --clean`
4. **Check logs** after test execution
5. **Review DB snapshots** for debugging
6. **Use markers** to run specific test categories
7. **Keep configuration** in version control (except passwords)

---

## 📈 Performance

- Average test execution time: ~60 seconds per test
- Includes SSH connection, command execution, verification, and snapshots
- Parallel execution available but may cause test interference

---

## 🔐 Security Notes

- Passwords are stored in `config.yaml` - ensure proper file permissions
- SSH connections use password authentication
- No sensitive data is logged in reports
- Consider using SSH keys instead of passwords for production

---

## 🚀 Future Enhancements

- [ ] VRF-based route testing (requires VRF configuration)
- [ ] Interface-based route testing
- [ ] Nexthop-VRF testing
- [ ] Parallel test execution optimization
- [ ] Integration with CI/CD pipelines
- [ ] Email notification support
- [ ] Slack/Teams integration for notifications

---

## 📄 License

Copyright 2025. Licensed under Apache License 2.0.

---

## 👥 Authors

Automated Testing Framework Team

---

**Framework Status**: ✅ Production Ready
**Last Test Execution**: 2025-11-11
**Test Pass Rate**: Check latest reports in `results/`

---

**End of README**
