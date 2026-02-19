"""
VRF FORWARDING NEGATIVE TESTS - LOOPBACK AND PORTCHANNEL
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \\
  --testbed ./testbeds/ztp_standalone.yaml  \\
  tests/system/vrf/test_vrf_loopback_portchannel_negative.py \\
  --logs-path ./logs/vrf_loopback_portchannel_neg_$(date +%F_%H%M%S) \\
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Negative test suite validating VRF forwarding restrictions on Loopback and
  PortChannel interfaces that already have Layer 3 (IP) configurations. The
  suite verifies that VRF binding fails with the correct error message when
  attempted on:
    1. A Loopback interface with an IP address configured
    2. A PortChannel interface with an IP address configured

  For each test the suite:
    - Performs pre-test cleanup to ensure a known-good initial state
    - Creates the target VRF fresh
    - Configures the logical interface and assigns an IP (with conflict check)
    - Attempts to bind the VRF (expected to be REJECTED)
    - Asserts the specific L3-configuration error message is returned
    - Cleans up all created resources on teardown

Pre-requisites:
  - Topology: standalone (single DUT) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node (standalone)
        # +-----------------------------+
        # |          dut1               |
        # |       (smic_sonic1)         |
        # |  Loopback100  (TC 2.1)      |
        # |  PortChannel100 / Eth8      |
        # |              (TC 2.2)       |
        # +-----------------------------+

  - Feature flags / min SONiC version: VRF and PortChannel support enabled
  - Required test variables (YAML):
      vars/system/vrf/vars_vrf_loopback_portchannel_negative.yaml
    Keys used:
      defaults.cli_type         (klish)
      defaults.verify_timeout
      defaults.cleanup
      loopback_id               (100)
      portchannel_id            (100)
      member_interface          (Ethernet8)
      ip_pools.loopback.*
      ip_pools.portchannel.*
      testcases.2.1.*
      testcases.2.2.*
"""

# Negative testcases: VRF binding blocked by existing L3 config on Loopback/PortChannel.

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import pytest
import yaml

from spytest import SpyTestDict, st

VAR_FILE_ENV = "VRF_LOOPBACK_PORTCHANNEL_NEG_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "system"
    / "vrf"
    / "vars_vrf_loopback_portchannel_negative.yaml"
)


# ---------------------------------------------------------------------------
# Module-level YAML loader
# ---------------------------------------------------------------------------

def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(
            f"VRF loopback/portchannel negative variable file not found: {candidate}"
        )

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError(
            "vars_vrf_loopback_portchannel_negative.yaml must contain key 'testcases'"
        )

    return content


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

@pytest.mark.topology("any")
class TestVrfLoopbackPortchannelNegative:
    """
    Negative testcases: VRF forwarding is blocked when the target logical
    interface (Loopback or PortChannel) already carries an IP address.
    """

    data = SpyTestDict()

    # ------------------------------------------------------------------
    # Class-level setup / teardown
    # ------------------------------------------------------------------

    @classmethod
    def setup_class(cls) -> None:
        """Load YAML configuration and resolve topology handles."""
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        min_topology = defaults.get("min_topology") or ["D1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))

        cli_type_raw = defaults.get("cli_type", "klish")
        cls.data.cli_type = cli_type_raw if isinstance(cli_type_raw, str) else "klish"

        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Resource-tracking lists for class-level teardown
        cls.data.configured_vrfs: List[str] = []
        cls.data.configured_loopbacks: List[int] = []
        cls.data.configured_portchannels: List[int] = []
        cls.data.configured_ips: List[Dict[str, str]] = []

        # Resolve DUT handle
        cls.data.dut: Optional[str] = None
        if hasattr(topology, "D1"):
            cls.data.dut = topology.D1
        else:
            dut_names = st.get_dut_names()
            if dut_names:
                cls.data.dut = dut_names[0]

        if not cls.data.dut:
            st.error("No DUT found in topology")

        cls.data.dut_names = st.get_dut_names()

        # Top-level YAML values (may be overridden per testcase)
        cls.data.loopback_id = int(config.get("loopback_id", 100))
        cls.data.portchannel_id = int(config.get("portchannel_id", 100))
        cls.data.member_interface = config.get("member_interface", "Ethernet8")
        cls.data.ip_pools = SpyTestDict(config.get("ip_pools", {}))

        # Disable pagination to prevent --more-- prompt from breaking output parsing
        st.log("Setting terminal length to 0 to disable CLI pagination")
        st.show(
            cls.data.dut,
            "terminal length 0",
            type=cls.data.cli_type,
            skip_tmpl=True,
            skip_error_check=True,
        )

        st.log(
            f"Setup complete. DUT={cls.data.dut}  CLI={cls.data.cli_type}  "
            f"Loopback ID={cls.data.loopback_id}  "
            f"PortChannel ID={cls.data.portchannel_id}  "
            f"Member={cls.data.member_interface}"
        )

    @classmethod
    def teardown_class(cls) -> None:
        """Remove all test resources tracked across the suite."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled – skipping class-level resource removal")
            return
        cls._cleanup_all_resources()

    # ------------------------------------------------------------------
    # Per-test setup / teardown
    # ------------------------------------------------------------------

    def setup_method(self) -> None:
        """Reset per-test bookkeeping collections."""
        self._test_vrfs: List[str] = []
        self._test_loopbacks: List[int] = []
        self._test_portchannels: List[int] = []
        self._test_ips: List[Dict[str, str]] = []
        self._ensure_terminal_length()

    def teardown_method(self) -> None:
        """Remove any resources the current testcase configured."""
        if not self.data.cleanup_enabled:
            self._test_vrfs = []
            self._test_loopbacks = []
            self._test_portchannels = []
            self._test_ips = []
            return

        st.log("Starting per-test cleanup")

        # IPs first (before deleting the interface they sit on)
        while self._test_ips:
            ip_cfg = self._test_ips.pop()
            self._remove_ip_from_interface(
                ip_cfg["interface"], ip_cfg["ip"], ip_cfg["subnet"]
            )
            if ip_cfg in self.data.configured_ips:
                self.data.configured_ips.remove(ip_cfg)

        # PortChannels
        while self._test_portchannels:
            pc_id = self._test_portchannels.pop()
            self._delete_portchannel(pc_id)
            if pc_id in self.data.configured_portchannels:
                self.data.configured_portchannels.remove(pc_id)

        # Loopbacks
        while self._test_loopbacks:
            lb_id = self._test_loopbacks.pop()
            self._delete_loopback(lb_id)
            if lb_id in self.data.configured_loopbacks:
                self.data.configured_loopbacks.remove(lb_id)

        # VRFs last
        while self._test_vrfs:
            vrf_name = self._test_vrfs.pop()
            self._remove_vrf(vrf_name)
            if vrf_name in self.data.configured_vrfs:
                self.data.configured_vrfs.remove(vrf_name)

    # ------------------------------------------------------------------
    # Class-level cleanup helper
    # ------------------------------------------------------------------

    @classmethod
    def _cleanup_all_resources(cls) -> None:
        """Best-effort removal of all resources created during the suite."""
        st.log("Starting class-level cleanup")

        # IPs
        while cls.data.configured_ips:
            ip_cfg = cls.data.configured_ips.pop()
            try:
                cmds = [
                    f"interface {ip_cfg['interface']}",
                    f"no ip address {ip_cfg['ip']}/{ip_cfg['subnet']}",
                    "exit",
                ]
                st.config(cls.data.dut, cmds, type=cls.data.cli_type, skip_error_check=True)
            except Exception as exc:
                st.log(f"IP cleanup error: {exc}")

        # PortChannels
        while cls.data.configured_portchannels:
            pc_id = cls.data.configured_portchannels.pop()
            try:
                cmd = f"no interface PortChannel {pc_id}"
                st.config(cls.data.dut, cmd, type=cls.data.cli_type, skip_error_check=True)
            except Exception as exc:
                st.log(f"PortChannel cleanup error: {exc}")

        # Loopbacks
        while cls.data.configured_loopbacks:
            lb_id = cls.data.configured_loopbacks.pop()
            try:
                cmd = f"no interface Loopback {lb_id}"
                st.config(cls.data.dut, cmd, type=cls.data.cli_type, skip_error_check=True)
            except Exception as exc:
                st.log(f"Loopback cleanup error: {exc}")

        # VRFs
        while cls.data.configured_vrfs:
            vrf_name = cls.data.configured_vrfs.pop()
            try:
                cmd = f"no ip vrf {vrf_name}"
                st.config(cls.data.dut, cmd, type=cls.data.cli_type, skip_error_check=True)
            except Exception as exc:
                st.log(f"VRF cleanup error: {exc}")

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _ensure_terminal_length(self) -> None:
        """Set terminal length 0 to prevent --more-- pagination interrupts."""
        try:
            st.show(
                self.data.dut,
                "terminal length 0",
                type=self.data.cli_type,
                skip_tmpl=True,
                skip_error_check=True,
            )
        except Exception as exc:
            st.log(f"Note: terminal length set failed (non-critical): {exc}")

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Fetch a testcase definition from the loaded YAML data."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for '{tcid}' in YAML")
        return testcase

    def _get_used_ips(self) -> List[str]:
        """
        Return a list of IP addresses (without prefix length) currently
        configured on the DUT, parsed from 'show ip interface' output.
        """
        output = st.show(
            self.data.dut,
            "show ip interface",
            type=self.data.cli_type,
            skip_tmpl=True,
            skip_error_check=True,
        )
        used: List[str] = []
        if not output:
            return used
        for line in output.splitlines():
            for token in line.split():
                if "/" in token and "." in token:
                    ip_only = token.split("/")[0]
                    if ip_only not in used:
                        used.append(ip_only)
        st.log(f"Currently used IPs: {used}")
        return used

    def _find_available_ip(self, pool_name: str) -> Tuple[str, str]:
        """
        Return (ip_address, subnet) for the first unused IP in the named pool.
        Checks the DUT's 'show ip interface' output to detect conflicts.
        """
        pool = self.data.ip_pools.get(pool_name, {})
        primary_ip: str = pool.get("primary", "")
        subnet: str = str(pool.get("subnet", "24"))
        fallback_ips: List[str] = pool.get("fallback", [])

        self._ensure_terminal_length()
        used_ips = self._get_used_ips()

        if primary_ip and primary_ip not in used_ips:
            st.log(f"Using primary IP {primary_ip}/{subnet} from pool '{pool_name}'")
            return primary_ip, subnet

        for entry in fallback_ips:
            if "/" in entry:
                fb_ip, fb_subnet = entry.split("/", 1)
            else:
                fb_ip, fb_subnet = entry, subnet
            if fb_ip not in used_ips:
                st.log(f"Using fallback IP {fb_ip}/{fb_subnet} from pool '{pool_name}'")
                return fb_ip, fb_subnet

        st.report_fail(
            "msg",
            f"No available IP in pool '{pool_name}' – all candidates are in use.",
        )

    # ------------------------------------------------------------------
    # VRF helpers
    # ------------------------------------------------------------------

    def _vrf_exists(self, vrf_name: str) -> bool:
        """Return True if the named VRF is already present on the DUT."""
        output = st.show(
            self.data.dut,
            "show ip vrf",
            type=self.data.cli_type,
            skip_tmpl=True,
            skip_error_check=True,
        )
        return bool(output and vrf_name in output)

    def _create_vrf(self, vrf_name: str) -> None:
        """
        Create a VRF if it does not already exist and track it for cleanup.
        Handles the 'mgmt' VRF without skipping cleanup tracking.
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        # Remove first to ensure a fresh, clean VRF
        if self._vrf_exists(vrf_name):
            st.log(f"VRF '{vrf_name}' exists – removing to recreate fresh")
            st.config(dut, f"no ip vrf {vrf_name}", type=cli_type, skip_error_check=True)
            st.wait(1)

        st.log(f"Creating VRF '{vrf_name}'")
        output = st.config(dut, f"ip vrf {vrf_name}", type=cli_type, skip_error_check=False)

        if output and ("Error" in output or "error" in output):
            st.report_fail("msg", f"Failed to create VRF '{vrf_name}': {output}")

        if vrf_name not in self._test_vrfs:
            self._test_vrfs.append(vrf_name)
        if vrf_name not in self.data.configured_vrfs:
            self.data.configured_vrfs.append(vrf_name)

        st.log(f"VRF '{vrf_name}' created successfully")

    def _remove_vrf(self, vrf_name: str) -> None:
        """Delete a VRF, suppressing errors (best-effort cleanup)."""
        dut = self.data.dut
        cli_type = self.data.cli_type
        st.log(f"Removing VRF '{vrf_name}'")
        try:
            st.config(dut, f"no ip vrf {vrf_name}", type=cli_type, skip_error_check=True)
            st.log(f"VRF '{vrf_name}' removed")
        except Exception as exc:
            st.log(f"Error removing VRF '{vrf_name}': {exc}")

    # ------------------------------------------------------------------
    # Loopback helpers
    # ------------------------------------------------------------------

    def _create_loopback_with_ip(
        self, loopback_id: int, ip_addr: str, subnet: str
    ) -> None:
        """
        Create Loopback<loopback_id>, assign ip_addr/subnet, and bring it up.
        Performs a pre-creation cleanup to guarantee a fresh state.
        """
        dut = self.data.dut
        cli_type = self.data.cli_type
        lb_intf = f"Loopback{loopback_id}"

        # Pre-cleanup: delete the loopback in case it was left from a prior run
        st.log(f"Pre-cleanup: removing {lb_intf} if it exists")
        st.config(
            dut,
            f"no interface Loopback {loopback_id}",
            type=cli_type,
            skip_error_check=True,
        )
        st.wait(1)

        st.log(f"Creating {lb_intf} with IP {ip_addr}/{subnet}")
        cmds = [
            f"interface Loopback {loopback_id}",
            f"ip address {ip_addr}/{subnet}",
            "no shutdown",
            "exit",
        ]
        result = st.config(dut, cmds, type=cli_type, skip_error_check=False)

        if result and ("Error" in result or "error" in result):
            st.report_fail(
                "msg",
                f"Failed to configure {lb_intf} with IP {ip_addr}/{subnet}: {result}",
            )

        # Track for cleanup
        if loopback_id not in self._test_loopbacks:
            self._test_loopbacks.append(loopback_id)
        if loopback_id not in self.data.configured_loopbacks:
            self.data.configured_loopbacks.append(loopback_id)

        ip_cfg = {"interface": lb_intf, "ip": ip_addr, "subnet": subnet}
        if ip_cfg not in self._test_ips:
            self._test_ips.append(ip_cfg)
        if ip_cfg not in self.data.configured_ips:
            self.data.configured_ips.append(ip_cfg)

        st.log(f"{lb_intf} configured successfully with IP {ip_addr}/{subnet}")

    def _verify_loopback_ip(self, loopback_id: int, ip_addr: str) -> bool:
        """Return True if ip_addr appears on Loopback<loopback_id> in 'show ip interface'."""
        lb_intf = f"Loopback{loopback_id}"
        output = st.show(
            self.data.dut,
            "show ip interface",
            type=self.data.cli_type,
            skip_tmpl=True,
            skip_error_check=True,
        )
        found = bool(output and lb_intf in output and ip_addr in output)
        if found:
            st.log(f"Verified: IP {ip_addr} is present on {lb_intf}")
        else:
            st.log(f"Verification failed: IP {ip_addr} NOT found on {lb_intf}")
        return found

    def _delete_loopback(self, loopback_id: int) -> None:
        """Remove Loopback<loopback_id>, suppressing errors."""
        st.log(f"Deleting Loopback {loopback_id}")
        try:
            st.config(
                self.data.dut,
                f"no interface Loopback {loopback_id}",
                type=self.data.cli_type,
                skip_error_check=True,
            )
            st.log(f"Loopback {loopback_id} deleted")
        except Exception as exc:
            st.log(f"Error deleting Loopback {loopback_id}: {exc}")

    # ------------------------------------------------------------------
    # PortChannel helpers
    # ------------------------------------------------------------------

    def _clean_member_interface(self, interface: str) -> None:
        """
        Prepare a physical interface for PortChannel membership:
          - Remove from any existing PortChannel (no channel-group)
          - Remove any IP address
          - Remove from switchport/VLAN
          - Ensure it is up
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log(f"Cleaning member interface {interface} before PortChannel creation")
        cmds = [
            f"interface {interface}",
            "no channel-group",          # detach from any existing LAG
            "no switchport access Vlan", # remove from any VLAN
            "no ip address",             # remove any IP address
            "no shutdown",
            "exit",
        ]
        st.config(dut, cmds, type=cli_type, skip_error_check=True)
        st.wait(1)

    def _create_portchannel_with_ip(
        self, portchannel_id: int, member_interface: str, ip_addr: str, subnet: str
    ) -> None:
        """
        Build PortChannel<portchannel_id>:
          1. Clean the member physical interface
          2. Remove existing PortChannel (if any) to start fresh
          3. Add physical interface as PortChannel member
          4. Bring up PortChannel
          5. Assign ip_addr/subnet to PortChannel

        Steps mirror the test procedure in vrf_functionality.md TC 2.
        """
        dut = self.data.dut
        cli_type = self.data.cli_type
        pc_intf = f"PortChannel{portchannel_id}"

        # Step 1: Clean member interface
        self._clean_member_interface(member_interface)

        # Step 2: Remove existing PortChannel to ensure clean state
        st.log(f"Pre-cleanup: removing {pc_intf} if it exists")
        st.config(
            dut,
            f"no interface PortChannel {portchannel_id}",
            type=cli_type,
            skip_error_check=True,
        )
        st.wait(1)

        # Step 3: Add physical interface as PortChannel member
        st.log(f"Adding {member_interface} to PortChannel {portchannel_id}")
        cmds = [
            f"interface {member_interface}",
            f"channel-group {portchannel_id}",
            "no shutdown",
            "exit",
        ]
        result = st.config(dut, cmds, type=cli_type, skip_error_check=False)
        if result and ("Error" in result or "error" in result):
            st.report_fail(
                "msg",
                f"Failed to add {member_interface} to PortChannel {portchannel_id}: {result}",
            )

        # Step 4: Bring up PortChannel
        st.log(f"Bringing up {pc_intf}")
        cmds = [
            f"interface PortChannel {portchannel_id}",
            "no shutdown",
            "exit",
        ]
        st.config(dut, cmds, type=cli_type, skip_error_check=True)
        st.wait(2)

        # Step 5: Assign IP to PortChannel
        st.log(f"Assigning IP {ip_addr}/{subnet} to {pc_intf}")
        cmds = [
            f"interface PortChannel {portchannel_id}",
            f"ip address {ip_addr}/{subnet}",
            "exit",
        ]
        result = st.config(dut, cmds, type=cli_type, skip_error_check=False)
        if result and ("Error" in result or "error" in result):
            st.report_fail(
                "msg",
                f"Failed to assign IP {ip_addr}/{subnet} to {pc_intf}: {result}",
            )

        # Track for cleanup
        if portchannel_id not in self._test_portchannels:
            self._test_portchannels.append(portchannel_id)
        if portchannel_id not in self.data.configured_portchannels:
            self.data.configured_portchannels.append(portchannel_id)

        ip_cfg = {"interface": pc_intf, "ip": ip_addr, "subnet": subnet}
        if ip_cfg not in self._test_ips:
            self._test_ips.append(ip_cfg)
        if ip_cfg not in self.data.configured_ips:
            self.data.configured_ips.append(ip_cfg)

        st.log(f"{pc_intf} created with member {member_interface} and IP {ip_addr}/{subnet}")

    def _verify_portchannel_ip(self, portchannel_id: int, ip_addr: str) -> bool:
        """Return True if ip_addr appears on PortChannel<portchannel_id>."""
        pc_intf = f"PortChannel{portchannel_id}"
        output = st.show(
            self.data.dut,
            "show ip interface",
            type=self.data.cli_type,
            skip_tmpl=True,
            skip_error_check=True,
        )
        found = bool(output and pc_intf in output and ip_addr in output)
        if found:
            st.log(f"Verified: IP {ip_addr} is present on {pc_intf}")
        else:
            st.log(f"Verification failed: IP {ip_addr} NOT found on {pc_intf}")
        return found

    def _delete_portchannel(self, portchannel_id: int) -> None:
        """Remove PortChannel<portchannel_id> and its member bindings."""
        dut = self.data.dut
        cli_type = self.data.cli_type
        st.log(f"Deleting PortChannel {portchannel_id}")
        try:
            # Detach member first
            member = self.data.member_interface
            cmds = [
                f"interface {member}",
                "no channel-group",
                "exit",
            ]
            st.config(dut, cmds, type=cli_type, skip_error_check=True)
            # Delete PortChannel
            st.config(
                dut,
                f"no interface PortChannel {portchannel_id}",
                type=cli_type,
                skip_error_check=True,
            )
            st.log(f"PortChannel {portchannel_id} deleted")
        except Exception as exc:
            st.log(f"Error deleting PortChannel {portchannel_id}: {exc}")

    # ------------------------------------------------------------------
    # IP cleanup helper
    # ------------------------------------------------------------------

    def _remove_ip_from_interface(
        self, interface: str, ip_addr: str, subnet: str
    ) -> None:
        """Remove a specific IP/prefix from an interface, suppressing errors."""
        st.log(f"Removing IP {ip_addr}/{subnet} from {interface}")
        try:
            cmds = [
                f"interface {interface}",
                f"no ip address {ip_addr}/{subnet}",
                "exit",
            ]
            st.config(
                self.data.dut, cmds, type=self.data.cli_type, skip_error_check=True
            )
        except Exception as exc:
            st.log(f"Error removing IP from {interface}: {exc}")

    # ------------------------------------------------------------------
    # VRF binding attempt (the negative action under test)
    # ------------------------------------------------------------------

    def _attempt_vrf_binding(
        self, vrf_name: str, interface_type: str, interface_id: str
    ) -> Tuple[bool, str]:
        """
        Attempt 'ip vrf forwarding <vrf_name>' on the given interface.
        This is expected to FAIL when the interface carries an IP address.

        Args:
            interface_type: klish interface keyword, e.g. "Loopback" or "PortChannel"
            interface_id:   numeric part, e.g. "100"

        Returns:
            (binding_succeeded: bool, raw_output: str)
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        full_intf = f"{interface_type}{interface_id}"
        st.log(
            f"Attempting 'ip vrf forwarding {vrf_name}' on {full_intf} "
            f"(expected to be REJECTED)"
        )

        cmds_str = (
            f"interface {interface_type} {interface_id}\n"
            f"ip vrf forwarding {vrf_name}\n"
            "exit"
        )

        try:
            output = st.config(
                dut,
                cmds_str,
                type=cli_type,
                conf=True,
                skip_error_check=True,
            )
        except Exception as exc:
            st.log(f"Exception during VRF binding attempt: {exc}")
            output = str(exc)

        st.log(f"VRF binding raw output: {output}")

        binding_succeeded = bool(
            output and "Error" not in output and "error" not in output
        )
        if binding_succeeded:
            st.log("WARNING: VRF binding was ACCEPTED – this is a test FAILURE")
        else:
            st.log("VRF binding was rejected as expected (Error detected in output)")

        return binding_succeeded, output

    def _verify_error_message(self, output: str, expected_substring: str) -> bool:
        """Return True when expected_substring is present in output."""
        st.log(f"Checking output for expected error: '{expected_substring}'")
        if expected_substring in output:
            st.log("Expected error message confirmed in output")
            return True
        st.log(f"Expected error NOT found. Actual output:\n{output}")
        return False

    # ------------------------------------------------------------------
    # TC 2.1 – Loopback interface
    # ------------------------------------------------------------------

    @pytest.mark.inventory(feature="Regression", testcases=["VRF_Loopback_TC2.1"])
    @pytest.mark.negative
    def test_vrf_forwarding_restriction_loopback_with_ip(self) -> None:
        """
        TC 2.1 – VRF forwarding blocked on Loopback interface with IP.

        Steps:
          1. Cleanup: remove Loopback100 if present
          2. VRF prep: remove then recreate VRF 'mgmt'
          3. Create Loopback100; assign an available IP/32 (conflict-checked)
          4. Bring interface up
          5. Attempt: ip vrf forwarding mgmt  on Loopback 100
          6. Assert: system returns
               '% Error: L3 Configuration exists for Interface: Loopback100'
        """
        st.banner("TC 2.1: VRF forwarding restriction on Loopback with IP (negative)")

        testcase = self._get_testcase("2.1")
        loopback_id: int = int(testcase.get("loopback_id", self.data.loopback_id))
        vrf_name: str = testcase.get("vrf_name", "mgmt")
        expected_error: str = testcase.get("expected_error", "L3 Configuration exists")

        st.log(f"TC: {testcase.get('title')}")
        st.log(f"Desc: {testcase.get('description')}")
        st.log(
            f"Loopback ID={loopback_id}  VRF='{vrf_name}'  "
            f"Expected error='{expected_error}'"
        )

        # Step 1: VRF preparation – recreate fresh
        self._create_vrf(vrf_name)
        st.wait(2)

        # Step 2: Find an available IP for the Loopback
        ip_addr, subnet = self._find_available_ip("loopback")

        # Step 3 & 4: Create Loopback with IP
        self._create_loopback_with_ip(loopback_id, ip_addr, subnet)
        st.wait(3)

        # Step 5: Verify the IP is present before the negative test
        if not self._verify_loopback_ip(loopback_id, ip_addr):
            st.report_fail(
                "msg",
                f"Pre-condition failed: IP {ip_addr} not found on Loopback{loopback_id}",
            )

        # Step 6: Attempt VRF binding – must be REJECTED
        succeeded, output = self._attempt_vrf_binding(
            vrf_name, "Loopback", str(loopback_id)
        )

        if succeeded:
            st.report_fail(
                "msg",
                f"VRF binding ACCEPTED but should have FAILED. "
                f"Loopback{loopback_id} has IP {ip_addr}/{subnet} configured.",
            )

        # Step 7: Confirm the correct error message
        if not self._verify_error_message(output, expected_error):
            st.report_fail(
                "msg",
                f"Expected error '{expected_error}' not found in output. "
                f"Actual output: {output}",
            )

        st.log("TC 2.1 PASSED: VRF binding correctly rejected on Loopback with IP")
        st.report_pass("test_case_passed")

    # ------------------------------------------------------------------
    # TC 2.2 – PortChannel interface
    # ------------------------------------------------------------------

    @pytest.mark.inventory(feature="Regression", testcases=["VRF_PortChannel_TC2.2"])
    @pytest.mark.negative
    def test_vrf_forwarding_restriction_portchannel_with_ip(self) -> None:
        """
        TC 2.2 – VRF forwarding blocked on PortChannel interface with IP.

        Steps:
          1. VRF prep: ensure Vrf111 exists (create fresh)
          2. Cleanup: detach member and remove PortChannel100 if present
          3. Clean Ethernet8: remove from any channel-group, VLAN, or IP
          4. Create PortChannel100; add Ethernet8 as member
          5. Assign available IP/24 to PortChannel100 (conflict-checked)
          6. Attempt: ip vrf forwarding Vrf111  on PortChannel 100
          7. Assert: system returns
               '% Error: L3 Configuration exists for Interface: PortChannel100'
        """
        st.banner("TC 2.2: VRF forwarding restriction on PortChannel with IP (negative)")

        testcase = self._get_testcase("2.2")
        portchannel_id: int = int(testcase.get("portchannel_id", self.data.portchannel_id))
        vrf_name: str = testcase.get("vrf_name", "Vrf111")
        member_interface: str = testcase.get("member_interface", self.data.member_interface)
        expected_error: str = testcase.get("expected_error", "L3 Configuration exists")

        st.log(f"TC: {testcase.get('title')}")
        st.log(f"Desc: {testcase.get('description')}")
        st.log(
            f"PortChannel ID={portchannel_id}  Member={member_interface}  "
            f"VRF='{vrf_name}'  Expected error='{expected_error}'"
        )

        # Step 1: VRF preparation
        self._create_vrf(vrf_name)
        st.wait(2)

        # Step 2: Find available IP for PortChannel
        ip_addr, subnet = self._find_available_ip("portchannel")

        # Steps 3–5: Build PortChannel with member and IP
        self._create_portchannel_with_ip(portchannel_id, member_interface, ip_addr, subnet)
        st.wait(3)

        # Step 6: Verify IP is present before the negative test
        if not self._verify_portchannel_ip(portchannel_id, ip_addr):
            st.report_fail(
                "msg",
                f"Pre-condition failed: IP {ip_addr} not found on "
                f"PortChannel{portchannel_id}",
            )

        # Step 7: Attempt VRF binding – must be REJECTED
        succeeded, output = self._attempt_vrf_binding(
            vrf_name, "PortChannel", str(portchannel_id)
        )

        if succeeded:
            st.report_fail(
                "msg",
                f"VRF binding ACCEPTED but should have FAILED. "
                f"PortChannel{portchannel_id} has IP {ip_addr}/{subnet} configured.",
            )

        # Step 8: Confirm the correct error message
        if not self._verify_error_message(output, expected_error):
            st.report_fail(
                "msg",
                f"Expected error '{expected_error}' not found in output. "
                f"Actual output: {output}",
            )

        st.log("TC 2.2 PASSED: VRF binding correctly rejected on PortChannel with IP")
        st.report_pass("test_case_passed")
