"""
BGP MED AND WEIGHT ATTRIBUTES - Path Selection Testing
Author: Athira
2025

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ~/hp/Athira/testbed_vs_3rr.yaml \
  tests/routing/BGP/test_bgp_med_weight.py \
  --logs-path ./logs/test_bgp_med_weight_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Comprehensive validation of BGP path selection attributes including MED
  (Multi-Exit Discriminator) attribute propagation (BGP-34) and weight
  attribute priority in inbound route selection (BGP-35).

  All tests use klish CLI mode and validate BGP path selection behavior
  in a 3-node linear topology.

Pre-requisites:
  - Topology: 3-node (D1-D2-D3) linear | Supported: HW and Virtual
  - Topology Diagram:
        # BGP-34 Topology (MED Test - SAME AS for D1 and D3):
        # +----------+         +----------+         +----------+
        # |    D1    |=========|    D2    |=========|    D3    |
        # | AS 65001 |  Link1  | AS 65002 |  Link2  | AS 65001 |
        # +----------+         +----------+         +----------+
        #
        # BGP-35 Topology (Weight Test - Different AS):
        # +----------+         +----------+         +----------+
        # |    D1    |=========|    D2    |=========|    D3    |
        # | AS 65001 |  Link1  | AS 65002 |  Link2  | AS 65003 |
        # +----------+         +----------+         +----------+
        #
        # D1-D2 link:
        #   - IPv4: 10.10.1.0/24 (D1: .1, D2: .2)
        #
        # D2-D3 link:
        #   - IPv4: 10.10.2.0/24 (D2: .1, D3: .2)
        #
        # Test networks:
        #   - BGP-34: 10.1.0.0/24 (advertised from D1 and D3 with different MEDs)
        #   - BGP-35: 10.2.0.0/24 (advertised from D1 and D3 with different weights)
  - Feature flags / min SONiC version: BGP support, klish CLI
  - Required test variables (YAML): tests/routing/BGP/vars_bgp_med_weight.yaml
"""

from pathlib import Path
from typing import Any, Dict, List, Mapping
import re

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api
from apis.routing.route_map import RouteMap

VAR_FILE_ENV = "BGP_MED_WEIGHT_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent / "vars_bgp_med_weight.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"BGP MED/Weight variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("BGP MED/Weight YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("D1D2:1", "D2D3:1")
class TestBGPMedWeight:
    """Testcases covering BGP MED and weight attribute path selection."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.banner("BGP MED/WEIGHT ATTRIBUTES - CLASS SETUP")
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        min_topology = defaults.get("min_topology") or ["D1D2:1", "D2D3:1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 60))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Map DUT aliases for 3-node topology
        cls.data.dut1 = topology.D1
        cls.data.dut2 = topology.D2
        cls.data.dut3 = topology.D3
        cls.data.d1d2_ports = [topology.D1D2P1]
        cls.data.d2d1_ports = [topology.D2D1P1]
        cls.data.d2d3_ports = [topology.D2D3P1]
        cls.data.d3d2_ports = [topology.D3D2P1]

        # Store AS numbers from defaults (testcases can override these)
        cls.data.d1_as = cls.data.defaults.get("d1_as")
        cls.data.d2_as = cls.data.defaults.get("d2_as")
        cls.data.d3_as = cls.data.defaults.get("d3_as")

        # Store router IDs from YAML
        cls.data.d1_router_id = cls.data.defaults.get("d1_router_id")
        cls.data.d2_router_id = cls.data.defaults.get("d2_router_id")
        cls.data.d3_router_id = cls.data.defaults.get("d3_router_id")

        # Store link IP addresses from YAML
        cls.data.d1d2_ipv4 = cls.data.defaults.get("d1d2_ipv4")
        cls.data.d2d1_ipv4 = cls.data.defaults.get("d2d1_ipv4")
        cls.data.d2d3_ipv4 = cls.data.defaults.get("d2d3_ipv4")
        cls.data.d3d2_ipv4 = cls.data.defaults.get("d3d2_ipv4")

        # Extract neighbor IPs
        cls.data.d1_neighbor_ipv4 = cls.data.d2d1_ipv4.split("/")[0]
        cls.data.d2_d1_neighbor_ipv4 = cls.data.d1d2_ipv4.split("/")[0]
        cls.data.d2_d3_neighbor_ipv4 = cls.data.d3d2_ipv4.split("/")[0]
        cls.data.d3_neighbor_ipv4 = cls.data.d2d3_ipv4.split("/")[0]

        st.log(f"DUT1: {cls.data.dut1}, AS: {cls.data.d1_as}, Router-ID: {cls.data.d1_router_id}")
        st.log(f"DUT2: {cls.data.dut2}, AS: {cls.data.d2_as}, Router-ID: {cls.data.d2_router_id}")
        st.log(f"DUT3: {cls.data.dut3}, AS: {cls.data.d3_as}, Router-ID: {cls.data.d3_router_id}")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup all BGP and interface configurations after the suite completes."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled; skipping teardown")
            return

        st.banner("BGP MED/WEIGHT ATTRIBUTES - CLASS TEARDOWN")
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
        """Remove all BGP configurations from all DUTs using BGP API."""
        st.log("Cleaning up BGP configurations on all DUTs")
        for dut in [cls.data.dut1, cls.data.dut2, cls.data.dut3]:
            # Exit from any config mode first to ensure clean state
            st.config(dut, "end", type="klish", skip_error_check=True)
            # Use unconfig_router_bgp which is more robust - removes BGP regardless of AS number
            bgp_api.unconfig_router_bgp(dut, cli_type=cls.data.cli_type, skip_error_check=True)
            st.wait(3)  # Wait for BGP to fully shut down

    @classmethod
    def _cleanup_all_interfaces(cls) -> None:
        """Remove all IP addresses from interfaces and loopbacks."""
        st.log("Cleaning up interface configurations on all DUTs")

        # Cleanup D1 interfaces
        cls._cleanup_interface_ip(cls.data.dut1, cls.data.d1d2_ports[0], cls.data.d1d2_ipv4)

        # Cleanup D2 interfaces
        cls._cleanup_interface_ip(cls.data.dut2, cls.data.d2d1_ports[0], cls.data.d2d1_ipv4)
        cls._cleanup_interface_ip(cls.data.dut2, cls.data.d2d3_ports[0], cls.data.d2d3_ipv4)

        # Cleanup D3 interfaces
        cls._cleanup_interface_ip(cls.data.dut3, cls.data.d3d2_ports[0], cls.data.d3d2_ipv4)

        # Cleanup loopbacks, static routes, and route-maps on all DUTs
        for dut in [cls.data.dut1, cls.data.dut2, cls.data.dut3]:
            # Remove static routes used in tests
            cls._remove_static_route(dut, "10.1.0.0/24", "blackhole")
            cls._remove_static_route(dut, "10.2.0.0/24", "blackhole")
            # Remove loopbacks (this also removes the connected routes)
            for loopback in ["Loopback10", "Loopback20"]:
                cls._remove_loopback(dut, loopback)
            # Cleanup route-maps
            cls._remove_route_map(dut, "SET_MED_100")
            cls._remove_route_map(dut, "SET_MED_50")
            cls._remove_route_map(dut, "PREPEND_AS")

    @classmethod
    def _cleanup_interface_ip(cls, dut: str, interface: str, ip_addr: str) -> None:
        """Remove IP address from interface using klish CLI."""
        if not ip_addr:
            return

        # Try to remove the specific IP address first (in case it's on a different interface)
        # Extract just the IP/prefix without splitting
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"no ip address {ip_addr}",
            "exit",
            "exit",
        ]
        st.config(dut, commands, type="klish", skip_error_check=True)

        # Also try to remove all IP addresses from the interface (more aggressive cleanup)
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no ip address",
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

    @classmethod
    def _remove_static_route(cls, dut: str, network: str, nexthop: str) -> None:
        """Remove static route using klish CLI."""
        # In klish mode, use 'blackhole' keyword instead of 'Null0' interface
        if nexthop.lower() in ["null0", "null"]:
            nexthop = "blackhole"

        commands = [
            "configure terminal",
            f"no ip route {network} {nexthop}",
            "exit",
        ]
        st.config(dut, commands, type="klish", skip_error_check=True)

    @classmethod
    def _remove_route_map(cls, dut: str, route_map: str) -> None:
        """Remove route-map using klish CLI."""
        commands = [
            "configure terminal",
            f"no route-map {route_map}",
            "exit",
        ]
        st.config(dut, commands, type="klish", skip_error_check=True)


    def _remove_ip_from_all_interfaces(self, dut: str, ip_addr: str) -> None:
        """
        Remove specific IP address from all interfaces on the DUT.
        This prevents 'IP already configured on different interface' errors.
        """
        st.log(f"Removing IP {ip_addr} from all interfaces on {dut} (if present)")

        # Try to remove from common interface names that might have the IP
        common_interfaces = [
            "Ethernet0", "Ethernet4", "Ethernet8", "Ethernet12",
            "Ethernet16", "Ethernet20", "Ethernet24", "Ethernet28",
            "Ethernet32", "Ethernet36", "Ethernet40", "Ethernet44",
            "Ethernet48", "Ethernet52", "Ethernet56", "Ethernet60"
        ]

        for intf in common_interfaces:
            commands = [
                "configure terminal",
                f"interface {intf}",
                f"no ip address {ip_addr}",
                "exit",
                "exit",
            ]
            st.config(dut, commands, type="klish", skip_error_check=True)

    def _configure_interface_ip(self, dut: str, interface: str, ip_addr: str) -> None:
        """Configure IP address on interface using klish CLI."""
        st.log(f"Configuring {ip_addr} on {interface} at {dut}")

        # First remove the IP from all interfaces to prevent conflicts
        self._remove_ip_from_all_interfaces(dut, ip_addr)

        # Now configure the IP on the target interface
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no shutdown",  # Ensure interface is up (as per manual config)
            f"ip address {ip_addr}",
            "exit",
            "exit",
        ]
        st.config(dut, commands, type="klish")

    def _configure_loopback(self, dut: str, loopback: str, ip_addr: str) -> None:
        """Configure loopback interface with IP address using klish CLI."""
        st.log(f"Configuring loopback {loopback} with {ip_addr} on {dut}")

        commands = [
            "configure terminal",
            f"interface {loopback}",
            f"ip address {ip_addr}",
            "no shutdown",  # Enable the loopback interface so connected route becomes active
            "exit",
            "exit",
        ]
        st.config(dut, commands, type="klish")

    def _configure_bgp_router(
        self,
        dut: str,
        local_as: int,
        router_id: str
    ) -> None:
        """Configure BGP router with AS and router-id using BGP API."""
        st.log(f"Configuring BGP router on {dut}: AS {local_as}, Router-ID {router_id}")

        # Create BGP router with router-id
        bgp_api.create_bgp_router(dut, local_as, router_id=router_id, cli_type=self.data.cli_type)

        # Try to disable eBGP policy requirement (command may not exist in all SONiC versions)
        # If it fails, we'll rely on explicit export route-maps for eBGP advertisement
        st.log(f"Attempting to disable 'bgp ebgp-requires-policy' on {dut}")
        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            "no bgp ebgp-requires-policy",
            "exit",
            "exit",
        ]
        st.config(dut, commands, type="klish", skip_error_check=True)

    def _configure_bgp_neighbor(
        self,
        dut: str,
        local_as: int,
        neighbor_ip: str,
        remote_as: int
    ) -> None:
        """
        Configure BGP neighbor using direct klish commands.

        NOTE: Using direct klish commands instead of bgp_api.create_bgp_neighbor()
        because the API generates invalid commands like 'router-id bgp {AS}' in klish mode.

        Follows manual config pattern - neighbor command enters neighbor context,
        then address-family enters neighbor-specific AF context where activate
        is applied WITHOUT repeating neighbor IP.

        Correct pattern:
          router bgp {AS}
            neighbor X.X.X.X remote-as Y     → enters neighbor context
            address-family ipv4 unicast      → enters neighbor-specific AF context
              activate                       → applies to this neighbor (no IP needed)
        """
        st.log(f"Configuring BGP neighbor {neighbor_ip} (AS {remote_as}) on {dut}")

        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            f"neighbor {neighbor_ip} remote-as {remote_as}",  # enters neighbor context
            "address-family ipv4 unicast",  # enters neighbor-specific AF context
            "activate",  # applies to this neighbor
            "exit",  # exit address-family
            "exit",  # exit neighbor
            "exit",  # exit router bgp
            "exit",  # exit configure terminal
        ]
        st.config(dut, commands, type="klish")

    def _configure_static_route(self, dut: str, network: str, nexthop: str = "Null0") -> None:
        """
        Configure static route using standard routing API.

        Uses ip_api.create_static_route() which properly handles different CLI types
        and ensures routes are correctly installed in FRR's routing table.
        """
        st.log(f"Configuring static route {network} via {nexthop} on {dut}")

        # Normalize nexthop - Null0 becomes blackhole for the API
        if nexthop.lower() in ["null0", "null"]:
            nexthop = "blackhole"

        # Use standard routing API which handles CLI type selection and FRR sync
        result = ip_api.create_static_route(
            dut,
            next_hop=nexthop,
            static_ip=network,
            family='ipv4'
        )

        if not result:
            st.error(f"Failed to configure static route {network} via {nexthop} on {dut}")
        else:
            st.log(f"Successfully configured static route {network} via {nexthop} on {dut}")

    def _configure_bgp_network(self, dut: str, local_as: int, network: str, route_map: str = "") -> None:
        """
        Advertise network in BGP using explicit network statement.

        NOTE: Using 'network' statement with static blackhole routes because:
        - Loopback IPs with /24 only create /32 host routes, not the full subnet
        - Static routes ARE in the RIB, so they pass BGP import-check
        - Network statement with existing RIB entry works reliably
        """
        st.log(f"Advertising network {network} in BGP on {dut} via network statement")

        # Use direct klish commands for network statement as the BGP API has issues with klish + route-maps
        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            "address-family ipv4 unicast",
        ]

        # Add the network statement
        commands.append(f"network {network}")

        commands.extend([
            "exit",  # exit address-family
            "exit",  # exit router bgp
            "exit",  # exit configure terminal
        ])

        st.config(dut, commands, type="klish")

    def _configure_bgp_redistribute_static(self, dut: str, local_as: int, route_map: str = "") -> None:
        """
        Redistribute static routes in BGP using direct klish commands.

        NOTE: Using direct klish commands instead of BGP API because:
        - The API's config_address_family_redistribute() has a bug in klish mode
        - It sends malformed "router-id bgp <AS>" command causing syntax errors
        - Direct commands ensure proper redistribute static configuration
        """
        st.log(f"Redistributing static routes in BGP on {dut}")

        # Use direct klish commands to configure redistribute static
        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            "address-family ipv4 unicast",
        ]

        # Add redistribute static with optional route-map
        if route_map:
            commands.append(f"redistribute static route-map {route_map}")
        else:
            commands.append("redistribute static")

        commands.extend([
            "exit",  # exit address-family
            "exit",  # exit router bgp
            "exit",  # exit configure terminal
        ])

        st.config(dut, commands, type="klish")
        st.log(f"Successfully configured BGP redistribute static on {dut}")

    def _configure_bgp_redistribute_connected(self, dut: str, local_as: int, route_map: str = "") -> None:
        """
        Redistribute connected routes in BGP using direct klish commands.

        NOTE: Using 'redistribute connected' instead of 'redistribute static' because
        on SONiC (FRR 10.x), static/blackhole routes are NOT exported to eBGP peers
        due to internal policy enforcement. Connected routes work reliably for eBGP.
        """
        st.log(f"Redistributing connected routes in BGP on {dut}")

        # Use direct klish commands to configure redistribute connected
        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            "address-family ipv4 unicast",
        ]

        # Add redistribute connected with optional route-map
        if route_map:
            commands.append(f"redistribute connected route-map {route_map}")
        else:
            commands.append("redistribute connected")

        commands.extend([
            "exit",  # exit address-family
            "exit",  # exit router bgp
            "exit",  # exit configure terminal
        ])

        st.config(dut, commands, type="klish")
        st.log(f"Successfully configured BGP redistribute connected on {dut}")

    def _reapply_bgp_redistribute_connected(self, dut: str, local_as: int, route_map: str = "") -> None:
        """
        Re-apply BGP redistribute connected configuration (remove and re-add).

        CRITICAL: This is required when redistribution is configured BEFORE neighbor
        address-family activation. Re-applying redistribution ensures routes are
        properly advertised to neighbors.

        This follows the correct configuration sequence:
        1. Configure neighbor with address-family activation
        2. Re-apply redistribution (no redistribute connected + redistribute connected route-map)
        """
        st.log(f"Re-applying BGP redistribute connected on {dut} to ensure route advertisement")

        # Step 1: Remove existing redistribution
        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            "address-family ipv4 unicast",
            "no redistribute connected",
            "exit",
            "end",  # Use 'end' to commit configuration and exit to privileged EXEC
        ]
        st.config(dut, commands, type="klish")

        # Step 2: Re-apply redistribution with route-map
        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            "address-family ipv4 unicast",
        ]

        if route_map:
            commands.append(f"redistribute connected route-map {route_map}")
        else:
            commands.append("redistribute connected")

        commands.extend([
            "exit",  # exit address-family
            "end",   # Use 'end' to commit configuration and exit to privileged EXEC
        ])

        st.config(dut, commands, type="klish")
        st.log(f"Successfully re-applied BGP redistribute connected on {dut}")

    def _reapply_bgp_redistribute_static(self, dut: str, local_as: int, route_map: str = "") -> None:
        """
        Re-apply BGP redistribute static configuration (remove and re-add).

        CRITICAL: This is required when redistribution is configured BEFORE neighbor
        address-family activation. Re-applying redistribution ensures routes are
        properly advertised to neighbors.

        This follows the correct configuration sequence:
        1. Configure neighbor with address-family activation
        2. Re-apply redistribution (no redistribute static + redistribute static route-map)
        """
        st.log(f"Re-applying BGP redistribute static on {dut} to ensure route advertisement")

        # Step 1: Remove existing redistribution
        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            "address-family ipv4 unicast",
            "no redistribute static",
            "exit",
            "end",  # Use 'end' to commit configuration and exit to privileged EXEC
        ]
        st.config(dut, commands, type="klish")

        # Step 2: Re-apply redistribution with route-map
        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            "address-family ipv4 unicast",
        ]

        if route_map:
            commands.append(f"redistribute static route-map {route_map}")
        else:
            commands.append("redistribute static")

        commands.extend([
            "exit",  # exit address-family
            "end",   # Use 'end' to commit configuration and exit to privileged EXEC
        ])

        st.config(dut, commands, type="klish")
        st.log(f"Successfully re-applied BGP redistribute static on {dut}")

    def _configure_bgp_network_advertise(
        self,
        dut: str,
        local_as: int,
        network: str,
        route_map: str = "",
        disable_import_check: bool = True
    ) -> None:
        """
        Advertise a network in BGP using explicit network statement.

        Args:
            dut: Device under test
            local_as: Local BGP AS number
            network: Network to advertise (e.g., "10.2.0.0/24")
            route_map: Optional route-map to apply (for outbound direction)
            disable_import_check: Disable BGP network import-check (default: True)

        NOTE: Using explicit 'network' statement instead of redistribution.
        The network must exist in the routing table for BGP to advertise it.
        With disable_import_check=True, BGP will advertise the network even if
        it's a blackhole route or not in the IGP routing table.
        """
        st.log(f"Advertising network {network} in BGP on {dut}")

        # Use direct klish commands for network advertisement
        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            "address-family ipv4 unicast",
        ]

        # Add the network statement
        # Note: "no bgp network import-check" is not supported in some SONiC versions
        # Static blackhole routes are already in RIB, so they should be advertised without it
        commands.append(f"network {network}")

        commands.extend([
            "exit",  # exit address-family
            "exit",  # exit router bgp
            "exit",  # exit configure terminal
        ])

        st.config(dut, commands, type="klish")

        # Apply route-map to neighbor if specified (for outbound)
        # Note: Route-map needs to be applied at neighbor level for network statements
        if route_map:
            st.log(f"Note: Route-map {route_map} should be applied at neighbor level for network statements")

    def _configure_route_map_set_med(
        self,
        dut: str,
        route_map_name: str,
        med_value: int
    ) -> None:
        """Configure route-map to set MED attribute using RouteMap API."""
        st.log(f"Configuring route-map {route_map_name} to set MED {med_value} on {dut}")

        rmap = RouteMap(route_map_name)
        rmap.add_permit_sequence('10')
        rmap.add_sequence_set_metric('10', str(med_value))
        rmap.execute_command(dut, config='yes', cli_type=self.data.cli_type)

    def _configure_simple_permit_route_map(self, dut: str, route_map_name: str) -> None:
        """
        Configure simple permit route-map for route advertisement.

        Creates a route-map with a single permit statement to allow route advertisement
        without any attribute manipulation. Useful for eBGP export policies where routes
        need explicit permission to be advertised.
        """
        st.log(f"Configuring simple permit route-map {route_map_name} on {dut}")

        rmap = RouteMap(route_map_name)
        rmap.add_permit_sequence('10')
        rmap.execute_command(dut, config='yes', cli_type=self.data.cli_type)

    def _configure_route_map_prepend_as(
        self,
        dut: str,
        route_map_name: str,
        as_numbers: List[int]
    ) -> None:
        """
        Configure route-map to prepend AS-PATH using direct klish commands.

        NOTE: Using direct klish commands instead of RouteMap API because:
        - The API generates syntax errors like 'set as-path prepend 65004 65005'
        - Correct klish syntax requires comma separation or repeated 'set as-path prepend' statements
        - Direct commands ensure proper AS-PATH prepending configuration
        """
        as_list = ','.join([str(asn) for asn in as_numbers])
        st.log(f"Configuring route-map {route_map_name} to prepend AS-PATH {as_list} on {dut}")

        # Use direct klish commands to avoid API syntax errors
        commands = [
            "configure terminal",
            f"route-map {route_map_name} permit 10",
            f"set as-path prepend {as_list}",
            "exit",  # exit route-map
            "exit",  # exit configure terminal
        ]
        st.config(dut, commands, type="klish")

    def _apply_route_map_to_neighbor(
        self,
        dut: str,
        local_as: int,
        neighbor_ip: str,
        remote_as: int,
        route_map_name: str,
        direction: str = "out"
    ) -> None:
        """
        Apply route-map to BGP neighbor using direct klish commands.

        NOTE: Using direct klish commands instead of BGP API because:
        - The API's config_bgp_neighbor_properties() doesn't properly apply route-maps in klish mode
        - It enters address-family mode but doesn't execute the neighbor route-map command
        - Direct commands ensure proper route-map application to neighbors
        """
        st.log(f"Applying route-map {route_map_name} to neighbor {neighbor_ip} ({direction}) on {dut}")

        # Use direct klish commands to apply route-map to neighbor
        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            "address-family ipv4 unicast",
            f"neighbor {neighbor_ip} route-map {route_map_name} {direction}",
            "exit",  # exit address-family
            "exit",  # exit router bgp
            "exit",  # exit configure terminal
        ]
        st.config(dut, commands, type="klish")

    def _configure_bgp_neighbor_with_weight(
        self,
        dut: str,
        local_as: int,
        neighbor_ip: str,
        remote_as: int,
        weight: int
    ) -> None:
        """
        Configure BGP neighbor with weight using direct klish commands.

        Follows manual config pattern - neighbor command enters neighbor context,
        then address-family enters neighbor-specific AF context where activate/weight
        are applied WITHOUT repeating neighbor IP.

        Correct pattern:
          router bgp {AS}
            neighbor X.X.X.X remote-as Y     → enters neighbor context
            address-family ipv4 unicast      → enters neighbor-specific AF context
              activate                       → applies to this neighbor (no IP needed)
              weight Z                       → applies to this neighbor (no IP needed)
        """
        st.log(f"Configuring BGP neighbor {neighbor_ip} (AS {remote_as}) with weight {weight} on {dut}")

        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            f"neighbor {neighbor_ip} remote-as {remote_as}",  # enters neighbor context
            "address-family ipv4 unicast",  # enters neighbor-specific AF context
            "activate",  # applies to this neighbor
            f"weight {weight}",  # applies to this neighbor
            "exit",  # exit address-family
            "exit",  # exit neighbor
            "exit",  # exit router bgp
            "exit",  # exit configure terminal
        ]
        st.config(dut, commands, type="klish")

    def _configure_neighbor_weight(
        self,
        dut: str,
        local_as: int,
        neighbor_ip: str,
        weight: int
    ) -> None:
        """
        Configure weight for BGP neighbor using direct klish commands.

        NOTE: Using direct klish commands instead of bgp_api.config_bgp_neighbor_properties()
        because the API generates invalid commands like 'router-id bgp {AS}' in klish mode.
        """
        st.log(f"Configuring weight {weight} for neighbor {neighbor_ip} on {dut}")

        # Use direct klish commands to avoid API bugs
        commands = [
            "configure terminal",
            f"router bgp {local_as}",
            "address-family ipv4 unicast",
            f"neighbor {neighbor_ip} weight {weight}",
            "exit",  # exit address-family
            "exit",  # exit router bgp
            "exit",  # exit configure terminal
        ]
        st.config(dut, commands, type="klish")

    def _verify_bgp_session_established(self, dut: str, neighbor_ip: str) -> bool:
        """
        Verify BGP session is established with neighbor.

        Parse raw CLI output directly instead of relying on template parsing.
        """
        st.log(f"Verifying BGP session established on {dut} with neighbor {neighbor_ip}")

        # Ensure we're in user mode before running show commands
        # Exit from any config modes (klish may leave us in config mode)
        st.config(dut, "end", type="klish", skip_error_check=True)

        # Try click CLI first - parse raw output
        try:
            cmd = "show ip bgp summary"
            output = st.show(dut, cmd, type="click", skip_tmpl=True)

            if isinstance(output, str):
                for line in output.splitlines():
                    stripped_line = line.strip()
                    if stripped_line.startswith(neighbor_ip):
                        if "Established" in line or "Estab" in line:
                            st.log(f"BGP session established with {neighbor_ip} (click CLI)")
                            return True
                        # Parse State/PfxRcd column
                        fields = stripped_line.split()
                        if len(fields) >= 10:
                            state_pfxrcd = fields[-2]
                            if re.match(r'^\d+$', state_pfxrcd):
                                st.log(f"BGP session established with {neighbor_ip} (State/PfxRcd={state_pfxrcd})")
                                return True
        except Exception as e:
            st.log(f"Click CLI check failed: {e}, trying klish")

        # Try klish CLI - parse raw output
        try:
            cmd = "show bgp ipv4 unicast summary"
            output = st.show(dut, cmd, type="klish", skip_tmpl=True)

            if isinstance(output, str):
                for line in output.splitlines():
                    stripped_line = line.strip()
                    if stripped_line.startswith(neighbor_ip):
                        if "Established" in line or "Estab" in line:
                            st.log(f"BGP session established with {neighbor_ip} (klish CLI)")
                            return True
                        fields = stripped_line.split()
                        if len(fields) >= 10:
                            state_pfxrcd = fields[-2]
                            if re.match(r'^\d+$', state_pfxrcd):
                                st.log(f"BGP session established with {neighbor_ip} (State/PfxRcd={state_pfxrcd})")
                                return True
        except Exception as e:
            st.log(f"Klish CLI check also failed: {e}")

        st.log(f"BGP session NOT established with {neighbor_ip}")
        return False

    def _verify_bgp_route(
        self,
        dut: str,
        prefix: str,
        should_exist: bool = True
    ) -> bool:
        """Verify BGP route exists or doesn't exist in BGP table."""
        st.log(f"Verifying BGP route {prefix} on {dut} (should_exist={should_exist})")

        # Ensure we're in user mode before running show commands
        st.config(dut, "end", type="klish", skip_error_check=True)

        # Use click CLI for reliable route verification (same as BGP-34)
        cmd = f"show ip bgp network {prefix}"

        try:
            st.log(f"DEBUG: Executing command: {cmd} on {dut}")
            output = st.show(dut, cmd, type="click", skip_tmpl=True)
            st.log(f"DEBUG: Command output length: {len(str(output))} characters")
            st.log(f"DEBUG: Output preview: {str(output)[:500]}")

            # Check for BGP routing table entry (same as BGP-34)
            route_exists = "BGP routing table entry" in str(output)
            st.log(f"DEBUG: Route {prefix} exists in BGP table: {route_exists}")

            if should_exist:
                if route_exists:
                    st.log(f"BGP route {prefix} found on {dut}")
                    return True
            else:
                if not route_exists:
                    st.log(f"BGP route {prefix} correctly absent on {dut}")
                    return True
        except Exception as e:
            st.log(f"ERROR: BGP route verification failed: {e}")
            st.log(f"ERROR: Exception type: {type(e).__name__}")

        if should_exist:
            st.log(f"BGP route {prefix} NOT found on {dut}")
        else:
            st.log(f"BGP route {prefix} should be absent but was found on {dut}")
        return False

    def _verify_bgp_route_med(
        self,
        dut: str,
        prefix: str,
        expected_med: int
    ) -> bool:
        """Verify BGP route has expected MED value."""
        st.log(f"Verifying BGP route {prefix} has MED {expected_med} on {dut}")

        # Ensure we're in user mode before running show commands
        st.config(dut, "end", type="klish", skip_error_check=True)

        cmd = f"show ip bgp network {prefix}"

        try:
            st.log(f"DEBUG: Executing command: {cmd} on {dut}")
            output = st.show(dut, cmd, type="click", skip_tmpl=True)
            st.log(f"DEBUG: MED check output: {str(output)[:500]}")

            if isinstance(output, str):
                # Look for MED/Metric in output
                # Example: "Metric: 50" or "MED: 50"
                med_match = re.search(r'(?:Metric|MED)[:\s]+(\d+)', output, re.IGNORECASE)
                if med_match:
                    med_value = int(med_match.group(1))
                    st.log(f"DEBUG: Found MED value: {med_value}")
                    if med_value == expected_med:
                        st.log(f"BGP route {prefix} has correct MED {expected_med}")
                        return True
                    else:
                        st.log(f"BGP route {prefix} has MED {med_value}, expected {expected_med}")
                        return False
                else:
                    st.log(f"DEBUG: No MED value found in output")
        except Exception as e:
            st.log(f"ERROR: MED verification failed: {e}")

        st.log(f"Could not verify MED for route {prefix}")
        return False

    def _verify_bgp_best_path_via_neighbor(
        self,
        dut: str,
        prefix: str,
        neighbor_ip: str
    ) -> bool:
        """Verify BGP best path is via specified neighbor."""
        st.log(f"Verifying BGP best path for {prefix} is via {neighbor_ip} on {dut}")

        # Ensure we're in user mode before running show commands
        st.config(dut, "end", type="klish", skip_error_check=True)

        cmd = f"show ip bgp network {prefix}"

        try:
            st.log(f"DEBUG: Executing command: {cmd} on {dut}")
            output = st.show(dut, cmd, type="click", skip_tmpl=True)
            st.log(f"DEBUG: Best path check output: {str(output)[:1000]}")

            if isinstance(output, str):
                lines = output.splitlines()

                # FRRouting format: Look for the neighbor IP followed by "best" keyword in subsequent lines
                # Example:
                #   10.10.2.2 from 10.10.2.2 (3.3.3.3)
                #     Origin incomplete, metric 50, localpref 100, valid, internal, best (MED)
                for i, line in enumerate(lines):
                    st.log(f"DEBUG: Checking line {i}: {line[:100]}")
                    # Check if this line contains the neighbor IP (format: "    10.10.2.2 from 10.10.2.2")
                    if neighbor_ip in line and "from" in line:
                        st.log(f"DEBUG: Found neighbor {neighbor_ip} on line {i}")
                        # Look ahead in the next few lines for "best" keyword
                        for j in range(i+1, min(i+5, len(lines))):
                            st.log(f"DEBUG: Checking next line {j}: {lines[j][:100]}")
                            # Match patterns like: "best (MED)", "best (Weight)", "valid, external, best"
                            if re.search(r'\bbest\b', lines[j], re.IGNORECASE):
                                st.log(f"Found 'best' keyword on line {j} for neighbor {neighbor_ip}")
                                st.log(f"Best path for {prefix} is via {neighbor_ip}")
                                return True
                        st.log(f"DEBUG: Found neighbor {neighbor_ip} but no 'best' keyword in following lines")

                # Also check for older format with ">" marker
                for line in lines:
                    if ">" in line and neighbor_ip in line:
                        st.log(f"Best path for {prefix} is via {neighbor_ip} (found > marker)")
                        return True

                st.log(f"DEBUG: No best path indicator found for neighbor '{neighbor_ip}'")
        except Exception as e:
            st.log(f"ERROR: Best path verification failed: {e}")

        st.log(f"Best path for {prefix} is NOT via {neighbor_ip}")
        return False

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    def _debug_verify_static_route_in_rib(self, dut: str, prefix: str) -> None:
        """Debug: Verify static route exists in routing table (RIB)."""
        st.log(f"DEBUG: Checking if static route {prefix} exists in RIB on {dut}")
        st.config(dut, "end", type="klish", skip_error_check=True)

        output = st.show(dut, "show ip route", type="click", skip_tmpl=True)
        st.log(f"DEBUG: 'show ip route' output on {dut}:")
        st.log(f"{output}")

        if prefix in str(output):
            st.log(f"✅ DEBUG: Static route {prefix} FOUND in RIB on {dut}")
        else:
            st.log(f"❌ DEBUG: Static route {prefix} NOT FOUND in RIB on {dut}")

    def _debug_verify_route_in_bgp_table(self, dut: str, prefix: str) -> None:
        """Debug: Verify route exists in BGP table."""
        st.log(f"DEBUG: Checking if route {prefix} exists in BGP table on {dut}")
        st.config(dut, "end", type="klish", skip_error_check=True)

        cmd = f"show ip bgp network {prefix}"
        output = st.show(dut, cmd, type="click", skip_tmpl=True)
        st.log(f"DEBUG: '{cmd}' output on {dut}:")
        st.log(f"{output}")

        if "BGP routing table entry" in str(output):
            st.log(f"✅ DEBUG: Route {prefix} FOUND in BGP table on {dut}")
        else:
            st.log(f"❌ DEBUG: Route {prefix} NOT FOUND in BGP table on {dut}")

    def _debug_show_advertised_routes(self, dut: str, neighbor_ip: str) -> None:
        """Debug: Show routes being advertised to a neighbor."""
        st.log(f"DEBUG: Checking routes advertised from {dut} to neighbor {neighbor_ip}")
        st.config(dut, "end", type="klish", skip_error_check=True)

        cmd = f"show ip bgp neighbors {neighbor_ip} advertised-routes"
        output = st.show(dut, cmd, type="click", skip_tmpl=True)
        st.log(f"DEBUG: Advertised routes from {dut} to {neighbor_ip}:")
        st.log(f"{output}")

    def _debug_show_bgp_config(self, dut: str, local_as: int) -> None:
        """Debug: Show BGP running configuration."""
        st.log(f"DEBUG: Checking BGP configuration on {dut}")
        st.config(dut, "end", type="klish", skip_error_check=True)

        cmd = f"show running-config | grep -A 30 'router bgp {local_as}'"
        try:
            output = st.show(dut, cmd, type="click", skip_tmpl=True)
            st.log(f"DEBUG: BGP configuration on {dut}:")
            st.log(f"{output}")
        except:
            # Fallback to vtysh if click fails
            output = st.show(dut, "show running-config", type="vtysh", skip_tmpl=True)
            st.log(f"DEBUG: Full running config on {dut}:")
            st.log(f"{output}")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-34"])
    def test_bgp_med_propagation(self) -> None:
        """
        BGP-34: Verify MED Attribute Propagation

        Verify that BGP MED attribute is correctly propagated and influences
        path selection. Lower MED value should be preferred.
        """
        st.banner("TEST: BGP-34 - MED Attribute Propagation")

        # Ensure clean slate - remove any existing BGP config
        st.log("Pre-test cleanup: Removing any existing BGP configurations")
        self._cleanup_all_bgp()

        testcase = self._get_testcase("BGP-34")

        # Extract AS numbers (testcase-specific overrides or defaults)
        d1_as = testcase.get("d1_as", self.data.d1_as)
        d2_as = testcase.get("d2_as", self.data.d2_as)
        d3_as = testcase.get("d3_as", self.data.d3_as)

        st.log(f"BGP-34 AS Configuration: D1={d1_as}, D2={d2_as}, D3={d3_as}")

        # Extract test parameters
        test_network = testcase.get("test_network", "10.1.0.0/24")
        d1_loopback = testcase.get("d1_loopback", "Loopback10")
        d1_loopback_ip = testcase.get("d1_loopback_ip", "10.1.0.1/24")
        d3_loopback = testcase.get("d3_loopback", "Loopback10")
        d3_loopback_ip = testcase.get("d3_loopback_ip", "10.1.0.100/24")
        d1_med = testcase.get("d1_med", 100)
        d3_med = testcase.get("d3_med", 50)
        d1_route_map = testcase.get("d1_route_map", "SET_MED_100")
        d3_route_map = testcase.get("d3_route_map", "SET_MED_50")

        # Step 1: Configure interfaces
        st.log("Configuring interfaces on all DUTs")
        self._configure_interface_ip(self.data.dut1, self.data.d1d2_ports[0], self.data.d1d2_ipv4)
        self._configure_interface_ip(self.data.dut2, self.data.d2d1_ports[0], self.data.d2d1_ipv4)
        self._configure_interface_ip(self.data.dut2, self.data.d2d3_ports[0], self.data.d2d3_ipv4)
        self._configure_interface_ip(self.data.dut3, self.data.d3d2_ports[0], self.data.d3d2_ipv4)

        # Step 2: Configure static blackhole routes for the test network
        # Reason: Loopback IPs with /24 only create /32 host routes, not the full subnet
        # Static blackhole routes ARE in the RIB, so BGP network statement will work
        st.log(f"Configuring static blackhole routes for {test_network} on D1 and D3")
        self._configure_static_route(self.data.dut1, test_network, "Null0")
        self._configure_static_route(self.data.dut3, test_network, "Null0")
        st.log(f"Static blackhole routes configured - {test_network} is now in RIB")

        # Step 3: Configure route-maps with MED
        st.log("Configuring route-maps to set MED values")
        self._configure_route_map_set_med(self.data.dut1, d1_route_map, d1_med)
        self._configure_route_map_set_med(self.data.dut3, d3_route_map, d3_med)

        # Step 4: Configure BGP routers (create BGP instance with AS and router-id)
        st.log("Configuring BGP routers on all DUTs")
        self._configure_bgp_router(self.data.dut1, d1_as, self.data.d1_router_id)
        self._configure_bgp_router(self.data.dut2, d2_as, self.data.d2_router_id)
        self._configure_bgp_router(self.data.dut3, d3_as, self.data.d3_router_id)

        # Step 5: Configure BGP neighbors
        st.log("Configuring BGP neighbors")
        self._configure_bgp_neighbor(self.data.dut1, d1_as, self.data.d1_neighbor_ipv4, d2_as)
        self._configure_bgp_neighbor(self.data.dut2, d2_as, self.data.d2_d1_neighbor_ipv4, d1_as)
        self._configure_bgp_neighbor(self.data.dut2, d2_as, self.data.d2_d3_neighbor_ipv4, d3_as)
        self._configure_bgp_neighbor(self.data.dut3, d3_as, self.data.d3_neighbor_ipv4, d2_as)

        # Step 6: Advertise the test network via BGP network statement
        # The static blackhole routes (created in Step 2) are in the RIB, so network statement will work
        st.log(f"Advertising network {test_network} in BGP via network statement")
        self._configure_bgp_network(self.data.dut1, d1_as, test_network)
        self._configure_bgp_network(self.data.dut3, d3_as, test_network)

        # Step 6.5: Apply MED route-maps to neighbors (outbound) on D1 and D3
        st.log(f"Applying MED route-maps to neighbors on D1 (MED={d1_med}) and D3 (MED={d3_med})")
        self._apply_route_map_to_neighbor(
            self.data.dut1, d1_as,
            self.data.d1_neighbor_ipv4, d2_as,
            d1_route_map, direction="out"
        )
        self._apply_route_map_to_neighbor(
            self.data.dut3, d3_as,
            self.data.d3_neighbor_ipv4, d2_as,
            d3_route_map, direction="out"
        )

        # Step 7: Wait for BGP sessions to establish
        st.log("Waiting for BGP sessions to establish")
        st.wait(30)

        # Step 8: Verify BGP sessions
        st.log("Verifying BGP sessions are established")
        if not self._verify_bgp_session_established(self.data.dut2, self.data.d2_d1_neighbor_ipv4):
            st.report_fail("msg", "BGP session not established between D2 and D1")

        if not self._verify_bgp_session_established(self.data.dut2, self.data.d2_d3_neighbor_ipv4):
            st.report_fail("msg", "BGP session not established between D2 and D3")

        # Step 9: Verify route exists on D2
        st.log(f"Verifying route {test_network} exists on D2")
        if not st.poll_wait(
            lambda: self._verify_bgp_route(self.data.dut2, test_network),
            self.data.verify_timeout,
        ):
            st.report_fail("msg", f"Route {test_network} not found on D2")

        # Step 10: Verify best path is via D3 (lower MED)
        st.log(f"Verifying best path for {test_network} is via D3 (MED={d3_med})")
        if not st.poll_wait(
            lambda: self._verify_bgp_best_path_via_neighbor(
                self.data.dut2, test_network, self.data.d2_d3_neighbor_ipv4
            ),
            self.data.verify_timeout,
        ):
            st.report_fail("msg", f"Best path for {test_network} is not via D3 (lower MED)")

        st.log("Successfully verified MED attribute propagation and path selection")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-35"])
    def test_bgp_weight_priority(self) -> None:
        """
        BGP-35: Verify Weight Attribute Priority in Inbound Selection (iBGP)

        Verify that weight attribute takes highest priority in BGP path selection.

        NOTE: This test uses iBGP topology due to SONiC FRR 10.x limitation where
        eBGP export policy prevents advertisement of non-interface-connected routes.
        Weight is a local-only attribute, so iBGP is appropriate for this test.

        Topology: D1 (AS 65001) — iBGP — D2 (AS 65001) — iBGP — D3 (AS 65001)
        """
        st.banner("TEST: BGP-35 - Weight Attribute Priority (iBGP)")

        # Ensure clean slate - remove any existing BGP config from previous test
        st.log("Pre-test cleanup: Removing any existing BGP configurations")
        self._cleanup_all_bgp()

        testcase = self._get_testcase("BGP-35")

        # Extract AS numbers (testcase-specific overrides or defaults)
        d1_as = testcase.get("d1_as", self.data.d1_as)
        d2_as = testcase.get("d2_as", self.data.d2_as)
        d3_as = testcase.get("d3_as", self.data.d3_as)

        st.log(f"BGP-35 AS Configuration: D1={d1_as}, D2={d2_as}, D3={d3_as}")

        # Extract test parameters
        test_network = testcase.get("test_network", "10.2.0.0/24")
        d1_loopback = testcase.get("d1_loopback", "Loopback20")
        d1_loopback_ip = testcase.get("d1_loopback_ip", "10.2.0.1/32")  # Changed from /24 to /32
        d3_loopback = testcase.get("d3_loopback", "Loopback20")
        d3_loopback_ip = testcase.get("d3_loopback_ip", "10.2.0.100/32")  # Changed from /24 to /32
        d1_weight = testcase.get("d1_weight", 100)
        d3_weight = testcase.get("d3_weight", 200)

        # Step 1: Configure interfaces
        st.log("Configuring interfaces on all DUTs")
        self._configure_interface_ip(self.data.dut1, self.data.d1d2_ports[0], self.data.d1d2_ipv4)
        self._configure_interface_ip(self.data.dut2, self.data.d2d1_ports[0], self.data.d2d1_ipv4)
        self._configure_interface_ip(self.data.dut2, self.data.d2d3_ports[0], self.data.d2d3_ipv4)
        self._configure_interface_ip(self.data.dut3, self.data.d3d2_ports[0], self.data.d3d2_ipv4)

        # Step 1.5: Clean up any old static routes from previous tests
        # CRITICAL: Old static routes can interfere with connected route advertisement
        st.log(f"Cleaning up any old static routes for {test_network} on D1 and D3")
        self._remove_static_route(self.data.dut1, test_network, "Null0")
        self._remove_static_route(self.data.dut3, test_network, "Null0")
        st.log(f"Old static routes cleaned up")

        # Step 2: Configure loopback interfaces with /32 addresses
        # CRITICAL: SONiC loopback interfaces ONLY accept /32 IPv4 addresses.
        # We use /32 loopback IPs and then advertise the aggregate /24 network via BGP network statement.
        st.log(f"Configuring loopback interfaces with /32 addresses on D1 and D3")
        self._configure_loopback(self.data.dut1, d1_loopback, d1_loopback_ip)
        self._configure_loopback(self.data.dut3, d3_loopback, d3_loopback_ip)
        st.log(f"Loopback interfaces configured with /32 addresses")

        # Step 2.5: Add static blackhole route for the /24 network
        # CRITICAL: BGP "network" command requires a matching route in the routing table!
        # Since loopbacks are /32, we need to create a /24 route for BGP to advertise.
        st.log(f"Adding static blackhole route for {test_network} on D1 and D3")
        self._configure_static_route(self.data.dut1, test_network, "Null0")
        self._configure_static_route(self.data.dut3, test_network, "Null0")
        st.log(f"Static blackhole routes configured")

        # Step 3: Configure BGP routers (create BGP instance with AS and router-id)
        st.log("Configuring BGP routers on all DUTs")
        self._configure_bgp_router(self.data.dut1, d1_as, self.data.d1_router_id)
        self._configure_bgp_router(self.data.dut2, d2_as, self.data.d2_router_id)
        self._configure_bgp_router(self.data.dut3, d3_as, self.data.d3_router_id)

        # Step 4: Configure BGP neighbors
        # D1 and D3 configure neighbors without weights
        st.log("Configuring BGP neighbors on D1 and D3")
        self._configure_bgp_neighbor(self.data.dut1, d1_as, self.data.d1_neighbor_ipv4, d2_as)
        self._configure_bgp_neighbor(self.data.dut3, d3_as, self.data.d3_neighbor_ipv4, d2_as)

        # Step 5: Configure BGP neighbors WITH weights on D2
        # Following manual config pattern: neighbor + address-family + activate + weight
        st.log("Configuring BGP neighbors with weights on D2")
        self._configure_bgp_neighbor_with_weight(
            self.data.dut2, d2_as,
            self.data.d2_d1_neighbor_ipv4, d1_as, d1_weight
        )
        self._configure_bgp_neighbor_with_weight(
            self.data.dut2, d2_as,
            self.data.d2_d3_neighbor_ipv4, d3_as, d3_weight
        )

        # Step 6: Advertise the /24 network in BGP using network statement
        # Since loopbacks are configured with /32, we need explicit network statements
        # to advertise the aggregate /24 network that the test expects.
        st.log(f"Advertising {test_network} in BGP via network statement on D1 and D3")
        self._configure_bgp_network(self.data.dut1, d1_as, test_network)
        self._configure_bgp_network(self.data.dut3, d3_as, test_network)

        # Step 7: Wait for BGP convergence
        st.wait(10, "Waiting for BGP to converge and advertise routes")

        # Step 7.5: DEBUG - Verify configuration and routes
        st.log("=" * 80)
        st.log("DEBUG: Verifying static routes and BGP advertisement")
        st.log("=" * 80)

        # Verify static routes are in RIB
        self._debug_verify_static_route_in_rib(self.data.dut1, test_network)
        self._debug_verify_static_route_in_rib(self.data.dut3, test_network)

        # Verify routes are in BGP table
        self._debug_verify_route_in_bgp_table(self.data.dut1, test_network)
        self._debug_verify_route_in_bgp_table(self.data.dut3, test_network)

        # Show BGP configuration
        self._debug_show_bgp_config(self.data.dut1, d1_as)
        self._debug_show_bgp_config(self.data.dut3, d3_as)

        # Show advertised routes to neighbors
        self._debug_show_advertised_routes(self.data.dut1, self.data.d1_neighbor_ipv4)
        self._debug_show_advertised_routes(self.data.dut3, self.data.d3_neighbor_ipv4)

        st.log("=" * 80)

        # Step 8: Wait for BGP sessions to establish and routes to propagate
        st.log("Waiting for BGP sessions to establish and routes to propagate")
        st.wait(30)

        # Step 9: Verify BGP sessions
        st.log("Verifying BGP sessions are established")
        if not self._verify_bgp_session_established(self.data.dut2, self.data.d2_d1_neighbor_ipv4):
            st.report_fail("msg", "BGP session not established between D2 and D1")

        if not self._verify_bgp_session_established(self.data.dut2, self.data.d2_d3_neighbor_ipv4):
            st.report_fail("msg", "BGP session not established between D2 and D3")

        # Step 10: Verify route exists on D2
        st.log(f"Verifying route {test_network} exists on D2")
        if not st.poll_wait(
            lambda: self._verify_bgp_route(self.data.dut2, test_network),
            self.data.verify_timeout,
        ):
            st.report_fail("msg", f"Route {test_network} not found on D2")

        # Step 11: Verify best path is via D3 (higher weight)
        st.log(f"Verifying best path for {test_network} is via D3 (weight={d3_weight})")
        if not st.poll_wait(
            lambda: self._verify_bgp_best_path_via_neighbor(
                self.data.dut2, test_network, self.data.d2_d3_neighbor_ipv4
            ),
            self.data.verify_timeout,
        ):
            st.report_fail("msg", f"Best path for {test_network} is not via D3 (higher weight should be preferred)")

        st.log("Successfully verified weight attribute priority in path selection")
        st.report_pass("test_case_passed")
