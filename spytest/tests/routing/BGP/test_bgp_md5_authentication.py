"""
BGP MD5 AUTHENTICATION (IPv4/IPv6) - Test ID 2.4.6
Author: QA Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2node.yaml  \
  tests/routing/BGP/test_bgp_md5_authentication.py \
  --logs-path ./logs/test_bgp_md5_authentication_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Comprehensive validation of BGP MD5/TCP-AO authentication for both IPv4 and IPv6 sessions.
  Tests verify that BGP sessions establish only when MD5 passwords match on both peers,
  and fail when passwords mismatch or are asymmetrically configured. Includes positive tests
  (matching keys), negative tests (mismatched keys, asymmetric configuration), and coordinated
  key rotation scenarios. Supports eBGP and iBGP with both direct peering and multihop loopback-based
  configurations. The test suite uses SpyTest BGP APIs with password parameters to configure MD5
  authentication, validates session state via 'show ip bgp summary', and ensures complete cleanup.
  Supports klish (sonic-cli) mode as specified in the test plan.

Pre-requisites:
  - Topology: t0/t1/any | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 2 nodes
        # +----------------------+                   +----------------------+
        # |   D1 (smic_sonic1)   |===================|   D2 (smic_sonic2)   |
        # |   AS 65001/65002     |     Ethernet4     |   AS 65002/65001     |
        # |   IPv4: 10.0.0.1/30  |                   |   IPv4: 10.0.0.2/30  |
        # |   IPv6: 2001:db8::1  |                   |   IPv6: 2001:db8::2  |
        # |   Lo0: 1.1.1.1/32    |                   |   Lo0: 2.2.2.2/32    |
        # +----------------------+                   +----------------------+

  - Feature flags / min SONiC version: BGP with MD5 authentication support required
  - Required test variables (YAML): vars_bgp_md5_authentication.yaml
    - defaults.cli_type (klish recommended for BGP MD5)
    - defaults.verify_timeout (90 seconds recommended)
    - defaults.cleanup (true for cleanup after tests)
    - defaults.min_topology (D1D2:1)
    - defaults.md5_ok (good password: bgpSecret1!)
    - defaults.md5_bad (wrong password: bgpSecret2!)
    - testcases.* definitions for all 6 sub-testcases (2.4.6.1 - 2.4.6.6)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import time

import pytest
import yaml

from spytest import SpyTestDict, st

import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api

VAR_FILE_ENV = "BGP_246_VAR_FILE"


def _candidate_var_files() -> List[Path]:
    """Return candidate YAML paths in search order."""
    candidates: List[Path] = []
    override = st.getenv(VAR_FILE_ENV)
    if override:
        candidates.append(Path(override))

    project_root = Path(__file__).resolve().parents[3]
    candidates.append(project_root / "vars" / "routing" / "bgp" / "vars_bgp_md5_authentication.yaml")
    candidates.append(Path(__file__).resolve().with_name("vars_bgp_md5_authentication.yaml"))
    return candidates


def _load_yaml_data() -> SpyTestDict:
    """Load testcase variables from the first available YAML file."""
    attempted: List[Path] = []
    for candidate in _candidate_var_files():
        attempted.append(candidate)
        if candidate.is_file():
            with candidate.open(encoding="utf-8") as handle:
                return SpyTestDict(yaml.safe_load(handle) or {})

    attempted_paths = ", ".join(str(path) for path in attempted)
    st.report_fail("msg", f"BGP 2.4.6 variable file not found. Checked: {attempted_paths}")
    return SpyTestDict()


def _iter_candidate_duts(topology: SpyTestDict) -> Iterable[str]:
    """Yield topology keys that resemble DUT aliases (D1, D2, ...)."""
    for key, value in topology.items():
        if key.upper().startswith("D") and value:
            yield key


@pytest.mark.topology("any")
class TestBgpMd5Authentication:
    """Testcases for validating BGP MD5/TCP-AO authentication - Test ID 2.4.6."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Load YAML configuration, topology, and defaults."""
        config = _load_yaml_data()
        defaults = SpyTestDict(config.get("defaults", {}))
        testcases = SpyTestDict(config.get("testcases", {}))

        min_topology = defaults.get("min_topology") or ["D1D2:1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = config
        cls.data.defaults = defaults
        cls.data.testcases = testcases
        cls.data.topology = topology
        cls.data.dut_names = st.get_dut_names()
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 90))
        cls.data.md5_ok = defaults.get("md5_ok", "bgpSecret1!")
        cls.data.md5_bad = defaults.get("md5_bad", "bgpSecret2!")
        cls.data.keepalive = int(defaults.get("keepalive", 60))
        cls.data.hold = int(defaults.get("hold", 180))

        cli_types_raw = defaults.get("cli_type", "klish")
        if isinstance(cli_types_raw, str):
            cli_types = [ct.strip().lower() for ct in cli_types_raw.split(",") if ct.strip()]
        elif isinstance(cli_types_raw, list):
            cli_types = [str(ct).strip().lower() for ct in cli_types_raw if ct]
        else:
            cli_types = ["klish"]

        cls.data.cli_types = cli_types
        cls.data.cleanup = bool(defaults.get("cleanup", True))
        cls.data.dut_map = SpyTestDict()

        for alias in _iter_candidate_duts(topology):
            cls.data.dut_map[alias] = getattr(topology, alias)

    def setup_method(self) -> None:
        """Initialize per-test tracking and preconditions."""
        self._configured_interfaces: List[SpyTestDict] = []
        self._configured_loopbacks: List[SpyTestDict] = []
        self._configured_static_routes: List[SpyTestDict] = []
        self._configured_neighbors: List[SpyTestDict] = []
        self._configured_routers: List[SpyTestDict] = []

    def teardown_method(self) -> None:
        """Cleanup all dynamic configuration pushed during the test."""
        if not self.data.get("cleanup", True):
            return

        # Remove BGP neighbors
        while self._configured_neighbors:
            entry = self._configured_neighbors.pop()
            self._remove_bgp_neighbor(entry)

        # Remove BGP routers
        while self._configured_routers:
            router = self._configured_routers.pop()
            self._remove_bgp_router(router)

        # Remove static routes
        while self._configured_static_routes:
            route = self._configured_static_routes.pop()
            self._remove_static_route(route)

        # Remove loopback IPs
        while self._configured_loopbacks:
            lb = self._configured_loopbacks.pop()
            self._remove_loopback_ip(lb)

        # Remove interface IPs
        while self._configured_interfaces:
            iface = self._configured_interfaces.pop()
            self._remove_interface_ip(iface)

    def _resolve_dut(self, alias: str | None) -> str | None:
        """Translate a topology alias (e.g., D1) to the framework DUT handle."""
        if not alias:
            return None
        if alias in self.data.dut_map:
            return self.data.dut_map[alias]
        if alias in self.data.dut_names:
            return alias
        st.warn(f"Unable to resolve DUT alias '{alias}'")
        return None

    def _configure_interface_ip(self, config: SpyTestDict) -> None:
        """Configure an IP address (IPv4 or IPv6) on an interface."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in interface config: {config}")

        interface = config.get("interface")
        ip_address = config.get("ip_address")
        prefix_length = config.get("prefix_length")
        family = config.get("family", "ipv4")
        cli_type = config.get("cli_type", "klish")

        result = ip_api.config_ip_addr_interface(
            dut,
            interface_name=interface,
            ip_address=ip_address,
            subnet=str(prefix_length),
            family=family,
            config="add",
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure IP {ip_address}/{prefix_length} on {dut}:{interface}")

        self._configured_interfaces.append(config)
        st.log(f"Configured {family} address {ip_address}/{prefix_length} on {dut}:{interface}")

    def _remove_interface_ip(self, config: SpyTestDict) -> None:
        """Remove an IP address from an interface."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        interface = config.get("interface")
        ip_address = config.get("ip_address")
        prefix_length = config.get("prefix_length")
        family = config.get("family", "ipv4")
        cli_type = config.get("cli_type", "klish")

        ip_api.config_ip_addr_interface(
            dut,
            interface_name=interface,
            ip_address=ip_address,
            subnet=str(prefix_length),
            family=family,
            config="remove",
            cli_type=cli_type,
        )

    def _configure_loopback_ip(self, config: SpyTestDict) -> None:
        """Configure a loopback interface with IP address (IPv4 or IPv6)."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in loopback config: {config}")

        loopback = config.get("loopback")
        ip_address = config.get("ip_address")
        prefix_length = config.get("prefix_length")
        family = config.get("family", "ipv4")
        cli_type = config.get("cli_type", "klish")

        result = ip_api.config_ip_addr_interface(
            dut,
            interface_name=loopback,
            ip_address=ip_address,
            subnet=str(prefix_length),
            family=family,
            config="add",
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure loopback {ip_address}/{prefix_length} on {dut}:{loopback}")

        self._configured_loopbacks.append(config)
        st.log(f"Configured {family} loopback {ip_address}/{prefix_length} on {dut}:{loopback}")

    def _remove_loopback_ip(self, config: SpyTestDict) -> None:
        """Remove a loopback interface IP address."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        loopback = config.get("loopback")
        ip_address = config.get("ip_address")
        prefix_length = config.get("prefix_length")
        family = config.get("family", "ipv4")
        cli_type = config.get("cli_type", "klish")

        ip_api.config_ip_addr_interface(
            dut,
            interface_name=loopback,
            ip_address=ip_address,
            subnet=str(prefix_length),
            family=family,
            config="remove",
            cli_type=cli_type,
        )

    def _configure_static_route(self, config: SpyTestDict) -> None:
        """Configure a static route (IPv4 or IPv6)."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in static route config: {config}")

        destination = config.get("destination")
        next_hop = config.get("next_hop")
        family = config.get("family", "ipv4")
        cli_type = config.get("cli_type", "klish")

        result = ip_api.create_static_route(
            dut,
            next_hop=next_hop,
            static_ip=destination,
            family=family,
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure {family} static route {destination} via {next_hop} on {dut}")

        self._configured_static_routes.append(config)
        st.log(f"Configured {family} static route {destination} via {next_hop} on {dut}")

    def _remove_static_route(self, config: SpyTestDict) -> None:
        """Remove a static route."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        destination = config.get("destination")
        next_hop = config.get("next_hop")
        family = config.get("family", "ipv4")
        cli_type = config.get("cli_type", "klish")

        ip_api.delete_static_route(
            dut,
            next_hop=next_hop,
            static_ip=destination,
            family=family,
            cli_type=cli_type,
        )

    def _configure_bgp_router(self, config: SpyTestDict) -> None:
        """Configure a BGP router instance with local ASN and router ID."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP router config: {config}")

        local_asn = config.get("local_asn")
        router_id = config.get("router_id")
        cli_type = config.get("cli_type", "klish")
        vrf = config.get("vrf", "default")

        result = bgp_api.config_bgp_router(
            dut,
            local_asn=local_asn,
            router_id=router_id,
            keep_alive=self.data.keepalive,
            hold=self.data.hold,
            config="yes",
            vrf=vrf,
            cli_type=cli_type,
            ebgp_req_policy=False,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure BGP router AS {local_asn} on {dut}")

        self._configured_routers.append(config)
        st.log(f"Configured BGP router AS {local_asn} with router-id {router_id} on {dut}")

    def _remove_bgp_router(self, config: SpyTestDict) -> None:
        """Remove BGP router instance."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        local_asn = config.get("local_asn")
        vrf = config.get("vrf", "default")
        cli_type = config.get("cli_type", "klish")

        bgp_api.config_router_bgp_mode(
            dut,
            local_asn=local_asn,
            config_mode="disable",
            vrf=vrf,
            cli_type=cli_type,
        )

    def _configure_bgp_neighbor(self, config: SpyTestDict) -> None:
        """Configure a BGP neighbor with optional MD5 password."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP neighbor config: {config}")

        local_asn = config.get("local_asn")
        neighbor_ip = config.get("neighbor_ip")
        remote_asn = config.get("remote_asn")
        password = config.get("password")
        family = config.get("family", "ipv4")
        cli_type = config.get("cli_type", "klish")
        vrf = config.get("vrf", "default")
        update_source = config.get("update_source")
        ebgp_multihop = config.get("ebgp_multihop")

        # Create neighbor with password (MD5 authentication)
        result = bgp_api.create_bgp_neighbor(
            dut,
            local_asn,
            neighbor_ip,
            remote_asn,
            keep_alive=self.data.keepalive,
            hold=self.data.hold,
            password=password,
            family=family,
            vrf=vrf,
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure BGP neighbor {neighbor_ip} on {dut}")

        # Configure update-source if specified (for loopback peering)
        if update_source:
            bgp_api.config_bgp(
                dut,
                local_as=local_asn,
                neighbor=neighbor_ip,
                config="yes",
                update_src=update_source,
                vrf_name=vrf,
                cli_type=cli_type,
            )

        # Configure ebgp-multihop if specified
        if ebgp_multihop:
            bgp_api.config_bgp(
                dut,
                local_as=local_asn,
                neighbor=neighbor_ip,
                config="yes",
                ebgp_mhop=ebgp_multihop,
                vrf_name=vrf,
                cli_type=cli_type,
            )

        # Activate neighbor in address family
        bgp_api.config_bgp(
            dut,
            local_as=local_asn,
            neighbor=neighbor_ip,
            config="yes",
            addr_family=family,
            config_type_list=["activate"],
            vrf_name=vrf,
            cli_type=cli_type,
        )

        self._configured_neighbors.append(config)
        password_str = " with MD5 authentication" if password else ""
        st.log(f"Configured BGP neighbor {neighbor_ip} AS {remote_asn} on {dut}{password_str}")

    def _update_bgp_neighbor_password(self, config: SpyTestDict, new_password: str) -> None:
        """Update the MD5 password for an existing BGP neighbor."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP neighbor password update: {config}")

        local_asn = config.get("local_asn")
        neighbor_ip = config.get("neighbor_ip")
        cli_type = config.get("cli_type", "klish")
        vrf = config.get("vrf", "default")

        # Update password using config_bgp
        result = bgp_api.config_bgp(
            dut,
            local_as=local_asn,
            neighbor=neighbor_ip,
            config="yes",
            password=new_password,
            config_type_list=["pswd"],
            vrf_name=vrf,
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to update MD5 password for neighbor {neighbor_ip} on {dut}")

        st.log(f"Updated MD5 password for BGP neighbor {neighbor_ip} on {dut}")

    def _remove_bgp_neighbor(self, config: SpyTestDict) -> None:
        """Remove BGP neighbor configuration."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        local_asn = config.get("local_asn")
        neighbor_ip = config.get("neighbor_ip")
        remote_asn = config.get("remote_asn")
        family = config.get("family", "ipv4")
        cli_type = config.get("cli_type", "klish")
        vrf = config.get("vrf", "default")

        bgp_api.delete_bgp_neighbor(
            dut,
            local_asn=local_asn,
            neighbor_ip=neighbor_ip,
            remote_asn=remote_asn,
            vrf=vrf,
            cli_type=cli_type,
        )

    def _verify_bgp_session_state(self, config: SpyTestDict, expected_state: str = "Established") -> bool:
        """Verify BGP session state matches expected state."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP session verification: {config}")

        neighbor_ip = config.get("neighbor_ip")
        family = config.get("family", "ipv4")

        def _check_state() -> bool:
            output = bgp_api.show_bgp_ipv4_summary(dut) if family == "ipv4" else bgp_api.show_bgp_ipv6_summary(dut)
            if not output:
                return False

            for entry in output:
                if entry.get("neighbor") == neighbor_ip:
                    state = entry.get("state", "").lower()
                    if expected_state.lower() in state or state == expected_state.lower():
                        return True
                    elif expected_state.lower() == "established" and "established" in state:
                        return True
            return False

        result = st.poll_wait(_check_state, self.data.verify_timeout)
        return result

    def _verify_bgp_session_not_established(self, config: SpyTestDict) -> bool:
        """Verify BGP session is NOT in Established state (Idle/Active/Connect)."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP session verification: {config}")

        neighbor_ip = config.get("neighbor_ip")
        family = config.get("family", "ipv4")

        def _check_not_established() -> bool:
            output = bgp_api.show_bgp_ipv4_summary(dut) if family == "ipv4" else bgp_api.show_bgp_ipv6_summary(dut)
            if not output:
                return True  # No output means not established

            for entry in output:
                if entry.get("neighbor") == neighbor_ip:
                    state = entry.get("state", "").lower()
                    # Session should be in Idle, Active, Connect, or any non-established state
                    if "established" not in state and state not in ["established"]:
                        return True
                    return False
            return True  # Neighbor not found means not established

        result = st.poll_wait(_check_not_established, self.data.verify_timeout)
        return result

    def _get_testcase(self, tcid: str) -> SpyTestDict:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return SpyTestDict(testcase)

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_MD5_TC2.4.6.1"])
    def test_bgp_md5_ipv4_ebgp_numbered_match_then_mismatch(self) -> None:
        """
        TC 2.4.6.1 – IPv4 eBGP numbered (/30) – MD5 match then mismatch.
        Verify session forms with matching MD5 keys and fails when key is changed on one side.
        """
        testcase = self._get_testcase("2.4.6.1")
        cli_type = testcase.get("cli_type", "klish")

        # Setup - Configure interfaces, BGP routers, and neighbors with matching MD5
        for setup_step in testcase.get("setup", []):
            if setup_step.get("type") == "interface":
                self._configure_interface_ip(SpyTestDict({**setup_step, "cli_type": cli_type}))
            elif setup_step.get("type") == "bgp_router":
                self._configure_bgp_router(SpyTestDict({**setup_step, "cli_type": cli_type}))
            elif setup_step.get("type") == "bgp_neighbor":
                neighbor_config = SpyTestDict({**setup_step, "cli_type": cli_type})
                neighbor_config.password = self.data.md5_ok
                self._configure_bgp_neighbor(neighbor_config)

        # Wait for BGP sessions to establish
        time.sleep(10)

        # Verify - Check sessions are Established with matching keys
        for verify_step in testcase.get("verify_initial", []):
            neighbor_config = SpyTestDict({**verify_step, "cli_type": cli_type})
            if not self._verify_bgp_session_state(neighbor_config, "Established"):
                st.report_fail("msg", f"BGP session {neighbor_config.neighbor_ip} failed to establish with matching MD5 keys")

        st.log("BGP sessions established successfully with matching MD5 keys")

        # Stimulus - Change MD5 key on one DUT to create mismatch
        stimulus_config = testcase.get("stimulus", {})
        if stimulus_config:
            neighbor_config = SpyTestDict({**stimulus_config, "cli_type": cli_type})
            self._update_bgp_neighbor_password(neighbor_config, self.data.md5_bad)
            st.log(f"Changed MD5 password on {neighbor_config.dut} to create mismatch")

        # Wait for session to drop
        time.sleep(10)

        # Verify - Check sessions are NOT Established after mismatch
        for verify_step in testcase.get("verify_mismatch", []):
            neighbor_config = SpyTestDict({**verify_step, "cli_type": cli_type})
            if not self._verify_bgp_session_not_established(neighbor_config):
                st.report_fail("msg", f"BGP session {neighbor_config.neighbor_ip} unexpectedly established with mismatched MD5 keys")

        st.log("BGP sessions correctly failed to establish with mismatched MD5 keys")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_MD5_TC2.4.6.2"])
    def test_bgp_md5_ipv4_ebgp_multihop_match_then_mismatch(self) -> None:
        """
        TC 2.4.6.2 – IPv4 eBGP loopback multihop – MD5 match then mismatch.
        Verify MD5 authentication with eBGP multihop peering via loopbacks.
        """
        testcase = self._get_testcase("2.4.6.2")
        cli_type = testcase.get("cli_type", "klish")

        # Setup - Configure loopbacks, interfaces, static routes, BGP routers, and neighbors
        for setup_step in testcase.get("setup", []):
            step_config = SpyTestDict({**setup_step, "cli_type": cli_type})
            if setup_step.get("type") == "loopback":
                self._configure_loopback_ip(step_config)
            elif setup_step.get("type") == "interface":
                self._configure_interface_ip(step_config)
            elif setup_step.get("type") == "static_route":
                self._configure_static_route(step_config)
            elif setup_step.get("type") == "bgp_router":
                self._configure_bgp_router(step_config)
            elif setup_step.get("type") == "bgp_neighbor":
                step_config.password = self.data.md5_ok
                self._configure_bgp_neighbor(step_config)

        # Wait for BGP sessions to establish
        time.sleep(10)

        # Verify - Check sessions are Established with matching keys
        for verify_step in testcase.get("verify_initial", []):
            neighbor_config = SpyTestDict({**verify_step, "cli_type": cli_type})
            if not self._verify_bgp_session_state(neighbor_config, "Established"):
                st.report_fail("msg", f"BGP multihop session {neighbor_config.neighbor_ip} failed to establish with matching MD5 keys")

        st.log("BGP multihop sessions established successfully with matching MD5 keys")

        # Stimulus - Change MD5 key on one DUT
        stimulus_config = testcase.get("stimulus", {})
        if stimulus_config:
            neighbor_config = SpyTestDict({**stimulus_config, "cli_type": cli_type})
            self._update_bgp_neighbor_password(neighbor_config, self.data.md5_bad)
            st.log(f"Changed MD5 password on {neighbor_config.dut} to create mismatch")

        # Wait for session to drop
        time.sleep(10)

        # Verify - Check sessions are NOT Established after mismatch
        for verify_step in testcase.get("verify_mismatch", []):
            neighbor_config = SpyTestDict({**verify_step, "cli_type": cli_type})
            if not self._verify_bgp_session_not_established(neighbor_config):
                st.report_fail("msg", f"BGP multihop session {neighbor_config.neighbor_ip} unexpectedly established with mismatched MD5 keys")

        st.log("BGP multihop sessions correctly failed with mismatched MD5 keys")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_MD5_TC2.4.6.3"])
    def test_bgp_md5_ipv6_ebgp_numbered_match_then_mismatch(self) -> None:
        """
        TC 2.4.6.3 – IPv6 eBGP numbered (/64) – AO/MD5 match then mismatch.
        Verify session forms with matching keys and fails with mismatch for IPv6 peers.
        """
        testcase = self._get_testcase("2.4.6.3")
        cli_type = testcase.get("cli_type", "klish")

        # Setup - Configure IPv6 interfaces, BGP routers, and neighbors with matching MD5/TCP-AO
        for setup_step in testcase.get("setup", []):
            step_config = SpyTestDict({**setup_step, "cli_type": cli_type, "family": "ipv6"})
            if setup_step.get("type") == "interface":
                self._configure_interface_ip(step_config)
            elif setup_step.get("type") == "bgp_router":
                self._configure_bgp_router(step_config)
            elif setup_step.get("type") == "bgp_neighbor":
                step_config.password = self.data.md5_ok
                step_config.family = "ipv6"
                self._configure_bgp_neighbor(step_config)

        # Wait for BGP sessions to establish
        time.sleep(10)

        # Verify - Check IPv6 sessions are Established
        for verify_step in testcase.get("verify_initial", []):
            neighbor_config = SpyTestDict({**verify_step, "cli_type": cli_type, "family": "ipv6"})
            if not self._verify_bgp_session_state(neighbor_config, "Established"):
                st.report_fail("msg", f"BGP IPv6 session {neighbor_config.neighbor_ip} failed to establish with matching keys")

        st.log("BGP IPv6 sessions established successfully with matching MD5/TCP-AO keys")

        # Stimulus - Change password on one DUT
        stimulus_config = testcase.get("stimulus", {})
        if stimulus_config:
            neighbor_config = SpyTestDict({**stimulus_config, "cli_type": cli_type})
            self._update_bgp_neighbor_password(neighbor_config, self.data.md5_bad)

        # Wait for session to drop
        time.sleep(10)

        # Verify - Check sessions are NOT Established
        for verify_step in testcase.get("verify_mismatch", []):
            neighbor_config = SpyTestDict({**verify_step, "cli_type": cli_type, "family": "ipv6"})
            if not self._verify_bgp_session_not_established(neighbor_config):
                st.report_fail("msg", f"BGP IPv6 session {neighbor_config.neighbor_ip} unexpectedly established with mismatched keys")

        st.log("BGP IPv6 sessions correctly failed with mismatched keys")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_MD5_TC2.4.6.4"])
    def test_bgp_md5_ipv6_ebgp_multihop_match_then_mismatch(self) -> None:
        """
        TC 2.4.6.4 – IPv6 eBGP loopback multihop – AO/MD5 match then mismatch.
        Verify AO/MD5 authentication with IPv6 eBGP over loopbacks.
        """
        testcase = self._get_testcase("2.4.6.4")
        cli_type = testcase.get("cli_type", "klish")

        # Setup - Configure IPv6 loopbacks, interfaces, static routes, and BGP
        for setup_step in testcase.get("setup", []):
            step_config = SpyTestDict({**setup_step, "cli_type": cli_type})
            if setup_step.get("type") == "loopback":
                step_config.family = "ipv6"
                self._configure_loopback_ip(step_config)
            elif setup_step.get("type") == "interface":
                step_config.family = "ipv6"
                self._configure_interface_ip(step_config)
            elif setup_step.get("type") == "static_route":
                step_config.family = "ipv6"
                self._configure_static_route(step_config)
            elif setup_step.get("type") == "bgp_router":
                self._configure_bgp_router(step_config)
            elif setup_step.get("type") == "bgp_neighbor":
                step_config.password = self.data.md5_ok
                step_config.family = "ipv6"
                self._configure_bgp_neighbor(step_config)

        # Wait for BGP sessions to establish
        time.sleep(10)

        # Verify initial state
        for verify_step in testcase.get("verify_initial", []):
            neighbor_config = SpyTestDict({**verify_step, "cli_type": cli_type, "family": "ipv6"})
            if not self._verify_bgp_session_state(neighbor_config, "Established"):
                st.report_fail("msg", f"BGP IPv6 multihop session {neighbor_config.neighbor_ip} failed to establish")

        st.log("BGP IPv6 multihop sessions established with MD5/TCP-AO")

        # Stimulus - Change password
        stimulus_config = testcase.get("stimulus", {})
        if stimulus_config:
            neighbor_config = SpyTestDict({**stimulus_config, "cli_type": cli_type})
            self._update_bgp_neighbor_password(neighbor_config, self.data.md5_bad)

        # Wait for session to drop
        time.sleep(10)

        # Verify mismatch state
        for verify_step in testcase.get("verify_mismatch", []):
            neighbor_config = SpyTestDict({**verify_step, "cli_type": cli_type, "family": "ipv6"})
            if not self._verify_bgp_session_not_established(neighbor_config):
                st.report_fail("msg", f"BGP IPv6 multihop session unexpectedly established with mismatched keys")

        st.log("BGP IPv6 multihop sessions correctly failed with mismatched keys")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_MD5_TC2.4.6.5"])
    def test_bgp_md5_ipv4_ibgp_rekey_coordinated(self) -> None:
        """
        TC 2.4.6.5 – IPv4 iBGP rekey – coordinated rotate without prolonged downtime.
        Demonstrate safe MD5 key rotation procedure.
        """
        testcase = self._get_testcase("2.4.6.5")
        cli_type = testcase.get("cli_type", "klish")

        # Setup - Configure iBGP with initial MD5 key
        for setup_step in testcase.get("setup", []):
            step_config = SpyTestDict({**setup_step, "cli_type": cli_type})
            if setup_step.get("type") == "interface":
                self._configure_interface_ip(step_config)
            elif setup_step.get("type") == "bgp_router":
                self._configure_bgp_router(step_config)
            elif setup_step.get("type") == "bgp_neighbor":
                step_config.password = self.data.md5_ok
                self._configure_bgp_neighbor(step_config)

        # Wait for initial establishment
        time.sleep(10)

        # Precheck - Verify initial sessions are Established
        for verify_step in testcase.get("precheck", []):
            neighbor_config = SpyTestDict({**verify_step, "cli_type": cli_type})
            if not self._verify_bgp_session_state(neighbor_config, "Established"):
                st.report_fail("msg", f"Initial iBGP session {neighbor_config.neighbor_ip} not established")

        st.log("Initial iBGP sessions established with MD5 key: {}", self.data.md5_ok)

        # Stimulus - Coordinated key rotation
        # Step 1: Change key on DUT2 (session will drop)
        rekey_steps = testcase.get("rekey_steps", [])
        if len(rekey_steps) >= 2:
            # Change first DUT
            step1_config = SpyTestDict({**rekey_steps[0], "cli_type": cli_type})
            self._update_bgp_neighbor_password(step1_config, self.data.md5_bad)
            st.log(f"Step 1: Changed MD5 key on {step1_config.dut} - session should drop")
            time.sleep(5)

            # Step 2: Change second DUT (session should re-establish)
            step2_config = SpyTestDict({**rekey_steps[1], "cli_type": cli_type})
            self._update_bgp_neighbor_password(step2_config, self.data.md5_bad)
            st.log(f"Step 2: Changed MD5 key on {step2_config.dut} - session should re-establish")
            time.sleep(10)

        # Verify - Check sessions re-established with new key
        for verify_step in testcase.get("verify_rekey", []):
            neighbor_config = SpyTestDict({**verify_step, "cli_type": cli_type})
            if not self._verify_bgp_session_state(neighbor_config, "Established"):
                st.report_fail("msg", f"iBGP session {neighbor_config.neighbor_ip} failed to re-establish after rekey")

        st.log("iBGP sessions successfully re-established with new MD5 key: {}", self.data.md5_bad)
        st.log("Key rotation completed with brief downtime (coordinated approach)")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_MD5_TC2.4.6.6"])
    @pytest.mark.negative
    def test_bgp_md5_ipv4_ebgp_asymmetric_negative(self) -> None:
        """
        TC 2.4.6.6 – Negative – remove MD5 on one side only (IPv4 eBGP).
        Session must not establish if one side lacks MD5 key (asymmetric configuration).
        """
        testcase = self._get_testcase("2.4.6.6")
        cli_type = testcase.get("cli_type", "klish")

        # Setup - Configure one DUT with MD5, other without (asymmetric)
        for setup_step in testcase.get("setup", []):
            step_config = SpyTestDict({**setup_step, "cli_type": cli_type})
            if setup_step.get("type") == "interface":
                self._configure_interface_ip(step_config)
            elif setup_step.get("type") == "bgp_router":
                self._configure_bgp_router(step_config)
            elif setup_step.get("type") == "bgp_neighbor":
                # One neighbor has password, other does not
                if setup_step.get("has_password", False):
                    step_config.password = self.data.md5_ok
                else:
                    step_config.password = None
                self._configure_bgp_neighbor(step_config)

        # Wait and observe
        time.sleep(15)

        # Verify - Sessions should NOT establish (asymmetric MD5 configuration)
        for verify_step in testcase.get("verify", []):
            neighbor_config = SpyTestDict({**verify_step, "cli_type": cli_type})
            if not self._verify_bgp_session_not_established(neighbor_config):
                st.report_fail("msg", f"BGP session {neighbor_config.neighbor_ip} unexpectedly established with asymmetric MD5 config")

        st.log("BGP sessions correctly failed to establish with asymmetric MD5 configuration")
        st.log("Test passed: one side with MD5, other without = no session")
        st.report_pass("test_case_passed")
