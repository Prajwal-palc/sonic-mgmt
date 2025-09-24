# ACL L3 Forwarding Test Analyzer

## 1. Topology type
- **Identified topology:** Dual-DUT L2/L3 setup with a traffic generator on each edge and a LAG interconnect between DUT1 and DUT2.
- **Inference:** The helper `get_handles()` calls `st.ensure_min_topology("D1D2:2", "D1T1:1", "D2T1:1")`, requiring two links between the DUTs and one traffic-generator connection per DUT, and then fetches TG handles `T1D1P1` and `T1D2P1`. A port channel is created across those DUT interconnects, confirming a LAG-based dual-DUT topology.

## 2. Overall test case purpose
- **Goal:** Validate that IPv4 and IPv6 ingress ACLs applied on router interfaces continue to enforce forwarding/drop behavior for L3 traffic traversing a port channel between two SONiC DUTs.
- **Context within SONiC/SpyTest:** The module configures static IP/IPv6 addressing, routing, and ACL tables via SpyTest APIs, sends traffic from an external traffic generator, and verifies both data-plane delivery and ACL counter accounting to ensure SONiC ACL pipeline correctness in a multi-DUT scenario.

## 3. Detailed breakdown of sub-testcases
- **Module fixture `acl_v4_module_hooks`:** Autouse fixture that provisions the topology once per module. It initializes TG resources, builds the port channel, pushes IPv4/IPv6 ACL tables from `acl_json_config_v4_l3_traffic` and `acl_json_config_v6_l3_traffic`, programs interface addresses, static routes, and ARP/NDP entries, and generates traffic streams for each ACL rule direction. After all tests it removes the ACLs, LAG, and IP data.
- **Helper routines:**
  - `create_streams()` derives TG streams directly from ACL rule definitions so traffic precisely matches or misses configured rules.
  - `transmit()` starts continuous traffic for the prepared streams.
  - `verify_packet_count()` evaluates TG statistics, expecting forwarding for permit rules and drops for deny rules.
  - `verify_acl_hit_counters()` and `verify_rule_priority()` query DUT counters to ensure ACL matches are recorded and that default permit rules remain unused when higher-priority rules should match.
- **`test_ft_acl_ingress_ipv4_l3_forwarding`:**
  - Sends traffic from TG1 through the IPv4 ingress ACL bound to DUT1’s interface.
  - Confirms TG receive counts align with each ACL rule’s expected action, then validates ACL hit counters and rule priority behavior on DUT1.
  - Demonstrates that IPv4 ingress ACL policies enforce the intended forwarding behavior while maintaining accurate counters.
- **`test_ft_acl_ingress_ipv6_l3_forwarding`:**
  - Transmits IPv6 traffic from TG2 through the IPv6 ingress ACL on DUT2.
  - Verifies traffic statistics, IPv6 ACL counters (using `acl_type` set to `ipv6`), and priority ordering for the IPv6 rule set.
  - Ensures IPv6 ingress ACL enforcement mirrors the IPv4 case across the dual-DUT topology.

## 4. Dependencies and prerequisites
- **Topology fixtures:** Requires `st.ensure_min_topology` to supply two DUTs with dual interconnect links and TG attachments; absence of this layout would prevent LAG creation and bidirectional TG traffic.
- **Autouse fixture:** `acl_v4_module_hooks` must run to configure ACLs, IP interfaces, static routes, and static ARP/NDP entries before any traffic validation occurs.
- **Traffic generator:** Expects Ixia by default (`data.tg_type = 'ixia'`) but adapts to Spirent if detected; without a compatible TG, stream creation and validation would fail.
- **Platform capabilities:** DUTs must support port channels, static IPv4/IPv6 routing, and ACL application on both physical and LAG interfaces.

## 5. Key inputs and parameters
- **Static data dictionary:** Contains packet rates (`data.rate_pps`), burst sizes, timeouts, port channel name, and all IPv4/IPv6 addressing used for interfaces and static routes.
- **ACL configurations:** `acl_json_config_v4_l3_traffic` and `acl_json_config_v6_l3_traffic` define tables (`L3_IPV4_INGRESS`, `L3_IPV6_INGRESS`, etc.) and rule attributes that drive both DUT configuration and TG stream generation.
- **Topology variables:** `vars` from `st.ensure_min_topology` expose DUT identifiers (`vars.D1`, `vars.D2`), interface aliases (`vars.D1T1P1`, etc.), and TG port mappings required throughout the setup and validation logic.
- **ACL type flag:** `data.acl_type = "ipv6"` selects the counter command path when validating IPv6 rules.
- **MAC learning inputs:** `basic_obj.get_ifconfig_ether` retrieves interface MAC addresses for traffic streams; static ARP/NDP entries use predefined MACs to force deterministic forwarding.

## 6. External libraries and modules
- **SpyTest core:** `st`, `tgapi`, and `SpyTestDict` provide logging, topology discovery, TG integration, and shared data structures.
- **ACL APIs:** `apis.qos.acl` and `tests.qos.acl.acl_utils` supply helper functions for applying ACL configs, parsing rule attributes, and reporting results.
- **Switching/routing helpers:** `apis.switching.portchannel`, `apis.routing.ip`, and `apis.routing.arp` manage LAGs, interface IP configuration, static routes, and neighbor entries.
- **System utilities:** `apis.system.basic`, `utilities.common`, and `utilities.parallel.ensure_no_exception` support MAC discovery, concurrent command execution, and exception handling during cleanup.
- **Standard libraries:** `pprint`, `json`, and `pytest` enable formatting, JSON handling, and test/fixture declaration.

## 7. Unspecified items
- Specific hardware SKU, ASIC type, or SONiC image version: **Not specified.**
- Exact testbed YAML filename or inventory group used to realize the topology: **Not specified.**
- External traffic generator chassis/port identifiers beyond logical aliases: **Not specified.**
