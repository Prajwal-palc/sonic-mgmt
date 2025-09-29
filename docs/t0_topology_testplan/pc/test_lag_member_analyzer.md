# LAG Member Test Analyzer

## 1. Topology Type
- **Topology:** `t0` fabric with server-facing VLANs and a single DUT under test.
- **Inference:** The module-level `pytestmark` declares `pytest.mark.topology("t0")`, constraining the fixture selection and inventory to t0-specific resources.【F:tests/pc/test_lag_member.py†L19-L21】

## 2. Overall Test Case Purpose
- **Goal:** Validate Link Aggregation Group (LAG) functionality on a SONiC DUT, ensuring correct member status, control-plane programming, and data-plane forwarding when ports are aggregated and traffic is sent across both aggregated and standalone links.
- **Context:** In SONiC regression, t0 topologies emulate TOR behavior with directly attached hosts. This test ensures that after dynamically creating a LAG between the DUT and the PTF host, the control-plane state (PORTCHANNEL DB entries, ARP tables) and forwarding behavior remain correct, safeguarding SONiC's link resilience and load-balancing guarantees.【F:tests/pc/test_lag_member.py†L112-L206】【F:tests/pc/test_lag_member.py†L406-L460】

## 3. Detailed Breakdown of Sub-testcases
### `test_lag_member_status`
- **Intent & Logic:**
  - Uses the preconfigured LAG (via the `ptf_dut_setup_and_teardown` fixture) to query `duthost.get_port_channel_status` for `PortChannel1`.
  - Derives the expected member count from platform HWSKU defaults constrained by the most common port speed on the selected VLAN.
  - Asserts that all expected members appear in the port-channel status and that each member is selected by the LACP runner. When retry counters are exposed, checks they match the expected value of 3, validating stable LACP negotiations.【F:tests/pc/test_lag_member.py†L406-L432】
- **Relevance:** Confirms the control-plane state transitions after LAG creation, ensuring SONiC properly reports LAG membership and partner synchronization, which is foundational before traffic tests.

### `test_lag_member_traffic`
- **Intent & Logic:**
  - Performs ARP warm-up pings from both the LAG interface and the standalone port to ensure neighbor entries exist.
  - Verifies ARP resolution on the DUT for both the aggregated and standalone interfaces.
  - Invokes `run_lag_member_traffic_test`, which executes a PTF test (`lag_test.LagMemberTrafficTest`) to send ICMP flows among LAG members and the standalone port, validating bidirectional reachability across different attachment points.【F:tests/pc/test_lag_member.py†L434-L460】【F:tests/pc/test_lag_member.py†L372-L405】
- **Relevance:** Demonstrates data-plane correctness by ensuring traffic distribution and connectivity function as expected across aggregated links, complementing the status validation.

### Helper and Fixture Functions
- **`run_lag_member_traffic_test`:** Packages parameters (router MAC, VLAN info, LAG member lists) and launches the PTF-based traffic generator to exercise ICMP flows, bridging Python orchestration with PTF tests.【F:tests/pc/test_lag_member.py†L372-L405】
- **`generate_port_config`, `setup_dut_lag`, `setup_ptf_lag`:** Dynamically discover suitable ports, configure LAG interfaces on the DUT/PTF, assign VLAN/IP, and clear stale forwarding state to build a reproducible environment for the tests.【F:tests/pc/test_lag_member.py†L206-L360】
- **`common_setup_teardown`, `ptf_dut_setup_and_teardown`, `most_common_port_speed`:** Provide shared resource preparation, including copying test assets, computing dominant port speed, and ensuring proper cleanup via config reload and PTF teardown sequences.【F:tests/pc/test_lag_member.py†L332-L369】
- **`check_arp`:** Utility to poll the DUT ARP table for expected neighbor entries before traffic validation.【F:tests/pc/test_lag_member.py†L392-L401】

## 4. Dependencies and Prerequisites
- **Fixtures:** `duthost`, `ptfhost`, `tbinfo`, `copy_acstests_directory`, `copy_ptftests_directory`, `copy_arp_responder_py`, `common_setup_teardown`, `ptf_dut_setup_and_teardown`, `most_common_port_speed`. These supply device handles, topology metadata, and ensure PTF test assets/ARP responder are available.【F:tests/pc/test_lag_member.py†L12-L15】【F:tests/pc/test_lag_member.py†L332-L369】
- **Topology Constraints:** Requires a t0 testbed with sufficient active VLAN members to create a LAG and a spare standalone port, as enforced by `get_vlan_id` and port-speed checks.【F:tests/pc/test_lag_member.py†L206-L288】
- **Prerequisite State:** DUT must allow ACL table removal (`remove_acl_table`) and configuration reload, and PTF must support creating Linux bonds and running `arp_responder` under supervisor.【F:tests/pc/test_lag_member.py†L112-L206】【F:tests/pc/test_lag_member.py†L228-L312】

## 5. Key Inputs and Parameters
- **Hardware SKU Mapping:** `HWSKU_INTF_NUMBERS_DICT` governs expected LAG member counts per platform, adjusting default expectations.【F:tests/pc/test_lag_member.py†L37-L46】
- **Dynamic VLAN/Port Selection:** `generate_port_config` derives `src_vlan_id`, port mappings, and IP assignments using DUT config facts and `tbinfo` topology map, ensuring the test adapts to the deployed inventory.【F:tests/pc/test_lag_member.py†L206-L288】
- **IP Assignments:** Static VLAN ID 109 with derived IPs for DUT LAG, PTF LAG, and standalone port are injected to drive ICMP and ARP validation.【F:tests/pc/test_lag_member.py†L282-L306】
- **PTF Runner Parameters:** Includes DUT router MAC, VLAN info, aggregated member list, standalone interface, and `kvm_support` flag to orchestrate the packet test.【F:tests/pc/test_lag_member.py†L372-L405】

## 6. External Libraries and Modules
- **Standard Libraries:** `time`, `logging`, `ipaddress`, `json`, `sys`, and `collections.Counter` provide timing control, logging, IP calculations, JSON handling, runtime compatibility, and frequency analysis for port speeds.【F:tests/pc/test_lag_member.py†L1-L8】【F:tests/pc/test_lag_member.py†L206-L219】【F:tests/pc/test_lag_member.py†L380-L388】
- **Pytest:** Core testing framework managing fixtures, marks, and assertions.【F:tests/pc/test_lag_member.py†L1-L21】
- **SONiC Test Utilities:**
  - `tests.common.helpers.assertions` for `pytest_assert`/`pytest_require`.
  - `tests.ptf_runner.ptf_runner` to execute PTF scripts.
  - `tests.common.utilities.wait_until` for polling conditions.
  - `tests.common.fixtures.ptfhost_utils` for copying PTF assets.
  - `tests.common.config_reload.config_reload` to revert DUT state.【F:tests/pc/test_lag_member.py†L10-L16】
- **PTF Host APIs:** Methods invoked on `ptfhost` (e.g., `create_lag`, `set_dev_up_or_down`, `ptf_nn_agent`) rely on Ansible modules provided by SONiC test infrastructure to manipulate the PTF container.【F:tests/pc/test_lag_member.py†L228-L312】

## 7. Unspecified Items
- **Topology Diagram or Viewer Details:** Not specified.
- **Exact traffic profiles inside `lag_test.LagMemberTrafficTest`:** Not specified within this file.
- **External configuration sources (group_vars, CLI args):** Not specified beyond dynamic facts usage.
