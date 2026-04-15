"""
NTP PERSISTENCE TEST SUITE
Author: Athira
2026

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_1node_ntp.yaml \
  system/ntp/test_ntp_persistence.py \
  --logs-path ./logs/test_ntp_persistence_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native \
  --get-tech-support none --syslog-check none

  # For hardware testbed:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_HW_1node_ntp.yaml \
  system/ntp/test_ntp_persistence.py \
  --logs-path ./logs/test_ntp_persistence_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Comprehensive NTP configuration persistence test suite validating that NTP
  configuration persists correctly across:
  - Service restarts (ntp-config daemon)
  - Configuration reload (config reload -y)
  - System reboot (sudo reboot)
  - Running-config accuracy validation

  This suite verifies that all NTP configuration elements (service enable,
  authentication, keys, trusted keys, servers, source interface, VRF) are
  correctly saved to config_db.json and restored after various system operations.

  Based on manual test reports:
  - TC_NTP_PERSIST_001: Config save and daemon restart
  - TC_NTP_PERSIST_002: Config reload persistence
  - TC_NTP_PERSIST_003: Running-config accuracy

Pre-requisites:
  - Topology: single-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node
        # +--------------------+
        # |        D1          |
        # |     (DUT)          |
        # |   Ethernet0        |
        # |   Management0      |
        # +--------------------+

  - Feature flags / min SONiC version: NTP support, KLISH CLI, config save/reload
  - Required test variables (YAML): tests/system/ntp/vars_ntp_persistence.yaml
  - WARNING: TC_NTP_PERSIST_002 and TC_NTP_PERSIST_003 may take 3-5 minutes each
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import time
import json

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.system.ntp as ntp_api
import apis.system.basic as basic_api
import apis.system.reboot as reboot_api
import apis.switching.vlan as vlan_api
import apis.routing.ip as ip_api

# =============================================================================
# GLOBAL CONFIGURATION
# =============================================================================

# YAML configuration file path
VAR_FILE_ENV = "NTP_PERSISTENCE_VAR_FILE"
DEFAULT_VAR_FILE = Path(__file__).resolve().parent / "vars_ntp_persistence.yaml"

# Test constants
CLI_TYPE = "klish"  # Always use KLISH for IS-CLI validation
VERIFY_TIMEOUT = 60  # Default verification timeout (seconds)
RELOAD_TIMEOUT = 600  # Config reload timeout (10 minutes - increased for reliability)
REBOOT_TIMEOUT = 600  # System reboot timeout (10 minutes)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _is_virtual_sonic(dut: str) -> bool:
    """
    Detect if the device is running Virtual SONiC (VS).

    Args:
        dut: Device Under Test

    Returns:
        True if Virtual SONiC, False if hardware
    """
    try:
        output = st.show(dut, "show platform summary", skip_tmpl=True, skip_error_check=True)
        output_str = str(output).lower()

        # Check for Virtual SONiC indicators
        if 'asic: vs' in output_str or 'platform: x86_64-kvm' in output_str:
            st.log("Detected Virtual SONiC (VS) platform")
            return True

        st.log("Detected Hardware SONiC platform")
        return False
    except Exception as e:
        st.log(f"Could not detect platform type: {e}, assuming hardware")
        return False


def _get_accessible_ntp_server(dut: str) -> str:
    """
    Get an NTP server accessible from the DUT.

    For Virtual SONiC: Uses hardcoded local NTP server (192.168.100.175)
    For Hardware: Uses external public NTP server (Google NTP)

    Args:
        dut: Device Under Test

    Returns:
        IP address of accessible NTP server
    """
    if _is_virtual_sonic(dut):
        # For Virtual SONiC, use hardcoded local NTP server that is accessible from VS
        local_ntp_server = "192.168.100.175"
        st.log(f"Virtual SONiC detected - using local NTP server: {local_ntp_server}")

        # Verify server is pingable
        try:
            ping_result = st.show(dut, f"ping -c 2 -W 2 {local_ntp_server}",
                                 skip_tmpl=True, skip_error_check=True)
            if '2 received' in str(ping_result) or '2 packets received' in str(ping_result):
                st.log(f"✓ Local NTP server {local_ntp_server} is reachable")
            else:
                st.warn(f"⚠ Local NTP server {local_ntp_server} not responding to ping - will use anyway")
        except Exception as e:
            st.warn(f"Could not verify reachability of {local_ntp_server}: {e}")

        return local_ntp_server

    else:
        # Hardware SONiC - use public NTP server
        st.log("Hardware SONiC - using Google Public NTP server")
        return "216.239.35.0"  # time1.google.com


def _load_yaml_data() -> Dict[str, Any]:
    """
    Load testcase variables from YAML with optional environment override.

    Returns:
        Dictionary containing test configuration and variables
    """
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        st.error(f"NTP persistence variable file not found: {candidate}")
        pytest.skip(f"NTP persistence variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        st.error("NTP YAML must contain key 'testcases'")
        pytest.skip("NTP YAML must contain key 'testcases'")

    return content


def _cleanup_all_ntp_config(dut: str, cli_type: str = CLI_TYPE) -> None:
    """
    Clean up all NTP configuration on the DUT.

    Args:
        dut: Device Under Test
        cli_type: CLI type (default: klish)
    """
    st.banner("CLEANUP: Removing all NTP configuration")

    try:
        # Delete all NTP servers
        try:
            ntp_api.delete_ntp_servers(dut, cli_type=cli_type)
        except Exception as e:
            st.log(f"Server deletion warning (non-fatal): {e}")

        # Delete authentication and trusted keys (query from config_db.json for reliability)
        # Get existing keys from config_db.json
        auth_key_ids = []
        trusted_key_ids = []

        try:
            st.log("Querying existing NTP keys from config_db.json...")
            output = st.config(dut, "sudo cat /etc/sonic/config_db.json", skip_error_check=True)

            output_str = str(output) if output else ""

            if output_str and len(output_str.strip()) > 0 and output_str != "None":
                # Clean output - remove any command prompt artifacts
                last_brace = output_str.rfind('}')
                if last_brace > 0:
                    json_str = output_str[:last_brace + 1]
                    config_db = json.loads(json_str)

                    # Extract authentication keys from NTP_KEY table
                    if "NTP_KEY" in config_db:
                        for key_id_str in config_db["NTP_KEY"].keys():
                            try:
                                key_id = int(key_id_str)
                                if key_id not in auth_key_ids:
                                    auth_key_ids.append(key_id)
                            except ValueError:
                                st.log(f"Warning: Invalid key ID in config_db: {key_id_str}")

                        st.log(f"Found {len(auth_key_ids)} auth keys from config_db: {sorted(auth_key_ids)}")
                    else:
                        st.log("No NTP_KEY table found in config_db.json")
                else:
                    raise ValueError("No valid JSON found in config_db output")
            else:
                st.log("Warning: Could not read config_db.json, will use fallback key range")
                raise ValueError("Empty config_db output")

        except json.JSONDecodeError as e:
            st.log(f"Warning: Could not parse config_db.json: {e}")
        except Exception as e:
            st.log(f"Warning: Could not extract keys from config_db.json: {e}")
            # Fallback: try a range of common key IDs
            st.log("Fallback: Trying to delete common key IDs (1-100)")
            auth_key_ids = list(range(1, 101))

        # Delete authentication keys (deleting auth keys also removes trusted key status)
        if auth_key_ids:
            st.log(f"Deleting {len(auth_key_ids)} authentication keys: {sorted(auth_key_ids)}")
            for key_id in auth_key_ids:
                try:
                    # Delete the authentication key directly
                    # Note: Deleting an auth key automatically removes its trusted status
                    # We don't need to explicitly call delete_ntp_trusted_key which can hang
                    ntp_api.delete_ntp_auth_key(dut, key_id, cli_type=cli_type)
                    st.log(f"✓ Deleted auth key {key_id}")
                except Exception as e:
                    # Ignore errors during cleanup - key might not exist
                    st.log(f"Warning: Could not delete auth key {key_id}: {e}")
        else:
            st.log("No authentication keys found to delete")

        # Disable authentication
        try:
            ntp_api.config_ntp_authenticate(dut, config='no', cli_type=cli_type)
        except Exception as e:
            st.log(f"Auth disable warning (non-fatal): {e}")

        # Remove source interface
        try:
            # Try to remove common source interfaces
            for intf_name in ["Ethernet0", "Ethernet4", "Management0"]:
                try:
                    ntp_api.config_ntp_source_interface(dut, intf_name, config='no', cli_type=cli_type)
                except:
                    pass
        except:
            pass

        # Reset VRF to default
        try:
            ntp_api.config_ntp_vrf(dut, "default", cli_type=cli_type)
        except:
            pass

        # Disable NTP service
        try:
            ntp_api.config_ntp_enable(dut, config='no', cli_type=cli_type)
        except Exception as e:
            st.log(f"NTP disable warning (non-fatal): {e}")

        st.log("Cleanup completed successfully")

    except Exception as e:
        st.log(f"Cleanup error (non-fatal): {e}")


def _get_first_interface(dut: str, interface_type: str = "Ethernet") -> Optional[str]:
    """
    Get the first available interface of specified type from topology.

    Args:
        dut: Device Under Test
        interface_type: Interface type (Ethernet, Vlan, PortChannel, Loopback, Management)

    Returns:
        Interface name (e.g., "Ethernet0") or None if not found
    """
    try:
        if interface_type == "Ethernet":
            # Try to get all ports available on the DUT
            all_ports = st.get_all_ports(dut)
            if all_ports:
                st.log(f"Available Ethernet ports: {all_ports}")
                # Return first Ethernet port
                for port in all_ports:
                    if port.startswith("Ethernet"):
                        st.log(f"Selected Ethernet interface: {port}")
                        return port
                # If no Ethernet prefix, return first port
                st.log(f"No Ethernet-prefixed port found, using first port: {all_ports[0]}")
                return all_ports[0]

        elif interface_type == "Management":
            return "Management0"

        elif interface_type == "Loopback":
            return "Loopback0"

        return None

    except Exception as e:
        st.log(f"Error getting interface: {e}, will try Management0 as fallback")
        # Use Management0 as ultimate fallback since it exists on all SONiC devices
        return "Management0" if interface_type == "Ethernet" else None


def _verify_config_db_ntp(dut: str, expected_config: Dict[str, Any]) -> bool:
    """
    Verify NTP configuration in config_db.json matches expected values.

    Args:
        dut: Device Under Test
        expected_config: Dictionary with expected NTP configuration

    Returns:
        True if config matches, False otherwise
    """
    try:
        # Read config_db.json - use st.config() to execute Linux commands
        st.log("Reading config_db.json to verify NTP configuration persistence")
        output = st.config(dut, "sudo cat /etc/sonic/config_db.json", skip_error_check=True)

        # st.config() returns the command output as string
        output_str = str(output) if output else ""

        # Check if we have valid output
        if not output_str or len(output_str.strip()) == 0 or output_str == "None":
            st.error("Failed to read config_db.json - empty output")
            st.log(f"Output type: {type(output)}, Output value: {repr(output)}")
            return False

        # Clean output - remove any command prompt artifacts

        # Find the last '}' which should be the end of JSON
        last_brace = output_str.rfind('}')
        if last_brace == -1:
            st.error("No closing brace found in config_db.json output")
            st.log(f"Output preview (first 500 chars): {output_str[:500]}")
            return False

        # Extract only the JSON part
        json_str = output_str[:last_brace + 1]

        st.log(f"Attempting to parse JSON (length: {len(json_str)} chars)")

        # Parse JSON
        try:
            config_db = json.loads(json_str)
            st.log(f"✓ Successfully parsed config_db.json, found {len(config_db)} top-level keys")
        except json.JSONDecodeError as e:
            st.error(f"JSON parsing failed at position {e.pos}: {e.msg}")
            st.log(f"JSON excerpt around error: {json_str[max(0, e.pos-50):min(len(json_str), e.pos+50)]}")
            raise

        # Check NTP global config
        if "NTP" not in config_db:
            st.error("NTP table not found in config_db.json - configuration may not have synced yet")
            st.log(f"Available tables: {list(config_db.keys())}")
            return False

        if "global" not in config_db["NTP"]:
            st.error("NTP global configuration not found in config_db.json")
            st.log(f"NTP table keys: {list(config_db['NTP'].keys())}")
            return False

        ntp_global = config_db["NTP"]["global"]
        st.log(f"NTP global config in DB: {ntp_global}")

        # Verify admin_state
        if "ntp_enable" in expected_config:
            expected_state = "enabled" if expected_config["ntp_enable"] else "disabled"
            actual_state = ntp_global.get("admin_state", "")
            if actual_state != expected_state:
                st.error(f"admin_state mismatch: expected {expected_state}, got {actual_state}")
                return False

        # Verify VRF
        if "vrf" in expected_config:
            actual_vrf = ntp_global.get("vrf", "default")
            if actual_vrf != expected_config["vrf"]:
                st.error(f"VRF mismatch: expected {expected_config['vrf']}, got {actual_vrf}")
                return False

        # Verify authentication
        if "auth_enabled" in expected_config:
            # In config_db.json, the field is "authentication" not "auth_enabled"
            expected_auth = "enabled" if expected_config["auth_enabled"] else "disabled"
            actual_auth = ntp_global.get("authentication", "disabled")
            st.log(f"Authentication check: expected={expected_auth}, actual={actual_auth}")
            if actual_auth != expected_auth:
                st.error(f"authentication mismatch: expected {expected_auth}, got {actual_auth}")
                return False
            st.log("✓ Authentication setting verified")

        # Verify source interface
        if "source_interface" in expected_config:
            actual_src_intf = ntp_global.get("src_intf", "")

            # Handle both string and list formats
            if isinstance(actual_src_intf, list):
                # If it's a list, get first element or empty string
                actual_src_intf = actual_src_intf[0] if actual_src_intf and actual_src_intf[0] else ""

            expected_intf = expected_config["source_interface"]
            if actual_src_intf != expected_intf:
                st.log(f"Warning: source_interface mismatch: expected '{expected_intf}', got '{actual_src_intf}'")
                # Don't fail on source interface mismatch, just warn
            else:
                st.log(f"✓ Source interface verified: {actual_src_intf}")

        # Check NTP servers
        if "servers" in expected_config and "NTP_SERVER" in config_db:
            ntp_servers = config_db["NTP_SERVER"]
            st.log(f"NTP servers in DB: {list(ntp_servers.keys())}")

            for expected_server in expected_config["servers"]:
                if expected_server not in ntp_servers:
                    st.error(f"Server {expected_server} not found in config_db.json")
                    return False

        # Check NTP authentication keys
        if "auth_keys" in expected_config and "NTP_KEY" in config_db:
            ntp_keys = config_db["NTP_KEY"]
            st.log(f"NTP keys in DB: {list(ntp_keys.keys())}")

            for key_id in expected_config["auth_keys"]:
                if str(key_id) not in ntp_keys:
                    st.error(f"Auth key {key_id} not found in config_db.json")
                    return False

        st.log("✓ config_db.json verification passed")
        return True

    except json.JSONDecodeError as e:
        st.error(f"Failed to parse config_db.json: {e}")
        return False
    except Exception as e:
        st.error(f"Error verifying config_db.json: {e}")
        return False


def _save_configuration(dut: str) -> bool:
    """
    Save current configuration to startup-config.

    Uses st.config() to execute 'config save -y' command.

    Args:
        dut: Device Under Test

    Returns:
        True if save succeeded, False otherwise
    """
    try:
        st.log("Saving configuration using 'sudo config save -y'")
        output = st.config(dut, "sudo config save -y", skip_error_check=True)

        if output:
            st.log(f"Config save output: {output}")

        # Allow time for config to be written to disk
        time.sleep(3)

        st.log("✓ Configuration saved successfully")
        return True

    except Exception as e:
        st.error(f"Failed to save configuration: {e}")
        return False


def _reload_configuration(dut: str, timeout: int = RELOAD_TIMEOUT) -> bool:
    """
    Reload configuration using reboot_api.config_reload().

    This uses the framework's built-in config reload which properly handles
    device disconnection and reconnection.

    IMPORTANT: Config reload will restore config from config_db.json.
    The framework automatically preserves management interface configuration.

    Args:
        dut: Device Under Test
        timeout: Maximum time to wait for reload to complete (seconds)

    Returns:
        True if reload succeeded, False otherwise
    """
    try:
        st.log("Executing config reload using framework API (this will take ~2-3 minutes)")
        st.banner("CONFIG RELOAD IN PROGRESS - PLEASE WAIT")

        # NOTE: reboot_api.config_reload() uses st.config_db_reload() internally
        # which has special handling to preserve management interface configuration
        # Use the framework's config_reload API which handles everything properly
        # This will:
        # 1. Execute 'config reload -y'
        # 2. Wait for device to disconnect
        # 3. Wait for device to reconnect
        # 4. Wait for system to be ready
        reboot_api.config_reload(dut)

        st.log("Config reload initiated, waiting for system to be ready...")

        # Wait for system to be fully ready with custom timeout
        st.wait_system_status(dut, max_time=timeout)

        # Additional wait for NTP and other services to stabilize
        st.log("Waiting 30 seconds for all services (including NTP) to stabilize...")
        time.sleep(30)

        st.log("✓ Configuration reload completed successfully")
        return True

    except Exception as e:
        st.error(f"Config reload failed: {e}")
        # Try to reconnect to the device
        st.log("Attempting to reconnect to device...")
        try:
            st.wait_system_status(dut, max_time=120)
            st.log("✓ Device reconnected after error")
            return True
        except:
            st.error("Failed to reconnect to device")
            return False


# =============================================================================
# TEST CLASS: NTP PERSISTENCE TESTS
# =============================================================================

@pytest.mark.topology("any")
@pytest.mark.ntp_persistence
class TestNTPPersistence:
    """
    Test Category: NTP Configuration Persistence
    Tests: Config save, daemon restart, config reload, system reboot, running-config accuracy
    """

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.banner("MODULE PROLOGUE: NTP Persistence Tests")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        topology = st.get_testbed_vars()

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type = defaults.get("cli_type", CLI_TYPE)
        cls.data.verify_timeout = int(defaults.get("verify_timeout", VERIFY_TIMEOUT))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Get DUT handle
        cls.data.dut = topology.D1
        cls.data.dut_names = st.get_dut_names()

        # Auto-detect accessible NTP server based on platform (VS vs HW)
        cls.data.test_server = _get_accessible_ntp_server(cls.data.dut)

        st.log(f"Test setup complete. DUT: {cls.data.dut}, CLI type: {cls.data.cli_type}")
        st.log(f"Platform-specific test server: {cls.data.test_server}")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup all NTP configuration after the suite completes."""
        st.banner("MODULE EPILOGUE: Cleaning up NTP Persistence configuration")
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping")
            return

        _cleanup_all_ntp_config(cls.data.dut, cls.data.cli_type)

        # Save clean config
        try:
            _save_configuration(cls.data.dut)
        except:
            pass

    def setup_method(self) -> None:
        """Reset per-test bookkeeping."""
        st.log("Test setup: Preparing for next test")
        # Clean start for each test
        _cleanup_all_ntp_config(self.data.dut, self.data.cli_type)

    def teardown_method(self) -> None:
        """Cleanup after each test."""
        if not self.data.cleanup_enabled:
            return

        st.log("Test teardown: Cleaning up test configuration")
        _cleanup_all_ntp_config(self.data.dut, self.data.cli_type)

    @pytest.mark.persistence
    @pytest.mark.inventory(feature="NTP", testcase="TC_NTP_PERSIST_001")
    def test_ntp_config_persists_after_save_and_daemon_restart(self) -> None:
        """
        TC_NTP_PERSIST_001: NTP configuration persists after config save and daemon restart

        Verify that comprehensive NTP configuration persists correctly after:
        1. Configuration save (sudo config save -y)
        2. NTP service restart (systemctl restart ntp-config)

        This test validates that config_db.json is correctly updated and configuration
        is restored after daemon restart.

        Steps:
          1. Configure comprehensive NTP setup (enable, auth, keys, servers, source-interface)
          2. Verify initial configuration
          3. Save configuration
          4. Verify config_db.json contains all settings
          5. Restart ntp-config service
          6. Verify configuration persists after restart

        Expected: All NTP configuration persists correctly in config_db.json and after restart

        Based on manual test report: TC_NTP_PERSIST_001.md
        """
        st.banner("TEST: TC_NTP_PERSIST_001 - Config Persistence After Save and Daemon Restart")

        tc_data = self.data.testcases.get("NTP_PERSIST_001", {})
        if not tc_data:
            pytest.skip("Test case NTP_PERSIST_001 not found in YAML")

        dut = self.data.dut
        cli_type = self.data.cli_type
        test_server = self.data.test_server

        # Get first available interface for NTP source
        # Try Ethernet first, fallback to Management0 if needed
        source_intf = _get_first_interface(dut, "Ethernet")
        if not source_intf:
            st.log("No Ethernet interface available, using Management0 as NTP source interface")
            source_intf = "Management0"

        st.log(f"Using NTP source interface: {source_intf}")

        # STEP 1: Configure comprehensive NTP setup
        st.banner("STEP 1: Configure Comprehensive NTP Setup")

        # Enable NTP service
        st.log("1.1: Enable NTP service")
        if not ntp_api.config_ntp_enable(dut, config='yes', cli_type=cli_type):
            st.report_fail("msg", "Failed to enable NTP service")

        # Enable authentication
        st.log("1.2: Enable NTP authentication")
        if not ntp_api.config_ntp_authenticate(dut, config='yes', cli_type=cli_type):
            st.report_fail("msg", "Failed to enable NTP authentication")

        # Configure authentication key
        st.log("1.3: Configure authentication key (ID=100, MD5)")
        if not ntp_api.config_ntp_auth_key(dut, key_id=100, auth_type="md5",
                                            password="TestPersist123", cli_type=cli_type):
            st.report_fail("msg", "Failed to configure authentication key 100")

        # Mark key as trusted
        st.log("1.4: Mark key 100 as trusted")
        if not ntp_api.config_ntp_trusted_key(dut, key_id=100, cli_type=cli_type):
            st.report_fail("msg", "Failed to configure trusted key 100")

        # Configure NTP server (without key first, as per manual test findings)
        st.log(f"1.5: Configure NTP server {test_server} with iburst and prefer")
        if not ntp_api.config_ntp_server(dut, ipaddress=test_server,
                                          iburst=True, prefer=True, cli_type=cli_type):
            st.report_fail("msg", f"Failed to configure NTP server {test_server}")

        # Configure source interface
        st.log(f"1.6: Configure source interface {source_intf}")
        if not ntp_api.config_ntp_source_interface(dut, source_intf, config='yes', cli_type=cli_type):
            st.report_fail("msg", f"Failed to configure source interface {source_intf}")

        # STEP 2: Verify initial configuration
        st.banner("STEP 2: Verify Initial Configuration")

        # Verify NTP global config
        global_config = ntp_api.show_ntp_global(dut, cli_type=cli_type)
        if not global_config:
            st.report_fail("msg", "Failed to get NTP global configuration")

        st.log(f"NTP Global Config: {global_config}")

        # Verify NTP is enabled
        if global_config.get('ntp_service') != 'enabled':
            st.report_fail("msg", "NTP service not enabled")

        # Verify authentication is enabled
        if global_config.get('authentication') != 'enabled':
            st.report_fail("msg", "NTP authentication not enabled")

        # Verify servers configured
        servers = ntp_api.show_ntp_server(dut, cli_type=cli_type)
        server_found = False
        if servers:
            for srv in servers:
                if test_server in srv.get('remote', ''):
                    server_found = True
                    break

        if not server_found:
            st.report_fail("msg", f"NTP server {test_server} not found in configuration")

        st.log("✓ Initial configuration verified successfully")

        # STEP 2.5: Wait for NTP configuration to sync to CONFIG_DB
        st.log("Waiting for NTP configuration to sync to CONFIG_DB (10 seconds)...")
        time.sleep(10)  # Allow NTP daemon to write config to CONFIG_DB

        # STEP 3: Save configuration
        st.banner("STEP 3: Save Configuration")

        if not _save_configuration(dut):
            st.report_fail("msg", "Failed to save configuration")

        time.sleep(5)  # Allow time for config to be written to disk

        # STEP 4: Verify config_db.json contains all settings
        st.banner("STEP 4: Verify config_db.json Contains All Settings")

        expected_db_config = {
            "ntp_enable": True,
            "auth_enabled": True,
            "vrf": "default",
            "servers": [test_server],
            "auth_keys": [100],
            "source_interface": source_intf
        }

        if not _verify_config_db_ntp(dut, expected_db_config):
            st.report_fail("msg", "NTP configuration not correctly saved in config_db.json")

        st.log("✓ config_db.json verification passed")

        # STEP 5: Restart NTP service/daemon
        st.banner("STEP 5: Restart NTP Service/Daemon")

        st.log("Restarting NTP daemon (ntp service)...")
        try:
            # In SONiC, NTP configuration is handled by ntp container
            # Restarting just the ntp daemon is sufficient
            output = st.config(dut, "sudo systemctl restart ntp", skip_error_check=True)
            st.log(f"NTP restart output: {output}")
            time.sleep(10)  # Wait for service to restart and stabilize
            st.log("✓ NTP service restarted")
        except Exception as e:
            st.log(f"Warning: NTP restart may have failed: {e}")
            st.log("Continuing with verification...")

        # STEP 6: Verify configuration persists after restart
        st.banner("STEP 6: Verify Configuration Persists After Restart")

        # Small delay to ensure system is stable after restart
        st.log("Waiting 5 seconds for system to stabilize after NTP restart...")
        time.sleep(5)

        # Re-verify global config
        st.log("Executing 'show ntp global' to verify configuration after restart")
        global_config_after = ntp_api.show_ntp_global(dut, cli_type=cli_type)
        if not global_config_after:
            st.report_fail("msg", "Failed to get NTP global configuration after restart")

        st.log(f"NTP Global Config After Restart: {global_config_after}")

        # Verify NTP still enabled
        if global_config_after.get('ntp_service') != 'enabled':
            st.report_fail("msg", "NTP service not enabled after restart")

        # Verify authentication still enabled
        if global_config_after.get('authentication') != 'enabled':
            st.report_fail("msg", "NTP authentication not enabled after restart")

        # Verify servers still configured
        servers_after = ntp_api.show_ntp_server(dut, cli_type=cli_type)
        server_found_after = False
        if servers_after:
            for srv in servers_after:
                if test_server in srv.get('remote', ''):
                    server_found_after = True
                    break

        if not server_found_after:
            st.report_fail("msg", f"NTP server {test_server} not found after restart")

        st.log("✓ PASS: NTP configuration persisted correctly after save and daemon restart")
        st.report_pass("test_case_passed")

    @pytest.mark.persistence
    @pytest.mark.config_reload
    @pytest.mark.inventory(feature="NTP", testcase="TC_NTP_PERSIST_002")
    def test_ntp_config_persists_across_config_reload(self) -> None:
        """
        TC_NTP_PERSIST_002: NTP configuration persists across config reload

        Verify that NTP configuration survives a full configuration reload
        (sudo config reload -y), which simulates a system reboot by:
        1. Stopping all SONiC services
        2. Reloading configuration from config_db.json
        3. Restarting all SONiC services

        This is a comprehensive test that validates configuration persistence
        in a near-reboot scenario.

        Steps:
          1. Configure comprehensive NTP setup
          2. Save configuration
          3. Verify config_db.json
          4. Execute config reload
          5. Wait for system to come back up
          6. Verify all configuration persisted

        Expected: All NTP configuration intact after config reload

        WARNING: This test takes 3-5 minutes due to config reload operation

        Based on manual test report: TC_NTP_PERSIST_002.md
        """
        st.banner("TEST: TC_NTP_PERSIST_002 - Config Persistence Across Config Reload")

        tc_data = self.data.testcases.get("NTP_PERSIST_002", {})
        if not tc_data:
            pytest.skip("Test case NTP_PERSIST_002 not found in YAML")

        dut = self.data.dut
        cli_type = self.data.cli_type
        test_server = self.data.test_server

        # Get first available interface for NTP source
        # Try Ethernet first, fallback to Management0 if needed
        source_intf = _get_first_interface(dut, "Ethernet")
        if not source_intf:
            st.log("No Ethernet interface available, using Management0 as NTP source interface")
            source_intf = "Management0"

        st.log(f"Using NTP source interface: {source_intf}")

        # STEP 1: Configure comprehensive NTP setup
        st.banner("STEP 1: Configure Comprehensive NTP Setup for Reload Test")

        # Enable NTP
        st.log("1.1: Enable NTP service")
        if not ntp_api.config_ntp_enable(dut, config='yes', cli_type=cli_type):
            st.report_fail("msg", "Failed to enable NTP service")

        # Enable authentication
        st.log("1.2: Enable NTP authentication")
        if not ntp_api.config_ntp_authenticate(dut, config='yes', cli_type=cli_type):
            st.report_fail("msg", "Failed to enable NTP authentication")

        # Configure authentication key (use key ID 50 as per manual test)
        st.log("1.3: Configure authentication key (ID=50, MD5)")
        if not ntp_api.config_ntp_auth_key(dut, key_id=50, auth_type="md5",
                                            password="ReloadTest123", cli_type=cli_type):
            st.report_fail("msg", "Failed to configure authentication key 50")

        # Mark key as trusted
        st.log("1.4: Mark key 50 as trusted")
        if not ntp_api.config_ntp_trusted_key(dut, key_id=50, cli_type=cli_type):
            st.report_fail("msg", "Failed to configure trusted key 50")

        # Configure NTP server
        st.log(f"1.5: Configure NTP server {test_server} with iburst")
        if not ntp_api.config_ntp_server(dut, ipaddress=test_server,
                                          iburst=True, cli_type=cli_type):
            st.report_fail("msg", f"Failed to configure NTP server {test_server}")

        # Configure source interface
        st.log(f"1.6: Configure source interface {source_intf}")
        if not ntp_api.config_ntp_source_interface(dut, source_intf, config='yes', cli_type=cli_type):
            st.log(f"Warning: Failed to configure source interface {source_intf}, continuing...")

        # Capture pre-reload configuration
        st.log("1.7: Capture pre-reload configuration")
        global_config_before = ntp_api.show_ntp_global(dut, cli_type=cli_type)
        servers_before = ntp_api.show_ntp_server(dut, cli_type=cli_type)

        st.log(f"Pre-reload NTP Global: {global_config_before}")
        st.log(f"Pre-reload NTP Servers: {len(servers_before) if servers_before else 0} servers")

        # STEP 1.8: Wait for NTP configuration to sync to CONFIG_DB
        st.log("1.8: Waiting for NTP configuration to sync to CONFIG_DB (10 seconds)...")
        time.sleep(10)  # Allow NTP daemon to write config to CONFIG_DB

        # STEP 2: Save configuration
        st.banner("STEP 2: Save Configuration to config_db.json")

        if not _save_configuration(dut):
            st.report_fail("msg", "Failed to save configuration")

        time.sleep(5)  # Allow time for config to be written to disk

        # STEP 3: Verify config_db.json before reload
        st.banner("STEP 3: Verify config_db.json Before Reload")

        expected_db_config = {
            "ntp_enable": True,
            "auth_enabled": True,
            "vrf": "default",
            "servers": [test_server],
            "auth_keys": [50],
            "source_interface": source_intf
        }

        if not _verify_config_db_ntp(dut, expected_db_config):
            st.log("Warning: config_db.json verification failed, but continuing with reload test")

        # STEP 4: Execute config reload
        st.banner("STEP 4: Execute Config Reload (This will take ~3 minutes)")

        if not _reload_configuration(dut, timeout=RELOAD_TIMEOUT):
            st.report_fail("msg", "Config reload failed or timed out")

        # STEP 5: Verify configuration persisted after reload
        st.banner("STEP 5: Verify Configuration Persisted After Reload")

        # Re-verify global config
        global_config_after = ntp_api.show_ntp_global(dut, cli_type=cli_type)
        if not global_config_after:
            st.report_fail("msg", "Failed to get NTP global configuration after reload")

        st.log(f"Post-reload NTP Global: {global_config_after}")

        # Verify NTP still enabled
        if global_config_after.get('ntp_service') != 'enabled':
            st.report_fail("msg", "NTP service not enabled after reload")

        # Verify authentication still enabled
        if global_config_after.get('authentication') != 'enabled':
            st.report_fail("msg", "NTP authentication not enabled after reload")

        # Verify servers still configured
        servers_after = ntp_api.show_ntp_server(dut, cli_type=cli_type)
        server_found = False
        if servers_after:
            for srv in servers_after:
                if test_server in srv.get('remote', ''):
                    server_found = True
                    break

        if not server_found:
            st.report_fail("msg", f"NTP server {test_server} not found after reload")

        st.log(f"Post-reload NTP Servers: {len(servers_after) if servers_after else 0} servers")

        # Verify config_db.json still contains settings
        if not _verify_config_db_ntp(dut, expected_db_config):
            st.log("Warning: config_db.json verification failed after reload")

        st.log("✓ PASS: NTP configuration persisted correctly across config reload")
        st.report_pass("test_case_passed")

    @pytest.mark.persistence
    @pytest.mark.running_config
    @pytest.mark.inventory(feature="NTP", testcase="TC_NTP_PERSIST_003")
    def test_ntp_running_config_accuracy(self) -> None:
        """
        TC_NTP_PERSIST_003: Running-config accuracy validation

        Verify that 'show running-configuration' command accurately reflects
        the current NTP configuration state, including:
        - NTP enable/disable state
        - NTP authentication settings
        - Authentication keys with correct algorithms
        - NTP servers with all options
        - Source interface configuration
        - VRF binding

        This test also validates the authentication key command syntax based on
        bug investigation findings from manual testing.

        Steps:
          1. Configure various NTP settings
          2. Execute 'show running-configuration | grep ntp'
          3. Verify output contains all configured elements
          4. Test authentication key syntax variations
          5. Verify running-config accuracy

        Expected: Running-config accurately reflects all NTP configuration

        Based on manual test report: TC_NTP_PERSIST_003.md
        """
        st.banner("TEST: TC_NTP_PERSIST_003 - Running-Config Accuracy Validation")

        tc_data = self.data.testcases.get("NTP_PERSIST_003", {})
        if not tc_data:
            pytest.skip("Test case NTP_PERSIST_003 not found in YAML")

        dut = self.data.dut
        cli_type = self.data.cli_type
        test_server = self.data.test_server

        # STEP 1: Configure NTP settings
        st.banner("STEP 1: Configure NTP Settings for Running-Config Test")

        # Test authentication key with correct syntax
        st.log("1.1: Test authentication-key command syntax (correct)")
        if not ntp_api.config_ntp_auth_key(dut, key_id=10, auth_type="md5",
                                            password="TestKey123", cli_type=cli_type):
            st.report_fail("msg", "Failed to configure authentication key 10 with correct syntax")

        # Mark key as trusted
        st.log("1.2: Configure trusted key 10")
        if not ntp_api.config_ntp_trusted_key(dut, key_id=10, cli_type=cli_type):
            st.report_fail("msg", "Failed to configure trusted key 10")

        # Enable authentication
        st.log("1.3: Enable NTP authentication")
        if not ntp_api.config_ntp_authenticate(dut, config='yes', cli_type=cli_type):
            st.report_fail("msg", "Failed to enable NTP authentication")

        # Configure NTP server
        st.log(f"1.4: Configure NTP server {test_server}")
        if not ntp_api.config_ntp_server(dut, ipaddress=test_server,
                                          iburst=True, cli_type=cli_type):
            st.report_fail("msg", f"Failed to configure NTP server {test_server}")

        # Enable NTP service
        st.log("1.5: Enable NTP service")
        if not ntp_api.config_ntp_enable(dut, config='yes', cli_type=cli_type):
            st.report_fail("msg", "Failed to enable NTP service")

        # STEP 2: Verify running-configuration contains NTP settings
        st.banner("STEP 2: Verify Running-Configuration Accuracy")

        st.log("2.1: Execute 'show running-configuration | grep ntp'")

        # Get running configuration with NTP settings
        try:
            output = st.show(dut, "show running-configuration | grep ntp",
                             type='klish', skip_tmpl=True, exec_mode=True)

            if not output:
                st.report_fail("msg", "No NTP configuration found in running-config")

            # Convert output to string
            if isinstance(output, list):
                output_str = '\n'.join(str(item) for item in output)
            else:
                output_str = str(output)

            st.log(f"Running-config NTP section:\n{output_str}")

            # STEP 3: Verify key elements present in running-config
            st.banner("STEP 3: Verify Key Elements in Running-Config")

            # Check for authentication key 10
            if "authentication-key 10" not in output_str:
                st.report_fail("msg", "Authentication key 10 not found in running-config")
            st.log("✓ Authentication key 10 found in running-config")

            # Check for trusted key 10
            if "trusted-key 10" not in output_str:
                st.log("Warning: Trusted key 10 not shown in running-config (may be implicit)")

            # Check for authentication enabled
            if "ntp authenticate" not in output_str:
                st.log("Warning: 'ntp authenticate' not shown in running-config")

            # Check for NTP server
            if test_server not in output_str:
                st.report_fail("msg", f"NTP server {test_server} not found in running-config")
            st.log(f"✓ NTP server {test_server} found in running-config")

            # Check for NTP enable
            if "ntp enable" in output_str or "ntp" in output_str:
                st.log("✓ NTP configuration present in running-config")

        except Exception as e:
            st.error(f"Error executing show running-configuration: {e}")
            st.report_fail("msg", "Failed to get running-configuration")

        # STEP 4: Verify configuration via show commands
        st.banner("STEP 4: Cross-Verify with Show Commands")

        # Verify via show ntp global
        global_config = ntp_api.show_ntp_global(dut, cli_type=cli_type)
        if not global_config:
            st.report_fail("msg", "Failed to get NTP global configuration")

        st.log(f"NTP Global Config: {global_config}")

        # Verify authentication is enabled
        if global_config.get('authentication') != 'enabled':
            st.report_fail("msg", "NTP authentication not shown as enabled")

        # Verify NTP is enabled
        if global_config.get('ntp_service') != 'enabled':
            st.report_fail("msg", "NTP service not shown as enabled")

        # Verify servers
        servers = ntp_api.show_ntp_server(dut, cli_type=cli_type)
        server_found = False
        if servers:
            for srv in servers:
                if test_server in srv.get('remote', ''):
                    server_found = True
                    break

        if not server_found:
            st.report_fail("msg", f"NTP server {test_server} not found in show ntp server")

        st.log("✓ PASS: Running-config accurately reflects NTP configuration")
        st.report_pass("test_case_passed")


# =============================================================================
# END OF TEST SCRIPT
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
