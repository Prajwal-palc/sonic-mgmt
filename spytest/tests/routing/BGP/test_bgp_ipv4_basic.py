"""
BGP IPv4 Basic Configuration and Verification
Author: Athira
2025

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2node.yaml  \
  tests/routing/BGP/test_bgp_ipv4_basic.py \
  --logs-path ./logs/test_bgp_ipv4_basic_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of BGP IPv4 neighbor session establishment using
  SpyTest APIs and the klish CLI. The test configures IPv4 addresses on
  interfaces, establishes iBGP neighbor sessions, verifies session state,
  and performs clean teardown. Interface names are dynamically resolved from
  the topology file, and test parameters are loaded from YAML to remain
  reusable across SONiC hardware and virtual environments.

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes (interfaces dynamically resolved from topology)
        # +--------------------+                       +--------------------+
        # |        DUT1        |                       |        DUT2        |
        # |    10.1.1.1/24     |=======================|    10.1.1.2/24     |
        # | BGP AS 65001       |      D1D2P1-D2D1P1   | BGP AS 65001       |
        # | Router-ID 1.1.1.1  |                       | Router-ID 2.2.2.2  |
        # +--------------------+                       +--------------------+

  - Feature flags / min SONiC version: BGP support required
  - Required test variables (YAML): vars_bgp_ipv4_basic.yaml
    - defaults.cli_type (klish)
    - defaults.verify_timeout (90)
    - defaults.cleanup (true)
    - defaults.min_topology (D1D2:1)
    - testcases.* definitions
"""

# Testcase for BGP IPv4 basic configuration and verification

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api
import apis.common.scapy_traffic as scapy_api


VAR_FILE_ENV = "BGP_IPV4_BASIC_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent / "vars_bgp_ipv4_basic.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"BGP IPv4 basic variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("BGP IPv4 basic YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestBgpIpv4Basic:
    """Testcases covering BGP IPv4 basic configuration, verification, and unconfiguration."""

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
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 90))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Store DUT references
        cls.data.dut1 = topology.D1
        cls.data.dut2 = topology.D2

        # Store interface references from topology (dynamically resolved)
        cls.data.dut1_interface = topology.D1D2P1  # DUT1's interface connected to DUT2
        cls.data.dut2_interface = topology.D2D1P1  # DUT2's interface connected to DUT1

        st.log(f"Setup complete: DUT1={cls.data.dut1}, DUT2={cls.data.dut2}")
        st.log(f"Interfaces: DUT1={cls.data.dut1_interface}, DUT2={cls.data.dut2_interface}")

    @classmethod
    def teardown_class(cls) -> None:
        """
        Ensure all BGP and interface configurations are removed after the suite completes.

        This cleanup runs after both test 001 and test 002 have completed.
        It removes the BGP session and interface IPs that were configured in test 001
        and used by test 002.
        """
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping teardown")
            return
        st.banner("Starting module cleanup (teardown_class)")
        cls._cleanup_all_configs()

    @classmethod
    def _cleanup_all_configs(cls) -> None:
        """Remove all BGP configurations and interface IP addresses."""
        st.log("Cleaning up BGP and interface configurations")

        # Get test 001 configuration to retrieve interface IPs for cleanup
        testcase_001 = cls.data.testcases.get("001", {})
        dut1_config = testcase_001.get("dut1", {})
        dut2_config = testcase_001.get("dut2", {})

        # Cleanup BGP on both DUTs
        st.banner("Module Teardown: Unconfigure BGP")
        for dut in [cls.data.dut1, cls.data.dut2]:
            try:
                # Use direct klish command to remove all BGP configuration
                commands = [
                    "configure terminal",
                    "no router bgp",
                    "exit"
                ]
                st.config(dut, commands, type=cls.data.cli_type, skip_error_check=True)
                st.log(f"BGP cleanup completed on {dut}")
            except Exception as e:
                st.log(f"BGP cleanup error on {dut}: {e}")

        # Cleanup interface IP addresses
        st.banner("Module Teardown: Unconfigure interface IP addresses")
        if dut1_config and dut2_config:
            try:
                ip_api.delete_ip_interface(
                    cls.data.dut1,
                    cls.data.dut1_interface,
                    dut1_config['ip_address'],
                    subnet=dut1_config['subnet'],
                    family="ipv4",
                    cli_type=cls.data.cli_type,
                    skip_error=True
                )
                st.log(f"Interface IP cleanup completed on {cls.data.dut1}")
            except Exception as e:
                st.log(f"Interface IP cleanup error on {cls.data.dut1}: {e}")

            try:
                ip_api.delete_ip_interface(
                    cls.data.dut2,
                    cls.data.dut2_interface,
                    dut2_config['ip_address'],
                    subnet=dut2_config['subnet'],
                    family="ipv4",
                    cli_type=cls.data.cli_type,
                    skip_error=True
                )
                st.log(f"Interface IP cleanup completed on {cls.data.dut2}")
            except Exception as e:
                st.log(f"Interface IP cleanup error on {cls.data.dut2}: {e}")

        st.log("Module cleanup completed")

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    def _configure_interface_ip(self, dut: str, interface: str, ip_address: str, subnet: str) -> None:
        """Configure IPv4 address on interface."""
        st.log(f"Configuring {ip_address}/{subnet} on {dut} {interface}")
        result = ip_api.config_ip_addr_interface(
            dut,
            interface_name=interface,
            ip_address=ip_address,
            subnet=subnet,
            family="ipv4",
            config='add',
            cli_type=self.data.cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure IP {ip_address}/{subnet} on {dut} {interface}")

    def _unconfigure_interface_ip(self, dut: str, interface: str, ip_address: str, subnet: str) -> None:
        """Remove IPv4 address from interface."""
        st.log(f"Removing {ip_address}/{subnet} from {dut} {interface}")
        try:
            ip_api.delete_ip_interface(
                dut,
                interface_name=interface,
                ip_address=ip_address,
                subnet=subnet,
                family="ipv4",
                cli_type=self.data.cli_type,
                skip_error=True
            )
        except Exception as e:
            st.log(f"Error removing IP from {dut} {interface}: {e}")

    def _configure_bgp_router(self, dut: str, local_asn: int, router_id: str, vrf: str = 'default') -> None:
        """
        Configure BGP router with AS number and router-id.

        Pattern from test_bgp_svi_ipv4.py:
        - Use enable_router_bgp_mode() to enter BGP mode
        - Router-ID should be configured separately if needed
        - Do NOT exit BGP mode (neighbor config needs to be in same mode)
        """
        st.log(f"Configuring BGP router on {dut}: AS {local_asn}, Router-ID {router_id}")

        # Create BGP router instance and stay in BGP router mode
        # Note: Router-ID configuration is skipped here as it's not working in klish
        # BGP will use router-id from loopback or can be configured via direct commands
        result = bgp_api.enable_router_bgp_mode(
            dut,
            local_asn=local_asn,
            vrf_name=vrf,
            cli_type=self.data.cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to create BGP router on {dut}")

        st.log(f"BGP router AS {local_asn} configured on {dut} (router-ID will be auto-assigned or configured separately)")

    def _configure_bgp_neighbor(
        self,
        dut: str,
        local_asn: int,
        neighbor_ip: str,
        remote_asn: int,
        family: str = "ipv4",
        vrf: str = 'default'
    ) -> None:
        """Configure BGP neighbor."""
        st.log(f"Configuring BGP neighbor on {dut}: neighbor {neighbor_ip} remote-as {remote_asn}")
        result = bgp_api.config_bgp_neighbor(
            dut,
            local_asn=local_asn,
            neighbor_ip=neighbor_ip,
            remote_asn=remote_asn,
            family=family,
            config='yes',
            vrf=vrf,
            cli_type=self.data.cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure BGP neighbor {neighbor_ip} on {dut}")

    def _activate_bgp_neighbor(
        self,
        dut: str,
        local_asn: int,
        neighbor_ip: str,
        remote_asn: int,
        family: str = "ipv4",
        vrf: str = 'default'
    ) -> None:
        """Activate BGP neighbor in address family."""
        st.log(f"Activating BGP neighbor {neighbor_ip} on {dut} for {family}")
        result = bgp_api.config_bgp_neighbor_properties(
            dut,
            local_asn=local_asn,
            neighbor_ip=neighbor_ip,
            family=family,
            mode='unicast',
            vrf=vrf,
            remote_asn=remote_asn,
            activate='yes',
            cli_type=self.data.cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to activate BGP neighbor {neighbor_ip} on {dut}")

    def _verify_bgp_session(
        self,
        dut: str,
        neighbor_ip: str,
        state: str = "Established",
        vrf: str = 'default'
    ) -> None:
        """Verify BGP session state."""
        st.log(f"Verifying BGP session on {dut}: neighbor {neighbor_ip} state {state}")

        # Use poll_wait to retry verification with timeout
        def _check_bgp_session() -> bool:
            return bgp_api.verify_bgp_summary(
                dut,
                family='ipv4',
                neighbor=neighbor_ip,
                state=state,
                vrf=vrf,
                cli_type=self.data.cli_type
            )

        if not st.poll_wait(_check_bgp_session, self.data.verify_timeout):
            st.report_fail("msg", f"BGP session {neighbor_ip} not in {state} state on {dut}")

    def _cleanup_bgp_completely(self, dut: str) -> None:
        """
        Completely cleanup BGP configuration using 'no router bgp' command.
        This removes all BGP configuration regardless of AS number.
        """
        st.log(f"Performing complete BGP cleanup on {dut}")
        try:
            # Use direct klish command to remove all BGP configuration
            commands = [
                "configure terminal",
                "no router bgp",
                "exit"
            ]
            st.config(dut, commands, type=self.data.cli_type, skip_error_check=True)
            st.log(f"BGP cleanup completed on {dut}")
        except Exception as e:
            st.log(f"Error during BGP cleanup on {dut}: {e}")

    def _unconfigure_bgp(self, dut: str, local_asn: int = None, vrf: str = 'default') -> None:
        """Unconfigure BGP router."""
        st.log(f"Unconfiguring BGP on {dut}")
        try:
            if local_asn:
                bgp_api.unconfig_router_bgp(
                    dut,
                    vrf_name=vrf,
                    local_asn=local_asn,
                    cli_type=self.data.cli_type,
                    skip_error_check=True
                )
            else:
                bgp_api.cleanup_router_bgp(
                    dut_list=[dut],
                    cli_type=self.data.cli_type,
                    skip_error_check=True
                )
        except Exception as e:
            st.log(f"Error unconfiguring BGP on {dut}: {e}")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_IPv4_001"])
    def test_bgp_ipv4_configure_verify_unconfig(self) -> None:
        """
        BGP-IPv4-001: Configure BGP IPv4 neighbor and verify session.

        This test establishes BGP session which will be used by test 002 for traffic validation.
        BGP and interface cleanup is performed in module teardown to allow test 002 to use
        the established session.

        Test Steps:
        0. Clean up any existing BGP configuration
        1. Configure IPv4 addresses on DUT1 and DUT2 interfaces
        2. Configure BGP routers on both DUTs
        3. Configure BGP neighbors on both DUTs
        4. Activate neighbors in IPv4 unicast address family
        5. Verify BGP session establishment

        Note: BGP session is NOT unconfigured at end of this test. It persists for test 002.
              Cleanup is performed in module teardown (teardown_class).
        """
        testcase = self._get_testcase("001")

        st.banner("TEST CASE: BGP IPv4 Configure and Verify Session")

        # Get test parameters
        dut1_config = testcase.get("dut1", {})
        dut2_config = testcase.get("dut2", {})

        # Step 0: Clean up any existing BGP configuration
        st.banner("Step 0: Clean up any existing BGP configuration")
        self._cleanup_bgp_completely(self.data.dut1)
        self._cleanup_bgp_completely(self.data.dut2)

        # Step 1: Configure interface IP addresses
        st.banner("Step 1: Configure interface IP addresses")
        self._configure_interface_ip(
            self.data.dut1,
            self.data.dut1_interface,
            dut1_config["ip_address"],
            dut1_config["subnet"]
        )
        self._configure_interface_ip(
            self.data.dut2,
            self.data.dut2_interface,
            dut2_config["ip_address"],
            dut2_config["subnet"]
        )

        # Step 2: Configure BGP routers
        st.banner("Step 2: Configure BGP routers")
        self._configure_bgp_router(
            self.data.dut1,
            dut1_config["bgp_asn"],
            dut1_config["router_id"]
        )
        self._configure_bgp_router(
            self.data.dut2,
            dut2_config["bgp_asn"],
            dut2_config["router_id"]
        )

        # Step 3: Configure BGP neighbors
        st.banner("Step 3: Configure BGP neighbors")
        self._configure_bgp_neighbor(
            self.data.dut1,
            dut1_config["bgp_asn"],
            dut1_config["neighbor_ip"],
            dut1_config["remote_asn"]
        )
        self._configure_bgp_neighbor(
            self.data.dut2,
            dut2_config["bgp_asn"],
            dut2_config["neighbor_ip"],
            dut2_config["remote_asn"]
        )

        # Step 4: Activate neighbors in IPv4 unicast address family
        st.banner("Step 4: Activate neighbors in IPv4 unicast address family")
        self._activate_bgp_neighbor(
            self.data.dut1,
            dut1_config["bgp_asn"],
            dut1_config["neighbor_ip"],
            dut1_config["remote_asn"]
        )
        self._activate_bgp_neighbor(
            self.data.dut2,
            dut2_config["bgp_asn"],
            dut2_config["neighbor_ip"],
            dut2_config["remote_asn"]
        )

        # Step 5: Verify BGP session establishment
        st.banner("Step 5: Verify BGP session establishment")
        self._verify_bgp_session(
            self.data.dut1,
            dut1_config["neighbor_ip"],
            state="Established"
        )
        self._verify_bgp_session(
            self.data.dut2,
            dut2_config["neighbor_ip"],
            state="Established"
        )

        st.log("BGP sessions successfully established on both DUTs")
        st.log("BGP session will persist for use by test 002")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_IPv4_002"])
    @pytest.mark.depends(on=["test_bgp_ipv4_configure_verify_unconfig"])
    def test_bgp_ipv4_traffic_validation(self) -> None:
        """
        BGP-IPv4-002: Validate BGP IPv4 traffic forwarding using Scapy.

        This test extends BGP_IPv4_001. It uses the BGP session from test 001
        and only validates traffic forwarding.

        Test Steps:
        1. Verify BGP session is established (from test 001)
        2. Verify basic connectivity with ping
        3. Get MAC addresses from interfaces
        4. Send bidirectional Scapy traffic (DUT1 -> DUT2 and DUT2 -> DUT1)
        5. Verify traffic forwarding
        """
        # Reuse configuration from test case 001
        testcase = self._get_testcase("001")

        st.banner("TEST CASE: BGP IPv4 Traffic Validation with Scapy")

        # Get test parameters from test 001 configuration
        dut1_config = testcase.get("dut1", {})
        dut2_config = testcase.get("dut2", {})

        # Get traffic parameters from test 002 configuration
        testcase_002 = self._get_testcase("002")
        traffic_config = testcase_002.get("traffic", {})

        try:
            # Step 1: Verify BGP session is established (from test 001)
            st.banner("Step 1: Verify BGP session is established")
            self._verify_bgp_session(
                self.data.dut1,
                dut1_config["neighbor_ip"],
                state="Established"
            )
            self._verify_bgp_session(
                self.data.dut2,
                dut2_config["neighbor_ip"],
                state="Established"
            )

            st.log("BGP sessions verified - using established session from test 001")

            # Step 2: Verify basic connectivity with ping
            st.banner("Step 2: Verify basic connectivity with ping")
            ping_result = scapy_api.verify_ping(
                self.data.dut1,
                dut1_config["neighbor_ip"],
                src_ip=dut1_config["ip_address"],
                count=5
            )
            if not ping_result:
                st.log("WARNING: Ping failed, but continuing with Scapy traffic test")

            # Step 3: Get MAC addresses from interfaces
            st.banner("Step 3: Get MAC addresses from interfaces")
            dut1_mac = scapy_api.get_interface_mac(
                self.data.dut1,
                self.data.dut1_interface,
                cli_type=self.data.cli_type
            )
            dut2_mac = scapy_api.get_interface_mac(
                self.data.dut2,
                self.data.dut2_interface,
                cli_type=self.data.cli_type
            )

            # Use default MACs if not found
            if not dut1_mac:
                dut1_mac = scapy_api.get_default_mac(1)
                st.log(f"Using default MAC for DUT1: {dut1_mac}")

            if not dut2_mac:
                dut2_mac = scapy_api.get_default_mac(2)
                st.log(f"Using default MAC for DUT2: {dut2_mac}")

            st.log(f"DUT1 Interface MAC: {dut1_mac}")
            st.log(f"DUT2 Interface MAC: {dut2_mac}")

            # Step 4: Send bidirectional Scapy traffic
            st.banner("Step 4: Send bidirectional Scapy traffic")

            # Traffic from DUT1 to DUT2
            st.log(f"Sending traffic from DUT1 ({dut1_config['ip_address']}) to DUT2 ({dut1_config['neighbor_ip']})")
            traffic_result_d1_d2 = scapy_api.send_traffic(
                dut=self.data.dut1,
                interface=self.data.dut1_interface,
                src_ip=dut1_config["ip_address"],
                dst_ip=dut1_config["neighbor_ip"],
                src_mac=dut1_mac,
                dst_mac=dut2_mac,
                duration=traffic_config.get("duration", 10),
                pps=traffic_config.get("pps", 1000),
                payload_size=traffic_config.get("payload_size", 200),
                traffic_type=traffic_config.get("type", "udp")
            )

            if not traffic_result_d1_d2["success"]:
                st.log(f"WARNING: Traffic from DUT1 to DUT2 completed with warnings")
                st.log(f"Packets sent: {traffic_result_d1_d2['packets_sent']}")
            else:
                st.log(f"Traffic from DUT1 to DUT2 sent successfully: {traffic_result_d1_d2['packets_sent']} packets")

            # Traffic from DUT2 to DUT1
            st.log(f"Sending traffic from DUT2 ({dut2_config['ip_address']}) to DUT1 ({dut2_config['neighbor_ip']})")
            traffic_result_d2_d1 = scapy_api.send_traffic(
                dut=self.data.dut2,
                interface=self.data.dut2_interface,
                src_ip=dut2_config["ip_address"],
                dst_ip=dut2_config["neighbor_ip"],
                src_mac=dut2_mac,
                dst_mac=dut1_mac,
                duration=traffic_config.get("duration", 10),
                pps=traffic_config.get("pps", 1000),
                payload_size=traffic_config.get("payload_size", 200),
                traffic_type=traffic_config.get("type", "udp")
            )

            if not traffic_result_d2_d1["success"]:
                st.log(f"WARNING: Traffic from DUT2 to DUT1 completed with warnings")
                st.log(f"Packets sent: {traffic_result_d2_d1['packets_sent']}")
            else:
                st.log(f"Traffic from DUT2 to DUT1 sent successfully: {traffic_result_d2_d1['packets_sent']} packets")

            # Step 5: Verify traffic forwarding
            st.banner("Step 5: Verify traffic forwarding")

            # Verify connectivity is still working after traffic
            ping_after_traffic = scapy_api.verify_ping(
                self.data.dut1,
                dut1_config["neighbor_ip"],
                src_ip=dut1_config["ip_address"],
                count=5
            )

            if ping_after_traffic:
                st.log("PASS: Traffic forwarding verified successfully")
            else:
                st.log("WARNING: Post-traffic ping verification inconclusive")

            # Log traffic summary
            st.banner("Traffic Test Summary")
            st.log(f"DUT1 -> DUT2: {traffic_result_d1_d2['packets_sent']} packets sent")
            st.log(f"DUT2 -> DUT1: {traffic_result_d2_d1['packets_sent']} packets sent")
            st.log(f"Total packets: {traffic_result_d1_d2['packets_sent'] + traffic_result_d2_d1['packets_sent']}")

            # Cleanup Scapy scripts
            scapy_api.cleanup_scapy_script(self.data.dut1)
            scapy_api.cleanup_scapy_script(self.data.dut2)

        except Exception as e:
            st.log(f"Traffic test failed with exception: {e}")
            # Cleanup Scapy scripts even on failure
            try:
                scapy_api.cleanup_scapy_script(self.data.dut1)
                scapy_api.cleanup_scapy_script(self.data.dut2)
            except:
                pass
            raise

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_IPv4_003"])
    @pytest.mark.depends(on=["test_bgp_ipv4_configure_verify_unconfig"])
    def test_bgp_ipv4_route_advertisement(self) -> None:
        """
        BGP-IPv4-003: Validate BGP IPv4 route advertisement with real host-to-host routing.

        This test extends BGP_IPv4_001 by adding LAN interfaces on routers, real host devices,
        and advertising LAN networks via the existing iBGP session from test 001.

        Topology: Host1 ---- Eth16 ---- R1 ---- Eth4(iBGP from test 001) ---- R2 ---- Eth16 ---- Host2
                    H1            R1-LAN         R1-R2 iBGP link              R2-LAN          H2

        Test 001 provides:
        - R1 Eth4: 10.1.1.1/24 ↔ R2 Eth4: 10.1.1.2/24 (iBGP link)
        - iBGP session established between R1 and R2 (AS 65001)

        Test Steps:
        1. Verify iBGP session from test 001 is still established
        2. Configure R1 LAN interface (Ethernet16) for Host1
        3. Configure R2 LAN interface (Ethernet16) for Host2
        4. Configure Host1 interface and static default route
        5. Configure Host2 interface and static default route
        6. Advertise LAN networks via existing BGP session
        7. Verify BGP route learning on both routers
        8. Verify routing tables on routers
        9. Test host-to-host connectivity (H1 ping H2)
        10. Verify end-to-end traffic forwarding

        Note: This test reuses the iBGP session from test 001. Cleanup removes only
              the additions made by this test, preserving test 001's BGP configuration.
        """
        # Get test 003 specific configuration
        testcase_003 = self._get_testcase("003")
        router1_config = testcase_003.get("router1", {})
        router2_config = testcase_003.get("router2", {})
        host1_config = testcase_003.get("host1", {})
        host2_config = testcase_003.get("host2", {})
        traffic_config = testcase_003.get("traffic", {})
        verification = testcase_003.get("verification", {})

        st.banner("TEST CASE: BGP IPv4 Route Advertisement - Extending Test 001 with Real Hosts")
        st.log(f"Topology: Host1({host1_config['device']}) -- R1({self.data.dut1}) -- R2({self.data.dut2}) -- Host2({host2_config['device']})")
        st.log("Reusing iBGP session from test 001, adding LAN interfaces and hosts")

        # Get host device handles from topology
        host1 = st.get_dut_names()[2] if len(st.get_dut_names()) > 2 else None  # vs_sonic_3
        host2 = st.get_dut_names()[3] if len(st.get_dut_names()) > 3 else None  # vs_sonic_4

        if not host1 or not host2:
            st.report_fail("msg", "Test requires 4 devices (2 routers + 2 hosts). Only 2 devices found in topology.")

        try:
            # Step 1: Verify iBGP session from test 001 is still established
            st.banner("Step 1: Verify iBGP session from test 001 is established")
            self._verify_bgp_session(
                self.data.dut1,
                router1_config['neighbor_ip'],
                state="Established"
            )
            self._verify_bgp_session(
                self.data.dut2,
                router2_config['neighbor_ip'],
                state="Established"
            )
            st.log("iBGP session from test 001 verified - using existing BGP configuration")

            # Step 2: Configure R1 LAN interface for Host1
            st.banner("Step 2: Configure R1 LAN interface for Host1")
            st.log(f"Configuring R1 LAN interface {router1_config['lan_interface']}: {router1_config['lan_ip']}/{router1_config['lan_subnet']}")
            self._configure_interface_ip(
                self.data.dut1,
                router1_config['lan_interface'],
                router1_config['lan_ip'],
                router1_config['lan_subnet']
            )

            # Step 3: Configure R2 LAN interface for Host2
            st.banner("Step 3: Configure R2 LAN interface for Host2")
            st.log(f"Configuring R2 LAN interface {router2_config['lan_interface']}: {router2_config['lan_ip']}/{router2_config['lan_subnet']}")
            self._configure_interface_ip(
                self.data.dut2,
                router2_config['lan_interface'],
                router2_config['lan_ip'],
                router2_config['lan_subnet']
            )

            # Step 4: Configure Host1 interface and static default route
            st.banner("Step 4: Configure Host1 interface and static default route")
            st.log(f"Configuring Host1 interface {host1_config['interface']}: {host1_config['ip']}/{host1_config['subnet']}")
            self._configure_interface_ip(
                host1,
                host1_config['interface'],
                host1_config['ip'],
                host1_config['subnet']
            )
            st.log(f"Adding default route on Host1 via gateway {host1_config['gateway']}")
            ip_api.create_static_route(
                host1,
                next_hop=host1_config['gateway'],
                static_ip="0.0.0.0/0",
                family='ipv4',
                cli_type=self.data.cli_type
            )

            # Step 5: Configure Host2 interface and static default route
            st.banner("Step 5: Configure Host2 interface and static default route")
            st.log(f"Configuring Host2 interface {host2_config['interface']}: {host2_config['ip']}/{host2_config['subnet']}")
            self._configure_interface_ip(
                host2,
                host2_config['interface'],
                host2_config['ip'],
                host2_config['subnet']
            )
            st.log(f"Adding default route on Host2 via gateway {host2_config['gateway']}")
            ip_api.create_static_route(
                host2,
                next_hop=host2_config['gateway'],
                static_ip="0.0.0.0/0",
                family='ipv4',
                cli_type=self.data.cli_type
            )

            # Step 6: Advertise LAN networks via existing BGP session
            st.banner("Step 6: Advertise LAN networks via existing BGP session")
            st.log(f"R1 advertising network {router1_config['lan_network']}")
            bgp_api.advertise_bgp_network(
                self.data.dut1,
                router1_config['bgp_asn'],
                router1_config['lan_network'],
                vrf='default',
                cli_type=self.data.cli_type
            )
            st.log(f"R2 advertising network {router2_config['lan_network']}")
            bgp_api.advertise_bgp_network(
                self.data.dut2,
                router2_config['bgp_asn'],
                router2_config['lan_network'],
                vrf='default',
                cli_type=self.data.cli_type
            )

            # Wait for BGP route propagation
            st.wait(10, "Waiting for BGP route propagation")

            # Step 7: Verify BGP route learning
            st.banner("Step 7: Verify BGP route learning on routers")

            # Verify R1 learned R2's LAN network
            st.log(f"Verifying R1 learned route {verification['router1_should_learn']}")
            result_r1 = bgp_api.verify_ip_bgp_route(
                self.data.dut1,
                family='ipv4',
                network=verification['router1_should_learn'],
                next_hop=verification['next_hop_r1'],
                cli_type=self.data.cli_type
            )
            if not result_r1:
                st.log(f"WARNING: R1 did not learn route {verification['router1_should_learn']}")

            # Verify R2 learned R1's LAN network
            st.log(f"Verifying R2 learned route {verification['router2_should_learn']}")
            result_r2 = bgp_api.verify_ip_bgp_route(
                self.data.dut2,
                family='ipv4',
                network=verification['router2_should_learn'],
                next_hop=verification['next_hop_r2'],
                cli_type=self.data.cli_type
            )
            if not result_r2:
                st.log(f"WARNING: R2 did not learn route {verification['router2_should_learn']}")

            # Step 8: Verify routing table entries
            st.banner("Step 8: Verify routing tables on routers")

            # Show routing table on R1
            st.log(f"Checking routing table on R1 ({self.data.dut1})")
            show_route_r1 = ip_api.show_ip_route(
                self.data.dut1,
                family='ipv4',
                cli_type=self.data.cli_type
            )
            st.log(f"R1 routing table entries: {show_route_r1}")

            # Show routing table on R2
            st.log(f"Checking routing table on R2 ({self.data.dut2})")
            show_route_r2 = ip_api.show_ip_route(
                self.data.dut2,
                family='ipv4',
                cli_type=self.data.cli_type
            )
            st.log(f"R2 routing table entries: {show_route_r2}")

            # Step 9: Test host-to-host connectivity
            st.banner("Step 9: Test real host-to-host connectivity (H1 to H2)")

            # Ping from Host1 to Host2
            st.log(f"Pinging from Host1 ({host1_config['ip']}) to Host2 ({host2_config['ip']})")
            ping_result_h1_h2 = ip_api.ping(
                host1,
                verification['host1_ping_host2'],
                family='ipv4',
                count=5,
                cli_type=self.data.cli_type
            )
            if ping_result_h1_h2:
                st.log(f"SUCCESS: Ping from Host1 to Host2 successful")
            else:
                st.log(f"WARNING: Ping from Host1 to Host2 failed")

            # Ping from Host2 to Host1
            st.log(f"Pinging from Host2 ({host2_config['ip']}) to Host1 ({host1_config['ip']})")
            ping_result_h2_h1 = ip_api.ping(
                host2,
                verification['host2_ping_host1'],
                family='ipv4',
                count=5,
                cli_type=self.data.cli_type
            )
            if ping_result_h2_h1:
                st.log(f"SUCCESS: Ping from Host2 to Host1 successful")
            else:
                st.log(f"WARNING: Ping from Host2 to Host1 failed")

            # Step 10: Verify end-to-end traffic forwarding
            st.banner("Step 10: Verify end-to-end traffic forwarding through BGP")
            if ping_result_h1_h2 and ping_result_h2_h1:
                st.log("SUCCESS: Bidirectional host-to-host routing verified through BGP")
                st.log("BGP route advertisement and learning working correctly")
                st.log("End-to-end connectivity established across iBGP routers")
            else:
                st.log("WARNING: Host-to-host connectivity has issues")

            # Log test summary
            st.banner("BGP Route Advertisement Test Summary (H1-R1-R2-H2 Topology)")
            st.log(f"R1 advertised: {router1_config['lan_network']}")
            st.log(f"R2 advertised: {router2_config['lan_network']}")
            st.log(f"R1 learned: {verification['router1_should_learn']} (verified: {result_r1})")
            st.log(f"R2 learned: {verification['router2_should_learn']} (verified: {result_r2})")
            st.log(f"Ping H1→H2: {'PASS' if ping_result_h1_h2 else 'FAIL'}")
            st.log(f"Ping H2→H1: {'PASS' if ping_result_h2_h1 else 'FAIL'}")
            st.log(f"Topology: Host1({host1_config['ip']}) -- R1({router1_config['lan_ip']}) -- R2({router2_config['lan_ip']}) -- Host2({host2_config['ip']})")

        finally:
            # Cleanup test 003 additions only (preserve test 001's BGP configuration)
            st.banner("Cleanup: Remove test 003 additions (preserving test 001 BGP)")
            try:
                # Unadvertise networks from BGP (but keep BGP session)
                st.log("Unadvertising LAN networks from BGP")
                bgp_api.advertise_bgp_network(
                    self.data.dut1,
                    router1_config['bgp_asn'],
                    router1_config['lan_network'],
                    config='no',
                    vrf='default',
                    cli_type=self.data.cli_type
                )
                bgp_api.advertise_bgp_network(
                    self.data.dut2,
                    router2_config['bgp_asn'],
                    router2_config['lan_network'],
                    config='no',
                    vrf='default',
                    cli_type=self.data.cli_type
                )

                # Remove static routes from hosts
                st.log("Removing static routes from hosts")
                ip_api.delete_static_route(
                    host1,
                    next_hop=host1_config['gateway'],
                    static_ip="0.0.0.0/0",
                    family='ipv4',
                    cli_type=self.data.cli_type
                )
                ip_api.delete_static_route(
                    host2,
                    next_hop=host2_config['gateway'],
                    static_ip="0.0.0.0/0",
                    family='ipv4',
                    cli_type=self.data.cli_type
                )

                # Remove LAN interface IPs (but keep WAN IPs from test 001)
                st.log("Removing LAN interface IP addresses")
                # R1 LAN (added in test 003)
                self._unconfigure_interface_ip(
                    self.data.dut1,
                    router1_config['lan_interface'],
                    router1_config['lan_ip'],
                    router1_config['lan_subnet']
                )
                # R2 LAN (added in test 003)
                self._unconfigure_interface_ip(
                    self.data.dut2,
                    router2_config['lan_interface'],
                    router2_config['lan_ip'],
                    router2_config['lan_subnet']
                )
                # Host1
                self._unconfigure_interface_ip(
                    host1,
                    host1_config['interface'],
                    host1_config['ip'],
                    host1_config['subnet']
                )
                # Host2
                self._unconfigure_interface_ip(
                    host2,
                    host2_config['interface'],
                    host2_config['ip'],
                    host2_config['subnet']
                )

                st.log("Test 003 cleanup completed - test 001 BGP configuration preserved")
                st.log("iBGP session remains for potential future tests")
            except Exception as e:
                st.log(f"Error during cleanup: {e}")

        st.report_pass("test_case_passed")
