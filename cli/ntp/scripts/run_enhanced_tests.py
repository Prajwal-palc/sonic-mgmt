#!/usr/bin/env python3
"""
Enhanced NTP CLI Test Runner
Executes comprehensive test suite with full reporting
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import LOGS_DIR, RESULTS_DIR

# Setup logging
log_file = os.path.join(LOGS_DIR, f"test_runner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def print_banner():
    """Print test execution banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════════════╗
    ║                                                                      ║
    ║           NTP CLI AUTOMATION TEST FRAMEWORK - ENHANCED               ║
    ║                                                                      ║
    ║                    Comprehensive Test Execution                      ║
    ║                                                                      ║
    ╚══════════════════════════════════════════════════════════════════════╝
    """
    print(banner)
    logger.info("NTP CLI Test Execution Started")


def check_prerequisites():
    """Check if all prerequisites are met"""
    logger.info("Checking prerequisites...")

    # Check pytest installation
    try:
        import pytest
        logger.info(f"✓ pytest installed: {pytest.__version__}")
    except ImportError:
        logger.error("✗ pytest not installed")
        return False

    # Check paramiko installation
    try:
        import paramiko
        logger.info(f"✓ paramiko installed: {paramiko.__version__}")
    except ImportError:
        logger.error("✗ paramiko not installed")
        return False

    # Check directories
    if not os.path.exists(LOGS_DIR):
        logger.error(f"✗ Logs directory not found: {LOGS_DIR}")
        return False
    logger.info(f"✓ Logs directory exists: {LOGS_DIR}")

    if not os.path.exists(RESULTS_DIR):
        logger.error(f"✗ Results directory not found: {RESULTS_DIR}")
        return False
    logger.info(f"✓ Results directory exists: {RESULTS_DIR}")

    logger.info("All prerequisites met!")
    return True


def run_tests():
    """Execute pytest test suite"""
    logger.info("="*80)
    logger.info("Starting Test Execution")
    logger.info("="*80)

    # Change to scripts directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Prepare pytest command
    pytest_args = [
        "pytest",
        "test_ntp_cli_enhanced.py",
        "-v",
        "--tb=short",
        f"--html={RESULTS_DIR}/pytest_html_report_{timestamp}.html",
        "--self-contained-html",
        "--json-report",
        f"--json-report-file={RESULTS_DIR}/pytest_json_report_{timestamp}.json"
    ]

    logger.info(f"Executing command: {' '.join(pytest_args)}")
    logger.info(f"Working directory: {os.getcwd()}")

    try:
        # Run pytest
        result = subprocess.run(
            pytest_args,
            capture_output=False,
            text=True
        )

        logger.info("="*80)
        logger.info(f"Test execution completed with return code: {result.returncode}")
        logger.info("="*80)

        return result.returncode

    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")
        return 1


def print_summary():
    """Print execution summary"""
    logger.info("\n" + "="*80)
    logger.info("TEST EXECUTION SUMMARY")
    logger.info("="*80)

    # List generated reports
    logger.info("\nGenerated Reports:")

    reports = [
        ("Main Test Report", f"{RESULTS_DIR}/ntp_cli_test_report.html"),
        ("Pytest Report", f"{RESULTS_DIR}/pytest_report_final.html"),
        ("CLI Summary", f"{RESULTS_DIR}/ntp_cli_summary.html"),
        ("Test Summary (MD)", f"{RESULTS_DIR}/ntp_test_summary.md"),
        ("Execution Summary (MD)", f"{RESULTS_DIR}/ntp_execution_summary.md"),
        ("Test Log", f"{RESULTS_DIR}/test.log")
    ]

    for name, path in reports:
        if os.path.exists(path):
            size = os.path.getsize(path)
            logger.info(f"  ✓ {name}: {path} ({size} bytes)")
        else:
            logger.warning(f"  ✗ {name}: Not found")

    logger.info(f"\nLogs Directory: {LOGS_DIR}")
    logger.info(f"Results Directory: {RESULTS_DIR}")

    logger.info("\n" + "="*80)
    logger.info("To view reports:")
    logger.info(f"  firefox {RESULTS_DIR}/ntp_cli_test_report.html")
    logger.info(f"  firefox {RESULTS_DIR}/pytest_report_final.html")
    logger.info("="*80 + "\n")


def main():
    """Main entry point"""
    print_banner()

    # Check prerequisites
    if not check_prerequisites():
        logger.error("Prerequisites check failed. Please install required packages:")
        logger.error("  pip3 install -r requirements.txt")
        return 1

    # Run tests
    return_code = run_tests()

    # Print summary
    print_summary()

    if return_code == 0:
        logger.info("✓ All tests completed successfully!")
    else:
        logger.warning(f"⚠ Tests completed with return code: {return_code}")

    return return_code


if __name__ == "__main__":
    sys.exit(main())
