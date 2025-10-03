# VLAN Ports Down Test Analyzer

## 1. Topology Type
- **Identified Topology:** `t0` leaf-spine topology.
- **Evidence & Inference:** The file-level `pytestmark` applies `@pytest.mark.topology('t0')`, constraining execution to T0 testbeds where a single DUT connects to multiple T1 neighbors. This matches the fixture usage (`duthosts`, `nbrhosts`, T1 route checks) that assumes T0-style uplinks.

## 2. Overall Test Case Purpose
- **High-Level Goal:** Validate that a SONiC DUT preserves VLAN interface functionality when every access/member port in that VLAN is administratively shut down.
- **Context in SONiC Automation:** Ensures VLAN resiliency and routing advertisement in T0 topologies after link failures. The test confirms: (1) the VLAN L3 interface stays operational, (2) BGP continues advertising the VLAN subnet to T1 peers, and (3) IP-in-IP decapsulation still works so traffic forwarded to the VLAN IP is handled correctly.

## 3. Detailed Breakdown of Sub-Testcases
### `vlan_ports_setup` (module-scoped fixture)
- **Role:** Prepares the DUT by shutting down all admin-up member ports of the first discovered VLAN, yielding the VLAN name to tests, and restores port states afterwards.
- **Why It Matters:** Simulates a worst-case VLAN access outage, enabling the downstream test to verify DUT behavior under that condition.

### `test_vlan_ports_down`
- **Intent & Logic:**
  1. Consume the `vlan_ports_setup` fixture and gather interface facts (`show_ip_interface`, `show_ipv6_interfaces`).
  2. Assert the VLAN L3 interface remains operationally "up" for both IPv4 and IPv6 despite all member ports being down.
  3. For each T1 neighbor (skipping PT0 peers), retrieve routing information and verify that the VLAN subnet (IPv4 and IPv6) is still advertised via BGP. If no neighbor responds, skip the test.
  4. When running on real ASICs (non-VS), derive PTF port mappings from `get_extended_minigraph_facts` and craft an IPv4-in-IPv4 packet using `ptf.testutils`. Send the encapsulated packet from a PTF port and expect the DUT to decapsulate and forward the inner UDP packet to any uplink port (verified with wildcarded MAC/TOS/TTL via `ptf.mask`).
- **Relevance:** Demonstrates end-to-end that control-plane advertising and data-plane decapsulation remain intact, satisfying the overall resilience validation goal.

## 4. Dependencies and Prerequisites
- **Pytest Fixtures:** `duthosts`, `rand_one_dut_hostname`, `nbrhosts`, `tbinfo`, `ptfadapter` (provided by the SONiC pytest infrastructure). They supply DUT handles, neighbor automation access, testbed metadata, and traffic injection capability.
- **Topology Constraints:** Requires a T0 testbed with VLANs defined and reachable T1 neighbors. IP-in-IP portion is skipped for the virtual switch (`vs`) ASIC type.
- **Runtime Tools:** SONiC CLI via `duthost.shell`, BGP route queries on neighbor hosts, and minigraph-derived port mappings for PTF traffic.

## 5. Key Inputs and Parameters
- **`vlan_brief`, `get_interfaces_status`:** Determine VLAN membership and identify ports to shut down.
- **`show_ip_interface`, `show_ipv6_interfaces`:** Provide operational state and addressing used for assertions and packet crafting.
- **`nbrhosts`:** Supplies remote host objects capable of running `get_route` to verify BGP advertisement.
- **`tbinfo` & `get_extended_minigraph_facts`:** Offer minigraph topology data, especially port-channel membership and PTF port indices.
- **`ptfadapter.dataplane.get_mac`, `duthost.facts['router_mac']`:** Populate Ethernet headers for generated packets.
- **Hard-coded Packet Fields (`1.1.1.1`, `2.2.2.2`, etc.):** Define IP-in-IP encapsulation parameters to exercise decapsulation logic.

## 6. External Libraries and Modules
- **`pytest`:** Provides fixtures, marks, and assertion mechanisms.
- **`logging`:** Emits diagnostic logs for setup actions and verification steps.
- **`ptf.testutils`, `ptf.mask`:** Construct, send, and match network packets during the IP-in-IP verification.
- **`time`:** Introduces a delay after shutting down ports to allow neighbor convergence.
- **`netaddr.IPNetwork`, `netaddr.NOHOST`:** Normalize VLAN subnets for route lookup.
- **`tests.common.helpers.assertions.pytest_assert`:** Custom assertion helper aligning with SONiC test conventions.
- **`scapy.all.IP`, `scapy.all.Ether`:** Packet header classes used when masking expected frames.

## 7. Unspecified Items
- **Additional configuration sources (group vars, CLI params):** Not specified.
- **Exact neighbor inventory or traffic profiles beyond what is observed in the code:** Not specified.
