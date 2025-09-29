# Tagged ARP Test Analyzer

## 1. Topology Type
- **Declared topology markers:** `pytest.mark.topology('t0', 'm0', 'mx')`, meaning the test can execute on T0, M0, or MX topologies.
- **Inference:** The `pytestmark` declaration applies to the whole module and drives the testbed selection in the SONiC test framework. The fixtures `tbinfo` and `rand_one_dut_hostname` further suggest a single-DUT topology rather than dual ToR, reinforced by the `skip_dualtor` fixture that explicitly skips dualtor environments. Together these indicate the canonical T0-style topology with VLAN connectivity, but the marker allows execution on compatible M0/MX variants.

## 2. Overall Test Case Purpose
- The module validates **tagged Gratuitous ARP (GARP) handling across VLAN members**. It checks that when the PTF host sends tagged ARP replies for dummy hosts, the DUT installs the correct ARP entries and handles VLAN tagging behavior correctly.
- Within the SONiC framework this ensures Layer-2/Layer-3 interoperability on access VLANs: ARP learning, VLAN port membership, and ARP table population remain consistent with expected forwarding logic.

## 3. Detailed Breakdown of Sub-Testcases
### `test_tagged_arp_pkt`
- **Intent & Logic:**
  - Iterates through the active VLAN ports discovered via `running_vlan_ports_list`.
  - For each VLAN member and permitted VLAN ID, it clears ARP state, builds tagged ARP reply packets (opcode 2) with dummy MAC/IP pairs, and sends them from the corresponding PTF port.
  - Uses `wait_until` with `_check_arp_entries` to poll `show arp` until all dummy entries appear with the expected interface and VLAN ID.
  - On failure, collects diagnostic outputs (`show mac`, `show arp`, interface counters, portchannel state) before raising the captured error.
- **Why it matters:** Confirms SONiC correctly accepts tagged ARP packets, populates ARP tables with accurate VLAN bindings, and maintains consistency between VLAN membership and ARP learning. This is crucial for multi-VLAN access scenarios in T0 networks.

### Helper Functions and Fixtures
- **`setup_arp` (module-level autouse fixture):** Enables ARP acceptance on VLAN interfaces before the test and restores the original configuration with cleanup afterward, including clearing ARP entries. This ensures the DUT is in a known state.
- **`enable_arp` / `arp_cleanup`:** Support functions invoked by `setup_arp` and the test to toggle kernel ARP acceptance and reset ARP tables.
- **`build_arp_packet`:** Constructs the tagged ARP reply packets with specified VLAN IDs, MACs, and IPs.
- **`_check_arp_entries`:** Validates the DUT ARP table contents against the dummy data set and enforces that entries appear on the correct VLAN device.
- **`skip_dualtor`:** Guard fixture preventing execution in dual ToR environments where tagging expectations differ.

## 4. Dependencies and Prerequisites
- **Fixtures:** `ptfadapter`, `duthosts`, `rand_one_dut_hostname`, `rand_selected_dut`, `tbinfo`, `ports_list`, `vlan_intfs_dict`, `setup_acl_table`, `setup_po2vlan`, `cfg_facts`, plus autouse fixtures like `setup_arp`.
- **Purpose:** These fixtures provision DUT access, select a target device, expose topology data, build VLAN/port-channel mappings, and prepare the PTF environment. `cfg_facts` fetches current running configuration to know VLAN members for ARP enablement.
- **Topology constraints:** Dual ToR is explicitly skipped, implying a single-DUT setup with VLAN trunks/access members.

## 5. Key Inputs and Parameters
- **Constants:** `PTF_PORT_MAPPING_MODE`, `DUMMY_MAC_PREFIX`, `DUMMY_IP_PREFIX`, `DUMMY_ARP_COUNT` control packet construction and iteration counts.
- **Runtime Data:** `running_vlan_ports_list` returns structures containing `port_index`, permitted VLAN IDs, and device names; these drive the packet emission loops.
- **Command outputs:** `duthost.command('show arp')` and related CLI commands provide verification data.
- **Testbed Information:** `tbinfo` and `cfg_facts` deliver topology and configuration needed for setup and validation.

## 6. External Libraries and Modules
- **`pytest` / `pytest.mark`:** Provides test framework, fixtures, and topology markers.
- **`ptf.testutils`:** Supplies packet construction and send utilities for crafting ARP frames.
- **`logging`, `pprint`:** Used for structured logging and human-readable output of command results.
- **SONiC Test Common Helpers:**
  - `change_mac_addresses`, `remove_ip_addresses`: PTF host utilities (imported but unused, likely for shared fixture completeness).
  - VLAN and ACL helpers (`setup_acl_table`, `setup_po2vlan`, `vlan_intfs_dict`, `running_vlan_ports_list`, etc.) orchestrate VLAN/port-channel setup and environment consistency.
  - `pytest_require`: Assertion helper for conditional skips.
  - `wait_until`: Utility to poll for ARP entry convergence.

## 7. Unspecified Items
- **Additional topology diagrams or explicit port counts:** Not specified.
- **Exact source of VLAN/port definitions within `testbed.yaml` or inventory:** Not specified.
