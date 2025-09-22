# `test_interface.py` QA Summary

## 1. Topology Type
- **Topology requirement:** `st.ensure_min_topology("D1D2:2", "D1T1:2")` mandates two DUTs (D1, D2) interconnected by two links and a traffic generator (T1) with two links to D1. This inference comes from the topology notation used in the module-level fixture, showing both DUT-to-DUT and DUT-to-TG connectivity expectations.

## 2. Overall Purpose
- The module validates Layer2/Layer3 interface robustness on SONiC devices, covering MTU-dependent forwarding, FEC interoperability, interface flap resilience, and overrun/error counter behavior under oversized traffic.

## 3. Subtestcases and Rationale
- **`test_ft_port_frame_fwd_diff_mtu`** – Sets large MTU values on access ports, transmits VLAN-tagged frames of different sizes from the traffic generator, and validates lossless delivery. This ensures the DUT forwards jumbo frames as configured.
- **`test_ft_port_fec_nofec`** – Retrieves the negotiated speed, toggles Forward Error Correction settings asymmetrically between peer ports via `port_fec_no_fec`, and verifies link-down/up reactions. It confirms FEC mismatches are detected and that matching FEC restores link health.
- **`test_ft_port_fn_verify_shut_noshut`** – Assigns IPv4 addresses across the D1–D2 link, verifies bidirectional ping, repeatedly shuts/noshuts the interface, checks connectivity again, performs a config save/reload, and repeats verification. This exercises interface stability through administrative flaps and reboots.
- **`test_ft_ovr_counters`** – Clears counters, runs jumbo traffic bidirectionally to ensure `rx_ovr`/`tx_ovr` stay at zero, then lowers MTU on one port and transmits oversized frames to confirm `rx_err` increments while overrun counters remain unaffected. Validates statistics accuracy for MTU violations.

## 4. Dependencies / Prerequisites
- **Fixtures:**
  - `interface_module_hooks` (module, autouse) prepares the topology, initializes shared data, creates a VLAN with TG-facing ports, acquires traffic-generator handles, resets stats, and builds reusable traffic streams. It also performs VLAN and TG cleanup on teardown.
  - `interface_func_hooks` (function, autouse) restores the MTU of `vars.D1T1P1` after `test_ft_ovr_counters` runs.
- **Helper:** `initialize_variables()` seeds IP/MAC/MTU values, derives default MTU from the DUT, and stores a random VLAN ID.
- **Topology constraint:** Requires two DUTs plus a TG as enforced by `ensure_min_topology`.
- **Hardware nuance:** `port_fec_no_fec` branches on Broadcom TH3 hardware (via `base_obj.get_hwsku`) to choose appropriate FEC values.

## 5. Key Inputs and Sources
- **Static test parameters:**
  - `intf_data.ip_address`, `ip_address1`, `mask`, `mtu`, `mtu1`, `mtu2`, `wait_sec`, `source_mac`, `destination_mac` – hardcoded in `initialize_variables`.
- **Dynamic values:**
  - `intf_data.vlan_id` from `random_vlan_list()` (utilities helper supplying random VLAN IDs).
  - `intf_data.mtu_default` and `speed` fetched from `intfapi.get_interface_property` (runtime DUT queries).
  - `vars.*` handles (DUT names, interfaces, TG ports, constants) populated by `st.ensure_min_topology` using the active `testbed.yaml` definition.
  - Traffic stream IDs created via `tgapi.tg_traffic_config` during fixture setup.

## 6. External Libraries and Roles
- `pytest` – fixtures and test definitions.
- `spytest.st`, `tgapi`, `SpyTestDict` – SpyTest harness utilities for topology negotiation, logging, and TG control.
- `apis.switching.vlan` – VLAN creation and cleanup on DUTs.
- `apis.system.interface` – Interface property configuration, counter access, status verification, and administrative control.
- `apis.routing.ip` – IP configuration and ping validation.
- `apis.system.reboot` – Configuration save/reload workflow.
- `apis.system.basic` – Hardware SKU inspection for platform-specific logic.
- `utilities.common.random_vlan_list` – Supplies random VLAN IDs to avoid collisions.
