# Test Plan Analyzer: `tests/snmp/test_snmp_fdb.py`

## 1. Topology Type
- **Topology markers**: The module-level `pytestmark` lists `t0`, `m0`, `mx`, and `m1` topologies, indicating the test is designed to run on leaf-spine T0 as well as multi-DUT (dualtor/metro) variants. This is inferred directly from the `pytest.mark.topology('t0', 'm0', 'mx', 'm1')` declaration.
- **Inference**: The reliance on VLAN access/portchannel ports, dual ToR fixtures, and the port-to-VLAN helper (`running_vlan_ports_list`) implies the classic T0-style fanout connectivity, while the presence of mux simulator toggling confirms dualtor readiness.

## 2. Overall Test Case Purpose
- **High-level goal**: Validate that dynamically learned MAC addresses injected through the dataplane are exposed correctly via SNMP FDB tables on SONiC devices.
- **Context**: Within the SONiC regression suite, this test ensures the SNMP agent accurately reports forwarding database entries after packets are sourced from PTF ports. It cross-checks DUT dataplane learning, control-plane FDB management, and SNMP telemetry consistency.

## 3. Detailed Breakdown of Sub-Testcases
### `test_snmp_fdb_send_tagged`
- **Intent & Flow**:
  - Gathers the running configuration and identifies all PortChannels.
  - Waits for every PortChannel (and its members) to reach the operational "Up" state using `is_port_channel_up`.
  - Builds the active VLAN member list from `running_vlan_ports_list`, then iteratively sends tagged ICMP packets from each PTF port for every permitted VLAN. Each packet uses a unique dummy MAC (`02:11:22:33:XX:YY`).
  - Flushes the dataplane cache and waits until all dummy MAC addresses appear as dynamic entries in `show mac` output (tracked via `get_fdb_dynamic_mac_count`).
  - Retrieves SNMP facts (via `get_snmp_facts`) and confirms that:
    - Every injected dummy MAC appears in the SNMP FDB table.
    - Each FDB entry maps to an SNMP interface whose name matches the expected physical port or PortChannel.
    - Counts of injected PortChannel-derived entries align with SNMP reports.
- **Relevance**: Demonstrates end-to-end validation that traffic learning propagates through the hardware/FDB pipeline and surfaces through SNMP, guaranteeing management-plane observability of Layer-2 state.

### Helper Functions & Fixtures
- `fdb_cleanup` (module-level, autouse): Clears pre-existing dynamic MAC entries to ensure the test measures only new learning events.
- `build_icmp_packet`: Crafts VLAN-tagged ICMP frames with controllable MAC/IP fields for deterministic learning behavior.
- `is_port_channel_up`: Confirms all PortChannels and member links are operational before traffic generation.
- `check_snmp_facts`: Encapsulates SNMP validation logic, comparing expected MAC/interface counts with SNMP-reported data.
- `get_fdb_dynamic_mac_count` / `fdb_table_has_no_dynamic_macs`: Utilities for counting/validating dynamic MAC entries via CLI output.

## 4. Dependencies and Prerequisites
- **Fixtures**:
  - `ptfadapter`, `duthosts`, `rand_one_dut_hostname`, `rand_selected_dut`, `tbinfo`, `ports_list`, `localhost`, `creds_all_duts` – standard SONiC pytest fixtures delivering DUT/PTF handles, topology metadata, and credentials.
  - Dual ToR-specific fixtures: `toggle_all_simulator_ports_to_rand_selected_tor_m`, `setup_standby_ports_on_rand_unselected_tor` ensure mux simulator state aligns with test expectations.
  - Autouse cleanups: `fdb_cleanup` (defined here) and imported fixtures such as `change_mac_addresses`, `setup_po2vlan`, `acl_rule_cleanup` prepare VLAN/PortChannel environments (actual setup performed by imported fixtures even though not referenced directly in function arguments).
- **Topology constraints**: Requires access to VLAN member interfaces and PortChannels; expects SNMP to be reachable via management IP.

## 5. Key Inputs and Parameters
- `DUMMY_MAC_PREFIX` (`02:11:22:33`): Prefix used to synthesize unique MAC addresses for learning validation.
- `config_facts['PORTCHANNEL']`: Determines the set of PortChannels expected to be operational and reflected in SNMP.
- VLAN membership data from `running_vlan_ports_list`: Drives which ports/VLAN IDs transmit packets.
- SNMP credentials from `creds_all_duts[duthost.hostname]['snmp_rocommunity']`: Authenticate SNMP GET operations.
- Host IP retrieved from inventory (`ansible_host`): Target address for SNMP queries.

## 6. External Libraries and Modules
- `pytest`: Test framework providing fixtures and markers.
- `ptf.testutils`: Generates and transmits crafted packets on PTF interfaces.
- `logging`, `pprint`: Logging utilities for debug output.
- SONiC helper modules:
  - `tests.common.utilities.wait_until`: Retry/timeout logic for asynchronous checks.
  - `tests.common.helpers.snmp_helpers.get_snmp_facts`: Fetches SNMP tables from the DUT.
  - `tests.common.helpers.portchannel_to_vlan` helpers (`running_vlan_ports_list`, `setup_po2vlan`, `acl_rule_cleanup`, `vlan_intfs_dict`, etc.): Manage VLAN-to-PortChannel mapping and environment preparation.
  - `tests.common.helpers.backend_acl`, `tests.common.fixtures.duthost_utils`, `tests.common.fixtures.ptfhost_utils`: Provide ACL setup, DUT fixture utilities, and PTF MAC adjustments as part of the overall L2 validation toolkit.
  - `tests.common.helpers.assertions.pytest_assert`: Consistent assertion wrapper with logging.

## 7. Unspecified Items
- Specific packet counts per interface, detailed mux simulator behavior, and external inventory parameters beyond the ones enumerated above are **Not specified** within this test file.
