# System Reboot Test Analyzer

## 1. Topology Type
- **Identified Topology:** Single-DUT (D1) topology with management network access.
- **Inference:**
  - The module fixture calls `st.ensure_min_topology("D1")`, indicating the test requires at least one device under test named `D1`.
  - Test docstring for `test_ft_sytem_bootup_logging_debug` references "Testbed : D1 --- Mgmt Network", reinforcing the single-device, management-network-focused setup.

## 2. Overall Test Case Purpose
- **High-Level Goal:** Validate system reboot mechanisms and logging behavior on a SONiC device, including hard reboots via RPS control, soft/fast reboots with configuration persistence, boot-time log cleanliness, and hardware watchdog functionality.
- **Context in SONiC/SpyTest:** These tests exercise resilience and system services within the SpyTest automation framework, ensuring reboot operations, watchdog timers, and logging subsystems behave as expected across reboots.

## 3. Detailed Breakdown of Sub-Testcases
- **`test_ft_sys_hard_reboot_multiple_iter`**
  - **Intent & Logic:** Performs multiple hard reboot cycles by toggling remote power supply (RPS) using `st.do_rps`, waits for interface recovery, and validates the reboot cause and post-boot logging.
  - **Why It Matters:** Confirms the device can withstand repeated power cycles, report the correct reboot cause, and restore logging after hard reboots, supporting system resilience verification.

- **`test_ft_sys_soft_reboot_multiple_iter`**
  - **Intent & Logic:** Saves configuration, runs multiple fast reload (`st.reboot(..., "fast")`) iterations, ensures interfaces return, verifies platform accessibility via `get_hwsku`, and finally performs `config_reload`.
  - **Why It Matters:** Ensures soft reboots preserve configuration, recover interfaces, and keep system services operational, critical for controlled reboot scenarios.

- **`test_ft_sytem_bootup_logging_debug`**
  - **Intent & Logic:** Clears log buffer, sets logging level to Debug, idles, then ensures no unwanted log entries appear beyond expected platform-specific exceptions, and checks for absence of unwanted log keywords.
  - **Why It Matters:** Validates that enabling verbose logging does not generate spurious errors during idle periods post-boot, safeguarding log quality and noise control.

- **`test_ft_hw_watchdog`**
  - **Intent & Logic:** Verifies hardware watchdog support by enabling/disabling/resetting, awaiting expiry, checking reboot causes, validating timeout configuration adjustments, running status, kdump generation, and ensuring reboot cause matches expectations.
  - **Why It Matters:** Confirms the hardware watchdog feature behaves reliably, triggers correct reboot cause reporting, and supports timeout customization—essential for device self-recovery assurance.

- **`test_hw_watchdog_stop_start_service`**
  - **Intent & Logic:** Performs platform support check, stops the watchdog service, and verifies the service status becomes inactive.
  - **Why It Matters:** Ensures the watchdog service can be controlled manually, which supports maintenance or troubleshooting workflows tied to the watchdog functionality.

### Helper Constructs
- **Module Fixture `reboot_module_hooks`:**
  - Initializes global `data` dictionary with iteration counts, idle wait time, max VLAN, topology info, platform constants, and applies VLAN range configuration. Ensures post-test cleanup by clearing VLAN configuration.
  - Provides shared setup essential for consistent test environment across subtests.
- **Function Fixture `reboot_func_hooks`:**
  - Autouse fixture currently yielding without extra logic; placeholder for per-test setup/teardown if needed.
- **`platform_check` Helper:**
  - Validates whether the current hardware platform supports watchdog features before executing watchdog tests, marking unsupported platforms accordingly.

## 4. Dependencies and Prerequisites
- **Fixtures:**
  - `reboot_module_hooks` (module scope, autouse) for topology setup, VLAN configuration, and environment preparation.
  - `reboot_func_hooks` (function scope, autouse) ensuring fixture chain execution.
- **Topology Constraints:** Requires at least one DUT (`D1`) with RPS control and support for VLAN configuration, logging commands, and hardware watchdog operations when applicable.
- **Other Requirements:** Access to SpyTest APIs (`st`, `SpyTestDict`) and specific platform constants retrieved via `st.get_datastore`.

## 5. Key Inputs and Parameters
- **`data.iter_count`:** Number of reboot iterations (default 3) used in hard/soft reboot loops.
- **`data.idle_sleep`:** Idle wait duration (300 seconds) used in logging debug test.
- **`data.max_vlan`:** Upper bound of VLAN range configured; adjusted based on feature support to limit runtime.
- **Platform Constants:** Retrieved via `st.get_datastore(vars.D1, "constants")` to determine supported platforms for watchdog features.
- **Watchdog Timing Values:** Hardcoded min/max timeouts and additional sleep offsets to compute expiry wait durations.

## 6. External Libraries and Modules
- **`pytest`:** Provides fixture and marker infrastructure for test execution.
- **`random`:** Generates random watchdog timeout values within specified range.
- **SpyTest Core (`st`, `SpyTestDict`):** Core test framework utilities for logging, device control, reporting, and shared data structures.
- **`apis.switching.vlan`:** VLAN configuration API for setting up and cleaning VLAN ranges.
- **`apis.system.logging`:** Logging subsystem interactions (clear logs, set severity, check log contents).
- **`apis.system.basic`:** Basic system information retrieval (hardware SKU) used for platform identification.
- **`apis.system.interface`:** Interface polling to verify port status after reboots.
- **`apis.system.reboot`:** Reboot utilities including config save/reload and reboot cause retrieval.
- **`apis.system.box_services`:** Hardware watchdog control APIs (enable/disable/reset/status/timeout/kdump/service control).

## 7. Unspecified Items
- Testbed file references, explicit neighbor topology details, and CLI parameter sources are **Not specified** within this test file.
