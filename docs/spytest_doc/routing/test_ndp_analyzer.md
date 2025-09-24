# NDP Test Analyzer

## 1. Topology Type
- **Identified topology:** `D1T1:2` topology consisting of one DUT connected to two traffic-generator ports (TG1 and TG2).
- **Evidence & rationale:** The `ndp_module_hooks` fixture calls `st.ensure_min_topology("D1T1:2")`, ensuring a topology with one device under test (D1) and two tester links (T1P1, T1P2). The comments inside the test also describe "TG1-----DUT-----TG2", and testbed variables such as `vars.D1T1P1` and `vars.D1T1P2` are used to configure interfaces, confirming the single-DUT dual-TG layout.

## 2. Overall Test Case Purpose
- **High-level objective:** Validate IPv6 Neighbor Discovery Protocol (NDP) behavior on a SONiC device, covering dynamic neighbor learning, clearing the NDP table, and managing static neighbor entries.
- **Context within SONiC/SpyTest:** The test automates an IPv6 neighbor workflow using SpyTest fixtures and SONiC APIs. It ensures that a SONiC switch correctly learns neighbors from attached traffic generators, responds to `sonic-clear ndp`, and supports static neighbor entries—key elements for IPv6 reachability and control-plane correctness.

## 3. Detailed Breakdown of Sub-Testcases
### `test_ft_ipv6_neighbor_entry`
- **Intent & logic:**
  1. Collect initial NDP entries via `arp_obj.get_ndp_count` and expect dynamic neighbors learned through traffic-generator interfaces to meet `2 * data.count` entries (two ports, each generating `data.count` neighbors).
  2. Execute `arp_obj.clear_ndp_table` (equivalent to `sudo sonic-clear ndp`) and confirm that dynamic entries are flushed. If residual entries remain, the test verifies that they all show status `NOARP`, indicating unresolved neighbors rather than stale reachability.
  3. Configure a static NDP entry with `arp_obj.config_static_ndp` and ensure the static count increases, then remove the static entry.
  4. On success, report the test as passed.
- **Why it matters:** This subtest validates core IPv6 neighbor management behaviors—learning, clearing, and statically programming neighbors. Proper functionality is essential to maintaining accurate neighbor tables for IPv6 routing and connectivity.

### Helper Fixtures and Data
- **`ndp_module_hooks` (module-scoped, autouse):** Provisions the testbed, initializes traffic generators through `tgapi`, configures IPv6 addresses on DUT interfaces and VLAN, sets up traffic-generator interfaces, and performs cleanup by removing IPv6 and VLAN configurations after tests.
- **`ndp_func_hooks` (function-scoped, autouse):** Placeholder for per-test setup/teardown (currently no additional actions but ensures consistency for future extensions).
- **`data` (`SpyTestDict`):** Stores reusable configuration constants such as VLAN ID, IPv6 addresses, MAC addresses, counters, and control flags shared across test steps.

## 4. Dependencies and Prerequisites
- **Fixtures:**
  - `ndp_module_hooks` requires topology support (`st.ensure_min_topology("D1T1:2")`), traffic-generator handles (`tgapi.get_handles_byname`), and DUT access via `st.get_dut_names()`.
  - `ndp_func_hooks` ensures per-test consistency.
- **Topology constraints:** One SONiC DUT connected to at least two traffic-generator ports with VLAN capability on the second link.
- **Libraries/Modules:** SONiC API modules (`apis.switching.vlan`, `apis.routing.ip`, `apis.routing.arp`) must be available to configure interfaces and neighbors. The `filter_and_select` utility is required to filter NDP output when validating table clearing.

## 5. Key Inputs and Parameters
- **Topology variables:** `vars.D1T1P1`, `vars.D1T1P2`, and `vars.D1` from `st.get_testbed_vars()` specify DUT identifiers and port mappings drawn from `testbed.yaml`.
- **Configuration constants (`data`):**
  - `data.vlan_1`, `data.vlan_int_1`: VLAN configuration used on the DUT.
  - `data.local_ip6_addr`, `data.local_ip6_addr_rt`: IPv6 addresses applied to DUT interfaces and routing contexts.
  - `data.neigh_ip6_addr_gw`: IPv6 addresses provisioned on TG interfaces and for static neighbor tests.
  - `data.tg_mac1`, `data.tg_mac2`, `data.tg_mac3`: Source MAC addresses used for TG sessions and static neighbor entries.
  - `data.count`: Number of IPv6 addresses advertised by each TG interface, used to compute expected neighbor counts.
  - `data.clear_parallel`: Controls whether clean-up APIs run in parallel (false by default).

## 6. External Libraries and Modules
- **`pytest`:** Provides fixtures, markers, and test execution framework.
- **`spytest` package (`st`, `tgapi`, `SpyTestDict`):** Core SpyTest utilities for logging, DUT interaction, topology validation, traffic-generator access, and structured data storage.
- **`apis.switching.vlan` (`vlan_obj`):** Configures VLANs and memberships on the SONiC DUT.
- **`apis.routing.ip` (`ip_obj`):** Applies IPv6 addresses and clears IP configuration.
- **`apis.routing.arp` (`arp_obj`):** Manages NDP/ARP tables, retrieves neighbor counts, and configures static entries.
- **`utilities.common.filter_and_select`:** Filters command outputs for validation logic.

## 7. Unspecified Items
- Testbed hardware specifics (platform, ASIC type), software image versions, and traffic patterns beyond TG interface configuration are **not specified** in the test file.
