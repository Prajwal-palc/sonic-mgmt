"""
VRF CONFIGURATION AND CONNECTIVITY (PING)
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/ztp_standalone.yaml  \
  tests/routing/vrf/test_vrf_ping.py \
  --logs-path ./logs/test_vrf_ping_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Validates VRF configuration and connectivity on a standalone SONiC DUT.
  TC_VRF_01 checks that a VRF bound to a physical interface persists in both
  'show ip vrf' and 'show running-configuration'.
  TC_VRF_02 extends the same scenario by assigning an IP address inside the VRF
  and verifying zero-loss local ping within that VRF context.
  Full pre-condition cleanup runs before each test and idempotent teardown runs
  after every test method, leaving the DUT in a clean state.

Pre-requisites:
  - Topology: Standalone (D1 only) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node
        # +--------------------+
        # |     smic_sonic1    |
        # |   Ethernet368      |
        # +--------------------+

  - Minimum SONiC version: any with klish (IS-CLI) enabled
  - Required test variables (YAML): vars/routing/vrf/vars_vrf_ping.yaml
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.ip as ip_api
import apis.routing.vrf as vrf_api
import apis.system.switch_configuration as sw_cfg_api

# ---------------------------------------------------------------------------
# YAML variable file path
# ---------------------------------------------------------------------------
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "routing"
    / "vrf"
    / "vars_vrf_ping.yaml"
)

# ---------------------------------------------------------------------------
# Test Case IDs
# ---------------------------------------------------------------------------
TC_IDS = SpyTestDict(
    {
        "vrf_config_persistence": "TC_VRF_01",
        "vrf_connectivity_ping":  "TC_VRF_02",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML."""
    if not DEFAULT_VAR_FILE.is_file():
        raise FileNotFoundError(
            f"VRF variable file not found: {DEFAULT_VAR_FILE}"
        )
    with DEFAULT_VAR_FILE.open(encoding="utf-8") as fh:
        content = yaml.safe_load(fh) or {}
    if "testcases" not in content:
        raise ValueError("VRF YAML must contain key 'testcases'")
    return content


def _klish_intf_cmd(intf: str) -> str:
    """
    Convert an interface name like 'Ethernet368' or 'PortChannel10' into
    the klish 'interface <type> <number>' command string.

    klish requires a space between the type keyword and the port number,
    e.g. 'interface Ethernet 368'.  A simple regex split on the boundary
    between letters and digits handles all standard SONiC interface names
    without importing the internal API helper get_interface_number_from_name.
    """
    match = re.match(r"^([A-Za-z]+)(\d+.*)$", intf)
    if match:
        return "interface {} {}".format(match.group(1), match.group(2))
    # Fallback – let klish reject it with skip_error_check=True
    return "interface {}".format(intf)


def _safe_delete_ip(dut: str, intf: str, ip_address: str, subnet: str, cli_type: str) -> None:
    """
    Remove a specific IP address from an interface, ignoring errors.

    For klish: uses 'configure terminal' → interface sub-mode → 'no ip address'
    sequence executed via st.config with conf=True so the framework handles
    the transition from any session state (Exec or Config mode).

    For non-klish: delegates to ip_api.delete_ip_interface.
    """
    if cli_type != "klish":
        try:
            ip_api.delete_ip_interface(
                dut, intf, ip_address, subnet,
                family="ipv4", cli_type=cli_type, skip_error=True,
            )
        except Exception:  # noqa: BLE001
            pass
        return

    try:
        command = [
            _klish_intf_cmd(intf),
            "no ip address {}/{}".format(ip_address, subnet),
            "exit",
        ]
        st.config(dut, command, type="klish", conf=True, skip_error_check=True)
    except Exception:  # noqa: BLE001
        pass


def _safe_delete_any_ip(dut: str, intf: str, cli_type: str) -> None:
    """
    Remove ALL IP addresses currently assigned to an interface, ignoring errors.

    Used by pre-condition cleanup to clear any existing L3 config (e.g. a
    default-VRF IP like 10.0.0.4/31) before attempting 'ip vrf forwarding'.
    SONiC rejects VRF binding when L3 configuration already exists:
      % Error: L3 Configuration exists for Interface: <intf>

    For klish: issues 'no ip address' (no arguments) in interface sub-mode,
    which removes all IPv4 addresses in one command.
    For non-klish: reads current IPs via get_interface_ip_address and removes
    each one individually.
    """
    if cli_type != "klish":
        try:
            entries = ip_api.get_interface_ip_address(
                dut, interface_name=intf, family="ipv4", cli_type=cli_type
            ) or []
            for entry in entries:
                ip_cidr = entry.get("ipaddr", "")
                if "/" in ip_cidr:
                    ip_addr, subnet = ip_cidr.split("/", 1)
                    ip_api.delete_ip_interface(
                        dut, intf, ip_addr, subnet,
                        family="ipv4", cli_type=cli_type, skip_error=True,
                    )
        except Exception:  # noqa: BLE001
            pass
        return

    try:
        command = [
            _klish_intf_cmd(intf),
            "no ip address",
            "exit",
        ]
        st.config(dut, command, type="klish", conf=True, skip_error_check=True)
    except Exception:  # noqa: BLE001
        pass


def _safe_unbind(dut: str, vrf_name: str, intf: str, cli_type: str) -> None:
    """
    Remove VRF binding from interface, ignoring errors.

    For klish: uses 'configure terminal' → interface sub-mode →
    'no ip vrf forwarding' sequence via st.config with conf=True so the
    framework handles the transition from any session state (Exec or
    Config mode).

    For non-klish: delegates to vrf_api.bind_vrf_interface.
    """
    if cli_type != "klish":
        try:
            vrf_api.bind_vrf_interface(
                dut,
                vrf_name=vrf_name,
                intf_name=intf,
                config="no",
                cli_type=cli_type,
                skip_error=True,
            )
        except Exception:  # noqa: BLE001
            pass
        return

    try:
        command = [
            _klish_intf_cmd(intf),
            "no ip vrf forwarding {}".format(vrf_name),
            "exit",
        ]
        st.config(dut, command, type="klish", conf=True, skip_error_check=True)
    except Exception:  # noqa: BLE001
        pass


def _safe_delete_vrf(dut: str, vrf_name: str, cli_type: str) -> None:
    """Delete a VRF instance, ignoring errors."""
    try:
        vrf_api.config_vrf(
            dut,
            vrf_name=vrf_name,
            config="no",
            cli_type=cli_type,
            skip_error=True,
        )
    except Exception:  # noqa: BLE001
        pass


def _get_bound_vrf_for_interface(dut: str, intf: str, cli_type: str) -> List[str]:
    """
    Return list of VRF names that have 'intf' bound to them.
    Uses 'show ip vrf' parsed output (interfaces field is a list).

    NOTE: This function is intentionally NOT called during _full_cleanup
    because issuing 'show ip vrf' via st.show() while the klish session
    is already active causes the framework to send 'exit' to leave klish
    exec mode, but the prompt transition (--sonic-mgmt--# → admin@sonic:~$)
    is not what the framework expects, resulting in:
      OSError: Prompt Not Detected in DF 2.0: '--sonic-mgmt--#'
    Cleanup uses the known-VRF list (Step 3) which is idempotent and
    avoids any show command in klish context.
    """
    bound_vrfs: List[str] = []
    try:
        output = st.show(dut, "show ip vrf", type=cli_type)
        for entry in output:
            vrf_n = entry.get("vrfname", "")
            if not vrf_n or vrf_n == "default":
                continue
            intfs = entry.get("interfaces", [])
            # interfaces is always a list from the TextFSM template
            if isinstance(intfs, list) and intf in intfs:
                bound_vrfs.append(vrf_n)
            elif isinstance(intfs, str) and intf == intfs:
                bound_vrfs.append(vrf_n)
    except Exception:  # noqa: BLE001
        pass
    return bound_vrfs


def _get_ips_on_interface(dut: str, intf: str, cli_type: str) -> List[Dict[str, str]]:
    """Return list of {ip, subnet} dicts currently assigned to the interface."""
    result: List[Dict[str, str]] = []
    try:
        entries = ip_api.get_interface_ip_address(
            dut, interface_name=intf, family="ipv4", cli_type=cli_type
        )
        for entry in (entries or []):
            ip_cidr = entry.get("ipaddr", "")
            if "/" in ip_cidr:
                ip_addr, subnet = ip_cidr.split("/", 1)
                result.append({"ip": ip_addr, "subnet": subnet})
    except Exception:  # noqa: BLE001
        pass
    return result


def _verify_ip_on_interface(dut: str, intf: str, ip_cidr: str, vrf_name: str, cli_type: str) -> bool:
    """
    Verify IP address and VRF assignment on an interface.

    Uses 'show ip interfaces | no-more' for klish to avoid --more-- pagination
    that causes OSError: Prompt Not Detected when the output spans many lines.
    Falls back to 'show ip interface' for non-klish CLI types.

    Parsed TextFSM fields (show_ip_interfaces.tmpl): interface, ipaddr, vrf.
    """
    try:
        cmd = "show ip interfaces | no-more" if cli_type == "klish" else "show ip interface"
        output = st.show(dut, cmd, type=cli_type)
        if not output:
            st.log(f"No output from '{cmd}'")
            return False
        for entry in output:
            if (entry.get("interface") == intf
                    and entry.get("ipaddr") == ip_cidr
                    and entry.get("vrf", "") == vrf_name):
                return True
        st.log(
            f"Expected interface={intf}, ipaddr={ip_cidr}, vrf={vrf_name}. "
            f"Not found in '{cmd}' output."
        )
        return False
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Test Class
# ---------------------------------------------------------------------------

@pytest.mark.topology("any")
class TestVrfPing:
    """
    Suite covering VRF configuration persistence and local-ping connectivity.

    TC_VRF_01 - Verify VRF binding appears in 'show ip vrf' and
                'show running-configuration'.
    TC_VRF_02 - Verify VRF-bound interface IP is reachable via
                'ping vrf <vrf> <ip>' with 0% packet loss.
    """

    data = SpyTestDict()

    # ------------------------------------------------------------------
    # Class-level setup / teardown
    # ------------------------------------------------------------------

    @classmethod
    def setup_class(cls) -> None:
        """Load topology, YAML config, and perform pre-condition cleanup."""
        st.banner("SETUP_CLASS: TestVrfPing - start")

        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        min_topology = defaults.get("min_topology") or ["D1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.topology = topology
        cls.data.dut = topology.D1
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))

        # Per-test bookkeeping – reset in setup_method / teardown_method
        cls.data.active_vrf = None
        cls.data.active_intf = None
        cls.data.active_ip = None
        cls.data.active_subnet = None

        st.banner("SETUP_CLASS: TestVrfPing - complete")

    @classmethod
    def teardown_class(cls) -> None:
        """Safety cleanup after the entire suite."""
        st.banner("TEARDOWN_CLASS: TestVrfPing - start")
        if cls.data.cleanup_enabled:
            cls._full_cleanup()
        st.banner("TEARDOWN_CLASS: TestVrfPing - complete")

    # ------------------------------------------------------------------
    # Method-level setup / teardown
    # ------------------------------------------------------------------

    def setup_method(self) -> None:
        """Pre-condition cleanup + reset per-test tracking before each test."""
        self.data.active_vrf = None
        self.data.active_intf = None
        self.data.active_ip = None
        self.data.active_subnet = None
        # Run pre-condition cleanup before every test
        self._full_cleanup()

    def teardown_method(self) -> None:
        """Remove configuration created by the test method (config mode safe)."""
        if not self.data.cleanup_enabled:
            return
        st.banner("TEARDOWN_METHOD: cleaning up VRF test residue")
        dut = self.data.dut
        cli_type = self.data.cli_type

        # No pre-flight session reset needed: all cleanup helpers below use
        # st.config with conf=True which makes the klish framework enter
        # 'configure terminal' automatically from any session state
        # (Exec mode, Config mode, or interface-config sub-mode).
        # Sending 'end' or 'exit' before cleanup would only leave the session
        # in Exec mode (--sonic-mgmt--#) where conf=True still re-enters
        # config — so the extra step adds no value and risks the
        # OSError: Prompt Not Detected crash if 'exit' is accidentally used.

        # 1. Remove IP first (must happen before VRF unbind)
        if self.data.active_ip and self.data.active_intf and self.data.active_subnet:
            st.log(
                f"Removing IP {self.data.active_ip}/{self.data.active_subnet} "
                f"from {self.data.active_intf}"
            )
            _safe_delete_ip(
                dut,
                self.data.active_intf,
                self.data.active_ip,
                self.data.active_subnet,
                cli_type,
            )

        # 2. Unbind interface from VRF
        if self.data.active_vrf and self.data.active_intf:
            st.log(f"Unbinding {self.data.active_intf} from VRF {self.data.active_vrf}")
            _safe_unbind(dut, self.data.active_vrf, self.data.active_intf, cli_type)

        # 3. Delete VRF
        if self.data.active_vrf:
            st.log(f"Deleting VRF {self.data.active_vrf}")
            _safe_delete_vrf(dut, self.data.active_vrf, cli_type)

        self.data.active_vrf = None
        self.data.active_intf = None
        self.data.active_ip = None
        self.data.active_subnet = None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @classmethod
    def _full_cleanup(cls) -> None:
        """
        Idempotent cleanup for known test VRFs and their interface bindings.

        Steps (all use st.config with conf=True — safe from any session state):
          1a. Remove ALL IPs from the test interface (clears pre-existing
              default-VRF addresses like 10.0.0.4/31; SONiC rejects VRF
              binding with "L3 Configuration exists for Interface" when any
              IP is present on the interface).
          1b. Remove known test IPs individually (idempotent safety net).
          2.  Unbind test interface from each known test VRF.
          3.  Delete each known test VRF.
        Order: IP removal → unbind → VRF delete — required by SONiC.

        Design note — why no dynamic 'show ip vrf' discovery:
          Calling st.show(dut, "show ip vrf", type="klish") during cleanup
          (setup_method / teardown_class) causes the framework to send 'exit'
          to leave the klish Exec mode session.  The prompt transition
          (--sonic-mgmt--# → admin@sonic:~$) is not what the framework
          expects while returning to mgmt-user, resulting in:
            OSError: Prompt Not Detected in DF 2.0: '--sonic-mgmt--#'
          Using the fixed known-VRF list with skip_error=True is idempotent
          and avoids any show command in a live klish session context.
        """
        dut = cls.data.dut
        cli_type = cls.data.cli_type
        tc1 = cls.data.testcases.get("TC_VRF_01", {})
        tc2 = cls.data.testcases.get("TC_VRF_02", {})
        interface = tc1.get("interface", "Ethernet368")

        # Known IP addresses used by test cases (skip_error makes these idempotent)
        known_ips = [
            {
                "ip": tc2.get("ip_address", "10.0.2.1"),
                "subnet": str(tc2.get("subnet", "24")),
            },
        ]
        known_vrfs = [
            tc1.get("vrf_name", "Vrftest"),
            tc2.get("vrf_name", "Vrfping"),
        ]

        # Step 1a – Remove ALL IPs from the interface (covers pre-existing
        # default-VRF addresses like 10.0.0.4/31 that SONiC refuses to
        # overwrite when binding a VRF: "L3 Configuration exists for Interface")
        st.log(f"Pre-cleanup: removing all IPs from {interface} (if any)")
        _safe_delete_any_ip(dut, interface, cli_type)

        # Step 1b – Also explicitly remove known test IPs (idempotent safety)
        for ip_entry in known_ips:
            st.log(
                f"Pre-cleanup: removing IP {ip_entry['ip']}/{ip_entry['subnet']} "
                f"from {interface} (if assigned)"
            )
            _safe_delete_ip(dut, interface, ip_entry["ip"], ip_entry["subnet"], cli_type)

        # Step 2 – Unbind interface from each known VRF
        for vrf_name in known_vrfs:
            st.log(f"Pre-cleanup: unbinding {interface} from VRF {vrf_name} (if bound)")
            _safe_unbind(dut, vrf_name, interface, cli_type)

        # Step 3 – Delete known VRFs
        for vrf_name in known_vrfs:
            st.log(f"Pre-cleanup: deleting VRF {vrf_name} (if exists)")
            _safe_delete_vrf(dut, vrf_name, cli_type)

    def _get_testcase(self, tcid: str) -> Dict[str, Any]:
        """Fetch testcase definition from YAML, fail immediately if missing."""
        tc = self.data.testcases.get(tcid)
        if not tc:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return tc

    def _verify_vrf_and_interface(self, dut: str, vrf_name: str, interface: str, cli_type: str) -> bool:
        """
        Verify VRF exists AND interface is listed under it.
        Uses a single get_vrf_verbose call — it checks existence and returns the
        interface binding list in one 'show ip vrf' execution, avoiding the
        redundant second call that verify_vrf would add.
        """
        # Single call: existence + interface binding together
        vrf_data = vrf_api.get_vrf_verbose(dut, vrfname=vrf_name, cli_type=cli_type)
        if not vrf_data:
            st.log(f"VRF {vrf_name} not found in 'show ip vrf'")
            return False

        bound_intfs = vrf_data.get("interfaces", [])
        if interface not in bound_intfs:
            st.log(
                f"Interface {interface} not found in VRF {vrf_name} interfaces: "
                f"{bound_intfs}"
            )
            return False

        st.log(f"Verified: VRF {vrf_name} exists with {interface} bound to it")
        return True

    # ------------------------------------------------------------------
    # TC_VRF_01 – VRF Configuration Persistence
    # ------------------------------------------------------------------

    @pytest.mark.inventory(feature="VRF", testcases=["TC_VRF_01"])
    def test_vrf_config_persistence(self) -> None:
        """
        TC_VRF_01 – Create VRF 'Vrftest', bind Ethernet368, and verify:
          1. 'show ip vrf' lists Vrftest with Ethernet368 in the Interfaces column.
          2. 'show running-configuration interface Ethernet368' contains
             'ip vrf forwarding Vrftest'.
        """
        st.banner("TC_VRF_01: VRF Configuration Persistence - start")
        dut = self.data.dut
        cli_type = self.data.cli_type
        tc = self._get_testcase(TC_IDS.vrf_config_persistence)

        vrf_name = tc.get("vrf_name", "Vrftest")
        interface = tc.get("interface", "Ethernet368")

        # Track for teardown
        self.data.active_vrf = vrf_name
        self.data.active_intf = interface

        # Step 1 – Create VRF
        st.log(f"Step 1: Creating VRF {vrf_name}")
        if not vrf_api.config_vrf(dut, vrf_name=vrf_name, config="yes", cli_type=cli_type):
            st.report_tc_fail(TC_IDS.vrf_config_persistence, "msg",
                              f"Failed to create VRF {vrf_name}")

        # Step 2 – Bind interface to VRF
        st.log(f"Step 2: Binding {interface} to VRF {vrf_name}")
        if not vrf_api.bind_vrf_interface(
            dut, vrf_name=vrf_name, intf_name=interface, config="yes", cli_type=cli_type
        ):
            st.report_tc_fail(TC_IDS.vrf_config_persistence, "msg",
                              f"Failed to bind {interface} to VRF {vrf_name}")

        # Step 3 – Verify 'show ip vrf' (single call — binding is immediate)
        st.log(f"Step 3: Verifying 'show ip vrf' shows {vrf_name} with {interface}")
        if not self._verify_vrf_and_interface(dut, vrf_name, interface, cli_type):
            st.report_tc_fail(
                TC_IDS.vrf_config_persistence, "msg",
                f"'show ip vrf' did not show VRF {vrf_name} with interface {interface}"
            )

        # Step 4 – Verify running-configuration contains VRF forwarding line
        st.log(
            f"Step 4: Verifying running-config interface {interface} "
            f"contains 'ip vrf forwarding {vrf_name}'"
        )
        if not sw_cfg_api.verify_show_running_configuration(
            dut,
            sub_cmd=f"interface {interface}",
            match_pattern_list=[f"ip vrf forwarding {vrf_name}"],
            cli_type=cli_type,
        ):
            st.report_tc_fail(
                TC_IDS.vrf_config_persistence, "msg",
                f"Running-config missing 'ip vrf forwarding {vrf_name}' "
                f"under interface {interface}"
            )

        st.report_tc_pass(TC_IDS.vrf_config_persistence, "test_case_passed")
        st.banner("TC_VRF_01: VRF Configuration Persistence - PASS")
        st.report_pass("test_case_passed")

    # ------------------------------------------------------------------
    # TC_VRF_02 – VRF Connectivity via Ping
    # ------------------------------------------------------------------

    @pytest.mark.inventory(feature="VRF", testcases=["TC_VRF_02"])
    def test_vrf_connectivity_ping(self) -> None:
        """
        TC_VRF_02 – Create VRF 'Vrfping', bind Ethernet368, assign 10.0.2.1/24, and verify:
          1. 'show ip interfaces' lists the IP address and VRF correctly.
          2. 'ping vrf Vrfping 10.0.2.1' completes with 0% packet loss.
        """
        st.banner("TC_VRF_02: VRF Connectivity Ping - start")
        dut = self.data.dut
        cli_type = self.data.cli_type
        tc = self._get_testcase(TC_IDS.vrf_connectivity_ping)

        vrf_name = tc.get("vrf_name", "Vrfping")
        interface = tc.get("interface", "Ethernet368")
        ip_address = tc.get("ip_address", "10.0.2.1")
        subnet = str(tc.get("subnet", "24"))
        ping_target = tc.get("ping_target", ip_address)
        ping_count = int(tc.get("ping_count", 5))

        # Track for teardown
        self.data.active_vrf = vrf_name
        self.data.active_intf = interface
        self.data.active_ip = ip_address
        self.data.active_subnet = subnet

        # Step 1 – Create VRF
        st.log(f"Step 1: Creating VRF {vrf_name}")
        if not vrf_api.config_vrf(dut, vrf_name=vrf_name, config="yes", cli_type=cli_type):
            st.report_tc_fail(TC_IDS.vrf_connectivity_ping, "msg",
                              f"Failed to create VRF {vrf_name}")

        # Step 2 – Bind interface to VRF
        st.log(f"Step 2: Binding {interface} to VRF {vrf_name}")
        if not vrf_api.bind_vrf_interface(
            dut, vrf_name=vrf_name, intf_name=interface, config="yes", cli_type=cli_type
        ):
            st.report_tc_fail(TC_IDS.vrf_connectivity_ping, "msg",
                              f"Failed to bind {interface} to VRF {vrf_name}")

        # Step 3 – Assign IP address
        st.log(f"Step 3: Assigning IP {ip_address}/{subnet} to {interface}")
        if not ip_api.config_ip_addr_interface(
            dut,
            interface_name=interface,
            ip_address=ip_address,
            subnet=subnet,
            family="ipv4",
            config="add",
            cli_type=cli_type,
        ):
            st.report_tc_fail(TC_IDS.vrf_connectivity_ping, "msg",
                              f"Failed to assign IP {ip_address}/{subnet} to {interface}")

        # Step 4 – Verify 'show ip interfaces' shows IP and VRF
        # Uses _verify_ip_on_interface which sends 'show ip interfaces | no-more'
        # for klish to avoid --more-- pagination causing OSError: Prompt Not Detected.
        st.log(
            f"Step 4: Verifying 'show ip interfaces | no-more' shows "
            f"{ip_address}/{subnet} with VRF {vrf_name} on {interface}"
        )
        if not st.poll_wait(
            _verify_ip_on_interface,
            self.data.verify_timeout,
            dut,
            interface,
            f"{ip_address}/{subnet}",
            vrf_name,
            cli_type,
        ):
            st.report_tc_fail(
                TC_IDS.vrf_connectivity_ping, "msg",
                f"'show ip interfaces' does not show {ip_address}/{subnet} "
                f"with VRF {vrf_name} on {interface}"
            )

        # Step 5 – Ping within VRF context, expect 0% packet loss
        st.log(f"Step 5: Pinging {ping_target} within VRF {vrf_name}")
        if not ip_api.ping(
            dut,
            ping_target,
            family="ipv4",
            interface=vrf_name,
            count=ping_count,
            cli_type=cli_type,
        ):
            st.report_tc_fail(
                TC_IDS.vrf_connectivity_ping, "msg",
                f"Ping to {ping_target} via 'ping vrf {vrf_name}' failed "
                f"(expected 0% packet loss)"
            )

        st.report_tc_pass(TC_IDS.vrf_connectivity_ping, "test_case_passed")
        st.banner("TC_VRF_02: VRF Connectivity Ping - PASS")
        st.report_pass("test_case_passed")
