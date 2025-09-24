# Test Case Analysis: `spytest/tests/security/test_security_save_reboot.py`

## 1. Topology Type
- **Topology:** Single-DUT topology (`D1`).
- **Inference:** The module-level fixture calls `st.ensure_min_topology("D1")`, which provisions the minimal setup containing one device under test referenced as `vars.D1`.【F:spytest/tests/security/test_security_save_reboot.py†L15-L17】

## 2. Overall Test Case Purpose
- **High-level goal:** Validate that TACACS+ and RADIUS security configurations remain intact after performing a configuration save followed by a device reboot in SONiC using the SpyTest framework.【F:spytest/tests/security/test_security_save_reboot.py†L55-L93】【F:spytest/tests/security/test_security_save_reboot.py†L111-L129】
- **Context:** The test suite leverages SpyTest security APIs to set up authentication servers, save the running configuration, reboot the DUT, and confirm that both TACACS+ and RADIUS settings persist, ensuring configuration durability across reloads.

## 3. Detailed Breakdown of Sub-Testcases
- **`test_ft_security_config_mgmt_verifying_config_with_save_reboot`**
  - **Intent & Logic:**
    1. Initiates a configuration save and device reload using `reboot.config_save_reload`.
    2. Revalidates TACACS+ server settings with `tacacs_config_verify`.
    3. If the DUT supports the RADIUS feature, rechecks RADIUS global and server parameters via `checking_radius_config`.
    4. Reports the test as passed if all validations succeed.【F:spytest/tests/security/test_security_save_reboot.py†L111-L129】
  - **Contribution:** Confirms that critical authentication configurations survive a save-and-reboot workflow, which is essential for operational stability and compliance requirements.
- **Helper Functions & Fixtures:**
  - `security_module_hooks` (module-level autouse fixture) prepares the topology, loads service parameters, and preconfigures TACACS+/RADIUS before tests, then performs cleanup afterward.【F:spytest/tests/security/test_security_save_reboot.py†L13-L54】
  - `security_func_hooks` (function-level autouse fixture) reserved for per-test setup/teardown (currently a no-op).【F:spytest/tests/security/test_security_save_reboot.py†L22-L25】
  - Utility functions (`security_variables`, `security_module_prolog`, `security_module_epilog`, `tacacs_config`, `tacacs_config_verify`, `config_global_radius`, `radius_config`, `checking_radius_config`, `verify_security_default_config`) orchestrate configuration, verification, and cleanup flows supporting the primary test case.【F:spytest/tests/security/test_security_save_reboot.py†L27-L110】

## 4. Dependencies and Prerequisites
- **Fixtures:** Module-level `security_module_hooks` and function-level `security_func_hooks` must execute automatically to establish initial configurations and ensure cleanup.【F:spytest/tests/security/test_security_save_reboot.py†L13-L25】
- **Topology Requirement:** Availability of at least one DUT (`D1`) accessible via SpyTest topology management.【F:spytest/tests/security/test_security_save_reboot.py†L15-L17】
- **Feature Support:** The DUT must support TACACS+ and, if applicable, RADIUS; RADIUS-related steps are conditional on `st.is_feature_supported("radius", vars.D1)`.【F:spytest/tests/security/test_security_save_reboot.py†L59-L70】【F:spytest/tests/security/test_security_save_reboot.py†L120-L124】
- **Service Parameters:** The test relies on predefined service parameters (e.g., IPs, keys, timeouts) accessible through `ensure_service_params`, typically sourced from testbed or inventory data.【F:spytest/tests/security/test_security_save_reboot.py†L27-L44】

## 5. Key Inputs and Parameters
- **RADIUS parameters:** Host IP, passkey, priority, global passkey, authentication type, timeout, and retransmit values fetched via `ensure_service_params` and stored in `security_data` for configuration and verification.【F:spytest/tests/security/test_security_save_reboot.py†L29-L36】【F:spytest/tests/security/test_security_save_reboot.py†L72-L87】
- **TACACS+ parameters:** Host IP, TCP port, passkey, timeout, priority, and authentication type retrieved similarly for provisioning and validation.【F:spytest/tests/security/test_security_save_reboot.py†L37-L44】【F:spytest/tests/security/test_security_save_reboot.py†L94-L104】
- **Feature flags:** `st.is_feature_supported("radius", ...)` controls whether RADIUS configuration and verification steps are executed.【F:spytest/tests/security/test_security_save_reboot.py†L59-L70】【F:spytest/tests/security/test_security_save_reboot.py†L121-L124】

## 6. External Libraries and Modules
- `pytest`: Provides fixture and test declaration decorators for structuring the test module.【F:spytest/tests/security/test_security_save_reboot.py†L1】
- `spytest.st`: SpyTest service toolbox offering topology management, feature detection, logging, and reporting utilities used throughout the module.【F:spytest/tests/security/test_security_save_reboot.py†L2】【F:spytest/tests/security/test_security_save_reboot.py†L57-L58】【F:spytest/tests/security/test_security_save_reboot.py†L126-L128】
- `SpyTestDict`: Specialized dictionary structure for storing test data in an attribute-friendly format.【F:spytest/tests/security/test_security_save_reboot.py†L3】【F:spytest/tests/security/test_security_save_reboot.py†L27-L44】
- `apis.security.radius`: Provides functions for configuring and validating RADIUS server settings on the DUT.【F:spytest/tests/security/test_security_save_reboot.py†L4】【F:spytest/tests/security/test_security_save_reboot.py†L68-L90】
- `apis.security.tacacs`: Supplies TACACS+ configuration and verification helpers for the DUT.【F:spytest/tests/security/test_security_save_reboot.py†L5】【F:spytest/tests/security/test_security_save_reboot.py†L92-L104】
- `utilities.utils.ensure_service_params`: Retrieves parameter values from service configuration data sources such as testbed definitions.【F:spytest/tests/security/test_security_save_reboot.py†L6】【F:spytest/tests/security/test_security_save_reboot.py†L27-L44】
- `apis.system.reboot`: Enables saving configuration and reloading the DUT (`config_save_reload`).【F:spytest/tests/security/test_security_save_reboot.py†L7】【F:spytest/tests/security/test_security_save_reboot.py†L113-L118】
- `apis.system.switch_configuration`: Offers access to running configuration verification utilities (`verify_running_config`).【F:spytest/tests/security/test_security_save_reboot.py†L8】【F:spytest/tests/security/test_security_save_reboot.py†L95-L104】

## 7. Unspecified Items
- Detailed topology diagram, neighbor devices, and specific inventory sources for service parameters: **Not specified.**
- Exact versions of SONiC/SpyTest or authentication servers under test: **Not specified.**
