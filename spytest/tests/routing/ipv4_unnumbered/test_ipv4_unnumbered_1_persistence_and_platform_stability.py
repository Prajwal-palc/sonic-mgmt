"""
IPv4 Unnumbered Interface - Persistence and Platform Stability
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_1node_unnumbered.yaml  \
  tests/routing/ipv4_unnumbered/test_ipv4_unnumbered_1_persistence_and_platform_stability.py \
  --logs-path ./logs/test_ipv4_unnumbered_persistence_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Validates that IPv4 unnumbered interface configuration persists across various
  reboot types (warm, fast, cold), maintains system stability, and correctly handles
  donor IP dependency. Verifies that when the donor IP is removed, dependent
  unnumbered interfaces fail appropriately, and when the donor IP is restored,
  the unnumbered configuration recovers automatically. Tests use klish CLI type
  exclusively and verify configuration persistence, reboot resilience, and
  dependent behavior.

Pre-requisites:
  - Topology: 1 node (single DUT) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node
        #                    +------------------------+
        #                    |         DUT            |
        #                    |                        |
        #                    |  Loopback0 (Donor)     |
        #                    |  IP: 10.10.10.1/32     |
        #                    |          |             |
        #                    |          | (borrows)   |
        #                    |          ↓             |
        #                    |  Ethernet0 (Target)    |
        #                    |  ip unnumbered         |
        #                    |  Loopback0             |
        #                    +------------------------+
  - Feature: IPv4 unnumbered interface support
  - Reboot permissions required (warm, fast, cold)
  - Required variables: See vars_ipv4_unnumbered.yaml
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
import apis.system.reboot as reboot_api


@pytest.mark.topology("any")
class TestIPv4UnnumberedPersistence:
    """
    Test class for IPv4 unnumbered interface persistence and stability validation.

    Test Coverage:
    - TC_IPv4_Unnumbered_1.2.1.1: Configure IP unnumbered
    - TC_IPv4_Unnumbered_1.2.1.2: Warm reboot persistence
    - TC_IPv4_Unnumbered_1.2.1.3: Fast reboot persistence
    - TC_IPv4_Unnumbered_1.2.1.4: Cold reboot persistence
    - TC_IPv4_Unnumbered_1.2.1.5: Remove donor IP - dependent failure
    - TC_IPv4_Unnumbered_1.2.1.6: Restore donor IP - automatic recovery
    """

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """
        Setup class-level test environment.
        Collects topology information and initializes test parameters.
        """
        st.log("=" * 80)
        st.log("IPv4 Unnumbered - Persistence and Stability - Setup Class")
        st.log("=" * 80)

        # Get topology - single DUT required
        cls.data.topology = st.ensure_min_topology("D1")

        # CLI type - using klish exclusively as per requirement
        cls.data.cli_type = "klish"

        # Get DUT handle
        cls.data.dut = cls.data.topology.D1

        # Get DUT name
        dut_names = st.get_dut_names()
        cls.data.dut_name = dut_names[0] if len(dut_names) > 0 else "DUT1"

        # Test parameters
        cls.data.donor_interface = "Loopback0"
        cls.data.donor_ip = "10.10.10.1/32"
        cls.data.donor_ip_addr = "10.10.10.1"
        cls.data.donor_netmask = "32"

        # Target interface (unnumbered)
        cls.data.target_interface = "Ethernet0"

        # Reboot wait times (in seconds)
        cls.data.warm_reboot_wait = 600  # 10 minutes
        cls.data.fast_reboot_wait = 480  # 8 minutes
        cls.data.cold_reboot_wait = 900  # 15 minutes
        cls.data.post_reboot_stabilize = 60  # 1 minute stabilization

        # Configuration tracking
        cls.data.config_applied = False
        cls.data.donor_ip_configured = False
        cls.data.unnumbered_configured = False

        st.log("Test parameters:")
        st.log(f"  DUT: {cls.data.dut_name}")
        st.log(f"  Donor interface: {cls.data.donor_interface}")
        st.log(f"  Donor IP: {cls.data.donor_ip}")
        st.log(f"  Target interface: {cls.data.target_interface}")
        st.log(f"  CLI type: {cls.data.cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """
        Teardown class-level configuration.
        Removes all test configurations.
        """
        st.log("=" * 80)
        st.log("IPv4 Unnumbered - Persistence and Stability - Teardown Class")
        st.log("=" * 80)

        cls._cleanup_all_configuration()

    def setup_method(self) -> None:
        """
        Setup per-test method.
        Ensures DUT is reachable.
        """
        st.log("Test method setup - verifying DUT reachability")

        # Verify DUT is reachable
        if not basic_api.poll_for_system_status(self.data.dut, iteration=5, delay=2):
            st.error(f"DUT {self.data.dut_name} is not ready")

    def teardown_method(self) -> None:
        """
        Teardown per-test method.
        """
        st.log("Test method teardown")

    @classmethod
    def _cleanup_all_configuration(cls) -> None:
        """
        Remove all test configuration.
        """
        st.log("Cleaning up all test configuration")

        try:
            # Remove unnumbered configuration from target interface
            st.log(f"Removing unnumbered configuration from {cls.data.target_interface}")

            # Use st.config for klish commands
            cmd = f"configure terminal; interface {cls.data.target_interface}; no ip unnumbered {cls.data.donor_interface}; exit; exit"
            st.config(cls.data.dut, cmd, type=cls.data.cli_type, skip_error_check=True)

            # Remove IP from donor interface (optional)
            st.log(f"Removing IP from {cls.data.donor_interface}")
            cmd = f"configure terminal; interface {cls.data.donor_interface}; no ip address {cls.data.donor_ip}; exit; exit"
            st.config(cls.data.dut, cmd, type=cls.data.cli_type, skip_error_check=True)

            # Save configuration
            st.config(cls.data.dut, "write memory", type=cls.data.cli_type, skip_error_check=True)

        except Exception as e:
            st.log(f"Exception during cleanup: {e}")

    def _configure_donor_interface(self) -> None:
        """
        Configure donor interface (Loopback0) with IP address.
        """
        st.log(f"Configuring donor interface {self.data.donor_interface} with IP {self.data.donor_ip}")

        # Configure Loopback0 with IP address
        cmd_list = [
            "configure terminal",
            f"interface {self.data.donor_interface}",
            f"ip address {self.data.donor_ip}",
            "no shutdown",
            "exit",
            "exit"
        ]

        for cmd in cmd_list:
            result = st.config(self.data.dut, cmd, type=self.data.cli_type)
            if not result:
                st.report_fail("msg", f"Failed to execute command: {cmd}")

        # Wait for configuration to apply
        st.wait(3, "Waiting for donor interface configuration to apply")

        self.data.donor_ip_configured = True

        st.log(f"Donor interface {self.data.donor_interface} configured successfully")

    def _configure_unnumbered_interface(self) -> None:
        """
        Configure target interface (Ethernet0) as unnumbered, borrowing from donor.
        """
        st.log(
            f"Configuring {self.data.target_interface} as unnumbered, "
            f"borrowing from {self.data.donor_interface}"
        )

        # Configure Ethernet0 with ip unnumbered
        cmd_list = [
            "configure terminal",
            f"interface {self.data.target_interface}",
            "no shutdown",
            f"ip unnumbered {self.data.donor_interface}",
            "exit",
            "exit"
        ]

        for cmd in cmd_list:
            result = st.config(self.data.dut, cmd, type=self.data.cli_type)
            if not result:
                st.report_fail("msg", f"Failed to execute command: {cmd}")

        # Wait for configuration to apply
        st.wait(3, "Waiting for unnumbered configuration to apply")

        self.data.unnumbered_configured = True

        st.log(f"Unnumbered interface {self.data.target_interface} configured successfully")

    def _save_configuration(self) -> None:
        """
        Save running configuration to startup configuration.
        """
        st.log("Saving configuration to startup-config")

        result = st.config(self.data.dut, "write memory", type=self.data.cli_type)

        if not result:
            st.report_fail("msg", "Failed to save configuration")

        st.wait(2, "Waiting after configuration save")

        st.log("Configuration saved successfully")

    def _verify_running_config_unnumbered(self) -> bool:
        """
        Verify running-config contains unnumbered configuration.

        Returns:
            True if unnumbered config present, False otherwise
        """
        st.log(f"Verifying running-config for {self.data.target_interface}")

        # Get running-config for target interface
        output = st.show(
            self.data.dut,
            f"show running-config interface {self.data.target_interface}",
            type=self.data.cli_type,
        )

        st.log(f"Running-config output: {output}")

        # Convert to string
        output_str = str(output)

        # Check for "ip unnumbered Loopback0"
        unnumbered_present = f"ip unnumbered {self.data.donor_interface}" in output_str

        if unnumbered_present:
            st.log(f"✓ Running-config contains 'ip unnumbered {self.data.donor_interface}'")
            return True
        else:
            st.error(f"✗ Running-config missing 'ip unnumbered {self.data.donor_interface}'")
            return False

    def _verify_donor_interface_ip(self) -> bool:
        """
        Verify donor interface has expected IP address.

        Returns:
            True if donor has IP, False otherwise
        """
        st.log(f"Verifying {self.data.donor_interface} has IP {self.data.donor_ip_addr}")

        # Get IP interface information
        output = st.show(
            self.data.dut,
            f"show ip interface {self.data.donor_interface}",
            type=self.data.cli_type,
        )

        st.log(f"Donor interface output: {output}")

        # Convert to string
        output_str = str(output)

        # Check for donor IP address
        ip_present = self.data.donor_ip_addr in output_str

        if ip_present:
            st.log(f"✓ Donor interface has IP {self.data.donor_ip_addr}")
            return True
        else:
            st.error(f"✗ Donor interface missing IP {self.data.donor_ip_addr}")
            return False

    def _verify_unnumbered_has_borrowed_ip(self, should_have_ip: bool = True) -> bool:
        """
        Verify unnumbered interface has (or doesn't have) borrowed IP.

        Args:
            should_have_ip: True if interface should have IP, False if it shouldn't

        Returns:
            True if verification passes, False otherwise
        """
        st.log(
            f"Verifying {self.data.target_interface} "
            f"{'has' if should_have_ip else 'does not have'} borrowed IP"
        )

        # Get IP interface information
        output = st.show(
            self.data.dut,
            f"show ip interface {self.data.target_interface}",
            type=self.data.cli_type,
        )

        st.log(f"Target interface output: {output}")

        # Convert to string
        output_str = str(output)

        # Check for borrowed IP address
        ip_present = self.data.donor_ip_addr in output_str

        # Check for "Unnumbered" indication
        unnumbered_indicated = "Unnumbered" in output_str or "unnumbered" in output_str

        if should_have_ip:
            if ip_present and unnumbered_indicated:
                st.log(
                    f"✓ {self.data.target_interface} has borrowed IP {self.data.donor_ip_addr} "
                    f"from {self.data.donor_interface}"
                )
                return True
            else:
                st.error(
                    f"✗ {self.data.target_interface} missing borrowed IP or unnumbered indication"
                )
                return False
        else:
            if not ip_present:
                st.log(f"✓ {self.data.target_interface} correctly has no IP address")
                return True
            else:
                st.error(
                    f"✗ {self.data.target_interface} unexpectedly has IP address"
                )
                return False

    def _verify_interface_status(self, interface: str, expected_status: str = "up") -> bool:
        """
        Verify interface operational status.

        Args:
            interface: Interface name
            expected_status: Expected status (up/down)

        Returns:
            True if status matches, False otherwise
        """
        st.log(f"Verifying {interface} status is {expected_status}")

        # Get interface status
        output = st.show(
            self.data.dut,
            f"show interface status {interface}",
            type=self.data.cli_type,
        )

        st.log(f"Interface status output: {output}")

        # Convert to string
        output_str = str(output).lower()

        # Check for expected status
        status_match = expected_status.lower() in output_str

        if status_match:
            st.log(f"✓ Interface {interface} status is {expected_status}")
            return True
        else:
            st.error(f"✗ Interface {interface} status is not {expected_status}")
            return False

    def _remove_donor_ip(self) -> None:
        """
        Remove IP address from donor interface.
        """
        st.log(f"Removing IP address from {self.data.donor_interface}")

        # Remove IP address
        cmd_list = [
            "configure terminal",
            f"interface {self.data.donor_interface}",
            f"no ip address {self.data.donor_ip}",
            "exit",
            "exit"
        ]

        for cmd in cmd_list:
            result = st.config(self.data.dut, cmd, type=self.data.cli_type)
            if not result:
                st.report_fail("msg", f"Failed to execute command: {cmd}")

        st.wait(2, "Waiting after donor IP removal")

        st.log(f"Donor IP removed from {self.data.donor_interface}")

    def _restore_donor_ip(self) -> None:
        """
        Restore IP address to donor interface.
        """
        st.log(f"Restoring IP address to {self.data.donor_interface}")

        # Restore IP address
        cmd_list = [
            "configure terminal",
            f"interface {self.data.donor_interface}",
            f"ip address {self.data.donor_ip}",
            "exit",
            "exit"
        ]

        for cmd in cmd_list:
            result = st.config(self.data.dut, cmd, type=self.data.cli_type)
            if not result:
                st.report_fail("msg", f"Failed to execute command: {cmd}")

        st.wait(3, "Waiting after donor IP restoration")

        st.log(f"Donor IP restored to {self.data.donor_interface}")

    def _perform_reboot(self, reboot_type: str, wait_time: int) -> None:
        """
        Perform system reboot and wait for DUT to come back online.

        Args:
            reboot_type: Type of reboot (warm/fast/cold)
            wait_time: Maximum wait time in seconds
        """
        st.log(f"Performing {reboot_type} reboot")

        # Record pre-reboot uptime
        pre_reboot_output = st.show(
            self.data.dut,
            "show system uptime",
            type=self.data.cli_type,
        )
        st.log(f"Pre-reboot uptime: {pre_reboot_output}")

        # Initiate reboot based on type
        if reboot_type == "warm":
            st.log("Initiating warm reboot...")
            st.reboot(self.data.dut, "warm")
        elif reboot_type == "fast":
            st.log("Initiating fast reboot...")
            st.reboot(self.data.dut, "fast")
        elif reboot_type == "cold":
            st.log("Initiating cold reboot...")
            st.reboot(self.data.dut, "normal")
        else:
            st.report_fail("msg", f"Unknown reboot type: {reboot_type}")

        # Wait for reboot to complete
        st.log(f"Waiting up to {wait_time} seconds for system to reboot...")
        st.wait(30, "Initial wait for reboot to start")

        # Wait for DUT to be reachable
        if not st.wait_system_status(self.data.dut, max_time=wait_time):
            st.report_fail("msg", f"DUT did not come back online after {reboot_type} reboot")

        st.log(f"{reboot_type.capitalize()} reboot completed successfully")

        # Wait for stabilization
        st.wait(self.data.post_reboot_stabilize, "Waiting for system stabilization")

        # Verify uptime changed
        post_reboot_output = st.show(
            self.data.dut,
            "show system uptime",
            type=self.data.cli_type,
        )
        st.log(f"Post-reboot uptime: {post_reboot_output}")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_IPv4_Unnumbered_1.2.1.1"])
    def test_ipv4_unnumbered_configure_baseline(self) -> None:
        """
        TC_IPv4_Unnumbered_1.2.1.1: Configure IPv4 unnumbered baseline.

        Test Steps:
        1. Configure donor interface (Loopback0) with IP
        2. Configure target interface (Ethernet0) as unnumbered
        3. Verify running-config shows unnumbered configuration
        4. Verify target interface borrows IP from donor
        5. Save configuration
        """
        st.banner("TC_IPv4_Unnumbered_1.2.1.1: Configure IPv4 Unnumbered Baseline")

        # Step 1: Configure donor interface
        self._configure_donor_interface()

        # Step 2: Verify donor interface has IP
        if not self._verify_donor_interface_ip():
            st.report_fail("msg", f"Donor interface {self.data.donor_interface} not configured correctly")

        # Step 3: Configure unnumbered interface
        self._configure_unnumbered_interface()

        # Step 4: Verify running-config shows unnumbered configuration
        if not self._verify_running_config_unnumbered():
            st.report_fail("msg", "Unnumbered configuration not present in running-config")

        # Step 5: Verify target interface has borrowed IP
        if not self._verify_unnumbered_has_borrowed_ip(should_have_ip=True):
            st.report_fail("msg", "Target interface not borrowing IP from donor")

        # Step 6: Verify interfaces are up
        if not self._verify_interface_status(self.data.donor_interface, "up"):
            st.report_fail("msg", f"Donor interface {self.data.donor_interface} not up")

        if not self._verify_interface_status(self.data.target_interface, "up"):
            st.report_fail("msg", f"Target interface {self.data.target_interface} not up")

        # Step 7: Save configuration
        self._save_configuration()

        # Step 8: Verify configuration saved
        st.log("Verifying configuration saved to startup-config")

        startup_output = st.show(
            self.data.dut,
            f"show startup-config interface {self.data.target_interface}",
            type=self.data.cli_type,
        )
        st.log(f"Startup-config: {startup_output}")

        startup_str = str(startup_output)
        if f"ip unnumbered {self.data.donor_interface}" not in startup_str:
            st.report_fail("msg", "Configuration not saved to startup-config")

        st.log("✓ Test passed: IPv4 unnumbered baseline configured successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_IPv4_Unnumbered_1.2.1.2"])
    def test_ipv4_unnumbered_warm_reboot_persistence(self) -> None:
        """
        TC_IPv4_Unnumbered_1.2.1.2: Verify configuration persists across warm reboot.

        Test Steps:
        1. Ensure baseline configuration exists
        2. Perform warm reboot
        3. Verify running-config still contains unnumbered configuration
        4. Verify target interface still borrows IP from donor
        5. Verify system stability
        """
        st.banner("TC_IPv4_Unnumbered_1.2.1.2: Warm Reboot Persistence")

        # Step 1: Ensure baseline configuration exists
        if not self.data.unnumbered_configured:
            st.log("Baseline not configured, configuring now...")
            self._configure_donor_interface()
            self._configure_unnumbered_interface()
            self._save_configuration()

        # Step 2: Verify pre-reboot state
        st.log("Verifying pre-reboot configuration")

        if not self._verify_running_config_unnumbered():
            st.report_fail("msg", "Pre-reboot: Unnumbered configuration missing")

        if not self._verify_unnumbered_has_borrowed_ip(should_have_ip=True):
            st.report_fail("msg", "Pre-reboot: Target not borrowing IP")

        # Step 3: Perform warm reboot
        self._perform_reboot("warm", self.data.warm_reboot_wait)

        # Step 4: Verify post-reboot configuration persistence
        st.log("Verifying post-reboot configuration persistence")

        if not self._verify_running_config_unnumbered():
            st.report_fail("msg", "Post-reboot: Unnumbered configuration NOT persisted")

        # Step 5: Verify donor interface still has IP
        if not self._verify_donor_interface_ip():
            st.report_fail("msg", "Post-reboot: Donor interface lost IP")

        # Step 6: Verify target interface still borrows IP
        if not self._verify_unnumbered_has_borrowed_ip(should_have_ip=True):
            st.report_fail("msg", "Post-reboot: Target not borrowing IP")

        # Step 7: Verify interfaces operational
        if not self._verify_interface_status(self.data.donor_interface, "up"):
            st.report_fail("msg", "Post-reboot: Donor interface not up")

        if not self._verify_interface_status(self.data.target_interface, "up"):
            st.report_fail("msg", "Post-reboot: Target interface not up")

        # Step 8: Verify system health
        st.log("Verifying system health after warm reboot")

        version_output = st.show(self.data.dut, "show version", type=self.data.cli_type)
        st.log(f"System version: {version_output}")

        st.log("✓ Test passed: Configuration persisted across warm reboot")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_IPv4_Unnumbered_1.2.1.3"])
    def test_ipv4_unnumbered_fast_reboot_persistence(self) -> None:
        """
        TC_IPv4_Unnumbered_1.2.1.3: Verify configuration persists across fast reboot.

        Test Steps:
        1. Ensure baseline configuration exists
        2. Perform fast reboot
        3. Verify running-config still contains unnumbered configuration
        4. Verify target interface still borrows IP from donor
        5. Verify system stability
        """
        st.banner("TC_IPv4_Unnumbered_1.2.1.3: Fast Reboot Persistence")

        # Step 1: Ensure baseline configuration exists
        if not self.data.unnumbered_configured:
            st.log("Baseline not configured, configuring now...")
            self._configure_donor_interface()
            self._configure_unnumbered_interface()
            self._save_configuration()

        # Step 2: Verify pre-reboot state
        st.log("Verifying pre-reboot configuration")

        if not self._verify_running_config_unnumbered():
            st.report_fail("msg", "Pre-reboot: Unnumbered configuration missing")

        if not self._verify_unnumbered_has_borrowed_ip(should_have_ip=True):
            st.report_fail("msg", "Pre-reboot: Target not borrowing IP")

        # Step 3: Perform fast reboot
        self._perform_reboot("fast", self.data.fast_reboot_wait)

        # Step 4: Verify post-reboot configuration persistence
        st.log("Verifying post-reboot configuration persistence")

        if not self._verify_running_config_unnumbered():
            st.report_fail("msg", "Post-reboot: Unnumbered configuration NOT persisted")

        # Step 5: Verify donor interface still has IP
        if not self._verify_donor_interface_ip():
            st.report_fail("msg", "Post-reboot: Donor interface lost IP")

        # Step 6: Verify target interface still borrows IP
        if not self._verify_unnumbered_has_borrowed_ip(should_have_ip=True):
            st.report_fail("msg", "Post-reboot: Target not borrowing IP")

        # Step 7: Verify interfaces operational
        if not self._verify_interface_status(self.data.donor_interface, "up"):
            st.report_fail("msg", "Post-reboot: Donor interface not up")

        if not self._verify_interface_status(self.data.target_interface, "up"):
            st.report_fail("msg", "Post-reboot: Target interface not up")

        st.log("✓ Test passed: Configuration persisted across fast reboot")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_IPv4_Unnumbered_1.2.1.4"])
    def test_ipv4_unnumbered_cold_reboot_persistence(self) -> None:
        """
        TC_IPv4_Unnumbered_1.2.1.4: Verify configuration persists across cold reboot.

        Test Steps:
        1. Ensure baseline configuration exists
        2. Perform cold reboot (full power cycle)
        3. Verify running-config still contains unnumbered configuration
        4. Verify target interface still borrows IP from donor
        5. Verify system stability
        """
        st.banner("TC_IPv4_Unnumbered_1.2.1.4: Cold Reboot Persistence")

        # Step 1: Ensure baseline configuration exists
        if not self.data.unnumbered_configured:
            st.log("Baseline not configured, configuring now...")
            self._configure_donor_interface()
            self._configure_unnumbered_interface()
            self._save_configuration()

        # Step 2: Verify pre-reboot state
        st.log("Verifying pre-reboot configuration")

        if not self._verify_running_config_unnumbered():
            st.report_fail("msg", "Pre-reboot: Unnumbered configuration missing")

        if not self._verify_unnumbered_has_borrowed_ip(should_have_ip=True):
            st.report_fail("msg", "Pre-reboot: Target not borrowing IP")

        # Step 3: Perform cold reboot
        self._perform_reboot("cold", self.data.cold_reboot_wait)

        # Step 4: Verify post-reboot configuration persistence
        st.log("Verifying post-reboot configuration persistence")

        if not self._verify_running_config_unnumbered():
            st.report_fail("msg", "Post-reboot: Unnumbered configuration NOT persisted")

        # Step 5: Verify donor interface still has IP
        if not self._verify_donor_interface_ip():
            st.report_fail("msg", "Post-reboot: Donor interface lost IP")

        # Step 6: Verify target interface still borrows IP
        if not self._verify_unnumbered_has_borrowed_ip(should_have_ip=True):
            st.report_fail("msg", "Post-reboot: Target not borrowing IP")

        # Step 7: Verify interfaces operational
        if not self._verify_interface_status(self.data.donor_interface, "up"):
            st.report_fail("msg", "Post-reboot: Donor interface not up")

        if not self._verify_interface_status(self.data.target_interface, "up"):
            st.report_fail("msg", "Post-reboot: Target interface not up")

        # Step 8: Verify system health after cold reboot
        st.log("Verifying system health after cold reboot")

        platform_output = st.show(
            self.data.dut,
            "show platform summary",
            type=self.data.cli_type,
        )
        st.log(f"Platform summary: {platform_output}")

        st.log("✓ Test passed: Configuration persisted across cold reboot")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_IPv4_Unnumbered_1.2.1.5"])
    def test_ipv4_unnumbered_remove_donor_ip_failure(self) -> None:
        """
        TC_IPv4_Unnumbered_1.2.1.5: Verify dependent failure when donor IP removed.

        Test Steps:
        1. Ensure baseline configuration exists
        2. Verify target has borrowed IP (baseline)
        3. Remove IP from donor interface
        4. Verify target has NO IP (dependent failure)
        5. Verify unnumbered config still present in running-config
        6. Verify system stability (no crash)
        """
        st.banner("TC_IPv4_Unnumbered_1.2.1.5: Remove Donor IP - Dependent Failure")

        # Step 1: Ensure baseline configuration exists
        if not self.data.unnumbered_configured:
            st.log("Baseline not configured, configuring now...")
            self._configure_donor_interface()
            self._configure_unnumbered_interface()
            self._save_configuration()

        # Step 2: Verify baseline - target has borrowed IP
        st.log("Verifying baseline: Target has borrowed IP")

        if not self._verify_unnumbered_has_borrowed_ip(should_have_ip=True):
            st.report_fail("msg", "Baseline: Target not borrowing IP")

        # Step 3: Remove IP from donor interface
        self._remove_donor_ip()

        # Step 4: Verify donor interface has NO IP
        st.log("Verifying donor interface has no IP after removal")

        donor_output = st.show(
            self.data.dut,
            f"show ip interface {self.data.donor_interface}",
            type=self.data.cli_type,
        )

        st.log(f"Donor interface after IP removal: {donor_output}")

        donor_str = str(donor_output)

        # Check donor has no IP
        if self.data.donor_ip_addr in donor_str:
            st.report_fail("msg", "Donor IP not removed successfully")

        # Step 5: Verify target has NO IP (dependent failure)
        st.log("Verifying target has no IP (dependent failure expected)")

        if not self._verify_unnumbered_has_borrowed_ip(should_have_ip=False):
            st.report_fail("msg", "Target still has IP after donor IP removed (should fail)")

        # Step 6: Verify unnumbered config still present in running-config
        if not self._verify_running_config_unnumbered():
            st.report_fail("msg", "Unnumbered config removed from running-config (should persist)")

        # Step 7: Verify system stability (no crash)
        st.log("Verifying system stability after donor IP removal")

        uptime_output = st.show(
            self.data.dut,
            "show system uptime",
            type=self.data.cli_type,
        )
        st.log(f"System uptime: {uptime_output}")

        st.log("✓ Test passed: Dependent failure correctly observed when donor IP removed")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_IPv4_Unnumbered_1.2.1.6"])
    def test_ipv4_unnumbered_restore_donor_ip_recovery(self) -> None:
        """
        TC_IPv4_Unnumbered_1.2.1.6: Verify automatic recovery when donor IP restored.

        Test Steps:
        1. Ensure donor IP is removed (from previous test or setup)
        2. Verify target has NO IP (dependent failure state)
        3. Restore IP to donor interface
        4. Verify target AUTOMATICALLY recovers borrowed IP
        5. Verify no manual intervention required
        6. Verify system stability
        """
        st.banner("TC_IPv4_Unnumbered_1.2.1.6: Restore Donor IP - Automatic Recovery")

        # Step 1: Ensure unnumbered is configured
        if not self.data.unnumbered_configured:
            st.log("Baseline not configured, configuring now...")
            self._configure_donor_interface()
            self._configure_unnumbered_interface()
            self._save_configuration()

        # Step 2: Ensure donor IP is removed
        st.log("Removing donor IP to set up recovery test")
        self._remove_donor_ip()

        # Step 3: Verify target has no IP (dependent failure state)
        st.log("Verifying target has no IP before recovery")

        if not self._verify_unnumbered_has_borrowed_ip(should_have_ip=False):
            st.log("Warning: Target still has IP, but proceeding with recovery test")

        # Step 4: Restore IP to donor interface
        self._restore_donor_ip()

        # Step 5: Verify donor interface has IP restored
        if not self._verify_donor_interface_ip():
            st.report_fail("msg", "Donor IP not restored successfully")

        # Step 6: Verify target AUTOMATICALLY recovers borrowed IP
        st.log("Verifying target automatically recovered borrowed IP")

        if not self._verify_unnumbered_has_borrowed_ip(should_have_ip=True):
            st.report_fail(
                "msg",
                "Target did NOT automatically recover IP after donor restoration"
            )

        # Step 7: Verify unnumbered config still present
        if not self._verify_running_config_unnumbered():
            st.report_fail("msg", "Unnumbered config missing from running-config")

        # Step 8: Verify interfaces operational
        if not self._verify_interface_status(self.data.donor_interface, "up"):
            st.report_fail("msg", "Donor interface not up after recovery")

        if not self._verify_interface_status(self.data.target_interface, "up"):
            st.report_fail("msg", "Target interface not up after recovery")

        # Step 9: Save configuration with restored state
        self._save_configuration()

        st.log("✓ Test passed: Automatic recovery successful when donor IP restored")
        st.report_pass("test_case_passed")
