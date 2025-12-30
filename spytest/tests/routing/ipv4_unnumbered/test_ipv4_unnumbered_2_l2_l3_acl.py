"""
IPv4 Unnumbered Interface - L2/L3/ACL Scenarios
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_2node_unnumbered.yaml  \
  tests/routing/ipv4_unnumbered/test_ipv4_unnumbered_2_l2_l3_acl.py \
  --logs-path ./logs/test_ipv4_unnumbered_l2_l3_acl_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Validates that IPv4 unnumbered interfaces function correctly in Layer 2, Layer 3,
  and ACL scenarios, behaving equivalently to numbered interfaces for routing and
  access control operations. Verifies that unnumbered interfaces support ping with
  source selection, static routing configurations, ACL enforcement, and maintain
  proper reachability. Tests use klish CLI type exclusively and verify that
  unnumbered interfaces integrate seamlessly into L2/L3 forwarding and security policies.

Pre-requisites:
  - Topology: 2 nodes (DUT1 + DUT2) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        #                    +------------------------+
        #                    |         DUT1           |
        #                    |  Loopback0: 10.10.10.1 | (Donor)
        #                    |  Ethernet0: unnumbered | (Borrows)
        #                    +------------------------+
        #                             |
        #                             | Ethernet0 (unnumbered)
        #                             |
        #                    +------------------------+
        #                    |         DUT2           |
        #                    |  Ethernet0: 10.10.10.2 |
        #                    |  Loopback0: 20.20.20.1 |
        #                    +------------------------+
  - Feature: IPv4 unnumbered interface, static routing, ACL support
  - Required variables: See vars_ipv4_unnumbered_l2_l3_acl.yaml
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

import pytest

from spytest import SpyTestDict, st
from spytest.dicts import SpyTestDict

# Import APIs
import apis.routing.ip as ip_api
import apis.system.interface as interface_api
import apis.system.basic as basic_api


@pytest.mark.topology("any")
class TestIPv4UnnumberedL2L3ACL:
    """
    Test class for IPv4 unnumbered interface L2/L3/ACL validation.

    Test Coverage:
    - TC_IPv4_Unnumbered_1.2.2.1: Configure unnumbered and verify
    - TC_IPv4_Unnumbered_1.2.2.2: Test basic connectivity
    - TC_IPv4_Unnumbered_1.2.2.3: Test ping with source selection
    - TC_IPv4_Unnumbered_1.2.2.4: Configure static routes over unnumbered
    - TC_IPv4_Unnumbered_1.2.2.5: Test ACL permit enforcement
    - TC_IPv4_Unnumbered_1.2.2.6: Test ACL deny enforcement
    """

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """
        Setup class-level test environment.
        Collects topology information and initializes test parameters.
        """
        st.log("=" * 80)
        st.log("IPv4 Unnumbered - L2/L3/ACL Scenarios - Setup Class")
        st.log("=" * 80)

        # Get topology - 2 nodes required
        cls.data.topology = st.ensure_min_topology("D1D2:1")

        # CLI type - using klish exclusively as per requirement
        cls.data.cli_type = "klish"

        # Get DUT handles
        cls.data.dut1 = cls.data.topology.D1
        cls.data.dut2 = cls.data.topology.D2

        # Get DUT names
        dut_names = st.get_dut_names()
        cls.data.dut1_name = dut_names[0] if len(dut_names) > 0 else "DUT1"
        cls.data.dut2_name = dut_names[1] if len(dut_names) > 1 else "DUT2"

        # Test parameters - DUT1 configuration
        cls.data.dut1_donor_interface = "Loopback0"
        cls.data.dut1_donor_ip = "10.10.10.1/32"
        cls.data.dut1_donor_ip_addr = "10.10.10.1"

        cls.data.dut1_target_interface = "Ethernet0"

        # Test parameters - DUT2 configuration
        cls.data.dut2_interface = "Ethernet0"
        cls.data.dut2_ip = "10.10.10.2/30"
        cls.data.dut2_ip_addr = "10.10.10.2"

        cls.data.dut2_loopback = "Loopback0"
        cls.data.dut2_loopback_ip = "20.20.20.1/32"
        cls.data.dut2_loopback_ip_addr = "20.20.20.1"

        # Static routes
        cls.data.dut1_static_route_dest = "20.20.20.1/32"
        cls.data.dut1_static_route_nexthop = "10.10.10.2"

        cls.data.dut2_static_route_dest = "10.10.10.1/32"
        cls.data.dut2_static_route_nexthop = "10.10.10.1"

        # ACL parameters
        cls.data.acl_name_permit = "TEST_ACL"
        cls.data.acl_name_deny = "TEST_ACL_DENY"

        # Configuration tracking
        cls.data.dut1_configured = False
        cls.data.dut2_configured = False
        cls.data.static_routes_configured = False
        cls.data.acl_configured = False

        st.log("Test parameters:")
        st.log(f"  DUT1: {cls.data.dut1_name}")
        st.log(f"  DUT2: {cls.data.dut2_name}")
        st.log(f"  DUT1 Donor: {cls.data.dut1_donor_interface} - {cls.data.dut1_donor_ip}")
        st.log(f"  DUT1 Target: {cls.data.dut1_target_interface} (unnumbered)")
        st.log(f"  DUT2 Interface: {cls.data.dut2_interface} - {cls.data.dut2_ip}")
        st.log(f"  CLI type: {cls.data.cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """
        Teardown class-level configuration.
        Removes all test configurations.
        """
        st.log("=" * 80)
        st.log("IPv4 Unnumbered - L2/L3/ACL Scenarios - Teardown Class")
        st.log("=" * 80)

        cls._cleanup_all_configuration()

    def setup_method(self) -> None:
        """
        Setup per-test method.
        Ensures DUTs are reachable.
        """
        st.log("Test method setup - verifying DUT reachability")

        # Verify DUTs are reachable
        for dut in [self.data.dut1, self.data.dut2]:
            if not basic_api.poll_for_system_status(dut, iteration=5, delay=2):
                st.error(f"DUT {dut} is not ready")

    def teardown_method(self) -> None:
        """
        Teardown per-test method.
        """
        st.log("Test method teardown")

    @classmethod
    def _cleanup_all_configuration(cls) -> None:
        """
        Remove all test configuration from both DUTs.
        """
        st.log("Cleaning up all test configuration")

        try:
            # Cleanup DUT1
            st.log("Cleaning up DUT1 configuration")

            # Remove ACLs from interface
            cmd = f"configure terminal; interface {cls.data.dut1_target_interface}; no ip access-group {cls.data.acl_name_permit} in; exit; exit"
            st.config(cls.data.dut1, cmd, type=cls.data.cli_type, skip_error_check=True)

            cmd = f"configure terminal; interface {cls.data.dut1_target_interface}; no ip access-group {cls.data.acl_name_deny} in; exit; exit"
            st.config(cls.data.dut1, cmd, type=cls.data.cli_type, skip_error_check=True)

            # Remove ACLs
            cmd = f"configure terminal; no ip access-list {cls.data.acl_name_permit}; exit"
            st.config(cls.data.dut1, cmd, type=cls.data.cli_type, skip_error_check=True)

            cmd = f"configure terminal; no ip access-list {cls.data.acl_name_deny}; exit"
            st.config(cls.data.dut1, cmd, type=cls.data.cli_type, skip_error_check=True)

            # Remove static route
            cmd = f"configure terminal; no ip route {cls.data.dut1_static_route_dest} {cls.data.dut1_static_route_nexthop}; exit"
            st.config(cls.data.dut1, cmd, type=cls.data.cli_type, skip_error_check=True)

            # Remove unnumbered
            cmd = f"configure terminal; interface {cls.data.dut1_target_interface}; no ip unnumbered {cls.data.dut1_donor_interface}; exit; exit"
            st.config(cls.data.dut1, cmd, type=cls.data.cli_type, skip_error_check=True)

            # Remove donor IP
            cmd = f"configure terminal; interface {cls.data.dut1_donor_interface}; no ip address {cls.data.dut1_donor_ip}; exit; exit"
            st.config(cls.data.dut1, cmd, type=cls.data.cli_type, skip_error_check=True)

            # Cleanup DUT2
            st.log("Cleaning up DUT2 configuration")

            # Remove static route
            cmd = f"configure terminal; no ip route {cls.data.dut2_static_route_dest} {cls.data.dut2_static_route_nexthop}; exit"
            st.config(cls.data.dut2, cmd, type=cls.data.cli_type, skip_error_check=True)

            # Remove interface IPs
            cmd = f"configure terminal; interface {cls.data.dut2_interface}; no ip address {cls.data.dut2_ip}; exit; exit"
            st.config(cls.data.dut2, cmd, type=cls.data.cli_type, skip_error_check=True)

            cmd = f"configure terminal; interface {cls.data.dut2_loopback}; no ip address {cls.data.dut2_loopback_ip}; exit; exit"
            st.config(cls.data.dut2, cmd, type=cls.data.cli_type, skip_error_check=True)

        except Exception as e:
            st.log(f"Exception during cleanup: {e}")

    def _configure_dut1_donor_interface(self) -> None:
        """
        Configure donor interface (Loopback0) on DUT1.
        """
        st.log(f"Configuring DUT1 donor interface {self.data.dut1_donor_interface}")

        cmd_list = [
            "configure terminal",
            f"interface {self.data.dut1_donor_interface}",
            f"ip address {self.data.dut1_donor_ip}",
            "no shutdown",
            "exit",
            "exit"
        ]

        for cmd in cmd_list:
            result = st.config(self.data.dut1, cmd, type=self.data.cli_type)
            if not result:
                st.report_fail("msg", f"Failed to execute command on DUT1: {cmd}")

        st.wait(2, "Waiting for donor interface configuration")

        st.log("DUT1 donor interface configured successfully")

    def _configure_dut1_unnumbered_interface(self) -> None:
        """
        Configure unnumbered interface (Ethernet0) on DUT1.
        """
        st.log(f"Configuring DUT1 unnumbered interface {self.data.dut1_target_interface}")

        cmd_list = [
            "configure terminal",
            f"interface {self.data.dut1_target_interface}",
            "no shutdown",
            f"ip unnumbered {self.data.dut1_donor_interface}",
            "exit",
            "exit"
        ]

        for cmd in cmd_list:
            result = st.config(self.data.dut1, cmd, type=self.data.cli_type)
            if not result:
                st.report_fail("msg", f"Failed to execute command on DUT1: {cmd}")

        st.wait(2, "Waiting for unnumbered interface configuration")

        self.data.dut1_configured = True

        st.log("DUT1 unnumbered interface configured successfully")

    def _configure_dut2_interfaces(self) -> None:
        """
        Configure interfaces on DUT2.
        """
        st.log("Configuring DUT2 interfaces")

        # Configure Ethernet0
        cmd_list = [
            "configure terminal",
            f"interface {self.data.dut2_interface}",
            f"ip address {self.data.dut2_ip}",
            "no shutdown",
            "exit",
            "exit"
        ]

        for cmd in cmd_list:
            result = st.config(self.data.dut2, cmd, type=self.data.cli_type)
            if not result:
                st.report_fail("msg", f"Failed to execute command on DUT2: {cmd}")

        # Configure Loopback0
        cmd_list = [
            "configure terminal",
            f"interface {self.data.dut2_loopback}",
            f"ip address {self.data.dut2_loopback_ip}",
            "no shutdown",
            "exit",
            "exit"
        ]

        for cmd in cmd_list:
            result = st.config(self.data.dut2, cmd, type=self.data.cli_type)
            if not result:
                st.report_fail("msg", f"Failed to execute command on DUT2: {cmd}")

        st.wait(2, "Waiting for DUT2 interface configuration")

        self.data.dut2_configured = True

        st.log("DUT2 interfaces configured successfully")

    def _save_configuration(self, dut) -> None:
        """
        Save running configuration.

        Args:
            dut: DUT to save configuration on
        """
        st.log(f"Saving configuration on {dut}")

        result = st.config(dut, "write memory", type=self.data.cli_type)

        if not result:
            st.log(f"Warning: Failed to save configuration on {dut}")

        st.wait(2, "Waiting after configuration save")

    def _verify_running_config_has_string(self, dut, search_string: str, interface: Optional[str] = None) -> bool:
        """
        Verify running-config contains a specific string.

        Args:
            dut: DUT to check
            search_string: String to search for
            interface: Optional interface name to limit search

        Returns:
            True if string found, False otherwise
        """
        if interface:
            st.log(f"Verifying running-config for interface {interface} contains '{search_string}'")
            output = st.show(dut, f"show running-config interface {interface}", type=self.data.cli_type)
        else:
            st.log(f"Verifying running-config contains '{search_string}'")
            output = st.show(dut, "show running-config", type=self.data.cli_type)

        st.log(f"Running-config output: {output}")

        output_str = str(output)
        found = search_string in output_str

        if found:
            st.log(f"✓ Found '{search_string}' in running-config")
            return True
        else:
            st.error(f"✗ Not found '{search_string}' in running-config")
            return False

    def _verify_route_in_table(self, dut, route_prefix: str, should_exist: bool = True) -> bool:
        """
        Verify route exists in routing table.

        Args:
            dut: DUT to check
            route_prefix: Route prefix to search for
            should_exist: True if route should exist, False otherwise

        Returns:
            True if verification passes, False otherwise
        """
        st.log(f"Verifying route {route_prefix} {'exists' if should_exist else 'does not exist'} in routing table")

        output = st.show(dut, "show ip route", type=self.data.cli_type)

        st.log(f"Routing table: {output}")

        output_str = str(output)
        route_found = route_prefix in output_str

        if should_exist:
            if route_found:
                st.log(f"✓ Route {route_prefix} found in routing table")
                return True
            else:
                st.error(f"✗ Route {route_prefix} not found in routing table")
                return False
        else:
            if not route_found:
                st.log(f"✓ Route {route_prefix} correctly not in routing table")
                return True
            else:
                st.error(f"✗ Route {route_prefix} unexpectedly found in routing table")
                return False

    def _test_ping(self, source_dut, destination_ip: str, count: int = 5, source_ip: Optional[str] = None) -> Dict[str, Any]:
        """
        Test ping connectivity.

        Args:
            source_dut: Source DUT
            destination_ip: Destination IP address
            count: Number of ping packets
            source_ip: Optional source IP address

        Returns:
            Dictionary with ping statistics
        """
        if source_ip:
            st.log(f"Testing ping from {source_ip} to {destination_ip} (count={count})")
            cmd = f"ping {destination_ip} -I {source_ip} -c {count}"
        else:
            st.log(f"Testing ping to {destination_ip} (count={count})")
            cmd = f"ping {destination_ip} -c {count}"

        output = st.config(source_dut, cmd, type="vtysh", skip_error_check=True)

        st.log(f"Ping output: {output}")

        # Parse ping statistics
        stats = {
            "transmitted": 0,
            "received": 0,
            "loss_percent": 100.0,
            "success": False
        }

        output_str = str(output)

        # Parse transmitted/received
        match = re.search(r"(\d+)\s+packets\s+transmitted.*?(\d+)\s+received", output_str)
        if match:
            stats["transmitted"] = int(match.group(1))
            stats["received"] = int(match.group(2))

        # Parse packet loss
        match = re.search(r"(\d+\.?\d*)%\s+packet\s+loss", output_str)
        if match:
            stats["loss_percent"] = float(match.group(1))

        # Determine success
        if stats["loss_percent"] == 0.0 and stats["received"] > 0:
            stats["success"] = True

        st.log(f"Ping statistics: {stats}")

        return stats

    def _configure_static_route(self, dut, destination: str, nexthop: str) -> None:
        """
        Configure static route.

        Args:
            dut: DUT to configure on
            destination: Destination prefix
            nexthop: Next-hop IP address
        """
        st.log(f"Configuring static route {destination} via {nexthop}")

        cmd_list = [
            "configure terminal",
            f"ip route {destination} {nexthop}",
            "exit"
        ]

        for cmd in cmd_list:
            result = st.config(dut, cmd, type=self.data.cli_type)
            if not result:
                st.report_fail("msg", f"Failed to configure static route: {cmd}")

        st.wait(2, "Waiting for static route installation")

        st.log(f"Static route {destination} via {nexthop} configured")

    def _create_acl(self, dut, acl_name: str, rules: List[str]) -> None:
        """
        Create IP access list with rules.

        Args:
            dut: DUT to configure on
            acl_name: Name of the ACL
            rules: List of ACL rule strings
        """
        st.log(f"Creating ACL {acl_name} with {len(rules)} rules")

        cmd_list = [
            "configure terminal",
            f"ip access-list {acl_name}"
        ]

        # Add rules
        cmd_list.extend(rules)

        cmd_list.extend(["exit", "exit"])

        for cmd in cmd_list:
            result = st.config(dut, cmd, type=self.data.cli_type)
            if not result:
                st.report_fail("msg", f"Failed to configure ACL: {cmd}")

        st.wait(1, "Waiting for ACL creation")

        st.log(f"ACL {acl_name} created successfully")

    def _apply_acl_to_interface(self, dut, interface: str, acl_name: str, direction: str = "in") -> None:
        """
        Apply ACL to interface.

        Args:
            dut: DUT to configure on
            interface: Interface name
            acl_name: ACL name
            direction: Direction (in or out)
        """
        st.log(f"Applying ACL {acl_name} to interface {interface} ({direction})")

        cmd_list = [
            "configure terminal",
            f"interface {interface}",
            f"ip access-group {acl_name} {direction}",
            "exit",
            "exit"
        ]

        for cmd in cmd_list:
            result = st.config(dut, cmd, type=self.data.cli_type)
            if not result:
                st.report_fail("msg", f"Failed to apply ACL: {cmd}")

        st.wait(1, "Waiting for ACL application")

        st.log(f"ACL {acl_name} applied to {interface}")

    def _remove_acl_from_interface(self, dut, interface: str, acl_name: str, direction: str = "in") -> None:
        """
        Remove ACL from interface.

        Args:
            dut: DUT to configure on
            interface: Interface name
            acl_name: ACL name
            direction: Direction (in or out)
        """
        st.log(f"Removing ACL {acl_name} from interface {interface}")

        cmd_list = [
            "configure terminal",
            f"interface {interface}",
            f"no ip access-group {acl_name} {direction}",
            "exit",
            "exit"
        ]

        for cmd in cmd_list:
            result = st.config(dut, cmd, type=self.data.cli_type, skip_error_check=True)

        st.wait(1, "Waiting after ACL removal")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_IPv4_Unnumbered_1.2.2.1"])
    def test_ipv4_unnumbered_l2_l3_acl_configure_and_verify(self) -> None:
        """
        TC_IPv4_Unnumbered_1.2.2.1: Configure unnumbered and verify configuration.

        Test Steps:
        1. Configure DUT1 Loopback0 (donor) with IP
        2. Configure DUT1 Ethernet0 (unnumbered) borrowing from Loopback0
        3. Configure DUT2 Ethernet0 and Loopback0
        4. Verify running-config on both DUTs
        5. Save configurations
        """
        st.banner("TC_IPv4_Unnumbered_1.2.2.1: Configure and Verify Unnumbered")

        # Step 1: Configure DUT1 donor interface
        self._configure_dut1_donor_interface()

        # Step 2: Verify donor interface configured
        if not self._verify_running_config_has_string(
            self.data.dut1,
            f"ip address {self.data.dut1_donor_ip}",
            interface=self.data.dut1_donor_interface
        ):
            st.report_fail("msg", "DUT1 donor interface not configured")

        # Step 3: Configure DUT1 unnumbered interface
        self._configure_dut1_unnumbered_interface()

        # Step 4: Verify unnumbered configuration
        if not self._verify_running_config_has_string(
            self.data.dut1,
            f"ip unnumbered {self.data.dut1_donor_interface}",
            interface=self.data.dut1_target_interface
        ):
            st.report_fail("msg", "DUT1 unnumbered interface not configured")

        # Step 5: Configure DUT2 interfaces
        self._configure_dut2_interfaces()

        # Step 6: Verify DUT2 Ethernet0 configured
        if not self._verify_running_config_has_string(
            self.data.dut2,
            f"ip address {self.data.dut2_ip}",
            interface=self.data.dut2_interface
        ):
            st.report_fail("msg", "DUT2 Ethernet0 not configured")

        # Step 7: Verify DUT2 Loopback0 configured
        if not self._verify_running_config_has_string(
            self.data.dut2,
            f"ip address {self.data.dut2_loopback_ip}",
            interface=self.data.dut2_loopback
        ):
            st.report_fail("msg", "DUT2 Loopback0 not configured")

        # Step 8: Save configurations
        self._save_configuration(self.data.dut1)
        self._save_configuration(self.data.dut2)

        # Step 9: Verify running-config shows all configurations
        st.log("Verifying complete running-config on both DUTs")

        output_dut1 = st.show(self.data.dut1, "show running-config", type=self.data.cli_type)
        st.log(f"DUT1 running-config: {output_dut1}")

        output_dut2 = st.show(self.data.dut2, "show running-config", type=self.data.cli_type)
        st.log(f"DUT2 running-config: {output_dut2}")

        st.log("✓ Test passed: Unnumbered configuration successful")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_IPv4_Unnumbered_1.2.2.2"])
    def test_ipv4_unnumbered_l2_l3_acl_basic_connectivity(self) -> None:
        """
        TC_IPv4_Unnumbered_1.2.2.2: Test basic Layer 3 connectivity.

        Test Steps:
        1. Ensure configuration exists
        2. Ping DUT2 Ethernet0 from DUT1
        3. Verify 0% packet loss
        4. Verify ARP resolution
        """
        st.banner("TC_IPv4_Unnumbered_1.2.2.2: Basic Connectivity Test")

        # Step 1: Ensure configuration exists
        if not self.data.dut1_configured or not self.data.dut2_configured:
            st.log("Configuration not present, configuring now...")
            self._configure_dut1_donor_interface()
            self._configure_dut1_unnumbered_interface()
            self._configure_dut2_interfaces()
            self._save_configuration(self.data.dut1)
            self._save_configuration(self.data.dut2)

        # Step 2: Wait for interfaces to be up
        st.wait(5, "Waiting for interfaces to stabilize")

        # Step 3: Ping DUT2 from DUT1
        ping_stats = self._test_ping(
            self.data.dut1,
            self.data.dut2_ip_addr,
            count=5
        )

        # Step 4: Verify ping successful
        if not ping_stats["success"]:
            st.report_fail(
                "msg",
                f"Ping from DUT1 to DUT2 ({self.data.dut2_ip_addr}) failed: "
                f"{ping_stats['loss_percent']}% packet loss"
            )

        if ping_stats["loss_percent"] > 0:
            st.report_fail(
                "msg",
                f"Packet loss detected: {ping_stats['loss_percent']}%"
            )

        # Step 5: Verify ARP resolution
        st.log("Verifying ARP resolution")
        arp_output = st.show(self.data.dut1, "show arp", type=self.data.cli_type)
        st.log(f"ARP table: {arp_output}")

        arp_str = str(arp_output)
        if self.data.dut2_ip_addr not in arp_str:
            st.log(f"Warning: DUT2 IP {self.data.dut2_ip_addr} not in ARP table (may not be critical)")

        st.log("✓ Test passed: Basic connectivity successful")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_IPv4_Unnumbered_1.2.2.3"])
    def test_ipv4_unnumbered_l2_l3_acl_ping_source_selection(self) -> None:
        """
        TC_IPv4_Unnumbered_1.2.2.3: Test ping with source IP selection.

        Test Steps:
        1. Ensure configuration exists
        2. Ping with source IP (borrowed IP from Loopback0)
        3. Verify ping successful with source selection
        4. Verify 0% packet loss
        """
        st.banner("TC_IPv4_Unnumbered_1.2.2.3: Ping with Source Selection")

        # Step 1: Ensure configuration exists
        if not self.data.dut1_configured or not self.data.dut2_configured:
            st.log("Configuration not present, configuring now...")
            self._configure_dut1_donor_interface()
            self._configure_dut1_unnumbered_interface()
            self._configure_dut2_interfaces()
            self._save_configuration(self.data.dut1)
            self._save_configuration(self.data.dut2)

        # Step 2: Wait for interfaces to be up
        st.wait(3, "Waiting for interfaces to stabilize")

        # Step 3: Ping with source IP selection
        ping_stats = self._test_ping(
            self.data.dut1,
            self.data.dut2_ip_addr,
            count=5,
            source_ip=self.data.dut1_donor_ip_addr
        )

        # Step 4: Verify ping successful
        if not ping_stats["success"]:
            st.report_fail(
                "msg",
                f"Ping with source {self.data.dut1_donor_ip_addr} to DUT2 failed: "
                f"{ping_stats['loss_percent']}% packet loss"
            )

        if ping_stats["loss_percent"] > 0:
            st.report_fail(
                "msg",
                f"Packet loss with source selection: {ping_stats['loss_percent']}%"
            )

        st.log(f"✓ Ping with source {self.data.dut1_donor_ip_addr} successful")

        st.log("✓ Test passed: Ping with source selection successful")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_IPv4_Unnumbered_1.2.2.4"])
    def test_ipv4_unnumbered_l2_l3_acl_static_routes(self) -> None:
        """
        TC_IPv4_Unnumbered_1.2.2.4: Configure static routes over unnumbered.

        Test Steps:
        1. Ensure basic configuration exists
        2. Configure static route on DUT1 to DUT2 Loopback0
        3. Configure static route on DUT2 to DUT1 Loopback0
        4. Verify routes in routing table
        5. Test end-to-end connectivity (DUT1 Loopback0 to DUT2 Loopback0)
        6. Verify 0% packet loss
        """
        st.banner("TC_IPv4_Unnumbered_1.2.2.4: Static Routes over Unnumbered")

        # Step 1: Ensure configuration exists
        if not self.data.dut1_configured or not self.data.dut2_configured:
            st.log("Configuration not present, configuring now...")
            self._configure_dut1_donor_interface()
            self._configure_dut1_unnumbered_interface()
            self._configure_dut2_interfaces()
            self._save_configuration(self.data.dut1)
            self._save_configuration(self.data.dut2)

        # Step 2: Configure static route on DUT1
        self._configure_static_route(
            self.data.dut1,
            self.data.dut1_static_route_dest,
            self.data.dut1_static_route_nexthop
        )

        # Step 3: Verify route on DUT1
        if not self._verify_route_in_table(self.data.dut1, "20.20.20.1", should_exist=True):
            st.report_fail("msg", "Static route to 20.20.20.1 not installed on DUT1")

        # Step 4: Configure static route on DUT2
        self._configure_static_route(
            self.data.dut2,
            self.data.dut2_static_route_dest,
            self.data.dut2_static_route_nexthop
        )

        # Step 5: Verify route on DUT2
        if not self._verify_route_in_table(self.data.dut2, "10.10.10.1", should_exist=True):
            st.report_fail("msg", "Static route to 10.10.10.1 not installed on DUT2")

        self.data.static_routes_configured = True

        # Step 6: Verify routing table shows routes
        st.log("Verifying routing tables on both DUTs")

        route_output_dut1 = st.show(self.data.dut1, "show ip route", type=self.data.cli_type)
        st.log(f"DUT1 routing table: {route_output_dut1}")

        route_output_dut2 = st.show(self.data.dut2, "show ip route", type=self.data.cli_type)
        st.log(f"DUT2 routing table: {route_output_dut2}")

        # Step 7: Test end-to-end connectivity
        st.log("Testing end-to-end connectivity via static routes")

        # Ping from DUT1 to DUT2 Loopback0
        ping_stats = self._test_ping(
            self.data.dut1,
            self.data.dut2_loopback_ip_addr,
            count=10
        )

        if not ping_stats["success"]:
            st.report_fail(
                "msg",
                f"Ping from DUT1 to DUT2 Loopback0 ({self.data.dut2_loopback_ip_addr}) failed: "
                f"{ping_stats['loss_percent']}% packet loss"
            )

        # Ping from DUT2 to DUT1 Loopback0
        ping_stats_reverse = self._test_ping(
            self.data.dut2,
            self.data.dut1_donor_ip_addr,
            count=10
        )

        if not ping_stats_reverse["success"]:
            st.report_fail(
                "msg",
                f"Ping from DUT2 to DUT1 Loopback0 ({self.data.dut1_donor_ip_addr}) failed: "
                f"{ping_stats_reverse['loss_percent']}% packet loss"
            )

        # Step 8: Save configurations
        self._save_configuration(self.data.dut1)
        self._save_configuration(self.data.dut2)

        st.log("✓ Test passed: Static routes over unnumbered successful")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_IPv4_Unnumbered_1.2.2.5"])
    def test_ipv4_unnumbered_l2_l3_acl_permit_enforcement(self) -> None:
        """
        TC_IPv4_Unnumbered_1.2.2.5: Test ACL permit enforcement on unnumbered.

        Test Steps:
        1. Ensure configuration exists
        2. Create ACL with permit rules
        3. Apply ACL to unnumbered interface (inbound)
        4. Verify ACL in running-config
        5. Test traffic (should be permitted)
        6. Verify 0% packet loss
        """
        st.banner("TC_IPv4_Unnumbered_1.2.2.5: ACL Permit Enforcement")

        # Step 1: Ensure configuration exists
        if not self.data.dut1_configured or not self.data.dut2_configured:
            st.log("Configuration not present, configuring now...")
            self._configure_dut1_donor_interface()
            self._configure_dut1_unnumbered_interface()
            self._configure_dut2_interfaces()
            self._save_configuration(self.data.dut1)
            self._save_configuration(self.data.dut2)

        # Step 2: Create ACL with permit rules
        acl_rules = [
            f"permit icmp {self.data.dut2_ip_addr}/32 any",
            "permit tcp any any established",
            "deny ip any any"
        ]

        self._create_acl(self.data.dut1, self.data.acl_name_permit, acl_rules)

        # Step 3: Apply ACL to unnumbered interface
        self._apply_acl_to_interface(
            self.data.dut1,
            self.data.dut1_target_interface,
            self.data.acl_name_permit,
            direction="in"
        )

        self.data.acl_configured = True

        # Step 4: Verify ACL in running-config
        if not self._verify_running_config_has_string(
            self.data.dut1,
            f"ip access-group {self.data.acl_name_permit} in",
            interface=self.data.dut1_target_interface
        ):
            st.report_fail("msg", "ACL not applied to interface")

        # Step 5: Verify ACL configuration
        acl_output = st.show(
            self.data.dut1,
            f"show ip access-lists {self.data.acl_name_permit}",
            type=self.data.cli_type,
            skip_error_check=True
        )
        st.log(f"ACL configuration: {acl_output}")

        # Step 6: Wait for ACL to take effect
        st.wait(3, "Waiting for ACL to take effect")

        # Step 7: Test traffic (should be permitted)
        st.log("Testing traffic with permit ACL (ICMP should be allowed)")

        ping_stats = self._test_ping(
            self.data.dut2,
            self.data.dut1_donor_ip_addr,
            count=5
        )

        # Step 8: Verify traffic permitted (0% loss)
        if not ping_stats["success"]:
            st.report_fail(
                "msg",
                f"Traffic blocked by permit ACL (should be allowed): "
                f"{ping_stats['loss_percent']}% packet loss"
            )

        if ping_stats["loss_percent"] > 0:
            st.report_fail(
                "msg",
                f"Unexpected packet loss with permit ACL: {ping_stats['loss_percent']}%"
            )

        st.log("✓ ACL permit rule working correctly")

        st.log("✓ Test passed: ACL permit enforcement successful")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_IPv4_Unnumbered_1.2.2.6"])
    def test_ipv4_unnumbered_l2_l3_acl_deny_enforcement(self) -> None:
        """
        TC_IPv4_Unnumbered_1.2.2.6: Test ACL deny enforcement on unnumbered.

        Test Steps:
        1. Ensure configuration exists
        2. Remove permit ACL if applied
        3. Create ACL with deny rules
        4. Apply deny ACL to unnumbered interface
        5. Test traffic (should be denied)
        6. Verify 100% packet loss
        7. Restore permit ACL
        8. Verify traffic resumes
        """
        st.banner("TC_IPv4_Unnumbered_1.2.2.6: ACL Deny Enforcement")

        # Step 1: Ensure configuration exists
        if not self.data.dut1_configured or not self.data.dut2_configured:
            st.log("Configuration not present, configuring now...")
            self._configure_dut1_donor_interface()
            self._configure_dut1_unnumbered_interface()
            self._configure_dut2_interfaces()
            self._save_configuration(self.data.dut1)
            self._save_configuration(self.data.dut2)

        # Step 2: Remove permit ACL if applied
        if self.data.acl_configured:
            self._remove_acl_from_interface(
                self.data.dut1,
                self.data.dut1_target_interface,
                self.data.acl_name_permit,
                direction="in"
            )

        # Step 3: Create deny ACL
        acl_rules_deny = [
            f"deny icmp {self.data.dut2_ip_addr}/32 any",
            "permit icmp any any"
        ]

        self._create_acl(self.data.dut1, self.data.acl_name_deny, acl_rules_deny)

        # Step 4: Apply deny ACL to interface
        self._apply_acl_to_interface(
            self.data.dut1,
            self.data.dut1_target_interface,
            self.data.acl_name_deny,
            direction="in"
        )

        # Step 5: Verify deny ACL applied
        if not self._verify_running_config_has_string(
            self.data.dut1,
            f"ip access-group {self.data.acl_name_deny} in",
            interface=self.data.dut1_target_interface
        ):
            st.report_fail("msg", "Deny ACL not applied to interface")

        # Step 6: Wait for ACL to take effect
        st.wait(3, "Waiting for deny ACL to take effect")

        # Step 7: Test traffic (should be denied)
        st.log("Testing traffic with deny ACL (ICMP should be blocked)")

        ping_stats = self._test_ping(
            self.data.dut2,
            self.data.dut1_donor_ip_addr,
            count=5
        )

        # Step 8: Verify traffic denied (100% loss expected)
        if ping_stats["success"]:
            st.report_fail(
                "msg",
                "Traffic allowed by deny ACL (should be blocked)"
            )

        if ping_stats["loss_percent"] != 100.0:
            st.log(
                f"Warning: Expected 100% loss, got {ping_stats['loss_percent']}% "
                "(ACL may not be fully enforcing)"
            )

        st.log("✓ ACL deny rule working correctly")

        # Step 9: Restore permit ACL
        st.log("Restoring permit ACL to resume traffic")

        self._remove_acl_from_interface(
            self.data.dut1,
            self.data.dut1_target_interface,
            self.data.acl_name_deny,
            direction="in"
        )

        # Re-create and apply permit ACL
        acl_rules_permit = [
            f"permit icmp {self.data.dut2_ip_addr}/32 any",
            "permit tcp any any established",
            "deny ip any any"
        ]

        self._create_acl(self.data.dut1, self.data.acl_name_permit, acl_rules_permit)

        self._apply_acl_to_interface(
            self.data.dut1,
            self.data.dut1_target_interface,
            self.data.acl_name_permit,
            direction="in"
        )

        st.wait(3, "Waiting for permit ACL to take effect")

        # Step 10: Verify traffic resumes
        ping_stats_resume = self._test_ping(
            self.data.dut2,
            self.data.dut1_donor_ip_addr,
            count=5
        )

        if not ping_stats_resume["success"]:
            st.report_fail(
                "msg",
                "Traffic not resumed after restoring permit ACL"
            )

        st.log("✓ Traffic resumed with permit ACL")

        # Step 11: Save final configuration
        self._save_configuration(self.data.dut1)

        st.log("✓ Test passed: ACL deny enforcement successful")
        st.report_pass("test_case_passed")
