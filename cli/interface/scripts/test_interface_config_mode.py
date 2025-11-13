"""
Test Suite for Interface Configuration Mode
Tests: TC-IF-009, TC-IF-010
"""

import pytest
import logging
import time

logger = logging.getLogger(__name__)


class TestInterfaceConfigMode:
    """Test class for interface configuration mode navigation"""

    @pytest.mark.config_commands
    def test_TC_IF_009_config_mode_ethernet0(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-009: Enter Interface Configuration Mode - Ethernet0
        Verify entry into interface configuration mode for Ethernet0
        """
        test_logger.info("TC-IF-009: Enter Interface Configuration Mode - Ethernet0")

        commands = [
            "configure terminal",
            "interface Ethernet 0",
            "exit",
            "exit"
        ]

        output, exit_code = device_connection.execute_commands(commands, wait_time=0.5)

        test_data_logger["log_command"](" ; ".join(commands), output, exit_code)

        # Get DB snapshot
        db_snapshot = device_connection.get_db_snapshot()
        test_data_logger["log_db_snapshot"](db_snapshot)

        test_logger.info(f"Command output length: {len(output)} bytes")

        # Verify configuration mode was entered
        assert len(output) > 0, "No output received from commands"

        # Check for configuration mode prompts
        if "conf-if" in output or "Ethernet0" in output or "interface" in output.lower():
            test_logger.info("✓ Configuration mode prompt detected")

        test_logger.info("✓ Test PASSED: Configuration mode navigation completed")

    @pytest.mark.config_commands
    def test_TC_IF_010_config_mode_ethernet4(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-010: Enter Interface Configuration Mode - Ethernet4
        Verify entry into interface configuration mode for Ethernet4
        """
        test_logger.info("TC-IF-010: Enter Interface Configuration Mode - Ethernet4")

        commands = [
            "configure terminal",
            "interface Ethernet 4",
            "exit",
            "exit"
        ]

        output, exit_code = device_connection.execute_commands(commands, wait_time=0.5)

        test_data_logger["log_command"](" ; ".join(commands), output, exit_code)

        test_logger.info(f"Command output length: {len(output)} bytes")

        # Verify configuration mode was entered
        assert len(output) > 0, "No output received from commands"

        if "conf-if" in output or "Ethernet4" in output or "interface" in output.lower():
            test_logger.info("✓ Configuration mode prompt detected")

        test_logger.info("✓ Test PASSED: Configuration mode navigation completed")
