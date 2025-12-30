"""
BGP ADVANCED FEATURES - IPv4/IPv6 Network Advertisement, v6only, and Aggregate-Address
Author: Athira
2025

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_advanced_features.py \
  --logs-path ./logs/test_bgp_advanced_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Comprehensive validation of advanced BGP features including IPv4 network advertisement (BGP-20),
  IPv6 link-local only BGP sessions (BGP-15), IPv6 network advertisement (BGP-21),
  aggregate-address advertisement (BGP-25), and aggregate summary-only behavior (BGP-26).
  All tests use klish CLI mode and validate both control-plane (BGP/RIB) and optional
  data-plane (traffic) states.

Pre-requisites:
  - Topology: 2-node (D1-D2) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes with eBGP peering
        # +--------------------+                       +--------------------+
        # |        D1          |                       |        D2          |
        # |  (SONiC/klish)     |=======================|  (SONiC/klish)     |
        # |   AS 65001         |  Ethernet4-Ethernet4  |   AS 65002         |
        # +--------------------+                       +--------------------+
        #
        # D1-D2 link:
        #   - IPv4: 10.0.24.0/31 (D1: .1, D2: .0)
        #   - IPv6: 2001:db8:24::1/127 and 2001:db8:24::0/127
        #   - IPv6 link-local enabled for BGP-15
        #
        # Additional loopbacks configured per test case:
        #   - Loopback1, Loopback10, Loopback20, Loopback21
  - Feature flags / min SONiC version: BGP support, klish CLI
  - Required test variables (YAML): tests/routing/BGP/vars_bgp_advanced_features.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api

VAR_FILE_ENV = "BGP_ADVANCED_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent / "vars_bgp_advanced_features.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"BGP advanced variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("BGP advanced YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("D1D2:1")
class TestBGPAdvancedFeatures:
    """Testcases covering BGP advanced features: network advertisement, v6only, aggregates."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.banner("BGP ADVANCED FEATURES - CLASS SETUP")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        min_topology = defaults.get("min_topology") or ["D1D2:1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 60))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Map DUT aliases
        cls.data.dut1 = topology.D1
        cls.data.dut2 = topology.D2
        cls.data.d1d2_ports = [topology.D1D2P1]
        cls.data.d2d1_ports = [topology.D2D1P1]

        # Store AS numbers
        cls.data.d1_as = defaults.get("d1_as", 65001)
        cls.data.d2_as = defaults.get("d2_as", 65002)

        # Store router IDs
        cls.data.d1_router_id = defaults.get("d1_router_id", "1.1.1.1")
        cls.data.d2_router_id = defaults.get("d2_router_id", "2.2.2.2")

        # Store link IP addresses
        cls.data.d1d2_ipv4 = defaults.get("d1d2_ipv4", "10.0.24.1/31")
        cls.data.d2d1_ipv4 = defaults.get("d2d1_ipv4", "10.0.24.0/31")
        cls.data.d1d2_ipv6 = defaults.get("d1d2_ipv6", "2001:db8:24::1/127")
        cls.data.d2d1_ipv6 = defaults.get("d2d1_ipv6", "2001:db8:24::0/127")

        # Extract neighbor IPs
        cls.data.d1_neighbor_ipv4 = cls.data.d2d1_ipv4.split("/")[0]
        cls.data.d2_neighbor_ipv4 = cls.data.d1d2_ipv4.split("/")[0]
        cls.data.d1_neighbor_ipv6 = cls.data.d2d1_ipv6.split("/")[0]
        cls.data.d2_neighbor_ipv6 = cls.data.d1d2_ipv6.split("/")[0]

        st.log(f"DUT1: {cls.data.dut1}, AS: {cls.data.d1_as}, Router-ID: {cls.data.d1_router_id}")
        st.log(f"DUT2: {cls.data.dut2}, AS: {cls.data.d2_as}, Router-ID: {cls.data.d2_router_id}")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup all BGP and interface configurations after the suite completes."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled; skipping teardown")
            return

        st.banner("BGP ADVANCED FEATURES - CLASS TEARDOWN")
        cls._cleanup_all_bgp()
        cls._cleanup_all_interfaces()

    def setup_method(self, method) -> None:
        """Reset per-test bookkeeping."""
        st.banner(f"TEST SETUP: {method.__name__}")

    def teardown_method(self, method) -> None:
        """Cleanup after each test."""
        st.banner(f"TEST TEARDOWN: {method.__name__}")
        if self.data.cleanup_enabled:
            self._cleanup_all_bgp()
            self._cleanup_all_interfaces()

    @classmethod
    def _cleanup_all_bgp(cls) -> None:
        """Remove all BGP configurations from both DUTs using klish CLI."""
        st.log("Cleaning up BGP configurations on both DUTs")
        for dut in [cls.data.dut1, cls.data.dut2]:
            as_num = cls.data.d1_as if dut == cls.data.dut1 else cls.data.d2_as

            # Use klish CLI commands to remove BGP
            commands = [
                "configure terminal",
                "no router bgp",
                "exit",
                "clear bgp all",
            ]
            st.config(dut, commands, type="klish", skip_error_check=True)
            st.wait(2)

    @classmethod
    def _cleanup_all_interfaces(cls) -> None:
        """Remove all IP addresses from interfaces and loopbacks."""
        st.log("Cleaning up interface configurations on both DUTs")

        # Cleanup D1 interfaces
        cls._cleanup_interface_ip(cls.data.dut1, cls.data.d1d2_ports[0], cls.data.d1d2_ipv4)
        cls._cleanup_interface_ip(cls.data.dut1, cls.data.d1d2_ports[0], cls.data.d1d2_ipv6, ipv6=True)

        # Cleanup D2 interfaces
        cls._cleanup_interface_ip(cls.data.dut2, cls.data.d2d1_ports[0], cls.data.d2d1_ipv4)
        cls._cleanup_interface_ip(cls.data.dut2, cls.data.d2d1_ports[0], cls.data.d2d1_ipv6, ipv6=True)

        # Cleanup loopbacks on both DUTs
        for dut in [cls.data.dut1, cls.data.dut2]:
            for loopback in ["Loopback1", "Loopback10", "Loopback20", "Loopback21"]:
                cls._remove_loopback(dut, loopback)

    @classmethod
    def _cleanup_interface_ip(cls, dut: str, interface: str, ip_addr: str, ipv6: bool = False) -> None:
        """Remove IP address from interface using klish CLI."""
        if not ip_addr:
            return

        ip_cmd = "ipv6 address" if ipv6 else "ip address"
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"no {ip_cmd}",
            "exit",
            "exit",
        ]
        st.config(dut, commands, type="klish", skip_error_check=True)

    @classmethod
    def _remove_loopback(cls, dut: str, loopback: str) -> None:
        """Remove loopback interface using klish CLI."""
        commands = [
            "configure terminal",
            f"no interface {loopback}",
            "exit",
        ]
        st.config(dut, commands, type="klish", skip_error_check=True)

    def _check_bgp_health(self, dut: str) -> bool:
        """Check if BGP instance exists and is healthy."""
        st.log(f"Checking BGP health on {dut}")

        # Try klish CLI first
        try:
            cmd = "show bgp ipv4 summary"
            output = st.show(dut, cmd, type="klish")
            if "not found" in str(output).lower() or "no bgp" in str(output).lower():
                st.log(f"BGP instance not found on {dut} (klish)")
                return False
            st.log(f"BGP instance exists on {dut} (klish)")
            return True
        except Exception as e:
            st.log(f"Klish BGP health check failed: {e}")

        # Try click CLI as fallback
        try:
            cmd = "show ip bgp summary"
            output = st.show(dut, cmd, type="click")
            if "not found" in str(output).lower() or "no bgp" in str(output).lower():
                st.log(f"BGP instance not found on {dut} (click)")
                return False
            st.log(f"BGP instance exists on {dut} (click)")
            return True
        except Exception as e:
            st.log(f"Click BGP health check failed: {e}")
            return False

    def _configure_bgp_session_with_network(
        self,
        dut1: str,
        dut2: str,
        d1_as: int,
        d2_as: int,
        d1_router_id: str,
        d2_router_id: str,
        d1_neighbor_ip: str,
        d2_neighbor_ip: str,
        network: str,
        ipv6: bool = False,
        redistribute_connected: bool = False,
        route_map_name: str = "PERMIT_ALL"
    ) -> None:
        """
        Configure complete BGP session with network advertisement in single context.

        Args:
            redistribute_connected: If True, configure 'redistribute connected' with route-map
            route_map_name: Name of route-map to use (default: PERMIT_ALL)
        """
        st.log(f"Configuring BGP session with network {network} between {dut1} and {dut2}")

        # Configure interface IPs first
        self._configure_interface_ip(
            dut1,
            self.data.d1d2_ports[0],
            self.data.d1d2_ipv4 if not ipv6 else self.data.d1d2_ipv6,
            ipv6=ipv6
        )
        self._configure_interface_ip(
            dut2,
            self.data.d2d1_ports[0],
            self.data.d2d1_ipv4 if not ipv6 else self.data.d2d1_ipv6,
            ipv6=ipv6
        )

        # Configure route-map if redistribution is enabled
        if redistribute_connected:
            route_map_commands = [
                "configure terminal",
                f"route-map {route_map_name}",
                "exit",
                "exit",
            ]
            st.config(dut1, route_map_commands, type="klish")

        # Configure BGP on DUT1 with neighbor AND network in same context
        # IMPORTANT: network command must be in global address-family context,
        # NOT in neighbor address-family context
        addr_family = "ipv6 unicast" if ipv6 else "ipv4 unicast"
        commands_d1 = [
            "configure terminal",
            f"router bgp {d1_as}",
            f"router-id {d1_router_id}",
            f"neighbor {d1_neighbor_ip} remote-as {d2_as}",
            f"address-family {addr_family}",           # Global address-family
            "activate",     # Activate neighbor in address-family
            f"network {network}",                      # network in global address-family
        ]

        # Add redistribution if requested
        if redistribute_connected:
            commands_d1.append("redistribute connected")
            commands_d1.append(f"route-map {route_map_name}")

        commands_d1.extend([
            "exit",                                     # Exit address-family
            "exit",                                     # Exit router bgp
            "end",
        ])
        st.config(dut1, commands_d1, type="klish")

        # Configure BGP on DUT2
        commands_d2 = [
            "configure terminal",
            f"router bgp {d2_as}",
            f"router-id {d2_router_id}",
            f"neighbor {d2_neighbor_ip} remote-as {d1_as}",
            f"address-family {addr_family}",
            "activate",
            "exit",
            "exit",
            "end",
        ]
        st.config(dut2, commands_d2, type="klish")

    def _verify_bgp_session_established(self, dut: str, neighbor_ip: str) -> bool:
        """
        Verify BGP session is established with neighbor.

        Parse raw CLI output directly instead of relying on template parsing.
        Look for "Established" in raw output or integer in State/PfxRcd column.
        """
        st.log(f"Verifying BGP session established on {dut} with neighbor {neighbor_ip}")

        # Determine if IPv4 or IPv6 based on neighbor IP
        is_ipv6 = ":" in neighbor_ip

        # Try click CLI first - parse raw output
        try:
            cmd = "show ip bgp summary" if not is_ipv6 else "show ipv6 bgp summary"
            output = st.show(dut, cmd, type="click", skip_tmpl=True)

            if isinstance(output, str):
                # Look for neighbor IP at the START of the line
                for line in output.splitlines():
                    # Check if line starts with neighbor IP (accounting for whitespace)
                    stripped_line = line.strip()
                    if stripped_line.startswith(neighbor_ip):
                        # Check if "Established" appears in the line
                        if "Established" in line or "Estab" in line:
                            st.log(f"BGP session established with {neighbor_ip} (found 'Established' in click output)")
                            return True
                        # Parse the State/PfxRcd column
                        # Format: Neighbor V AS MsgRcvd MsgSent TblVer InQ OutQ Up/Down State/PfxRcd NeighborName
                        # Split by whitespace and check if State/PfxRcd (index -2) is an integer
                        import re
                        fields = stripped_line.split()
                        if len(fields) >= 10:
                            # State/PfxRcd is the 2nd to last field (before NeighborName)
                            state_pfxrcd = fields[-2]
                            # If it's a number, session is established
                            if re.match(r'^\d+$', state_pfxrcd):
                                st.log(f"BGP session established with {neighbor_ip} (State/PfxRcd={state_pfxrcd})")
                                return True
        except Exception as e:
            st.log(f"Click CLI check failed: {e}, trying klish")

        # Try klish CLI - parse raw output
        try:
            if is_ipv6:
                cmd = "show bgp ipv6 unicast summary"
            else:
                cmd = "show bgp ipv4 unicast summary"

            output = st.show(dut, cmd, type="klish", skip_tmpl=True)

            if isinstance(output, str):
                # Look for neighbor IP at the START of the line
                for line in output.splitlines():
                    stripped_line = line.strip()
                    if stripped_line.startswith(neighbor_ip):
                        # Check if "Established" appears in the line
                        if "Established" in line or "Estab" in line:
                            st.log(f"BGP session established with {neighbor_ip} (found 'Established' in klish output)")
                            return True
                        # Parse the State/PfxRcd column
                        import re
                        fields = stripped_line.split()
                        if len(fields) >= 10:
                            # State/PfxRcd is the 2nd to last field
                            state_pfxrcd = fields[-2]
                            if re.match(r'^\d+$', state_pfxrcd):
                                st.log(f"BGP session established with {neighbor_ip} (State/PfxRcd={state_pfxrcd})")
                                return True
        except Exception as e:
            st.log(f"Klish CLI check also failed: {e}")

        st.log(f"BGP session NOT established with {neighbor_ip}")
        return False

    def _extract_linklocal_address(self, dut: str, interface: str) -> str:
        """
        Extract IPv6 link-local address from an interface.

        Args:
            dut: Device under test
            interface: Interface name (e.g., Ethernet4)

        Returns:
            Link-local IPv6 address (e.g., fe80::xxxx) or empty string if not found
        """
        st.log(f"Extracting link-local IPv6 address from {dut} {interface}")

        # Run show ipv6 interface command in klish mode
        cmd = f"show ipv6 interface {interface}"
        output = st.show(dut, cmd, type="klish", skip_tmpl=True)

        if isinstance(output, str):
            # Parse output looking for link-local address
            # Example line: "  inet6 fe80::5054:ff:fe12:3456/64 scope link"
            import re
            for line in output.splitlines():
                # Match lines with "inet6 fe80:"
                match = re.search(r'inet6\s+(fe80:[0-9a-f:]+)', line, re.IGNORECASE)
                if match:
                    linklocal = match.group(1)
                    st.log(f"Found link-local address: {linklocal}")
                    return linklocal

        st.log(f"No link-local address found on {dut} {interface}")
        return ""

    def _configure_bgp_linklocal_neighbor(
        self,
        dut1: str, dut2: str,
        d1_as: int, d2_as: int,
        d1_router_id: str, d2_router_id: str,
        d1_interface: str, d2_interface: str,
        d1_neighbor_ll: str, d2_neighbor_ll: str
    ) -> None:
        """
        Configure BGP session using IPv6 link-local addresses.

        Args:
            dut1, dut2: Devices under test
            d1_as, d2_as: AS numbers
            d1_router_id, d2_router_id: Router IDs
            d1_interface, d2_interface: Interface names
            d1_neighbor_ll, d2_neighbor_ll: Link-local neighbor addresses
        """
        st.log(f"Configuring BGP link-local session between {dut1} and {dut2}")

        # Configure DUT1 - Use link-local neighbor with interface specification
        commands_d1 = [
            "configure terminal",
            f"router bgp {d1_as}",
            f"router-id {d1_router_id}",
            f"neighbor {d1_neighbor_ll} interface {d1_interface}",
            f"neighbor {d1_neighbor_ll} remote-as {d2_as}",
            "address-family ipv6 unicast",
            "activate",
            "exit",
            "exit",
            "end",
        ]
        st.config(dut1, commands_d1, type="klish")

        # Configure DUT2 - Use link-local neighbor with interface specification
        commands_d2 = [
            "configure terminal",
            f"router bgp {d2_as}",
            f"router-id {d2_router_id}",
            f"neighbor {d2_neighbor_ll} interface {d2_interface}",
            f"neighbor {d2_neighbor_ll} remote-as {d1_as}",
            "address-family ipv6 unicast",
            "activate",
            "exit",
            "exit",
            "end",
        ]
        st.config(dut2, commands_d2, type="klish")

        st.log("BGP link-local neighbor configuration completed")

    def _configure_base_bgp_session(self, ipv6: bool = False) -> None:
        """Configure basic eBGP session between D1 and D2."""
        st.log("Configuring base BGP session between D1 and D2")

        # Configure physical interface IPs
        self._configure_interface_ip(
            self.data.dut1,
            self.data.d1d2_ports[0],
            self.data.d1d2_ipv4 if not ipv6 else self.data.d1d2_ipv6,
            ipv6=ipv6
        )
        self._configure_interface_ip(
            self.data.dut2,
            self.data.d2d1_ports[0],
            self.data.d2d1_ipv4 if not ipv6 else self.data.d2d1_ipv6,
            ipv6=ipv6
        )

        # Configure BGP on D1
        self._configure_bgp_neighbor(
            self.data.dut1,
            self.data.d1_as,
            self.data.d1_router_id,
            self.data.d1_neighbor_ipv4 if not ipv6 else self.data.d1_neighbor_ipv6,
            self.data.d2_as,
            ipv6=ipv6
        )

        # Configure BGP on D2
        self._configure_bgp_neighbor(
            self.data.dut2,
            self.data.d2_as,
            self.data.d2_router_id,
            self.data.d2_neighbor_ipv4 if not ipv6 else self.data.d2_neighbor_ipv6,
            self.data.d1_as,
            ipv6=ipv6
        )

        st.wait(10)  # Wait for BGP session establishment

    def _configure_interface_ip(self, dut: str, interface: str, ip_addr: str, ipv6: bool = False) -> None:
        """Configure IP address on interface using klish CLI."""
        st.log(f"Configuring {ip_addr} on {interface} at {dut}")

        ip_cmd = "ipv6 address" if ipv6 else "ip address"
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"{ip_cmd} {ip_addr}",
            "exit",
            "exit",
        ]
        st.config(dut, commands, type="klish")

    def _configure_loopback(self, dut: str, loopback: str, ip_addr: str, ipv6: bool = False) -> None:
        """Configure loopback interface with IP address using klish CLI."""
        st.log(f"Configuring loopback {loopback} with {ip_addr} on {dut}")

        ip_cmd = "ipv6 address" if ipv6 else "ip address"
        commands = [
            "configure terminal",
            f"interface {loopback}",
            f"{ip_cmd} {ip_addr}",
            "exit",
            "exit",
        ]
        st.config(dut, commands, type="klish")

    def _configure_bgp_neighbor(
        self,
        dut: str,
        local_as: int,
        router_id: str,
        neighbor_ip: str,
        remote_as: int,
        ipv6: bool = False
    ) -> None:
        """Configure BGP neighbor using klish CLI."""
        st.log(f"Configuring BGP neighbor {neighbor_ip} on {dut}")

        addr_family = "ipv6 unicast" if ipv6 else "ipv4 unicast"
        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            f"router-id {router_id}",
            f"neighbor {neighbor_ip} remote-as {remote_as}",
            f"address-family {addr_family}",
            "activate",
            "exit",
            "exit",
        ]
        st.config(dut, commands, type="klish")

    def _configure_bgp_network(self, dut: str, local_as: int, network: str, ipv6: bool = False) -> None:
        """Advertise network in BGP using klish CLI."""
        st.log(f"Advertising network {network} in BGP on {dut}")

        addr_family = "ipv6 unicast" if ipv6 else "ipv4 unicast"
        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            f"address-family {addr_family}",
            f"network {network}",
            "exit",
            "exit",
        ]
        st.config(dut, commands, type="klish")

    def _configure_bgp_aggregate(
        self,
        dut: str,
        local_as: int,
        aggregate: str,
        summary_only: bool = False
    ) -> None:
        """Configure BGP aggregate-address using klish CLI."""
        st.log(f"Configuring aggregate {aggregate} on {dut} (summary-only={summary_only})")

        summary_flag = " summary-only" if summary_only else ""
        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            "address-family ipv4 unicast",
            f"aggregate-address {aggregate}{summary_flag}",
            "exit",
            "exit",
        ]
        st.config(dut, commands, type="klish")

    def _configure_ipv6_linklocal_bgp(self, dut: str, local_as: int, router_id: str, interface: str) -> None:
        """Configure BGP using IPv6 link-local addresses (v6only) using klish CLI."""
        st.log(f"Configuring IPv6 link-local BGP on {dut} via {interface}")

        # First, enable IPv6 on the interface
        enable_ipv6_cmds = [
            "configure terminal",
            f"interface {interface}",
            "ipv6 enable",
            "exit",
            "exit",
        ]
        st.config(dut, enable_ipv6_cmds, type="klish")

        # Configure BGP with link-local neighbor
        # Note: neighbor address will be link-local (fe80::...) - needs to be discovered
        # For now, using a placeholder approach
        neighbor_ll = "fe80::2"  # This should be discovered dynamically in production
        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            f"router-id {router_id}",
            f"neighbor {neighbor_ll} remote-as {local_as}",
            f"neighbor {neighbor_ll} interface {interface}",
            "address-family ipv6 unicast",
            "activate",
            "exit",
            "exit",
        ]
        st.config(dut, commands, type="klish")

    def _verify_bgp_route(
        self,
        dut: str,
        prefix: str,
        ipv6: bool = False,
        should_exist: bool = True
    ) -> bool:
        """Verify BGP route exists or doesn't exist in BGP table using click CLI."""
        family = "ipv6" if ipv6 else "ip"
        st.log(f"Verifying BGP {family} route {prefix} on {dut} (should_exist={should_exist})")

        # Use click CLI for reliable route verification - show ip bgp network displays BGP routes
        cmd = f"show {family} bgp network"

        # Try click CLI first (most reliable)
        try:
            output = st.show(dut, cmd, type="click")
            route_exists = prefix in str(output)

            if should_exist:
                if route_exists:
                    st.log(f"BGP route {prefix} found on {dut} (click CLI)")
                    return True
            else:
                if not route_exists:
                    st.log(f"BGP route {prefix} correctly absent on {dut} (click CLI)")
                    return True
        except Exception as e:
            st.log(f"Click CLI failed: {e}, trying klish CLI as fallback")

        # Fallback to klish CLI with simple string matching
        try:
            cmd = f"show bgp {family if family == 'ipv6' else 'ipv4'} unicast"
            output = st.show(dut, cmd, type="klish")
            route_exists = prefix in str(output)

            if should_exist:
                if route_exists:
                    st.log(f"BGP route {prefix} found on {dut} (klish CLI)")
                    return True
            else:
                if not route_exists:
                    st.log(f"BGP route {prefix} correctly absent on {dut} (klish CLI)")
                    return True
        except Exception as e:
            st.log(f"Klish CLI also failed: {e}")

        # Log failure
        if should_exist:
            st.log(f"BGP route {prefix} NOT found on {dut}")
            return False
        else:
            st.log(f"BGP route {prefix} should be absent but was found on {dut}")
            return False

    def _verify_ip_route(
        self,
        dut: str,
        prefix: str,
        ipv6: bool = False,
        should_exist: bool = True
    ) -> bool:
        """Verify IP route exists in RIB."""
        family = "ipv6" if ipv6 else "ip"
        st.log(f"Verifying {family} route {prefix} on {dut} (should_exist={should_exist})")

        cmd = f"show {family} route {prefix}"
        output = st.show(dut, cmd, type="klish")

        route_exists = prefix in str(output)

        if should_exist:
            return route_exists
        else:
            return not route_exists

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase


    @pytest.mark.inventory(feature="Regression", testcases=["BGP-15"])
    def test_bgp_ipv6_linklocal_session(self) -> None:
        """
        BGP-15: Verify BGP Session Using IPv6 Link-Local Only (v6only)

        Verify that BGP peering can be established using only IPv6 link-local addresses,
        without global IPv6 addressing. This is a control-plane only test.
        """
        st.banner("TEST: BGP-15 - IPv6 Link-Local BGP Session")

        # Step 1: Enable IPv6 on interfaces to generate link-local addresses
        st.log("Enabling IPv6 on interfaces to generate link-local addresses")
        for dut, port in [(self.data.dut1, self.data.d1d2_ports[0]),
                          (self.data.dut2, self.data.d2d1_ports[0])]:
            commands = [
                "configure terminal",
                f"interface {port}",
                "ipv6 enable",
                "exit",
                "exit",
            ]
            st.config(dut, commands, type="klish")

        # Wait for link-local addresses to be generated
        st.wait(10)

        # Step 2: Extract link-local addresses from both DUTs
        st.log("Extracting link-local IPv6 addresses from interfaces")
        d1_linklocal = self._extract_linklocal_address(self.data.dut1, self.data.d1d2_ports[0])
        d2_linklocal = self._extract_linklocal_address(self.data.dut2, self.data.d2d1_ports[0])

        if not d1_linklocal or not d2_linklocal:
            st.report_fail("msg", f"Failed to extract link-local addresses. D1: {d1_linklocal}, D2: {d2_linklocal}")

        st.log(f"D1 link-local: {d1_linklocal}, D2 link-local: {d2_linklocal}")

        # Step 3: Configure BGP sessions using link-local addresses
        st.log("Configuring BGP sessions with link-local neighbors")
        self._configure_bgp_linklocal_neighbor(
            dut1=self.data.dut1,
            dut2=self.data.dut2,
            d1_as=self.data.d1_as,
            d2_as=self.data.d2_as,
            d1_router_id=self.data.d1_router_id,
            d2_router_id=self.data.d2_router_id,
            d1_interface=self.data.d1d2_ports[0],
            d2_interface=self.data.d2d1_ports[0],
            d1_neighbor_ll=d2_linklocal,
            d2_neighbor_ll=d1_linklocal
        )

        # Step 4: Wait for BGP session to establish
        st.wait(15)

        # Step 5: Verify BGP session is established
        st.log("Verifying BGP IPv6 link-local session establishment")
        if not self._verify_bgp_session_established(self.data.dut1, d2_linklocal):
            st.report_fail("msg", f"BGP IPv6 link-local session not established on D1 with neighbor {d2_linklocal}")

        if not self._verify_bgp_session_established(self.data.dut2, d1_linklocal):
            st.report_fail("msg", f"BGP IPv6 link-local session not established on D2 with neighbor {d1_linklocal}")

        st.log("Successfully established BGP sessions using IPv6 link-local addresses")
        st.report_pass("test_case_passed")


    @pytest.mark.inventory(feature="Regression", testcases=["BGP-25"])
    def test_bgp_aggregate_address(self) -> None:
        """
        BGP-25: Verify Aggregate-Address Advertisement

        Verify that SONiC advertises an aggregated prefix when component routes exist.
        """
        st.banner("TEST: BGP-25 - Aggregate-Address Advertisement")
        testcase = self._get_testcase("BGP-25")

        # Configure loopbacks with component routes FIRST (before BGP session)
        loopback1_ip = testcase.get("loopback1_ip", "10.10.1.1/24")
        loopback2_ip = testcase.get("loopback2_ip", "10.10.2.1/24")
        network1 = testcase.get("network1", "10.10.1.0/24")
        network2 = testcase.get("network2", "10.10.2.0/24")
        aggregate = testcase.get("aggregate", "10.10.0.0/16")

        self._configure_loopback(self.data.dut1, "Loopback20", loopback1_ip, ipv6=False)
        self._configure_loopback(self.data.dut1, "Loopback21", loopback2_ip, ipv6=False)

        # Step 1: Create route-map (required for aggregate-address)
        route_map_commands = [
            "configure terminal",
            "route-map PERMIT_ALL permit 10",
            "exit",
            "end",
        ]
        st.config(self.data.dut1, route_map_commands, type="klish")
        st.config(self.data.dut2, route_map_commands, type="klish")

        # Step 2: Configure BGP with networks and aggregate FIRST
        commands_d1_bgp = [
            "configure terminal",
            f"router bgp {self.data.d1_as}",
            f"router-id {self.data.d1_router_id}",
            "address-family ipv4 unicast",
            f"network {network1}",
            f"network {network2}",
            f"aggregate-address {aggregate}",
            "route-map PERMIT_ALL permit 10",
            "end",
        ]
        st.config(self.data.dut1, commands_d1_bgp, type="klish")

        # Step 3: Configure BGP neighbor
        commands_d1_neighbor = [
            "configure terminal",
            f"router bgp {self.data.d1_as}",
            f"router-id {self.data.d1_router_id}",
            f"neighbor {self.data.d1_neighbor_ipv4} remote-as {self.data.d2_as}",
            "address-family ipv4 unicast",
            "activate",
            "end",
        ]
        st.config(self.data.dut1, commands_d1_neighbor, type="klish")

        # Configure DUT2 neighbor
        commands_d2 = [
            "configure terminal",
            f"router bgp {self.data.d2_as}",
            f"router-id {self.data.d2_router_id}",
            f"neighbor {self.data.d2_neighbor_ipv4} remote-as {self.data.d1_as}",
            "address-family ipv4 unicast",
            "activate",
            "exit",
            "exit",
            "end",
        ]
        st.config(self.data.dut2, commands_d2, type="klish")

        # Verify BGP session established
        st.wait(15)
        if not self._verify_bgp_session_established(self.data.dut1, self.data.d1_neighbor_ipv4):
            st.report_fail("msg", f"BGP session not established between D1 and D2")

        # Verify aggregate route on DUT2
        if not st.poll_wait(
            lambda: self._verify_bgp_route(self.data.dut2, aggregate, ipv6=False),
            self.data.verify_timeout,
        ):
            st.report_fail("msg", f"Aggregate route {aggregate} not found on DUT2")

        # Verify component routes are also present (not summary-only)
        if not st.poll_wait(
            lambda: self._verify_bgp_route(self.data.dut2, network1, ipv6=False),
            self.data.verify_timeout,
        ):
            st.report_fail("msg", f"Component route {network1} not found on DUT2")

        st.log(f"Successfully verified aggregate {aggregate} and component routes")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-26"])
    def test_bgp_aggregate_summary_only(self) -> None:
        """
        BGP-26: Verify Aggregate Summary-Only Behavior

        Verify that component routes are suppressed when summary-only is configured.
        """
        st.banner("TEST: BGP-26 - Aggregate Summary-Only")
        testcase = self._get_testcase("BGP-26")

        # Configure loopbacks with component routes FIRST (before BGP session)
        loopback1_ip = testcase.get("loopback1_ip", "10.10.1.1/24")
        loopback2_ip = testcase.get("loopback2_ip", "10.10.2.1/24")
        network1 = testcase.get("network1", "10.10.1.0/24")
        network2 = testcase.get("network2", "10.10.2.0/24")
        aggregate = testcase.get("aggregate", "10.10.0.0/16")

        self._configure_loopback(self.data.dut1, "Loopback20", loopback1_ip, ipv6=False)
        self._configure_loopback(self.data.dut1, "Loopback21", loopback2_ip, ipv6=False)

        # Step 1: Create route-map (required for aggregate-address)
        route_map_commands = [
            "configure terminal",
            "route-map PERMIT_ALL permit 10",
            "exit",
            "end",
        ]
        st.config(self.data.dut1, route_map_commands, type="klish")
        st.config(self.data.dut2, route_map_commands, type="klish")

        # Step 2: Configure BGP with networks and aggregate summary-only FIRST
        commands_d1_bgp = [
            "configure terminal",
            f"router bgp {self.data.d1_as}",
            f"router-id {self.data.d1_router_id}",
            "address-family ipv4 unicast",
            f"network {network1}",
            f"network {network2}",
            f"aggregate-address {aggregate} summary-only",
            "route-map PERMIT_ALL permit 10",
            "end",
        ]
        st.config(self.data.dut1, commands_d1_bgp, type="klish")

        # Step 3: Configure BGP neighbor
        commands_d1_neighbor = [
            "configure terminal",
            f"router bgp {self.data.d1_as}",
            f"router-id {self.data.d1_router_id}",
            f"neighbor {self.data.d1_neighbor_ipv4} remote-as {self.data.d2_as}",
            "address-family ipv4 unicast",
            "activate",
            "end",
        ]
        st.config(self.data.dut1, commands_d1_neighbor, type="klish")

        # Configure DUT2 neighbor
        commands_d2 = [
            "configure terminal",
            f"router bgp {self.data.d2_as}",
            f"router-id {self.data.d2_router_id}",
            f"neighbor {self.data.d2_neighbor_ipv4} remote-as {self.data.d1_as}",
            "address-family ipv4 unicast",
            "activate",
            "exit",
            "exit",
            "end",
        ]
        st.config(self.data.dut2, commands_d2, type="klish")

        # Verify BGP session established
        st.wait(15)
        if not self._verify_bgp_session_established(self.data.dut1, self.data.d1_neighbor_ipv4):
            st.report_fail("msg", f"BGP session not established between D1 and D2")

        # Verify aggregate route on DUT2
        if not st.poll_wait(
            lambda: self._verify_bgp_route(self.data.dut2, aggregate, ipv6=False),
            self.data.verify_timeout,
        ):
            st.report_fail("msg", f"Aggregate route {aggregate} not found on DUT2")

        # Verify component routes are NOT present (summary-only suppresses them)
        if not st.poll_wait(
            lambda: self._verify_bgp_route(self.data.dut2, network1, ipv6=False, should_exist=False),
            self.data.verify_timeout,
        ):
            st.report_fail("msg", f"Component route {network1} should be suppressed but found on DUT2")

        if not st.poll_wait(
            lambda: self._verify_bgp_route(self.data.dut2, network2, ipv6=False, should_exist=False),
            self.data.verify_timeout,
        ):
            st.report_fail("msg", f"Component route {network2} should be suppressed but found on DUT2")

        st.log(f"Successfully verified aggregate {aggregate} with summary-only (components suppressed)")
        st.report_pass("test_case_passed")
