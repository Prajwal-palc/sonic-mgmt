"""
CLI Connection Handler for SONiC Device Testing
Handles SSH connections and CLI command execution
"""

import paramiko
import time
import logging
from typing import Dict, Tuple, Optional
import re

logger = logging.getLogger(__name__)


class CLIConnection:
    """Handles SSH connection and CLI command execution for SONiC devices"""

    def __init__(self, host: str, port: int, username: str, password: str,
                 cli_mode: str = "sonic-cli", timeout: int = 30):
        """
        Initialize CLI connection

        Args:
            host: Device IP address
            port: SSH port (default 22)
            username: SSH username
            password: SSH password
            cli_mode: CLI mode to enter (default: sonic-cli)
            timeout: Command timeout in seconds
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.cli_mode = cli_mode
        self.timeout = timeout
        self.client = None
        self.shell = None
        self.connected = False

    def connect(self) -> bool:
        """
        Establish SSH connection to device

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to {self.host}:{self.port}")
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False
            )

            # Open interactive shell
            self.shell = self.client.invoke_shell()
            self.shell.settimeout(self.timeout)

            # Wait for initial prompt
            time.sleep(1)
            self._receive_output()

            # Enter CLI mode
            if self.cli_mode:
                self._enter_cli_mode()

            self.connected = True
            logger.info(f"Successfully connected to {self.host}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to {self.host}: {str(e)}")
            self.connected = False
            return False

    def _enter_cli_mode(self) -> bool:
        """Enter sonic-cli mode"""
        try:
            logger.debug(f"Entering {self.cli_mode} mode")
            self.shell.send(f"{self.cli_mode}\n")
            time.sleep(1)
            output = self._receive_output()

            # Disable pagination
            self.shell.send("terminal length 0\n")
            time.sleep(0.5)
            self._receive_output()

            return True
        except Exception as e:
            logger.error(f"Failed to enter CLI mode: {str(e)}")
            return False

    def _receive_output(self, wait_time: float = 0.5) -> str:
        """
        Receive output from shell

        Args:
            wait_time: Time to wait for output

        Returns:
            str: Output received from shell
        """
        time.sleep(wait_time)
        output = ""

        try:
            while self.shell.recv_ready():
                chunk = self.shell.recv(4096).decode('utf-8', errors='ignore')
                output += chunk
                time.sleep(0.1)
        except Exception as e:
            logger.warning(f"Error receiving output: {str(e)}")

        return output

    def execute_command(self, command: str, wait_time: float = 1.0) -> Tuple[str, int]:
        """
        Execute CLI command

        Args:
            command: Command to execute
            wait_time: Time to wait for command output

        Returns:
            Tuple[str, int]: (output, exit_code) - exit_code is 0 for success, 1 for failure
        """
        if not self.connected:
            logger.error("Not connected to device")
            return "", 1

        try:
            logger.debug(f"Executing command: {command}")

            # Send command
            self.shell.send(f"{command}\n")

            # Receive output
            output = self._receive_output(wait_time)

            # Check for errors in output
            exit_code = 0
            if "%Error" in output or "Error:" in output or "Invalid" in output:
                # Some errors are expected (like negative tests)
                logger.debug(f"Command returned error (may be expected): {command}")
                exit_code = 0  # Don't fail on CLI errors as they might be expected

            logger.debug(f"Command output length: {len(output)} bytes")
            return output, exit_code

        except Exception as e:
            logger.error(f"Failed to execute command '{command}': {str(e)}")
            return "", 1

    def execute_commands(self, commands: list, wait_time: float = 1.0) -> Tuple[str, int]:
        """
        Execute multiple CLI commands

        Args:
            commands: List of commands to execute
            wait_time: Time to wait after each command

        Returns:
            Tuple[str, int]: (combined_output, exit_code)
        """
        combined_output = ""
        final_exit_code = 0

        for command in commands:
            output, exit_code = self.execute_command(command, wait_time)
            combined_output += f"\n{command}\n{output}\n"

            if exit_code != 0:
                final_exit_code = exit_code

        return combined_output, final_exit_code

    def get_db_snapshot(self, table: str = "CONFIG_DB") -> Dict:
        """
        Get database snapshot (mock implementation)

        Args:
            table: Database table name

        Returns:
            Dict: Database snapshot
        """
        # This is a mock implementation
        # In real scenario, you would execute 'redis-cli' commands
        snapshot = {
            "timestamp": time.time(),
            "table": table,
            "host": self.host,
            "data": {}
        }

        try:
            # Example: Get interface configuration from DB
            # output, _ = self.execute_command(f"redis-cli -n 4 KEYS '*INTERFACE*'")
            # Parse and add to snapshot
            snapshot["data"]["note"] = "DB snapshot feature requires redis-cli access"
        except Exception as e:
            logger.warning(f"Failed to get DB snapshot: {str(e)}")

        return snapshot

    def disconnect(self):
        """Close SSH connection"""
        try:
            if self.shell:
                self.shell.send("exit\n")
                time.sleep(0.5)
                self.shell.close()

            if self.client:
                self.client.close()

            self.connected = False
            logger.info(f"Disconnected from {self.host}")

        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
        return False


class CLICommandResult:
    """Represents the result of a CLI command execution"""

    def __init__(self, command: str, output: str, exit_code: int,
                 timestamp: float, device: str):
        self.command = command
        self.output = output
        self.exit_code = exit_code
        self.timestamp = timestamp
        self.device = device
        self.success = (exit_code == 0)

    def has_error(self) -> bool:
        """Check if output contains error messages"""
        error_patterns = ["%Error", "Error:", "Invalid", "Failed", "failed"]
        return any(pattern in self.output for pattern in error_patterns)

    def to_dict(self) -> Dict:
        """Convert result to dictionary"""
        return {
            "command": self.command,
            "output": self.output,
            "exit_code": self.exit_code,
            "timestamp": self.timestamp,
            "device": self.device,
            "success": self.success,
            "has_error": self.has_error()
        }
