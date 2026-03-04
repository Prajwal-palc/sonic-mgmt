# L3 ACL Test Plan — Minimal Topology

## Topology

```
  +-----------+   eth0       eth1   +-----------+
  |  Scapy TX +-------[ DUT ]-------+ Scapy RX  |
  | 10.0.0.1  |     Port1  Port2    | 20.0.0.2  |
  | MAC: AA:01|   ACL applied IN    | MAC: BB:02|
  +-----------+                     +-----------+
```

**Two hosts connected to a Device Under Test (DUT) with two ports. All Access Control Lists (ACLs) are applied ingress on DUT Port1.**

| Role        | Interface | IP Address  | MAC               |
|-------------|-----------|-------------|-------------------|
| TX (Sender) | eth0      | 10.0.0.1/24 | 00:AA:AA:AA:AA:01 |
| RX (Receiver)| eth1     | 20.0.0.2/24 | 00:BB:BB:BB:BB:02 |

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

## Notes

- All scripts require `sudo` (raw packet socket).
- Verify `conf.iface` is set to the correct interface before running.
- Use `tcpdump -i eth1` on the RX side to independently confirm drops.
- L3-12 (DSCP) requires ASIC QoS/DSCP classification support — skip on VS.
- Negative (NEG) tests verify edge cases, invalid input handling, and error resilience.
- Robustness (R) tests verify persistence, consistency, and lack of state leakage across reconfigurations.
- All robustness tests should pass on both VS and HW platforms unless explicitly tagged HW.
