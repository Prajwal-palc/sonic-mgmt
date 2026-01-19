# Port Mirroring Test Analyzer

## 1. Topology Type
- **Topology**: `t0` testbed with a single SONiC DUT interconnected to PTF host ports across VLAN member interfaces.【F:tests/span/test_port_mirroring.py†L10-L12】【F:tests/span/conftest.py†L37-L62】
- **Inference**: The file is marked with `pytest.mark.topology('t0')`, and the fixtures derive three access member ports from the VLAN configuration facts, which is characteristic of the T0 topology where a single DUT connects to multiple TOR-facing endpoints.【F:tests/span/test_port_mirroring.py†L10-L12】【F:tests/span/conftest.py†L37-L62】

## 2. Overall Test Case Purpose
- **Goal**: Validate local SPAN (port mirroring) functionality on SONiC, ensuring sessions mirror traffic correctly for ingress, egress, bidirectional, and multi-source scenarios.【F:tests/span/test_port_mirroring.py†L15-L94】
- **Context**: Within SONiC automation, SPAN enables traffic monitoring. These tests verify that the switch can configure mirror sessions via `config mirror_session span` CLI and forward mirrored copies to a designated monitor port, confirming data-plane visibility for troubleshooting and monitoring workflows.【F:tests/span/test_port_mirroring.py†L15-L94】【F:tests/span/conftest.py†L148-L165】

## 3. Detailed Breakdown of Sub-Testcases
- **`test_mirroring_rx`**
  - **Intent**: Establish a SPAN session mirroring ingress traffic (`rx`) from a single source port to the monitor port, verifying that packets arriving from the PTF host on the DUT are mirrored to the monitor interface.【F:tests/span/test_port_mirroring.py†L15-L29】
  - **Logic**: Uses the shared session setup to send an ICMP packet from the configured source port and validates reception on the monitor port via the helper routine. Confirms the DUT mirrors inbound traffic as configured.【F:tests/span/test_port_mirroring.py†L15-L29】【F:tests/span/span_helpers.py†L8-L21】
  - **Relevance**: Proves baseline ingress mirroring works, establishing confidence in SPAN functionality for capturing traffic entering the switch.

- **`test_mirroring_tx`**
  - **Intent**: Verify SPAN configuration for egress (`tx`) mirroring by sending a packet from the DUT towards the PTF host and ensuring it is copied to the monitor port.【F:tests/span/test_port_mirroring.py†L32-L46】
  - **Logic**: Utilizes the same helper to transmit through the second source index representing outbound traffic and checks mirrored delivery. Demonstrates the switch mirrors egressed packets.【F:tests/span/test_port_mirroring.py†L32-L46】【F:tests/span/span_helpers.py†L8-L21】
  - **Relevance**: Validates that SPAN can capture packets leaving the DUT, which is critical for observing transmitted traffic flows.

- **`test_mirroring_both`**
  - **Intent**: Confirm bidirectional mirroring by sequentially sending packets in both ingress and egress directions under a single session configured for `both`.【F:tests/span/test_port_mirroring.py†L49-L70】
  - **Logic**: Sends ICMP packets using both source indices with the helper function, verifying the monitor port receives mirrored copies for each direction. Ensures combined directional mirroring works.【F:tests/span/test_port_mirroring.py†L49-L70】【F:tests/span/span_helpers.py†L8-L21】
  - **Relevance**: Demonstrates comprehensive SPAN coverage where monitoring requires visibility on both ingress and egress, aligning with network troubleshooting needs.

- **`test_mirroring_multiple_source`**
  - **Intent**: Validate SPAN sessions configured with multiple source ports (comma-separated) still mirror ingress traffic from each source to the monitor port.【F:tests/span/test_port_mirroring.py†L73-L94】
  - **Logic**: The session fixture builds a configuration using both source interfaces; the test sends packets from each source index and verifies mirrored reception twice. Highlights multi-port mirroring capability.【F:tests/span/test_port_mirroring.py†L73-L94】【F:tests/span/conftest.py†L114-L131】【F:tests/span/span_helpers.py†L8-L21】
  - **Relevance**: Ensures SPAN can cover multiple monitored interfaces simultaneously, which is essential for capturing distributed traffic.

- **Helper Functions & Parameterization**
  - **`send_and_verify_mirrored_packet`**: Constructs ICMP packets, sends them via PTF adapter, and confirms they appear on the monitor port, encapsulating the common verification logic for all subtests.【F:tests/span/span_helpers.py†L8-L21】
  - **`setup_session` Fixture**: Applies SPAN configuration before each test, verifies it via `show mirror_session`, and removes it afterward, ensuring consistent DUT state across tests.【F:tests/span/conftest.py†L135-L165】
  - **`session_info` Fixture**: Derives session parameters (direction, source ports, indices) based on the test name, enabling scenario-specific configuration without duplicating code.【F:tests/span/conftest.py†L97-L133】

## 4. Dependencies and Prerequisites
- **Fixtures**: `cfg_facts`, `ports_for_test`, `setup_monitor_port`, `session_info`, and `setup_session` orchestrate DUT selection, port preparation, SPAN session lifecycle, and mirrored port validation.【F:tests/span/conftest.py†L11-L165】
- **Topology Requirements**: A T0 topology with at least three physical VLAN member ports not in PortChannels to serve as two sources and one monitor.【F:tests/span/conftest.py†L37-L62】
- **Release Constraints**: `skip_unsupported_release` automatically skips unsupported SONiC releases earlier than 202012 where SPAN is unavailable.【F:tests/span/conftest.py†L65-L69】
- **Backend Considerations**: The autouse import `skip_test_module_over_backend_topologies` ensures the suite is skipped on back-end storage topologies incompatible with SPAN testing.【F:tests/span/conftest.py†L7-L8】

## 5. Key Inputs and Parameters
- **VLAN and Port Selection**: Derived from persistent config facts to determine source and monitor ports, ensuring tests run on active access ports.【F:tests/span/conftest.py†L37-L62】
- **Session Configuration Parameters**: `session_name`, `session_source_ports`, `session_destination_port`, and `session_direction` drive the CLI configuration for each SPAN session and are customized per test via `session_info`.【F:tests/span/conftest.py†L124-L154】
- **PTF Port Indices**: `source1_index`, `source2_index`, and `destination_index` map logical interfaces to PTF dataplane ports, guiding packet transmission and verification.【F:tests/span/conftest.py†L124-L163】

## 6. External Libraries and Modules
- **`pytest`**: Provides the testing framework, fixtures, and topology markers for orchestrating the SPAN validation scenarios.【F:tests/span/test_port_mirroring.py†L5-L12】
- **`tests.common.fixtures.ptfhost_utils.change_mac_addresses`**: Imported autouse fixture ensuring deterministic MAC addresses on the PTF host; although not directly referenced, it standardizes the PTF environment.【F:tests/span/test_port_mirroring.py†L7-L8】
- **`span_helpers.send_and_verify_mirrored_packet`**: Local helper leveraging `ptf.testutils` to send/verify ICMP packets on the PTF dataplane, enabling consistent packet validation.【F:tests/span/test_port_mirroring.py†L8-L29】【F:tests/span/span_helpers.py†L8-L21】
- **`tests.common.utilities.skip_release`**: Skips test execution on unsupported SONiC releases, enforcing prerequisite firmware versions for SPAN support.【F:tests/span/conftest.py†L7-L69】
- **`ptf.testutils`**: Used within the helper to craft ICMP packets and perform send/verify operations against the PTF dataplane.【F:tests/span/span_helpers.py†L8-L21】

## 7. Unspecified Items
- **Additional Inventory or group_vars parameters**: Not specified in the provided test files.
- **Explicit DUT count or neighbor layout beyond VLAN usage**: Not specified.
