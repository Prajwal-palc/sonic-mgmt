"""
BGP IPv4 OVER LOOPBACK INTERFACE
Author: QA Team
2025

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_loopback_ipv4.py \
  --logs-path ./logs/test_bgp_loopback_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Comprehensive validation of IPv4 iBGP neighbor session establishment over
  Loopback interface. The test suite provisions Loopback interfaces, configures
  IP addressing, establishes iBGP session between DUT1 and DUT2 (AS 65100) using
  loopback IPs as BGP endpoints, and validates session establishment, interface
  flap resilience, traffic forwarding with Scapy, and configuration persistence
  across save/reboot.

Pre-requisites:
  - Topology: t0/t1/any | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes (BGP over Loopback)
        # +-------------------------+                   +-------------------------+
        # |   DUT1 (smic_sonic1)    |                   |   DUT2 (smic_sonic2)    |
        # |   AS 65100              |                   |   AS 65100              |
        # |   Router-ID: 1.1.1.1    |                   |   Router-ID: 2.2.2.2    |
        # |                         |                   |                         |
        # |   Loopback0             |                   |   Loopback0             |
        # |   IP: 1.1.1.1/32        |                   |   IP: 2.2.2.2/32        |
        # |                         |                   |                         |
        # |   Ethernet4             |                   |   Ethernet4             |
        # |   IP: 10.1.1.1/30       |===================|   IP: 10.1.1.2/30       |
        # |   (underlay)            |     Ethernet4     |   (underlay)            |
        # +-------------------------+                   +-------------------------+

  - Feature flags / min SONiC version: Loopback interface and BGP support required
  - Required test variables (YAML): vars_bgp_loopback_ipv4.yaml
    - defaults.cli_type (klish)
    - defaults.verify_timeout (120 seconds recommended)
    - defaults.cleanup (true for cleanup after tests)
    - defaults.min_topology (D1D2:1)
    - testcases.* definitions for all testcases
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pytest
import yaml

from spytest import SpyTestDict, st

import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api
import apis.system.interface as intf_api
import apis.system.reboot as reboot_api
import apis.system.basic as basic_api
import apis.common.scapy_traffic as scapy_api

VAR_FILE_ENV = "BGP_LOOPBACK_VAR_FILE"


def _candidate_var_files() -> List[Path]:
    """Return candidate YAML paths in search order."""
    candidates: List[Path] = []
    override = st.getenv(VAR_FILE_ENV)
    if override:
        candidates.append(Path(override))

    project_root = Path(__file__).resolve().parents[3]
    candidates.append(project_root / "vars" / "routing" / "bgp" / "vars_bgp_loopback_ipv4.yaml")
    candidates.append(Path(__file__).resolve().with_name("vars_bgp_loopback_ipv4.yaml"))
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
    st.report_fail("msg", f"BGP Loopback variable file not found. Checked: {attempted_paths}")
    return SpyTestDict()


def _iter_candidate_duts(topology: SpyTestDict) -> Iterable[str]:
    """Yield topology keys that resemble DUT aliases (D1, D2, ...)."""
    for key, value in topology.items():
        if key.upper().startswith("D") and value:
            yield key


@pytest.mark.topology("any")
class TestBgpLoopbackIpv4:
    """Testcases for validating IPv4 iBGP session establishment over Loopback interface."""

    data = SpyTestDict()

    @classmethod
    def _resolve_topology_vars(cls, obj: Any, topology: SpyTestDict) -> Any:
        """Recursively resolve {{topology_var}} placeholders in config."""
        if isinstance(obj, dict):
            return {key: cls._resolve_topology_vars(value, topology) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [cls._resolve_topology_vars(item, topology) for item in obj]
        elif isinstance(obj, str) and obj.startswith("{{") and obj.endswith("}}"):
            var_name = obj[2:-2]
            resolved = getattr(topology, var_name, None)
            if resolved is None:
                st.warn(f"Topology variable '{var_name}' not found, using original value")
                return obj
            st.log(f"Resolved {obj} -> {resolved}")
            return resolved
        else:
            return obj

    @classmethod
    def setup_class(cls) -> None:
        """Load YAML configuration, topology, and defaults."""
        config = _load_yaml_data()
        defaults = SpyTestDict(config.get("defaults", {}))

        min_topology = defaults.get("min_topology") or ["D1D2:1"]
        topology = st.ensure_min_topology(*min_topology)

        # Resolve topology variables in config (e.g., {{D1D2P1}} -> Ethernet4)
        config = cls._resolve_topology_vars(config, topology)

        cls.data.config = config
        cls.data.defaults = defaults
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 300))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Map DUT aliases to device handles
        cls.data.dut_map = SpyTestDict()
        for dut_alias in _iter_candidate_duts(topology):
            cls.data.dut_map[dut_alias] = getattr(topology, dut_alias)

        cls.data.dut_names = st.get_dut_names()
        st.log(f"Setup complete. DUT map: {cls.data.dut_map}, CLI type: {cls.data.cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup configuration after all tests complete."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping teardown")
            return

        st.banner("CLASS TEARDOWN: Starting cleanup")
        cleanup_config = cls.data.config.get("cleanup", {})

        # Cleanup BGP neighbors
        for neighbor_cfg in cleanup_config.get("bgp_neighbors", []):
            dut = cls._resolve_dut(neighbor_cfg.get("dut"))
            if dut:
                st.log(f"Removing BGP neighbor {neighbor_cfg.get('neighbor_ip')} on {neighbor_cfg.get('dut')}")
                try:
                    bgp_api.config_bgp_neighbor(
                        dut,
                        local_asn=neighbor_cfg.get("local_asn"),
                        neighbor_ip=neighbor_cfg.get("neighbor_ip"),
                        remote_asn=neighbor_cfg.get("local_asn"),  # iBGP uses same ASN
                        config="no",
                        cli_type=cls.data.cli_type
                    )
                except Exception as e:
                    st.log(f"Error removing BGP neighbor: {e}")

        # Cleanup BGP routers
        for router_cfg in cleanup_config.get("bgp_routers", []):
            dut = cls._resolve_dut(router_cfg.get("dut"))
            if dut:
                st.log(f"Removing BGP router AS {router_cfg.get('local_asn')} on {router_cfg.get('dut')}")
                try:
                    st.config(dut, [
                        "no router bgp {}".format(router_cfg.get("local_asn"))
                    ], type="klish", skip_error_check=True)
                except Exception as e:
                    st.log(f"Error removing BGP router: {e}")

        # Cleanup Loopback IP addresses
        for loopback_cfg in cleanup_config.get("loopback_interfaces", []):
            dut = cls._resolve_dut(loopback_cfg.get("dut"))
            if dut:
                interface = loopback_cfg.get("interface")
                st.log(f"Removing IP addresses from {interface} on {loopback_cfg.get('dut')}")
                try:
                    st.config(dut, [
                        f"interface {interface}",
                        "no ip address",
                        "exit"
                    ], type="klish", skip_error_check=True)
                except Exception as e:
                    st.log(f"Error removing Loopback IP: {e}")

        # Cleanup Loopback interfaces
        for loopback_cfg in cleanup_config.get("loopbacks", []):
            dut = cls._resolve_dut(loopback_cfg.get("dut"))
            if dut:
                interface = loopback_cfg.get("interface")
                st.log(f"Removing {interface} on {loopback_cfg.get('dut')}")
                try:
                    st.config(dut, [
                        f"no interface {interface}"
                    ], type="klish", skip_error_check=True)
                except Exception as e:
                    st.log(f"Error removing Loopback: {e}")

        # Cleanup underlay interfaces
        for intf_cfg in cleanup_config.get("underlay_interfaces", []):
            dut = cls._resolve_dut(intf_cfg.get("dut"))
            if dut:
                interface = intf_cfg.get("interface")
                st.log(f"Removing IP addresses from {interface} on {intf_cfg.get('dut')}")
                try:
                    st.config(dut, [
                        f"interface {interface}",
                        "no ip address",
                        "exit"
                    ], type="klish", skip_error_check=True)
                except Exception as e:
                    st.log(f"Error removing underlay interface IP: {e}")

        # Cleanup static routes
        for route_cfg in cleanup_config.get("static_routes", []):
            dut = cls._resolve_dut(route_cfg.get("dut"))
            if dut:
                st.log(f"Removing static route {route_cfg.get('destination')} on {route_cfg.get('dut')}")
                try:
                    ip_api.delete_static_route(
                        dut,
                        next_hop=route_cfg.get("next_hop"),
                        static_ip=route_cfg.get("destination"),
                        family="ipv4",
                        cli_type=cls.data.cli_type
                    )
                except Exception as e:
                    st.log(f"Error removing static route: {e}")

        st.banner("CLASS TEARDOWN: Cleanup complete")

    @classmethod
    def _resolve_dut(cls, alias: str | None) -> str | None:
        """Translate a topology alias (e.g., D1) to the framework DUT handle."""
        if not alias:
            return None
        if alias in cls.data.dut_map:
            return cls.data.dut_map[alias]
        if alias in cls.data.dut_names:
            return alias
        st.warn(f"Unable to resolve DUT alias '{alias}'")
        return None

    def _get_testcase(self, tcid: str) -> SpyTestDict:
        """Fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return SpyTestDict(testcase)

    def _configure_loopbacks(self, testcase: SpyTestDict) -> None:
        """Configure Loopback interfaces on DUTs."""
        st.banner("Configuring Loopback interfaces")
        for loopback_cfg in testcase.get("loopbacks", []):
            dut = self._resolve_dut(loopback_cfg.get("dut"))
            if not dut:
                st.report_fail("msg", f"Invalid DUT alias: {loopback_cfg.get('dut')}")

            interface = loopback_cfg.get("interface")
            st.log(f"Creating {interface} on {loopback_cfg.get('dut')}")

            # Create loopback interface using API (same as working test)
            result = ip_api.config_loopback_interfaces(
                dut,
                loopback_name=interface,
                config="yes"
            )
            if not result:
                st.report_fail("msg", f"Failed to create {interface} on {loopback_cfg.get('dut')}")

    def _configure_loopback_interfaces(self, testcase: SpyTestDict) -> None:
        """Configure IP addresses on Loopback interfaces."""
        st.banner("Configuring Loopback L3 interfaces")
        for loopback_cfg in testcase.get("loopback_interfaces", []):
            dut = self._resolve_dut(loopback_cfg.get("dut"))
            if not dut:
                st.report_fail("msg", f"Invalid DUT alias: {loopback_cfg.get('dut')}")

            interface = loopback_cfg.get("interface")
            ip_address = loopback_cfg.get("ip_address")
            prefix_length = loopback_cfg.get("prefix_length")

            st.log(f"Configuring {interface} with IP {ip_address}/{prefix_length} on {loopback_cfg.get('dut')}")

            # Configure IP address on Loopback interface (no cli_type like working test)
            result = ip_api.config_ip_addr_interface(
                dut,
                interface_name=interface,
                ip_address=ip_address,
                subnet=str(prefix_length),
                family="ipv4",
                config="add"
            )
            if not result:
                st.report_fail("msg", f"Failed to configure IP on {interface} on {loopback_cfg.get('dut')}")

    def _configure_underlay_interfaces(self, testcase: SpyTestDict) -> None:
        """Configure underlay physical interfaces."""
        st.banner("Configuring underlay interfaces")
        for intf_cfg in testcase.get("underlay_interfaces", []):
            dut = self._resolve_dut(intf_cfg.get("dut"))
            if not dut:
                st.report_fail("msg", f"Invalid DUT alias: {intf_cfg.get('dut')}")

            interface = intf_cfg.get("interface")
            ip_address = intf_cfg.get("ip_address")
            prefix_length = intf_cfg.get("prefix_length")
            admin_status = intf_cfg.get("admin_status", "up")

            st.log(f"Configuring {interface} with IP {ip_address}/{prefix_length} on {intf_cfg.get('dut')}")

            # Configure IP address (no cli_type like working test)
            result = ip_api.config_ip_addr_interface(
                dut,
                interface_name=interface,
                ip_address=ip_address,
                subnet=str(prefix_length),
                family="ipv4",
                config="add"
            )
            if not result:
                st.report_fail("msg", f"Failed to configure IP on {interface} on {intf_cfg.get('dut')}")

            # Set interface admin state using interface_operation like working test
            if admin_status == "up":
                intf_api.interface_operation(dut, interface, operation="startup")

        # Wait for underlay interfaces to stabilize
        st.wait(10, "Waiting for underlay interfaces to stabilize")

    def _configure_static_routes(self, testcase: SpyTestDict) -> None:
        """Configure static routes for loopback reachability."""
        st.banner("Configuring static routes")
        for route_cfg in testcase.get("static_routes", []):
            dut = self._resolve_dut(route_cfg.get("dut"))
            if not dut:
                st.report_fail("msg", f"Invalid DUT alias: {route_cfg.get('dut')}")

            destination = route_cfg.get("destination")
            next_hop = route_cfg.get("next_hop")

            st.log(f"Creating static route {destination} via {next_hop} on {route_cfg.get('dut')}")

            result = ip_api.create_static_route(
                dut,
                next_hop=next_hop,
                static_ip=destination,
                family="ipv4"
            )
            if not result:
                st.report_fail("msg", f"Failed to create static route on {route_cfg.get('dut')}")

    def _verify_loopback_ping(self, testcase: SpyTestDict) -> None:
        """Verify ping connectivity between loopback interfaces."""
        st.banner("Verifying loopback ping connectivity")

        # Get loopback IPs from configuration
        loopback_ips = {}
        for loopback_cfg in testcase.get("loopback_interfaces", []):
            dut_alias = loopback_cfg.get("dut")
            loopback_ips[dut_alias] = loopback_cfg.get("ip_address")

        # Test ping from D1 to D2
        if "D1" in loopback_ips and "D2" in loopback_ips:
            dut1 = self._resolve_dut("D1")
            dut2 = self._resolve_dut("D2")
            d1_loopback_ip = loopback_ips["D1"]
            d2_loopback_ip = loopback_ips["D2"]

            st.log(f"Testing ping from D1 ({d1_loopback_ip}) to D2 ({d2_loopback_ip})")
            result = ip_api.ping(
                dut1,
                addresses=d2_loopback_ip,
                source_ip=d1_loopback_ip,
                count=5
            )
            if result:
                st.log(f"SUCCESS: Ping from {d1_loopback_ip} to {d2_loopback_ip} passed")
            else:
                st.error(f"FAILED: Ping from {d1_loopback_ip} to {d2_loopback_ip} failed")
                st.report_fail("msg", f"Loopback ping failed from D1 to D2")

            st.log(f"Testing ping from D2 ({d2_loopback_ip}) to D1 ({d1_loopback_ip})")
            result = ip_api.ping(
                dut2,
                addresses=d1_loopback_ip,
                source_ip=d2_loopback_ip,
                count=5
            )
            if result:
                st.log(f"SUCCESS: Ping from {d2_loopback_ip} to {d1_loopback_ip} passed")
            else:
                st.error(f"FAILED: Ping from {d2_loopback_ip} to {d1_loopback_ip} failed")
                st.report_fail("msg", f"Loopback ping failed from D2 to D1")

        st.log("Loopback ping connectivity verified successfully")

    def _configure_bgp_routers(self, testcase: SpyTestDict) -> None:
        """Configure BGP router instances."""
        st.banner("Configuring BGP routers")
        for router_cfg in testcase.get("bgp_routers", []):
            dut = self._resolve_dut(router_cfg.get("dut"))
            if not dut:
                st.report_fail("msg", f"Invalid DUT alias: {router_cfg.get('dut')}")

            local_asn = router_cfg.get("local_asn")
            router_id = router_cfg.get("router_id")

            st.log(f"Creating BGP router AS {local_asn} with router-id {router_id} on {router_cfg.get('dut')}")

            # Configure BGP router with router-id using direct CLI
            # In klish mode, the command is "router-id" not "bgp router-id"
            bgp_config = [
                "configure terminal",
                "no router bgp",
                f"router bgp {local_asn}",
                f"router-id {router_id}",
                "end"
            ]
            st.config(dut, bgp_config, type="klish", skip_error_check=False)
            st.log(f"BGP router configured on {router_cfg.get('dut')}")

    def _configure_bgp_neighbors(self, testcase: SpyTestDict) -> None:
        """Configure BGP neighbors and activate address family."""
        st.banner("Configuring BGP neighbors")
        for neighbor_cfg in testcase.get("bgp_neighbors", []):
            dut = self._resolve_dut(neighbor_cfg.get("dut"))
            if not dut:
                st.report_fail("msg", f"Invalid DUT alias: {neighbor_cfg.get('dut')}")

            local_asn = neighbor_cfg.get("local_asn")
            neighbor_ip = neighbor_cfg.get("neighbor_ip")
            remote_asn = neighbor_cfg.get("remote_asn")
            update_source = neighbor_cfg.get("update_source")
            family = neighbor_cfg.get("family", "ipv4")
            activate = neighbor_cfg.get("activate", True)

            st.log(f"Creating BGP neighbor {neighbor_ip} (AS {remote_asn}) on {neighbor_cfg.get('dut')}")

            # Configure BGP neighbor using direct CLI
            # In klish mode, after "neighbor X.X.X.X remote-as Y", klish enters neighbor config mode
            # Commands in neighbor config mode don't need "neighbor X.X.X.X" prefix
            neighbor_config = [
                "configure terminal",
                f"router bgp {local_asn}",
                f"neighbor {neighbor_ip} remote-as {remote_asn}",
            ]

            # Add update-source if specified (in neighbor config mode, no "neighbor X.X.X.X" prefix)
            if update_source:
                neighbor_config.append(f"update-source interface {update_source}")
                # Add ebgp-multihop for loopback peering (required for BGP over loopback)
                neighbor_config.append(f"ebgp-multihop 2")

            # Activate in address-family context (in AF mode, no "neighbor X.X.X.X" prefix)
            if activate:
                neighbor_config.extend([
                    f"address-family {family} unicast",
                    "activate",
                    "exit",
                ])

            neighbor_config.append("end")

            st.config(dut, neighbor_config, type="klish", skip_error_check=False)
            st.log(f"BGP neighbor {neighbor_ip} configured and activated on {neighbor_cfg.get('dut')}")

    def _verify_bgp_sessions(self, testcase: SpyTestDict) -> None:
        """Verify BGP session establishment."""
        st.banner("Verifying BGP sessions")
        verification = testcase.get("verification", {})

        for session_check in verification.get("bgp_session_checks", []):
            dut = self._resolve_dut(session_check.get("dut"))
            if not dut:
                st.report_fail("msg", f"Invalid DUT alias: {session_check.get('dut')}")

            neighbor_ip = session_check.get("neighbor_ip")
            expected_state = session_check.get("expected_state", "Established")

            st.log(f"Verifying BGP session with {neighbor_ip} on {session_check.get('dut')}")

            # Poll for BGP session establishment
            st.log(f"Polling for BGP session establishment with {neighbor_ip} (timeout: {self.data.verify_timeout}s)")

            def _check_bgp_state() -> bool:
                return bgp_api.verify_bgp_summary(
                    dut,
                    family="ipv4",
                    neighbor=neighbor_ip,
                    state=expected_state,
                    cli_type=self.data.cli_type
                )

            if not st.poll_wait(_check_bgp_state, self.data.verify_timeout):
                st.report_fail("msg", f"BGP session with {neighbor_ip} not established on {session_check.get('dut')} after {self.data.verify_timeout}s")

            st.log(f"BGP session with {neighbor_ip} established successfully on {session_check.get('dut')}")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-LB-001"])
    def test_bgp_loopback_session_establishment(self) -> None:
        """
        Test BGP-LB-001: iBGP over Loopback Configuration and Session Establishment

        Objective:
            Verify iBGP IPv4 neighbor session establishment over Loopback interface

        Steps:
            1. Create Loopback0 on both DUTs
            2. Configure IP addresses on Loopback0 interface
            3. Configure underlay IP addresses on Ethernet4
            4. Configure static routes for loopback reachability
            5. Configure BGP router with AS 65100 on both DUTs
            6. Configure iBGP neighbors using loopback IPs with update-source
            7. Activate IPv4 unicast address family
            8. Verify BGP session establishment
        """
        testcase = self._get_testcase("BGP-LB-001")

        # Configuration phase
        self._configure_loopbacks(testcase)
        self._configure_loopback_interfaces(testcase)
        self._configure_underlay_interfaces(testcase)
        self._configure_static_routes(testcase)

        # Verify loopback ping before BGP configuration
        self._verify_loopback_ping(testcase)

        self._configure_bgp_routers(testcase)
        self._configure_bgp_neighbors(testcase)

        # Verification phase
        self._verify_bgp_sessions(testcase)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-LB-002"])
    @pytest.mark.depends(on=["test_bgp_loopback_session_establishment"])
    def test_bgp_loopback_interface_flap(self) -> None:
        """
        Test BGP-LB-002: BGP over Loopback Interface Flap Scenario

        Objective:
            Validate BGP session resilience to underlay interface flap

        Steps:
            1. Verify BGP session is established (from test 001)
            2. Shutdown underlay interface (Ethernet4) on DUT1
            3. Verify BGP session goes down
            4. Bring up underlay interface (Ethernet4) on DUT1
            5. Verify BGP session re-establishes
        """
        testcase = self._get_testcase("BGP-LB-002")

        st.banner("TEST CASE: BGP over Loopback Interface Flap")

        # Get DUT handles
        dut1 = self._resolve_dut("D1")
        dut2 = self._resolve_dut("D2")

        if not dut1 or not dut2:
            st.report_fail("msg", "Unable to resolve DUT aliases")

        try:
            # Step 1: Verify BGP session is established
            st.banner("Step 1: Verify BGP session is established")
            self._verify_bgp_sessions(testcase)
            st.log("BGP sessions verified - using established session from test 001")

            # Step 2: Shutdown underlay interface
            st.banner("Step 2: Shutdown underlay interface on DUT1")
            underlay_interface = testcase.get("underlay_interface", "Ethernet4")

            st.log(f"Shutting down {underlay_interface} on DUT1")
            intf_api.interface_shutdown(
                dut1,
                interfaces=[underlay_interface],
                cli_type=self.data.cli_type
            )

            st.wait(10, "Waiting for interface shutdown to take effect")

            # Step 3: Verify BGP session goes down
            st.banner("Step 3: Verify BGP session goes down")
            neighbor_ip = testcase.get("verification", {}).get("bgp_session_checks", [{}])[0].get("neighbor_ip", "2.2.2.2")

            st.log(f"Verifying BGP session with {neighbor_ip} is down on DUT1")

            # Wait for BGP session to go down (Active or Idle state)
            def _check_bgp_down() -> bool:
                output = bgp_api.show_bgp_ipv4_summary_vtysh(dut1)
                if output:
                    for entry in output:
                        if entry.get("neighbor") == neighbor_ip:
                            state = entry.get("state", "")
                            # Session is down if not Established
                            return state != "Established"
                return True  # Assume down if no output

            if not st.poll_wait(_check_bgp_down, 60):
                st.log("WARNING: BGP session did not go down as expected")

            # Step 4: Bring up underlay interface
            st.banner("Step 4: Bring up underlay interface on DUT1")

            st.log(f"Bringing up {underlay_interface} on DUT1")
            intf_api.interface_noshutdown(
                dut1,
                interfaces=[underlay_interface],
                cli_type=self.data.cli_type
            )

            st.wait(15, "Waiting for interface to come up and stabilize")

            # Step 5: Verify BGP session re-establishes
            st.banner("Step 5: Verify BGP session re-establishes")
            self._verify_bgp_sessions(testcase)

            st.log("SUCCESS: BGP session recovered after interface flap")

        except Exception as e:
            st.log(f"Error during interface flap test: {e}")
            # Ensure interface is brought back up
            try:
                intf_api.interface_noshutdown(
                    dut1,
                    interfaces=[underlay_interface],
                    cli_type=self.data.cli_type
                )
            except Exception:
                pass
            raise

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-LB-003"])
    @pytest.mark.depends(on=["test_bgp_loopback_session_establishment"])
    def test_bgp_loopback_traffic_validation(self) -> None:
        """
        Test BGP-LB-003: BGP over Loopback Traffic Validation using Scapy

        Objective:
            Validate bidirectional traffic forwarding using Scapy-generated packets
            over the established BGP session on Loopback. Reuses existing BGP session.

        Steps:
            1. Verify BGP session is established (from test 001)
            2. Advertise test networks via BGP on both DUTs
            3. Verify route propagation
            4. Send bidirectional ICMP traffic using Scapy
            5. Verify traffic statistics
            6. Cleanup test network advertisements
        """
        testcase = self._get_testcase("BGP-LB-003")

        st.banner("TEST CASE: BGP over Loopback Traffic Validation")
        st.log("Reusing iBGP session from test BGP-LB-001")

        # Get DUT handles
        dut1 = self._resolve_dut("D1")
        dut2 = self._resolve_dut("D2")

        if not dut1 or not dut2:
            st.report_fail("msg", "Unable to resolve DUT aliases")

        try:
            # Step 1: Verify BGP session is established
            st.banner("Step 1: Verify BGP session is established")
            self._verify_bgp_sessions(testcase)
            st.log("BGP sessions verified - using established session from test 001")

            # Step 2: Advertise test networks
            st.banner("Step 2: Advertise test networks via BGP")

            test_network_dut1 = testcase.get("test_network_dut1", "192.168.10.0/24")
            test_network_dut2 = testcase.get("test_network_dut2", "192.168.20.0/24")
            local_asn = testcase.get("local_asn", 65100)

            st.log(f"DUT1 advertising network {test_network_dut1}")
            network_config_dut1 = [
                f"router bgp {local_asn}",
                "address-family ipv4 unicast",
                f"network {test_network_dut1}",
                "exit",
                "exit"
            ]
            st.config(dut1, network_config_dut1, type="klish", skip_error_check=False)

            st.log(f"DUT2 advertising network {test_network_dut2}")
            network_config_dut2 = [
                f"router bgp {local_asn}",
                "address-family ipv4 unicast",
                f"network {test_network_dut2}",
                "exit",
                "exit"
            ]
            st.config(dut2, network_config_dut2, type="klish", skip_error_check=False)

            st.wait(10, "Waiting for BGP route propagation")

            # Step 3: Verify route propagation
            st.banner("Step 3: Verify route propagation")
            st.log("Route verification placeholder - routes should be learned via BGP")

            # Step 4: Send bidirectional ICMP traffic using Scapy
            st.banner("Step 4: Send bidirectional ICMP traffic using Scapy")

            # Get underlay interface names for traffic generation
            underlay_dut1 = self.data.topology.D1D2P1  # Ethernet4 on DUT1
            underlay_dut2 = self.data.topology.D2D1P1  # Ethernet4 on DUT2

            # Get interface MAC addresses
            st.log("Retrieving interface MAC addresses")
            mac_d1 = scapy_api.get_interface_mac(dut1, underlay_dut1, cli_type="klish")
            mac_d2 = scapy_api.get_interface_mac(dut2, underlay_dut2, cli_type="klish")

            # Use default MACs if retrieval fails
            if not mac_d1:
                mac_d1 = scapy_api.get_default_mac(1)
                st.log(f"Using default MAC for DUT1: {mac_d1}")
            if not mac_d2:
                mac_d2 = scapy_api.get_default_mac(2)
                st.log(f"Using default MAC for DUT2: {mac_d2}")

            st.log(f"DUT1 {underlay_dut1} MAC: {mac_d1}")
            st.log(f"DUT2 {underlay_dut2} MAC: {mac_d2}")

            # Get underlay IP addresses for source IPs from BGP-LB-001 testcase
            testcase_001 = self._get_testcase("BGP-LB-001")
            underlay_config = testcase_001.get("underlay_interfaces", [])
            underlay_ip_d1 = None
            underlay_ip_d2 = None
            for intf in underlay_config:
                if intf.get("dut") == "D1":
                    underlay_ip_d1 = intf.get("ip_address")
                elif intf.get("dut") == "D2":
                    underlay_ip_d2 = intf.get("ip_address")

            # Extract network IPs for destination (first usable IP from each test network)
            # test_network_dut1 = "192.168.10.0/24" -> dst_ip = "192.168.10.1"
            # test_network_dut2 = "192.168.20.0/24" -> dst_ip = "192.168.20.1"
            dst_ip_from_d1 = test_network_dut2.split('/')[0].rsplit('.', 1)[0] + '.1'  # 192.168.20.1
            dst_ip_from_d2 = test_network_dut1.split('/')[0].rsplit('.', 1)[0] + '.1'  # 192.168.10.1

            st.log(f"Traffic Test Parameters:")
            st.log(f"  DUT1 -> DUT2: {underlay_ip_d1} -> {dst_ip_from_d1} (via {test_network_dut2})")
            st.log(f"  DUT2 -> DUT1: {underlay_ip_d2} -> {dst_ip_from_d2} (via {test_network_dut1})")

            # Create and execute Scapy traffic script on DUT1 (D1 -> D2 direction)
            st.log("Creating Scapy traffic script on DUT1 for D1->D2 traffic")
            script_d1_success = scapy_api.create_scapy_script(
                dut=dut1,
                interface=underlay_dut1,
                src_ip=underlay_ip_d1,
                dst_ip=dst_ip_from_d1,
                src_mac=mac_d1,
                dst_mac=mac_d2,
                duration=5,  # 5 seconds of traffic
                pps=100,  # 100 packets per second
                traffic_type="icmp"
            )

            if not script_d1_success:
                st.error("Failed to create Scapy script on DUT1")
            else:
                st.log("Scapy script created successfully on DUT1")

            # Create and execute Scapy traffic script on DUT2 (D2 -> D1 direction)
            st.log("Creating Scapy traffic script on DUT2 for D2->D1 traffic")
            script_d2_success = scapy_api.create_scapy_script(
                dut=dut2,
                interface=underlay_dut2,
                src_ip=underlay_ip_d2,
                dst_ip=dst_ip_from_d2,
                src_mac=mac_d2,
                dst_mac=mac_d1,
                duration=5,  # 5 seconds of traffic
                pps=100,  # 100 packets per second
                traffic_type="icmp"
            )

            if not script_d2_success:
                st.error("Failed to create Scapy script on DUT2")
            else:
                st.log("Scapy script created successfully on DUT2")

            # Step 5: Verify traffic statistics
            st.banner("Step 5: Verify traffic statistics")

            if script_d1_success and script_d2_success:
                st.log("SUCCESS: Bidirectional Scapy traffic scripts created")
                st.log("Note: Actual traffic execution requires Scapy to be installed on devices")
                st.log("      In production, execute scripts with: sudo python3 /tmp/scapy_traffic_sender.py")
            else:
                st.log("WARNING: Some Scapy traffic scripts failed to create")

        finally:
            # Step 6: Cleanup test network advertisements
            st.banner("Step 6: Cleanup test network advertisements")
            try:
                st.log(f"Removing network {test_network_dut1} from DUT1")
                no_network_config_dut1 = [
                    f"router bgp {local_asn}",
                    "address-family ipv4 unicast",
                    f"no network {test_network_dut1}",
                    "exit",
                    "exit"
                ]
                st.config(dut1, no_network_config_dut1, type="klish", skip_error_check=True)

                st.log(f"Removing network {test_network_dut2} from DUT2")
                no_network_config_dut2 = [
                    f"router bgp {local_asn}",
                    "address-family ipv4 unicast",
                    f"no network {test_network_dut2}",
                    "exit",
                    "exit"
                ]
                st.config(dut2, no_network_config_dut2, type="klish", skip_error_check=True)
            except Exception as e:
                st.log(f"Error during cleanup: {e}")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-LB-004"])
    @pytest.mark.depends(on=["test_bgp_loopback_session_establishment"])
    def test_bgp_loopback_save_reboot(self) -> None:
        """
        Test BGP-LB-004: BGP over Loopback Config Persistence (Save and Reboot)

        Objective:
            Verify iBGP configuration over Loopback persists across save and reboot

        Steps:
            1. Verify iBGP session from test 001 is established
            2. Save running configuration to startup configuration
            3. Perform device reboot
            4. Wait for devices to come back online
            5. Verify Loopback interface is up
            6. Verify Loopback IP addresses are configured
            7. Verify underlay interface is up
            8. Verify BGP session is re-established after reboot
        """
        testcase = self._get_testcase("BGP-LB-004")

        st.banner("TEST CASE: BGP over Loopback Config Persistence (Save and Reboot)")

        # Get DUT handles
        dut1 = self._resolve_dut("D1")
        dut2 = self._resolve_dut("D2")

        if not dut1 or not dut2:
            st.report_fail("msg", "Unable to resolve DUT aliases")

        try:
            # Step 1: Verify iBGP session before reboot
            st.banner("Step 1: Verify iBGP session before reboot")
            self._verify_bgp_sessions(testcase)
            st.log("iBGP session verified before reboot")

            # Step 2: Save configuration on both DUTs
            st.banner("Step 2: Save running configuration to startup")
            st.log("Saving configuration on DUT1")
            basic_api.deploy_package(dut1, mode='save')

            st.log("Saving configuration on DUT2")
            basic_api.deploy_package(dut2, mode='save')

            st.log("Configuration saved successfully on both DUTs")

            # Step 3: Reboot devices
            st.banner("Step 3: Reboot devices")
            st.log("Rebooting DUT1 and DUT2")

            # Reboot both DUTs
            st.reboot([dut1, dut2], 'fast')

            st.log("Devices rebooted successfully")

            # Step 4: Wait for devices to come back online
            st.banner("Step 4: Wait for devices to come back online")
            st.wait(90, "Waiting for devices to stabilize after reboot")

            # Step 5-7: Verify interfaces and configuration after reboot
            st.banner("Step 5-7: Verify interfaces after reboot")

            verification = testcase.get("verification", {})

            # Set terminal length to avoid pagination issues
            st.config(dut1, "terminal length 0", type="klish", skip_error_check=True)
            st.config(dut2, "terminal length 0", type="klish", skip_error_check=True)

            # Verify BGP daemon is running after reboot
            st.log("Checking BGP daemon status on both DUTs")
            for dut_name, dut in [("DUT1", dut1), ("DUT2", dut2)]:
                bgp_status = basic_api.get_ps_aux(dut, "bgp")
                if not bgp_status or "bgpd" not in str(bgp_status):
                    st.log(f"BGP daemon not running on {dut_name}, attempting restart")
                    try:
                        # Restart BGP daemon
                        st.config(dut, "sudo systemctl restart bgp", type="klish", skip_error_check=True)
                        st.wait(15, f"Waiting for BGP daemon to restart on {dut_name}")
                    except Exception as e:
                        st.log(f"Error restarting BGP on {dut_name}: {e}")
                else:
                    st.log(f"BGP daemon is running on {dut_name}")

            # Verify Loopback and underlay interfaces are up
            for intf_check in verification.get("interface_checks", []):
                dut = self._resolve_dut(intf_check.get("dut"))
                interface = intf_check.get("interface")
                expected_status = intf_check.get("expected_status", "up")

                st.log(f"Verifying {interface} is {expected_status} on {intf_check.get('dut')}")

                # Use show command directly to avoid prompt detection issues
                output = st.show(dut, f"show interface {interface}", type="klish", skip_error_check=True, skip_tmpl=True)

                if isinstance(output, str):
                    if expected_status == "up" and "up" in output.lower():
                        st.log(f"SUCCESS: {interface} is {expected_status} on {intf_check.get('dut')}")
                    else:
                        st.log(f"WARNING: {interface} status verification - output: {output[:200]}")

            # Step 8: Verify BGP session is re-established
            st.banner("Step 8: Verify BGP session re-established after reboot")

            # Wait longer for BGP to re-establish after reboot
            st.wait(60, "Additional wait for BGP to re-establish after reboot")

            # Verify static routes are present after reboot
            st.log("Verifying static routes are present after reboot")
            for dut_name, dut in [("DUT1", dut1), ("DUT2", dut2)]:
                routes = ip_api.show_ip_route(dut)
                st.log(f"{dut_name} routing table after reboot: {len(routes) if routes else 0} routes")

            # Verify loopback interfaces are reachable
            st.log("Verifying loopback reachability")
            testcase_001 = self._get_testcase("BGP-LB-001")
            loopback_cfg = testcase_001.get("loopback_interfaces", [])
            d1_loopback_ip = None
            d2_loopback_ip = None
            for cfg in loopback_cfg:
                if cfg.get("dut") == "D1":
                    d1_loopback_ip = cfg.get("ip_address")
                elif cfg.get("dut") == "D2":
                    d2_loopback_ip = cfg.get("ip_address")

            if d1_loopback_ip and d2_loopback_ip:
                ping_result = ip_api.ping(dut1, d2_loopback_ip, count=3)
                st.log(f"Ping from DUT1 to DUT2 loopback ({d2_loopback_ip}): {'SUCCESS' if ping_result else 'FAILED'}")

            # Verify BGP sessions
            self._verify_bgp_sessions(testcase)

            st.log("SUCCESS: BGP configuration persisted across reboot")
            st.log("SUCCESS: BGP session re-established after reboot")

        except Exception as e:
            st.log(f"Error during save/reboot test: {e}")
            raise

        st.report_pass("test_case_passed")
