"""
Enhanced SSH Client for SONiC CLI with DB Snapshot capabilities
"""

import paramiko
import time
import logging
import json
from datetime import datetime
from typing import Tuple, Optional, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)


class CommandResult:
    """Class to store command execution results"""

    def __init__(self, command: str):
        self.command = command
        self.output = ""
        self.return_code = 0
        self.start_time = datetime.now()
        self.end_time = None
        self.duration = 0
        self.error_message = None

    def complete(self, output: str, return_code: int):
        """Mark command as completed"""
        self.output = output
        self.return_code = return_code
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "command": self.command,
            "output": self.output,
            "return_code": self.return_code,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "error_message": self.error_message
        }


class EnhancedSONiCSSHClient:
    """Enhanced SSH Client with logging and DB snapshot capabilities"""

    def __init__(self, host: str, username: str, password: str, port: int = 22,
                 log_dir: str = None):
        """
        Initialize Enhanced SSH client

        Args:
            host: IP address or hostname
            username: SSH username
            password: SSH password
            port: SSH port
            log_dir: Directory to save command logs
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.log_dir = log_dir or "/home/adminuser/draksha/cli/ntp/logs"

        self.client = None
        self.shell = None
        self.in_sonic_cli = False
        self.in_config_mode = False

        # Command history
        self.command_history: List[CommandResult] = []

        # Create log directory
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)

    def connect(self) -> bool:
        """Establish SSH connection"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            logger.info(f"Connecting to {self.host}...")
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=30,
                allow_agent=False,
                look_for_keys=False
            )

            self.shell = self.client.invoke_shell()
            self.shell.settimeout(10)
            time.sleep(2)
            self._clear_buffer()

            logger.info(f"Successfully connected to {self.host}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to {self.host}: {str(e)}")
            return False

    def disconnect(self):
        """Close SSH connection"""
        try:
            if self.in_config_mode:
                self.exit_config_mode()
            if self.in_sonic_cli:
                self.exit_sonic_cli()

            if self.shell:
                self.shell.close()
            if self.client:
                self.client.close()

            logger.info(f"Disconnected from {self.host}")

        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")

    def _clear_buffer(self) -> str:
        """Clear shell buffer"""
        output = ""
        try:
            while self.shell.recv_ready():
                chunk = self.shell.recv(4096).decode('utf-8', errors='ignore')
                output += chunk
                time.sleep(0.1)
        except:
            pass
        return output

    def execute_command(self, command: str, wait_time: float = 2.0) -> Tuple[str, int]:
        """Execute command and track results"""
        cmd_result = CommandResult(command)

        try:
            self._clear_buffer()

            logger.debug(f"Executing: {command}")
            self.shell.send(command + '\n')
            time.sleep(wait_time)

            output = ""
            max_wait = 10
            start_time = time.time()

            while time.time() - start_time < max_wait:
                if self.shell.recv_ready():
                    chunk = self.shell.recv(4096).decode('utf-8', errors='ignore')
                    output += chunk
                    time.sleep(0.1)
                else:
                    time.sleep(0.2)
                    if not self.shell.recv_ready():
                        break

            # Remove echoed command
            lines = output.split('\n')
            if lines and command in lines[0]:
                output = '\n'.join(lines[1:])

            # Detect errors
            return_code = 0
            error_keywords = ['Error', 'error', 'Invalid', 'invalid', 'Failed', 'failed', 'syntax error']
            if any(keyword in output for keyword in error_keywords):
                return_code = 1

            cmd_result.complete(output, return_code)
            self.command_history.append(cmd_result)

            logger.debug(f"Output ({len(output)} chars): {output[:200]}...")

            return output, return_code

        except Exception as e:
            logger.error(f"Error executing command '{command}': {str(e)}")
            cmd_result.error_message = str(e)
            cmd_result.complete("", 1)
            self.command_history.append(cmd_result)
            return str(e), 1

    def enter_sonic_cli(self) -> Tuple[str, bool]:
        """Enter SONiC CLI mode"""
        if self.in_sonic_cli:
            return "Already in SONiC CLI mode", True

        output, rc = self.execute_command("sonic-cli", wait_time=3)

        if rc == 0 or "sonic#" in output or "sonic>" in output:
            self.in_sonic_cli = True
            logger.info("Entered SONiC CLI mode")
            return output, True
        else:
            logger.error("Failed to enter SONiC CLI mode")
            return output, False

    def exit_sonic_cli(self) -> Tuple[str, bool]:
        """Exit SONiC CLI mode"""
        if not self.in_sonic_cli:
            return "Not in SONiC CLI mode", True

        output, rc = self.execute_command("exit", wait_time=2)
        self.in_sonic_cli = False
        self.in_config_mode = False
        logger.info("Exited SONiC CLI mode")
        return output, True

    def enter_config_mode(self) -> Tuple[str, bool]:
        """Enter configuration mode"""
        if not self.in_sonic_cli:
            return "Not in SONiC CLI mode", False

        if self.in_config_mode:
            return "Already in config mode", True

        output, rc = self.execute_command("configure terminal", wait_time=2)

        if rc == 0 or "sonic(config)#" in output:
            self.in_config_mode = True
            logger.info("Entered config mode")
            return output, True
        else:
            logger.error("Failed to enter config mode")
            return output, False

    def exit_config_mode(self) -> Tuple[str, bool]:
        """Exit configuration mode"""
        if not self.in_config_mode:
            return "Not in config mode", True

        output, rc = self.execute_command("exit", wait_time=2)
        self.in_config_mode = False
        logger.info("Exited config mode")
        return output, True

    def capture_db_snapshot(self, test_id: str) -> Dict:
        """
        Capture database snapshot for NTP configuration

        Args:
            test_id: Test case ID

        Returns:
            Dict: Database snapshot
        """
        snapshot = {
            "test_id": test_id,
            "timestamp": datetime.now().isoformat(),
            "host": self.host,
            "ntp_global": None,
            "ntp_servers": None,
            "ntp_associations": None
        }

        try:
            # Exit config mode if in it
            if self.in_config_mode:
                self.exit_config_mode()

            # Capture NTP global config
            output, _ = self.execute_command("show ntp global", wait_time=2)
            snapshot["ntp_global"] = output

            # Capture NTP servers
            output, _ = self.execute_command("show ntp server", wait_time=2)
            snapshot["ntp_servers"] = output

            # Capture NTP associations
            output, _ = self.execute_command("show ntp associations", wait_time=2)
            snapshot["ntp_associations"] = output

            logger.debug(f"Captured DB snapshot for {test_id}")

        except Exception as e:
            logger.error(f"Error capturing DB snapshot: {str(e)}")
            snapshot["error"] = str(e)

        return snapshot

    def save_command_log(self, test_id: str, filename: str = None):
        """
        Save command history to log file

        Args:
            test_id: Test case ID
            filename: Custom filename (optional)
        """
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{test_id}_{self.host}_{timestamp}.json"

            filepath = Path(self.log_dir) / filename

            log_data = {
                "test_id": test_id,
                "host": self.host,
                "timestamp": datetime.now().isoformat(),
                "commands": [cmd.to_dict() for cmd in self.command_history]
            }

            with open(filepath, 'w') as f:
                json.dump(log_data, f, indent=2)

            logger.info(f"Saved command log to {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error saving command log: {str(e)}")
            return None

    def get_command_history(self) -> List[Dict]:
        """Get command history as list of dictionaries"""
        return [cmd.to_dict() for cmd in self.command_history]

    def clear_command_history(self):
        """Clear command history"""
        self.command_history.clear()

    def cleanup_ntp_config(self) -> bool:
        """Clean up all NTP configuration"""
        try:
            logger.info("Cleaning up NTP configuration...")

            # Get current servers
            output, _ = self.execute_command("show ntp server", wait_time=2)

            # Enter config mode
            self.enter_config_mode()

            # Remove servers
            cleanup_commands = [
                "no ntp server 10.10.10.1", "no ntp server 10.10.10.2",
                "no ntp server 10.10.10.3", "no ntp server 10.10.10.4",
                "no ntp server 10.10.10.5", "no ntp server 10.10.10.6",
                "no ntp server 10.10.10.7", "no ntp server 10.10.10.8",
                "no ntp server 10.10.10.9", "no ntp server 10.10.10.10",
                "no ntp server 10.10.10.11", "no ntp server 10.10.10.12",
                "no ntp server 10.10.10.100", "no ntp server 10.10.10.201",
                "no ntp server 10.10.10.202", "no ntp server 10.10.10.250",
                "no ntp server time.google.com", "no ntp server pool.ntp.org",
                "no ntp authenticate", "no ntp source-interface", "no ntp vrf",
            ]

            for cmd in cleanup_commands:
                self.execute_command(cmd, wait_time=1)

            self.exit_config_mode()

            logger.info("NTP configuration cleanup completed")
            return True

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return False


# Compatibility alias
SONiCSSHClient = EnhancedSONiCSSHClient
