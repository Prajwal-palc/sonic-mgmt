# Test Plan Analysis: `tests/fdb/test_fdb_mac_expire.py`

## 1. Topology Type
- **Topology**: T0 (with markers also covering `m0` and `mx`).
- **Inference**: The module-level `pytestmark` applies `pytest.mark.topology('t0', 'm0', 'mx')`, showing the test is intended for the T0-style topology family (standard T0 and its Mellanox variants). The use of T0 fixtures such as `tbinfo` and references to minigraph VLAN and port-channel data match common T0 deployments where a single DUT connects to multiple TOR-facing neighbors.【F:tests/fdb/test_fdb_mac_expire.py†L10-L13】【F:tests/fdb/test_fdb_mac_expire.py†L78-L101】

## 2. Overall Test Case Purpose
- **Goal**: Validate that the SONiC FDB aging timer behaves as configured and that MAC entries expire from the DUT after the aging interval, even under different refresh behaviors.
- **Context**: Within SONiC QA, FDB correctness ensures proper L2 forwarding and resource cleanup. This test updates the `fdb_aging_time`, injects dummy MAC entries via PTF traffic, and confirms that those entries are removed after the timer expires, safeguarding against stale MAC state that could disrupt forwarding or consume resources.【F:tests/fdb/test_fdb_mac_expire.py†L18-L72】【F:tests/fdb/test_fdb_mac_expire.py†L116-L165】

## 3. Detailed Breakdown of Sub-Testcases
- **`testFdbMacExpire`**
  - **Intent**: Parameterized over `refresh_type` to cover scenarios where FDB refresh is disabled or triggered via destination MAC refresh. The test configures the DUT aging timer, runs a PTF script to populate dummy MAC entries, waits for the configured timer, polls the FDB table, and asserts that the dummy MAC entries have aged out.【F:tests/fdb/test_fdb_mac_expire.py†L149-L165】
  - **Logic**:
    1. Reads the `--fdb_aging_time` CLI option to set the target aging interval.
    2. Builds PTF parameters including topology name, DUT router MAC, dummy MAC prefix, refresh behavior, and aging time.
    3. Calls `self.__runPtfTest` to trigger `fdb_mac_expire_test.FdbMacExpireTest` on the PTF host, which installs dummy MAC entries.
    4. Sleeps for the aging time, then polls the FDB table at 15-second intervals until the timeout to ensure the entries are removed.
    5. Uses `pytest_assert` to fail the test if any dummy MAC entries persist after the expected expiration window.【F:tests/fdb/test_fdb_mac_expire.py†L116-L165】
  - **Relevance**: Demonstrates that SONiC honors the configured FDB aging time across different refresh behaviors, directly supporting the module’s high-level purpose of validating MAC expiry handling.

- **Supporting Helpers and Fixtures**
  - **Private helper methods (`__getFdbTableCount`, `__loadSwssConfig`, `__deleteTmpSwitchConfig`, `__runPtfTest`)**: Provide reusable logic for querying MAC entries, reloading SWSS configuration, managing temporary switch configuration files, and invoking PTF tests. These utilities simplify the test workflow and ensure consistent handling of DUT state and validation steps.【F:tests/fdb/test_fdb_mac_expire.py†L28-L76】【F:tests/fdb/test_fdb_mac_expire.py†L116-L139】
  - **Fixtures (`copyFdbInfo`, `clearSonicFdbEntries`, `validateDummyMacAbsent`, `prepareDut`)**: Automatically prepare and clean up the environment by copying FDB templates to the PTF host, clearing existing FDB entries, verifying dummy MAC absence, and updating/restoring the DUT’s SWSS configuration with the desired aging time. These are critical prerequisites that isolate the test from external state and ensure reproducibility.【F:tests/fdb/test_fdb_mac_expire.py†L78-L145】

## 4. Dependencies and Prerequisites
- **Fixtures**: `duthosts`, `rand_one_dut_hostname`, `rand_selected_dut`, `ptfhost`, `tbinfo`, and `request` are required to interact with the DUT/PTF and access topology metadata. Autouse fixtures manage DUT preparation, FDB cleanup, and template distribution.【F:tests/fdb/test_fdb_mac_expire.py†L78-L165】
- **Topology Constraints**: Requires a single-DUT topology supporting VLANs/port-channels (typical T0) because the fixtures expect minigraph VLAN and port-channel data for the PTF template.【F:tests/fdb/test_fdb_mac_expire.py†L90-L106】
- **Configuration Access**: Needs permission to copy and modify `/etc/swss/config.d/switch.json` within the SWSS container to adjust `fdb_aging_time`, and to execute `sonic-clear` and `swssconfig` commands on the DUT.【F:tests/fdb/test_fdb_mac_expire.py†L38-L72】【F:tests/fdb/test_fdb_mac_expire.py†L122-L144】

## 5. Key Inputs and Parameters
- **`--fdb_aging_time` CLI option**: Determines the aging interval applied during the test; used both for DUT configuration and wait logic.【F:tests/fdb/test_fdb_mac_expire.py†L123-L140】【F:tests/fdb/test_fdb_mac_expire.py†L149-L165】
- **PTF Parameters**: `testbed_type`, `router_mac`, `fdb_info`, `dummy_mac_prefix`, `refresh_type`, `aging_time`, `kvm_support` dictate how the PTF script generates traffic and validates MAC aging behavior. These derive from DUT facts, fixtures, and class constants.【F:tests/fdb/test_fdb_mac_expire.py†L149-L159】
- **Class Constants**: `DUMMY_MAC_PREFIX`, `FDB_INFO_FILE`, and `POLLING_INTERVAL_SEC` define the MAC pattern, PTF configuration path, and polling cadence for verifying FDB expiration.【F:tests/fdb/test_fdb_mac_expire.py†L24-L27】【F:tests/fdb/test_fdb_mac_expire.py†L160-L165】

## 6. External Libraries and Modules
- **Standard Libraries**: `logging` for runtime logging; `time` for sleep intervals and timing logic.【F:tests/fdb/test_fdb_mac_expire.py†L1-L3】【F:tests/fdb/test_fdb_mac_expire.py†L161-L165】
- **Pytest**: Core testing framework providing markers, fixtures, parameterization, and assertion helpers.【F:tests/fdb/test_fdb_mac_expire.py†L2-L3】【F:tests/fdb/test_fdb_mac_expire.py†L10-L13】【F:tests/fdb/test_fdb_mac_expire.py†L137-L165】
- **SONiC Test Utilities**:
  - `tests.common.helpers.assertions.pytest_assert` for enhanced assertion handling with logging.【F:tests/fdb/test_fdb_mac_expire.py†L5-L6】【F:tests/fdb/test_fdb_mac_expire.py†L138-L165】
  - `tests.common.fixtures.ptfhost_utils.copy_ptftests_directory` (imported for side effects) ensures PTF tests are available on the PTF host.【F:tests/fdb/test_fdb_mac_expire.py†L6-L8】
  - `tests.ptf_runner.ptf_runner` to execute the PTF test cases from within pytest.【F:tests/fdb/test_fdb_mac_expire.py†L7-L8】【F:tests/fdb/test_fdb_mac_expire.py†L60-L75】

## 7. Unspecified Items
- **Testbed YAML specifics**: Not specified.
- **Exact PTF test implementation (`fdb_mac_expire_test.FdbMacExpireTest`)**: Not specified within this file.
- **Default value of `--fdb_aging_time`**: Not specified.
