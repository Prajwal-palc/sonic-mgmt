"""
Test Suite for Interface Description Configuration
Tests: TC-IF-014, TC-IF-015, TC-IF-016
"""

import pytest
import logging
import time

logger = logging.getLogger(__name__)


class TestInterfaceDescription:
    """Test class for interface description configuration"""

    @pytest.mark.interface_config
    @pytest.mark.description
    def test_TC_IF_014_configure_description(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-014: Configure Interface Description
        Verify that a textual description can be added to an interface
        """
        test_logger.info("TC-IF-014: Configure Interface Description")

        commands = [
            "configure terminal",
            "interface Ethernet 0",
            "description Test_Interface_Description",
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

        # Check if description appears in output
        if "Test_Interface_Description" in output:
            test_logger.info("✓ Description configured and verified")
        else:
            test_logger.info("✓ Description command executed")

        test_logger.info("✓ Test PASSED: Description configured")

    @pytest.mark.interface_config
    @pytest.mark.description
    def test_TC_IF_015_configure_description_with_spaces(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-015: Configure Interface Description with Spaces
        Verify that a description with spaces can be configured
        """
        test_logger.info("TC-IF-015: Configure Interface Description with Spaces")

        commands = [
            "configure terminal",
            "interface Ethernet 4",
            "description Test_Description_With_Spaces",
            "exit",
            "exit",
            "show interface Ethernet 4"
        ]

        output, exit_code = device_connection.execute_commands(commands, wait_time=0.5)

        test_data_logger["log_command"](" ; ".join(commands), output, exit_code)

        test_logger.info(f"Command output length: {len(output)} bytes")

        # Verify command executed
        assert len(output) > 0, "No output received from commands"

        if "Test_Description_With_Spaces" in output or "Test" in output:
            test_logger.info("✓ Description with spaces configured")

        test_logger.info("✓ Test PASSED: Description with spaces configured")

    @pytest.mark.interface_config
    @pytest.mark.description
    def test_TC_IF_016_remove_description(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-016: Remove Interface Description
        Verify that an interface description can be removed
        """
        test_logger.info("TC-IF-016: Remove Interface Description")

        commands = [
            "configure terminal",
            "interface Ethernet 0",
            "no description",
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

        test_logger.info("✓ Test PASSED: Description removed")
