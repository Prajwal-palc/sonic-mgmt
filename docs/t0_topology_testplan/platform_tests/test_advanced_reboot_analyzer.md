# Advanced Reboot Test Analyzer

## 1. Topology Type
- **Declared Topologies:** The module-level `pytestmark` constrains execution to `t0` and `t0-sonic` topologies via `pytest.mark.topology('t0', "t0-sonic")`. Dual ToR awareness is inferred from checks against `tbinfo['topo']['name']` containing `dualtor`.【F:tests/platform_tests/test_advanced_reboot.py†L27-L61】
- **Inference Method:** The test fixture `testing_config` inspects the selected DUT and skips single- or dual-TOR permutations depending on whether the testbed contains dual ToR mux cables, revealing that both single-TOR and dual-TOR T0 variants are supported.【F:tests/platform_tests/test_advanced_reboot.py†L47-L81】

## 2. Overall Test Case Purpose
- **Primary Goal:** Validate SONiC's advanced reboot workflows—fast reboot, warm reboot, and warm reboot under stress scenarios (MAC address movement and SAD cases)—for both single and dual ToR T0 environments. The tests confirm that the advanced reboot orchestration maintains control-plane and data-plane stability, ensures MAC learning behavior, and recovers correctly from injected failure scenarios.
- **Context:** Within the SONiC test framework, advanced reboot testing verifies the resiliency of platform reboot mechanisms, safeguarding traffic forwarding, neighbor relationships, and service continuity when orchestrated reboot commands are issued.

## 3. Detailed Breakdown of Sub-Testcases
### `test_fast_reboot`
- **Intent:** Invokes the `advancedReboot` fixture with `rebootType='fast-reboot'` to execute the standard fast reboot validation flow, including pre/post health checks and log analysis.【F:tests/platform_tests/test_advanced_reboot.py†L84-L98】
- **Relevance:** Ensures that fast reboot achieves expected downtime boundaries and service recovery, forming a baseline for advanced reboot reliability.

### `test_fast_reboot_from_other_vendor`
- **Intent:** Runs a fast reboot but simulates migration from a third-party NOS by flushing SONiC databases before reboot, using `other_vendor_nos=True` in `get_advanced_reboot` and calling `flush_dbs` on the DUT.【F:tests/platform_tests/test_advanced_reboot.py†L101-L118】
- **Relevance:** Validates that SONiC can perform a clean fast reboot even when starting from a factory-reset-like state, important for multi-vendor interoperability.

### `test_warm_reboot`
- **Intent:** Executes warm reboot testing. In dual ToR mode it toggles mux simulator ports to create asymmetric active/standby conditions before initiating the reboot, then runs the warm reboot workflow.【F:tests/platform_tests/test_advanced_reboot.py†L121-L152】
- **Relevance:** Confirms warm reboot resiliency under realistic dual ToR traffic steering, ensuring minimal impact on data plane forwarding.

### `test_warm_reboot_mac_jump`
- **Intent:** Performs warm reboot while permitting MAC address "jumping" (movement) to verify that MAC learning suppression during reboot prevents unwanted learn events and that learning resumes afterward.【F:tests/platform_tests/test_advanced_reboot.py†L155-L173】
- **Relevance:** Protects against MAC event storms or control-plane instability during warm reboot, ensuring correct SAI orchestration.

### `test_warm_reboot_sad`
- **Intent:** Parameterized over SAD (Stress And Diagnostics) cases. Retrieves preboot/in-boot failure injections via `get_sad_case_list` and runs warm reboot while applying those disturbances, ensuring recovery and post-test restoration.【F:tests/platform_tests/test_advanced_reboot.py†L178-L199】
- **Relevance:** Validates that warm reboot remains robust against predefined failure scenarios, safeguarding network resiliency.

## 4. Dependencies and Prerequisites
- **Fixtures:** Relies on numerous fixtures, including `get_advanced_reboot`, `verify_dut_health`, `advanceboot_loganalyzer`, `consistency_checker_provider`, `capture_interface_counters`, `testing_config`, `toggle_all_simulator_ports`, `toggle_simulator_port_to_upper_tor`, and more for setup, monitoring, and cleanup.【F:tests/platform_tests/test_advanced_reboot.py†L5-L199】
- **Topology Constraints:** Requires T0/T0-dual ToR environments with mux simulator control when dual ToR is involved, as enforced in `testing_config` and decorator marks.【F:tests/platform_tests/test_advanced_reboot.py†L27-L81】【F:tests/platform_tests/test_advanced_reboot.py†L121-L152】
- **Hardware Check:** Skips certain platforms (e.g., Arista 7050 without SSD and EOS neighbors) based on `check_if_ssd` results, ensuring hardware prerequisites are met.【F:tests/platform_tests/test_advanced_reboot.py†L35-L66】

## 5. Key Inputs and Parameters
- **Command-Line Options:** Uses `--neighbor_type` to determine if SSD requirement applies and `sad_case_list` to select SAD scenarios via `pytest_generate_tests`.【F:tests/platform_tests/test_advanced_reboot.py†L62-L118】【F:tests/platform_tests/test_advanced_reboot.py†L86-L118】【F:tests/platform_tests/test_advanced_reboot.py†L85-L118】
- **Fixture Parameters:** `testing_config` parameterizes single vs. dual ToR modes. `get_advanced_reboot` accepts parameters such as `rebootType`, `other_vendor_nos`, and `allow_mac_jumping`, tailoring the reboot workflow.【F:tests/platform_tests/test_advanced_reboot.py†L47-L173】
- **SAD Case Definitions:** `get_sad_case_list` pulls scenario definitions based on DUT and neighbor inventory, customizing failure injections per testbed.【F:tests/platform_tests/test_advanced_reboot.py†L189-L199】

## 6. External Libraries and Modules
- **Pytest:** Used for test definitions, fixtures, parameterization, and markers.【F:tests/platform_tests/test_advanced_reboot.py†L1-L199】
- **SONiC Test Utilities:** Imports from `tests.common` cover fixture utilities (`ptfhost_utils`, `duthost_utils`, `advanced_reboot`, `consistency_checker`, etc.), health checks, mux simulator controls, SAD case helpers, and device utilities; these provide orchestration hooks and verifications essential for advanced reboot validation.【F:tests/platform_tests/test_advanced_reboot.py†L5-L199】
- **Python Standard Library:** `logging` and `random` support logging and randomized selection in helper logic (e.g., choosing interfaces for mux toggling).【F:tests/platform_tests/test_advanced_reboot.py†L2-L3】【F:tests/platform_tests/test_advanced_reboot.py†L138-L145】

## 7. Unspecified Items
- **Detailed Contents of Imported Fixtures/Helpers:** Not specified in this file.
- **Exact reboot pass/fail criteria thresholds:** Not specified.
