# QA Analysis: `test_ndp.py`

## 1. Topology Type and Inference
* The module fixture enforces `st.ensure_min_topology("D1T1:2")`, which requires one DUT (D1) connected to one traffic generator (T1) with two links. This corresponds to a TG–DUT–TG linear setup, aligning with the test bed comment `TG1-----DUT-----TG2` in the test body.【F:spytest/tests/routing/test_ndp.py†L25-L61】【F:spytest/tests/routing/test_ndp.py†L87-L92】

## 2. Overall Test Case Purpose
* Validate IPv6 Neighbor Discovery Protocol (NDP) handling by the DUT: ensure dynamic neighbor entries form, cache clearing via `sonic-clear ndp` removes dynamic records, and static neighbor entries can be created and removed successfully.【F:spytest/tests/routing/test_ndp.py†L87-L109】

## 3. Subtestcases and Contributions
* **`ndp_module_hooks` (module-level autouse fixture)** – Builds baseline IPv6 connectivity and VLAN environment, programs traffic-generator interfaces, and resets TG ports so subsequent validations operate on a prepared topology. Cleanup removes the IPv6 and VLAN configuration to leave the DUT clean.【F:spytest/tests/routing/test_ndp.py†L25-L66】 This setup is essential because the main test relies on those IPv6 interfaces and TG sessions to generate neighbor entries.
* **`ndp_func_hooks` (function-level autouse fixture)** – Placeholder for per-test setup/teardown (currently no operations). Maintains framework consistency for extending test-specific handling.【F:spytest/tests/routing/test_ndp.py†L68-L72】
* **`test_ft_ipv6_neighbor_entry`** – Executes the functional checks:
  * Displays current NDP entries and verifies that TG-driven dynamic neighbors are present; failure indicates neighbor discovery malfunction.【F:spytest/tests/routing/test_ndp.py†L93-L97】
  * Clears the NDP cache and confirms entries are removed (either zero or flagged as `NOARP`), proving cache flush behavior.【F:spytest/tests/routing/test_ndp.py†L98-L104】
  * Creates a static neighbor entry and checks it appears, then deletes it, confirming static NDP configuration support.【F:spytest/tests/routing/test_ndp.py†L105-L109】 These steps collectively validate dynamic learning, cache clearing, and static programming aspects of NDP.

## 4. Dependencies and Prerequisites
* Requires SpyTest framework objects (`st`, `tgapi`, `SpyTestDict`) and Pytest for fixtures/marks.【F:spytest/tests/routing/test_ndp.py†L3-L4】【F:spytest/tests/routing/test_ndp.py†L25-L32】
* Depends on the availability of SpyTest API modules for VLAN, IPv6 interface, and ARP/NDP configuration (`apis.switching.vlan`, `apis.routing.ip`, `apis.routing.arp`).【F:spytest/tests/routing/test_ndp.py†L5-L7】
* Needs a testbed supplying at least one SONiC DUT with two traffic-generator connections matching `D1T1:2`, exposing handles such as `vars.D1`, `vars.D1T1P1`, and `vars.D1T1P2`.【F:spytest/tests/routing/test_ndp.py†L25-L61】【F:spytest/tests/routing/test_ndp.py†L93-L109】
* Traffic generator integration must support `tgapi.get_handles_byname` and `tg_interface_config` to emulate IPv6 neighbors.【F:spytest/tests/routing/test_ndp.py†L29-L59】
* No additional prerequisites are specified beyond the default SpyTest environment and device access. If optional per-test setup were needed, `ndp_func_hooks` is prepared but currently empty.【F:spytest/tests/routing/test_ndp.py†L68-L72】

## 5. Key Inputs and Their Sources
* Static test parameters (`vlan_1`, IPv6 addresses, MACs, counts, flags) are defined in the module-level `SpyTestDict` and are intrinsic to the test script.【F:spytest/tests/routing/test_ndp.py†L11-L22】
* DUT and traffic-generator resource identifiers (`vars.D1`, `vars.D1T1P1`, `vars.D1T1P2`) originate from the SpyTest testbed definition accessed through `st.ensure_min_topology` and `st.get_testbed_vars()`, which map to entries in the deployed `testbed.yaml` (implicit).【F:spytest/tests/routing/test_ndp.py†L25-L61】【F:spytest/tests/routing/test_ndp.py†L93-L109】
* No additional CLI parameters or group variables are referenced. Not specified otherwise.

## 6. External Libraries and Roles
* **Pytest** – Provides fixture and marker infrastructure.【F:spytest/tests/routing/test_ndp.py†L1-L2】【F:spytest/tests/routing/test_ndp.py†L75-L82】
* **SpyTest Core (`st`, `tgapi`, `SpyTestDict`)** – Supplies topology management, device interaction, TG handle access, and structured data storage.【F:spytest/tests/routing/test_ndp.py†L3-L4】【F:spytest/tests/routing/test_ndp.py†L25-L61】
* **`apis.switching.vlan`** – Handles VLAN creation and membership on the DUT.【F:spytest/tests/routing/test_ndp.py†L5-L6】【F:spytest/tests/routing/test_ndp.py†L40-L41】【F:spytest/tests/routing/test_ndp.py†L65】
* **`apis.routing.ip`** – Configures IPv6 addresses on interfaces and removes them during cleanup.【F:spytest/tests/routing/test_ndp.py†L6-L7】【F:spytest/tests/routing/test_ndp.py†L39-L42】【F:spytest/tests/routing/test_ndp.py†L64】
* **`apis.routing.arp`** – Performs NDP show, clear, and static neighbor operations central to the validation.【F:spytest/tests/routing/test_ndp.py†L7-L8】【F:spytest/tests/routing/test_ndp.py†L93-L109】
* **`utilities.common.filter_and_select`** – Filters NDP output to verify entries are marked `NOARP` after clearing.【F:spytest/tests/routing/test_ndp.py†L9-L10】【F:spytest/tests/routing/test_ndp.py†L101-L104】
* No additional external libraries are used.
