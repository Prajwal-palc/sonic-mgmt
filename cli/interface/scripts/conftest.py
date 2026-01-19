"""
Pytest Configuration and Fixtures
Provides shared fixtures and configuration for all tests
"""

import pytest
import yaml
import logging
import json
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from cli_connection import CLIConnection, CLICommandResult

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global test results storage
test_results = []


def pytest_configure(config):
    """Pytest configuration hook"""
    # Create necessary directories
    base_dir = Path(__file__).parent.parent
    logs_dir = base_dir / "logs"
    results_dir = base_dir / "results"

    logs_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    # Store in config for access in fixtures
    config.test_start_time = datetime.now()
    config.test_results = []


def pytest_unconfigure(config):
    """Pytest unconfiguration hook - called after all tests"""
    # Generate reports after all tests complete
    logger.info("Generating test reports...")


@pytest.fixture(scope="session")
def device_config():
    """Load device configuration from YAML file"""
    config_file = Path(__file__).parent.parent / "config" / "devices.yaml"

    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded device configuration from {config_file}")
        return config
    except Exception as e:
        logger.error(f"Failed to load device config: {str(e)}")
        pytest.fail(f"Failed to load device configuration: {str(e)}")


@pytest.fixture(scope="session")
def test_config(device_config):
    """Get test configuration"""
    return device_config.get('test_config', {})


@pytest.fixture(scope="session")
def log_dir(device_config):
    """Get logging directory"""
    log_dir = device_config.get('logging', {}).get('log_dir', '/home/adminuser/draksha/cli/interface/logs')
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    return log_dir


@pytest.fixture(scope="session")
def results_dir(device_config):
    """Get results directory"""
    results_dir = device_config.get('reporting', {}).get('results_dir', '/home/adminuser/draksha/cli/interface/results')
    Path(results_dir).mkdir(parents=True, exist_ok=True)
    return results_dir


@pytest.fixture(scope="function")
def device1_connection(device_config, log_dir, request):
    """
    Fixture for device 1 (192.168.100.97) connection
    Scope: function - new connection for each test
    """
    device_info = device_config['devices']['device1']

    logger.info(f"Creating connection to {device_info['host']}")

    connection = CLIConnection(
        host=device_info['host'],
        port=device_info['port'],
        username=device_info['username'],
        password=device_info['password'],
        cli_mode=device_info['cli_mode'],
        timeout=device_config.get('test_config', {}).get('timeout', 30)
    )

    # Connect
    if not connection.connect():
        pytest.fail(f"Failed to connect to device {device_info['host']}")

    # Store connection info for logging
    request.node.device_host = device_info['host']
    request.node.device_name = device_info['name']

    yield connection

    # Teardown: disconnect
    connection.disconnect()


@pytest.fixture(scope="function")
def device2_connection(device_config, log_dir, request):
    """
    Fixture for device 2 (192.168.100.142) connection
    Scope: function - new connection for each test
    """
    device_info = device_config['devices']['device2']

    logger.info(f"Creating connection to {device_info['host']}")

    connection = CLIConnection(
        host=device_info['host'],
        port=device_info['port'],
        username=device_info['username'],
        password=device_info['password'],
        cli_mode=device_info['cli_mode'],
        timeout=device_config.get('test_config', {}).get('timeout', 30)
    )

    # Connect
    if not connection.connect():
        pytest.fail(f"Failed to connect to device {device_info['host']}")

    # Store connection info for logging
    request.node.device_host = device_info['host']
    request.node.device_name = device_info['name']

    yield connection

    # Teardown: disconnect
    connection.disconnect()


@pytest.fixture(scope="function", params=['device1', 'device2'])
def device_connection(request, device_config, log_dir):
    """
    Parametrized fixture for both devices
    Each test will run on both devices
    """
    device_name = request.param
    device_info = device_config['devices'][device_name]

    logger.info(f"Creating connection to {device_info['host']} ({device_name})")

    connection = CLIConnection(
        host=device_info['host'],
        port=device_info['port'],
        username=device_info['username'],
        password=device_info['password'],
        cli_mode=device_info['cli_mode'],
        timeout=device_config.get('test_config', {}).get('timeout', 30)
    )

    # Connect
    if not connection.connect():
        pytest.fail(f"Failed to connect to device {device_info['host']}")

    # Store connection info for logging
    request.node.device_host = device_info['host']
    request.node.device_name = device_info.get('name', device_name)
    request.node.device_param = device_name

    yield connection

    # Teardown: disconnect
    connection.disconnect()


@pytest.fixture(scope="function")
def test_logger(request, log_dir):
    """
    Create test-specific logger and log file
    """
    test_name = request.node.name
    device_host = getattr(request.node, 'device_host', 'unknown')

    # Create test-specific log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(log_dir) / f"{test_name}_{device_host}_{timestamp}.log"

    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Create logger
    test_logger = logging.getLogger(f"test.{test_name}")
    test_logger.addHandler(file_handler)
    test_logger.setLevel(logging.DEBUG)

    test_logger.info(f"=== Starting test: {test_name} ===")
    test_logger.info(f"Device: {device_host}")

    yield test_logger

    test_logger.info(f"=== Test completed: {test_name} ===")

    # Remove handler
    test_logger.removeHandler(file_handler)
    file_handler.close()


@pytest.fixture(scope="function")
def test_data_logger(request, log_dir, results_dir):
    """
    Logger for test data (commands, responses, DB snapshots)
    """
    test_name = request.node.name
    device_host = getattr(request.node, 'device_host', 'unknown')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Data storage
    test_data = {
        "test_name": test_name,
        "device": device_host,
        "timestamp": timestamp,
        "start_time": time.time(),
        "commands": [],
        "responses": [],
        "db_snapshots": [],
        "result": None,
        "error": None
    }

    def log_command(command: str, response: str, exit_code: int = 0):
        """Log command execution"""
        test_data["commands"].append(command)
        test_data["responses"].append({
            "command": command,
            "response": response,
            "exit_code": exit_code,
            "timestamp": time.time()
        })

    def log_db_snapshot(snapshot: Dict):
        """Log database snapshot"""
        test_data["db_snapshots"].append(snapshot)

    def save():
        """Save test data to file"""
        test_data["end_time"] = time.time()
        test_data["duration"] = test_data["end_time"] - test_data["start_time"]

        # Save as JSON (exclude function objects)
        json_file = Path(log_dir) / f"{test_name}_{device_host}_{timestamp}.json"
        data_to_save = {
            "test_name": test_data["test_name"],
            "device": test_data["device"],
            "timestamp": test_data["timestamp"],
            "start_time": test_data["start_time"],
            "end_time": test_data["end_time"],
            "duration": test_data["duration"],
            "commands": test_data["commands"],
            "responses": test_data["responses"],
            "db_snapshots": test_data["db_snapshots"],
            "result": test_data.get("result"),
            "error": test_data.get("error")
        }
        with open(json_file, 'w') as f:
            json.dump(data_to_save, f, indent=2)

        # Also save detailed log
        log_file = Path(log_dir) / f"{test_name}_{device_host}_{timestamp}_detailed.log"
        with open(log_file, 'w') as f:
            f.write(f"Test: {test_name}\n")
            f.write(f"Device: {device_host}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Duration: {test_data['duration']:.2f}s\n")
            f.write("="* 80 + "\n\n")

            for resp in test_data["responses"]:
                f.write(f"Command: {resp['command']}\n")
                f.write(f"Exit Code: {resp['exit_code']}\n")
                f.write(f"Response:\n{resp['response']}\n")
                f.write("-" * 80 + "\n")

    test_data["log_command"] = log_command
    test_data["log_db_snapshot"] = log_db_snapshot
    test_data["save"] = save

    yield test_data

    # Save test data on teardown
    save()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture test results
    """
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        # Store result
        test_result = {
            "test_name": item.name,
            "test_id": item.nodeid,
            "outcome": report.outcome,
            "duration": report.duration,
            "device": getattr(item, 'device_host', 'unknown'),
            "device_name": getattr(item, 'device_name', 'unknown'),
            "timestamp": datetime.now().isoformat(),
            "markers": [marker.name for marker in item.iter_markers()]
        }

        if report.outcome == "failed":
            test_result["error"] = str(report.longrepr)

        # Add to global results
        if hasattr(item.config, 'test_results'):
            item.config.test_results.append(test_result)

        # Also store in module-level for report generation
        test_results.append(test_result)


@pytest.fixture(scope="session", autouse=True)
def generate_reports(request):
    """
    Auto-fixture to generate reports after all tests complete
    """
    yield

    # This runs after all tests
    logger.info("All tests completed. Report generation will be triggered by separate script.")


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection - add markers based on test names
    """
    for item in items:
        # Add markers based on test name patterns
        if "show" in item.name.lower():
            item.add_marker(pytest.mark.show_commands)
        if "config" in item.name.lower():
            item.add_marker(pytest.mark.config_commands)
        if "mtu" in item.name.lower():
            item.add_marker(pytest.mark.mtu)
        if "description" in item.name.lower():
            item.add_marker(pytest.mark.description)
        if "shutdown" in item.name.lower():
            item.add_marker(pytest.mark.shutdown)
        if "invalid" in item.name.lower() or "negative" in item.name.lower():
            item.add_marker(pytest.mark.negative)

        # Add device-specific markers
        if hasattr(item, 'callspec') and 'device_connection' in item.callspec.params:
            device = item.callspec.params['device_connection']
            if device == 'device1':
                item.add_marker(pytest.mark.device1)
            elif device == 'device2':
                item.add_marker(pytest.mark.device2)
