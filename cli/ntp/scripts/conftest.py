"""
Enhanced Pytest Configuration with Comprehensive Logging and Reporting
"""

import pytest
import logging
import sys
import os
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ACTIVE_INSTANCES, LOGS_DIR, RESULTS_DIR, TEST_CONFIG
from enhanced_ssh_client import EnhancedSONiCSSHClient
from report_generator import ComprehensiveReportGenerator

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'pytest_execution.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def comprehensive_reporter():
    """Session-scoped comprehensive report generator"""
    reporter = ComprehensiveReportGenerator(RESULTS_DIR)
    yield reporter

    # Generate all reports at end of session
    try:
        logger.info("Generating comprehensive reports...")
        reports = reporter.generate_all_reports()

        logger.info("Reports generated successfully:")
        for report_name, report_path in reports.items():
            logger.info(f"  - {report_name}: {report_path}")

    except Exception as e:
        logger.error(f"Error generating reports: {str(e)}")


@pytest.fixture(params=ACTIVE_INSTANCES, ids=lambda x: x['name'])
def vs_instance(request):
    """Fixture providing VS instance configuration"""
    return request.param


@pytest.fixture
def enhanced_ssh_client(vs_instance):
    """Fixture providing enhanced SSH client with logging"""
    client = EnhancedSONiCSSHClient(
        host=vs_instance['host'],
        username=vs_instance['username'],
        password=vs_instance['password'],
        port=vs_instance['port'],
        log_dir=LOGS_DIR
    )

    # Connect
    if not client.connect():
        pytest.skip(f"Failed to connect to {vs_instance['name']} ({vs_instance['host']})")

    # Enter SONiC CLI
    _, success = client.enter_sonic_cli()
    if not success:
        client.disconnect()
        pytest.skip(f"Failed to enter SONiC CLI on {vs_instance['name']}")

    yield client

    # Cleanup
    try:
        if TEST_CONFIG.get('cleanup_after_test', True):
            client.cleanup_ntp_config()
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")

    client.disconnect()


def pytest_configure(config):
    """Pytest configuration hook"""
    # Add custom markers
    config.addinivalue_line("markers", "global_config: NTP global configuration tests")
    config.addinivalue_line("markers", "authentication: NTP authentication tests")
    config.addinivalue_line("markers", "auth_keys: NTP authentication key tests")
    config.addinivalue_line("markers", "trusted_keys: NTP trusted key tests")
    config.addinivalue_line("markers", "servers: NTP server configuration tests")
    config.addinivalue_line("markers", "source_interface: NTP source interface tests")
    config.addinivalue_line("markers", "vrf: NTP VRF configuration tests")
    config.addinivalue_line("markers", "show_commands: NTP show command tests")
    config.addinivalue_line("markers", "complex: Complex NTP configuration scenarios")

    logger.info("="*80)
    logger.info("NTP CLI TEST FRAMEWORK - ENHANCED VERSION")
    logger.info("="*80)
    logger.info(f"Logs Directory: {LOGS_DIR}")
    logger.info(f"Results Directory: {RESULTS_DIR}")
    logger.info(f"Active VS Instances: {len(ACTIVE_INSTANCES)}")
    logger.info("="*80)


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished"""
    logger.info("="*80)
    logger.info("TEST SESSION COMPLETED")
    logger.info(f"Exit Status: {exitstatus}")
    logger.info("="*80)
