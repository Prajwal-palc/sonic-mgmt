# Test Analysis: `spytest/tests/qos/acl/test_acls.py`

## Topology type
- The module requires a dual-DUT topology with a port-channel between DUT1 and DUT2 and traffic generators on both ends. This is documented in the ASCII diagram inside `get_handles()` and enforced by `st.ensure_min_topology("D1D2:2", "D1T1:2", "D2T1:1")`, which demands two inter-DUT links, two TG connections to DUT1, and one TG connection to DUT2.【F:spytest/tests/qos/acl/test_acls.py†L41-L60】
- Traffic generator handles are retrieved for ports `T1D1P1`, `T1D2P1`, and `T1D1P2`, and the ports are reset before use, showing that the tests expect three TG-facing links mapped to the topology above.【F:spytest/tests/qos/acl/test_acls.py†L54-L63】

## Overall test case purpose
- The file validates SONiC ACL functionality across IPv4, IPv6, and MAC domains on multiple attachment points (interfaces, VLANs, port-channels, and switch-wide bindings) while measuring traffic behavior, counter increments, rule priorities, and management-plane configuration workflows.【F:spytest/tests/qos/acl/test_acls.py†L279-L331】【F:spytest/tests/qos/acl/test_acls.py†L355-L1106】
- Module fixtures stand up shared infrastructure—VLANs, port-channels, ACL tables, and IxNetwork/Spirent streams—so that each scenario can focus on a specific ACL use case (ingress vs egress, port vs VLAN binding, control-plane tools like config-loader, REST, and gNMI). This aligns with SpyTest’s goal of end-to-end feature validation on SONiC devices.【F:spytest/tests/qos/acl/test_acls.py†L69-L331】

## Detailed breakdown of sub-testcases

### Shared helpers and fixtures
- Utility functions build ACL JSON payloads, apply them, drive traffic, and check statistics. `create_streams()` programs TG flows according to ACL rule definitions, `transmit()` runs those streams, and `verify_packet_count()` plus `verify_acl_hit_counters()` inspect forwarding/drop behavior and ASIC counters, forming the backbone for every subtest.【F:spytest/tests/qos/acl/test_acls.py†L153-L254】
- `acl_v4_module_hooks` (module scope) wires up the base topology, applies foundational ACLs on both DUTs, and prepares traffic streams before yielding to the test body, while `acl_function_hooks` performs selective cleanup after certain functions, preventing residue between scenarios.【F:spytest/tests/qos/acl/test_acls.py†L279-L339】

### `test_ft_acl_ingress_ipv4`
- Deletes MAC ACL tables on DUT1, runs IPv4 ingress traffic from TG1 to TG2, and confirms forwarding, ACL hit counters, rule priority (via `verify_rule_priority`), and traffic redirection to TG3, proving IPv4 ingress ACL enforcement with redirect actions.【F:spytest/tests/qos/acl/test_acls.py†L355-L375】
- Demonstrates that ingress ACLs can both forward/drop packets and redirect to alternate ports, key to validating SONiC’s policing logic.

### `test_ft_acl_egress_ipv4`
- Sends traffic from TG2 through DUT1 egress ACLs applied to the TG1-facing port, verifying packet counts and counter increments.【F:spytest/tests/qos/acl/test_acls.py†L379-L389】
- Ensures IPv4 egress ACLs enforce the configured actions and report statistics correctly.

### `test_ft_acl_egress_ipv6`
- Clears interface counters, transmits traffic through DUT2’s IPv6 egress ACL, and checks both traffic drops/forwards and IPv6 ACL counters.【F:spytest/tests/qos/acl/test_acls.py†L393-L411】
- Confirms IPv6 egress ACL support on the second DUT and validates telemetry accuracy.

### `test_ft_acl_ingress_ipv6`
- Mirrors the IPv6 ingress case on DUT2: clears counters, drives TG2-to-TG1 traffic, validates forwarding decisions, IPv6 counters, and rule priority behavior.【F:spytest/tests/qos/acl/test_acls.py†L414-L436】
- Shows that ingress IPv6 ACL rules execute in priority order and that higher-priority drops take precedence.

### `test_ft_mac_acl_port`
- Replaces existing ACLs with MAC-specific tables on a DUT1 port, updates VLAN IDs in rule templates, runs traffic in both directions, and verifies counts and counters for ingress and egress MAC rules.【F:spytest/tests/qos/acl/test_acls.py†L439-L468】
- Validates MAC ACL enforcement at the port level, covering L2 filtering use cases.

### `test_ft_acl_port_channel_ingress`
- Clears ACL state, binds an IPv6 ingress ACL to DUT1’s port-channel, runs TG2-to-TG1 traffic, and confirms packets follow configured actions and counters increment.【F:spytest/tests/qos/acl/test_acls.py†L472-L492】
- Ensures ACLs function correctly on aggregated interfaces, which are common in SONiC deployments.

### `test_ft_acl_port_channel_egress`
- Applies an IPv6 egress ACL to the port-channel (after removing conflicting egress tables) and validates TG1-to-TG2 traffic along with counter statistics.【F:spytest/tests/qos/acl/test_acls.py†L495-L513】
- Demonstrates egress ACL enforcement on LAGs.

### `test_ft_acl_port_channel_V4_egress`
- Binds an IPv4 egress ACL to the port-channel on DUT2 and verifies TG2-to-TG1 traffic compliance and validation via `acl_utils.report_result`.【F:spytest/tests/qos/acl/test_acls.py†L516-L535】
- Extends port-channel coverage to IPv4 rules.

### `test_ft_acl_vlan_v6_egress`
- Configures an IPv6 egress ACL on a VLAN interface, resets counters, and sends traffic from TG1 to TG2 to assert enforcement and counter updates.【F:spytest/tests/qos/acl/test_acls.py†L540-L567】
- Verifies VLAN-bound IPv6 ACL functionality.

### `test_ft_acl_vlan_v6_ingress`
- Applies an IPv6 ingress ACL to the VLAN, drives TG2 traffic toward DUT1, and checks forwarding results and IPv6 counters.【F:spytest/tests/qos/acl/test_acls.py†L568-L588】
- Confirms ingress VLAN ACLs behave as expected for IPv6 flows.

### `test_ft_acl_vlan_V4_ingress`
- Sets up an IPv4 ingress ACL on the VLAN (forcing rule6 to `FORWARD`), transmits TG1 traffic, and checks counter accuracy.【F:spytest/tests/qos/acl/test_acls.py†L590-L610】
- Covers IPv4 VLAN ingress behavior and custom packet action overrides.

### `test_ft_acl_vlan_V4_egress`
- Attaches an IPv4 egress ACL to the VLAN, sends TG2 traffic, and validates the resulting enforcement and counters.【F:spytest/tests/qos/acl/test_acls.py†L612-L630】
- Ensures IPv4 VLAN egress ACLs act as configured.

### `test_ft_acl_port_channel_V4_ingress`
- Applies an IPv4 ingress ACL to the port-channel with a `DROP` action override and verifies TG1 traffic is treated per policy.【F:spytest/tests/qos/acl/test_acls.py†L632-L653】
- Tests ACL drops on LAG ingress for IPv4.

### `test_ft_v4_acl_switch`
- Programs switch-wide IPv4 ingress/egress ACL tables, clears counters, tests TG1 and TG2 directions, and validates both packet results and counters for each stage.【F:spytest/tests/qos/acl/test_acls.py†L655-L695】
- Confirms chassis-wide ACL bindings affect all relevant ports consistently.

### `test_ft_mac_acl_switch`
- Similar to the previous test but with MAC ACL tables bound to the switch, verifying forwarding decisions and counters for ingress MAC rules.【F:spytest/tests/qos/acl/test_acls.py†L698-L719】
- Ensures global MAC ACL policies propagate properly.

### `test_ft_mac_acl_switch_egress`
- Applies switch-level MAC egress ACLs and validates TG2 traffic and counters.【F:spytest/tests/qos/acl/test_acls.py†L722-L745】
- Verifies switch-wide egress filtering at Layer 2.

### `test_ft_mac_acl_vlan`
- Attaches MAC ACLs to the VLAN for both ingress and egress directions, runs TG1/TG2 traffic, and inspects packet counts and counters.【F:spytest/tests/qos/acl/test_acls.py†L748-L770】
- Demonstrates VLAN-level MAC ACL coverage.

### `test_ft_mac_acl_portchannel`
- Applies ingress MAC ACLs to a port-channel on DUT2, updates VLAN IDs in template rules, and confirms TG1 traffic follows policy and counters increment.【F:spytest/tests/qos/acl/test_acls.py†L773-L794】
- Validates L2 ACL support on aggregated interfaces.

### `test_ft_mac_acl_egress_portchannel`
- Configures egress MAC ACLs on the port-channel and ensures TG2 traffic is enforced and counted correctly.【F:spytest/tests/qos/acl/test_acls.py†L797-L817】
- Completes MAC ACL coverage on LAG egress.

### `test_ft_mac_acl_port_adv`
- Switches hardware ACL counter mode to `per-interface-rule`, applies MAC ACLs, drives traffic, verifies ASIC stats, then restores the default `per-rule` mode.【F:spytest/tests/qos/acl/test_acls.py†L820-L838】
- Validates advanced counter modes for MAC ACLs.

### `test_ft_acl_ingress_ipv4_adv`
- Performs the same counter-mode toggle for IPv4 ingress ACLs, confirming rule statistics in `per-interface-rule` mode before reverting to `per-rule`.【F:spytest/tests/qos/acl/test_acls.py†L841-L859】
- Ensures hardware counter configurations behave for IPv4 ACLs.

### `test_ft_acl_loader`
- Exercises ACL rule management via `acl-loader` and CLI tools: deletes existing ACLs, applies base tables, performs full and incremental updates using loader commands, checks rule counts, then repeats using `config acl` commands to ensure parity.【F:spytest/tests/qos/acl/test_acls.py†L862-L921】
- Validates configuration workflows and rule scaling support.

### `test_ft_acl_icmpv6`
- Temporarily assigns IPv6 addresses to the VLAN on both DUTs, pings across the link to confirm forwarding, then removes the addresses.【F:spytest/tests/qos/acl/test_acls.py†L925-L949】
- Demonstrates that ACL settings do not block essential IPv6 control traffic and that ICMPv6 connectivity remains intact.

### `test_ft_mac_acl_prioirty_ingress`
- Applies combined MAC and IPv4 ingress ACLs on a port, drives TG1 traffic to validate both forwarding and dropping rules, and confirms counter updates to show rule priority resolution.【F:spytest/tests/qos/acl/test_acls.py†L952-L980】
- Tests precedence between ACL types on the same interface.

### `test_ft_mac_acl_prioirty_egress`
- Similar to the ingress priority test but on egress: ensures MAC drops override IPv4 forward actions and validates counters for both tables.【F:spytest/tests/qos/acl/test_acls.py†L983-L1009】
- Confirms cross-table priority handling for egress traffic.

### `test_acl_rest`
- Constructs ACL table and rule payloads compliant with `sonic-acl` YANG, pushes them via REST, reads back the configuration, and then verifies ingress and egress traffic follow the newly programmed rules.【F:spytest/tests/qos/acl/test_acls.py†L1014-L1069】
- Verifies RESTCONF-based ACL management and functional enforcement.

### `test_ft_acl_gnmi`
- Builds equivalent ACL objects, writes them via gNMI, confirms the device returns clean data, and validates forwarding behavior for the programmed rule.【F:spytest/tests/qos/acl/test_acls.py†L1075-L1106】
- Ensures gNMI configuration paths properly apply ACLs and affect data-plane traffic.

## Dependencies and prerequisites
- Relies on SpyTest’s topology discovery (`st.ensure_min_topology`) to guarantee required DUT and TG connections before any test executes.【F:spytest/tests/qos/acl/test_acls.py†L54-L59】
- Module and function fixtures provision VLANs, port-channels, ACL tables, and traffic streams, and they tear them down after execution, ensuring idempotent runs.【F:spytest/tests/qos/acl/test_acls.py†L279-L339】
- Uses utility wrappers such as `utils.exec_all` and `ensure_no_exception` to run parallel operations and check for failures, which keeps multi-DUT configuration synchronized.【F:spytest/tests/qos/acl/test_acls.py†L76-L135】【F:spytest/tests/qos/acl/test_acls.py†L479-L508】
- Requires access to traffic generators supported by `tgapi` (Ixia or Spirent), SONiC CLI/REST/gNMI interfaces, and ACL configuration templates from `tests.qos.acl` modules.【F:spytest/tests/qos/acl/test_acls.py†L54-L63】【F:spytest/tests/qos/acl/test_acls.py†L69-L324】

## Key inputs and parameters
- The shared `data` object seeds rate, VLAN IDs, port-channel name, CLI type, and traffic generator type; these influence stream creation, ACL bindings, and validation thresholds.【F:spytest/tests/qos/acl/test_acls.py†L24-L33】【F:spytest/tests/qos/acl/test_acls.py†L69-L100】
- Helper functions inject port lists into ACL JSON (`add_port_to_acl_table`) and tweak rule attributes such as `PACKET_ACTION`, VLAN IDs, DSCP/PCP fields, and counter modes, tailoring each scenario’s behavior.【F:spytest/tests/qos/acl/test_acls.py†L138-L188】【F:spytest/tests/qos/acl/test_acls.py†L286-L324】【F:spytest/tests/qos/acl/test_acls.py†L603-L604】
- REST and gNMI tests define explicit ACL table/rule names, priorities, protocol numbers, address prefixes, and actions to validate northbound interfaces.【F:spytest/tests/qos/acl/test_acls.py†L1015-L1069】【F:spytest/tests/qos/acl/test_acls.py†L1075-L1106】

## External libraries and modules
- `spytest.st` provides logging, reporting, topology, and REST/gNMI helpers; `tgapi` controls traffic generators; `SpyTestDict` offers structured state storage.【F:spytest/tests/qos/acl/test_acls.py†L1-L33】
- Feature-specific APIs—`apis.qos.acl`, `apis.switching.vlan`, `apis.switching.portchannel`, and `apis.routing.ip`—configure SONiC features programmatically for each test.【F:spytest/tests/qos/acl/test_acls.py†L7-L13】
- System interfaces (`apis.system.interface`, `apis.system.rest`, `apis.system.gnmi`) expose counter reads, RESTCONF operations, and gNMI RPCs used by management-plane tests.【F:spytest/tests/qos/acl/test_acls.py†L14-L16】
- Utility packages (`utilities.common`, `utilities.parallel`, and `tests.qos.acl` data modules) deliver parallel execution, reusable JSON templates, argument builders, and reporting helpers to streamline ACL scenarios.【F:spytest/tests/qos/acl/test_acls.py†L10-L20】【F:spytest/tests/qos/acl/test_acls.py†L181-L188】

## Unspecified items
- Exact hardware models, SONiC image versions, and detailed testbed.yaml definitions are not specified in the test file. Not specified.
- No explicit pass/fail thresholds beyond traffic counts and counter increments are documented. Not specified.
