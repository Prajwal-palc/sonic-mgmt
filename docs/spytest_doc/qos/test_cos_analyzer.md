# QoS CoS Test Analyzer

## 1. Topology type
- **Topology**: D1T1:2 (one DUT connected to a traffic generator with two links).
- **Inference**: The module-level fixture calls `st.ensure_min_topology("D1T1:2")` and later acquires traffic generator port handles `T1D1P1` and `T1D1P2`, indicating a single DUT with two tester connections.【F:spytest/tests/qos/test_cos.py†L25-L37】

## 2. Overall test case purpose
- **Goal**: Validate CoS queue classification and mapping on a SONiC DUT by driving specific traffic profiles from a traffic generator and inspecting queue counters on the device.
- **Context**: Within the SpyTest QoS suite, this file ensures that packets destined for the CPU hit the expected CoS queue and that user priority-to-queue mappings steer VLAN traffic to the intended hardware queues. The automation covers CPU queue visibility (using `show queue counters` or ASIC BCM counters) and egress interface queue counters, reflecting SONiC QoS control-plane and data-plane behaviors.【F:spytest/tests/qos/test_cos.py†L40-L191】【F:spytest/tests/qos/test_cos.py†L242-L352】

## 3. Detailed breakdown of sub-testcases
### 3.1 `test_ft_cos_cpu_counters`
- **Intent**: Confirm that control-plane traffic types (ARP replies, L2 unicast to the switch MAC, IPv6 packets with varying hop-limits, and IPv4 packets with TTL 0) are trapped to the CPU and increment the expected CoS queue counters.
- **Logic**:
  1. Configure IPv4 and IPv6 addresses on the DUT interface connected to the tester (`configuring_ipv4_and_ipv6_address`).
  2. Transmit pre-created TG streams for ARP replies and unicast frames toward the DUT’s MAC, verifying CPU queue counters via `cos_counters_checking`.
  3. Verify IPv6 and IPv4 reachability (ping helpers) and send traffic with hop-limit/TTL variations to ensure exception packets are trapped.
  4. Aggregate status from each traffic type and fail if any queue counter does not increment.【F:spytest/tests/qos/test_cos.py†L152-L224】【F:spytest/tests/qos/test_cos.py†L242-L304】
- **Why it matters**: Demonstrates that SONiC’s CPU CoS queue handling is correctly classifying multiple protocols, a prerequisite for accurate control-plane QoS and network stability.

### 3.2 `test_ft_cos_tc_queue_map`
- **Intent**: Validate that the TC-to-queue mapping translates VLAN priority 4 traffic into queue 5 when the mapping is configured.
- **Logic**:
  1. Configure MAC aging time and create a VLAN with both tester ports as tagged members (`fdb_config`, `vlan_config`).
  2. Send VLAN-tagged traffic from the receiver port to populate the FDB, confirming the dynamic MAC entry exists.
  3. Apply the QoS map tying traffic class 4 to queue 5 and bind it to the ingress port (`configuring_tc_to_queue_map`, `binding_queue_map_to_interfaces`).
  4. Clear counters, transmit priority-tagged traffic from the ingress port, and check that the UC5 queue counter increments sufficiently (>2000 packets).【F:spytest/tests/qos/test_cos.py†L227-L352】
- **Why it matters**: Ensures SONiC enforces administrator-defined QoS mappings so that traffic classes align with hardware queueing policies, validating data-plane QoS behavior.

### Helper functions and fixtures
- **`cos_module_hooks`**: Module-scoped autouse fixture that prepares topology, initializes shared `data` variables, configures DUT MAC information, and provisions traffic generator streams; it also performs cleanup by clearing QoS/VLAN state after all tests.【F:spytest/tests/qos/test_cos.py†L20-L121】
- **`cos_func_hooks`**: Function-scoped autouse fixture that removes test-specific IP addresses after `test_ft_cos_cpu_counters`, ensuring isolation between tests.【F:spytest/tests/qos/test_cos.py†L103-L110】
- **Support helpers**: Functions like `cos_variables`, `configuring_ipv4_and_ipv6_address`, `cos_counters_checking`, `ping_ipv6_interface`, `ping_ipv4_interface`, `fdb_config`, and `vlan_config` encapsulate repeated setup/verification tasks for readability and reuse across the subtests.【F:spytest/tests/qos/test_cos.py†L122-L239】

## 4. Dependencies and prerequisites
- **Fixtures**: Relies on SpyTest-provided fixtures (`cos_module_hooks`, `cos_func_hooks`) to manage DUT and traffic generator state before/after tests.【F:spytest/tests/qos/test_cos.py†L20-L121】【F:spytest/tests/qos/test_cos.py†L103-L110】
- **Topology constraints**: Requires one DUT with two traffic generator links (D1T1:2) exposing ports `D1T1P1` and `D1T1P2`.【F:spytest/tests/qos/test_cos.py†L25-L37】
- **Traffic generator**: Needs a TG capable of configuring Ethernet/VLAN streams, ARP, IPv4, and IPv6 flows, as the tests create multiple stream types and rely on TG ping operations.【F:spytest/tests/qos/test_cos.py†L40-L204】
- **Queue counter access**: Depends on SONiC supporting either the public `show queue counters` CLI or BCM counter access to observe CPU queues (`st.is_feature_supported("bcmcmd", ...)`).【F:spytest/tests/qos/test_cos.py†L176-L191】

## 5. Key inputs and parameters
- **Addressing and QoS constants**: `cos_variables` seeds IP addresses, VLAN ID 555, MAC addresses, VLAN priority 4, target queue 5, and other parameters consumed by stream configuration and QoS mapping logic.【F:spytest/tests/qos/test_cos.py†L122-L149】
- **Interface references**: Uses `vars.D1T1P1` and `vars.D1T1P2` from the ensured topology for IP configuration, VLAN membership, and queue inspection.【F:spytest/tests/qos/test_cos.py†L152-L352】
- **Traffic generation handles**: `data.tg`, `data.tg_ph_1`, `data.tg_ph_2`, and `data.streams[...]` identify TG ports and created stream IDs for subsequent run/stop actions.【F:spytest/tests/qos/test_cos.py†L31-L97】

## 6. External libraries and modules
- **`spytest` utilities (`st`, `tgapi`, `SpyTestDict`)**: Provide logging, topology helpers, and abstraction over the traffic generator interfaces.【F:spytest/tests/qos/test_cos.py†L5-L41】
- **Routing and system APIs**: `apis.routing.ip`, `apis.routing.arp`, `apis.system.basic`, and `apis.system.interface` configure interfaces, verify IPs/ARP/ND, and retrieve queue counters.【F:spytest/tests/qos/test_cos.py†L8-L16】【F:spytest/tests/qos/test_cos.py†L152-L224】【F:spytest/tests/qos/test_cos.py†L324-L352】
- **Switching/QoS APIs**: `apis.switching.vlan`, `apis.switching.mac`, `apis.qos.cos`, and `apis.qos.qos` manage VLANs, MAC tables, TC-to-queue maps, and QoS profiles.【F:spytest/tests/qos/test_cos.py†L13-L16】【F:spytest/tests/qos/test_cos.py†L227-L352】
- **ASIC utilities**: `apis.common.asic` offers fallback access to BCM counters when native CLI support is unavailable.【F:spytest/tests/qos/test_cos.py†L11-L191】
- **Common helpers**: `utilities.common.filter_and_select` assists in extracting counter fields from command output.【F:spytest/tests/qos/test_cos.py†L18-L189】

## 7. Unspecified items
- **SONiC image/build requirements**: Not specified.
- **Exact QoS queue identifiers beyond UC5/MC1**: Not specified.
- **Traffic generator hardware model or software version**: Not specified.
