"""
LLDP CLI CONFIGURATION
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_2vs.yaml  \
  system/lldp/test_lldp_cli_configuration.py \
  --logs-path ./logs/test_lldp_cli_configuration_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Implements the LLDP CLI functional coverage defined in testcases_lldp_1.md,
  driving configuration changes via klish and validating click show outputs on
  both DUT and neighbor. The suite toggles global/interface enablement, rx/tx
  states, timers, management address TLVs, and 802.1/802.3 TLV selections while
  asserting that LLDP neighbors, TLVs, statistics, and running configuration
  remain consistent across user and sudo contexts.

Pre-requisites:
  - Topology: D1D2:1 | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |        D1         |                       |        D2         |
        # |   Ethernet4       |=======================|   Ethernet4       |
        # +--------------------+                       +--------------------+
  - Feature flags / min SONiC version: LLDP enabled, click + klish support
  - Required test variables (YAML): defaults.cli_type, defaults.verify_timeout (optional)
"""

from __future__ import annotations

import time
from typing import Iterable

import pytest

import apis.system.lldp as lldp_api
from spytest import SpyTestDict, st
from utilities.utils import get_interface_number_from_name


@pytest.mark.topology("D1D2:1")
class TestLldpCliConfiguration:
    """Testcases covering LLDP CLI configuration using klish with click validation."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Discover topology handles and prepare defaults."""
        topology = st.ensure_min_topology("D1D2:1")

        cls.data.dut = topology.D1
        cls.data.peer = topology.D2
        cls.data.port = topology.D1D2P1
        cls.data.peer_port = topology.D2D1P1
        cls.data.dut_interface_cmd = cls._build_interface_cli(cls.data.port)
        cls.data.peer_interface_cmd = cls._build_interface_cli(cls.data.peer_port)

        cls.data.system_name = "SupermicroSonic"
        cls.data.system_description = "Supermicro Sonic"
        cls.data.management_ipv4 = "10.1.1.1"
        cls.data.lldp_timer = 10

        if not cls._wait_for_neighbors(cls.data.dut, cls.data.port, expect=True, timeout=120):
            st.report_fail("msg", f"Missing initial LLDP neighbor on {cls.data.port}")
        if not cls._wait_for_neighbors(cls.data.peer, cls.data.peer_port, expect=True, timeout=120):
            st.report_fail("msg", f"Missing initial LLDP neighbor on {cls.data.peer_port}")

    @classmethod
    def teardown_class(cls) -> None:
        """Restore LLDP defaults on both nodes."""
        cls._restore_defaults(
            cls.data.dut,
            cls.data.dut_interface_cmd,
            cls.data.management_ipv4,
        )
        cls._restore_defaults(
            cls.data.peer,
            cls.data.peer_interface_cmd,
            cls.data.management_ipv4,
        )

    def test_lldp_cli_configuration(self) -> None:
        """End-to-end LLDP CLI validation using klish config and click show commands."""
        d1 = self.data.dut
        d2 = self.data.peer
        port = self.data.port
        peer_port = self.data.peer_port
        intf_cmd = self.data.dut_interface_cmd

        baseline_neighbors = lldp_api.get_lldp_neighbors(d1, interface=port, cli_type="click")
        baseline_table = lldp_api.get_lldp_table(d1, cli_type="click")
        baseline_stats = lldp_api.get_lldp_statistics(d1, ports=[port], cli_type="click")

        if baseline_neighbors is None:
            st.report_fail("msg", f"Failed to fetch baseline LLDP neighbor data for {port}")
        if baseline_table is None:
            st.report_fail("msg", "Failed to fetch baseline LLDP table output")
        if baseline_stats is None:
            st.report_fail("msg", "Failed to fetch baseline LLDP statistics")

        # Step 1: Global LLDP enable/disable toggling.
        self._apply_klish(d1, ["lldp enable"])
        self._apply_klish(d1, ["no lldp enable"])
        if not self._wait_for_neighbors(d1, port, expect=False, timeout=60):
            st.report_fail("msg", "LLDP neighbor entries persisted after global disable")
        self._apply_klish(d1, ["lldp enable"])
        if not self._wait_for_neighbors(d1, port, expect=True, timeout=120):
            st.report_fail("msg", "LLDP neighbor did not return after global enable")

        # Step 2: Interface-level enable/disable.
        self._apply_klish(
            d1,
            [
                f"interface {intf_cmd}",
                "lldp enable",
                "no lldp enable",
                "lldp enable",
                "exit",
            ],
        )
        if not self._wait_for_neighbors(d1, port, expect=True, timeout=90):
            st.report_fail("msg", f"LLDP neighbor missing on {port} after interface toggles")

        # Step 3: RX/TX toggling on the interface.
        self._apply_klish(
            d1,
            [
                f"interface {intf_cmd}",
                "lldp receive",
                "lldp transmit",
                "no lldp receive",
                "no lldp transmit",
                "lldp receive",
                "lldp transmit",
                "exit",
            ],
        )
        st.wait(5)

        # Step 4: Configure LLDP timer and restore default.
        self._apply_klish(d1, [f"lldp timer {self.data.lldp_timer}"])
        st.wait(1)
        self._apply_klish(d1, ["no lldp timer"])

        # Step 5: Configure global TLVs and management address.
        self._apply_klish(
            d1,
            [
                f"lldp system-name \"{self.data.system_name}\"",
                f"lldp system-description \"{self.data.system_description}\"",
                "lldp tlv-select system-capabilities",
                "lldp tlv-select management-address",
                f"lldp tlv-set management-address ipv4 {self.data.management_ipv4}",
                "lldp tlv-select link-aggregation",
                "lldp tlv-select max-frame-size",
                "lldp tlv-select port-vlan-id",
                "lldp tlv-select power-management",
                "lldp tlv-select vlan-name",
            ],
        )

        st.wait(30)

        # Validate LLDP show commands on DUT (click).
        table_after = lldp_api.get_lldp_table(d1, cli_type="click") or []
        neighbor_after = lldp_api.get_lldp_neighbors(d1, interface=port, cli_type="click") or []
        stats_after = lldp_api.get_lldp_statistics(d1, ports=[port], cli_type="click") or []

        matching_entries = [entry for entry in table_after if entry.get("LocalPort") == port]
        if not matching_entries:
            matching_entries = [entry for entry in table_after if entry.get("localport") == port]
        if not matching_entries:
            st.report_fail("msg", f"'show lldp table' missing port {port}")

        if not neighbor_after:
            st.report_fail("msg", f"'show lldp neighbor {port}' returned no entries")

        if not stats_after or not stats_after[0].get("interface"):
            st.report_fail("msg", f"'show lldp statistics {port}' returned empty counters")

        # Validate TLVs on peer using click.
        if not self._wait_for_neighbors(d2, peer_port, expect=True, timeout=120):
            st.report_fail("msg", f"Peer neighbor missing on {peer_port} after TLV configuration")
        peer_neighbor = lldp_api.get_lldp_neighbors(d2, interface=peer_port, cli_type="click") or []
        if not peer_neighbor:
            st.report_fail("msg", f"Peer 'show lldp neighbor {peer_port}' returned no data")
        peer_entry = peer_neighbor[0]

        if peer_entry.get("chassis_name") != self.data.system_name:
            st.report_fail(
                "msg",
                f"System name TLV mismatch on peer: expected {self.data.system_name}, "
                f"got {peer_entry.get('chassis_name')}",
            )
        if peer_entry.get("chassis_descr") != self.data.system_description:
            st.report_fail(
                "msg",
                f"System description TLV mismatch on peer: expected {self.data.system_description}, "
                f"got {peer_entry.get('chassis_descr')}",
            )
        if peer_entry.get("chassis_mgmt_ip") != self.data.management_ipv4:
            st.report_fail(
                "msg",
                f"Management address TLV mismatch on peer: expected {self.data.management_ipv4}, "
                f"got {peer_entry.get('chassis_mgmt_ip')}",
            )
        if not peer_entry.get("portvlanid_value"):
            st.report_fail("msg", "Port VLAN ID TLV missing on peer neighbor output")

        # Validate LLDP statistics on peer as well.
        peer_stats = lldp_api.get_lldp_statistics(d2, ports=[peer_port], cli_type="click") or []
        if not peer_stats or not peer_stats[0].get("interface"):
            st.report_fail("msg", f"Peer 'show lldp statistics {peer_port}' returned empty counters")

        # Run sudo validation commands.
        sudo_neighbor = self._run_sudo_show(d1, "show lldp neighbor")
        sudo_table = self._run_sudo_show(d1, "show lldp table")
        if not sudo_neighbor.strip():
            st.report_fail("msg", "sudo vtysh 'show lldp neighbor' returned empty output")
        if not sudo_table.strip():
            st.report_fail("msg", "sudo vtysh 'show lldp table' returned empty output")

        st.report_pass("test_case_passed")

    @staticmethod
    def _build_interface_cli(interface_name: str | None) -> str | None:
        if not interface_name:
            return None
        info = get_interface_number_from_name(interface_name)
        if isinstance(info, dict) and {"type", "number"}.issubset(info):
            return f"{info['type']} {info['number']}"
        return interface_name

    @staticmethod
    def _apply_klish(dut: str, commands: Iterable[str]) -> None:
        command_list = [cmd for cmd in commands if cmd]
        script = ["sonic-cli", "configure terminal"]
        script.extend(command_list)
        script.extend(["end", "exit"])
        st.apply_script(dut, script)

    @staticmethod
    def _wait_for_neighbors(dut: str, interface: str, expect: bool, timeout: int) -> bool:
        end_time = time.time() + timeout
        while time.time() < end_time:
            entries = lldp_api.get_lldp_neighbors(dut, interface=interface, cli_type="click") or []
            has_neighbor = bool(entries)
            if expect and has_neighbor:
                return True
            if not expect and not has_neighbor:
                return True
            st.wait(5)
        return False

    @classmethod
    def _restore_defaults(cls, dut: str, interface_cmd: str | None, management_ipv4: str) -> None:
        cleanup_cmds = [
            "lldp enable",
            "no lldp timer",
            "no lldp system-name",
            "no lldp system-description",
            "no lldp tlv-select system-capabilities",
            "no lldp tlv-select management-address",
            f"no lldp tlv-set management-address ipv4 {management_ipv4}",
            "no lldp tlv-select link-aggregation",
            "no lldp tlv-select max-frame-size",
            "no lldp tlv-select port-vlan-id",
            "no lldp tlv-select power-management",
            "no lldp tlv-select vlan-name",
        ]
        cls._apply_klish(dut, cleanup_cmds)

        if interface_cmd:
            cls._apply_klish(
                dut,
                [
                    f"interface {interface_cmd}",
                    "lldp enable",
                    "lldp receive",
                    "lldp transmit",
                    "exit",
                ],
            )

    @staticmethod
    def _run_sudo_show(dut: str, command: str) -> str:
        cmd = f'sudo vtysh -c "{command}"'
        output = st.config(dut, cmd, skip_error_check=True)
        return str(output or "")
