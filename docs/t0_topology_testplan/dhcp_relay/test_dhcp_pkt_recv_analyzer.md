# DHCP Packet Receive Test Analyzer

## 1. Topology Type
- **Topology:** Multi-platform topologies marked as `t0`, `m0`, `mx`, and `m1`.
- **Inference:** The module-level `pytestmark` applies `pytest.mark.topology("t0", "m0", 'mx', "m1")`, indicating the test is designed to run on any of these topologies depending on the lab setup. The test harness selects the specific DUT through the `rand_selected_dut` fixture, meaning the infrastructure must provide at least one DUT in the marked topologies.

## 2. Overall Test Case Purpose
- **Objective:** Validate that a SONiC DUT correctly receives DHCPv6 multicast solicit messages when the DHCP relay feature is enabled.
- **Context:** Within SONiC's DHCP relay functionality, the test ensures that multicast DHCPv6 solicit packets from hosts reach the DUT regardless of ACL table configurations (empty table vs. table containing multicast-accept rule). This supports regression coverage for packet reception behavior in T0-style access topologies that connect hosts via ToR switches.

## 3. Detailed Breakdown of Sub-Testcases
- **Fixture `check_dhcp_relay_feature_state` (module scope):** Skips the entire module if the DHCP relay feature is not enabled on the randomly selected DUT. It queries the DUT's feature status and enforces the prerequisite for the subsequent tests.

- **Class `Dhcpv6PktRecvBase`:**
  - **Fixture `setup_teardown` (class scope):** Derives the list of host-facing interfaces and their corresponding PTF port indices for the selected DUT. It respects any interfaces disabled in the topology definition and converts the topology description into PTF indices that can be used for packet transmission. This fixture provides the base data (`ptf_indices`, `dut_intf_ptf_index`) to all inheriting test classes.
  - **Helper `parse_ptf_indices`:** Parses topology host interface encodings (e.g., `0.0@0`, `1.2`) to extract PTF port indices specific to the active DUT.
  - **Test `test_dhcpv6_multicast_recv`:**
    - **Intent:** Choose a random PTF port, construct a DHCPv6 solicit multicast packet, and transmit it toward the DUT. Using `capture_and_check_packet_on_dut`, it monitors the selected interface on the DUT for the expected packet transaction ID. Success indicates the DUT received the multicast packet.
    - **Checks:** Ensures at least one captured packet matches the transaction ID (`trid`) used in the generated DHCPv6 solicit. Validates packet reception from host to DUT.
    - **Relevance:** This test is the core validation for verifying DHCPv6 multicast packet acceptance under different ACL configurations provided by derived classes.

- **Class `TestDhcpv6WithEmptyAclTable` (inherits `Dhcpv6PktRecvBase`):**
  - **Fixture `setup_teardown_acl` (class scope):** Creates an L3V6 ingress ACL table bound to the relevant interfaces without adding rules (empty table). After the test, it removes the ACL table. The inherited `test_dhcpv6_multicast_recv` then verifies packet reception with no ACL rules applied.

- **Class `TestDhcpv6WithMulticastAccpectAcl` (inherits `Dhcpv6PktRecvBase`):**
  - **Fixture `setup_teardown_acl` (class scope):** Creates the same ACL table but loads a multicast-accept rule (`dhcp_relay/acl/dhcpv6_pkt_recv_multicast_accept.json`) along with the default drop-all rule implied for L3V6 tables. It uses `acl-loader update full` to program the rule. After testing, the ACL table is removed. The inherited `test_dhcpv6_multicast_recv` ensures the DUT still receives DHCPv6 multicast packets when only the specific rule allows them.

## 4. Dependencies and Prerequisites
- **Fixtures:**
  - `rand_selected_dut`: Provides access to the DUT under test.
  - `toggle_all_simulator_ports_to_rand_selected_tor`: Ensures mux simulator ports align with the chosen ToR in dual-TOR environments.
  - `setup_standby_ports_on_rand_unselected_tor`: Prepares standby ports on the non-selected TOR when applicable.
  - `ptfadapter`: Offers the interface to transmit packets from the PTF host.
  - `tbinfo`: Supplies topology metadata, including interface mappings and disabled ports.
- **Topology Constraints:** Must support host interfaces defined in the topology description and permit binding ingress ACL tables to those interfaces.
- **Feature Requirement:** DHCP relay feature must be enabled on the DUT (enforced by `check_dhcp_relay_feature_state`).

## 5. Key Inputs and Parameters
- `tbinfo['topo']['properties']['topology']['host_interfaces']`: Determines candidate host-facing ports for packet injection.
- `tbinfo['topo']['properties']['topology']['disabled_host_interfaces']`: Excludes interfaces that should not participate in the test.
- `duthost.get_extended_minigraph_facts(...)['minigraph_ptf_indices']`: Maps DUT interfaces to PTF port IDs used for packet transmission.
- `ACL_TABLE_NAME_DHCPV6_PKT_RECV_TEST`, `ACL_STAGE_INGRESS`, `ACL_TABLE_TYPE_L3V6`: Constants defining the ACL table configuration applied during tests.
- `ACL_RULE_FILE_PATH_MULTICAST_ACCEPT`: Points to the JSON file describing the multicast-accept ACL rule.
- DHCPv6 packet parameters (`DHCPV6_MAC_MULTICAST`, `DHCPV6_IP_MULTICAST`, UDP ports, and transaction ID) govern the packet constructed and validated during the test.

## 6. External Libraries and Modules
- `logging`: For emitting diagnostic information during the test run.
- `ptf.packet` (Scapy-like API) and `ptf.testutils`: Build and send packets via the PTF environment.
- `pytest`: Provides fixtures, markers, and assertion framework.
- `random`: Selects a random PTF port for more varied coverage.
- `re`: Parses interface encodings when deriving PTF indices.
- `scapy.layers.dhcp6.DHCP6_Solicit`: Packet layer used to construct DHCPv6 solicit messages.
- `tests.common.dualtor.mux_simulator_control.toggle_all_simulator_ports_to_rand_selected_tor`: Fixture import that influences mux simulator state in dual-TOR setups.
- `tests.common.helpers.assertions.pytest_assert`: Wrapper that supplies consistent assertion behavior with improved logging.
- `tests.common.utilities.capture_and_check_packet_on_dut`: Context manager to capture packets on the DUT and validate them with a callback.

## 7. Unspecified Items
- Any additional CLI parameters, group variables, or inventory-driven values beyond those explicitly referenced in the code are **Not specified** in this test file.
