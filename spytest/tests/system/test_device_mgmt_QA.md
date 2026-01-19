# QA Analysis: `test_device_mgmt.py`

## 1. Topology
- **Topology used:** `CONSOLE_ONLY` on device alias `D1`.
- **Inference:** The module-scoped `mgmt_module_hooks` fixture calls `st.ensure_min_topology("D1", "CONSOLE_ONLY")`, explicitly requesting this topology before tests run.

## 2. Overall Test Purpose
- Validates that the management interface (`eth0`) can transition between DHCP-acquired addressing and a statically configured address while maintaining reachability to the configured gateway. It ensures cleanup by restoring DHCP and confirming connectivity.

## 3. Subtests / Key Steps
1. **Enable DHCP and gather baseline addressing**
   - `intf_obj.enable_dhcp_on_interface` followed by `basic_obj.get_ifconfig_inet` ensures the interface can obtain an address via DHCP. Failure to receive an IP fails the test, confirming prerequisite connectivity.
2. **Derive and configure static parameters**
   - Retrieves current IP, netmask, and gateway via `basic_obj` helpers, then applies them statically with `intf_obj.config_static_ip_to_interface`. Ensures static configuration uses verified values from the device.
3. **Connectivity verification with static IP**
   - Executes `ping_obj.ping` towards the management gateway to confirm reachability after static configuration. Failures accumulate for final reporting.
4. **Remove static configuration and confirm cleanup**
   - Uses `intf_obj.delete_ip_on_interface_linux` and rechecks `basic_obj.get_ifconfig_inet` to verify no stale IP remains once static settings are removed.
5. **Re-enable DHCP and revalidate reachability**
   - Restores DHCP via `intf_obj.enable_dhcp_on_interface` and pings the gateway again to ensure DHCP functionality remains intact post-test.

## 4. Dependencies / Prerequisites
- **Fixtures:**
  - `mgmt_module_hooks` (module scope, autouse) sets up topology and disables SSH retries via `st.set_module_params(tryssh=0)`.
  - `mgmt_func_hooks` (function scope, autouse) currently no-op but reserved for per-test setup/teardown.
- **Topology constraint:** Requires a single DUT accessible via console (`CONSOLE_ONLY`).
- **Framework prerequisites:** Relies on SpyTest framework (`st`, `SpyTestDict`) for orchestration and result reporting.

## 5. Key Inputs and Sources
- **Device under test:** Stored as `data.dut`, assigned from `vars.D1` returned by `st.ensure_min_topology`.
- **Interface name:** Hardcoded as `eth0` within the test body.
- **IP parameters (IP, netmask, gateway):** Retrieved dynamically from the DUT using `basic_obj` helper APIs (`get_ifconfig_inet`, `get_ifconfig`, `get_ifconfig_gateway`). No external inventory or YAML inputs referenced.

## 6. External Libraries and Roles
- `pytest`: Provides test structure, fixtures, and marks.
- `spytest` (`st`, `SpyTestDict`): SpyTest harness for logging, topology management, and reporting.
- `apis.routing.ip` (`ping_obj`): Supplies the `ping` utility for connectivity checks.
- `apis.system.interface` (`intf_obj`): Manages interface configuration actions (enable DHCP, apply/delete IPs).
- `apis.system.basic` (`basic_obj`): Retrieves interface status, addresses, and gateway information from the DUT.

