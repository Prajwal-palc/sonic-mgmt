# NTP CLI Automation Framework - Quick Start Guide

## Overview
Enhanced pytest framework for SONiC NTP CLI automation with comprehensive reporting.

## Quick Start

### 1. Install Dependencies
```bash
cd /home/adminuser/draksha/cli/ntp/scripts
pip3 install -r requirements.txt
```

### 2. Run Tests
```bash
# Run all tests
python3 run_enhanced_tests.py

# OR use pytest directly
pytest test_ntp_cli_enhanced.py -v
```

### 3. View Results
```bash
# Open main report
firefox /home/adminuser/draksha/ntp/cli/results/ntp_cli_test_report.html

# View logs
tail -f /home/adminuser/draksha/cli/ntp/logs/pytest_execution.log
```

## Configuration

### VS Instances (Edit `config.py`)
- **VS1**: 192.168.100.97 (admin/YourPaSsWoRd)
- **VS2**: 192.168.100.142 (admin/YourPaSsWoRd)

### Customize
```bash
nano config.py
# Edit VS_INSTANCES section
```

## Test Execution Options

```bash
# Run by category
pytest test_ntp_cli_enhanced.py -m servers -v
pytest test_ntp_cli_enhanced.py -m authentication -v

# Run on specific VS
pytest test_ntp_cli_enhanced.py -k "VS1" -v

# Run specific test
pytest test_ntp_cli_enhanced.py::TestNTPGlobalConfiguration::test_ntp_001_enable_ntp -v
```

## Generated Reports

All saved to: `/home/adminuser/draksha/ntp/cli/results/`

1. **ntp_cli_test_report.html** - Main comprehensive report
2. **pytest_report_final.html** - Debugging report
3. **ntp_cli_summary.html** - Coverage summary
4. **test.log** - Consolidated log
5. **ntp_test_summary.md** - Test summary
6. **ntp_execution_summary.md** - Execution summary

## Logs

Location: `/home/adminuser/draksha/cli/ntp/logs/`
- pytest_execution.log
- Per-test JSON logs with commands/responses/DB snapshots

## Documentation

- **User Guide**: `/home/adminuser/draksha/ntp/docs/pytest_execution_user_guide.md`
- **Test Plan**: `/home/adminuser/draksha/ntp/docs/ntp_cli_test_plan.md`
- **Part 2 Summary**: `/home/adminuser/draksha/ntp/docs/PART2_COMPREHENSIVE_SUMMARY.md`

## Troubleshooting

### Connection Failed
```bash
# Test connectivity
ping 192.168.100.97
ssh admin@192.168.100.97
```

### Import Errors
```bash
# Reinstall dependencies
pip3 install -r requirements.txt
```

### View Debug Logs
```bash
tail -f /home/adminuser/draksha/cli/ntp/logs/pytest_execution.log
```

## Support

For detailed instructions, see:
- `/home/adminuser/draksha/ntp/docs/pytest_execution_user_guide.md`

---

**Framework Version**: 2.0 Enhanced
**Total Tests**: 50 test cases × 2 VS instances = 100 tests
**Status**: Ready for execution
