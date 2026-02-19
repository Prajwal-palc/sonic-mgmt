"""
IPV6 INTERFACE STATUS CONSISTENCY
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \\
  --testbed ./testbeds/ztp_standalone.yaml  \\
  tests/system/interface/test_ipv6_interface_status_consistency.py \\
  --logs-path ./logs/ipv6_intf_status_$(date +%F_%H%M%S) \\
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Validates IPv6 interface operational-status reporting consistency across
  three different SONiC show commands for both Loopback and physical Ethernet
  interfaces. Specifically:

  TC 1  (Loopback Status Consistency, IPv4 vs IPv6)
        Creates Loopback100 with an IPv4 address and verifies that:
          • show interface Loopback 100   → Admin/Oper Up/Up  (authoritative)
          • show ipv6 interfaces          → Up/Up after IPv6 assignment
          • show ip interfaces            → expected Up/Up; documents a known
                                            SONiC reporting discrepancy if the
                                            Protocol column shows Down instead.

  TC 2  (Physical Interface Pre-check and Abort Logic)
        Resets Ethernet8 to a clean L2 state, then checks whether its
        Admin/Oper status is Up/Up.  If not Up/Up the test is marked as
        skipped (pytest.skip) and TC 3 is also skipped automatically, to
        prevent false positives on an uncabled port.

  TC 3  (IPv6 Assignment and Status Verification on Physical Interface)
        Prerequisite: TC 2 must complete without skip.
        Assigns an IPv6 address to Ethernet8 and asserts that
        show ipv6 interfaces reports Up/Up for that interface.

Pre-requisites:
  - Topology: standalone (single DUT) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node (standalone)
        # +-------------------------------+
        # |          dut1                 |
        # |       (smic_sonic1)           |
        # |  Loopback100       (TC 1)     |
        # |  Ethernet8  (cabled)  (TC 2-3)|
        # +-------------------------------+
        # Note: Ethernet8 must be physically cabled or have a loopback
        # plug for TC 2 to pass and TC 3 to execute.

  - Feature flags / min SONiC version: IPv6 enabled; Loopback support present
  - Required test variables (YAML):
      vars/system/interface/vars_ipv6_interface_status.yaml
    Keys used:
      defaults.cli_type               (klish)
      defaults.verify_timeout
      defaults.cleanup
      loopback_id                     (100)
      physical_interface              (Ethernet8)
      ip_pools.loopback_ipv4.*
      ip_pools.loopback_ipv6.*
      ip_pools.physical_ipv6.*
      testcases.1.*  testcases.2.*  testcases.3.*
"""

# Test cases for IPv6 interface status consistency validation.

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.ip as ip_api
import apis.system.interface as intf_api

VAR_FILE_ENV = "IPV6_INTF_STATUS_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "system"
    / "interface"
    / "vars_ipv6_interface_status.yaml"
)

# Expected status string that indicates a healthy interface
_STATUS_UP_UP = "up/up"

# Sentinel: set to True by TC 2 when the physical port is confirmed Up/Up
_TC2_PASSED_FLAG = "tc2_physical_link_up"


# ---------------------------------------------------------------------------
# Module-level YAML loader
# ---------------------------------------------------------------------------

def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(
            f"IPv6 interface status variable file not found: {candidate}"
        )

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError(
            "vars_ipv6_interface_status.yaml must contain key 'testcases'"
        )

    return content


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

@pytest.mark.topology("any")
class TestIPv6InterfaceStatusConsistency:
    """
    Validates IPv6 interface status consistency across 'show ip interfaces',
    'show interface <name>', and 'show ipv6 interfaces' for Loopback and
    physical Ethernet interfaces.
    """

    data = SpyTestDict()

    # ------------------------------------------------------------------
    # Class-level setup / teardown
    # ------------------------------------------------------------------

    @classmethod
    def setup_class(cls) -> None:
        """Load YAML configuration and initialize topology handles."""
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

        # Resource-tracking for teardown
        cls.data.configured_loopbacks: List[int] = []
        cls.data.configured_ips: List[Dict[str, str]] = []

        # Inter-test flag: TC 3 needs TC 2 to confirm the physical link is up
        cls.data[_TC2_PASSED_FLAG] = False

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

        # Top-level YAML topology parameters
        cls.data.loopback_id = int(config.get("loopback_id", 100))
        cls.data.physical_interface = config.get("physical_interface", "Ethernet8")
        cls.data.ip_pools = SpyTestDict(config.get("ip_pools", {}))

        # Disable pagination globally
        st.log("Setting terminal length 0 to disable CLI pagination")
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
            f"Physical={cls.data.physical_interface}"
        )

    @classmethod
    def teardown_class(cls) -> None:
        """Remove all resources created during the suite."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled – skipping class teardown")
            return
        cls._cleanup_all_resources()

    # ------------------------------------------------------------------
    # Per-test setup / teardown
    # ------------------------------------------------------------------

    def setup_method(self) -> None:
        """Reset per-test bookkeeping."""
        self._test_loopbacks: List[int] = []
        self._test_ips: List[Dict[str, str]] = []
        self._ensure_terminal_length()

    def teardown_method(self) -> None:
        """Remove resources created by the current test."""
        if not self.data.cleanup_enabled:
            self._test_loopbacks = []
            self._test_ips = []
            return

        st.log("Per-test teardown starting")

        while self._test_ips:
            ip_cfg = self._test_ips.pop()
            self._remove_ip_from_interface(
                ip_cfg["interface"], ip_cfg["ip"],
                ip_cfg["subnet"], ip_cfg.get("family", "ipv4"),
            )
            if ip_cfg in self.data.configured_ips:
                self.data.configured_ips.remove(ip_cfg)

        while self._test_loopbacks:
            lb_id = self._test_loopbacks.pop()
            self._delete_loopback(lb_id)
            if lb_id in self.data.configured_loopbacks:
                self.data.configured_loopbacks.remove(lb_id)

    # ------------------------------------------------------------------
    # Class-level cleanup
    # ------------------------------------------------------------------

    @classmethod
    def _cleanup_all_resources(cls) -> None:
        """Best-effort cleanup of all suite-level resources."""
        st.log("Class-level cleanup starting")

        while cls.data.configured_ips:
            ip_cfg = cls.data.configured_ips.pop()
            family = ip_cfg.get("family", "ipv4")
            prefix_cmd = "ip" if family == "ipv4" else "ipv6"
            try:
                cmds = [
                    f"interface {ip_cfg['interface']}",
                    f"no {prefix_cmd} address {ip_cfg['ip']}/{ip_cfg['subnet']}",
                    "exit",
                ]
                st.config(
                    cls.data.dut, cmds,
                    type=cls.data.cli_type, skip_error_check=True,
                )
            except Exception as exc:
                st.log(f"IP cleanup error: {exc}")

        while cls.data.configured_loopbacks:
            lb_id = cls.data.configured_loopbacks.pop()
            try:
                st.config(
                    cls.data.dut,
                    f"no interface Loopback {lb_id}",
                    type=cls.data.cli_type, skip_error_check=True,
                )
            except Exception as exc:
                st.log(f"Loopback cleanup error: {exc}")

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _ensure_terminal_length(self) -> None:
        """Prevent --more-- pagination from breaking output parsing."""
        try:
            st.show(
                self.data.dut, "terminal length 0",
                type=self.data.cli_type,
                skip_tmpl=True, skip_error_check=True,
            )
        except Exception as exc:
            st.log(f"terminal length set failed (non-critical): {exc}")

    def _get_testcase(self, tcid: str) -> Dict[str, Any]:
        """Fetch a testcase definition by ID from the loaded YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for '{tcid}' in YAML")
        return testcase

    def _get_used_ips(self, family: str = "ipv4") -> List[str]:
        """
        Return IP addresses already configured on the DUT (without prefix).
        Parses 'show ip interface' or 'show ipv6 interface' raw output.
        """
        command = "show ip interface" if family == "ipv4" else "show ipv6 interface"
        output: str = st.show(
            self.data.dut, command,
            type=self.data.cli_type,
            skip_tmpl=True, skip_error_check=True,
        ) or ""

        used: List[str] = []
        for token in output.split():
            if "/" in token and ("." in token or ":" in token):
                ip_only = token.split("/")[0].strip(",")
                if ip_only and ip_only not in used:
                    used.append(ip_only)
        return used

    def _find_available_ip(
        self, pool_name: str, family: str = "ipv4"
    ) -> Tuple[str, str]:
        """
        Return (ip_address, subnet) for the first unused IP in the named pool.
        Uses 'show ip interface' / 'show ipv6 interface' for conflict detection.
        """
        pool = self.data.ip_pools.get(pool_name, {})
        primary_ip: str = pool.get("primary", "")
        subnet: str = str(pool.get("subnet", "24"))
        fallbacks: List[str] = pool.get("fallback", [])

        self._ensure_terminal_length()
        used = self._get_used_ips(family)
        st.log(f"Used {family} IPs: {used}")

        if primary_ip and primary_ip not in used:
            st.log(f"Using primary {family} {primary_ip}/{subnet} from '{pool_name}'")
            return primary_ip, subnet

        for entry in fallbacks:
            if "/" in entry:
                fb_ip, fb_subnet = entry.split("/", 1)
            else:
                fb_ip, fb_subnet = entry, subnet
            if fb_ip not in used:
                st.log(f"Using fallback {family} {fb_ip}/{fb_subnet} from '{pool_name}'")
                return fb_ip, fb_subnet

        st.report_fail(
            "msg",
            f"No available {family} IP in pool '{pool_name}' – all candidates in use.",
        )

    # ------------------------------------------------------------------
    # IP address helpers
    # ------------------------------------------------------------------

    def _configure_ip_on_interface(
        self,
        interface: str,
        ip_addr: str,
        subnet: str,
        family: str = "ipv4",
    ) -> None:
        """
        Assign ip_addr/subnet to interface using klish CLI.
        Delegates to the framework's config_ip_addr_interface API.
        Tracks the assignment for cleanup.
        """
        dut = self.data.dut
        cli_type = self.data.cli_type
        st.log(f"Configuring {family} {ip_addr}/{subnet} on {interface}")

        result = ip_api.config_ip_addr_interface(
            dut,
            interface_name=interface,
            ip_address=ip_addr,
            subnet=subnet,
            family=family,
            config="add",
            cli_type=cli_type,
        )
        if not result:
            st.report_fail(
                "msg",
                f"Failed to configure {family} {ip_addr}/{subnet} on {interface}",
            )

        ip_cfg = {"interface": interface, "ip": ip_addr, "subnet": subnet, "family": family}
        if ip_cfg not in self._test_ips:
            self._test_ips.append(ip_cfg)
        if ip_cfg not in self.data.configured_ips:
            self.data.configured_ips.append(ip_cfg)

        st.log(f"{family} {ip_addr}/{subnet} configured on {interface}")

    def _remove_ip_from_interface(
        self,
        interface: str,
        ip_addr: str,
        subnet: str,
        family: str = "ipv4",
    ) -> None:
        """Remove ip_addr/subnet from interface, suppressing errors."""
        dut = self.data.dut
        cli_type = self.data.cli_type
        st.log(f"Removing {family} {ip_addr}/{subnet} from {interface}")
        try:
            ip_api.delete_ip_interface(
                dut,
                interface_name=interface,
                ip_address=ip_addr,
                subnet=subnet,
                family=family,
                skip_error=True,
                cli_type=cli_type,
            )
        except Exception as exc:
            st.log(f"Error removing {family} IP from {interface}: {exc}")

    # ------------------------------------------------------------------
    # Loopback helpers
    # ------------------------------------------------------------------

    def _create_loopback(self, loopback_id: int) -> None:
        """
        Create Loopback<loopback_id> using klish CLI.
        Performs pre-cleanup to guarantee a fresh state.
        """
        dut = self.data.dut
        cli_type = self.data.cli_type
        lb_name = f"Loopback{loopback_id}"

        st.log(f"Pre-cleanup: removing {lb_name} if present")
        st.config(
            dut,
            f"no interface Loopback {loopback_id}",
            type=cli_type, skip_error_check=True,
        )
        st.wait(1)

        st.log(f"Creating {lb_name}")
        cmds = [
            f"interface Loopback {loopback_id}",
            "no shutdown",
            "exit",
        ]
        result = st.config(dut, cmds, type=cli_type, skip_error_check=False)
        if result and ("Error" in result or "error" in result):
            st.report_fail("msg", f"Failed to create {lb_name}: {result}")

        if loopback_id not in self._test_loopbacks:
            self._test_loopbacks.append(loopback_id)
        if loopback_id not in self.data.configured_loopbacks:
            self.data.configured_loopbacks.append(loopback_id)

        st.log(f"{lb_name} created")

    def _delete_loopback(self, loopback_id: int) -> None:
        """Delete Loopback<loopback_id>, suppressing errors."""
        st.log(f"Deleting Loopback {loopback_id}")
        try:
            st.config(
                self.data.dut,
                f"no interface Loopback {loopback_id}",
                type=self.data.cli_type, skip_error_check=True,
            )
        except Exception as exc:
            st.log(f"Error deleting Loopback {loopback_id}: {exc}")

    # ------------------------------------------------------------------
    # Status query helpers
    # ------------------------------------------------------------------

    def _get_status_from_show_ip_interface(self, interface: str) -> Optional[str]:
        """
        Return the combined Admin/Oper status string (e.g. 'up/up' or 'up/down')
        for *interface* as reported by 'show ip interface'.

        Uses get_interface_ip_address() which parses the command output into a
        list of dicts.  Each dict is expected to contain a 'status' field when
        the TextFSM template includes admin/oper columns, or we fall back to
        raw text inspection.
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        # API-based attempt (structured parse)
        entries = ip_api.get_interface_ip_address(
            dut, interface_name=interface, family="ipv4", cli_type=cli_type
        )
        if entries:
            for entry in entries:
                if entry.get("status"):
                    st.log(
                        f"show ip interface: {interface} status = {entry['status']}"
                    )
                    return str(entry["status"]).lower()

        # Fallback: raw text parsing
        raw: str = st.show(
            dut, "show ip interface",
            type=cli_type, skip_tmpl=True, skip_error_check=True,
        ) or ""
        for line in raw.splitlines():
            if interface in line:
                # Look for tokens that look like "up/up" or "up/down"
                for token in line.split():
                    if "/" in token and token.replace("/", "").replace("up", "").replace("down", "") == "":
                        status = token.lower()
                        st.log(
                            f"show ip interface (raw parse): {interface} status = {status}"
                        )
                        return status
        st.log(f"Could not determine status for {interface} from show ip interface")
        return None

    def _get_status_from_show_interface(self, interface: str) -> Optional[str]:
        """
        Return the combined Admin/Oper status string for *interface* as
        reported by 'show interface status'.

        Uses interface_status_show() which parses the output into dicts with
        'admin' and 'oper' keys.
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        entries = intf_api.interface_status_show(dut, interfaces=[interface], cli_type=cli_type)
        if entries:
            for entry in entries:
                admin = str(entry.get("admin", "")).lower()
                oper = str(entry.get("oper", "")).lower()
                if admin and oper:
                    combined = f"{admin}/{oper}"
                    st.log(f"show interface status: {interface} admin={admin} oper={oper}")
                    return combined

        # Fallback: parse 'show interface <name>' raw output
        raw: str = st.show(
            dut, f"show interface {interface}",
            type=cli_type, skip_tmpl=True, skip_error_check=True,
        ) or ""
        # klish format: "<intf> is up, line protocol is up"
        admin_state = "up" if " is up" in raw else ("down" if " is down" in raw else None)
        protocol_state = None
        if "line protocol is up" in raw:
            protocol_state = "up"
        elif "line protocol is down" in raw:
            protocol_state = "down"

        if admin_state and protocol_state:
            combined = f"{admin_state}/{protocol_state}"
            st.log(f"show interface (raw): {interface} = {combined}")
            return combined

        st.log(f"Could not determine status for {interface} from show interface")
        return None

    def _get_status_from_show_ipv6_interface(self, interface: str) -> Optional[str]:
        """
        Return the combined Admin/Oper status string for *interface* as
        reported by 'show ipv6 interface'.

        Uses get_interface_ip_address(family='ipv6') which internally calls
        prepare_show_ipv6_interface_output() for structured parsing.
        Fallback parses raw text.
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        entries = ip_api.get_interface_ip_address(
            dut, interface_name=interface, family="ipv6", cli_type=cli_type
        )
        if entries:
            for entry in entries:
                if entry.get("status"):
                    st.log(
                        f"show ipv6 interface: {interface} status = {entry['status']}"
                    )
                    return str(entry["status"]).lower()

        # Fallback: raw text parsing
        raw: str = st.show(
            dut, "show ipv6 interface",
            type=cli_type, skip_tmpl=True, skip_error_check=True,
        ) or ""
        for line in raw.splitlines():
            if interface in line:
                for token in line.split():
                    if "/" in token and token.replace("/", "").replace("up", "").replace("down", "") == "":
                        status = token.lower()
                        st.log(
                            f"show ipv6 interface (raw): {interface} status = {status}"
                        )
                        return status
        st.log(f"Could not determine status for {interface} from show ipv6 interface")
        return None

    def _verify_interface_link_up(self, interface: str) -> bool:
        """
        Return True when verify_interface_status confirms both admin and oper
        are 'up' for *interface*.  Uses the framework API for structured check.
        """
        admin_ok = intf_api.verify_interface_status(
            self.data.dut, interface, "admin", "up",
            cli_type=self.data.cli_type,
        )
        oper_ok = intf_api.verify_interface_status(
            self.data.dut, interface, "oper", "up",
            cli_type=self.data.cli_type,
        )
        result = bool(admin_ok and oper_ok)
        st.log(
            f"Interface {interface} up check: admin={admin_ok} oper={oper_ok} "
            f"combined={result}"
        )
        return result

    # ------------------------------------------------------------------
    # Physical interface helpers (TC 2 / TC 3)
    # ------------------------------------------------------------------

    def _clean_physical_interface(self, interface: str) -> None:
        """
        Reset *interface* to a bare L2 state:
          - Remove any IP / IPv6 address
          - Cycle shutdown → no shutdown to reset state
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log(f"Cleaning {interface}: removing IP/IPv6 and resetting link state")
        cmds = [
            f"interface {interface}",
            "no ip address",
            "no ipv6 address",
            "shutdown",
            "no shutdown",
            "exit",
        ]
        st.config(dut, cmds, type=cli_type, skip_error_check=True)
        st.wait(3)  # allow link to stabilise after shutdown/no-shutdown

    # ------------------------------------------------------------------
    # TC 1 – Loopback Status Consistency
    # ------------------------------------------------------------------

    @pytest.mark.inventory(feature="Regression", testcases=["IPv6_Intf_TC1"])
    def test_loopback_status_consistency(self) -> None:
        """
        TC 1 – Loopback Interface Status Consistency (IPv4 vs IPv6).

        Steps:
          1. Cleanup: remove Loopback100 if present
          2. Create Loopback100 + assign IPv4 (conflict-checked) + no shutdown
          3. Verify 'show ip interfaces' for Loopback100
             (should be up/up; documents discrepancy if up/down – known bug)
          4. Verify 'show interface Loopback 100' → must be up/up (authoritative)
          5. Assign IPv6 address (conflict-checked) to Loopback100
          6. Verify 'show ipv6 interfaces' for Loopback100 → must be up/up

        Pass criteria:
          Steps 4 and 6 must both report up/up.
          Step 3 is compared and any discrepancy is logged as a known bug;
          a mismatch in step 3 alone causes the test to FAIL to flag the issue.
        """
        st.banner("TC 1: Loopback Interface Status Consistency (IPv4 vs IPv6)")

        testcase = self._get_testcase("1")
        loopback_id: int = int(testcase.get("loopback_id", self.data.loopback_id))
        lb_name = f"Loopback{loopback_id}"

        st.log(f"TC: {testcase.get('title')}")
        st.log(f"Desc: {testcase.get('description')}")

        # ----------------------------------------------------------------
        # Step 1 & 2: Create Loopback with IPv4
        # ----------------------------------------------------------------
        self._create_loopback(loopback_id)

        ipv4_pool = testcase.get("ipv4_pool", "loopback_ipv4")
        ipv4_addr, ipv4_subnet = self._find_available_ip(ipv4_pool, family="ipv4")

        st.log(f"Step 2: Assigning IPv4 {ipv4_addr}/{ipv4_subnet} to {lb_name}")
        self._configure_ip_on_interface(lb_name, ipv4_addr, ipv4_subnet, family="ipv4")
        st.wait(3)

        # ----------------------------------------------------------------
        # Step 3: Verify 'show ip interfaces' (may show the known bug)
        # ----------------------------------------------------------------
        st.log(f"Step 3: Checking 'show ip interfaces' status for {lb_name}")
        ipv4_show_status = self._get_status_from_show_ip_interface(lb_name)
        st.log(f"  show ip interfaces → {lb_name} status: {ipv4_show_status}")

        # ----------------------------------------------------------------
        # Step 4: Verify 'show interface Loopback 100' (authoritative check)
        # ----------------------------------------------------------------
        st.log(f"Step 4: Checking 'show interface {lb_name}' status (authoritative)")
        detail_status = self._get_status_from_show_interface(lb_name)
        st.log(f"  show interface {lb_name} → status: {detail_status}")

        if detail_status != _STATUS_UP_UP:
            st.report_fail(
                "msg",
                f"Step 4 FAILED: {lb_name} detail status is '{detail_status}', "
                f"expected '{_STATUS_UP_UP}'. Interface is not up.",
            )
        st.log(f"Step 4 PASSED: {lb_name} shows {_STATUS_UP_UP} in detail view")

        # ----------------------------------------------------------------
        # Step 3 discrepancy detection
        # ----------------------------------------------------------------
        if ipv4_show_status and ipv4_show_status != _STATUS_UP_UP:
            st.log(
                f"KNOWN BUG DETECTED: 'show ip interfaces' reports {lb_name} as "
                f"'{ipv4_show_status}' while 'show interface {lb_name}' correctly "
                f"shows '{detail_status}'. This is a SONiC reporting discrepancy."
            )
            # The test marks FAIL to flag the discrepancy / reproduce the bug
            st.report_fail(
                "msg",
                f"Step 3 FAILED (Bug Reproduced): 'show ip interfaces' shows "
                f"'{ipv4_show_status}' for {lb_name} but the interface is actually "
                f"'{detail_status}'. IPv4 summary command reports incorrect oper status.",
            )
        else:
            st.log(
                f"Step 3 PASSED: 'show ip interfaces' correctly shows "
                f"'{ipv4_show_status}' for {lb_name}"
            )

        # ----------------------------------------------------------------
        # Step 5: Assign IPv6 to the same Loopback
        # ----------------------------------------------------------------
        ipv6_pool = testcase.get("ipv6_pool", "loopback_ipv6")
        ipv6_addr, ipv6_subnet = self._find_available_ip(ipv6_pool, family="ipv6")

        st.log(f"Step 5: Assigning IPv6 {ipv6_addr}/{ipv6_subnet} to {lb_name}")
        self._configure_ip_on_interface(lb_name, ipv6_addr, ipv6_subnet, family="ipv6")
        st.wait(3)

        # ----------------------------------------------------------------
        # Step 6: Verify 'show ipv6 interfaces'
        # ----------------------------------------------------------------
        st.log(f"Step 6: Checking 'show ipv6 interfaces' for {lb_name}")
        ipv6_show_status = self._get_status_from_show_ipv6_interface(lb_name)
        st.log(f"  show ipv6 interface → {lb_name} status: {ipv6_show_status}")

        if ipv6_show_status != _STATUS_UP_UP:
            st.report_fail(
                "msg",
                f"Step 6 FAILED: 'show ipv6 interfaces' reports {lb_name} as "
                f"'{ipv6_show_status}', expected '{_STATUS_UP_UP}'.",
            )
        st.log(f"Step 6 PASSED: {lb_name} shows {_STATUS_UP_UP} in 'show ipv6 interfaces'")

        st.log(
            f"TC 1 SUMMARY – {lb_name}:\n"
            f"  show ip interfaces:       {ipv4_show_status}\n"
            f"  show interface <name>:    {detail_status}\n"
            f"  show ipv6 interfaces:     {ipv6_show_status}"
        )
        st.report_pass("test_case_passed")

    # ------------------------------------------------------------------
    # TC 2 – Physical Interface Pre-check
    # ------------------------------------------------------------------

    @pytest.mark.inventory(feature="Regression", testcases=["IPv6_Intf_TC2"])
    def test_physical_interface_precheck(self) -> None:
        """
        TC 2 – Physical Interface Pre-check and Abort Logic.

        Steps:
          1. Reset Ethernet8: remove IPs, cycle shutdown/no-shutdown
          2. Check 'show interface status' for Admin and Oper columns
          3. If status is NOT up/up  → pytest.skip (aborts TC 3 as well)
          4. If status IS  up/up     → set class flag; report pass

        Note: TC 3 checks cls.data[_TC2_PASSED_FLAG] and skips itself if False.
        """
        st.banner("TC 2: Physical Interface Pre-check and Abort Logic")

        testcase = self._get_testcase("2")
        interface: str = testcase.get("interface", self.data.physical_interface)

        st.log(f"TC: {testcase.get('title')}")
        st.log(f"Desc: {testcase.get('description')}")
        st.log(f"Target interface: {interface}")

        # Step 1: Clean the interface to get raw L2 state
        st.log(f"Step 1: Cleaning {interface} to obtain raw L2 status")
        self._clean_physical_interface(interface)

        # Step 2: Check Admin/Oper status
        st.log(f"Step 2: Checking 'show interface status' for {interface}")
        link_status = self._get_status_from_show_interface(interface)
        st.log(f"  {interface} status: {link_status}")

        # Step 3: Abort if not up/up
        if link_status != _STATUS_UP_UP:
            reason = (
                f"TC 2 ABORTED: {interface} is not physically Up/Up "
                f"(status='{link_status}'). "
                f"Ensure the port is cabled or has a loopback plug. "
                f"TC 3 is skipped."
            )
            st.log(reason)
            self.data[_TC2_PASSED_FLAG] = False
            pytest.skip(reason)

        # Step 4: Physical link confirmed up/up
        self.data[_TC2_PASSED_FLAG] = True
        st.log(f"TC 2 PASSED: {interface} is Up/Up – proceeding to TC 3")
        st.report_pass("test_case_passed")

    # ------------------------------------------------------------------
    # TC 3 – IPv6 Assignment and Status Verification (Physical)
    # ------------------------------------------------------------------

    @pytest.mark.inventory(feature="Regression", testcases=["IPv6_Intf_TC3"])
    def test_physical_interface_ipv6_status(self) -> None:
        """
        TC 3 – IPv6 Assignment and Status Verification on Physical Interface.

        Prerequisites:
          TC 2 must complete without skip (physical link must be Up/Up).

        Steps:
          1. Prerequisite check: skip if TC 2 did not confirm Up/Up
          2. Assign IPv6 address to Ethernet8 (conflict-checked from pool)
          3. Verify 'show ipv6 interfaces' shows Ethernet8 as up/up
             with the correct address
        """
        st.banner("TC 3: IPv6 Assignment and Status Verification on Physical Interface")

        # Step 1: Prerequisite guard
        if not self.data.get(_TC2_PASSED_FLAG, False):
            reason = (
                "TC 3 SKIPPED: TC 2 pre-check did not confirm physical link Up/Up. "
                "Ensure Ethernet8 is cabled before running this test."
            )
            st.log(reason)
            pytest.skip(reason)

        testcase = self._get_testcase("3")
        interface: str = testcase.get("interface", self.data.physical_interface)
        ipv6_pool: str = testcase.get("ipv6_pool", "physical_ipv6")

        st.log(f"TC: {testcase.get('title')}")
        st.log(f"Desc: {testcase.get('description')}")
        st.log(f"Target interface: {interface}")

        # Step 2: Assign IPv6 address (conflict-checked)
        ipv6_addr, ipv6_subnet = self._find_available_ip(ipv6_pool, family="ipv6")
        st.log(f"Step 2: Assigning IPv6 {ipv6_addr}/{ipv6_subnet} to {interface}")

        self._configure_ip_on_interface(interface, ipv6_addr, ipv6_subnet, family="ipv6")
        st.wait(3)

        # Step 3: Verify Admin/Oper status via 'show ipv6 interfaces'
        st.log(f"Step 3: Checking 'show ipv6 interfaces' for {interface}")
        ipv6_status = self._get_status_from_show_ipv6_interface(interface)
        st.log(f"  show ipv6 interfaces → {interface} status: {ipv6_status}")

        if ipv6_status != _STATUS_UP_UP:
            st.report_fail(
                "msg",
                f"TC 3 FAILED: 'show ipv6 interfaces' reports {interface} as "
                f"'{ipv6_status}', expected '{_STATUS_UP_UP}'. "
                f"IPv6 address: {ipv6_addr}/{ipv6_subnet}.",
            )

        # Confirm the correct address is visible
        st.log(f"Step 3: Verifying IPv6 address {ipv6_addr} is present on {interface}")
        entries = ip_api.get_interface_ip_address(
            self.data.dut,
            interface_name=interface,
            family="ipv6",
            cli_type=self.data.cli_type,
        )
        addr_found = any(
            ipv6_addr in str(entry.get("ipaddr", ""))
            for entry in (entries or [])
        )
        if not addr_found:
            st.report_fail(
                "msg",
                f"TC 3 FAILED: IPv6 address {ipv6_addr} not visible in "
                f"'show ipv6 interfaces' for {interface}.",
            )

        st.log(
            f"TC 3 PASSED: {interface} shows {_STATUS_UP_UP} with "
            f"IPv6 {ipv6_addr}/{ipv6_subnet} in 'show ipv6 interfaces'"
        )
        st.report_pass("test_case_passed")
