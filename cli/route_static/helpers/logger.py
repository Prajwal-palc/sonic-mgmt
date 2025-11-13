"""
Custom Logger Module
Provides enhanced logging capabilities for test execution
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class TestLogger:
    """Custom logger for test framework"""

    _loggers = {}

    @staticmethod
    def setup_logger(name: str, log_dir: str, level: str = "INFO") -> logging.Logger:
        """
        Set up a logger instance

        Args:
            name: Logger name
            log_dir: Directory for log files
            level: Logging level

        Returns:
            logging.Logger: Configured logger instance
        """
        if name in TestLogger._loggers:
            return TestLogger._loggers[name]

        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))
        logger.handlers = []  # Clear existing handlers

        # Create log directory
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)

        # File handler
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_path / f"{name}_{timestamp}.log"
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)

        # Add handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        TestLogger._loggers[name] = logger
        return logger

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        Get existing logger or create new one

        Args:
            name: Logger name

        Returns:
            logging.Logger: Logger instance
        """
        if name in TestLogger._loggers:
            return TestLogger._loggers[name]
        return logging.getLogger(name)


class CLILogger:
    """Logger specifically for CLI command execution"""

    def __init__(self, log_dir: str, device_name: str, test_name: str):
        """
        Initialize CLI Logger

        Args:
            log_dir: Directory for CLI logs
            device_name: Device name
            test_name: Test case name
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.device_name = device_name
        self.test_name = test_name
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"{device_name}_{test_name}_{self.timestamp}.log"
        self.logger = logging.getLogger(f"CLILogger-{device_name}-{test_name}")

    def log_command(self, command: str, output: str, success: bool = True):
        """
        Log CLI command and its output

        Args:
            command: CLI command executed
            output: Command output
            success: Whether command succeeded
        """
        with open(self.log_file, 'a') as f:
            f.write("=" * 80 + "\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Device: {self.device_name}\n")
            f.write(f"Test: {self.test_name}\n")
            f.write(f"Command: {command}\n")
            f.write(f"Status: {'SUCCESS' if success else 'FAILED'}\n")
            f.write("-" * 80 + "\n")
            f.write("Output:\n")
            f.write(output + "\n")
            f.write("=" * 80 + "\n\n")

    def log_verification(self, verify_command: str, output: str):
        """
        Log verification command and output

        Args:
            verify_command: Verification command
            output: Command output
        """
        with open(self.log_file, 'a') as f:
            f.write("=" * 80 + "\n")
            f.write(f"Verification Command: {verify_command}\n")
            f.write("-" * 80 + "\n")
            f.write("Output:\n")
            f.write(output + "\n")
            f.write("=" * 80 + "\n\n")

    def log_error(self, error: str):
        """
        Log error message

        Args:
            error: Error message
        """
        with open(self.log_file, 'a') as f:
            f.write("=" * 80 + "\n")
            f.write(f"ERROR - {datetime.now().isoformat()}\n")
            f.write("-" * 80 + "\n")
            f.write(error + "\n")
            f.write("=" * 80 + "\n\n")

    def get_log_path(self) -> str:
        """
        Get log file path

        Returns:
            str: Log file path
        """
        return str(self.log_file)
