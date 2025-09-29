# OSPF Test Plan Analyzer: `tests/ospf/test_ospf.py`

## 1. Topology Type
- **Topology:** `t0`.
- **Inference:** The module-level `pytestmark` applies `pytest.mark.topology('t0')`, indicating that the testbed must be the SONiC T0 topology with a single DUT connected to fanout (ToR) neighbors that can run routing daemons.

## 2. Overall Test Case Purpose
- **Goal:** Validate that Open Shortest Path First (OSPF) can replace Border Gateway Protocol (BGP) for route exchange between the DUT and its SONiC neighbors.
- **Context:** Within the SONiC pytest framework, the suite verifies that when OSPF is enabled on both the DUT and the neighboring SONiC VMs, former BGP-learned routes appear as OSPF routes and remain dynamically synchronized when neighbor-originated networks are added or removed. This demonstrates interoperability of FRR's OSPF implementation on SONiC devices and confirms routing resilience when changing control-plane protocols.

## 3. Detailed Breakdown of Sub-Testcases

### `test_ospf_neighborship`
- **Intent & Logic:**
  1. Reads BGP-learned prefixes gathered during the `ospf_setup` fixture.
  2. Checks whether `ospfd` is already running on the DUT; if not, it starts the daemon inside the BGP container, disables BGP, and configures OSPF to advertise each neighbor's /31 link network.
  3. Confirms that every neighbor reported by `show ip ospf neighbor` reaches the `Full` adjacency state.
  4. Parses the OSPF routing table and compares the learned OSPF prefixes against the original BGP prefixes captured before the migration.
- **Why It Matters:** Ensures that enabling OSPF preserves routing reachability previously supplied by BGP and that all neighbors form full adjacencies, validating the protocol hand-off.

### `test_ospf_dynamic_routing`
- **Intent & Logic:**
  1. On the first neighbor VM, configures a loopback interface and advertises it into OSPF.
  2. Ensures OSPF is configured on the DUT (starting `ospfd` and applying neighbor networks if required).
  3. Verifies both that OSPF adjacencies reach the `Full` state and that the new loopback route is installed on the DUT via the OSPF routing table.
  4. Removes the loopback interface on the neighbor, waits for convergence, and confirms the route disappears from the DUT.
- **Why It Matters:** Demonstrates OSPF's ability to learn and withdraw routes dynamically as neighbors originate or remove networks, proving correct control-plane updates beyond the initial migration.

### Helper Fixtures and Utilities
- **`ospf_setup` (module fixture):** Builds neighbor IP mapping from minigraph data, captures the DUT's existing BGP routes, and configures each neighbor VM to start `ospfd`, disable the original BGP session, and redistribute BGP routes into OSPF. It also reloads both DUT and neighbor configurations after the tests.
- **Other Fixtures Used:** `duthosts`, `rand_one_dut_hostname`, and `nbrhosts` provide access to the active DUT, random DUT selection, and neighbor host handles, respectively. These fixtures originate from the wider SONiC pytest framework. Their internal implementations are not shown here.

## 4. Dependencies and Prerequisites
- **Fixtures:** `ospf_setup`, `duthosts`, `rand_one_dut_hostname`, `nbrhosts` (all required). `ospf_setup` itself depends on SONiC neighbor type being `sonic`, the `tbinfo` testbed description, and FRR configuration access.
- **Topology Constraints:** Requires a T0 topology with SONiC-based neighbor VMs capable of running FRR and exposing BGP/OSPF sessions.
- **Services/Daemons:** Ability to start FRR `ospfd` within the DUT and neighbor BGP containers and to run `vtysh` configuration commands. SSH/API access to both DUT and neighbor hosts is assumed.

## 5. Key Inputs and Parameters
- **Neighbor Addresses (`setup_info['nbr_addr']`):** Derived from minigraph facts; used to apply `network x.x.x.x/31 area 0` statements on the DUT and neighbors.
- **Original BGP Prefixes (`setup_info['bgp_routes']`):** Captured before OSPF conversion to validate route parity after migration.
- **Loopback Network (`192.168.10.1/32`):** Added in the dynamic routing test to validate OSPF route advertisement and withdrawal.
- **Pytest Option `--neighbor_type`:** The fixtures skip the suite unless neighbors are SONiC-based (`neighbor_type == "sonic"`).
- **Testbed Metadata (`tbinfo`):** Supplies minigraph data (e.g., BGP neighbors) leveraged by `ospf_setup`.

## 6. External Libraries and Modules
- **`pytest`:** Provides the testing framework, fixtures, and markers.
- **`logging`:** Retrieves a module-level logger (unused in assertions but available for debug output).
- **`time`:** Introduces waits after reconfiguration to allow routing convergence.
- **`re`:** Parses routing table output to extract prefix strings.
- **SONiC Helper Modules (fixture scope):** `tests.common.config_reload` and `tests.common.helpers.multi_thread_utils.SafeThreadPoolExecutor` (imported in `conftest.py`) manage device configuration reloads and concurrent operations during teardown. These enable safe cleanup but are not directly used in `test_ospf.py`.

## 7. Unspecified Items
- Exact implementations of core fixtures (`duthosts`, `rand_one_dut_hostname`, `nbrhosts`, `tbinfo`) are **Not specified** within this file.
- The specific hardware layout of the T0 topology beyond the single DUT with SONiC neighbors is **Not specified** in the test file.
- Logging outputs or thresholds for convergence timing beyond the fixed `time.sleep(5)` waits are **Not specified**.
