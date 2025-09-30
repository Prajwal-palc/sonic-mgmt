# SRv6 VLAN Forwarding Test Analyzer

## 1. Topology Type
- **Identified Topology:** `t0` leaf-spine topology with downstream servers and upstream T1 peers.
- **Inference:** The module-level `pytestmark` explicitly limits execution to the `t0` topology, and the `setup_downstream_uN` fixture parses `tbinfo` to ensure the topology type is `t0` before continuing. It also classifies LLDP neighbors containing "Servers" as downstream and those containing "T1" as upstream, reflecting the T0 server/T1 peer layout.【F:tests/srv6/test_srv6_vlan_forwarding.py†L19-L85】【F:tests/srv6/test_srv6_vlan_forwarding.py†L90-L155】

## 2. Overall Test Case Purpose
- **High-Level Goal:** Validate SRv6 uN segment processing for VLAN-attached hosts on a SONiC ToR running a T0 topology. The tests ensure that SRv6 traffic decapsulates correctly towards a downstream VLAN host and that failure scenarios (such as a downed downstream port) do not cause unwanted flooding within the VLAN.
- **Broader Context:** Within SONiC's SRv6 feature validation, these tests exercise control-plane configuration (locators, SIDs, static routes, and proxy ARP) and data-plane forwarding through PTF-based traffic injection. They confirm that SRv6 uN behavior integrates properly with VLAN interfaces and neighbor resolution in the SONiC/pytest infrastructure.【F:tests/srv6/test_srv6_vlan_forwarding.py†L37-L194】

## 3. Detailed Breakdown of Sub-Testcases
### `test_srv6_uN_forwarding_towards_vlan`
- **Intent & Logic:** Uses the `setup_downstream_uN` fixture to configure SRv6 locators, SIDs, and static routes, then sends SRv6-encapsulated traffic (with and without Segment Routing Headers) from a PTF upstream port towards the DUT. The helper `run_srv6_downstrean_traffic_test` function generates random payloads, crafts packets, and expects the DUT to decapsulate and forward them to the selected downstream VLAN port with correct Ethernet and IPv6 header updates.【F:tests/srv6/test_srv6_vlan_forwarding.py†L37-L120】【F:tests/srv6/test_srv6_vlan_forwarding.py†L181-L194】
- **Relevance:** Confirms the primary SRv6 VLAN forwarding functionality—decapsulation, neighbor MAC resolution, TTL decrement, and delivery to the proper VLAN member.

### `test_srv6_uN_no_vlan_flooding`
- **Intent & Logic:** After the same SRv6 configuration, this test shuts down the chosen downstream DUT port, clears the FDB, and transmits multiple SRv6 packets. It verifies that no downstream VLAN ports receive the traffic (ensuring lack of flooding) and then restores the interface state.【F:tests/srv6/test_srv6_vlan_forwarding.py†L196-L236】
- **Relevance:** Ensures resilience and containment; SRv6 traffic should not be flooded within the VLAN when the specific destination member is down, preventing unintended traffic leakage.

### Helper Components
- **`run_srv6_downstrean_traffic_test`:** Reusable helper for crafting SRv6 packets with or without SRH, predicting expected output frames, and invoking `runSendReceive` to validate forwarding.【F:tests/srv6/test_srv6_vlan_forwarding.py†L23-L73】
- **Fixtures:**
  - `proxy_arp_enabled`: Temporarily enables proxy ARP/NDP on all DUT VLANs, ensuring neighbor resolution for the tests.【F:tests/srv6/test_srv6_vlan_forwarding.py†L75-L118】
  - `setup_downstream_uN`: Builds the end-to-end SRv6 environment, including VLAN host addressing, PTF interface setup, SRv6 database entries, and static routes; tears everything down afterward.【F:tests/srv6/test_srv6_vlan_forwarding.py†L120-L178】

## 4. Dependencies and Prerequisites
- **Fixtures:** `rand_selected_dut`, `ptfhost`, `tbinfo`, `ptfadapter`, `proxy_arp_enabled`, and `setup_downstream_uN`. They provide DUT access, topology metadata, traffic generators, and configuration scaffolding.【F:tests/srv6/test_srv6_vlan_forwarding.py†L75-L236】
- **Topology Constraints:** Requires a `t0` topology with VLAN members connected to PTF ports and both server-facing and T1-facing neighbors. The test skips otherwise.【F:tests/srv6/test_srv6_vlan_forwarding.py†L147-L167】
- **Device Capabilities:** DUT must support SRv6 configuration commands, static routing entries, and proxy ARP subcommands; enforced through `pytest_require` checks.【F:tests/srv6/test_srv6_vlan_forwarding.py†L89-L118】

## 5. Key Inputs and Parameters
- **Topology Info (`tbinfo`):** Supplies VLAN names, member ports, neighbor roles, and PTF port mappings, driving port selection for traffic injection and verification.【F:tests/srv6/test_srv6_vlan_forwarding.py†L120-L178】
- **PTF/DUT Ports:** Derived from minigraph facts and LLDP output to identify upstream source and downstream destination ports.【F:tests/srv6/test_srv6_vlan_forwarding.py†L137-L176】
- **SRv6 Configuration Constants:** Hard-coded prefixes (`fcbb:bbbb:1::/48`, `fcbb:bbbb:2::/48`, `fcbb:bbbb::/32`) define locator, SID, and traffic destinations for the test scenario.【F:tests/srv6/test_srv6_vlan_forwarding.py†L162-L176】
- **Proxy ARP State:** Controlled through CLI commands to ensure neighbor discovery when the downstream server port is selected.【F:tests/srv6/test_srv6_vlan_forwarding.py†L89-L118】
- **`with_srh` Parameter:** Pytest parametrization toggling between SRv6 packets with and without Segment Routing Headers to exercise both decapsulation paths.【F:tests/srv6/test_srv6_vlan_forwarding.py†L180-L205】

## 6. External Libraries and Modules
- **`scapy` (Ether, IPv6, UDP, Raw):** Constructs custom IPv6 and SRv6 packets used in traffic generation.【F:tests/srv6/test_srv6_vlan_forwarding.py†L1-L34】
- **`ptf.testutils` (`simple_ipv6_sr_packet`, `send`, `verify_no_packet_any`):** Provides helpers to craft SRv6 packets, transmit them, and validate absence of packets on specified ports.【F:tests/srv6/test_srv6_vlan_forwarding.py†L9-L34】【F:tests/srv6/test_srv6_vlan_forwarding.py†L207-L236】
- **`srv6_utils` (`runSendReceive`, `get_neighbor_mac`):** SONiC-specific utilities for SRv6 traffic validation and neighbor MAC retrieval.【F:tests/srv6/test_srv6_vlan_forwarding.py†L10-L34】
- **`tests.common.helpers.assertions.pytest_require`:** Ensures required CLI functionality exists before proceeding, preventing unsupported scenarios from running.【F:tests/srv6/test_srv6_vlan_forwarding.py†L11-L118】
- **Standard Libraries (`random`, `string`, `ipaddress`, `time`, `logging`, `pytest`):** Provide randomness, addressing utilities, timing, logging, and test orchestration.【F:tests/srv6/test_srv6_vlan_forwarding.py†L1-L118】

## 7. Unspecified Items
- **Explicit DUT Hardware Models Beyond ASIC Marks:** Not specified.
- **Detailed testbed.yaml variable names or group_vars references:** Not specified.
- **Exact implementations of imported helpers (`runSendReceive`, `get_neighbor_mac`):** Not specified in this file.
