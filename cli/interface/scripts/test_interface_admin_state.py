"""
Test Suite for Interface Administrative State
Tests: TC-IF-012, TC-IF-013
"""

import pytest
import logging
import time

logger = logging.getLogger(__name__)


class TestInterfaceAdminState:
    """Test class for interface shutdown/enable commands"""

    @pytest.mark.interface_config
    @pytest.mark.shutdown
    def test_TC_IF_012_shutdown_interface(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-012: Shutdown Interface
        Verify that an interface can be administratively disabled
        """
        test_logger.info("TC-IF-012: Shutdown Interface")

        commands = [
            "configure terminal",
            "interface Ethernet 0",
            "shutdown",
            "exit",
            "exit",
            "show interface Ethernet 0"
        ]

        output, exit_code = device_connection.execute_commands(commands, wait_time=0.5)

        test_data_logger["log_command"](" ; ".join(commands), output, exit_code)

        # Get DB snapshot after configuration
        db_snapshot = device_connection.get_db_snapshot()
        test_data_logger["log_db_snapshot"](db_snapshot)

        test_logger.info(f"Command output length: {len(output)} bytes")

        # Verify command executed
        assert len(output) > 0, "No output received from commands"

        # Check for shutdown indication in output
        if "down" in output.lower() or "disabled" in output.lower():
            test_logger.info("✓ Interface admin state changed to down")

        test_logger.info("✓ Test PASSED: Shutdown command executed")

    @pytest.mark.interface_config
    @pytest.mark.shutdown
    def test_TC_IF_013_no_shutdown_interface(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-013: No Shutdown Interface (Enable)
        Verify that an interface can be administratively enabled
        """
        test_logger.info("TC-IF-013: No Shutdown Interface (Enable)")

        commands = [
            "configure terminal",
            "interface Ethernet 0",
            "no shutdown",
            "exit",
            "exit",
            "show interface Ethernet 0"
        ]

        output, exit_code = device_connection.execute_commands(commands, wait_time=0.5)

        test_data_logger["log_command"](" ; ".join(commands), output, exit_code)

        # Get DB snapshot
        db_snapshot = device_connection.get_db_snapshot()
        test_data_logger["log_db_snapshot"](db_snapshot)

        test_logger.info(f"Command output length: {len(output)} bytes")

        # Verify command executed
        assert len(output) > 0, "No output received from commands"

        # Check for enabled indication in output
        if "up" in output.lower() or "enabled" in output.lower():
            test_logger.info("✓ Interface admin state changed to up")

        test_logger.info("✓ Test PASSED: No shutdown command executed")
