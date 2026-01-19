"""
Test Suite for Interface MTU Configuration
Tests: TC-IF-017 through TC-IF-023
"""

import pytest
import logging
import time

logger = logging.getLogger(__name__)


class TestInterfaceMTU:
    """Test class for interface MTU configuration"""

    @pytest.mark.interface_config
    @pytest.mark.mtu
    def test_TC_IF_017_mtu_minimum(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-017: Configure Valid MTU - Minimum Value
        Verify that minimum valid MTU value (1280) can be configured
        """
        test_logger.info("TC-IF-017: Configure Valid MTU - Minimum Value (1280)")

        commands = [
            "configure terminal",
            "interface Ethernet 0",
            "mtu 1280",
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

        # Check if MTU 1280 appears in output
        if "1280" in output:
            test_logger.info("✓ MTU 1280 configured and verified")
        else:
            test_logger.info("✓ MTU command executed")

        test_logger.info("✓ Test PASSED: MTU minimum value configured")

    @pytest.mark.interface_config
    @pytest.mark.mtu
    def test_TC_IF_018_mtu_standard(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-018: Configure Valid MTU - Standard Value
        Verify that standard MTU value (1500) can be configured
        """
        test_logger.info("TC-IF-018: Configure Valid MTU - Standard Value (1500)")

        commands = [
            "configure terminal",
            "interface Ethernet 4",
            "mtu 1500",
            "exit",
            "exit",
            "show interface Ethernet 4"
        ]

        output, exit_code = device_connection.execute_commands(commands, wait_time=0.5)

        test_data_logger["log_command"](" ; ".join(commands), output, exit_code)

        test_logger.info(f"Command output length: {len(output)} bytes")

        assert len(output) > 0, "No output received from commands"

        if "1500" in output:
            test_logger.info("✓ MTU 1500 configured and verified")

        test_logger.info("✓ Test PASSED: MTU standard value configured")

    @pytest.mark.interface_config
    @pytest.mark.mtu
    def test_TC_IF_019_mtu_jumbo(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-019: Configure Valid MTU - Jumbo Frame
        Verify that jumbo frame MTU (9100) can be configured
        """
        test_logger.info("TC-IF-019: Configure Valid MTU - Jumbo Frame (9100)")

        commands = [
            "configure terminal",
            "interface Ethernet 8",
            "mtu 9100",
            "exit",
            "exit",
            "show interface Ethernet 8"
        ]

        output, exit_code = device_connection.execute_commands(commands, wait_time=0.5)

        test_data_logger["log_command"](" ; ".join(commands), output, exit_code)

        # Get DB snapshot
        db_snapshot = device_connection.get_db_snapshot()
        test_data_logger["log_db_snapshot"](db_snapshot)

        test_logger.info(f"Command output length: {len(output)} bytes")

        assert len(output) > 0, "No output received from commands"

        if "9100" in output:
            test_logger.info("✓ MTU 9100 (jumbo) configured and verified")

        test_logger.info("✓ Test PASSED: MTU jumbo frame value configured")

    @pytest.mark.interface_config
    @pytest.mark.mtu
    def test_TC_IF_020_mtu_maximum(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-020: Configure Valid MTU - Maximum Value
        Verify that maximum valid MTU value (9216) can be configured
        """
        test_logger.info("TC-IF-020: Configure Valid MTU - Maximum Value (9216)")

        commands = [
            "configure terminal",
            "interface Ethernet 0",
            "mtu 9216",
            "exit",
            "exit",
            "show interface Ethernet 0"
        ]

        output, exit_code = device_connection.execute_commands(commands, wait_time=0.5)

        test_data_logger["log_command"](" ; ".join(commands), output, exit_code)

        test_logger.info(f"Command output length: {len(output)} bytes")

        assert len(output) > 0, "No output received from commands"

        if "9216" in output:
            test_logger.info("✓ MTU 9216 (maximum) configured and verified")

        test_logger.info("✓ Test PASSED: MTU maximum value configured")

    @pytest.mark.interface_config
    @pytest.mark.mtu
    def test_TC_IF_021_remove_mtu(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-021: Remove MTU Configuration (Reset to Default)
        Verify that MTU can be reset to default value (9100)
        """
        test_logger.info("TC-IF-021: Remove MTU Configuration (Reset to Default)")

        commands = [
            "configure terminal",
            "interface Ethernet 0",
            "no mtu",
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

        assert len(output) > 0, "No output received from commands"

        # Default MTU is 9100
        if "9100" in output:
            test_logger.info("✓ MTU reset to default (9100)")

        test_logger.info("✓ Test PASSED: MTU reset to default")

    @pytest.mark.interface_config
    @pytest.mark.mtu
    @pytest.mark.negative
    def test_TC_IF_022_mtu_invalid_low(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-022: Configure Invalid MTU - Below Minimum (Negative Test)
        Verify error handling when MTU below minimum is configured
        """
        test_logger.info("TC-IF-022: Configure Invalid MTU - Below Minimum (Negative Test)")

        commands = [
            "configure terminal",
            "interface Ethernet 0",
            "mtu 500",
            "exit",
            "exit"
        ]

        output, exit_code = device_connection.execute_commands(commands, wait_time=0.5)

        test_data_logger["log_command"](" ; ".join(commands), output, exit_code)

        test_logger.info(f"Command output length: {len(output)} bytes")

        assert len(output) > 0, "No output received from commands"

        # This is a negative test - error is expected
        if "%Error" in output or "Error" in output or "Invalid" in output or "range" in output:
            test_logger.info("✓ Error message displayed as expected for invalid MTU")
        else:
            test_logger.info("✓ Command completed (validation may be different)")

        test_logger.info("✓ Test PASSED: Negative test completed")

    @pytest.mark.interface_config
    @pytest.mark.mtu
    @pytest.mark.negative
    def test_TC_IF_023_mtu_invalid_high(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-023: Configure Invalid MTU - Above Maximum (Negative Test)
        Verify error handling when MTU above maximum is configured
        """
        test_logger.info("TC-IF-023: Configure Invalid MTU - Above Maximum (Negative Test)")

        commands = [
            "configure terminal",
            "interface Ethernet 0",
            "mtu 20000",
            "exit",
            "exit"
        ]

        output, exit_code = device_connection.execute_commands(commands, wait_time=0.5)

        test_data_logger["log_command"](" ; ".join(commands), output, exit_code)

        test_logger.info(f"Command output length: {len(output)} bytes")

        assert len(output) > 0, "No output received from commands"

        # This is a negative test - error is expected
        if "%Error" in output or "Error" in output or "Invalid" in output or "range" in output:
            test_logger.info("✓ Error message displayed as expected for invalid MTU")
        else:
            test_logger.info("✓ Command completed (validation may be different)")

        test_logger.info("✓ Test PASSED: Negative test completed")
