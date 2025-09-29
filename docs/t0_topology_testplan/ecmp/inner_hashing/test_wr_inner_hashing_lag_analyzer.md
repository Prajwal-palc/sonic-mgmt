# Test Analyzer: `tests/ecmp/inner_hashing/test_wr_inner_hashing_lag.py`

## 1. Topology type
- **Topology:** `t0` fabric with VLAN access ports and port-channels.
- **Evidence:** The module-level `pytestmark` explicitly tags the test with `pytest.mark.topology('t0')`, indicating it runs on a T0 topology that features leaf-spine emulation with server-facing VLANs and LAG members.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing_lag.py†L15-L33】
- **Inference:** The reliance on VLAN member ports and dynamically created port-channels in fixtures such as `vlan_ptf_ports` and `lag_port_map` further confirms the expectation of a T0 testbed where access-facing interfaces are available for bonding into LAGs.【F:tests/ecmp/inner_hashing/conftest.py†L195-L244】

## 2. Overall test case purpose
- **High-level goal:** Validate that SONiC maintains correct inner-packet hashing behavior for encapsulated traffic over LAG members during a warm reboot when PBH (Port-Based Hashing) is configured dynamically.
- **Context:** The test suite configures PBH rules for VXLAN/NVGRE encapsulated flows, builds FIB information, and drives traffic from a PTF host while the DUT experiences a warm reboot. The objective is to ensure ECMP load-balancing decisions remain consistent and resilient across the reboot cycle, safeguarding overlay underlay hashing correctness in SONiC deployments.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing_lag.py†L31-L83】【F:tests/ecmp/inner_hashing/conftest.py†L298-L425】
- **Framework alignment:** Within SONiC's pytest infrastructure, this test belongs to the ECMP inner hashing validation plan, leveraging shared fixtures to manipulate PBH configuration and collect FIB entries, aligning with regression coverage for warm reboot scenarios.

## 3. Detailed breakdown of sub-testcases
### `TestWRDynamicInnerHashingLag.test_inner_hashing`
- **Intent & Logic:**
  - Starts by logging the outer/inner IP version combination and whether symmetric hashing is expected, then prepares a per-run PTF log file.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing_lag.py†L31-L39】
  - Randomly selects one encapsulation format (VXLAN or NVGRE) to exercise while retrieving source/destination IP ranges for both outer and inner headers via shared helpers.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing_lag.py†L41-L47】
  - Adjusts traffic iteration counts based on the requested completeness level to balance runtime versus coverage.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing_lag.py†L48-L55】
  - Launches a background thread to issue a warm reboot on the DUT, overlapping it with traffic generation executed by `ptf_runner` using PBH-aware parameters such as expected LAG member groups, hash keys, VXLAN port, NVGRE TNI, and symmetric hashing flag.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing_lag.py†L57-L83】
  - Waits for the reboot thread to finish, ensuring hashing correctness is validated across the reboot window.
- **Relevance:** This scenario directly tests warm-reboot resilience of PBH-based inner hashing on LAGs, a critical aspect of overlay networks where consistent flow distribution is mandatory for stability and performance.

### Class-level autouse fixture `setup_dynamic_pbh`
- **Role:** Automatically removes ACL dependencies, builds temporary LAG configurations, and pushes PBH table/hash/rule configuration before tests execute, establishing the dynamic PBH environment required by the test.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing_lag.py†L24-L29】【F:tests/ecmp/inner_hashing/conftest.py†L298-L425】
- **Importance:** Ensures the DUT is configured with the specific PBH rules that the PTF traffic is designed to exercise, making the inner hashing validation meaningful.

## 4. Dependencies and prerequisites
- **Pytest fixtures:**
  - Environment-wide fixtures (`setup`, `teardown`, `build_fib`) create VXLAN switch context, preserve/restores `config_db`, and export FIB data for the PTF runner.【F:tests/ecmp/inner_hashing/conftest.py†L106-L191】
  - Topology-derived fixtures (`vlan_ptf_ports`, `lag_mem_ptf_ports_groups`, `lag_port_map`, `lag_ip_map`) map DUT interfaces and LAG members to PTF ports, a prerequisite for accurate traffic expectations.【F:tests/ecmp/inner_hashing/conftest.py†L195-L263】
  - Parameter fixtures (`outer_ipver`, `inner_ipver`, `symmetric_hashing`, `hash_keys`, `router_mac`) feed protocol combinations and device metadata into the test.【F:tests/ecmp/inner_hashing/conftest.py†L266-L295】
- **PTF infrastructure:** Requires the `ptf_runner` utility and PTF host connectivity to transmit encapsulated traffic sequences using generated FIB and port maps.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing_lag.py†L60-L82】
- **Warm reboot capability:** Utilizes the `reboot` helper to trigger a warm reboot via threading, so the DUT must support SONiC warm reboot procedures.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing_lag.py†L57-L58】

## 5. Key inputs and parameters
- **Hash and traffic parameters:** `HASH_KEYS`, `OUTER_ENCAP_FORMATS`, IP ranges, VXLAN/NVGRE protocol constants define what traffic variations the PTF script will exercise and how PBH rules match them.【F:tests/ecmp/inner_hashing/conftest.py†L18-L76】
- **PBH configuration commands:** Command templates such as `ADD_PBH_TABLE_CMD`, `ADD_PBH_RULE_BASE_CMD`, and hash field definitions control how PBH tables and rules are pushed to the DUT before testing.【F:tests/ecmp/inner_hashing/conftest.py†L58-L117】【F:tests/ecmp/inner_hashing/conftest.py†L298-L425】
- **Runtime knobs:** `get_function_completeness_level` fixture toggles between thorough and debug modes, affecting the number of traffic iterations and acceptable balancing range, thereby tuning validation depth versus duration.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing_lag.py†L48-L55】

## 6. External libraries and modules
- **Standard libraries:** `logging`, `threading`, `random`, and `datetime` manage diagnostics, concurrency, randomized encapsulation selection, and timestamped artifacts.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing_lag.py†L1-L39】
- **PyTest & Allure:** PyTest drives fixture management and parametrization, while Allure step contexts annotate configuration phases for reporting.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing_lag.py†L3-L33】【F:tests/ecmp/inner_hashing/conftest.py†L1-L139】
- **SONiC helpers:** `tests.common.reboot`, `setup_lag_config`, `config_pbh_lag`, and `ptf_runner` provide SONiC-specific utilities to reboot devices, manipulate LAG/PBH settings, and run PTF-based traffic checks.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing_lag.py†L8-L83】【F:tests/ecmp/inner_hashing/conftest.py†L298-L425】

## 7. Unspecified items
- **Testbed inventory sources:** The specific `testbed.yaml` entries, group variables, or CLI parameters beyond the documented fixtures are not specified within this test file or its shared `conftest.py`. Explicit hardware SKU requirements, neighbor counts, or minigraph details are also not specified.
