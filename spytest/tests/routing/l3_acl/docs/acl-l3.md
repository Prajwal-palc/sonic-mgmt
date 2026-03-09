# L3 ACL Test Plan — Minimal Topology

## Overview

This test plan validates L3 (Layer 3 / IP-level) Access Control Lists on a Device Under Test using external Scapy-based traffic generation. **All tests are executed with traffic flowing from external TX and RX hosts (NOT running inside the DUT).**

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
         │  packets)                        Scapy  │
         │                                 sniff)  │
         │                                         │
         ├─────────────[ DUT (VS or HW) ]─────────┤
         │          Port1    ↔    Port2           │
         │       (ACL Ingress applied here)       │
         │                                         │
         └─────────────────────────────────────────┘

DUT forwarding path: Port1 (RX) → ACL → Routing Decision → Port2 (TX)
```

### Key Architecture Decisions

1. **External Traffic Sources**: Scapy runs on separate physical or virtual hosts connected to DUT ports (not containerized within DUT-VS)
2. **Unidirectional Primary Flow**: TX Host → DUT Port1 → Routing → DUT Port2 → RX Host (one-way)
3. **ACL Enforcement Point**: Ingress on Port1 (ACLs are evaluated immediately upon packet arrival)
4. **Return Path**: Return traffic (RX → TX) is NOT tested in baseline test cases; TCP ACK tests (L3-09) use crafted packets with predetermined seq/ack numbers

| Role        | Interface | IP Address  | MAC Address       | OS/Platform |
|-------------|-----------|-------------|-------------------|-------------|
| TX (Sender) | eth0      | 10.0.0.1/24 | 00:AA:AA:AA:AA:01 | Linux (any) |
| RX (Receiver)| eth1     | 20.0.0.2/24 | 00:BB:BB:BB:BB:02 | Linux (any) |
| DUT Port1   | Port1     | (See DUT setup) | Inherits from port | SONiC VS/HW |
| DUT Port2   | Port2     | (See DUT setup) | Inherits from port | SONiC VS/HW |

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

**Port Connectivity:**
- Port1 and Port2 must be operationally UP (link layer)
- Verify: `show interface status | grep -E "Port1|Port2"`

**L3 Configuration (Required for Routing):**
```
DUT# configure terminal
DUT# interface Port1
DUT# no shutdown
DUT# ip address 10.0.0.254 255.255.255.0
DUT# exit
DUT# interface Port2
DUT# no shutdown
DUT# ip address 20.0.0.254 255.255.255.0
DUT# exit
```

**Routing Setup:**
- Each port must be in a routable subnet
- TX Host (10.0.0.1/24) connects to Port1 (10.0.0.254/24)
- RX Host (20.0.0.2/24) connects to Port2 (20.0.0.254/24)
- Verify routing: `show ip route` should show both subnets

**MTU Configuration:**
- Verify Port1 and Port2 MTU ≥ 1500 bytes (standard Ethernet):
  ```
  DUT# show interface status | grep -E "MTU|Port[12]"
  ```
- If testing jumbo frames, configure accordingly on all devices

**Baseline ACL State:**
- DUT should start with **NO ACLs** applied (or all in `shutdown` state)
- Each test case explicitly configures its required ACL rules
- After each test, ACL rules are REMOVED to restore baseline

### Network Connectivity Verification

**Pre-test Sanity Check (no ACLs):**
```bash
# On TX Host:
sudo python3 -c "
from scapy.all import *
pkt = IP(src='10.0.0.1', dst='20.0.0.2')/ICMP()
send(pkt, iface='eth0', verbose=True)
"

# On RX Host (in parallel):
sudo tcpdump -i eth1 'src 10.0.0.1' -c 1

# Expected: RX Host captures ICMP from TX Host
```

If baseline connectivity fails, troubleshoot:
1. Check link status: `ip link show eth0` (should be UP)
2. Check IP config: `ip addr show eth0` (should show 10.0.0.1/24)
3. Check DUT routing: `show ip route 10.0.0.0/24` (should show Port1)
4. Check physical cable: Verify cable is plugged in and link lights are ON

---

## Legend

| Tag | Meaning                                               |
|-----|-------------------------------------------------------|
| VS  | Virtual/software DUT (OVS, SONiC-VS, FRR, etc.)      |
| HW  | Physical ASIC/TCAM required                           |
| B   | Both VS and HW                                        |
| NEG | Negative/edge case test                               |
| R   | Robustness/persistence test                           |

---

## 4.1 IP Address Match (9 cases)

### Functional Test Cases (3 cases)

| TC ID | Description                      | Tag | Scapy Traffic                                         | Expected  |
|-------|----------------------------------|-----|-------------------------------------------------------|-----------|
| L3-01 | Deny source IP (host)            | B   | `IP(src="10.0.0.99")/ICMP()`                          | Dropped   |
| L3-02 | Deny source IP subnet /24        | B   | `IP(src="10.0.0.50")/UDP()` (any host in .0/24)       | Dropped   |
| L3-03 | Deny destination IP (host)       | B   | `IP(src="10.0.0.1", dst="20.0.0.99")/TCP()`           | Dropped   |

### Negative/Edge Case Tests (3 cases)

| TC ID | Description                      | Tag | Scapy Traffic                                         | Expected  |
|-------|----------------------------------|-----|-------------------------------------------------------|-----------|
| L3-N01 | Overlapping IP subnets (more specific rule) | NEG | `IP(src="10.0.0.0/25")` and `IP(src="10.0.0.0/24")` rules conflict | More specific rule (/25) takes precedence |
| L3-N02 | IP broadcast address (255.255.255.255) | NEG | `IP(dst="255.255.255.255")/ICMP()`                    | Dropped or handled per policy |
| L3-N03 | Malformed/invalid IP address     | NEG | Crafted packet with truncated IP header               | Dropped or error handling |

### Robustness/Persistence Tests (3 cases)

| TC ID | Description                      | Tag | Scapy Traffic                                         | Expected  |
|-------|----------------------------------|-----|-------------------------------------------------------|-----------|
| L3-R01 | ACL rule persistence after IP config change | B | Change TX/RX IP, rules still applied                  | Rules persist, traffic behavior unchanged |
| L3-R02 | High-frequency rule updates with live traffic | B | Modify rule 100+ times/sec while sending packets      | No errors, consistent final state |
| L3-R03 | Concurrent multiple IP-based ACL rules | B | Multiple overlapping IP rules, send varied traffic    | All rules evaluated correctly, no cross-interference |

---

## 4.2 Protocol Match (12 cases)

### Functional Test Cases (4 cases)

| TC ID | Description                      | Tag | Scapy Traffic                                         | Expected          |
|-------|----------------------------------|-----|-------------------------------------------------------|-------------------|
| L3-04 | Deny ICMP                        | B   | `IP()/ICMP(type=8)`                                   | Dropped           |
| L3-05 | Deny UDP, permit TCP             | B   | `IP()/UDP(dport=53)` vs `IP()/TCP(dport=80)`          | UDP=Drop, TCP=Fwd |
| L3-06 | Deny TCP destination port 80     | B   | `IP()/TCP(dport=80, flags="S")`                       | Dropped           |
| L3-07 | Deny UDP destination port 53     | B   | `IP()/UDP(dport=53)`                                  | Dropped           |

### Negative/Edge Case Tests (3 cases)

| TC ID | Description                      | Tag | Scapy Traffic                                         | Expected          |
|-------|----------------------------------|-----|-------------------------------------------------------|-------------------|
| L3-N04 | Unknown/reserved protocol number | NEG | `IP(proto=99)/Raw()` - undefined protocol             | Dropped or default action |
| L3-N05 | Port range edge cases (0, 65535) | NEG | `IP()/TCP(dport=0)` and `TCP(dport=65535)`            | Correct handling per rule |

### Robustness/Persistence Tests (5 cases)

| TC ID | Description                      | Tag | Scapy Traffic                                         | Expected          |
|-------|----------------------------------|-----|-------------------------------------------------------|-------------------|
| L3-R04 | Protocol rule persistence during port config change | B | Modify interface speed/config, rules persist         | Rules unaffected by port config |
| L3-R05 | ACL rule state consistency under protocol stress | B | Rapid protocol type changes (ICMP→UDP→TCP)           | Rules evaluate correctly each change |
| L3-R06 | Deny + Permit protocol rules with same IP | B | `IP(src=X)/DENY` + `IP(src=X)/PERMIT TCP`            | First matching rule wins |

---

## 4.3 TCP Flags (7 cases)

### Functional Test Cases (2 cases)

| TC ID | Description                      | Tag | Scapy Traffic                                         | Expected  |
|-------|----------------------------------|-----|-------------------------------------------------------|-----------|
| L3-08 | Deny TCP SYN (new connections)   | B   | `IP()/TCP(dport=80, flags="S")`                       | Dropped   |
| L3-09 | Permit TCP ACK (established)     | B   | `IP()/TCP(dport=80, flags="A", seq=100, ack=1)`       | Forwarded |

### Negative/Edge Case Tests (2 cases)

| TC ID | Description                      | Tag | Scapy Traffic                                         | Expected  |
|-------|----------------------------------|-----|-------------------------------------------------------|-----------|
| L3-N06 | TCP flags with invalid combinations (SYN+FIN) | NEG | `IP()/TCP(flags="SF")`                                | Dropped or flagged invalid |
| L3-N07 | TCP flag match with zero flags   | NEG | `IP()/TCP(flags=0x00)`                                | Handled per policy (unusual) |

### Robustness/Persistence Tests (3 cases)

| TC ID | Description                      | Tag | Scapy Traffic                                         | Expected  |
|-------|----------------------------------|-----|-------------------------------------------------------|-----------|
| L3-R07 | TCP flag rule persistence across connection resets | B | RST flag, then retransmit, rules still applied        | Rules persist, behavior consistent |
| L3-R08 | Stateful TCP flag evaluation under sustained traffic | B | Long-lived TCP stream, 10000+ packets                 | Consistent flag evaluation, no state leak |
| L3-R09 | Concurrent TCP SYN and ACK from different flows | B | Two TCP flows (one SYN, one ACK) simultaneously        | Each evaluated correctly, no cross-talk |

---

## 4.4 Combined & Functional (10 cases)

### Functional Test Cases (3 cases)

| TC ID | Description                      | Tag | Scapy Traffic                                         | Expected  |
|-------|----------------------------------|-----|-------------------------------------------------------|-----------|
| L3-10 | Deny 5-tuple flow                | B   | `IP(src="10.0.0.99",dst="20.0.0.2")/TCP(dport=80)`   | Dropped   |
| L3-11 | Implicit deny-all                | B   | `IP(src="172.16.0.1")/ICMP()` (no matching permit)   | Dropped   |
| L3-12 | Deny DSCP EF (tos=0xB8)          | HW  | `IP(tos=0xB8)/UDP()`                                  | Dropped   |

### Negative/Edge Case Tests (2 cases)

| TC ID | Description                      | Tag | Scapy Traffic                                         | Expected  |
|-------|----------------------------------|-----|-------------------------------------------------------|-----------|
| L3-N08 | 5-tuple with all zeros (no match) | NEG | `IP(src="0.0.0.0", dst="0.0.0.0")/TCP(sport=0, dport=0)` | Handled per policy |
| L3-N09 | DSCP value edge cases (0, 63)    | NEG | `IP(tos=0x00)/UDP()` and `IP(tos=0xFC)/UDP()`         | Correct handling |

### Robustness/Persistence Tests (5 cases)

| TC ID | Description                      | Tag | Scapy Traffic                                         | Expected  |
|-------|----------------------------------|-----|-------------------------------------------------------|-----------|
| L3-R10 | ACL rule persistence after DSCP config change | HW | Modify QoS policies, DSCP ACL still works             | Rules unaffected by QoS config |
| L3-R11 | 5-tuple rule accuracy under 100K+ packet streams | B | Long sustained flow, verify rule hit counter          | Counter accurate, no packet loss |
| L3-R12 | Mixed 5-tuple and subnet-based rules | B | Apply both types simultaneously, varied traffic       | All rules evaluated without interference |
| L3-R13 | ACL rule atomicity during rapid reconfig | B | Update 5-tuple rule while traffic active              | Atomic update, no intermediate state inconsistency |
| L3-R14 | Implicit deny enforcement with permit rules present | B | Permit some traffic, deny others implicitly           | Implicit deny works, no false forwards |

---

## Test Summary

| Suite    | Functional | Negative | Robustness | Total |
|----------|------------|----------|------------|-------|
| L3 ACL   | 12         | 9        | 13         | 34    |

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
| `l3_acl_traffic.py`    | L3-01 → L3-R14 automated traffic tests    |
| `acl_test_runner.py`   | Master runner with VS/HW filter & report  |

---

## Important Implementation Notes

### Execution & Permissions

- **All scripts require `sudo`** (raw socket operations)
- **Verify interface is correct**: `ethtool -i eth0` should show driver; `ip addr show eth0` should show 10.0.0.1/24
- **Use tcpdump for manual verification**: `sudo tcpdump -i eth1 'src 10.0.0.1' -c 5` to independently confirm packet drops

### Traffic Generation Details

**Scapy Packet Construction:**
- All L2 frames are crafted manually with `Ether(src=TX_MAC, dst=RX_MAC)`
- IP checksums are auto-computed by Scapy (no manual intervention needed)
- TCP/UDP checksums are auto-computed
- Packets are sent via `sendp(..., iface='eth0', verbose=False)` (L2-level send)

**Packet Timing:**
- Default inter-packet delay: 50ms (0.05 sec)
- Default packet count per test: 10 packets
- RX sniff timeout: 4 seconds (sufficient for 10 packets @ 50ms interval)
- If packets don't arrive, increase timeout in l3_acl_traffic.py

**Traffic Direction & Statefulness:**
- **Primary flow is UNIDIRECTIONAL**: TX Host → DUT Port1 → Port2 → RX Host
- **Return traffic is NOT tested** (RX does not send packets back to TX)
- **TCP ACK test (L3-09)** uses crafted ACK packets with predetermined seq/ack numbers (NOT a real TCP handshake)
- **Implications**: DUT does NOT need to establish any TCP state; it simply forwards or drops packets based on header fields

### Test Case Clarifications

#### **L3-R01: ACL Rule Persistence After IP Config Change**
- **Execution**: Tests that ACL rules remain applied when host IP addresses change
- **Implementation**:
  1. Configure ACL rule blocking traffic from 10.0.0.99
  2. Send traffic from 10.0.0.1 (should PASS)
  3. Send traffic from 10.0.0.99 (should DROP due to ACL)
  4. Modify TX host IP to 10.0.0.100 (change `ip addr` on eth0)
  5. Send traffic again from 10.0.0.100 (should PASS; rule doesn't match new IP)
- **Pass Criteria**: ACL rule continues to work correctly after host IP reconfiguration

#### **L3-R02: High-Frequency Rule Updates with Live Traffic**
- **Execution**: Rapidly modify ACL rules (100+ times/sec) while continuously sending traffic
- **Implementation**:
  1. Start background thread continuously sending packets from TX
  2. In foreground, repeatedly add/remove ACL rules at maximum speed (via DUT CLI)
  3. Monitor RX to detect any traffic anomalies (sudden drops/passes)
  4. Verify final DUT state matches expected rules
- **Pass Criteria**:
  - No errors during rapid rule updates
  - No unintended packet loss/passes during updates
  - Final state is consistent with last rule applied
- **Note**: May require SM_ISCLI batched commands for performance; native CLI may be too slow

#### **L3-09: Permit TCP ACK (Established Session)**
- **Execution**: Forward packets with TCP ACK flag set
- **Details**:
  - Packets are CRAFTED (not from real TCP handshake)
  - Source/dest IPs and ports are static
  - TCP flags field has ACK bit set (flags="A")
  - seq/ack numbers are predetermined (seq=100, ack=1)
- **Pass Criteria**: Packets with ACK flag are forwarded (RX count ≥ 90% of TX count)
- **Important**: DUT does NOT verify TCP sequence/acknowledgment numbers or TCP state; it only checks the ACK flag bit

#### **L3-12: Deny DSCP EF (QoS Field)**
- **Platform**: **HW only** — skip on SONiC-VS
- **Prerequisites**:
  - DUT must have QoS classification rules configured to recognize DSCP EF (0xB8)
  - ACL rule must match DSCP field (using `tos` byte in IP header)
- **Scapy Packet**: `IP(tos=0xB8)/UDP()` (DSCP EF is 6 MSBs of ToS byte; 0xB8 = 10111000 binary)
- **Expected**: Packets dropped if ACL rule denies DSCP EF
- **VS Behavior**: VS may not support DSCP classification; test typically skipped on VS

### Counter Validation

**DUT ACL Hit Counters:**
- Query with: `show acl ACLTABLE --verbose` or `show acl ACLRULE ACLNAME`
- Compare counter value against expected packet count (sent)
- Acceptable margin: ±1 packet (due to timing/processing)
- **Note**: Implementation does NOT currently validate counters; manual verification required

### Negative (NEG) & Robustness (R) Test Notes

**Negative Tests** (L3-N01 through L3-N09):
- Verify edge cases, malformed inputs, and boundary conditions
- Expected outcomes may vary by platform (VS vs HW)
- **L3-N02 (Broadcast)**: Some platforms drop broadcasts automatically; define baseline behavior first
- **L3-N03 (Malformed IP)**: Test with truncated IP headers, invalid header length, etc.

**Robustness Tests** (L3-R01 through L3-R14):
- Verify ACL stability across configuration changes and traffic stress
- Most tests should pass on both VS and HW unless explicitly tagged HW
- Tests verify **lack of state leakage** (rules don't interfere with each other)

### Scapy Version & Dependencies

- Minimum Scapy version: 2.4.4
- Tested with: Scapy 2.5.0+ on Python 3.9+
- Optional: tcpdump for independent packet verification
- Optional: iperf3 for sustained traffic tests (robustness tests)

### Troubleshooting

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| "No such device" error | Interface eth0/eth1 doesn't exist | Verify interface names; may be ens3, veth*, etc. |
| "Permission denied" | Missing sudo or CAP_NET_RAW | Run with `sudo`; verify `getcap` |
| RX Host sees 0 packets | No L3 route between subnets | Check `show ip route` on DUT |
| RX Host sees some packets | ACL not configured or misconfigured | Verify ACL applied with `show acl` on DUT |
| Packet count mismatch (< 90%) | High packet loss on network | Reduce inter-packet delay; check MTU/link quality |
