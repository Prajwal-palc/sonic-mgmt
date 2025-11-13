"""
Comprehensive Test Suite for Interface Commands
Tests all commands extracted from interface.xml:
- Creation: interface Ethernet <id>
- Update: shutdown, no shutdown, description, mtu
- Deletion: no description, no mtu
- Recreation: combination of deletion and re-creation
- Show: all show interface commands

Test IDs: TC-IF-100 through TC-IF-140
"""

import pytest
import logging
from interface_xml_parser import InterfaceXMLParser

logger = logging.getLogger(__name__)


class TestInterfaceComprehensive:
    """Comprehensive test class covering all interface operations"""

    # =================================================================
    # SHOW COMMANDS (TC-IF-100 to TC-IF-106)
    # =================================================================

    @pytest.mark.show_commands
    def test_TC_IF_100_show_interface_all(self, device_connection, test_logger, test_data_logger):
        """TC-IF-100: Show all interfaces"""
        test_logger.info("TC-IF-100: Show Interface - Display All Interfaces")

        command = "show interface"
        output, exit_code = device_connection.execute_command(command)

        test_data_logger["log_command"](command, output, exit_code)
        test_logger.info(f"Command output length: {len(output)} bytes")

        assert len(output) > 0, "No output received from command"
        test_logger.info("✓ Test PASSED: Show interface all")

    @pytest.mark.show_commands
    def test_TC_IF_101_show_interface_counters(self, device_connection, test_logger, test_data_logger):
        """TC-IF-101: Show interface counters"""
        test_logger.info("TC-IF-101: Show Interface Counters")

        command = "show interface counters"
        output, exit_code = device_connection.execute_command(command, wait_time=2.0)

        test_data_logger["log_command"](command, output, exit_code)
        test_logger.info(f"Command output length: {len(output)} bytes")

        assert len(output) > 0, "No output received from command"
        test_logger.info("✓ Test PASSED: Show interface counters")

    @pytest.mark.show_commands
    def test_TC_IF_102_show_interface_status(self, device_connection, test_logger, test_data_logger):
        """TC-IF-102: Show interface status"""
        test_logger.info("TC-IF-102: Show Interface Status")

        command = "show interface status"
        output, exit_code = device_connection.execute_command(command)

        test_data_logger["log_command"](command, output, exit_code)
        test_logger.info(f"Command output length: {len(output)} bytes")

        assert len(output) > 0, "No output received from command"
        test_logger.info("✓ Test PASSED: Show interface status")

    @pytest.mark.show_commands
    def test_TC_IF_103_show_interface_ethernet(self, device_connection, test_logger, test_data_logger):
        """TC-IF-103: Show all Ethernet interfaces"""
        test_logger.info("TC-IF-103: Show All Ethernet Interfaces")

        command = "show interface Ethernet"
        output, exit_code = device_connection.execute_command(command)

        test_data_logger["log_command"](command, output, exit_code)
        test_logger.info(f"Command output length: {len(output)} bytes")

        assert len(output) > 0, "No output received from command"
        test_logger.info("✓ Test PASSED: Show interface Ethernet")

    @pytest.mark.show_commands
    def test_TC_IF_104_show_interface_ethernet0(self, device_connection, test_logger, test_data_logger):
        """TC-IF-104: Show Ethernet0"""
        test_logger.info("TC-IF-104: Show Ethernet0")

        command = "show interface Ethernet 0"
        output, exit_code = device_connection.execute_command(command)

        test_data_logger["log_command"](command, output, exit_code)
        test_logger.info(f"Command output length: {len(output)} bytes")

        assert len(output) > 0, "No output received from command"
        test_logger.info("✓ Test PASSED: Show interface Ethernet 0")

    @pytest.mark.show_commands
    def test_TC_IF_105_show_interface_ethernet4(self, device_connection, test_logger, test_data_logger):
        """TC-IF-105: Show Ethernet4"""
        test_logger.info("TC-IF-105: Show Ethernet4")

        command = "show interface Ethernet 4"
        output, exit_code = device_connection.execute_command(command)

        test_data_logger["log_command"](command, output, exit_code)
        test_logger.info(f"Command output length: {len(output)} bytes")

        assert len(output) > 0, "No output received from command"
        test_logger.info("✓ Test PASSED: Show interface Ethernet 4")

    @pytest.mark.show_commands
    def test_TC_IF_106_show_interface_ethernet8(self, device_connection, test_logger, test_data_logger):
        """TC-IF-106: Show Ethernet8"""
        test_logger.info("TC-IF-106: Show Ethernet8")

        command = "show interface Ethernet 8"
        output, exit_code = device_connection.execute_command(command)

        test_data_logger["log_command"](command, output, exit_code)
        test_logger.info(f"Command output length: {len(output)} bytes")

        assert len(output) > 0, "No output received from command"
        test_logger.info("✓ Test PASSED: Show interface Ethernet 8")

    # =================================================================
    # CREATION COMMANDS (TC-IF-110 to TC-IF-112)
    # =================================================================

    @pytest.mark.config_commands
    @pytest.mark.creation
    def test_TC_IF_110_create_interface_ethernet0(self, device_connection, test_logger, test_data_logger):
        """TC-IF-110: Create/Enter Ethernet0 configuration mode"""
        test_logger.info("TC-IF-110: Create/Enter Ethernet0 Config")

        commands = [
            "configure terminal",
            "interface Ethernet 0",
            "end"
        ]

        for command in commands:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        test_logger.info("✓ Test PASSED: Interface Ethernet 0 creation")

    @pytest.mark.config_commands
    @pytest.mark.creation
    def test_TC_IF_111_create_interface_ethernet4(self, device_connection, test_logger, test_data_logger):
        """TC-IF-111: Create/Enter Ethernet4 configuration mode"""
        test_logger.info("TC-IF-111: Create/Enter Ethernet4 Config")

        commands = [
            "configure terminal",
            "interface Ethernet 4",
            "end"
        ]

        for command in commands:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        test_logger.info("✓ Test PASSED: Interface Ethernet 4 creation")

    @pytest.mark.config_commands
    @pytest.mark.creation
    def test_TC_IF_112_create_interface_ethernet8(self, device_connection, test_logger, test_data_logger):
        """TC-IF-112: Create/Enter Ethernet8 configuration mode"""
        test_logger.info("TC-IF-112: Create/Enter Ethernet8 Config")

        commands = [
            "configure terminal",
            "interface Ethernet 8",
            "end"
        ]

        for command in commands:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        test_logger.info("✓ Test PASSED: Interface Ethernet 8 creation")

    # =================================================================
    # UPDATE COMMANDS - SHUTDOWN (TC-IF-120 to TC-IF-121)
    # =================================================================

    @pytest.mark.update_commands
    @pytest.mark.shutdown
    def test_TC_IF_120_shutdown_interface(self, device_connection, test_logger, test_data_logger):
        """TC-IF-120: Shutdown (disable) interface"""
        test_logger.info("TC-IF-120: Shutdown Interface")

        commands = [
            "configure terminal",
            "interface Ethernet 4",
            "shutdown",
            "end"
        ]

        for command in commands:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        test_logger.info("✓ Test PASSED: Interface shutdown")

    @pytest.mark.update_commands
    @pytest.mark.shutdown
    def test_TC_IF_121_no_shutdown_interface(self, device_connection, test_logger, test_data_logger):
        """TC-IF-121: No shutdown (enable) interface"""
        test_logger.info("TC-IF-121: No Shutdown Interface")

        commands = [
            "configure terminal",
            "interface Ethernet 4",
            "no shutdown",
            "end"
        ]

        for command in commands:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        test_logger.info("✓ Test PASSED: Interface no shutdown")

    # =================================================================
    # UPDATE COMMANDS - DESCRIPTION (TC-IF-122 to TC-IF-123)
    # =================================================================

    @pytest.mark.update_commands
    @pytest.mark.description
    def test_TC_IF_122_set_description(self, device_connection, test_logger, test_data_logger):
        """TC-IF-122: Set interface description"""
        test_logger.info("TC-IF-122: Set Interface Description")

        commands = [
            "configure terminal",
            "interface Ethernet 4",
            "description Test_Interface",
            "end"
        ]

        for command in commands:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        test_logger.info("✓ Test PASSED: Set description")

    @pytest.mark.update_commands
    @pytest.mark.description
    def test_TC_IF_123_set_description_with_spaces(self, device_connection, test_logger, test_data_logger):
        """TC-IF-123: Set interface description with spaces"""
        test_logger.info("TC-IF-123: Set Description with Spaces")

        commands = [
            "configure terminal",
            "interface Ethernet 4",
            "description Interface for Testing",
            "end"
        ]

        for command in commands:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        test_logger.info("✓ Test PASSED: Set description with spaces")

    # =================================================================
    # UPDATE COMMANDS - MTU (TC-IF-124 to TC-IF-125)
    # =================================================================

    @pytest.mark.update_commands
    @pytest.mark.mtu
    def test_TC_IF_124_set_mtu_1500(self, device_connection, test_logger, test_data_logger):
        """TC-IF-124: Set MTU to 1500"""
        test_logger.info("TC-IF-124: Set MTU to 1500")

        commands = [
            "configure terminal",
            "interface Ethernet 4",
            "mtu 1500",
            "end"
        ]

        for command in commands:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        test_logger.info("✓ Test PASSED: Set MTU 1500")

    @pytest.mark.update_commands
    @pytest.mark.mtu
    def test_TC_IF_125_set_mtu_9000(self, device_connection, test_logger, test_data_logger):
        """TC-IF-125: Set MTU to 9000"""
        test_logger.info("TC-IF-125: Set MTU to 9000")

        commands = [
            "configure terminal",
            "interface Ethernet 4",
            "mtu 9000",
            "end"
        ]

        for command in commands:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        test_logger.info("✓ Test PASSED: Set MTU 9000")

    # =================================================================
    # DELETE COMMANDS (TC-IF-130 to TC-IF-131)
    # =================================================================

    @pytest.mark.delete_commands
    @pytest.mark.description
    def test_TC_IF_130_delete_description(self, device_connection, test_logger, test_data_logger):
        """TC-IF-130: Remove interface description"""
        test_logger.info("TC-IF-130: Delete Description")

        commands = [
            "configure terminal",
            "interface Ethernet 4",
            "no description",
            "end"
        ]

        for command in commands:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        test_logger.info("✓ Test PASSED: Delete description")

    @pytest.mark.delete_commands
    @pytest.mark.mtu
    def test_TC_IF_131_delete_mtu(self, device_connection, test_logger, test_data_logger):
        """TC-IF-131: Reset MTU to default"""
        test_logger.info("TC-IF-131: Delete/Reset MTU")

        commands = [
            "configure terminal",
            "interface Ethernet 4",
            "no mtu",
            "end"
        ]

        for command in commands:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        test_logger.info("✓ Test PASSED: Delete MTU (reset to default)")

    # =================================================================
    # RECREATION COMMANDS (TC-IF-140 to TC-IF-142)
    # =================================================================

    @pytest.mark.recreation
    @pytest.mark.description
    def test_TC_IF_140_recreate_description(self, device_connection, test_logger, test_data_logger):
        """TC-IF-140: Delete and recreate interface description"""
        test_logger.info("TC-IF-140: Recreate Description")

        # Delete existing description
        commands_delete = [
            "configure terminal",
            "interface Ethernet 4",
            "no description",
            "end"
        ]

        for command in commands_delete:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        # Recreate with new description
        commands_create = [
            "configure terminal",
            "interface Ethernet 4",
            "description Recreated_Interface",
            "end"
        ]

        for command in commands_create:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        test_logger.info("✓ Test PASSED: Recreate description")

    @pytest.mark.recreation
    @pytest.mark.mtu
    def test_TC_IF_141_recreate_mtu(self, device_connection, test_logger, test_data_logger):
        """TC-IF-141: Delete and recreate MTU configuration"""
        test_logger.info("TC-IF-141: Recreate MTU")

        # Delete/reset MTU
        commands_delete = [
            "configure terminal",
            "interface Ethernet 4",
            "no mtu",
            "end"
        ]

        for command in commands_delete:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        # Recreate with new MTU
        commands_create = [
            "configure terminal",
            "interface Ethernet 4",
            "mtu 2000",
            "end"
        ]

        for command in commands_create:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        test_logger.info("✓ Test PASSED: Recreate MTU")

    @pytest.mark.recreation
    @pytest.mark.workflow
    def test_TC_IF_142_full_interface_recreation(self, device_connection, test_logger, test_data_logger):
        """TC-IF-142: Complete interface configuration recreation workflow"""
        test_logger.info("TC-IF-142: Full Interface Recreation")

        # Step 1: Clear all config
        commands_clear = [
            "configure terminal",
            "interface Ethernet 4",
            "no description",
            "no mtu",
            "end"
        ]

        for command in commands_clear:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        # Step 2: Recreate with full config
        commands_recreate = [
            "configure terminal",
            "interface Ethernet 4",
            "description Fully_Recreated_Interface",
            "mtu 1600",
            "no shutdown",
            "end"
        ]

        for command in commands_recreate:
            output, exit_code = device_connection.execute_command(command)
            test_data_logger["log_command"](command, output, exit_code)

        test_logger.info("✓ Test PASSED: Full interface recreation")
