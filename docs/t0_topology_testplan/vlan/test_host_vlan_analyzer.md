# Host VLAN Test Analyzer

## 1. Topology Type
- **Declared topologies:** `t0`, `m0`, `mx`, and `t0-2vlans`, as indicated by `pytestmark = [pytest.mark.topology("t0", "m0", "mx", 't0-2vlans')]`.
- **Inference:** The `pytestmark` topology marker drives how the test runner selects applicable testbeds. The referenced fixture `testbed_params` also queries minigraph data (`get_extended_minigraph_facts`) that is present on multi-DUT T0-style setups, confirming the expectation of a T0-class leaf-spine testbed variant with possible dual ToR (dual-homing) coverage.

## 2. Overall Test Case Purpose
- This file validates that SONiC correctly **prevents VLAN interface–destined traffic from flooding across host-facing bridge ports**.
- Within the broader SONiC QA context, the test ensures host VLAN configuration compliance and L2 control-plane correctness in leaf/rack switch scenarios where server ports are in a VLAN. Avoiding flooding verifies proper MAC learning/forwarding behavior after configuring the VLAN interface MAC address.

## 3. Detailed Breakdown of Sub-testcases
### `test_host_vlan_no_floodling`
- **Intent:** Verifies that ICMP packets targeted at the DUT's VLAN interface are not flooded to other host ports within the same bridge VLAN.
- **Logic:**
  1. Uses `testbed_params` to gather a VLAN interface, its member ports, and associated PTF port mapping.
  2. Ensures the VLAN interface MAC is set through `setup_host_vlan_intf_mac`, accounting for Mellanox ASIC restrictions.
  3. Chooses one host member port to transmit from (`test_ptf_port`) and several others to monitor (`dut_ports_to_check`).
  4. Constructs an ICMP packet targeted at the VLAN interface IP and MAC with a unique fingerprint payload.
  5. For each monitored port, enables `tcpdump` capture via the `log_icmp_updates` context manager while transmitting packets from the PTF.
  6. Fetches the capture file, parses it with Scapy, and asserts that no packets containing the fingerprint are observed. Any presence indicates undesired flooding and fails the test.
- **Importance:** Demonstrates VLAN host isolation, ensuring that SONiC only terminates VLAN interface traffic at the switch CPU and does not propagate it as L2 floods, protecting server networks from stray control-plane traffic.

## 4. Dependencies and Prerequisites
- **Fixtures:**
  - `duthosts`, `rand_one_dut_hostname`, `tbinfo` – provide DUT access and testbed metadata.
  - `ptfadapter` – enables packet injection from the PTF test host.
  - `testbed_params` – extracts VLAN interface details and port mappings from minigraph facts.
  - `verify_host_port_vlan_membership` – confirms that expected host ports are present in the bridge VLAN before testing.
  - `setup_host_vlan_intf_mac` – temporarily configures a deterministic MAC on the VLAN interface and restores it afterward.
  - `toggle_all_simulator_ports_to_rand_selected_tor` – keeps dual ToR mux simulator ports aligned when applicable.
- **Topology constraints:** Availability of a VLAN-enabled T0/M0/MX testbed with host ports mapped to the PTF and access to redis-cli and tcpdump on the DUT.
- **Utilities:** `wait_until`, `delete_running_config`, and `skip_release` ensure timing, cleanup, and release gating.

## 5. Key Inputs and Parameters
- `mg_facts` from `get_extended_minigraph_facts` – supplies VLAN interface names, members, and PTF index mapping.
- `DUT_VLAN_INTF_MAC` – target MAC configured on the VLAN interface for consistent validation, potentially adjusted for Mellanox ASICs via `get_new_vlan_intf_mac_mellanox`.
- `HOST_PORT_FLOODING_CHECK_COUNT`, `ICMP_PKT_COUNT`, `ICMP_PKT_SRC_IP`, `ICMP_PKT_FINGERPRINT` – control how many ports are monitored, number of packets sent, packet source IP, and detection signature.
- `tbinfo["topo"]["name"]` – informs cleanup behavior (e.g., dualtor-specific handling when removing config).

## 6. External Libraries and Modules
- **Standard library:** `contextlib`, `random`, `time`, `tempfile`, `json` – support context managers, sampling, pacing, temporary files, and JSON manipulation.
- **PyTest (`pytest`)** – supplies the testing framework, fixtures, and markers.
- **Scapy (`scapy.all.sniff`)** – reads the captured pcap to detect undesired packets.
- **PTF (`ptf.testutils`)** – crafts and sends ICMP packets from the PTF host.
- **SONiC test helpers:**
  - `tests.common.dualtor.mux_simulator_control` – manages dual ToR mux state.
  - `tests.common.utilities` – provides IP validation (`is_ipv4_address`), waiting helpers, config deletion, and release skipping.
  - `tests.common.helpers.assertions.pytest_assert` – wraps assertions with informative messages.
- **DUT shell interactions:** The `duthost` fixture’s `shell`, `get_dut_iface_mac`, and `get_extended_minigraph_facts` methods execute Ansible-based commands on the device under test.

## 7. Unspecified Items
- Testbed inventory parameters beyond the VLAN facts (e.g., exact port counts or hardware SKUs) – **Not specified**.
- Specifics of `toggle_all_simulator_ports_to_rand_selected_tor` internals – **Not specified**.
- Detailed release support matrix beyond the skipped versions – **Not specified**.
