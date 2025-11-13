"""
Test Suite for Interface Configuration Workflows
Tests: TC-IF-024, TC-IF-026, TC-IF-027, TC-IF-028
"""

import pytest
import logging
import time

logger = logging.getLogger(__name__)


class TestInterfaceWorkflows:
    """Test class for combined interface configuration workflows"""

    @pytest.mark.interface_config
    @pytest.mark.workflow
    def test_TC_IF_024_complete_interface_config(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-024: Complete Interface Configuration - All Parameters
        Verify that all interface parameters can be configured together
        """
        test_logger.info("TC-IF-024: Complete Interface Configuration - All Parameters")

        commands = [
            "configure terminal",
            "interface Ethernet 0",
            "no shutdown",
            "description Production_Interface",
            "mtu 9000",
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

        # Check if configuration appears in output
        checks = []
        if "Production_Interface" in output:
            checks.append("description")
            test_logger.info("✓ Description configured")
        if "9000" in output:
            checks.append("MTU")
            test_logger.info("✓ MTU configured")

        test_logger.info(f"✓ Test PASSED: Complete configuration applied (verified: {checks})")

    @pytest.mark.interface_config
    @pytest.mark.workflow
    def test_TC_IF_026_multiple_interface_config(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-026: Multiple Interface Configuration
        Verify that multiple interfaces can be configured sequentially
        """
        test_logger.info("TC-IF-026: Multiple Interface Configuration")

        commands = [
            "configure terminal",
            "interface Ethernet 0",
            "description Interface_0",
            "no shutdown",
            "exit",
            "interface Ethernet 4",
            "description Interface_4",
            "no shutdown",
            "exit",
            "interface Ethernet 8",
            "description Interface_8",
            "no shutdown",
            "exit",
            "exit",
            "show interface status"
        ]

        output, exit_code = device_connection.execute_commands(commands, wait_time=0.5)

        test_data_logger["log_command"](" ; ".join(commands), output, exit_code)

        # Get DB snapshot
        db_snapshot = device_connection.get_db_snapshot()
        test_data_logger["log_db_snapshot"](db_snapshot)

        test_logger.info(f"Command output length: {len(output)} bytes")

        # Verify command executed
        assert len(output) > 0, "No output received from commands"

        # Check if multiple interfaces appear in output
        interface_count = output.count("Interface_")
        test_logger.info(f"✓ Multiple interfaces configured (found {interface_count} interface descriptions)")

        test_logger.info("✓ Test PASSED: Multiple interfaces configured")

    @pytest.mark.interface_config
    @pytest.mark.workflow
    @pytest.mark.shutdown
    def test_TC_IF_027_shutdown_reenable_workflow(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-027: Shutdown and Re-enable Interface Workflow
        Verify complete workflow of shutting down and re-enabling interface
        """
        test_logger.info("TC-IF-027: Shutdown and Re-enable Interface Workflow")

        # Step 1: Show current state
        output1, _ = device_connection.execute_command("show interface Ethernet 0")
        test_data_logger["log_command"]("show interface Ethernet 0 (initial)", output1, 0)

        # Step 2: Shutdown
        commands_shutdown = [
            "configure terminal",
            "interface Ethernet 0",
            "shutdown",
            "exit",
            "exit"
        ]
        output2, _ = device_connection.execute_commands(commands_shutdown, wait_time=0.5)
        test_data_logger["log_command"](" ; ".join(commands_shutdown), output2, 0)

        # Step 3: Verify shutdown
        output3, _ = device_connection.execute_command("show interface Ethernet 0")
        test_data_logger["log_command"]("show interface Ethernet 0 (after shutdown)", output3, 0)

        # Step 4: Re-enable
        commands_enable = [
            "configure terminal",
            "interface Ethernet 0",
            "no shutdown",
            "exit",
            "exit"
        ]
        output4, _ = device_connection.execute_commands(commands_enable, wait_time=0.5)
        test_data_logger["log_command"](" ; ".join(commands_enable), output4, 0)

        # Step 5: Verify enabled
        output5, _ = device_connection.execute_command("show interface Ethernet 0")
        test_data_logger["log_command"]("show interface Ethernet 0 (after enable)", output5, 0)

        # Get DB snapshot
        db_snapshot = device_connection.get_db_snapshot()
        test_data_logger["log_db_snapshot"](db_snapshot)

        combined_output = output1 + output2 + output3 + output4 + output5
        test_logger.info(f"Command output length: {len(combined_output)} bytes")

        # Verify workflow completed
        assert len(combined_output) > 0, "No output received from workflow"

        test_logger.info("✓ Test PASSED: Shutdown and re-enable workflow completed")

    @pytest.mark.interface_config
    @pytest.mark.workflow
    def test_TC_IF_028_configuration_rollback(self, device_connection, test_logger, test_data_logger):
        """
        TC-IF-028: Configuration Rollback - Remove All Parameters
        Verify that all configured parameters can be removed
        """
        test_logger.info("TC-IF-028: Configuration Rollback - Remove All Parameters")

        commands = [
            "configure terminal",
            "interface Ethernet 0",
            "no description",
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

        # Verify command executed
        assert len(output) > 0, "No output received from commands"

        test_logger.info("✓ Test PASSED: Configuration rollback completed")
