"""
BGP ROUTE REDISTRIBUTION - eBGP Connected and Static Routes with Traffic Verification
Author: Claude Code
2025

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2node.yaml  \
  tests/routing/BGP/test_bgp_ebgp_connected_static_redistribution.py \
  --logs-path ./logs/bgp_ebgp_redistribution_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Comprehensive validation of BGP route redistribution functionality covering
  connected and static route redistribution scenarios with end-to-end traffic
  verification. Tests establish eBGP sessions (AS 65001 and AS 65002) with RFC
  8212 compliant route-maps, redistribute directly attached interfaces and
  loopback addresses into BGP, redistribute static routes, and validate
  bidirectional traffic forwarding using ping tests. All configurations use klish
  mode while show commands use click for consistency.

Pre-requisites:
  - Topology: 4 nodes (2 routers + 2 hosts) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 4 nodes (R1-R2 WAN link, R1-H1 LAN, R2-H2 LAN)
        # +----------------+     WAN Link      +----------------+
        # |   R1 (D1)      |  Eth4  -  Eth4    |   R2 (D2)      |
        # | 10.1.1.1/24    |===================| 10.1.1.2/24    |
        # | AS 65001       |                   | AS 65002       |
        # +----------------+                   +----------------+
        #   Eth16|                                    |Eth16
        #        |                                    |
        #   +--------+                           +--------+
        #   | H1 (D3)|                           | H2 (D4)|
        #   |192.0.2 |                           |198.51  |
        #   | .10/24 |                           |.100.10 |
        #   +--------+                           +--------+
  - Required test variables (YAML): vars_bgp_ebgp_connected_static_redistribution.yaml
  - Feature: RFC 8212 support, BGP redistribution (connected, static)
  - Min SONiC version: 202205+ (for klish BGP support)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.ip as ip_api
import apis.routing.bgp as bgp_api
import apis.system.interface as intf_api

# Test case IDs for tracking
TC_IDS = SpyTestDict({
    "base_ebgp": "TC-BGP-EBGP-REDIST-001",
    "connected_redist": "TC-BGP-EBGP-REDIST-002",
    "static_redist": "TC-BGP-EBGP-REDIST-003",
})

VAR_FILE_ENV = "BGP_EBGP_CONNECTED_STATIC_REDISTRIBUTION_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent / "vars_bgp_ebgp_connected_static_redistribution.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"BGP eBGP redistribution variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("BGP eBGP redistribution YAML must contain key 'testcases'")

    return content


class TestBgpEbgpConnectedStaticRedistribution:
    """
    Test class for BGP eBGP route redistribution scenarios.
    Validates connected and static route redistribution with traffic verification.
    """

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """
        Class-level setup: load configuration and establish topology mapping.
        Initializes test data from YAML and maps topology aliases to device handles.
        """
        st.banner("CLASS SETUP: BGP eBGP Route Redistribution Test Initialization")

        # Load configuration from YAML
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # Get topology from testbed (avoid framework topology validation issues)
        topology = st.get_testbed_vars()

        # Initialize class data
        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))

        # CLI types: klish for both config and show commands
        cls.data.config_cli_type = defaults.get("config_cli_type", "klish")
        cls.data.show_cli_type = defaults.get("show_cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 90))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Map devices from topology
        cls.data.r1 = topology.D1  # Router 1 (smic_sonic1)
        cls.data.r2 = topology.D2  # Router 2 (smic_sonic2)
        cls.data.h1 = topology.D3  # Host 1 (vs_sonic_3)
        cls.data.h2 = topology.D4  # Host 2 (vs_sonic_4)

        # Map interfaces from topology
        cls.data.r1_wan_port = topology.D1D2P1  # R1 Eth4 → R2
        cls.data.r1_lan_port = topology.D1D3P1  # R1 Eth16 → H1
        cls.data.r2_wan_port = topology.D2D1P1  # R2 Eth4 → R1
        cls.data.r2_lan_port = topology.D2D4P1  # R2 Eth16 → H2
        cls.data.h1_port = topology.D3D1P1      # H1 Eth0 → R1
        cls.data.h2_port = topology.D4D2P1      # H2 Eth16 → R2

        st.log(f"Topology initialized: R1={cls.data.r1}, R2={cls.data.r2}, "
               f"H1={cls.data.h1}, H2={cls.data.h2}")
        st.log(f"CLI types: config={cls.data.config_cli_type}, show={cls.data.show_cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """
        Class-level teardown: cleanup all configurations.
        Removes BGP, route-maps, interfaces, and restores devices to clean state.
        """
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping teardown")
            return

        st.banner("CLASS TEARDOWN: BGP eBGP Route Redistribution Cleanup")
        cls._cleanup_all_configs()
        st.log("Cleanup completed successfully")

    @classmethod
    def _cleanup_all_configs(cls) -> None:
        """Remove all configurations in reverse order of setup."""
        tc_config = cls.data.testcases.get("001", {})
        r1_config = tc_config.get("router1", {})
        r2_config = tc_config.get("router2", {})

        duts = [cls.data.r1, cls.data.r2]

        # Step 1: Remove BGP configurations
        st.log("Removing BGP configurations")
        for dut, config in zip([cls.data.r1, cls.data.r2], [r1_config, r2_config]):
            try:
                st.config(dut, [
                    "configure terminal",
                    "no router bgp",
                    "end"
                ], type="klish", skip_error_check=True)
                st.log(f"BGP removed on {dut}")
            except Exception as e:
                st.log(f"BGP cleanup error on {dut}: {e}")

        # Step 2: Remove route-maps
        st.log("Removing route-maps")
        for dut in duts:
            try:
                ip_api.config_route_map(
                    dut,
                    route_map="PERMIT_ALL",
                    config='no',
                    cli_type=cls.data.config_cli_type
                )
                st.log(f"Route-map removed on {dut}")
            except Exception as e:
                st.log(f"Route-map cleanup error on {dut}: {e}")

        # Step 3: Remove loopback interfaces (from test 002)
        st.log("Removing loopback interfaces")
        for dut in duts:
            try:
                ip_api.configure_loopback(
                    dut=dut,
                    loopback_name="Loopback1",
                    config='no',
                    cli_type=cls.data.config_cli_type
                )
                st.log(f"Loopback1 removed on {dut}")
            except Exception as e:
                st.log(f"Loopback cleanup error on {dut}: {e}")

        # Step 4: Remove static routes (from test 003)
        st.log("Removing static routes")
        tc_003 = cls.data.testcases.get("003", {})
        if tc_003:
            for dut, config_key in [(cls.data.r1, 'router1'), (cls.data.r2, 'router2')]:
                try:
                    static_config = tc_003.get(config_key, {}).get('static_route', {})
                    if static_config:
                        ip_api.delete_static_route(
                            dut,
                            next_hop=static_config.get('next_hop'),
                            static_ip=static_config.get('network'),
                            family='ipv4',
                            cli_type=cls.data.config_cli_type
                        )
                        st.log(f"Static route removed on {dut}")
                except Exception as e:
                    st.log(f"Static route cleanup error on {dut}: {e}")

        # Step 5: Remove IP addresses from interfaces
        st.log("Removing IP addresses from interfaces")
        try:
            # Remove WAN IPs
            ip_api.delete_ip_interface(
                cls.data.r1, cls.data.r1_wan_port, f"{r1_config['wan_ip']}/{r1_config['wan_subnet']}",
                family='ipv4', cli_type=cls.data.config_cli_type
            )
            ip_api.delete_ip_interface(
                cls.data.r2, cls.data.r2_wan_port, f"{r2_config['wan_ip']}/{r2_config['wan_subnet']}",
                family='ipv4', cli_type=cls.data.config_cli_type
            )

            # Remove LAN IPs (from test 002)
            tc_002 = cls.data.testcases.get("002", {})
            if tc_002:
                r1_lan = tc_002.get('router1', {})
                r2_lan = tc_002.get('router2', {})
                if r1_lan:
                    ip_api.delete_ip_interface(
                        cls.data.r1, cls.data.r1_lan_port,
                        f"{r1_lan['lan_ip']}/{r1_lan['lan_subnet']}",
                        family='ipv4', cli_type=cls.data.config_cli_type
                    )
                if r2_lan:
                    ip_api.delete_ip_interface(
                        cls.data.r2, cls.data.r2_lan_port,
                        f"{r2_lan['lan_ip']}/{r2_lan['lan_subnet']}",
                        family='ipv4', cli_type=cls.data.config_cli_type
                    )

                # Remove host IPs and default routes
                h1_config = tc_002.get('host1', {})
                h2_config = tc_002.get('host2', {})
                if h1_config:
                    ip_api.delete_static_route(
                        cls.data.h1, next_hop=h1_config['gateway'], static_ip='0.0.0.0/0',
                        family='ipv4', cli_type=cls.data.config_cli_type
                    )
                    ip_api.delete_ip_interface(
                        cls.data.h1, cls.data.h1_port,
                        f"{h1_config['ip']}/{h1_config['subnet']}",
                        family='ipv4', cli_type=cls.data.config_cli_type
                    )
                if h2_config:
                    ip_api.delete_static_route(
                        cls.data.h2, next_hop=h2_config['gateway'], static_ip='0.0.0.0/0',
                        family='ipv4', cli_type=cls.data.config_cli_type
                    )
                    ip_api.delete_ip_interface(
                        cls.data.h2, cls.data.h2_port,
                        f"{h2_config['ip']}/{h2_config['subnet']}",
                        family='ipv4', cli_type=cls.data.config_cli_type
                    )

            st.log("IP addresses removed successfully")
        except Exception as e:
            st.log(f"IP address cleanup error: {e}")

    @classmethod
    def _configure_wan_interfaces(cls, tc_config: dict) -> None:
        """Configure WAN interfaces on R1 and R2 for eBGP peering."""
        st.log("Configuring WAN interfaces for eBGP")

        r1_config = tc_config.get('router1', {})
        r2_config = tc_config.get('router2', {})

        # Configure R1 WAN interface (use klish for config)
        result = ip_api.config_ip_addr_interface(
            dut=cls.data.r1,
            interface_name=cls.data.r1_wan_port,
            ip_address=r1_config['wan_ip'],
            subnet=r1_config['wan_subnet'],
            family='ipv4',
            config='add',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure WAN IP on R1 {cls.data.r1_wan_port}")

        # Configure R2 WAN interface (use klish for config)
        result = ip_api.config_ip_addr_interface(
            dut=cls.data.r2,
            interface_name=cls.data.r2_wan_port,
            ip_address=r2_config['wan_ip'],
            subnet=r2_config['wan_subnet'],
            family='ipv4',
            config='add',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure WAN IP on R2 {cls.data.r2_wan_port}")

        # Enable interfaces
        intf_api.interface_operation(
            cls.data.r1, cls.data.r1_wan_port,
            operation="startup", cli_type=cls.data.config_cli_type
        )
        intf_api.interface_operation(
            cls.data.r2, cls.data.r2_wan_port,
            operation="startup", cli_type=cls.data.config_cli_type
        )

        st.log(f"WAN interfaces configured: R1 {r1_config['wan_ip']}, R2 {r2_config['wan_ip']}")

    # Continuing in next message due to length...
    @classmethod
    def _configure_lan_interfaces(cls, tc_config: dict) -> None:
        """Configure LAN interfaces on R1 and R2 for host connectivity."""
        st.log("Configuring LAN interfaces")

        r1_config = tc_config.get('router1', {})
        r2_config = tc_config.get('router2', {})

        # Configure R1 LAN interface (use klish for config)
        result = ip_api.config_ip_addr_interface(
            dut=cls.data.r1,
            interface_name=cls.data.r1_lan_port,
            ip_address=r1_config['lan_ip'],
            subnet=r1_config['lan_subnet'],
            family='ipv4',
            config='add',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure LAN IP on R1 {cls.data.r1_lan_port}")

        # Configure R2 LAN interface (use klish for config)
        result = ip_api.config_ip_addr_interface(
            dut=cls.data.r2,
            interface_name=cls.data.r2_lan_port,
            ip_address=r2_config['lan_ip'],
            subnet=r2_config['lan_subnet'],
            family='ipv4',
            config='add',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure LAN IP on R2 {cls.data.r2_lan_port}")

        # Enable interfaces
        intf_api.interface_operation(
            cls.data.r1, cls.data.r1_lan_port,
            operation="startup", cli_type=cls.data.config_cli_type
        )
        intf_api.interface_operation(
            cls.data.r2, cls.data.r2_lan_port,
            operation="startup", cli_type=cls.data.config_cli_type
        )

        st.log(f"LAN interfaces configured: R1 {r1_config['lan_ip']}, R2 {r2_config['lan_ip']}")

    @classmethod
    def _configure_loopbacks(cls, tc_config: dict) -> None:
        """Configure loopback interfaces on R1 and R2."""
        st.log("Configuring loopback interfaces")

        r1_config = tc_config.get('router1', {})
        r2_config = tc_config.get('router2', {})

        # Configure R1 Loopback1
        result = ip_api.configure_loopback(
            dut=cls.data.r1,
            loopback_name="Loopback1",
            config='yes',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", "Failed to create Loopback1 on R1")

        result = ip_api.config_ip_addr_interface(
            dut=cls.data.r1,
            interface_name="Loopback1",
            ip_address=r1_config['loopback_ip'],
            subnet='32',
            family='ipv4',
            config='add',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure IP on R1 Loopback1")

        # Configure R2 Loopback1
        result = ip_api.configure_loopback(
            dut=cls.data.r2,
            loopback_name="Loopback1",
            config='yes',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", "Failed to create Loopback1 on R2")

        result = ip_api.config_ip_addr_interface(
            dut=cls.data.r2,
            interface_name="Loopback1",
            ip_address=r2_config['loopback_ip'],
            subnet='32',
            family='ipv4',
            config='add',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure IP on R2 Loopback1")

        st.log(f"Loopbacks configured: R1 {r1_config['loopback_ip']}, R2 {r2_config['loopback_ip']}")

    @classmethod
    def _configure_hosts(cls, tc_config: dict) -> None:
        """Configure host devices H1 and H2 with IPs and default gateways."""
        st.log("Configuring host devices")

        h1_config = tc_config.get('host1', {})
        h2_config = tc_config.get('host2', {})

        # Configure H1 interface and gateway
        result = ip_api.config_ip_addr_interface(
            dut=cls.data.h1,
            interface_name=cls.data.h1_port,
            ip_address=h1_config['ip'],
            subnet=h1_config['subnet'],
            family='ipv4',
            config='add',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure IP on H1 {cls.data.h1_port}")

        result = ip_api.create_static_route(
            dut=cls.data.h1,
            next_hop=h1_config['gateway'],
            static_ip='0.0.0.0/0',
            family='ipv4',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure default gateway on H1")

        # Configure H2 interface and gateway
        result = ip_api.config_ip_addr_interface(
            dut=cls.data.h2,
            interface_name=cls.data.h2_port,
            ip_address=h2_config['ip'],
            subnet=h2_config['subnet'],
            family='ipv4',
            config='add',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure IP on H2 {cls.data.h2_port}")

        result = ip_api.create_static_route(
            dut=cls.data.h2,
            next_hop=h2_config['gateway'],
            static_ip='0.0.0.0/0',
            family='ipv4',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure default gateway on H2")

        st.log(f"Hosts configured: H1 {h1_config['ip']}, H2 {h2_config['ip']}")

    @classmethod
    def _configure_bgp_routers(cls, tc_config: dict) -> None:
        """Configure BGP router instances on R1 and R2."""
        st.log("Configuring BGP router instances")

        r1_config = tc_config.get('router1', {})
        r2_config = tc_config.get('router2', {})

        # Configure R1 BGP router (use klish for config)
        result = bgp_api.config_bgp(
            dut=cls.data.r1,
            local_as=r1_config['bgp_asn'],
            router_id=r1_config['router_id'],
            config='yes',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure BGP on R1 (AS {r1_config['bgp_asn']})")

        # Configure R2 BGP router (use klish for config)
        result = bgp_api.config_bgp(
            dut=cls.data.r2,
            local_as=r2_config['bgp_asn'],
            router_id=r2_config['router_id'],
            config='yes',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure BGP on R2 (AS {r2_config['bgp_asn']})")

        st.log(f"BGP routers configured: R1 AS{r1_config['bgp_asn']}, R2 AS{r2_config['bgp_asn']}")

    @classmethod
    def _configure_route_maps(cls) -> None:
        """Configure route-maps for RFC 8212 compliance."""
        st.log("Configuring route-maps (PERMIT_ALL) for RFC 8212")

        # Create route-map on R1 (use klish for config)
        result = ip_api.config_route_map(
            cls.data.r1,
            route_map="PERMIT_ALL",
            config='yes',
            sequence='10',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", "Failed to create route-map PERMIT_ALL on R1")

        # Create route-map on R2 (use klish for config)
        result = ip_api.config_route_map(
            cls.data.r2,
            route_map="PERMIT_ALL",
            config='yes',
            sequence='10',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", "Failed to create route-map PERMIT_ALL on R2")

        st.log("Route-maps PERMIT_ALL configured on both routers")

    @classmethod
    def _restart_bgp_docker_if_needed(cls, dut, device_name: str) -> None:
        """
        Check for BGP docker issue and restart if needed.

        Known SONiC issue: '% No BGP neighbors found in VRF default'
        Workaround: docker restart bgp outside sonic-cli prompt

        Args:
            dut: Device under test
            device_name: Device name for logging (e.g., "R1", "R2")
        """
        st.log(f"Checking BGP status on {device_name}")

        # Execute show command in klish mode to check for error
        output = st.show(dut, "show bgp summary", type='klish', skip_tmpl=True, skip_error_check=True)

        # Check if output contains the known error message
        if isinstance(output, str) and "No BGP neighbors found in VRF default" in output:
            st.log(f"Detected BGP docker issue on {device_name}: 'No BGP neighbors found in VRF default'")
            st.log(f"Applying workaround: restarting BGP docker on {device_name}")

            # Exit klish mode to run docker command
            st.config(dut, "exit", type='klish', skip_error_check=True)
            st.config(dut, "exit", type='klish', skip_error_check=True)

            # Restart BGP docker container
            st.config(dut, "sudo docker restart bgp", type='click', skip_error_check=True)

            # Wait for BGP docker to come up
            st.log(f"Waiting 30 seconds for BGP docker to restart on {device_name}")
            st.wait(30)

            # Verify BGP is back up by checking docker status
            st.log(f"Verifying BGP docker is running on {device_name}")
            docker_status = st.show(dut, "sudo docker ps | grep bgp", type='click', skip_tmpl=True, skip_error_check=True)

            if isinstance(docker_status, str) and "bgp" in docker_status:
                st.log(f"BGP docker successfully restarted on {device_name}")
            else:
                st.warn(f"BGP docker status unclear on {device_name}, proceeding anyway")

            # Re-verify BGP is accessible
            st.log(f"Re-verifying BGP summary is accessible on {device_name}")
            output = st.show(dut, "show bgp summary", type='klish', skip_tmpl=True, skip_error_check=True)

            if isinstance(output, str) and "No BGP neighbors found in VRF default" not in output:
                st.log(f"BGP docker issue resolved on {device_name}")
            else:
                st.error(f"BGP docker issue persists on {device_name} after restart")
        else:
            st.log(f"BGP status OK on {device_name} - no docker restart needed")

    @classmethod
    def _configure_bgp_neighbors(cls, tc_config: dict) -> None:
        """Configure BGP neighbors with route-map application using direct klish commands."""
        st.log("Configuring BGP neighbors with RFC 8212 route-maps")

        r1_config = tc_config.get('router1', {})
        r2_config = tc_config.get('router2', {})

        # Configure R1 neighbor (R2) using direct klish commands
        st.log(f"Configuring BGP neighbor {r1_config['neighbor_ip']} on R1")
        commands = [
            f"router bgp {r1_config['bgp_asn']}",
            f"neighbor {r1_config['neighbor_ip']} remote-as {r1_config['remote_asn']}",
            "address-family ipv4 unicast",
            "activate",
            "route-map PERMIT_ALL in",
            "route-map PERMIT_ALL out",
            "end"
        ]
        st.config(cls.data.r1, commands, type='klish')

        # Configure R2 neighbor (R1) using direct klish commands
        st.log(f"Configuring BGP neighbor {r2_config['neighbor_ip']} on R2")
        commands = [
            f"router bgp {r2_config['bgp_asn']}",
            f"neighbor {r2_config['neighbor_ip']} remote-as {r2_config['remote_asn']}",
            "address-family ipv4 unicast",
            "activate",
            "route-map PERMIT_ALL in",
            "route-map PERMIT_ALL out",
            "end"
        ]
        st.config(cls.data.r2, commands, type='klish')

        st.log("BGP neighbors configured with route-maps on both routers")

        # Check for BGP docker issue and apply workaround if needed
        cls._restart_bgp_docker_if_needed(cls.data.r1, "R1")
        cls._restart_bgp_docker_if_needed(cls.data.r2, "R2")

    @classmethod
    def _configure_redistribution(cls, redistribute_type: str) -> None:
        """
        Configure BGP redistribution.

        Args:
            redistribute_type: Type of redistribution ('connected' or 'static')
        """
        st.log(f"Configuring BGP redistribution: {redistribute_type}")

        tc_config = cls.data.testcases.get("001", {})
        r1_asn = tc_config['router1']['bgp_asn']
        r2_asn = tc_config['router2']['bgp_asn']

        # Configure redistribution on R1 (use klish for config)
        result = bgp_api.config_bgp(
            dut=cls.data.r1,
            local_as=r1_asn,
            config='yes',
            addr_family='ipv4',
            config_type_list=['redist'],
            redistribute=redistribute_type,
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure {redistribute_type} redistribution on R1")

        # Configure redistribution on R2 (use klish for config)
        result = bgp_api.config_bgp(
            dut=cls.data.r2,
            local_as=r2_asn,
            config='yes',
            addr_family='ipv4',
            config_type_list=['redist'],
            redistribute=redistribute_type,
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure {redistribute_type} redistribution on R2")

        st.log(f"BGP {redistribute_type} redistribution configured on both routers")

    @classmethod
    def _configure_static_routes(cls, tc_config: dict) -> None:
        """Configure static routes on R1 and R2."""
        st.log("Configuring static routes for redistribution")

        r1_static = tc_config.get('router1', {}).get('static_route', {})
        r2_static = tc_config.get('router2', {}).get('static_route', {})

        # Configure R1 static route (use klish for config)
        result = ip_api.create_static_route(
            dut=cls.data.r1,
            next_hop=r1_static['next_hop'],
            static_ip=r1_static['network'],
            family='ipv4',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure static route on R1: {r1_static['network']}")

        # Configure R2 static route (use klish for config)
        result = ip_api.create_static_route(
            dut=cls.data.r2,
            next_hop=r2_static['next_hop'],
            static_ip=r2_static['network'],
            family='ipv4',
            cli_type=cls.data.config_cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure static route on R2: {r2_static['network']}")

        st.log(f"Static routes configured: R1 {r1_static['network']}, R2 {r2_static['network']}")

    @classmethod
    def _verify_bgp_session(cls, tc_config: dict) -> bool:
        """Verify BGP session is established using direct klish commands."""
        st.log("Verifying BGP session status")

        r1_config = tc_config.get('router1', {})
        r2_config = tc_config.get('router2', {})

        # Verify R1 sees R2 as neighbor using direct klish command
        st.log(f"R1: Checking BGP summary for neighbor {r1_config['neighbor_ip']}")
        output_r1 = st.show(cls.data.r1, "show bgp ipv4 unicast summary", type='klish')
        result_r1 = False
        if output_r1:
            for entry in output_r1:
                if entry.get('neighbor', '') == r1_config['neighbor_ip']:
                    state = entry.get('state', '')
                    # In klish, when Established, state shows prefix count (numeric)
                    # When not established, state shows text like "Idle", "Connect", etc.
                    if state.isdigit() or state.lower() == 'established':
                        result_r1 = True
                        st.log(f"R1: BGP neighbor {r1_config['neighbor_ip']} is Established (state={state})")
                        break

        # Additional verification using 'show bgp ipv4 unicast neighbor' for detailed state
        if not result_r1:
            st.log(f"R1: Checking detailed BGP neighbor info for {r1_config['neighbor_ip']}")
            neighbor_output_r1 = st.show(cls.data.r1,
                                         f"show bgp ipv4 unicast neighbor {r1_config['neighbor_ip']}",
                                         type='klish')
            if neighbor_output_r1:
                for entry in neighbor_output_r1:
                    bgp_state = entry.get('bgpstate', '').lower()
                    if 'established' in bgp_state:
                        result_r1 = True
                        st.log(f"R1: BGP neighbor {r1_config['neighbor_ip']} BGP State: {bgp_state}")
                        break

        if not result_r1:
            st.error(f"R1: BGP neighbor {r1_config['neighbor_ip']} not in Established state")

        # Verify R2 sees R1 as neighbor using direct klish command
        st.log(f"R2: Checking BGP summary for neighbor {r2_config['neighbor_ip']}")
        output_r2 = st.show(cls.data.r2, "show bgp ipv4 unicast summary", type='klish')
        result_r2 = False
        if output_r2:
            for entry in output_r2:
                if entry.get('neighbor', '') == r2_config['neighbor_ip']:
                    state = entry.get('state', '')
                    # In klish, when Established, state shows prefix count (numeric)
                    # When not established, state shows text like "Idle", "Connect", etc.
                    if state.isdigit() or state.lower() == 'established':
                        result_r2 = True
                        st.log(f"R2: BGP neighbor {r2_config['neighbor_ip']} is Established (state={state})")
                        break

        # Additional verification using 'show bgp ipv4 unicast neighbor' for detailed state
        if not result_r2:
            st.log(f"R2: Checking detailed BGP neighbor info for {r2_config['neighbor_ip']}")
            neighbor_output_r2 = st.show(cls.data.r2,
                                         f"show bgp ipv4 unicast neighbor {r2_config['neighbor_ip']}",
                                         type='klish')
            if neighbor_output_r2:
                for entry in neighbor_output_r2:
                    bgp_state = entry.get('bgpstate', '').lower()
                    if 'established' in bgp_state:
                        result_r2 = True
                        st.log(f"R2: BGP neighbor {r2_config['neighbor_ip']} BGP State: {bgp_state}")
                        break

        if not result_r2:
            st.error(f"R2: BGP neighbor {r2_config['neighbor_ip']} not in Established state")

        if result_r1 and result_r2:
            st.log("BGP sessions established on both routers")
            return True
        else:
            st.error("BGP session verification failed")
            return False

    @classmethod
    def _verify_bgp_redistributed_routes(cls, tc_config: dict, route_type: str) -> bool:
        """
        Verify redistributed routes appear in BGP table with correct next-hop.
        Uses 'show bgp ipv4 unicast' to verify routes and next-hop values.

        Args:
            tc_config: Test case configuration
            route_type: Type of routes ('connected' or 'static')
        """
        st.log(f"Verifying BGP {route_type} redistributed routes with next-hop validation")

        verification = tc_config.get('verification', {})

        if route_type == 'connected':
            # Get expected routes from YAML verification section
            r1_expected_routes = verification.get('router1_learned_routes', [])
            r2_expected_routes = verification.get('router2_learned_routes', [])
            r1_expected_next_hop = verification.get('next_hop_r1', '')
            r2_expected_next_hop = verification.get('next_hop_r2', '')

            if not r1_expected_routes or not r2_expected_routes:
                st.error("router1_learned_routes or router2_learned_routes not defined in YAML")
                return False

            # Verify R1 learned routes from R2 with correct next-hop
            st.log(f"R1: Verifying routes {r1_expected_routes} with next-hop {r1_expected_next_hop}")
            result_r1 = True
            for route in r1_expected_routes:
                route_check = bgp_api.verify_bgp_rib(
                    dut=cls.data.r1,
                    network=route,
                    next_hop=r1_expected_next_hop,
                    cli_type='klish'
                )
                if not route_check:
                    st.error(f"R1: Route {route} with next-hop {r1_expected_next_hop} not found")
                    result_r1 = False
                else:
                    st.log(f"R1: Route {route} verified with next-hop {r1_expected_next_hop}")

            # Verify R2 learned routes from R1 with correct next-hop
            st.log(f"R2: Verifying routes {r2_expected_routes} with next-hop {r2_expected_next_hop}")
            result_r2 = True
            for route in r2_expected_routes:
                route_check = bgp_api.verify_bgp_rib(
                    dut=cls.data.r2,
                    network=route,
                    next_hop=r2_expected_next_hop,
                    cli_type='klish'
                )
                if not route_check:
                    st.error(f"R2: Route {route} with next-hop {r2_expected_next_hop} not found")
                    result_r2 = False
                else:
                    st.log(f"R2: Route {route} verified with next-hop {r2_expected_next_hop}")

            result = result_r1 and result_r2

        elif route_type == 'static':
            # Get expected static routes from YAML verification section
            r1_expected_static = verification.get('router1_learned_static', '')
            r2_expected_static = verification.get('router2_learned_static', '')
            r1_expected_next_hop = verification.get('next_hop_r1', '')
            r2_expected_next_hop = verification.get('next_hop_r2', '')

            if not r1_expected_static or not r2_expected_static:
                st.error("router1_learned_static or router2_learned_static not defined in YAML")
                return False

            # Verify R1 learned R2's static route with correct next-hop
            st.log(f"R1: Verifying static route {r1_expected_static} with next-hop {r1_expected_next_hop}")
            result_r1 = bgp_api.verify_bgp_rib(
                dut=cls.data.r1,
                network=r1_expected_static,
                next_hop=r1_expected_next_hop,
                cli_type='klish'
            )
            if not result_r1:
                st.error(f"R1: Static route {r1_expected_static} with next-hop {r1_expected_next_hop} not found")
            else:
                st.log(f"R1: Static route {r1_expected_static} verified with next-hop {r1_expected_next_hop}")

            # Verify R2 learned R1's static route with correct next-hop
            st.log(f"R2: Verifying static route {r2_expected_static} with next-hop {r2_expected_next_hop}")
            result_r2 = bgp_api.verify_bgp_rib(
                dut=cls.data.r2,
                network=r2_expected_static,
                next_hop=r2_expected_next_hop,
                cli_type='klish'
            )
            if not result_r2:
                st.error(f"R2: Static route {r2_expected_static} with next-hop {r2_expected_next_hop} not found")
            else:
                st.log(f"R2: Static route {r2_expected_static} verified with next-hop {r2_expected_next_hop}")

            result = result_r1 and result_r2

        if result:
            st.log(f"BGP {route_type} route verification passed with next-hop validation")
            return True
        else:
            st.error(f"BGP {route_type} route verification failed")
            return False

    @classmethod
    def _verify_ip_routes(cls, tc_config: dict, route_type: str) -> bool:
        """
        Verify redistributed routes installed in IP routing table (use click for show commands).

        Args:
            tc_config: Test case configuration
            route_type: Type of routes ('connected' or 'static')
        """
        st.log(f"Verifying IP routing table for {route_type} routes")

        if route_type == 'connected':
            # R1 should have R2's LAN route (use click for show)
            r2_lan_prefix = tc_config['router2']['lan_network']
            #.split('/')[0]
            result_r1 = ip_api.verify_ip_route(
                dut=cls.data.r1,
                ip_address=r2_lan_prefix,
                type='B',  # BGP routes marked with 'B'
                cli_type=cls.data.show_cli_type
            )

            # R2 should have R1's LAN route (use click for show)
            r1_lan_prefix = tc_config['router1']['lan_network']
            #.split('/')[0]
            result_r2 = ip_api.verify_ip_route(
                dut=cls.data.r2,
                ip_address=r1_lan_prefix,
                type='B',
                cli_type=cls.data.show_cli_type
            )

            result = result_r1 and result_r2

        elif route_type == 'static':
            # R1 should have R2's static route (use click for show)
            r2_static_prefix = tc_config['router2']['static_route']['network']
            #.split('/')[0]
            result_r1 = ip_api.verify_ip_route(
                dut=cls.data.r1,
                ip_address=r2_static_prefix,
                type='B',
                cli_type=cls.data.show_cli_type
            )

            # R2 should have R1's static route (use click for show)
            r1_static_prefix = tc_config['router1']['static_route']['network']
            #.split('/')[0]
            result_r2 = ip_api.verify_ip_route(
                dut=cls.data.r2,
                ip_address=r1_static_prefix,
                type='B',
                cli_type=cls.data.show_cli_type
            )

            result = result_r1 and result_r2

        if result:
            st.log(f"IP route verification for {route_type} routes passed")
            return True
        else:
            st.error(f"IP route verification for {route_type} routes failed")
            return False

    @classmethod
    def _verify_traffic_host_to_host(cls, tc_config: dict) -> bool:
        """Verify bidirectional connectivity between H1 and H2 using ping."""
        st.log("Verifying host-to-host connectivity (H1 ↔ H2)")

        h1_config = tc_config.get('host1', {})
        h2_config = tc_config.get('host2', {})

        # Ping from H1 to H2 (use click for show)
        st.log(f"Ping from H1 ({h1_config['ip']}) to H2 ({h2_config['ip']})")
        result_h1_to_h2 = ip_api.ping(
            dut=cls.data.h1,
            addresses=h2_config['ip'],
            count=5,
            cli_type=cls.data.show_cli_type
        )

        # Ping from H2 to H1 (use click for show)
        st.log(f"Ping from H2 ({h2_config['ip']}) to H1 ({h1_config['ip']})")
        result_h2_to_h1 = ip_api.ping(
            dut=cls.data.h2,
            addresses=h1_config['ip'],
            count=5,
            cli_type=cls.data.show_cli_type
        )

        if result_h1_to_h2 and result_h2_to_h1:
            st.log("Host-to-host traffic verification passed")
            return True
        else:
            st.error("Host-to-host traffic verification failed")
            return False

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_eBGP_Redist_TC001"])
    def test_001_bgp_ebgp_base_configuration(self) -> None:
        """
        TC 001: Establish base eBGP session.
        Configures WAN interfaces, BGP neighbors, and route-maps for RFC 8212.
        """
        st.banner("TEST 001: BGP eBGP Base Configuration")

        tc_config = self.data.testcases.get("001", {})
        if not tc_config:
            st.report_fail("msg", "Test case 001 configuration not found in YAML")

        # Step 1: Configure WAN interfaces
        self._configure_wan_interfaces(tc_config)

        # Step 2: Configure BGP instances
        self._configure_bgp_routers(tc_config)

        # Step 3: Configure route-maps (RFC 8212)
        self._configure_route_maps()

        # Step 4: Configure BGP neighbors with route-maps
        self._configure_bgp_neighbors(tc_config)

        # Step 5: Wait for BGP session to establish
        st.wait(10, "Waiting for BGP session to establish")

        # Step 6: Verify BGP session established
        if not st.poll_wait(
            self._verify_bgp_session,
            self.data.verify_timeout,
            tc_config
        ):
            st.report_tc_fail(TC_IDS.base_ebgp, "bgp_session_not_established",
                              "BGP session failed to reach Established state")
            st.report_fail("test_case_failed")

        st.report_tc_pass(TC_IDS.base_ebgp, "bgp_session_established",
                          "BGP eBGP session established successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_eBGP_Redist_TC002"])
    @pytest.mark.depends(on="test_001_bgp_ebgp_base_configuration")
    def test_002_bgp_connected_route_redistribution(self) -> None:
        """
        TC 002: Validate connected route redistribution.
        Configures LAN interfaces, loopbacks, hosts, and redistributes connected routes.
        """
        st.banner("TEST 002: BGP Connected Route Redistribution")

        tc_config = self.data.testcases.get("002", {})
        if not tc_config:
            st.report_fail("msg", "Test case 002 configuration not found in YAML")

        # Step 1: Configure LAN interfaces and loopbacks
        self._configure_lan_interfaces(tc_config)
        self._configure_loopbacks(tc_config)

        # Step 2: Configure host devices
        self._configure_hosts(tc_config)

        # Step 3: Enable connected route redistribution
        self._configure_redistribution(redistribute_type='connected')

        # Step 4: Wait for route redistribution to propagate
        st.wait(10, "Waiting for connected routes to be redistributed")

        # Step 5: Verify redistributed routes in BGP
        if not st.poll_wait(
            self._verify_bgp_redistributed_routes,
            self.data.verify_timeout,
            tc_config,
            'connected'
        ):
            st.report_tc_fail(TC_IDS.connected_redist, "bgp_routes_not_learned",
                              "Connected routes not learned via BGP")
            st.report_fail("test_case_failed")

        # Step 6: Verify routes in IP routing table
        if not st.poll_wait(
            self._verify_ip_routes,
            self.data.verify_timeout,
            tc_config,
            'connected'
        ):
            st.report_tc_fail(TC_IDS.connected_redist, "routes_not_installed",
                              "Connected routes not installed in routing table")
            st.report_fail("test_case_failed")

        # Step 7: Verify end-to-end traffic (H1 ↔ H2)
        if not self._verify_traffic_host_to_host(tc_config):
            st.report_tc_fail(TC_IDS.connected_redist, "traffic_verification_failed",
                              "Host-to-host traffic verification failed")
            st.report_fail("test_case_failed")

        st.report_tc_pass(TC_IDS.connected_redist, "connected_redistribution_passed",
                          "Connected route redistribution verified successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_eBGP_Redist_TC003"])
    @pytest.mark.depends(on="test_002_bgp_connected_route_redistribution")
    def test_003_bgp_static_route_redistribution(self) -> None:
        """
        TC 003: Validate static route redistribution.
        Configures static routes and redistributes them into BGP.
        """
        st.banner("TEST 003: BGP Static Route Redistribution")

        tc_config = self.data.testcases.get("003", {})
        if not tc_config:
            st.report_fail("msg", "Test case 003 configuration not found in YAML")

        # Step 1: Configure static routes
        self._configure_static_routes(tc_config)

        # Step 2: Enable static route redistribution
        self._configure_redistribution(redistribute_type='static')

        # Step 3: Wait for route redistribution to propagate
        st.wait(10, "Waiting for static routes to be redistributed")

        # Step 4: Verify redistributed static routes in BGP
        if not st.poll_wait(
            self._verify_bgp_redistributed_routes,
            self.data.verify_timeout,
            tc_config,
            'static'
        ):
            st.report_tc_fail(TC_IDS.static_redist, "bgp_static_routes_not_learned",
                              "Static routes not learned via BGP")
            st.report_fail("test_case_failed")

        # Step 5: Verify static routes in IP routing table
        if not st.poll_wait(
            self._verify_ip_routes,
            self.data.verify_timeout,
            tc_config,
            'static'
        ):
            st.report_tc_fail(TC_IDS.static_redist, "static_routes_not_installed",
                              "Static routes not installed in routing table")
            st.report_fail("test_case_failed")

        st.report_tc_pass(TC_IDS.static_redist, "static_redistribution_passed",
                          "Static route redistribution verified successfully")
        st.report_pass("test_case_passed")
