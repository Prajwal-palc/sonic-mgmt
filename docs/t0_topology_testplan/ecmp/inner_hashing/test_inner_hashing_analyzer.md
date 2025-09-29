# Inner Hashing Test Analyzer

## 1. Topology Type
- **Topology:** `t0` topology as indicated by the module-level `pytestmark` that selects `pytest.mark.topology('t0')` for all tests in this file.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L18-L21】
- **Inference:** The explicit topology marker shows that the tests assume a T0 leaf-spine environment. Supporting fixtures from `conftest.py` derive VLAN members, LAG members, and minigraph facts that are characteristic of T0 setups (e.g., `T0_VLAN`, VLAN/LAG mappings), confirming the topology alignment.【F:tests/ecmp/inner_hashing/conftest.py†L54-L126】【F:tests/ecmp/inner_hashing/conftest.py†L200-L244】

## 2. Overall Test Case Purpose
- **High-level Goal:** Validate SONiC's Policy-Based Hashing (PBH) behavior for inner-packet hashing on encapsulated VXLAN and NVGRE traffic. The tests confirm that inner headers drive ECMP selection regardless of outer encapsulation, and that PBH rule edits maintain proper load distribution.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L1-L107】
- **Framework Context:** Within SONiC's ECMP test suite, this module ensures that dynamically configured PBH tables and statically pre-configured setups both produce balanced hashing across expected port groups, aligning with SONiC PBH and ECMP resiliency requirements. PTF dataplane validation and DUT counter checks tie the SONiC control-plane configuration to packet forwarding correctness.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L33-L105】【F:tests/ecmp/inner_hashing/conftest.py†L116-L199】【F:tests/ecmp/inner_hashing/conftest.py†L268-L343】

## 3. Detailed Breakdown of Sub-Testcases
### 3.1 `TestDynamicInnerHashing.test_inner_hashing`
- **Intent & Logic:**
  - Runs under the `dynamic_config` marker with an autouse fixture `setup_dynamic_pbh` that pushes PBH configuration onto the DUT at runtime.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L24-L35】
  - Logs parameters for each outer/inner IP version combination and symmetric hashing mode, builds input ranges for inner/outer IPs, and normalizes PTF balancing iterations based on completeness level.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L37-L63】
  - Executes the `inner_hash_test.InnerHashTest` PTF script with parameters describing expected FIB data, router MAC, VLAN/LAG ports, hash keys, encapsulation formats, and load-balancing thresholds.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L65-L89】
  - Clears PBH statistics before each run, then uses `retry_call` on `check_pbh_counters` to verify that PBH counters match expected distributions across encapsulation formats and hash keys.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L91-L105】【F:tests/ecmp/inner_hashing/conftest.py†L310-L343】
  - If the parameter combination matches randomly selected versions (`update_outer_ipver`, `update_inner_ipver`), obtains the `update_rule` fixture to swap PBH rule behavior, re-runs the PTF test, and re-verifies counters for the swapped mapping to validate runtime edits.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L107-L139】【F:tests/ecmp/inner_hashing/conftest.py†L344-L408】
- **Relevance:** Ensures that dynamically configured PBH responds correctly both initially and after rule updates, demonstrating operational flexibility and correctness during live configuration changes.

### 3.2 `TestStaticInnerHashing.test_inner_hashing`
- **Intent & Logic:**
  - Runs when the CLI option `--static_config` is supplied, skipping dynamic configuration; assumes PBH rules are pre-installed before the test.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L141-L170】【F:tests/ecmp/inner_hashing/conftest.py†L70-L95】
  - Similar to the dynamic test, calculates source/destination IP ranges, launches the same PTF `InnerHashTest` with parameters reflecting static PBH expectations, and captures logs for analysis.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L145-L170】
- **Relevance:** Validates that pre-existing PBH configurations sustain correct inner hashing without on-test modifications, ensuring regression coverage for statically managed deployments.

### Helper Fixtures and Parameterization
- `setup_dynamic_pbh`: Configures PBH tables, hash fields, and rules dynamically for T0 VLAN interfaces before dynamic tests.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L27-L35】【F:tests/ecmp/inner_hashing/conftest.py†L246-L309】
- `update_rule`: Temporarily swaps PBH rule match fields between IPv4/IPv6 combinations to test rule edit flows, then restores original settings after validation.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L107-L139】【F:tests/ecmp/inner_hashing/conftest.py†L344-L408】
- Module-level fixtures parameterize outer and inner IP versions and manage completeness-driven balancing thresholds, ensuring coverage across IPv4/IPv6 permutations.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L37-L79】【F:tests/ecmp/inner_hashing/conftest.py†L264-L343】

## 4. Dependencies and Prerequisites
- **Fixtures:** The tests rely on `duthost`, `ptfhost`, `tbinfo`, `vlan_ptf_ports`, `lag_mem_ptf_ports_groups`, `router_mac`, `hash_keys`, `outer_ipver`, `inner_ipver`, `symmetric_hashing`, `get_function_completeness_level`, and `update_rule`, all provided via `conftest.py` and common SONiC fixtures.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L33-L108】【F:tests/ecmp/inner_hashing/conftest.py†L96-L343】
- **Topology Constraints:** Requires a T0 testbed with VLAN members and LAG-capable ports to derive port groups and hashing expectations.【F:tests/ecmp/inner_hashing/conftest.py†L116-L244】
- **Pre-test Setup:** Dynamic tests expect to configure PBH on-the-fly; static tests require the `--static_config` option and pre-populated PBH tables to avoid reconfiguration.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L24-L170】【F:tests/ecmp/inner_hashing/conftest.py†L70-L95】

## 5. Key Inputs and Parameters
- **PTF Parameters:** `fib_info`, `router_mac`, VLAN/LAG port lists, hash keys, encapsulation formats, symmetric hashing flag, and IP ranges drive traffic generation and expected output in the PTF script.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L65-L170】
- **Balancing Controls:** `balancing_test_times` and `balancing_range` adjust the number of flows and acceptable variance based on completeness level (`--completeness_level`).【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L55-L79】【F:tests/ecmp/inner_hashing/conftest.py†L408-L411】
- **Randomized Rule Update Trigger:** `update_outer_ipver` and `update_inner_ipver` choose a specific outer/inner IP version pair to exercise PBH rule updates during dynamic runs.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L22-L24】【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L107-L139】
- **CLI Options:** `--static_config` toggles between dynamic and static suites; `--completeness_level` influences thoroughness. Additional PBH constants (hash keys, VXLAN/NVGRE parameters) are defined in `conftest.py` and shape DUT configuration.【F:tests/ecmp/inner_hashing/conftest.py†L16-L169】【F:tests/ecmp/inner_hashing/conftest.py†L70-L95】

## 6. External Libraries and Modules
- **`logging` / `random` / `datetime`:** Provide diagnostic logging, random selection for rule-update coverage, and timestamping for log files.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L7-L24】
- **`pytest` & `allure`:** Supply fixtures, markers, parameterization, and reporting steps for test orchestration and allure-based documentation.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L7-L35】【F:tests/ecmp/inner_hashing/conftest.py†L1-L95】
- **`retry.api.retry_call`:** Repeats PBH counter verification to accommodate telemetry latency.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L11-L105】
- **`tests.ptf_runner.ptf_runner`:** Launches the PTF dataplane test script against the DUT with specified parameters.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L12-L104】
- **`tests.ecmp.inner_hashing.conftest` helpers:** Provide configuration functions (`config_pbh`, `check_pbh_counters`, etc.) and fixtures to prepare the DUT and compute expectations.【F:tests/ecmp/inner_hashing/test_inner_hashing.py†L12-L105】【F:tests/ecmp/inner_hashing/conftest.py†L16-L408】

## 7. Unspecified Items
- **Explicit testbed inventory references:** Not specified.
- **Detailed PTF test implementation (`inner_hash_test.InnerHashTest`):** Not specified within this file.
- **Exact pass/fail thresholds beyond balancing range and counter equality tolerances:** Not specified.
