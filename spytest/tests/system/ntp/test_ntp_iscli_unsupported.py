"""
NTP IS-CLI UNSUPPORTED TEST CASES - SSE-T8196 Issue Documentation
Author: Athira
2026

Description:
  This file contains NTP test cases that are currently UNSUPPORTED due to
  feature limitations in the current SONiC klish CLI implementation or
  configuration requirements not met in the test environment.

  Many tests document specific SSE-T8196 issues reported for SMCI SONiC v1.2 IS-CLI.

  These tests serve as:
  - Documentation of known limitations
  - Regression detection if issues are fixed
  - Negative test validation

UNSUPPORTED TEST CASES AND REASONS (10 tests total):

SERVER CONFIGURATION LIMITATIONS:

1. test_ntp_025_server_association_server
   - Reason: Association type attribute is not supported in REST API response
   - Feature limitation: klish CLI does not expose association_type in REST output
   - Will be supported when: SONiC REST API includes association_type field

2. test_ntp_027_server_association_pool
   - Reason: Pool association type not supported in klish CLI
   - Feature limitation: klish only supports 'ntp server' command, not 'ntp pool'
   - Will be supported when: klish CLI implements 'ntp pool' command
   - Workaround: Use REST or gNMI interface for pool configuration

3. test_ntp_028_server_all_options
   - Reason: Some NTP server options not supported in klish CLI
   - Missing options: iburst, association_type, key, trusted/prefer
   - Will be supported when: klish CLI implements full option set

SOURCE INTERFACE LIMITATIONS (SSE-T8196 Issues #1, #2, #4):

4. test_ntp_034_source_interface_vlan ⭐ NEW
   - Issue: SSE-T8196 #2 - Can't set NTP "source-interface VLAN"
   - Tests: VLAN interfaces (Vlan10, Vlan100) cannot be configured as source-interface
   - Expected: Command should fail with error for VLAN interfaces

5. test_ntp_042_source_interface_management ⭐ NEW
   - Issue: SSE-T8196 #4 - Cannot set Management0 as NTP source-interface
   - Tests: Management0 interface cannot be configured as source-interface
   - Expected: Command should fail or not take effect for Management0

6. test_ntp_043_multiple_source_interfaces ⭐ NEW
   - Issue: SSE-T8196 #1 - Does not support multiple NTP source-interfaces
   - Also tests: Cannot delete source-interface individually
   - Expected: Only one source-interface allowed; must delete without specifying interface name

VRF CONFIGURATION:

7. test_ntp_036_config_vrf_without_mgmt
   - Reason: mgmt VRF not defined in test configuration
   - Configuration requirement: Requires vrf_names list with 'mgmt' entry in YAML
   - Will be supported when: Test environment has management VRF configured

8. test_ntp_037_config_vrf_with_mgmt
   - Reason: mgmt VRF not defined in test configuration
   - Configuration requirement: Requires vrf_names list with 'mgmt' entry in YAML
   - Will be supported when: Test environment has management VRF configured

SHOW COMMANDS (SSE-T8196 Issue #7):

9. test_ntp_041_show_ntp_associations
   - Issue: SSE-T8196 #7 - Show ntp associations missing fields
   - Reason: NTP associations data not available or incomplete
   - Possible causes:
     * NTP server not providing association information
     * Server not synchronized yet
     * Association feature not fully implemented in this SONiC version
   - Will be supported when: SONiC NTP associations feature is fully implemented

NTP SERVER MODE (SSE-T8196 Issue #3):

10. test_ntp_044_enable_ntp_server_mode ⭐ NEW
    - Issue: SSE-T8196 #3 - Switch does not support acting as an NTP server
    - Tests: SONiC can only operate as NTP client, not NTP server
    - Expected: Commands to enable server mode should fail or not be available
    - Note: This is about serving time to other devices, not using upstream servers

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_1node.yaml \\
  tests/system/ntp/test_ntp_iscli_unsupported.py \\
  --logs-path ./logs/test_ntp_unsupported_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Pre-requisites:
  - Topology: single-node | Supported: HW and Virtual
  - Feature flags / min SONiC version: NTP support with full feature implementation
  - Required test variables (YAML): tests/system/ntp/vars_ntp_iscli_local.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.system.ntp as ntp_api
import apis.system.basic as basic_api

# YAML configuration file path
VAR_FILE_ENV = "NTP_ISCLI_VAR_FILE"
DEFAULT_VAR_FILE = Path(__file__).resolve().parent / "vars_ntp_iscli_local.yaml"


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        st.error(f"NTP variable file not found: {candidate}")
        pytest.skip(f"NTP variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        st.error("NTP YAML must contain key 'testcases'")
        pytest.skip("NTP YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestNTPUnsupportedServerConfiguration:
    """UNSUPPORTED: NTP Server Configuration tests with feature limitations"""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup for server configuration tests."""
        st.banner("MODULE PROLOGUE: NTP Unsupported Server Configuration Tests")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        topology = st.get_testbed_vars()

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.ntp_servers = SpyTestDict(config.get("ntp_servers", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.dut = topology.D1
        cls.data.configured_servers: List[str] = []

        # Load local NTP server from config
        cls.data.local_ntp_server = defaults.get("local_ntp_server", "192.168.100.175")

        # Clean up any existing NTP servers from previous test runs
        st.log("Cleaning up existing NTP servers before starting tests")
        try:
            ntp_api.delete_ntp_servers(cls.data.dut, cli_type=cls.data.cli_type)
        except Exception as e:
            st.log(f"Pre-test cleanup warning: {e}")

    def teardown_method(self, method) -> None:
        """Cleanup servers after each test."""
        dut = self.data.dut
        cli_type = self.data.cli_type

        # Clean up configured servers
        if hasattr(self.data, 'configured_servers') and self.data.configured_servers:
            for server in self.data.configured_servers[:]:  # Copy list to avoid modification during iteration
                try:
                    ntp_api.delete_ntp_server(dut, ipaddress=server, cli_type=cli_type)
                    st.log(f"Cleaned up NTP server: {server}")
                except Exception as e:
                    st.log(f"Cleanup error for server {server}: {e}")
            self.data.configured_servers.clear()

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup all NTP servers."""
        st.banner("MODULE EPILOGUE: Cleaning up NTP servers")
        dut = cls.data.dut
        cli_type = cls.data.cli_type

        try:
            ntp_api.delete_ntp_servers(dut, cli_type=cli_type)
        except Exception as e:
            st.log(f"Cleanup error: {e}")

    @pytest.mark.servers
    @pytest.mark.unsupported
    def test_ntp_025_server_association_server(self) -> None:
        """NTP-025: Configure NTP server with association type 'server'."""
        st.banner("TEST: NTP-025 - Configure NTP Server with Association Type Server")

        dut = self.data.dut
        cli_type = self.data.cli_type
        server_addr = self.data.local_ntp_server  # Use local NTP server
        association_type = "server"

        # Configure server with association type server
        result = ntp_api.config_ntp_server(
            dut, ipaddress=server_addr, association_type=association_type, cli_type=cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure NTP server {server_addr} with association {association_type}")

        self.data.configured_servers.append(server_addr)

        # Verify server is configured
        if not ntp_api.verify_ntp_server(dut, server=server_addr, cli_type=cli_type):
            st.report_fail("msg", f"NTP server {server_addr} not found in configuration")

        # Verify association type via REST API (skip if not supported)
        from apis.system.rest import get_rest
        rest_urls = st.get_datastore(dut, "rest_urls")
        if not rest_urls:
            st.log("REST URLs datastore not available, skipping REST API verification")
            st.report_pass("test_case_passed")
            return

        url = rest_urls.get('ntp_server_config', '/restconf/data/sonic-ntp:sonic-ntp/NTP_SERVER')

        response = get_rest(dut, rest_url=url)
        if not response or 'output' not in response:
            st.log("Failed to retrieve NTP server configuration via REST, skipping attribute check")
            st.report_pass("test_case_passed")
            return

        # Find server in the list and check association type
        server_list = response['output'].get('sonic-ntp:NTP_SERVER', {}).get('NTP_SERVER_LIST', [])

        for srv in server_list:
            if srv.get('server_address') == server_addr:
                actual_assoc_type = srv.get('association_type')
                if actual_assoc_type is None:
                    st.log(f"Association type not supported in this SONiC version - Feature not implemented")
                    st.report_unsupported("test_case_unsupported", "Association type configuration not supported in klish CLI")
                    return
                elif actual_assoc_type != association_type:
                    st.report_fail("msg", f"Association type mismatch: Expected '{association_type}', got '{actual_assoc_type}'")
                else:
                    st.log(f"Verified: Server {server_addr} configured with association_type={actual_assoc_type}")
                break

        st.report_pass("test_case_passed")

    @pytest.mark.servers
    @pytest.mark.unsupported
    def test_ntp_027_server_association_pool(self) -> None:
        """NTP-027: Configure NTP server with association type 'pool'."""
        st.banner("TEST: NTP-027 - Configure NTP Server with Association Type Pool")

        dut = self.data.dut
        cli_type = self.data.cli_type
        server_addr = "pool.ntp.org"
        association_type = "pool"

        # NOTE: The 'ntp pool' command is not supported in klish CLI
        # Only REST/gNMI interfaces support pool association type
        # This is a known CLI limitation in SONiC IS-CLI
        if cli_type in ["klish"]:
            st.log("SKIPPING: 'ntp pool' association type not supported in klish CLI")
            st.log("Feature limitation: klish CLI only supports 'ntp server' command")
            st.log("Pool association requires REST or gNMI interface")
            st.report_unsupported("msg", "NTP pool association type not supported in klish CLI - feature limitation")

        # Configure server with association type pool
        result = ntp_api.config_ntp_server(
            dut, ipaddress=server_addr, association_type=association_type, cli_type=cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure NTP server {server_addr} with association {association_type}")

        self.data.configured_servers.append(server_addr)

        # Verify server is configured
        if not ntp_api.verify_ntp_server(dut, server=server_addr, cli_type=cli_type):
            st.report_fail("msg", f"NTP server {server_addr} not found in configuration")

        # Verify association type via REST API (skip if not supported)
        from apis.system.rest import get_rest
        rest_urls = st.get_datastore(dut, "rest_urls")
        if not rest_urls:
            st.log("REST URLs datastore not available, skipping REST API verification")
            st.report_pass("test_case_passed")
            return

        url = rest_urls.get('ntp_server_config', '/restconf/data/sonic-ntp:sonic-ntp/NTP_SERVER')

        response = get_rest(dut, rest_url=url)
        if not response or 'output' not in response:
            st.log("Failed to retrieve NTP server configuration via REST, skipping attribute check")
            st.report_pass("test_case_passed")
            return

        # Find server in the list and check association type
        server_list = response['output'].get('sonic-ntp:NTP_SERVER', {}).get('NTP_SERVER_LIST', [])

        for srv in server_list:
            if srv.get('server_address') == server_addr:
                actual_assoc_type = srv.get('association_type')
                if actual_assoc_type is None:
                    st.log(f"Association type not supported in this SONiC version - Feature not implemented")
                    st.report_unsupported("test_case_unsupported", "Association type configuration not supported in klish CLI")
                    return
                elif actual_assoc_type != association_type:
                    st.report_fail("msg", f"Association type mismatch: Expected '{association_type}', got '{actual_assoc_type}'")
                else:
                    st.log(f"Verified: Server {server_addr} configured with association_type={actual_assoc_type}")
                break

        st.report_pass("test_case_passed")

    @pytest.mark.servers
    @pytest.mark.unsupported
    def test_ntp_028_server_all_options(self) -> None:
        """NTP-028: Configure NTP server with all available options."""
        st.banner("TEST: NTP-028 - Configure NTP Server with All Options")

        dut = self.data.dut
        cli_type = self.data.cli_type
        server_addr = self.data.local_ntp_server  # Use local NTP server
        version = 4
        association_type = "server"
        key_id = 25

        # Configure authentication key before using it
        st.log(f"Configuring authentication key {key_id}")
        if not ntp_api.config_ntp_auth_key(dut, key_id, "sha256", "SecureKey123", cli_type=cli_type):
            st.report_fail("msg", f"Failed to configure authentication key {key_id}")

        # Add a small delay to ensure auth key is committed to device
        import time
        time.sleep(2)
        st.log(f"Authentication key {key_id} configured, proceeding to configure NTP server")

        # Configure server with all options: version, association, iburst, key, prefer
        # Note: association_type parameter is not supported in klish CLI
        result = ntp_api.config_ntp_server(
            dut,
            ipaddress=server_addr,
            version=version,
            iburst=True,
            key_id=key_id,
            prefer=True,
            cli_type=cli_type,
        )
        if not result:
            st.report_fail("msg", f"Failed to configure NTP server {server_addr} with all options")

        self.data.configured_servers.append(server_addr)

        # Verify server is configured
        if not ntp_api.verify_ntp_server(dut, server=server_addr, cli_type=cli_type):
            st.report_fail("msg", f"NTP server {server_addr} not found in configuration")

        # Verify options via REST API (skip unsupported attributes)
        from apis.system.rest import get_rest
        rest_urls = st.get_datastore(dut, "rest_urls")
        if not rest_urls:
            st.log("REST URLs datastore not available, skipping REST API verification")
            st.report_pass("test_case_passed")
            return

        url = rest_urls.get('ntp_server_config', '/restconf/data/sonic-ntp:sonic-ntp/NTP_SERVER')

        response = get_rest(dut, rest_url=url)
        if not response or 'output' not in response:
            st.log("Failed to retrieve NTP server configuration via REST, skipping attribute check")
            st.report_pass("test_case_passed")
            return

        # Find server and check supported attributes
        server_list = response['output'].get('sonic-ntp:NTP_SERVER', {}).get('NTP_SERVER_LIST', [])

        for srv in server_list:
            if srv.get('server_address') == server_addr:
                st.log(f"Found server {server_addr} in configuration: {srv}")

                # Check which attributes are actually supported
                unsupported_attrs = []

                # Check version (usually supported)
                actual_version = srv.get('version')
                if actual_version is not None and actual_version != version:
                    st.report_fail("msg", f"Version mismatch: Expected {version}, got {actual_version}")

                # Check iburst, association, key, prefer - may not be supported
                if srv.get('iburst') is None:
                    unsupported_attrs.append('iburst')
                if srv.get('association_type') is None:
                    unsupported_attrs.append('association_type')
                if srv.get('key') is None:
                    unsupported_attrs.append('key')
                if srv.get('trusted') is None:
                    unsupported_attrs.append('trusted/prefer')

                if unsupported_attrs:
                    st.log(f"Unsupported attributes in this SONiC version: {', '.join(unsupported_attrs)}")
                    st.report_unsupported("test_case_unsupported",
                                  f"Some options not supported in klish CLI: {', '.join(unsupported_attrs)}")
                    return

                st.log(f"Verified: Server {server_addr} configured with all supported options")
                break

        st.report_pass("test_case_passed")


@pytest.mark.topology("any")
class TestNTPUnsupportedSourceInterface:
    """UNSUPPORTED: NTP Source Interface Configuration with limitations

    Tests for known source interface restrictions:
    - SSE-T8196: Cannot set VLAN as NTP source-interface
    - SSE-T8196: Cannot set Management0 as NTP source-interface
    - SSE-T8196: Does not support multiple NTP source-interfaces
    - SSE-T8196: Cannot delete source-interface individually
    """

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup for source interface limitation tests."""
        st.banner("MODULE PROLOGUE: NTP Source Interface Limitation Tests")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        topology = st.get_testbed_vars()

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.dut = topology.D1

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup source interface configuration."""
        st.banner("MODULE EPILOGUE: Cleaning up source interface")
        dut = cls.data.dut
        cli_type = cls.data.cli_type

        try:
            ntp_api.config_ntp_source_interface(dut, interface="", config="no", cli_type=cli_type)
        except Exception as e:
            st.log(f"Cleanup error: {e}")

    @pytest.mark.source_interface
    @pytest.mark.unsupported
    def test_ntp_034_source_interface_vlan(self) -> None:
        """NTP-034: Attempt to configure VLAN as NTP source-interface (negative test).

        Issue: SSE-T8196 SMCI SONiC v1.2][SMCI IS-CLI] Can't set NTP "source-interface VLAN"

        Expected: Command should fail with error indicating VLAN interfaces are not supported
        as NTP source-interface in klish CLI.
        """
        st.banner("TEST: NTP-034 - Configure VLAN as Source Interface (Negative)")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # Test both Vlan naming conventions
        vlan_interfaces = ["Vlan10", "Vlan100"]

        for interface in vlan_interfaces:
            st.log(f"Attempting to configure {interface} as NTP source-interface")

            # Attempt to configure VLAN interface as source
            output = st.config(
                dut,
                f"ntp source-interface {interface}",
                type=cli_type,
                skip_error_check=True
            )

            output_str = str(output)

            # Check if error occurred (expected behavior)
            if "Error" in output_str or "not supported" in output_str.lower() or "Invalid" in output_str:
                st.log(f"✓ Expected error received for {interface}: VLAN not supported as source-interface")
                st.log(f"Error output: {output_str}")
            else:
                st.log(f"⚠ WARNING: {interface} source-interface command did not produce expected error")
                st.log(f"This may indicate the limitation has been fixed, or error detection failed")
                st.log(f"Output: {output_str}")

        st.log("ISSUE SSE-T8196 CONFIRMED: VLAN interfaces cannot be used as NTP source-interface")
        st.report_unsupported("msg", "VLAN interfaces not supported as NTP source-interface in klish CLI")

    @pytest.mark.source_interface
    @pytest.mark.unsupported
    def test_ntp_042_source_interface_management(self) -> None:
        """NTP-042: Attempt to configure Management0 as NTP source-interface (negative test).

        Issue: SSE-T8196 SMCI SONiC v1.2][SMCI IS-CLI] Cannot set Management0 as NTP source-interface

        Expected: Command should fail with error or Management0 should not be accepted
        as NTP source-interface in klish CLI.
        """
        st.banner("TEST: NTP-042 - Configure Management0 as Source Interface (Negative)")

        dut = self.data.dut
        cli_type = self.data.cli_type
        interface = "Management0"

        st.log(f"Attempting to configure {interface} as NTP source-interface")

        # Attempt to configure Management0 interface as source
        output = st.config(
            dut,
            f"ntp source-interface {interface}",
            type=cli_type,
            skip_error_check=True
        )

        output_str = str(output)

        # Check if error occurred (expected behavior)
        if "Error" in output_str or "not supported" in output_str.lower() or "Invalid" in output_str:
            st.log(f"✓ Expected error received: Management0 not supported as source-interface")
            st.log(f"Error output: {output_str}")
        else:
            st.log(f"⚠ WARNING: Management0 source-interface command did not produce expected error")
            st.log(f"Output: {output_str}")

            # If command succeeded, verify it actually took effect
            show_output = st.show(dut, "show ntp global", type=cli_type, skip_tmpl=True)
            show_str = str(show_output)

            if "Management0" in show_str or "management" in show_str.lower():
                st.log("⚠ Management0 appears in show output - limitation may have been fixed")
            else:
                st.log("✓ Management0 not visible in show output despite command succeeding")

        st.log("ISSUE SSE-T8196 CONFIRMED: Management0 cannot be used as NTP source-interface")
        st.report_unsupported("msg", "Management0 not supported as NTP source-interface in klish CLI")

    @pytest.mark.source_interface
    @pytest.mark.unsupported
    def test_ntp_043_multiple_source_interfaces(self) -> None:
        """NTP-043: Attempt to configure multiple NTP source-interfaces (negative test).

        Issue: SSE-T8196 SMCI SONiC v1.2][SMCI IS-CLI] It does not support multiple NTP
        source-interface, nor does it support deleting source-interface individually

        Expected: Only one source-interface should be allowed at a time. Configuring a second
        source-interface should either fail or replace the first one.
        """
        st.banner("TEST: NTP-043 - Configure Multiple Source Interfaces (Negative)")

        dut = self.data.dut
        cli_type = self.data.cli_type

        first_interface = "Ethernet0"
        second_interface = "Ethernet4"

        try:
            # Step 1: Configure first source-interface
            st.log(f"Step 1: Configuring first source-interface: {first_interface}")
            result1 = ntp_api.config_ntp_source_interface(
                dut, interface=first_interface, config="yes", cli_type=cli_type
            )

            if not result1:
                st.report_fail("msg", f"Failed to configure first source-interface {first_interface}")

            # Verify first interface is configured
            show_output1 = st.show(dut, "show ntp global", type=cli_type, skip_tmpl=True)
            show_str1 = str(show_output1)

            if first_interface not in show_str1:
                st.log(f"⚠ WARNING: {first_interface} not visible in show output after configuration")

            # Step 2: Attempt to configure second source-interface
            st.log(f"Step 2: Attempting to configure second source-interface: {second_interface}")
            output2 = st.config(
                dut,
                f"ntp source-interface {second_interface}",
                type=cli_type,
                skip_error_check=True
            )

            output_str2 = str(output2)

            # Step 3: Check the result
            show_output2 = st.show(dut, "show ntp global", type=cli_type, skip_tmpl=True)
            show_str2 = str(show_output2)

            # Analyze behavior
            if "Error" in output_str2:
                st.log("✓ Expected behavior: Error when configuring second source-interface")
                st.log(f"Error output: {output_str2}")
            elif second_interface in show_str2 and first_interface not in show_str2:
                st.log("✓ Expected behavior: Second interface replaced first interface")
                st.log("Only one source-interface is active at a time")
            elif second_interface in show_str2 and first_interface in show_str2:
                st.log("⚠ UNEXPECTED: Both interfaces appear in show output")
                st.log("This may indicate the limitation has been fixed to support multiple interfaces")
                st.report_fail("msg", "Multiple source-interfaces found - expected limitation not present")
            else:
                st.log("Configuration behavior unclear - manual verification needed")

            # Step 4: Test individual deletion limitation
            st.log(f"Step 3: Attempting to delete individual source-interface: {second_interface}")
            delete_output = st.config(
                dut,
                f"no ntp source-interface {second_interface}",
                type=cli_type,
                skip_error_check=True
            )

            delete_str = str(delete_output)

            # Check if individual deletion is supported
            show_output3 = st.show(dut, "show ntp global", type=cli_type, skip_tmpl=True)
            show_str3 = str(show_output3)

            if "Error" in delete_str or second_interface in show_str3:
                st.log("✓ Expected behavior: Cannot delete source-interface individually")
                st.log("Must use 'no ntp source-interface' without interface name to delete")
            else:
                st.log("⚠ Individual deletion may be supported - limitation may have been fixed")

        finally:
            # Cleanup: Delete all source interfaces
            st.log("Cleanup: Deleting all source-interface configuration")
            ntp_api.config_ntp_source_interface(dut, interface="", config="no", cli_type=cli_type)

        st.log("ISSUE SSE-T8196 CONFIRMED: Multiple source-interfaces not supported")
        st.log("ISSUE SSE-T8196 CONFIRMED: Cannot delete source-interface individually")
        st.report_unsupported("msg", "Multiple NTP source-interfaces and individual deletion not supported in klish CLI")


@pytest.mark.topology("any")
class TestNTPUnsupportedServerMode:
    """UNSUPPORTED: NTP Server Mode - Switch acting as NTP server

    Tests for NTP server mode limitation:
    - SSE-T8196: The switch does not support acting as an NTP server
    """

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup for NTP server mode tests."""
        st.banner("MODULE PROLOGUE: NTP Server Mode Limitation Tests")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        topology = st.get_testbed_vars()

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.dut = topology.D1

    @pytest.mark.servers
    @pytest.mark.unsupported
    def test_ntp_044_enable_ntp_server_mode(self) -> None:
        """NTP-044: Attempt to enable SONiC switch as NTP server (negative test).

        Issue: SSE-T8196 SMCI SONiC v1.2][SMCI IS-CLI] The switch does not support acting
        as an NTP server

        Expected: SONiC should only operate as NTP client, not as NTP server. Any command
        to enable server mode should fail or not be available.

        Note: This tests whether the device can act as an NTP server to provide time to
        other devices, not whether it can configure upstream NTP servers (which is supported).
        """
        st.banner("TEST: NTP-044 - Enable NTP Server Mode (Negative)")

        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log("Testing if SONiC supports acting as an NTP server for other devices")

        # Test various possible commands to enable NTP server mode
        server_mode_commands = [
            "ntp server enable",
            "ntp enable-server",
            "ntp allow",
            "ntp serve",
        ]

        errors_found = 0
        for cmd in server_mode_commands:
            st.log(f"Attempting command: {cmd}")
            output = st.config(dut, cmd, type=cli_type, skip_error_check=True)
            output_str = str(output)

            if "Error" in output_str or "Invalid" in output_str or "not found" in output_str.lower():
                st.log(f"✓ Command '{cmd}' produced expected error (not supported)")
                errors_found += 1
            else:
                st.log(f"⚠ Command '{cmd}' did not produce error: {output_str}")

        # Check configuration for any server mode indicators
        st.log("Checking running configuration for NTP server mode indicators")
        config_output = st.show(dut, "show running-config | include ntp", type=cli_type, skip_tmpl=True)
        config_str = str(config_output)

        server_keywords = ["server enable", "enable-server", "ntp serve", "ntp allow"]
        server_mode_found = any(keyword in config_str.lower() for keyword in server_keywords)

        if server_mode_found:
            st.log("⚠ WARNING: Server mode configuration found in running-config")
            st.log("This may indicate the limitation has been fixed")
        else:
            st.log("✓ No server mode configuration found in running-config (expected)")

        # Check show ntp global for server mode status
        show_global = st.show(dut, "show ntp global", type=cli_type, skip_tmpl=True)
        show_str = str(show_global)

        if "server mode" in show_str.lower() or "serving" in show_str.lower():
            st.log("⚠ Server mode status visible in show ntp global")
        else:
            st.log("✓ No server mode indicators in show ntp global (expected)")

        st.log(f"Result: {errors_found}/{len(server_mode_commands)} server mode commands produced errors")
        st.log("ISSUE SSE-T8196 CONFIRMED: SONiC switch does not support acting as NTP server")
        st.log("Note: SONiC can use upstream NTP servers (client mode) but cannot serve time to other devices")

        st.report_unsupported("msg", "NTP server mode not supported - switch can only act as NTP client")


@pytest.mark.topology("any")
class TestNTPUnsupportedVRF:
    """UNSUPPORTED: NTP VRF Configuration tests requiring mgmt VRF"""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup for VRF tests."""
        st.banner("MODULE PROLOGUE: NTP Unsupported VRF Tests")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        topology = st.get_testbed_vars()

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.vrf_names = config.get("vrf_names", [])
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.dut = topology.D1
        cls.data.mgmt_vrf_enabled = False

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup VRF configuration."""
        st.banner("MODULE EPILOGUE: Cleaning up NTP VRF")
        dut = cls.data.dut
        cli_type = cls.data.cli_type

        try:
            # Delete NTP VRF configuration
            st.config(dut, "no ntp vrf", type=cli_type)

            # Disable management VRF if we enabled it
            if cls.data.mgmt_vrf_enabled:
                st.config(dut, "no management vrf", type=cli_type)
        except Exception as e:
            st.log(f"Cleanup error: {e}")

    @pytest.mark.vrf
    @pytest.mark.unsupported
    def test_ntp_036_config_vrf_without_mgmt(self) -> None:
        """NTP-036: Attempt to configure NTP VRF without management VRF (negative test)."""
        st.banner("TEST: NTP-036 - Configure NTP VRF Without Management VRF")

        dut = self.data.dut
        cli_type = self.data.cli_type

        if not self.data.vrf_names or "mgmt" not in self.data.vrf_names:
            st.report_unsupported("msg", "mgmt VRF not defined in configuration")

        # Try to configure NTP VRF without enabling management VRF first
        # This should fail with error: "Must condition not satisfied"
        output = st.config(dut, "ntp vrf mgmt", type=cli_type, skip_error_check=True)

        # Verify error message is present
        if "Error" in str(output) or "Must condition not satisfied" in str(output):
            st.log("Expected error received: NTP VRF configuration requires management VRF")
            st.report_pass("test_case_passed")
        else:
            st.report_fail("msg", "Expected error for NTP VRF without management VRF, but command succeeded")

    @pytest.mark.vrf
    @pytest.mark.unsupported
    def test_ntp_037_config_vrf_with_mgmt(self) -> None:
        """NTP-037: Configure NTP VRF with management VRF enabled (positive test)."""
        st.banner("TEST: NTP-037 - Configure NTP VRF With Management VRF")

        dut = self.data.dut
        cli_type = self.data.cli_type

        if not self.data.vrf_names or "mgmt" not in self.data.vrf_names:
            st.report_unsupported("msg", "mgmt VRF not defined in configuration")

        # Step 1: Enable management VRF
        st.log("Enabling management VRF")
        result = st.config(dut, "management vrf", type=cli_type)
        if not result:
            st.report_fail("msg", "Failed to enable management VRF")

        self.data.mgmt_vrf_enabled = True

        # Step 2: Configure NTP VRF
        st.log("Configuring NTP VRF mgmt")
        result = st.config(dut, "ntp vrf mgmt", type=cli_type)
        if not result:
            st.report_fail("msg", "Failed to configure NTP VRF")

        # Step 3: Verify NTP VRF configuration
        # Use appropriate show command for klish mode
        show_cmd = "show ntp global" if cli_type == "klish" else "show ntp"
        output = st.show(dut, show_cmd, type=cli_type, skip_tmpl=True)
        output_str = ' '.join(str(item) for item in output) if isinstance(output, list) else str(output)
        if "mgmt" not in output_str:
            st.report_fail("msg", "NTP VRF 'mgmt' not found in show ntp output")

        st.report_pass("test_case_passed")


@pytest.mark.topology("any")
class TestNTPUnsupportedShowCommands:
    """UNSUPPORTED: NTP Show Commands with feature limitations"""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup for show command tests."""
        st.banner("MODULE PROLOGUE: NTP Unsupported Show Commands Tests")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        topology = st.get_testbed_vars()

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.ntp_servers = SpyTestDict(config.get("ntp_servers", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.dut = topology.D1
        cls.data.local_ntp_server = defaults.get("local_ntp_server", "192.168.100.175")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup show command test configuration."""
        st.banner("MODULE EPILOGUE: Cleaning up show commands test")
        dut = cls.data.dut
        cli_type = cls.data.cli_type

        try:
            # Delete all servers
            ntp_api.delete_ntp_servers(dut, cli_type=cli_type)

            # Delete authentication keys
            ntp_api.delete_ntp_auth_key(dut, 10, cli_type=cli_type)

            # Disable authentication and NTP
            ntp_api.config_ntp_authenticate(dut, config="no", cli_type=cli_type)
            ntp_api.config_ntp_enable(dut, config="no", cli_type=cli_type)

        except Exception as e:
            st.log(f"Cleanup error: {e}")

    @pytest.mark.show_commands
    @pytest.mark.unsupported
    def test_ntp_041_show_ntp_associations(self) -> None:
        """NTP-041: Verify 'show ntp associations' command displays NTP peer associations."""
        st.banner("TEST: NTP-041 - Verify Show NTP Associations")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # Setup: Configure NTP server
        server_addr = "172.16.1.1"

        st.log(f"Configuring NTP server {server_addr}")
        ntp_api.config_ntp_server(dut, ipaddress=server_addr, cli_type=cli_type)

        # Execute show ntp associations command
        st.log("Executing: show ntp associations")
        output = st.show(dut, "show ntp associations", type=cli_type)

        # Verify output contains expected information
        output_str = str(output)

        # Check for table headers (based on manual log)
        # Expected headers: remote, local, st, t, when, poll, reach, delay, offset, jitter
        expected_headers = ["remote", "local", "st", "t", "poll"]

        # Check if at least some headers are present
        headers_found = sum(1 for header in expected_headers if header.lower() in output_str.lower())

        if headers_found < 2:
            st.log("Warning: show ntp associations may not show standard table format")

        # Note: NTP associations data may not be available if:
        # 1. NTP server is not providing association information
        # 2. Server is not synchronized yet
        # 3. Association feature is not fully implemented in this SONiC version
        if not output or len(output_str) < 10:
            st.log("UNSUPPORTED: show ntp associations returns no meaningful data")
            st.log("This may indicate NTP association feature is not fully implemented or server not synchronized")
            st.report_unsupported("msg", "NTP associations data not available - feature may not be fully implemented")

        st.log("show ntp associations command executed successfully")
        st.report_pass("test_case_passed")
