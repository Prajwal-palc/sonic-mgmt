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
        """Ensure all BGP and interface configurations are removed after the suite completes."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping teardown")
            return
        st.banner("Starting final cleanup")
        cls._cleanup_all_configs()

    @classmethod
    def _cleanup_all_configs(cls) -> None:
        """Remove all BGP configurations and interface IP addresses."""
        st.log("Cleaning up BGP configurations")

        # Cleanup BGP on both DUTs
        for dut in [cls.data.dut1, cls.data.dut2]:
            try:
                bgp_api.cleanup_router_bgp(dut_list=[dut], cli_type=cls.data.cli_type)
            except Exception as e:
                st.log(f"BGP cleanup error on {dut}: {e}")

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
        """Configure BGP router with AS number and router-id."""
        st.log(f"Configuring BGP router on {dut}: AS {local_asn}, Router-ID {router_id}")
        result = bgp_api.config_bgp_router(
            dut,
            local_asn=local_asn,
            router_id=router_id,
            config='yes',
            vrf=vrf,
            cli_type=self.data.cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure BGP router on {dut}")

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
        BGP-IPv4-001: Configure BGP IPv4 neighbor, verify session, and unconfigure.

        Test Steps:
        1. Configure IPv4 addresses on DUT1 and DUT2 interfaces
        2. Configure BGP routers on both DUTs
        3. Configure BGP neighbors on both DUTs
        4. Activate neighbors in IPv4 unicast address family
        5. Verify BGP session establishment
        6. Unconfigure BGP on both DUTs
        7. Unconfigure IP addresses on interfaces
        """
        testcase = self._get_testcase("001")

        st.banner("TEST CASE: BGP IPv4 Configure, Verify, Unconfigure")

        # Get test parameters
        dut1_config = testcase.get("dut1", {})
        dut2_config = testcase.get("dut2", {})

        try:
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

        finally:
            # Step 6: Unconfigure BGP
            st.banner("Step 6: Unconfigure BGP")
            self._unconfigure_bgp(self.data.dut1, dut1_config["bgp_asn"])
            self._unconfigure_bgp(self.data.dut2, dut2_config["bgp_asn"])

            # Step 7: Unconfigure interface IP addresses
            st.banner("Step 7: Unconfigure interface IP addresses")
            self._unconfigure_interface_ip(
                self.data.dut1,
                self.data.dut1_interface,
                dut1_config["ip_address"],
                dut1_config["subnet"]
            )
            self._unconfigure_interface_ip(
                self.data.dut2,
                self.data.dut2_interface,
                dut2_config["ip_address"],
                dut2_config["subnet"]
            )

        st.report_pass("test_case_passed")
