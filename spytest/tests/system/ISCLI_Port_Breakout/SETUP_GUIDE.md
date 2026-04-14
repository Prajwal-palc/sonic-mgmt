# Port Breakout Test Suite - Setup Guide

## Prerequisites for Running Spytest Scripts

Before running any Port Breakout test scripts, you need to set up the spytest virtual environment and install all required packages.

---

## Step 1: Create and Activate Spytest Virtual Environment

### Navigate to spytest directory
```bash
cd /home/claudeuser/draksha/sonic-mgmt/spytest
```

### Create virtual environment (if not already created)
```bash
python3 -m venv spytest_venv
```

### Activate virtual environment
```bash
source spytest_venv/bin/activate
```

**Note:** You should see `(spytest_venv)` prefix in your terminal prompt after activation.

---

## Step 2: Install Python Dependencies

### Upgrade pip
```bash
pip install --upgrade pip
```

### Install pytest and pytest plugins
```bash
pip install pytest==7.1.3
pip install pytest-xdist==2.5.0
pip install pytest-timeout==2.1.0
pip install pytest-html==3.1.1
pip install pytest-repeat==0.9.1
```

### Install SONiC/Spytest specific packages
```bash
pip install jinja2==3.1.2
pip install tabulate==0.9.0
pip install netmiko==4.1.2
pip install paramiko==2.12.0
pip install textfsm==1.1.3
pip install ttp==0.9.1
pip install pysnmp==4.4.12
pip install pyyaml==6.0
pip install xlsxwriter==3.0.3
pip install xlrd==2.0.1
pip install Pillow==9.3.0
pip install redis==4.3.4
pip install psutil==5.9.4
```

### Install additional utilities
```bash
pip install colorlog==6.7.0
pip install pexpect==4.8.0
pip install scp==0.14.4
pip install ipaddress==1.0.23
pip install requests==2.28.1
```

---

## Step 3: Install Spytest Framework

### Install spytest package (if available)
```bash
# If spytest is packaged
pip install -e .
```

**OR**

### Set PYTHONPATH for spytest modules
```bash
export PYTHONPATH=/home/claudeuser/draksha/sonic-mgmt/spytest:$PYTHONPATH
```

**Add to ~/.bashrc for persistence:**
```bash
echo 'export PYTHONPATH=/home/claudeuser/draksha/sonic-mgmt/spytest:$PYTHONPATH' >> ~/.bashrc
source ~/.bashrc
```

---

## Step 4: Verify Installation

### Check Python version
```bash
python --version
# Should be Python 3.8 or higher
```

### Check pytest installation
```bash
pytest --version
# Should show pytest version 7.1.3 or compatible
```

### List installed packages
```bash
pip list | grep -E "pytest|spytest|netmiko|paramiko"
```

### Test spytest imports
```bash
python -c "from spytest import st; print('Spytest import successful')"
```

---

## Step 5: Configure Testbed File

### Create testbed directory (if not exists)
```bash
mkdir -p /home/claudeuser/draksha/sonic-mgmt/spytest/testbeds
```

### Create testbed configuration file

Create file: `/home/claudeuser/draksha/sonic-mgmt/spytest/testbeds/testbed_breakout.yaml`

```yaml
# testbed_breakout.yaml
---
devices:
  - alias: "D1"
    properties:
      type: "sonic"
      ip: "192.168.1.10"
      username: "admin"
      password: "YourPassword"
      protocol: "ssh"
      port: 22
    credentials:
      - username: "admin"
        password: "YourPassword"
        mode: "mgmt-user"

  - alias: "D2"
    properties:
      type: "sonic"
      ip: "192.168.1.11"
      username: "admin"
      password: "YourPassword"
      protocol: "ssh"
      port: 22
    credentials:
      - username: "admin"
        password: "YourPassword"
        mode: "mgmt-user"

topology:
  - link: ["D1:Ethernet24", "D2:Ethernet24"]
  - link: ["D1:Ethernet32", "D2:Ethernet32"]
  - link: ["D1:Ethernet40", "D2:Ethernet40"]
  - link: ["D1:Ethernet48", "D2:Ethernet48"]

params:
  breakout_capable_ports:
    D1:
      - "Ethernet24"
      - "Ethernet32"
      - "Ethernet40"
      - "Ethernet48"
    D2:
      - "Ethernet24"
      - "Ethernet32"
      - "Ethernet40"
      - "Ethernet48"
```

**Important:** Update IP addresses, usernames, and passwords according to your setup!

---

## Step 6: Verify Device Connectivity

### Test SSH connection to DUT1
```bash
ssh admin@192.168.1.10
# Enter password and verify you can login
# Type 'exit' to logout
```

### Test SSH connection to DUT2
```bash
ssh admin@192.168.1.11
# Enter password and verify you can login
# Type 'exit' to logout
```

### Verify SONiC CLI access
```bash
ssh admin@192.168.1.10
sonic-cli
show version
exit
exit
```

---

## Step 7: Create Logs Directory

```bash
mkdir -p /home/claudeuser/draksha/sonic-mgmt/spytest/logs
```

---

## Step 8: Run First Test (Verification)

### Activate virtual environment
```bash
cd /home/claudeuser/draksha/sonic-mgmt/spytest
source spytest_venv/bin/activate
```

### Run a simple test to verify setup
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_breakout.yaml \
  tests/system/ISCLI_Port_Breakout/test_pb_f_004_revert_to_default.py \
  --logs-path ./logs/verification_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### Check test results
```bash
# Check the logs directory
ls -lh logs/
# Look for the latest log directory
cd logs/verification_<timestamp>/
cat results.txt
```

---

## Complete Installation Script

Here's a complete script to set up everything:

```bash
#!/bin/bash

echo "=== Port Breakout Test Suite - Setup Script ==="
echo ""

# Navigate to spytest directory
cd /home/claudeuser/draksha/sonic-mgmt/spytest

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv spytest_venv

# Activate virtual environment
echo "Activating virtual environment..."
source spytest_venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install pytest and plugins
echo "Installing pytest and plugins..."
pip install pytest==7.1.3
pip install pytest-xdist==2.5.0
pip install pytest-timeout==2.1.0
pip install pytest-html==3.1.1
pip install pytest-repeat==0.9.1

# Install SONiC/Spytest packages
echo "Installing SONiC/Spytest packages..."
pip install jinja2==3.1.2
pip install tabulate==0.9.0
pip install netmiko==4.1.2
pip install paramiko==2.12.0
pip install textfsm==1.1.3
pip install ttp==0.9.1
pip install pysnmp==4.4.12
pip install pyyaml==6.0
pip install xlsxwriter==3.0.3
pip install xlrd==2.0.1
pip install Pillow==9.3.0
pip install redis==4.3.4
pip install psutil==5.9.4

# Install utilities
echo "Installing utilities..."
pip install colorlog==6.7.0
pip install pexpect==4.8.0
pip install scp==0.14.4
pip install ipaddress==1.0.23
pip install requests==2.28.1

# Set PYTHONPATH
echo "Setting PYTHONPATH..."
export PYTHONPATH=/home/claudeuser/draksha/sonic-mgmt/spytest:$PYTHONPATH

# Create directories
echo "Creating directories..."
mkdir -p testbeds
mkdir -p logs

# Verify installation
echo ""
echo "=== Verification ==="
python --version
pytest --version
python -c "from spytest import st; print('Spytest import: SUCCESS')"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit testbed file: testbeds/testbed_breakout.yaml"
echo "2. Update device IP addresses and credentials"
echo "3. Verify device connectivity"
echo "4. Run test: ./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_breakout.yaml tests/system/ISCLI_Port_Breakout/test_pb_f_004_revert_to_default.py"
echo ""
```

### Save and run the setup script
```bash
cd /home/claudeuser/draksha/sonic-mgmt/spytest
nano setup_breakout_tests.sh
# Paste the script above
chmod +x setup_breakout_tests.sh
./setup_breakout_tests.sh
```

---

## Common Installation Issues

### Issue 1: Python version mismatch
**Error:** `Python 3.6 or higher required`

**Solution:**
```bash
# Check Python version
python3 --version

# If version is too old, install Python 3.8+
sudo apt update
sudo apt install python3.8 python3.8-venv python3.8-dev
```

### Issue 2: pip installation fails
**Error:** `Could not install packages due to an EnvironmentError`

**Solution:**
```bash
# Use --user flag
pip install --user <package-name>

# Or use sudo (not recommended in venv)
sudo pip install <package-name>
```

### Issue 3: Spytest module not found
**Error:** `ModuleNotFoundError: No module named 'spytest'`

**Solution:**
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=/home/claudeuser/draksha/sonic-mgmt/spytest:$PYTHONPATH

# Verify spytest directory exists
ls -la /home/claudeuser/draksha/sonic-mgmt/spytest/spytest/
```

### Issue 4: SSH connection fails
**Error:** `Connection timeout` or `Authentication failed`

**Solution:**
```bash
# Verify device is reachable
ping 192.168.1.10

# Test SSH manually
ssh admin@192.168.1.10

# Check SSH key permissions
chmod 600 ~/.ssh/id_rsa

# Use password authentication
ssh -o PreferredAuthentications=password admin@192.168.1.10
```

### Issue 5: Permission denied on /tmp
**Error:** `PermissionError: [Errno 13] Permission denied: '/tmp/...'`

**Solution:**
```bash
# Set temporary directory
export TMPDIR=/home/claudeuser/tmp
mkdir -p $TMPDIR

# Or fix /tmp permissions
sudo chmod 1777 /tmp
```

---

## Package Requirements File

You can also create a `requirements.txt` file:

Create file: `/home/claudeuser/draksha/sonic-mgmt/spytest/requirements_breakout.txt`

```txt
pytest==7.1.3
pytest-xdist==2.5.0
pytest-timeout==2.1.0
pytest-html==3.1.1
pytest-repeat==0.9.1
jinja2==3.1.2
tabulate==0.9.0
netmiko==4.1.2
paramiko==2.12.0
textfsm==1.1.3
ttp==0.9.1
pysnmp==4.4.12
pyyaml==6.0
xlsxwriter==3.0.3
xlrd==2.0.1
Pillow==9.3.0
redis==4.3.4
psutil==5.9.4
colorlog==6.7.0
pexpect==4.8.0
scp==0.14.4
ipaddress==1.0.23
requests==2.28.1
```

### Install from requirements file
```bash
pip install -r requirements_breakout.txt
```

---

## Running Tests After Setup

### Always activate virtual environment first
```bash
cd /home/claudeuser/draksha/sonic-mgmt/spytest
source spytest_venv/bin/activate
```

### Run single test
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_breakout.yaml \
  tests/system/ISCLI_Port_Breakout/test_pb_f_004_revert_to_default.py \
  --logs-path ./logs/pb_f_004_$(date +%F_%H%M%S)
```

### Run all tests
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_breakout.yaml \
  tests/system/ISCLI_Port_Breakout/ \
  --logs-path ./logs/all_tests_$(date +%F_%H%M%S)
```

### Deactivate virtual environment when done
```bash
deactivate
```

---

## Quick Reference

### Essential Commands

```bash
# Activate venv
source spytest_venv/bin/activate

# Run test
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_breakout.yaml <test_file>

# Check logs
ls -lh logs/

# Deactivate venv
deactivate
```

### Environment Variables

```bash
# Set PYTHONPATH
export PYTHONPATH=/home/claudeuser/draksha/sonic-mgmt/spytest:$PYTHONPATH

# Set temporary directory
export TMPDIR=/home/claudeuser/tmp

# Set log level
export SPYTEST_LOG_LEVEL=DEBUG
```

---

## Verification Checklist

Before running tests, ensure:

- ✅ Virtual environment created and activated
- ✅ All Python packages installed
- ✅ PYTHONPATH set correctly
- ✅ Testbed file configured with correct IPs and credentials
- ✅ SSH connectivity to all DUTs verified
- ✅ SONiC CLI accessible on all DUTs
- ✅ Logs directory exists
- ✅ Test ports support breakout capability
- ✅ Breakout cables/optics installed

---

## Support

For issues:
1. Check logs in `./logs/<test_run_directory>/`
2. Review this SETUP_GUIDE.md
3. Check README.md for test-specific information
4. Verify all prerequisites met

---

**Last Updated:** March 31, 2026

**Status:** ✅ SETUP GUIDE COMPLETE
