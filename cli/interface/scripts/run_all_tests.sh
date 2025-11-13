#!/bin/bash

#=============================================================================
# Master Test Execution Script for Interface CLI Testing
# Executes pytest suite and generates all required reports
#=============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_DIR/logs"
RESULTS_DIR="$PROJECT_DIR/results"
CONFIG_DIR="$PROJECT_DIR/config"

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}  Interface CLI Testing Framework - Master Execution Script${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""

#=============================================================================
# Step 1: Prerequisites Check
#=============================================================================
echo -e "${YELLOW}[Step 1/6] Checking Prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python3 found: $(python3 --version)${NC}"

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}✗ pip3 is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ pip3 found${NC}"

# Check required packages
echo "Checking required Python packages..."
REQUIRED_PACKAGES=("pytest" "paramiko" "yaml")
ALL_INSTALLED=true

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $package"
    else
        echo -e "  ${RED}✗${NC} $package (missing)"
        ALL_INSTALLED=false
    fi
done

if [ "$ALL_INSTALLED" = false ]; then
    echo ""
    echo -e "${YELLOW}Installing missing packages...${NC}"
    pip3 install -r "$SCRIPT_DIR/requirements.txt" || {
        echo -e "${RED}Failed to install packages${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Packages installed${NC}"
fi

echo ""

#=============================================================================
# Step 2: Directory Setup
#=============================================================================
echo -e "${YELLOW}[Step 2/6] Setting up Directories...${NC}"

mkdir -p "$LOGS_DIR"
mkdir -p "$RESULTS_DIR"

echo -e "${GREEN}✓ Directories ready${NC}"
echo "  Logs: $LOGS_DIR"
echo "  Results: $RESULTS_DIR"
echo ""

#=============================================================================
# Step 3: Configuration Verification
#=============================================================================
echo -e "${YELLOW}[Step 3/6] Verifying Configuration...${NC}"

CONFIG_FILE="$CONFIG_DIR/devices.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}✗ Configuration file not found: $CONFIG_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Configuration file found${NC}"

# Extract device IPs and test connectivity
echo "Checking device connectivity..."
DEVICE1_IP="192.168.100.97"
DEVICE2_IP="192.168.100.142"

for IP in "$DEVICE1_IP" "$DEVICE2_IP"; do
    if ping -c 1 -W 2 "$IP" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $IP is reachable"
    else
        echo -e "  ${YELLOW}⚠${NC} $IP is not reachable (tests may fail)"
    fi
done

echo ""

#=============================================================================
# Step 4: Run Pytest Suite
#=============================================================================
echo -e "${YELLOW}[Step 4/6] Running Pytest Test Suite...${NC}"
echo ""

cd "$SCRIPT_DIR"

# Run pytest with HTML report
pytest -v \
    --html="$RESULTS_DIR/pytest_report_final.html" \
    --self-contained-html \
    --tb=short \
    2>&1 | tee "$LOGS_DIR/pytest_execution_$(date +%Y%m%d_%H%M%S).log"

PYTEST_EXIT_CODE=${PIPESTATUS[0]}

echo ""
if [ $PYTEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed${NC}"
elif [ $PYTEST_EXIT_CODE -eq 1 ]; then
    echo -e "${YELLOW}⚠ Some tests failed (see report for details)${NC}"
else
    echo -e "${RED}✗ Test execution encountered errors${NC}"
fi

echo ""

#=============================================================================
# Step 5: Generate Custom Reports
#=============================================================================
echo -e "${YELLOW}[Step 5/6] Generating Custom Reports...${NC}"

python3 "$SCRIPT_DIR/generate_reports.py"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Custom reports generated${NC}"
else
    echo -e "${YELLOW}⚠ Report generation completed with warnings${NC}"
fi

echo ""

#=============================================================================
# Step 6: Summary
#=============================================================================
echo -e "${YELLOW}[Step 6/6] Test Execution Summary${NC}"
echo ""

# Count test results from logs
TOTAL_TESTS=$(find "$LOGS_DIR" -name "*.json" -type f | wc -l)
PYTEST_REPORT="$RESULTS_DIR/pytest_report_final.html"

echo -e "${BLUE}======================================================================${NC}"
echo -e "  Test Execution Completed"
echo -e "${BLUE}======================================================================${NC}"
echo ""
echo "Test Results:"
echo "  Total Test Executions: $TOTAL_TESTS"
echo "  Pytest Exit Code: $PYTEST_EXIT_CODE"
echo ""
echo "Generated Reports:"
echo "  1. pytest_report_final.html - Standard pytest HTML report"
echo "  2. interface_cli_test_report.html - Detailed custom report"
echo "  3. interface_cli_summary.html - Summary dashboard"
echo "  4. interface_summary.md - Markdown summary"
echo "  5. interface_execution_summary.md - Execution details"
echo ""
echo "Report Location: $RESULTS_DIR"
echo "Logs Location: $LOGS_DIR"
echo ""

# List generated files
if [ -d "$RESULTS_DIR" ]; then
    echo "Generated Report Files:"
    ls -lh "$RESULTS_DIR"/*.html "$RESULTS_DIR"/*.md 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
    echo ""
fi

echo -e "${BLUE}======================================================================${NC}"
echo ""

# View report prompt
if [ -f "$PYTEST_REPORT" ]; then
    echo -e "${GREEN}To view the pytest report:${NC}"
    echo "  firefox $PYTEST_REPORT"
    echo "  or"
    echo "  google-chrome $PYTEST_REPORT"
    echo ""
fi

echo -e "${GREEN}Test execution completed successfully!${NC}"

exit $PYTEST_EXIT_CODE
