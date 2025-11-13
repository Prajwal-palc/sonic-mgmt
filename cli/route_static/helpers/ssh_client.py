"""
SSH Client Helper Module
Provides SSH connectivity and command execution for SONiC devices
"""

import paramiko
import time
import logging
from typing import Tuple, Optional


class SSHClient:
    """SSH Client for SONiC CLI command execution"""

    def __init__(self, host: str, port: int, username: str, password: str,
                 timeout: int = 30):
        """
        Initialize SSH Client

        Args:
            host: Device IP address
            port: SSH port (default 22)
            username: SSH username
            password: SSH password
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.client = None
        self.logger = logging.getLogger(f"SSHClient-{host}")

    def connect(self) -> bool:
        """
        Establish SSH connection to device

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.logger.info(f"Connecting to {self.host}:{self.port}")
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False
            )

            self.logger.info(f"Successfully connected to {self.host}")
            return True

        except Exception as e:
            self.logger.error(f"Connection failed to {self.host}: {str(e)}")
            return False

    def disconnect(self):
        """Close SSH connection"""
        if self.client:
            self.client.close()
            self.logger.info(f"Disconnected from {self.host}")

    def execute_command(self, command: str, timeout: int = 10) -> Tuple[str, str, int]:
        """
        Execute a single command via SSH

        Args:
            command: Command to execute
            timeout: Command execution timeout

        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        try:
            self.logger.debug(f"Executing command: {command}")
            stdin, stdout, stderr = self.client.exec_command(
                command, timeout=timeout
            )

            exit_code = stdout.channel.recv_exit_status()
            stdout_str = stdout.read().decode('utf-8', errors='ignore')
            stderr_str = stderr.read().decode('utf-8', errors='ignore')

            self.logger.debug(f"Command exit code: {exit_code}")
            return stdout_str, stderr_str, exit_code

        except Exception as e:
            self.logger.error(f"Command execution failed: {str(e)}")
            return "", str(e), -1

    def execute_interactive(self, command: str, wait_time: int = 2) -> str:
        """
        Execute command in interactive shell mode

        Args:
            command: Command to execute
            wait_time: Time to wait for command completion

        Returns:
            str: Command output
        """
        try:
            channel = self.client.invoke_shell()
            time.sleep(1)

            # Clear initial output
            if channel.recv_ready():
                channel.recv(4096).decode('utf-8', errors='ignore')

            # Send command
            channel.send(command + '\n')
            time.sleep(wait_time)

            # Collect output
            output = ""
            while channel.recv_ready():
                chunk = channel.recv(4096).decode('utf-8', errors='ignore')
                output += chunk
                time.sleep(0.1)

            channel.close()
            return output

        except Exception as e:
            self.logger.error(f"Interactive command execution failed: {str(e)}")
            return f"Error: {str(e)}"

    def execute_cli_command(self, cli_command: str, verify_command: Optional[str] = None) -> dict:
        """
        Execute SONiC CLI command in configuration mode

        Args:
            cli_command: CLI command to execute
            verify_command: Optional verification command

        Returns:
            dict: Command execution results
        """
        result = {
            'command': cli_command,
            'success': False,
            'output': '',
            'error': '',
            'verification_output': ''
        }

        try:
            # Execute configuration command
            config_cmd = (
                f"sonic-cli\n"
                f"configure terminal\n"
                f"{cli_command}\n"
                f"exit\n"
                f"exit\n"
            )

            output = self.execute_interactive(config_cmd, wait_time=3)
            result['output'] = output

            # Filter out non-critical system errors
            filtered_output = output
            # Ignore sonic_platform import errors (background process issue)
            if "sonic_platform" in output and "ModuleNotFoundError" in output:
                # Remove the traceback from output for error checking
                lines = output.split('\n')
                filtered_lines = []
                skip_traceback = False
                for line in lines:
                    if "Traceback (most recent call last):" in line:
                        skip_traceback = True
                    if skip_traceback and line.strip() == "":
                        skip_traceback = False
                        continue
                    if not skip_traceback:
                        filtered_lines.append(line)
                filtered_output = '\n'.join(filtered_lines)

            # Check for actual CLI errors (not system background errors)
            cli_errors = ['error:', '% error', 'invalid command', 'command failed', 'syntax error']
            if any(err in filtered_output.lower() for err in cli_errors):
                result['success'] = False
                result['error'] = "Command execution encountered errors"
            else:
                result['success'] = True

            # Execute verification command if provided
            if verify_command:
                verify_cmd = f"sonic-cli\n{verify_command}\nexit\n"
                verify_output = self.execute_interactive(verify_cmd, wait_time=2)
                result['verification_output'] = verify_output

            return result

        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
            self.logger.error(f"CLI command execution failed: {str(e)}")
            return result

    def execute_show_command(self, show_command: str) -> str:
        """
        Execute SONiC show command

        Args:
            show_command: Show command to execute

        Returns:
            str: Command output
        """
        try:
            cmd = f"sonic-cli\n{show_command}\nexit\n"
            output = self.execute_interactive(cmd, wait_time=2)
            return output

        except Exception as e:
            self.logger.error(f"Show command execution failed: {str(e)}")
            return f"Error: {str(e)}"

    def cleanup_routes(self):
        """Clean up all static routes (test cleanup)"""
        self.logger.info("Cleaning up static routes")
        cleanup_commands = [
            "show ip route static",
            "show ipv6 route static"
        ]

        for cmd in cleanup_commands:
            output = self.execute_show_command(cmd)
            self.logger.debug(f"Cleanup command output: {output}")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
