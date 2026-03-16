# L2 ACL Test Plan — Minimal Topology

## Overview

This test plan validates L2 (Layer 2 / MAC/VLAN-level) Access Control Lists on a Device Under Test using external Scapy-based traffic generation. **All tests are executed with traffic flowing from external TX and RX hosts (NOT running inside the DUT).**

## Architecture

### Network Topology

```
┌─────────────────┐                       ┌─────────────────┐
│  External Host  │                       │  External Host  │
│    TX (Scapy)   │                       │    RX (Scapy)   │
│   10.0.0.1/24   │                       │   20.0.0.2/24   │
│ MAC:AA:AA:AA:01 │                       │ MAC:BB:BB:BB:02 │
└────────┬────────┘                       └────────┬────────┘
         │                                         │
         │ eth0                              eth1  │
         │ (Raw Scapy                      (Raw   │
         │  L2 frames)                      Scapy  │
         │                                 sniff)  │
         │                                         │
         ├─────────────[ DUT (VS or HW) ]─────────┤
         │          Port1    ↔    Port2           │
         │       (ACL Ingress applied here)       │
         │                                         │
         └─────────────────────────────────────────┘

DUT switching path: Port1 (RX) → L2 ACL → Bridging → Port2 (TX)
```

### Key Architecture Decisions

1. **External Traffic Sources**: Scapy runs on separate physical or virtual hosts connected to DUT ports (not containerized within DUT-VS)
2. **L2 Switching Topology**: TX Host → DUT Port1 (L2 mode, ingress ACL) → Bridging Decision → DUT Port2 (L2 mode) → RX Host
3. **Unidirectional Primary Flow**: TX Host → DUT Port1 → Switching Bridge → DUT Port2 → RX Host (one-way)
4. **ACL Enforcement Point**: Ingress on Port1 (ACLs evaluated immediately upon L2 frame arrival)
5. **No IP Routing**: Unlike L3 ACL tests, L2 tests focus on MAC address and VLAN switching (not IP routing)

| Role        | Interface | IP Address  | MAC Address       | Port Mode |
|-------------|-----------|-------------|-------------------|-----------|
| TX (Sender) | eth0      | 10.0.0.1/24 | 00:AA:AA:AA:AA:01 | N/A (host) |
| RX (Receiver)| eth1     | 20.0.0.2/24 | 00:BB:BB:BB:BB:02 | N/A (host) |
| DUT Port1   | Port1     | (unrouted)  | Inherits from port | Switchport |
| DUT Port2   | Port2     | (unrouted)  | Inherits from port | Switchport |

---

## Prerequisites & Requirements

### Host Requirements (TX and RX hosts)

**OS & Kernel:**
- Linux kernel 5.4+ (tested on Ubuntu 20.04 LTS, 22.04 LTS)
- Python 3.8+ with pip3

**Required Software:**
```bash
# Install Scapy
sudo pip3 install scapy --break-system-packages

# Verify installation
python3 -c "from scapy.all import *; print(f'Scapy {SCAPY_VERSION} OK')"
```

**Network Interface Drivers:**
- E1000, virtio-net, or modern NIC drivers supporting raw packet I/O
- Verify with: `ethtool -i eth0` (should show driver name)

**Permissions:**
- Scripts require `sudo` for raw socket operations (`CAP_NET_RAW`)
- Alternatively, grant capabilities: `sudo setcap cap_net_raw=ep /usr/bin/python3`

**Network Stack Configuration:**
- Disable local iptables/nftables rules that might block traffic:
  ```bash
  sudo iptables -P INPUT ACCEPT
  sudo iptables -P FORWARD ACCEPT
  sudo iptables -P OUTPUT ACCEPT
  ```
- Verify no local firewall is enabled: `sudo ufw status` should show "inactive"

### DUT Requirements (Port1 & Port2 Configuration)

**Port Connectivity & L2 Mode:**
- Port1 and Port2 must be operationally UP (link layer)
- **Both ports must be in L2 switchport mode** (not L3 routed mode)
- Verify: `show interface status | grep -E "Port1|Port2"`

**Port Mode Configuration (Critical for L2):**
```
DUT# configure terminal
DUT# interface Port1
DUT# switchport mode access
DUT# no shutdown
DUT# exit
DUT# interface Port2
DUT# switchport mode access
DUT# no shutdown
DUT# exit
```

**VLAN Configuration (Required for L2-06, L2-07 tests):**
- Create VLAN 1 (native/default): Typically pre-configured
- Create VLAN 10, 100, 200 for test cases
- Assign Port1/Port2 to appropriate VLANs

```
DUT# configure terminal
DUT# vlan 10
DUT# exit
DUT# vlan 100
DUT# exit
DUT# vlan 200
DUT# exit

# Assign ports to VLANs (example: access VLAN)
DUT# interface Port1
DUT# switchport access vlan 1
DUT# exit
DUT# interface Port2
DUT# switchport access vlan 1
DUT# exit
```

**MAC Address Learning:**
- DUT must support dynamic MAC address learning from frames on Port1
- MAC aging timeout (typical: 300 seconds / 5 minutes)
- Verify: `show mac address-table` after sending traffic from TX host

**Baseline L2 State:**
- DUT should start with **NO L2 ACLs** applied (or all in `shutdown` state)
- Both ports should be in same VLAN (VLAN 1 is typical default)
- Each test case explicitly configures its required ACL rules
- After each test, ACL rules are REMOVED to restore baseline

### Network Connectivity Verification

**Pre-test Sanity Check (no ACLs):**
```bash
# On TX Host:
sudo python3 -c "
from scapy.all import *
pkt = Ether(src='00:aa:aa:aa:aa:01', dst='00:bb:bb:bb:bb:02')/IP(src='10.0.0.1', dst='20.0.0.2')/ICMP()
sendp(pkt, iface='eth0', verbose=True)
"

# On RX Host (in parallel):
sudo tcpdump -i eth1 'src 00:aa:aa:aa:aa:01' -c 1

# Expected: RX Host captures frame from TX Host MAC address
```

If baseline connectivity fails, troubleshoot:
1. Check link status: `ip link show eth0` (should be UP)
2. Check DUT port status: `show interface status Port1 Port2` (should both be UP)
3. Check DUT VLAN membership: `show vlan brief` (Port1/Port2 should be in same VLAN)
4. Check no L2 ACL is applied: `show acl` or `show access-list` (should be empty)
5. Check physical cable: Verify cable is plugged in and link lights are ON

---

## Legend

| Tag | Meaning                                               |
|-----|-------------------------------------------------------|
| B   | Both VS and HW                                        |
| NEG | Negative/edge case test                               |
| R   | Robustness/persistence test                           |

---

## L2 ACL Test Cases (19 cases)

### Functional Test Cases (8 cases)

| TC ID | Description                           | Tag | Scapy Traffic                                         | Expected              |
|-------|---------------------------------------|-----|-------------------------------------------------------|-----------------------|
| L2-01 | Permit exact source MAC               | B   | `Ether(src="00:AA:AA:AA:AA:01")/IP()`                 | Forwarded             |
| L2-02 | Deny exact source MAC                 | B   | `Ether(src="DE:AD:00:00:00:01")/IP()`                 | Dropped               |
| L2-03 | Deny exact destination MAC            | B   | `Ether(dst="FE:ED:00:00:00:02")/IP()`                 | Dropped               |
| L2-04 | Deny broadcast destination MAC        | B   | `Ether(dst="FF:FF:FF:FF:FF:FF")/ARP()`                | Dropped               |
| L2-05 | Deny EtherType ARP (0x0806)           | B   | `Ether(type=0x0806)/ARP()`                            | Dropped               |
| L2-06 | Deny specific VLAN (VLAN 100)         | B   | `Ether()/Dot1Q(vlan=100)/IP()`                        | Dropped               |
| L2-07 | Permit VLAN 10, deny VLAN 200         | B   | `Dot1Q(vlan=10)/IP()` vs `Dot1Q(vlan=200)/IP()`       | 10=Fwd / 200=Drop     |
| L2-08 | ACL rule priority — permit before deny| B   | `Ether(src="00:AA:AA:AA:AA:01")` with deny-all last   | Forwarded (rule 1 wins)|

### Negative/Edge Case Tests (3 cases)

| TC ID | Description                           | Tag | Scapy Traffic                                         | Expected              |
|-------|---------------------------------------|-----|-------------------------------------------------------|-----------------------|
| L2-N01 | MAC case sensitivity (uppercase hex)  | NEG | `Ether(src="00:aa:aa:aa:aa:01")` lowercase vs rule uppercase | Forwarded (case-insensitive) |
| L2-N02 | Multicast destination MAC             | NEG | `Ether(dst="01:00:5E:00:00:01")/IP()`                 | Forwarded (no rule)   |
| L2-N03 | ACL with invalid/corrupt MAC          | NEG | `Ether(src="ZZ:ZZ:ZZ:ZZ:ZZ:ZZ")` - malformed         | Dropped or error handling |

### Robustness/Persistence Tests (8 cases)

| TC ID | Description                           | Tag | Scapy Traffic                                         | Expected              |
|-------|---------------------------------------|-----|-------------------------------------------------------|-----------------------|
| L2-R01 | ACL rule persistence after DUT reboot | B   | Send traffic before/after simulated reboot            | Rules persist, traffic behavior unchanged |
| L2-R02 | ACL modification while traffic active | B   | Update rule, traffic continues mid-stream             | New packets follow updated rule |
| L2-R03 | Multiple ACL updates in rapid succession | B | Rapid enable/disable of ACL rules (10+ cycles)        | No errors, final state consistent |
| L2-R04 | Concurrent traffic on denied/allowed MAC pairs | B | Two flows with different MAC rules active             | Correct handling of both flows (no crosstalk) |
| L2-R05 | ACL counter accuracy after long traffic run | B | 1000+ packets, verify DUT counter == TX count         | Counter accurate, no overflow/reset |
| L2-R06 | VLAN rule persistence across config changes | B | Add/remove other rules, VLAN ACL still works          | Unaffected by other config changes |
| L2-R07 | ACL aging/timeout behavior (if supported) | B | Send initial traffic, wait 5min, re-send              | Consistent behavior (no state timeout) |
| L2-R08 | Mixed permit/deny rules with same match criteria | NEG | First rule permit, second deny, same MAC              | First rule wins (no ambiguity) |

---

## Test Summary

| Suite    | Functional | Negative | Robustness | Total |
|----------|------------|----------|------------|-------|
| L2 ACL   | 8          | 3        | 8          | 19    |

---

## Pass / Fail Criteria

| ACL Action | Pass Condition                              |
|------------|---------------------------------------------|
| PERMIT     | RX count ≥ 90% of TX count                  |
| DENY       | RX count == 0 (all packets dropped)         |
| Counter    | DUT ACL hit counter == TX packet count      |

---

## File Reference

| File                   | Purpose                                   |
|------------------------|-------------------------------------------|
| `setup_ports.py`       | Configure TX/RX Scapy ports (eth0, eth1)  |
| `l2_acl_traffic.py`    | L2-01 → L2-R08 automated traffic tests    |
| `acl_test_runner.py`   | Master runner with VS/HW filter & report  |

---

## Important Implementation Notes

### Execution & Permissions

- **All scripts require `sudo`** (raw socket operations)
- **Verify interface is correct**: `ethtool -i eth0` should show driver; `ip addr show eth0` should show 10.0.0.1/24
- **Use tcpdump for manual verification**: `sudo tcpdump -i eth1 'src 00:aa:aa:aa:aa:01' -c 5` to independently confirm packet drops

### L2 Switching vs L3 Routing (Critical Difference from L3 Tests)

**L2 ACL Tests:**
- Ports are in **switchport mode** (L2 switching)
- **NO IP addresses** on DUT ports (unlike L3 tests)
- Packets are forwarded based on **MAC address learning**, not IP routing
- VLAN tags determine switching decision
- **Unidirectional traffic**: TX → DUT Port1 → Bridge → DUT Port2 → RX (one-way, no return)

**L3 ACL Tests (for comparison):**
- Ports are in **routed mode** (L3 IP forwarding)
- DUT ports have **IP addresses** (10.0.0.254/24, 20.0.0.254/24)
- Packets are forwarded based on IP routing tables

### Scapy L2 Frame Construction

**Frame Format:**
```
Ether(src=TX_MAC, dst=RX_MAC) / [optional: Dot1Q(vlan=N)] / [optional: IP() / ...]
```

- **L2-01 to L2-05**: Untagged frames: `Ether(src=..., dst=...)/IP()`
- **L2-06 to L2-07**: Tagged frames: `Ether()/Dot1Q(vlan=N)/IP()`

**Checksum & FCS:**
- Scapy auto-computes Ethernet FCS (Frame Check Sequence)
- No manual intervention needed

### Packet Timing

- Default inter-packet delay: 50ms (0.05 sec)
- Default packet count per test: 10 packets
- RX sniff timeout: 4 seconds (sufficient for 10 packets @ 50ms interval)
- If packets don't arrive, increase timeout in l2_acl_traffic.py

### Traffic Direction & MAC Learning

- **Primary flow is UNIDIRECTIONAL**: TX Host → DUT Port1 → Port2 → RX Host
- **Return traffic is NOT tested** (RX does not send packets back to TX)
- DUT learns TX Host MAC from incoming frames on Port1
- DUT forwards based on destination MAC (crafted as RX MAC) to Port2
- RX Host receives frames due to MAC address match, not IP routing

### MAC Address Behavior

**Dynamic MAC Learning:**
- DUT learns TX host MAC from first frame received on Port1
- MAC is added to switching table with aging timer (typically 300 seconds)
- RX MAC in crafted frames must be either:
  - RX host MAC (00:BB:BB:BB:BB:02), OR
  - Broadcast (FF:FF:FF:FF:FF:FF), OR
  - Multicast (01:00:5E:...)

**MAC Aging (L2-R07):**
- Test waits 5 minutes between traffic
- MAC aging timeout is typically 300 seconds
- After aging timeout, MAC entry is deleted and port is flooded to all ports
- Expected behavior: Traffic should still work (frames flooded to all VLAN ports)

**MAC Case Sensitivity (L2-N01):**
- DUT MAC comparison is case-insensitive (standard)
- Example: `00:aa:aa:aa:aa:01` and `00:AA:AA:AA:AA:01` are equivalent
- ACL matching should accept both uppercase and lowercase MAC addresses

### VLAN Handling

**Untagged Frames (L2-01 to L2-05):**
- Frames are in native/default VLAN (typically VLAN 1)
- No 802.1Q tag present in frame
- DUT forwards based on port VLAN membership

**Tagged Frames (L2-06 to L2-07):**
- Frames include 802.1Q VLAN tag (4 bytes)
- `Dot1Q(vlan=10)` creates tag with VLAN ID 10
- DUT forwards based on VLAN membership AND port mode
- VLAN-based ACL rules match on VLAN ID in tag

**Port Configuration for Tests:**
- L2-01 to L2-05: Both ports in VLAN 1 (native), no VLAN tag
- L2-06 (deny VLAN 100): Port1/Port2 in VLAN 1; test uses VLAN 100 (should be dropped)
- L2-07 (permit VLAN 10, deny VLAN 200): Port1/Port2 in VLAN 1; test uses VLAN 10 (permit) and VLAN 200 (deny)

### ARP Handling (L2-04, L2-05)

**L2-04: Broadcast Destination MAC**
- Test sends frame with broadcast MAC (FF:FF:FF:FF:FF:FF) + ARP payload
- DUT behavior depends on default broadcast policy:
  - Some platforms drop broadcast ACL match as security (expected)
  - Some platforms flood broadcast to all VLAN ports
- ACL rule should explicitly deny broadcast MACs if required

**L2-05: EtherType ARP (0x0806)**
- Test sends frame with EtherType 0x0806 (ARP) instead of 0x0800 (IP)
- DUT ACL must match on EtherType field (some platforms use "ether type" keyword)
- Confirmation: `show access-list` should display `EtherType 0x0806` or similar syntax

### Test Case Clarifications

#### **L2-01: Permit Exact Source MAC**
- **Execution**: Sends frame with TX MAC (00:AA:AA:AA:AA:01); should be forwarded
- **Default behavior**: Typically, if no ACL is configured, all traffic is permitted
- **Interpretation**: This test validates that explicit permit rules work (not implicit permit)

#### **L2-02: Deny Exact Source MAC**
- **Execution**: Sends frame with blocked source MAC (DE:AD:00:00:00:01); should be dropped
- **Expected**: RX count = 0 (all packets dropped)

#### **L2-03: Deny Exact Destination MAC**
- **Execution**: Sends frame with non-existent destination MAC (FE:ED:00:00:00:02)
- **Note**: Destination MAC may cause DUT to not forward (MAC not in table); clarify expected behavior
- **Expected**: RX count = 0 (dropped by ACL or MAC table miss)

#### **L2-04: Deny Broadcast Destination MAC (FF:FF:FF:FF:FF:FF)**
- **Execution**: Sends broadcast ARP frame; should be dropped by ACL rule
- **DUT behavior**: Some platforms have special handling for broadcast (always drop, flood, or trap to CPU)
- **Expected**: RX count = 0 if ACL rule denies broadcast

#### **L2-05: Deny EtherType ARP (0x0806)**
- **Execution**: Sends frame with ARP EtherType instead of IP
- **DUT support**: Confirm DUT ACL syntax supports EtherType matching (e.g., `ether type 0x0806`)
- **Expected**: RX count = 0 if ACL denies ARP EtherType

#### **L2-06: Deny Specific VLAN (VLAN 100)**
- **Execution**: Sends frame with VLAN 100 tag; should be dropped
- **Prerequisites**: VLAN 100 must exist on DUT; Port1/Port2 should reject VLAN 100 (or allow it and let ACL drop it)
- **Expected**: RX count = 0 (dropped by VLAN ACL rule)

#### **L2-07: Permit VLAN 10, Deny VLAN 200**
- **Execution**: Two phases:
  - Phase 1: Send VLAN 10 tagged frame → forwarded (RX count ≥ 9/10)
  - Phase 2: Send VLAN 200 tagged frame → dropped (RX count = 0)
- **Prerequisites**: VLANs 10 and 200 must exist; Port1/Port2 must support these VLANs
- **Expected**: VLAN 10 = PERMIT, VLAN 200 = DENY

#### **L2-R01: ACL Rule Persistence After DUT Reboot**
- **Execution**:
  1. Configure ACL rule
  2. Send traffic (should work with rule)
  3. Simulate reboot (write memory + reload)
  4. Send traffic again
- **Expected**: ACL rule persists; traffic behavior unchanged
- **Note**: "Reboot" means configuration reload, not necessarily power cycle

#### **L2-R05: ACL Counter Accuracy (1000+ packets)**
- **Execution**: Send 1000+ packets; verify DUT counter = TX packet count
- **Note**: Baseline tests use 10 packets; this test is 100x larger
- **Expected**: Counter accuracy within ±1 packet (acceptable)
- **Concern**: Counter field size (16-bit vs 32-bit vs 64-bit); document if counter overflows

#### **L2-R07: MAC Aging/Timeout Behavior (5-minute wait)**
- **Execution**:
  1. Send initial traffic (TX MAC is learned)
  2. Wait 5 minutes (MAC aging timeout is typically 300 seconds)
  3. Send traffic again
- **Expected**: Traffic still works (MAC relearned or flooded)
- **Note**: L2-R07 tests MAC table aging, not ACL aging (ACLs don't age)
- **Clarification**: Document DUT's MAC aging timeout value

### Counter Validation

**DUT L2 ACL Hit Counters:**
- Query with: `show access-list ACLNAME` or `show l2-acl` (platform-specific)
- Compare counter value against expected packet count (sent)
- Acceptable margin: ±1 packet (due to timing/processing)
- **Note**: L2 ACL counters may be per-rule or per-table (platform-specific)
- **Important**: Counter matching TX packet count is manual validation (NOT auto-checked)

### Negative (NEG) & Robustness (R) Test Notes

**Negative Tests** (L2-N01 through L2-N03):
- Verify edge cases, malformed inputs, and boundary conditions
- Expected outcomes may vary by platform (VS vs HW)
- **L2-N01 (Case sensitivity)**: Confirm DUT MAC comparison is case-insensitive
- **L2-N02 (Multicast)**: Some platforms flood multicast; define baseline behavior first
- **L2-N03 (Invalid MAC)**: Test with malformed MAC addresses (if Scapy allows); expect DUT to drop

**Robustness Tests** (L2-R01 through L2-R08):
- Verify ACL stability across configuration changes and traffic stress
- Most tests should pass on both VS and HW unless explicitly tagged HW
- Tests verify **lack of state leakage** (rules don't interfere with each other)

### Scapy Version & Dependencies

- Minimum Scapy version: 2.4.4
- Tested with: Scapy 2.5.0+ on Python 3.9+
- Optional: tcpdump for independent packet verification
- Optional: iperf3 for sustained traffic tests (robustness tests)

### Key Differences: L2 vs L3 ACL Testing

| Aspect | L2 ACL | L3 ACL |
|--------|--------|--------|
| **DUT Port Mode** | Switchport (L2) | Routed (L3) |
| **Port IPs** | None (unrouted) | 10.0.0.254/24, 20.0.0.254/24 |
| **Forwarding** | MAC switching + VLAN bridging | IP routing |
| **ACL Scope** | MAC, EtherType, VLAN | IP, protocol, TCP/UDP, DSCP |
| **VLAN Dependency** | Critical (native + tagged) | Not tested |
| **MAC Learning** | Dynamic (aging timer) | N/A (IP-based) |
| **Test Framework** | L2-only frames + Scapy | L2 + L3 frames + Scapy |

### Troubleshooting

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| "No such device" error | Interface eth0/eth1 doesn't exist | Verify interface names; may be ens3, veth*, etc. |
| "Permission denied" | Missing sudo or CAP_NET_RAW | Run with `sudo`; verify `getcap` |
| RX Host sees 0 packets | Port1/Port2 not in same VLAN | Check `show vlan brief` on DUT |
| RX Host sees 0 packets | DUT ports not in switchport mode | Check `show interface mode` or `show running-config` |
| RX Host sees some packets | ACL not configured or misconfigured | Verify ACL applied with `show acl` on DUT |
| Packet count mismatch (< 90%) | High packet loss on network | Reduce inter-packet delay; check MTU/link quality |
| All tests fail | Frame switching not working | Verify Port1/Port2 are UP and in same VLAN |
| L2-06/L2-07 fail | VLANs 100/200 don't exist | Create VLANs: `vlan 100`, `vlan 200`, etc. |
