"""
Pytest Configuration and Fixtures
Provides shared fixtures and configuration for all test cases
"""

import pytest
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add helpers to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.config_loader import ConfigLoader
from helpers.ssh_client import SSHClient
from helpers.db_helper import DBHelper
from helpers.logger import TestLogger, CLILogger


# Global configuration
config_loader = ConfigLoader()


def pytest_configure(config):
    """Pytest configuration hook"""
    # Validate configuration
    if not config_loader.validate_config():
        raise ValueError("Invalid configuration file")

    # Set up logging
    log_settings = config_loader.get_logging_settings()
    TestLogger.setup_logger(
        "pytest_framework",
        log_settings.get('log_dir'),
        log_settings.get('level', 'INFO')
    )

    # Create required directories
    log_dir = Path(log_settings.get('log_dir'))
    log_dir.mkdir(parents=True, exist_ok=True)

    cli_log_dir = Path(log_settings.get('cli_log_dir'))
    cli_log_dir.mkdir(parents=True, exist_ok=True)

    db_snapshot_dir = Path(log_settings.get('db_snapshot_dir'))
    db_snapshot_dir.mkdir(parents=True, exist_ok=True)

    results_dir = Path(config_loader.get_results_settings().get('results_dir'))
    results_dir.mkdir(parents=True, exist_ok=True)


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Add markers to tests based on test name
    for item in items:
        # Add markers based on test name patterns
        if "ipv4" in item.nodeid.lower():
            item.add_marker(pytest.mark.ipv4)
        if "ipv6" in item.nodeid.lower():
            item.add_marker(pytest.mark.ipv6)
        if "vrf" in item.nodeid.lower():
            item.add_marker(pytest.mark.vrf)
        if "blackhole" in item.nodeid.lower():
            item.add_marker(pytest.mark.blackhole)
        if "delete" in item.nodeid.lower() or "no_" in item.nodeid.lower():
            item.add_marker(pytest.mark.deletion)


@pytest.fixture(scope="session")
def config():
    """
    Provide configuration object for tests

    Returns:
        ConfigLoader: Configuration loader instance
    """
    return config_loader


@pytest.fixture(scope="session")
def test_devices(config):
    """
    Provide list of test devices

    Returns:
        list: List of device configurations
    """
    return config.get_devices()


@pytest.fixture(scope="function", params=config_loader.get_devices(), ids=lambda d: d['name'])
def device(request):
    """
    Parametrized fixture for each test device

    Returns:
        dict: Device configuration
    """
    return request.param


@pytest.fixture(scope="function")
def ssh_client(device, config):
    """
    Provide SSH client for device

    Args:
        device: Device configuration
        config: Test configuration

    Returns:
        SSHClient: Connected SSH client
    """
    ssh_settings = config.get_ssh_settings()

    client = SSHClient(
        host=device['host'],
        port=device.get('port', 22),
        username=device['username'],
        password=device['password'],
        timeout=ssh_settings.get('timeout', 30)
    )

    # Connect to device
    if not client.connect():
        pytest.skip(f"Failed to connect to device {device['name']}")

    yield client

    # Disconnect after test
    client.disconnect()


@pytest.fixture(scope="function")
def db_helper(ssh_client, config):
    """
    Provide database helper

    Args:
        ssh_client: SSH client instance
        config: Test configuration

    Returns:
        DBHelper: Database helper instance
    """
    log_settings = config.get_logging_settings()
    db_snapshot_dir = log_settings.get('db_snapshot_dir')

    return DBHelper(ssh_client, db_snapshot_dir)


@pytest.fixture(scope="function")
def cli_logger(device, request, config):
    """
    Provide CLI logger for test

    Args:
        device: Device configuration
        request: Pytest request object
        config: Test configuration

    Returns:
        CLILogger: CLI logger instance
    """
    log_settings = config.get_logging_settings()
    cli_log_dir = log_settings.get('cli_log_dir')

    test_name = request.node.name
    device_name = device['name']

    return CLILogger(cli_log_dir, device_name, test_name)


@pytest.fixture(scope="function")
def test_context(device, ssh_client, db_helper, cli_logger, config, request):
    """
    Provide complete test context with all necessary components

    Args:
        device: Device configuration
        ssh_client: SSH client
        db_helper: Database helper
        cli_logger: CLI logger
        config: Configuration
        request: Pytest request

    Returns:
        dict: Test context
    """
    test_name = request.node.name
    logger = TestLogger.get_logger("test_context")

    context = {
        'device': device,
        'ssh_client': ssh_client,
        'db_helper': db_helper,
        'cli_logger': cli_logger,
        'config': config,
        'test_name': test_name,
        'test_start_time': datetime.now(),
        'logger': logger
    }

    # Pre-test cleanup if enabled
    if config.should_cleanup_before_test():
        logger.info(f"Pre-test cleanup for {test_name} on {device['name']}")
        ssh_client.cleanup_routes()

    # Capture pre-test snapshot if enabled
    if config.should_capture_db_snapshot():
        logger.info(f"Capturing pre-test snapshot for {test_name}")
        context['snapshot_before'] = db_helper.capture_snapshot(
            f"{test_name}_before",
            device['name']
        )

    yield context

    # Capture post-test snapshot if enabled
    if config.should_capture_db_snapshot():
        logger.info(f"Capturing post-test snapshot for {test_name}")
        context['snapshot_after'] = db_helper.capture_snapshot(
            f"{test_name}_after",
            device['name']
        )

    # Post-test cleanup if enabled
    if config.should_cleanup_after_test():
        logger.info(f"Post-test cleanup for {test_name} on {device['name']}")
        ssh_client.cleanup_routes()

    # Calculate test duration
    context['test_duration'] = (datetime.now() - context['test_start_time']).total_seconds()
    logger.info(f"Test {test_name} completed in {context['test_duration']:.2f} seconds")


@pytest.fixture(scope="function")
def ipv4_test_data(config):
    """
    Provide IPv4 test data

    Returns:
        dict: IPv4 test data
    """
    return config.get_ipv4_test_data()


@pytest.fixture(scope="function")
def ipv6_test_data(config):
    """
    Provide IPv6 test data

    Returns:
        dict: IPv6 test data
    """
    return config.get_ipv6_test_data()


# Pytest hooks for metadata
def pytest_html_report_title(report):
    """Set HTML report title"""
    report.title = "Static Route CLI Test Report"


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to add custom data to test reports

    This hook captures test execution details for reporting
    """
    outcome = yield
    report = outcome.get_result()

    # Add custom attributes
    if report.when == "call":
        # Add device info if available
        if hasattr(item, 'funcargs') and 'device' in item.funcargs:
            device = item.funcargs['device']
            report.device_name = device.get('name', 'Unknown')
            report.device_host = device.get('host', 'Unknown')

        # Add test metadata
        report.test_start_time = getattr(item, 'test_start_time', None)
        report.test_duration = getattr(item, 'test_duration', None)


# Register custom markers
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "ipv4: marks tests as IPv4 related"
    )
    config.addinivalue_line(
        "markers", "ipv6: marks tests as IPv6 related"
    )
    config.addinivalue_line(
        "markers", "vrf: marks tests as VRF related"
    )
    config.addinivalue_line(
        "markers", "blackhole: marks tests as blackhole route related"
    )
    config.addinivalue_line(
        "markers", "deletion: marks tests as route deletion related"
    )
    config.addinivalue_line(
        "markers", "interface: marks tests as interface-based route related"
    )
