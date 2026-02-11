# SM_ISCLI_28: BGP Configuration Mode - Show Configuration Verification

**Author:** Athira
**Date:** 2026-02-11
**Feature Category:** Routing / BGP CLI
**Test Directory:** `spytest/tests/routing/bgp/`
**Test File:** `test_sm_iscli_28_bgp_show_config.py`
**Vars File:** `spytest/vars/routing/bgp/vars_sm_iscli_28.yaml`

---

## Overview

Verify that `show configuration` command displays complete BGP configuration when executed from within BGP configuration modes (router-bgp, address-family, neighbor contexts). This test validates the fix for a bug where SMC IS-CLI did not show BGP configs when `show configuration` was run from BGP configuration mode.

**Bug Scenario:**
- Configure BGP in IS-CLI
- While in BGP configuration mode, execute `show configuration`
- **Expected:** All relevant BGP configuration should be displayed
- **Bug (old behavior):** SMC IS-CLI would not show BGP configs (Broadcom IS-CLI shows them correctly)

---

## Test Scope

### Commands Under Test

1. **BGP Configuration:**
   - `router bgp <asn>`
   - `address-family ipv4 unicast`
   - `address-family l2vpn evpn`
   - `neighbor <ip> remote-as <asn>`
   - `redistribute connected`
   - `activate` (in address-family context)

2. **Show Commands:**
   - `show configuration` (from various BGP sub-modes)

### Configuration Modes Tested

1. **router-bgp mode** - `sonic(config-router-bgp)#`
2. **router-bgp address-family mode** - `sonic(config-router-bgp-af)#`
3. **router-bgp neighbor mode** - `sonic(config-router-bgp-neighbor)#`
4. **router-bgp neighbor address-family mode** - `sonic(config-router-bgp-neighbor-af)#`

---

## Test Cases

### TC_28.1: Show Configuration from Router BGP Mode

**Objective:** Verify `show configuration` displays complete BGP config when executed from router-bgp mode.

**Steps:**
1. Enter configuration mode
2. Enter `router bgp <asn>` mode
3. Configure address-family ipv4 unicast with redistribute connected
4. Configure address-family l2vpn evpn
5. Configure BGP neighbor with remote-as
6. Execute `show configuration` from router-bgp mode
7. Verify output contains:
   - router bgp statement
   - address-family configurations
   - redistribute statements
   - neighbor configurations

**Expected Result:**
- `show configuration` displays all BGP configuration elements
- Output includes address-family blocks
- Output includes neighbor configurations
- No configuration is hidden or omitted

**Priority:** High
**Type:** Functional

---

### TC_28.2: Show Configuration from Router BGP Address-Family Mode

**Objective:** Verify `show configuration` displays address-family config when executed from router-bgp-af mode.

**Steps:**
1. Enter configuration mode
2. Enter `router bgp <asn>` mode
3. Enter `address-family ipv4 unicast` mode
4. Configure `redistribute connected`
5. Execute `show configuration` from address-family mode
6. Verify output contains:
   - address-family ipv4 unicast statement
   - redistribute connected statement
   - exit statement

**Expected Result:**
- `show configuration` displays address-family configuration
- Redistribution policy is shown
- Configuration context is correctly displayed

**Priority:** High
**Type:** Functional

---

### TC_28.3: Show Configuration from Router BGP Neighbor Mode

**Objective:** Verify `show configuration` displays neighbor config when executed from router-bgp-neighbor mode.

**Steps:**
1. Enter configuration mode
2. Enter `router bgp <asn>` mode
3. Configure `neighbor <ip> remote-as <asn>`
4. Enter neighbor configuration mode
5. Configure neighbor address-family l2vpn evpn with activate
6. Exit to neighbor mode
7. Execute `show configuration` from neighbor mode
8. Verify output contains:
   - neighbor remote-as statement
   - neighbor address-family configurations
   - activate statement within address-family

**Expected Result:**
- `show configuration` displays neighbor configuration
- Address-family sub-configuration for neighbor is shown
- Activate commands are included

**Priority:** High
**Type:** Functional

---

### TC_28.4: Show Configuration from Router BGP Neighbor Address-Family Mode

**Objective:** Verify `show configuration` displays neighbor address-family config when executed from router-bgp-neighbor-af mode.

**Steps:**
1. Enter configuration mode
2. Enter `router bgp <asn>` mode
3. Configure `neighbor <ip> remote-as <asn>`
4. Enter neighbor address-family l2vpn evpn mode
5. Configure `activate`
6. Execute `show configuration` from neighbor address-family mode
7. Verify output contains:
   - address-family l2vpn evpn statement
   - activate statement

**Expected Result:**
- `show configuration` displays neighbor address-family configuration
- Activate statement is shown
- Context is correctly represented

**Priority:** High
**Type:** Functional

---

### TC_28.5: Pagination Handling for Large BGP Configuration

**Objective:** Verify `show configuration` handles pagination correctly for large BGP configurations.

**Steps:**
1. Configure BGP with multiple address-families and neighbors
2. Execute `show configuration` from router-bgp mode
3. Verify pagination is handled automatically (no manual --more interaction needed)
4. Verify all configuration is captured

**Expected Result:**
- Pagination is handled transparently
- All configuration is retrieved
- No data loss due to pagination

**Priority:** Medium
**Type:** Functional

---

## Topology Requirements

- **Min Topology:** Single DUT (`D1`)
- **Device Type:** Hardware or Virtual (both supported)
- **BGP Requirement:** BGP must be supported/enabled

**Topology Diagram:**
```
# Topology - 1 node
# +--------------------+
# |        DUT1        |
# |   (BGP Config)     |
# +--------------------+
```

---

## Pre-requisites

- SONiC device with BGP support
- IS-CLI (klish) available
- No existing BGP configuration that conflicts with test
- Test should cleanup BGP configuration after execution

---

## CLI Types Tested

- **klish (IS-CLI):** Primary focus - this is where the bug exists
- **click:** Not applicable (bug is specific to IS-CLI)

---

## Test Variables (YAML)

**File:** `spytest/vars/routing/bgp/vars_sm_iscli_28.yaml`

```yaml
defaults:
  cli_type: klish
  verify_timeout: 30
  cleanup: true
  min_topology:
    - "D1"

testcases:
  "28.1":
    title: "Show Configuration from Router BGP Mode"
    description: "Verify show configuration displays complete BGP config from router-bgp mode"
    bgp_config:
      asn: 65001
      address_families:
        - ipv4_unicast:
            redistribute: ["connected"]
        - l2vpn_evpn: {}
      neighbors:
        - ip: "20.1.1.4"
          remote_as: 65001
          address_families:
            - l2vpn_evpn:
                activate: true
    expected_in_output:
      - "router bgp 65001"
      - "address-family ipv4 unicast"
      - "redistribute connected"
      - "address-family l2vpn evpn"
      - "neighbor 20.1.1.4 remote-as 65001"
      - "activate"

  "28.2":
    title: "Show Configuration from Router BGP Address-Family Mode"
    description: "Verify show configuration from address-family context"
    bgp_config:
      asn: 65001
      address_family:
        type: "ipv4 unicast"
        redistribute: ["connected"]
    mode: "config-router-bgp-af"
    expected_in_output:
      - "address-family ipv4 unicast"
      - "redistribute connected"

  "28.3":
    title: "Show Configuration from Router BGP Neighbor Mode"
    description: "Verify show configuration from neighbor context"
    bgp_config:
      asn: 65001
      neighbor:
        ip: "20.1.1.4"
        remote_as: 65001
        address_families:
          - l2vpn_evpn:
              activate: true
    mode: "config-router-bgp-neighbor"
    expected_in_output:
      - "neighbor 20.1.1.4 remote-as 65001"
      - "address-family l2vpn evpn"
      - "activate"

  "28.4":
    title: "Show Configuration from Router BGP Neighbor Address-Family Mode"
    description: "Verify show configuration from neighbor address-family context"
    bgp_config:
      asn: 65001
      neighbor:
        ip: "20.1.1.4"
        remote_as: 65001
        address_family:
          type: "l2vpn evpn"
          activate: true
    mode: "config-router-bgp-neighbor-af"
    expected_in_output:
      - "address-family l2vpn evpn"
      - "activate"

  "28.5":
    title: "Pagination Handling for Large BGP Configuration"
    description: "Verify show configuration handles pagination for large configs"
    bgp_config:
      asn: 65001
      address_families:
        - ipv4_unicast:
            redistribute: ["connected", "static"]
        - ipv6_unicast:
            redistribute: ["connected"]
        - l2vpn_evpn: {}
      neighbors:
        - ip: "20.1.1.4"
          remote_as: 65001
        - ip: "20.1.1.5"
          remote_as: 65002
        - ip: "20.1.1.6"
          remote_as: 65003
    pagination_test: true
    expected_min_lines: 15
```

---

## Implementation Notes

### Key Implementation Details

1. **Configuration Approach:**
   - Use `st.config()` with `type="klish"` for BGP configuration
   - Navigate to specific BGP sub-modes before executing `show configuration`
   - Use `skip_error_check=True` initially to detect if command fails

2. **Show Configuration Execution:**
   - Execute `show configuration` using `st.show()` with `type="klish"`
   - Handle pagination automatically by using appropriate SpyTest functions
   - Consider using `st.config()` with `more` handling for large outputs

3. **Verification Strategy:**
   - Parse output of `show configuration` as text
   - Check for presence of expected configuration lines
   - Verify configuration elements are not missing
   - Ensure complete configuration is displayed (not truncated)

4. **Pagination Handling:**
   - Use `skip_tmpl=True` for raw output capture
   - Implement automatic '--more' handling
   - Verify complete output is captured without manual intervention

5. **Cleanup:**
   - Remove all BGP configuration in teardown
   - Use `no router bgp <asn>` to cleanly remove BGP config
   - Verify BGP config is removed after test

### Expected CLI Flow

```bash
# Test Case 28.1 example flow
sonic-cli
conf t
router bgp 65001
  address-family ipv4 unicast
    redistribute connected
    exit
  address-family l2vpn evpn
    exit
  neighbor 20.1.1.4 remote-as 65001
    address-family l2vpn evpn
      activate
      exit
    exit
  # Now execute show configuration
  show configuration
  # Verify output includes all above config
end
```

---

## Expected Test Runtime

- **Per Test Case:** 10-20 seconds
- **Total Suite:** < 2 minutes

---

## Markers

```python
@pytest.mark.topology("D1")
@pytest.mark.routing
@pytest.mark.bgp
@pytest.mark.cli_validation
```

---

## Success Criteria

- All test cases pass
- `show configuration` displays complete BGP configuration from all sub-modes
- No configuration elements are hidden or omitted
- Pagination is handled correctly
- Test cleanup leaves no BGP configuration residue

---

## Known Issues / Observations

**Bug (before fix):**
- SMC IS-CLI `show configuration` from BGP mode did not show BGP configs
- Broadcom IS-CLI correctly showed BGP configs

**Expected behavior (after fix):**
- SMC IS-CLI should match Broadcom IS-CLI behavior
- All BGP configuration should be visible from `show configuration` in any BGP sub-mode

---

## How to Run

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_1node.yaml \
  tests/routing/bgp/test_sm_iscli_28_bgp_show_config.py \
  --logs-path ./logs/sm_iscli_28_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native \
  --port-init-wait 0
```

---

## References

- Manual test log from SONiC device (2026-01-29)
- SONiC Version: SONiC.202505-smci-dev-iscli-2026-01-29T04-02-03
- SPyTest coding guideline: `spy_test_coding_guideline.md`
- Bug Report: SM_ISCLI_28 - show configuration in BGP mode incomplete
