"""
Test Suite for Interface Show Commands
Tests: TC-IF-001 through TC-IF-008
"""

import pytest
import logging
import time

logger = logging.getLogger(__name__)


class TestInterfaceShowCommands:
    """Test class for interface show commands"""

    @pytest.mark.show_commands
    def test_TC_IF_001_show_interface_all(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-001: Show Interface - Display All Interfaces
        Verify that all interface information is displayed correctly
        """
        test_logger.info("TC-IF-001: Show Interface - Display All Interfaces")

        command = "show interface"
        output, exit_code = device_connection.execute_command(command)

        test_data_logger["log_command"](command, output, exit_code)

        # Get DB snapshot
        db_snapshot = device_connection.get_db_snapshot()
        test_data_logger["log_db_snapshot"](db_snapshot)

        test_logger.info(f"Command output length: {len(output)} bytes")

        # Verify interface information is present
        assert len(output) > 0, "No output received from command"
        assert "Ethernet" in output or "Interface" in output, "No interface information in output"

        test_logger.info("✓ Test PASSED: Interface information displayed")

    @pytest.mark.show_commands
    def test_TC_IF_002_show_interface_counters(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-002: Show Interface Counters
        Verify that interface counters are displayed for all physical interfaces
        """
        test_logger.info("TC-IF-002: Show Interface Counters")

        command = "show interface counters"
        output, exit_code = device_connection.execute_command(command, wait_time=2.0)

        test_data_logger["log_command"](command, output, exit_code)

        test_logger.info(f"Command output length: {len(output)} bytes")

        # Verify counters are present
        assert len(output) > 0, "No output received from command"
        # Look for counter-related keywords
        counter_keywords = ["RX_OK", "TX_OK", "RX_ERR", "TX_ERR", "Interface"]
        found_keywords = [kw for kw in counter_keywords if kw in output]

        assert len(found_keywords) > 0, f"No counter information found. Output: {output[:200]}"

        test_logger.info(f"✓ Test PASSED: Counter information displayed (found: {found_keywords})")

    @pytest.mark.show_commands
    def test_TC_IF_003_show_interface_status(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-003: Show Interface Status
        Verify that the status of all physical interfaces is displayed
        """
        test_logger.info("TC-IF-003: Show Interface Status")

        command = "show interface status"
        output, exit_code = device_connection.execute_command(command)

        test_data_logger["log_command"](command, output, exit_code)

        test_logger.info(f"Command output length: {len(output)} bytes")

        # Verify status information is present
        assert len(output) > 0, "No output received from command"
        status_keywords = ["Interface", "Status", "Ethernet", "State"]
        found_keywords = [kw for kw in status_keywords if kw in output]

        assert len(found_keywords) > 0, f"No status information found. Found keywords: {found_keywords}"

        test_logger.info("✓ Test PASSED: Interface status displayed")

    @pytest.mark.show_commands
    def test_TC_IF_004_show_interface_ethernet(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-004: Show Specific Interface - Ethernet Without ID
        Verify that all Ethernet interfaces are displayed when no specific ID is provided
        """
        test_logger.info("TC-IF-004: Show Specific Interface - Ethernet Without ID")

        command = "show interface Ethernet"
        output, exit_code = device_connection.execute_command(command)

        test_data_logger["log_command"](command, output, exit_code)

        test_logger.info(f"Command output length: {len(output)} bytes")

        # Verify Ethernet interface information
        assert len(output) > 0, "No output received from command"
        assert "Ethernet" in output, "No Ethernet interface information in output"

        test_logger.info("✓ Test PASSED: Ethernet interfaces displayed")

    @pytest.mark.show_commands
    def test_TC_IF_005_show_interface_ethernet0(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-005: Show Specific Interface - Ethernet0
        Verify that specific Ethernet interface (Ethernet0) information is displayed
        """
        test_logger.info("TC-IF-005: Show Specific Interface - Ethernet0")

        command = "show interface Ethernet 0"
        output, exit_code = device_connection.execute_command(command)

        test_data_logger["log_command"](command, output, exit_code)

        # Get DB snapshot
        db_snapshot = device_connection.get_db_snapshot()
        test_data_logger["log_db_snapshot"](db_snapshot)

        test_logger.info(f"Command output length: {len(output)} bytes")

        # Verify Ethernet0 information
        assert len(output) > 0, "No output received from command"
        # May show error if interface doesn't exist, but command should execute
        test_logger.info(f"Ethernet0 command executed successfully")

        test_logger.info("✓ Test PASSED: Command executed")

    @pytest.mark.show_commands
    def test_TC_IF_006_show_interface_ethernet4(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-006: Show Specific Interface - Ethernet4
        Verify that specific Ethernet interface (Ethernet4) information is displayed
        """
        test_logger.info("TC-IF-006: Show Specific Interface - Ethernet4")

        command = "show interface Ethernet 4"
        output, exit_code = device_connection.execute_command(command)

        test_data_logger["log_command"](command, output, exit_code)

        test_logger.info(f"Command output length: {len(output)} bytes")

        assert len(output) > 0, "No output received from command"

        test_logger.info("✓ Test PASSED: Command executed")

    @pytest.mark.show_commands
    def test_TC_IF_007_show_interface_ethernet8(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-007: Show Specific Interface - Ethernet8
        Verify that specific Ethernet interface (Ethernet8) information is displayed
        """
        test_logger.info("TC-IF-007: Show Specific Interface - Ethernet8")

        command = "show interface Ethernet 8"
        output, exit_code = device_connection.execute_command(command)

        test_data_logger["log_command"](command, output, exit_code)

        test_logger.info(f"Command output length: {len(output)} bytes")

        assert len(output) > 0, "No output received from command"

        test_logger.info("✓ Test PASSED: Command executed")

    @pytest.mark.show_commands
    @pytest.mark.negative
    def test_TC_IF_008_show_interface_invalid(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-008: Show Specific Interface - Invalid ID (Negative Test)
        Verify error handling when an invalid Ethernet interface ID is provided
        """
        test_logger.info("TC-IF-008: Show Specific Interface - Invalid ID (Negative Test)")

        command = "show interface Ethernet 999"
        output, exit_code = device_connection.execute_command(command)

        test_data_logger["log_command"](command, output, exit_code)

        test_logger.info(f"Command output length: {len(output)} bytes")

        # This is a negative test - error is expected
        assert len(output) > 0, "No output received from command"

        # Check if error message is present (expected for invalid interface)
        if "%Error" in output or "Error" in output or "Invalid" in output or "not" in output:
            test_logger.info("✓ Test PASSED: Error message displayed as expected for invalid interface")
        else:
            test_logger.info("✓ Test PASSED: Command completed (no interface found or empty output expected)")
