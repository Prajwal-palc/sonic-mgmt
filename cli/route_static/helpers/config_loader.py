"""
Configuration Loader Module
Loads and validates test configuration from YAML files
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any


class ConfigLoader:
    """Configuration loader and validator"""

    def __init__(self, config_file: str = None):
        """
        Initialize Config Loader

        Args:
            config_file: Path to configuration file
        """
        if config_file is None:
            config_file = Path(__file__).parent.parent / "config" / "config.yaml"
        else:
            config_file = Path(config_file)

        self.config_file = config_file
        self.config = {}
        self.logger = logging.getLogger("ConfigLoader")
        self.load_config()

    def load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                self.config = yaml.safe_load(f)
            self.logger.info(f"Configuration loaded from: {self.config_file}")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            raise

    def get_devices(self) -> List[Dict[str, Any]]:
        """
        Get list of test devices

        Returns:
            list: List of device configurations
        """
        devices = self.config.get('devices', [])
        return [d for d in devices if d.get('enabled', True)]

    def get_device_by_name(self, name: str) -> Dict[str, Any]:
        """
        Get device configuration by name

        Args:
            name: Device name

        Returns:
            dict: Device configuration
        """
        devices = self.get_devices()
        for device in devices:
            if device.get('name') == name:
                return device
        return None

    def get_ssh_settings(self) -> Dict[str, Any]:
        """Get SSH connection settings"""
        return self.config.get('ssh', {})

    def get_cli_settings(self) -> Dict[str, Any]:
        """Get CLI settings"""
        return self.config.get('cli', {})

    def get_logging_settings(self) -> Dict[str, Any]:
        """Get logging settings"""
        return self.config.get('logging', {})

    def get_results_settings(self) -> Dict[str, Any]:
        """Get results settings"""
        return self.config.get('results', {})

    def get_test_data(self) -> Dict[str, Any]:
        """Get test data configuration"""
        return self.config.get('test_data', {})

    def get_ipv4_test_data(self) -> Dict[str, Any]:
        """Get IPv4 test data"""
        return self.get_test_data().get('ipv4', {})

    def get_ipv6_test_data(self) -> Dict[str, Any]:
        """Get IPv6 test data"""
        return self.get_test_data().get('ipv6', {})

    def get_vrf_config(self) -> Dict[str, Any]:
        """Get VRF configuration"""
        return self.config.get('vrf', {})

    def get_interface_config(self) -> Dict[str, Any]:
        """Get interface configuration"""
        return self.config.get('interfaces', {})

    def get_execution_settings(self) -> Dict[str, Any]:
        """Get execution settings"""
        return self.config.get('execution', {})

    def get_database_settings(self) -> Dict[str, Any]:
        """Get database settings"""
        return self.config.get('database', {})

    def get_reporting_settings(self) -> Dict[str, Any]:
        """Get reporting settings"""
        return self.config.get('reporting', {})

    def is_vrf_enabled(self) -> bool:
        """Check if VRF testing is enabled"""
        return self.get_vrf_config().get('enabled', False)

    def is_interface_enabled(self) -> bool:
        """Check if interface testing is enabled"""
        return self.get_interface_config().get('enabled', False)

    def should_capture_db_snapshot(self) -> bool:
        """Check if DB snapshot capture is enabled"""
        return self.get_execution_settings().get('capture_db_snapshot', True)

    def should_cleanup_before_test(self) -> bool:
        """Check if cleanup before test is enabled"""
        return self.get_execution_settings().get('cleanup_before_test', True)

    def should_cleanup_after_test(self) -> bool:
        """Check if cleanup after test is enabled"""
        return self.get_execution_settings().get('cleanup_after_test', True)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def validate_config(self) -> bool:
        """
        Validate configuration

        Returns:
            bool: True if configuration is valid
        """
        required_keys = ['devices', 'ssh', 'cli', 'logging', 'results']

        for key in required_keys:
            if key not in self.config:
                self.logger.error(f"Missing required configuration key: {key}")
                return False

        # Validate devices
        devices = self.get_devices()
        if not devices:
            self.logger.error("No enabled devices found in configuration")
            return False

        for device in devices:
            required_device_keys = ['name', 'host', 'username', 'password']
            for key in required_device_keys:
                if key not in device:
                    self.logger.error(f"Device missing required key: {key}")
                    return False

        self.logger.info("Configuration validation successful")
        return True
