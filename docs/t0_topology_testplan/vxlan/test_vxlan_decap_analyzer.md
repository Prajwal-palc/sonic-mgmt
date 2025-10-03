# VXLAN Decapsulation Test Analyzer

## 1. Topology Type
- **Topology:** `t0`.
- **Inference:** The test module sets `pytestmark = [pytest.mark.topology('t0')]`, indicating it targets devices under test (DUTs) arranged in the T0 topology variant commonly used in SONiC regression. No additional topology hints are declared in this file.

## 2. Overall Test Case Purpose
- **Objective:** Validate VXLAN decapsulation behavior on a SONiC DUT under different operational states of the VXLAN configuration (no VXLAN, enabled, and removed).
- **Scope in SONiC framework:** The test provisions the DUT with VXLAN tunnel and mapping configuration, prepares the PTF host with ARP responder data, and invokes the `vxlan-decap.Vxlan` PTF script. This aligns with regression coverage for VXLAN functionality by verifying that encapsulated traffic is correctly decapsulated and forwarded when VXLAN is active, and confirming benign behavior otherwise.

## 3. Detailed Breakdown of Sub-Testcases
### `test_vxlan_decap`
- **Intent & Logic:**
  - Consumes the `setup` fixture to gather minigraph facts, stage VXLAN configuration, and initialize the PTF host.
  - Uses the parameterized `vxlan_status` fixture to iterate over three scenarios: `NoVxLAN`, `Enabled`, and `Removed`. Depending on the scenario, the fixture programs or clears VXLAN tunnel/map entries in the ASIC DB, or simply clears forwarding caches.
  - Determines if the topology is dual ToR active-active and collects SONiC administrative credentials (including alternate password) for the PTF script.
  - Executes the `ptf_runner` with the `vxlan-decap.Vxlan` test, passing scenario-specific flags, configuration file locations, and authentication details. The runner captures logs per scenario for later inspection.
- **Relevance:** This single pytest test orchestrates the entire VXLAN decapsulation validation by varying the control-plane state and exercising the data-plane checks housed in the PTF test script. Passing the PTF script across scenarios demonstrates correct handling of VXLAN tunnels on the DUT.

### Helper Fixtures and Utilities
- **`prepare_ptf` helper:** Configures ARP responder inside the PTF container, writes minigraph-derived VXLAN information (`/tmp/vxlan_decap.json`), and ensures VLAN MAC details are available to the PTF test.
- **`generate_vxlan_config_files`:** Constructs `/tmp/vxlan_db.tunnel.json` and `/tmp/vxlan_db.maps.json` based on minigraph loopback and VLAN data so the DUT can be programmed with VXLAN tunnel and map entries.
- **`setup` fixture (module scope):**
  - Acquires extended minigraph facts, handles dual ToR adjustments for unselected ToR mapping, pushes template `vxlan_switch.json` into the SWSS container, and invokes `prepare_ptf` and `generate_vxlan_config_files`.
  - Provides gathered facts to tests and performs teardown by stopping the ARP responder and removing VXLAN configuration from the ASIC DB.
- **`vxlan_status` fixture (function scope, parameterized):** Applies or removes VXLAN configuration for each scenario before executing the PTF test, and clears FDB/ARP tables when no VXLAN is configured. This fixture drives the scenario coverage within `test_vxlan_decap`.

## 4. Dependencies and Prerequisites
- **Fixtures:** `duthosts`, `rand_one_dut_hostname`, `ptfhost`, `tbinfo`, `creds`, `toggle_all_simulator_ports_to_rand_selected_tor_m`, along with module-level fixtures defined in the file (`setup`, `vxlan_status`). These fixtures supply DUT/PTF handles, topology information, credentials, and traffic-mirroring controls essential for the test flow.
- **Topology Constraints:** Requires availability of the `t0` topology and, optionally, dual ToR active-active configuration (`dualtor-aa` substring check) to exercise dual ToR–specific logic.
- **Environment:** Access to the SWSS container and Redis DB on the DUT for programming VXLAN objects, and supervisory control of services inside the PTF container.

## 5. Key Inputs and Parameters
- **Static constants:** `VTEP2_IP`, `VNI_BASE`, and `COUNT` determine remote VTEP address, VNI offset, and packet iteration count for the PTF script.
- **Minigraph facts (`mg_facts`):** Provide port indices, VLANs, interfaces, loopback addresses, and MAC addresses used to build configuration files and PTF metadata.
- **Credential inputs (`creds` fixture and derived alt password):** Supply authentication for the PTF script to interact with the DUT when necessary.
- **PTF configuration paths:** `/tmp/vxlan_decap.json`, `/tmp/vxlan_db.tunnel.json`, `/tmp/vxlan_db.maps.json`, and `/vxlan.switch.json` feed the PTF and DUT control logic.
- **Scenario parameter (`vxlan_status`):** Drives configuration toggling to test VXLAN behavior under different operational states.

## 6. External Libraries and Modules
- **Standard libraries:** `json`, `logging`, `datetime`, and `time.sleep` handle serialization, logging, timestamping, and pacing.
- **PyPI / third-party:**
  - `pytest` for fixture and test orchestration.
  - `jinja2.Template` for rendering the `arp_responder.conf` template before copying to the PTF host.
  - `netaddr.IPAddress` to identify IPv4 loopback addresses when generating VXLAN configuration.
- **SONiC test utilities:**
  - `tests.common.fixtures.ptfhost_utils` suite for manipulating the PTF container (fixtures imported for side effects).
  - `tests.ptf_runner.ptf_runner` to execute the PTF data-plane test cases.
  - `tests.common.dualtor.mux_simulator_control` to control the dual ToR mux simulator state (fixture imported for side effects).
  - Local helpers `render_template_to_host` and `DUT_VXLAN_PORT_JSON` for pushing VXLAN switch configuration artifacts.

## 7. Unspecified Items
- Specific packet expectations, pass/fail criteria, and detailed PTF script assertions are defined within `ptftests/vxlan-decap.Vxlan` and are **not specified** in this file.
- Any particular values from `testbed.yaml` or inventory beyond those fetched via fixtures are **not specified** here.
