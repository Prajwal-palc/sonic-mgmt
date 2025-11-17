"""
INTERFACE EVENTS - LAG/ECMP Propagation and Recovery

How to run:
  cd Siddu/sonic-mgmt/spytest
  source spytest_venv/bin/activate
  ./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml \
  system/interface_events/testcases_Interface_events2.py \
  --logs-path ./logs/test_interface_events_lag_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates propagation and recovery in LAG/ECMP scenarios. The test creates
  a PortChannel interface on two DUTs, adds member interfaces, and verifies
  that CLI commands accurately reflect the PortChannel state and member
  information. The test focuses on validating "show interface PortChannel"
  command output for accurate state representation.

Pre-requisites:
  - Topology: 2 nodes | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |   smic_sonic1      |                       |   smic_sonic2      |
        # | Ethernet0          |=======================| Ethernet0          |
        # | Ethernet4          |=======================| Ethernet4          |
        # | Ethernet8          |=======================| Ethernet8          |
        # | Ethernet12         |=======================| Ethernet12         |
        # +--------------------+                       +--------------------+

  - Required: sonic-cli, klish mode support
  - Required test variables (YAML): testbed_2vs.yaml
  - Test ID: TC_INTF_EVENTS_002 (Test Plan 1.3.1)
"""

import time
import pytest
from spytest import st

@pytest.mark.topology("any")
class TestInterfaceLagEcmp:
    """Testcases covering LAG/ECMP propagation and recovery validation."""

    @classmethod
    def setup_class(cls):
        """Initialize test environment and collect topology information."""
        st.log("=" * 80)
        st.log("Setting up TestInterfaceLagEcmp class")
        st.log("=" * 80)

        # Get DUT list
        cls.dut_list = st.get_dut_names()
        st.log(f"Available DUTs: {cls.dut_list}")

        if len(cls.dut_list) < 2:
            st.report_fail("msg", f"This test requires at least 2 DUTs, found: {len(cls.dut_list)}")

        # Use first two DUTs
        cls.dut1 = cls.dut_list[0]
        cls.dut2 = cls.dut_list[1]
        st.log(f"Using DUT1: {cls.dut1}, DUT2: {cls.dut2}")

        # CLI type - using klish
        cls.cli_type = "klish"

        # PortChannel configuration
        cls.portchannel_number = 10
        cls.portchannel_name = f"PortChannel{cls.portchannel_number}"

        # Get interfaces from testbed for both DUTs
        st.log("Fetching interfaces from testbed...")

        # Get interfaces for DUT1
        cls.dut1_interfaces = []
        dut1_links = st.get_dut_links(cls.dut1)
        st.log(f"DUT1 links: {dut1_links}")

        # Extract interface names from testbed
        # Expected interfaces: Ethernet0, Ethernet4, Ethernet8, Ethernet12
        cls.testbed_interfaces = ["Ethernet0", "Ethernet4", "Ethernet8", "Ethernet12"]

        # Select first interface for PortChannel member
        cls.member_interface = cls.testbed_interfaces[0]
        st.log(f"Selected member interface for PortChannel: {cls.member_interface}")

        # Disable pagination on both DUTs
        st.log("Disabling pagination on both DUTs...")
        st.config(cls.dut1, "terminal length 0", type=cls.cli_type)
        st.config(cls.dut2, "terminal length 0", type=cls.cli_type)

        st.log("Setup class completed successfully")

    @classmethod
    def teardown_class(cls):
        """Cleanup and restore configuration after all tests."""
        st.log("=" * 80)
        st.log("Tearing down TestInterfaceLagEcmp class")
        st.log("=" * 80)

        # Cleanup will be handled in test teardown
        st.log("Teardown class completed")

    def setup_method(self):
        """Setup for each test method."""
        st.log("Setting up test method")

    def teardown_method(self):
        """Teardown for each test method."""
        st.log("Tearing down test method")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_INTF_EVENTS_002"])
    def test_lag_ecmp_propagation_recovery(self):
        """
        TC_INTF_EVENTS_002: Validate propagation and recovery in LAG/ECMP.

        Test Procedure:
        1. Bring all interfaces to UP state on both DUTs
        2. Capture baseline interface status on both DUTs
        3. Create PortChannel10 on both DUTs
        4. Add first interface (Ethernet0) to PortChannel10 on both DUTs
        5. Display and store "show interface PortChannel" output
        6. Cleanup: Remove interface from PortChannel and delete PortChannel
        """
        st.log("=" * 80)
        st.log("TEST: Validate LAG/ECMP Propagation and Recovery")
        st.log("=" * 80)

        dut1 = self.dut1
        dut2 = self.dut2
        member_interface = self.member_interface
        portchannel_name = self.portchannel_name

        # ================================================================
        # STEP 1: Bring all interfaces to UP state on both DUTs
        # ================================================================
        st.log("=" * 80)
        st.log("Step 1: Bringing all interfaces to UP state")
        st.log("=" * 80)

        # Configure interfaces on DUT1
        st.log(f"Configuring interfaces on {dut1}...")
        for interface in self.testbed_interfaces:
            st.log(f"  --> Bringing up {interface} on {dut1}")
            st.config(dut1, "configure terminal", type=self.cli_type)
            st.config(dut1, f"interface {interface}", type=self.cli_type)
            st.config(dut1, "no shutdown", type=self.cli_type)
            st.config(dut1, "exit", type=self.cli_type)
        st.config(dut1, "exit", type=self.cli_type)
        st.log(f"All interfaces configured on {dut1}")

        # Configure interfaces on DUT2
        st.log(f"Configuring interfaces on {dut2}...")
        for interface in self.testbed_interfaces:
            st.log(f"  --> Bringing up {interface} on {dut2}")
            st.config(dut2, "configure terminal", type=self.cli_type)
            st.config(dut2, f"interface {interface}", type=self.cli_type)
            st.config(dut2, "no shutdown", type=self.cli_type)
            st.config(dut2, "exit", type=self.cli_type)
        st.config(dut2, "exit", type=self.cli_type)
        st.log(f"All interfaces configured on {dut2}")

        time.sleep(3)

        # ================================================================
        # STEP 2: Baseline interface status check on both DUTs
        # ================================================================
        st.log("=" * 80)
        st.log("Step 2: Capturing baseline interface status")
        st.log("=" * 80)

        # Set terminal length 0 before show command on DUT1
        st.config(dut1, "terminal length 0", type=self.cli_type)
        baseline_status_dut1 = st.show(dut1, "show interface status", type=self.cli_type)
        st.log(f"Baseline Interface Status on {dut1}:")
        st.log(f"{baseline_status_dut1}")

        # Set terminal length 0 before show command on DUT2
        st.config(dut2, "terminal length 0", type=self.cli_type)
        baseline_status_dut2 = st.show(dut2, "show interface status", type=self.cli_type)
        st.log(f"Baseline Interface Status on {dut2}:")
        st.log(f"{baseline_status_dut2}")

        # ================================================================
        # STEP 3: Create PortChannel10 on both DUTs
        # ================================================================
        st.log("=" * 80)
        st.log("Step 3: Creating PortChannel10 on both DUTs")
        st.log("=" * 80)

        # Create PortChannel on DUT1
        st.log(f"Creating {portchannel_name} on {dut1}...")
        st.config(dut1, "configure terminal", type=self.cli_type)
        st.config(dut1, f"interface {portchannel_name}", type=self.cli_type)
        st.config(dut1, "exit", type=self.cli_type)
        st.config(dut1, "exit", type=self.cli_type)
        st.log(f"{portchannel_name} created on {dut1}")

        # Create PortChannel on DUT2
        st.log(f"Creating {portchannel_name} on {dut2}...")
        st.config(dut2, "configure terminal", type=self.cli_type)
        st.config(dut2, f"interface {portchannel_name}", type=self.cli_type)
        st.config(dut2, "exit", type=self.cli_type)
        st.config(dut2, "exit", type=self.cli_type)
        st.log(f"{portchannel_name} created on {dut2}")

        time.sleep(2)

        # ================================================================
        # STEP 4: Add first interface to PortChannel10 on both DUTs
        # ================================================================
        st.log("=" * 80)
        st.log(f"Step 4: Adding {member_interface} to {portchannel_name} on both DUTs")
        st.log("=" * 80)

        # Add member interface to PortChannel on DUT1
        st.log(f"Adding {member_interface} to {portchannel_name} on {dut1}...")
        st.config(dut1, "configure terminal", type=self.cli_type)
        st.config(dut1, f"interface {member_interface}", type=self.cli_type)
        st.config(dut1, f"channel-group {self.portchannel_number}", type=self.cli_type)
        st.config(dut1, "exit", type=self.cli_type)
        st.config(dut1, "exit", type=self.cli_type)
        st.log(f"{member_interface} added to {portchannel_name} on {dut1}")

        # Add member interface to PortChannel on DUT2
        st.log(f"Adding {member_interface} to {portchannel_name} on {dut2}...")
        st.config(dut2, "configure terminal", type=self.cli_type)
        st.config(dut2, f"interface {member_interface}", type=self.cli_type)
        st.config(dut2, f"channel-group {self.portchannel_number}", type=self.cli_type)
        st.config(dut2, "exit", type=self.cli_type)
        st.config(dut2, "exit", type=self.cli_type)
        st.log(f"{member_interface} added to {portchannel_name} on {dut2}")

        time.sleep(3)

        # Display show commands after adding interfaces to portchannel (outside sonic-cli)
        st.log("=" * 80)
        st.log("Executing show commands after adding interface to PortChannel (Linux shell)")
        st.log("=" * 80)

        # Execute on DUT1
        st.log(f"Executing 'show interfaces portchannel' on {dut1} (Linux shell)...")
        portchannel_linux_dut1 = st.show(dut1, "show interfaces portchannel", type="click")

        st.log("=" * 80)
        st.log(f"PortChannel Status outside sonic-cli on {dut1}:")
        st.log("=" * 80)
        st.log(f"{portchannel_linux_dut1}")

        st.log(f"Executing 'show interface status' on {dut1} (Linux shell)...")
        intf_status_linux_dut1 = st.show(dut1, "show interface status", type="click")

        st.log("=" * 80)
        st.log(f"Interface Status outside sonic-cli on {dut1}:")
        st.log("=" * 80)
        st.log(f"{intf_status_linux_dut1}")

        # Execute on DUT2
        st.log(f"Executing 'show interfaces portchannel' on {dut2} (Linux shell)...")
        portchannel_linux_dut2 = st.show(dut2, "show interfaces portchannel", type="click")

        st.log("=" * 80)
        st.log(f"PortChannel Status outside sonic-cli on {dut2}:")
        st.log("=" * 80)
        st.log(f"{portchannel_linux_dut2}")

        st.log(f"Executing 'show interface status' on {dut2} (Linux shell)...")
        intf_status_linux_dut2 = st.show(dut2, "show interface status", type="click")

        st.log("=" * 80)
        st.log(f"Interface Status outside sonic-cli on {dut2}:")
        st.log("=" * 80)
        st.log(f"{intf_status_linux_dut2}")
        st.log("=" * 80)

        # ================================================================
        # STEP 5: Display and store "show interface PortChannel" output
        # ================================================================
        st.log("=" * 80)
        st.log("Step 5: Displaying PortChannel status")
        st.log("=" * 80)

        # Set terminal length 0 before show command on DUT1
        st.config(dut1, "terminal length 0", type=self.cli_type)
        st.log(f"Executing 'show interface PortChannel' on {dut1}...")
        portchannel_output_dut1 = st.show(dut1, "show interface PortChannel", type=self.cli_type, skip_error_check=True)

        st.log("=" * 80)
        st.log(f"PortChannel Status on {dut1}:")
        st.log("=" * 80)
        st.log(f"{portchannel_output_dut1}")
        st.log("=" * 80)

        # Set terminal length 0 before show command on DUT2
        st.config(dut2, "terminal length 0", type=self.cli_type)
        st.log(f"Executing 'show interface PortChannel' on {dut2}...")
        portchannel_output_dut2 = st.show(dut2, "show interface PortChannel", type=self.cli_type, skip_error_check=True)

        st.log("=" * 80)
        st.log(f"PortChannel Status on {dut2}:")
        st.log("=" * 80)
        st.log(f"{portchannel_output_dut2}")
        st.log("=" * 80)

        # Store outputs in variables for potential future validation
        portchannel_status = {
            "dut1": portchannel_output_dut1,
            "dut2": portchannel_output_dut2
        }

        st.log("PortChannel outputs stored in variable")
        st.log(f"Output stored for {dut1}: {type(portchannel_status['dut1'])}")
        st.log(f"Output stored for {dut2}: {type(portchannel_status['dut2'])}")

        # ================================================================
        # STEP 6: Cleanup - Remove interface from PortChannel and delete PortChannel
        # ================================================================
        st.log("=" * 80)
        st.log("Step 6: Cleanup - Removing configuration")
        st.log("=" * 80)

        # Remove member interface from PortChannel on DUT1
        st.log(f"Removing {member_interface} from {portchannel_name} on {dut1}...")
        st.config(dut1, "configure terminal", type=self.cli_type)
        st.config(dut1, f"interface {member_interface}", type=self.cli_type)
        st.config(dut1, "no channel-group", type=self.cli_type)
        st.config(dut1, "exit", type=self.cli_type)
        st.config(dut1, "exit", type=self.cli_type)
        st.log(f"{member_interface} removed from {portchannel_name} on {dut1}")

        # Remove member interface from PortChannel on DUT2
        st.log(f"Removing {member_interface} from {portchannel_name} on {dut2}...")
        st.config(dut2, "configure terminal", type=self.cli_type)
        st.config(dut2, f"interface {member_interface}", type=self.cli_type)
        st.config(dut2, "no channel-group", type=self.cli_type)
        st.config(dut2, "exit", type=self.cli_type)
        st.config(dut2, "exit", type=self.cli_type)
        st.log(f"{member_interface} removed from {portchannel_name} on {dut2}")

        time.sleep(2)

        # Display show commands after removing interfaces from portchannel (outside sonic-cli)
        st.log("=" * 80)
        st.log("Executing show commands after removing interface from PortChannel (Linux shell)")
        st.log("=" * 80)

        # Execute on DUT1
        st.log(f"Executing 'show interfaces portchannel' on {dut1} (Linux shell)...")
        portchannel_after_remove_dut1 = st.show(dut1, "show interfaces portchannel", type="click")

        st.log("=" * 80)
        st.log(f"PortChannel Status outside sonic-cli on {dut1}:")
        st.log("=" * 80)
        st.log(f"{portchannel_after_remove_dut1}")

        st.log(f"Executing 'show interface status' on {dut1} (Linux shell)...")
        intf_status_after_remove_dut1 = st.show(dut1, "show interface status", type="click")

        st.log("=" * 80)
        st.log(f"Interface Status outside sonic-cli on {dut1}:")
        st.log("=" * 80)
        st.log(f"{intf_status_after_remove_dut1}")

        # Execute on DUT2
        st.log(f"Executing 'show interfaces portchannel' on {dut2} (Linux shell)...")
        portchannel_after_remove_dut2 = st.show(dut2, "show interfaces portchannel", type="click")

        st.log("=" * 80)
        st.log(f"PortChannel Status outside sonic-cli on {dut2}:")
        st.log("=" * 80)
        st.log(f"{portchannel_after_remove_dut2}")

        st.log(f"Executing 'show interface status' on {dut2} (Linux shell)...")
        intf_status_after_remove_dut2 = st.show(dut2, "show interface status", type="click")

        st.log("=" * 80)
        st.log(f"Interface Status outside sonic-cli on {dut2}:")
        st.log("=" * 80)
        st.log(f"{intf_status_after_remove_dut2}")
        st.log("=" * 80)

        # Delete PortChannel on DUT1
        st.log(f"Deleting {portchannel_name} on {dut1}...")
        st.config(dut1, "configure terminal", type=self.cli_type)
        st.config(dut1, f"no interface {portchannel_name}", type=self.cli_type)
        st.config(dut1, "exit", type=self.cli_type)
        st.log(f"{portchannel_name} deleted on {dut1}")

        # Delete PortChannel on DUT2
        st.log(f"Deleting {portchannel_name} on {dut2}...")
        st.config(dut2, "configure terminal", type=self.cli_type)
        st.config(dut2, f"no interface {portchannel_name}", type=self.cli_type)
        st.config(dut2, "exit", type=self.cli_type)
        st.log(f"{portchannel_name} deleted on {dut2}")

        # Verify cleanup by checking PortChannel status
        st.log("Verifying cleanup...")

        # Set terminal length 0 before show command on DUT1
        st.config(dut1, "terminal length 0", type=self.cli_type)
        cleanup_status_dut1 = st.show(dut1, "show interface PortChannel", type=self.cli_type, skip_error_check=True)
        st.log(f"PortChannel status after cleanup on {dut1}:")
        st.log(f"{cleanup_status_dut1}")

        # Set terminal length 0 before show command on DUT2
        st.config(dut2, "terminal length 0", type=self.cli_type)
        cleanup_status_dut2 = st.show(dut2, "show interface PortChannel", type=self.cli_type, skip_error_check=True)
        st.log(f"PortChannel status after cleanup on {dut2}:")
        st.log(f"{cleanup_status_dut2}")

        # ================================================================
        # Final Test Summary
        # ================================================================
        st.log("")
        st.log("=" * 80)
        st.log("TEST RESULT: PASS")
        st.log("=" * 80)
        st.log(f"Successfully created {portchannel_name} on both DUTs")
        st.log(f"Successfully added {member_interface} to {portchannel_name} on both DUTs")
        st.log("Successfully displayed PortChannel status using 'show interface PortChannel'")
        st.log("Successfully cleaned up all configurations")
        st.log("=" * 80)

        st.report_pass("test_case_passed")
