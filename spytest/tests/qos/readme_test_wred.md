# WRED QoS SpyTest Review

## 1. Topology
- **Topology type:** The module-level fixture ensures a minimum topology of `"D1T1:3"`, which denotes one DUT (`D1`) connected to a single traffic generator (`T1`) with three traffic-generator ports (`P1`, `P2`, `P3`). This inference comes from the `st.ensure_min_topology("D1T1:3")` call and the subsequent retrieval of `T1D1P1`, `T1D1P2`, and `T1D1P3` handles for traffic generation.【F:spytest/tests/qos/test_wred.py†L29-L71】

## 2. Overall Test Purpose
- **Goal:** Validate that Weighted Random Early Detection (WRED) functionality operates correctly under configured DSCP-to-TC and TC-to-queue mappings, ensuring traffic is classified to the expected queues and that green drop counters increment appropriately when thresholds are exceeded.【F:spytest/tests/qos/test_wred.py†L124-L179】

## 3. Subtestcases
- **Module setup (`wred_module_hooks`):** Prepares DUT and traffic generator by applying WRED/ECN configuration, acquiring traffic-generator handles, resetting statistics, and creating three traffic streams (egress VLAN learning, DSCP 8 flow, DSCP 24 flow). This setup is essential for establishing the environment in which WRED behavior will be exercised.【F:spytest/tests/qos/test_wred.py†L29-L71】
- **Per-test fixture (`wred_func_hooks`):** Autouse function fixture reserved for per-test setup/teardown; currently a no-op, but enforces structure for additional per-test requirements if added later.【F:spytest/tests/qos/test_wred.py†L78-L84】
- **Helper `wred_running_config`:** Confirms that the WRED profile is present in the running configuration before executing traffic tests, ensuring the DUT has the correct drop thresholds configured.【F:spytest/tests/qos/test_wred.py†L87-L90】
- **Helper `configuring_tc_to_queue_map`:** Programs TC-to-queue mappings so DSCP classification can direct packets into the intended egress queues, which is fundamental for observing queue-specific WRED behavior.【F:spytest/tests/qos/test_wred.py†L91-L93】
- **Helper `configuring_dscp_to_tc_map`:** Establishes DSCP-to-TC mapping, allowing ingress traffic differentiation that feeds into the TC-to-queue configuration, directly impacting WRED queue selection.【F:spytest/tests/qos/test_wred.py†L94-L96】
- **Helper `binding_queue_map_to_interfaces`:** Binds QoS maps to all three interfaces linked to the traffic generator, ensuring that both matched and unmatched flows experience the configured QoS behavior.【F:spytest/tests/qos/test_wred.py†L97-L100】
- **Helper `fdb_config`:** Sets MAC aging time to a deterministic value and verifies it, preventing MAC aging from interfering with FDB-dependent validation steps.【F:spytest/tests/qos/test_wred.py†L102-L106】
- **Helper `vlan_config`:** Creates the VLAN under test and adds all traffic-generator ports as tagged members, providing the L2 broadcast domain required for the traffic scenarios.【F:spytest/tests/qos/test_wred.py†L107-L113】
- **Helper `cos_counters_checking`:** Retrieves ASIC counters and verifies that WRED green packet drop counters increased, directly supporting the success criteria for WRED functionality.【F:spytest/tests/qos/test_wred.py†L115-L123】
- **Main test `test_ft_wred_functionality`:** Executes the end-to-end validation: MAC learning via VLAN-tagged traffic, verifying MAC table updates, confirming configurations, running matched/unmatched DSCP traffic, and checking interface plus queue counters to assert WRED behavior.【F:spytest/tests/qos/test_wred.py†L124-L179】

## 4. Dependencies and Prerequisites
- **Fixtures:** `wred_module_hooks` (module, autouse) and `wred_func_hooks` (function, autouse) manage environment setup/cleanup.【F:spytest/tests/qos/test_wred.py†L29-L84】
- **Configuration assets:** Uses `tests.qos.wred_ecn_config_json` module to initialize WRED-specific variables and profiles, and invokes `apply_wred_ecn_config` to program the DUT.【F:spytest/tests/qos/test_wred.py†L6-L37】
- **Topology constraints:** Requires one DUT with three traffic-generator-connected interfaces corresponding to handles `T1D1P1`, `T1D1P2`, and `T1D1P3`, as enforced by the topology declaration.【F:spytest/tests/qos/test_wred.py†L33-L71】

## 5. Key Inputs and Sources
- **Static test parameters:** MAC addresses, VLAN ID, aging time, DSCP values, QoS object names, and queue identifiers are hard-coded into a shared `SpyTestDict` (`data`).【F:spytest/tests/qos/test_wred.py†L17-L27】
- **WRED configuration data:** Derived from `wred_config.init_vars(vars, apply_wred=True)`, which likely pulls thresholds/profile definitions from the JSON module; applied to the DUT via `apply_wred_ecn_config`.【F:spytest/tests/qos/test_wred.py†L33-L37】
- **Traffic generator streams:** Created using traffic-generator API calls with the above static parameters, defining VLAN-tagged learning traffic and two DSCP-differentiated flows for validation.【F:spytest/tests/qos/test_wred.py†L47-L71】
- **Additional runtime values:** DUT and interface references come from the topology object `vars` provided by SpyTest (`vars.D1`, `vars.D1T1P*`).【F:spytest/tests/qos/test_wred.py†L33-L175】
- **External configuration files/testbed:** Not specified within this file; any references to `testbed.yaml`, `group_vars`, or CLI parameters are implicit through SpyTest's `ensure_min_topology` and config modules and not directly visible here. Therefore, explicit external sources beyond the JSON helper are **Not specified**.

## 6. External Libraries and Roles
- **`spytest` framework:** Provides logging, topology management, traffic-generator API access, and reporting utilities (`st`, `tgapi`, `SpyTestDict`, `poll_wait`).【F:spytest/tests/qos/test_wred.py†L3-L4】
- **QoS and system API modules (`apis.*`):**
  - `apis.qos.qos`: Clears QoS configuration during teardown.【F:spytest/tests/qos/test_wred.py†L74】
  - `apis.system.switch_configuration`: Verifies running configuration entries for WRED profiles.【F:spytest/tests/qos/test_wred.py†L87-L90】
  - `apis.switching.vlan`: Manages VLAN creation, membership, and cleanup.【F:spytest/tests/qos/test_wred.py†L9-L113】
  - `apis.common.asic`: Retrieves ASIC counter data for WRED drop verification.【F:spytest/tests/qos/test_wred.py†L10-L122】
  - `apis.qos.cos`: Configures QoS classification maps and applies them to ports.【F:spytest/tests/qos/test_wred.py†L11-L100】
  - `apis.qos.wred`: Supplies `apply_wred_ecn_config` for programming WRED profiles.【F:spytest/tests/qos/test_wred.py†L12-L37】
  - `apis.switching.mac`: Configures MAC aging and verifies MAC table entries.【F:spytest/tests/qos/test_wred.py†L13-L166】
  - `apis.system.interface`: Clears and displays interface counters during the test.【F:spytest/tests/qos/test_wred.py†L14-L177】
- **`utilities.common`:** Provides `exec_all` helpers used to apply WRED configuration in parallel-friendly fashion.【F:spytest/tests/qos/test_wred.py†L15-L37】
- **`tests.qos.wred_ecn_config_json`:** Supplies test-specific WRED configuration templates and initialization logic.【F:spytest/tests/qos/test_wred.py†L6-L37】

