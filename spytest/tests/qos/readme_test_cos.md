# QoS CoS Test Reference

## 1. Topology
- **Type:** `D1T1:2` (one DUT with two links to a single traffic generator).
- **Inference:** The module-level fixture calls `st.ensure_min_topology("D1T1:2")`, and both test docstrings describe two traffic-generator ports connected to the DUT, confirming the same topology requirement.

## 2. Overall Purpose
Validate QoS Class-of-Service behavior by ensuring CPU-directed traffic lands in the proper CPU queue and by confirming traffic class (TC) to egress queue mappings for VLAN-priority traffic on switch ports.

## 3. Subtestcases
| Test | What It Covers | Why It Matters |
| --- | --- | --- |
| `test_ft_cos_cpu_counters` | Configures IPv4/IPv6 routing interfaces, generates ARP, switching, IPv4 (TTL 0), and IPv6 (hop-limit 0/255) traffic streams from the traffic generator, and verifies CPU queue counters (`MC1`) increment. | Demonstrates that diverse control-plane and exception traffic types are correctly classified into the expected CPU CoS queue, proving CPU-side QoS handling works.
| `test_ft_cos_tc_queue_map` | Programs MAC aging, VLAN membership, learns MAC entries via tagged streams, binds a TC→queue map (priority 4 → queue 5), transmits VLAN priority-4 traffic, and confirms queue 5 counters increase. | Shows data-plane QoS mapping is honored for VLAN-priority-tagged traffic, validating TC-to-queue configuration on egress interfaces.

## 4. Dependencies & Prerequisites
- **Fixtures:**
  - `cos_module_hooks` (autouse/module): Ensures topology, initializes shared `data` dictionary, applies base configs, acquires traffic-generator handles, and pre-creates traffic streams.
  - `cos_func_hooks` (autouse/function): Cleans up IPv4/IPv6 interface configuration after `test_ft_cos_cpu_counters`.
- **Configuration Helpers:** `cos_module_config`, `cos_variables`, `configuring_ipv4_and_ipv6_address`, VLAN/FDB/QoS helper functions invoked by tests.
- **Topology/Hardware:** Requires a traffic generator with two ports connected to the DUT; assumes access to CPU queue counters either via SONiC CLI (`show queue counters`) or Broadcom BCMCMD support.
- **Not specified:** Additional inventory, DUT image version, or platform-specific prerequisites beyond the minimum topology.

## 5. Key Inputs
- **From `cos_variables()`:** VLAN ID (`555`), MAC addresses, VLAN priority (`4`), queue ID (`5`), IP addressing (IPv4/IPv6 subnets, TGEN peers), and traffic profiles (rates, burst sizes).
- **From `st.ensure_min_topology()`:** Device aliases such as `vars.D1`, test-port aliases (`vars.D1T1P1`, `vars.D1T1P2`), and traffic-generator port handles via `tgapi.get_handle_byname`.
- **Runtime Parameters:** None provided via `testbed.yaml`, group vars, or CLI overrides—values are hard-coded within the module. If alternative inputs exist, they are **Not specified** in this file.

## 6. External Libraries & Roles
- `spytest` (`st`, `tgapi`, `SpyTestDict`): Test harness utilities, logging, topology management, and traffic generator integration.
- `apis.routing.ip`, `apis.routing.arp`: Configure/verify IP interfaces and ARP/NDP entries.
- `apis.system.basic`, `apis.common.asic`, `apis.system.interface`: Retrieve MAC/interface data and access ASIC/queue counters.
- `apis.switching.vlan`, `apis.switching.mac`: VLAN membership management and MAC table configuration/verification.
- `apis.qos.cos`, `apis.qos.qos`: Configure QoS mappings and clear QoS state.
- `utilities.common.filter_and_select`: Filter helper for queue-counter parsing.

