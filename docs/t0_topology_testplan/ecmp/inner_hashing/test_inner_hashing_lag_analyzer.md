# Inner Hashing LAG Test Analyzer

## 1. Topology Type
- **Topology:** T0 topology with a single DUT connected to multiple T0 fanout neighbors.
- **Inference:** The module-level `pytestmark` applies `@pytest.mark.topology('t0')`, explicitly constraining the testbed to the T0 topology. 【F:tests/ecmp/inner_hashing/test_inner_hashing_lag.py†L18-L21】

## 2. Overall Test Case Purpose
- **Goal:** Validate dynamic inner-packet hashing behaviour for traffic that traverses LAG members on a SONiC DUT.
- **Context:** The test configures LAG-based PBH (Policy-Based Hashing) rules and then uses a PTF test to ensure inner packet fields drive balanced traffic distribution across LAG members, followed by PBH counter verification. This fits within SONiC ECMP validation, ensuring hashing correctness for encapsulated flows handled by SpyTest/PTF infrastructure. 【F:tests/ecmp/inner_hashing/test_inner_hashing_lag.py†L10-L70】

## 3. Detailed Breakdown of Sub-Testcases
### `TestDynamicInnerHashingLag`
A test class marked with `@pytest.mark.dynamic_config` to indicate dynamic configuration is required. It includes an auto-used module-scope fixture that configures LAG and PBH before executing the PTF-driven validation. 【F:tests/ecmp/inner_hashing/test_inner_hashing_lag.py†L23-L39】

#### `test_inner_hashing`
- **Intent & Logic:**
  - Logs the hashing scenario (outer/inner IP versions and symmetric hashing setting).
  - Computes timestamped log file paths.
  - Retrieves source/destination IP ranges for both outer and inner headers via helper functions.
  - Derives balancing thresholds based on the completeness level (debug vs. thorough).
  - Invokes `ptf_runner` to execute `inner_hash_test.InnerHashTest` with detailed parameters including FIB info, router MAC, VLAN port lists, expected LAG port groups, hash keys, encapsulation formats, and PTF queue configuration.
  - After PTF execution, repeatedly calls `check_pbh_counters` with retries to confirm PBH statistics reflect expected hashing distribution.
- **Relevance:** Confirms that the dynamically configured PBH LAG rules achieve balanced inner-packet hashing across LAG members under different encapsulation scenarios, which is essential for ECMP/LAG resiliency and load distribution. 【F:tests/ecmp/inner_hashing/test_inner_hashing_lag.py†L29-L70】

### Helper Fixture: `setup_dynamic_pbh`
- **Role:** Automatically configures required LAG settings (`setup_lag_config`) and applies PBH configuration (`config_pbh_lag`) before tests run, ensuring the DUT is in the expected state for hashing validation. 【F:tests/ecmp/inner_hashing/test_inner_hashing_lag.py†L25-L37】

## 4. Dependencies and Prerequisites
- **Fixtures:**
  - `duthost`, `lag_port_map`, `lag_ip_map`, `hash_keys`, `ptfhost`, `outer_ipver`, `inner_ipver`, `router_mac`, `vlan_ptf_ports`, `symmetric_hashing`, `lag_mem_ptf_ports_groups`, `get_function_completeness_level` – provided by broader ECMP inner hashing test infrastructure (definitions not shown). 【F:tests/ecmp/inner_hashing/test_inner_hashing_lag.py†L25-L70】
- **Topology Constraint:** T0 topology via `pytest.mark.topology('t0')`. 【F:tests/ecmp/inner_hashing/test_inner_hashing_lag.py†L18-L21】
- **PBH/LAG Config Helpers:** `setup_lag_config` and `config_pbh_lag` imported from `tests.ecmp.inner_hashing.conftest` supply configuration routines to prepare the DUT. 【F:tests/ecmp/inner_hashing/test_inner_hashing_lag.py†L13-L37】

## 5. Key Inputs and Parameters
- **Hashing Controls:** `hash_keys`, `symmetric_hashing` – determine which packet fields influence hashing and whether symmetric behavior is enforced.
- **Traffic Profiles:** `outer_ipver`, `inner_ipver`, `inner_src_ip_range`, `inner_dst_ip_range`, `outer_src_ip_range`, `outer_dst_ip_range` – control encapsulation layers exercised during PTF runs.
- **Topology Data:** `vlan_ptf_ports`, `lag_mem_ptf_ports_groups`, `lag_port_map`, `lag_ip_map` – describe PTF-facing VLAN ports and LAG membership.
- **Infrastructure Paths:** `FIB_INFO_FILE_DST`, `VXLAN_PORT`, `PTF_QLEN`, `OUTER_ENCAP_FORMATS`, `NVGRE_TNI` – constants pointing to route tables, VXLAN parameters, queue sizes, and encapsulation formats used by the PTF script.
- **Execution Settings:** `get_function_completeness_level` influences `balancing_test_times` and `balancing_range`; `router_mac` identifies the DUT MAC; generated log file names track PTF output. 【F:tests/ecmp/inner_hashing/test_inner_hashing_lag.py†L13-L70】

## 6. External Libraries and Modules
- **`logging`** – structured logging of test execution details.
- **`pytest`** – test framework providing fixtures, markers, and assertions.
- **`allure`** – reporting integration for step annotations.
- **`datetime`** – timestamp generation for log files.
- **`retry.api.retry_call`** – retry mechanism ensuring PBH counter checks allow for propagation delays.
- **`tests.ptf_runner.ptf_runner`** – helper to execute PTF scripts from pytest.
- **`tests.ecmp.inner_hashing.conftest` utilities** – provide IP range helpers, constants, and configuration routines for PBH/LAG.
These imports collectively enable configuration, traffic generation, result validation, and reporting for the hashing test. 【F:tests/ecmp/inner_hashing/test_inner_hashing_lag.py†L10-L70】

## 7. Unspecified Items
- Definitions of fixtures (e.g., `hash_keys`, `lag_port_map`) and their data sources are **Not specified** within this file.
- Detailed structure of the PTF test `inner_hash_test.InnerHashTest` is **Not specified** in the test case.
