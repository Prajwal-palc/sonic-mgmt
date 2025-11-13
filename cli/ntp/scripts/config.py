"""
Enhanced Configuration for NTP CLI Test Framework
Supports configurable parameters: Host IP, Port, Username, Password
"""

import os
import yaml

# Base directories
BASE_DIR = "/home/adminuser/draksha"
CLI_BASE_DIR = os.path.join(BASE_DIR, "cli/ntp")
SCRIPTS_DIR = os.path.join(CLI_BASE_DIR, "scripts")
LOGS_DIR = os.path.join(CLI_BASE_DIR, "logs")
RESULTS_DIR = os.path.join(BASE_DIR, "ntp/cli/results")
DOCS_DIR = os.path.join(BASE_DIR, "ntp/docs")

# Ensure directories exist
for directory in [SCRIPTS_DIR, LOGS_DIR, RESULTS_DIR, DOCS_DIR]:
    os.makedirs(directory, exist_ok=True)

# VS Instance Configuration - CONFIGURABLE
VS_INSTANCES = [
    {
        "name": "VS1",
        "host": "192.168.100.97",
        "port": 22,
        "username": "admin",
        "password": "YourPaSsWoRd",
        "enabled": True
    },
    {
        "name": "VS2",
        "host": "192.168.100.142",
        "port": 22,
        "username": "admin",
        "password": "YourPaSsWoRd",
        "enabled": True
    }
]

# Filter only enabled instances
ACTIVE_INSTANCES = [inst for inst in VS_INSTANCES if inst.get("enabled", True)]

# Test Configuration
TEST_CONFIG = {
    "command_wait_time": 2.0,  # seconds
    "connection_timeout": 30,  # seconds
    "max_retries": 3,
    "cleanup_after_test": True,
    "capture_db_snapshot": True,
    "verbose_logging": True
}

# Logging Configuration
LOG_CONFIG = {
    "log_level": "DEBUG",
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "console_level": "INFO",
    "file_level": "DEBUG"
}

# Report Configuration
REPORT_CONFIG = {
    "generate_html": True,
    "generate_json": True,
    "generate_markdown": True,
    "include_screenshots": False,
    "include_db_snapshots": True,
    "professional_format": True
}

# NTP Test Data
NTP_TEST_DATA = {
    "servers": [
        "10.10.10.1", "10.10.10.2", "10.10.10.3", "10.10.10.4", "10.10.10.5",
        "10.10.10.6", "10.10.10.7", "10.10.10.8", "10.10.10.9", "10.10.10.10",
        "10.10.10.11", "10.10.10.12", "10.10.10.13", "10.10.10.14",
        "10.10.10.100", "10.10.10.201", "10.10.10.202", "10.10.10.250",
        "time.google.com", "pool.ntp.org"
    ],
    "auth_keys": {
        "md5": list(range(1, 6)),
        "sha1": list(range(10, 15)),
        "sha256": list(range(20, 25)),
        "sha384": list(range(30, 35)),
        "sha512": list(range(40, 45))
    },
    "interfaces": ["Ethernet0", "Management0"],
    "vrfs": ["mgmt", "default"],
    "versions": [3, 4]
}


def load_config_from_file(config_file: str = None):
    """
    Load configuration from YAML file

    Args:
        config_file: Path to YAML configuration file

    Returns:
        dict: Configuration dictionary
    """
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                custom_config = yaml.safe_load(f)
                return custom_config
        except Exception as e:
            print(f"Warning: Failed to load config from {config_file}: {e}")
    return None


def get_vs_instance_by_name(name: str):
    """Get VS instance configuration by name"""
    for instance in VS_INSTANCES:
        if instance['name'] == name:
            return instance
    return None


def get_active_instances():
    """Get list of active VS instances"""
    return ACTIVE_INSTANCES


# Export configuration
__all__ = [
    'BASE_DIR', 'CLI_BASE_DIR', 'SCRIPTS_DIR', 'LOGS_DIR', 'RESULTS_DIR', 'DOCS_DIR',
    'VS_INSTANCES', 'ACTIVE_INSTANCES', 'TEST_CONFIG', 'LOG_CONFIG', 'REPORT_CONFIG',
    'NTP_TEST_DATA', 'load_config_from_file', 'get_vs_instance_by_name', 'get_active_instances'
]
