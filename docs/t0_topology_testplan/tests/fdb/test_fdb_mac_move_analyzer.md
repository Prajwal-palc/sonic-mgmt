# Test Plan Analysis: `tests/fdb/test_fdb_mac_move.py`

## 1. Topology Type
- **Topology:** `t0`.
- **Inference:** The file sets a module-level `pytestmark` with `pytest.mark.topology('t0')`, explicitly binding the test to the T0 topology used in SONiC testbeds.

## 2. Overall Test Case Purpose
- **High-Level Goal:** Validate the robustness of Forwarding Database (FDB) handling on a SONiC DUT when MAC addresses move across VLAN member ports.
- **Context:** Within the SONiC pytest framework, this scenario stresses dynamic MAC learning by:
  - Populating large numbers of dummy MAC entries per VLAN member interface via crafted ARP requests sent from PTF ports.
  - Verifying that the DUT advertises an increased count of dynamic MAC addresses in the CRM (Container Resource Monitor) statistics.
  - Ensuring correct cleanup and dataplane flushing between loops, simulating repetitive MAC-move conditions.
- **Outcome:** Demonstrates that SONiC maintains accurate FDB state across iterative MAC movement events in a T0 topology.

## 3. Detailed Breakdown of Sub-Testcases
### `test_fdb_mac_move`
- **Intent:** Exercise repeated MAC learning and movement by generating dummy MAC addresses on every VLAN member port and confirming the DUT’s FDB tracks the learned entries.
- **Logic Flow:**
  1. Clean the DUT/neighbor FDB state via `fdb_cleanup` fixture helper.
  2. Determine loop count from the `get_function_completeness_level` fixture (`debug`, `basic`, etc.) to scale test intensity.
  3. Pull persistent configuration facts to map VLANs, port channels, and PTF port indices; reinitialize the PTF dataplane after topology adjustments.
  4. Build a VLAN member inventory limited to interfaces present and administratively up in the current T0 topology.
  5. Calculate the available FDB capacity via CRM counters to size the number of dummy MACs per member (`dummay_mac_count`).
  6. Generate dummy MAC addresses for each usable member with `get_fdb_dict`.
  7. For each loop iteration and port, send ARP requests from the PTF to provoke MAC learning on the DUT.
  8. Wait for the DUT’s dynamic MAC count to exceed the number of VLAN members, asserting successful FDB population.
  9. Flush the PTF dataplane and perform another cleanup before the next iteration.
- **Relevance:** Directly validates MAC-move resilience and DUT learning behavior, which is essential for correct L2 forwarding in access topologies.

### Helper: `get_fdb_dict`
- **Role:** Constructs a mapping from PTF port indices to lists of dummy MAC addresses to be advertised. It uses a base MAC per port and generates sequential addresses to simulate multiple hosts.
- **Relevance:** Encapsulates MAC generation logic, ensuring consistent data used by the main test when driving ARP traffic.

## 4. Dependencies and Prerequisites
- **Fixtures:** `ptfadapter`, `duthosts`, `fanouthosts`, `rand_one_dut_hostname`, `ptfhost`, `get_function_completeness_level`, and `rotate_syslog`. These supply access to the testbed topology, DUTs, fanout controls, PTF interfaces, and logging management.
- **Topology Constraints:** Requires a T0 topology with at least one VLAN configured and PTF port mappings that align with DUT ports (`ifaces_map`).
- **Utilities:** Relies on helper functions from `tests/fdb/utils.py` for FDB management and packet injection, and `tests.common` helpers for waiting and assertions.

## 5. Key Inputs and Parameters
- **Constants:** `TOTAL_FDB_ENTRIES`, `FDB_POPULATE_SLEEP_TIMEOUT`, `BASE_MAC_ADDRESS`, and `LOOP_TIMES_LEVEL_MAP` determine MAC counts, wait intervals, and loop scaling.
- **Dynamic Inputs:**
  - `get_function_completeness_level` fixture chooses test intensity (`debug`, `basic`, `confident`, etc.).
  - CRM resource counters (`get_crm_resources`) define the maximum number of MACs to inject per port.
  - `ptfhost.host.options['variable_manager'].extra_vars['ifaces_map']` supplies PTF-to-DUT port mappings.
  - Persistent config facts (`config_facts`) provide VLAN, port, and port-channel metadata.

## 6. External Libraries and Modules
- **Standard Library:** `logging`, `time`, `math`, and `collections.defaultdict` for logging, timing, calculations, and data structures.
- **Pytest:** `pytest` for test markers, fixtures, and assertions.
- **SONiC Test Utilities:**
  - `tests.common.utilities.wait_until` for polling conditions.
  - `tests.common.helpers.assertions.pytest_assert` for enhanced assertion handling.
  - `tests/fdb/utils` module functions: `MacToInt`, `IntToMac`, `fdb_cleanup`, `get_crm_resources`, `send_arp_request`, `get_fdb_dynamic_mac_count`, providing MAC manipulation, cleanup, CRM queries, and packet sending.

## 7. Unspecified Items
- Any further testbed-specific variables (e.g., inventory details beyond VLAN/port facts) or environmental prerequisites beyond those listed are **Not specified** in this file.
