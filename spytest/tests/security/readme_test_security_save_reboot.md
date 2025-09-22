# test_security_save_reboot.py QA Review

## 1. Topology Type Used and Inference
* **Topology:** Single DUT topology (`D1`).
* **Inference:** The module-level fixture calls `st.ensure_min_topology("D1")`, which provisions the minimum topology containing only device `D1`; no other devices or links are referenced in the test, supporting the single-DUT conclusion.

## 2. Overall Test Case Purpose
* Validate that TACACS+ and RADIUS authentication configurations persist across a configuration save and subsequent reboot on the DUT. The test applies TACACS+/RADIUS settings, saves the configuration, reboots, and verifies post-reboot configuration retention.

## 3. Subtestcases and Contributions
1. **Module Autouse Fixture (`security_module_hooks`)**
   * Sets up topology, loads service parameters into `security_data`, and executes the prolog. Ensures initial TACACS+/RADIUS configuration is applied before tests.
2. **`security_variables()` Helper**
   * Fetches TACACS+/RADIUS parameters from service definitions and stores them in `security_data`, ensuring consistent inputs for configuration steps.
3. **`security_module_prolog()`**
   * Applies TACACS+ configuration and (if supported) RADIUS global/server configuration, then validates pre-reboot state. Establishes baseline configuration that should persist.
4. **`tacacs_config()` / `tacacs_config_verify()`**
   * Configures TACACS+ server and verifies the running configuration reflects the change, ensuring TACACS+ settings are ready for persistence validation.
5. **`config_global_radius()` / `radius_config()` / `checking_radius_config()`**
   * Configure and verify RADIUS global and server parameters. These checks ensure the RADIUS configuration is correctly applied pre- and post-reboot, which is essential for testing retention.
6. **`security_module_epilog()`**
   * Cleans up TACACS+/RADIUS configuration after tests, restoring defaults to avoid polluting subsequent tests.
7. **Main Test `test_ft_security_config_mgmt_verifying_config_with_save_reboot()`**
   * Executes config save and reload, then re-validates TACACS+ (and conditionally RADIUS) configuration. This is the central validation that configuration persists through reboot.

## 4. Dependencies and Prerequisites
* **Fixtures:**
  * Module autouse fixture `security_module_hooks` (topology setup, prolog/epilog).
  * Function autouse fixture `security_func_hooks` (no additional setup).
* **Topology Constraints:** Requires access to a single DUT referenced as `D1` via `st.ensure_min_topology("D1")`.
* **Libraries/Modules:** Depends on `apis.security.radius`, `apis.security.tacacs`, `apis.system.reboot`, `apis.system.switch_configuration`, and utility `ensure_service_params`.

## 5. Key Inputs and Sources
* `ensure_service_params(vars.D1, ...)` pulls TACACS+/RADIUS parameters (`hosts`, `globals`, etc.) from the service parameter definitions, typically backed by inventory such as `testbed.yaml` or group vars; exact source is abstracted—**Not specified** explicitly.
* `st.ensure_min_topology("D1")` derives device mapping from the topology description—underlying file (e.g., testbed definition) is **Not specified**.

## 6. External Libraries and Roles
* **`pytest`** – Provides fixtures and test execution framework.
* **`spytest` (`st`, `SpyTestDict`)** – SpyTest utilities for topology management, logging, and data storage.
* **`apis.security.radius` / `apis.security.tacacs`** – API wrappers to configure and verify RADIUS/TACACS+ on the DUT.
* **`utilities.utils.ensure_service_params`** – Retrieves configuration parameters from service definitions.
* **`apis.system.reboot`** – Performs configuration save and device reload.
* **`apis.system.switch_configuration`** – Verifies running configuration entries after reboot.

