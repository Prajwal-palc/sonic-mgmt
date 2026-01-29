"""
SMCI SONiC IS-CLI Interface Bugs Verification Test Suite

Author: Athira
Copyright (C) 2026, PalC Networks

How to run:
  # Run all interface bug tests
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_1node.yaml \\
  tests/system/interface/test_interface_iscli_bugs.py \\
  --logs-path ./logs/interface_bugs_$(date +%F_%H%M%S) \\
  --log-level info --skip-init-config --ifname-type native

  # Run specific bug test
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_1node.yaml \\
  -k "test_interface_001" \\
  tests/system/interface/test_interface_iscli_bugs.py \\
  --logs-path ./logs/interface_bug_001 \\
  --log-level debug

Description:
  This test suite verifies 13 interface-related bugs in SMCI SONiC IS-CLI.
  Tests are designed for interactive verification first, then automation.

Pre-requisites:
  - Topology: one-node (D1) with management access | Supported: HW and Virtual
  - IS-CLI enabled on device
  - Management interface configured
  - At least one Ethernet interface available for testing
"""

import pytest
import re
from spytest import st, SpyTestDict
from spytest.utils import filter_and_select
import apis.system.interface as intf_api
import apis.system.basic as basic_api


# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Bug IDs for tracking
BUG_IDS = SpyTestDict({
    "TC_001": "SM_ISCLI_1",
    "TC_008": "SM_ISCLI_8",
    "TC_012": "SM_ISCLI_12",
    "TC_022": "SM_ISCLI_22",
    "TC_025": "SM_ISCLI_25",
    "TC_031": "SM_ISCLI_31",
    "TC_032": "SM_ISCLI_32",
    "TC_033": "SM_ISCLI_33",
    "TC_034": "SM_ISCLI_34",
    "TC_035": "SM_ISCLI_35",
    "TC_036": "SM_ISCLI_36",
    "TC_059": "SM_ISCLI_59",
    "TC_061": "SM_ISCLI_61",
    "TC_062": "SM_ISCLI_62",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level setup and teardown
    """
    global vars, data

    st.banner("MODULE PROLOGUE: Interface Bugs Test Suite Starting")

    # Get testbed variables
    vars = st.get_testbed_vars()

    # Verify we have at least one DUT
    if not vars.duts:
        st.report_fail("msg", "No DUTs available in testbed")

    # Use first DUT
    data.dut = vars.D1
    data.cli_type = "klish"  # IS-CLI

    # Store original management IP for safety
    try:
        mgmt_ip_output = st.show(data.dut, "ifconfig eth0", skip_tmpl=True)
        st.log(f"Original management interface state: {mgmt_ip_output}")
        data.original_mgmt_config = mgmt_ip_output
    except Exception as e:
        st.log(f"Could not capture original management config: {e}")
        data.original_mgmt_config = None

    # Get available Ethernet interfaces
    try:
        interfaces = st.show(data.dut, "show interface status", type=data.cli_type)
        data.test_interface = "Ethernet0"  # Default test interface
        st.log(f"Available interfaces: {interfaces}")
    except Exception as e:
        st.log(f"Could not get interface list: {e}")
        data.test_interface = "Ethernet0"

    st.log(f"Test DUT: {data.dut}")
    st.log(f"Test Interface: {data.test_interface}")
    st.log(f"CLI Type: {data.cli_type}")

    yield

    # Module epilogue - cleanup
    st.banner("MODULE EPILOGUE: Cleaning up test configurations")

    # Note: Be VERY careful with management interface cleanup
    # Changing management IP during cleanup can break SSH connection

    st.log("Interface bugs test suite completed")


# ============================================================================
# Test Class: Interface Show Commands
# ============================================================================

class TestInterfaceShowCommands:
    """
    Tests for interface show command bugs
    """

    @pytest.mark.interface_bugs
    @pytest.mark.bug_SM_ISCLI_1
    def test_interface_001_show_run_ordering(self):
        """
        TC-001: Verify interface ordering in show running-configuration
        Bug ID: SM_ISCLI_1
        Description: Ordering of interfaces in show run is incorrect
        """
        st.log("\n" + "="*80)
        st.log(f"TEST: {BUG_IDS.TC_001} - Show Running-Config Interface Ordering")
        st.log("="*80)

        dut = data.dut
        cli_type = data.cli_type

        # Step 1: Configure interfaces to ensure we have multiple types
        st.banner("STEP 1: Configure test interfaces")

        test_configs = [
            {"interface": "Loopback0", "ip": "1.1.1.1/32"},
            {"interface": "Loopback1", "ip": "2.2.2.2/32"},
            {" interface": data.test_interface, "ip": "192.168.1.1/24"},
        ]

        for config in test_configs:
            try:
                interface = config["interface"]
                ip = config["ip"]

                if "Loopback" in interface:
                    # Create loopback
                    st.config(dut, f"interface {interface}", type=cli_type)

                # Configure IP
                ip_config = f"""
interface {interface}
ip address {ip}
end
"""
                st.config(dut, ip_config, type=cli_type, skip_error_check=True)
                st.log(f"✓ Configured {interface} with IP {ip}")
            except Exception as e:
                st.log(f"Warning: Could not configure {interface}: {e}")

        # Step 2: Get show running-configuration output
        st.banner("STEP 2: Get show running-configuration")

        try:
            # Use | no-more to prevent pagination
            running_config = st.show(dut, "show running-configuration | no-more",
                                    type=cli_type, skip_tmpl=True, skip_error_check=True)

            st.log(f"Running config output length: {len(str(running_config))} chars")

            # Extract interface section
            config_text = str(running_config)

            # Find all interface declarations
            interface_pattern = r'^interface\s+(\S+.*?)$'
            interfaces_found = re.findall(interface_pattern, config_text, re.MULTILINE)

            st.log(f"Interfaces found in order: {interfaces_found}")

            # Step 3: Verify ordering
            st.banner("STEP 3: Verify interface ordering")

            if not interfaces_found:
                st.log("⚠ WARNING: No interfaces found in running-config")
                st.report_fail("msg", "No interfaces found in running-configuration")

            # Check for logical grouping
            # Expected patterns:
            # - Loopback interfaces first (or grouped together)
            # - Management interfaces grouped
            # - Ethernet interfaces grouped

            loopback_indices = [i for i, iface in enumerate(interfaces_found) if "Loopback" in iface]
            mgmt_indices = [i for i, iface in enumerate(interfaces_found) if "Management" in iface or "eth0" in iface]
            ethernet_indices = [i for i, iface in enumerate(interfaces_found) if "Ethernet" in iface]

            st.log(f"Loopback positions: {loopback_indices}")
            st.log(f"Management positions: {mgmt_indices}")
            st.log(f"Ethernet positions: {ethernet_indices}")

            # Check if each type is grouped (consecutive indices)
            def is_grouped(indices):
                if len(indices) <= 1:
                    return True
                return max(indices) - min(indices) == len(indices) - 1

            loopback_grouped = is_grouped(loopback_indices)
            mgmt_grouped = is_grouped(mgmt_indices)
            ethernet_grouped = is_grouped(ethernet_indices)

            st.log(f"Loopback interfaces grouped: {loopback_grouped}")
            st.log(f"Management interfaces grouped: {mgmt_grouped}")
            st.log(f"Ethernet interfaces grouped: {ethernet_grouped}")

            # Determine pass/fail
            if loopback_grouped and mgmt_grouped and ethernet_grouped:
                st.log("✓ PASS: Interfaces are properly grouped by type")
                st.report_pass("test_case_passed")
            else:
                st.log("❌ FAIL: Interface ordering is inconsistent")
                st.log(f"Full interface order: {interfaces_found}")
                st.report_fail("msg", f"Interface ordering incorrect. Bug {BUG_IDS.TC_001} confirmed")

        except Exception as e:
            st.log(f"❌ ERROR: Failed to verify interface ordering: {e}")
            st.report_fail("msg", f"Test error: {e}")


    @pytest.mark.interface_bugs
    @pytest.mark.bug_SM_ISCLI_12
    def test_interface_012_show_ip_interface_mgmt(self):
        """
        TC-012: Verify show ip interface displays management port
        Bug ID: SM_ISCLI_12
        Description: show ip interface doesn't show management port on IS-CLI
        """
        st.log("\n" + "="*80)
        st.log(f"TEST: {BUG_IDS.TC_012} - Show IP Interface Management Port")
        st.log("="*80)

        dut = data.dut
        cli_type = data.cli_type

        # Step 1: Get Click CLI output
        st.banner("STEP 1: Get Click CLI show ip interfaces output")

        try:
            click_output = st.show(dut, "show ip interfaces", type="click", skip_tmpl=True)
            st.log(f"Click CLI output: {click_output}")

            # Check for eth0/Management in Click output
            click_has_mgmt = "eth0" in str(click_output) or "Management" in str(click_output)
            st.log(f"Click CLI shows management: {click_has_mgmt}")

            if not click_has_mgmt:
                st.log("⚠ WARNING: Management interface not in Click CLI output either")

        except Exception as e:
            st.log(f"Could not get Click CLI output: {e}")
            click_output = None
            click_has_mgmt = False

        # Step 2: Get IS-CLI output
        st.banner("STEP 2: Get IS-CLI show ip interface output")

        try:
            iscli_output = st.show(dut, "show ip interface", type=cli_type,
                                  skip_tmpl=True, skip_error_check=True)
            st.log(f"IS-CLI output: {iscli_output}")

            # Check for Management0/eth0 in IS-CLI output
            iscli_has_mgmt = ("Management0" in str(iscli_output) or
                            "Management 0" in str(iscli_output) or
                            "eth0" in str(iscli_output))

            st.log(f"IS-CLI shows management: {iscli_has_mgmt}")

        except Exception as e:
            st.log(f"ERROR getting IS-CLI output: {e}")
            iscli_output = None
            iscli_has_mgmt = False

        # Step 3: Compare and verify
        st.banner("STEP 3: Verify management interface visibility")

        st.log("\n" + "-"*80)
        st.log("RESULTS:")
        st.log(f"  Click CLI shows management: {click_has_mgmt}")
        st.log(f"  IS-CLI shows management: {iscli_has_mgmt}")
        st.log("-"*80)

        if click_has_mgmt and not iscli_has_mgmt:
            st.log(f"❌ FAIL: Bug {BUG_IDS.TC_012} CONFIRMED")
            st.log("Management interface visible in Click CLI but NOT in IS-CLI")
            st.report_fail("msg", f"Management interface missing from IS-CLI output. Bug {BUG_IDS.TC_012}")
        elif iscli_has_mgmt:
            st.log("✓ PASS: Management interface visible in IS-CLI")
            st.report_pass("test_case_passed")
        else:
            st.log("⚠ INCONCLUSIVE: Management interface not visible in either CLI")
            st.report_fail("msg", "Management interface not found in any CLI output")


    @pytest.mark.interface_bugs
    @pytest.mark.bug_SM_ISCLI_31
    def test_interface_031_show_ip_interfaces_mgmt(self):
        """
        TC-031: Verify show ip interfaces displays management IP
        Bug ID: SM_ISCLI_31
        Description: show ip interfaces not showing mgmt IP whereas Click CLI shows it
        """
        st.log("\n" + "="*80)
        st.log(f"TEST: {BUG_IDS.TC_031} - Show IP Interfaces Management IP")
        st.log("="*80)

        dut = data.dut
        cli_type = data.cli_type

        # This test is similar to TC-012 but focuses on "show ip interfaces" (plural)
        # and management IP address display

        st.banner("STEP 1: Get management IP from Linux")

        try:
            ifconfig_output = st.show(dut, "ifconfig eth0", skip_tmpl=True)
            st.log(f"ifconfig eth0 output: {ifconfig_output}")

            # Extract IP address from ifconfig
            ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', str(ifconfig_output))
            if ip_match:
                mgmt_ip = ip_match.group(1)
                st.log(f"Management IP from ifconfig: {mgmt_ip}")
            else:
                mgmt_ip = None
                st.log("Could not extract management IP from ifconfig")
        except Exception as e:
            st.log(f"Error getting ifconfig: {e}")
            mgmt_ip = None

        # Step 2: Check Click CLI
        st.banner("STEP 2: Check Click CLI show ip interfaces")

        try:
            click_output = st.show(dut, "show ip interfaces", type="click", skip_tmpl=True)
            click_text = str(click_output)

            st.log(f"Click CLI output:\n{click_text}")

            # Check for management IP
            if mgmt_ip and mgmt_ip in click_text:
                st.log(f"✓ Click CLI shows management IP: {mgmt_ip}")
                click_has_mgmt_ip = True
            elif "eth0" in click_text:
                st.log("✓ Click CLI shows eth0 interface")
                click_has_mgmt_ip = True
            else:
                st.log("✗ Click CLI does NOT show management interface")
                click_has_mgmt_ip = False

        except Exception as e:
            st.log(f"Error with Click CLI: {e}")
            click_has_mgmt_ip = False

        # Step 3: Check IS-CLI
        st.banner("STEP 3: Check IS-CLI show ip interfaces")

        try:
            iscli_output = st.show(dut, "show ip interfaces", type=cli_type,
                                  skip_tmpl=True, skip_error_check=True)
            iscli_text = str(iscli_output)

            st.log(f"IS-CLI output:\n{iscli_text}")

            # Check for management IP or interface
            if mgmt_ip and mgmt_ip in iscli_text:
                st.log(f"✓ IS-CLI shows management IP: {mgmt_ip}")
                iscli_has_mgmt_ip = True
            elif "Management0" in iscli_text or "Management 0" in iscli_text:
                st.log("✓ IS-CLI shows Management interface")
                iscli_has_mgmt_ip = True
            else:
                st.log("✗ IS-CLI does NOT show management interface")
                iscli_has_mgmt_ip = False

            # Check for docker0 IP (should NOT be present)
            if "docker0" in iscli_text or "240.127." in iscli_text:
                st.log("⚠ WARNING: Docker IP found in IS-CLI output (should be hidden)")
                has_docker_ip = True
            else:
                has_docker_ip = False

        except Exception as e:
            st.log(f"Error with IS-CLI: {e}")
            iscli_has_mgmt_ip = False
            has_docker_ip = False

        # Step 4: Verify results
        st.banner("STEP 4: Verify results")

        st.log("\n" + "-"*80)
        st.log("RESULTS:")
        st.log(f"  Management IP (from ifconfig): {mgmt_ip}")
        st.log(f"  Click CLI shows management: {click_has_mgmt_ip}")
        st.log(f"  IS-CLI shows management: {iscli_has_mgmt_ip}")
        st.log(f"  IS-CLI shows docker IP: {has_docker_ip}")
        st.log("-"*80)

        issues_found = []

        if click_has_mgmt_ip and not iscli_has_mgmt_ip:
            issues_found.append("Management IP missing from IS-CLI")

        if has_docker_ip:
            issues_found.append("Docker IP incorrectly shown in IS-CLI")

        if issues_found:
            st.log(f"❌ FAIL: Bug {BUG_IDS.TC_031} CONFIRMED")
            for issue in issues_found:
                st.log(f"  - {issue}")
            st.report_fail("msg", f"Management IP display issues: {', '.join(issues_found)}")
        else:
            st.log("✓ PASS: Management IP correctly displayed")
            st.report_pass("test_case_passed")


# ============================================================================
# Test Class: Interface Configuration
# ============================================================================

class TestInterfaceConfiguration:
    """
    Tests for interface configuration bugs
    """

    @pytest.mark.interface_bugs
    @pytest.mark.bug_SM_ISCLI_8
    @pytest.mark.risk_high  # Can break SSH connection
    @pytest.mark.hardware_only  # Skip on virtual SONiC
    def test_interface_008_mgmt_static_ip(self):
        """
        TC-008: Verify Management0 can be assigned static IP
        Bug ID: SM_ISCLI_8
        Description: Management0 can't be assigned a static IP address

        WARNING: This test changes management IP - use with caution!
        Recommend running on console or with backup connection.

        LIMITATION: This test is SKIPPED on virtual SONiC and only runs on hardware.
        Reason: High risk of breaking SSH connection on vSONiC. Requires hardware
        setup with console access for safe execution.
        """
        st.log("\n" + "="*80)
        st.log(f"TEST: {BUG_IDS.TC_008} - Management Static IP Assignment")
        st.log("="*80)
        st.log("⚠ WARNING: This test modifies management IP address")
        st.log("⚠ Ensure you have console access or alternative connection")

        dut = data.dut
        cli_type = data.cli_type

        # Check if running on virtual SONiC - skip if so
        try:
            show_version = st.show(dut, "show version", type=cli_type, skip_tmpl=True)
            if "vsonic" in str(show_version).lower() or "virtual" in str(show_version).lower():
                st.log("⚠ SKIPPING: Test not supported on virtual SONiC")
                st.log("   Reason: High risk of SSH disconnection")
                st.log("   Action: Test only on hardware with console access")
                pytest.skip("TC-008 requires hardware setup with console access")
        except Exception as e:
            st.log(f"Could not determine platform type: {e}")
            # Assume hardware and proceed (safer than skipping on hardware)

        # For safety, use a test IP on same subnet as current management
        # This minimizes risk of losing connection

        st.banner("STEP 1: Get current management IP")

        try:
            current_ip_output = st.show(dut, "ip addr show eth0", skip_tmpl=True)
            st.log(f"Current management interface: {current_ip_output}")

            # Extract current IP
            ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+/\d+)', str(current_ip_output))
            if ip_match:
                current_ip = ip_match.group(1)
                st.log(f"Current management IP: {current_ip}")

                # Calculate test IP (current IP + 10, same subnet)
                ip_parts = current_ip.split('/')
                addr_parts = ip_parts[0].split('.')
                last_octet = int(addr_parts[3])
                new_last_octet = (last_octet + 10) % 254 or 254
                test_ip = f"{addr_parts[0]}.{addr_parts[1]}.{addr_parts[2]}.{new_last_octet}/{ip_parts[1]}"
                st.log(f"Test IP to use: {test_ip}")
            else:
                st.log("⚠ Cannot extract current IP - SKIPPING test for safety")
                pytest.skip("Cannot determine safe test IP")

        except Exception as e:
            st.log(f"Error getting current IP: {e}")
            pytest.skip(f"Cannot get current management IP: {e}")

        st.banner("STEP 2: Attempt to configure static IP via IS-CLI")

        try:
            # WARNING: This can break connection!
            ip_config = f"""
interface Management 0
ip address {test_ip}
end
"""
            result = st.config(dut, ip_config, type=cli_type, skip_error_check=True)
            st.log(f"Configuration result: {result}")

            # Check for errors in output
            if result and ("Error" in str(result) or "error" in str(result).lower()):
                st.log(f"❌ FAIL: Error configuring management IP")
                st.log(f"Error output: {result}")
                st.report_fail("msg", f"Failed to configure management IP. Bug {BUG_IDS.TC_008}")

            st.wait(5, "Waiting for IP configuration to apply")

        except Exception as e:
            st.log(f"❌ FAIL: Exception during configuration: {e}")
            st.report_fail("msg", f"Exception configuring management IP: {e}")

        st.banner("STEP 3: Verify IP was applied")

        try:
            # Check running-config
            show_output = st.show(dut, "show running-configuration interface Management 0",
                                type=cli_type, skip_tmpl=True, skip_error_check=True)
            st.log(f"Running config: {show_output}")

            if test_ip.split('/')[0] in str(show_output):
                st.log(f"✓ Test IP found in running-config")
                config_ok = True
            else:
                st.log(f"✗ Test IP NOT in running-config")
                config_ok = False

            # Check actual interface
            check_ip = st.show(dut, "ip addr show eth0", skip_tmpl=True)
            st.log(f"Actual interface state: {check_ip}")

            if test_ip.split('/')[0] in str(check_ip):
                st.log(f"✓ Test IP applied to interface")
                applied_ok = True
            else:
                st.log(f"✗ Test IP NOT applied to interface")
                applied_ok = False

        except Exception as e:
            st.log(f"Error verifying configuration: {e}")
            config_ok = False
            applied_ok = False

        # STEP 4: Restore original IP (CRITICAL!)
        st.banner("STEP 4: Restore original management IP")

        try:
            restore_config = f"""
interface Management 0
ip address {current_ip}
end
"""
            st.config(dut, restore_config, type=cli_type, skip_error_check=True)
            st.wait(5, "Waiting for IP restoration")
            st.log(f"✓ Restored original IP: {current_ip}")
        except Exception as e:
            st.log(f"⚠ WARNING: Failed to restore original IP: {e}")
            st.log(f"⚠ Manual intervention may be required!")

        # Step 5: Determine pass/fail
        st.banner("STEP 5: Test result")

        if config_ok and applied_ok:
            st.log("✓ PASS: Management IP configuration successful")
            st.report_pass("test_case_passed")
        else:
            st.log(f"❌ FAIL: Management IP configuration failed")
            st.log(f"  Config in running-config: {config_ok}")
            st.log(f"  IP applied to interface: {applied_ok}")
            st.report_fail("msg", f"Management IP configuration issues. Bug {BUG_IDS.TC_008}")


    @pytest.mark.interface_bugs
    @pytest.mark.bug_SM_ISCLI_32
    def test_interface_032_loopback_subnet_validation(self):
        """
        TC-032: Verify loopback interfaces reject non-/32 subnets
        Bug ID: SM_ISCLI_32
        Description: Able to configure non-/32 addresses on Loopback interfaces
        """
        st.log("\n" + "="*80)
        st.log(f"TEST: {BUG_IDS.TC_032} - Loopback Non-/32 Subnet Validation")
        st.log("="*80)

        dut = data.dut
        cli_type = data.cli_type

        test_loopback = "Loopback99"
        test_configs = [
            {"subnet": "/24", "should_fail": True},
            {"subnet": "/30", "should_fail": True},
            {"subnet": "/31", "should_fail": True},
            {"subnet": "/32", "should_fail": False},  # Should succeed
        ]

        results = []

        for test in test_configs:
            subnet = test["subnet"]
            should_fail = test["should_fail"]
            test_ip = f"10.99.99.1{subnet}"

            st.banner(f"Testing subnet: {subnet}")

            try:
                # Configure loopback with test subnet
                config_cmd = f"""
interface {test_loopback}
ip address {test_ip}
end
"""
                output = st.config(dut, config_cmd, type=cli_type, skip_error_check=True)
                st.log(f"Configuration output: {output}")

                # Check for error
                has_error = output and ("Error" in str(output) or "error" in str(output).lower())

                # Verify in running-config
                show_output = st.show(dut, f"show running-configuration interface {test_loopback}",
                                    type=cli_type, skip_tmpl=True, skip_error_check=True)

                config_applied = test_ip.split('/')[0] in str(show_output)

                st.log(f"  Error shown: {has_error}")
                st.log(f"  Config applied: {config_applied}")

                # Determine if behavior is correct
                if should_fail:
                    # Should have rejected the config
                    correct_behavior = has_error or not config_applied
                    status = "✓ CORRECT" if correct_behavior else "✗ INCORRECT"
                else:
                    # Should have accepted the config
                    correct_behavior = not has_error and config_applied
                    status = "✓ CORRECT" if correct_behavior else "✗ INCORRECT"

                results.append({
                    "subnet": subnet,
                    "should_fail": should_fail,
                    "has_error": has_error,
                    "config_applied": config_applied,
                    "correct": correct_behavior,
                    "status": status
                })

                st.log(f"  Result: {status}")

                # Cleanup
                if config_applied:
                    cleanup_cmd = f"""
interface {test_loopback}
no ip address {test_ip}
end
"""
                    st.config(dut, cleanup_cmd, type=cli_type, skip_error_check=True)

            except Exception as e:
                st.log(f"Exception testing {subnet}: {e}")
                results.append({
                    "subnet": subnet,
                    "error": str(e),
                    "correct": False,
                    "status": "✗ EXCEPTION"
                })

        # Cleanup loopback interface
        try:
            st.config(dut, f"no interface {test_loopback}", type=cli_type, skip_error_check=True)
        except:
            pass

        # Analyze results
        st.banner("Test Results Summary")

        for result in results:
            st.log(f"  {result['subnet']}: {result['status']}")

        incorrect_results = [r for r in results if not r.get('correct', False)]

        if incorrect_results:
            st.log(f"\n❌ FAIL: Bug {BUG_IDS.TC_032} CONFIRMED")
            st.log(f"  {len(incorrect_results)} incorrect behaviors detected")
            for r in incorrect_results:
                st.log(f"    - {r['subnet']}: Expected {'rejection' if r['should_fail'] else 'acceptance'}")
            st.report_fail("msg", f"Loopback subnet validation incorrect. Bug {BUG_IDS.TC_032}")
        else:
            st.log("\n✓ PASS: All subnet validations correct")
            st.report_pass("test_case_passed")


    @pytest.mark.interface_bugs
    @pytest.mark.bug_SM_ISCLI_34
    def test_interface_034_duplicate_ip_validation(self):
        """
        TC-034: Verify duplicate IP address (primary/secondary) is rejected
        Bug ID: SM_ISCLI_34
        Description: Allows same IP for primary and secondary address
        """
        st.log("\n" + "="*80)
        st.log(f"TEST: {BUG_IDS.TC_034} - Duplicate IP Address Validation")
        st.log("="*80)

        dut = data.dut
        cli_type = data.cli_type
        test_if = data.test_interface

        test_ip = "10.34.34.1/24"

        st.banner("STEP 1: Configure primary IP address")

        try:
            config_primary = f"""
interface {test_if}
ip address {test_ip}
end
"""
            result = st.config(dut, config_primary, type=cli_type, skip_error_check=True)
            st.log(f"Primary IP configuration result: {result}")

            if "Error" in str(result):
                st.log("⚠ WARNING: Error configuring primary IP (unexpected)")

        except Exception as e:
            st.log(f"Error configuring primary IP: {e}")
            st.report_fail("msg", f"Failed to configure primary IP: {e}")

        st.banner("STEP 2: Attempt to configure same IP as secondary")

        try:
            config_secondary = f"""
interface {test_if}
ip address {test_ip} secondary
end
"""
            result = st.config(dut, config_secondary, type=cli_type, skip_error_check=True)
            st.log(f"Secondary IP configuration result: {result}")

            # Check for error message
            has_error = result and (
                "Error" in str(result) or
                "already configured" in str(result).lower() or
                "duplicate" in str(result).lower()
            )

            st.log(f"Error detected: {has_error}")

            # Extract error message if present
            if has_error:
                error_msg = str(result)
                st.log(f"Error message: {error_msg}")

        except Exception as e:
            st.log(f"Exception during secondary IP config: {e}")
            has_error = True  # Exception counts as rejection

        st.banner("STEP 3: Verify only one IP in configuration")

        try:
            show_output = st.show(dut, f"show running-configuration interface {test_if}",
                                type=cli_type, skip_tmpl=True, skip_error_check=True)
            st.log(f"Interface configuration:\n{show_output}")

            # Count occurrences of test IP
            ip_count = str(show_output).count(test_ip.split('/')[0])
            st.log(f"IP address appears {ip_count} time(s) in config")

        except Exception as e:
            st.log(f"Error checking configuration: {e}")
            ip_count = 0

        # Cleanup
        st.banner("STEP 4: Cleanup test configuration")

        try:
            cleanup_config = f"""
interface {test_if}
no ip address {test_ip}
end
"""
            st.config(dut, cleanup_config, type=cli_type, skip_error_check=True)
        except:
            pass

        # Determine result
        st.banner("STEP 5: Test result")

        st.log("\n" + "-"*80)
        st.log("RESULTS:")
        st.log(f"  Error shown for duplicate IP: {has_error}")
        st.log(f"  IP count in config: {ip_count}")
        st.log("-"*80)

        if has_error and ip_count <= 1:
            st.log("✓ PASS: Duplicate IP correctly rejected")
            st.report_pass("test_case_passed")
        else:
            st.log(f"❌ FAIL: Bug {BUG_IDS.TC_034} CONFIRMED")
            if not has_error:
                st.log("  - No error message shown for duplicate IP")
            if ip_count > 1:
                st.log(f"  - Duplicate IP accepted ({ip_count} occurrences)")
            st.report_fail("msg", f"Duplicate IP not rejected. Bug {BUG_IDS.TC_034}")


# ============================================================================
# Test Class: Interface Display Issues
# ============================================================================

class TestInterfaceDisplayIssues:
    """
    Tests for interface display and formatting bugs
    """

    @pytest.mark.interface_bugs
    @pytest.mark.bug_SM_ISCLI_22
    def test_interface_022_mgmt_naming_consistency(self):
        """
        TC-022: Verify Management interface naming consistency
        Bug ID: SM_ISCLI_22
        Description: Management0 appears as eth0 in running-config
        """
        st.log("\n" + "="*80)
        st.log(f"TEST: {BUG_IDS.TC_022} - Management Interface Naming")
        st.log("="*80)

        dut = data.dut
        cli_type = data.cli_type

        st.banner("STEP 1: Get running-configuration")

        try:
            running_config = st.show(dut, "show running-configuration | no-more",
                                    type=cli_type, skip_tmpl=True, skip_error_check=True)
            config_text = str(running_config)

            st.log(f"Running config length: {len(config_text)} chars")

        except Exception as e:
            st.log(f"Error getting running-config: {e}")
            st.report_fail("msg", f"Cannot get running-configuration: {e}")

        st.banner("STEP 2: Check for management interface naming")

        # Look for both possible names
        has_management0 = "interface Management0" in config_text or "interface Management 0" in config_text
        has_eth0 = "interface eth0" in config_text

        st.log(f"Contains 'interface Management0': {has_management0}")
        st.log(f"Contains 'interface eth0': {has_eth0}")

        # Extract context around interface declarations
        if has_eth0:
            # Find lines around "interface eth0"
            for i, line in enumerate(config_text.split('\n')):
                if 'interface eth0' in line.lower():
                    st.log(f"Found at line {i}: {line}")
                    # Show context
                    start = max(0, i-2)
                    end = min(len(config_text.split('\n')), i+5)
                    context = '\n'.join(config_text.split('\n')[start:end])
                    st.log(f"Context:\n{context}")

        st.banner("STEP 3: Verify naming consistency")

        st.log("\n" + "-"*80)
        st.log("RESULTS:")
        st.log(f"  Uses 'Management0': {has_management0}")
        st.log(f"  Uses 'eth0': {has_eth0}")
        st.log("-"*80)

        if has_eth0:
            st.log(f"❌ FAIL: Bug {BUG_IDS.TC_022} CONFIRMED")
            st.log("Management interface shown as 'eth0' instead of 'Management0'")
            st.report_fail("msg", f"Inconsistent management interface naming. Bug {BUG_IDS.TC_022}")
        elif has_management0:
            st.log("✓ PASS: Management interface correctly named 'Management0'")
            st.report_pass("test_case_passed")
        else:
            st.log("⚠ INCONCLUSIVE: No management interface found in running-config")
            st.report_fail("msg", "Management interface not found in configuration")


    @pytest.mark.interface_bugs
    @pytest.mark.bug_SM_ISCLI_25
    def test_interface_025_description_quotes(self):
        """
        TC-025: Verify description with multiple words uses quotes
        Bug ID: SM_ISCLI_25
        Description: show running-config shows description without quotes
        """
        st.log("\n" + "="*80)
        st.log(f"TEST: {BUG_IDS.TC_025} - Description Quotes in Show Running-Config")
        st.log("="*80)

        dut = data.dut
        cli_type = data.cli_type
        test_if = data.test_interface

        test_description = "Ethernet interface to DC"  # Multi-word description

        st.banner("STEP 1: Configure multi-word description")

        try:
            desc_config = f"""
interface {test_if}
description {test_description}
end
"""
            result = st.config(dut, desc_config, type=cli_type, skip_error_check=True)
            st.log(f"Description configuration result: {result}")

        except Exception as e:
            st.log(f"Error configuring description: {e}")
            st.report_fail("msg", f"Failed to configure description: {e}")

        st.banner("STEP 2: Get show running-configuration output")

        try:
            show_output = st.show(dut, f"show running-configuration interface {test_if}",
                                type=cli_type, skip_tmpl=True, skip_error_check=True)
            st.log(f"Interface configuration:\n{show_output}")

            # Find description line
            desc_line = None
            for line in str(show_output).split('\n'):
                if 'description' in line.lower():
                    desc_line = line.strip()
                    break

            if desc_line:
                st.log(f"Description line found: '{desc_line}'")
            else:
                st.log("⚠ Description line not found in output")

        except Exception as e:
            st.log(f"Error getting running-config: {e}")
            desc_line = None

        st.banner("STEP 3: Test copy/paste of description")

        if desc_line:
            try:
                # Remove leading/trailing whitespace and try to re-apply
                # This simulates copy/paste of the line
                st.log(f"Attempting to re-apply: {desc_line}")

                reapply_config = f"""
interface {test_if}
{desc_line}
end
"""
                reapply_result = st.config(dut, reapply_config, type=cli_type, skip_error_check=True)
                st.log(f"Re-apply result: {reapply_result}")

                # Check for error
                has_error = reapply_result and ("Error" in str(reapply_result) or
                                               "error" in str(reapply_result).lower())

                st.log(f"Re-apply caused error: {has_error}")

            except Exception as e:
                st.log(f"Exception during re-apply: {e}")
                has_error = True
        else:
            has_error = True  # Can't test without description line

        # Cleanup
        try:
            cleanup_config = f"""
interface {test_if}
no description
end
"""
            st.config(dut, cleanup_config, type=cli_type, skip_error_check=True)
        except:
            pass

        st.banner("STEP 4: Verify description format")

        st.log("\n" + "-"*80)
        st.log("RESULTS:")
        st.log(f"  Description line: {desc_line}")
        st.log(f"  Copy/paste failed: {has_error}")

        # Check if description has quotes
        if desc_line:
            has_quotes = '"' in desc_line
            st.log(f"  Has quotes: {has_quotes}")
        else:
            has_quotes = False
        st.log("-"*80)

        if has_error and not has_quotes:
            st.log(f"❌ FAIL: Bug {BUG_IDS.TC_025} CONFIRMED")
            st.log("Multi-word description without quotes causes copy/paste to fail")
            st.report_fail("msg", f"Description format issue. Bug {BUG_IDS.TC_025}")
        elif not has_error or has_quotes:
            st.log("✓ PASS: Description properly formatted")
            st.report_pass("test_case_passed")
        else:
            st.log("⚠ INCONCLUSIVE: Could not verify description format")
            st.report_fail("msg", "Description format test inconclusive")


# ============================================================================
# Additional test cases to be implemented:
# - TC-033: Show interface detailed information
# - TC-035: Speed auto command
# - TC-036: Standalone link training
# - TC-059: Multiple management/routing display issues
# - TC-061: Show interface management syntax
# - TC-062: IPv6 autoconfig default state
# ============================================================================

# Placeholder functions for remaining tests (to be implemented)

@pytest.mark.interface_bugs
@pytest.mark.bug_SM_ISCLI_33
@pytest.mark.skip(reason="To be implemented after interactive testing")
def test_interface_033_show_interface_details():
    """TC-033: Show interface detailed information - To be implemented"""
    pass

@pytest.mark.interface_bugs
@pytest.mark.bug_SM_ISCLI_35
@pytest.mark.skip(reason="To be implemented after interactive testing")
def test_interface_035_speed_auto_command():
    """TC-035: Speed auto command availability - To be implemented"""
    pass

@pytest.mark.interface_bugs
@pytest.mark.bug_SM_ISCLI_36
@pytest.mark.skip(reason="To be implemented after interactive testing")
def test_interface_036_standalone_link_training():
    """TC-036: Standalone link training command - To be implemented"""
    pass

@pytest.mark.interface_bugs
@pytest.mark.bug_SM_ISCLI_59
@pytest.mark.skip(reason="To be implemented after interactive testing")
def test_interface_059_mgmt_ip_routing_display():
    """TC-059: Management IP and routing display issues - To be implemented"""
    pass

@pytest.mark.interface_bugs
@pytest.mark.bug_SM_ISCLI_61
@pytest.mark.skip(reason="To be implemented after interactive testing")
def test_interface_061_show_interface_mgmt_syntax():
    """TC-061: Show interface management syntax - To be implemented"""
    pass

@pytest.mark.interface_bugs
@pytest.mark.bug_SM_ISCLI_62
@pytest.mark.skip(reason="To be implemented after interactive testing")
def test_interface_062_ipv6_autoconfig_default():
    """TC-062: IPv6 autoconfig default and control - To be implemented"""
    pass
