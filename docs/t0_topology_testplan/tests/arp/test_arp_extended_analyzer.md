# ARP Extended Test Analyzer (tests/arp/test_arp_extended.py)

## 1. Topology type
* **Supported topologies:** The module is marked to run on both `t0` and `dualtor` setups via `pytestmark`, indicating the testbench expects a single ToR or dual ToR fabric with VLAN-backed host-facing networks.【F:tests/arp/test_arp_extended.py†L12-L56】
* **Inference details:** Fixture `intfs_for_test` inspects `tbinfo['topo']` and minigraph data to pick DUT front-panel interfaces, with logic specialized for `t0`, storage backends, and dual ToR variants, confirming reliance on VLAN-based access topologies.【F:tests/arp/conftest.py†L64-L169】

## 2. Overall test case purpose
* **High-level goal:** Validate extended ARP behaviors on SONiC, specifically gratuitous ARP learning and proxy ARP/ND responses, ensuring the DUT correctly learns host entries without solicitation and proxies for downstream hosts in both IPv4 and IPv6 contexts.【F:tests/arp/test_arp_extended.py†L1-L98】
* **Framework context:** These tests run within the SONiC pytest infrastructure, leveraging shared fixtures to manipulate CONFIG_DB, gather minigraph facts, and drive PTF-generated traffic, thereby confirming control-plane features (gratuitous ARP enablement and proxy ARP/NDP) align with fabric expectations.【F:tests/arp/conftest.py†L186-L325】【F:tests/arp/conftest.py†L341-L391】

## 3. Detailed breakdown of sub-testcases
* **`test_arp_garp_enabled`**
  * **Intent & logic:** After ensuring gratuitous ARP is enabled (`garp_enabled`), the test crafts a gratuitous ARP packet with a novel IP/MAC pair and sends it from the PTF port. It then verifies the DUT's ARP table learned the MAC/interface mapping solely from the unsolicited GARP frame.【F:tests/arp/test_arp_extended.py†L19-L53】
  * **Relevance:** Confirms the DUT honors GARP learning, a prerequisite for rapid host mobility handling and redundancy scenarios, ensuring configuration knobs propagated via CONFIG_DB take effect.【F:tests/arp/conftest.py†L186-L238】

* **`test_proxy_arp`**
  * **Intent & logic:** Validates proxy ARP (IPv4) and proxy NDP (IPv6). For each protocol version emitted by `packets_for_test`, the test verifies prerequisites (interface addresses configured), optionally collects debug data for IPv6, sends an ARP/NS from the PTF, and expects the DUT to respond with its router MAC, proving proxy functionality.【F:tests/arp/test_arp_extended.py†L56-L98】
  * **Relevance:** Ensures the DUT can answer on behalf of downstream hosts when proxy ARP/NDP is enabled, supporting complex L2/L3 interconnect designs and dual ToR neighbor resolution.【F:tests/arp/conftest.py†L283-L325】【F:tests/arp/conftest.py†L341-L391】

* **Helper fixture `packets_for_test`**
  * Generates protocol-specific outgoing and expected packets, deriving DUT MAC addresses, incrementing target IPs, and masking IPv6 flow-label fields, enabling parameterized validation across IPv4 and IPv6 without duplicating packet crafting logic.【F:tests/arp/conftest.py†L341-L391】

## 4. Dependencies and prerequisites
* **Autouse setup:** `set_polling_interval` reduces CRM polling interval to accelerate counter updates during the module, then restores defaults, requiring DUT CLI access.【F:tests/arp/conftest.py†L26-L35】
* **Configuration access:** Fixtures `config_facts` and `intfs_for_test` rely on minigraph facts, ASIC instances, and CONFIG_DB content to select viable interfaces and configure temporary IPs, necessitating a fully provisioned SONiC DUT with VLANs and front-panel connectivity.【F:tests/arp/conftest.py†L57-L169】
* **State manipulation:** Fixtures `garp_enabled` and `proxy_arp_enabled` adjust CONFIG_DB entries and CLI settings, requiring the DUT to expose `config vlan proxy_arp` commands and allow `sonic-db-cli` operations.【F:tests/arp/conftest.py†L186-L325】
* **Traffic generation:** `ip_and_intf_info`, `packets_for_test`, and `ptfadapter` demand a PTF host with mapped interfaces and MAC learning capability to transmit and verify frames.【F:tests/arp/conftest.py†L240-L391】

## 5. Key inputs and parameters
* **Topology metadata (`tbinfo`):** Guides interface selection, differentiating storage backend, isolated, and dual ToR setups to keep test ports appropriate.【F:tests/arp/conftest.py†L64-L169】
* **Configuration data (`config_facts`):** Supplies VLAN interfaces and IDs, feeding into both enabling fixtures and packet crafting to align with actual DUT addressing.【F:tests/arp/test_arp_extended.py†L49-L53】【F:tests/arp/conftest.py†L57-L314】
* **PTF interface mapping (`ip_and_intf_info`):** Provides source IPs, IPv6 addresses, and interface indices for traffic injection, ensuring packets target the correct VLAN subnet.【F:tests/arp/test_arp_extended.py†L27-L33】【F:tests/arp/conftest.py†L240-L279】
* **Generated packets (`packets_for_test`):** Parameterizes the test across IPv4/IPv6, controlling expected behavior and enabling conditional debug output for IPv6 flows.【F:tests/arp/test_arp_extended.py†L64-L98】【F:tests/arp/conftest.py†L341-L391】

## 6. External libraries and modules
* **`logging`**: Provides test logging for packet transmission and debug data capture.【F:tests/arp/test_arp_extended.py†L4-L47】
* **`ptf.testutils`, `ptf.mask`, `ptf.packet`**: Used to craft and transmit ARP/NDP packets and to mask non-deterministic IPv6 header fields when validating responses.【F:tests/arp/test_arp_extended.py†L33-L48】【F:tests/arp/conftest.py†L1-L390】
* **`pytest`**: Supplies the testing framework, markers, fixtures, and skipping/assertion utilities.【F:tests/arp/test_arp_extended.py†L6-L98】【F:tests/arp/conftest.py†L5-L325】
* **SONiC helper modules** (`tests.arp.arp_utils`, `tests.common.utilities`, `tests.common.helpers.assertions`, `tests.common.config_reload`, etc.): Provide DUT interaction helpers, IP increment utilities, and assertion wrappers to manage state and validate outcomes consistently.【F:tests/arp/test_arp_extended.py†L8-L53】【F:tests/arp/conftest.py†L8-L325】
* **`scapy` IPv6 helpers**: Enable construction of Neighbor Solicitation/Advertisement packets with correct link-local addressing for IPv6 proxy checks.【F:tests/arp/conftest.py†L15-L390】

## 7. Unspecified items
* **Testbed inventory specifics, CLI arguments beyond defaults, and exact DUT/ASIC models** are not specified within the test case or its local fixtures. Not specified.
