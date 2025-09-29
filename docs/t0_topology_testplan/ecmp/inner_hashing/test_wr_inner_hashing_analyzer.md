# Warm Reboot Inner Hashing Test Analyzer

## 1. Topology Type
- **Topology**: `t0` testbed. The module-level `pytestmark` applies the `topology('t0')` marker, constraining the suite to a single-DUT T0 setup with fanout leaf-spine neighbors.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L15-L18】
- **Inference**: The same marker is used across inner-hashing suites for VLAN-based T0 environments, and fixture usage (e.g., `vlan_ptf_ports`, `lag_mem_ptf_ports_groups`) assumes T0 VLAN membership derived from `tbinfo` and minigraph facts.【F:tests/ecmp/inner_hashing/conftest.py†L194-L218】

## 2. Overall Test Case Purpose
- **Goal**: Validate that SONiC's Policy Based Hashing (PBH) for tunneled traffic maintains expected inner-packet load-balancing behavior across warm reboots under both dynamically applied and statically pre-configured PBH settings.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L21-L123】
- **Context**: The suite targets ECMP inner-hashing correctness for overlay encapsulations (VXLAN/NVGRE) in T0 topologies. It leverages PBH configuration helpers to program hash fields and rules, builds FIB information for PTF validation, and runs the shared `inner_hash_test.InnerHashTest` PTF script concurrently with a DUT warm reboot, mirroring regression coverage in SONiC's pytest automation framework.【F:tests/ecmp/inner_hashing/conftest.py†L106-L191】【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L34-L82】

## 3. Detailed Breakdown of Sub-Testcases
### `TestWRDynamicInnerHashing.test_inner_hashing`
- **Intent**: After dynamically programming PBH tables via the class autouse fixture, trigger a warm reboot while PTF injects encapsulated traffic to verify that inner hash distribution and expected nexthop groups remain correct post-reboot.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L24-L82】
- **Logic**:
  - Autouse `setup_dynamic_pbh` configures PBH tables, hash fields, hash objects, and rules for VLAN ports before tests execute.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L24-L27】【F:tests/ecmp/inner_hashing/conftest.py†L335-L386】
  - Chooses a random encapsulation format (VXLAN or NVGRE) to reduce runtime, then derives inner/outer source-destination IP ranges using shared helpers.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L40-L46】【F:tests/ecmp/inner_hashing/conftest.py†L428-L435】
  - Adjusts PTF balancing iterations based on the optional `--completeness_level` knob and launches warm reboot and PTF runner threads in parallel to stress PBH resiliency.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L47-L81】
- **Relevance**: Confirms that dynamically applied PBH survives warm reboot transitions and continues to deliver deterministic hashing, guarding against regressions in configuration persistence and ECMP member selection.

### `TestWRStaticInnerHashing.test_inner_hashing`
- **Intent**: Exercise the same warm reboot hashing validation when PBH is presumed to be pre-configured (static mode), ensuring hash behavior does not regress for pre-provisioned deployments.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L85-L123】
- **Logic**:
  - Reuses shared fixtures to supply FIB data, VLAN/LAG port mappings, and hashing parameters without re-programming PBH dynamically.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L103-L118】【F:tests/ecmp/inner_hashing/conftest.py†L141-L275】
  - Runs warm reboot and PTF validation concurrently for both IPv4/IPv6 outer and inner combinations across the supported encapsulations list.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L88-L123】
- **Relevance**: Provides coverage for environments where PBH configuration is static, verifying warm reboot resilience irrespective of configuration workflow.

## 4. Dependencies and Prerequisites
- **Autouse PBH setup**: `setup` fixture backs up `config_db`, injects VXLAN switch settings, and reloads configuration on teardown to maintain DUT integrity.【F:tests/ecmp/inner_hashing/conftest.py†L106-L139】
- **FIB preparation**: `build_fib` extracts routing information, maps nexthops to PTF ports, and copies the data to the traffic generator, enabling PTF validation of forwarding paths.【F:tests/ecmp/inner_hashing/conftest.py†L141-L191】
- **Port topology fixtures**: `vlan_ptf_ports` and `lag_mem_ptf_ports_groups` depend on minigraph facts to map DUT interfaces to PTF indices, aligning traffic expectations with actual topology wiring.【F:tests/ecmp/inner_hashing/conftest.py†L194-L218】
- **Optional static/dynamic gating**: CLI option `--static_config` toggles collection to include only relevant classes (dynamic vs static markers).【F:tests/ecmp/inner_hashing/conftest.py†L79-L98】

## 5. Key Inputs and Parameters
- **Hash keys & ranges**: `hash_keys` fixture clones the standard PBH key list to drive PTF variation; IP range constants define the address space used for encapsulated flows.【F:tests/ecmp/inner_hashing/conftest.py†L18-L75】【F:tests/ecmp/inner_hashing/conftest.py†L271-L275】
- **Traffic profiles**: `outer_ipver` and `inner_ipver` parameterized fixtures iterate the suite across IPv4/IPv6 combinations, ensuring coverage of dual-stack encapsulation behavior.【F:tests/ecmp/inner_hashing/conftest.py†L288-L295】
- **Encapsulation controls**: `OUTER_ENCAP_FORMATS` list feeds both random selection (dynamic case) and exhaustive coverage (static case), while `NVGRE_TNI` and `VXLAN_PORT` supply protocol-specific match fields to PTF.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L40-L77】【F:tests/ecmp/inner_hashing/conftest.py†L32-L55】
- **Completeness level**: `get_function_completeness_level` reads the `--completeness_level` option to scale traffic iterations for thoroughness vs debug runs.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L47-L54】【F:tests/ecmp/inner_hashing/conftest.py†L561-L563】

## 6. External Libraries and Modules
- **PyTest & Allure**: Provide test structuring, markers, fixtures, and step annotations for reporting.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L3-L5】
- **Threading & logging**: Orchestrate parallel warm reboots and PTF runs while capturing diagnostic information.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L1-L2】【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L32-L82】
- **SONiC helpers**: `tests.common.reboot`, PBH configuration utilities, and `ptf_runner` abstract device control, configuration, and traffic execution mechanics.【F:tests/ecmp/inner_hashing/test_wr_inner_hashing.py†L8-L11】【F:tests/ecmp/inner_hashing/conftest.py†L335-L386】

## 7. Unspecified Items
- **Explicit hardware requirements**: Not specified.
- **PTF test implementation details**: Not specified within this file.
