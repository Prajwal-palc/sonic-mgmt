#!/bin/bash

##############################################################################
# Port Breakout Test Suite - Automated Setup Script
#
# This script sets up the spytest virtual environment and installs all
# required dependencies for running Port Breakout test automation.
#
# Usage: ./setup_breakout_tests.sh
##############################################################################

set -e  # Exit on error

echo "=========================================================================="
echo "  Port Breakout Test Suite - Setup Script"
echo "=========================================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the correct directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${YELLOW}Current directory: $SCRIPT_DIR${NC}"
echo ""

# Step 1: Check Python version
echo "Step 1: Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MINOR" -lt 8 ]; then
    echo -e "${RED}ERROR: Python 3.8 or higher required. Current: $PYTHON_VERSION${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Python version $PYTHON_VERSION is compatible${NC}"
fi
echo ""

# Step 2: Create virtual environment
echo "Step 2: Creating virtual environment..."
if [ -d "spytest_venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists. Skipping creation.${NC}"
else
    python3 -m venv spytest_venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi
echo ""

# Step 3: Activate virtual environment
echo "Step 3: Activating virtual environment..."
source spytest_venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Step 4: Upgrade pip
echo "Step 4: Upgrading pip..."
pip install --upgrade pip --quiet
echo -e "${GREEN}✓ Pip upgraded${NC}"
echo ""

# Step 5: Install packages from requirements file
echo "Step 5: Installing Python packages..."
if [ -f "requirements_breakout.txt" ]; then
    echo "Installing from requirements_breakout.txt..."
    pip install -r requirements_breakout.txt --quiet
    echo -e "${GREEN}✓ All packages installed from requirements file${NC}"
else
    echo -e "${YELLOW}requirements_breakout.txt not found. Installing packages manually...${NC}"

    # Install pytest and plugins
    pip install pytest==7.1.3 pytest-xdist==2.5.0 pytest-timeout==2.1.0 \
                pytest-html==3.1.1 pytest-repeat==0.9.1 --quiet

    # Install SONiC/Spytest packages
    pip install jinja2==3.1.2 tabulate==0.9.0 netmiko==4.1.2 paramiko==2.12.0 \
                textfsm==1.1.3 ttp==0.9.1 pysnmp==4.4.12 pyyaml==6.0 \
                xlsxwriter==3.0.3 xlrd==2.0.1 Pillow==9.3.0 redis==4.3.4 \
                psutil==5.9.4 --quiet

    # Install utilities
    pip install colorlog==6.7.0 pexpect==4.8.0 scp==0.14.4 \
                ipaddress==1.0.23 requests==2.28.1 --quiet

    echo -e "${GREEN}✓ All packages installed manually${NC}"
fi
echo ""

# Step 6: Set PYTHONPATH
echo "Step 6: Setting PYTHONPATH..."
export PYTHONPATH=$SCRIPT_DIR:$PYTHONPATH
echo -e "${GREEN}✓ PYTHONPATH set to: $PYTHONPATH${NC}"
echo ""

# Step 7: Create directories
echo "Step 7: Creating directories..."
mkdir -p testbeds
mkdir -p logs
echo -e "${GREEN}✓ Directories created (testbeds, logs)${NC}"
echo ""

# Step 8: Verify installation
echo "Step 8: Verifying installation..."
echo ""

echo -n "  Checking Python version... "
python --version
echo -e "  ${GREEN}✓${NC}"

echo -n "  Checking pytest version... "
pytest --version | head -1
echo -e "  ${GREEN}✓${NC}"

echo -n "  Checking spytest import... "
if python -c "from spytest import st" 2>/dev/null; then
    echo -e "${GREEN}✓ SUCCESS${NC}"
else
    echo -e "${YELLOW}⚠ WARNING: Spytest module not found${NC}"
    echo -e "  ${YELLOW}This is OK if spytest is in the parent directory${NC}"
fi

echo ""

# Step 9: Check for testbed file
echo "Step 9: Checking testbed configuration..."
if [ -f "testbeds/testbed_breakout.yaml" ]; then
    echo -e "${GREEN}✓ Testbed file exists: testbeds/testbed_breakout.yaml${NC}"
else
    echo -e "${YELLOW}⚠ Testbed file not found: testbeds/testbed_breakout.yaml${NC}"
    echo "  You need to create this file with your device configuration."
    echo "  See SETUP_GUIDE.md for template."
fi
echo ""

# Summary
echo "=========================================================================="
echo -e "  ${GREEN}Setup Complete!${NC}"
echo "=========================================================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Activate virtual environment (every time you run tests):"
echo -e "   ${YELLOW}source spytest_venv/bin/activate${NC}"
echo ""
echo "2. Configure testbed file (if not already done):"
echo -e "   ${YELLOW}nano testbeds/testbed_breakout.yaml${NC}"
echo "   Update device IPs, usernames, and passwords"
echo ""
echo "3. Verify device connectivity:"
echo -e "   ${YELLOW}ssh admin@<device-ip>${NC}"
echo ""
echo "4. Run a test:"
echo -e "   ${YELLOW}./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_breakout.yaml \\${NC}"
echo -e "   ${YELLOW}  tests/system/ISCLI_Port_Breakout/test_pb_f_004_revert_to_default.py${NC}"
echo ""
echo "For detailed instructions, see:"
echo "  - SETUP_GUIDE.md (complete setup instructions)"
echo "  - README.md (test case descriptions)"
echo "  - PORT_BREAKOUT_DELIVERY_SUMMARY.md (delivery summary)"
echo ""
echo "=========================================================================="
echo ""

# Add to bashrc for persistent PYTHONPATH (optional)
echo -e "${YELLOW}Optional:${NC} Add PYTHONPATH to ~/.bashrc for persistence?"
echo "This will automatically set PYTHONPATH when you login."
read -p "Add to ~/.bashrc? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if ! grep -q "PYTHONPATH.*sonic-mgmt/spytest" ~/.bashrc; then
        echo "export PYTHONPATH=$SCRIPT_DIR:\$PYTHONPATH" >> ~/.bashrc
        echo -e "${GREEN}✓ Added to ~/.bashrc${NC}"
        echo "Run 'source ~/.bashrc' to apply changes"
    else
        echo -e "${YELLOW}Already exists in ~/.bashrc${NC}"
    fi
fi
echo ""

echo "Setup script completed successfully!"
echo ""
