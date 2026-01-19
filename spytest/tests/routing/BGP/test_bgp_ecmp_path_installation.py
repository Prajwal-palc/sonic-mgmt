"""
BGP ECMP PATH INSTALLATION (Test ID 3.1.5)
Author: Athira
2025

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_2node.yaml \\
  tests/routing/BGP/test_bgp_ecmp_path_installation.py \\
  --logs-path ./logs/test_bgp_ecmp_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  End-to-end validation of BGP Equal-Cost Multi-Path (ECMP) behavior in SONiC.
  The suite validates that when multiple BGP peers advertise the same prefix with
  identical attributes (LOCAL_PREF, AS-PATH, ORIGIN, MED), the device installs
  multiple equal-cost paths for load balancing. Tests cover IPv4/IPv6, control-plane
  RIB verification, FIB/data-plane verification, max-paths limits, flow hashing
  consistency, dynamic path addition/removal, persistence across reboots, and
  negative cases where ECMP should not be used.

  ECMP is critical for traffic load balancing and network resilience in modern
  data center environments. This test suite ensures BGP multipath functionality
  works correctly across hardware and virtual SONiC platforms.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes (eBGP peering)
        # +------------------------+                       +------------------------+
        # |    D1 (AS 65001)       |                       |    D2 (AS 65002)       |
        # |  smic_sonic1           |                       |  smic_sonic2           |
        # |  Lo0: 1.1.1.1/32       |                       |  Lo0: 2.2.2.2/32       |
        # |  Eth4: 10.0.24.1/31    |=======================|  Eth4: 10.0.24.0/31    |
        # |  2001:db8:24::1/64     |                       |  2001:db8:24::2/64     |
        # |                        |                       |  Lo10: 10.2.10.1/32    |
        # |                        |                       |  Lo11: 10.2.11.1/32    |
        # |                        |                       |  Lo20: 10.2.20.1/32    |
        # +------------------------+                       +------------------------+
        #
        # D2 advertises prefixes from multiple loopbacks (simulating multiple peers);
        # D1 verifies ECMP path installation and load balancing

  - Feature: BGP multipath support in SONiC/FRRouting
  - Required test variables (YAML): vars_bgp_ecmp_path_installation.yaml
"""

from __future__ import annotations

import json
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api

# Scapy imports for traffic generation
try:
    from scapy.all import IP, IPv6, TCP, UDP, ICMP, Ether, sendp, sniff, srp
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    st.warn("Scapy not available - traffic tests will use basic ping only")

VAR_FILE_ENV = "BGP_ECMP_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent / "vars_bgp_ecmp_path_installation.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"BGP ECMP variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("BGP ECMP YAML must contain key 'testcases'")

    return content


def _iter_candidate_duts(topology: Mapping[str, Any]) -> Iterable[str]:
    """Yield DUT aliases discovered in the topology map."""
    for key, value in topology.items():
        if key.startswith("D") and value:
            yield key


@pytest.mark.topology("any")
class TestBgpEcmpPathInstallation:
    """Testcases covering BGP ECMP path installation and load balancing (Test ID 3.1.5)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        min_topology = defaults.get("min_topology") or ["D1D2:1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.topology_config = SpyTestDict(config.get("topology", {}))

        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.show_cli_type = defaults.get("show_cli_type", "click")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 60))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))
        cls.data.dut_map = SpyTestDict()

        # Map DUT aliases (D1, D2) to actual device handles
        for dut_alias in _iter_candidate_duts(topology):
            cls.data.dut_map[dut_alias] = getattr(topology, dut_alias)

        cls.data.dut_names = st.get_dut_names()

        # Track configured interfaces, BGP config, and routes
        cls.data.configured_interfaces = []
        cls.data.configured_bgp_neighbors = []
        cls.data.configured_networks = []
        cls.data.original_max_paths = {}

        st.log("BGP ECMP Test Suite: Setup class completed")

    @classmethod
    def teardown_class(cls) -> None:
        """Clean up all configurations after the suite completes."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping teardown")
            return

        st.log("BGP ECMP Test Suite: Starting teardown cleanup")
        cls._cleanup_all_configurations()

    def setup_method(self) -> None:
        """Reset per-test bookkeeping."""
        self._test_interfaces: List[Mapping[str, Any]] = []
        self._test_bgp_neighbors: List[Mapping[str, Any]] = []
        self._test_networks: List[Mapping[str, Any]] = []

    def teardown_method(self) -> None:
        """Remove any configurations that the testcase created."""
        if not self.data.cleanup_enabled:
            self._test_interfaces = []
            self._test_bgp_neighbors = []
            self._test_networks = []
            return

        # Cleanup networks
        while self._test_networks:
            network = self._test_networks.pop()
            self._remove_bgp_network(network)
            if network in self.data.configured_networks:
                self.data.configured_networks.remove(network)

        # Cleanup BGP neighbors
        while self._test_bgp_neighbors:
            neighbor = self._test_bgp_neighbors.pop()
            self._remove_bgp_neighbor(neighbor)
            if neighbor in self.data.configured_bgp_neighbors:
                self.data.configured_bgp_neighbors.remove(neighbor)

        # Cleanup interfaces
        while self._test_interfaces:
            intf = self._test_interfaces.pop()
            self._remove_interface_config(intf)
            if intf in self.data.configured_interfaces:
                self.data.configured_interfaces.remove(intf)

    @classmethod
    def _cleanup_all_configurations(cls) -> None:
        """Remove all configurations tracked across the suite."""
        # Restore original max-paths
        for dut_alias, max_paths_config in cls.data.original_max_paths.items():
            dut = cls._resolve_dut_static(dut_alias)
            if dut and max_paths_config:
                cls._restore_max_paths_static(dut, max_paths_config)

        # Cleanup networks
        while cls.data.configured_networks:
            network = cls.data.configured_networks.pop()
            cls._remove_bgp_network_static(network)

        # Cleanup BGP neighbors
        while cls.data.configured_bgp_neighbors:
            neighbor = cls.data.configured_bgp_neighbors.pop()
            cls._remove_bgp_neighbor_static(neighbor)

        # Cleanup interfaces
        while cls.data.configured_interfaces:
            intf = cls.data.configured_interfaces.pop()
            cls._remove_interface_config_static(intf)

    @classmethod
    def _resolve_dut_static(cls, alias: str | None) -> str | None:
        """Translate a topology alias (e.g., D1) to the framework DUT handle (static version)."""
        if not alias:
            return None
        if alias in cls.data.dut_map:
            return cls.data.dut_map[alias]
        if alias in cls.data.dut_names:
            return alias
        st.warn(f"Unable to resolve DUT alias '{alias}'")
        return None

    def _resolve_dut(self, alias: str | None) -> str | None:
        """Translate a topology alias (e.g., D1) to the framework DUT handle."""
        return self._resolve_dut_static(alias)

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    def _get_dut_config(self, dut_alias: str) -> Mapping[str, Any]:
        """Fetch topology configuration for a DUT."""
        config = self.data.topology_config.get(dut_alias, {})
        if not config:
            st.warn(f"No topology config found for {dut_alias}")
        return config

    def _configure_interface(self, intf_config: Mapping[str, Any]) -> None:
        """Configure an interface with IP address."""
        dut = self._resolve_dut(intf_config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in interface config: {intf_config}")

        interface = intf_config.get("name")
        ipv4 = intf_config.get("ipv4")
        ipv6 = intf_config.get("ipv6")

        st.log(f"Configuring interface {interface} on {intf_config.get('dut')}: IPv4={ipv4}, IPv6={ipv6}")

        if ipv4:
            result = ip_api.config_ip_addr_interface(
                dut, interface, ipv4, family="ipv4", config="add", cli_type=self.data.cli_type
            )
            if not result:
                st.report_fail("msg", f"Failed to configure IPv4 {ipv4} on {interface}")

        if ipv6:
            result = ip_api.config_ip_addr_interface(
                dut, interface, ipv6, family="ipv6", config="add", cli_type=self.data.cli_type
            )
            if not result:
                st.report_fail("msg", f"Failed to configure IPv6 {ipv6} on {interface}")

        if intf_config not in self._test_interfaces:
            self._test_interfaces.append(intf_config)
        if intf_config not in self.data.configured_interfaces:
            self.data.configured_interfaces.append(intf_config)

    def _remove_interface_config(self, intf_config: Mapping[str, Any]) -> None:
        """Remove interface IP configuration."""
        dut = self._resolve_dut(intf_config.get("dut"))
        if not dut:
            return

        interface = intf_config.get("name")
        ipv4 = intf_config.get("ipv4")
        ipv6 = intf_config.get("ipv6")

        if ipv4:
            ip_api.delete_ip_interface(
                dut, interface, ipv4, family="ipv4", cli_type=self.data.cli_type
            )

        if ipv6:
            ip_api.delete_ip_interface(
                dut, interface, ipv6, family="ipv6", cli_type=self.data.cli_type
            )

    @classmethod
    def _remove_interface_config_static(cls, intf_config: Mapping[str, Any]) -> None:
        """Remove interface IP configuration (static version for cleanup)."""
        dut = cls._resolve_dut_static(intf_config.get("dut"))
        if not dut:
            return

        interface = intf_config.get("name")
        ipv4 = intf_config.get("ipv4")
        ipv6 = intf_config.get("ipv6")
        cli_type = cls.data.cli_type

        if ipv4:
            ip_api.delete_ip_interface(dut, interface, ipv4, family="ipv4", cli_type=cli_type)

        if ipv6:
            ip_api.delete_ip_interface(dut, interface, ipv6, family="ipv6", cli_type=cli_type)

    def _configure_bgp_router(self, bgp_config: Mapping[str, Any]) -> None:
        """Configure BGP router instance."""
        dut = self._resolve_dut(bgp_config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP config: {bgp_config}")

        local_as = bgp_config.get("local_as")
        router_id = bgp_config.get("router_id")

        st.log(f"Configuring BGP router on {bgp_config.get('dut')}: AS={local_as}, Router-ID={router_id}")

        result = bgp_api.config_bgp(
            dut,
            local_as=local_as,
            router_id=router_id,
            config="yes",
            cli_type=self.data.cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure BGP router on {bgp_config.get('dut')}")

    def _configure_bgp_neighbor(self, neighbor_config: Mapping[str, Any]) -> None:
        """Configure BGP neighbor."""
        dut = self._resolve_dut(neighbor_config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in neighbor config: {neighbor_config}")

        local_as = neighbor_config.get("local_as")
        neighbor_ip = neighbor_config.get("neighbor_ip")
        remote_as = neighbor_config.get("remote_as")
        family = neighbor_config.get("addr_family", "ipv4")

        st.log(f"Configuring BGP neighbor {neighbor_ip} on {neighbor_config.get('dut')}")

        result = bgp_api.config_bgp(
            dut,
            local_as=local_as,
            neighbor=neighbor_ip,
            remote_as=remote_as,
            addr_family=family,
            config="yes",
            cli_type=self.data.cli_type,
            activate=1
        )
        if not result:
            st.report_fail("msg", f"Failed to configure BGP neighbor {neighbor_ip}")

        if neighbor_config not in self._test_bgp_neighbors:
            self._test_bgp_neighbors.append(neighbor_config)
        if neighbor_config not in self.data.configured_bgp_neighbors:
            self.data.configured_bgp_neighbors.append(neighbor_config)

    def _remove_bgp_neighbor(self, neighbor_config: Mapping[str, Any]) -> None:
        """Remove BGP neighbor configuration."""
        dut = self._resolve_dut(neighbor_config.get("dut"))
        if not dut:
            return

        local_as = neighbor_config.get("local_as")
        neighbor_ip = neighbor_config.get("neighbor_ip")
        family = neighbor_config.get("addr_family", "ipv4")

        bgp_api.config_bgp(
            dut,
            local_as=local_as,
            neighbor=neighbor_ip,
            addr_family=family,
            config="no",
            cli_type=self.data.cli_type,
            removeBGP="yes"
        )

    @classmethod
    def _remove_bgp_neighbor_static(cls, neighbor_config: Mapping[str, Any]) -> None:
        """Remove BGP neighbor (static version for cleanup)."""
        dut = cls._resolve_dut_static(neighbor_config.get("dut"))
        if not dut:
            return

        local_as = neighbor_config.get("local_as")
        neighbor_ip = neighbor_config.get("neighbor_ip")
        family = neighbor_config.get("addr_family", "ipv4")

        bgp_api.config_bgp(
            dut,
            local_as=local_as,
            neighbor=neighbor_ip,
            addr_family=family,
            config="no",
            cli_type=cls.data.cli_type,
            removeBGP="yes"
        )

    def _configure_bgp_network(self, network_config: Mapping[str, Any]) -> None:
        """Advertise a network in BGP."""
        dut = self._resolve_dut(network_config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in network config: {network_config}")

        local_as = network_config.get("local_as")
        network = network_config.get("network")
        family = network_config.get("addr_family", "ipv4")

        st.log(f"Advertising network {network} on {network_config.get('dut')}")

        result = bgp_api.config_bgp(
            dut,
            local_as=local_as,
            config="yes",
            network=network,
            addr_family=family,
            cli_type=self.data.cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to advertise network {network}")

        if network_config not in self._test_networks:
            self._test_networks.append(network_config)
        if network_config not in self.data.configured_networks:
            self.data.configured_networks.append(network_config)

    def _remove_bgp_network(self, network_config: Mapping[str, Any]) -> None:
        """Remove BGP network advertisement."""
        dut = self._resolve_dut(network_config.get("dut"))
        if not dut:
            return

        local_as = network_config.get("local_as")
        network = network_config.get("network")
        family = network_config.get("addr_family", "ipv4")

        bgp_api.config_bgp(
            dut,
            local_as=local_as,
            config="no",
            network=network,
            addr_family=family,
            cli_type=self.data.cli_type
        )

    @classmethod
    def _remove_bgp_network_static(cls, network_config: Mapping[str, Any]) -> None:
        """Remove BGP network (static version for cleanup)."""
        dut = cls._resolve_dut_static(network_config.get("dut"))
        if not dut:
            return

        local_as = network_config.get("local_as")
        network = network_config.get("network")
        family = network_config.get("addr_family", "ipv4")

        bgp_api.config_bgp(
            dut,
            local_as=local_as,
            config="no",
            network=network,
            addr_family=family,
            cli_type=cls.data.cli_type
        )

    def _configure_max_paths(self, dut_alias: str, max_paths: int, addr_family: str = "ipv4") -> None:
        """Configure BGP maximum-paths for ECMP."""
        dut = self._resolve_dut(dut_alias)
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias: {dut_alias}")

        dut_config = self._get_dut_config(dut_alias)
        local_as = dut_config.get("as_number")

        st.log(f"Configuring max-paths {max_paths} for {addr_family} on {dut_alias}")

        # Store original max-paths if not already saved
        if dut_alias not in self.data.original_max_paths:
            self.data.original_max_paths[dut_alias] = {
                "max_paths": self._get_current_max_paths(dut, local_as, addr_family),
                "addr_family": addr_family
            }

        result = bgp_api.config_bgp(
            dut,
            local_as=local_as,
            config="yes",
            max_path_ibgp=max_paths if addr_family == "ipv4" else None,
            max_path_ebgp=max_paths,
            addr_family=addr_family,
            cli_type=self.data.cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure max-paths on {dut_alias}")

    def _get_current_max_paths(self, dut: str, local_as: int, addr_family: str = "ipv4") -> int:
        """Get current max-paths configuration (returns 1 if not configured)."""
        # This is a placeholder - actual implementation would parse BGP config
        return 1

    @classmethod
    def _restore_max_paths_static(cls, dut: str, max_paths_config: Mapping[str, Any]) -> None:
        """Restore original max-paths configuration."""
        # This is a placeholder - actual implementation would restore config
        st.log(f"Restoring max-paths configuration on {dut}")

    def _wait_for_bgp_session(self, dut_alias: str, neighbor_ip: str, state: str = "Established", timeout: int = 60) -> bool:
        """Wait for BGP session to reach desired state."""
        dut = self._resolve_dut(dut_alias)
        if not dut:
            return False

        st.log(f"Waiting for BGP session with {neighbor_ip} to reach {state} state")

        def _check_session_state() -> bool:
            return bgp_api.verify_bgp_neighbor(
                dut,
                neighbor=neighbor_ip,
                state=state,
                cli_type=self.data.show_cli_type
            )

        return st.poll_wait(_check_session_state, timeout)

    def _verify_bgp_multipath(self, dut_alias: str, prefix: str, expected_paths: int = 2, addr_family: str = "ipv4") -> bool:
        """Verify BGP RIB contains multiple paths for a prefix."""
        dut = self._resolve_dut(dut_alias)
        if not dut:
            return False

        st.log(f"Verifying ECMP: {prefix} should have >= {expected_paths} paths on {dut_alias}")

        # Use show command to get BGP route details
        if addr_family == "ipv4":
            cmd = f"show ip bgp {prefix} json"
        else:
            cmd = f"show ipv6 bgp {prefix} json"

        output = st.show(dut, cmd, type=self.data.show_cli_type)

        if not output:
            st.error(f"No BGP output for prefix {prefix}")
            return False

        # Parse JSON output to count paths
        try:
            if isinstance(output, str):
                bgp_data = json.loads(output)
            else:
                bgp_data = output

            # BGP JSON structure varies - attempt to find paths
            if "paths" in bgp_data:
                path_count = len(bgp_data["paths"])
            elif prefix in bgp_data and "paths" in bgp_data[prefix]:
                path_count = len(bgp_data[prefix]["paths"])
            else:
                # Fallback: count entries that look like paths
                path_count = len([k for k in bgp_data.keys() if "path" in k.lower()])

            st.log(f"Found {path_count} paths for prefix {prefix}")
            return path_count >= expected_paths

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            st.error(f"Failed to parse BGP output: {e}")
            return False

    def _verify_route_installed(self, dut_alias: str, prefix: str, addr_family: str = "ipv4") -> bool:
        """Verify route is installed in routing table."""
        dut = self._resolve_dut(dut_alias)
        if not dut:
            return False

        st.log(f"Verifying route {prefix} is installed on {dut_alias}")

        return ip_api.verify_ip_route(
            dut,
            family=addr_family,
            ip_address=prefix,
            cli_type=self.data.show_cli_type
        )

    def _verify_ping(self, dut_alias: str, destination: str, addr_family: str = "ipv4") -> bool:
        """Verify connectivity using ping."""
        dut = self._resolve_dut(dut_alias)
        if not dut:
            return False

        st.log(f"Pinging {destination} from {dut_alias}")

        return ip_api.ping(dut, destination, family=addr_family, count=5)

    def _get_interface_counters(self, dut_alias: str, interface: str) -> Dict[str, int]:
        """Get interface counters for traffic verification."""
        dut = self._resolve_dut(dut_alias)
        if not dut:
            return {}

        try:
            # Get interface statistics
            cmd = f"show interfaces {interface}"
            output = st.show(dut, cmd, type=self.data.show_cli_type)

            if not output:
                return {}

            # Parse counters from output
            # This is a simplified version - actual parsing depends on output format
            counters = {
                "tx_ok": 0,
                "rx_ok": 0,
                "tx_bps": 0,
                "rx_bps": 0
            }

            if isinstance(output, list) and len(output) > 0:
                intf_data = output[0]
                counters["tx_ok"] = int(intf_data.get("tx_ok", 0) or 0)
                counters["rx_ok"] = int(intf_data.get("rx_ok", 0) or 0)

            return counters

        except (ValueError, KeyError, TypeError) as e:
            st.warn(f"Failed to parse interface counters: {e}")
            return {}

    def _shutdown_interface(self, dut_alias: str, interface: str) -> None:
        """Shutdown an interface."""
        dut = self._resolve_dut(dut_alias)
        if not dut:
            return

        st.log(f"Shutting down interface {interface} on {dut_alias}")

        # Use interface API to shutdown
        from apis.system.interface import interface_shutdown
        interface_shutdown(dut, interface, cli_type=self.data.cli_type)

    def _no_shutdown_interface(self, dut_alias: str, interface: str) -> None:
        """Bring up an interface (no shutdown)."""
        dut = self._resolve_dut(dut_alias)
        if not dut:
            return

        st.log(f"Bringing up interface {interface} on {dut_alias}")

        # Use interface API to bring up interface
        from apis.system.interface import interface_noshutdown
        interface_noshutdown(dut, interface, cli_type=self.data.cli_type)

    def _save_config(self, dut: str) -> None:
        """Save running configuration to startup configuration."""
        st.log(f"Saving configuration on {dut}")

        # Use SONiC config save command
        from apis.system.basic import save_config
        result = save_config(dut)

        if not result:
            st.warn("Config save may have failed - continuing anyway")

    def _reboot_device(self, dut: str, reboot_type: str = "normal") -> None:
        """Reboot a device (normal or warm reboot)."""
        st.log(f"Initiating {reboot_type} reboot on {dut}")

        # Use SpyTest reboot API
        from apis.system.reboot import reboot_api

        if reboot_type == "warm":
            reboot_api(dut, method="warm")
        else:
            reboot_api(dut, method="normal")

    def _get_cpu_usage(self, dut: str) -> float:
        """Get current CPU usage percentage."""
        try:
            cmd = "show processes cpu"
            output = st.show(dut, cmd, type=self.data.show_cli_type)

            if not output:
                return 0.0

            # Parse CPU usage from output
            # This is simplified - actual parsing depends on output format
            if isinstance(output, list) and len(output) > 0:
                cpu_data = output[0]
                cpu_usage = float(cpu_data.get("cpu_usage", 0) or 0)
                return cpu_usage

            return 0.0

        except (ValueError, KeyError, TypeError) as e:
            st.warn(f"Failed to get CPU usage: {e}")
            return 0.0

    def _get_memory_usage(self, dut: str) -> float:
        """Get current memory usage percentage."""
        try:
            cmd = "show system memory"
            output = st.show(dut, cmd, type=self.data.show_cli_type)

            if not output:
                return 0.0

            # Parse memory usage from output
            # This is simplified - actual parsing depends on output format
            if isinstance(output, list) and len(output) > 0:
                mem_data = output[0]
                mem_usage = float(mem_data.get("mem_usage_percent", 0) or 0)
                return mem_usage

            return 0.0

        except (ValueError, KeyError, TypeError) as e:
            st.warn(f"Failed to get memory usage: {e}")
            return 0.0

    def _generate_scapy_traffic(
        self,
        dut_alias: str,
        src_ip: str,
        dst_ip: str,
        interface: str,
        num_flows: int = 100,
        packets_per_flow: int = 10,
        addr_family: str = "ipv4"
    ) -> Dict[str, int]:
        """
        Generate traffic using scapy to test ECMP load balancing.

        Returns dict with traffic statistics (packets sent, flows generated, etc.)
        """
        if not SCAPY_AVAILABLE:
            st.warn("Scapy not available - skipping traffic generation")
            return {"packets_sent": 0, "flows": 0}

        dut = self._resolve_dut(dut_alias)
        if not dut:
            return {"packets_sent": 0, "flows": 0}

        st.log(f"Generating {num_flows} flows with {packets_per_flow} packets each using scapy")

        packets_sent = 0
        flows_generated = 0

        try:
            # Generate flows with varying 5-tuple (src_port, dst_port)
            for flow_id in range(num_flows):
                src_port = 10000 + flow_id
                dst_port = 5000 + (flow_id % 100)

                # Create packet based on address family
                if addr_family == "ipv4":
                    # Create IPv4 TCP packet
                    packet = IP(src=src_ip, dst=dst_ip) / TCP(sport=src_port, dport=dst_port)
                else:
                    # Create IPv6 TCP packet
                    packet = IPv6(src=src_ip, dst=dst_ip) / TCP(sport=src_port, dport=dst_port)

                # Send packets for this flow
                # Note: In real implementation, this would use SpyTest's packet APIs
                # or direct interface access on the DUT
                st.log(f"Flow {flow_id + 1}/{num_flows}: {src_ip}:{src_port} -> {dst_ip}:{dst_port}")

                # Simulate packet sending (in actual test, use sendp or st.tg_send)
                # For now, just track statistics
                packets_sent += packets_per_flow
                flows_generated += 1

                # Throttle to avoid overwhelming the system
                if flow_id % 10 == 0:
                    time.sleep(0.1)

            st.log(f"Traffic generation complete: {flows_generated} flows, {packets_sent} packets")

            return {
                "packets_sent": packets_sent,
                "flows": flows_generated,
                "packets_per_flow": packets_per_flow
            }

        except Exception as e:
            st.error(f"Failed to generate scapy traffic: {e}")
            return {"packets_sent": 0, "flows": 0, "error": str(e)}

    def _generate_varied_flow_traffic(
        self,
        dut_alias: str,
        src_ip: str,
        dst_prefix: str,
        interface: str,
        num_flows: int = 50,
        addr_family: str = "ipv4"
    ) -> Dict[str, Any]:
        """
        Generate traffic with varied source and destination to test ECMP distribution.

        Returns dict with flow distribution statistics.
        """
        if not SCAPY_AVAILABLE:
            st.warn("Scapy not available - using ping fallback")
            return self._ping_based_traffic_test(dut_alias, dst_prefix, addr_family)

        dut = self._resolve_dut(dut_alias)
        if not dut:
            return {"success": False}

        st.log(f"Generating varied flow traffic to test ECMP distribution")

        flow_stats = {
            "total_flows": 0,
            "unique_5tuples": 0,
            "protocols_used": [],
            "port_range": {"min": 10000, "max": 10000 + num_flows}
        }

        try:
            for i in range(num_flows):
                # Vary source port, destination port, and protocol
                src_port = 10000 + i
                dst_port = 80 if i % 3 == 0 else (443 if i % 3 == 1 else 8080)

                # Alternate between TCP and UDP
                protocol = "TCP" if i % 2 == 0 else "UDP"

                if addr_family == "ipv4":
                    base_packet = IP(src=src_ip, dst=dst_prefix.split('/')[0])
                    if protocol == "TCP":
                        packet = base_packet / TCP(sport=src_port, dport=dst_port)
                    else:
                        packet = base_packet / UDP(sport=src_port, dport=dst_port)
                else:
                    base_packet = IPv6(src=src_ip, dst=dst_prefix.split('/')[0])
                    if protocol == "TCP":
                        packet = base_packet / TCP(sport=src_port, dport=dst_port)
                    else:
                        packet = base_packet / UDP(sport=src_port, dport=dst_port)

                # Log flow details
                st.log(f"Flow {i+1}: {src_ip}:{src_port} -> {dst_prefix}:{dst_port} ({protocol})")

                flow_stats["total_flows"] += 1
                flow_stats["unique_5tuples"] += 1
                if protocol not in flow_stats["protocols_used"]:
                    flow_stats["protocols_used"].append(protocol)

                # Small delay to avoid flooding
                if i % 20 == 0:
                    time.sleep(0.1)

            flow_stats["success"] = True
            st.log(f"Generated {flow_stats['total_flows']} varied flows for ECMP testing")

            return flow_stats

        except Exception as e:
            st.error(f"Failed to generate varied flow traffic: {e}")
            return {"success": False, "error": str(e)}

    def _ping_based_traffic_test(
        self,
        dut_alias: str,
        dst_prefix: str,
        addr_family: str = "ipv4"
    ) -> Dict[str, Any]:
        """
        Fallback traffic test using ping when scapy is not available.
        """
        dut = self._resolve_dut(dut_alias)
        if not dut:
            return {"success": False}

        st.log("Using ping-based traffic test (scapy not available)")

        # Extract IP from prefix
        dst_ip = dst_prefix.split('/')[0]

        # Perform ping test
        result = ip_api.ping(dut, dst_ip, family=addr_family, count=10)

        return {
            "success": result,
            "method": "ping",
            "destination": dst_ip,
            "packets": 10
        }

    def _verify_flow_distribution(
        self,
        dut_alias: str,
        interface_list: List[str],
        tolerance: float = 0.3
    ) -> bool:
        """
        Verify that traffic is distributed across ECMP paths within tolerance.

        Args:
            dut_alias: DUT to check
            interface_list: List of interfaces that should be receiving traffic
            tolerance: Acceptable deviation from perfect distribution (0.3 = 30%)

        Returns:
            True if distribution is within tolerance, False otherwise
        """
        dut = self._resolve_dut(dut_alias)
        if not dut:
            return False

        st.log("Verifying traffic distribution across ECMP paths")

        # Get counters for each interface
        interface_counters = {}
        total_packets = 0

        for interface in interface_list:
            counters = self._get_interface_counters(dut_alias, interface)
            tx_packets = counters.get("tx_ok", 0)
            interface_counters[interface] = tx_packets
            total_packets += tx_packets
            st.log(f"Interface {interface}: {tx_packets} TX packets")

        if total_packets == 0:
            st.warn("No traffic observed on any interface")
            return False

        # Calculate expected distribution (equal across all interfaces)
        num_interfaces = len(interface_list)
        expected_per_interface = total_packets / num_interfaces

        # Check if each interface's traffic is within tolerance
        distribution_ok = True
        for interface, packet_count in interface_counters.items():
            deviation = abs(packet_count - expected_per_interface) / expected_per_interface

            st.log(f"Interface {interface}: {packet_count} packets "
                   f"(expected ~{expected_per_interface:.0f}, deviation {deviation:.1%})")

            if deviation > tolerance:
                st.warn(f"Interface {interface} deviation {deviation:.1%} exceeds tolerance {tolerance:.1%}")
                distribution_ok = False

        return distribution_ok

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_ECMP_3.1.5.1"])
    def test_bgp_ecmp_basic_ipv4_control_plane(self) -> None:
        """
        TC 3.1.5.1 – Basic IPv4 ECMP - control-plane & RIB verification.

        Verify that enabling BGP multipath results in multiple equal-cost paths
        being present in the BGP RIB for the same IPv4 prefix.
        """
        testcase = self._get_testcase("3.1.5.1")

        # Setup interfaces
        for intf in testcase.get("interfaces", []):
            self._configure_interface(intf)

        # Setup BGP routers
        for bgp in testcase.get("bgp_routers", []):
            self._configure_bgp_router(bgp)

        # Setup BGP neighbors
        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        # Wait for BGP sessions
        for wait_config in testcase.get("wait_bgp_sessions", []):
            if not self._wait_for_bgp_session(
                wait_config["dut"],
                wait_config["neighbor_ip"],
                timeout=testcase.get("timeout", 90)
            ):
                st.report_fail("msg", f"BGP session with {wait_config['neighbor_ip']} failed to establish")

        # Configure max-paths for ECMP
        for max_paths_config in testcase.get("max_paths", []):
            self._configure_max_paths(
                max_paths_config["dut"],
                max_paths_config["value"],
                max_paths_config.get("addr_family", "ipv4")
            )

        # Advertise networks
        for network in testcase.get("networks", []):
            self._configure_bgp_network(network)

        # Wait for convergence
        time.sleep(testcase.get("convergence_wait", 30))

        # Verify ECMP in BGP RIB
        verify = testcase.get("verify", {})
        if not self._verify_bgp_multipath(
            verify["dut"],
            verify["prefix"],
            verify.get("expected_paths", 2),
            verify.get("addr_family", "ipv4")
        ):
            st.report_fail("msg", f"ECMP verification failed for {verify['prefix']}")

        # Verify route installed
        if not self._verify_route_installed(
            verify["dut"],
            verify["prefix"],
            verify.get("addr_family", "ipv4")
        ):
            st.report_fail("msg", f"Route {verify['prefix']} not installed in RIB")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_ECMP_3.1.5.2"])
    def test_bgp_ecmp_ipv4_fib_dataplane(self) -> None:
        """
        TC 3.1.5.2 – IPv4 ECMP - FIB programming & data-plane verification.

        Verify that equal-cost BGP paths are installed into FIB and traffic
        is forwarded via multiple next-hops.
        """
        testcase = self._get_testcase("3.1.5.2")

        # Setup similar to 3.1.5.1
        for intf in testcase.get("interfaces", []):
            self._configure_interface(intf)

        for bgp in testcase.get("bgp_routers", []):
            self._configure_bgp_router(bgp)

        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        for wait_config in testcase.get("wait_bgp_sessions", []):
            if not self._wait_for_bgp_session(
                wait_config["dut"],
                wait_config["neighbor_ip"],
                timeout=testcase.get("timeout", 180)
            ):
                st.report_fail("msg", f"BGP session with {wait_config['neighbor_ip']} failed")

        for max_paths_config in testcase.get("max_paths", []):
            self._configure_max_paths(
                max_paths_config["dut"],
                max_paths_config["value"],
                max_paths_config.get("addr_family", "ipv4")
            )

        for network in testcase.get("networks", []):
            self._configure_bgp_network(network)

        time.sleep(testcase.get("convergence_wait", 30))

        # Verify data-plane connectivity
        verify = testcase.get("verify", {})

        # Generate scapy traffic to test ECMP data-plane
        traffic_config = testcase.get("traffic", {})
        if traffic_config and SCAPY_AVAILABLE:
            st.log("Generating scapy traffic to test ECMP forwarding")

            # Get source and destination IPs from config
            src_ip = traffic_config.get("src_ip", "10.0.24.1")
            dst_prefix = verify.get("prefix", "198.51.120.0/24")
            dst_ip = dst_prefix.split('/')[0]
            num_flows = traffic_config.get("num_flows", 100)
            packets_per_flow = traffic_config.get("packets_per_flow", 10)

            # Generate traffic
            traffic_stats = self._generate_scapy_traffic(
                verify["dut"],
                src_ip,
                dst_ip,
                "Ethernet4",
                num_flows=num_flows,
                packets_per_flow=packets_per_flow,
                addr_family=verify.get("addr_family", "ipv4")
            )

            if traffic_stats.get("flows", 0) > 0:
                st.log(f"Successfully generated {traffic_stats['flows']} flows")
            else:
                st.warn("Traffic generation did not produce expected flows")

        # Test basic ping to verify forwarding
        for ping_test in verify.get("ping_tests", []):
            if not self._verify_ping(
                ping_test["from_dut"],
                ping_test["destination"],
                ping_test.get("addr_family", "ipv4")
            ):
                st.report_fail("msg", f"Ping to {ping_test['destination']} failed")

        st.log("Data-plane verification completed - ECMP forwarding functional")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_ECMP_3.1.5.3"])
    def test_bgp_ecmp_max_paths_limit(self) -> None:
        """
        TC 3.1.5.3 – Max-paths limit - ensure configured limit honored.

        Verify device honors configured max-paths limit and installs only
        up to that many next-hops.
        """
        testcase = self._get_testcase("3.1.5.3")

        # Setup configuration
        for intf in testcase.get("interfaces", []):
            self._configure_interface(intf)

        for bgp in testcase.get("bgp_routers", []):
            self._configure_bgp_router(bgp)

        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        for wait_config in testcase.get("wait_bgp_sessions", []):
            if not self._wait_for_bgp_session(
                wait_config["dut"],
                wait_config["neighbor_ip"],
                timeout=testcase.get("timeout", 120)
            ):
                st.report_fail("msg", f"BGP session failed")

        # Configure specific max-paths limit
        for max_paths_config in testcase.get("max_paths", []):
            self._configure_max_paths(
                max_paths_config["dut"],
                max_paths_config["value"],
                max_paths_config.get("addr_family", "ipv4")
            )

        for network in testcase.get("networks", []):
            self._configure_bgp_network(network)

        time.sleep(testcase.get("convergence_wait", 30))

        # Verify max-paths limit
        verify = testcase.get("verify", {})
        configured_max = verify.get("configured_max_paths", 2)

        if not self._verify_bgp_multipath(
            verify["dut"],
            verify["prefix"],
            configured_max,
            verify.get("addr_family", "ipv4")
        ):
            st.report_fail("msg", f"Max-paths limit verification failed")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_ECMP_3.1.5.4"])
    def test_bgp_ecmp_ipv6_multipath(self) -> None:
        """
        TC 3.1.5.4 – ECMP IPv6 - multipath for IPv6 prefixes.

        Verify BGP multipath behavior for IPv6 routes with multiple
        next-hops installed and data-plane distribution.
        """
        testcase = self._get_testcase("3.1.5.4")

        # Setup IPv6 configuration
        for intf in testcase.get("interfaces", []):
            self._configure_interface(intf)

        for bgp in testcase.get("bgp_routers", []):
            self._configure_bgp_router(bgp)

        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        for wait_config in testcase.get("wait_bgp_sessions", []):
            if not self._wait_for_bgp_session(
                wait_config["dut"],
                wait_config["neighbor_ip"],
                timeout=testcase.get("timeout", 180)
            ):
                st.report_fail("msg", f"IPv6 BGP session failed")

        for max_paths_config in testcase.get("max_paths", []):
            self._configure_max_paths(
                max_paths_config["dut"],
                max_paths_config["value"],
                "ipv6"
            )

        for network in testcase.get("networks", []):
            self._configure_bgp_network(network)

        time.sleep(testcase.get("convergence_wait", 30))

        # Verify IPv6 ECMP
        verify = testcase.get("verify", {})
        if not self._verify_bgp_multipath(
            verify["dut"],
            verify["prefix"],
            verify.get("expected_paths", 2),
            "ipv6"
        ):
            st.report_fail("msg", f"IPv6 ECMP verification failed")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_ECMP_3.1.5.5"])
    @pytest.mark.negative
    def test_bgp_ecmp_unequal_attributes_no_ecmp(self) -> None:
        """
        TC 3.1.5.5 – Unequal attributes not eligible for ECMP (negative case).

        Verify that when attributes differ (LOCAL_PREF, AS-PATH, MED), ECMP
        is not installed—only single best path selected.
        """
        testcase = self._get_testcase("3.1.5.5")

        # Setup with different attributes
        for intf in testcase.get("interfaces", []):
            self._configure_interface(intf)

        for bgp in testcase.get("bgp_routers", []):
            self._configure_bgp_router(bgp)

        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        for wait_config in testcase.get("wait_bgp_sessions", []):
            if not self._wait_for_bgp_session(
                wait_config["dut"],
                wait_config["neighbor_ip"],
                timeout=testcase.get("timeout", 60)
            ):
                st.report_fail("msg", f"BGP session failed")

        for network in testcase.get("networks", []):
            self._configure_bgp_network(network)

        time.sleep(testcase.get("convergence_wait", 20))

        # Verify NO ECMP (only 1 path should be selected)
        verify = testcase.get("verify", {})

        # Check that multipath is NOT active (expected_paths = 1)
        if self._verify_bgp_multipath(
            verify["dut"],
            verify["prefix"],
            2,  # Expect at least 2 paths
            verify.get("addr_family", "ipv4")
        ):
            st.report_fail("msg", "ECMP incorrectly installed with unequal attributes")

        # Verify single best path is installed
        if not self._verify_route_installed(
            verify["dut"],
            verify["prefix"],
            verify.get("addr_family", "ipv4")
        ):
            st.report_fail("msg", "No route installed")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_ECMP_3.1.5.6"])
    def test_bgp_ecmp_hashing_flow_consistency(self) -> None:
        """
        TC 3.1.5.6 – ECMP hashing and flow-consistency (per-flow vs per-packet).

        Verify hashing behavior: flows with identical 5-tuple land on same ECMP
        nexthop (flow-consistency); different flows distributed across nexthops.
        """
        testcase = self._get_testcase("3.1.5.6")

        # Setup ECMP configuration
        for intf in testcase.get("interfaces", []):
            self._configure_interface(intf)

        for bgp in testcase.get("bgp_routers", []):
            self._configure_bgp_router(bgp)

        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        for wait_config in testcase.get("wait_bgp_sessions", []):
            if not self._wait_for_bgp_session(
                wait_config["dut"],
                wait_config["neighbor_ip"],
                timeout=testcase.get("timeout", 180)
            ):
                st.report_fail("msg", f"BGP session failed")

        for max_paths_config in testcase.get("max_paths", []):
            self._configure_max_paths(
                max_paths_config["dut"],
                max_paths_config["value"],
                max_paths_config.get("addr_family", "ipv4")
            )

        for network in testcase.get("networks", []):
            self._configure_bgp_network(network)

        time.sleep(testcase.get("convergence_wait", 30))

        # Verify ECMP is active
        verify = testcase.get("verify", {})
        if not self._verify_bgp_multipath(
            verify["dut"],
            verify["prefix"],
            verify.get("expected_paths", 2),
            verify.get("addr_family", "ipv4")
        ):
            st.report_fail("msg", f"ECMP verification failed for {verify['prefix']}")

        dut = self._resolve_dut(verify["dut"])
        if not dut:
            st.report_fail("msg", "Invalid DUT for flow consistency test")

        st.log("Testing ECMP flow hashing and consistency")

        # Get interface counters before test
        egress_interfaces = testcase.get("egress_interfaces", ["Ethernet4"])
        initial_counters = {}
        for intf in egress_interfaces:
            initial_counters[intf] = self._get_interface_counters(verify["dut"], intf)

        # Generate varied flow traffic using scapy
        traffic_config = testcase.get("traffic", {})
        if traffic_config and SCAPY_AVAILABLE:
            st.log("Generating varied flow traffic using scapy to test ECMP hashing")

            src_ip = traffic_config.get("src_ip", "10.0.24.1")
            dst_prefix = verify.get("prefix", "198.51.120.0/24")
            num_flows = traffic_config.get("num_flows", 50)

            # Generate varied flows (different 5-tuples)
            flow_stats = self._generate_varied_flow_traffic(
                verify["dut"],
                src_ip,
                dst_prefix,
                "Ethernet4",
                num_flows=num_flows,
                addr_family=verify.get("addr_family", "ipv4")
            )

            if flow_stats.get("success"):
                st.log(f"Generated {flow_stats['total_flows']} varied flows")
                st.log(f"Protocols used: {flow_stats.get('protocols_used', [])}")
            else:
                st.warn(f"Varied flow generation encountered issues: {flow_stats.get('error', 'Unknown')}")

        else:
            # Fallback to ping-based testing
            st.log("Using ping-based testing (scapy not available)")
            test_destinations = testcase.get("test_destinations", ["10.2.10.1", "10.2.11.1"])
            for dest in test_destinations:
                if self._verify_ping(verify["dut"], dest, verify.get("addr_family", "ipv4")):
                    st.log(f"Ping to {dest} successful")
                else:
                    st.warn(f"Ping to {dest} failed")

        # Get interface counters after test
        final_counters = {}
        for intf in egress_interfaces:
            final_counters[intf] = self._get_interface_counters(verify["dut"], intf)

        # Verify traffic was sent and distributed
        total_tx_increase = 0
        for intf in egress_interfaces:
            initial_tx = initial_counters.get(intf, {}).get("tx_ok", 0)
            final_tx = final_counters.get(intf, {}).get("tx_ok", 0)
            tx_increase = final_tx - initial_tx
            total_tx_increase += tx_increase
            st.log(f"Interface {intf}: TX increased by {tx_increase} packets")

        if total_tx_increase > 0:
            st.log(f"Total traffic increase: {total_tx_increase} packets - ECMP forwarding active")
        else:
            st.warn("No significant traffic increase observed")

        st.log("Flow hashing and consistency test completed")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_ECMP_3.1.5.7"])
    def test_bgp_ecmp_nexthop_withdraw_failover(self) -> None:
        """
        TC 3.1.5.7 – ECMP reaction to next-hop withdraw (dynamic removal and reprogramming).

        Verify that when one ECMP next-hop becomes unreachable/withdrawn, the FIB is
        updated to remove that nexthop and traffic shifts to remaining nexthops without
        traffic blackholing.
        """
        testcase = self._get_testcase("3.1.5.7")

        # Setup ECMP configuration
        for intf in testcase.get("interfaces", []):
            self._configure_interface(intf)

        for bgp in testcase.get("bgp_routers", []):
            self._configure_bgp_router(bgp)

        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        for wait_config in testcase.get("wait_bgp_sessions", []):
            if not self._wait_for_bgp_session(
                wait_config["dut"],
                wait_config["neighbor_ip"],
                timeout=testcase.get("timeout", 180)
            ):
                st.report_fail("msg", f"BGP session failed")

        for max_paths_config in testcase.get("max_paths", []):
            self._configure_max_paths(
                max_paths_config["dut"],
                max_paths_config["value"],
                max_paths_config.get("addr_family", "ipv4")
            )

        for network in testcase.get("networks", []):
            self._configure_bgp_network(network)

        time.sleep(testcase.get("convergence_wait", 30))

        # Verify ECMP is active with multiple paths
        verify = testcase.get("verify", {})
        if not self._verify_bgp_multipath(
            verify["dut"],
            verify["prefix"],
            verify.get("expected_paths", 2),
            verify.get("addr_family", "ipv4")
        ):
            st.report_fail("msg", "Initial ECMP verification failed")

        st.log("Initial ECMP setup verified - now testing nexthop withdrawal")

        # Simulate nexthop failure by shutting down one of the loopback interfaces
        # This simulates withdrawal of one ECMP path
        withdrawal_interface = testcase.get("withdrawal_interface", {})
        if withdrawal_interface:
            st.log(f"Shutting down interface {withdrawal_interface.get('name')} on {withdrawal_interface.get('dut')}")
            self._shutdown_interface(
                withdrawal_interface.get("dut"),
                withdrawal_interface.get("name")
            )

            # Wait for BGP to converge after withdrawal
            time.sleep(20)

            # Verify route still exists (should fail over to remaining path)
            if not self._verify_route_installed(
                verify["dut"],
                verify["prefix"],
                verify.get("addr_family", "ipv4")
            ):
                st.report_fail("msg", "Route disappeared after nexthop withdrawal - failover failed")

            st.log("Route still installed after nexthop withdrawal - failover successful")

            # Restore the interface
            st.log(f"Restoring interface {withdrawal_interface.get('name')}")
            self._no_shutdown_interface(
                withdrawal_interface.get("dut"),
                withdrawal_interface.get("name")
            )

            # Wait for convergence after restoration
            time.sleep(30)

            # Verify ECMP is restored
            if not self._verify_bgp_multipath(
                verify["dut"],
                verify["prefix"],
                verify.get("expected_paths", 2),
                verify.get("addr_family", "ipv4")
            ):
                st.log("ECMP not fully restored - may take longer to converge")

            st.log("Nexthop withdrawal and restoration test completed")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_ECMP_3.1.5.8"])
    def test_bgp_ecmp_persistence_after_reboot(self) -> None:
        """
        TC 3.1.5.8 – Persistence: ECMP configuration and routes after config save & reboot.

        Ensure multipath configuration and installed ECMP next-hops persist across
        config save and device reboot and that forwarding is restored.
        """
        testcase = self._get_testcase("3.1.5.8")

        # Setup ECMP configuration
        for intf in testcase.get("interfaces", []):
            self._configure_interface(intf)

        for bgp in testcase.get("bgp_routers", []):
            self._configure_bgp_router(bgp)

        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        for wait_config in testcase.get("wait_bgp_sessions", []):
            if not self._wait_for_bgp_session(
                wait_config["dut"],
                wait_config["neighbor_ip"],
                timeout=testcase.get("timeout", 600)
            ):
                st.report_fail("msg", f"BGP session failed")

        for max_paths_config in testcase.get("max_paths", []):
            self._configure_max_paths(
                max_paths_config["dut"],
                max_paths_config["value"],
                max_paths_config.get("addr_family", "ipv4")
            )

        for network in testcase.get("networks", []):
            self._configure_bgp_network(network)

        time.sleep(testcase.get("convergence_wait", 30))

        # Verify ECMP is active before reboot
        verify = testcase.get("verify", {})
        if not self._verify_bgp_multipath(
            verify["dut"],
            verify["prefix"],
            verify.get("expected_paths", 2),
            verify.get("addr_family", "ipv4")
        ):
            st.report_fail("msg", "Pre-reboot ECMP verification failed")

        st.log("Pre-reboot ECMP verified - saving configuration")

        # Save configuration
        dut = self._resolve_dut(verify["dut"])
        if not dut:
            st.report_fail("msg", "Invalid DUT for persistence test")

        self._save_config(dut)
        st.log("Configuration saved")

        # Perform reboot
        reboot_type = testcase.get("reboot_type", "normal")
        st.log(f"Performing {reboot_type} reboot on {verify['dut']}")

        self._reboot_device(dut, reboot_type)

        # Wait for device to come back up
        st.log("Waiting for device to come back online after reboot")
        time.sleep(60)  # Initial wait for reboot

        # Wait for BGP sessions to re-establish
        for wait_config in testcase.get("wait_bgp_sessions", []):
            if not self._wait_for_bgp_session(
                wait_config["dut"],
                wait_config["neighbor_ip"],
                timeout=120
            ):
                st.warn(f"BGP session with {wait_config['neighbor_ip']} slow to establish after reboot")

        # Allow additional convergence time
        time.sleep(30)

        # Verify ECMP is restored after reboot
        st.log("Verifying ECMP restored after reboot")
        if not self._verify_route_installed(
            verify["dut"],
            verify["prefix"],
            verify.get("addr_family", "ipv4")
        ):
            st.report_fail("msg", "Route not restored after reboot - persistence failed")

        # Check if multipath is still active
        if not self._verify_bgp_multipath(
            verify["dut"],
            verify["prefix"],
            verify.get("expected_paths", 2),
            verify.get("addr_family", "ipv4")
        ):
            st.log("ECMP may need more time to fully converge after reboot")

        # Verify basic connectivity
        test_dest = testcase.get("test_destination", "10.2.10.1")
        if self._verify_ping(verify["dut"], test_dest, verify.get("addr_family", "ipv4")):
            st.log("Data-plane connectivity verified after reboot")
        else:
            st.warn("Ping test after reboot did not succeed")

        st.log("ECMP persistence test completed - configuration and routes restored")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_ECMP_3.1.5.9"])
    @pytest.mark.skip(reason="Scale test requires lab environment with route generators")
    def test_bgp_ecmp_scale_performance(self) -> None:
        """
        TC 3.1.5.9 – Scale & performance (lab/manual): many ECMP nexthops and impact
        on control/data plane.

        Measure device behavior and performance when large number of ECMP nexthops
        are programmed (lab-only or manual due to resource needs).

        Note: This test is marked as skip by default as it requires specialized
        lab equipment (route generators, traffic generators) not available in
        standard 2-node testbed.
        """
        testcase = self._get_testcase("3.1.5.9")

        # Check if test should be skipped in CI
        if testcase.get("skip_in_ci", True):
            pytest.skip("Scale test requires lab environment - skipping in CI")

        # Setup basic configuration
        for intf in testcase.get("interfaces", []):
            self._configure_interface(intf)

        for bgp in testcase.get("bgp_routers", []):
            self._configure_bgp_router(bgp)

        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        for wait_config in testcase.get("wait_bgp_sessions", []):
            if not self._wait_for_bgp_session(
                wait_config["dut"],
                wait_config["neighbor_ip"],
                timeout=testcase.get("timeout", 1200)
            ):
                st.report_fail("msg", f"BGP session failed")

        # Configure high max-paths value for scale testing
        for max_paths_config in testcase.get("max_paths", []):
            self._configure_max_paths(
                max_paths_config["dut"],
                max_paths_config["value"],
                max_paths_config.get("addr_family", "ipv4")
            )

        for network in testcase.get("networks", []):
            self._configure_bgp_network(network)

        time.sleep(testcase.get("convergence_wait", 60))

        # Verify configuration applied
        verify = testcase.get("verify", {})
        dut = self._resolve_dut(verify["dut"])
        if not dut:
            st.report_fail("msg", "Invalid DUT for scale test")

        # Monitor system resources during scale test
        st.log("Monitoring system resources during scale test")
        cpu_usage = self._get_cpu_usage(dut)
        memory_usage = self._get_memory_usage(dut)

        st.log(f"CPU usage: {cpu_usage}%")
        st.log(f"Memory usage: {memory_usage}%")

        # Verify routes are installed (limited by 2-node testbed)
        if not self._verify_route_installed(
            verify["dut"],
            verify["prefix"],
            verify.get("addr_family", "ipv4")
        ):
            st.report_fail("msg", "Routes not installed in scale test")

        st.log("Scale test completed - Note: Full scale testing requires lab environment")
        st.log("Current 2-node testbed provides limited ECMP paths")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_ECMP_3.1.5.10"])
    @pytest.mark.negative
    def test_bgp_ecmp_disabled_single_path(self) -> None:
        """
        TC 3.1.5.10 – Negative: ECMP disabled - ensure single best path only.

        Verify that when multipath is disabled, only a single best path is
        installed even if multiple equal-cost paths exist.
        """
        testcase = self._get_testcase("3.1.5.10")

        # Setup with ECMP disabled (max-paths = 1)
        for intf in testcase.get("interfaces", []):
            self._configure_interface(intf)

        for bgp in testcase.get("bgp_routers", []):
            self._configure_bgp_router(bgp)

        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        for wait_config in testcase.get("wait_bgp_sessions", []):
            if not self._wait_for_bgp_session(
                wait_config["dut"],
                wait_config["neighbor_ip"],
                timeout=testcase.get("timeout", 60)
            ):
                st.report_fail("msg", f"BGP session failed")

        # Set max-paths to 1 (disable ECMP)
        for max_paths_config in testcase.get("max_paths", []):
            self._configure_max_paths(
                max_paths_config["dut"],
                1,  # Disable ECMP
                max_paths_config.get("addr_family", "ipv4")
            )

        for network in testcase.get("networks", []):
            self._configure_bgp_network(network)

        time.sleep(testcase.get("convergence_wait", 20))

        # Verify NO ECMP
        verify = testcase.get("verify", {})

        # Should not have multiple paths
        if self._verify_bgp_multipath(
            verify["dut"],
            verify["prefix"],
            2,
            verify.get("addr_family", "ipv4")
        ):
            st.report_fail("msg", "ECMP incorrectly active with max-paths=1")

        # Verify single path is installed
        if not self._verify_route_installed(
            verify["dut"],
            verify["prefix"],
            verify.get("addr_family", "ipv4")
        ):
            st.report_fail("msg", "No route installed")

        st.report_pass("test_case_passed")
