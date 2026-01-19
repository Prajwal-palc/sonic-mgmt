#!/bin/bash

##############################################################################
# Static Route CLI Test Execution Script
# This script executes the pytest-based test framework
##############################################################################

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Static Route CLI Test Execution${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install/upgrade dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1

echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Create necessary directories
mkdir -p logs/cli_output
mkdir -p logs/db_snapshots
mkdir -p results

# Clean previous results (optional)
if [ "$1" == "--clean" ]; then
    echo -e "${YELLOW}Cleaning previous results...${NC}"
    rm -rf logs/*
    rm -rf results/*
    echo -e "${GREEN}✓ Previous results cleaned${NC}"
    echo ""
fi

# Run pytest with HTML and JSON reports
echo -e "${GREEN}Starting pytest execution...${NC}"
echo ""

pytest scripts/test_route_static.py \
    --html=results/pytest_report_final.html \
    --self-contained-html \
    --json-report \
    --json-report-file=results/test_results.json \
    --json-report-indent=2 \
    -v \
    --tb=short \
    --color=yes

PYTEST_EXIT_CODE=$?

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Generating Reports...${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Generate comprehensive reports
python3 scripts/generate_reports.py \
    --json-report results/test_results.json \
    --results-dir results

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Test Execution Complete${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Display results summary
echo -e "${YELLOW}Results Location:${NC}"
echo "  - HTML Report: ${SCRIPT_DIR}/results/pytest_report_final.html"
echo "  - CLI Test Report: ${SCRIPT_DIR}/results/route_static_cli_test_report.html"
echo "  - Summary Report: ${SCRIPT_DIR}/results/route_static_cli_summary.html"
echo "  - Summary MD: ${SCRIPT_DIR}/results/route_static_summary.md"
echo "  - Execution Summary: ${SCRIPT_DIR}/results/route_static_execution_summary.md"
echo "  - Test Logs: ${SCRIPT_DIR}/logs/"
echo ""

if [ $PYTEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}⚠ Some tests failed. Check reports for details.${NC}"
fi

echo ""
echo -e "${YELLOW}To view reports:${NC}"
echo "  firefox results/pytest_report_final.html &"
echo "  firefox results/route_static_cli_test_report.html &"
echo ""

# Deactivate virtual environment
deactivate

exit $PYTEST_EXIT_CODE
