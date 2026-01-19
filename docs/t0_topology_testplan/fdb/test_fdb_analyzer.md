# FDB Test Analyzer

## 1. Topology Type
- **Supported topologies:** `t0`, `m0`, and `mx` topologies are explicitly marked via `pytestmark`. This indicates the test is designed to run on leaf-spine style T0 environments as well as management-only (m0) and mixed (mx) lab variations where VLAN-based L2 forwarding is available.
- **Inference details:** The topology list is declared in `pytestmark`, and several fixtures (`tbinfo`, `rand_one_dut_hostname`, `active_active_ports`) inspect the testbed metadata to adjust behavior (e.g., dual ToR handling). This combination signals that the test needs a DUT with VLAN members connected to a PTF host in the SONiC T0-style fanout layout.

## 2. Overall Test Case Purpose
- **Primary goal:** Validate SONiC's forwarding database (FDB) learning, forwarding, and reporting pipeline across VLAN-access and port-channel members.
- **Scope within SONiC QA:** The test seeds MAC entries through various packet types (Ethernet, ARP request/reply) from the PTF host, then verifies that learned entries forward correctly between VLAN members and that `show mac`/`fdb_facts` reflect the expected MAC/VLAN/port/type attributes. It also ensures the DUT never learns its own router MAC. This covers dynamic MAC learning, dummy MAC population, MAC flooding resilience, and CLI parity—key requirements for L2 data plane validation in SONiC/pytest infrastructure.

## 3. Detailed Breakdown of Sub-Testcases

### `test_fdb`
- **Intent & flow:**
  - Applies pre/post-test clean-up (`fdb_cleanup`) to start from a known state.
  - Re-initializes the PTF adapter, collects DUT VLAN/port configuration, and determines which PTF ports are active in the topology.
  - Uses `setup_fdb` to send Ethernet/ARP packets (depending on `pkt_type` parameter) from each active VLAN member to populate dynamic MAC entries, including dummy MACs per port.
  - Performs pairwise traffic forwarding checks between every combination of VLAN members (front-panel or port-channel members), verifying packets exit on expected ports with appropriate VLAN tagging using `send_recv_eth`.
  - Gathers FDB facts from the DUT, validating MAC address formatting, VLAN and port membership accuracy, entry types, and ensuring the dummy MAC count matches expectations.
- **Importance:** Confirms end-to-end MAC learning and forwarding correctness, plus ensures CLI/Ansible FDB reporting remains consistent—central to verifying SONiC switching behavior under varied packet stimuli.

### `test_self_mac_not_learnt`
- **Intent & flow:**
  - Clears the FDB, selects a random front-panel interface from minigraph facts, and transmits packets sourced from the DUT's own router MAC.
  - After allowing learning time, fetches FDB facts to assert the DUT did not mistakenly learn or install its own MAC.
- **Importance:** Guards against control-plane MAC pollution, ensuring the DUT's router MAC remains excluded from dynamic FDB learning—critical for preventing forwarding loops or blackholes.

### Helper Functions & Fixtures
- **`setup_fdb` & packet senders (`send_eth`, `send_arp_request`, `send_arp_reply`, `send_recv_eth`):** Craft and transmit the traffic required for populating and validating FDB behavior, handling VLAN tagging, retries, and expected packet matching.
- **`get_dummay_mac_count`:** Dynamically adjusts dummy MAC load based on topology size or configuration (e.g., dual ToR, large T0 variants) to control runtime while preserving coverage.
- **`pkt_type` fixture:** Parameterizes the tests across Ethernet, ARP request, ARP reply, and cleanup runs, broadening the coverage of learning mechanisms.
- **`setup_active_active_ports`:** Special handling for active-active dual ToR scenarios to steer traffic through the correct TOR instance before validation.
- **`record_mux_status`:** Collects mux cable state on failure for debugging dual ToR environments.

## 4. Dependencies and Prerequisites
- **Fixtures:** `disable_fdb_aging`, `change_mac_addresses`, `remove_ip_addresses`, `config_active_active_dualtor_active_standby`, `validate_active_active_dualtor_setup`, `active_active_ports`, `toggle_all_simulator_ports_to_rand_selected_tor_m`, `fanouthosts`, `ptfadapter`, `duthosts`, `rand_one_dut_hostname`, `rand_selected_dut`, `rand_unselected_dut`, `tbinfo`, `ptfhost`, `ansible_adhoc`.
  - These fixtures configure the DUT/PTF environment, manage mux/dualtor behavior, and provide topology & host metadata essential for building the VLAN/member tables and validating outputs.
- **Topology prerequisites:** DUT must expose VLANs with at least two active members (front-panel or port-channel), PTF interfaces mapped to those members, and dual ToR mux simulator access when applicable.
- **Ansible access:** Required to execute `fdb_facts`, `portstat`, `sonic-clear fdb all`, and other shell commands.

## 5. Key Inputs and Parameters
- **`pkt_type` (fixture):** Drives traffic variations (Ethernet, ARP request/reply, cleanup) to test different learning paths.
- **`get_dummay_mac_count`:** Determines per-port dummy MAC injection count based on topology size to balance coverage with execution time.
- **`router_mac`, `port_index_map`, `VLAN`/`VLAN_MEMBER`/`PORTCHANNEL` configs:** Retrieved from `config_facts`; used to map logical VLAN membership to PTF ports.
- **`interface_table`, `vlan_table`:** Derived structures enumerating VLAN-to-port relationships, guiding both traffic generation and FDB validations.
- **`tbinfo['topo']['name']`:** Influences dummy MAC count selection and dualtor behavior (e.g., detecting `dualtor` topologies).

## 6. External Libraries and Modules
- **PyTest (`pytest`):** Provides test framework, fixtures, parametrization, and assertions.
- **PTF (`ptf.testutils`, `ptf.packet`, `ptf.mask`):** Supplies packet crafting, sending, and verification utilities for Ethernet/ARP traffic with VLAN tagging.
- **Standard libraries (`collections`, `time`, `itertools`, `logging`, `pprint`, `re`, `random`):** Support data structuring, timing, logging, regex validation, and random selection.
- **SONiC test helpers:** Modules under `tests.common` (e.g., `helpers.assertions`, `fixtures.duthost_utils`, `dualtor` utilities, `helpers.portchannel_to_vlan`, `helpers.backend_acl`) deliver shared setup/teardown logic, fixture provisioning, ACL/vlan configuration helpers, and debugging utilities tailored to SONiC QA.

## 7. Unspecified Items
- **Exact fanout device requirements, traffic rate expectations, and environmental variables beyond those noted above:** Not specified.
