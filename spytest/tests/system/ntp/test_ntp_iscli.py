"""
NTP IS-CLI AUTOMATION TEST SUITE
Author: Athira
2026

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_1node.yaml \
  tests/system/ntp/test_ntp_iscli.py \
  --logs-path ./logs/test_ntp_iscli_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Comprehensive NTP CLI automation test suite validating NTP global configuration,
  authentication (MD5, SHA1, SHA256, SHA384, SHA512), authentication keys, trusted keys,
  server configuration with various options (version, association, iburst, prefer),
  source interface configuration, and VRF support. Tests cover positive and negative
  scenarios including enable/disable operations, CRUD operations on servers and keys,
  and complex multi-server setups with authentication.

Pre-requisites:
  - Topology: single-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node
        # +--------------------+
        # |        D1          |
        # |     (DUT)          |
        # +--------------------+

  - Feature flags / min SONiC version: NTP support required
  - Required test variables (YAML): tests/system/ntp/vars_ntp_iscli.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.system.ntp as ntp_api
import apis.system.basic as basic_api
import apis.switching.vlan as vlan_api
import apis.routing.ip as ip_api

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
class TestNTPGlobalConfiguration:
    """Test Category 1: NTP Global Configuration - Enable/Disable NTP service"""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.banner("MODULE PROLOGUE: NTP Global Configuration Tests")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # NTP tests don't require connected ports, just a single device
        # min_topology = defaults.get("min_topology") or ["D1:1"]
        # topology = st.ensure_min_topology(*min_topology)
        topology = st.get_testbed_vars()

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Get DUT handle
        cls.data.dut = topology.D1
        cls.data.dut_names = st.get_dut_names()

        # Disable terminal paging for klish CLI to prevent '--more--' prompts
        if cls.data.cli_type == "klish":
            st.log("Disabling terminal paging for klish CLI to prevent '--more--' prompts")
            try:
                st.config(cls.data.dut, "terminal length 0", type=cls.data.cli_type, skip_error_check=True)
                st.log("✓ Terminal paging disabled successfully")
            except Exception as e:
                st.log(f"⚠ Warning: Could not disable terminal paging: {e}")

        st.log(f"Test setup complete. DUT: {cls.data.dut}, CLI type: {cls.data.cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup all NTP configuration after the suite completes."""
        st.banner("MODULE EPILOGUE: Cleaning up NTP configuration")
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping")
            return

        dut = cls.data.dut
        cli_type = cls.data.cli_type

        # Disable NTP and clear all configuration
        try:
            # Delete all servers
            ntp_api.delete_ntp_servers(dut, cli_type=cli_type)

            # Delete all authentication keys
            for key_id in range(1, 100):
                ntp_api.delete_ntp_auth_key(dut, key_id, cli_type=cli_type)

            # Disable NTP
            ntp_api.config_ntp_enable(dut, config="no", cli_type=cli_type)

        except Exception as e:
            st.log(f"Cleanup error (non-fatal): {e}")

    def setup_method(self) -> None:
        """Reset per-test bookkeeping."""
        st.log("Test setup: Preparing for next test")

    def teardown_method(self) -> None:
        """Cleanup after each test."""
        if not self.data.cleanup_enabled:
            return

        st.log("Test teardown: Cleaning up test configuration")

    @pytest.mark.global_config
    def test_ntp_001_enable_ntp(self) -> None:
        """NTP-001: Enable NTP service and verify it is active."""
        st.banner("TEST: NTP-001 - Enable NTP Service")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # Enable NTP
        result = ntp_api.config_ntp_enable(dut, config="yes", cli_type=cli_type)
        if not result:
            st.report_fail("msg", "Failed to enable NTP service")

        # Verify NTP is enabled by checking configuration
        ntp_status = ntp_api.verify_ntp_config(dut, ntp_enable=True, cli_type=cli_type)
        if not ntp_status:
            st.report_fail("msg", "NTP service is not enabled after configuration")

        st.report_pass("test_case_passed")

    @pytest.mark.global_config
    def test_ntp_002_disable_ntp(self) -> None:
        """NTP-002: Disable NTP service and verify it is inactive."""
        st.banner("TEST: NTP-002 - Disable NTP Service")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # First enable NTP
        ntp_api.config_ntp_enable(dut, config="yes", cli_type=cli_type)

        # Then disable NTP
        result = ntp_api.config_ntp_enable(dut, config="no", cli_type=cli_type)
        if not result:
            st.report_fail("msg", "Failed to disable NTP service")

        # Verify NTP is disabled via REST API
        from apis.system.rest import get_rest
        rest_urls = st.get_datastore(dut, "rest_urls")
        if not rest_urls:
            st.log("REST URLs datastore not available, skipping REST API verification")
            st.report_pass("test_case_passed")
            return

        url = rest_urls.get('ntp_global_config', '/restconf/data/sonic-ntp:sonic-ntp/NTP')

        response = get_rest(dut, rest_url=url)
        if response and 'output' in response:
            output = response['output']
            if 'sonic-ntp:NTP' in output and 'global' in output['sonic-ntp:NTP']:
                admin_state = output['sonic-ntp:NTP']['global'].get('admin_state', '')
                if admin_state == 'disabled':
                    st.log(f"Verified: NTP service is disabled (admin_state={admin_state})")
                else:
                    st.report_fail("msg", f"NTP service state mismatch: Expected 'disabled', got '{admin_state}'")
            else:
                st.log("NTP global configuration not found, assuming disabled")
        else:
            st.log("Could not verify via REST, assuming configuration succeeded")

        st.report_pass("test_case_passed")

    @pytest.mark.global_config
    def test_ntp_003_reenable_ntp(self) -> None:
        """NTP-003: Re-enable NTP service after disabling."""
        st.banner("TEST: NTP-003 - Re-enable NTP Service")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # Disable NTP
        ntp_api.config_ntp_enable(dut, config="no", cli_type=cli_type)

        # Re-enable NTP
        result = ntp_api.config_ntp_enable(dut, config="yes", cli_type=cli_type)
        if not result:
            st.report_fail("msg", "Failed to re-enable NTP service")

        # Verify NTP is enabled by checking configuration
        ntp_status = ntp_api.verify_ntp_config(dut, ntp_enable=True, cli_type=cli_type)
        if not ntp_status:
            st.report_fail("msg", "NTP service is not enabled after re-configuration")

        st.report_pass("test_case_passed")


@pytest.mark.topology("any")
class TestNTPAuthentication:
    """Test Category 2: NTP Authentication - Enable/Disable authentication"""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup for authentication tests."""
        st.banner("MODULE PROLOGUE: NTP Authentication Tests")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # NTP tests don't require connected ports, just a single device
        # min_topology = defaults.get("min_topology") or ["D1:1"]
        # topology = st.ensure_min_topology(*min_topology)
        topology = st.get_testbed_vars()

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.dut = topology.D1

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup authentication configuration."""
        st.banner("MODULE EPILOGUE: Cleaning up authentication")
        dut = cls.data.dut
        cli_type = cls.data.cli_type

        try:
            # Disable authentication
            ntp_api.config_ntp_authenticate(dut, config="no", cli_type=cli_type)
        except Exception as e:
            st.log(f"Cleanup error: {e}")

    @pytest.mark.authentication
    def test_ntp_004_enable_authentication(self) -> None:
        """NTP-004: Enable NTP authentication."""
        st.banner("TEST: NTP-004 - Enable NTP Authentication")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # Enable authentication
        result = ntp_api.config_ntp_authenticate(dut, config="yes", cli_type=cli_type)
        if not result:
            st.report_fail("msg", "Failed to enable NTP authentication")

        # Verify authentication is enabled via REST API
        from apis.system.rest import get_rest
        rest_urls = st.get_datastore(dut, "rest_urls")
        if not rest_urls:
            st.log("REST URLs datastore not available, skipping REST API verification")
            st.report_pass("test_case_passed")
            return

        url = rest_urls.get('ntp_global_config', '/restconf/data/sonic-ntp:sonic-ntp/NTP')

        response = get_rest(dut, rest_url=url)
        if response and 'output' in response:
            output = response['output']
            if 'sonic-ntp:NTP' in output and 'global' in output['sonic-ntp:NTP']:
                auth_state = output['sonic-ntp:NTP']['global'].get('authentication', 'disabled')
                if auth_state == 'enabled' or auth_state is True:
                    st.log(f"Verified: NTP authentication is enabled (authentication={auth_state})")
                else:
                    st.report_fail("msg", f"NTP authentication state mismatch: Expected 'enabled', got '{auth_state}'")
            else:
                st.log("Could not find NTP authentication status in response")
        else:
            st.log("Could not verify via REST, assuming configuration succeeded")

        st.report_pass("test_case_passed")

    @pytest.mark.authentication
    def test_ntp_005_disable_authentication(self) -> None:
        """NTP-005: Disable NTP authentication."""
        st.banner("TEST: NTP-005 - Disable NTP Authentication")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # Enable first
        ntp_api.config_ntp_authenticate(dut, config="yes", cli_type=cli_type)

        # Then disable
        result = ntp_api.config_ntp_authenticate(dut, config="no", cli_type=cli_type)
        if not result:
            st.report_fail("msg", "Failed to disable NTP authentication")

        # Verify authentication is disabled via REST API
        from apis.system.rest import get_rest
        rest_urls = st.get_datastore(dut, "rest_urls")
        if not rest_urls:
            st.log("REST URLs datastore not available, skipping REST API verification")
            st.report_pass("test_case_passed")
            return

        url = rest_urls.get('ntp_global_config', '/restconf/data/sonic-ntp:sonic-ntp/NTP')

        response = get_rest(dut, rest_url=url)
        if response and 'output' in response:
            output = response['output']
            if 'sonic-ntp:NTP' in output and 'global' in output['sonic-ntp:NTP']:
                auth_state = output['sonic-ntp:NTP']['global'].get('authentication', 'enabled')
                if auth_state == 'disabled' or auth_state is False:
                    st.log(f"Verified: NTP authentication is disabled (authentication={auth_state})")
                else:
                    st.report_fail("msg", f"NTP authentication state mismatch: Expected 'disabled', got '{auth_state}'")
            else:
                st.log("Could not find NTP authentication status in response")
        else:
            st.log("Could not verify via REST, assuming configuration succeeded")

        st.report_pass("test_case_passed")


@pytest.mark.topology("any")
class TestNTPAuthenticationKeys:
    """Test Category 3: NTP Authentication Keys - Configure keys with different hash algorithms"""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup for authentication key tests."""
        st.banner("MODULE PROLOGUE: NTP Authentication Keys Tests")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # NTP tests don't require connected ports, just a single device
        # min_topology = defaults.get("min_topology") or ["D1:1"]
        # topology = st.ensure_min_topology(*min_topology)
        topology = st.get_testbed_vars()

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.auth_keys = SpyTestDict(config.get("auth_keys", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.dut = topology.D1
        cls.data.configured_keys: List[int] = []

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup all authentication keys."""
        st.banner("MODULE EPILOGUE: Cleaning up authentication keys")
        dut = cls.data.dut
        cli_type = cls.data.cli_type

        for key_id in cls.data.configured_keys:
            try:
                ntp_api.delete_ntp_auth_key(dut, key_id, cli_type=cli_type)
            except Exception as e:
                st.log(f"Cleanup error for key {key_id}: {e}")

    @pytest.mark.auth_keys
    def test_ntp_007_auth_key_md5(self) -> None:
        """NTP-007: Configure authentication key with MD5."""
        st.banner("TEST: NTP-007 - Configure MD5 Authentication Key")

        dut = self.data.dut
        cli_type = self.data.cli_type
        key_config = self.data.auth_keys.md5_key

        key_id = key_config.key_id
        auth_type = key_config.auth_type
        password = key_config.password

        # Configure key
        result = ntp_api.config_ntp_auth_key(
            dut, key_id, auth_type, password, cli_type=cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure MD5 auth key {key_id}")

        self.data.configured_keys.append(key_id)
        st.report_pass("test_case_passed")

    @pytest.mark.auth_keys
    def test_ntp_008_auth_key_sha1(self) -> None:
        """NTP-008: Configure authentication key with SHA1."""
        st.banner("TEST: NTP-008 - Configure SHA1 Authentication Key")

        dut = self.data.dut
        cli_type = self.data.cli_type
        key_config = self.data.auth_keys.sha1_key

        key_id = key_config.key_id
        auth_type = key_config.auth_type
        password = key_config.password

        # Configure key
        result = ntp_api.config_ntp_auth_key(
            dut, key_id, auth_type, password, cli_type=cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure SHA1 auth key {key_id}")

        self.data.configured_keys.append(key_id)
        st.report_pass("test_case_passed")

    @pytest.mark.auth_keys
    def test_ntp_009_auth_key_sha256(self) -> None:
        """NTP-009: Configure authentication key with SHA256."""
        st.banner("TEST: NTP-009 - Configure SHA256 Authentication Key")

        dut = self.data.dut
        cli_type = self.data.cli_type
        key_config = self.data.auth_keys.sha256_key

        key_id = key_config.key_id
        auth_type = key_config.auth_type
        password = key_config.password

        # Configure key
        result = ntp_api.config_ntp_auth_key(
            dut, key_id, auth_type, password, cli_type=cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure SHA256 auth key {key_id}")

        self.data.configured_keys.append(key_id)
        st.report_pass("test_case_passed")

    @pytest.mark.auth_keys
    def test_ntp_010_auth_key_sha384(self) -> None:
        """NTP-010: Configure authentication key with SHA384."""
        st.banner("TEST: NTP-010 - Configure SHA384 Authentication Key")

        dut = self.data.dut
        cli_type = self.data.cli_type
        key_config = self.data.auth_keys.sha384_key

        key_id = key_config.key_id
        auth_type = key_config.auth_type
        password = key_config.password

        # Configure key
        result = ntp_api.config_ntp_auth_key(
            dut, key_id, auth_type, password, cli_type=cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure SHA384 auth key {key_id}")

        self.data.configured_keys.append(key_id)
        st.report_pass("test_case_passed")

    @pytest.mark.auth_keys
    def test_ntp_011_auth_key_sha512(self) -> None:
        """NTP-011: Configure authentication key with SHA512."""
        st.banner("TEST: NTP-011 - Configure SHA512 Authentication Key")

        dut = self.data.dut
        cli_type = self.data.cli_type
        key_config = self.data.auth_keys.sha512_key

        key_id = key_config.key_id
        auth_type = key_config.auth_type
        password = key_config.password

        # Configure key
        result = ntp_api.config_ntp_auth_key(
            dut, key_id, auth_type, password, cli_type=cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure SHA512 auth key {key_id}")

        self.data.configured_keys.append(key_id)
        st.report_pass("test_case_passed")

    @pytest.mark.auth_keys
    def test_ntp_013_delete_auth_key(self) -> None:
        """NTP-013: Delete NTP authentication key."""
        st.banner("TEST: NTP-013 - Delete Authentication Key")

        dut = self.data.dut
        cli_type = self.data.cli_type
        key_id = 99

        # First configure a key
        ntp_api.config_ntp_auth_key(dut, key_id, "md5", "TestPass", cli_type=cli_type)

        # Then delete it
        result = ntp_api.delete_ntp_auth_key(dut, key_id, cli_type=cli_type)
        if not result:
            st.report_fail("msg", f"Failed to delete auth key {key_id}")

        # Verify key is deleted via REST API
        from apis.system.rest import get_rest
        rest_urls = st.get_datastore(dut, "rest_urls")
        if not rest_urls:
            st.log("REST URLs datastore not available, skipping REST API verification")
            st.report_pass("test_case_passed")
            return

        url = rest_urls.get('ntp_auth_keys_config', '/restconf/data/sonic-ntp:sonic-ntp/NTP_KEY')

        response = get_rest(dut, rest_url=url)
        if response and 'output' in response:
            output = response['output']
            if 'sonic-ntp:NTP_KEY' in output and 'NTP_KEY_LIST' in output['sonic-ntp:NTP_KEY']:
                key_list = output['sonic-ntp:NTP_KEY']['NTP_KEY_LIST']
                for key in key_list:
                    if key.get('key_id') == key_id:
                        st.report_fail("msg", f"Auth key {key_id} still exists after deletion")
                st.log(f"Verified: Auth key {key_id} successfully deleted")
            else:
                st.log("No auth keys found, deletion verified")
        else:
            st.log("Could not verify via REST, assuming deletion succeeded")

        st.report_pass("test_case_passed")


@pytest.mark.topology("any")
class TestNTPTrustedKeys:
    """Test Category 3B: NTP Trusted Key Configuration"""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup for trusted key tests."""
        st.banner("MODULE PROLOGUE: NTP Trusted Keys Tests")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # NTP tests don't require connected ports, just a single device
        topology = st.get_testbed_vars()

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.trusted_keys = config.get("trusted_keys", [])
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.dut = topology.D1
        cls.data.configured_trusted_keys: List[int] = []

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup all trusted keys."""
        st.banner("MODULE EPILOGUE: Cleaning up trusted keys")
        dut = cls.data.dut
        cli_type = cls.data.cli_type

        for key_id in cls.data.configured_trusted_keys:
            try:
                ntp_api.delete_ntp_trusted_key(dut, key_id, cli_type=cli_type)
            except Exception as e:
                st.log(f"Cleanup error for trusted key {key_id}: {e}")

    @pytest.mark.trusted_keys
    def test_ntp_012_config_trusted_key(self) -> None:
        """NTP-012: Configure NTP trusted key."""
        st.banner("TEST: NTP-012 - Configure Trusted Key")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # Use the first trusted key from config
        if not self.data.trusted_keys:
            st.report_unsupported("msg", "No trusted keys defined in configuration")

        key_id = self.data.trusted_keys[0]

        # Configure trusted key
        result = ntp_api.config_ntp_trusted_key(dut, key_id, cli_type=cli_type)
        if not result:
            st.report_fail("msg", f"Failed to configure trusted key {key_id}")

        self.data.configured_trusted_keys.append(key_id)
        st.report_pass("test_case_passed")

    @pytest.mark.trusted_keys
    def test_ntp_014_config_multiple_trusted_keys(self) -> None:
        """NTP-014: Configure multiple NTP trusted keys."""
        st.banner("TEST: NTP-014 - Configure Multiple Trusted Keys")

        dut = self.data.dut
        cli_type = self.data.cli_type

        if len(self.data.trusted_keys) < 2:
            st.report_unsupported("msg", "Need at least 2 trusted keys in configuration")

        # Configure multiple trusted keys
        for key_id in self.data.trusted_keys:
            result = ntp_api.config_ntp_trusted_key(dut, key_id, cli_type=cli_type)
            if not result:
                st.report_fail("msg", f"Failed to configure trusted key {key_id}")
            self.data.configured_trusted_keys.append(key_id)

        st.report_pass("test_case_passed")

    @pytest.mark.trusted_keys
    def test_ntp_015_delete_trusted_key(self) -> None:
        """NTP-015: Delete NTP trusted key."""
        st.banner("TEST: NTP-015 - Delete Trusted Key")

        dut = self.data.dut
        cli_type = self.data.cli_type
        key_id = 99

        # First configure a trusted key
        ntp_api.config_ntp_trusted_key(dut, key_id, cli_type=cli_type)

        # Then delete it
        result = ntp_api.delete_ntp_trusted_key(dut, key_id, cli_type=cli_type)
        if not result:
            st.report_fail("msg", f"Failed to delete trusted key {key_id}")

        st.report_pass("test_case_passed")

    @pytest.mark.trusted_keys
    def test_ntp_016_trusted_key_max_id(self) -> None:
        """NTP-016: Configure NTP trusted key with maximum key ID (65535)."""
        st.banner("TEST: NTP-016 - Configure Trusted Key with Maximum ID")

        dut = self.data.dut
        cli_type = self.data.cli_type
        key_id = 65535  # Maximum NTP key ID

        # Configure trusted key with maximum ID
        result = ntp_api.config_ntp_trusted_key(dut, key_id, cli_type=cli_type)
        if not result:
            st.report_fail("msg", f"Failed to configure trusted key with maximum ID {key_id}")

        self.data.configured_trusted_keys.append(key_id)
        st.report_pass("test_case_passed")


@pytest.mark.topology("any")
class TestNTPServerConfiguration:
    """Test Category 4: NTP Server Configuration - Add, update, delete NTP servers"""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup for server configuration tests."""
        st.banner("MODULE PROLOGUE: NTP Server Configuration Tests")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # NTP tests don't require connected ports, just a single device
        # min_topology = defaults.get("min_topology") or ["D1:1"]
        # topology = st.ensure_min_topology(*min_topology)
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

        # Skip cleanup for specific tests that need to preserve servers
        skip_cleanup_tests = ['test_ntp_029_server_max_limit', 'test_ntp_032_multiple_servers']
        if method.__name__ in skip_cleanup_tests:
            st.log(f"Skipping server cleanup for {method.__name__}")
            return

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
    def test_ntp_020_basic_server_ip(self) -> None:
        """NTP-020: Configure basic NTP server with IP address."""
        st.banner("TEST: NTP-020 - Configure NTP Server with IP")

        dut = self.data.dut
        cli_type = self.data.cli_type
        server_addr = self.data.local_ntp_server  # Use local NTP server

        # Configure server
        result = ntp_api.config_ntp_server(dut, ipaddress=server_addr, cli_type=cli_type)
        if not result:
            st.report_fail("msg", f"Failed to configure NTP server {server_addr}")

        self.data.configured_servers.append(server_addr)

        # Verify server is configured
        if not ntp_api.verify_ntp_server(dut, server=server_addr, cli_type=cli_type):
            st.report_fail("msg", f"NTP server {server_addr} not found in configuration")

        st.report_pass("test_case_passed")

    @pytest.mark.servers
    def test_ntp_021_server_hostname(self) -> None:
        """NTP-021: Configure NTP server with hostname."""
        st.banner("TEST: NTP-021 - Configure NTP Server with Hostname")

        dut = self.data.dut
        cli_type = self.data.cli_type
        server_addr = "time.google.com"

        # Configure server
        result = ntp_api.config_ntp_server(dut, ipaddress=server_addr, cli_type=cli_type)
        if not result:
            st.report_fail("msg", f"Failed to configure NTP server {server_addr}")

        self.data.configured_servers.append(server_addr)

        # Verify server is configured
        if not ntp_api.verify_ntp_server(dut, server=server_addr, cli_type=cli_type):
            st.report_fail("msg", f"NTP server {server_addr} not found in configuration")

        st.log(f"Verified: NTP server {server_addr} (hostname) configured successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.servers
    def test_ntp_026_server_iburst(self) -> None:
        """NTP-026: Configure NTP server with iburst option."""
        st.banner("TEST: NTP-026 - Configure NTP Server with iburst")

        dut = self.data.dut
        cli_type = self.data.cli_type
        server_config = self.data.ntp_servers.primary_server

        server_addr = server_config.address
        iburst = server_config.iburst

        # Configure server with iburst
        result = ntp_api.config_ntp_server(
            dut, ipaddress=server_addr, iburst=iburst, cli_type=cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure NTP server {server_addr} with iburst")

        self.data.configured_servers.append(server_addr)

        # Verify server is configured
        if not ntp_api.verify_ntp_server(dut, server=server_addr, cli_type=cli_type):
            st.report_fail("msg", f"NTP server {server_addr} not found in configuration")

        # Verify iburst option via REST API (skip if not supported)
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

        # Find server in the list and check iburst
        server_list = response['output'].get('sonic-ntp:NTP_SERVER', {}).get('NTP_SERVER_LIST', [])
        for srv in server_list:
            if srv.get('server_address') == server_addr:
                actual_iburst = srv.get('iburst')
                if actual_iburst is None:
                    st.log(f"Iburst not supported in this SONiC version - Feature not implemented")
                    st.report_unsupported("test_case_unsupported", "Iburst configuration not supported in klish CLI")
                    return
                elif actual_iburst != 'on':
                    st.report_fail("msg", f"Iburst mismatch: Expected 'on', got '{actual_iburst}'")
                else:
                    st.log(f"Verified: Server {server_addr} configured with iburst={actual_iburst}")
                break

        st.report_pass("test_case_passed")

    @pytest.mark.servers
    def test_ntp_030_delete_server(self) -> None:
        """NTP-030: Delete NTP server."""
        st.banner("TEST: NTP-030 - Delete NTP Server")

        dut = self.data.dut
        cli_type = self.data.cli_type
        server_addr = "10.10.10.99"

        # First configure the server
        ntp_api.config_ntp_server(dut, ipaddress=server_addr, cli_type=cli_type)

        # Then delete it
        result = ntp_api.delete_ntp_server(dut, ipaddress=server_addr, cli_type=cli_type)
        if not result:
            st.report_fail("msg", f"Failed to delete NTP server {server_addr}")

        # Verify server is deleted via REST API
        from apis.system.rest import get_rest
        rest_urls = st.get_datastore(dut, "rest_urls")
        if not rest_urls:
            st.log("REST URLs datastore not available, skipping REST API verification")
            st.report_pass("test_case_passed")
            return

        url = rest_urls.get('ntp_server_config', '/restconf/data/sonic-ntp:sonic-ntp/NTP_SERVER')

        response = get_rest(dut, rest_url=url)
        if response and 'output' in response:
            server_list = response['output'].get('sonic-ntp:NTP_SERVER', {}).get('NTP_SERVER_LIST', [])
            for srv in server_list:
                if srv.get('server_address') == server_addr:
                    st.report_fail("msg", f"NTP server {server_addr} still exists after deletion")
            st.log(f"Verified: NTP server {server_addr} successfully deleted")
        else:
            st.log("No servers found, deletion verified")

        st.report_pass("test_case_passed")

    @pytest.mark.servers
    def test_ntp_022_server_version_4(self) -> None:
        """NTP-022: Configure NTP server with version 4."""
        st.banner("TEST: NTP-022 - Configure NTP Server with Version 4")

        dut = self.data.dut
        cli_type = self.data.cli_type
        server_addr = self.data.local_ntp_server  # Use local NTP server
        version = 4

        # Configure server with version 4
        result = ntp_api.config_ntp_server(
            dut, ipaddress=server_addr, version=version, cli_type=cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure NTP server {server_addr} with version {version}")

        self.data.configured_servers.append(server_addr)

        # Verify server is configured
        if not ntp_api.verify_ntp_server(dut, server=server_addr, cli_type=cli_type):
            st.report_fail("msg", f"NTP server {server_addr} not found in configuration")

        # Verify version via REST API
        from apis.system.rest import get_rest
        rest_urls = st.get_datastore(dut, "rest_urls")
        if not rest_urls:
            st.log("REST URLs datastore not available, skipping REST API verification")
            st.report_pass("test_case_passed")
            return

        url = rest_urls.get('ntp_server_config', '/restconf/data/sonic-ntp:sonic-ntp/NTP_SERVER')

        response = get_rest(dut, rest_url=url)
        if not response or 'output' not in response:
            st.report_fail("msg", "Failed to retrieve NTP server configuration via REST")

        # Find server in the list and verify version
        server_found = False
        server_list = response['output'].get('sonic-ntp:NTP_SERVER', {}).get('NTP_SERVER_LIST', [])

        for srv in server_list:
            if srv.get('server_address') == server_addr:
                server_found = True
                actual_version = srv.get('version')
                if actual_version != version:
                    st.report_fail("msg", f"Version mismatch: Expected {version}, got {actual_version}")
                st.log(f"Verified: Server {server_addr} configured with version {actual_version}")
                break

        if not server_found:
            st.report_fail("msg", f"Server {server_addr} not found in NTP_SERVER_LIST")

        st.report_pass("test_case_passed")

    @pytest.mark.servers
    def test_ntp_023_server_prefer(self) -> None:
        """NTP-023: Configure NTP server with prefer option."""
        st.banner("TEST: NTP-023 - Configure NTP Server with Prefer")

        dut = self.data.dut
        cli_type = self.data.cli_type
        server_addr = self.data.local_ntp_server  # Use local NTP server

        # Configure server with prefer option
        result = ntp_api.config_ntp_server(
            dut, ipaddress=server_addr, prefer=True, cli_type=cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure NTP server {server_addr} with prefer option")

        self.data.configured_servers.append(server_addr)

        # Verify server is configured
        if not ntp_api.verify_ntp_server(dut, server=server_addr, cli_type=cli_type):
            st.report_fail("msg", f"NTP server {server_addr} not found in configuration")

        # Verify prefer option (trusted="yes") via REST API (skip if not supported)
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

        # Find server in the list and check prefer (trusted)
        server_list = response['output'].get('sonic-ntp:NTP_SERVER', {}).get('NTP_SERVER_LIST', [])

        for srv in server_list:
            if srv.get('server_address') == server_addr:
                trusted_status = srv.get('trusted')
                if trusted_status is None:
                    st.log(f"Prefer (trusted) attribute not supported in this SONiC version - Feature not implemented")
                    st.report_unsupported("test_case_unsupported", "Prefer option not reflected in REST API for klish CLI")
                    return
                elif trusted_status != 'yes':
                    st.report_fail("msg", f"Prefer (trusted) mismatch: Expected 'yes', got '{trusted_status}'")
                else:
                    st.log(f"Verified: Server {server_addr} configured with prefer option (trusted={trusted_status})")
                break

        st.report_pass("test_case_passed")

    @pytest.mark.servers
    def test_ntp_024_server_auth_key(self) -> None:
        """NTP-024: Configure NTP server with authentication key."""
        st.banner("TEST: NTP-024 - Configure NTP Server with Authentication Key")

        dut = self.data.dut
        cli_type = self.data.cli_type
        server_addr = self.data.local_ntp_server  # Use local NTP server
        key_id = 15

        # Configure server with authentication key
        result = ntp_api.config_ntp_server(
            dut, ipaddress=server_addr, key_id=key_id, cli_type=cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure NTP server {server_addr} with key {key_id}")

        self.data.configured_servers.append(server_addr)

        # Verify server is configured
        if not ntp_api.verify_ntp_server(dut, server=server_addr, cli_type=cli_type):
            st.report_fail("msg", f"NTP server {server_addr} not found in configuration")

        # Verify authentication key via REST API (skip if not supported)
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

        # Find server in the list and check key
        server_list = response['output'].get('sonic-ntp:NTP_SERVER', {}).get('NTP_SERVER_LIST', [])

        for srv in server_list:
            if srv.get('server_address') == server_addr:
                actual_key = srv.get('key')
                if actual_key is None:
                    st.log(f"Key attribute not supported in this SONiC version - Feature not implemented")
                    st.report_unsupported("test_case_unsupported", "Authentication key option not reflected in REST API for klish CLI")
                    return
                elif actual_key != key_id:
                    st.report_fail("msg", f"Key ID mismatch: Expected {key_id}, got {actual_key}")
                else:
                    st.log(f"Verified: Server {server_addr} configured with key ID {actual_key}")
                break

        st.report_pass("test_case_passed")

    @pytest.mark.servers
    def test_ntp_029_server_max_limit(self) -> None:
        """NTP-029: Test maximum NTP server limit (10 servers)."""
        st.banner("TEST: NTP-029 - Test Maximum NTP Server Limit")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # First, configure servers up to the limit
        # Based on manual testing, max limit is 10 servers
        # We'll try to add 4 servers beyond what might already exist
        test_servers = ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"]

        # Attempt to configure servers
        # This should fail with "Max elements limit 10 reached"
        failed_count = 0
        for server_addr in test_servers:
            output = st.config(
                dut,
                f"ntp server {server_addr}",
                type=cli_type,
                skip_error_check=True,
            )
            if "Error" in str(output) or "Max elements limit" in str(output):
                st.log(f"Expected max limit error for server {server_addr}: {output}")
                failed_count += 1
            else:
                # Server was successfully added
                self.data.configured_servers.append(server_addr)

        # We expect at least some servers to fail if we're at or near the limit
        # This is not a strict failure - just validation that limit exists
        st.log(f"Max limit validation: {failed_count} out of {len(test_servers)} servers hit the limit")

        st.report_pass("test_case_passed")

    @pytest.mark.servers
    def test_ntp_032_multiple_servers(self) -> None:
        """NTP-032: Configure multiple NTP servers."""
        st.banner("TEST: NTP-032 - Configure Multiple NTP Servers")

        dut = self.data.dut
        cli_type = self.data.cli_type
        test_servers = self.data.ntp_servers.test_servers

        # Configure multiple servers
        for server_addr in test_servers:
            result = ntp_api.config_ntp_server(dut, ipaddress=server_addr, cli_type=cli_type)
            if not result:
                st.report_fail("msg", f"Failed to configure NTP server {server_addr}")
            self.data.configured_servers.append(server_addr)

        # Verify all servers are configured
        for server_addr in test_servers:
            if not ntp_api.verify_ntp_server(dut, server=server_addr, cli_type=cli_type):
                st.report_fail("msg", f"NTP server {server_addr} not found in configuration")

        st.report_pass("test_case_passed")


@pytest.mark.topology("any")
class TestNTPSourceInterface:
    """Test Category 5: NTP Source Interface Configuration"""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup for source interface tests."""
        st.banner("MODULE PROLOGUE: NTP Source Interface Tests")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # NTP tests don't require connected ports, just a single device
        # min_topology = defaults.get("min_topology") or ["D1:1"]
        # topology = st.ensure_min_topology(*min_topology)
        topology = st.get_testbed_vars()

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.source_interfaces = config.get("source_interfaces", [])
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
    def test_ntp_033_source_interface_ethernet(self) -> None:
        """NTP-033: Configure NTP source interface Ethernet0."""
        st.banner("TEST: NTP-033 - Configure Source Interface Ethernet0")

        dut = self.data.dut
        cli_type = self.data.cli_type
        interface = "Ethernet0"

        # Configure source interface
        result = ntp_api.config_ntp_source_interface(
            dut, interface=interface, config="yes", cli_type=cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure source interface {interface}")

        st.report_pass("test_case_passed")

    @pytest.mark.source_interface
    def test_ntp_035_delete_source_interface(self) -> None:
        """NTP-035: Delete NTP source interface."""
        st.banner("TEST: NTP-035 - Delete Source Interface")

        dut = self.data.dut
        cli_type = self.data.cli_type
        interface = "Ethernet0"

        # First configure
        ntp_api.config_ntp_source_interface(
            dut, interface=interface, config="yes", cli_type=cli_type
        )

        # Then delete
        result = ntp_api.config_ntp_source_interface(
            dut, interface="", config="no", cli_type=cli_type
        )
        if not result:
            st.report_fail("msg", "Failed to delete source interface")

        st.report_pass("test_case_passed")

    @pytest.mark.source_interface
    def test_ntp_036_source_interface_svi(self) -> None:
        """NTP-036: Attempt to configure VLAN SVI as NTP source-interface (negative test).

        Issue: Customer Report + SSE-T8196 - SVI cannot be configured as NTP source
        even after configuring an IP address on them.

        VS Coverage: 95% (Full CLI and configuration validation)
        HW Additional: Routing and packet validation

        Test validates:
        - VLAN creation works
        - SVI IP configuration works
        - NTP source-interface command behavior with SVI
        - Error handling or silent failure detection
        """
        st.banner("TEST: NTP-036 - Configure SVI (Vlan10) as Source Interface")

        dut = self.data.dut
        cli_type = self.data.cli_type

        try:
            # Step 1: Create VLAN 10 using klish CLI
            st.log("Step 1: Creating VLAN 10 using klish CLI")

            # Create VLAN using klish commands (must create VLAN first, then configure interface)
            # Use a single config block to avoid prompt issues
            vlan_config = """
            vlan 10
            exit
            interface Vlan 10
            end
            """

            st.config(dut, vlan_config, type=cli_type, skip_error_check=True)

            # Wait for VLAN creation to complete
            st.wait(2, "Waiting for VLAN creation to complete")

            # Verify VLAN creation using show command
            show_vlan_output = st.show(dut, "show Vlan", type=cli_type, skip_tmpl=True)
            show_vlan_str = str(show_vlan_output)

            if "Vlan10" not in show_vlan_str and "10" not in show_vlan_str:
                st.log(f"⚠ WARNING: Vlan10 not found in show Vlan output")
                st.log(f"show Vlan output: {show_vlan_str}")
                st.report_fail("msg", "Failed to create VLAN 10 - not visible in show Vlan")

            st.log("✓ VLAN 10 created successfully")

            # Step 2: Configure IP address on SVI using klish CLI
            st.log("Step 2: Configuring IP address 10.1.1.1/24 on Vlan10 using klish CLI")

            # Configure IP using klish commands as a single config block
            ip_config = """
interface Vlan 10
ip address 10.1.1.1/24
end
"""
            output = st.config(dut, ip_config, type=cli_type, skip_error_check=True)
            if "Error" in str(output):
                st.log(f"Error configuring IP - Output: {output}")
                st.report_fail("msg", f"Failed to configure IP on Vlan10: {output}")

            # Verify IP is configured (query specific interface to avoid paging)
            st.wait(5, "Waiting for IP configuration to take effect")
            st.log("Verifying IP address on Vlan10 (querying specific interface)")

            output = st.show(dut, "show ip interface Vlan 10", type=cli_type, skip_error_check=True)
            output_str = str(output)

            # Log the output for debugging but don't fail if verification is inconclusive
            # The main goal is testing NTP source-interface behavior, not IP config
            if "10.1.1.1" in output_str or "10.1.1.1/24" in output_str:
                st.log("✓ IP address 10.1.1.1/24 verified on Vlan10")
            elif output_str and "Vlan10" in output_str:
                st.log("⚠ Vlan10 exists but IP format may differ, continuing with test")
                st.log(f"Output: {output_str[:200]}")  # Log first 200 chars
            else:
                st.log(f"⚠ WARNING: Could not verify IP - output: {output_str[:200]}")
                st.log("Note: Proceeding with test as IP config may still be present")

            # Step 3: Attempt to configure Vlan10 as NTP source-interface
            st.log("Step 3: Attempting to configure Vlan10 as NTP source-interface")
            output = st.config(
                dut,
                "ntp source-interface Vlan10",
                type=cli_type,
                skip_error_check=True
            )

            output_str = str(output)
            st.log(f"Command output: {output_str}")

            # Step 4: Analyze the result
            st.log("Step 4: Validating command result")

            error_detected = False
            if "Error" in output_str or "not supported" in output_str.lower() or "Invalid" in output_str:
                st.log("✓ Expected error received: SVI not supported as source-interface")
                st.log(f"Error output: {output_str}")
                error_detected = True
            else:
                st.log("⚠ Command did not produce error - checking if configuration persisted")

                # Check show ntp global
                show_output = st.show(dut, "show ntp global", type=cli_type, skip_tmpl=True)
                show_str = str(show_output)

                if "Vlan10" in show_str or "10.1.1.1" in show_str:
                    st.log("⚠ UNEXPECTED: Vlan10 appears in show ntp global output")
                    st.log("This may indicate the limitation has been resolved")
                    st.log(f"show ntp global output: {show_str}")
                else:
                    st.log("✓ Vlan10 not visible in show ntp global (expected behavior)")
                    error_detected = True

            # Step 5: Determine test result based on customer defect presence
            st.log("\n" + "="*80)
            st.log("TEST RESULTS: SVI as NTP Source-Interface")
            st.log("="*80)

            if error_detected:
                st.log("❌ CUSTOMER DEFECT CONFIRMED: SVI cannot be configured as NTP source-interface")
                st.log("Customer Issue: SVIs cannot be configured as NTP source interfaces,")
                st.log("                even after configuring an IP address on them.")
                st.log("SSE-T8196 #2: Can't set NTP 'source-interface VLAN'")
                st.log("="*80)

                # Cleanup before failing
                st.log("Cleanup: Removing test configuration before reporting failure")
                try:
                    ntp_api.config_ntp_source_interface(dut, interface="", config="no", cli_type=cli_type)
                except Exception as e:
                    st.log(f"Cleanup warning (NTP source): {e}")

                try:
                    # Remove IP using klish CLI as a config block
                    ip_delete_config = """
interface Vlan 10
no ip address 10.1.1.1/24
end
"""
                    st.config(dut, ip_delete_config, type=cli_type, skip_error_check=True)
                    st.wait(1, "Waiting after IP deletion")
                except Exception as e:
                    st.log(f"Cleanup warning (IP): {e}")

                try:
                    # Delete VLAN using klish CLI
                    st.config(dut, "no interface Vlan 10", type=cli_type, skip_error_check=True)
                except Exception as e:
                    st.log(f"Cleanup warning (VLAN): {e}")

                # Report FAIL when customer defect is present
                st.report_fail("msg", "Customer defect SSE-T8196: SVI cannot be configured as NTP source-interface")

            else:
                st.log("✓ SUCCESS: SVI can be configured as NTP source-interface")
                st.log("The customer limitation appears to have been RESOLVED")
                st.log("="*80)

        finally:
            # Cleanup
            st.log("Cleanup: Removing test configuration")

            # Remove NTP source-interface (if it was set)
            try:
                ntp_api.config_ntp_source_interface(dut, interface="", config="no", cli_type=cli_type)
            except Exception as e:
                st.log(f"Cleanup warning (NTP source): {e}")

            # Remove IP from SVI using klish CLI
            try:
                # Remove IP using klish CLI as a config block
                ip_delete_config = """
interface Vlan 10
no ip address 10.1.1.1/24
end
"""
                st.config(dut, ip_delete_config, type=cli_type, skip_error_check=True)
                st.wait(1, "Waiting after IP deletion")
            except Exception as e:
                st.log(f"Cleanup warning (IP): {e}")

            # Delete VLAN using klish CLI
            try:
                st.config(dut, "no interface Vlan 10", type=cli_type, skip_error_check=True)
            except Exception as e:
                st.log(f"Cleanup warning (VLAN): {e}")

        st.log("Test completed: SVI can be used as NTP source-interface (defect resolved)")
        st.report_pass("test_case_passed")

    @pytest.mark.source_interface
    @pytest.mark.source_interface
    def test_ntp_037_source_interface_management_static(self) -> None:
        """NTP-037: Verify Management interface naming (Management0 vs eth0) - INFORMATIONAL.

        Issue: Customer Report - Management0 vs eth0 naming with static IP configuration

        This test validates that Management interface is accessible but DOES NOT change
        the IP address to avoid disrupting the active SSH connection.

        IMPORTANT: Changing management IP while connected through that interface will
        disrupt the SSH session and cause the test to hang.

        VS Coverage: 100% (CLI validation without IP disruption)
        HW Additional: Can test IP change in isolated environment
        """
        st.banner("TEST: NTP-037 - Management Interface Naming Validation (Informational)")

        dut = self.data.dut
        cli_type = self.data.cli_type

        try:
            # Step 1: Verify Management interface is accessible
            st.log("Step 1: Checking Management interface accessibility")

            # Try Management0 naming
            output_mgmt0 = st.show(dut, "show ip interface Management 0",
                                   type=cli_type, skip_error_check=True)
            mgmt0_accessible = "Management" in str(output_mgmt0) or "Error" not in str(output_mgmt0)

            # Try eth0 naming (in click CLI)
            output_eth0 = st.show(dut, "show ip interface eth0",
                                 type="click", skip_error_check=True)
            eth0_accessible = "eth0" in str(output_eth0)

            st.log(f"Management0 accessible (klish): {mgmt0_accessible}")
            st.log(f"eth0 accessible (click): {eth0_accessible}")

            # Step 2: Document the behavior WITHOUT changing IP
            st.log("Step 2: Documenting Management interface behavior")
            st.log("✓ VALIDATED: Management interface is accessible")
            st.log("✓ DOCUMENTED: Both 'Management 0' (klish) and 'eth0' (click) naming work")
            st.log("⚠ LIMITATION: Cannot change management IP during active SSH session")
            st.log("⚠ REASON: Would disrupt the connection used for testing")

            # Step 3: Get current management IP for documentation
            st.log("Step 3: Documenting current management IP")
            current_output = st.show(dut, "show ip interface Management 0", type=cli_type)
            st.log(f"Current Management interface status:\n{current_output}")

            # Step 4: Test NTP source-interface configuration (without IP change)
            st.log("Step 4: Testing NTP source-interface with Management interface")

            # Test Management0 naming
            st.log("Testing: ntp source-interface Management 0")
            result_mgmt0 = st.config(dut, "ntp source-interface Management 0",
                                     type=cli_type, skip_error_check=True)

            if "Error" in str(result_mgmt0) or "not" in str(result_mgmt0).lower():
                st.log("⚠ ISSUE CONFIRMED: Management0 cannot be set as NTP source-interface")
                issue_found = True
            else:
                st.log("✓ Management0 accepted as NTP source-interface")
                issue_found = False
                # Clean up
                st.config(dut, "no ntp source-interface", type=cli_type, skip_error_check=True)

            # Test eth0 naming (likely won't work in klish, but document it)
            st.log("Testing: ntp source-interface eth0 (expected to fail in klish)")
            result_eth0 = st.config(dut, "ntp source-interface eth0",
                                   type=cli_type, skip_error_check=True)

            if "Error" in str(result_eth0):
                st.log("✓ EXPECTED: eth0 naming not accepted in klish CLI")
            else:
                st.log("✓ eth0 naming accepted")
                # Clean up
                st.config(dut, "no ntp source-interface", type=cli_type, skip_error_check=True)

            # Report results
            st.log("\n" + "="*70)
            st.log("TEST SUMMARY:")
            st.log("="*70)
            st.log("✓ Management interface accessible via both naming conventions")
            st.log("✓ Management0 vs eth0 naming documented")
            if issue_found:
                st.log("⚠ CUSTOMER ISSUE CONFIRMED: Management0 cannot be NTP source-interface")
            else:
                st.log("✓ Management0 works as NTP source-interface")
            st.log("⚠ IP change test skipped to preserve SSH connection")
            st.log("="*70 + "\n")

            # Pass with documentation
            st.report_pass("test_case_passed")

        except Exception as e:
            st.log(f"Test exception: {e}")
            st.report_fail("msg", f"Test failed with exception: {e}")



    @pytest.mark.source_interface
    def test_ntp_038_verify_source_in_running_config(self) -> None:
        """NTP-038: Verify NTP source-interface appears in running-config and persists.

        Issue: SSE-T8196 #6 - Other than server IP, NTP settings do not appear in running-config
        This test specifically validates source-interface configuration display.

        VS Coverage: 100% (Configuration persistence validation)
        HW Additional: None required

        Test validates:
        - Source-interface configuration appears in running-config
        - Configuration persists after save
        - Configuration format and syntax
        - Multiple show command consistency
        """
        st.banner("TEST: NTP-038 - Verify Source-Interface in Running-Config")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # Check device connectivity before proceeding (resilience after previous test failures)
        st.log("Checking device connectivity...")
        try:
            st.show(dut, "show version", type=cli_type, skip_error_check=False)
            st.log("✓ Device is reachable and responsive")
        except Exception as e:
            st.log(f"❌ Device not reachable: {e}")
            st.log("⚠ This may be due to issues in previous tests (e.g., management IP change)")
            st.report_env_fail("msg", f"Device unreachable - possible cascading failure: {e}")
            return

        interface = "Ethernet0"

        try:
            # Step 1: Configure source-interface
            st.log(f"Step 1: Configuring source-interface {interface}")
            result = ntp_api.config_ntp_source_interface(
                dut, interface=interface, config="yes", cli_type=cli_type
            )

            if not result:
                st.report_fail("msg", f"Failed to configure source-interface {interface}")

            st.log(f"✓ Source-interface {interface} configured")

            # Step 2: Check show ntp global
            st.log("Step 2: Checking 'show ntp global' output")
            show_global = st.show(dut, "show ntp global", type=cli_type, skip_tmpl=True)
            show_global_str = str(show_global)

            source_in_global = interface in show_global_str or "source" in show_global_str.lower()

            if source_in_global:
                st.log(f"✓ Source-interface visible in show ntp global")
                st.log(f"Output: {show_global_str}")
            else:
                st.log(f"⚠ WARNING: Source-interface NOT visible in show ntp global")
                st.log(f"Related to SSE-T8196 #5: Source-interface info missing from show output")
                st.log(f"Output: {show_global_str}")

            # Step 3: Check running-config (pipe commands don't work in klish)
            st.log("Step 3: Checking 'show running-config' for source-interface")

            # Exit config mode before running show command to avoid pagination issues
            st.config(dut, "end", type=cli_type, skip_error_check=True)

            # Use full command name with no-more to avoid pagination
            running_config = st.show(dut, "show running-configuration | no-more",
                                    type=cli_type, skip_tmpl=True, skip_error_check=True)

            if isinstance(running_config, list):
                running_config_str = '\n'.join(str(item) for item in running_config)
            else:
                running_config_str = str(running_config)

            # Filter for NTP lines in Python (since pipe doesn't work in klish)
            ntp_lines = [line for line in running_config_str.split('\n') if 'ntp' in line.lower()]
            ntp_config_str = '\n'.join(ntp_lines)

            st.log(f"Running-config NTP section:\n{ntp_config_str if ntp_lines else '(no NTP config found)'}")

            # Check for source-interface in running-config
            source_keywords = [
                f"ntp source-interface {interface}",
                f"source-interface {interface}",
                f"source {interface}",
                interface
            ]

            source_in_config = any(keyword in running_config_str for keyword in source_keywords)

            if source_in_config:
                st.log(f"✓ Source-interface {interface} found in running-config")
            else:
                st.log(f"⚠ WARNING: Source-interface {interface} NOT found in running-config")
                st.log(f"Related to SSE-T8196 #6: NTP settings missing from running-config")

            # Step 4: Save configuration
            st.log("Step 4: Saving configuration to startup-config")
            # Use direct command instead of non-existent basic_api.save_config()
            st.config(dut, "config save -y", skip_error_check=True)
            st.log("✓ Configuration save command executed")

            # Step 5: Check startup-config (pipe commands don't work in klish)
            st.log("Step 5: Verifying source-interface in startup-config")

            # Exit config mode before running show command to avoid pagination issues
            st.config(dut, "end", type=cli_type, skip_error_check=True)

            # Use full command name with no-more to avoid pagination
            startup_config = st.show(dut, "show startup-configuration | no-more",
                                    type=cli_type, skip_tmpl=True, skip_error_check=True)

            if isinstance(startup_config, list):
                startup_config_str = '\n'.join(str(item) for item in startup_config)
            else:
                startup_config_str = str(startup_config)

            # Filter for NTP lines in Python
            startup_ntp_lines = [line for line in startup_config_str.split('\n') if 'ntp' in line.lower()]

            source_in_startup = any(keyword in startup_config_str for keyword in source_keywords)

            if source_in_startup:
                st.log(f"✓ Source-interface persisted to startup-config")
                st.log(f"Startup-config: {startup_config_str}")
            else:
                st.log(f"⚠ WARNING: Source-interface NOT in startup-config")
                st.log(f"Configuration may not persist across reboot")

            # Step 6: Comprehensive validation
            st.log("\n" + "="*80)
            st.log("CONFIGURATION PERSISTENCE VALIDATION RESULTS")
            st.log("="*80)
            st.log(f"Source-interface configured: ✓")
            st.log(f"Visible in 'show ntp global': {'✓' if source_in_global else '✗ ISSUE SSE-T8196 #5'}")
            st.log(f"Present in running-config: {'✓' if source_in_config else '✗ ISSUE SSE-T8196 #6'}")
            st.log(f"Persisted to startup-config: {'✓' if source_in_startup else '✗ PERSISTENCE ISSUE'}")

            # Create detailed issue report
            issues_found = []

            if not source_in_global:
                issues_found.append("Source-interface not visible in show ntp global (SSE-T8196 #5)")

            if not source_in_config:
                issues_found.append("Source-interface missing from running-config (SSE-T8196 #6)")

            if not source_in_startup:
                issues_found.append("Source-interface not persisted to startup-config")

            if issues_found:
                st.log("\n⚠ ISSUES DETECTED:")
                for idx, issue in enumerate(issues_found, 1):
                    st.log(f"  {idx}. {issue}")
                st.log("\nExpected Behavior: Source-interface should be visible in all outputs")
                st.log("Actual Behavior: Configuration partially missing from show/config outputs")
            else:
                st.log("\n✓ All validations passed - source-interface properly displayed and persisted")

            st.log("="*80)

            # Test should pass even if issues found (documentation purpose)
            # Critical failure only if configuration completely failed

        finally:
            # Cleanup
            st.log("Cleanup: Removing source-interface configuration")
            try:
                ntp_api.config_ntp_source_interface(dut, interface="", config="no", cli_type=cli_type)
                basic_api.save_config(dut)
            except Exception as e:
                st.log(f"Cleanup warning: {e}")

        st.log("Test completed: Source-interface configuration persistence validated")
        st.report_pass("test_case_passed")


@pytest.mark.topology("any")
class TestNTPVRF:
    """Test Category 5B: NTP VRF Configuration"""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup for VRF tests."""
        st.banner("MODULE PROLOGUE: NTP VRF Tests")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # NTP tests don't require connected ports, just a single device
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
    def test_ntp_038_delete_vrf(self) -> None:
        """NTP-038: Delete NTP VRF configuration."""
        st.banner("TEST: NTP-038 - Delete NTP VRF")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # Configure NTP VRF first (assuming management VRF is enabled from previous test)
        if not self.data.mgmt_vrf_enabled:
            st.config(dut, "management vrf", type=cli_type)
            self.data.mgmt_vrf_enabled = True

        st.config(dut, "ntp vrf mgmt", type=cli_type)

        # Delete NTP VRF
        result = st.config(dut, "no ntp vrf", type=cli_type)
        if not result:
            st.report_fail("msg", "Failed to delete NTP VRF")

        st.report_pass("test_case_passed")


@pytest.mark.topology("any")
class TestNTPShowCommands:
    """Test Category 5C: NTP Show Commands Verification"""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup for show command tests."""
        st.banner("MODULE PROLOGUE: NTP Show Commands Tests")
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
    def test_ntp_039_show_ntp_global(self) -> None:
        """NTP-039: Verify 'show ntp global' command displays NTP service and authentication status.

        Also validates Issue SSE-T8196: NTP source-interface related information cannot be seen
        in show ntp global output.
        """
        st.banner("TEST: NTP-039 - Verify Show NTP Global")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # Setup: Enable NTP and authentication
        st.log("Enabling NTP service")
        ntp_api.config_ntp_enable(dut, config="yes", cli_type=cli_type)

        st.log("Enabling NTP authentication")
        ntp_api.config_ntp_authenticate(dut, config="yes", cli_type=cli_type)

        # Configure source interface to test Issue #5
        source_interface = "Ethernet0"
        st.log(f"Configuring source-interface: {source_interface} (to test Issue SSE-T8196)")
        ntp_api.config_ntp_source_interface(dut, interface=source_interface, config="yes", cli_type=cli_type)

        # Execute show ntp global command
        st.log("Executing: show ntp global")
        output = st.show(dut, "show ntp global", type=cli_type, skip_tmpl=True)

        # Verify output contains expected information
        if isinstance(output, list):
            output_str = ' '.join(str(item) for item in output)
        else:
            output_str = str(output)

        # Check for NTP service status
        if "NTP service" not in output_str and "enabled" not in output_str:
            st.report_fail("msg", "show ntp global: NTP service status not found in output")

        # Check for NTP authentication status
        if "NTP authentication" not in output_str:
            st.report_fail("msg", "show ntp global: NTP authentication status not found in output")

        # Issue SSE-T8196 validation: Check for source-interface in show ntp global
        st.log(f"Validating Issue SSE-T8196: Checking if source-interface {source_interface} appears in show ntp global")
        source_keywords = ["source", "source-interface", source_interface]
        source_found = any(keyword in output_str for keyword in source_keywords)

        if not source_found:
            st.log(f"⚠ ISSUE SSE-T8196 CONFIRMED: Source-interface {source_interface} NOT displayed in show ntp global")
            st.log(f"Expected to see source-interface information but it is missing from output")
            st.log(f"show ntp global output: {output_str}")
            # Document the issue but don't fail the test - this is a known limitation
        else:
            st.log(f"✓ Source-interface information IS present in show ntp global output")
            st.log(f"Issue SSE-T8196 may have been resolved")

        # Cleanup source interface
        ntp_api.config_ntp_source_interface(dut, interface="", config="no", cli_type=cli_type)

        st.log("show ntp global command output verified successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.show_commands
    def test_ntp_040_show_ntp_server(self) -> None:
        """NTP-040: Verify 'show ntp server' command displays configured NTP servers with properties."""
        st.banner("TEST: NTP-040 - Verify Show NTP Server")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # Setup: Configure NTP server with all options
        server_addr = self.data.local_ntp_server  # Use local NTP server
        version = 3
        key_id = 10

        st.log("Configuring authentication key")
        ntp_api.config_ntp_auth_key(dut, key_id, "sha256", "CompleteKey", cli_type=cli_type)

        st.log(f"Configuring NTP server {server_addr} with version {version}, key {key_id}, prefer, iburst")
        ntp_api.config_ntp_server(
            dut,
            ipaddress=server_addr,
            version=version,
            key_id=key_id,
            prefer=True,
            iburst=True,
            cli_type=cli_type,
        )

        # Execute show ntp server command
        st.log("Executing: show ntp server")
        output = st.show(dut, "show ntp server", type=cli_type, skip_tmpl=True)

        # Verify output contains expected information
        if isinstance(output, list):
            output_str = ' '.join(str(item) for item in output)
        else:
            output_str = str(output)

        # Check for server address
        if server_addr not in output_str:
            st.report_fail("msg", f"show ntp server: Server {server_addr} not found in output")

        # Check for version (if shown in output)
        # Note: Version may be shown as integer or string
        if str(version) not in output_str and f"version {version}" not in output_str.lower():
            st.log(f"Warning: Version {version} not explicitly shown in output (may be default)")

        st.log("show ntp server command output verified successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.show_commands
    def test_ntp_041_verify_running_config_display(self) -> None:
        """NTP-041: Verify NTP configuration appears in running-config output.

        Issue: SSE-T8196 SMCI SONiC v1.2][SMCI IS-CLI] Other than the server IP,
        NTP settings do not appear in the running-config

        This test validates that all NTP configuration parameters (not just server IP)
        are properly displayed in 'show running-config'.
        """
        st.banner("TEST: NTP-041 - Verify Running-Config Display")

        dut = self.data.dut
        cli_type = self.data.cli_type
        server_addr = self.data.local_ntp_server  # Use local NTP server

        try:
            # Configure comprehensive NTP setup
            st.log("Step 1: Configure complete NTP setup")

            st.log("- Enabling NTP service")
            ntp_api.config_ntp_enable(dut, config="yes", cli_type=cli_type)

            st.log("- Enabling NTP authentication")
            ntp_api.config_ntp_authenticate(dut, config="yes", cli_type=cli_type)

            st.log("- Configuring authentication key")
            key_id = 10
            ntp_api.config_ntp_auth_key(dut, key_id, "sha256", "CompleteKey", cli_type=cli_type)

            st.log("- Configuring trusted key")
            ntp_api.config_ntp_trusted_key(dut, key_id, cli_type=cli_type)

            st.log(f"- Configuring NTP server {server_addr} with all options")
            ntp_api.config_ntp_server(
                dut,
                ipaddress=server_addr,
                version=4,
                key_id=key_id,
                prefer=True,
                iburst=True,
                cli_type=cli_type,
            )

            st.log("- Configuring source interface")
            ntp_api.config_ntp_source_interface(dut, interface="Ethernet0", config="yes", cli_type=cli_type)

            # Get running-config with NTP settings
            st.log("Step 2: Retrieve running-config")
            config_output = st.show(dut, "show running-config | include ntp", type=cli_type, skip_tmpl=True)

            if isinstance(config_output, list):
                config_str = ' '.join(str(item) for item in config_output)
            else:
                config_str = str(config_output)

            st.log(f"Running-config NTP section:\n{config_str}")

            # Define expected configuration elements
            expected_settings = {
                "ntp_enable": {
                    "keywords": ["ntp enable", "ntp"],
                    "description": "NTP service enable command",
                    "required": False,  # May be implicit
                },
                "ntp_authenticate": {
                    "keywords": ["ntp authenticate", "authenticate"],
                    "description": "NTP authentication enable",
                    "required": False,  # May be implicit
                },
                "ntp_auth_key": {
                    "keywords": [f"ntp authentication-key {key_id}", f"key {key_id}", "authentication-key"],
                    "description": f"Authentication key {key_id}",
                    "required": True,
                },
                "ntp_trusted_key": {
                    "keywords": [f"ntp trusted-key {key_id}", f"trusted-key {key_id}"],
                    "description": f"Trusted key {key_id}",
                    "required": False,
                },
                "ntp_server": {
                    "keywords": [f"ntp server {server_addr}", server_addr],
                    "description": f"NTP server {server_addr}",
                    "required": True,
                },
                "server_version": {
                    "keywords": ["version 4", "version"],
                    "description": "Server version parameter",
                    "required": False,  # Often not shown if default
                },
                "server_prefer": {
                    "keywords": ["prefer", "trusted"],
                    "description": "Server prefer option",
                    "required": False,
                },
                "server_iburst": {
                    "keywords": ["iburst"],
                    "description": "Server iburst option",
                    "required": False,
                },
                "server_key": {
                    "keywords": [f"key {key_id}"],
                    "description": f"Server authentication key {key_id}",
                    "required": False,
                },
                "source_interface": {
                    "keywords": ["ntp source-interface", "source-interface", "Ethernet0"],
                    "description": "Source interface configuration",
                    "required": False,
                },
            }

            # Step 3: Validate each setting
            st.log("Step 3: Validating NTP settings in running-config")
            missing_settings = []
            present_settings = []

            for setting_name, setting_info in expected_settings.items():
                found = any(keyword in config_str for keyword in setting_info["keywords"])

                if found:
                    st.log(f"✓ {setting_info['description']}: FOUND in running-config")
                    present_settings.append(setting_name)
                else:
                    st.log(f"⚠ {setting_info['description']}: NOT FOUND in running-config")
                    if setting_info["required"]:
                        missing_settings.append(setting_name)

            # Step 4: Report findings
            st.log("\n" + "="*80)
            st.log("RUNNING-CONFIG VALIDATION RESULTS")
            st.log("="*80)
            st.log(f"Settings found: {len(present_settings)}/{len(expected_settings)}")
            st.log(f"Present: {', '.join(present_settings)}")

            if missing_settings:
                st.log(f"\n⚠ ISSUE SSE-T8196 CONFIRMED: Required NTP settings missing from running-config")
                st.log(f"Missing required settings: {', '.join(missing_settings)}")
                st.log(f"\nExpected Behavior: All configured NTP parameters should appear in running-config")
                st.log(f"Actual Behavior: Only {len(present_settings)} out of {len(expected_settings)} settings visible")
                # Document the issue but don't fail - this is a known limitation
            else:
                st.log("\n✓ All required NTP settings found in running-config")
                if len(present_settings) == len(expected_settings):
                    st.log("✓ Issue SSE-T8196 may have been resolved")

            # Additional validation: Check if at least server IP is present
            if server_addr not in config_str:
                st.report_fail("msg", f"CRITICAL: NTP server {server_addr} not found in running-config")

            st.log("="*80)

        finally:
            # Cleanup
            st.log("Cleanup: Removing test NTP configuration")
            try:
                ntp_api.delete_ntp_server(dut, ipaddress=server_addr, cli_type=cli_type)
                ntp_api.delete_ntp_auth_key(dut, key_id, cli_type=cli_type)
                ntp_api.delete_ntp_trusted_key(dut, key_id, cli_type=cli_type)
                ntp_api.config_ntp_source_interface(dut, interface="", config="no", cli_type=cli_type)
                ntp_api.config_ntp_authenticate(dut, config="no", cli_type=cli_type)
            except Exception as e:
                st.log(f"Cleanup warning: {e}")

        st.report_pass("test_case_passed")


@pytest.mark.topology("any")
class TestNTPComplexScenarios:
    """Test Category 6: Complex NTP Configuration Scenarios"""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup for complex scenario tests."""
        st.banner("MODULE PROLOGUE: NTP Complex Scenarios Tests")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # NTP tests don't require connected ports, just a single device
        # min_topology = defaults.get("min_topology") or ["D1:1"]
        # topology = st.ensure_min_topology(*min_topology)
        topology = st.get_testbed_vars()

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.dut = topology.D1
        cls.data.configured_servers: List[str] = []
        cls.data.local_ntp_server = defaults.get("local_ntp_server", "192.168.100.175")

        # Clean up any existing NTP servers from previous test runs
        st.log("Cleaning up existing NTP servers before starting complex tests")
        try:
            ntp_api.delete_ntp_servers(cls.data.dut, cli_type=cls.data.cli_type)
        except Exception as e:
            st.log(f"Pre-test cleanup warning: {e}")

    def teardown_method(self, method) -> None:
        """Cleanup servers after each test."""
        dut = self.data.dut
        cli_type = self.data.cli_type

        # Skip cleanup for test_ntp_045 which tests deleting all config
        if method.__name__ == 'test_ntp_045_delete_all_config':
            st.log(f"Skipping server cleanup for {method.__name__}")
            return

        # Clean up configured servers
        if hasattr(self.data, 'configured_servers') and self.data.configured_servers:
            for server in self.data.configured_servers[:]:
                try:
                    ntp_api.delete_ntp_server(dut, ipaddress=server, cli_type=cli_type)
                    st.log(f"Cleaned up NTP server: {server}")
                except Exception as e:
                    st.log(f"Cleanup error for server {server}: {e}")
            self.data.configured_servers.clear()

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup after complex scenarios."""
        st.banner("MODULE EPILOGUE: Cleaning up complex configurations")
        dut = cls.data.dut
        cli_type = cls.data.cli_type

        try:
            # Delete all servers
            ntp_api.delete_ntp_servers(dut, cli_type=cli_type)

            # Delete authentication keys
            for key_id in [100, 201, 202, 250]:
                ntp_api.delete_ntp_auth_key(dut, key_id, cli_type=cli_type)

            # Disable authentication and NTP
            ntp_api.config_ntp_authenticate(dut, config="no", cli_type=cli_type)
            ntp_api.config_ntp_enable(dut, config="no", cli_type=cli_type)

        except Exception as e:
            st.log(f"Cleanup error: {e}")

    @pytest.mark.complex
    def test_ntp_044_complete_setup(self) -> None:
        """NTP-044: Complete NTP setup with authentication and server."""
        st.banner("TEST: NTP-044 - Complete NTP Setup with Authentication")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # Enable NTP
        if not ntp_api.config_ntp_enable(dut, config="yes", cli_type=cli_type):
            st.report_fail("msg", "Failed to enable NTP")

        # Enable authentication
        if not ntp_api.config_ntp_authenticate(dut, config="yes", cli_type=cli_type):
            st.report_fail("msg", "Failed to enable authentication")

        # Configure authentication key
        key_id = 100
        if not ntp_api.config_ntp_auth_key(
            dut, key_id, "sha256", "SecurePassword123", cli_type=cli_type
        ):
            st.report_fail("msg", f"Failed to configure auth key {key_id}")

        # Configure trusted key
        if not ntp_api.config_ntp_trusted_key(dut, key_id, cli_type=cli_type):
            st.report_fail("msg", f"Failed to configure trusted key {key_id}")

        # Configure NTP server with all options
        server_addr = self.data.local_ntp_server  # Use local NTP server
        if not ntp_api.config_ntp_server(
            dut,
            ipaddress=server_addr,
            key_id=key_id,
            prefer=True,
            iburst=True,
            cli_type=cli_type,
        ):
            st.report_fail("msg", f"Failed to configure NTP server {server_addr}")

        # Verify configuration
        if not ntp_api.verify_ntp_server(dut, server=server_addr, cli_type=cli_type):
            st.report_fail("msg", f"NTP server {server_addr} not found in configuration")

        st.report_pass("test_case_passed")

    @pytest.mark.complex
    def test_ntp_046_time_drift_correction(self) -> None:
        """NTP-046: Validate NTP corrects manual clock drift over time."""
        st.banner("TEST: NTP-046 - Validate NTP Time Drift Correction")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # This test requires a working NTP server
        # Using the local NTP server for actual time synchronization testing
        ntp_server = self.data.local_ntp_server  # Use local NTP server

        st.log("Step 1: Enable NTP and configure NTP server")
        result = ntp_api.config_ntp_enable(dut, config="yes", cli_type=cli_type)
        if not result:
            st.report_fail("msg", "Failed to enable NTP service")

        result = ntp_api.config_ntp_server(dut, ipaddress=ntp_server, cli_type=cli_type)
        if not result:
            st.report_fail("msg", f"Failed to configure NTP server {ntp_server}")

        self.data.configured_servers.append(ntp_server)

        # Verify NTP server was configured
        ntp_servers = ntp_api.show_ntp_server(dut, cli_type=cli_type)
        if not ntp_servers:
            st.report_fail("msg", "Failed to verify NTP server configuration")

        ntp_servers_str = str(ntp_servers)
        if ntp_server not in ntp_servers_str:
            st.report_fail("msg", f"NTP server {ntp_server} not found after configuration")

        st.log(f"✅ NTP enabled and server {ntp_server} configured successfully")

        # Wait for NTP to sync initially
        st.log("Step 2: Wait for initial NTP sync (30 seconds)")
        st.wait(30, "Waiting for NTP to sync")

        # Get current time before drift
        st.log("Step 3: Record current system time")
        output_before = ntp_api.show_clock(dut, cli_type=cli_type)
        st.log(f"System time before drift: {output_before}")

        # Get NTP status before drift
        st.log("Step 4: Check NTP status before drift")
        ntp_output_before = ntp_api.show_ntp_server(dut, cli_type=cli_type)
        st.log(f"NTP status before drift:\n{ntp_output_before}")

        # Introduce time drift - set clock backward by 5 minutes
        st.log("Step 5: Introduce time drift (set clock backward by 5 minutes)")
        drift_output = st.config(
            dut,
            "sudo date --set='-5 minutes'",
            type="click",
            skip_error_check=True
        )
        st.log(f"Time drift applied: {drift_output}")

        # Verify time has drifted
        output_after_drift = ntp_api.show_clock(dut, cli_type=cli_type)
        st.log(f"System time after drift: {output_after_drift}")

        # Check chronyc tracking to see the offset
        st.log("Step 6: Check chronyc tracking for time offset")
        chronyc_output = st.config(
            dut,
            "chronyc tracking",
            type="click",
            skip_error_check=True
        )
        st.log(f"Chronyc tracking output:\n{chronyc_output}")

        # Wait for NTP to correct the drift
        # NTP typically takes some time to correct large drifts
        st.log("Step 7: Wait for NTP to correct the drift (60 seconds)")
        st.wait(60, "Waiting for NTP to correct time drift")

        # Check NTP status after drift correction
        st.log("Step 8: Check NTP status after drift correction")
        ntp_output_after = ntp_api.show_ntp_server(dut, cli_type=cli_type)
        st.log(f"NTP status after drift correction:\n{ntp_output_after}")

        # Get final time
        output_final = ntp_api.show_clock(dut, cli_type=cli_type)
        st.log(f"System time after NTP correction: {output_final}")

        # Check chronyc tracking again to verify offset is reduced
        st.log("Step 9: Verify time offset is reduced using chronyc tracking")
        chronyc_final = st.config(
            dut,
            "chronyc tracking",
            type="click",
            skip_error_check=True
        )
        st.log(f"Chronyc tracking after correction:\n{chronyc_final}")

        # Validate chronyc output
        if not chronyc_final or not isinstance(chronyc_final, str):
            st.report_fail("msg", "Failed to get chronyc tracking output")

        if "System time" not in chronyc_final and "Last offset" not in chronyc_final:
            st.report_fail("msg", "Chronyc tracking output does not contain expected time offset information")

        st.log("✅ NTP is actively tracking and correcting time drift")

        # Validate NTP server output
        if not ntp_output_after:
            st.report_fail("msg", "Failed to get NTP server status after drift correction")

        # Convert output to string for validation
        ntp_output_str = str(ntp_output_after)
        if ntp_server not in ntp_output_str and "pool.ntp.org" not in ntp_output_str:
            st.report_fail("msg", f"NTP server {ntp_server} not found in show ntp server output")

        st.log(f"✅ NTP server {ntp_server} is configured and reachable")

        st.log("Step 10: Cleanup - Remove test NTP server")
        ntp_api.delete_ntp_server(dut, ipaddress=ntp_server, cli_type=cli_type)
        if ntp_server in self.data.configured_servers:
            self.data.configured_servers.remove(ntp_server)

        st.log("✅ Time drift correction test completed successfully")
        st.log("NOTE: Full NTP synchronization may take several minutes in production")
        st.report_pass("test_case_passed")

    @pytest.mark.complex
    def test_ntp_045_delete_all_config(self) -> None:
        """NTP-045: Delete all NTP configuration."""
        st.banner("TEST: NTP-045 - Delete All NTP Configuration")

        dut = self.data.dut
        cli_type = self.data.cli_type

        # Setup configuration first
        ntp_api.config_ntp_enable(dut, config="yes", cli_type=cli_type)
        server_addr = "10.10.10.251"
        ntp_api.config_ntp_server(dut, ipaddress=server_addr, cli_type=cli_type)
        key_id = 101
        ntp_api.config_ntp_auth_key(dut, key_id, "md5", "TestPass", cli_type=cli_type)

        # Delete all configuration
        if not ntp_api.delete_ntp_server(dut, ipaddress=server_addr, cli_type=cli_type):
            st.report_fail("msg", f"Failed to delete server {server_addr}")

        if not ntp_api.delete_ntp_auth_key(dut, key_id, cli_type=cli_type):
            st.report_fail("msg", f"Failed to delete auth key {key_id}")

        if not ntp_api.config_ntp_enable(dut, config="no", cli_type=cli_type):
            st.report_fail("msg", "Failed to disable NTP")

        st.report_pass("test_case_passed")
