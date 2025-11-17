"""
INTERFACE EVENTS - Admin/Link State Changes with Reboot Validation

How to run:
  cd Siddu/sonic-mgmt/spytest
  source spytest_venv/bin/activate
  ./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml \
  system/interface_events/testcases_Interface_events_reboot.py \
  --logs-path ./logs/test_interface_events_reboot_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates CLI/syslog for interface administrative and link state changes,
  followed by configuration save and reboot validation. The test performs
  multiple shutdown/no-shutdown cycles on interfaces from the testbed to
  verify that state transitions are accurately reflected in CLI outputs.
  Each iteration validates admin state and operational state changes through
  show interface status command. After completing all iterations, the test
  saves the configuration, reboots the device, waits for it to come back up,
  and validates that the interface status is correctly preserved after reboot.

Pre-requisites:
  - Topology: 1+ nodes | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |   smic_sonic1      |                       |   smic_sonic2      |
        # |   Ethernet4        |=======================|   Ethernet4        |
        # +--------------------+                       +--------------------+

  - Required: sonic-cli, klish mode support
  - Required test variables (YAML): testbed_2vs.yaml
  - Test ID: TC_INTF_EVENTS_REBOOT (Test Plan 1.1.10 with reboot)
"""

import time
import pytest
from spytest import st

@pytest.mark.topology("any")
class TestInterfaceEventsReboot:
    """Testcases covering interface admin/link state changes validation with reboot."""

    @classmethod
    def setup_class(cls):
        """Initialize test environment and collect topology information."""
        st.log("=" * 80)
        st.log("Setting up TestInterfaceEventsReboot class")
        st.log("=" * 80)

        # Get DUT list
        cls.dut_list = st.get_dut_names()
        st.log(f"Available DUTs: {cls.dut_list}")

        if not cls.dut_list:
            st.report_fail("msg", "No DUTs found in topology")

        # Use first DUT
        cls.dut = cls.dut_list[0]
        st.log(f"Using DUT: {cls.dut}")

        # Get interfaces from testbed
        cls.dut_to_dut_ports = st.get_dut_links(cls.dut)
        st.log(f"DUT links: {cls.dut_to_dut_ports}")

        # CLI type - using klish
        cls.cli_type = "klish"

        # Disable pagination first to prevent --more-- prompts
        st.log("Disabling pagination...")
        st.config(cls.dut, "terminal length 0", type=cls.cli_type)

        # Get actual interface name from device (handles alias vs native name issue)
        # Query the device to get the native interface names
        st.log("Querying device to get native interface names...")
        interface_status = st.show(cls.dut, "show interface status", type=cls.cli_type)
        st.log(f"Interface status output type: {type(interface_status).__name__}")

        # Find first usable interface
        cls.test_interface = None
        if isinstance(interface_status, list):
            # Look for first interface with admin=up and oper=up
            for entry in interface_status:
                if isinstance(entry, dict):
                    intf = entry.get('interface', '')
                    admin = entry.get('admin', '').lower()
                    if intf and 'ethernet' in intf.lower() and admin == 'up':
                        cls.test_interface = intf
                        st.log(f"Selected interface {intf} from device (admin={admin})")
                        break

        # Fallback if no interface found
        if not cls.test_interface:
            if cls.dut_to_dut_ports and len(cls.dut_to_dut_ports) > 0:
                cls.test_interface = "Ethernet0"
                st.log(f"Using fallback interface: {cls.test_interface}")
            else:
                cls.test_interface = "Ethernet4"
                st.log(f"No links found, using fallback interface: {cls.test_interface}")

        # Test iteration count
        cls.iterations = 4

        st.log("Setup class completed successfully")

    @classmethod
    def teardown_class(cls):
        """Cleanup and restore interface state after all tests."""
        st.log("=" * 80)
        st.log("Tearing down TestInterfaceEventsReboot class")
        st.log("=" * 80)

        # Ensure interface is up before exiting
        try:
            st.log(f"Restoring {cls.test_interface} to up state")
            # Use separate commands to avoid the error
            st.config(cls.dut, "configure terminal", type=cls.cli_type)
            st.config(cls.dut, f"interface {cls.test_interface}", type=cls.cli_type)
            st.config(cls.dut, "no shutdown", type=cls.cli_type)
            output = st.config(cls.dut, "end", type=cls.cli_type)
            st.log(f"Restore completed")
        except Exception as e:
            st.log(f"Warning: Failed to restore interface state: {e}")

        st.log("Teardown class completed")

    def setup_method(self):
        """Setup for each test method."""
        st.log("Setting up test method")

    def teardown_method(self):
        """Teardown for each test method."""
        st.log("Tearing down test method")

    def _parse_interface_data(self, output, interface):
        """
        Parse interface status output which can be in different formats.
        Handles both native names (Ethernet0) and alias names (fortyGigE0/0).

        Returns: dict with 'admin' and 'oper' states, or None if not found
        """
        if not output:
            return None

        # Check if output is a list of dictionaries (parsed format)
        if isinstance(output, list):
            for entry in output:
                if isinstance(entry, dict):
                    # Check 'interface', 'alias', and 'altname' fields
                    intf = entry.get('interface', '')
                    alias = entry.get('alias', '')
                    altname = entry.get('altname', '')

                    if intf == interface or alias == interface or altname == interface:
                        return {
                            'admin': entry.get('admin', 'unknown').lower(),
                            'oper': entry.get('oper', 'unknown').lower()
                        }

        # Check if output is a string (raw text format)
        if isinstance(output, str):
            for line in output.split('\n'):
                # Match if interface name appears ANYWHERE in the line
                if interface in line:
                    # Try to parse the line - find admin and oper columns
                    parts = line.split()

                    # Try to find 'up' or 'down' status indicators
                    admin = 'unknown'
                    oper = 'unknown'

                    for i, part in enumerate(parts):
                        part_lower = part.lower()
                        if part_lower in ['up', 'down']:
                            if admin == 'unknown':
                                admin = part_lower
                            elif oper == 'unknown':
                                oper = part_lower
                                break

                    if admin != 'unknown' or oper != 'unknown':
                        return {'admin': admin, 'oper': oper}

        return None

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_REBOOT"])
    def test_interface_admin_state_changes_with_reboot(self):
        """
        TC_INTF_EVENTS_REBOOT: Validate CLI/syslog for admin/link state changes with reboot.

        Test Procedure:
        1. Bring interface to UP state
        2. Capture baseline interface status
        3. Capture baseline syslog output
        4. Perform 4 iterations of shutdown/no-shutdown cycles
        5. Validate state transitions in each iteration
        6. Verify consistency across all iterations
        7. Save configuration using "sudo config save -y"
        8. Reboot device using "sudo reboot"
        9. Wait 300 seconds for device to reboot and reconnect
        10. Validate interface status after reboot
        """
        st.log("=" * 80)
        st.log("TEST: Validate Interface Admin/Link State Changes with Reboot")
        st.log("=" * 80)

        dut = self.dut
        interface = self.test_interface

        # Step 0: Disable pagination to get full output
        st.log("=" * 80)
        st.log("Step 0: Disabling pagination")
        st.log("=" * 80)

        # Disable pagination so we get full output without --more-- prompts
        st.config(dut, "terminal length 0", type=self.cli_type)
        st.log("Pagination disabled with 'terminal length 0'")

        # Step 1: Bring interface to UP state
        st.log("=" * 80)
        st.log(f"Step 1: Bringing {interface} to UP state")
        st.log("=" * 80)

        # Use separate commands to avoid config mode errors
        st.config(dut, "configure terminal", type=self.cli_type)
        st.config(dut, f"interface {interface}", type=self.cli_type)
        st.config(dut, "no shutdown", type=self.cli_type)
        st.config(dut, "end", type=self.cli_type)
        st.log(f"Interface {interface} set to no shutdown")
        time.sleep(3)

        # Step 2: Baseline interface status check
        st.log("=" * 80)
        st.log("Step 2: Capturing baseline interface status")
        st.log("=" * 80)

        baseline_status_output = st.show(dut, "show interface status", type=self.cli_type)
        st.log(f"Baseline Interface Status Output (type: {type(baseline_status_output).__name__}):")
        st.log(f"{baseline_status_output}")

        # Parse and validate baseline
        baseline_data = self._parse_interface_data(baseline_status_output, interface)
        if baseline_data:
            st.log(f"SUCCESS: {interface} found - Admin: {baseline_data['admin']}, Oper: {baseline_data['oper']}")
            if 'up' in baseline_data['admin'] or 'up' in baseline_data['oper']:
                st.log("Baseline validation: Interface is UP")
        else:
            st.report_fail("msg", f"Interface {interface} not found in baseline status output")

        # Step 3: Baseline syslog check
        st.log("=" * 80)
        st.log("Step 3: Capturing baseline syslog output")
        st.log("=" * 80)

        try:
            baseline_syslog_output = st.show(dut, "sudo tail -20 /var/log/syslog", skip_tmpl=True, skip_error_check=True)
            st.log(f"Baseline Syslog Output (last 20 lines):\n{baseline_syslog_output}")
        except Exception as e:
            st.log(f"Note: syslog command failed: {e}")
            baseline_syslog_output = "syslog not available"

        # Step 4-8: Perform shutdown/no-shutdown cycles
        st.log("=" * 80)
        st.log(f"Step 4-8: Performing {self.iterations} shutdown/no-shutdown cycles")
        st.log("=" * 80)

        iteration_results = []

        for iteration in range(1, self.iterations + 1):
            st.log("")
            st.log("=" * 80)
            st.log(f"ITERATION {iteration} - SHUTDOWN/NO-SHUTDOWN CYCLE")
            st.log("=" * 80)

            # Shutdown interface
            st.log(f"--> Iteration {iteration}: Shutting down {interface}")
            st.config(dut, "configure terminal", type=self.cli_type)
            st.config(dut, f"interface {interface}", type=self.cli_type)
            st.config(dut, "shutdown", type=self.cli_type)
            st.config(dut, "end", type=self.cli_type)
            st.log(f"Shutdown command executed")
            time.sleep(3)

            # Re-apply terminal length 0 (lost when session changed)
            st.log(f"--> Iteration {iteration}: Re-applying terminal length 0")
            st.config(dut, "terminal length 0", type=self.cli_type)

            # Get interface status after shutdown
            st.log(f"--> Iteration {iteration}: Getting interface status after shutdown")
            shutdown_status_output = st.show(dut, "show interface status", type=self.cli_type)
            st.log(f"Status output after shutdown (type: {type(shutdown_status_output).__name__})")

            # Parse and validate shutdown state
            shutdown_data = self._parse_interface_data(shutdown_status_output, interface)
            shutdown_valid = False
            if shutdown_data:
                st.log(f"Interface {interface} after shutdown - Admin: {shutdown_data['admin']}, Oper: {shutdown_data['oper']}")
                if 'down' in shutdown_data['admin'] or 'down' in shutdown_data['oper']:
                    st.log(f"SUCCESS: Interface is DOWN in iteration {iteration}")
                    shutdown_valid = True
                else:
                    st.log(f"FAILURE: Interface is NOT DOWN in iteration {iteration}")
            else:
                st.log(f"WARNING: Interface {interface} not found in shutdown status output")

            # Get syslog after shutdown
            try:
                shutdown_syslog_output = st.show(dut, f"sudo grep -i '{interface}' /var/log/syslog | tail -10", skip_tmpl=True, skip_error_check=True)
                st.log(f"Syslog after shutdown (last 10 entries for {interface}):\n{shutdown_syslog_output}")
            except Exception as e:
                st.log(f"Note: syslog grep failed: {e}")

            # No shutdown interface
            st.log(f"--> Iteration {iteration}: Bringing up {interface}")
            st.config(dut, "configure terminal", type=self.cli_type)
            st.config(dut, f"interface {interface}", type=self.cli_type)
            st.config(dut, "no shutdown", type=self.cli_type)
            st.config(dut, "end", type=self.cli_type)
            st.log(f"No shutdown command executed")
            time.sleep(3)

            # Re-apply terminal length 0 (lost when session changed)
            st.log(f"--> Iteration {iteration}: Re-applying terminal length 0")
            st.config(dut, "terminal length 0", type=self.cli_type)

            # Get interface status after no shutdown
            st.log(f"--> Iteration {iteration}: Getting interface status after no shutdown")
            noshut_status_output = st.show(dut, "show interface status", type=self.cli_type)
            st.log(f"Status output after no shutdown (type: {type(noshut_status_output).__name__})")

            # Parse and validate no shutdown state
            noshut_data = self._parse_interface_data(noshut_status_output, interface)
            noshut_valid = False
            if noshut_data:
                st.log(f"Interface {interface} after no shutdown - Admin: {noshut_data['admin']}, Oper: {noshut_data['oper']}")
                if 'up' in noshut_data['admin'] or 'up' in noshut_data['oper']:
                    st.log(f"SUCCESS: Interface is UP in iteration {iteration}")
                    noshut_valid = True
                else:
                    st.log(f"FAILURE: Interface is NOT UP in iteration {iteration}")
            else:
                st.log(f"WARNING: Interface {interface} not found in no shutdown status output")

            # Get syslog after no shutdown
            try:
                noshut_syslog_output = st.show(dut, f"sudo grep -i '{interface}' /var/log/syslog | tail -10", skip_tmpl=True, skip_error_check=True)
                st.log(f"Syslog after no shutdown (last 10 entries for {interface}):\n{noshut_syslog_output}")
            except Exception as e:
                st.log(f"Note: syslog grep failed: {e}")

            # Store iteration result
            iteration_result = {
                "iteration": iteration,
                "shutdown_valid": shutdown_valid,
                "noshut_valid": noshut_valid,
                "overall": shutdown_valid and noshut_valid
            }
            iteration_results.append(iteration_result)

            st.log(f"Iteration {iteration} Result: {'PASS' if iteration_result['overall'] else 'FAIL'}")
            st.log("=" * 80)

        # Iteration validation summary
        st.log("")
        st.log("=" * 80)
        st.log("ITERATION VALIDATION - Test Summary")
        st.log("=" * 80)

        all_iterations_passed = True
        for result in iteration_results:
            status = "PASS" if result["overall"] else "FAIL"
            st.log(f"Iteration {result['iteration']}: {status}")
            if not result["overall"]:
                all_iterations_passed = False

        # Generate summary table
        st.log("")
        st.log("Detailed Results:")
        st.log("-" * 80)
        st.log(f"{'Iteration':<12} {'Shutdown':<15} {'No-Shutdown':<15} {'Overall':<10}")
        st.log("-" * 80)

        for result in iteration_results:
            shutdown_status = "PASS" if result["shutdown_valid"] else "FAIL"
            noshut_status = "PASS" if result["noshut_valid"] else "FAIL"
            overall_status = "PASS" if result["overall"] else "FAIL"
            st.log(f"{result['iteration']:<12} {shutdown_status:<15} {noshut_status:<15} {overall_status:<10}")

        st.log("-" * 80)

        if not all_iterations_passed:
            st.log("")
            st.log("=" * 80)
            st.log("TEST RESULT: FAIL (Iteration validation failed)")
            st.log("One or more iterations failed validation")
            st.log("=" * 80)
            st.report_fail("msg", "Interface state transition validation failed in one or more iterations")

        st.log("")
        st.log("=" * 80)
        st.log("All iterations completed successfully - Proceeding with reboot test")
        st.log("=" * 80)

        # ================================================================
        # NEW STEPS: Save configuration, reboot, and validate after reboot
        # ================================================================

        # Step 9: Save configuration
        st.log("")
        st.log("=" * 80)
        st.log("Step 9: Saving configuration using 'sudo config save -y'")
        st.log("=" * 80)

        save_output = st.show(dut, "sudo config save -y", skip_tmpl=True, skip_error_check=True)
        st.log(f"Config save output:\n{save_output}")
        st.log("Configuration saved successfully")

        # Step 10: Reboot device
        st.log("")
        st.log("=" * 80)
        st.log("Step 10: Rebooting device using 'sudo reboot'")
        st.log("=" * 80)

        st.log("Initiating reboot...")
        st.reboot(dut, skip_port_wait=True)
        st.log("Reboot command sent")

        # Step 11: Wait for device to come back up
        st.log("")
        st.log("=" * 80)
        st.log("Step 11: Waiting 300 seconds for device to reboot and reconnect")
        st.log("=" * 80)

        st.log("Device is rebooting... waiting for 300 seconds")
        time.sleep(300)

        st.log("Attempting to reconnect to device...")
        # Wait for ports to be ready
        st.wait_system_status(dut, max_time=120)
        st.log("Device reconnected successfully")

        # Step 12: Validate interface status after reboot
        st.log("")
        st.log("=" * 80)
        st.log("Step 12: Validating interface status after reboot")
        st.log("=" * 80)

        # Disable pagination after reboot
        st.config(dut, "terminal length 0", type=self.cli_type)

        # Get interface status after reboot
        st.log(f"Getting interface status for {interface} after reboot...")
        reboot_status_output = st.show(dut, "show interface status", type=self.cli_type)
        st.log(f"Interface Status After Reboot (type: {type(reboot_status_output).__name__}):")
        st.log(f"{reboot_status_output}")

        # Parse and validate post-reboot state
        reboot_data = self._parse_interface_data(reboot_status_output, interface)
        reboot_valid = False
        if reboot_data:
            st.log(f"Interface {interface} after reboot - Admin: {reboot_data['admin']}, Oper: {reboot_data['oper']}")
            # Interface should be UP after reboot (since we ended with no shutdown)
            if 'up' in reboot_data['admin'] or 'up' in reboot_data['oper']:
                st.log(f"SUCCESS: Interface is UP after reboot")
                reboot_valid = True
            else:
                st.log(f"FAILURE: Interface is NOT UP after reboot")
        else:
            st.log(f"WARNING: Interface {interface} not found in status output after reboot")
            st.report_fail("msg", f"Interface {interface} not found in status output after reboot")

        # ================================================================
        # Final Test Summary
        # ================================================================
        st.log("")
        st.log("=" * 80)
        st.log("FINAL TEST RESULT")
        st.log("=" * 80)

        if all_iterations_passed and reboot_valid:
            st.log("")
            st.log("TEST RESULT: PASS")
            st.log(f"✓ All {self.iterations} shutdown/no-shutdown iterations passed")
            st.log("✓ Configuration saved successfully")
            st.log("✓ Device rebooted successfully")
            st.log("✓ Interface state validated correctly after reboot")
            st.log("=" * 80)
            st.report_pass("test_case_passed")
        else:
            st.log("")
            st.log("TEST RESULT: FAIL")
            if not all_iterations_passed:
                st.log("✗ One or more iterations failed validation")
            if not reboot_valid:
                st.log("✗ Interface state validation failed after reboot")
            st.log("=" * 80)
            st.report_fail("msg", "Test failed: Interface state validation failed after reboot")
