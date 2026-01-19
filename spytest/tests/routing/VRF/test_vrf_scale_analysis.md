# VRF Scale Test Case Analysis

## 1. Topology type and inference
- **Topology requirement:** Dual DUTs with a common traffic generator. The setup demands four interconnect links between DUT1 and DUT2, plus two links from each DUT to the traffic generator (T1). 
- **Inference source:** Derived from `initialize_topology()`, which calls `st.ensure_min_topology("D1D2:4", "D1T1:2", "D2T1:2")` before mapping DUT and TGEN ports.

## 2. Overall test purpose
- Validate large-scale VRF-Lite deployments by provisioning hundreds of VRFs, ensuring interface bindings survive link flaps, confirming static route leak traffic delivery, verifying BGP peering across the VRFs, and confirming configuration persistence across a fast reboot.

## 3. Subtests and their roles
- **`test_vrf_scale`**
  - *Focus:* Confirms all VRFs are created on both DUTs and remain bound to interfaces after a port flap.
  - *Relevance:* Ensures foundational VRF provisioning and resiliency before running more advanced routing scenarios.
- **`test_vrf_route_leak`**
  - *Focus:* Programs static routes across the VRFs to leak traffic between VRF instances and validates end-to-end IPv4 forwarding via traffic generator statistics.
  - *Relevance:* Demonstrates that large numbers of VRFs can exchange traffic through static route leaking under load.
- **`test_vrf_bgp`**
  - *Focus:* Establishes BGP neighbor relationships for the high-scale VRF set, including neighbor activation and post-clear verification.
  - *Relevance:* Proves dynamic routing control-plane scalability and stability after clear operations.
- **`test_vrf_reload`**
  - *Focus:* Saves the running configuration, performs a fast reboot, and checks that VRF/interface bindings are restored.
  - *Relevance:* Validates configuration persistence and system recovery for scaled VRF deployments.

## 4. Dependencies and prerequisites
- **Fixtures:**
  - `prologue_epilogue` (module-scoped, autouse) runs `initialize_topology()` and `base_config()` for setup.
  - `vrf_fixture_vrf_scale` (function-scoped) yields per-test and currently only banners during teardown.
- **Topology & hardware:** Requires two SONiC DUTs meeting the `ensure_min_topology` port map and hardware-aware VRF limits (max VRFs determined via `basic_obj.get_hwsku` and campus build detection).
- **Traffic generator:** Access to SpyTest traffic generator objects (`tgen_obj_dict`) for configuring interfaces and streams.
- **Configuration assets:** JSON config-db templates (`vrf_scale_dut1*.json`, `vrf_scale_dut2*.json`) expected under `routing/VRF/` to preload VRF and interface state; defaults copied via `basic_obj.copy_file_to_local_path`.
- **Library dependencies:** Uses SpyTest utilities (`st`, `utils`, `tgapi`), platform APIs (MAC/VLAN/IP/VRF/BGP/port/reboot), and helper library `vrf_lib` (aliased `loc_lib`).

## 5. Key inputs and their origins
- **Dynamic scaling parameters:** `max_vrfs`, `static_lower`, `static_upper`, `bgp_vrfs_start`, `bgp_vrfs_end`, and JSON file names selected in `initialize_topology()` according to detected platform/campus build.
- **VRF and addressing lists:**
  - `vrf_list`, VLAN names, DUT-to-DUT IP ranges, and TG stream IP ranges created at runtime via helper `ip_range()`.
  - Traffic stream configuration leverages normalized PPS (`tgapi.normalize_pps`) and TG MAC discovery from `mac_api`.
- **BGP attributes:** Router IDs (`data.dut1_router_id`, `data.dut2_router_id`) and AS number lists (`data.dut1_as_scale`, `data.dut2_as_scale`) sourced from `vrf_vars.py`.
- **Device and port handles:** Provided by `st.ensure_min_topology` (`vars` object) and resolved into SpyTest/TGEN handles stored in the shared `data` dictionary.
- **External references:** No explicit testbed YAML or CLI parameter usage is defined beyond what SpyTest derives from the topology helper. (Not specified.)

## 6. External libraries and roles
- **`pytest`** – supplies the test framework, fixtures, and markers.
- **`os` / `ipaddress`** – handle filesystem paths for config templates and generate incremental IP data.
- **SpyTest core modules (`st`, `utils`, `tgapi`)** – provide logging, command execution, and traffic generator abstractions.
- **SpyTest traffic generator support (`tgen_obj_dict`)** – retrieves TG session objects for port/traffic configuration.
- **SONiC API wrappers (`mac_api`, `vlan_api`, `ip_api`, `vrf_api`, `bgp_api`, `ip_bgp`, `port_api`, `reboot_api`, `basic_obj`)** – apply and verify control-plane and system settings across DUTs.
- **`utilities.parallel`** – executes configuration tasks simultaneously on both DUTs.
- **Local helper modules (`vrf_lib`, `vrf_vars`)** – encapsulate TG utilities and share test-wide data defaults.

