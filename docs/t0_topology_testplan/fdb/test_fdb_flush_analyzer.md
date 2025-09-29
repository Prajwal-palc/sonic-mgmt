# FDB Flush Test Plan Analysis

## 1. Topology Type
- **Topology Markers:** The module-level `pytestmark` declares `pytest.mark.topology('t0', 'm0', 'mx')`, indicating the test is designed to run on topologies that provide full layer-2/3 connectivity typical of T0, single ToR (m0), or multi-Tier MX setups.
- **Inference:** These topology tags come from the pytest topology fixture system. They signal that the test requires a fabric with VLANs and fanout connectivity to exercise MAC learning and flushing behaviors across multiple interfaces.

## 2. Overall Test Case Purpose
- **High-Level Goal:** Validate that SONiC's FDB (Forwarding Database) operations—dynamic learning, static entry programming, interface shutdown/startup, and FDB flush—execute cleanly without generating new core files on the DUT.
- **Context in SONiC Automation:** Ensures the robustness of SWSS and related FDB orchestration during common operational workflows (e.g., swssconfig pushes, `sonic-clear fdb`, interface flaps). This contributes to regression coverage for data-plane resiliency and control-plane stability in the SONiC QA test suite.

## 3. Detailed Breakdown of Sub-Testcases
### `testFdbFlush`
- **Parameterization:** Runs once per `flush_type` in `["dynamic", "static", "interface", "mix"]`.
- **Flow:**
  1. Calls `prepare_test` to clean FDB entries, record existing core dumps, select three operational interfaces randomly, and generate static FDB JSON configs that are copied to the DUT.
  2. Depending on `flush_type`, performs dynamic FDB creation via a PTF traffic script, pushes static FDB entries with `swssconfig`, and/or shuts down interfaces.
  3. Regardless of the scenario, clears dynamic entries, removes static entries, and brings interfaces back up.
  4. Re-checks core files to ensure no new dumps were produced; fails if new core files are detected.
- **Relevance:** Demonstrates that various FDB flushing paths do not destabilize the system or leave residual crash artifacts, covering both dynamic learning and configuration-driven scenarios.

### Helper Methods and Fixtures
- **Lifecycle Fixtures (`autouse=True`):**
  - `copyFdbInfo` prepares PTF-side topology variables and drops `fdb_info.txt` onto the PTF host.
  - `clearSonicFdbEntries` clears the DUT FDB table before and after the class.
  - `validateDummyMacAbsent` asserts that no residual dummy MAC entries exist prior to execution.
  - `prepareDut` backs up and modifies `swss` switch configuration (aging timer) before tests and restores it afterwards, also cleaning temporary files.
- **Utility Methods:** Functions such as `prepare_test`, `dynamic_fdb_oper`, `static_fdb_oper`, `checkDutCorefiles`, and `create_fdb_oper_files` orchestrate setup/teardown and data-plane interactions required by the main test.
- **Support Routine:** The imported `fdb_cleanup` helper ensures a clean FDB state per iteration, while `ptf_runner` executes traffic scripts on the PTF host to generate dynamic MAC learning.

## 4. Dependencies and Prerequisites
- **Fixtures:** `duthosts`, `rand_one_dut_hostname`, `ptfhost`, `ptfadapter`, `fanouthosts`, `tbinfo`, and `request` provide device handles, platform metadata, and context. Class fixtures rely on these to configure DUT/PTF state automatically.
- **Topology Requirements:** Needs at least three operational DUT interfaces to select target ports; relies on a fanout environment for traffic generation (`fanouthosts`).
- **Artifacts and Tools:** Requires `fdb/files/fdb.j2` template and ability to copy files between control host, DUT, and PTF. Utilizes Docker access to the `swss` container for swssconfig operations.

## 5. Key Inputs and Parameters
- **Flush Types (`FLUSH_TYPES`):** Drives the scenario under test (dynamic learning, static programming, interface flap, or combinations).
- **FDB JSON Paths:** `FDB_SET_JSON_FILE` and `FDB_DEL_JSON_FILE` determine where static entry configs are stored (`/tmp/` locally and `/etc/sonic/` on the DUT).
- **Dummy MAC Prefix & Aging Time:** `DUMMY_MAC_PREFIX` used to verify absence/presence of test entries; `fdb_aging_time` set to 60 seconds within `prepareDut` to control learning behavior.
- **PTF Parameters:** `tbinfo['topo']['name']`, `duthost.facts['router_mac']`, and template-generated FDB information guide the PTF traffic generation.
- **Interface Selection:** Random sampling of three up interfaces from `duthost.get_interfaces_status()` ensures variability while requiring sufficient operational links.

## 6. External Libraries and Modules
- **Standard Libraries:** `logging`, `pytest`, `json`, `random`, `os` for logging, parameterization, serialization, randomness, and file operations.
- **Test Utilities:**
  - `pytest_assert` for expressive assertion messages.
  - `copy_ptftests_directory` fixture ensures PTF test assets are present (imported for side-effect).
  - `ptf_runner` to execute Python-based PTF traffic tests.
  - `fdb_cleanup` (local `tests/fdb/utils.py`) to reset FDB state across DUT and fanouts.
- **Ansible Host APIs:** Methods like `duthost.shell`, `duthost.command`, `duthost.copy`, `duthost.replace`, and `duthost.get_extended_minigraph_facts` come from the Sonic-mgmt Ansible host abstractions, enabling device configuration and inspection.

## 7. Unspecified Items
- **Testbed Inventory Source:** Specific `testbed.yaml` entries or variable names beyond those accessed through `tbinfo` are not specified.
- **Pass/Fail Thresholds Beyond Core Files:** Additional success metrics (e.g., MAC table counts post-flush) are not specified.
