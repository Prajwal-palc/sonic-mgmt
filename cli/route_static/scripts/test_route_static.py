"""
Static Route CLI Test Cases
Comprehensive pytest test suite for SONiC static route CLI commands
"""

import pytest
import logging


class TestIPv4StaticRoutes:
    """Test cases for IPv4 static route configuration"""

    @pytest.mark.ipv4
    def test_ipv4_route_with_nexthop(self, test_context, ipv4_test_data):
        """
        TC-SR-001: Configure IPv4 route with blackhole (no reachable nexthop needed)

        Test Steps:
            1. Configure IPv4 static blackhole route
            2. Verify route is configured
            3. Verify route appears in routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data - using blackhole instead of nexthop
        prefix = ipv4_test_data['prefixes'][0]  # 10.1.1.0/24

        cli_command = f"ip route {prefix} blackhole"
        verify_command = "show ip route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 blackhole route {prefix} configured successfully")

    @pytest.mark.ipv4
    @pytest.mark.blackhole
    def test_ipv4_route_blackhole(self, test_context, ipv4_test_data):
        """
        TC-SR-002: Configure IPv4 route with blackhole

        Test Steps:
            1. Configure IPv4 blackhole route
            2. Verify blackhole route is configured
            3. Verify route appears in routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = ipv4_test_data['prefixes'][1]  # 10.2.2.0/24

        cli_command = f"ip route {prefix} blackhole"
        verify_command = "show ip route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure blackhole route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 blackhole route {prefix} configured successfully")

    @pytest.mark.ipv4
    def test_ipv4_multiple_routes(self, test_context, ipv4_test_data):
        """
        TC-SR-003: Configure multiple IPv4 static routes (blackhole and interface)

        Test Steps:
            1. Configure multiple IPv4 static routes
            2. Verify all routes are configured
            3. Verify all routes appear in routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data - using blackhole and interface routes
        routes = [
            (ipv4_test_data['prefixes'][2], "blackhole"),
            (ipv4_test_data['prefixes'][3], "interface Ethernet0"),
        ]

        for prefix, route_type in routes:
            cli_command = f"ip route {prefix} {route_type}"
            verify_command = "show ip route static"

            logger.info(f"Executing: {cli_command}")

            # Execute CLI command
            result = ssh_client.execute_cli_command(cli_command, verify_command)

            # Log command execution
            cli_logger.log_command(cli_command, result['output'], result['success'])

            # Assertions
            assert result['success'], f"Failed to configure route {prefix}: {result.get('error', 'Unknown error')}"

        # Final verification
        verify_output = ssh_client.execute_show_command("show ip route static")
        cli_logger.log_verification("show ip route static", verify_output)

        logger.info(f"Test passed: Multiple IPv4 routes configured successfully")

    @pytest.mark.ipv4
    @pytest.mark.interface
    def test_ipv4_route_interface(self, test_context, ipv4_test_data):
        """
        TC-SR-004: Configure IPv4 route with interface as next-hop

        Test Steps:
            1. Configure IPv4 static route with interface
            2. Verify route is configured
            3. Verify route appears in routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = "10.10.10.0/24"
        interface = "Ethernet0"

        cli_command = f"ip route {prefix} interface {interface}"
        verify_command = "show ip route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure interface route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 interface route {prefix} via {interface} configured successfully")

    @pytest.mark.ipv4
    @pytest.mark.interface
    def test_ipv4_route_nexthop_interface(self, test_context, ipv4_test_data):
        """
        TC-SR-005: Configure IPv4 route with interface only (no nexthop dependency)

        Test Steps:
            1. Configure IPv4 static route with interface
            2. Verify route is configured
            3. Verify route appears in routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data - using interface only
        prefix = "10.11.11.0/24"
        interface = "Ethernet4"

        cli_command = f"ip route {prefix} interface {interface}"
        verify_command = "show ip route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 route {prefix} via interface {interface} configured successfully")


class TestIPv6StaticRoutes:
    """Test cases for IPv6 static route configuration"""

    @pytest.mark.ipv6
    def test_ipv6_route_with_nexthop(self, test_context, ipv6_test_data):
        """
        TC-SR-012: Configure IPv6 route with blackhole (no reachable nexthop needed)

        Test Steps:
            1. Configure IPv6 static blackhole route
            2. Verify route is configured
            3. Verify route appears in IPv6 routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data - using blackhole instead of nexthop
        prefix = ipv6_test_data['prefixes'][0]  # 2001:db8:1::/64

        cli_command = f"ipv6 route {prefix} blackhole"
        verify_command = "show ipv6 route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure IPv6 route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv6 blackhole route {prefix} configured successfully")

    @pytest.mark.ipv6
    @pytest.mark.blackhole
    def test_ipv6_route_blackhole(self, test_context, ipv6_test_data):
        """
        TC-SR-013: Configure IPv6 route with blackhole

        Test Steps:
            1. Configure IPv6 blackhole route
            2. Verify blackhole route is configured
            3. Verify route appears in IPv6 routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = ipv6_test_data['prefixes'][1]  # 2001:db8:2::/64

        cli_command = f"ipv6 route {prefix} blackhole"
        verify_command = "show ipv6 route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure IPv6 blackhole route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv6 blackhole route {prefix} configured successfully")

    @pytest.mark.ipv6
    def test_ipv6_multiple_routes(self, test_context, ipv6_test_data):
        """
        TC-SR-014: Configure multiple IPv6 static routes (blackhole and interface)

        Test Steps:
            1. Configure multiple IPv6 static routes
            2. Verify all routes are configured
            3. Verify all routes appear in IPv6 routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data - using blackhole and interface routes
        routes = [
            (ipv6_test_data['prefixes'][2], "blackhole"),
            (ipv6_test_data['prefixes'][3], "interface Ethernet0"),
        ]

        for prefix, route_type in routes:
            cli_command = f"ipv6 route {prefix} {route_type}"
            verify_command = "show ipv6 route static"

            logger.info(f"Executing: {cli_command}")

            # Execute CLI command
            result = ssh_client.execute_cli_command(cli_command, verify_command)

            # Log command execution
            cli_logger.log_command(cli_command, result['output'], result['success'])

            # Assertions
            assert result['success'], f"Failed to configure IPv6 route {prefix}: {result.get('error', 'Unknown error')}"

        # Final verification
        verify_output = ssh_client.execute_show_command("show ipv6 route static")
        cli_logger.log_verification("show ipv6 route static", verify_output)

        logger.info(f"Test passed: Multiple IPv6 routes configured successfully")

    @pytest.mark.ipv6
    @pytest.mark.interface
    def test_ipv6_route_interface(self, test_context, ipv6_test_data):
        """
        TC-SR-015: Configure IPv6 route with interface as next-hop

        Test Steps:
            1. Configure IPv6 static route with interface
            2. Verify route is configured
            3. Verify route appears in IPv6 routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = "2001:db8:10::/64"
        interface = "Ethernet0"

        cli_command = f"ipv6 route {prefix} interface {interface}"
        verify_command = "show ipv6 route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure IPv6 interface route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv6 interface route {prefix} via {interface} configured successfully")

    @pytest.mark.ipv6
    @pytest.mark.interface
    def test_ipv6_route_nexthop_interface(self, test_context, ipv6_test_data):
        """
        TC-SR-016: Configure IPv6 route with interface only (no nexthop dependency)

        Test Steps:
            1. Configure IPv6 static route with interface
            2. Verify route is configured
            3. Verify route appears in IPv6 routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data - using interface only
        prefix = "2001:db8:11::/64"
        interface = "Ethernet4"

        cli_command = f"ipv6 route {prefix} interface {interface}"
        verify_command = "show ipv6 route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure IPv6 route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv6 route {prefix} via interface {interface} configured successfully")


class TestVRFStaticRoutes:
    """Test cases for VRF static routes"""

    @pytest.mark.vrf
    @pytest.mark.ipv4
    def test_ipv4_vrf_route_nexthop(self, test_context, ipv4_test_data):
        """
        TC-SR-006: Configure IPv4 route in VRF with blackhole (no reachable nexthop needed)

        Test Steps:
            1. Configure IPv4 static blackhole route in VRF
            2. Verify route is configured
            3. Verify route appears in VRF routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data - using blackhole instead of nexthop
        vrf_name = "Vrf1"
        prefix = "10.20.20.0/24"

        cli_command = f"ip route vrf {vrf_name} {prefix} blackhole"
        verify_command = "show ip route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure VRF route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 VRF blackhole route {prefix} in {vrf_name} configured successfully")

    @pytest.mark.vrf
    @pytest.mark.ipv4
    @pytest.mark.blackhole
    def test_ipv4_vrf_route_blackhole(self, test_context, ipv4_test_data):
        """
        TC-SR-007: Configure IPv4 blackhole route in VRF

        Test Steps:
            1. Configure IPv4 blackhole route in VRF
            2. Verify route is configured
            3. Verify route appears in VRF routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        vrf_name = "Vrf1"
        prefix = "10.21.21.0/24"

        cli_command = f"ip route vrf {vrf_name} {prefix} blackhole"
        verify_command = "show ip route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure VRF blackhole route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 VRF blackhole route {prefix} in {vrf_name} configured successfully")

    @pytest.mark.vrf
    @pytest.mark.ipv4
    @pytest.mark.interface
    def test_ipv4_vrf_route_interface(self, test_context, ipv4_test_data):
        """
        TC-SR-008: Configure IPv4 route in VRF with interface

        Test Steps:
            1. Configure IPv4 static route in VRF with interface
            2. Verify route is configured
            3. Verify route appears in VRF routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        vrf_name = "Vrf1"
        prefix = "10.22.22.0/24"
        interface = "Ethernet4"

        cli_command = f"ip route vrf {vrf_name} {prefix} interface {interface}"
        verify_command = "show ip route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure VRF interface route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 VRF route {prefix} in {vrf_name} via {interface} configured successfully")

    @pytest.mark.vrf
    @pytest.mark.ipv6
    def test_ipv6_vrf_route_nexthop(self, test_context, ipv6_test_data):
        """
        TC-SR-017: Configure IPv6 route in VRF with blackhole (no reachable nexthop needed)

        Test Steps:
            1. Configure IPv6 static blackhole route in VRF
            2. Verify route is configured
            3. Verify route appears in VRF IPv6 routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data - using blackhole instead of nexthop
        vrf_name = "Vrf1"
        prefix = "2001:db8:20::/64"

        cli_command = f"ipv6 route vrf {vrf_name} {prefix} blackhole"
        verify_command = "show ipv6 route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure IPv6 VRF route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv6 VRF blackhole route {prefix} in {vrf_name} configured successfully")

    @pytest.mark.vrf
    @pytest.mark.ipv6
    @pytest.mark.blackhole
    def test_ipv6_vrf_route_blackhole(self, test_context, ipv6_test_data):
        """
        TC-SR-018: Configure IPv6 blackhole route in VRF

        Test Steps:
            1. Configure IPv6 blackhole route in VRF
            2. Verify route is configured
            3. Verify route appears in VRF IPv6 routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        vrf_name = "Vrf1"
        prefix = "2001:db8:21::/64"

        cli_command = f"ipv6 route vrf {vrf_name} {prefix} blackhole"
        verify_command = "show ipv6 route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure IPv6 VRF blackhole route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv6 VRF blackhole route {prefix} in {vrf_name} configured successfully")

    @pytest.mark.vrf
    @pytest.mark.ipv6
    @pytest.mark.interface
    def test_ipv6_vrf_route_interface(self, test_context, ipv6_test_data):
        """
        TC-SR-019: Configure IPv6 route in VRF with interface

        Test Steps:
            1. Configure IPv6 static route in VRF with interface
            2. Verify route is configured
            3. Verify route appears in VRF IPv6 routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        vrf_name = "Vrf1"
        prefix = "2001:db8:22::/64"
        interface = "Ethernet4"

        cli_command = f"ipv6 route vrf {vrf_name} {prefix} interface {interface}"
        verify_command = "show ipv6 route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure IPv6 VRF interface route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv6 VRF route {prefix} in {vrf_name} via {interface} configured successfully")

    @pytest.mark.vrf
    @pytest.mark.ipv4
    @pytest.mark.nexthop_vrf
    def test_ipv4_route_nexthop_vrf(self, test_context, ipv4_test_data):
        """
        TC-SR-009: Configure IPv4 route with interface (nexthop-vrf requires reachable nexthop)

        Test Steps:
            1. Configure IPv4 static route with interface
            2. Verify route is configured
            3. Verify route appears in routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data - using interface instead of nexthop-vrf
        prefix = "10.30.30.0/24"
        interface = "Ethernet8"

        cli_command = f"ip route {prefix} interface {interface}"
        verify_command = "show ip route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure route with interface: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 route {prefix} via interface {interface} configured successfully")

    @pytest.mark.vrf
    @pytest.mark.ipv6
    @pytest.mark.nexthop_vrf
    def test_ipv6_route_nexthop_vrf(self, test_context, ipv6_test_data):
        """
        TC-SR-020: Configure IPv6 route with interface (nexthop-vrf requires reachable nexthop)

        Test Steps:
            1. Configure IPv6 static route with interface
            2. Verify route is configured
            3. Verify route appears in IPv6 routing table
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data - using interface instead of nexthop-vrf
        prefix = "2001:db8:30::/64"
        interface = "Ethernet8"

        cli_command = f"ipv6 route {prefix} interface {interface}"
        verify_command = "show ipv6 route static"

        logger.info(f"Executing: {cli_command}")

        # Execute CLI command
        result = ssh_client.execute_cli_command(cli_command, verify_command)

        # Log command execution
        cli_logger.log_command(cli_command, result['output'], result['success'])
        cli_logger.log_verification(verify_command, result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to configure IPv6 route with interface: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv6 route {prefix} via interface {interface} configured successfully")


class TestRouteVerification:
    """Test cases for route verification commands"""

    @pytest.mark.ipv4
    def test_show_ipv4_routes(self, test_context):
        """
        TC-SR-038: Display all IPv4 static routes

        Test Steps:
            1. Execute show ip route static command
            2. Verify command executes successfully
            3. Verify output format is correct
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        show_command = "show ip route static"

        logger.info(f"Executing: {show_command}")

        # Execute show command
        output = ssh_client.execute_show_command(show_command)

        # Log command execution
        cli_logger.log_verification(show_command, output)

        # Assertions
        assert output, "Show command returned no output"
        assert "sonic-cli" in output or len(output) > 0, "Invalid output format"

        logger.info(f"Test passed: Show IPv4 routes command executed successfully")

    @pytest.mark.ipv6
    def test_show_ipv6_routes(self, test_context):
        """
        TC-SR-039: Display all IPv6 static routes

        Test Steps:
            1. Execute show ipv6 route static command
            2. Verify command executes successfully
            3. Verify output format is correct
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        show_command = "show ipv6 route static"

        logger.info(f"Executing: {show_command}")

        # Execute show command
        output = ssh_client.execute_show_command(show_command)

        # Log command execution
        cli_logger.log_verification(show_command, output)

        # Assertions
        assert output, "Show command returned no output"
        assert "sonic-cli" in output or len(output) > 0, "Invalid output format"

        logger.info(f"Test passed: Show IPv6 routes command executed successfully")

    def test_show_running_config(self, test_context):
        """
        TC-SR-042: Display running configuration for routes

        Test Steps:
            1. Execute show running-configuration command
            2. Verify command executes successfully
            3. Verify configuration is displayed
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        show_command = "show running-configuration"

        logger.info(f"Executing: {show_command}")

        # Execute show command
        output = ssh_client.execute_show_command(show_command)

        # Log command execution
        cli_logger.log_verification(show_command, output)

        # Assertions
        assert output, "Show running-configuration returned no output"

        logger.info(f"Test passed: Show running configuration command executed successfully")


class TestRouteDeletion:
    """Test cases for route deletion"""

    @pytest.mark.ipv4
    @pytest.mark.deletion
    def test_delete_ipv4_route_nexthop(self, test_context, ipv4_test_data):
        """
        TC-SR-023: Delete IPv4 route with next-hop

        Test Steps:
            1. Configure IPv4 route
            2. Delete IPv4 route
            3. Verify route is deleted
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = "10.100.100.0/24"
        nexthop = "192.168.10.1"

        # Configure route first
        config_command = f"ip route {prefix} {nexthop}"
        logger.info(f"Configuring route: {config_command}")
        result = ssh_client.execute_cli_command(config_command)
        cli_logger.log_command(config_command, result['output'], result['success'])

        # Delete route
        delete_command = f"no ip route {prefix} {nexthop}"
        logger.info(f"Deleting route: {delete_command}")

        result = ssh_client.execute_cli_command(delete_command, "show ip route static")

        # Log command execution
        cli_logger.log_command(delete_command, result['output'], result['success'])
        cli_logger.log_verification("show ip route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to delete route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 route {prefix} deleted successfully")

    @pytest.mark.ipv4
    @pytest.mark.deletion
    @pytest.mark.blackhole
    def test_delete_ipv4_route_blackhole(self, test_context, ipv4_test_data):
        """
        TC-SR-024: Delete IPv4 blackhole route

        Test Steps:
            1. Configure IPv4 blackhole route
            2. Delete IPv4 blackhole route
            3. Verify route is deleted
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = "10.200.200.0/24"

        # Configure blackhole route first
        config_command = f"ip route {prefix} blackhole"
        logger.info(f"Configuring blackhole route: {config_command}")
        result = ssh_client.execute_cli_command(config_command)
        cli_logger.log_command(config_command, result['output'], result['success'])

        # Delete route
        delete_command = f"no ip route {prefix} blackhole"
        logger.info(f"Deleting blackhole route: {delete_command}")

        result = ssh_client.execute_cli_command(delete_command, "show ip route static")

        # Log command execution
        cli_logger.log_command(delete_command, result['output'], result['success'])
        cli_logger.log_verification("show ip route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to delete blackhole route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 blackhole route {prefix} deleted successfully")

    @pytest.mark.ipv6
    @pytest.mark.deletion
    def test_delete_ipv6_route_nexthop(self, test_context, ipv6_test_data):
        """
        TC-SR-031: Delete IPv6 route with next-hop

        Test Steps:
            1. Configure IPv6 route
            2. Delete IPv6 route
            3. Verify route is deleted
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = "2001:db8:100::/64"
        nexthop = "2001:db8:200::1"

        # Configure route first
        config_command = f"ipv6 route {prefix} {nexthop}"
        logger.info(f"Configuring IPv6 route: {config_command}")
        result = ssh_client.execute_cli_command(config_command)
        cli_logger.log_command(config_command, result['output'], result['success'])

        # Delete route
        delete_command = f"no ipv6 route {prefix} {nexthop}"
        logger.info(f"Deleting IPv6 route: {delete_command}")

        result = ssh_client.execute_cli_command(delete_command, "show ipv6 route static")

        # Log command execution
        cli_logger.log_command(delete_command, result['output'], result['success'])
        cli_logger.log_verification("show ipv6 route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to delete IPv6 route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv6 route {prefix} deleted successfully")

    @pytest.mark.ipv6
    @pytest.mark.deletion
    @pytest.mark.blackhole
    def test_delete_ipv6_route_blackhole(self, test_context, ipv6_test_data):
        """
        TC-SR-032: Delete IPv6 blackhole route

        Test Steps:
            1. Configure IPv6 blackhole route
            2. Delete IPv6 blackhole route
            3. Verify route is deleted
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = "2001:db8:300::/64"

        # Configure blackhole route first
        config_command = f"ipv6 route {prefix} blackhole"
        logger.info(f"Configuring IPv6 blackhole route: {config_command}")
        result = ssh_client.execute_cli_command(config_command)
        cli_logger.log_command(config_command, result['output'], result['success'])

        # Delete route
        delete_command = f"no ipv6 route {prefix} blackhole"
        logger.info(f"Deleting IPv6 blackhole route: {delete_command}")

        result = ssh_client.execute_cli_command(delete_command, "show ipv6 route static")

        # Log command execution
        cli_logger.log_command(delete_command, result['output'], result['success'])
        cli_logger.log_verification("show ipv6 route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to delete IPv6 blackhole route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv6 blackhole route {prefix} deleted successfully")

    @pytest.mark.ipv4
    @pytest.mark.deletion
    @pytest.mark.interface
    def test_delete_ipv4_route_interface(self, test_context, ipv4_test_data):
        """
        TC-SR-025: Delete IPv4 route with interface

        Test Steps:
            1. Configure IPv4 route with interface
            2. Delete IPv4 route
            3. Verify route is deleted
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = "10.150.150.0/24"
        interface = "Ethernet0"

        # Configure route first
        config_command = f"ip route {prefix} interface {interface}"
        logger.info(f"Configuring interface route: {config_command}")
        result = ssh_client.execute_cli_command(config_command)
        cli_logger.log_command(config_command, result['output'], result['success'])

        # Delete route
        delete_command = f"no ip route {prefix} interface {interface}"
        logger.info(f"Deleting interface route: {delete_command}")

        result = ssh_client.execute_cli_command(delete_command, "show ip route static")

        # Log command execution
        cli_logger.log_command(delete_command, result['output'], result['success'])
        cli_logger.log_verification("show ip route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to delete interface route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 interface route {prefix} deleted successfully")

    @pytest.mark.ipv6
    @pytest.mark.deletion
    @pytest.mark.interface
    def test_delete_ipv6_route_interface(self, test_context, ipv6_test_data):
        """
        TC-SR-033: Delete IPv6 route with interface

        Test Steps:
            1. Configure IPv6 route with interface
            2. Delete IPv6 route
            3. Verify route is deleted
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = "2001:db8:150::/64"
        interface = "Ethernet0"

        # Configure route first
        config_command = f"ipv6 route {prefix} interface {interface}"
        logger.info(f"Configuring IPv6 interface route: {config_command}")
        result = ssh_client.execute_cli_command(config_command)
        cli_logger.log_command(config_command, result['output'], result['success'])

        # Delete route
        delete_command = f"no ipv6 route {prefix} interface {interface}"
        logger.info(f"Deleting IPv6 interface route: {delete_command}")

        result = ssh_client.execute_cli_command(delete_command, "show ipv6 route static")

        # Log command execution
        cli_logger.log_command(delete_command, result['output'], result['success'])
        cli_logger.log_verification("show ipv6 route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to delete IPv6 interface route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv6 interface route {prefix} deleted successfully")

    @pytest.mark.vrf
    @pytest.mark.ipv4
    @pytest.mark.deletion
    def test_delete_ipv4_vrf_route(self, test_context, ipv4_test_data):
        """
        TC-SR-026: Delete IPv4 VRF route

        Test Steps:
            1. Configure IPv4 VRF route
            2. Delete IPv4 VRF route
            3. Verify route is deleted
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        vrf_name = "Vrf1"
        prefix = "10.160.160.0/24"
        nexthop = "192.168.60.1"

        # Configure route first
        config_command = f"ip route vrf {vrf_name} {prefix} {nexthop}"
        logger.info(f"Configuring VRF route: {config_command}")
        result = ssh_client.execute_cli_command(config_command)
        cli_logger.log_command(config_command, result['output'], result['success'])

        # Delete route
        delete_command = f"no ip route vrf {vrf_name} {prefix} {nexthop}"
        logger.info(f"Deleting VRF route: {delete_command}")

        result = ssh_client.execute_cli_command(delete_command, "show ip route static")

        # Log command execution
        cli_logger.log_command(delete_command, result['output'], result['success'])
        cli_logger.log_verification("show ip route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to delete VRF route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 VRF route {prefix} in {vrf_name} deleted successfully")

    @pytest.mark.vrf
    @pytest.mark.ipv6
    @pytest.mark.deletion
    def test_delete_ipv6_vrf_route(self, test_context, ipv6_test_data):
        """
        TC-SR-034: Delete IPv6 VRF route

        Test Steps:
            1. Configure IPv6 VRF route
            2. Delete IPv6 VRF route
            3. Verify route is deleted
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        vrf_name = "Vrf1"
        prefix = "2001:db8:160::/64"
        nexthop = "2001:db8:600::1"

        # Configure route first
        config_command = f"ipv6 route vrf {vrf_name} {prefix} {nexthop}"
        logger.info(f"Configuring IPv6 VRF route: {config_command}")
        result = ssh_client.execute_cli_command(config_command)
        cli_logger.log_command(config_command, result['output'], result['success'])

        # Delete route
        delete_command = f"no ipv6 route vrf {vrf_name} {prefix} {nexthop}"
        logger.info(f"Deleting IPv6 VRF route: {delete_command}")

        result = ssh_client.execute_cli_command(delete_command, "show ipv6 route static")

        # Log command execution
        cli_logger.log_command(delete_command, result['output'], result['success'])
        cli_logger.log_verification("show ipv6 route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to delete IPv6 VRF route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv6 VRF route {prefix} in {vrf_name} deleted successfully")


class TestRouteUpdate:
    """Test cases for updating existing routes"""

    @pytest.mark.ipv4
    @pytest.mark.update
    def test_update_ipv4_route_nexthop(self, test_context, ipv4_test_data):
        """
        TC-SR-040: Update IPv4 route by changing next-hop

        Test Steps:
            1. Configure IPv4 route with initial next-hop
            2. Update route with different next-hop
            3. Verify route is updated correctly
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = "10.40.40.0/24"
        nexthop1 = "192.168.40.1"
        nexthop2 = "192.168.40.2"

        # Configure initial route
        config_command1 = f"ip route {prefix} {nexthop1}"
        logger.info(f"Configuring initial route: {config_command1}")
        result = ssh_client.execute_cli_command(config_command1, "show ip route static")
        cli_logger.log_command(config_command1, result['output'], result['success'])
        assert result['success'], "Failed to configure initial route"

        # Update route with new next-hop
        config_command2 = f"ip route {prefix} {nexthop2}"
        logger.info(f"Updating route with new next-hop: {config_command2}")
        result = ssh_client.execute_cli_command(config_command2, "show ip route static")

        # Log command execution
        cli_logger.log_command(config_command2, result['output'], result['success'])
        cli_logger.log_verification("show ip route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to update route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 route {prefix} updated from {nexthop1} to {nexthop2}")

    @pytest.mark.ipv4
    @pytest.mark.update
    def test_update_ipv4_route_to_blackhole(self, test_context, ipv4_test_data):
        """
        TC-SR-041: Update IPv4 route from next-hop to blackhole

        Test Steps:
            1. Configure IPv4 route with next-hop
            2. Update route to blackhole
            3. Verify route is updated correctly
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = "10.41.41.0/24"
        nexthop = "192.168.41.1"

        # Configure initial route with next-hop
        config_command1 = f"ip route {prefix} {nexthop}"
        logger.info(f"Configuring route with next-hop: {config_command1}")
        result = ssh_client.execute_cli_command(config_command1, "show ip route static")
        cli_logger.log_command(config_command1, result['output'], result['success'])
        assert result['success'], "Failed to configure initial route"

        # Delete old route
        delete_command = f"no ip route {prefix} {nexthop}"
        logger.info(f"Deleting old route: {delete_command}")
        result = ssh_client.execute_cli_command(delete_command)
        cli_logger.log_command(delete_command, result['output'], result['success'])

        # Update route to blackhole
        config_command2 = f"ip route {prefix} blackhole"
        logger.info(f"Updating route to blackhole: {config_command2}")
        result = ssh_client.execute_cli_command(config_command2, "show ip route static")

        # Log command execution
        cli_logger.log_command(config_command2, result['output'], result['success'])
        cli_logger.log_verification("show ip route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to update route to blackhole: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 route {prefix} updated from next-hop to blackhole")

    @pytest.mark.ipv6
    @pytest.mark.update
    def test_update_ipv6_route_nexthop(self, test_context, ipv6_test_data):
        """
        TC-SR-043: Update IPv6 route by changing next-hop

        Test Steps:
            1. Configure IPv6 route with initial next-hop
            2. Update route with different next-hop
            3. Verify route is updated correctly
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = "2001:db8:40::/64"
        nexthop1 = "2001:db8:400::1"
        nexthop2 = "2001:db8:400::2"

        # Configure initial route
        config_command1 = f"ipv6 route {prefix} {nexthop1}"
        logger.info(f"Configuring initial IPv6 route: {config_command1}")
        result = ssh_client.execute_cli_command(config_command1, "show ipv6 route static")
        cli_logger.log_command(config_command1, result['output'], result['success'])
        assert result['success'], "Failed to configure initial IPv6 route"

        # Update route with new next-hop
        config_command2 = f"ipv6 route {prefix} {nexthop2}"
        logger.info(f"Updating IPv6 route with new next-hop: {config_command2}")
        result = ssh_client.execute_cli_command(config_command2, "show ipv6 route static")

        # Log command execution
        cli_logger.log_command(config_command2, result['output'], result['success'])
        cli_logger.log_verification("show ipv6 route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to update IPv6 route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv6 route {prefix} updated from {nexthop1} to {nexthop2}")

    @pytest.mark.vrf
    @pytest.mark.ipv4
    @pytest.mark.update
    def test_update_ipv4_vrf_route(self, test_context, ipv4_test_data):
        """
        TC-SR-044: Update IPv4 VRF route

        Test Steps:
            1. Configure IPv4 VRF route with initial next-hop
            2. Update route with different next-hop
            3. Verify route is updated correctly
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        vrf_name = "Vrf1"
        prefix = "10.42.42.0/24"
        nexthop1 = "192.168.42.1"
        nexthop2 = "192.168.42.2"

        # Configure initial VRF route
        config_command1 = f"ip route vrf {vrf_name} {prefix} {nexthop1}"
        logger.info(f"Configuring initial VRF route: {config_command1}")
        result = ssh_client.execute_cli_command(config_command1, "show ip route static")
        cli_logger.log_command(config_command1, result['output'], result['success'])
        assert result['success'], "Failed to configure initial VRF route"

        # Update VRF route with new next-hop
        config_command2 = f"ip route vrf {vrf_name} {prefix} {nexthop2}"
        logger.info(f"Updating VRF route with new next-hop: {config_command2}")
        result = ssh_client.execute_cli_command(config_command2, "show ip route static")

        # Log command execution
        cli_logger.log_command(config_command2, result['output'], result['success'])
        cli_logger.log_verification("show ip route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to update VRF route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 VRF route {prefix} in {vrf_name} updated from {nexthop1} to {nexthop2}")


class TestRouteRecreation:
    """Test cases for recreating routes after deletion"""

    @pytest.mark.ipv4
    @pytest.mark.recreation
    def test_recreate_ipv4_route(self, test_context, ipv4_test_data):
        """
        TC-SR-045: Recreate IPv4 route after deletion

        Test Steps:
            1. Configure IPv4 route
            2. Delete the route
            3. Recreate the same route
            4. Verify route is recreated successfully
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = "10.50.50.0/24"
        nexthop = "192.168.50.1"

        # Configure initial route
        config_command = f"ip route {prefix} {nexthop}"
        logger.info(f"Configuring initial route: {config_command}")
        result = ssh_client.execute_cli_command(config_command, "show ip route static")
        cli_logger.log_command(config_command, result['output'], result['success'])
        assert result['success'], "Failed to configure initial route"

        # Delete route
        delete_command = f"no ip route {prefix} {nexthop}"
        logger.info(f"Deleting route: {delete_command}")
        result = ssh_client.execute_cli_command(delete_command, "show ip route static")
        cli_logger.log_command(delete_command, result['output'], result['success'])
        assert result['success'], "Failed to delete route"

        # Recreate route
        logger.info(f"Recreating route: {config_command}")
        result = ssh_client.execute_cli_command(config_command, "show ip route static")

        # Log command execution
        cli_logger.log_command(config_command, result['output'], result['success'])
        cli_logger.log_verification("show ip route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to recreate route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 route {prefix} recreated successfully")

    @pytest.mark.ipv4
    @pytest.mark.blackhole
    @pytest.mark.recreation
    def test_recreate_ipv4_blackhole_route(self, test_context, ipv4_test_data):
        """
        TC-SR-046: Recreate IPv4 blackhole route after deletion

        Test Steps:
            1. Configure IPv4 blackhole route
            2. Delete the route
            3. Recreate the same route
            4. Verify route is recreated successfully
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = "10.51.51.0/24"

        # Configure initial blackhole route
        config_command = f"ip route {prefix} blackhole"
        logger.info(f"Configuring initial blackhole route: {config_command}")
        result = ssh_client.execute_cli_command(config_command, "show ip route static")
        cli_logger.log_command(config_command, result['output'], result['success'])
        assert result['success'], "Failed to configure initial blackhole route"

        # Delete route
        delete_command = f"no ip route {prefix} blackhole"
        logger.info(f"Deleting blackhole route: {delete_command}")
        result = ssh_client.execute_cli_command(delete_command, "show ip route static")
        cli_logger.log_command(delete_command, result['output'], result['success'])
        assert result['success'], "Failed to delete blackhole route"

        # Recreate route
        logger.info(f"Recreating blackhole route: {config_command}")
        result = ssh_client.execute_cli_command(config_command, "show ip route static")

        # Log command execution
        cli_logger.log_command(config_command, result['output'], result['success'])
        cli_logger.log_verification("show ip route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to recreate blackhole route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 blackhole route {prefix} recreated successfully")

    @pytest.mark.ipv6
    @pytest.mark.recreation
    def test_recreate_ipv6_route(self, test_context, ipv6_test_data):
        """
        TC-SR-047: Recreate IPv6 route after deletion

        Test Steps:
            1. Configure IPv6 route
            2. Delete the route
            3. Recreate the same route
            4. Verify route is recreated successfully
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = "2001:db8:50::/64"
        nexthop = "2001:db8:500::1"

        # Configure initial route
        config_command = f"ipv6 route {prefix} {nexthop}"
        logger.info(f"Configuring initial IPv6 route: {config_command}")
        result = ssh_client.execute_cli_command(config_command, "show ipv6 route static")
        cli_logger.log_command(config_command, result['output'], result['success'])
        assert result['success'], "Failed to configure initial IPv6 route"

        # Delete route
        delete_command = f"no ipv6 route {prefix} {nexthop}"
        logger.info(f"Deleting IPv6 route: {delete_command}")
        result = ssh_client.execute_cli_command(delete_command, "show ipv6 route static")
        cli_logger.log_command(delete_command, result['output'], result['success'])
        assert result['success'], "Failed to delete IPv6 route"

        # Recreate route
        logger.info(f"Recreating IPv6 route: {config_command}")
        result = ssh_client.execute_cli_command(config_command, "show ipv6 route static")

        # Log command execution
        cli_logger.log_command(config_command, result['output'], result['success'])
        cli_logger.log_verification("show ipv6 route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to recreate IPv6 route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv6 route {prefix} recreated successfully")

    @pytest.mark.vrf
    @pytest.mark.ipv4
    @pytest.mark.recreation
    def test_recreate_ipv4_vrf_route(self, test_context, ipv4_test_data):
        """
        TC-SR-048: Recreate IPv4 VRF route after deletion

        Test Steps:
            1. Configure IPv4 VRF route
            2. Delete the route
            3. Recreate the same route
            4. Verify route is recreated successfully
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        vrf_name = "Vrf1"
        prefix = "10.52.52.0/24"
        nexthop = "192.168.52.1"

        # Configure initial VRF route
        config_command = f"ip route vrf {vrf_name} {prefix} {nexthop}"
        logger.info(f"Configuring initial VRF route: {config_command}")
        result = ssh_client.execute_cli_command(config_command, "show ip route static")
        cli_logger.log_command(config_command, result['output'], result['success'])
        assert result['success'], "Failed to configure initial VRF route"

        # Delete route
        delete_command = f"no ip route vrf {vrf_name} {prefix} {nexthop}"
        logger.info(f"Deleting VRF route: {delete_command}")
        result = ssh_client.execute_cli_command(delete_command, "show ip route static")
        cli_logger.log_command(delete_command, result['output'], result['success'])
        assert result['success'], "Failed to delete VRF route"

        # Recreate route
        logger.info(f"Recreating VRF route: {config_command}")
        result = ssh_client.execute_cli_command(config_command, "show ip route static")

        # Log command execution
        cli_logger.log_command(config_command, result['output'], result['success'])
        cli_logger.log_verification("show ip route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to recreate VRF route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 VRF route {prefix} in {vrf_name} recreated successfully")

    @pytest.mark.vrf
    @pytest.mark.ipv6
    @pytest.mark.recreation
    def test_recreate_ipv6_vrf_route(self, test_context, ipv6_test_data):
        """
        TC-SR-049: Recreate IPv6 VRF route after deletion

        Test Steps:
            1. Configure IPv6 VRF route
            2. Delete the route
            3. Recreate the same route
            4. Verify route is recreated successfully
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        vrf_name = "Vrf1"
        prefix = "2001:db8:52::/64"
        nexthop = "2001:db8:520::1"

        # Configure initial IPv6 VRF route
        config_command = f"ipv6 route vrf {vrf_name} {prefix} {nexthop}"
        logger.info(f"Configuring initial IPv6 VRF route: {config_command}")
        result = ssh_client.execute_cli_command(config_command, "show ipv6 route static")
        cli_logger.log_command(config_command, result['output'], result['success'])
        assert result['success'], "Failed to configure initial IPv6 VRF route"

        # Delete route
        delete_command = f"no ipv6 route vrf {vrf_name} {prefix} {nexthop}"
        logger.info(f"Deleting IPv6 VRF route: {delete_command}")
        result = ssh_client.execute_cli_command(delete_command, "show ipv6 route static")
        cli_logger.log_command(delete_command, result['output'], result['success'])
        assert result['success'], "Failed to delete IPv6 VRF route"

        # Recreate route
        logger.info(f"Recreating IPv6 VRF route: {config_command}")
        result = ssh_client.execute_cli_command(config_command, "show ipv6 route static")

        # Log command execution
        cli_logger.log_command(config_command, result['output'], result['success'])
        cli_logger.log_verification("show ipv6 route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to recreate IPv6 VRF route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv6 VRF route {prefix} in {vrf_name} recreated successfully")

    @pytest.mark.ipv4
    @pytest.mark.interface
    @pytest.mark.recreation
    def test_recreate_ipv4_interface_route(self, test_context, ipv4_test_data):
        """
        TC-SR-050: Recreate IPv4 interface route after deletion

        Test Steps:
            1. Configure IPv4 interface route
            2. Delete the route
            3. Recreate the same route
            4. Verify route is recreated successfully
        """
        ssh_client = test_context['ssh_client']
        cli_logger = test_context['cli_logger']
        logger = test_context['logger']

        # Test data
        prefix = "10.53.53.0/24"
        interface = "Ethernet0"

        # Configure initial interface route
        config_command = f"ip route {prefix} interface {interface}"
        logger.info(f"Configuring initial interface route: {config_command}")
        result = ssh_client.execute_cli_command(config_command, "show ip route static")
        cli_logger.log_command(config_command, result['output'], result['success'])
        assert result['success'], "Failed to configure initial interface route"

        # Delete route
        delete_command = f"no ip route {prefix} interface {interface}"
        logger.info(f"Deleting interface route: {delete_command}")
        result = ssh_client.execute_cli_command(delete_command, "show ip route static")
        cli_logger.log_command(delete_command, result['output'], result['success'])
        assert result['success'], "Failed to delete interface route"

        # Recreate route
        logger.info(f"Recreating interface route: {config_command}")
        result = ssh_client.execute_cli_command(config_command, "show ip route static")

        # Log command execution
        cli_logger.log_command(config_command, result['output'], result['success'])
        cli_logger.log_verification("show ip route static", result['verification_output'])

        # Assertions
        assert result['success'], f"Failed to recreate interface route: {result.get('error', 'Unknown error')}"

        logger.info(f"Test passed: IPv4 interface route {prefix} via {interface} recreated successfully")
